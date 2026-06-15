#!/usr/bin/env python3
"""WRATH continuous assurance — telemetry/SLO catalog + drift check (★ signature).

Two halves of "operate what you designed": (1) generate the model-driven telemetry / SLO catalog from
the design — KPIs → SLI → gNMI/OpenConfig sensor → threshold → action; (2) re-validate the read-only
network state against design intent and flag drift. Closed-loop actions are alert/ticket only — WRATH
never auto-pushes to a device (House Rule 6). Pure + deterministic — see webui/test_assurance.py.

    slo_catalog(problem) -> [ {kpi, sensor, threshold, action} ]
    drift_check(state)   -> {checks, drift, ok}
    render(problem, state=None) -> markdown
"""
import sys

_OC = "/interfaces/interface/state"  # OpenConfig interface state root


def slo_catalog(problem):
    p = (problem or "").lower()
    rows = [
        {"kpi": "Reachability / availability", "sensor": f"{_OC}/oper-status",
         "threshold": "oper-status = UP", "action": "alert + ticket on down"},
        {"kpi": "Interface health (errors/discards)", "sensor": f"{_OC}/counters/in-errors",
         "threshold": "error rate < 0.01%", "action": "alert"},
        {"kpi": "Link utilization / capacity", "sensor": f"{_OC}/counters/out-octets",
         "threshold": "< 70% sustained", "action": "capacity review"},
    ]
    if any(k in p for k in ["sla", "slo", "convergence", "99.", "sub-", "availab", "uptime"]):
        rows.append({"kpi": "Convergence under failure", "sensor": "synthetic probe + IS-IS/TI-LFA event counters",
                     "threshold": "≤ design target (state HW dependency)", "action": "alert + record"})
    if any(k in p for k in ["l3vpn", "vpn", "mpls", "bgp", "sr-mpls"]):
        rows.append({"kpi": "BGP session health", "sensor": ".../bgp/neighbors/neighbor/state/session-state",
                     "threshold": "ESTABLISHED", "action": "page on flap/down"})
        rows.append({"kpi": "VPNv4/v6 prefix count", "sensor": ".../afi-safis/afi-safi/state/prefixes/received",
                     "threshold": "within expected band", "action": "alert on sudden drop"})
    if any(k in p for k in ["evpn", "vxlan", "dci"]):
        rows.append({"kpi": "EVPN MAC / IMET routes", "sensor": ".../l2vpn-evpn state",
                     "threshold": "stable per design", "action": "alert on churn"})
    if any(k in p for k in ["security", "pci", "hipaa", "nist", "cis", "segment", "control-plane"]):
        rows.append({"kpi": "Control-plane protection", "sensor": "CoPP/LPTS drop counters",
                     "threshold": "drops within policy", "action": "alert on anomaly"})
    return rows


def drift_check(state):
    """Compare a read-only state snapshot against design intent. Returns checks + drift/ok counts."""
    checks = []
    for dev, d in (state.get("devices", {}) or {}).items():
        for nb in d.get("bgp_neighbors", []):
            ok = nb.get("state") == "Established"
            checks.append({"check": f"BGP {dev} → {nb.get('neighbor')} ({nb.get('afi')})",
                           "expected": "Established", "observed": nb.get("state", "?"),
                           "status": "ok" if ok else "drift"})
        for itf in d.get("interfaces", []):
            desc = (itf.get("desc") or "")
            is_core = desc.startswith("to:P") or "CORE" in desc.upper() or "to:P1" in desc
            if itf.get("oper") == "down" and itf.get("name") != "Loopback0":
                checks.append({"check": f"Interface {dev} {itf['name']} ({desc})",
                               "expected": "up", "observed": "down", "status": "drift"})
            if is_core and isinstance(itf.get("mtu"), int) and itf["mtu"] < 9000:
                checks.append({"check": f"Core MTU {dev} {itf['name']}",
                               "expected": "≥ 9000 (jumbo)", "observed": str(itf["mtu"]), "status": "drift"})
    drift = sum(1 for c in checks if c["status"] == "drift")
    return {"checks": checks, "drift": drift, "ok": len(checks) - drift}


def render(problem, state=None):
    cat = slo_catalog(problem)
    L = ["## Service assurance — telemetry & SLO catalog",
         "_Model-driven telemetry (gNMI / OpenConfig). Closed-loop actions are **alert/ticket only** — "
         "WRATH never auto-pushes to a device (House Rule 6)._", "",
         "| KPI | SLI sensor (gNMI/OpenConfig) | Threshold | Action |", "|---|---|---|---|"]
    L += [f"| {r['kpi']} | `{r['sensor']}` | {r['threshold']} | {r['action']} |" for r in cat]
    if state is not None:
        dr = drift_check(state)
        L += ["", "## Drift check — live read-only state vs design intent",
              f"_Continuous assurance (House Rule 8): re-validates current state. "
              f"**{dr['ok']} checks healthy · {dr['drift']} drift.**_", "",
              "| Check | Expected | Observed | Status |", "|---|---|---|---|"]
        for c in dr["checks"]:
            mark = "✅ ok" if c["status"] == "ok" else "⚠ DRIFT"
            L.append(f"| {c['check']} | {c['expected']} | {c['observed']} | {mark} |")
        if not dr["checks"]:
            L.append("| — | — | — | no state available |")
    return "\n".join(L)


if __name__ == "__main__":
    print(render(" ".join(sys.argv[1:]) or "SR-MPLS L3VPN core, 99.999% SLA"))
