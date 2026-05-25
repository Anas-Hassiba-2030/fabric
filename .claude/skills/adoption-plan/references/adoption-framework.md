# Adoption framework — reference for Adoption & Success

## Barrier dimensions → typical actions
| Dimension | Typical barrier | Action shape |
|---|---|---|
| Skills | team can't operate SR/EVPN/telemetry | targeted enablement session + runbook + shadowing |
| Process | change process bypasses new automation | update change template; make automation the default path |
| Tooling | dashboards exist but not in ops workflow | embed in NOC view; alert routing to the right queue |
| Organizational | no clear owner for the new capability | name an accountable owner; add to a role's charter |

## Barrier → action → owner → milestone (the core table)
| Barrier | Action | Owner (role/person) | Milestone date | Status |
|---|---|---|---|---|
| <barrier> | <concrete action> | <named owner> | <date> | open/in-progress/done |
Every row has a real owner and a real date, or it's not on the plan.

## Value scorecard
| Metric | Business driver (from Discovery) | Baseline | Target | By when |
|---|---|---|---|---|
| MTTR for core incidents | reduce downtime cost | <baseline> | <target> | <date> |
| Time to deploy a new service | agility / time-to-market | <baseline> | <target> | <date> |
| % changes via automation | reduce human-error outages | <baseline> | <target> | <date> |
Each metric **traces to a driver** — drop any metric that doesn't.

## Enablement session arc (ATX / Accelerator)
Awareness ("what it does, why it matters for you") → Capability ("hands-on, your environment") →
Habit ("it's now the default way we work"). Each session maps to the barriers it removes and ends
with an owner + next action.

## Adoption curve checkpoints
30/60/90-day reviews against the scorecard; re-baseline barriers; celebrate a realized metric to
build momentum.
