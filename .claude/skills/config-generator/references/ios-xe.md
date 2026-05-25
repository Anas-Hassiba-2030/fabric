# Cisco IOS-XE — config reference

**Model:** running-config is **applied line-by-line immediately** (no candidate by default). Idempotent
per-line (re-entering a line is a no-op) but **order matters** and there is no atomic rollback unless
you use `configure replace` from a saved file or `reload in <min>` as a dead-man switch. Save with
`write memory` / `copy run start` — but only after verification.

## Lockout safety
`reload in 10` before a risky mgmt/routing change; cancel with `reload cancel` once reachability is
confirmed. Or stage a full config and `configure replace flash:good.cfg` to revert atomically.

## Interfaces / p2p
```
interface GigabitEthernet1
 description to:PE1.Gi1 [core]
 ip address 10.0.0.0 255.255.255.254
 mtu 9216
 no shutdown
```

## IS-IS + SR + TI-LFA
```
segment-routing mpls
 global-block 16000 23999
router isis CORE
 net 49.0001.0100.0000.0001.00
 is-type level-2-only
 metric-style wide
 segment-routing mpls
 fast-reroute per-prefix ti-lfa level-2     ! HW/BFD dependent
interface Loopback0
 isis prefix-sid index 1
```

## BGP (iBGP RR client + VPNv4)
```
router bgp 65000
 bgp router-id 10.255.0.1
 neighbor 10.255.0.254 remote-as 65000
 neighbor 10.255.0.254 update-source Loopback0
 address-family vpnv4
  neighbor 10.255.0.254 activate
```
eBGP: `neighbor x ttl-security hops N`, `bfd`, `neighbor x maximum-prefix`.

## CoPP / mgmt hardening
Explicit `control-plane` + `policy-map` CoPP (IOS-XE does **not** police control-plane for you). VTY
ACL, `transport input ssh`, `ip ssh version 2`, AAA, `service password-encryption` (weak — prefer
`enable secret` / type-9), management in a dedicated VRF (`Mgmt-vrf`).

## QoS
MQC: `class-map` → `policy-map` → `service-policy`. `mls qos` only on older switching platforms.

## Gotchas
- No two-stage commit → a half-applied script can lock you out; always pair risky changes with
  `reload in`.
- `ip routing` must be on for L3; some platforms default off.
- LAG = `Port-channel`; put `channel-group N mode active` on members.
