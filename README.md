# WRATH — Network Solution Architect's Operating Brain

**Workbench for Reasoned Architecture, Testing & Handover.**
A Claude-native agent system that turns Claude Code into a full solution-architecture engine for a
senior network architect. Built on real Anthropic primitives — **subagents, skills, hooks** — organized
around the **Solution Mesh**: a reasoning *graph* (not a linear workflow) that decomposes a network
problem, routes it across specialist subagents, and converges on a validated, customer-ready solution.

Owner: **Kamal Hassiba** — Network / Solution Architect (CCIE #17453, SP & R&S).

---

## How to run it

Open Claude Code in this directory. `CLAUDE.md` auto-loads, so the main thread **becomes the WRATH
Orchestrator**. Then either:

- Just **state a problem in plain language** —
  > *"Design an SR-MPLS core for a 3-DC service provider, multi-vendor, give me the HLD, a BoM, and a one-pager for the CTO."*
- …or invoke the entry skill explicitly: **`/wrath <your problem>`**.

The Orchestrator restates the goal, plans the graph, routes to specialists (via the Task tool),
runs the gate rules (Critic on every design, Validator on every config), and returns a stack of
deliverables with every open question flagged for you.

Slash commands: `/wrath <problem>` (boot the loop), `/wrath-review` (fresh-Critic gate),
`/wrath-verify` (run the suite + doctor), `/wrath-handoff` (grounded handoff bundle).

### …or use the visual console
Prefer a UI? There's a local web console that shows the pipeline running stage-by-stage and lets you
work the result:
```bash
python3 webui/app.py      # open http://localhost:8765
```
Demo mode needs zero config (and the Validator + Standards gates still run for real); set
`ANTHROPIC_API_KEY` for Live mode. Every deliverable is badged **REAL / LIVE / DEMO** so nothing looks
faked. Beyond watching the run, the console adds **Blueprints**, a **Critic-intensity dial**,
**What-if / Compare** (diff two designs), **Save pattern** (distil + git-commit a reusable pattern),
**Analytics**, **Inbox**, **Compliance** and **Assurance** packs, **audience re-voicing**
(Board/CFO/CISO/NOC), and **Share / Export** (HTML report, Markdown bundle, topology SVG). There's also
a **headless CLI** — `python webui/cli.py "<problem>"` — for CI/scripts. See `webui/README.md`.

---

## What's here

```
CLAUDE.md            ← THE ORCHESTRATOR (operative): house rules, routing, gate rules, defenses
README.md            ← this file
.claude/
  settings.json      ← hooks: destructive-action-guard + session-start
  agents/            ← 16 specialist subagents (Task-invocable)
  skills/            ← wrath, requirements-intake, hld-generator, topology-diagram, lld-generator,
                       config-generator, config-audit, bom-builder, sow-writer, exec-deck,
                       migration-runbook, telemetry-design, rca-playbook, adoption-plan, standards-checker
  hooks/             ← destructive_action_guard.py, session_start.py, csirt_guard.py
  commands/          ← slash commands: /wrath, /wrath-review, /wrath-verify, /wrath-handoff
wrath/
  ORCHESTRATOR.md    ← pointer: where the orchestrator lives (→ CLAUDE.md)
  PROTOCOL.md        ← the charter, verbatim (source of truth — do not edit)
  memory/            ← episodic (customers/) + semantic (patterns/)
  mcp/               ← read-only MCP servers: wrath-standards + wrath-netstate (registered in .mcp.json)
deliverables/        ← run outputs land here
webui/               ← the WRATH Console (stdlib web app) + headless CLI + the deterministic engine
                       modules and their tests (grounding, clarify, trust, routing, assurance, …)
.mcp.json            ← registers the WRATH MCP servers for Claude Code
run_tests.sh         ← one command: runs every deterministic check (ALL GREEN = working)
```

---

## Build status — honest, no overselling

Built per the charter's build order (`wrath/PROTOCOL.md` §8). Each phase is useful on its own.

| Phase | Theme | Components | Status |
|---|---|---|---|
| **1** | Design | Orchestrator + `discovery` + `designer-hld` + `critic`; skills `requirements-intake`, `hld-generator`, `topology-diagram`; `destructive-action-guard` + `session-start` hooks | ✅ **Operational (deep)** |
| **2** | Implement | `designer-lld` + `config-engineer` + `validator`; the gate rules that enforce validation | 🟢 Agents + skills built — `lld-generator`, `config-generator` (per-vendor refs), `config-audit` (lint pre-pass); deepen via real engagements |
| **3** | Sell | `bom-commercials` + `sow-writer` + `exec-storyteller`; docx/pptx/xlsx | 🟢 Agents + skills built — `bom-builder`, `sow-writer`, `exec-deck`; doc-format export via the generation connector |
| **4** | Operate | `migration-planner` + `assurance-architect` + `troubleshooter` | 🟢 Agents + skills built — `migration-runbook`, `telemetry-design`, `rca-playbook` |
| **5** | Scale & connect | `librarian` + episodic memory + `standards-officer` + `multivendor-translator` + `adoption-success`; Docs/Standards & read-only Network-state MCPs | 🟢 Agents + skills built — `standards-checker`, `adoption-plan`; **both MCPs built** (`wrath-standards`, read-only `wrath-netstate`) — offline-grounded now, live data source is a config swap |

**All five phases now have their skills built** — every agent has the method skill it loads, and the
config/standards paths have deterministic helpers (`config_lint.py`) and a verified standards index.
`discovery`, `designer-hld`, and `critic` remain the deepest (full worked examples); the rest grow with
real engagements. The system never pretends a component is more than it is (House Rule 7).

### What's real vs. what needs building

- **Real now:** subagents, skills, hooks, the two custom MCP servers, model tiers, the orchestration patterns — all standard Claude Code primitives.
- **Available connectors:** filesystem, Git, web search, document generation.
- **Custom builds — now built (`wrath/mcp/`):** the Docs/Standards MCP (`wrath-standards`) and the **read-only** Network-state MCP (`wrath-netstate`). These are what turn WRATH from "very good reasoning assistant" into "plugged into the live estate." They run today against a curated standards index and JSON state snapshots; pointing them at a live docs source / pyATS-gNMI-NetBox feed is a data-source swap, not a rebuild. Honest caveat: live wiring to a customer's estate still needs that estate's credentials/access — that's the remaining real-world step, not more code.

---

## Verify it

```
bash run_tests.sh        # every deterministic check; ALL GREEN = working
python webui/doctor.py   # system self-check; with ANTHROPIC_API_KEY also makes a real Opus 4.7 call
```
`run_tests.sh` runs the full battery with no API key: JSON validity, the CSIRT + destructive-action
guard hooks, the `config_lint` self-test, the MCP stdio servers, the audit gate on worked-example
configs, **and the engine proofs** — anti-hallucination grounding (a fabricated RFC is blocked), the
clarify-gate, trust report, cost/risk honesty, memory recall, what-if, blueprints, pattern distil +
git-persist, analytics, inbox, audience reframing, compliance, **continuous-assurance drift**, model
routing, provenance, the headless CLI, and a **pipeline-integrity proof** (every stage stays wired to a
real subagent + skill, routing matches each agent's tier). Safe to wire into a SessionStart hook or CI.

---

## The 8 House Rules (why it's trustworthy in front of a customer)

1. Trade-offs, never a single answer. 2. No config ships unvalidated. 3. Brownfield always has a rollback. 4. Claims are grounded (no invented RFCs). 5. Security designed in, not bolted on. 6. The irreversible needs a human. 7. Honest about confidence. 8. Compounding memory.

*WRATH drafts; the CCIE owns the final call.*
