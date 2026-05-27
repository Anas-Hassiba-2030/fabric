#!/usr/bin/env python3
"""Proof that RCA isolates a real fault chain from read-only state — no API key.

Run:  python webui/test_rca.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rca  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1

# Fault chain: the eBGP neighbor 192.0.2.2 sits in 192.0.2.0/30, whose interface is DOWN.
faulty = {"devices": {"PE1": {
    "interfaces": [{"name": "Gi0/0/0/0", "ip": "10.0.0.0/31", "oper": "up", "desc": "to:P1"},
                   {"name": "Gi0/0/0/1", "ip": "192.0.2.1/30", "oper": "down", "desc": "to:CustA-CE"}],
    "bgp_neighbors": [{"neighbor": "10.255.0.254", "afi": "vpnv4", "state": "Established", "prefixes": 1420},
                      {"neighbor": "192.0.2.2", "afi": "ipv4", "state": "Idle", "prefixes": 0}]}}}

print("=== 1. Isolates the causal chain (down link -> BGP can't form) ===")
a = rca.analyze("CustA lost connectivity, BGP down", faulty)
check("root cause names the down interface as the cause", "Gi0/0/0/1" in a["root_cause"] and "down" in a["root_cause"].lower())
check("root cause links it to the Idle BGP session", "192.0.2.2" in a["root_cause"] and "Idle" in a["root_cause"])
check("physical layer confirmed", any(h["layer"].startswith("Physical") and h["verdict"] == "confirmed" for h in a["hypotheses"]))
check("BGP layer confirmed", any("BGP" in h["layer"] and h["verdict"] == "confirmed" for h in a["hypotheses"]))

print("=== 2. Fix respects House Rule 6 (human confirms the irreversible) + a verify step ===")
check("fix exists and defers the push to Kamal", a["fix"] and "House Rule 6" in a["fix"])
check("verify step checks Established + prefixes", a["verify"] and "Established" in a["verify"])

print("=== 3. Does NOT wrongly correlate when the neighbor isn't in the down subnet ===")
other = {"devices": {"PE1": {
    "interfaces": [{"name": "Gi0/0/0/1", "ip": "10.9.9.1/30", "oper": "down", "desc": "to:X"}],
    "bgp_neighbors": [{"neighbor": "192.0.2.2", "afi": "ipv4", "state": "Idle", "prefixes": 0}]}}}
a2 = rca.analyze("bgp down", other)
check("no false causal chain when subnets don't match", "because its next-hop" not in a2["root_cause"])

print("=== 4. Healthy state -> honest 'no fault visible' (House Rule 7) ===")
clean = {"devices": {"P1": {"interfaces": [{"name": "Gi0", "ip": "10.0.0.0/31", "oper": "up", "desc": "to:P2"}],
                            "bgp_neighbors": [{"neighbor": "10.0.0.1", "afi": "vpnv4", "state": "Established", "prefixes": 10}]}}}
a3 = rca.analyze("slow", clean)
check("no fault -> says so, asks for more evidence", "No fault visible" in a3["root_cause"])
check("no fix proposed when nothing is wrong", a3["fix"] is None)

print("=== 5. Render + deterministic ===")
md = rca.render("CustA down", faulty)
check("render has the hypothesis tree + root cause", "hypothesis tree" in md and "Isolated root cause" in md)
check("deterministic", rca.render("x", faulty) == rca.render("x", faulty))

print()
print("RESULT:", "ALL GREEN — RCA isolates faults from evidence, honestly." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
