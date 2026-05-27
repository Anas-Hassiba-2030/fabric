#!/usr/bin/env python3
"""WRATH Network-state MCP (READ-ONLY) — live show/telemetry/inventory, never write.

Backs the Troubleshooter and any agent that needs current network state (charter §5: "Network-state
MCP (read-only) ... do read-only first, never write"). Safety posture is structural: this server
exposes ONLY read tools. There is no write/config/apply tool anywhere in it, so it cannot change a
device even if asked. Any change to the network stays with the Config Engineer + destructive-action-
guard + Kamal (House Rules 2/6).

Data source: JSON snapshots in $WRATH_NETSTATE_DIR (default: ./state). Each *.json holds a
{"devices": {...}} map shaped like state/sample-testbed.json. This makes the MCP functional and
testable offline; to go live, point WRATH_NETSTATE_DIR at snapshots produced by pyATS `learn`,
gNMI subscriptions, or a NetBox/CMDB export — the tool surface stays identical and read-only.

Tools:
  list_devices()                       -> devices + role/platform/site
  get_interfaces(device)               -> interface table (name/ip/oper/desc/mtu)
  get_bgp_neighbors(device)            -> BGP sessions (neighbor/as/afi/state/prefixes)
  get_route(device, prefix)            -> route lookup for a prefix
  get_inventory(device)                -> hardware/serial/redundancy
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_REPO, "webui"))
from _mcpserver import MCPServer, log  # noqa: E402
import netstate  # noqa: E402  (shared read-only loader: WRATH_NETSTATE_URL or snapshot dir, normalized)

STATE_DIR = os.environ.get("WRATH_NETSTATE_DIR") or os.path.join(_HERE, "state")


def _load_state():
    # One read-only source for the web app AND this MCP: a WRATH_NETSTATE_URL feed (read-only GET) or
    # the snapshot dir, foreign formats normalized. Never writes to a device or source.
    return (netstate.load() or {}).get("devices", {})


def _device(name):
    devs = _load_state()
    d = devs.get(name)
    if not d:
        raise ValueError(f"device '{name}' not found. Known: {', '.join(sorted(devs)) or '(none — check WRATH_NETSTATE_DIR)'}")
    return d


server = MCPServer("wrath-netstate", "0.1.0")


@server.tool(
    "list_devices",
    "List devices in the read-only network-state snapshot with role, platform, version, and site.",
    {"type": "object", "properties": {}},
)
def list_devices(_args):
    devs = _load_state()
    if not devs:
        return f"no devices in snapshot dir {STATE_DIR} — set WRATH_NETSTATE_DIR to a snapshot directory"
    return "\n".join(
        f"{n} — {d.get('role','?')} / {d.get('platform','?')} {d.get('version','')} @ {d.get('site','?')}"
        for n, d in sorted(devs.items()))


@server.tool(
    "get_interfaces", "Read the interface table for a device (name, ip, oper-state, description, mtu).",
    {"type": "object", "properties": {"device": {"type": "string"}}, "required": ["device"]},
)
def get_interfaces(args):
    d = _device(str(args.get("device", "")))
    rows = d.get("interfaces", [])
    if not rows:
        return "(no interfaces in snapshot)"
    out = [f"{r.get('name'):<26} {str(r.get('ip','')):<18} {r.get('oper','?'):<5} mtu={r.get('mtu','-')}  {r.get('desc','')}" for r in rows]
    return "\n".join(out)


@server.tool(
    "get_bgp_neighbors", "Read BGP neighbors for a device (neighbor, remote-as, afi, state, prefixes).",
    {"type": "object", "properties": {"device": {"type": "string"}}, "required": ["device"]},
)
def get_bgp_neighbors(args):
    d = _device(str(args.get("device", "")))
    rows = d.get("bgp_neighbors", [])
    if not rows:
        return "(no BGP neighbors in snapshot)"
    return "\n".join(
        f"{r.get('neighbor'):<16} AS{r.get('remote_as','?'):<7} {r.get('afi','?'):<7} {r.get('state','?'):<12} prefixes={r.get('prefixes','-')}"
        for r in rows)


@server.tool(
    "get_route", "Look up a route/prefix in a device's RIB snapshot (protocol, next-hop, label).",
    {"type": "object", "properties": {"device": {"type": "string"}, "prefix": {"type": "string"}}, "required": ["device", "prefix"]},
)
def get_route(args):
    d = _device(str(args.get("device", "")))
    prefix = str(args.get("prefix", ""))
    routes = d.get("routes", {})
    r = routes.get(prefix)
    if not r:
        return f"no route for {prefix} in snapshot. Known prefixes: {', '.join(sorted(routes)) or '(none)'}"
    label = f" label={r['label']}" if "label" in r else ""
    return f"{prefix} via {r.get('nexthop','?')} [{r.get('protocol','?')}]{label}"


@server.tool(
    "get_inventory", "Read hardware inventory for a device (chassis, serial, PSU/RP redundancy).",
    {"type": "object", "properties": {"device": {"type": "string"}}, "required": ["device"]},
)
def get_inventory(args):
    d = _device(str(args.get("device", "")))
    inv = d.get("inventory", {})
    if not inv:
        return "(no inventory in snapshot)"
    return "\n".join(f"{k}: {v}" for k, v in inv.items())


if __name__ == "__main__":
    log(f"wrath-netstate MCP (READ-ONLY) starting; snapshot dir = {STATE_DIR}")
    server.run()
