---
name: lld-generator
description: Drives a Low-Level Design — approved HLD → addressing/IPAM, IGP/BGP design, SR-SID/label plan, interface maps, QoS policy, security zones, and naming, with no collisions and a per-device build sheet. Use when converting an approved HLD into an implementable LLD. Loaded by the Designer-LLD agent.
---

# LLD Generator

Turn an **approved** HLD into something an engineer builds from without guessing. The HLD says
"SR-MPLS core with redundant RRs"; you produce the exact loopbacks, SIDs, labels, interfaces, QoS
classes, zones, and names. Core discipline: **collision-free, loop-free under failure, and grounded
in the customer's existing conventions** — reuse their scheme, don't impose a new one (House Rule 8).

## Inputs (read first)
1. The approved HLD in `deliverables/` (architecture, security posture, topology, decision log).
2. The customer's conventions from `fabric/memory/customers/<name>.md` — naming, IP scheme, ASN, QoS model. **Reuse them.** If none exist, propose a scheme and flag it as a new convention to record.

## Procedure
1. **Addressing / IPAM** — allocate loopbacks, point-to-point links (/31 or /127), VIPs/anycast, management. One authoritative allocation table; no overlaps. See `references/lld-patterns.md`.
2. **IGP design** — IS-IS or OSPF per HLD: areas/levels, metrics, reference bandwidth, timers, TI-LFA/FRR, authentication. Loop-free under each modeled failure.
3. **SR-SID / label plan** — SRGB range, per-node prefix-SIDs (loopback ↔ SID mapping), adjacency-SID strategy, anycast-SIDs for RR/GW pairs. No SID collisions; document the SRGB.
4. **BGP design** — ASN(s), iBGP (RR clusters, cluster-IDs, no path hiding), address-families (VPNv4/v6, EVPN, L2VPN), RT/RD plan, eBGP edges with TTL-security/GTSM.
5. **Interface map** — per-device port → role → neighbor → subnet → description, with MTU and LAG/ESI.
6. **QoS** — class map end-to-end (markings, queues, drop policy), aligned across platforms; mark at the edge, trust in the core.
7. **Security zones** — carry the HLD's segmentation down to concrete zones, VRFs, and ACL intent; CoPP/iACL targets; management-plane plane separation (House Rule 5).
8. **Naming** — apply the customer convention to every hostname, interface description, policy, and VRF.

## Outputs (to `deliverables/`)
- **LLD document** — the sections above, per-area.
- **IPAM sheet** — the authoritative addressing allocation table.
- **Per-device design tables** — one block per device an engineer can configure straight from.

## Pre-empt the Critic
Self-check before returning: any IP/SID/RT collision? loop or blackhole under a modeled failure?
RR design hide paths? eBGP edges missing TTL-security? QoS markings consistent end-to-end? security
posture actually carried down to zones/ACLs, not dropped? Anything the HLD left ambiguous that you
**invented** instead of flagging (House Rule 7)? Fix these now — the Critic will find them.

Return a summary + path to the LLD. The Orchestrator routes it to the Critic before Config.
