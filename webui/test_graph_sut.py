#!/usr/bin/env python3
"""Phase 6 — graph SUT tests: verify the typed-graph answerer beats naive floor on answer_relevance.

38 checks covering: corpus loading, BM25 index, command extraction, concept promotion,
fault-path vs. graph-path routing, SUT contract, and the key thesis metric comparison.
"""
import os
import sys
import math

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from opsrag import graph_sut as gs
from opsrag import evaluator

_PASS = _FAIL = 0


def ok(label: str) -> None:
    global _PASS
    _PASS += 1
    print(f"  PASS  {label}")


def fail(label: str, detail: str = "") -> None:
    global _FAIL
    _FAIL += 1
    print(f"  FAIL  {label}" + (f": {detail}" if detail else ""))


def check(cond: bool, label: str, detail: str = "") -> None:
    ok(label) if cond else fail(label, detail)


# ---------------------------------------------------------------------------
# 1. Corpus loading
# ---------------------------------------------------------------------------

def test_corpus():
    gs.invalidate_index()
    corpus, _ = gs._index()
    types = {c["type"] for c in corpus}
    check("pattern" in types, "corpus contains pattern docs")
    check("fault" in types, "corpus contains fault docs")
    check("concept" in types, "corpus contains concept docs")

    concepts = [c for c in corpus if c["type"] == "concept"]
    check(len(concepts) >= 20, f"at least 20 concept paragraphs ({len(concepts)})")

    patterns = [c for c in corpus if c["type"] == "pattern"]
    check(len(patterns) >= 1, f"at least one pattern file ({len(patterns)})")

    faults = [c for c in corpus if c["type"] == "fault"]
    check(len(faults) >= 3, f"at least 3 fault docs ({len(faults)})")


# ---------------------------------------------------------------------------
# 2. BM25 index internals
# ---------------------------------------------------------------------------

def test_bm25():
    gs.invalidate_index()
    corpus, bm25 = gs._index()

    # Verify IDF is populated
    check(len(bm25._idf) > 0, "BM25 IDF populated")

    # Score ordering: "session-establishment BGP TCP OpenConfirm" should rank session concept #1
    query = "BGP session TCP OpenConfirm state machine"
    top = bm25.top_k(query, k=5)
    check(len(top) == 5, "top_k returns 5 results")

    top_idxs = [i for i, _ in top]
    top_sources = [corpus[i]["source"] for i in top_idxs]
    check(any("session" in s for s in top_sources), f"session concept in top-5 for session query: {top_sources}")

    # Route reflector query
    rr_top = bm25.top_k("iBGP route reflector cluster ORIGINATOR_ID", k=5)
    rr_sources = [corpus[i]["source"] for i, _ in rr_top]
    check(any("reflector" in s or "rr" in s.lower() for s in rr_sources), f"RR concept ranked for RR query: {rr_sources}")

    # Zero-match query produces some results (not crash)
    z_top = bm25.top_k("xyzzy foobar nonexistent token", k=3)
    check(len(z_top) == 3, "top_k returns 3 even for zero-match query")


# ---------------------------------------------------------------------------
# 3. Tokeniser
# ---------------------------------------------------------------------------

def test_tokeniser():
    toks = gs._tok("BGP session state: OpenConfirm!")
    check("bgp" in toks, "tokeniser lowercases")
    check("openconfirm" in toks, "tokeniser strips punctuation")
    check("state" not in toks or "session" in toks, "tokeniser keeps content words")

    toks2 = gs._tok("the is a an")
    check(len(toks2) == 0, "tokeniser strips stopwords-only input")


# ---------------------------------------------------------------------------
# 4. Command extraction
# ---------------------------------------------------------------------------

def test_cmd_extraction():
    text = (
        "Run show bgp summary to see sessions. "
        "Use show ip bgp neighbors 192.0.2.1 for detail. "
        "ping 10.0.0.1 to test reachability. "
        "Avoid show version in production."
    )
    cmds = gs._extract_commands(text)
    cmd_strs = [c["cmd"].lower() for c in cmds]
    check(any("show bgp summary" in c for c in cmd_strs), "extracts 'show bgp summary'")
    check(any("show ip bgp neighbors" in c for c in cmd_strs), "extracts 'show ip bgp neighbors'")
    check(any("ping" in c for c in cmd_strs), "extracts ping")

    # No commands in irrelevant text
    empty = gs._extract_commands("The route reflector uses CLUSTER_LIST for loop prevention.")
    check(len(empty) == 0, "no commands extracted from concept-only text")


# ---------------------------------------------------------------------------
# 5. Concept promotion
# ---------------------------------------------------------------------------

def test_concept_promotion():
    gs.invalidate_index()
    corpus, bm25 = gs._index()

    # For a session-establishment question, the session concept should be promoted
    q = {
        "id": "test-01",
        "question": "What state immediately precedes Established in the BGP FSM?",
        "category": "session-establishment",
        "difficulty": "recall",
        "ground_truth": {"answer": "OpenConfirm", "commands": []},
    }
    resp = gs.graph_sut(q)
    check("answer" in resp, "graph_sut returns 'answer' key")
    check("retrieved_context" in resp, "graph_sut returns 'retrieved_context' key")
    check("commands" in resp, "graph_sut returns 'commands' key")
    check(isinstance(resp["answer"], str), "answer is a string")
    check(len(resp["answer"]) > 0, "answer is non-empty for recall question")

    # Answer should contain 'OpenConfirm' (it's in the concept paragraph)
    check("OpenConfirm" in resp["answer"], f"session concept promoted (answer starts: {resp['answer'][:60]!r})")


# ---------------------------------------------------------------------------
# 6. Category alias resolution
# ---------------------------------------------------------------------------

def test_alias():
    q = {
        "id": "test-02",
        "question": "How does BGP ADD-PATH improve path visibility through a route reflector?",
        "category": "addpath",   # alias → add-path-advanced
        "difficulty": "apply",
        "ground_truth": {"answer": "ADD-PATH path-ID", "commands": []},
    }
    resp = gs.graph_sut(q)
    check(len(resp["answer"]) > 0, "alias category resolves and returns answer")
    check("ADD-PATH" in resp["answer"] or "path" in resp["answer"].lower(),
          f"ADD-PATH concept in answer: {resp['answer'][:80]!r}")


# ---------------------------------------------------------------------------
# 7. Fault-linked routing
# ---------------------------------------------------------------------------

def test_fault_routing():
    q_fault = {
        "id": "q001",
        "question": "eBGP session stays in Active. remote-as mismatch suspected.",
        "category": "session-establishment",
        "difficulty": "diagnose",
        "fault_id": "f-bgp-wrong-remote-as",
        "ground_truth": {"answer": "remote-as mismatch", "commands": []},
    }
    resp = gs.graph_sut(q_fault)
    check("remote-as" in resp["answer"].lower() or "mismatch" in resp["answer"].lower(),
          f"fault path used for fault_id question: {resp['answer'][:80]!r}")
    check(len(resp["commands"]) > 0, "fault path emits commands")


# ---------------------------------------------------------------------------
# 8. SUT contract compliance
# ---------------------------------------------------------------------------

def test_contract():
    import os
    bm_dir = os.path.join(os.path.dirname(_HERE), "thesis", "benchmark")
    qs = []
    import json
    for fn in sorted(os.listdir(bm_dir)):
        if fn.endswith(".json") and fn != "schema.json":
            with open(os.path.join(bm_dir, fn)) as fh:
                qs.extend(json.load(fh))

    # Sample 20 questions to verify contract without running the full benchmark
    sample = qs[::10][:20]
    errors = []
    for q in sample:
        try:
            r = gs.graph_sut(q)
            if not isinstance(r.get("answer"), str):
                errors.append(f"{q['id']}: answer not str")
            if not isinstance(r.get("commands"), list):
                errors.append(f"{q['id']}: commands not list")
        except Exception as e:
            errors.append(f"{q['id']}: {e}")

    check(len(errors) == 0, f"SUT contract for 20 sampled questions ({errors[:3] if errors else 'ok'})")


# ---------------------------------------------------------------------------
# 9. Answer relevance comparison: graph_sut vs naive_sut vs opsrag_sut
# ---------------------------------------------------------------------------

def test_answer_relevance():
    """The thesis metric comparison — graph_sut must beat naive on answer_relevance."""
    import os, json
    bm_dir = os.path.join(os.path.dirname(_HERE), "thesis", "benchmark")

    # Evaluate a 50-question sample for speed
    all_qs = []
    for fn in sorted(os.listdir(bm_dir)):
        if fn.endswith(".json") and fn != "schema.json":
            with open(os.path.join(bm_dir, fn)) as fh:
                all_qs.extend(json.load(fh))
    sample = all_qs[::4][:50]

    def _ar(sut_fn):
        scores = []
        for q in sample:
            resp = sut_fn(q)
            gt = q.get("ground_truth", {}).get("answer", "")
            scores.append(evaluator.answer_relevance(resp["answer"], gt))
        return sum(scores) / len(scores)

    graph_ar = _ar(gs.graph_sut)
    naive_ar = _ar(evaluator.naive_sut)
    opsrag_ar = _ar(evaluator.opsrag_sut)

    print(f"    answer_relevance: graph={graph_ar:.3f}  naive={naive_ar:.3f}  opsrag={opsrag_ar:.3f}")

    check(graph_ar > naive_ar, f"graph_sut AR ({graph_ar:.3f}) > naive AR ({naive_ar:.3f})")
    check(graph_ar > opsrag_ar, f"graph_sut AR ({graph_ar:.3f}) > opsrag_sut AR ({opsrag_ar:.3f})")
    check(graph_ar >= 0.05, f"graph_sut AR >= 0.05 (minimum useful level): {graph_ar:.3f}")


# ---------------------------------------------------------------------------
# 10. Executability is preserved for fault questions
# ---------------------------------------------------------------------------

def test_executability():
    import os, json
    bm_dir = os.path.join(os.path.dirname(_HERE), "thesis", "benchmark")
    all_qs = []
    for fn in sorted(os.listdir(bm_dir)):
        if fn.endswith(".json") and fn != "schema.json":
            with open(os.path.join(bm_dir, fn)) as fh:
                all_qs.extend(json.load(fh))

    fault_qs = [q for q in all_qs if q.get("fault_id")]
    pass_count = 0
    for q in fault_qs:
        resp = gs.graph_sut(q)
        if evaluator.executability(resp["commands"]):
            pass_count += 1

    rate = pass_count / len(fault_qs) if fault_qs else 0
    check(rate >= 0.9, f"fault questions executability rate {rate:.2f} >= 0.90 ({pass_count}/{len(fault_qs)})")


# ---------------------------------------------------------------------------
# 11. Index cache + invalidation
# ---------------------------------------------------------------------------

def test_cache():
    gs.invalidate_index()
    c1, b1 = gs._index()
    c2, b2 = gs._index()
    check(c1 is c2, "index is cached (same object on second call)")
    gs.invalidate_index()
    c3, b3 = gs._index()
    check(c3 is not c1, "invalidate_index forces rebuild")


# ---------------------------------------------------------------------------
# 12. New concept categories (Phase 7 — 52 concepts total)
# ---------------------------------------------------------------------------

def test_new_concepts():
    """Verify Phase 7 concept additions: as-path-loop, local-preference, 12 new categories."""
    new_cats = [
        "as-path-loop", "local-preference",
        "ibgp-scaling", "bgp-timers", "peer-groups", "prefix-filter",
        "bgp-attributes", "network-import", "bgp-convergence", "rib-fib",
        "weight-policy", "bgp-monitoring", "bgp-multihop-advanced", "bgp-capacity",
    ]
    concepts = gs._CONCEPTS
    missing = [c for c in new_cats if c not in concepts]
    check(len(missing) == 0, f"all 14 new concept categories present (missing: {missing})")
    check(len(concepts) >= 50, f"total concepts >= 50 ({len(concepts)} found)")

    # Spot-check retrieval quality for two new categories
    gs.invalidate_index()
    q_lp = {
        "id": "test-lp-01",
        "question": "An inbound route-map on the iBGP session to the route reflector sets local-preference 50. How does this affect path selection?",
        "category": "local-preference",
        "difficulty": "apply",
        "ground_truth": {"answer": "local-preference", "commands": []},
    }
    resp_lp = gs.graph_sut(q_lp)
    check(
        "local-preference" in resp_lp["answer"].lower() or "local-pref" in resp_lp["answer"].lower(),
        f"local-preference concept promoted (answer: {resp_lp['answer'][:80]!r})"
    )

    q_asp = {
        "id": "test-asp-01",
        "question": "R2 receives a BGP UPDATE but the prefix is silently discarded despite the session being Established. Own AS appears in AS_PATH.",
        "category": "as-path-loop",
        "difficulty": "diagnose",
        "ground_truth": {"answer": "AS_PATH loop", "commands": []},
    }
    resp_asp = gs.graph_sut(q_asp)
    check(
        "as_path" in resp_asp["answer"].lower() or "loop" in resp_asp["answer"].lower() or "as 65001" in resp_asp["answer"].lower(),
        f"as-path-loop concept promoted (answer: {resp_asp['answer'][:80]!r})"
    )

    q_rib = {
        "id": "test-rib-01",
        "question": "What is the difference between BGP Adj-RIB-In, Loc-RIB, and Adj-RIB-Out?",
        "category": "rib-fib",
        "difficulty": "recall",
        "ground_truth": {"answer": "Adj-RIB-In", "commands": []},
    }
    resp_rib = gs.graph_sut(q_rib)
    check(
        "rib" in resp_rib["answer"].lower(),
        f"rib-fib concept promoted (answer: {resp_rib['answer'][:80]!r})"
    )

    q_cap = {
        "id": "test-cap-01",
        "question": "How does maximum-prefix protect a BGP router from a peer advertising too many routes?",
        "category": "bgp-capacity",
        "difficulty": "recall",
        "ground_truth": {"answer": "maximum-prefix", "commands": []},
    }
    resp_cap = gs.graph_sut(q_cap)
    check(
        "maximum-prefix" in resp_cap["answer"].lower() or "prefix" in resp_cap["answer"].lower(),
        f"bgp-capacity concept promoted (answer: {resp_cap['answer'][:80]!r})"
    )


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== graph SUT tests ===")
    print("--- corpus ---")
    test_corpus()
    print("--- BM25 ---")
    test_bm25()
    print("--- tokeniser ---")
    test_tokeniser()
    print("--- command extraction ---")
    test_cmd_extraction()
    print("--- concept promotion ---")
    test_concept_promotion()
    print("--- alias ---")
    test_alias()
    print("--- fault routing ---")
    test_fault_routing()
    print("--- contract ---")
    test_contract()
    print("--- answer relevance comparison ---")
    test_answer_relevance()
    print("--- executability ---")
    test_executability()
    print("--- cache ---")
    test_cache()
    print("--- new concepts (Phase 7) ---")
    test_new_concepts()

    total = _PASS + _FAIL
    print(f"\n{total} checks: {_PASS} PASS, {_FAIL} FAIL")
    sys.exit(0 if _FAIL == 0 else 1)
