#!/usr/bin/env python3
"""WRATH cost/TCO drivers + risk register, generated from the design (P1).

Honest by construction: per House Rule 4 we never invent prices, so this produces the TCO *structure*
— the capex/opex drivers and where each figure must come from (BoM, SoW, quote, customer) — plus a
qualitative risk register inferred from the design. No currency is fabricated; the BoM stage yields
SKUs (flagged until verified) and a real quote supplies the numbers.

Pure + deterministic (no LLM/key), so it is fully testable — see webui/test_tco.py.

    cost_drivers(problem) -> {"horizon": str, "capex": [...], "opex": [...]}
    risk_register(problem) -> [ {area, risk, likelihood, impact, mitigation, owner} ]
    render(problem) -> markdown
"""
import sys

_LEVELS = {"High", "Medium", "Low"}

# Capex/opex are design-driven categories, NOT amounts. "source" says where the number comes from.
CAPEX = [
    {"item": "Network hardware (chassis, line cards, RU)", "driver": "device count × platform class from the design", "source": "BoM"},
    {"item": "Optics / transceivers", "driver": "interface map (type × count per link)", "source": "BoM"},
    {"item": "Software licenses / subscriptions", "driver": "features used in the LLD → license tier", "source": "BoM"},
    {"item": "Spares", "driver": "sparing policy (typically a % of hardware)", "source": "BoM"},
    {"item": "Design & deployment services", "driver": "scope and effort", "source": "SoW"},
]
OPEX = [
    {"item": "Support / maintenance contract", "driver": "installed base × support tier, annual", "source": "quote"},
    {"item": "Power, cooling & rack", "driver": "device power draw × facility rate", "source": "customer-supplied"},
    {"item": "Software subscription renewals", "driver": "license term renewals", "source": "quote"},
    {"item": "Operations & monitoring", "driver": "telemetry/assurance tooling + run effort", "source": "customer/SoW"},
    {"item": "Training & enablement", "driver": "team size, platform delta", "source": "SoW"},
]


def cost_drivers(problem):
    return {"horizon": "3–5 year TCO horizon (confirm against the customer's refresh cycle)",
            "capex": list(CAPEX), "opex": list(OPEX)}


def risk_register(problem):
    p = (problem or "").lower()
    risks = [
        {"area": "Resilience / SLA", "risk": "Failure-mode convergence misses the SLA target",
         "likelihood": "Medium", "impact": "High",
         "mitigation": "Validate FRR/TI-LFA under each modeled failure; confirm any HW dependency (e.g. BFD-in-HW).",
         "owner": "Designer-LLD"},
    ]
    if any(k in p for k in ["brownfield", "migrat", "cutover", "existing", "upgrade", "replace"]):
        risks.append({"area": "Cutover execution", "risk": "Live cutover causes an unplanned outage",
                      "likelihood": "Medium", "impact": "High",
                      "mitigation": "Phased migration with a per-step rollback and objective go/no-go gates (House Rule 3).",
                      "owner": "Migration Planner"})
    if any(k in p for k in ["pci", "hipaa", "nist", "cis", "security", "compliance", "segmentation"]):
        risks.append({"area": "Compliance", "risk": "Design misses a required control / audit finding",
                      "likelihood": "Low", "impact": "High",
                      "mitigation": "Standards-officer compliance matrix; security designed in from the HLD (House Rule 5).",
                      "owner": "Standards Officer"})
    if any(k in p for k in ["junos", "arista", "nokia", "multivendor", "multi-vendor", "heterogeneous"]):
        risks.append({"area": "Multi-vendor interop", "risk": "Feature/encoding mismatch between vendors",
                      "likelihood": "Medium", "impact": "Medium",
                      "mitigation": "Multivendor-translator flags lossy translations; validate interop on the gateway pair.",
                      "owner": "Multivendor Translator"})
    if any(k in p for k in ["sr-mpls", "srv6", "evpn", "vxlan", "segment routing", "mpls"]):
        risks.append({"area": "Control plane", "risk": "SID/label or RD/RT collision",
                      "likelihood": "Low", "impact": "High",
                      "mitigation": "Single authoritative SRGB/label/RT plan in the LLD; no overlaps; documented.",
                      "owner": "Designer-LLD"})
    if any(k in p for k in ["scale", "growth", "1000", "large", "national", "tbps"]):
        risks.append({"area": "Capacity / scale", "risk": "Insufficient headroom for 3–5 yr growth",
                      "likelihood": "Medium", "impact": "Medium",
                      "mitigation": "Size to peak + growth headroom; separate required vs growth capacity in the BoM.",
                      "owner": "BoM & Commercials"})
    return risks


def render(problem):
    cd = cost_drivers(problem)
    lines = [f"## Cost model — TCO drivers ({cd['horizon']})",
             "_No currency figures are invented (House Rule 4); each line names where its number comes from._",
             "", "**Capex**", "| Category | Cost driver | Figure source |", "|---|---|---|"]
    lines += [f"| {c['item']} | {c['driver']} | {c['source']} |" for c in cd["capex"]]
    lines += ["", "**Opex (recurring)**", "| Category | Cost driver | Figure source |", "|---|---|---|"]
    lines += [f"| {o['item']} | {o['driver']} | {o['source']} |" for o in cd["opex"]]

    lines += ["", "## Risk register", "| # | Area | Risk | Likelihood | Impact | Mitigation | Owner |",
              "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(risk_register(problem), 1):
        lines.append(f"| {i} | {r['area']} | {r['risk']} | {r['likelihood']} | {r['impact']} | "
                     f"{r['mitigation']} | {r['owner']} |")
    lines += ["", "_TCO totals require the BoM SKUs (flagged until verified current) and a vendor quote; "
              "outage/risk cost is customer-supplied._"]
    return "\n".join(lines)


if __name__ == "__main__":
    print(render(" ".join(sys.argv[1:]) or "Brownfield SR-MPLS migration with PCI segmentation"))
