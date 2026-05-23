# Technology Trade-offs — reference for the HLD Generator

Common decisions in SP/enterprise network design, with the axes that matter. These are *starting
frames* — the Designer must adapt to the actual requirements and **ground specifics** (scale limits,
feature/EoL, convergence behavior) before committing (House Rule 4). Never copy a verdict blindly.

## Transport / underlay
| Option | When it fits | Watch-outs |
|---|---|---|
| **SR-MPLS** | Modern SP/enterprise core; want TE + simplicity over LDP+RSVP; ECMP; FRR via TI-LFA | Needs SR-capable platforms/SW; SID planning discipline; controller optional |
| **SRv6** | IPv6-native, service-programming (uSID), future-leaning estates | Newer; ASIC/scale support varies by platform — verify; larger header |
| **LDP + RSVP-TE (legacy MPLS)** | Brownfield already running it; no driver to change | Two protocols to operate; RSVP-TE state/scaling; the thing you usually migrate *from* |
| **EVPN-VXLAN (DC underlay)** | Data-center fabric, L2/L3 overlay, multi-tenancy | Underlay IGP + BGP-EVPN design; ARP/ND suppression; MTU for VXLAN |

## Services / overlay
| Option | When it fits | Watch-outs |
|---|---|---|
| **EVPN** | Multipoint L2/L3 VPN, DC interconnect, all-active multihoming | Route-type discipline; ESI/LAG design; mass-withdraw behavior |
| **L3VPN (MPLS VPN)** | Classic per-VRF L3 service | RT/RD plan; PE scale; inter-AS options A/B/C |
| **Traditional L2VPN (VPWS/VPLS)** | Point-to-point / legacy multipoint L2 | VPLS scaling, MAC learning, flooding — EVPN usually supersedes |
| **SD-WAN overlay** | Many branches, transport-independent, central policy | Vendor lock-in; underlay still matters; security/SLA of the overlay |

## Redundancy / resiliency
- **Convergence:** TI-LFA / FRR for sub-50ms *protection* — but the **sub-50ms claim depends on
  hardware/BFD in hardware**; state that dependency, don't bury it (a classic Critic catch).
- **Route reflectors:** redundant RRs, cluster-ID design, avoid path hiding; consider RR placement vs forwarding path.
- **Multihoming:** EVPN all-active vs single-active; LAG/ESI; failure-domain isolation.

## Control-plane / security (House Rule 5 — design in)
- **CoPP / iACL** to protect the RP/control plane.
- **GTSM (RFC 5082, TTL security)** on multi-hop BGP — a missing/incorrect TTL/GTSM setting silently breaks multi-site/multi-DC iBGP; verify it.
- **MACsec** for L2 link encryption; **IPsec** where the path is untrusted.
- **Management-plane hardening:** AAA, control-plane to mgmt separation, no plaintext secrets.

## Scale ceilings (always verify against the actual platform/SW — do not assume)
Route/label/SID scale, FIB/RIB limits, BFD session counts, RR client counts, EVPN MAC/ARP scale —
these are platform- and release-specific. Look them up; cite the source.
