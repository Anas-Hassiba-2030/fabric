#!/usr/bin/env bash
# WRATH consolidated test runner — runs every deterministic check in the repo with one command.
# Usage: bash run_tests.sh   (exit 0 = all green). Safe to wire into a SessionStart hook or CI.
set -u
cd "$(dirname "$0")"
PY="$(command -v python || command -v python3)"
fail=0
step() { echo; echo "==> $1"; }
ok()   { echo "    PASS — $1"; }
bad()  { echo "    FAIL — $1"; fail=1; }

step "JSON config validity"
for f in .claude/settings.json .mcp.json \
         wrath/mcp/data/standards.json wrath/mcp/state/sample-testbed.json; do
  if "$PY" -c "import json,sys; json.load(open('$f'))" 2>/dev/null; then ok "$f"; else bad "$f"; fi
done

step "CSIRT guard hook battery"
if bash .claude/hooks/test_csirt_guard.sh >/tmp/_csirt.out 2>&1; then ok "csirt_guard ($(grep -c PASS /tmp/_csirt.out) checks)"; else bad "csirt_guard"; cat /tmp/_csirt.out; fi

step "config_lint self-test"
if "$PY" .claude/skills/config-audit/scripts/config_lint.py --self-test >/tmp/_lint.out 2>&1 && grep -q "SELF-TEST PASS" /tmp/_lint.out; then ok "config_lint self-test"; else bad "config_lint self-test"; cat /tmp/_lint.out; fi

step "anti-hallucination grounding proof (no API key)"
if "$PY" webui/test_grounding.py >/tmp/_grnd.out 2>&1; then ok "grounding net holds (fake RFC blocked, bad config failed, numbers flagged)"; else bad "grounding net"; cat /tmp/_grnd.out; fi

step "Clarifying-questions gate proof (no API key)"
if "$PY" webui/test_clarify.py >/tmp/_clar.out 2>&1; then ok "clarify-gate holds (vague blocked, fully-specified ready)"; else bad "clarify gate"; cat /tmp/_clar.out; fi

step "Memory recall proof (no API key)"
if "$PY" webui/test_recall.py >/tmp/_rec.out 2>&1; then ok "memory recall compounds (pattern recalled, no false positives)"; else bad "memory recall"; cat /tmp/_rec.out; fi

step "Auto topology diagram proof (no API key)"
if "$PY" webui/test_topology.py >/tmp/_topo.out 2>&1; then ok "auto topology renders valid Mermaid (core+redundancy, DC vs SP)"; else bad "auto topology"; cat /tmp/_topo.out; fi

step "Cost/TCO + risk register honesty proof (no API key)"
if "$PY" webui/test_tco.py >/tmp/_tco.out 2>&1; then ok "cost/TCO honest (drivers sourced, no invented currency, risks adapt)"; else bad "cost/TCO"; cat /tmp/_tco.out; fi

step "Trust report fidelity proof (no API key)"
if "$PY" webui/test_trust.py >/tmp/_trust.out 2>&1; then ok "trust report faithful (grounded/flagged/blocked, ledger, confidence)"; else bad "trust report"; cat /tmp/_trust.out; fi

step "Run export proof (no API key)"
if "$PY" webui/test_export.py >/tmp/_exp.out 2>&1; then ok "run export bundles the stack (order, deliverables, grounding, trust)"; else bad "run export"; cat /tmp/_exp.out; fi

step "What-if compare proof (no API key)"
if "$PY" webui/test_whatif.py >/tmp/_wif.out 2>&1; then ok "what-if compare diffs runs (changed/same/only, metrics, deltas)"; else bad "what-if compare"; cat /tmp/_wif.out; fi

step "Engagement blueprints proof (no API key)"
if "$PY" webui/test_blueprints.py >/tmp/_bp.out 2>&1; then ok "blueprints complete + clear the clarify-gate"; else bad "blueprints"; cat /tmp/_bp.out; fi

step "Cross-run analytics proof (no API key)"
if "$PY" webui/test_analytics.py >/tmp/_an.out 2>&1; then ok "analytics aggregate faithfully (runs, trust, grounding, tags)"; else bad "analytics"; cat /tmp/_an.out; fi

step "Self-improving pattern distil proof (no API key)"
if "$PY" webui/test_distill.py >/tmp/_dst.out 2>&1; then ok "accepted runs distil into reusable, RAG-discoverable patterns"; else bad "pattern distil"; cat /tmp/_dst.out; fi

step "Live-mode wiring proof (mocked Claude, no API key)"
if "$PY" webui/test_live.py >/tmp/_live.out 2>&1; then ok "live wiring chains, gates bite, hallucination caught"; else bad "live wiring"; cat /tmp/_live.out; fi

step "MCP servers (stdio JSON-RPC)"
if bash wrath/mcp/test_servers.sh >/tmp/_mcp.out 2>&1; then ok "wrath-standards + wrath-netstate ($(grep -c PASS /tmp/_mcp.out) checks)"; else bad "mcp servers"; cat /tmp/_mcp.out; fi

step "Worked-example configs pass the audit gate"
for cfg in deliverables/example-acme-sp/03-config-pe1.cfg deliverables/example-acme-sp/03b-config-pe3.cfg; do
  if "$PY" .claude/skills/config-audit/scripts/config_lint.py "$cfg" >/tmp/_cfg.out 2>&1; then ok "$(basename "$cfg") (no CRITICAL/HIGH)"; else bad "$(basename "$cfg") — $(grep -E '^\[' /tmp/_cfg.out | head -3)"; fi
done

step "Skills + MCP servers present"
sk=$(find .claude/skills -name SKILL.md | wc -l); mc=$(ls wrath/mcp/*_server.py 2>/dev/null | wc -l)
[ "$sk" -ge 15 ] && ok "$sk skills" || bad "only $sk skills"
[ "$mc" -eq 2 ]  && ok "$mc MCP servers" || bad "expected 2 MCP servers, found $mc"

echo
if [ "$fail" -eq 0 ]; then echo "ALL GREEN"; else echo "FAILURES ABOVE"; fi
exit $fail
