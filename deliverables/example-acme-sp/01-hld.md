# High-Level Design — Acme SP core modernization

*Phase: Design. Skill: `hld-generator`. Gate: reviewed by `critic`. Status: worked example.*

## 1. Frame
- **Goal:** simpler, TE-capable, fast-converging multi-DC core delivering L3VPN, multi-vendor, migratable from live LDP with no edge forklift.
- **Hard constraints:** R1–R7 (see brief). Reuse existing loopback/IP scheme and ASN 65000.
- **Out of scope:** CE, apps, DC fabric, physical.

## 2. Technology decisions (trade-offs — House Rule 1)

### Transport / underlay
| Option | Fit | Complexity | Risk | Operability | Verdict |
|---|---|---|---|---|---|
| **SR-MPLS** | high — TE + TI-LFA, drops LDP+RSVP | low-med | low (mature, multi-vendor) | simpler (one protocol) | ◄ **recommend** — meets R3, simplifies ops, broad platform support |
| SRv6 | high (future) | med-high | med — ASIC/scale varies, verify per platform | newer tooling | rejected for now — no driver over SR-MPLS; revisit at next refresh |
| Keep LDP+RSVP-TE | low — the thing we're modernizing from | — | — | two protocols | rejected — fails the "simpler" goal |

### Service / overlay
| Option | Verdict |
|---|---|
| **BGP/MPLS L3VPN (VPNv4)** | ◄ **recommend** — exactly R2, reuses existing PE edge, RFC 4364 |
| EVPN | rejected — no L2 multipoint requirement here; overkill for this service |

### Fast convergence
- **TI-LFA** for per-prefix sub-50ms **protection**. **Dependency, stated honestly:** the sub-50ms
  figure depends on BFD-in-hardware and linecard support — listed as open question Q3; verify before committing the SLA.

### Route reflection
- **Redundant RRs** with distinct **cluster-IDs** (no path hiding), plus an **anycast loopback/SID** so
  PEs follow the nearest RR. Two RRs (R-requirement).

## 3. Security designed in (House Rule 5)
- **Control plane:** IOS-XR LPTS + explicit CoPP profile; Junos lo0 RE-protection filter. Both tuned to permit only required control traffic.
- **Multi-hop nothing by default;** eBGP to customers uses GTSM (RFC 5082) + max-prefix.
- **Management plane** isolated in its own VRF, SSH-only, AAA (TACACS+), no telnet, no plaintext secrets.
- **IGP/BGP authentication** enabled.

## 4. Reference topology
```mermaid
graph TD
  subgraph DC1 [DC1 — IOS-XR]
    PE1[PE1]:::pe
    P1[P1 / core]:::p
    RR1[RR1]:::rr
  end
  subgraph DC2 [DC2 — IOS-XR]
    PE2[PE2]:::pe
    P2[P2 / core]:::p
    RR2[RR2]:::rr
  end
  subgraph DC3 [DC3 — Junos]
    PE3[PE3]:::pe
  end
  PE1 --- P1 --- RR1
  PE2 --- P2 --- RR2
  P1 --- P2
  P1 --- PE3
  P2 --- PE3
  PE1 -. iBGP VPNv4 .- RR1
  PE2 -. iBGP VPNv4 .- RR2
  PE3 -. iBGP VPNv4 .- RR1
  classDef pe fill:#e6f0ff; classDef p fill:#eee; classDef rr fill:#ffe6e6;
```
Roles: PE (service edge), P (core transit), RR (route reflection, anycast pair). Failure domains: per-DC; core mesh survives a single P or link via TI-LFA.

## 5. Resiliency analysis
- **Single core link down** → TI-LFA backup path, sub-50ms *if* HW/BFD supports it (Q3).
- **Single RR down** → PEs reach the surviving RR via the anycast SID; no session re-design needed.
- **Single P node down** → traffic reroutes over the alternate DC path; VPNv4 unaffected (RR diversity).
- **Honest ceiling:** scale tested to ~1,400 + 30% headroom; beyond ~10k VPNv4 revisit RR placement.

## 6. Decision log
| Decision | Alternatives | Why | Underlying assumption |
|---|---|---|---|
| SR-MPLS | SRv6, keep LDP/RSVP | simpler, TE, multi-vendor mature, meets R3 | platforms SR-capable (verify linecards) |
| VPNv4 L3VPN | EVPN | matches service, reuses edge (R5) | no L2 multipoint need |
| Anycast RR pair | distinct RR per PE | nearest-RR + clean failover | anycast SID supported on platforms |
| TI-LFA | LFA, none | sub-50ms protection | **BFD-in-hardware (Q3 — unverified)** |

## Critic pre-empt
Convergence claim flags its HW dependency (Q3). Security is in §3, not an appendix. RR design avoids
path hiding (distinct cluster-IDs). Scale ceiling stated. SRv6 explicitly deferred with a reason.
