#!/usr/bin/env python3
"""Proof that WRATH's cost/TCO + risk register stays honest — WITHOUT an API key.

The deliverable must be useful AND honest: real capex/opex drivers each naming their figure source,
a risk register inferred from the design, and — critically — NO invented currency figures
(House Rule 4). Risks adapt to the problem.

Run:  python webui/test_tco.py     (no key, deterministic)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tco  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


print("=== 1. Cost drivers are present and every line names a figure source ===")
cd = tco.cost_drivers("SR-MPLS core")
check("capex categories present", len(cd["capex"]) >= 3)
check("opex categories present", len(cd["opex"]) >= 3)
check("every capex line names a source", all(c["source"] for c in cd["capex"]))
check("every opex line names a source", all(o["source"] for o in cd["opex"]))

print("=== 2. NO invented currency (House Rule 4) ===")
text = tco.render("Brownfield SR-MPLS migration with PCI segmentation, multi-vendor, national scale")
check("no $ amount fabricated", re.search(r"\$\s?\d", text) is None)
check("explicitly says figures need BoM/quote", "quote" in text.lower() and "BoM" in text)

print("=== 3. Risk register adapts to the problem ===")
brown = tco.risk_register("Brownfield migration cutover of an SR-MPLS core with PCI")
areas = {r["area"] for r in brown}
check("brownfield -> cutover-execution risk", "Cutover execution" in areas)
check("PCI -> compliance risk", "Compliance" in areas)
check("SR-MPLS -> control-plane (SID/label) risk", "Control plane" in areas)
green = tco.risk_register("Greenfield campus switching")
check("non-brownfield -> no cutover risk", "Cutover execution" not in {r["area"] for r in green})

print("=== 4. Every risk is well-formed (qualitative levels, owner, mitigation) ===")
for r in brown:
    check(f"[{r['area']}] has High/Medium/Low likelihood & impact",
          r["likelihood"] in tco._LEVELS and r["impact"] in tco._LEVELS)
    check(f"[{r['area']}] has a mitigation and an owner", bool(r["mitigation"]) and bool(r["owner"]))

print("=== 5. Deterministic ===")
check("same problem -> identical output", tco.render("x core") == tco.render("x core"))

print()
print("RESULT:", "ALL GREEN — cost/TCO + risk register is useful and honest." if not fails
      else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
