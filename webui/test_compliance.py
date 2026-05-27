#!/usr/bin/env python3
"""Proof that the compliance pack maps frameworks honestly — no API key.

Run:  python webui/test_compliance.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compliance  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


print("=== 1. Detects named frameworks ===")
check("PCI+HIPAA detected", set(compliance.detect("PCI and HIPAA hospital edge")) >= {"PCI", "HIPAA"})
check("CIS detected", "CIS" in compliance.detect("harden to CIS benchmarks"))
check("none named -> NIST baseline", compliance.detect("plain SR-MPLS core") == ["NIST"])

print("=== 2. Report includes the right sections + a matrix ===")
r = compliance.report("Brownfield core with PCI segmentation and NIST baseline")
check("has PCI DSS section", "## PCI DSS" in r)
check("has NIST CSF section", "## NIST CSF" in r)
check("renders a control matrix", "| Control area | Addressed by | Status |" in r)
check("maps segmentation to a control", "egment" in r)

print("=== 3. Honest: design-level, not a certification claim ===")
check("explicitly not a formal attestation", "not a formal" in r.lower())
check("requires audit evidence", "audit" in r.lower())
check("never claims 'certified'", "certified" not in r.lower())
check("status is 'Design-addressed', not 'compliant'", "Design-addressed" in r and "fully compliant" not in r.lower())

print("=== 4. Deterministic ===")
check("same problem -> identical report", compliance.report("PCI core") == compliance.report("PCI core"))

print()
print("RESULT:", "ALL GREEN — compliance pack maps honestly." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
