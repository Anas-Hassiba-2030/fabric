#!/usr/bin/env bash
# Functional test for the WRATH MCP servers — drives each over stdio with JSON-RPC and checks the
# responses. No MCP client/SDK required. Run: bash wrath/mcp/test_servers.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python || command -v python3)"
fail=0

# Send a sequence of JSON-RPC lines to a server and capture stdout.
drive() { printf '%s\n' "$@" | "$PY" "$1_SERVER" 2>/dev/null; }

check() { # desc, haystack, needle
  if printf '%s' "$2" | grep -q -- "$3"; then echo "  PASS  $1"; else echo "  FAIL  $1 (missing: $3)"; fail=1; fi
}

INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}'
LIST='{"jsonrpc":"2.0","id":2,"method":"tools/list"}'

echo "=== wrath-standards ==="
S="$HERE/standards_server.py"
out=$(printf '%s\n%s\n%s\n%s\n%s\n' \
  "$INIT" "$LIST" \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"lookup_standard","arguments":{"ref":"RFC 5082"}}}' \
  '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"verify_citation","arguments":{"ref":"RFC 9999","claim":"made up"}}}' \
  '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"search_standards","arguments":{"query":"evpn"}}}' \
  | "$PY" "$S" 2>/dev/null)
check "initialize ok"            "$out" '"serverInfo"'
check "tools/list has lookup"    "$out" 'lookup_standard'
check "RFC 5082 grounded (GTSM)" "$out" 'Generalized TTL Security'
check "unknown RFC -> UNVERIFIED" "$out" 'UNVERIFIED'
check "search finds EVPN RFC"    "$out" '7432'

echo "=== wrath-netstate (read-only) ==="
N="$HERE/network_state_server.py"
out=$(WRATH_NETSTATE_DIR="$HERE/state" printf '%s\n%s\n%s\n%s\n%s\n%s\n%s\n' \
  "$INIT" "$LIST" \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_devices","arguments":{}}}' \
  '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_bgp_neighbors","arguments":{"device":"PE1"}}}' \
  '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"get_route","arguments":{"device":"PE1","prefix":"0.0.0.0/0"}}}' \
  '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"check_drift","arguments":{}}}' \
  '{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"diagnose","arguments":{"symptom":"CustA lost connectivity, BGP down"}}}' \
  | WRATH_NETSTATE_DIR="$HERE/state" "$PY" "$N" 2>/dev/null)
check "initialize ok"          "$out" '"serverInfo"'
check "lists PE1"              "$out" 'PE1'
check "BGP Idle neighbor seen" "$out" 'Idle'
check "default route via RR"   "$out" '10.255.0.254'
check "check_drift flags DRIFT" "$out" 'DRIFT'
check "diagnose isolates the down-link cause" "$out" 'because its next-hop'
# safety: there must be NO write/config tool exposed
if printf '%s' "$out" | grep -qiE '"name":\s*"(set_|write_|config|apply|push|delete_)'; then
  echo "  FAIL  read-only posture (a write tool is exposed!)"; fail=1
else
  echo "  PASS  read-only posture (no write/config/apply tool exposed)"
fi

echo "=== done ==="
exit $fail
