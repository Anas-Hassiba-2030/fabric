# FABRIC — Roadmap to a real, zero-hallucination system

## Honest status (read first)
FABRIC exists in three forms, not equally "real":
- **Demo mode** (default web UI): pipeline animation + **2 real gates** (`config_lint` validator, citation-guard).
  The design prose is **canned placeholder** — it is *not* real engineering, it's a faithful mockup of the flow.
- **Live mode** (needs `ANTHROPIC_API_KEY`): real Claude designs each stage = real building, but **not yet fully
  grounded**, so it can still make mistakes. This roadmap hardens it.
- **Inside Claude Code** (the 16 real agents): fully real, already working (design → Critic → revise proven).

**Principle for zero hallucination:** a claim ships only if it is (a) grounded in a real source,
(b) passed a deterministic gate, or (c) explicitly marked *unverified — needs a human*. No invented
RFCs, SKUs, or numbers.

---

## Phase 1 — Make Live mode real + grounded  ✅ DONE
**Goal:** in Live mode FABRIC genuinely designs, and nothing ships unverified.
**Build:**
- Each stage uses its **real agent definition + skill** (loaded from the repo) as the system prompt — the
  actual specialist, not a stub.
- Outputs piped through the gates *inside the run*: HLD → **Critic** (must clear), Config → **config_lint**
  (must PASS), every RFC/standard → **standards check** (verify or BLOCK).
- UI: each deliverable gets a badge — `✓ grounded / gate-passed` or `⚠ needs verification` — and shows which check ran.
**Kills hallucination:** every claim is verified or visibly flagged; a fabricated RFC is blocked (already proven).
**Done when:** a Live run yields a real design where every factual claim is verified or flagged.

## Phase 2 — Real chaining + reject→revise loops  ✅ DONE
**Goal:** stages build on each other; gates have teeth.
**Build:** HLD→LLD→Config pass real context forward; a Critic/Validator **FAIL visibly routes back** and the
stage re-runs on screen (the design→critique→revise loop, live).
**Done when:** a failing config is sent back, fixed, and re-passes — visibly.

## Phase 3 — Provenance + compounding memory
**Goal:** every claim traceable; the system learns.
**Build:** deliverables cite sources (RFC links, customer conventions); each finished run is saved to memory
(`fabric/memory/customers` + `patterns`) and reused next time.
**Done when:** a claim links to its source; a second run reuses the first's conventions.

## Phase 4 — Agile, smooth, modern UX
**Goal:** the polish.
**Build:** smoother animations/transitions, responsive layout, export deliverables (PDF/Markdown), copy/share a
run, loading + error states, keyboard nav.
**Done when:** it feels like a premium product on any screen size.

## Phase 5 — Productionize (later)
Auth, save/load runs, deploy beyond localhost, multi-user.

---

## How we work
- I build one phase at a time, commit to the PR; you `git pull` + test on your machine.
- **Live-mode testing needs your `ANTHROPIC_API_KEY`.** I can build the logic here but can't fully test Live
  without a key — you verify on your side. Demo mode and the gates I can test fully.
