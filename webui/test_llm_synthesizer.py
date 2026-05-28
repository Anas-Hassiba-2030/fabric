#!/usr/bin/env python3
"""Tests for Phase 4 LLM synthesiser + dense-RAG baseline (no API key required).

All checks are deterministic: the LLM SUT falls back to the deterministic OpsRAG baseline
when ANTHROPIC_API_KEY is not set, so the entire suite runs without a live Anthropic account.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(os.path.dirname(HERE))

# Ensure no API key so we exercise the fallback path only.
os.environ.pop("ANTHROPIC_API_KEY", None)

from opsrag import llm_synthesizer, dense_rag
from opsrag.dense_rag import _tokens, _BM25Index, chunk_text

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        print(f"  PASS {name}")
        _PASS += 1
    else:
        print(f"  FAIL {name}" + (f": {detail}" if detail else ""))
        _FAIL += 1


# --------------------------------------------------------------------------
# Section 1: Dense-RAG primitives
# --------------------------------------------------------------------------
print("\n=== 1. Dense-RAG primitives ===")

# tokeniser
toks = _tokens("show bgp neighbors 10.0.0.1 is this Established?")
check("tokens lowercase + strip stopwords", "show" in toks and "established" in toks and "is" not in toks)
check("tokens drop short", all(len(t) >= 3 for t in toks))

# chunker
chunks = chunk_text("A" * 1200, source="test.md")
check("chunk_text splits at _CHUNK_SIZE", len(chunks) >= 3, f"got {len(chunks)}")
check("chunk_text source tagged", all(c["source"] == "test.md" for c in chunks))
check("chunk_text overlap (step < size)", chunks[1]["offset"] < chunks[0]["offset"] + 500)

# tiny text — no crash
tiny_chunks = chunk_text("short", source="tiny.md")
check("chunk_text handles tiny text", len(tiny_chunks) >= 1)

# BM25 index basics
corpus = [
    {"text": "BGP session stuck in Active state means TCP handshake not completing", "source": "a"},
    {"text": "OSPF hello packets on the same area must match hello and dead intervals", "source": "b"},
    {"text": "BGP TCP-MD5 password mismatch causes Active state, peer rejects the session", "source": "c"},
    {"text": "MPLS label stack disposition at penultimate hop popping", "source": "d"},
]
idx = _BM25Index(corpus)
results = idx.score("BGP session Active state TCP", top_k=3)
check("BM25 returns ranked results", len(results) >= 2)
check("BM25 top result is BGP relevant", "bgp" in results[0][1]["text"].lower() or
      "active" in results[0][1]["text"].lower())
check("BM25 score descending", results[0][0] >= results[-1][0])

# Zero-result query
zero = idx.score("quantum xyzzy nonexistent", top_k=3)
check("BM25 returns empty for no-match query", len(zero) == 0)

# --------------------------------------------------------------------------
# Section 2: Dense-RAG SUT contract
# --------------------------------------------------------------------------
print("\n=== 2. Dense-RAG SUT contract ===")

q_bgp = {
    "id": "q-001",
    "category": "session-establishment",
    "difficulty": "diagnose",
    "question": "R2 shows BGP neighbor in Active state. What commands do you run first?",
    "fault_id": None,
    "ground_truth": {"answer": "...", "layer": "bgp", "commands": []},
}

resp = dense_rag.dense_rag_sut(q_bgp)
check("dense_rag_sut returns answer key", "answer" in resp)
check("dense_rag_sut returns retrieved_context key", "retrieved_context" in resp)
check("dense_rag_sut returns commands list", isinstance(resp.get("commands"), list))
check("dense_rag_sut source tagged", resp.get("_source") == "dense-rag-bm25")
check("dense_rag_sut context not empty (corpus has content)", len(resp.get("retrieved_context", "")) > 0)

# Non-BGP question still returns a valid struct
q_other = {
    "id": "q-050",
    "category": "flowspec",
    "difficulty": "recall",
    "question": "What is BGP Flowspec used for?",
    "fault_id": None,
}
resp2 = dense_rag.dense_rag_sut(q_other)
check("dense_rag_sut contract on unfamiliar category", all(k in resp2 for k in ("answer", "retrieved_context", "commands")))

# --------------------------------------------------------------------------
# Section 3: LLM synthesiser — graph retrieval (no API key)
# --------------------------------------------------------------------------
print("\n=== 3. LLM synthesiser — graph retrieval ===")

nodes = llm_synthesizer._retrieve(q_bgp, top_k=5)
check("_retrieve returns list", isinstance(nodes, list))
check("_retrieve items have required keys",
      all("type" in n and "name" in n and "content" in n for n in nodes) if nodes else True)

ctx = llm_synthesizer._format_context(nodes)
check("_format_context returns string", isinstance(ctx, str))
# Even with empty nodes the function returns a usable string
empty_ctx = llm_synthesizer._format_context([])
check("_format_context handles empty nodes", "(no typed context" in empty_ctx)

# --------------------------------------------------------------------------
# Section 4: LLM synthesiser — response parser
# --------------------------------------------------------------------------
print("\n=== 4. LLM synthesiser — response parser ===")

raw_good = """
ANSWER:
The BGP session is in Active state because the TCP handshake is not completing, typically due to
a wrong remote-AS (RFC 4271 S6) or a TCP-MD5 password mismatch (RFC 2385).

COMMANDS:
show bgp neighbors 10.0.0.1
show ip bgp summary
show log | inc BGP
"""
parsed = llm_synthesizer._parse_response(raw_good)
check("parser extracts ANSWER", len(parsed["answer"]) > 20)
check("parser extracts 3 COMMANDS", len(parsed["commands"]) == 3)
check("parser commands are dicts with cmd key", all("cmd" in c for c in parsed["commands"]))
check("parser commands device defaults to R1", all(c.get("device") == "R1" for c in parsed["commands"]))

raw_none_cmds = "ANSWER:\nBGP is fine.\n\nCOMMANDS:\nNONE"
parsed2 = llm_synthesizer._parse_response(raw_none_cmds)
check("parser handles NONE commands gracefully", parsed2["commands"] == [])

raw_config_cmd = "ANSWER:\nSomething.\n\nCOMMANDS:\nrouter bgp 65001\nshow bgp summary"
parsed3 = llm_synthesizer._parse_response(raw_config_cmd)
check("parser rejects config commands (non-show)", len(parsed3["commands"]) == 1 and
      parsed3["commands"][0]["cmd"].lower().startswith("show"))

raw_empty = ""
parsed4 = llm_synthesizer._parse_response(raw_empty)
check("parser handles empty response", parsed4["answer"] == "" and parsed4["commands"] == [])

# --------------------------------------------------------------------------
# Section 5: LLM SUT fallback path (no key → deterministic baseline)
# --------------------------------------------------------------------------
print("\n=== 5. LLM SUT fallback path (no API key) ===")

result = llm_synthesizer.llm_sut(q_bgp)
check("llm_sut returns answer key", "answer" in result)
check("llm_sut returns retrieved_context key", "retrieved_context" in result)
check("llm_sut returns commands list", isinstance(result.get("commands"), list))
check("llm_sut fallback source tagged", result.get("_source") in ("deterministic-fallback", "api-error-fallback"))

# Non-fault-linked question still returns valid struct
q_recall = {
    "id": "q-020",
    "category": "security",
    "difficulty": "recall",
    "question": "What is the purpose of TCP-MD5 authentication in BGP (RFC 2385)?",
    "fault_id": None,
}
result2 = llm_synthesizer.llm_sut(q_recall)
check("llm_sut recall question returns valid struct",
      all(k in result2 for k in ("answer", "retrieved_context", "commands")))

# --------------------------------------------------------------------------
# Section 6: Prompt builder
# --------------------------------------------------------------------------
print("\n=== 6. Prompt builder ===")

prompt = llm_synthesizer._build_prompt(q_bgp, "mock context text")
check("prompt contains SYSTEM_PROMPT header", "OpsRAG" in prompt)
check("prompt contains RETRIEVED CONTEXT", "RETRIEVED CONTEXT" in prompt)
check("prompt contains the question", q_bgp["question"] in prompt)
check("prompt contains context text", "mock context text" in prompt)
check("prompt contains CATEGORY", "session-establishment" in prompt)

# --------------------------------------------------------------------------
# Section 7: Evaluator integration — dense_rag_sut as a third SUT
# --------------------------------------------------------------------------
print("\n=== 7. Evaluator integration ===")

from opsrag import evaluator

# Score one question with dense_rag_sut
row = evaluator.score_question(q_bgp, dense_rag.dense_rag_sut(q_bgp))
check("score_question with dense_rag_sut returns id", row["id"] == "q-001")
check("score_question executability bool", isinstance(row["executability"], bool))
check("score_question score 0-1", 0.0 <= row["score"] <= 1.0)

# Score one question with llm_sut
row2 = evaluator.score_question(q_recall, llm_synthesizer.llm_sut(q_recall))
check("score_question with llm_sut returns category", row2["category"] == "security")

# Dense-RAG beats naive on executability (corpus has show commands → BM25 extracts them)
naive_r = evaluator.score_question(q_bgp, evaluator.naive_sut(q_bgp))
dense_r = evaluator.score_question(q_bgp, dense_rag.dense_rag_sut(q_bgp))
check("dense_rag executability >= naive (not zero floor)", dense_r["executability"] or not naive_r["executability"])

# --------------------------------------------------------------------------
print(f"\n{'='*40}")
print(f"RESULT: {_PASS} PASS / {_FAIL} FAIL")
if _FAIL:
    sys.exit(1)
