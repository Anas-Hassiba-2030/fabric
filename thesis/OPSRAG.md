# OpsRAG ↔ WRATH — positioning + extension plan

A strategic note for Kamal's thesis (*OpsRAG: A Self-Extending, Action-Grounded Retrieval-Augmented
Generation System for Network Operations*). **TL;DR:** OpsRAG is largely realised in WRATH today;
the thesis becomes the *formalisation + executable sandbox + benchmark + evaluation* layer on top of
a running, open-source artefact. That is a stronger design-science thesis than building all of it
from scratch in 12 months — and it de-risks Kamal's biggest threats up front.

---

## 1. The reframe — one paragraph Kamal can paste

> OpsRAG is realised in **WRATH** — an open-source, end-to-end network solution-architecture system
> built prior to this thesis. WRATH already implements the *structural* answers to generic RAG's three
> failure modes in network operations: typed deliverables (not flat chunks), citation- and config-grammar
> gates that block hallucinated RFC/CLI syntax, and an execution-grounded pattern library that admits
> learned artefacts only after they are accepted. The thesis contributes four novel layers on top:
> **(C1)** a formal typed knowledge-graph schema (Concept / Command / Configuration / Symptom /
> RootCause / Runbook with `verifies` / `diagnoses` / `depends-on` / `supersedes` / `contradicts`
> edges), **(C2)** an execution oracle — Containerlab + FRRouting with fault injection — against which
> generated runbooks are mechanically validated, **(C3)** an open BGP benchmark (~200 questions with
> sandbox-grounded ground truth), and **(C4)** an action-grounded evaluation methodology extending
> RAGAs/RAGBench with executability, diagnostic accuracy and time-to-verified-diagnosis. The
> reference implementation, benchmark and methodology will be released as the thesis artefacts.

This is honest, defensible, and **stronger than "I will build OpsRAG"** because the artefact is already
running and tested — the supervisor can see it on the day of the proposal review.

---

## 2. OpsRAG ↔ WRATH map (no hand-waving)

### Research Questions

| Kamal's RQ | What WRATH already provides | What the thesis adds |
|---|---|---|
| **RQ1** Typed-graph retrieval > generic chunked RAG | `webui/recall.py` + `wrath/memory/patterns/` already use *typed* memory (patterns, customer files, past runs) with provenance and network-term grounding; curated knowledge ranks above raw runs; the citation-guard blocks fabricated RFCs. | Formalise the schema (§3 below); ingest BGP corpus into it; run the **paired comparison** vs a flat-chunked dense-RAG baseline on the same generator (RAGAs metrics). |
| **RQ2** CLI-grammar-validated runbooks > free-form LLM generation | `config_lint` is the deterministic gate that already refuses ill-formed config (the validator stage). `webui/rca.py` returns a *structured* RCA (hypothesis tree → proven causal chain → fix → verify) — not prose. | Generalise from config-shaped to **runbook-shaped** structured output: a JSON/YAML runbook of typed Command nodes with parameter substitution, every command checked against a CLI grammar before emission. |
| **RQ3** Execution-outcome feedback > user-preference feedback for graph extension | `webui/distill.py` already distils **accepted** runs into reusable patterns committed to git, recalled next time. The admission signal today is "Kamal accepts." | Replace/augment the human "accept" with the **sandbox outcome** as the primary admission signal (graph edges admitted only when the runbook executed and diagnosed correctly). Keep user feedback as a ranking-only secondary signal. |
| **RQ4** Which design properties are essential vs BGP-specific | The integrity test (`webui/test_agents.py`) already pins the artefact's structural invariants. | Ablation study + the cross-protocol pilot in Kamal's plan. |

### Objectives

| OpsRAG objective | WRATH today | Thesis delta |
|---|---|---|
| **O1** Typed graph schema | Memory tree (patterns/customers/runs) carries provenance + tags but is informal. | Formal schema specification + Pydantic/JSON-Schema definition, layered over `recall.py`. |
| **O2** Technically-aware ingestion | Curated standards index in `wrath/mcp/data/standards.json`; pattern files; customer files. | Implement the *typed extractors* (CLI-aware, config-aware, RFC-aware) over a real BGP corpus; output flows into the typed graph. |
| **O3** Constrained runbook synthesis | `webui/rca.py` builds a structured RCA from the read-only state. The Validator+config_lint enforce CLI/config grammar on the design path. | Extend rca to **emit a Runbook artefact** (ordered typed Commands + params + expected verifications), grammar-validated. |
| **O4** Execution oracle | `wrath-netstate` MCP is read-only; the snapshot is static (sample-testbed). | **Containerlab + FRRouting** BGP topology (multi-AS, RR, route-server) with parameterised fault injection; new MCP tool `execute_runbook` (sandbox-only) returns structured success/failure. |
| **O5** Dual-signal feedback | Single signal today (user save → pattern + git commit). | Track both signals; gate graph admission on the execution-outcome signal; user signal ranks but does not admit. |
| **O6** Evaluation | `webui/test_*.py` (40+ deterministic proofs) + the doctor. | Add the **research evaluation harness**: RAGAs (context relevance, faithfulness, answer relevance) + the action-grounded metrics (executability rate, diagnostic accuracy under sandbox, MTVD) against a strong baseline. Release the ~200-question BGP benchmark. |
| **O7** Reflection | The IDEAS.md backlog + the run record carry the design history. | Failure-mode analysis + ablations + protocol-generalisation discussion. |

---

## 3. The formal schema (concrete, to layer over current memory)

```yaml
# nodes
Concept:        {id, name, kind: protocol|feature|metric, definition_provenance, confidence}
Command:        {id, platform, mode, syntax, params, expected_output_skeleton, provenance, confidence}
Configuration: {id, platform, scope, block, parameter_ranges, provenance, confidence}
Symptom:        {id, observable, layer: physical|link|igp|bgp|service|policy, provenance, confidence}
RootCause:      {id, name, layer, evidence_required, provenance, confidence}
Runbook:        {id, name, steps:[StepRef], diagnoses:[RootCauseRef], status: authored|learned|deprecated}
# edges (all carry: provenance, confidence, created_at, learned_or_authored)
verifies:       Command -> Concept | RootCause
diagnoses:      Runbook -> Symptom
depends_on:     Command -> Configuration | Concept
supersedes:     Artefact -> Artefact   (version_metadata)
contradicts:    Artefact <-> Artefact
```

This lives as `webui/opsrag/schema.py` (Pydantic) + a thin adapter that reads/writes against the
existing `wrath/memory/` tree, so the graph is bootstrapped from what we already have without losing it.

---

## 4. Execution oracle — exactly what to stand up

- **Containerlab topology** (`thesis/lab/topo-bgp.clab.yaml`): 4 FRRouting nodes — 2 ASes, eBGP at the edge, iBGP with a route-reflector inside one AS, a route-server.
- **Fault library** (`thesis/lab/faults/*.yaml`): misconfigured neighbour (wrong remote-as), missing route-map, AS-path mismatch, hold-timer drop, MD5 mismatch, MTU mismatch, blocked TCP/179. Each fault YAML names the injection step **and** the ground-truth diagnostic verdict.
- **Oracle interface**: a new read-only MCP tool `execute_runbook(runbook, scenario)` (next to `diagnose`/`check_drift`) launches the topo, injects the scenario's fault, runs each typed Command of the runbook, captures structured output, and returns `{executable: bool, diagnosis_correct: bool, evidence: […], commands: [{cmd, rc, output_match}]}`. The MCP itself stays read-only against any **real** device — the sandbox is a separate, ephemeral target.
- **Benchmark questions** are tuples `(symptom_description, scenario_id) → expected_root_cause`. ~200 across the fault library, ~40 per fault type.

---

## 5. Revised 12-month plan (built on WRATH, not from scratch)

| Months | Activities | Deliverables |
|---|---|---|
| **M1–M2** | Systematic literature review; formalise schema v1; map onto WRATH memory; pick BGP corpus | LR draft; `opsrag/schema.py`; corpus selection note |
| **M3–M4** | Typed ingestion extractors over BGP corpus; baseline tuned dense-RAG (same generator); benchmark v1 (100 questions) | ingestion pipeline; baseline; 100 sandbox-grounded questions |
| **M5–M6** | Containerlab/FRR sandbox; fault library; runbook synthesiser (grammar-checked); first end-to-end run | sandbox repo; fault library; synthesiser; pilot results; mid-point review |
| **M7–M8** | Dual-signal feedback (execution-gated admission); longitudinal study harness; benchmark to 200 | feedback subsystem; longitudinal logs |
| **M9–M10** | Full RAGAs + action-grounded evaluation; ablations (no graph / no grammar / no oracle / user-only feedback); cross-protocol pilot (OSPF or IS-IS) | evaluation results; ablation tables |
| **M11–M12** | Thesis writing; revision; submission | thesis + replication package + open benchmark release |

The reduced risk: M3–M4 standing up the *engine* is mostly done already; the academic novelty (M5–M10)
gets the time it deserves.

---

## 6. Why this is the right strategic answer for Kamal — in his terms

- His **abstract** is unchanged; only the implementation framing improves.
- His **C1–C5 contributions** all survive — and become more credible because the implementation is real and the schema/sandbox/benchmark/evaluation are the *additional* novel work, not the whole project.
- His **risk register** shrinks: schema-brittleness is partly retired (typed + fallback proven in WRATH); benchmark-contamination is mitigated by the sandbox-grounded ground truth; scope-creep is bounded because the surrounding system already exists.
- The **CV story** is stronger: "shipped WRATH (open-source operational solution-architecture system) + designed and evaluated OpsRAG as its self-extending execution-grounded extension" beats "proposed OpsRAG."

---

## 7. Action items (immediate)

1. **Send Kamal the reframed abstract** (§1 above).
2. **Decide BGP corpus** for ingestion (Cisco BGP design guide + RFCs 4271/4456/4760/5065/7606/8212 — all real, all in our standards index).
3. Spin up a **Containerlab/FRR proof-of-concept** with the *misconfigured neighbour* fault — one fault, one runbook, one verified diagnosis. The MVP of the execution oracle. The rest of the thesis grows from this.
4. Layer `opsrag/schema.py` over `recall.py` — bootstraps the graph from existing memory in a day.

If Kamal agrees with this framing, the thesis becomes execution + writing, not invention. That is the
disciplined way to ship a thesis on schedule.
