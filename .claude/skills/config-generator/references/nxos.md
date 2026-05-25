# Cisco NX-OS — config reference

**Model:** applied immediately like IOS-XE, but **feature-gated** — a capability does nothing until its
`feature` is enabled (`feature isis`, `feature bgp`, `feature interface-vlan`, `nv overlay evpn`,
`feature ospf`, `feature lacp`). Supports `checkpoint` + `rollback running-config checkpoint <name>`
for atomic revert, and `configure replace`. DC-focused: VXLAN-EVPN is the common fabric.

## Lockout safety
`checkpoint pre-change` → make changes → verify → keep, or `rollback running-config checkpoint pre-change` to revert atomically.

## Interfaces / p2p
```
interface Ethernet1/1
 description to:LEAF1.Eth1/1 [fabric]
 no switchport
 mtu 9216
 ip address 10.0.0.0/31
 no shutdown
```

## VXLAN-EVPN (typical DC fabric)
```
feature ospf ; feature bgp ; feature pim
feature nv overlay ; nv overlay evpn
feature vn-segment-vlan-based
interface nve1
 no shutdown
 source-interface loopback1
 host-reachability protocol bgp
```
Underlay IGP (OSPF/IS-IS) + multicast or ingress-replication; MTU must cover VXLAN overhead (50B).

## BGP (EVPN)
```
router bgp 65000
 router-id 10.255.0.1
 address-family l2vpn evpn
 neighbor 10.255.0.254
  remote-as 65000
  update-source loopback0
  address-family l2vpn evpn
   send-community extended
```

## CoPP / mgmt hardening
NX-OS ships a **default CoPP policy** (`copp profile strict|moderate|lenient`) — pick/tune it, don't
remove it. `feature ssh`, no telnet, management in the dedicated **`management` VRF** (mgmt0 lives
there by default), AAA.

## QoS
MQC with `type qos` / `type queuing` policy-maps; system queuing templates per platform — verify the
hardware queue model.

## Gotchas
- Forgetting `feature X` → the config silently won't parse/work; the lint pre-pass flags this.
- `no switchport` needed to make a port L3 on most platforms.
- mgmt0 is in VRF `management` — SSH/AAA/NTP source must reference it.
- vPC introduces its own consistency rules; peer-link + keepalive must be right or it splits.
