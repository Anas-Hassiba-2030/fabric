#!/usr/bin/env python3
"""Proof that continuous assurance generates an SLO catalog + honest drift check — no API key.

Run:  python webui/test_assurance.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assurance  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


print("=== 1. SLO catalog adapts to the design + uses real gNMI sensors ===")
cat = assurance.slo_catalog("SR-MPLS L3VPN core, 99.999% SLA")
kpis = " ".join(r["kpi"] for r in cat).lower()
check("always covers availability + interface health", "availability" in kpis and "interface health" in kpis)
check("L3VPN -> BGP session KPI", any("BGP session" in r["kpi"] for r in cat))
check("sensors are gNMI/OpenConfig paths", any("/interfaces/interface/state" in r["sensor"] for r in cat))
evpn = " ".join(r["kpi"] for r in assurance.slo_catalog("EVPN-VXLAN DCI")).lower()
check("EVPN problem -> EVPN KPI", "evpn" in evpn)

print("=== 2. Closed-loop is alert/ticket only — never an auto device-push (House Rule 6) ===")
actions = " ".join(r["action"] for r in assurance.slo_catalog("secure SR-MPLS PCI core")).lower()
check("no config/push/deploy action", not any(w in actions for w in ("push", "deploy", "configure", "conf t", "commit")))

print("=== 3. Drift check flags real drift and passes clean state ===")
state = {"devices": {"PE1": {
    "bgp_neighbors": [{"neighbor": "10.0.0.1", "afi": "vpnv4", "state": "Established"},
                      {"neighbor": "192.0.2.2", "afi": "ipv4", "state": "Idle"}],
    "interfaces": [{"name": "Gi0/0/0/0", "desc": "to:P1", "oper": "up", "mtu": 9216},
                   {"name": "Gi0/0/0/1", "desc": "to:CustA-CE", "oper": "down", "mtu": 1500}]}}}
dr = assurance.drift_check(state)
check("flags the Idle BGP session", any(c["status"] == "drift" and "Idle" in c["observed"] for c in dr["checks"]))
check("flags the down interface", any(c["status"] == "drift" and c["observed"] == "down" for c in dr["checks"]))
check("drift count >= 2", dr["drift"] >= 2)
clean = {"devices": {"P1": {"bgp_neighbors": [{"neighbor": "x", "afi": "vpnv4", "state": "Established"}],
                            "interfaces": [{"name": "Gi0", "desc": "to:P2", "oper": "up", "mtu": 9216}]}}}
check("clean state -> 0 drift", assurance.drift_check(clean)["drift"] == 0)

print("=== 4. Render includes catalog + drift section; deterministic ===")
md = assurance.render("SR-MPLS L3VPN core 99.999%", state)
check("has the SLO catalog", "telemetry & SLO catalog" in md)
check("has the drift section", "Drift check" in md and "DRIFT" in md)
check("deterministic", assurance.render("x core", state) == assurance.render("x core", state))

print()
print("RESULT:", "ALL GREEN — assurance generates telemetry/SLO + honest drift." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
