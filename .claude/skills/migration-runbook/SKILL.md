---
name: migration-runbook
description: Builds a brownfield cutover plan — phased migration with explicit maintenance windows, a rollback at EVERY step (House Rule 3), per-phase blast-radius/risk analysis, real pre/post verification tests, and objective go/no-go gates. Use whenever the solution touches a live network. Loaded by the Migration Planner agent.
---

# Migration Runbook

Brownfield change on a live network: a mistake is an outage. Core discipline (House Rule 3, absolute):
**no step ships without a clean rollback. If a step can't be reverted, redesign the step.**

## Inputs
Current state (existing config/topology/IPAM) and target state (the LLD). Identify what changes and —
just as important — **what must not move**.

## Procedure
1. **State delta** — current vs target; list every change, and the invariants that must hold throughout.
2. **Phase to bound blast radius** — never big-bang a live core. Each phase touches the smallest
   independently-revertible unit (one PE, one link, one service at a time). Order phases so the riskiest
   change happens with the most fallback intact.
3. **Per step, the four-part contract:**
   - **Pre-checks** — objective state captured before (baseline: adjacencies, routes, traffic, counters).
   - **Change** — the exact action (config delta / automation call).
   - **Post-checks** — the real, checkable test that it worked (not "looks fine").
   - **Rollback** — the exact reverse action + its own verification.
4. **Blast-radius + risk register** per phase: what's exposed if this step fails, likelihood, mitigation.
5. **Go/no-go gates** between phases — objective criteria; if not green, stop or roll back.

## Outputs (to `deliverables/`)
- **Migration runbook** — phased, with maintenance windows.
- **Rollback runbook** — the revert for every step, sequenced (last-changed, first-reverted).
- **Risk register + blast-radius analysis** per phase.
- **Go/no-go checklist** with objective criteria.

## Discipline
- Pre/post tests are **real and checkable** — name the command/telemetry and the expected result.
- Sequence around the lockout trap (the mgmt/routing change you depend on changes last, reverts first);
  use `commit confirmed` / `reload in` safety nets.
- Any push to a device is gated by the destructive-action-guard + Kamal (House Rule 6).

Return a summary + runbook paths. The Orchestrator routes this to the Critic, which will specifically
attack your rollback coverage and blast radius — pre-empt it.
