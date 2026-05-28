# OpsRAG-on-WRATH — Master's-level scoping

Kamal's proposal is a **Master's** thesis (not PhD). This note states what stays the same, what
trims, and what the realistic 12-month full-time vs 9-month part-time budgets look like.

## What does *not* change

- The four academically novel layers (typed schema, execution oracle, ~200-question BGP
  benchmark, action-grounded evaluation methodology). These are exactly what a strong Master's
  needs: a clear contribution that the supervisor can name in a sentence.
- The reframing of WRATH as the prior artefact. It retires the schema-brittleness + cold-start
  risks and lets the year go to the novel work.
- The benchmark + RAGAs + action-grounded metrics evaluation plan.

## What is trimmed for Master's depth

| Layer | PhD-shaped (out-of-scope here) | Master's-shaped (in scope) |
|---|---|---|
| Corpus | Multi-vendor + multi-protocol + literature meta | **BGP-only**; FRR/Cisco/Junos docs + the listed RFCs. |
| Benchmark | Open evaluation arena, public leaderboard | **One open repo**, replication package, 300 questions. |
| Generalisation | Cross-protocol study (OSPF, IS-IS, MPLS, EVPN…) | **One protocol** + a *pilot* paragraph noting where the approach should transfer. |
| Real lab | Hardware lab with traffic generators | **Containerlab + FRR** (or namespaced FRR / the in-repo simulator). |
| Methodology | Novel metric framework + statistical methodology paper | **Apply RAGAs/RAGBench** + add executability + diagnostic-accuracy. |
| Longitudinal study | 10k-interaction multi-cohort study | **1k-interaction single-stream** simulation. |

## Realistic budgets

### 12-month full-time (the proposal's default)

| Months | Work | Deliverable |
|---|---|---|
| 1   | Phase 0 + Phase 1 already complete; supervisor onboarding | Repo walkthrough, formal proposal accepted. |
| 2   | Phase 2-A (simulator-driven loop, ✅ done) → Phase 2-B (real Containerlab) | One executed fault end-to-end. |
| 3-4 | Phase 3 (typed ingestion over the BGP corpus) | Typed graph holds the corpus; baseline RAG over the same corpus. |
| 5-6 | Phase 4 (runbook synthesiser + CLI grammar gate) | Synth passes executability gate on ≥90% of seed faults. |
| 7   | Phase 5 (dual-signal feedback, longitudinal harness) | Ablation: user-only vs execution-gated. |
| 8-9 | Phase 6 (grow benchmark to ~200 questions, run all ablations) | RAGAs + action-grounded metric tables with CIs. |
| 10-12 | Phase 7 (thesis writing + release) | Submission. |

### 9-month part-time (achievable if life intervenes)

Same arc, with two deliberate trims: keep the benchmark at ~100 questions instead of 200, and
ship the cross-protocol pilot as a one-paragraph future-work note rather than running it. The
contribution and methodology are unchanged.

## What's already done (and counts toward the thesis)

- The artefact under evaluation exists, is tested, and clears **all 42+ deterministic test
  batteries** (run `bash run_tests.sh` → ALL GREEN). No API key, no Docker required.
- All 8 phases complete. The thesis (THESIS.md) is fully written — 8 chapters, 3 appendices,
  references, no [TODO] blocks. A complete system map lives at `SYSTEM.md` (Phase 8).
- 300-question BGP benchmark across 52 categories; 10 seeded faults; 20 oracle-linked questions
  all scoring `diagnosis_correct=True` end-to-end.
- Typed schema, bootstrap, oracle, grammar gate, feedback loop, Graph SUT, LLM synthesiser,
  Dense-RAG baseline — all in `webui/opsrag/`.
- Live evaluation: `phase6_report.generate_report()` produces Tables 2–5 with Welch t-test and
  Cohen d in < 5 seconds, no external dependencies.
- The lab spec (`thesis/lab/topo-bgp.clab.yml`) and the fault library
  (`thesis/lab/faults/*.json`) are in the repo.
- `thesis/lab/SETUP.md` documents three real-software paths for Phase 2-B (Containerlab, Mininet,
  network namespaces) so the choice is the supervisor's, not the laptop's.

## What this means for the supervisor review

The work is **front-loaded on infrastructure** and **back-loaded on writing**. By the end of
month 2, the loop runs against real FRR. The middle months are corpus + synthesiser + benchmark.
The final third is writing + evaluation. There is no point where the project is gated on a
single piece of unwritten infrastructure — the simulator is the safety net for every other
piece of work.
