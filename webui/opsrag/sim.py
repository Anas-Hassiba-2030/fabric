#!/usr/bin/env python3
"""OpsRAG BGP sandbox simulator — a deterministic mini-FRR for the seeded fault library.

Same return contract as a real Containerlab + FRR execution: feed it a fault scenario and a runbook,
get back per-command rc + realistic stdout. Lets the entire synthesizer → oracle → diagnosis loop run
end-to-end without Docker, so Phase 2 work (and most of the thesis writing) does not depend on a host.

Scope: faithfully reproduce the eight seeded faults on the topo-bgp topology:
  Faults 1-3 (original):  wrong-remote-as, MTU mismatch, TCP-MD5 mismatch
  Faults 4-8 (new):       route-policy-reject, next-hop-unreachable, max-prefix-limit,
                           hold-timer-expired, ebgp-multihop
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
                    "prefixes": 2, "afi": "ipv4", "configured_remote_as": 65010,
                    "md5_set": False, "route_map_deny": False,
                    "max_prefix_limit": None, "next_hop_in_rib": True,
                    "hold_time": 180, "keepalive": 60,
                    "hold_timer_expired": False, "multihop_required": False},
               ],
               "rib": {"192.0.2.0/31": True},
               "route_maps": {}},
        "R3": {"role": "ce", "as": 65010, "loopback": "10.255.0.3",
               "interfaces": [{"name": "eth1", "ip": "192.0.2.2/31", "oper": "up", "mtu": 9216, "desc": "to:R2"}],
               "bgp_neighbors": [{"neighbor": "192.0.2.1", "remote_as": 65001, "state": "Established",
                                  "prefixes": 2, "afi": "ipv4", "configured_remote_as": 65001}]},
    }}


def apply_fault(state: Dict, fault: Dict) -> Dict:
    """Mutate `state` per the fault inject spec."""
    inj = fault.get("inject", {})
    dev = inj.get("device", "")
    patch = inj.get("patch", []) or []
    text = "\n".join(patch)
    d = state["devices"].get(dev)
    if not d:
        return state

    # --- Faults 1 + 8: neighbor X remote-as Y (existing = wrong-AS; new 10.10.x.x = multihop) ---
    m = re.search(r"neighbor\s+(\S+)\s+remote-as\s+(\d+)", text, re.I)
    if m and "password" not in text.lower() and "maximum-prefix" not in text.lower():
        ip, new_as = m.group(1), int(m.group(2))
        existing_nb = next((nb for nb in d["bgp_neighbors"] if nb["neighbor"] == ip), None)
        if existing_nb:
            # Fault 1: wrong remote-as on an already-configured neighbour
            existing_nb["configured_remote_as"] = new_as
            existing_nb["state"] = "Active"
            existing_nb["prefixes"] = 0
            return state
        elif ip.startswith("10.10."):
            # Fault 8: brand-new non-adjacent eBGP peer; TTL=1 means it never opens
            d["bgp_neighbors"].append({
                "neighbor": ip, "remote_as": new_as,
                "configured_remote_as": new_as,
                "state": "Active", "prefixes": 0,
                "multihop_required": True, "md5_set": False,
            })
            return state

    # --- Fault 2: TCP-MD5 password mismatch ---
    m = re.search(r"neighbor\s+(\S+)\s+password\s+\S+", text, re.I)
    if m:
        ip = m.group(1)
        for nb in d["bgp_neighbors"]:
            if nb["neighbor"] == ip:
                nb["md5_set"] = True
                nb["state"] = "Idle"
                nb["prefixes"] = 0
        return state

    # --- Fault 3: MTU mismatch ---
    m_if = re.search(r"interface\s+(\S+)\b", text, re.I)
    mtu_m = re.search(r"\bip\s+mtu\s+(\d+)|\bmtu\s+(\d+)\b", text, re.I)
    if m_if and mtu_m:
        ifn = m_if.group(1)
        new = int(next(g for g in mtu_m.groups() if g))
        for it in d["interfaces"]:
            if it["name"].lower() == ifn.lower():
                it["mtu"] = new
        for nb in d["bgp_neighbors"]:
            if nb["remote_as"] != d["as"]:
                nb["state"] = "Active"
                nb["prefixes"] = 0
        return state

    # --- Fault 10 (check before Fault 4): local-pref override via route-map on iBGP session ---
    if re.search(r"set\s+local-preference\s+\d+", text, re.I):
        m_nb = re.search(r"neighbor\s+(\S+)\s+route-map\s+(\S+)\s+in", text, re.I)
        if m_nb:
            ip, rm_name = m_nb.group(1), m_nb.group(2)
        else:
            ip, rm_name = "10.255.0.1", "SET-LOW-LOCPREF"
        m_lp = re.search(r"set\s+local-preference\s+(\d+)", text, re.I)
        lp = int(m_lp.group(1)) if m_lp else 50
        for nb in d["bgp_neighbors"]:
            if nb["neighbor"] == ip:
                nb["route_map_deny"] = False
                nb["route_map_name"] = rm_name
                nb["local_pref_override"] = lp
                nb["local_pref_note"] = f"Set local-preference {lp} for all routes from this iBGP peer"
        d.setdefault("route_maps", {})[rm_name] = f"permit 10 / set local-preference {lp}"
        return state

    # --- Fault 4: route-policy deny (route-map DENY-ALL inbound on eBGP session) ---
    if re.search(r"route-map\s+\S+\s+deny", text, re.I) or re.search(r"route-map\s+\S+\s+in", text, re.I):
        # Find the neighbor this route-map is applied to
        m_nb = re.search(r"neighbor\s+(\S+)\s+route-map\s+(\S+)\s+in", text, re.I)
        rm_name = None
        if m_nb:
            ip, rm_name = m_nb.group(1), m_nb.group(2)
        else:
            # Route-map defined but neighbour line might be separate; apply to eBGP peer
            ip = "192.0.2.2"
        for nb in d["bgp_neighbors"]:
            if nb["neighbor"] == ip:
                nb["route_map_deny"] = True
                nb["route_map_name"] = rm_name or "DENY-ALL"
                nb["state"] = "Established"  # session stays up
                nb["prefixes"] = 0           # but no prefixes admitted
        if rm_name:
            d.setdefault("route_maps", {})[rm_name] = "deny 10 / permit 20"
        return state

    # --- Fault 5: next-hop unreachable (connected route removed) ---
    if re.search(r"no\s+ip\s+route\s+192\.0\.2\.0", text, re.I):
        d.setdefault("rib", {})["192.0.2.0/31"] = False
        for nb in d["bgp_neighbors"]:
            if nb.get("neighbor") == "192.0.2.2":
                nb["next_hop_in_rib"] = False
                # Session stays up (TCP keepalives through existing connection) but prefix inactive
                nb["state"] = "Established"
        return state

    # --- Fault 6: max-prefix limit exceeded ---
    m_mp = re.search(r"neighbor\s+(\S+)\s+maximum-prefix\s+(\d+)", text, re.I)
    if m_mp:
        ip, limit = m_mp.group(1), int(m_mp.group(2))
        for nb in d["bgp_neighbors"]:
            if nb["neighbor"] == ip:
                nb["max_prefix_limit"] = limit
                # Peer sends 2 prefixes; limit=1 causes immediate session teardown
                if limit < 2:
                    nb["state"] = "Idle"
                    nb["prefixes"] = 0
                    nb["max_prefix_exceeded"] = True
        return state

    # --- Fault 7: hold-timer too aggressive ---
    m_ht = re.search(r"neighbor\s+(\S+)\s+timers\s+(\d+)\s+(\d+)", text, re.I)
    if m_ht:
        ip = m_ht.group(1)
        keepalive, hold = int(m_ht.group(2)), int(m_ht.group(3))
        for nb in d["bgp_neighbors"]:
            if nb["neighbor"] == ip:
                nb["keepalive"] = keepalive
                nb["hold_time"] = hold
                if hold <= 10:
                    nb["hold_timer_expired"] = True
                    nb["state"] = "Idle"
                    nb["prefixes"] = 0
        return state

    # --- Fault 8: eBGP multihop not configured ---
    m_mh = re.search(r"neighbor\s+(\S+)\s+remote-as\s+(\d+)", text, re.I)
    if m_mh and "multihop" not in text.lower():
        ip = m_mh.group(1)
        # If the peer IP is a loopback (non-/31 subnet, different prefix), mark multihop needed
        if ip.startswith("10.10."):
            nb_new = {
                "neighbor": ip, "remote_as": int(m_mh.group(2)),
                "configured_remote_as": int(m_mh.group(2)),
                "state": "Active", "prefixes": 0,
                "multihop_required": True, "md5_set": False,
            }
            d["bgp_neighbors"].append(nb_new)
        return state

    # --- Fault 9: AS_PATH loop (own AS in received path) ---
    if re.search(r"as-path-loop-inject\s+65001", text, re.I):
        for nb in d["bgp_neighbors"]:
            if nb.get("remote_as", 0) != d["as"]:
                nb["as_path_loop"] = True
                nb["prefixes"] = 0
                # Session stays established; UPDATE is silently discarded by loop guard
                nb["state"] = "Established"
        return state

    return state


def exec_cmd(state: Dict, device: str, command: str) -> Dict:
    """Tiny show-command dispatcher returning realistic FRR-like output."""
    d = state["devices"].get(device)
    if not d:
        return {"rc": 1, "stdout": f"% device {device!r} not in sandbox", "device": device, "cmd": command}
    c = command.strip().lower()

    # --- show bgp summary ---
    if c.startswith(("show bgp summary", "show ip bgp summary")):
        lines = [f"BGP router identifier {d['loopback']}, local AS number {d['as']}",
                 "Neighbor        V         AS  State/PfxRcd"]
        for nb in d["bgp_neighbors"]:
            tail = str(nb["prefixes"]) if nb["state"] == "Established" else nb["state"]
            lines.append(f"{nb['neighbor']:<15}  4  {nb['remote_as']:>6}  {tail}")
        return {"rc": 0, "stdout": "\n".join(lines), "device": device, "cmd": command}

    # --- show ip bgp neighbors <addr> ---
    if c.startswith(("show ip bgp neighbors", "show bgp neighbors")):
        parts = command.split()
        if len(parts) < 4:
            return {"rc": 2, "stdout": "% usage: show ip bgp neighbors <addr>", "device": device, "cmd": command}
        ip = parts[-1]
        nb = next((x for x in d["bgp_neighbors"] if x["neighbor"] == ip), None)
        if not nb:
            return {"rc": 0, "stdout": f"% No neighbor {ip}", "device": device, "cmd": command}
        out = [
            f"BGP neighbor is {ip}, remote AS {nb.get('configured_remote_as', nb['remote_as'])}",
            f"  BGP state = {nb['state']}",
            f"  Configured remote-as: {nb.get('configured_remote_as', nb['remote_as'])}",
            f"  Peer actual AS: {nb['remote_as']}",
            f"  TCP-MD5 password: {'set' if nb.get('md5_set') else 'not set'}",
            f"  Hold time = {nb.get('hold_time', 180)}, Keepalive interval = {nb.get('keepalive', 60)}",
        ]
        if nb.get("hold_timer_expired"):
            out.append("  Last reset: Hold Timer Expired")
        if nb.get("route_map_deny"):
            rm = nb.get("route_map_name", "DENY-ALL")
            out.append(f"  Route-map for incoming advertisements is {rm}")
            out.append(f"  Prefixes received and rejected by policy: 2")
        if nb.get("max_prefix_exceeded"):
            out.append(f"  NOTIFICATION sent: Maximum prefix reached ({nb.get('max_prefix_limit',1)})")
        if nb.get("multihop_required"):
            out.append("  External BGP neighbor not directly connected.")
            out.append("  TTL = 1, multihop not configured")
        if not nb.get("next_hop_in_rib", True):
            out.append("  Next-hop: 192.0.2.2 (UNREACHABLE — not in RIB)")
        if nb.get("as_path_loop"):
            out.append("  Prefixes received: 1 (discarded by AS_PATH loop detection)")
            out.append("  AS_PATH loop detected: own AS 65001 in received path — UPDATE discarded")
        if nb.get("local_pref_override") is not None:
            rm = nb.get("route_map_name", "SET-LOW-LOCPREF")
            lp = nb.get("local_pref_override", 50)
            out.append(f"  Route-map for incoming advertisements is {rm}")
            out.append(f"  Set local-preference {lp} (overrides default 100)")
        return {"rc": 0, "stdout": "\n".join(out), "device": device, "cmd": command}

    # --- show interface <name> ---
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

    # --- show ip route <addr> ---
    if c.startswith(("show ip route", "show route")):
        parts = command.split()
        addr = parts[-1] if len(parts) >= 3 else ""
        rib = d.get("rib", {})
        # Check if address falls in any rib entry
        in_rib = any(
            addr.startswith(prefix.split("/")[0].rsplit(".", 1)[0])
            for prefix, ok in rib.items() if ok
        )
        if in_rib:
            return {"rc": 0, "stdout": f"C 192.0.2.0/31 is directly connected, eth2", "device": device, "cmd": command}
        return {"rc": 1, "stdout": f"% Network not in table: {addr}", "device": device, "cmd": command}

    # --- show route-map ---
    if c.startswith("show route-map"):
        parts = command.split()
        rm_name = parts[2] if len(parts) >= 3 else None
        rms = d.get("route_maps", {})
        if not rms:
            return {"rc": 0, "stdout": "% No route-maps defined", "device": device, "cmd": command}
        out = []
        for name, content in rms.items():
            if rm_name is None or name == rm_name:
                if "deny" in content:
                    out.append(f"route-map {name}, deny, sequence 10")
                    out.append("  Match clauses:")
                    out.append("  Set clauses:")
                    out.append(f"route-map {name}, permit, sequence 20")
                elif "local-preference" in content:
                    lp = re.search(r"local-preference\s+(\d+)", content)
                    out.append(f"route-map {name}, permit, sequence 10")
                    out.append("  Match clauses:")
                    out.append(f"  set local-preference {lp.group(1) if lp else '50'}")
                else:
                    out.append(f"route-map {name}, permit, sequence 10")
        return {"rc": 0, "stdout": "\n".join(out) or "% No route-maps matched", "device": device, "cmd": command}

    # --- show ip bgp <prefix> ---
    if c.startswith("show ip bgp ") and len(c.split()) >= 4:
        prefix = command.split()[3]
        # Find the eBGP neighbor state
        nb = next((x for x in d["bgp_neighbors"] if x.get("remote_as", 0) != d["as"]), None)
        if nb and not nb.get("next_hop_in_rib", True):
            return {"rc": 0, "stdout": (
                f"BGP routing table entry for {prefix}\n"
                f"Paths: (1 available, no best path)\n"
                f"  192.0.2.2 (UNREACHABLE)\n"
                f"  AS path: 65010\n"
                f"  Next hop: 192.0.2.2 (not in RIB)"
            ), "device": device, "cmd": command}
        if nb and nb.get("route_map_deny"):
            return {"rc": 0, "stdout": f"% Network {prefix} not in table (denied by policy)", "device": device, "cmd": command}
        return {"rc": 0, "stdout": (
            f"BGP routing table entry for {prefix}\n"
            f"Paths: (1 available, best #1)\n"
            f"  192.0.2.2 from 192.0.2.2 (10.255.0.3)\n"
            f"  AS path: 65010"
        ), "device": device, "cmd": command}

    return {"rc": 2, "stdout": f"% unrecognized in sandbox: {command}", "device": device, "cmd": command}
