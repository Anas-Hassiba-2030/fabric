---
name: telemetry-design
description: Designs the service-assurance layer — KPIs derived from the SLAs/SLOs, each mapped to a concrete model-driven telemetry source (gNMI/gRPC sensor paths, counters, synthetic tests), an SLI→SLO→threshold→action catalog, and closed-loop remediation only where safe and reversible. Use when the solution must be operable and measurable. Loaded by the Assurance Architect agent.
---

# Telemetry Design

A network you can't measure is one you can't operate. Core discipline: **measure the promise, not
whatever is easy to scrape**, and **every alert names its action** — no noise.

## Inputs
The SLAs/SLOs and success criteria from the Discovery brief, and the LLD (so sensor paths map to real
interfaces/protocols/services).

## Procedure
1. **Derive KPIs from the promises.** For each SLA/SLO (availability, latency, loss, jitter,
   convergence, capacity), name the KPI that proves it.
2. **Map each KPI to a concrete source** — a model-driven sensor path (gNMI/gRPC subscription),
   a counter, a log/event, or a synthetic probe. State cadence (streamed on-change vs sampled, interval).
   See `references/telemetry-catalog.md`.
3. **Define SLIs → SLOs → thresholds → action.** The threshold is the line where someone does
   something; the action is named. Distinguish warning from page.
4. **Where it lands** — collector/TSDB/dashboard/alerting path; retention.
5. **Closed-loop remediation** — only where the action is **safe and reversible** (e.g. shift traffic,
   raise a case). Anything that changes the live network stays gated (House Rule 6).

## Outputs (to `deliverables/`)
- **Assurance design** — what's measured, how, where it lands.
- **Telemetry subscription plan** — sensor paths + cadence, per platform.
- **SLO catalog** — `SLI | SLO target | sensor/source | warning | page | action`.
- **Closed-loop hooks** — the safe, reversible automations (and the gated ones, flagged).

## Discipline
- Measure the promise; don't pad the catalog with vanity counters.
- **Every alert is actionable** — if there's no action, it's not an alert, it's noise.
- Sampled vs on-change deliberately: on-change for state (adjacency up/down), sampled for rates.

Return a summary + assurance design path.
