#!/usr/bin/env python3
"""Proof that WRATH what-if compare diffs two runs faithfully — WITHOUT an API key.

Run:  python webui/test_whatif.py     (no key, deterministic)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import whatif  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


def rec(rid, problem, hld, extra=None, trust=None):
    stages = [{"id": "hld", "label": "HLD"}, {"id": "lld", "label": "LLD"}]
    deliv = {"hld": {"title": "HLD", "content": hld}, "lld": {"title": "LLD", "content": "same lld"}}
    if extra:
        stages.append({"id": extra[0], "label": extra[0]})
        deliv[extra[0]] = {"title": extra[0], "content": extra[1]}
    return {"id": rid, "problem": problem, "mode": "demo", "stages": stages,
            "deliverables": deliv, "trust": trust or {"confidence": "Medium", "counts": {"blocked": 1}}, "recall": []}


A = rec("a", "SR-MPLS core", "Transport: SR-MPLS\nRRs: 2\nSecurity: baseline")
B = rec("b", "SRv6 core", "Transport: SRv6\nRRs: 4\nSecurity: baseline",
        trust={"confidence": "High", "counts": {"blocked": 0}})

d = whatif.compare(A, B)

print("=== 1. Identical stage is 'same', differing stage is 'changed' ===")
byid = {s["id"]: s for s in d["stages"]}
check("LLD unchanged (identical content)", byid["lld"]["status"] == "same" and byid["lld"]["changed"] is False)
check("HLD changed (transport + RRs differ)", byid["hld"]["status"] == "changed" and byid["hld"]["changed"] is True)
check("HLD diff counts lines added & removed", byid["hld"]["added"] >= 1 and byid["hld"]["removed"] >= 1)
check("changed_count == 1", d["changed_count"] == 1)

print("=== 2. Stage only in one run is flagged only-a / only-b ===")
A2 = rec("a", "p", "x", extra=("config", "router bgp 65000"))
B2 = rec("b", "p", "x")
d2 = whatif.compare(A2, B2)
byid2 = {s["id"]: s for s in d2["stages"]}
check("config present only in A -> only-a", byid2["config"]["status"] == "only-a")

print("=== 3. Metrics carried for both sides (confidence + counts + recall) ===")
check("A confidence Medium, B High", d["a"]["confidence"] == "Medium" and d["b"]["confidence"] == "High")
check("blocked counts differ (1 vs 0)", d["a"]["counts"]["blocked"] == 1 and d["b"]["counts"]["blocked"] == 0)
check("problems carried", d["a"]["problem"] == "SR-MPLS core" and d["b"]["problem"] == "SRv6 core")

print("=== 4. Deterministic & symmetric-ish (same inputs -> same output) ===")
check("same inputs -> identical compare", whatif.compare(A, B) == whatif.compare(A, B))

print()
print("RESULT:", "ALL GREEN — what-if compare is faithful." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
