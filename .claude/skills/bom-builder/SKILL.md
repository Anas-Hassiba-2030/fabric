---
name: bom-builder
description: Turns a design into a defensible Bill of Materials — hardware, optics, licenses (smart-licensing tiers), and support — with every quantity traced to a design need, current SKUs/EoL verified, and a margin-aware commercial narrative. Use when a solution must be quoted or scoped commercially. Loaded by the BoM & Commercials agent.
---

# BoM Builder

Turn the design into numbers a customer can buy and you can defend. Core discipline: **every line item
traces to a design need (House Rule 1), every SKU/license is verified current (House Rule 4), and
anything you don't know is flagged, not invented (House Rule 7).**

## Inputs
The approved LLD/HLD + IPAM from `deliverables/` (device count, port/throughput needs, redundancy,
service scale), and the customer's growth/refresh assumptions from Discovery. Pull past deal structures
from `wrath/memory/customers/<name>.md` if present.

## Procedure
1. **Derive quantities from the design.** Per device: chassis/model, line cards, port counts → optics
   (type × count from the interface map), power/cooling, rack units. Per fabric: spares strategy.
   Every quantity has a one-line rationale tied to a design table.
2. **Licenses.** Map features used in the LLD to the right tier (e.g. smart-licensing / subscription
   tier, throughput tier, feature add-ons). Don't over- or under-license — name the feature that drives
   the tier.
3. **Support.** Service level (NBD vs 24×7×4 vs onsite) per device criticality; term (1/3/5 yr).
4. **Verify currency (House Rule 4).** Use WebSearch to confirm SKUs exist, license tiers are current,
   and parts aren't EoS/EoL within the support term. Never quote a dead part. Note the check date.
5. **Commercial narrative.** What drives the cost, required vs optional, where margin sits, and the
   levers (volume, term, tier). Frame as choices, not a single number.

## Output (to `deliverables/`)
- **BoM sheet** — columns: `Item | SKU | Description | Qty | Unit basis (the design driver) | Verified? | Notes`. Markdown table or CSV.
- **Sizing rationale** — the assumption behind each quantity (port count, throughput, redundancy, headroom).
- **Commercial summary** — the margin-aware pricing narrative.

## Discipline
- Flag pricing that depends on data you don't have (discount, exact support tier) rather than inventing it.
- Separate **required** from **optional/growth** so the customer sees the floor and the headroom.
