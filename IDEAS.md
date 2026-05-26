# Ideas & Concepts — escalating the system

A living catalog of capabilities that make the result better, more trustworthy, and more impressive.
Priority: **P0** = do next, **P1** = high value soon, **P2** = later, **★** = signature / astonishing.
Nothing here is built unless it says "DONE".

## Console / interface
- **DONE — Console redesign (modern, animated).** The orchestration pipeline is a compact **horizontal
  rail** (Orchestrator on top, phases left→right, icon cards, animated flowing connectors + red
  revise-arcs on gate bounces) instead of tall stacked card columns; the **deliverable** now owns the
  main panel. Glassmorphism, phase color-coding, running-node gradient ring, staged entrance, mermaid
  topology rendering (CDN, graceful fallback). Verified via headless Chromium screenshots.
- **DONE — Expand-to-fullscreen.** Both the Deliverable and Live-activity panels have an **⤢ EXPAND**
  button that opens the full content in a large modal (Esc / click-outside / ✕ to close); the
  deliverable view re-renders the topology diagram. Verified via headless screenshots.

## Quality & trust (least hallucination, best output)
- **DONE (P0) — Clarifying-questions gate.** Before designing, Discovery asks the *right* missing
  questions (scale, SLA, brownfield/greenfield, platform/version) instead of assuming. Deterministic
  gate `webui/clarify.py` (mirrored in the `requirements-intake` skill bank), enforced as the
  `pre-design-clarify` orchestration rule, surfaced in the Discovery stage, proven by
  `webui/test_clarify.py`. Biggest single quality lever.
- **DONE (P1) — Assumptions ledger + confidence/trust report.** The run ends with a scorecard —
  grounded / flagged / blocked counts, a verify-before-ship ledger, and a confidence level
  (High/Medium/Guarded) that never exceeds the evidence. Unanswered clarify-gate dimensions flow in
  as tracked assumptions (P0→P1 tie-in). `webui/trust.py`, surfaced as a `trust` pipeline stage,
  saved into the run record, proven by `webui/test_trust.py`.
- **P1 — Provenance everywhere** (DONE for citations): every factual claim links to its source or is
  marked unverified. Extend to SKUs (vendor EoL pages) and CVDs.
- **P2 — Adjustable red-team intensity.** A "Critic aggressiveness" dial; optional second adversarial pass.
- **★ Self-improving pattern library.** Every *accepted* design auto-distills a reusable pattern into
  memory (`wrath/memory/patterns`), so the system compounds and gets better with each engagement.

## Smarter orchestration
- **P1 — Multi-model routing.** Opus 4.7 for heavy reasoning (HLD, Critic, RCA); Sonnet/Haiku for cheap
  stages (formatting, BoM tables) — better cost/speed without losing quality. (Engine default already Opus 4.7.)
- **DONE — What-if / compare designs.** `⤳ What-if` re-runs with one changed constraint and
  auto-opens a side-by-side **diff** of the two stacks; `⇄ Compare` picks any two saved runs.
  Per-stage changed/same/only badges + line deltas + trust/grounding metric comparison.
  `webui/whatif.py` + `/api/compare`, proven by `webui/test_whatif.py`; UI verified via screenshots.
- **DONE — Memory RAG.** At run start, Discovery recalls the most relevant prior knowledge —
  patterns (semantic), customer files (episodic), and past saved runs — by network-term overlap and
  cites them (curated knowledge ranked first; no false positives). `webui/recall.py`, surfaced atop
  the Discovery stage + saved into the run record, proven by `webui/test_recall.py`. (House Rule 8.)

## Richer deliverables
- **DONE (P1) — Auto topology diagram.** Every HLD now embeds an inferred reference topology
  (Mermaid, inline): redundant core, leaf-spine for DC problems vs dual-homed PE sites otherwise,
  failure domains as subgraphs. `webui/topology.py` (reuses the skill's `to_mermaid.py`, which was
  hardened to emit Mermaid-valid subgraph ids), proven by `webui/test_topology.py`. _SVG/PNG export
  still open._
- **DONE — Export the deliverable stack.** A whole run (recalled memory + every stage in order with
  grounding verdicts + trust report) bundles to one Markdown document via `webui/export_run.py` and
  `GET /api/export?id=`, proven by `webui/test_export.py`. _XLSX/PPTX/DOCX still open (needs deps)._
- **DONE (P1) — Cost/TCO + risk register.** A `Cost & Risk` stage generates capex/opex TCO drivers
  (each naming its figure source: BoM/SoW/quote/customer) and a design-adaptive risk register
  (likelihood/impact/mitigation/owner) — with **no invented currency** (House Rule 4). `webui/tco.py`,
  proven by `webui/test_tco.py` (asserts no fabricated `$`).
- **P2 — Audience reframing.** One toggle to re-voice the exec summary for CFO / CISO / NOC.
- **P2 — Compliance pack.** NIST/CIS/PCI matrix as a standalone signed report.

## Plugged into the real estate (the big differentiators)
- **P2 — Read-only Network-state MCP → live.** Point it at pyATS/gNMI/NetBox so RCA & validation use
  *real* device state (server already exists; today it reads JSON snapshots).
- **P2 — Docs/Standards MCP → live fetch** with caching when egress allows (today: curated index).
- **P2 — Ticketing/Git integration.** Pull RFCs/incidents (ServiceNow/Jira), version every deliverable in Git.
- **★ Continuous assurance.** After a design, auto-generate the telemetry/SLO config + a watcher that
  re-validates the live network against the design and alerts on drift.

## Workflow & reach
- **P1 — Shareable read-only run links** + one-click PDF of the whole stack.
- **P2 — CLI / API mode** so runs can be triggered from CI or scripts (headless WRATH).
- **DONE — Engagement blueprints.** `⊞ Blueprints` opens a gallery of ready-to-run starters (SP core,
  DC fabric, DCI, campus, secure edge, SD-WAN); clicking one loads + runs it. Each is complete enough
  to clear the clarify-gate. `webui/blueprints.py` + `/api/blueprints`, enforced by
  `webui/test_blueprints.py` (every blueprint must pass clarify), UI verified via screenshot.
- **DONE — Run history / compounding memory**, **token auth + health for productionizing**, **doctor** (system self-check).

## Verification (already real, keep growing)
- DONE — `webui/test_grounding.py` (no-key proof hallucinations are caught), `webui/test_live.py`
  (no-key proof the live wiring + gates work), `webui/doctor.py` (system check + real Opus 4.7 call when keyed).

---
*Pick what to build next from here; P0/P1 first. Engine: Claude Opus 4.7.*
