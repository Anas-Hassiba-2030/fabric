# Standards index — reference for the Standards Checker

A curated list of **commonly cited, real** standards as a memory aid. **This is not a substitute for
verification** — confirm the number, title, and current status (an RFC may be obsoleted/updated) against
a real source before it goes in a customer deliverable (House Rule 4). If it's not here, look it up;
never guess a number.

## Routing — BGP
| Ref | Title (verify) | Commonly cited for |
|---|---|---|
| RFC 4271 | A Border Gateway Protocol 4 (BGP-4) | base BGP |
| RFC 4760 | Multiprotocol Extensions for BGP-4 (MP-BGP) | address-families (VPNv4/v6, EVPN) |
| RFC 4364 | BGP/MPLS IP VPNs | L3VPN |
| RFC 7432 | BGP MPLS-Based Ethernet VPN (EVPN) | EVPN control plane |
| RFC 8365 | Network Virtualization Overlay Solution using EVPN | EVPN-VXLAN |
| RFC 5082 | Generalized TTL Security Mechanism (GTSM) | multi-hop eBGP protection |
| RFC 7454 | BGP Operations and Security (BCP 194) | eBGP hardening baseline |
| RFC 8212 | Default EBGP Route Propagation without Policies | default-deny eBGP |
| RFC 6811 | BGP Prefix Origin Validation | RPKI ROV |
| RFC 8205 | BGPsec Protocol Specification | path validation |

## Routing — IGP / SR / MPLS
| Ref | Title (verify) | Cited for |
|---|---|---|
| RFC 1195 | IS-IS for IP and dual environments | IS-IS |
| RFC 2328 | OSPF Version 2 | OSPFv2 |
| RFC 5340 | OSPF for IPv6 (OSPFv3) | OSPFv3 |
| RFC 8402 | Segment Routing Architecture | SR |
| RFC 8660 | Segment Routing with the MPLS Data Plane | SR-MPLS |
| RFC 8754 | IPv6 Segment Routing Header (SRH) | SRv6 data plane |
| RFC 8986 | SRv6 Network Programming | SRv6 |

## Liveness / forwarding
| Ref | Title (verify) | Cited for |
|---|---|---|
| RFC 5880 | Bidirectional Forwarding Detection (BFD) | fast detection |
| RFC 5881 | BFD for IPv4/IPv6 (Single Hop) | single-hop BFD |
| RFC 1191 / RFC 8201 | Path MTU Discovery (v4 / v6) | MTU / MSS |
| RFC 8200 | IPv6 Specification | IPv6 base |
| RFC 4861 | Neighbor Discovery for IPv6 | ND |

## L2 / security / AAA (IEEE + RFC)
| Ref | Title (verify) | Cited for |
|---|---|---|
| IEEE 802.1AE | MACsec | link-layer encryption |
| IEEE 802.1AX | Link Aggregation (LACP) | LAG |
| IEEE 802.1Q | Bridges and VLANs | VLAN tagging |
| RFC 2865 | RADIUS | AAA |
| RFC 8907 | TACACS+ Protocol | AAA (device admin) |
| RFC 5424 | The Syslog Protocol | logging |

## Compliance baselines (frameworks — map to the customer's chosen one)
- **NIST SP 800-53** — security & privacy controls catalog.
- **CIS Benchmarks** — hardening guides (incl. Cisco IOS/NX-OS benchmarks).
- **PCI DSS** — payment-card environment requirements (segmentation, logging, access).
- Vendor **CVDs** (Cisco Validated Designs) — cite the specific CVD + version, verified.

## Hard rule
If a claim cites a standard **not** in this list, you have not verified it — look it up, confirm it
says what's claimed, and only then cite it. Cannot verify → `UNVERIFIED — blocker`.
