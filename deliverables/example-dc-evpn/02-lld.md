# LLD — Acme DC EVPN-VXLAN fabric

> Phase: Implement · Agent: designer-lld · Skill: lld-generator · collision-free, reuses Acme conventions

## Addressing / IPAM (authoritative — no overlaps)
| Purpose | Range | Notes |
|---|---|---|
| Loopback0 (router-id / BGP source) | 10.255.1.0/24 (one /32 per leaf; spines 10.255.0.x) | Leaf1 = 10.255.1.1 |
| Loopback1 (VTEP / NVE source) | 10.255.2.0/24 (/32 per VTEP) | Leaf1 = 10.255.2.1 |
| Spine↔leaf p2p (underlay) | 10.1.0.0/24 in /31s | Leaf1↔Spine1 = 10.1.0.0/31; Leaf1↔Spine2 = 10.1.0.2/31 |
| Spine RR loopbacks | 10.255.0.11 (S1), 10.255.0.12 (S2) | iBGP EVPN RR peers |
| Tenant subnet (TENANT-A web) | 10.20.10.0/24 | anycast GW 10.20.10.1 on every leaf |

## Underlay
OSPF process `UNDERLAY`, area `0.0.0.0`, all fabric links `ip ospf network point-to-point`, **MTU 9216**
fabric-wide. Router-id = loopback0.

## Overlay (BGP-EVPN)
- **iBGP** ASN **65001**; spines are route-reflectors; leaves peer to both spine loopbacks, `update-source loopback0`, AF `l2vpn evpn`, `send-community extended`.

## VNI / tenancy plan (no collisions)
| Object | Value | Maps to |
|---|---|---|
| L2VNI | **10010** | VLAN 10 (TENANT-A web) |
| L3VNI | **50001** | VRF TENANT-A (SVI Vlan901, `ip forward`) |
| RD / RT | `auto` (derived from router-id : VNI) | EVPN import/export, `route-target both auto evpn` |
| Anycast GW MAC | `0000.2222.3333` | identical fabric-wide (distributed default gateway) |

## Multihoming
Dual-homed hosts via **vPC** at go-live (EVPN ESI on the roadmap). Access ports `spanning-tree port type edge`.

## Security zones
Per-tenant VRF (`TENANT-A`); management in `vrf context management`, SSH only; **CoPP `strict`** on every
node; anycast-GW MAC consistency enforced.

## Per-device build sheet → Leaf1
Realized in `03-config-leaf1.cfg` (NX-OS). Every line traces to a row above. Output is **not final until
the Validator passes it** (House Rule 2) — see `04-validation.md`.
