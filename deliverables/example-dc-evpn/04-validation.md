# Validation — Leaf1 config

> Phase: Implement · Agent: validator · Skill: config-audit · Gate: **PASS** (House Rule 2)

## Deterministic pre-pass (config_lint, vendor nxos)
```
$ python .claude/skills/config-audit/scripts/config_lint.py deliverables/example-dc-evpn/03-config-leaf1.cfg --vendor nxos
# config_lint — vendor: nxos — 0 finding(s)
# pre-pass: clean — judgment still required
```
**VERDICT: PASS** — no CRITICAL/HIGH. This config is part of `run_tests.sh` and is re-checked on every run.

## Judgment pass (what the linter can't see)
- **Feature-gating correct** — every capability used (`router bgp`, `router ospf`, `nv overlay evpn`, `interface Vlan`) has its `feature` enabled; NX-OS would otherwise reject the lines.
- **Lockout-safe order** — mgmt VRF + SSH + underlay are applied before the overlay/NVE, so the box stays reachable through the change.
- **No session-killers** — uniform MTU 9216 on fabric links; iBGP (no eBGP-multihop/GTSM gap); strict CoPP retained; SSH-only (telnet disabled); no plaintext secrets.
- **Intent matches the LLD** — L2VNI 10010 ↔ VLAN 10, L3VNI 50001 ↔ VRF TENANT-A, anycast GW 10.20.10.1, EVPN RT `auto`.

## Acceptance criteria (objective)
1. EVPN sessions to both spine RRs **Established**, AF `l2vpn evpn`.
2. Anycast gateway `10.20.10.1` reachable + identical MAC on every leaf.
3. Host MAC/IP appears as EVPN type-2; mobility on vMotion converges sub-second.
4. config_lint gate **PASS** on every leaf; zero open P1/P2 at sign-off.

## Operate
Telemetry/SLO catalog + drift check via **📡 Assurance**; fault isolation via **🔧 Troubleshoot** — both
over the read-only network-state source.
