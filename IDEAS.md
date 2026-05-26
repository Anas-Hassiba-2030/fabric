# Ideas & Concepts — escalating the system

A living catalog of capabilities that make the result better, more trustworthy, and more impressive.
Priority: **P0** = do next, **P1** = high value soon, **P2** = later, **★** = signature / astonishing.
Nothing here is built unless it says "DONE". The interface is tracked separately (deferred for now).

## Quality & trust (least hallucination, best output)
- **P0 — Clarifying-questions gate.** Before designing, Discovery asks the *right* missing questions
  (scale, SLA, brownfield/greenfield, platform/version) instead of assuming. Biggest single quality lever.
- **P1 — Assumptions ledger + confidence score** per deliverable: every assumption listed, each claim
  tagged High/Med/Low confidence; the run ends with a "trust report" (grounded / flagged / blocked counts).
- **P1 — Provenance everywhere** (DONE for citations): every factual claim links to its source or is
  marked unverified. Extend to SKUs (vendor EoL pages) and CVDs.
- **P2 — Adjustable red-team intensity.** A "Critic aggressiveness" dial; optional second adversarial pass.
- **★ Self-improving pattern library.** Every *accepted* design auto-distills a reusable pattern into
  memory (`wrath/memory/patterns`), so the system compounds and gets better with each engagement.

## Smarter orchestration
- **P1 — Multi-model routing.** Opus 4.7 for heavy reasoning (HLD, Critic, RCA); Sonnet/Haiku for cheap
  stages (formatting, BoM tables) — better cost/speed without losing quality. (Engine default already Opus 4.7.)
- **P2 — What-if / compare designs.** Re-run with a changed constraint and **diff** the two designs
  side-by-side (e.g. "SR-MPLS vs SRv6", "2 RRs vs 4").
- **P2 — Memory RAG.** At run start, recall similar past engagements + patterns and cite them.

## Richer deliverables
- **P1 — Auto topology diagram.** Render the HLD's reference topology (Mermaid) inline + export as SVG/PNG.
- **P1 — Export to real formats.** BoM → XLSX, Exec one-pager → PPTX/PDF, SoW → DOCX (today: Markdown, DONE).
- **P1 — Cost/TCO + risk register** generated from the design (capex/opex/risk-cost, flagged unverified).
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
- **P2 — Engagement blueprints.** Starter packs (SP core, DC fabric, campus, SD-WAN, secure edge) to seed a run.
- **DONE — Run history / compounding memory**, **token auth + health for productionizing**, **doctor** (system self-check).

## Verification (already real, keep growing)
- DONE — `webui/test_grounding.py` (no-key proof hallucinations are caught), `webui/test_live.py`
  (no-key proof the live wiring + gates work), `webui/doctor.py` (system check + real Opus 4.7 call when keyed).

---
*Pick what to build next from here; P0/P1 first. Engine: Claude Opus 4.7.*
