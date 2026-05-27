#!/usr/bin/env python3
"""WRATH compliance pack — map the design to PCI/HIPAA/NIST/CIS control areas (Phase 4).

A standalone report that maps the solution to each relevant framework's control areas and what in the
design addresses them. Honest by construction: it claims *design-level* coverage and explicitly says
formal attestation needs audit evidence (House Rule 7) — it never declares "certified". The framework
control areas referenced are real and well-known (no invented standards — House Rule 4).

Pure + deterministic — see webui/test_compliance.py.

    detect(problem) -> [framework keys]
    report(problem) -> markdown
"""
import sys

# Real, well-known control areas per framework, mapped to the design measures WRATH produces.
FRAMEWORKS = {
    "PCI": {"name": "PCI DSS", "rows": [
        ("Req 1 — Network segmentation & firewalls", "Security zones / segmentation in the HLD & LLD"),
        ("Req 2 — No vendor defaults / hardening", "Control- & mgmt-plane hardening; no default SNMP communities (Validator blocks)"),
        ("Req 4 — Encrypt transmission of CHD", "MACsec / IPsec on the required paths"),
        ("Req 10 — Log & monitor access", "Model-driven telemetry + syslog in the assurance design"),
        ("Req 11 — Regularly test security", "Adversarial Validator gate + standards audit on every config"),
    ]},
    "HIPAA": {"name": "HIPAA Security Rule", "rows": [
        ("§164.312(a) — Access control", "Segmentation + AAA/802.1X"),
        ("§164.312(e) — Transmission security", "Encryption (IPsec/MACsec) where ePHI traverses"),
        ("§164.312(b) — Audit controls", "Telemetry/logging catalog"),
        ("§164.312(c) — Integrity", "Control-plane protection (CoPP/LPTS)"),
    ]},
    "NIST": {"name": "NIST CSF", "rows": [
        ("Identify", "Asset/topology inventory (read-only network-state)"),
        ("Protect", "Segmentation, hardening, encryption — security designed in (House Rule 5)"),
        ("Detect", "Model-driven telemetry + SLO catalog"),
        ("Respond", "RCA playbook + runbooks"),
        ("Recover", "Per-step rollback + phased migration plan (House Rule 3)"),
    ]},
    "CIS": {"name": "CIS Controls v8", "rows": [
        ("CIS 4 — Secure configuration", "Hardening; no defaults (Validator-enforced)"),
        ("CIS 8 — Audit log management", "Telemetry/syslog design"),
        ("CIS 12 — Network infrastructure mgmt", "Segmentation; management in its own VRF"),
        ("CIS 13 — Network monitoring & defense", "Assurance telemetry + edge protections (GTSM, max-prefix)"),
    ]},
}


def detect(problem):
    p = (problem or "").lower()
    found = [k for k in ("PCI", "HIPAA", "NIST", "CIS") if k.lower() in p]
    return found or ["NIST"]  # default baseline if no framework named


def report(problem):
    fw = detect(problem)
    L = [f"# Compliance pack — {', '.join(FRAMEWORKS[k]['name'] for k in fw)}",
         f"**Scope:** {(problem or '(unspecified)')[:160]}", "",
         "_Design-level mapping of the solution to each framework's control areas. This is not a formal "
         "attestation — sign-off requires audit evidence against the deployed estate (House Rule 7). "
         "No control number is invented (House Rule 4)._"]
    for k in fw:
        f = FRAMEWORKS[k]
        L += ["", f"## {f['name']}", "| Control area | Addressed by | Status |", "|---|---|---|"]
        for area, met in f["rows"]:
            L.append(f"| {area} | {met} | Design-addressed — confirm by audit |")
    L += ["", "_Status legend: **Design-addressed** = the design provides the control; final compliance "
          "is confirmed with configuration evidence and an audit._"]
    return "\n".join(L)


if __name__ == "__main__":
    print(report(" ".join(sys.argv[1:]) or "PCI and HIPAA segmented hospital edge"))
