---
name: fabric
title: "FABRIC — The Network Solution Architect's Operating Brain"
subtitle: "Federated Architecture Brain for Reasoning, Integration & Connectivity"
owner: "Kamal Hassiba — Network / Solution Architect (CCIE #17453, SP & R&S)"
version: "1.0 — Charter"
description: >
  A Claude-native agent system that turns Claude Code / Claude Desktop into a
  full solution-architecture engine for a senior network architect. It is built
  on real Anthropic primitives — subagents, hooks, MCP servers, and skills — and
  organized around the Solution Fabric: a reasoning GRAPH (not a linear workflow)
  that decomposes a network problem, routes it across specialist subagents, and
  converges on a validated, customer-ready solution. Use this protocol whenever
  you need to design, validate, automate, migrate, troubleshoot, scope, price, or
  present a network solution.
---

# FABRIC

### Federated Architecture Brain for Reasoning, Integration & Connectivity

> H-Nerve gave Hourani Group a *workflow studio* — linear chains: trigger → condition → action.
> FABRIC gives a Solution Architect something a level above that: a **Solution Fabric** — a
> living reasoning graph where the path to the answer is *discovered*, not pre-wired. The
> nodes are specialist agents. The links are formed at runtime, per problem. That is the
> difference between *automating a known process* and *solving an unknown one* — and solution
> architecture is the second thing.

---

## 0. The one idea everything hangs on

A **workflow** is a railway: the track is laid in advance, the train only goes where the rails go. Perfect for "every config gets linted," "every Friday email the report." Repetitive, deterministic, known.

A **Solution Fabric** is a road network with a driver. A problem enters. An **Orchestrator** reads it, decides which specialists to wake, lets them call each other, sends scouts back when evidence is thin, branches when there are two viable designs, and converges only when a validated answer exists. The route is *computed live* and is different for every problem.

```
            ┌─────────────────────────── THE SOLUTION FABRIC ───────────────────────────┐
            │                                                                            │
 problem ──▶ │   ORCHESTRATOR  ──decompose──▶  builds a graph of the right specialists   │
            │        │                                                                   │
            │        ├─▶ Discovery ──▶ Designer(HLD) ──▶ Designer(LLD) ──▶ Config Eng.   │
            │        │        ▲             │                  │              │          │
            │        │        └──need more──┘            Standards check   Validator     │
            │        │                                        │              │           │
            │        ├─▶ Risk/Assurance ◀───────────── Migration Planner ◀───┘           │
            │        │                                                                    │
            │        └─▶ CRITIC (red-team) ──reject──▶ back to the weak node              │
            │                       │ accept                                              │
            │                       ▼                                                     │
            │            BoM ▸ SoW ▸ Exec Brief ▸ Adoption Plan ──▶ deliverable           │
            └────────────────────────────────────────────────────────────────────────────┘
```

FABRIC contains **both** layers and they interlock:

| Layer | What it is | Use it for | In FABRIC |
|---|---|---|---|
| **Workflow rail** | Deterministic, pre-wired steps (the H-Nerve idea) | Repetitive guardrails: lint every config, review every design, archive every project | Implemented as **Hooks** (§4) |
| **Solution Fabric** | Dynamic reasoning graph of subagents | Novel problems: design this network, migrate that core, find this fault | Implemented as **Subagents + Orchestrator** (§2–3) |

The rule that decides which to use (straight from agent design): *use a workflow when the steps are known in advance; use the Fabric when the path depends on what you discover along the way.*

---

## 1. Architecture at a glance

```
fabric/
├── ORCHESTRATOR.md          ← the conductor (system prompt + routing logic)
├── agents/                  ← the specialist subagents (§2)
│   ├── discovery.md
│   ├── designer-hld.md
│   ├── designer-lld.md
│   ├── config-engineer.md
│   ├── validator.md
│   ├── migration-planner.md
│   ├── troubleshooter.md
│   ├── standards-officer.md
│   ├── bom-commercials.md
│   ├── sow-writer.md
│   ├── exec-storyteller.md
│   ├── adoption-success.md
│   ├── assurance-architect.md
│   ├── multivendor-translator.md
│   ├── librarian.md          ← memory keeper
│   └── critic.md             ← adversarial reviewer (run fresh)
├── skills/                  ← reusable procedures any agent can load (§3)
│   ├── hld-generator/
│   ├── lld-generator/
│   ├── config-generator/    (references: ios-xr.md, ios-xe.md, nxos.md, junos.md)
│   ├── config-audit/
│   ├── migration-runbook/
│   ├── rca-playbook/
│   ├── bom-builder/
│   ├── sow-writer/
│   ├── exec-deck/
│   ├── adoption-plan/
│   ├── telemetry-design/
│   ├── standards-checker/
│   ├── topology-diagram/
│   └── requirements-intake/
├── hooks/                   ← the workflow rail: event-fired guards (§4)
├── mcp/                     ← external connections (§5)
└── memory/                  ← episodic + semantic store (§6)
```

**Model tiers** (mix for cost + quality, no quality loss if the split is right):

| Tier | Model | Runs |
|---|---|---|
| Heavy | Opus 4.7 | Orchestrator, HLD design, RCA reasoning, Critic |
| Workhorse | Sonnet 4.6 | Config generation, LLD, SoW, BoM, most steps |
| Fast | Haiku 4.5 | Intent routing, config-lint triage, classification |

### 1.1 House rules — the principles every agent obeys

These are the system-wide behavioral rules, baked into the Orchestrator and inherited by every subagent. They are what make FABRIC trustworthy enough to put in front of a customer:

1. **Trade-offs, never a single answer.** Any design names the options and says why this one — an architect's value is the *reasoning*, not the verdict.
2. **No config ships unvalidated.** Every config/script passes the Validator before it is presented, no exceptions (enforced by hook).
3. **Brownfield always has a rollback.** If the solution touches a live network, a per-step rollback exists or the work is not done.
4. **Claims are grounded.** RFC/CVD/standard references are verified, never invented (enforced by hook).
5. **Security is designed in, not bolted on.** Every design carries a security posture from the HLD stage.
6. **The irreversible needs a human.** Pushing to a device, sending to a customer, submitting a change — Kamal confirms, the agent never acts alone.
7. **Honest about confidence.** Where data is thin, FABRIC says so and asks, rather than fabricating certainty.
8. **Compounding memory.** Every closed engagement teaches the system; nothing is solved twice from scratch.

### 1.2 How Kamal actually talks to it

No menus, no node-dragging. He states the problem in plain language and the Orchestrator builds the graph:

> *"Design an SR-MPLS core for a 3-DC service provider, multi-vendor, give me the HLD, a BoM, and a one-pager for the CTO."*

FABRIC routes Discovery → HLD → Critic → BoM → Exec Storyteller, and returns the package. He reviews, says "tighten the failover story and re-cost with redundant route reflectors," and the relevant nodes re-fire. It is a conversation with a senior team, not a form.

---

## 2. The Subagents — the specialists

Each subagent is an **isolated context window** with one mission. Critical rule from agent design: **subagents return summaries, not raw dumps** — the Orchestrator's window is precious. Each spec below gives: *Mission · Inputs · Outputs · Tools · When the Orchestrator routes here · Tier.*

### 2.0 ORCHESTRATOR — the conductor *(not a specialist; the brain)*
- **Mission:** Read the incoming problem, decompose it into subgoals, build the Solution Fabric (which agents, in what order, with what dependencies), route work, detect loops and premature stops, and synthesize the final deliverable.
- **Inputs:** Raw problem (RFP, email thread, "design me X", a fault report, a pricing ask).
- **Outputs:** A live plan/graph + the final assembled solution package.
- **Defends against the five failure modes:** hard step cap; repeated-call detection; "are we actually done?" completion check; goal restated every N steps; truncates oversized agent returns.
- **Tier:** Opus 4.7.

### 2.1 Discovery & Requirements agent
- **Mission:** Turn messy customer input into a structured, gap-free requirements brief. Asks the *right* clarifying questions instead of guessing.
- **Inputs:** RFP/RFI, call notes, email chains, existing topology dumps.
- **Outputs:** Requirements brief (business drivers, constraints, scale, SLAs, existing estate, success criteria, open questions).
- **Tools:** `requirements-intake` skill, docs MCP, memory (past projects for this customer).
- **Routed when:** Any new engagement, or when the Orchestrator detects the problem statement is underspecified.
- **Tier:** Sonnet.

### 2.2 Solution Designer — HLD
- **Mission:** Produce the High-Level Design: target architecture, technology selection with explicit trade-offs (e.g. SR-MPLS vs SRv6 vs legacy LDP/RSVP; EVPN vs traditional L2VPN; SD-WAN overlay vs DIY), the **security architecture** designed in from the start (segmentation, zero-trust posture, MACsec/encryption, control-plane protection — not bolted on later), and a reference topology.
- **Inputs:** Requirements brief.
- **Outputs:** HLD doc + topology diagram + a *decision log* (why this, why not that).
- **Tools:** `hld-generator`, `topology-diagram`, `standards-checker`, web search (feature/EoL/roadmap), memory.
- **Routed when:** Requirements are locked and a design is needed.
- **Tier:** Opus (this is the heavy reasoning node).

### 2.3 Detailed Designer — LLD
- **Mission:** Convert HLD into an implementable Low-Level Design: addressing plan, routing/IGP/BGP design, SR-SID/label plan, interface maps, naming, QoS, security zones.
- **Outputs:** LLD doc, per-device design tables, IPAM sheet.
- **Tools:** `lld-generator`, `topology-diagram`, memory (reuse customer conventions).
- **Routed when:** HLD approved (by the Critic and/or Kamal).
- **Tier:** Sonnet.

### 2.4 Config Engineer & Automation
- **Mission:** Generate device configuration and the automation to deploy it — multi-vendor (IOS-XR, IOS-XE, NX-OS, Junos), plus Python/Ansible (NETCONF/YANG, RESTCONF, pyATS) where Kamal automates.
- **Outputs:** Config files per device + an automation package (playbooks/scripts) + a dry-run/test plan.
- **Tools:** `config-generator` (+ per-vendor references), Git MCP, filesystem.
- **Hard rule:** Output is **never** considered final until the Validator (§2.5) passes it — enforced by a hook (§4).
- **Routed when:** LLD is approved.
- **Tier:** Sonnet.

### 2.5 Validator / Config Auditor
- **Mission:** Adversarially review configs and automation for errors, security gaps, idempotency, drift risk, and best-practice violations *before anything touches a device*.
- **Outputs:** Pass/Fail + an annotated defect list with severities and fixes.
- **Tools:** `config-audit` skill, standards MCP.
- **Routed when:** Any config or script is produced (also fired automatically by the pre-write hook).
- **Tier:** Sonnet (Haiku for first-pass triage).

### 2.6 Migration Planner
- **Mission:** Build the cutover plan for brownfield change — phased migration, maintenance windows, **rollback at every step**, blast-radius analysis, pre/post validation tests. (This is Kamal's signature: complex zero/low-downtime migrations.)
- **Outputs:** Migration runbook + rollback runbook + risk register + go/no-go checklist.
- **Tools:** `migration-runbook`, ticketing MCP (change records), memory.
- **Routed when:** The solution touches an existing live network.
- **Tier:** Opus (high-stakes reasoning) → Sonnet for the document.

### 2.7 Troubleshooter / RCA
- **Mission:** Given symptoms, logs, and `show` outputs, run structured root-cause analysis — hypothesis tree, evidence gathering, isolation, fix + verification.
- **Outputs:** RCA report (timeline, root cause, contributing factors, fix, prevention).
- **Tools:** `rca-playbook`, network-state MCP (read-only show/telemetry), web search (bug/advisory lookup).
- **Routed when:** The problem is "it's broken / it's slow / it flaps," not "design me X."
- **Tier:** Opus (ReAct-heavy reasoning).

### 2.8 Standards & Compliance Officer
- **Mission:** Keep every design and config honest against RFCs, Cisco Validated Designs (CVDs), vendor docs, and the customer's own security baseline (NIST/CIS/PCI as relevant). **No hallucinated RFC numbers** — claims are grounded in the docs MCP or web search.
- **Outputs:** Compliance matrix (requirement → standard → met/not-met → evidence link).
- **Tools:** `standards-checker`, docs MCP, web search.
- **Routed when:** Any design or config exists, and before any deliverable is finalized (citation hook).
- **Tier:** Sonnet.

### 2.9 BoM & Commercials
- **Mission:** Size the solution and build the Bill of Materials — hardware, licenses (e.g. smart licensing tiers), optics, support, and a defensible margin-aware pricing narrative.
- **Outputs:** BoM sheet + sizing rationale + commercial summary.
- **Tools:** `bom-builder`, web search (current SKUs/EoL), memory (past deal structures).
- **Routed when:** A solution needs to be quoted or scoped commercially.
- **Tier:** Sonnet.

### 2.10 SoW & Proposal Writer
- **Mission:** Produce the Statement of Work and project plan — scope, deliverables, assumptions, exclusions, RACI, timeline, acceptance criteria. (Directly Kamal's scoping/SoW strength.)
- **Outputs:** SoW document + project plan + acceptance test plan.
- **Tools:** `sow-writer`, docx skill (formatted deliverable), memory (reusable SoW clauses).
- **Routed when:** Moving from solution to engagement.
- **Tier:** Sonnet.

### 2.11 Executive Storyteller
- **Mission:** Translate the technical solution into a C-level narrative — business outcomes, risk reduction, TCO, and a clean deck. (Kamal's "executive communication" lever.)
- **Outputs:** Executive summary + slide outline (or pptx via the skill) + the three-sentence "why this matters" line.
- **Tools:** `exec-deck`, pptx skill.
- **Routed when:** A stakeholder presentation is needed.
- **Tier:** Sonnet (Opus for the framing if the deal is large/contested).

### 2.12 Adoption & Customer Success
- **Mission:** Build adoption plans, ATX/Accelerator session outlines, and value-realization tracking — close the gap between *delivered* and *adopted*. (Kamal's current CSS role.)
- **Outputs:** Adoption plan (barriers → actions → owners → milestones), session agendas, value scorecard.
- **Tools:** `adoption-plan`, memory.
- **Routed when:** Post-design / post-delivery, or when the ask is about driving usage and outcomes.
- **Tier:** Sonnet.

### 2.13 Assurance Architect
- **Mission:** Design the observability and service-assurance layer — model-driven telemetry (gNMI/gRPC), KPIs, SLA/SLO definitions, alerting, closed-loop remediation hooks. (Echoes Kamal's first-of-its-kind STC Telco Cloud assurance work.)
- **Outputs:** Assurance design + telemetry subscription plan + SLO catalog.
- **Tools:** `telemetry-design`, standards MCP.
- **Routed when:** The solution must be operable and measurable, not just built.
- **Tier:** Sonnet.

### 2.14 Multi-Vendor Translator
- **Mission:** Translate a design or config between vendors — Cisco ⇄ Juniper ⇄ Nokia ⇄ Arista — preserving intent and flagging where a feature has no clean equivalent. (Kamal's multi-vendor estate experience.)
- **Outputs:** Translated config + a "lossy translation" warning list.
- **Tools:** `config-generator` references, validator.
- **Routed when:** A heterogeneous estate is in play.
- **Tier:** Sonnet.

### 2.15 Librarian — memory keeper
- **Mission:** Maintain FABRIC's memory: customer profiles, past designs, reusable patterns, lessons learned, "what we tried that failed." Retrieves the right past context at the start of every engagement and writes the new project back at the end.
- **Outputs:** Retrieved context packets (on demand) + archived project records (on close).
- **Tools:** memory store (§6), filesystem, Git.
- **Routed when:** Session start (retrieve) and project close (archive) — also fired by hooks.
- **Tier:** Haiku/Sonnet.

### 2.16 Critic — the red team
- **Mission:** Adversarially review *any* deliverable before it ships — find the flaw, the unstated assumption, the failure mode, the thing that breaks at 3am. Run as a **fresh agent with no shared context**, because an agent grading its own homework is too kind (a known weakness of self-critique).
- **Outputs:** Critique with severity, or "no significant issues."
- **Routed when:** Before HLD approval, before config ships, before any customer-facing document is finalized (post-design hook).
- **Tier:** Opus.

---

## 3. The Skills — the reusable procedures

Skills are the "how-to" each agent loads when it needs to *do a thing the same good way every time*. Each is a folder with a `SKILL.md` (frontmatter `name` + a deliberately "pushy" `description` so it actually triggers) and optional `references/`, `scripts/`, `assets/`. Three-level loading: metadata always in context → SKILL.md body when triggered → bundled references only as needed.

| Skill | What it does | Key references / scripts / assets |
|---|---|---|
| `requirements-intake` | Structured capture from RFP/notes/email into a gap-free brief; generates the clarifying-question set | `assets/brief-template.md` |
| `hld-generator` | Drives an HLD: requirements → tech-selection trade-off table → reference topology → decision log | `references/tech-tradeoffs.md` |
| `lld-generator` | HLD → LLD: addressing, routing, SR/label plan, naming, QoS, security zones | `assets/ipam-template.csv` |
| `config-generator` | Vendor-correct config from LLD; idempotent, commented | `references/{ios-xr,ios-xe,nxos,junos}.md` |
| `config-audit` | Lint + security + best-practice + idempotency review; pass/fail with fixes | `scripts/lint.py` (rule-based pre-pass) |
| `migration-runbook` | Phased cutover + per-step rollback + pre/post tests + go/no-go | `assets/runbook-template.md` |
| `rca-playbook` | Hypothesis tree → evidence → isolation → fix → verify → prevent | `references/symptom-patterns.md` |
| `bom-builder` | Sizing + BoM + license tiering + commercial summary | `assets/bom-template.xlsx` |
| `sow-writer` | SoW + project plan + acceptance criteria from a solution package | `assets/sow-template.docx`, `references/reusable-clauses.md` |
| `exec-deck` | Technical solution → C-level narrative + slide outline / pptx | `assets/deck-skeleton.pptx` |
| `adoption-plan` | Barriers → actions → owners → milestones + ATX session agendas | `assets/adoption-template.md` |
| `telemetry-design` | Model-driven telemetry plan, KPI/SLO catalog, closed-loop hooks | `references/gnmi-paths.md` |
| `standards-checker` | Build a compliance matrix against RFC/CVD/security baseline, evidence-linked | `references/standards-index.md` |
| `topology-diagram` | Generate network diagrams (Mermaid first, draw.io export optional) | `scripts/to_mermaid.py` |

> Authoring note: keep each `SKILL.md` body under ~500 lines; push depth into `references/` and let the agent pull only the file it needs (e.g. only `junos.md` for a Juniper job). Put deterministic, repeatable bits in `scripts/` so they run without burning reasoning tokens — e.g. the config linter's syntactic pass is a Python script, the *judgment* is the agent.

---

## 4. The Hooks — the workflow rail (deterministic guardrails)

Hooks are the **workflow layer** done right: known, repetitive guards fired on events, so the human never has to remember them and the Fabric can't skip them. These are genuine Claude Code hooks (event → script/agent).

| Hook | Fires on | Does | Why |
|---|---|---|---|
| **session-start** | Session begins | Librarian loads active customer context + recent designs into working memory | Never start cold; reuse history |
| **pre-write-config** | Before any config/script file is written | Run `config-audit` (script pre-pass + Validator agent) | No unvalidated config ever lands |
| **post-design-review** | After any HLD/LLD is produced | Auto-spawn the **Critic** (fresh context) before presenting to Kamal | Catch the flaw before the customer does |
| **citation-guard** | Before a standards/RFC/CVD claim is finalized | Verify against docs MCP / web search; block unsupported claims | Kill hallucinated RFC numbers |
| **destructive-action-guard** | Before "push to device," "send to customer," or "submit change" | Require explicit Kamal confirmation + show full payload | Never let an agent do the irreversible alone |
| **project-close** | Engagement marked done | Librarian archives design + configs + lessons to memory + Git | Compounding institutional knowledge |

Failure-mode defenses (loop caps, repeated-call detection, completion checks, goal-restatement) live in the Orchestrator, not as hooks — they're reasoning guards, not event guards.

---

## 5. MCP & infrastructure — the connections

What FABRIC plugs into. Honest status so nothing oversells:

| Connection | Purpose | Status |
|---|---|---|
| **Filesystem** | Local design/config repository (the working estate) | Ready — native |
| **Git MCP** | Version every design, config, runbook; diff/blame/history | Ready — standard connector |
| **Web search** | EoL/EoS dates, PSIRT advisories, latest feature/roadmap, vendor docs | Ready — native |
| **Diagramming** | Topology rendering | Ready via Mermaid; draw.io export = small build |
| **Docs / Standards MCP** | Grounded RFC / CVD / vendor-doc lookup for the Standards Officer | **Needs building** — wrap a docs index (or lean on web search v1) |
| **Ticketing MCP** (ServiceNow / Jira) | Pull RFCs/incidents, write change records, link SoW to delivery | Connector exists — needs Kamal's org credentials |
| **Network-state MCP** (read-only) | Live `show`/telemetry/inventory from NetBox / CMDB / pyATS testbed | **Needs building** — biggest custom piece; do read-only first, never write |
| **docx / pptx / xlsx generation** | Formatted SoW, exec decks, BoM sheets | Ready — native document skills |

> Safety posture: any MCP that can *change* the network is gated behind the `destructive-action-guard` hook and is **read-only by default**. The network-state MCP ships read-only; write access is a separate, later, deliberately-hard decision.

---

## 6. Memory — three layers

Don't conflate them (a classic agent mistake):

| Layer | Lifetime | Holds | Where |
|---|---|---|---|
| **Working** | This conversation | The current problem + intermediate findings | The live context window |
| **Episodic** | Across sessions, per customer | This customer's estate, conventions, history, past decisions, lessons | Vector store / per-customer files, retrieved by the Librarian |
| **Semantic** | Across all work | Reusable patterns, design templates, vendor knowledge, Kamal's own playbook | Knowledge base / the `skills` references |

The Librarian owns episodic + semantic; the Orchestrator owns working memory. Episodic is what makes FABRIC feel like *Kamal's* brain and not a generic assistant — by the tenth engagement it knows how he designs.

---

## 7. A worked trace — the Fabric in motion

**Problem in:** *"Customer wants to migrate ~200 PE routers from legacy LDP/RSVP MPLS to SR-MPLS with sub-second traffic impact, multi-vendor core (IOS-XR + Junos). They need it scoped, designed, and a board-ready business case in two weeks."*

```
Orchestrator decomposes → builds this graph (not a line):

  Discovery ──▶ Designer-HLD ──▶ Standards Officer (parallel check)
                    │
                    ├──▶ Critic  ──(reject: "no SR-TE fallback story")──▶ back to HLD
                    │
                    └──(accept)──▶ Designer-LLD ──▶ Config Engineer ──▶ Validator
                                        │                                   │
                          Multi-Vendor Translator (Junos) ───────────────▶ │
                                                                            ▼
                                       Migration Planner (200-node phased + rollback)
                                                  │
                                   ┌──────────────┼───────────────┐
                                   ▼              ▼               ▼
                              Assurance       BoM/Commercials   SoW Writer
                                   └──────────────┬───────────────┘
                                                  ▼
                                        Exec Storyteller (board case)
                                                  ▼
                                   Critic (final pass) ──▶ deliverable package
```

Notice: HLD got sent back once (the Critic found a gap), Standards ran in parallel, the Junos translation looped through the Validator, and three commercial agents fanned out at once. **A workflow could not have done that** — it would have marched straight off the rails the moment the Critic said "no."

**Out:** an HLD + LLD, validated multi-vendor configs, a 200-node migration runbook with rollback, an assurance/telemetry design, a BoM, a SoW, and a board-ready business case — assembled, cross-checked, and traceable.

---

## 8. Build order (how Kamal actually stands this up)

You don't build all 16 agents on day one. Sequence for fastest value:

1. **Skeleton:** Orchestrator + Discovery + Designer-HLD + Critic + filesystem/Git. → You can already design + get it red-teamed.
2. **Make it real:** Designer-LLD + Config Engineer + Validator + the pre-write & post-design hooks. → Now it produces validated, implementable output.
3. **Make it sellable:** BoM + SoW + Exec Storyteller + docx/pptx/xlsx skills. → Now it produces customer deliverables.
4. **Make it operable:** Migration Planner + Assurance + Troubleshooter. → Now it handles brownfield and run.
5. **Make it scale:** Librarian + episodic memory + Standards/Ticketing/Network-state MCPs + Multi-Vendor + Adoption. → Now it compounds and connects to his world.

Each phase is shippable on its own. Phase 1 is a weekend.

---

## 9. What is real vs. what needs building (no overselling)

- **Real Anthropic primitives, available now:** subagents, hooks, MCP, skills, the model tiers. The orchestration patterns here are standard and supported.
- **Available connectors:** filesystem, Git, web search, document generation, and (with his org's credentials) ticketing.
- **Custom builds required:** the Docs/Standards MCP and especially the read-only Network-state MCP. These are the two pieces that turn FABRIC from "very good reasoning assistant" into "plugged into the live estate." Worth doing — but be honest in any pitch that they're the build, not the given.

That honesty is the same discipline that makes the H-Nerve story credible: name exactly which layer each capability lives in.

---

*FABRIC v1.0 — Charter. Alternate names if you want options: MERIDIAN, KEYSTONE, NORTHSTAR. Lead with FABRIC — it is the only one that means both "network fabric" and "the fabric of reasoning," which is the whole idea.*
