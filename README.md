# FABRIC — Network Solution Architect's Operating Brain

**Federated Architecture Brain for Reasoning, Integration & Connectivity.**
A Claude-native agent system that turns Claude Code into a full solution-architecture engine for a
senior network architect. Built on real Anthropic primitives — **subagents, skills, hooks** — organized
around the **Solution Fabric**: a reasoning *graph* (not a linear workflow) that decomposes a network
problem, routes it across specialist subagents, and converges on a validated, customer-ready solution.

Owner: **Kamal Hassiba** — Network / Solution Architect (CCIE #17453, SP & R&S).

---

## How to run it

Open Claude Code in this directory. `CLAUDE.md` auto-loads, so the main thread **becomes the FABRIC
Orchestrator**. Then either:

- Just **state a problem in plain language** —
  > *"Design an SR-MPLS core for a 3-DC service provider, multi-vendor, give me the HLD, a BoM, and a one-pager for the CTO."*
- …or invoke the entry skill explicitly: **`/fabric <your problem>`**.

The Orchestrator restates the goal, plans the graph, routes to specialists (via the Task tool),
runs the gate rules (Critic on every design, Validator on every config), and returns a stack of
deliverables with every open question flagged for you.

---

## What's here

```
CLAUDE.md            ← THE ORCHESTRATOR (operative): house rules, routing, gate rules, defenses
README.md            ← this file
.claude/
  settings.json      ← hooks: destructive-action-guard + session-start
  agents/            ← 16 specialist subagents (Task-invocable)
  skills/            ← fabric, requirements-intake, hld-generator, topology-diagram, lld-generator,
                       config-generator, config-audit, bom-builder, sow-writer, exec-deck,
                       migration-runbook, telemetry-design, rca-playbook, adoption-plan, standards-checker
  hooks/             ← destructive_action_guard.py, session_start.py, csirt_guard.py
fabric/
  ORCHESTRATOR.md    ← pointer: where the orchestrator lives (→ CLAUDE.md)
  PROTOCOL.md        ← the charter, verbatim (source of truth — do not edit)
  memory/            ← episodic (customers/) + semantic (patterns/)
  mcp/               ← read-only MCP servers: fabric-standards + fabric-netstate (registered in .mcp.json)
deliverables/        ← run outputs land here
.mcp.json            ← registers the FABRIC MCP servers for Claude Code
```

---

## Build status — honest, no overselling

Built per the charter's build order (`fabric/PROTOCOL.md` §8). Each phase is useful on its own.

| Phase | Theme | Components | Status |
|---|---|---|---|
| **1** | Design | Orchestrator + `discovery` + `designer-hld` + `critic`; skills `requirements-intake`, `hld-generator`, `topology-diagram`; `destructive-action-guard` + `session-start` hooks | ✅ **Operational (deep)** |
| **2** | Implement | `designer-lld` + `config-engineer` + `validator`; the gate rules that enforce validation | 🟢 Agents + skills built — `lld-generator`, `config-generator` (per-vendor refs), `config-audit` (lint pre-pass); deepen via real engagements |
| **3** | Sell | `bom-commercials` + `sow-writer` + `exec-storyteller`; docx/pptx/xlsx | 🟢 Agents + skills built — `bom-builder`, `sow-writer`, `exec-deck`; doc-format export via the generation connector |
| **4** | Operate | `migration-planner` + `assurance-architect` + `troubleshooter` | 🟢 Agents + skills built — `migration-runbook`, `telemetry-design`, `rca-playbook` |
| **5** | Scale & connect | `librarian` + episodic memory + `standards-officer` + `multivendor-translator` + `adoption-success`; Docs/Standards & read-only Network-state MCPs | 🟢 Agents + skills built — `standards-checker`, `adoption-plan`; **both MCPs built** (`fabric-standards`, read-only `fabric-netstate`) — offline-grounded now, live data source is a config swap |

**All five phases now have their skills built** — every agent has the method skill it loads, and the
config/standards paths have deterministic helpers (`config_lint.py`) and a verified standards index.
`discovery`, `designer-hld`, and `critic` remain the deepest (full worked examples); the rest grow with
real engagements. The system never pretends a component is more than it is (House Rule 7).

### What's real vs. what needs building

- **Real now:** subagents, skills, hooks, the two custom MCP servers, model tiers, the orchestration patterns — all standard Claude Code primitives.
- **Available connectors:** filesystem, Git, web search, document generation.
- **Custom builds — now built (`fabric/mcp/`):** the Docs/Standards MCP (`fabric-standards`) and the **read-only** Network-state MCP (`fabric-netstate`). These are what turn FABRIC from "very good reasoning assistant" into "plugged into the live estate." They run today against a curated standards index and JSON state snapshots; pointing them at a live docs source / pyATS-gNMI-NetBox feed is a data-source swap, not a rebuild. Honest caveat: live wiring to a customer's estate still needs that estate's credentials/access — that's the remaining real-world step, not more code.

---

## The 8 House Rules (why it's trustworthy in front of a customer)

1. Trade-offs, never a single answer. 2. No config ships unvalidated. 3. Brownfield always has a rollback. 4. Claims are grounded (no invented RFCs). 5. Security designed in, not bolted on. 6. The irreversible needs a human. 7. Honest about confidence. 8. Compounding memory.

*FABRIC drafts; the CCIE owns the final call.*
