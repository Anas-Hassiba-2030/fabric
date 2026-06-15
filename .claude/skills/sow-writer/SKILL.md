---
name: sow-writer
description: Turns a solution package into a defensible Statement of Work — scope, deliverables, assumptions, explicit exclusions, RACI, timeline, and objective acceptance criteria — reusing proven clauses. Use when moving from a solution to an engagement. Loaded by the SoW & Proposal Writer agent.
---

# SoW Writer

Turn the solution into an engagement document that survives a dispute. Core discipline: **the value is
in what it excludes as much as what it includes** — the gaps are where scope creep and arguments live.

## Inputs
The solution package (HLD/LLD/BoM/migration plan) and the success criteria from the Discovery brief.
Reuse proven clauses from `references/sow-clauses.md` and from `wrath/memory/` — don't redraft
boilerplate.

## SoW sections (the contract)
1. **Scope** — what will be done, bounded. Tie to the design deliverables.
2. **Deliverables** — concrete artifacts, each with a definition of done.
3. **Assumptions** — what must be true for the plan/price to hold (access, info, environment, customer resources).
4. **Exclusions** — what is explicitly *not* in scope. Be generous and specific here.
5. **RACI** — per deliverable: one **Accountable** owner, Responsible doer(s), Consulted, Informed.
6. **Timeline** — phases, milestones, dependencies, customer-side gating items.
7. **Acceptance criteria** — objective, testable, tied to Discovery's success criteria.

## Companion artifacts (to `deliverables/`)
- **Project plan** — phases, milestones, dependencies, critical path.
- **Acceptance test plan** — the objective tests the customer signs off against.

## Discipline
- **Assumptions + exclusions explicit.** An unstated assumption is a future dispute.
- Acceptance criteria are **objective and testable** — "BGP sessions up and routes present on all PEs",
  not "network works".
- RACI names **one** accountable owner per deliverable.
- Sending this to a customer is gated by the destructive-action-guard + Kamal's confirmation (House Rule 6).

Return a summary + SoW path. Flag any scope assumption you couldn't confirm so Kamal closes it before sign.
