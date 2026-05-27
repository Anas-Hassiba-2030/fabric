#!/usr/bin/env python3
"""WRATH audience reframing — re-voice the exec one-pager per stakeholder (Phase 4).

The same validated solution, framed for who's in the room: the CFO hears cost/risk, the CISO hears
security/compliance, the NOC hears operability/SLA, the board hears outcome/decision. Honest by
construction — no invented currency (House Rule 4); money is framed as drivers, sourced elsewhere.

Pure + deterministic (no LLM/key) — see webui/test_audience.py.

    AUDIENCES -> ["exec","cfo","ciso","noc"]
    reframe(problem, audience) -> markdown
"""
import re
import sys

AUDIENCES = ["exec", "cfo", "ciso", "noc"]
LABEL = {"exec": "Board / Executive", "cfo": "CFO", "ciso": "CISO", "noc": "NOC / Operations"}


def _signals(problem):
    p = (problem or "").lower()
    return {
        "security": any(k in p for k in ["pci", "hipaa", "nist", "cis", "security", "segment",
                                         "encrypt", "macsec", "ipsec", "zero trust", "zero-trust",
                                         "firewall", "ddos"]),
        "compliance": [c.upper() for c in ("pci", "hipaa", "nist", "cis") if c in p],
        "sla": bool(re.search(r"99\.|\bsla\b|\bslo\b|convergence|sub-?\d+\s*ms|sub-second|availab|uptime", p)),
        "brownfield": any(k in p for k in ["brownfield", "migrat", "existing", "cutover", "upgrade"]),
    }


def reframe(problem, audience):
    a = (audience or "exec").lower()
    if a not in AUDIENCES:
        a = "exec"
    s = _signals(problem)
    L = [f"## Exec one-pager — for the {LABEL[a]}",
         "_Same validated solution, re-voiced for this audience; technology in support of the outcome._", ""]

    if a == "cfo":
        L += ["**Why this matters (money & risk):** today's design carries cost and exposure; this "
              "converts it into a predictable, defensible spend tied to a business outcome.",
              "", "- **Spend shape:** capex (hardware/optics/licenses) vs recurring opex (support, "
              "power, renewals) — every line traces to a design need; figures come from the BoM and a "
              "vendor quote, not guesses (House Rule 4).",
              "- **Risk avoided:** the cost of *not* acting — outage exposure and audit risk — framed "
              "with your figures, not invented ones.",
              "- **Phasing:** staged rollout spreads spend and de-risks each tranche.",
              "- **The ask:** approve the budget envelope and proceed to a firm quote."]
    elif a == "ciso":
        comp = (", ".join(s["compliance"]) if s["compliance"] else "the customer baseline (NIST/CIS)")
        L += [f"**Why this matters (risk posture & compliance):** security is designed in from the HLD, "
              f"measured against {comp}.",
              "", "- **Segmentation & blast radius:** failure/breach domains are bounded by design, not "
              "bolted on (House Rule 5).",
              "- **Control- & management-plane hardening:** CoPP/LPTS, mgmt in its own VRF, edge "
              "protections (GTSM, max-prefix).",
              "- **Encryption where required:** MACsec/IPsec per the data-classification need.",
              f"- **Auditability:** a requirement→standard→evidence compliance matrix, every citation "
              "verified — no invented standards (House Rule 4)." + (f" Covers {comp}." if s["compliance"] else ""),
              "- **The ask:** sign off on the security posture and required controls."]
    elif a == "noc":
        L += ["**Why this matters (operability & resilience):** the design is built to run and to be "
              "measured, not just to pass review.",
              "", "- **Resilience target:** convergence/availability met under each *modeled* failure "
              "(TI-LFA/FRR) — with the hardware dependency stated, not assumed.",
              "- **Observability:** model-driven telemetry → an SLI→SLO→threshold→action catalog so "
              "you see drift before customers do.",
              "- **Change safety:** " + ("a per-step rollback at every cutover stage with go/no-go gates "
              "(House Rule 3)." if s["brownfield"] else "objective go/no-go gates and reversible changes."),
              "- **MTTR:** runbooks and the RCA playbook shorten time-to-resolution.",
              "- **The ask:** confirm operational readiness, change windows, and staffing."]
    else:
        L += ["**Why this matters:** today this carries cost and risk; the design turns it into a "
              "measurable business outcome. The decision now is to approve and proceed.",
              "", "- **Outcome-led:** the capability the business gains, with technology in support.",
              "- **De-risked:** validated design, security designed in, a rollback where it touches "
              "production.",
              "- **The ask:** approve the solution and move to delivery."]
    return "\n".join(L)


if __name__ == "__main__":
    prob = " ".join(sys.argv[2:]) or "Brownfield SR-MPLS core, 99.999% SLA, PCI segmentation"
    print(reframe(prob, sys.argv[1] if len(sys.argv) > 1 else "cfo"))
