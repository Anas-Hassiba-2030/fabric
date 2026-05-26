# Statement of Work (excerpt) — Acme SP core modernization

*Phase: Sell. Skill: `sow-writer`. Agent: `sow-writer`. Status: worked example.*
*Sending a real SoW to a customer is gated by Kamal's confirmation (House Rule 6).*

## Scope
Design, build, validate, and migrate Acme's 3-DC core from LDP+RSVP-TE to SR-MPLS with BGP/MPLS L3VPN,
multi-vendor (IOS-XR DC1/DC2, Junos DC3), per the approved HLD/LLD, with zero customer-visible outage.

## Deliverables
| Deliverable | Definition of done |
|---|---|
| HLD | approved by Acme architecture; trade-offs + decision log (this engagement: `01-hld.md`) |
| LLD + IPAM | collision-free, reuses Acme scheme; per-device build sheet (`02-lld.md`) |
| Device configs + automation | per-device, validated PASS by the audit gate (`03`/`04`) |
| Migration runbook | phased, rollback at every step, go/no-go gates (`08`) |
| Acceptance test results | the success-criteria matrix, executed and signed |

## Assumptions
- Acme provides device access, jump hosts, credentials, and the weekly 02:00–05:00 windows.
- Existing topology/addressing as provided is accurate; ASN 65000 reused.
- Linecards support BFD-in-hardware for TI-LFA (HLD Q3) — to be confirmed in design validation.

## Exclusions (where disputes live — explicit)
- Customer CE devices, CE re-cabling/re-addressing (R5), and anything above L3.
- DC fabric / leaf-spine (separate project).
- Physical, power, rack, environmental.
- Remediation of pre-existing faults found mid-engagement (raised as a change request).
- SRv6 (explicitly deferred in the HLD).

## RACI (extract)
| Deliverable | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| LLD sign-off | WRATH team | **Acme network lead** | Acme security | Acme PMO |
| Per-site cutover | Joint | **Acme change manager** | Acme NOC | Exec sponsor |

## Acceptance criteria (objective, tied to Discovery success criteria)
1. All PE↔RR VPNv4 sessions **Established**; ≈1,400 prefixes present on each PE.
2. Single-link failure test reconverges within the agreed target; traffic restored (recorded).
3. No customer-visible outage during any cutover window.
4. Audit gate **PASS** on every deployed config; zero open P1/P2 at sign-off.

## Change control
Any change to scope, BoM, or timeline goes via written change request; re-estimated before work proceeds.
