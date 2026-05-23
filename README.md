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
  skills/            ← fabric (entry), requirements-intake, hld-generator, topology-diagram
  hooks/             ← destructive_action_guard.py, session_start.py
fabric/
  ORCHESTRATOR.md    ← pointer: where the orchestrator lives (→ CLAUDE.md)
  PROTOCOL.md        ← the charter, verbatim (source of truth — do not edit)
  memory/            ← episodic (customers/) + semantic (patterns/)
deliverables/        ← run outputs land here
```

---

## Build status — honest, no overselling

Built per the charter's build order (`fabric/PROTOCOL.md` §8). Each phase is useful on its own.

| Phase | Theme | Components | Status |
|---|---|---|---|
| **1** | Design | Orchestrator + `discovery` + `designer-hld` + `critic`; skills `requirements-intake`, `hld-generator`, `topology-diagram`; `destructive-action-guard` + `session-start` hooks | ✅ **Operational (deep)** |
| **2** | Implement | `designer-lld` + `config-engineer` + `validator`; the gate rules that enforce validation | 🟡 Agents scaffolded to charter depth; skills (`config-generator`, `config-audit`, `lld-generator`) pending |
| **3** | Sell | `bom-commercials` + `sow-writer` + `exec-storyteller`; docx/pptx/xlsx | 🟡 Agents scaffolded; deliverable skills pending |
| **4** | Operate | `migration-planner` + `assurance-architect` + `troubleshooter` | 🟡 Agents scaffolded |
| **5** | Scale & connect | `librarian` + episodic memory + `standards-officer` + `multivendor-translator` + `adoption-success`; Docs/Standards & read-only Network-state MCPs | 🟡 Agents + memory scaffolded; custom MCPs are a future build |

**Deep / Phase-1 operational:** `discovery`, `designer-hld`, `critic` — written with full method and
worked examples. **Scaffolded to charter depth:** the other 13 agents — real and invocable, written to
the protocol's §2 spec, to be deepened as their phase lands. The system never pretends a scaffolded
component is more than it is (House Rule 7).

### What's real vs. what needs building

- **Real now:** subagents, skills, hooks, model tiers, the orchestration patterns — all standard Claude Code primitives.
- **Available connectors:** filesystem, Git, web search, document generation.
- **Custom builds (future):** the Docs/Standards MCP and the **read-only** Network-state MCP. These turn FABRIC from "very good reasoning assistant" into "plugged into the live estate." They are the build, not the given.

---

## The 8 House Rules (why it's trustworthy in front of a customer)

1. Trade-offs, never a single answer. 2. No config ships unvalidated. 3. Brownfield always has a rollback. 4. Claims are grounded (no invented RFCs). 5. Security designed in, not bolted on. 6. The irreversible needs a human. 7. Honest about confidence. 8. Compounding memory.

*FABRIC drafts; the CCIE owns the final call.*
