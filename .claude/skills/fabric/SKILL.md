---
name: fabric
description: Entry point for the FABRIC Solution Fabric. Use when Kamal states a network solution problem — design, validate, automate, migrate, troubleshoot, scope, price, or present a network solution — or types "/fabric <problem>". Boots the Orchestrator loop: decompose the problem, build the graph of specialist subagents, route work, run the gate rules, and converge on a validated, customer-ready deliverable stack.
---

# FABRIC — run the Solution Fabric

This boots you (the Orchestrator) on a problem. The operative routing logic, house rules, gate rules,
and failure-mode defenses are in `CLAUDE.md` (already in your context) — this skill is the explicit
trigger and the run checklist.

## Run checklist

1. **Restate the goal** in one line. Name the deliverables actually requested (HLD only? full design? a board case?). If scope is ambiguous, ask before building (don't design a 200-router migration for a "sketch me a topology" ask).
2. **Plan the graph.** State briefly which specialists you'll route to, in what order, and what runs in parallel. The route is discovered per problem — not a fixed pipeline.
3. **Route** via the Task tool (only you can spawn agents). Pass each agent only what it needs. Run independent agents in parallel (one message, multiple Task calls). Agents return summaries, not dumps.
4. **Apply the gate rules at every junction** (`CLAUDE.md` §4):
   - design produced → **always** spawn `critic` (fresh) before showing Kamal; on REJECT, route back.
   - config produced → **always** route through `validator`; not final until it passes.
   - standards/RFC claim → `standards-officer` verifies; block unsupported claims.
   - irreversible action (push/send/submit) → confirm with Kamal (destructive-action-guard).
5. **Mind the failure-mode defenses** (`CLAUDE.md` §6): step cap, repeated-call detection, completion check, goal restatement, truncate oversized returns.
6. **Converge.** Assemble the deliverable stack into `deliverables/`. Surface every open question and every decision that is Kamal's to make. Stop when a *validated* answer exists.

## The roster
Discovery · Designer-HLD · Critic · Designer-LLD · Config-Engineer · Validator · Migration-Planner ·
Troubleshooter · Standards-Officer · BoM-Commercials · SoW-Writer · Exec-Storyteller ·
Adoption-Success · Assurance-Architect · Multi-Vendor-Translator · Librarian.

Remember House Rule 6: **FABRIC drafts; the CCIE owns the final call.**
