# Juniper Junos — config reference

**Model:** candidate config + **`commit`** (atomic, validated). `commit check` to validate without
applying; `commit confirmed <min>` for lockout-risky changes (auto-rollback); `rollback N` + `commit`
to revert. Structured hierarchy; `set`/`delete` or full-stanza. Idempotent — `set` of an existing
value is a no-op. `groups` + `apply-groups` for DRY/idempotent templating.

## Lockout safety
`commit confirmed 5` → verify reachability → `commit`. If you lose access, it auto-reverts.

## Interfaces / p2p
```
set interfaces ge-0/0/1 description "to:PE1.ge-0/0/1 [core]"
set interfaces ge-0/0/1 mtu 9216
set interfaces ge-0/0/1 unit 0 family inet address 10.0.0.0/31
set interfaces ge-0/0/1 unit 0 family iso          # IS-IS
set interfaces ge-0/0/1 unit 0 family mpls
```

## IS-IS + SR (SPRING) + TI-LFA
```
set protocols isis level 1 disable
set protocols isis interface lo0.0 passive
set protocols isis interface ge-0/0/1.0 point-to-point
set protocols isis backup-spf-options use-post-convergence-lsp     # TI-LFA (HW/BFD dependent)
set protocols mpls interface all
set protocols isis source-packet-routing srgb start-label 16000 index-range 8000
set protocols isis interface lo0.0 level 2 ipv4-adjacency-segment ... / node-segment index 1
```

## BGP (iBGP RR client + VPN)
```
set routing-options autonomous-system 65000
set protocols bgp group RR type internal
set protocols bgp group RR local-address 10.255.0.1
set protocols bgp group RR family inet-vpn unicast
set protocols bgp group RR neighbor 10.255.0.254
```
eBGP: `set protocols bgp group EXT ttl <n>` (GTSM), `bfd-liveness-detection`, `family ... prefix-limit`.

## CoPP / mgmt hardening
Junos uses **lo0 filters** as the control-plane protection (the "RE protection filter") + `firewall`
policers — apply a stateless filter on `lo0.0` to police/permit only required control traffic.
Management: dedicated `mgmt_junos` / inet.0 routing-instance or fxp0; `set system services ssh`, no
telnet, `set system root-authentication`, AAA.

## QoS (CoS)
`class-of-service`: classifiers, forwarding-classes, schedulers, scheduler-maps. Different vocabulary
from Cisco MQC — map markings (DSCP/EXP) to forwarding-classes explicitly.

## Gotchas
- A config without `commit` does nothing (candidate only).
- `family mpls` and `family iso` must be on the unit or IS-IS/MPLS won't run.
- `apply-groups` ordering/inheritance can surprise — `show configuration | display inheritance`.
- Logical units (`.0`) are mandatory; addressing lives on the unit, not the physical.
