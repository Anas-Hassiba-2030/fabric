# Customer — Acme SP

*Episodic memory for the worked example. Demonstrates what the Librarian writes back at engagement close.*

## Profile
- **Industry / type:** regional service provider
- **Footprint:** 3 data centers; ~1,400 VPNv4 prefixes, 30% 3-yr growth headroom; ASN 65000 (private)
- **Vendors / platforms:** Cisco IOS-XR (DC1, DC2); Juniper Junos (DC3); 100G-capable refresh
- **Primary contacts / decision owners:** Acme network lead (LLD sign-off), change manager (cutover)

## Conventions (REUSE)
- **Naming:** `PE#/P#/RR#`; interface desc `to:<neighbor>.<intf> [<role>]`
- **Addressing:** Loopback0 in `10.255.0.0/24`; core p2p `10.0.0.0/24` as /31s; mgmt `10.30.0.0/24` in VRF `MGMT`
- **SR:** SRGB `16000–23999`; prefix-SID = `16000 + loopback last octet`
- **RT/RD:** RD `<loopback>:<vrf-id>`; RT `65000:<vrf-id>`
- **Security baseline:** CIS (control-plane + mgmt-plane isolation)

## Installed base & current state
- Legacy LDP+RSVP-TE core being modernized to SR-MPLS + BGP L3VPN. Customer edge unchanged (R5).

## Past designs & deliverables
| Date | Engagement | Deliverable link | Outcome |
|---|---|---|---|
| 2026-05 | Core modernization (LDP→SR-MPLS, L3VPN) | `deliverables/example-acme-sp/` | HLD→LLD→config→validated PASS; phased migration designed |

## Decisions made (and why)
- **SR-MPLS over SRv6** — broader platform maturity, meets sub-50ms goal; SRv6 deferred to next refresh.
- **VPNv4 L3VPN over EVPN** — matches the service, reuses existing edge (R5).
- **Anycast RR pair (SID 16250)** — nearest-RR selection + clean failover; distinct cluster-IDs avoid path hiding.

## Lessons learned / what we tried that failed
- (none yet — first engagement)

## Open items
- **Q3:** TI-LFA sub-50ms depends on linecard BFD-in-hardware — verify before any SLA commitment
  (closed operationally in migration Phase 3).
