#!/usr/bin/env python3
"""OpsRAG BGP sandbox simulator — a deterministic mini-FRR for the seeded fault library.

Same return contract as a real Containerlab + FRR execution: feed it a fault scenario and a runbook,
get back per-command rc + realistic stdout. Lets the entire synthesizer → oracle → diagnosis loop run
end-to-end without Docker, so Phase 2 work (and most of the thesis writing) does not depend on a host.

Scope is intentionally narrow: just enough state + commands to faithfully reproduce the three seeded
faults (wrong remote-as, MTU mismatch, TCP-MD5 mismatch) on the topo-bgp topology. Real Containerlab
execution lands in Phase 2-B and is gated by output equivalence with this simulator on the same
benchmark.
"""
import re
from typing import Dict, List


def baseline_state() -> Dict:
    """Healthy state for the topo-bgp topology (R1 RR + R2 PE in AS 65001, R3 customer in AS 65010)."""
    return {"devices": {
        "R1": {"role": "rr", "as": 65001, "loopback": "10.255.0.1",
               "interfaces": [{"name": "eth1", "ip": "10.0.0.0/31", "oper": "up", "mtu": 9216, "desc": "to:R2"}],
               "bgp_neighbors": [{"neighbor": "10.255.0.2", "remote_as": 65001, "state": "Established",
                                  "prefixes": 3, "afi": "ipv4", "configured_remote_as": 65001}]},
        "R2": {"role": "pe", "as": 65001, "loopback": "10.255.0.2",
               "interfaces": [
                   {"name": "eth1", "ip": "10.0.0.1/31", "oper": "up", "mtu": 9216, "desc": "to:R1"},
                   {"name": "eth2", "ip": "192.0.2.1/31", "oper": "up", "mtu": 9216, "desc": "to:R3"},
               ],
               "bgp_neighbors": [
                   {"neighbor": "10.255.0.1", "remote_as": 65001, "state": "Established",
                    "prefixes": 3, "afi": "ipv4", "configured_remote_as": 65001},
                   {"neighbor": "192.0.2.2", "remote_as": 65010, "state": "Established",
                    "prefixes": 1, "afi": "ipv4", "configured_remote_as": 65010, "md5_set": False},
               ]},
        "R3": {"role": "ce", "as": 65010, "loopback": "10.255.0.3",
               "interfaces": [{"name": "eth1", "ip": "192.0.2.2/31", "oper": "up", "mtu": 9216, "desc": "to:R2"}],
               "bgp_neighbors": [{"neighbor": "192.0.2.1", "remote_as": 65001, "state": "Established",
                                  "prefixes": 2, "afi": "ipv4", "configured_remote_as": 65001}]},
    }}


def apply_fault(state: Dict, fault: Dict) -> Dict:
    """Mutate `state` per the fault inject. Recognises the three seeded patch dialects."""
    inj = fault.get("inject", {})
    dev = inj.get("device", "")
    patch = inj.get("patch", []) or []
    text = "\n".join(patch)
    d = state["devices"].get(dev)
    if not d:
        return state

    m = re.search(r"neighbor\s+(\S+)\s+remote-as\s+(\d+)", text, re.I)
    if m and "password" not in text.lower():
        ip, wrong = m.group(1), int(m.group(2))
        for nb in d["bgp_neighbors"]:
            if nb["neighbor"] == ip:
                nb["configured_remote_as"] = wrong   # what THIS device now thinks
                nb["state"] = "Active"               # session can't progress past OPEN
                nb["prefixes"] = 0
        return state

    m = re.search(r"neighbor\s+(\S+)\s+password\s+\S+", text, re.I)
    if m:
        ip = m.group(1)
        for nb in d["bgp_neighbors"]:
            if nb["neighbor"] == ip:
                nb["md5_set"] = True                 # asymmetric with the peer
                nb["state"] = "Idle"                 # TCP never opens
                nb["prefixes"] = 0
        return state

    m = re.search(r"interface\s+(\S+)\b", text, re.I)
    mtu_m = re.search(r"\bip\s+mtu\s+(\d+)|\bmtu\s+(\d+)\b", text, re.I)
    if m and mtu_m:
        ifn = m.group(1)
        new = int(next(g for g in mtu_m.groups() if g))
        for it in d["interfaces"]:
            if it["name"].lower() == ifn.lower():
                it["mtu"] = new
        # the eBGP neighbor reachable via that interface starts flapping
        for nb in d["bgp_neighbors"]:
            if nb["remote_as"] != d["as"]:           # eBGP
                nb["state"] = "Active"
                nb["prefixes"] = 0
        return state
    return state


def exec_cmd(state: Dict, device: str, command: str) -> Dict:
    """Tiny show-command dispatcher returning realistic FRR-like output."""
    d = state["devices"].get(device)
    if not d:
        return {"rc": 1, "stdout": f"% device {device!r} not in sandbox", "device": device, "cmd": command}
    c = command.strip().lower()

    if c.startswith(("show bgp summary", "show ip bgp summary")):
        lines = [f"BGP router identifier {d['loopback']}, local AS number {d['as']}",
                 "Neighbor        V         AS  State/PfxRcd"]
        for nb in d["bgp_neighbors"]:
            tail = str(nb["prefixes"]) if nb["state"] == "Established" else nb["state"]
            lines.append(f"{nb['neighbor']:<15}  4  {nb['remote_as']:>6}  {tail}")
        return {"rc": 0, "stdout": "\n".join(lines), "device": device, "cmd": command}

    if c.startswith(("show ip bgp neighbors", "show bgp neighbors")):
        parts = command.split()
        if len(parts) < 4:
            return {"rc": 2, "stdout": "% usage: show ip bgp neighbors <addr>", "device": device, "cmd": command}
        ip = parts[-1]
        nb = next((x for x in d["bgp_neighbors"] if x["neighbor"] == ip), None)
        if not nb:
            return {"rc": 0, "stdout": f"% No neighbor {ip}", "device": device, "cmd": command}
        out = [f"BGP neighbor is {ip}, remote AS {nb.get('configured_remote_as', nb['remote_as'])}",
               f"  BGP state = {nb['state']}",
               f"  Configured remote-as: {nb.get('configured_remote_as', nb['remote_as'])}",
               f"  Peer actual AS: {nb['remote_as']}",
               f"  TCP-MD5 password: {'set' if nb.get('md5_set') else 'not set'}"]
        return {"rc": 0, "stdout": "\n".join(out), "device": device, "cmd": command}

    if c.startswith("show interface"):
        parts = command.split()
        if len(parts) < 3:
            return {"rc": 2, "stdout": "% usage: show interface <name>", "device": device, "cmd": command}
        name = parts[2]
        it = next((x for x in d["interfaces"] if x["name"].lower() == name.lower()), None)
        if not it:
            return {"rc": 0, "stdout": f"% No interface {name}", "device": device, "cmd": command}
        out = [f"{it['name']} is {it['oper']}, line protocol is {it['oper']}",
               f"  Internet address {it['ip']}",
               f"  MTU {it['mtu']} bytes",
               f"  Description: {it.get('desc', '')}"]
        return {"rc": 0, "stdout": "\n".join(out), "device": device, "cmd": command}

    return {"rc": 2, "stdout": f"% unrecognized in sandbox: {command}", "device": device, "cmd": command}
