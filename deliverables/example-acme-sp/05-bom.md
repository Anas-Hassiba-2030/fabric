# Bill of Materials — Acme SP core (worked example)

*Phase: Sell. Skill: `bom-builder`. Agent: `bom-commercials`. Status: worked example.*
*Quantities trace to `02-lld.md`. SKUs/tiers are ILLUSTRATIVE placeholders — a real run verifies each
current via WebSearch (House Rule 4); `<verify>` marks what must be confirmed before quoting.*

## Hardware & licensing
| Item | SKU (verify) | Description | Qty | Design driver | Verified? |
|---|---|---|---|---|---|
| Core/PE router (XR) | `<verify>` | NCS-540/5500-class, 100G-capable | 4 | PE1, PE2, P1, P2 (LLD node table) | `<verify>` |
| PE router (Junos) | `<verify>` | MX-class, 100G-capable | 1 | PE3 (DC3, multi-vendor R4) | `<verify>` |
| Route reflector | `<verify>` | RR (can be VM/appliance) | 2 | RR1, RR2 (redundant RR requirement) | `<verify>` |
| 100G optics | `<verify>` | QSFP28, reach per span | 14 | 7 core /31 links × 2 ends (LLD link table) | `<verify>` |
| SR/L3VPN license | `<verify>` | tier incl. SR-MPLS + VPNv4 | 5 | features used: SR, VPNv4 (LLD) | `<verify>` |
| PSU redundancy | `<verify>` | 1+1 per chassis | 7×2 | resiliency (HLD §5) | `<verify>` |
| Support | `<verify>` | 24×7×4, 3-yr | 7 | core criticality | `<verify>` |

## Sizing rationale
- **5 routers + 2 RRs** = exactly the LLD node table; no spare router quoted here (sparing strategy is an optional line).
- **14× 100G optics** = the 7 core point-to-point links × 2 ends. Customer-facing optics scoped per CE order, excluded here.
- **License tier** driven by SR-MPLS + VPNv4; confirm the tier name includes both before quoting.
- **30% growth headroom** (brief) is **not** baked into hardware here — called out as an optional capacity line so the customer sees floor vs headroom.

## Commercial summary
Cost is driven by the 5 routers + RR pair and 100G optics; the SR/VPNv4 license tier is the main
recurring lever. Margin sits in services (design, migration) and support term. **Optional / growth:**
spares, the 30% headroom capacity, and DC-fabric work (separate project). **Flagged — needs data:**
volume discount and exact support tier depend on Acme's contract — not invented here (House Rule 7).
