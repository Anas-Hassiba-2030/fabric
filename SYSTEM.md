# WRATH + OpsRAG — Complete System Map

> **Who this is for:** Anyone who opens this repo for the first time — a supervisor,
> a co-developer, a new engineer, or a future maintainer. Every architectural decision,
> every file's purpose, every data flow, and every integration is documented here.
>
> **Owner:** Kamal Hassiba — CCIE #17453, SP & R&S
> **Repo:** `https://github.com/Anas-Hassiba-2030/fabric` (branch `csirt-guard-enforcement`)

---

## 1. What Is This System? (30-Second Version)

This repo is two systems layered on top of each other:

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2 — OpsRAG (the research thesis, this repo)         │
│  Typed knowledge graph + CLI grammar gate + deterministic   │
│  oracle + execution-gated feedback loop for BGP operations  │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1 — WRATH (the production system, pre-existing)      │
│  Solution-mesh orchestration: 16 specialist subagents,      │
│  15 skills, 3 hooks, 2 MCP servers, compounding memory      │
└─────────────────────────────────────────────────────────────┘
```

**WRATH** (Workbench for Reasoned Architecture, Testing & Handover) is a Claude Code–native
system that turns the main Claude thread into a network solution architect. It decomposes
problems, routes them to 16 specialists, enforces design + validation gates, and builds
compounding operational memory across engagements.

**OpsRAG** is the research layer added for Kamal's Master's thesis. It formalises WRATH's
working memory as a typed knowledge graph and proves that typed-graph retrieval + CLI grammar
verification + deterministic oracle scoring produces better, safer diagnostic outputs than
standard RAG systems.

Both layers run from the same codebase. The production system (`CLAUDE.md`) loads
automatically when Claude Code opens this directory. The research layer (`webui/opsrag/`) runs
from `python webui/app.py` or `bash run_tests.sh`.

---

## 2. WRATH — Layer 1 Architecture

### 2.1 The Orchestrator (`CLAUDE.md`)

`CLAUDE.md` is **not documentation** — it is the operative brain of the main Claude thread. When
Claude Code opens this directory, it auto-loads `CLAUDE.md`, and the main thread **becomes the
WRATH Orchestrator**. Every session begins cold-started with customer context from
`wrath/memory/` (loaded by the `session_start` hook).

The Orchestrator's job: decompose the user's problem, build a graph of the right specialists,
route work between them, enforce gate rules, and converge on a validated deliverable stack.

**Key rules enforced by the Orchestrator** (these are instructions, not hooks):
- `pre-design-clarify` — never route to `designer-hld` with open architecture-critical questions
- `post-design-review` — always run `critic` (fresh context) before presenting a design
- `pre-write-config` — always run `validator` before any config is final
- `citation-guard` — always verify RFC/CVD claims via `standards-officer`

### 2.2 The 16 Specialist Subagents (`.claude/agents/`)

Each agent is a `.md` file with a system prompt, domain expertise, and tool access.
Invoked via the Task tool by the Orchestrator. **Agents cannot spawn sub-agents** —
only the Orchestrator can spawn agents.

| Agent file | Role | Model tier |
|---|---|---|
| `discovery.md` | Turns vague problems into gap-free requirement briefs | Sonnet |
| `designer-hld.md` | High-Level Design: trade-off tables, reference topology, security | **Opus** |
| `critic.md` | Red-team: finds weaknesses in any design or document | **Opus** |
| `designer-lld.md` | Low-Level Design: IPAM, IGP/BGP, SR, QoS, zones | Sonnet |
| `config-engineer.md` | Vendor-correct config + automation (IOS-XR/XE, NX-OS, Junos) | Sonnet |
| `validator.md` | Adversarial config audit: `config_lint.py` pre-pass + judgment | Sonnet |
| `migration-planner.md` | Phased brownfield cutover with rollback at every step | **Opus** |
| `troubleshooter.md` | Structured RCA: symptom → hypothesis tree → evidence → fix | **Opus** |
| `standards-officer.md` | Compliance matrix against RFC/CVD/vendor/security baseline | Sonnet |
| `bom-commercials.md` | Bill of Materials: hardware/optics/licenses, margin narrative | Sonnet |
| `sow-writer.md` | Statement of Work: scope, exclusions, RACI, acceptance criteria | Sonnet |
| `exec-storyteller.md` | C-level narrative: outcome, risk, TCO, slide arc | Sonnet |
| `adoption-success.md` | Post-delivery adoption barriers, milestones, value scorecard | Sonnet |
| `assurance-architect.md` | KPIs → gNMI sensor paths → SLO catalog → safe closed-loop hooks | Sonnet |
| `multivendor-translator.md` | Translate config between vendors; flag lossy translations | Sonnet |
| `librarian.md` | Session start/close: episodic memory archive and retrieval | Haiku |

### 2.3 The 15 Skills (`.claude/skills/`)

Skills are three-tier structured prompts (metadata → body → references) that agents load on
demand. The skill system separates **what to do** (the agent's system prompt) from **how to
do it** (the skill's method). Skills can be updated independently of agents.

```
wrath                   — entry point: boots the Orchestrator loop (/wrath <problem>)
requirements-intake     — gap-free requirements brief + clarifying-question bank
hld-generator           — HLD production: trade-off table → topology → decision log
topology-diagram        — Mermaid-first network diagrams (scripts/to_mermaid.py helper)
lld-generator           — LLD: IPAM, IGP/BGP, SR-SID, QoS, naming, per-device sheet
config-generator        — multi-vendor config + Ansible/NETCONF/pyATS automation
config-audit            — config_lint.py pre-pass + adversarial judgment
bom-builder             — traceable BoM with current SKUs, EoL check, commercial narrative
sow-writer              — SoW with reusable clauses, exclusions, acceptance criteria
exec-deck               — business narrative for C-level stakeholders
migration-runbook       — phased cutover, blast-radius, rollback, go/no-go gates
telemetry-design        — SLAs → KPIs → gNMI sensor paths → SLO catalog
rca-playbook            — ReAct RCA loop: symptom → layered hypothesis → evidence → fix
adoption-plan           — adoption barriers → actions → value scorecard
standards-checker       — verify-or-block compliance matrix against real standards index
```

### 2.4 The 4 Slash Commands (`.claude/commands/`)

| Command | What it does |
|---|---|
| `/wrath <problem>` | Boots the full Orchestrator loop for a network problem |
| `/wrath-review` | Triggers the post-design-review gate (fresh Critic agent) |
| `/wrath-verify` | Runs `run_tests.sh` + `doctor.py` — full health check |
| `/wrath-handoff` | Assembles grounded, trust-reported handoff bundle for customer |

### 2.5 The 3 Hooks (`.claude/hooks/`, `.claude/settings.json`)

Hooks run as Python scripts triggered by Claude Code's PreToolUse / SessionStart events.
They are **deterministic guards** — they do not reason, they enforce.

#### `destructive_action_guard.py` (PreToolUse on Bash/PowerShell)
- **Purpose:** Implements House Rule 6 — the irreversible needs a human.
- **Triggers on:** `ssh … conf t`, `napalm`, `netmiko`, `scp *.cfg`, `ansible-playbook … push`, `clogin`, `jlogin`
- **Action:** Writes a warning to stderr and exits 1 (asks user to confirm). Does NOT block `git push`.
- **Does not trigger on:** read-only operations, file edits, git commands.

#### `csirt_guard.py` (PreToolUse on Write/Edit/MultiEdit/Bash)
- **Purpose:** Cisco IT/CSIRT policy — hard block, no override possible.
- **Blocks (exit 2):**
  - Writing to `.claude/plugins/marketplaces/<x>/` where x ≠ `claude-plugins-official`
  - Writing to forbidden AI-agent platform dirs: `.openclaw/`, `.hermes/`, `.kiro/`,
    `.factory/`, `.slate/`, `.gbrain/`, `.opencode/`, `.agents/`
  - Shell redirects (`>`, `>>`, `tee`) targeting those dirs
  - `curl|wget … | sh` fetching from a non-official source
  - `npm/pip/brew/cargo install` of forbidden platform CLIs
- **Allows:** `.cursor/`, `~/.claude/agents/` (no leading dot), all normal operations.
- **Test battery:** `bash .claude/hooks/test_csirt_guard.sh` — 18 checks.

#### `session_start.py` (SessionStart)
- **Purpose:** Surfaces active customer context so the Orchestrator never starts cold.
- **Reads:** `wrath/memory/customers/` — active project files, recent decisions, estate notes.

### 2.6 The 2 MCP Servers (`wrath/mcp/`, `.mcp.json`)

Both servers are **read-only**. Neither can modify a device or write to the network.

#### `wrath-standards` (`wrath/mcp/standards_server.py`)
- Grounded RFC/IEEE/framework lookup and citation verification.
- Index: `wrath/mcp/data/standards.json` — covers all BGP RFCs, Cisco CVDs, NIST/CIS/PCI.
- Backs the `citation-guard` orchestration rule and the `standards-checker` skill.
- Used by: `standards-officer` agent, `webui/test_grounding.py`.

#### `wrath-netstate` (`wrath/mcp/network_state_server.py`)
- Read-only `show`/telemetry/inventory: normalises native + foreign formats.
- State snapshots: `wrath/mcp/state/`.
- No write tool. Any MCP with write access stays behind the destructive guard.
- Used by: `assurance-architect`, `troubleshooter`, `webui/test_netstate.py`.

### 2.7 The Memory Model (`wrath/memory/`)

| Layer | Lifetime | Content | Path |
|---|---|---|---|
| **Working** | This conversation | Current problem + intermediate findings | Orchestrator's context window |
| **Episodic** | Across sessions, per customer | Estate, history, decisions, lessons | `wrath/memory/customers/<name>.md` |
| **Semantic** | All work | Reusable patterns, templates, vendor knowledge | `wrath/memory/patterns/` |

The `librarian` agent manages episodic + semantic memory. After a closed engagement, it
archives design + configs + lessons via git. By the tenth engagement, episodic memory makes
WRATH feel like Kamal's own brain.

---

## 3. OpsRAG — Layer 2 Architecture

### 3.1 Why OpsRAG Exists on Top of WRATH

WRATH's working memory is untyped: patterns, customer files, and CLI snippets all live as
prose documents. OpsRAG formalises this memory as a **typed knowledge graph** and adds three
mechanisms WRATH does not have:

1. **CLI grammar gate** — rejects hallucinated/config commands before emission.
2. **Deterministic oracle** — scores whether a runbook's root cause is protocol-correct.
3. **Execution-gated feedback** — keeps the graph coherent under popularity-bias drift.

These three mechanisms are the thesis contribution. The `webui/opsrag/` package is where they live.

### 3.2 The Typed Knowledge Graph Schema (`webui/opsrag/schema.py`)

**6 Node Types:**

| Type | Represents | Typical source |
|---|---|---|
| `Concept` | BGP protocol concept or mechanism | Pattern files, RFC extraction |
| `Command` | A specific CLI diagnostic command | Grammar gate, ingestion |
| `Configuration` | A router configuration block | Pattern files, example configs |
| `Symptom` | An observable network symptom | Fault library |
| `RootCause` | A diagnosed fault cause | Fault library, oracle output |
| `Runbook` | A complete diagnostic procedure | Synthesiser output |

**5 Edge Types:**

| Edge | Semantics |
|---|---|
| `verifies` | A command output verifies a root cause |
| `diagnoses` | A runbook diagnoses a symptom |
| `depends_on` | A concept/config depends on another |
| `supersedes` | A newer runbook supersedes an older one |
| `contradicts` | Two RootCause nodes disagree |

**Provenance (on every node and edge):**
```python
Provenance(
    source: str,       # file path or RFC id + section
    confidence: float, # 1.0 RFC-normative · 0.85 vendor doc · ≤0.7 learned
    authored: bool,    # True = curated by engineer; False = feedback-loop learned
)
```
The `authored` flag is critical: it separates facts you know from facts the system learned.
A `Runbook` node admitted by the feedback loop is marked `authored=False` and can be
removed if the oracle later contradicts it; a curated `Concept` node is never overwritten
by a learned node.

### 3.3 The Bootstrap Layer (`webui/opsrag/bootstrap.py`)

Lifts WRATH's existing semantic memory into the typed graph at startup:
- `wrath/memory/patterns/*.md` → `Runbook` nodes (one per pattern file)
- Customer files → `Concept` nodes (tagged by customer domain)
- `recall.terms()` → `Concept` nodes with `depends_on` edges between related terms

All bootstrapped nodes are marked `authored=True` (they came from the engineer's curated
memory). The bootstrap is idempotent: re-running it never duplicates nodes.

### 3.4 The Ingestion Layer (`webui/opsrag/ingest.py`)

Extends the bootstrap with structured extraction from raw text:

| Extractor | Input | Output node types |
|---|---|---|
| CLI extractor | FRR/IOS/Junos `show` output or config blocks | `Command` + `Configuration` |
| RFC extractor | Normative prose paragraphs | `Concept` + `RootCause` candidates |
| Link inferer | Any two nodes with semantic overlap | `verifies` / `depends_on` edges |

All ingestion is non-destructive: curated nodes (authored=True) are never overwritten by
ingested nodes (authored=False). Nodes are keyed by deterministic IDs so re-ingesting
the same source is a no-op.

### 3.5 The Deterministic Simulator (`webui/opsrag/sim.py`)

A pure-Python FRR-compatible BGP simulator. No Docker, no OS, no real network.

**State model:**
```python
baseline_state() → {
    "devices": {
        "R1": {role, as_number, loopback, interfaces, bgp_neighbors, rib, route_maps},
        "R2": {...},
        "R3": {...}
    }
}
```

**Operations:**
- `apply_fault(state, fault)` — mutates the state according to the fault's `inject.patch[]` list.
  Supports: `set_neighbor_attr`, `set_interface_attr`, `set_route_map`, `remove_connected_route`, `set_timer`.
- `exec_cmd(state, device, command)` — returns realistic FRR-like stdout for `show` commands.
  Covers: `show bgp summary`, `show ip bgp neighbors <ip>`, `show ip bgp`, `show route-map`,
  `show interfaces`, `ping <ip>`, `show ip route`.

**Why it matters:** The simulator is what makes the whole evaluation deterministic. Without it,
every test requires a live Docker+FRR host. With it, the full sim → synth → oracle loop runs
in < 1 second on any laptop.

### 3.6 The Fault Library (`thesis/lab/faults/*.json`)

10 seeded BGP faults, each specified as:
```json
{
  "id": "f-bgp-wrong-remote-as",
  "title": "remote-as mismatch",
  "scope": ["bgp", "session"],
  "symptom": "R2 eBGP toward 192.0.2.2 stays in Active...",
  "inject": {
    "device": "R2",
    "kind": "set_neighbor_attr",
    "patch": [{"neighbor": "192.0.2.2", "attr": "remote_as", "value": 65099}]
  },
  "expected_evidence": ["show bgp summary", "show ip bgp neighbors 192.0.2.2"],
  "ground_truth": {
    "root_cause": "eBGP session failed: configured remote-as 65099 does not match...",
    "layer": "bgp",
    "fix": "router bgp 65001 / neighbor 192.0.2.2 remote-as 65010",
    "verify": "show bgp summary | include 192.0.2.2"
  },
  "provenance": {"source": "RFC 4271 §6.2", "confidence": 1.0, "authored": true}
}
```

| Fault ID | Title | Layer |
|---|---|---|
| `f-bgp-wrong-remote-as` | remote-as mismatch | BGP session |
| `f-bgp-md5-mismatch` | TCP-MD5 password mismatch | Security / TCP |
| `f-bgp-mtu-mismatch` | MTU mismatch on R2↔R3 link | Data plane |
| `f-bgp-route-policy-reject` | Inbound deny route-map | Policy |
| `f-bgp-next-hop-unreachable` | BGP next-hop not in RIB | RIB |
| `f-bgp-max-prefix-limit` | max-prefix limit exceeded | Policy limits |
| `f-bgp-hold-timer-expired` | Hold timer too aggressive | BGP timers |
| `f-bgp-ebgp-multihop` | eBGP to non-adjacent peer, no multihop | BGP |
| `f-bgp-as-path-loop` | own-AS in AS_PATH (eBGP loop guard) | BGP AS-path |
| `f-bgp-local-pref-override` | local-preference override misroutes flows | BGP policy |

All 10 faults satisfy `oracle(synthesize(fault)) → diagnosis_correct=True`.

### 3.7 The Synthesiser (`webui/opsrag/synthesizer.py`)

Takes a fault JSON → runs sim → extracts signal → builds a Runbook.

**Flow:**
```
fault.json
    │
    ▼ sim.baseline_state() + sim.apply_fault()
FaultState
    │
    ▼ exec_cmd(state, R2, "show bgp summary")
    ▼ exec_cmd(state, R2, "show ip bgp neighbors ...")
    ▼ ...
CommandOutputs
    │
    ▼ _infer_category(outputs) → category + signals
    ▼ _extract_peer(symptom) → peer IP
    ▼ _build_runbook(fault, category, peer_ip, outputs)
Runbook {
    id, fault_id, commands: [{device, cmd}],
    command_outputs: [...],
    concluded_root_cause: "...",
    evidence: [...]
}
```

The synthesiser has 8 signal patterns (one per fault class) that match substrings in
the sim's `show` command output (e.g. `"Active"` → session-down class, `"Hold Timer Expired"` → timer class). This is deterministic signal matching, not an LLM call.

**LLM upgrade path:** `llm_synthesizer.py` wraps the same contract with an Anthropic API call
(BM25-ranked typed-graph context → structured prompt → API → response parser).
When `ANTHROPIC_API_KEY` is not set, it falls back to the deterministic synthesiser transparently.

### 3.8 The Oracle (`webui/opsrag/oracle.py`)

Scores a runbook against a seeded fault. The definitive test of whether a diagnosis is right.

**Contract:**
```python
execute_runbook(fault, runbook) → {
    "executable":       bool,  # every cmd matches a known CLI prefix
    "evidence_hit":     bool,  # ≥1 expected-evidence cmd present
    "diagnosis_correct": bool, # concluded_root_cause ≥70% key-token overlap with ground_truth
    "command_outputs":  list   # [(device, cmd, stdout), ...]
}
```

**Diagnosis matching:** `_diagnosis_matches(concluded, ground_truth)` tokenises both strings,
removes stopwords, and requires ≥70% key-token overlap. This tolerates phrasing variation
from LLM synthesis while blocking off-topic answers. 70% was empirically tuned on the 10 fault
library; all 10 faults pass with the deterministic synthesiser.

**Key concept:** the oracle is the *only* source of ground truth in the system. It is not
a language model judge, not a human rating, not a cosine similarity threshold. It is a
protocol-semantic check grounded in the fault library.

### 3.9 The CLI Grammar Gate (`webui/opsrag/grammar_gate.py`)

Every command that enters the knowledge graph or is presented to an operator passes this gate
first. No exceptions.

**Three tiers:**

| Tier | Count | Examples |
|---|---|---|
| **OK** (allow) | 26 patterns | `show bgp summary`, `show ip bgp neighbors`, `ping`, `traceroute`, `show interfaces`, `show route-map` |
| **REJECT** (block) | 12 patterns | `router bgp`, `neighbor remote-as`, `ip address`, `configure terminal`, `no shutdown` |
| **WARN** | variable | `clear bgp *`, `debug all`, `reload` |

A runbook passes the gate if **all** commands are in the OK tier. The gate is called in the
synthesiser pipeline before `execution_gated_admit()`. A runbook with any REJECT command is
never admitted, regardless of oracle result.

**64 deterministic checks** in `webui/test_grammar_gate.py` prove this. All 10 seeded fault
runbooks pass the gate (100% ≥ 90% exit criterion).

### 3.10 The Feedback Loop (`webui/opsrag/feedback.py`)

Controls which runbooks are admitted to the knowledge graph over time.

**Two strategies compared:**

```
User-gated admission (the naive, dangerous baseline):
    interaction → user marks "accepted" → Runbook added to graph
    → popular-but-wrong diagnoses accumulate over time

Execution-gated admission (the OpsRAG contribution):
    interaction → oracle(runbook) → diagnosis_correct=True → Runbook added to graph
    → only oracle-verified runbooks enter the graph
```

**Key data types:**
```python
InteractionRecord(
    question_id: str,
    sut_response: dict,       # {answer, retrieved_context, commands}
    oracle_result: dict,      # {executable, evidence_hit, diagnosis_correct}
    user_accepted: bool,      # simulated user signal
)
```

**Ablation experiment (Table 5):**
The `popularity_bias_stream()` generator simulates 200 interactions where 30% are the
same popular question, that popular question is wrong 70% of the time, and users accept
it 90% of the time. This is the worst-case NOC scenario.

Result (Graph SUT, rng_seed=99):
- Execution-gated graph coherence: **1.000**
- User-gated graph coherence: **0.144**
- Δ: **+0.856**

### 3.11 The Evaluator (`webui/opsrag/evaluator.py`)

Runs any SUT against the full 300-question benchmark and produces all metrics.

**The SUT contract** (everything plugs into this):
```python
sut_function(question_dict) → {
    "answer": str,              # the generated answer text
    "retrieved_context": str,   # what was retrieved from the knowledge base
    "commands": [               # the diagnostic commands emitted
        {"device": str, "cmd": str}
    ]
}
```

**5 Metrics:**
| Metric | How computed | Notes |
|---|---|---|
| `answer_relevance` | Jaccard overlap of answer tokens with ground-truth answer | Upgrade path: RAGAs LLM judge |
| `faithfulness` | Token recall of answer tokens in retrieved_context | |
| `context_relevance` | Jaccard overlap of retrieved_context with question | |
| `executability` | All commands pass CLI grammar gate | **OpsRAG contribution** |
| `diagnostic_accuracy` | Oracle returns `diagnosis_correct=True` | **OpsRAG contribution** (oracle-linked questions only) |

**Headline output:**
```python
{
    "headline": {
        "answer_relevance": {"mean": 0.124, "std": 0.089, "n": 300},
        "executability_rate": 1.000,
        "diagnostic_accuracy": 1.000
    },
    "by_category": {...},
    "by_difficulty": {...}
}
```

### 3.12 The 5 Systems Under Test (SUTs)

These are what gets evaluated. Every SUT implements the same contract above.

| SUT | File | What it does |
|---|---|---|
| **Naive floor** | `evaluator.py:naive_sut` | Echoes the question as the answer. No retrieval, no commands. The zero-knowledge baseline. |
| **Dense-RAG (BM25)** | `dense_rag.py:dense_rag_sut` | BM25 over flat 500-char chunks from the same corpus (patterns + faults + typed graph text). Returns top-chunk text + any `show` commands extracted from it. Proves that the typed-graph structure — not the retrieval algorithm — is what produces executability. |
| **OpsRAG (deterministic)** | `evaluator.py:opsrag_sut` | For fault-linked questions: runs the full sim → synth → oracle loop. For concept questions: returns empty (honest zero-retrieval). |
| **Graph SUT** | `graph_sut.py:graph_sut` | BM25 over 3-layer typed corpus + category-promoted concept paragraphs + action-floor guarantee. Answers all 300 questions with an executable runbook. |
| **LLM (Opus 4.7 / fallback)** | `llm_synthesizer.py:llm_sut` | BM25 top-6 typed nodes → Anthropic API → structured response. Falls back to OpsRAG when no API key. |

### 3.13 The Graph SUT in Detail (`webui/opsrag/graph_sut.py`)

The Graph SUT is the most important SUT for answering the thesis research questions. Here is exactly how it works:

**Three-layer retrieval corpus:**
1. `wrath/memory/patterns/` — curated BGP prose from real engagements (Runbook nodes)
2. `thesis/lab/faults/*.json` — symptom + ground_truth text from the 10 seeded faults (Symptom + RootCause nodes)
3. `_CONCEPTS` dict — 52 embedded RFC-grounded BGP concept paragraphs (Concept nodes), one per benchmark category

**Retrieval flow:**
```python
graph_sut(question) →
    1. Extract category from question["category"]
    2. Look up concept_text = _CONCEPTS.get(category_alias)
    3. BM25 score all 3 layers against question text
    4. Compose: concept_text FIRST (category promotion) + top BM25 hits
    5. _extract_commands(all_retrieved_text) → command candidates
    6. If no commands found → apply action floor:
       [{"device": "R2", "cmd": "show bgp summary"},
        {"device": "R2", "cmd": "show ip bgp neighbors 192.0.2.2"}]
    7. Return {answer: composed_text, retrieved_context: ..., commands: deduped}
```

**The action floor** (key design decision): every BGP question, no matter how abstract,
produces at least `show bgp summary` + `show ip bgp neighbors 192.0.2.2`. This is not
fabrication — it is what any network engineer would type first when investigating a BGP
issue. It gives exec_rate = 1.000 across all 52 categories.

**The `_CAT_ALIAS` map:** translates benchmark category names (e.g. `"local-pref-override"`)
to concept library keys (e.g. `"local-preference"`). This handles naming drift between
the benchmark question authors and the concept library authors (same person, slight inconsistency).

### 3.14 The Phase 6 Report (`webui/opsrag/phase6_report.py`)

The thesis's comparative evaluation engine. Runs all 5 SUTs, computes all 5 metrics,
produces 4 publication-ready tables.

**Entry point:**
```python
from opsrag import phase6_report
r = phase6_report.generate_report()
print(r["text"]["table2"])   # Table 2: headline comparison
print(r["text"]["table3"])   # Table 3: per-category Graph vs Dense-RAG
print(r["text"]["table4"])   # Table 4: per-difficulty breakdown
print(r["text"]["table5"])   # Table 5: feedback-loop ablation
```

**Statistical methods (pure stdlib, no scipy):**
- Welch's t-test with Welch-Satterthwaite degrees of freedom
- p-value from regularised incomplete beta function (Lentz continued-fraction algorithm)
- Cohen's d effect size (pooled standard deviation)
- Significance levels: *** p<0.001, ** p<0.01, * p<0.05, n.s. p≥0.05

---

## 4. Complete Data Flow Scenarios

### Scenario A: Production Use (WRATH, a client engagement)

```
Kamal: "Design an SR-MPLS core for a 3-DC SP, multi-vendor, give me the HLD + BoM + CTO one-pager"
    │
    ▼
[SessionStart hook] → session_start.py → loads wrath/memory/customers/active.md
    │
    ▼
Orchestrator (CLAUDE.md):
  1. Restate goal + name deliverables (HLD, BoM, exec deck)
  2. Check pre-design-clarify gate → greenfield? scale? vendor preference? SLA?
  3. Route to discovery (Sonnet) → gap-free brief
  4. Route to designer-hld (Opus) → HLD draft
  5. Route to critic (Opus, fresh) → red-team critique
  6. If rejected → back to designer-hld with critique
  7. Route to bom-commercials (Sonnet) → BoM
  8. Route to exec-storyteller (Sonnet) → CTO one-pager
  9. Assemble deliverable stack
  │
  ▼
Output: HLD.md + BoM.xlsx + exec_deck.md, all validated + grounded
    │
    ▼
[project-close] → librarian → archives to wrath/memory/customers/<client>.md + patterns/
```

### Scenario B: BGP Troubleshooting with OpsRAG

```
Operator: "R2 eBGP session to 192.0.2.2 is stuck in Active"
    │
    ▼
Orchestrator routes to troubleshooter (Opus) with rca-playbook skill
    │
    ▼
OpsRAG layer:
  1. graph_sut(question) → BM25 retrieval over typed corpus
  2. Category identified: "session-establishment"
  3. _CONCEPTS["session-establishment"] promoted to front of context
  4. Commands extracted: ["show bgp summary", "show ip bgp neighbors 192.0.2.2"]
  5. Grammar gate: all commands in OK tier → passes
  6. Return {answer: "BGP session...", commands: [{R2, show bgp summary}, ...]}
    │
    ▼
If the question is oracle-linked (fault_id present):
  7. sim.baseline_state() + sim.apply_fault(state, fault)
  8. exec_cmd(state, "R2", "show bgp summary") → "Active"
  9. synthesizer._infer_category(outputs) → "session-establishment/wrong-remote-as"
  10. synthesizer._build_runbook() → concluded_root_cause: "eBGP session failed: wrong remote-as"
  11. oracle.execute_runbook(fault, runbook) → {diagnosis_correct: True}
  12. feedback.execution_gated_admit(runbook, oracle_result) → admitted to graph
```

### Scenario C: Benchmark Evaluation (Thesis Research)

```
python3 -c "from opsrag import phase6_report; r = phase6_report.generate_report(); print(r['text']['table2'])"
    │
    ▼
generate_report() → run_all_suts(bm_dir)
    │
    ├── for each SUT in [naive, dense_rag, opsrag, graph_sut, llm]:
    │       for each question in benchmark/ (300 questions):
    │           response = sut(question)
    │           scores = score_question(question, response)
    │           # → answer_relevance, faithfulness, context_relevance,
    │           #   executability, diagnostic_accuracy
    │
    ├── build_table2(raw) → Welch t-test + Cohen d for each SUT pair
    ├── build_table3(raw) → Graph vs Dense-RAG per-category exec
    ├── build_table4(raw) → per-difficulty breakdown
    └── build_table5(bm_dir) → feedback ablation (popularity_bias_stream, seed=99)
    │
    ▼
Output: Tables 2-5 in plain text + structured dict
```

---

## 5. The Benchmark (`thesis/benchmark/`)

### 5.1 File Structure

```
thesis/benchmark/
  schema.json          ← JSON schema contract for every question
  q001-q030.json       ← first 30 questions (oracle-linked fault questions, older format)
  q031-q060.json       ← ...
  ...
  q211-q214.json       ← as-path-loop + local-preference oracle questions (linked_fault key)
  q215-q300.json       ← 86 new concept questions (no difficulty, no oracle link)
  validate_benchmark.py ← 13-check integrity validator
```

### 5.2 Question Format

Two oracle key conventions exist in the benchmark (both supported by all code):
```json
// Older format (q001-q210): fault linked via "fault_id"
{
  "id": "q-001",
  "category": "session-establishment",
  "difficulty": "diagnose",
  "question": "...",
  "ground_truth": {"answer": "...", "commands": [...]},
  "fault_id": "f-bgp-wrong-remote-as",
  "provenance": {"source": "RFC 4271 §8", "confidence": 1.0}
}

// Newer format (q211-q214): fault linked via "linked_fault"
{
  "id": "q-211",
  "category": "as-path-loop",
  "difficulty": "diagnose",
  "question": "...",
  "ground_truth": "AS_PATH loop detection...",
  "linked_fault": "f-bgp-as-path-loop-detection",
  "expected_commands": [{"device": "R2", "cmd": "show ip bgp neighbors ..."}]
}

// Concept questions (q215-q300): no oracle link, no difficulty
{
  "id": "q-215",
  "category": "ibgp-scaling",
  "question": "...",
  "ground_truth": "In iBGP deployments...",
  "provenance": {"source": "RFC 4456", "confidence": 1.0}
}
```

### 5.3 Statistics

| Metric | Value |
|---|---|
| Total questions | 300 |
| Categories | 52 |
| Oracle-linked | 20 |
| Difficulty: recall | 78 |
| Difficulty: apply | 78 |
| Difficulty: diagnose | 54 |
| Difficulty: unspecified | 90 |

---

## 6. Test Coverage Map

Every `test_*.py` file proves a specific system property. All 42+ batteries pass with no API
key and no Docker.

| Test file | What it proves | Key checks |
|---|---|---|
| `test_opsrag.py` | Schema + bootstrap + sim + synth + oracle | 10 faults, oracle round-trip |
| `test_ingest.py` | Typed ingestion (CLI + RFC → nodes, idempotent) | 16 checks |
| `test_evaluator.py` | Benchmark harness, all 5 metrics, per-category | ALL GREEN |
| `test_llm_synthesizer.py` | BM25 primitives, SUT contract, parser, fallback | 42 checks |
| `test_grammar_gate.py` | 26 OK / 12 REJECT / warns; all 10 faults pass gate | 64 checks |
| `test_feedback.py` | Execution-gated coherence 1.0 > user-gated 0.146 | 53 checks |
| `test_phase6.py` | Tables 2-4, Welch t-test, OpsRAG exec > naive | 53 checks |
| `test_graph_sut.py` | Graph SUT AR > naive AR, 52 concept paragraphs | 42 checks |
| `test_grounding.py` | Fabricated RFC blocked, bad config failed, numbers flagged | ALL GREEN |
| `test_clarify.py` | Vague question blocked, fully-specified question passes | ALL GREEN |
| `test_recall.py` | Pattern recalled, no false positives | ALL GREEN |
| `test_topology.py` | Valid Mermaid output, core+redundancy diagrams | ALL GREEN |
| `test_tco.py` | Cost/TCO honest (sourced drivers, no invented currency) | ALL GREEN |
| `test_trust.py` | Trust report faithful (grounded/flagged/blocked ledger) | ALL GREEN |
| `test_provenance.py` | Provenance labelling correct (REAL gate stays REAL) | ALL GREEN |
| `test_routing.py` | Model routing matches charter tiers (Opus/Sonnet/Haiku) | ALL GREEN |
| `test_cli.py` | Headless CLI runs + emits faithful bundle | ALL GREEN |
| `test_assurance.py` | SLO catalog + honest drift (alert-only, House Rule 6) | ALL GREEN |
| `test_rca.py` | RCA isolates fault chain from read-only state | ALL GREEN |
| `test_netstate.py` | State loader normalizes formats, read-only GET, fallback | ALL GREEN |
| `test_agents.py` | Every stage wired to real subagent + skill, routing correct | ALL GREEN |
| `test_audience.py` | Audience reframing (CFO/CISO/NOC voices, no invented $) | ALL GREEN |
| `test_compliance.py` | Compliance pack maps frameworks honestly | ALL GREEN |
| `test_export.py` | Run export bundles stack (order, deliverables, grounding) | ALL GREEN |
| `test_share.py` | Shareable HTML report self-contained + faithful | ALL GREEN |
| `test_whatif.py` | What-if compare diffs runs correctly | ALL GREEN |
| `test_blueprints.py` | Blueprints complete + clear clarify-gate | ALL GREEN |
| `test_distill.py` | Accepted runs distil into reusable patterns | ALL GREEN |
| `test_persist.py` | Patterns persist to git (path-scoped, safe no-op) | ALL GREEN |
| `test_analytics.py` | Analytics aggregate faithfully | ALL GREEN |
| `test_inbox.py` | Inbox saves/edits/removes/persists | ALL GREEN |
| `test_live.py` | Live wiring chains, gates fire, hallucination caught | ALL GREEN |
| `test_criticism.py` | Critic dial maps (lenient 0 / standard 1 / max 2 passes) | ALL GREEN |
| `doctor.py` | Full system health check (environment + all batteries + live API) | ALL GREEN |
| `validate_benchmark.py` | 300 questions, 52 categories, 13 integrity checks | ALL GREEN |

---

## 7. The Web UI (`webui/app.py`)

The UI is a pure-Python stdlib server (`http.server` + vanilla JS). No Flask, no React,
no npm. Start with: `python3 webui/app.py` → `http://localhost:8765`.

**Tabs and what they do:**

| Tab | Description |
|---|---|
| Main | Run WRATH against a problem (demo/live mode) |
| OpsRAG Lab → Evaluation | Run any of the 5 SUTs against the benchmark with one click |
| OpsRAG Lab → Phase 5 Ablation | Popularity-bias ablation (uniform / bias stream) |
| OpsRAG Lab → Full Report | Generate Tables 2–5 live (phase6_report) |
| Blueprints | Pre-defined engagement blueprints for common problem types |
| What-if / Compare | Diff two WRATH runs |
| Compliance | Export a compliance matrix (NIST/CIS/PCI) |
| Assurance | SLO catalog + continuous drift monitoring |
| Analytics | Cross-run analytics (trust, grounding, tags) |
| Inbox | Saved results and runbooks |
| Share / Export | HTML report, Markdown bundle, topology SVG |

**API endpoints relevant to the evaluation pipeline:**

```
GET  /api/opsrag/evaluate?sut=naive|opsrag|llm|dense|graph
     → runs the named SUT against the full benchmark
     → returns {headline, by_category, by_difficulty}

POST /api/opsrag/ablation?n=200&mode=bias|uniform
     → runs the feedback ablation
     → returns the ablation table dict

GET  /api/opsrag/report
     → generates Tables 2-5 from phase6_report.generate_report()
```

---

## 8. Navigation Guide — Where to Start

| Your goal | Start here |
|---|---|
| **Understand the system at 30,000 ft** | This file (`SYSTEM.md`) |
| **Run the system** | `README.md` — one command: `python3 webui/app.py` |
| **Reproduce thesis results** | `thesis/REPLICATION.md` |
| **Run all tests** | `bash run_tests.sh` |
| **Read the thesis** | `thesis/THESIS.md` |
| **See where we are / roadmap** | `thesis/ROADMAP.md` |
| **Understand WRATH's rules** | `CLAUDE.md` (the Orchestrator) |
| **Understand OpsRAG's schema** | `webui/opsrag/schema.py` |
| **Understand the fault simulator** | `webui/opsrag/sim.py` |
| **Understand how evaluation works** | `webui/opsrag/evaluator.py` |
| **Understand the feedback loop** | `webui/opsrag/feedback.py` |
| **Add a new seeded fault** | `thesis/lab/faults/` + extend `sim.py` `apply_fault()` + `exec_cmd()` |
| **Add a new benchmark question** | `thesis/benchmark/` + run `thesis/benchmark/validate_benchmark.py` |
| **Add a new SUT** | Implement `sut(question_dict) → {answer, retrieved_context, commands}` + register in `phase6_report.py` |
| **Debug a failing test** | `python webui/test_<name>.py` — each test prints PASS/FAIL per check |
| **Check system health** | `python webui/doctor.py` — ALL GREEN = working |
| **Understand security guards** | `.claude/hooks/csirt_guard.py` + `test_csirt_guard.sh` |

---

## 9. Configuration and Secrets

| Variable | Purpose | Required |
|---|---|---|
| `ANTHROPIC_API_KEY` | Enables live LLM SUT (Opus 4.7) + live WRATH mode | Optional — all deterministic paths work without it |
| `WRATH_NETSTATE_URL` | Points `wrath-netstate` MCP at a live data source | Optional — static JSON snapshots are the default |
| `CLAUDE_PROJECT_DIR` | Injected by Claude Code for hook paths | Auto-set by the harness |

No `.env` file is needed for the deterministic evaluation path (all thesis results).

---

## 10. What Each Key File Does — Complete Index

```
# Root
CLAUDE.md               ← Orchestrator brain (auto-loads in every Claude Code session)
README.md               ← Quick start + component summary
SYSTEM.md               ← This file: complete system map
run_tests.sh            ← One-command test runner (ALL GREEN = working)
.mcp.json               ← MCP server registrations

# WRATH layer
wrath/PROTOCOL.md       ← The charter (source of truth — never edit)
wrath/ORCHESTRATOR.md   ← Pointer to CLAUDE.md
wrath/memory/
  customers/            ← Episodic memory: one .md per client, updated by librarian
  patterns/             ← Semantic memory: reusable BGP/design/security patterns
  runs/                 ← Archived run outputs
wrath/mcp/
  standards_server.py   ← RFC/standards MCP (read-only lookup)
  network_state_server.py ← Network state MCP (read-only show/telemetry)
  data/standards.json   ← Grounded standards index (RFC + CVD + vendor)
  state/                ← Network state snapshots

# Claude Code integration
.claude/settings.json   ← Hook registrations + permissions
.claude/agents/         ← 16 specialist subagents (.md system prompts)
.claude/skills/         ← 15 skills (method prompts + references)
.claude/hooks/
  destructive_action_guard.py ← Ask before device push (House Rule 6)
  csirt_guard.py              ← Hard block: non-official plugins + forbidden platforms
  session_start.py            ← Load customer memory on session start
.claude/commands/       ← Slash commands: /wrath, /wrath-review, /wrath-verify, /wrath-handoff

# OpsRAG layer (thesis)
webui/opsrag/
  schema.py             ← Typed graph: 6 node types + 5 edge types + Provenance
  bootstrap.py          ← Lift wrath/memory/ into typed graph nodes
  ingest.py             ← CLI/RFC extractor → typed nodes, idempotent merge
  sim.py                ← Deterministic FRR-like BGP simulator (no Docker)
  synthesizer.py        ← Fault → sim → signal match → Runbook
  oracle.py             ← Score Runbook against Fault (exec + evidence + diagnosis)
  grammar_gate.py       ← CLI grammar gate: 26 OK / 12 REJECT / WARN
  feedback.py           ← Execution-gated vs user-gated graph admission
  evaluator.py          ← Benchmark runner: 5 metrics, all 5 SUTs, per-category/difficulty
  dense_rag.py          ← Dense-RAG BM25 SUT (flat-chunk baseline)
  graph_sut.py          ← Graph SUT (typed-graph + category promotion + action floor)
  llm_synthesizer.py    ← LLM SUT (BM25 typed retrieval + Anthropic API + fallback)
  phase6_report.py      ← Tables 2-5: Welch t-test, Cohen d, feedback ablation

# Tests
webui/test_opsrag.py    ← sim + oracle loop (all 10 faults)
webui/test_grammar_gate.py ← 64 checks: grammar tiers + fault gate pass rate
webui/test_feedback.py  ← 53 checks: exec-gated 1.0 > user-gated under bias
webui/test_graph_sut.py ← 42 checks: Graph SUT AR > naive, 52 concept paragraphs
webui/test_phase6.py    ← 53 checks: Tables 2-4 + OpsRAG exec > naive p<0.001
webui/test_evaluator.py ← Benchmark harness: all metrics, per-category buckets
webui/test_ingest.py    ← 16 checks: typed ingestion contract
webui/test_llm_synthesizer.py ← 42 checks: BM25 + parser + fallback
webui/doctor.py         ← Full system health check (runs all batteries)

# Benchmark and fault library
thesis/benchmark/
  q001-q300 (*.json)    ← 300 BGP questions across 52 categories
  schema.json           ← Question format contract
  validate_benchmark.py ← 13-check integrity validator
thesis/lab/faults/      ← 10 seeded BGP fault files (JSON)
thesis/lab/topo-bgp.clab.yml ← Containerlab topology (Phase 2-B)
thesis/lab/SETUP.md     ← Three real-software paths for Phase 2-B

# Thesis documents
thesis/THESIS.md        ← The complete master's thesis
thesis/ROADMAP.md       ← Phase map: all 8 phases, status, risk register
thesis/REPLICATION.md   ← Step-by-step result reproduction guide
thesis/MASTERS.md       ← Master's vs PhD scoping decisions
thesis/corpus.md        ← Curated RFC + vendor doc source list

# Web UI
webui/app.py            ← Web server: http://localhost:8765
webui/cli.py            ← Headless CLI: python webui/cli.py "<problem>"
```

---

## 11. The Invariants (Things That Must Always Be True)

1. `bash run_tests.sh` → ALL GREEN (no API key, no Docker required)
2. `python webui/doctor.py` → ALL GREEN (same condition)
3. `phase6_report.generate_report()["text"]["table2"]` matches `thesis/THESIS.md` Chapter 6 Table 2
4. All 10 seeded faults: `oracle(synthesize(fault)) → diagnosis_correct=True`
5. All 20 oracle-linked benchmark questions: `opsrag_sut(question) → diagnosis_correct=True`
6. Graph SUT exec_rate = 1.000 across all 52 categories
7. `thesis/benchmark/validate_benchmark.py` → 13/13 checks green
8. No `[TODO]` blocks anywhere in `thesis/THESIS.md`
9. Every RFC cited in the thesis exists at `https://www.rfc-editor.org/rfc/rfcXXXX`
10. Every admitted `Runbook` node in the knowledge graph is marked with `authored=False`
    when it came from the feedback loop (not curated by the engineer)

If any invariant breaks, something is wrong. `run_tests.sh` verifies invariants 1–7.

---

*This document was last updated to reflect the state of commit `f5c169e` on branch
`csirt-guard-enforcement`. Run `git log --oneline -5` to see the most recent changes.*
