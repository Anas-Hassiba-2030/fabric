# Pattern — SR-MPLS core with BGP L3VPN

*Semantic memory (House Rule 8): reusable, customer-agnostic. A go-to starting frame; always adapt to
the customer's conventions and ground platform specifics (House Rule 4). First applied: Acme SP.*

## When this fits
Multi-site provider/enterprise core, want TE + sub-50ms protection + simpler ops than LDP+RSVP-TE,
delivering per-VRF L3VPN, no L2 multipoint requirement. (If L2/multi-tenancy is needed → EVPN instead.)

## The shape
- **Transport:** SR-MPLS. One fabric-wide SRGB; prefix-SID = deterministic function of the loopback
  (one lookup from the loopback table). TI-LFA for protection — **state the BFD-in-HW dependency**.
- **Service:** BGP/MPLS L3VPN (VPNv4/v6, RFC 4364). RD `<loopback>:<vrf-id>`, RT per service.
- **Route reflection:** redundant RRs, **distinct cluster-IDs** (no path hiding), **anycast loopback +
  anycast SID** so PEs follow the nearest RR and fail over cleanly.
- **IGP:** IS-IS L2 (or OSPF), wide metrics, auth, `overload-bit on-startup`.
- **Security in:** CoPP/LPTS (XR) or lo0 RE-filter (Junos); mgmt-plane in its own VRF; eBGP edge with
  GTSM (RFC 5082) + max-prefix + inbound prefix policy.

## Reusable decisions (with the trap each avoids)
| Decision | Avoids |
|---|---|
| Deterministic prefix-SID = SRGB base + loopback octet | SID/loopback drift; hard-to-debug label plans |
| Anycast RR pair | RR failover re-design; path hiding |
| Distinct RR cluster-IDs | clients losing path diversity |
| /31 (or /127) core links | address burn |
| Jumbo core, 1500 at customer edge | label-overhead black-holes (verify no jumbo path crosses the 1500 link) |

## Migration note (brownfield from LDP)
Run SR and LDP **ships-in-the-night** (label coexistence); enable SR per node, prefer SR, move VPNv4
next-hops, soak, then remove LDP **last** (the one-way door). Rollback at every step (House Rule 3).
See `deliverables/example-acme-sp/08-migration-runbook.md` for the worked runbook.

## Gotchas by platform
- **IOS-XR:** two-stage commit — automation must `commit`; keep SRGB clear of the dynamic label range.
- **Junos:** need `family mpls` + `family iso` on the unit or IS-IS/MPLS won't run; candidate config does nothing until `commit`.
- **NX-OS:** feature-gated — `feature isis/bgp/mpls…` or it silently won't parse.
