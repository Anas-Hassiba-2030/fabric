# Requirements Brief — Acme SP core modernization

*Phase: Discovery. Skill: `requirements-intake`. Status: worked example.*

## Problem statement
Acme is a regional service provider running a legacy LDP+RSVP-TE MPLS core across 3 data centers.
They want a modern, simpler core with fast convergence and traffic engineering, delivering L3VPN to
business customers, with no forklift of the existing customer-facing edge. One site runs Juniper; the
other two run Cisco.

## Scope
- **In:** core transport modernization (3 DCs), L3VPN service control plane, route-reflection design,
  fast-convergence, QoS, control-plane security, assurance/telemetry, migration from the live LDP core.
- **Out:** customer CE devices, applications, physical/cabling, anything above L3, DC fabric (separate project).

## Hard requirements
| # | Requirement | Source |
|---|---|---|
| R1 | Multi-DC core, 3 sites, any-to-any | RFP |
| R2 | L3VPN service for business customers | RFP |
| R3 | Sub-second (target sub-50ms protection) reconvergence on link/node failure | RFP §SLA |
| R4 | Multi-vendor: Cisco IOS-XR (DC1/DC2), Juniper Junos (DC3) | call notes |
| R5 | No customer-edge re-cabling / re-addressing | constraint |
| R6 | Control-plane hardened; management plane isolated | security baseline (CIS) |
| R7 | Zero-/low-downtime migration from the live LDP core | RFP §migration |

## Scale / SLA
- ~1,400 VPNv4 prefixes today, 30% growth headroom over 3 years.
- Core links 10G now, 100G-capable platforms wanted for refresh.
- Maintenance windows: weekly 02:00–05:00 local, one site at a time.

## Constraints & assumptions
- Existing loopback/IP scheme to be **reused** where possible (R5).
- ASN 65000 (private) in use for the core today.
- Two route reflectors required for redundancy.

## Open questions (flagged, not assumed — House Rule 7)
1. Is SRv6 on the table, or is SR-MPLS the target? (assumed **SR-MPLS** pending confirmation — platform support is broader)
2. Confirmed Junos platform/version at DC3? (assumed MX-class, verify)
3. TI-LFA sub-50ms claim depends on BFD-in-hardware — confirm linecards support it.

## Success criteria (drive acceptance later)
- All PE↔RR VPNv4 sessions Established; ~1,400 prefixes present on each PE.
- Link-failure test reconverges within target; traffic restored.
- No customer-visible outage during migration.
