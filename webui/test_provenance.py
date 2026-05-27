#!/usr/bin/env python3
"""Proof that provenance labelling is honest — deterministic gates are REAL in any mode. No API key.

Run:  python webui/test_provenance.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import provenance  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


print("=== 1. Deterministic gates are REAL regardless of mode ===")
for k in ("tool-validate", "tool-standards", "tool-cost", "report"):
    check(f"{k} -> real in demo", provenance.classify(k, "demo") == "real")
    check(f"{k} -> real in live", provenance.classify(k, "live") == "real")

print("=== 2. Reasoning stages follow the mode ===")
check("llm in live -> live", provenance.classify("llm", "live") == "live")
check("llm in demo -> demo", provenance.classify("llm", "demo") == "demo")
check("gate (Critic) in live -> live", provenance.classify("gate", "live") == "live")
check("gate (Critic) in demo -> demo", provenance.classify("gate", "demo") == "demo")

print("=== 3. Labels are human and distinct ===")
labels = {provenance.label(p) for p in ("real", "live", "demo")}
check("three distinct labels", len(labels) == 3)
check("live label names Opus 4.7", "Opus 4.7" in provenance.label("live"))

print()
print("RESULT:", "ALL GREEN — provenance is honest (real gates stay real)." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
