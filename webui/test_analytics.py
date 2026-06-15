#!/usr/bin/env python3
"""Proof that WRATH cross-run analytics aggregate faithfully — no API key.

Run:  python webui/test_analytics.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analytics  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


def rec(mode, conf, counts, problem, stages=3):
    return {"mode": mode, "problem": problem, "stages": [{"id": f"s{i}"} for i in range(stages)],
            "trust": {"confidence": conf, "counts": counts}}


recs = [
    rec("demo", "Medium", {"verified": 2, "flagged": 1, "blocked": 1, "config_pass": 1, "config_fail": 0}, "SR-MPLS L3VPN core"),
    rec("live", "High", {"verified": 3, "flagged": 0, "blocked": 0, "config_pass": 1, "config_fail": 0}, "EVPN VXLAN data center fabric"),
    rec("demo", "Guarded", {"verified": 1, "flagged": 2, "blocked": 1, "config_pass": 0, "config_fail": 1}, "SR-MPLS migration brownfield"),
]
s = analytics.summarize(recs)

print("=== 1. Run + mode counts ===")
check("3 runs", s["runs"] == 3)
check("2 demo, 1 live", s["by_mode"].get("demo") == 2 and s["by_mode"].get("live") == 1)

print("=== 2. Trust distribution ===")
check("High=1, Medium=1, Guarded=1", s["trust"] == {"High": 1, "Medium": 1, "Guarded": 1})

print("=== 3. Grounding + config-gate totals summed ===")
check("verified=6", s["grounding_totals"]["verified"] == 6)
check("flagged=3", s["grounding_totals"]["flagged"] == 3)
check("blocked=2 (hallucinations caught across runs)", s["grounding_totals"]["blocked"] == 2)
check("config gate 2 pass / 1 fail", s["config_gate"] == {"pass": 2, "fail": 1})

print("=== 4. Top technologies extracted ===")
tags = dict(s["top_tags"])
check("sr-mpls appears twice", tags.get("sr-mpls") == 2)
check("evpn appears once", tags.get("evpn") == 1)
check("avg stages = 3.0", s["avg_stages"] == 3.0)

print("=== 5. Empty input is safe ===")
e = analytics.summarize([])
check("0 runs, avg 0", e["runs"] == 0 and e["avg_stages"] == 0)

print()
print("RESULT:", "ALL GREEN — analytics aggregate faithfully." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
