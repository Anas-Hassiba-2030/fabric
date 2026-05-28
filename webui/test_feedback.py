#!/usr/bin/env python3
"""Tests for Phase 5 — dual-signal feedback loop (no API key required).

All tests are deterministic: the query streams use fixed RNG seeds, the SUT is
the deterministic opsrag_sut, and the oracle results are simulated via the stream generators.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(os.path.dirname(HERE))

os.environ.pop("ANTHROPIC_API_KEY", None)

from opsrag import feedback
from opsrag.feedback import (
    record_interaction,
    execution_gated_admit,
    user_gated_admit,
    run_longitudinal_study,
    ablation,
    uniform_stream,
    popularity_bias_stream,
    format_ablation_table,
    InteractionRecord,
)
from opsrag.schema import Graph
from opsrag.evaluator import opsrag_sut, naive_sut

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


# Minimal benchmark subset for fast tests (3 questions: 1 fault-linked, 2 non-fault)
_FAULT_Q = {
    "id": "q-001",
    "category": "session-establishment",
    "difficulty": "diagnose",
    "fault_id": "f-bgp-wrong-remote-as",
    "question": "R2 shows BGP neighbor in Active state. What is the most likely cause?",
    "ground_truth": {"answer": "wrong remote AS", "layer": "bgp", "commands": [], "executable": False},
}
_RECALL_Q = {
    "id": "q-020",
    "category": "security",
    "difficulty": "recall",
    "fault_id": None,
    "question": "What is TCP-MD5 used for in BGP?",
    "ground_truth": {"answer": "authentication", "layer": "bgp", "commands": [], "executable": False},
}
_APPLY_Q = {
    "id": "q-050",
    "category": "communities",
    "difficulty": "apply",
    "fault_id": None,
    "question": "How do BGP communities limit route propagation?",
    "ground_truth": {"answer": "tag routes for policy", "layer": "bgp", "commands": [], "executable": False},
}
_QUESTIONS = [_FAULT_Q, _RECALL_Q, _APPLY_Q]

# --------------------------------------------------------------------------
# Section 1: InteractionRecord creation
# --------------------------------------------------------------------------
print("\n=== 1. InteractionRecord creation ===")

sut_resp = opsrag_sut(_RECALL_Q)
oracle_r = {"executable": True, "diagnosis_correct": None}
rec = record_interaction(_RECALL_Q, sut_resp, oracle_r, user_accepted=True, sut_name="opsrag")

check("record has interaction_id", rec.interaction_id.startswith("i-"))
check("record has question_id", rec.question_id == "q-020")
check("record has category", rec.category == "security")
check("record oracle_correct is None (non-fault q)", rec.oracle_correct is None)
check("record oracle_executable bool", isinstance(rec.oracle_executable, bool))
check("record user_accepted=True", rec.user_accepted is True)
check("record.to_dict() has all keys",
      all(k in rec.to_dict() for k in ("interaction_id", "question_id", "oracle_correct", "user_accepted")))

# Fault-linked record
sut_resp2 = opsrag_sut(_FAULT_Q)
oracle_r2 = {"executable": True, "diagnosis_correct": True}
rec2 = record_interaction(_FAULT_Q, sut_resp2, oracle_r2, user_accepted=True, sut_name="opsrag")
check("fault-linked record oracle_correct=True", rec2.oracle_correct is True)

oracle_r3 = {"executable": False, "diagnosis_correct": False}
rec3 = record_interaction(_FAULT_Q, sut_resp2, oracle_r3, user_accepted=True, sut_name="opsrag")
check("fault-linked record oracle_correct=False", rec3.oracle_correct is False)

# --------------------------------------------------------------------------
# Section 2: Execution-gated admission
# --------------------------------------------------------------------------
print("\n=== 2. Execution-gated admission ===")

g1 = Graph()
check("admit correct oracle → returns True", execution_gated_admit(g1, rec2) is True)
check("admitted node in graph", len(g1.nodes) == 1)
check("admitted node type=Runbook", list(g1.nodes.values())[0].type == "Runbook")
check("admitted node authored=False (machine-learned)", not list(g1.nodes.values())[0].provenance.authored)
check("admitted node admitted_by=execution-gated",
      list(g1.nodes.values())[0].attrs.get("admitted_by") == "execution-gated")

# Idempotent: re-admitting same record → no new node
old_size = len(g1.nodes)
result = execution_gated_admit(g1, rec2)
check("re-admitting same record is idempotent (no duplicate)", len(g1.nodes) == old_size)

# Incorrect oracle → NOT admitted
g2 = Graph()
check("incorrect oracle → NOT admitted", execution_gated_admit(g2, rec3) is False)
check("no node added for incorrect oracle", len(g2.nodes) == 0)

# oracle_correct=None (non-fault question) → NOT admitted
g3 = Graph()
check("None oracle → NOT admitted (non-fault q)", execution_gated_admit(g3, rec) is False)
check("no node for None-oracle", len(g3.nodes) == 0)

# --------------------------------------------------------------------------
# Section 3: User-gated admission
# --------------------------------------------------------------------------
print("\n=== 3. User-gated admission ===")

g4 = Graph()
# User accepted even though oracle says incorrect
check("user-accepted incorrect admitted by user-gated", user_gated_admit(g4, rec3) is True)
check("node admitted_by=user-gated", list(g4.nodes.values())[0].attrs.get("admitted_by") == "user-gated")

# User rejected → not admitted
rec_rejected = record_interaction(_RECALL_Q, sut_resp, oracle_r, user_accepted=False)
g5 = Graph()
check("user-rejected → NOT admitted", user_gated_admit(g5, rec_rejected) is False)
check("no node for rejected interaction", len(g5.nodes) == 0)

# Key distinction: user-gated admits wrong answers; execution-gated does not
g6a = Graph(); g6b = Graph()
execution_gated_admit(g6a, rec3)  # oracle=False → not admitted
user_gated_admit(g6b, rec3)       # user accepted incorrect → admitted
check("exec-gated rejects wrong answer; user-gated accepts it",
      len(g6a.nodes) == 0 and len(g6b.nodes) == 1)

# --------------------------------------------------------------------------
# Section 4: Coherence + retrieval accuracy measurement
# --------------------------------------------------------------------------
print("\n=== 4. Graph coherence measurement ===")

from opsrag.feedback import _measure_graph_coherence, _measure_retrieval_accuracy

# Graph with one execution-gated node and one user-gated (wrong) node
g7 = Graph()
execution_gated_admit(g7, rec2)   # correct → exec-gated
user_gated_admit(g7, rec3)        # wrong user-accepted → user-gated

coh = _measure_graph_coherence(g7)
check("coherence 0.5 for 1/2 correct nodes (exec-gated)", abs(coh - 0.5) < 0.01, f"got {coh}")

# Pure exec-gated graph → coherence=1.0
g8 = Graph()
execution_gated_admit(g8, rec2)
check("pure exec-gated graph coherence=1.0", _measure_graph_coherence(g8) == 1.0)

# Empty graph → coherence=1.0 (no machine nodes = no incoherence)
check("empty graph coherence=1.0", _measure_graph_coherence(Graph()) == 1.0)

# Retrieval accuracy: category-match proxy
g9 = Graph()
execution_gated_admit(g9, rec2)  # category=session-establishment
ra = _measure_retrieval_accuracy(g9, [_FAULT_Q])  # category=session-establishment
check("retrieval accuracy = 1.0 for category match", ra == 1.0, f"got {ra}")
ra0 = _measure_retrieval_accuracy(g9, [_RECALL_Q])  # category=security (not in graph)
check("retrieval accuracy = 0.0 for category miss", ra0 == 0.0, f"got {ra0}")

# --------------------------------------------------------------------------
# Section 5: Longitudinal study (small scale, fast)
# --------------------------------------------------------------------------
print("\n=== 5. Longitudinal study harness ===")

# 50-interaction stream (10-step snapshots for speed)
stream50 = uniform_stream(_QUESTIONS, opsrag_sut, n=50, rng_seed=42)
check("uniform_stream generates N tuples", len(stream50) == 50)
check("each tuple has 4 elements", all(len(t) == 4 for t in stream50))
check("questions are dicts", all(isinstance(t[0], dict) for t in stream50))
check("oracle_result is dict or None", all(t[2] is None or isinstance(t[2], dict) for t in stream50))

result50 = run_longitudinal_study(stream50, execution_gated_admit, step=10)
check("result has snapshots", "snapshots" in result50 and len(result50["snapshots"]) >= 1)
check("result has final_graph_size", "final_graph_size" in result50)
check("result has final_coherence 0–1", 0.0 <= result50["final_coherence"] <= 1.0)
check("result has admitted count", result50["admitted"] >= 0)
check("result admitted + rejected = 50", result50["admitted"] + result50["rejected"] == 50)

# Each snapshot has required keys
if result50["snapshots"]:
    snap = result50["snapshots"][0]
    check("snapshot has step", "step" in snap)
    check("snapshot has coherence", "coherence" in snap)
    check("snapshot has graph_size", "graph_size" in snap)

# Execution-gated should have coherence >= user-gated on uniform stream
result50_user = run_longitudinal_study(stream50, user_gated_admit, step=10)
check("exec-gated coherence >= user-gated (uniform stream)",
      result50["final_coherence"] >= result50_user["final_coherence"],
      f"exec={result50['final_coherence']}, user={result50_user['final_coherence']}")

# --------------------------------------------------------------------------
# Section 6: Ablation — popularity bias (the key thesis claim)
# --------------------------------------------------------------------------
print("\n=== 6. Ablation — popularity bias claim ===")

# 200-interaction popularity-biased stream: popular question often wrong but accepted
bias_stream = popularity_bias_stream(
    _QUESTIONS, opsrag_sut, n=200,
    popular_fraction=0.50,
    popular_wrong_rate=0.70,   # 70% of popular interactions have wrong answer
    popular_accept_rate=0.90,  # users accept 90% of the time anyway
    other_oracle_hit_rate=0.85,
    rng_seed=99,
)
check("bias_stream generates 200 tuples", len(bias_stream) == 200)

ab = ablation(bias_stream, step=50)
check("ablation has execution_gated key", "execution_gated" in ab)
check("ablation has user_gated key", "user_gated" in ab)
check("ablation has delta key", "delta" in ab)
check("ablation has verdict", ab["verdict"] in ("execution-gated dominates", "user-gated dominates", "tie"))

exec_coh = ab["execution_gated"]["final_coherence"]
user_coh = ab["user_gated"]["final_coherence"]
check("THESIS CLAIM: exec-gated coherence > user-gated under popularity bias",
      exec_coh > user_coh,
      f"exec={exec_coh:.3f}, user={user_coh:.3f}")

check("exec-gated verdict dominates (as expected)", ab["verdict"] == "execution-gated dominates")

# --------------------------------------------------------------------------
# Section 7: Format ablation table
# --------------------------------------------------------------------------
print("\n=== 7. Ablation table formatting ===")

tbl = format_ablation_table(ab)
check("table is a string", isinstance(tbl, str))
check("table contains coherence row", "coherence" in tbl.lower())
check("table contains verdict row", "Verdict" in tbl)
check("table contains delta column", "Delta" in tbl or "delta" in tbl.lower())
print()
print(tbl)

# --------------------------------------------------------------------------
print(f"\n{'='*40}")
print(f"RESULT: {_PASS} PASS / {_FAIL} FAIL")
if _FAIL:
    sys.exit(1)
