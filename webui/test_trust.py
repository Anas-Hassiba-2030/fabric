#!/usr/bin/env python3
"""Proof that WRATH's trust report aggregates honestly — WITHOUT an API key.

The run's closing scorecard must reflect exactly what the grounding gate found: count grounded
claims, surface flagged items into a verify-before-ship ledger, count blocked hallucinations, and
never claim more confidence than the evidence supports (House Rule 7).

Run:  python webui/test_trust.py     (no key, deterministic)
Exit 0 = the report is faithful.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trust  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


print("=== 1. A clean run (all grounded) -> High confidence ===")
clean = {"hld": {"status": "grounded",
                 "checks": [{"kind": "citation", "item": "RFC 4364", "verdict": "verified", "note": "L3VPN"}]}}
r = trust.report(clean)
check("confidence High", r["confidence"] == "High")
check("1 grounded citation counted", r["counts"]["verified"] == 1)
check("empty verify ledger", r["ledger"] == [])

print("=== 2. Flagged numbers/SKUs -> Medium + verify-before-ship ledger ===")
flagged = {"bom": {"status": "flagged",
                   "checks": [{"kind": "sku", "item": "NCS-540", "verdict": "flag", "note": "confirm not EoL"},
                              {"kind": "price", "item": "$1,200", "verdict": "flag", "note": "needs a quote"}]}}
r = trust.report(flagged)
check("confidence Medium", r["confidence"] == "Medium")
ledger_items = {l["item"] for l in r["ledger"]}
check("SKU in the verify ledger", "NCS-540" in ledger_items)
check("price in the verify ledger", "$1,200" in ledger_items)
check("every ledger entry has an action", all(l["action"] for l in r["ledger"]))

print("=== 3. A blocked stage -> Guarded, hallucination counted ===")
blocked = {"lld": {"status": "blocked",
                   "checks": [{"kind": "citation", "item": "RFC 9999", "verdict": "BLOCKED", "note": "fabricated"}]}}
r = trust.report(blocked)
check("confidence Guarded", r["confidence"] == "Guarded")
check("blocked claim counted", r["counts"]["blocked"] == 1)
check("blocked item is in the ledger as excluded",
      any(l["item"] == "RFC 9999" and "excluded" in l["action"] for l in r["ledger"]))

print("=== 4. Assumptions in play force at least Medium and are surfaced ===")
r = trust.report(clean, assumptions=["Scale not specified — assumed 40 sites"])
check("assumptions downgrade High -> Medium", r["confidence"] == "Medium")
check("assumption text carried through", r["assumptions"] == ["Scale not specified — assumed 40 sites"])
check("render shows the assumptions section", "Assumptions in play" in trust.render(r))

print("=== 5. Headline summarizes grounded / verify / blocked ===")
mixed = {**clean, **flagged, **blocked}
r = trust.report(mixed)
check("headline mentions grounded, verify, blocked", all(w in r["headline"] for w in ("grounded", "verify", "blocked")))

print()
print("RESULT:", "ALL GREEN — the trust report is faithful to the evidence." if not fails
      else f"{fails} FAILURE(S) — the report misrepresents the run.")
sys.exit(1 if fails else 0)
