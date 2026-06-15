#!/usr/bin/env python3
"""Proof that model routing matches the charter tiers — no API key.

Run:  python webui/test_routing.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routing  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


print("=== 1. Heavy reasoning -> Opus ===")
for a in ("designer-hld", "critic", "migration-planner", "troubleshooter"):
    check(f"{a} -> opus", routing.tier_for(a) == "opus" and "opus" in routing.model_for(a))

print("=== 2. Routine stages -> Sonnet; Librarian -> Haiku ===")
for a in ("discovery", "config-engineer", "bom-commercials", "exec-storyteller"):
    check(f"{a} -> sonnet", routing.tier_for(a) == "sonnet")
check("librarian -> haiku", routing.tier_for("librarian") == "haiku")

print("=== 3. Model ids are the real identifiers ===")
check("opus id", routing.model_for("critic") == "claude-opus-4-7")
check("sonnet id", routing.model_for("discovery") == "claude-sonnet-4-6")
check("haiku id", routing.model_for("librarian") == "claude-haiku-4-5-20251001")

print("=== 4. Explicit override wins (single-model mode) ===")
check("override forces one model", routing.model_for("critic", "claude-sonnet-4-6") == "claude-sonnet-4-6")
check("unknown agent -> sonnet default", routing.tier_for("mystery") == "sonnet")

print("=== 5. Pretty names ===")
check("pretty opus", routing.pretty("opus") == "Opus 4.7")
check("pretty haiku", routing.pretty("haiku") == "Haiku 4.5")

print()
print("RESULT:", "ALL GREEN — routing matches the charter tiers." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
