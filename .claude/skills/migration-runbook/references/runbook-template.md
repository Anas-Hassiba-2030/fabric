# Migration runbook template — reference for the Migration Planner

Fill per engagement. The shape enforces House Rule 3 (a rollback at every step).

## Header
- **Change**: <what + why>  •  **Window**: <date/time, duration>  •  **Approver**: <name>
- **Invariants** (must hold throughout): <e.g. customer X L3VPN reachable; mgmt plane never lost>
- **Participants / roles**: executor, verifier, go/no-go owner, customer contact.

## Per-phase block
```
### Phase N — <scope, e.g. "Migrate PE1 IGP LDP→SR">
Blast radius if this fails: <what traffic/services are exposed>
Risk: <likelihood> / Mitigation: <...>

Step N.1 — <action>
  Pre-check : <command> → expect <result>      (baseline captured)
  Change    : <exact config delta / automation call>
  Post-check: <command> → expect <result>
  Rollback  : <exact reverse action> → verify <command> → expect <baseline>

Step N.2 — ...

GO/NO-GO gate (end of phase):
  [ ] <objective criterion 1>
  [ ] <objective criterion 2>
  NO-GO action: <roll back to phase start / abort window>
```

## Baseline capture (pre-change, the "known good")
- IGP adjacencies + count; BGP sessions Established + prefix counts.
- Forwarding: label/route for key prefixes; traffic rate on uplinks.
- Service reachability matrix (named flows) — the same tests you'll run post-change.
Store baselines so post-checks compare against truth, not memory.

## Rollback ordering
Last-changed → first-reverted. The mgmt/routing path you depend on is changed **last** and reverted
**first**. Where the platform supports it, wrap risky steps in `commit confirmed <min>` (IOS-XR/Junos)
or `reload in <min>` (IOS-XE) so loss of access auto-reverts.

## Go/no-go gate criteria (objective only)
Adjacencies/sessions up to baseline count • key prefixes present • reachability matrix passes •
no new CRITICAL alerts • traffic restored to within X% of baseline.
