#!/usr/bin/env python3
"""Proof: OpsRAG benchmark evaluator (RAGAs-shape + action-grounded metrics).

Runs both reference SUTs (`naive` floor, `opsrag` synthesiser) over the seeded benchmark and
asserts that:
  - the harness produces every required metric column (RAGAs-shape + executability + diagnostic
    accuracy);
  - the OpsRAG SUT beats the naive floor on fault-linked executable questions;
  - per-category and per-difficulty buckets are present and total to n.

Run:  python webui/test_evaluator.py   (no key, no Docker, deterministic)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opsrag import evaluator  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH = os.path.join(REPO, "thesis", "benchmark")
fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


print("=== 1. Token primitives behave as expected (deterministic similarity) ===")
check("tokeniser drops stopwords + short tokens",
      "bgp" in evaluator._tokenise("BGP is a session protocol") and
      "is" not in evaluator._tokenise("BGP is a session protocol"))
check("jaccard of identical sets = 1.0",
      evaluator._jaccard(["bgp", "session"], ["bgp", "session"]) == 1.0)
check("jaccard of disjoint = 0.0",
      evaluator._jaccard(["bgp"], ["ospf"]) == 0.0)
check("recall is directional (reference in candidate)",
      evaluator._recall(["bgp"], ["bgp", "session"]) == 1.0 and
      evaluator._recall(["bgp", "session"], ["bgp"]) == 0.5)

print("=== 2. Per-metric scoring computes RAGAs-shape values ===")
sut = {"answer": "remote-as mismatch session active",
       "retrieved_context": "show bgp summary remote-as 65999 configured peer actual AS 65010",
       "commands": [{"device": "R2", "cmd": "show bgp summary"}]}
gt = {"answer": "remote-as mismatch on R2 toward R3 configured wrong peer is 65010"}
ar = evaluator.answer_relevance(sut["answer"], gt["answer"])
fa = evaluator.faithfulness(sut["answer"], sut["retrieved_context"])
cr = evaluator.context_relevance(sut["retrieved_context"], "remote-as wrong on R2 toward R3")
check("answer_relevance returns a 0-1 score", 0.0 < ar <= 1.0)
check("faithfulness returns a 0-1 score", 0.0 < fa <= 1.0)
check("context_relevance returns a 0-1 score", 0.0 < cr <= 1.0)

print("=== 3. Executability rejects bogus commands, accepts real show commands ===")
check("real show commands pass executability",
      evaluator.executability([{"device": "R2", "cmd": "show bgp summary"},
                                {"device": "R2", "cmd": "show ip bgp neighbors 192.0.2.2"}]))
check("empty command list fails executability",
      not evaluator.executability([]))
check("config command (no show prefix) is NOT counted as executable",
      not evaluator.executability([{"device": "R2", "cmd": "router bgp 65001"}]))
check("garbage command fails executability",
      not evaluator.executability([{"device": "R2", "cmd": "this is not a real cli"}]))

print("=== 4. Whole-benchmark sweep with reference SUTs ===")
naive_report = evaluator.evaluate(evaluator.naive_sut, BENCH)
opsrag_report = evaluator.evaluate(evaluator.opsrag_sut, BENCH)
check("benchmark contains >= 30 questions", naive_report["n"] >= 30)
check("headline metrics produced", "answer_relevance" in naive_report["headline"] and
      "executability_rate" in naive_report["headline"])
check("by_category buckets total to n",
      sum(b["n"] for b in naive_report["by_category"].values()) == naive_report["n"])
check("by_difficulty buckets total to n",
      sum(b["n"] for b in naive_report["by_difficulty"].values()) == naive_report["n"])

print("=== 5. OpsRAG SUT beats the naive floor on fault-linked executable questions ===")
naive_dx = naive_report["headline"]["diagnostic_accuracy"]
opsrag_dx = opsrag_report["headline"]["diagnostic_accuracy"]
check("naive SUT has near-zero diagnostic accuracy", naive_dx is not None and naive_dx == 0.0)
check("opsrag SUT achieves perfect diagnostic accuracy on the seeded faults", opsrag_dx == 1.0)
check("opsrag executability_rate >= naive",
      opsrag_report["headline"]["executability_rate"] >= naive_report["headline"]["executability_rate"])

print("=== 6. Per-question rows carry every required column ===")
sample = opsrag_report["per_question"][0]
for col in ("id", "category", "difficulty", "answer_relevance", "executability", "score"):
    check(f"per-question row has {col!r}", col in sample)

print()
print("RESULT:", "ALL GREEN — OpsRAG benchmark evaluator works end-to-end." if not fails
      else f"{fails} FAILURE(S).")

# Print headline summary so the test output doubles as a baseline report.
print()
print("Headline (naive baseline):  ", {k: v for k, v in naive_report["headline"].items()
                                       if k in ("answer_relevance", "executability_rate", "diagnostic_accuracy")})
print("Headline (opsrag baseline):", {k: v for k, v in opsrag_report["headline"].items()
                                      if k in ("answer_relevance", "executability_rate", "diagnostic_accuracy")})

sys.exit(1 if fails else 0)
