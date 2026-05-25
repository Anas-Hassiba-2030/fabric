# Cisco IOS-XR — config reference

**Model:** two-stage commit (candidate → `commit`). Config is hierarchical and **merge** by default;
explicit `no` to remove. Use `commit confirmed <min>` for lockout-risky changes (auto-rollback unless
re-confirmed). `show configuration failed` after a failed commit. Idempotent by nature — re-applying
the same stanza is a no-op.

## Lockout safety
`commit confirmed 5` then verify reachability, then `commit` to make permanent. `rollback configuration last 1` reverts.

## Interfaces / p2p
```
interface GigabitEthernet0/0/0/1
 description to:PE1.Gi0/0/0/1 [core]
 ipv4 address 10.0.0.0 255.255.255.254   ! /31
 mtu 9216
 no shutdown
```

## IS-IS + SR + TI-LFA
```
router isis CORE
 is-type level-2-only
 net 49.0001.0100.0000.0001.00
 address-family ipv4 unicast
  metric-style wide
  segment-routing mpls
  fast-reroute per-prefix ti-lfa            ! sub-50ms depends on HW/BFD
 interface Loopback0
  passive
  address-family ipv4 unicast
   prefix-sid index 1                       ! SRGB base + 1
 interface GigabitEthernet0/0/0/1
  point-to-point
  address-family ipv4 unicast
```
SRGB: `segment-routing global-block 16000 23999`.

## BGP (iBGP RR client + VPNv4)
```
router bgp 65000
 bgp router-id 10.255.0.1
 address-family vpnv4 unicast
 neighbor 10.255.0.254
  remote-as 65000
  update-source Loopback0
  address-family vpnv4 unicast
```
eBGP: `ttl-security` / `neighbor x ebgp-multihop` with care; `bfd fast-detect`.

## CoPP / mgmt hardening
LPTS handles much control-plane policing natively; add explicit policy via `control-plane`/`lpts`
where the baseline requires. Management in its own VRF: `vrf MGMT`, SSH `vrf`, AAA, no telnet.

## QoS
`class-map match-any`, `policy-map`, `service-policy input/output`. Mark at edge, trust core.

## Gotchas
- Two-stage commit means a script must `commit` — a config without commit does nothing.
- `mpls oam` / label-range overlaps with SRGB — keep SRGB clear of dynamic label range.
- `bundle-ether` for LAG; LACP period configured under the member.
