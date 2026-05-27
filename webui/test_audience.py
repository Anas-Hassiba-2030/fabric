#!/usr/bin/env python3
"""Proof that audience reframing re-voices honestly per stakeholder — no API key.

Run:  python webui/test_audience.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audience  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


PROB = "Brownfield migration of an SR-MPLS core, 99.999% availability, PCI and HIPAA segmentation"

print("=== 1. Every audience produces a distinct, labelled one-pager ===")
outs = {a: audience.reframe(PROB, a) for a in audience.AUDIENCES}
check("4 audiences", len(audience.AUDIENCES) == 4)
check("all distinct", len(set(outs.values())) == 4)
check("CFO labelled", "for the CFO" in outs["cfo"])
check("CISO labelled", "for the CISO" in outs["ciso"])
check("NOC labelled", "for the NOC" in outs["noc"].replace("/ Operations", ""))

print("=== 2. Each speaks to its audience's concerns ===")
check("CFO talks cost/spend/budget", re.search(r"capex|opex|budget|spend|quote", outs["cfo"].lower()) is not None)
check("CISO talks security/compliance", re.search(r"segment|compliance|encryption|hardening", outs["ciso"].lower()) is not None)
check("CISO surfaces detected PCI/HIPAA", "PCI" in outs["ciso"] and "HIPAA" in outs["ciso"])
check("NOC talks SLA/convergence/telemetry/rollback", re.search(r"convergence|telemetry|rollback|mttr", outs["noc"].lower()) is not None)
check("brownfield -> NOC mentions per-step rollback", "per-step rollback" in outs["noc"])

print("=== 3. Honest: no invented currency in ANY reframing (House Rule 4) ===")
for a, md in outs.items():
    check(f"[{a}] no fabricated $", re.search(r"\$\s?\d", md) is None)

print("=== 4. Unknown audience falls back to exec; greenfield has no rollback claim ===")
check("unknown -> exec board framing", "Board / Executive" in audience.reframe(PROB, "intern"))
g = audience.reframe("Greenfield campus switching, 99.9% SLA", "noc")
check("greenfield NOC -> reversible changes (not per-step rollback)", "per-step rollback" not in g)

print("=== 5. Deterministic ===")
check("same inputs -> identical", audience.reframe(PROB, "cfo") == audience.reframe(PROB, "cfo"))

print()
print("RESULT:", "ALL GREEN — audience reframing is faithful and honest." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
