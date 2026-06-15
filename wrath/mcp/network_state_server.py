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
  check_drift()                        -> live state vs design intent (Idle BGP, down links, MTU)
  diagnose(symptom)                    -> root-cause analysis (layered hypothesis tree, proven chain)
All read-only: check_drift/diagnose reason over the snapshot and recommend; they never change a device.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_REPO, "webui"))
from _mcpserver import MCPServer, log  # noqa: E402
import assurance  # noqa: E402  (shared SLO/drift engine — read-only reasoning over state)
import netstate  # noqa: E402  (shared read-only loader: WRATH_NETSTATE_URL or snapshot dir, normalized)
import rca  # noqa: E402  (shared root-cause engine — read-only reasoning over state)

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


@server.tool(
    "check_drift",
    "Re-validate current read-only state against design intent: flag non-Established BGP sessions, "
    "down (non-loopback) interfaces, and sub-jumbo core MTU. Read-only — reports drift, never fixes.",
    {"type": "object", "properties": {}},
)
def check_drift(_args):
    dr = assurance.drift_check({"devices": _load_state()})
    if not dr["checks"]:
        return "no state available, or nothing to check"
    head = f"{dr['ok']} healthy / {dr['drift']} drift"
    rows = [f"[{'DRIFT' if c['status'] == 'drift' else 'ok'}] {c['check']} — expected {c['expected']}, observed {c['observed']}"
            for c in dr["checks"]]
    return head + "\n" + "\n".join(rows)


@server.tool(
    "diagnose",
    "Root-cause analysis from the read-only state for a symptom: walks a layered hypothesis tree and "
    "isolates a proven causal chain (e.g. eBGP Idle because its next-hop link is down). Read-only; the "
    "fix is a recommendation a human executes.",
    {"type": "object", "properties": {"symptom": {"type": "string"}}, "required": ["symptom"]},
)
def diagnose(args):
    a = rca.analyze(str(args.get("symptom", "")), {"devices": _load_state()})
    out = [f"Symptom: {a['symptom']}", "", "Hypotheses:"]
    out += [f"  [{h['verdict']}] {h['layer']}: {h['hypothesis']} — {h['evidence']}" for h in a["hypotheses"]]
    out += ["", "Root cause: " + a["root_cause"]]
    if a["fix"]:
        out.append("Fix (needs human/Kamal — read-only MCP never pushes): " + a["fix"])
    if a["verify"]:
        out.append("Verify: " + a["verify"])
    return "\n".join(out)


if __name__ == "__main__":
    log(f"wrath-netstate MCP (READ-ONLY) starting; snapshot dir = {STATE_DIR}")
    server.run()
