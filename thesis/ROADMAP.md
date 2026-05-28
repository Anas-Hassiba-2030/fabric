# OpsRAG-on-WRATH — phased roadmap (where we are, where we're going)

The thesis is design science: the artefact is what's evaluated. WRATH is that artefact; OpsRAG is the
formalisation + executable-sandbox layer the thesis adds on top. Each phase produces a concrete
deliverable that the next phase relies on; nothing depends on hand-waving.

Legend:  ✅ done · 🟡 in progress · ⬜ next · 🔭 later

---

## Phase 0 — Foundation: WRATH ✅ DONE
The working artefact (no thesis-blocking gaps): 16 specialist subagents, 15 skills, 3 hooks,
2 read-only MCP servers, slash commands, anti-hallucination grounding + clarify-gate + Validator gate +
Trust report + Memory RAG + self-improving (git-committed) pattern library + RCA + Assurance + Compliance
+ Audience reframing + Headless CLI (`--require-confidence` gate) + Share/Export/SVG/PNG + Examples
viewer + Pipeline-integrity proof. **42 deterministic test checks ALL GREEN.**

_Why this phase counts toward the thesis:_ it disproves the straw-man baseline ("generic RAG hallucinates,
emits prose, can't be re-grounded") with running code that the supervisor can run today.

---

## Phase 1 — OpsRAG kernel ✅ DONE
Lift WRATH's working memory into a formally typed graph, define the sandbox + fault library, and
deliver an end-to-end loop that runs without Docker so the rest of the work can be wired and tested.

**Built (this turn):**
- ✅ Typed schema (`webui/opsrag/schema.py`): 6 node types + 5 edge types + provenance/confidence/authored.
- ✅ Bootstrap (`webui/opsrag/bootstrap.py`): lifts existing `wrath/memory/patterns` + `customers/` into typed nodes (validates green).
- ✅ Oracle harness (`webui/opsrag/oracle.py`): same return contract for real Containerlab and deterministic simulator; oracle-loop test green (correct runbook → diagnosed; wrong → not).
- ✅ Lab spec (`thesis/lab/topo-bgp.clab.yml`) + initial fault library (3 BGP faults).
- ✅ BGP corpus list (`thesis/corpus.md`), all RFC URLs grounded.
- ✅ `webui/test_opsrag.py` proves schema, bootstrap, oracle; wired into `run_tests.sh` + `doctor`.

**Output:** the typed graph bootstrapped from real memory + the testable execution loop + the sandbox
plan + the reframed abstract for the proposal.

---

## Phase 2-A — Simulator-driven action-grounded loop ✅ DONE
Same loop, no Docker host required, so the rest of the thesis is not blocked.
- ✅ `webui/opsrag/sim.py` — deterministic mini-FRR with `baseline_state()` + `apply_fault()` +
  `exec_cmd()`. Reproduces the three seeded faults (wrong remote-as, MTU mismatch, TCP-MD5
  mismatch) with realistic FRR-like stdout.
- ✅ `webui/opsrag/synthesizer.py` — baseline runbook synthesiser: symptom → discovery commands →
  signal match → typed runbook with `concluded_root_cause`. The LLM-driven version replaces only
  the inference step in Phase 4; the contract stays.
- ✅ `webui/opsrag/oracle.py` — runs the runbook against the simulated state, returns
  `{executable, evidence_hit, diagnosis_correct, command_outputs}`. Diagnosis match is exact-after-
  normalisation OR ≥70% key-token overlap (tolerates phrasing drift from an LLM synth).
- ✅ `webui/test_opsrag.py` extended: the full sim → synth → oracle loop closes on **every** seeded
  fault; a non-diagnostic runbook is honestly rejected. **32 deterministic checks ALL GREEN.**

## Phase 2-B — Real Containerlab + FRR validation ⬜ NEXT (one-day job on a Docker host)
- Deploy `topo-bgp.clab.yml`; verify all three FRR nodes start, OSPF underlay + iBGP RR work in the clean state.
- Inject each of the three seeded faults via the patch in `inject`; confirm symptom appears.
- Run the WRATH troubleshooter against the live sandbox (the netstate MCP source is swapped from
  static snapshot to a `containerlab inspect` adapter, via `WRATH_NETSTATE_URL`).
- Assert oracle returns the **same** `{executable, diagnosis_correct}` as the simulator on each
  fault. Any disagreement is a `sim.py` bug to fix, not a research result.
- See `thesis/lab/SETUP.md` for three concrete real-software paths (Containerlab, Mininet,
  Linux network namespaces) — promotion target is whichever the host supports.

**Exit criterion:** every seeded fault scores identically on `_real_execute` and `_simulate`. The
action-grounded loop is then proven on real software, and the simulator becomes the cheap
oracle for the benchmark sweep (Phase 6).

---

## Phase 3 — Typed ingestion over BGP corpus 🟡 IN PROGRESS
**Built (this push):**
- ✅ `webui/opsrag/ingest.py` — CLI extractor (FRR/IOS/Junos `show` + `router bgp` → typed
  `Command` + `Configuration` nodes) + RFC extractor (normative prose → `Concept` + `RootCause`
  candidates) + link inferer (verifies / depends_on edges).
- ✅ Idempotent merge into `Graph`; learned nodes flagged `authored=false` to distinguish them
  from curated artefacts.
- ✅ `webui/test_ingest.py` — 16 checks proving the contract holds.

**Still to do:** sweep the actual RFC PDFs + FRR/Cisco/Junos docs into the graph, ship a
**dense-RAG baseline** comparator (same generator over flat chunks), and report the first paired
benchmark v1 metrics.

**Exit criterion:** the typed graph holds the BGP corpus; baseline RAG runs over the same corpus; first
benchmark v1 (50+ questions, paired metric distributions) reported.

---

## Phase 3.5 — Benchmark + evaluator scaffold ✅ DONE (this push)
The academically novel evaluation methodology, built once and reused by every later experiment.
- ✅ `thesis/benchmark/schema.json` — formal contract every benchmark question follows.
- ✅ `thesis/benchmark/q001-q070.json` — **70 grounded BGP questions** across 14 categories
  (session-establishment, security, mtu-path, rr-reflector, address-family, communities,
  graceful-restart, ADD-PATH, BFD, RPKI, EVPN, VPNv4, BGP-LS, operational, …). Every question
  cites a real RFC; 7 are oracle-executable.
- ✅ `webui/opsrag/evaluator.py` — RAGAs-shape metrics (answer_relevance, faithfulness,
  context_relevance) **plus** the OpsRAG contribution: `executability` (every emitted command is
  syntactically valid) and `diagnostic_accuracy` (sim+oracle scores the runbook). Headline +
  per-category + per-difficulty buckets.
- ✅ Reference SUTs: `naive_sut` (the floor — echoes the question) and `opsrag_sut` (the
  Phase-2A deterministic synth). The contract `sut(question) → {answer, retrieved_context,
  commands}` is what Phase 4's LLM synth and the dense-RAG comparator will both plug into.
- ✅ `webui/test_evaluator.py` — 24 checks proving the harness produces every metric column,
  buckets total to n, and the OpsRAG SUT beats the naive floor (current headline:
  **executability_rate 0.986**, **diagnostic_accuracy 1.0** on the fault-linked subset).
- ✅ OpsRAG Lab UI got an "Evaluation" tab — run either SUT against the live benchmark and
  see the headline + per-category breakdown in one click.

---

## Phase 4 — LLM synthesiser + dense-RAG baseline 🟡 IN PROGRESS

**Built (this push):**
- ✅ `webui/opsrag/llm_synthesizer.py` — LLM-driven SUT: typed-graph retrieval (BM25-ranked keyword
  match, top-6 nodes) → structured prompt (system rules + grounded context) → Anthropic API call
  → response parser (ANSWER + COMMANDS sections). Graceful fallback to deterministic synth when no
  API key. Same `sut(question) → {answer, retrieved_context, commands}` contract.
- ✅ `webui/opsrag/dense_rag.py` — Dense-RAG comparator: BM25 over flat 500-char overlapping chunks
  from the same corpus (patterns + faults + typed graph nodes). Deterministic generation (top-chunk
  text + extracted show commands). This is the ablation baseline that isolates the typed-graph
  contribution from the LLM contribution.
- ✅ `webui/test_llm_synthesizer.py` — **42 checks ALL GREEN** covering BM25 primitives, SUT
  contract, response parser, fallback path, prompt builder, evaluator integration.
- ✅ `app.py` `/api/opsrag/evaluate` now accepts `?sut=naive|opsrag|llm|dense` — all four SUTs
  available from the Evaluation tab with one click.
- ✅ UI: four evaluation buttons in the OpsRAG Lab → Evaluation tab (Naive floor / OpsRAG
  deterministic / Dense-RAG BM25 / LLM Opus 4.7).

**Still to do:**
- Wire `ANTHROPIC_API_KEY` in a session and run a live LLM sweep to get the first Phase 4 metric row.
- CLI grammar gate (syntactic command validation before emission) — deterministic, no LLM.
- Retrieval upgrade: dense embedding retrieval (Phase 6 swap-in).

**Exit criterion:** LLM SUT passes the executability gate on ≥90% of the seed fault library (already
green on the deterministic path; next step is a live API run with the key set).

---

## Phase 5 — Dual-signal feedback loop ✅ DONE

**Built (this push):**
- ✅ `webui/opsrag/feedback.py` — execution-gated vs user-gated graph admission:
  - `InteractionRecord` — typed log of one query-response-feedback event.
  - `execution_gated_admit()` — admits Runbook node to graph ONLY if oracle returned
    `diagnosis_correct=True`. Idempotent; marks admitted nodes `authored=False`.
  - `user_gated_admit()` — admits if user accepted (baseline; vulnerable to popularity bias).
  - `uniform_stream()` + `popularity_bias_stream()` — deterministic, seeded query generators.
  - `run_longitudinal_study()` — replays N interactions, logs snapshots every STEP queries
    (graph size, coherence, retrieval accuracy).
  - `ablation()` — runs both strategies on the same stream, returns delta table.
  - `format_ablation_table()` — plain-text table for the thesis appendix.
- ✅ `webui/test_feedback.py` — **53 checks ALL GREEN** including the key thesis claim:
  ```
  exec-gated coherence: 1.000 (never admits a wrong runbook)
  user-gated coherence: 0.146 (admits popular-but-wrong runbooks)
  Δ coherence:         +0.854  ← the ablation result that goes in the thesis table
  ```
- ✅ `/api/opsrag/ablation?n=200&mode=bias|uniform` endpoint in `app.py`.
- ✅ OpsRAG Lab → **Phase 5 Ablation** tab: two buttons (popularity-bias / uniform stream)
  render the ablation table + coherence comparison in the UI.

**Exit criterion MET:** ablation confirms execution-gated dominates user-gated under
popularity-bias drift (Δ coherence = +0.854 over 200-interaction simulation).

---

## Phase 6 — Benchmark + evaluation ⬜
- Grow the fault library to **~200 BGP questions** across the literature-grounded categories.
- Run **RAGAs** (context relevance, faithfulness, answer relevance) + the action-grounded metrics
  (executability rate, diagnostic accuracy, mean-time-to-verified-diagnosis).
- Ablations: no-graph / no-grammar / no-oracle / user-only feedback / vendor-only corpus.
- Optional: cross-protocol pilot (OSPF or IS-IS) to support the generalisation discussion.

**Exit criterion:** paired comparisons with confidence intervals; ablation tables; release-ready
benchmark.

---

## Phase 7 — Thesis writing + release 🔭
- Thesis: introduction, related work, OpsRAG design, sandbox, evaluation, discussion (limits / threats).
- Open-source release: WRATH + the OpsRAG layer + the benchmark + the methodology note.
- Replication package.

---

## Risk register (current, mapped from Kamal's proposal)
| Risk | L / I | Status / mitigation |
|---|---|---|
| Schema brittleness | Med / High | **Partly retired** — typed schema + fallback chunked-prose path already in WRATH's recall. Phase 1 ✅. |
| Sandbox-to-real gap | Med / Med | Faults chosen to be protocol-standard not vendor-specific (Phase 2/6). |
| Feedback-loop instability | Med / High | Execution-outcome admission threshold + periodic consolidation; longitudinal study is the evaluation (Phase 5). |
| Benchmark contamination | High / Med | Compose-across-documents questions + decontaminated split reported (Phase 6). |
| Scope creep (multi-protocol / multi-vendor) | High / Med | BGP-only is fixed; cross-protocol is a *pilot*, not a deliverable (Phase 6). |

## Where we are right now
Phase 0 ✅. Phase 1 ✅. Phase 2-A ✅. Phase 3 foundation ✅. Phase 3.5 ✅. Phase 4 🟡. **Phase 5 ✅** — dual-signal feedback ablation proven (exec-gated coherence 1.000 vs user-gated 0.146). **Phase 4 🟡** —
LLM synthesiser + Dense-RAG baseline are built and tested (42 checks green). Benchmark is at **120
grounded questions** across 24 categories. The evaluator exposes all four SUTs from the OpsRAG Lab
UI and from `python -c "from opsrag import evaluator; ..."`.

Phase 2-B (real Containerlab) is gated on host availability and is not blocking the thesis.

**Running the evaluation:**
```python
from opsrag import evaluator, llm_synthesizer, dense_rag
import os, json

bm_dir = "thesis/benchmark"
# Deterministic (no API key needed):
r = evaluator.evaluate(evaluator.opsrag_sut, bm_dir)
# Dense-RAG ablation baseline:
r = evaluator.evaluate(dense_rag.dense_rag_sut, bm_dir)
# LLM-driven (requires ANTHROPIC_API_KEY):
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."
r = evaluator.evaluate(llm_synthesizer.llm_sut, bm_dir)
print(r["headline"])
```

Master's-level scope + the trim list (vs PhD-shaped work) is documented in `thesis/MASTERS.md`.
Three real-software paths to a Phase 2-B sandbox are in `thesis/lab/SETUP.md`.
