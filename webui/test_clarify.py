#!/usr/bin/env python3
"""Proof that WRATH's clarifying-questions gate works — WITHOUT an API key.

The P0 quality lever: before designing, Discovery must ask the right missing questions instead of
assuming (House Rule 7). We assert that a vague problem is held back with the architecture-critical
questions raised, and a fully-specified problem is cleared for design.

Run:  python webui/test_clarify.py     (no key, no network, deterministic)
Exit 0 = the gate holds.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clarify  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


print("=== 1. A vague problem is NOT ready for design and raises the right questions ===")
a = clarify.analyze("Design me a network.")
check("not ready for design", a["ready"] is False)
check("has blocking (architecture-critical) gaps", len(a["blocking"]) > 0)
for dim in ("deployment", "scale", "resilience", "platform"):
    check(f"flags missing '{dim}'", dim in a["blocking"])
check("every missing dimension carries a non-empty question",
      all(m["question"].strip() for m in a["missing"]))

print("=== 2. A fully-specified problem is READY for design (no blocking gaps) ===")
detailed = ("Brownfield migration of a 40-site service-provider core to SR-MPLS on Cisco IOS-XR "
            "(NCS 540, release 7.10), 99.999% availability with sub-50ms end-to-end convergence, "
            "carrying L3VPN and multicast, must meet PCI segmentation, cutover inside Q3 maintenance "
            "windows within a fixed budget.")
b = clarify.analyze(detailed)
check("ready for design", b["ready"] is True)
check("no blocking gaps remain", b["blocking"] == [])
for dim in ("deployment", "scale", "resilience", "platform", "security", "timeline", "services"):
    check(f"recognized '{dim}' as specified", dim in b["present"])

print("=== 3. Partial spec: missing SLA alone still blocks design ===")
c = clarify.analyze("Brownfield 40-site SR-MPLS core on Cisco IOS-XR carrying L3VPN.")
check("still not ready (SLA/SLO unspecified)", c["ready"] is False)
check("resilience is the/an open blocking question", "resilience" in c["blocking"])

print("=== 4. The rendered brief states the gate verdict ===")
brief = clarify.render_brief("Design me a network.", a)
check("brief marks NOT ready", "NOT ready for design" in brief)
check("brief lists the must-answer section", "Must answer before design" in brief)

print()
print("RESULT:", "ALL GREEN — the clarify-gate holds (no API key needed)." if not fails
      else f"{fails} FAILURE(S) — the gate has a hole.")
sys.exit(1 if fails else 0)
