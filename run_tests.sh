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

step "Compliance pack proof (no API key)"
if "$PY" webui/test_compliance.py >/tmp/_cmp.out 2>&1; then ok "compliance pack maps frameworks honestly (design-addressed, audit-confirmed)"; else bad "compliance"; cat /tmp/_cmp.out; fi

step "Headless CLI proof (no API key)"
if "$PY" webui/test_cli.py >/tmp/_cli.out 2>&1; then ok "headless WRATH runs + emits a faithful bundle"; else bad "headless cli"; cat /tmp/_cli.out; fi

step "Multi-model routing proof (no API key)"
if "$PY" webui/test_routing.py >/tmp/_rt.out 2>&1; then ok "routing matches charter tiers (Opus heavy / Sonnet / Haiku)"; else bad "routing"; cat /tmp/_rt.out; fi

step "Critic-intensity dial proof (no API key)"
if "$PY" webui/test_criticism.py >/tmp/_cr.out 2>&1; then ok "critic dial maps (lenient 0 / standard 1 / max 2 passes)"; else bad "critic dial"; cat /tmp/_cr.out; fi

step "Audience reframing proof (no API key)"
if "$PY" webui/test_audience.py >/tmp/_aud.out 2>&1; then ok "audience reframing honest (CFO/CISO/NOC voices, no invented $)"; else bad "audience"; cat /tmp/_aud.out; fi

step "Provenance labelling proof (no API key)"
if "$PY" webui/test_provenance.py >/tmp/_pv.out 2>&1; then ok "provenance honest (real gates stay REAL in any mode)"; else bad "provenance"; cat /tmp/_pv.out; fi

step "Shareable HTML report proof (no API key)"
if "$PY" webui/test_share.py >/tmp/_sh.out 2>&1; then ok "shareable HTML report self-contained + faithful"; else bad "share"; cat /tmp/_sh.out; fi

step "Run export proof (no API key)"
if "$PY" webui/test_export.py >/tmp/_exp.out 2>&1; then ok "run export bundles the stack (order, deliverables, grounding, trust)"; else bad "run export"; cat /tmp/_exp.out; fi

step "What-if compare proof (no API key)"
if "$PY" webui/test_whatif.py >/tmp/_wif.out 2>&1; then ok "what-if compare diffs runs (changed/same/only, metrics, deltas)"; else bad "what-if compare"; cat /tmp/_wif.out; fi

step "Engagement blueprints proof (no API key)"
if "$PY" webui/test_blueprints.py >/tmp/_bp.out 2>&1; then ok "blueprints complete + clear the clarify-gate"; else bad "blueprints"; cat /tmp/_bp.out; fi

step "Inbox (saved results) proof (no API key)"
if "$PY" webui/test_inbox.py >/tmp/_ib.out 2>&1; then ok "inbox saves/edits/removes/persists"; else bad "inbox"; cat /tmp/_ib.out; fi

step "Cross-run analytics proof (no API key)"
if "$PY" webui/test_analytics.py >/tmp/_an.out 2>&1; then ok "analytics aggregate faithfully (runs, trust, grounding, tags)"; else bad "analytics"; cat /tmp/_an.out; fi

step "Pattern git-persist proof (no API key, throwaway repo)"
if "$PY" webui/test_persist.py >/tmp/_ps.out 2>&1; then ok "patterns persist to git (path-scoped, safe no-op)"; else bad "git persist"; cat /tmp/_ps.out; fi

step "Self-improving pattern distil proof (no API key)"
if "$PY" webui/test_distill.py >/tmp/_dst.out 2>&1; then ok "accepted runs distil into reusable, RAG-discoverable patterns"; else bad "pattern distil"; cat /tmp/_dst.out; fi

step "Live-mode wiring proof (mocked Claude, no API key)"
if "$PY" webui/test_live.py >/tmp/_live.out 2>&1; then ok "live wiring chains, gates bite, hallucination caught"; else bad "live wiring"; cat /tmp/_live.out; fi

step "Read-only network-state loader proof (no live source)"
if "$PY" webui/test_netstate.py >/tmp/_ns.out 2>&1; then ok "state loader normalizes native+foreign formats, read-only GET, graceful fallback"; else bad "netstate"; cat /tmp/_ns.out; fi

step "Root-cause analysis proof (no API key)"
if "$PY" webui/test_rca.py >/tmp/_rca.out 2>&1; then ok "RCA isolates a fault chain from read-only state (honest, no false correlation)"; else bad "rca"; cat /tmp/_rca.out; fi

step "Continuous assurance proof (no API key)"
if "$PY" webui/test_assurance.py >/tmp/_as.out 2>&1; then ok "assurance: SLO catalog + honest drift (alert-only, House Rule 6)"; else bad "assurance"; cat /tmp/_as.out; fi

step "Pipeline integrity proof (stage -> subagent -> skill, no API key)"
if "$PY" webui/test_agents.py >/tmp/_ag.out 2>&1; then ok "every stage wired to a real subagent+skill; routing matches; slash commands present"; else bad "pipeline integrity"; cat /tmp/_ag.out; fi

step "OpsRAG kernel proof (schema + bootstrap + oracle, no Docker)"
if "$PY" webui/test_opsrag.py >/tmp/_or.out 2>&1; then ok "opsrag schema + bootstrap from memory + oracle loop"; else bad "opsrag"; cat /tmp/_or.out; fi

step "OpsRAG typed ingestion proof (Phase 3 foundation, no API key)"
if "$PY" webui/test_ingest.py >/tmp/_ing.out 2>&1; then ok "ingest extractors (CLI + RFC -> typed nodes, idempotent merge)"; else bad "opsrag ingest"; cat /tmp/_ing.out; fi

step "OpsRAG evaluator proof (RAGAs-shape + executability + diagnostic accuracy)"
if "$PY" webui/test_evaluator.py >/tmp/_ev.out 2>&1; then ok "evaluator scores benchmark; opsrag beats naive floor"; else bad "opsrag evaluator"; cat /tmp/_ev.out; fi

step "Phase 4 LLM synthesiser + Dense-RAG baseline proof (no API key)"
if "$PY" webui/test_llm_synthesizer.py >/tmp/_llm.out 2>&1; then ok "llm_sut fallback + dense_rag BM25 retrieval + response parser (42 checks)"; else bad "llm synthesiser"; cat /tmp/_llm.out; fi

step "Phase 5 dual-signal feedback loop proof (execution-gated vs user-gated ablation)"
if "$PY" webui/test_feedback.py >/tmp/_fb.out 2>&1; then ok "exec-gated coherence 1.0 vs user-gated 0.146 under popularity bias (53 checks)"; else bad "feedback loop"; cat /tmp/_fb.out; fi

step "Worked-example reader proof (path-jailed, no API key)"
if "$PY" webui/test_examples.py >/tmp/_ex.out 2>&1; then ok "examples reader lists+serves, traversal refused"; else bad "examples reader"; cat /tmp/_ex.out; fi

step "MCP servers (stdio JSON-RPC)"
if bash wrath/mcp/test_servers.sh >/tmp/_mcp.out 2>&1; then ok "wrath-standards + wrath-netstate ($(grep -c PASS /tmp/_mcp.out) checks)"; else bad "mcp servers"; cat /tmp/_mcp.out; fi

step "Worked-example configs pass the audit gate"
for cfg in deliverables/example-acme-sp/03-config-pe1.cfg deliverables/example-acme-sp/03b-config-pe3.cfg; do
  if "$PY" .claude/skills/config-audit/scripts/config_lint.py "$cfg" >/tmp/_cfg.out 2>&1; then ok "$(basename "$cfg") (no CRITICAL/HIGH)"; else bad "$(basename "$cfg") — $(grep -E '^\[' /tmp/_cfg.out | head -3)"; fi
done
if "$PY" .claude/skills/config-audit/scripts/config_lint.py deliverables/example-dc-evpn/03-config-leaf1.cfg --vendor nxos >/tmp/_cfg.out 2>&1; then ok "03-config-leaf1.cfg EVPN-VXLAN (no CRITICAL/HIGH)"; else bad "03-config-leaf1.cfg — $(grep -E '^\[' /tmp/_cfg.out | head -3)"; fi

step "Skills + MCP servers present"
sk=$(find .claude/skills -name SKILL.md | wc -l); mc=$(ls wrath/mcp/*_server.py 2>/dev/null | wc -l)
[ "$sk" -ge 15 ] && ok "$sk skills" || bad "only $sk skills"
[ "$mc" -eq 2 ]  && ok "$mc MCP servers" || bad "expected 2 MCP servers, found $mc"

echo
if [ "$fail" -eq 0 ]; then echo "ALL GREEN"; else echo "FAILURES ABOVE"; fi
exit $fail
