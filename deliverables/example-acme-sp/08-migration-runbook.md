# Migration Runbook (Phase 1 extract) — Acme SP core

*Phase: Operate. Skill: `migration-runbook`. Agent: `migration-planner`. Gate: `critic` attacks rollback coverage. Status: worked example.*
*Every live push is gated by the destructive-action-guard + Kamal (House Rule 6).*

## Header
- **Change:** introduce SR-MPLS alongside the live LDP core, one node at a time (ships-in-the-night), then move VPNv4 next-hops to SR. **Window:** weekly 02:00–05:00, one site.
- **Invariants:** customer L3VPN reachable throughout; management plane never lost; LDP stays up until SR is proven.
- **Strategy:** SR and LDP coexist during transition (label coexistence) so each step is independently revertible.

## Phase 1 — Enable SR on P1 (DC1 core), LDP still primary
Blast radius if it fails: DC1 transit only; LDP remains the forwarding plane, so **no service impact** expected.
Risk: low / Mitigation: SR enabled but not preferred until verified; `commit confirmed`.

```
Step 1.1 — Baseline (pre-check, the known-good)
  Pre-check : show isis adjacency ; show mpls forwarding ; record VPNv4 prefix count on PE1 (~1400)
              show route matrix for the named customer test flows  → record all
Step 1.2 — Enable SRGB + IS-IS SR on P1
  Change    : segment-routing global-block 16000 23999 ; router isis CORE … segment-routing mpls
              (commit confirmed 5)
  Post-check: show isis segment-routing label table → P1 prefix-SID 16011 present
              show mpls forwarding → SR labels installed; LDP labels STILL present (coexistence)
              VPNv4 prefix count unchanged (~1400); customer test flows still pass
  Confirm   : commit   (make permanent only after post-checks pass)
  Rollback  : rollback configuration last 1  → verify SR labels gone, LDP unchanged, flows pass
GO/NO-GO gate (end of Phase 1):
  [ ] P1 prefix-SID 16011 in the SR label table
  [ ] VPNv4 prefix count == baseline on PE1
  [ ] all customer test flows pass
  [ ] no new CRITICAL control-plane alerts
  NO-GO action: rollback last 1 on P1; abort window; LDP remains primary (no service change occurred)
```

## Subsequent phases (summarized — each follows the same 4-part contract)
| Phase | Change | Independently revertible? |
|---|---|---|
| 2 | Enable SR on P2, PE1, PE2, PE3 (per node) | yes — per node `rollback last 1` |
| 3 | Prefer SR for IGP next-hops; verify TI-LFA (closes HLD Q3) | yes — revert preference |
| 4 | Move VPNv4 next-hop resolution to SR; soak | yes — re-point to LDP |
| 5 | Remove LDP/RSVP-TE (only after soak + sign-off) | the one-way door — gated, last |

## Discipline check (pre-empt the Critic)
- Every step has a real pre-check, post-check, and a tested rollback (House Rule 3).
- LDP is retained until SR is proven and soaked — the irreversible step (LDP removal) is **last** and **gated**.
- Blast radius is one node/site per step; the core mesh + RR diversity keep service up during each change.
