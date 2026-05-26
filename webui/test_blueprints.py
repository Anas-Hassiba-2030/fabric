#!/usr/bin/env python3
"""Proof that WRATH engagement blueprints are well-formed and design-ready — no API key.

A blueprint is a starter the user fires with one click, so it must be *complete*: it has to clear the
clarifying-questions gate (no architecture-critical gaps) or it would just bounce back asking for
scale/SLA/platform/deployment. This test enforces that invariant.

Run:  python webui/test_blueprints.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blueprints  # noqa: E402
import clarify  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


bps = blueprints.all()
print("=== 1. Catalog shape ===")
check("at least 5 blueprints", len(bps) >= 5)
check("ids are unique", len({b["id"] for b in bps}) == len(bps))
check("every blueprint has id/name/category/icon/problem",
      all(all(b.get(k) for k in ("id", "name", "category", "icon", "problem")) for b in bps))

print("=== 2. Every blueprint clears the clarify-gate (design-ready) ===")
for b in bps:
    a = clarify.analyze(b["problem"])
    check(f"[{b['id']}] ready for design (no blocking gaps: {a['blocking']})", a["ready"])

print("=== 3. get() resolves and rejects unknowns ===")
check("get('sp-core') resolves", blueprints.get("sp-core") is not None)
check("get('nope') is None", blueprints.get("nope") is None)
check("all() returns copies (mutation-safe)", (lambda x: (x[0].__setitem__("name", "X"), blueprints.all()[0]["name"] != "X")[1])(blueprints.all()))

print()
print("RESULT:", "ALL GREEN — blueprints are complete and design-ready." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
