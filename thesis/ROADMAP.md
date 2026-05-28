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

## Phase 1 — OpsRAG kernel 🟡 IN PROGRESS
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

## Phase 2 — Sandbox bring-up + first executed runbook ⬜ NEXT
On a host with Docker + Containerlab installed:
- Deploy `topo-bgp.clab.yml`; verify all three FRR nodes start, OSPF underlay + iBGP RR work in the clean state.
- Inject `f-bgp-wrong-remote-as.json`; confirm symptom appears.
- Run the WRATH troubleshooter against the live sandbox (the netstate MCP source is swapped from
  static snapshot to a `containerlab inspect` adapter, via `WRATH_NETSTATE_URL`).
- Confirm the generated runbook executes against the sandbox and the oracle returns
  `{executable: true, diagnosis_correct: true}` end-to-end on the wrong-remote-as fault.

**Exit criterion:** one fault, one runbook, one verified diagnosis — the **action-grounded loop** working
on a real virtual network. This is the thesis's "killer demo."

---

## Phase 3 — Typed ingestion over BGP corpus ⬜
- CLI-aware extractor (parses FRR/IOS/Junos `show` and `router bgp` syntax into `Command` and `Configuration` nodes).
- RFC-aware extractor (normative vs informative passages → `Concept` and `RootCause` candidates).
- Concept extractor for definitional prose.
- Strong **dense-RAG baseline** with the same generator (the "generic RAG" comparator for RQ1).

**Exit criterion:** the typed graph holds the BGP corpus; baseline RAG runs over the same corpus; first
benchmark v1 (50 questions, paired metric distributions) reported.

---

## Phase 4 — Runbook synthesiser + CLI grammar gate ⬜
- Promote `webui/rca.py` from a single-shot causal-chain emitter to a **typed runbook synthesiser**:
  retrieves a subgraph, composes an ordered list of `Command` nodes, binds parameters, validates each
  command against the platform's CLI grammar **before emission**.
- Output is the structured runbook JSON the oracle consumes; the human-readable rendering is derived.

**Exit criterion:** synthesiser passes the executability gate on ≥90% of the seed fault library.

---

## Phase 5 — Dual-signal feedback loop ⬜
- Continue the existing pattern-distil path **gated by execution outcome** instead of human "accept."
- User signal kept for ranking only (no graph admission).
- Longitudinal-study harness: replay simulated query streams; log graph size, coherence, retrieval and
  runbook accuracy trajectories.

**Exit criterion:** ablation `user-feedback-only` vs `execution-gated` shows the latter avoids
popularity-bias drift over a 1k-interaction simulation.

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
Phase 0 done. **Phase 1 essentially complete in this push** (schema + bootstrap + oracle + lab + corpus + tests).
The next concrete piece of work is Phase 2's bring-up of the Containerlab sandbox on a real Docker host
and wiring `wrath-netstate`'s loader to read from `containerlab inspect` — about a day's work once a
Docker host is available.
