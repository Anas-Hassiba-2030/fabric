# OpsRAG (on WRATH) — brief for Kamal

> A paste-ready introduction for the proposal review. Pairs with the abstract in `OPSRAG.md` §1 and
> the phased plan in `ROADMAP.md`.

## In one paragraph
OpsRAG is realised in **WRATH**, an open-source, end-to-end network solution-architecture system that
is already running, tested, and demonstrably grounded. WRATH solves the *structural* failure modes of
generic RAG in operational domains — typed deliverables rather than flat chunks, a citation-guard that
blocks fabricated RFCs, a deterministic config-grammar gate that refuses unvalidated configuration, a
read-only Memory-RAG with provenance, an execution-grounded pattern library that admits learned
artefacts only after they are accepted, and a structured root-cause engine that returns a *proven*
causal chain rather than prose. The thesis adds four academically novel layers on top of this
artefact: **(1)** a formal typed knowledge-graph schema; **(2)** an execution oracle built on
Containerlab + FRRouting that runs generated runbooks against a virtual BGP topology with injected
faults; **(3)** an open ~200-question BGP benchmark with sandbox-grounded ground truth; **(4)** an
action-grounded evaluation methodology extending RAGAs / RAGBench with executability and diagnostic
accuracy. Phase 1 (the typed schema, the lifted graph, the sandbox spec, the initial fault library,
the deterministic oracle harness) is **complete and tested** in the repository; Phase 2 stands up
the sandbox and delivers the first end-to-end action-grounded loop. The thesis becomes execution and
writing, not invention.

## Why this framing — short
- We **already disprove generic RAG's failure modes in network operations** with a running artefact,
  so the related-work motivation isn't an argument from the literature, it's an artefact the supervisor
  can run on the day of the review.
- The four extensions above are the work that is **genuinely novel** and that's where the year goes —
  a sandbox-validated benchmark and a typed-graph + execution-feedback design that the literature
  consistently aspires to but stops short of.
- Risk register shrinks: schema brittleness, scope creep, and a long ingestion bring-up are largely
  retired by the existing artefact. What's left is the academically interesting part.

## What's in the repo today (Phase 1)
- `thesis/OPSRAG.md` — full positioning: RQ1-4 / O1-7 ↔ WRATH map + the formal schema + sandbox plan
  + revised 12-month timeline.
- `thesis/ROADMAP.md` — phases with done/in-progress/next status.
- `thesis/corpus.md` — curated BGP corpus (RFCs 4271 / 4456 / 4760 / 5065 / 5082 / 7606 / 7911 / 8212 /
  9234 + Cisco / Junos / FRR docs), every URL grounded.
- `thesis/lab/topo-bgp.clab.yml` — minimal Containerlab topology (R1 RR + R2 PE in AS 65001, R3 customer
  in AS 65010, FRRouting).
- `thesis/lab/faults/*.json` — three real faults seeded (wrong remote-as, MTU mismatch, TCP-MD5
  mismatch) — the start of the ~200-question benchmark.
- `webui/opsrag/` — the kernel: `schema.py` (typed graph) + `bootstrap.py` (lifts WRATH memory into
  typed nodes) + `oracle.py` (Containerlab-aware harness; runs deterministically without Docker today,
  same return contract for Phase 2).
- `webui/test_opsrag.py` — proof: schema validates, bootstrap produces typed nodes from real memory,
  the oracle loop is correct (a correct runbook is diagnosed; a wrong one is not). Wired into the
  consolidated test suite + `doctor`.

## What's next (Phase 2, ~1 day on a Docker host)
Deploy the Containerlab topology, inject `f-bgp-wrong-remote-as`, run the WRATH troubleshooter against
the live sandbox, and have the oracle return `{executable: true, diagnosis_correct: true}` end-to-end.
That single demo is the thesis's centre of gravity — *a generated runbook that actually executes
against a virtual network and proves itself.*

## Where the CV and the thesis meet
Kamal's CV currently leads with: "Network / Solution Architect, CCIE #17453, SP & R&S." With this
thesis the story becomes: *"…also shipped WRATH (open-source operational solution-architecture system)
and designed and evaluated **OpsRAG**, an action-grounded retrieval-augmented system for network
operations, with an open benchmark and a Containerlab/FRRouting execution oracle."* That reads as the
practitioner-researcher trajectory the thesis is supposed to demonstrate.
