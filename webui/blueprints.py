#!/usr/bin/env python3
"""WRATH engagement blueprints — ready-to-run starter problems (P2).

One-click starters for the common engagement shapes. Each is written to be *complete* — it specifies
deployment, scale, SLA, and platform — so it clears the clarifying-questions gate and goes straight to
design (that invariant is enforced by webui/test_blueprints.py).

    all() -> [ {id, name, category, icon, problem} ]
"""
import sys

BLUEPRINTS = [
    {"id": "sp-core", "name": "SP core modernization", "category": "Service Provider", "icon": "hld",
     "problem": "Brownfield migration of a 40-site service-provider core to SR-MPLS with BGP L3VPN on "
                "Cisco IOS-XR (NCS 540, release 7.10). 99.999% availability with sub-50ms TI-LFA "
                "convergence; carries L3VPN and multicast; NIST/PCI segmentation; multi-vendor edge; "
                "cutover within Q3 maintenance windows on a fixed budget."},
    {"id": "dc-fabric", "name": "Data-center fabric", "category": "Data Center", "icon": "lld",
     "problem": "Greenfield EVPN-VXLAN leaf-spine data-center fabric of 10 devices (2 spines, 8 leaves) "
                "on Cisco NX-OS (Nexus 9300/9500, release 10.3). 99.999% availability with sub-second "
                "convergence; multi-tenant L2/L3 with anycast gateway; PCI segmentation; ESI-LAG "
                "dual-homing; delivered this quarter within budget."},
    {"id": "dci", "name": "Data-center interconnect", "category": "Data Center", "icon": "migration",
     "problem": "Brownfield 2-site data-center interconnect over a DWDM ring, 6 devices, encrypted with "
                "MACsec, on Juniper Junos (MX series, release 22.4). 99.999% availability with "
                "sub-second convergence; EVPN L2 stretch plus L3VPN; HIPAA segmentation; cutover in "
                "monthly maintenance windows within budget."},
    {"id": "campus", "name": "Campus refresh", "category": "Enterprise", "icon": "standards",
     "problem": "Greenfield 3-site campus refresh, 1200 users, ~60 access switches and redundant "
                "distribution on Cisco IOS-XE (Catalyst 9300/9500, release 17.12). 99.99% availability "
                "with sub-second convergence; 802.1X with macro/micro segmentation (NIST/CIS); QoS for "
                "voice; phased rollout this year within budget."},
    {"id": "secure-edge", "name": "Secure internet edge", "category": "Security", "icon": "critic",
     "problem": "Brownfield secure internet edge for a hospital: dual-ISP, 4 devices, DDoS protection, "
                "stateful firewall and IPS, on Cisco platforms (ASR 1000 / Firepower, release 7.4). "
                "99.99% availability with sub-second failover convergence; PCI and HIPAA segmentation "
                "for medical devices; site-to-site IPsec; cutover in a single maintenance window within "
                "budget."},
    {"id": "sd-wan", "name": "SD-WAN rollout", "category": "WAN", "icon": "exec",
     "problem": "Greenfield SD-WAN across 80 sites on Cisco Catalyst SD-WAN (cEdge, release 17.12) with "
                "dual transport (MPLS plus broadband). 99.9% availability with sub-second convergence; "
                "application-aware routing and QoS; IPsec encryption everywhere; zero-trust "
                "segmentation (NIST); phased rollout over two quarters within budget."},
]


def all():
    return [dict(b) for b in BLUEPRINTS]


def get(bid):
    for b in BLUEPRINTS:
        if b["id"] == bid:
            return dict(b)
    return None


if __name__ == "__main__":
    for b in BLUEPRINTS:
        print(f"[{b['category']}] {b['name']} ({b['id']})")
    sys.exit(0)
