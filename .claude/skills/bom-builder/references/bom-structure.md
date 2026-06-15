# BoM structure — reference for the BoM Builder

Starting frame for line-item categories and the design driver behind each. Adapt to the platform;
**verify SKUs/tiers/EoL before quoting** (House Rule 4).

## Line-item categories
| Category | Examples | Quantity driver (from the design) |
|---|---|---|
| Chassis / platform | router, switch, fixed vs modular | role + throughput + port density in the LLD |
| Line cards / modules | NPU cards, MACsec-capable cards | port count + feature need (e.g. MACsec, timing) |
| Optics / transceivers | SR/LR/ER, DAC, breakout | one per interface in the interface map, by reach |
| Power / cooling | PSUs (1+1), fan trays | redundancy model + platform power draw |
| Licenses | tier/subscription, throughput, feature add-on | features used in the LLD (SR, EVPN, TE, telemetry) |
| Support | SmartNet / DNA / equivalent, SLA level, term | device criticality + customer ops model |
| Spares | cold/hot spares, sparing ratio | failure-domain + RMA-time tolerance |
| Services (optional) | install, migration, training | scope from the SoW |

## Sizing drivers to name explicitly
- **Port count & speed mix** → optics quantity and line-card choice.
- **Throughput / scale** (routes, MACs, tunnels, subscribers) → platform + license tier.
- **Redundancy** (1+1 PSU, dual RP, RR pair, all-active multihoming) → multipliers.
- **Growth headroom** — state the % and horizon; keep it a separate optional line, not baked silently.

## License tiers — verify, don't assume
Subscription/smart-licensing models change. Map the feature to the **lowest tier that includes it**,
cite the feature that forces the tier, and confirm the tier name is current via WebSearch.

## Currency / EoL checklist
- SKU still orderable? (not EoS)
- End-of-Life / End-of-Support date beyond the support term?
- License model still sold this way (perpetual vs subscription)?
- Optic compatible with the line card (some platforms enforce coded optics)?
Record the **date verified** next to each verified line.
