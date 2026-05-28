#!/usr/bin/env python3
"""Tests for Phase 4 CLI grammar gate (no API key required)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(os.path.dirname(HERE))

from opsrag.grammar_gate import validate_command, validate_runbook, gate

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        print(f"  PASS {name}")
        _PASS += 1
    else:
        print(f"  FAIL {name}" + (f": {detail}" if detail else ""))
        _FAIL += 1


# --------------------------------------------------------------------------
# Section 1: Individual command validation
# --------------------------------------------------------------------------
print("\n=== 1. Individual command validation ===")

# OK commands — standard show
for cmd in [
    "show bgp summary",
    "show bgp neighbors 10.0.0.1",
    "show bgp ipv4 unicast",
    "show ip bgp",
    "show ip bgp 192.168.1.0/24",
    "show bgp vpnv4 unicast all",
    "show bgp l2vpn evpn",
    "show bgp flowspec",
    "show interface GigabitEthernet0/0",
    "show ip route",
    "show ip ospf neighbor",
    "show segment-routing mpls gb",
    "show bfd neighbors",
    "show mpls forwarding-table",
    "show vrf CUSTOMER detail",
    "show rpki servers",
    "show bmp",
    "ping 10.0.0.1",
    "traceroute 192.0.2.1",
    "show log | inc BGP",
    "debug bgp updates",
    "clear bgp ipv4 unicast 10.0.0.1 soft out",
]:
    v = validate_command(cmd)
    check(f"OK: {cmd[:45]}", v.status == "ok", f"got {v.status}: {v.reason}")

# REJECT — config commands
for cmd in [
    "router bgp 65001",
    "neighbor 10.0.0.1 remote-as 65002",
    "network 10.0.0.0 mask 255.255.0.0",
    "ip prefix-list DENY permit 10.0.0.0/8",
    "route-map POLICY permit 10",
    "set local-preference 200",
    "interface GigabitEthernet0/0",
    "ip address 10.0.0.1 255.255.255.0",
    "no neighbor 10.0.0.2 shutdown",
    "commit",
    "write memory",
    "configure terminal",
]:
    v = validate_command(cmd)
    check(f"REJECT config: {cmd[:45]}", v.status == "reject", f"got {v.status}: {v.reason}")

# WARN — dangerous or unknown
for cmd in [
    "clear bgp *",
    "debug all",
    "show something-completely-unknown",
]:
    v = validate_command(cmd)
    check(f"WARN: {cmd[:45]}", v.status == "warn", f"got {v.status}: {v.reason}")

# Empty command
v_empty = validate_command("")
check("empty command rejected", v_empty.status == "reject")

# --------------------------------------------------------------------------
# Section 2: Runbook gate
# --------------------------------------------------------------------------
print("\n=== 2. Runbook gate ===")

good_rb = {
    "commands": [
        {"device": "R1", "cmd": "show bgp summary"},
        {"device": "R1", "cmd": "show bgp neighbors 10.0.0.1"},
        {"device": "R1", "cmd": "show ip route 10.0.0.0"},
    ]
}
result = validate_runbook(good_rb["commands"])
check("all-ok runbook passes gate", result["pass"] is True)
check("ok count = 3", result["ok"] == 3)
check("reject count = 0", result["reject"] == 0)
check("verdicts list length = 3", len(result["verdicts"]) == 3)
check("blocking_reason empty", result["blocking_reason"] == "")

# Mixed runbook (one config command)
mixed_rb = {
    "commands": [
        {"device": "R1", "cmd": "show bgp summary"},
        {"device": "R1", "cmd": "router bgp 65001"},   # CONFIG — must fail
    ]
}
result2 = validate_runbook(mixed_rb["commands"])
check("mixed runbook (config cmd) fails gate", result2["pass"] is False)
check("reject count = 1", result2["reject"] == 1)
check("blocking_reason not empty", len(result2["blocking_reason"]) > 0)

# Empty command list
empty_result = validate_runbook([])
check("empty command list fails gate (no commands)", empty_result["pass"] is False)

# Plain string commands (not dicts)
plain_cmds = ["show bgp summary", "show ip route"]
plain_result = validate_runbook([{"cmd": c} for c in plain_cmds])
check("plain string commands accepted", plain_result["pass"] is True)

# --------------------------------------------------------------------------
# Section 3: Gate function (top-level)
# --------------------------------------------------------------------------
print("\n=== 3. Gate function (top-level) ===")

# Synthesiser runbook format
synth_rb = {
    "commands": [
        {"device": "R1", "cmd": "show bgp neighbors 10.0.0.1"},
        {"device": "R1", "cmd": "show ip bgp summary"},
        {"device": "R2", "cmd": "show bgp ipv4 unicast 192.168.0.0/24"},
    ],
    "concluded_root_cause": "wrong remote-as configured",
}
g = gate(synth_rb)
check("gate() returns pass=True for clean synth runbook", g["pass"] is True)
check("gate() returns ok count", g["ok"] == 3)
check("gate() returns total count", g["total"] == 3)

# LLM-hallucinated config command in runbook
bad_rb = {
    "commands": [
        {"device": "R1", "cmd": "show bgp summary"},
        {"device": "R1", "cmd": "neighbor 10.0.0.1 remote-as 65002"},  # LLM hallucination
    ],
    "concluded_root_cause": "...",
}
g2 = gate(bad_rb)
check("gate() returns pass=False when config cmd present", g2["pass"] is False)
check("gate() blocking_reason identifies config command", "configuration" in g2["blocking_reason"].lower())

# --------------------------------------------------------------------------
# Section 4: Integration with synthesizer
# --------------------------------------------------------------------------
print("\n=== 4. Integration with synthesizer ===")

from opsrag import synthesizer
from opsrag.grammar_gate import gate as grammar_gate
import json, os

faults_dir = os.path.join(os.path.dirname(HERE), "thesis", "lab", "faults")
faults = []
for fname in sorted(os.listdir(faults_dir)):
    if fname.endswith(".json"):
        with open(os.path.join(faults_dir, fname)) as fh:
            faults.append(json.load(fh))

all_pass = True
for f in faults:
    rb = synthesizer.synthesise_with_sim(f)
    verdict = grammar_gate(rb)
    check(f"grammar gate passes synth runbook for {f['id']}", verdict["pass"],
          f"reject={verdict['reject']}, reason={verdict['blocking_reason']}")
    if not verdict["pass"]:
        all_pass = False

check("ALL seeded faults pass the grammar gate (≥90% exit criterion)", all_pass)

# --------------------------------------------------------------------------
print(f"\n{'='*40}")
print(f"RESULT: {_PASS} PASS / {_FAIL} FAIL")
if _FAIL:
    sys.exit(1)
