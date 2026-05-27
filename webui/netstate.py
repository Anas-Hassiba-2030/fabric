#!/usr/bin/env python3
"""WRATH read-only network-state source — pluggable + format-normalizing (live-wiring step).

One read-only loader behind assurance + RCA. It reads from, in order: an explicit source, a
`WRATH_NETSTATE_URL` (a read-only GET — pyATS/gNMI exporter, NetBox, or any JSON endpoint), or a
directory of snapshots (`WRATH_NETSTATE_DIR`, default `wrath/mcp/state`). The `normalize()` adapter
maps common field names (NetBox/gNMI/pyATS-ish) onto WRATH's device schema, so going live is a config
swap — not a rewrite. **Strictly read-only: only HTTP GET, never a write to a device or source.**

Pure parsing logic is deterministic — see webui/test_netstate.py.

    normalize(raw) -> {"devices": {name: {...}}}
    load(source=None) -> {"devices": {...}} | None
"""
import json
import os
import urllib.request

DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wrath", "mcp", "state")


def _oper(v):
    s = str(v or "").lower()
    if "down" in s:
        return "down"
    if "up" in s:
        return "up"
    return s or "?"


def _state(v):
    return "Established" if str(v or "").lower() == "established" else (v or "?")


def _itf(i):
    return {"name": i.get("name") or i.get("interface") or i.get("if") or "?",
            "ip": i.get("ip") or i.get("ipv4") or i.get("address") or "",
            "oper": _oper(i.get("oper") or i.get("oper-status") or i.get("status") or i.get("oper_status")),
            "mtu": i.get("mtu"),
            "desc": i.get("desc") or i.get("description") or ""}


def _nb(n):
    return {"neighbor": n.get("neighbor") or n.get("peer") or n.get("peer-ip") or n.get("address") or "?",
            "remote_as": n.get("remote_as") or n.get("remote-as") or n.get("peer_as"),
            "afi": n.get("afi") or n.get("address-family") or n.get("afi_safi") or "ipv4",
            "state": _state(n.get("state") or n.get("session-state") or n.get("session_state")),
            "prefixes": n.get("prefixes") or n.get("prefixes-received") or n.get("accepted_prefixes") or 0}


def _device(d):
    return {"role": d.get("role", ""), "platform": d.get("platform", ""), "version": d.get("version", ""),
            "site": d.get("site", ""),
            "interfaces": [_itf(i) for i in (d.get("interfaces") or [])],
            "bgp_neighbors": [_nb(n) for n in (d.get("bgp_neighbors") or d.get("bgp") or [])],
            "routes": d.get("routes", {})}


def normalize(raw):
    """Map a native or foreign (NetBox/gNMI/pyATS-ish) snapshot onto WRATH's device schema."""
    src = raw.get("devices", raw) if isinstance(raw, dict) else raw
    devices = {}
    if isinstance(src, dict):
        for name, d in src.items():
            devices[name] = _device(d if isinstance(d, dict) else {})
    elif isinstance(src, list):
        for d in src:
            if not isinstance(d, dict):
                continue
            name = d.get("name") or d.get("hostname") or d.get("device")
            if name:
                devices[name] = _device(d)
    return {"devices": devices}


def load(source=None):
    url = source if (source and str(source).startswith("http")) else os.environ.get("WRATH_NETSTATE_URL")
    if url:
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})  # read-only GET
            with urllib.request.urlopen(req, timeout=10) as r:
                return normalize(json.load(r))
        except Exception:
            return None
    d = source or os.environ.get("WRATH_NETSTATE_DIR") or DEFAULT_DIR
    merged = {"devices": {}}
    try:
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                for k, v in normalize(json.load(open(os.path.join(d, fn))))["devices"].items():
                    merged["devices"][k] = v
        return merged
    except Exception:
        return None


if __name__ == "__main__":
    print(json.dumps(load(), indent=1)[:1200])
