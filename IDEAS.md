# Ideas & Concepts — escalating the system

A living catalog of capabilities that make the result better, more trustworthy, and more impressive.
Priority: **P0** = do next, **P1** = high value soon, **P2** = later, **★** = signature / astonishing.
Nothing here is built unless it says "DONE".

## Trust & transparency
- **DONE — Modern in-app dialogs.** Replaced every native browser `prompt()` (What-if tweak, inbox
  notes, access token) with a themed modal input (Enter/Esc/click-outside) — no more "localhost says".
- **DONE (Phase 2) — Provenance labelling (no ambiguity).** Every deliverable is badged **REAL**
  (deterministic gate actually ran — Validator/Standards/Cost/Trust, in any mode), **LIVE · Opus 4.7**
  (model reasoning), or **DEMO** (representative). A legend sits on the pipeline; the export bundle
  tags each section's source. `webui/provenance.py`, proven by `webui/test_provenance.py`.

## Workspace
- **DONE (Phase: Inbox) — Saved-results inbox.** `📥 Inbox` bookmarks any run with a free-text note so
  you can test many things and keep the good ones; each item shows problem + note + trust badge +
  date, with Open / Edit-note / Remove. Persists to `wrath/memory/inbox.json` (local). `webui/inbox.py`
  + `/api/inbox`, proven by `webui/test_inbox.py`.

## Analytics
- **DONE (Phase 1) — Cross-run analytics dashboard.** `📊 Analytics` aggregates every saved run: total
  runs, live/demo split, claims grounded, hallucinations caught, patterns learned, avg stages, trust
  distribution, the grounding net (grounded/flagged/blocked), config-gate pass/fail, and most-worked
  technologies. `webui/analytics.py` + `/api/analytics`, proven by `webui/test_analytics.py`.

## Console / interface
- **DONE — Copy + remembered session.** Each deliverable has a **⧉ Copy** button (Markdown to clipboard, with a ✓ confirmation); the last problem, mode, and Critic-intensity persist across reloads (localStorage). Verified via headless Chromium (clipboard + restore-after-reload).
- **DONE — Toolbar declutter.** Secondary actions grouped (This run | Reports & library) with a divider, chips on their own row, history right-aligned — no wrapping/overflow at 1536 or 1920.
- **DONE — Console redesign (modern, animated).** The orchestration pipeline is a compact **horizontal
  rail** (Orchestrator on top, phases left→right, icon cards, animated flowing connectors + red
  revise-arcs on gate bounces) instead of tall stacked card columns; the **deliverable** now owns the
  main panel. Glassmorphism, phase color-coding, running-node gradient ring, staged entrance, mermaid
  topology rendering (CDN, graceful fallback) + **topology export as SVG (server-side) and PNG (client-side canvas rasterization)**. Verified via headless Chromium (SVG valid; PNG downloads with correct magic bytes).
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
- **DONE (Phase 4) — Critic-intensity dial.** A red-team aggressiveness control (Lenient / Standard / Aggressive / Max·2-passes): Lenient passes unless a clear blocker; Max runs two adversarial revision cycles. Live mode injects the aggressiveness into the Critic prompt. `webui/criticism.py`, proven by `webui/test_criticism.py`; verified end-to-end (Lenient=0 bounces, Max=2).
- **DONE (Phase 3) — Persisted compounding memory.** Saving a pattern now **commits it to git** (path-scoped — never sweeps up other working changes; optional push via `WRATH_AUTO_PUSH=1`) so learning survives restarts. `webui/persist.py`, proven by `webui/test_persist.py`.
- **DONE (★) — Self-improving pattern library.** `★ Save pattern` distils an accepted run into a
  reusable, customer-agnostic pattern (shape + only-verified references + provenance) written to
  `wrath/memory/patterns/`, which Memory RAG then recalls on the next similar problem — the system
  compounds with each engagement. `webui/distill.py` + `POST /api/distill`, proven by
  `webui/test_distill.py`; loop verified end-to-end (save → recalled next run) via screenshots.

## Smarter orchestration
- **DONE — Slash commands + pipeline-integrity guarantee.** Added Claude Code slash commands
  (`/wrath`, `/wrath-review`, `/wrath-verify`, `/wrath-handoff`) and a `webui/test_agents.py` integrity
  proof that EVERY pipeline stage stays wired to a real subagent + skill and that model routing matches
  each agent's declared tier — so "a subagent per stage" can't silently drift.
- **DONE — Multi-model routing.** Each Live call goes to the model the charter assigns: Opus for heavy reasoning (HLD, Critic, Migration, RCA), Sonnet for routine stages, Haiku for the Librarian — better cost/speed without losing quality on the hard stages. `ANTHROPIC_MODEL` forces single-model. The LIVE provenance badge shows the actual model per stage. `webui/routing.py`, proven by `webui/test_routing.py`.
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
- **DONE (Phase 4) — Audience reframing.** The Exec one-pager has Board / CFO / CISO / NOC re-voice tabs — each emphasizes that audience's concerns (money/risk, security/compliance, operability/SLA) with no invented currency. `webui/audience.py` + `/api/reframe`, proven by `webui/test_audience.py`.
- **DONE (Phase 4) — Compliance pack.** `🛡 Compliance` builds a standalone PCI/HIPAA/NIST/CIS matrix mapping each control area to the design measure that addresses it — honest (Design-addressed, audit-confirmed; never claims 'certified'). `webui/compliance.py` + `/api/compliance`, proven by `webui/test_compliance.py`.

## Operate & troubleshoot
- **DONE — Root-cause analysis engine.** `🔧 Troubleshoot` gives the `troubleshooter` agent / `rca-playbook` a runnable engine: from a symptom + the read-only network state it walks a layered hypothesis tree and isolates a *proven* causal chain (e.g. an eBGP session Idle because its next-hop interface — whose subnet holds the neighbor — is down), with a House-Rule-6 fix + verify step. `webui/rca.py` + `/api/rca`, proven by `webui/test_rca.py` (incl. no-false-correlation + honest no-fault cases).

## Plugged into the real estate (the big differentiators)
- **DONE — Pluggable read-only state source.** `webui/netstate.py` reads from `WRATH_NETSTATE_URL` (a read-only GET — pyATS/gNMI/NetBox JSON) or snapshot dir, with an adapter that normalizes native + foreign field shapes onto WRATH's device schema. Assurance + RCA run through it; going live is a config swap (point the URL at the estate's read-only feed). Strictly read-only (GET only). Proven by `webui/test_netstate.py`. **The stdio `wrath-netstate` MCP now reads through the same loader** — web app + Claude Code's MCP tool share one read-only, normalizing, URL-or-snapshot source — and exposes `check_drift` + `diagnose` (the same assurance/RCA engines) as read-only tools the real agents can call.
- **P2 — Docs/Standards MCP → live fetch** with caching when egress allows (today: curated index).
- **P2 — Ticketing/Git integration.** Pull RFCs/incidents (ServiceNow/Jira), version every deliverable in Git.
- **DONE (★) — Continuous assurance.** `📡 Assurance` generates the telemetry/SLO catalog from the design (KPI→gNMI/OpenConfig sensor→threshold→action) **and** runs a drift check that re-validates the read-only network state against design intent (catches Idle BGP, down core links, sub-jumbo MTU). Closed-loop is alert/ticket only — never an auto device-push (House Rule 6). `webui/assurance.py` + `/api/assurance`, proven by `webui/test_assurance.py`.

## Workflow & reach
- **DONE — Shareable read-only report.** `🔗 Share` opens a self-contained, styled HTML page of the whole run (renders markdown→HTML, topology via mermaid CDN with source fallback) — openable/sendable anywhere, print-to-PDF in the browser. `webui/share.py` + `GET /api/export.html?id=`, proven by `webui/test_share.py`.
- **DONE — CLI trust gate.** `webui/cli.py --require-confidence high|medium|guarded` exits non-zero if a run's trust confidence is below the bar — WRATH as a CI quality gate. Proven by `webui/test_cli.py`.
- **DONE — Headless CLI / API mode.** `python webui/cli.py "<problem>" [--mode live] [--intensity max] [--format json] [--out file]` runs the full pipeline with no browser and emits the deliverable bundle (reuses the engine + exporter). Honors mode + Critic dial. `webui/cli.py`, proven by `webui/test_cli.py`.
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
