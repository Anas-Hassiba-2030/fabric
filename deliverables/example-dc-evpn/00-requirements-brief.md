# Requirements Brief — Acme DC EVPN-VXLAN fabric

> Status: APPROVED · Author: Discovery agent · Phase: Design

## Business drivers
Acme is consolidating two aging 3-tier data centers onto a single spine-leaf fabric to support
multi-tenant workloads, faster service turn-up, and east-west scale — without the STP fragility and
manual VLAN sprawl of the legacy design.

## Scope
- **Greenfield** fabric (new build alongside the legacy DC, migrate workloads after).
- Scale: **10 devices** at go-live (2 spines, 8 leaves), ~480 server ports, 3-year growth to 16 leaves.
- Multi-tenant: initial 1 tenant (TENANT-A), design for ~30 VRFs / 500 L2 segments.

## SLAs / SLOs
- Availability **99.999%**; sub-second failover on a link/leaf loss.
- Non-blocking east-west; jumbo (9216) end-to-end in the fabric.

## Security baseline
- **PCI** segmentation between tenants and to the legacy DMZ; control-plane hardening; SSH-only mgmt.

## Constraints / platform
- **Cisco NX-OS** (Nexus 9300 leaves / 9500 spines, release 10.3). Existing BGP ASN 65001.

## Success criteria
- All leaves' EVPN sessions Established; anycast gateway reachable from every leaf; host MAC/IP mobility
  works on vMotion; single-leaf failure causes no tenant outage.

## Open questions (resolved at sign-off)
1. [architecture-critical] Underlay IGP — **OSPF** (team familiarity) vs IS-IS → **OSPF** chosen.
2. [architecture-critical] BUM replication — multicast (PIM) vs **ingress-replication (BGP)** → **ingress-replication** (no multicast in the underlay to operate).
3. [detail] vPC vs EVPN ESI multihoming for dual-homed hosts → vPC at go-live; ESI on the roadmap.
