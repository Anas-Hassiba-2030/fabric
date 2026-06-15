#!/usr/bin/env python3
"""Proof that the Critic-intensity dial maps sensibly — no API key.

Run:  python webui/test_criticism.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import criticism  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


print("=== 1. Rounds escalate with intensity ===")
check("low -> 0 revision rounds (lenient)", criticism.plan("low")["rounds"] == 0)
check("standard -> 1 round", criticism.plan("standard")["rounds"] == 1)
check("high -> 1 round (but harsher)", criticism.plan("high")["rounds"] == 1)
check("max -> 2 rounds", criticism.plan("max")["rounds"] == 2)

print("=== 2. Labels + hints are distinct and present ===")
labels = {criticism.plan(l)["label"] for l in criticism.LEVELS}
check("4 distinct labels", len(labels) == 4)
check("every level has a non-empty hint", all(criticism.plan(l)["hint"] for l in criticism.LEVELS))
check("high hint is more adversarial than low", "harsh" in criticism.plan("high")["hint"].lower())

print("=== 3. Unknown / empty falls back to Standard ===")
check("unknown -> standard", criticism.plan("aggressive-max-ultra") == criticism.plan("standard"))
check("empty -> standard", criticism.plan("") == criticism.plan("standard"))

print()
print("RESULT:", "ALL GREEN — Critic-intensity dial maps sensibly." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
