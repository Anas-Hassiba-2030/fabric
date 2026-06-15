# WRATH Memory

Three layers — do not conflate them (a classic agent mistake):

| Layer | Lifetime | Holds | Where |
|---|---|---|---|
| **Working** | This conversation | Current problem + intermediate findings | The live context window (owned by the Orchestrator) |
| **Episodic** | Across sessions, per customer | This customer's estate, conventions, history, past decisions, lessons | `customers/<customer>.md` |
| **Semantic** | Across all work | Reusable patterns, design templates, vendor knowledge, Kamal's playbook | `patterns/` |

The **Librarian** agent (`.claude/agents/librarian.md`) owns episodic + semantic memory: it retrieves
the right context at the **start** of every engagement and writes the new project back at the **close**.

## Conventions

- **`customers/<name>.md`** — one file per customer. Estate summary, naming/IP conventions, installed
  base, past designs (with links into `deliverables/`), decisions made and why, lessons learned,
  "what we tried that failed." The `session_start` hook surfaces `customers/active.md` if present.
- **`patterns/<topic>.md`** — reusable, customer-agnostic knowledge: a clean SR-MPLS migration pattern,
  a preferred EVPN fabric template, a go-to QoS model, gotchas by platform.

## Active customer

Create `customers/active.md` (or symlink it) to mark the engagement currently in focus — the
SessionStart hook reads it so you never start cold. Nothing is committed here yet; this is the store
the Librarian fills as engagements close (House Rule 8 — compounding memory).
