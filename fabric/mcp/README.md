# FABRIC MCP servers — the connections (charter §5)

Two **read-only** MCP servers that connect FABRIC to grounded references and network state. Both are
dependency-free Python stdio servers (stock `python3`, same posture as the hooks) and are registered
for Claude Code in the repo-root `.mcp.json`.

| Server | Purpose | Source | Safety |
|---|---|---|---|
| `fabric-standards` | grounded RFC / IEEE / framework lookup + citation verification | curated `data/standards.json`; best-effort live rfc-editor when egress allows | read-only; never fabricates a reference |
| `fabric-netstate` | live `show`/telemetry/inventory for the Troubleshooter & others | JSON snapshots in `$FABRIC_NETSTATE_DIR` (default `state/`) | **read-only by construction — no write/config/apply tool exists** |

## Tools
**fabric-standards** — `lookup_standard(ref)`, `search_standards(query)`, `verify_citation(ref, claim?)`.
Unknown/unverifiable references return `NOT FOUND` / `UNVERIFIED`, which is exactly what the
Orchestrator's citation-guard needs (House Rule 4 — kill hallucinated RFC numbers).

**fabric-netstate** — `list_devices()`, `get_interfaces(device)`, `get_bgp_neighbors(device)`,
`get_route(device, prefix)`, `get_inventory(device)`.

## Safety posture (charter §3 / House Rules 2 & 6)
The network-state MCP ships **read-only** and contains no tool that can change a device — write access
is a separate, deliberately-hard, later decision. Anything that changes the live network stays with the
Config Engineer behind the `destructive-action-guard` hook and Kamal's confirmation.

## Going live
The tool surface is fixed and read-only; only the data source changes:
- **Standards:** extend `data/standards.json` with verified entries, or rely on the live fetch where
  egress to `rfc-editor.org` is permitted (the server degrades gracefully to the curated index).
- **Network state:** point `FABRIC_NETSTATE_DIR` at snapshots produced by pyATS `learn`, gNMI
  subscriptions, or a NetBox/CMDB export (shape per `state/sample-testbed.json`). No code change.

## Test
```
bash fabric/mcp/test_servers.sh
```
Drives each server over stdio with JSON-RPC and asserts the tool results, including that no
write/config tool is exposed.
