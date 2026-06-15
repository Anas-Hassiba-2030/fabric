# Executive narrative — reference for the Exec Deck

How to translate engineering into a business story a CTO/CFO acts on.

## Translation table (tech → business)
| Engineering says | Executive hears (lead with this) |
|---|---|
| Sub-50ms TI-LFA convergence | "An outage that used to drop calls now self-heals before users notice" |
| SR-MPLS replaces LDP+RSVP | "One simpler protocol — fewer outages from complexity, faster to change" |
| EVPN all-active multihoming | "No single box can take the site down" |
| Model-driven telemetry | "We see problems forming and fix them before they're incidents" |
| Smart-licensing tier upgrade | "Pay for the capacity we use; scale without a forklift" |

## Framing trade-offs as business choices
Never a feature list. Always: **cost ↔ resilience ↔ speed.**
> "Option A is lower cost but a single-site failure is a 30-minute outage. Option B adds 12% to spend
> and makes that failure invisible. The choice is how much an hour of downtime is worth to us."

## TCO frame (5-year)
Capex (BoM) + Opex (support, power, staff time) + risk cost (expected downtime × cost/hour) −
benefit (agility, avoided outages, consolidation). Show the *direction*, grounded; don't fabricate
precision you don't have (House Rule 7).

## Slide discipline
- One idea per slide; the title states the takeaway, not the topic.
- One diagram for the architecture — reuse the topology-diagram output, simplified.
- The risk slide is a feature, not a confession: risk → likelihood → mitigation → residual.
- End on the **ask** and the **next step** — never trail off on a tech appendix.

## Anti-patterns
- Opening with the topology diagram (that's the *how*, slide 3 — not the lead).
- Acronyms unexplained. Numbers you can't source. "It's industry best practice" with no reference.
