# Low-Level Design — Acme SP core modernization

*Phase: Implement. Skill: `lld-generator`. Gate: reviewed by `critic`. Status: worked example.*
*Reuses the existing scheme (R5). Values here are the source of truth for the configs.*

## Addressing / IPAM
**Loopback0 — `10.255.0.0/24`** (router-id / SR prefix-SID source):
| Node | Loopback0 | Role | Site | Platform |
|---|---|---|---|---|
| PE1 | 10.255.0.1/32 | provider-edge | DC1 | IOS-XR |
| PE2 | 10.255.0.2/32 | provider-edge | DC2 | IOS-XR |
| PE3 | 10.255.0.3/32 | provider-edge | DC3 | Junos |
| P1 | 10.255.0.11/32 | core | DC1 | IOS-XR |
| P2 | 10.255.0.12/32 | core | DC2 | IOS-XR |
| RR-anycast | 10.255.0.250/32 | RR VIP (on RR1+RR2) | — | — |
| RR1 | 10.255.0.254/32 | route reflector | DC1 | IOS-XR |
| RR2 | 10.255.0.253/32 | route reflector | DC2 | IOS-XR |

**Core p2p links — `10.0.0.0/24` in /31s** (lower address = lower router-id end):
| Link | Subnet | A-end | B-end |
|---|---|---|---|
| PE1–P1 | 10.0.0.0/31 | PE1 .0 | P1 .1 |
| PE2–P2 | 10.0.0.2/31 | PE2 .2 | P2 .3 |
| P1–P2 | 10.0.0.4/31 | P1 .4 | P2 .5 |
| P1–PE3 | 10.0.0.6/31 | P1 .6 | PE3 .7 |
| P2–PE3 | 10.0.0.8/31 | P2 .8 | PE3 .9 |
| P1–RR1 | 10.0.0.10/31 | P1 .10 | RR1 .11 |
| P2–RR2 | 10.0.0.12/31 | P2 .12 | RR2 .13 |

**Management:** OOB `10.30.0.0/24`, VRF `MGMT`, never in the data plane.

## IGP — IS-IS (single L2 domain)
- NET: `49.0001.0100.0000.00XX.00` where XX = loopback last octet (PE1 → `...0001.00`).
- `metric-style wide`; reference bw set for 10/100G.
- **TI-LFA** per-prefix (Q3: confirm HW/BFD); BFD on core links.
- IS-IS authentication (HMAC-MD5/SHA per platform), `overload-bit on-startup`.

## SR-MPLS — SID / label plan
- **SRGB: `16000–23999`** (identical fabric-wide).
- **Prefix-SID = 16000 + loopback last octet:**
  | Node | Prefix-SID | (loopback) |
  |---|---|---|
  | PE1 | 16001 | .1 |
  | PE2 | 16002 | .2 |
  | PE3 | 16003 | .3 |
  | P1 | 16011 | .11 |
  | P2 | 16012 | .12 |
  | RR-anycast | 16250 | .250 (anycast on RR1+RR2) |
- Adjacency-SIDs dynamic. No SID overlaps SRGB; verified no two nodes share a prefix-SID.

## BGP — iBGP VPNv4
- **ASN 65000**, all iBGP. RRs reflect VPNv4.
- RR cluster-IDs distinct: RR1 `0.0.0.1`, RR2 `0.0.0.2` (no path hiding).
- PEs peer to **both** RRs (anycast loopback 10.255.0.250 as primary peer, plus explicit RR1/RR2 for the example) using `update-source Loopback0`.
- **RD** per PE per VRF: `<loopback>:<vrf-id>` (e.g. PE1 CustA → `10.255.0.1:100`).
- **RT** per service: CustA `65000:100` (hub-spoke uses `:1001/:1002`).
- Customer eBGP: GTSM (RFC 5082), `maximum-prefix`, prefix-list in.

## QoS — 5-class (mark at edge, trust in core)
| Class | Marking | Treatment |
|---|---|---|
| Network control | CS6 | protected |
| Realtime/VoIP | EF | priority, policed |
| Business | AF31 | guaranteed BW |
| Best effort | DF | default |
| Scavenger | CS1 | first to drop |

## Security zones (carry HLD §3 down)
- **Mgmt zone:** VRF `MGMT`, ACL permits SSH/TACACS+/NTP/syslog from the OOB net only.
- **Control plane:** CoPP/LPTS (XR) + lo0 filter (Junos) — permit IS-IS/BGP/BFD/SSH from peers, police the rest.
- **Customer eBGP edge:** GTSM + prefix-list + max-prefix.

## Naming
Hostnames `PE1/PE2/PE3/P1/P2/RR1/RR2`. Interface descriptions carry neighbor + role:
`to:P1.Gi0/0/0/0 [core]`, `to:CustA-CE [L3VPN-CustA eBGP]`.

## Critic pre-empt
No IP/SID/RT collisions (checked). RR cluster-IDs distinct. eBGP edge has GTSM. QoS markings consistent
across all three platforms. Q3 (TI-LFA HW dependency) carried forward from HLD, not silently resolved.
