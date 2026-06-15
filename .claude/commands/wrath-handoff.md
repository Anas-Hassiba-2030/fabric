---
description: Assemble the converged solution into a customer-ready, grounded handoff bundle + trust report.
---

Produce the engagement handoff for the current solution:

1. Verify every requested deliverable exists and passed its gate (the "are we actually done?" check). A partial stack is not done.
2. Assemble the stack in order (Discovery → HLD → LLD → Config → BoM → Cost & Risk → SoW → Exec → Migration → Standards), each with its grounding verdict.
3. Append the **trust report**: grounded / flagged / blocked counts, the verify-before-ship ledger, assumptions in play, and the confidence level — never claim more than the evidence supports (House Rule 7).
4. Note where the design touches production and confirm a per-step rollback exists (House Rule 3).
5. Offer the shareable HTML report (`/api/export.html`) and the Markdown bundle (`webui/export_run.py`) for sending to Kamal.

If a project is being closed, route to `librarian` to archive the design + lessons to `wrath/memory/` and distil a reusable pattern.
