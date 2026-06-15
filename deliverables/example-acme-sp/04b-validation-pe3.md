# Validation Report — PE3 config (Junos) + multi-vendor parity

*Phase: Implement (gate). Skills: `config-audit` + `multivendor-translator`. Status: worked example.*
*Demonstrates the gate and the multi-vendor requirement (R4) on the Junos side.*

## Layer 1 — deterministic lint pre-pass (actual tool output)
```
$ python .claude/skills/config-audit/scripts/config_lint.py \
        deliverables/example-acme-sp/03b-config-pe3.cfg

# config_lint — vendor: junos — 0 finding(s)
# pre-pass: clean — judgment still required
```
(exit 0 — vendor auto-detected as Junos)

## Layer 2 — judgment + cross-vendor parity (intent must survive the crossing)
| Intent (from LLD) | PE1 (IOS-XR) | PE3 (Junos) | Parity? |
|---|---|---|---|
| Router-id / loopback | `Loopback0 10.255.0.1` | `lo0.0 10.255.0.3` | ✓ same scheme |
| SR node SID | `prefix-sid index 1` (→16001) | `node-segment ipv4-index 3` (→16003) | ✓ same SRGB, deterministic index |
| SRGB | `global-block 16000 23999` | `srgb start-label 16000 index-range 8000` | ✓ identical range |
| TI-LFA | `fast-reroute per-prefix ti-lfa` | `backup-spf-options use-post-convergence-lsp` | ✓ same intent (Q3 HW dependency carried) |
| VPNv4 iBGP to RRs | `address-family vpnv4` to RR1/anycast | `family inet-vpn unicast` to RR1/anycast | ✓ |
| L3VPN RD/RT | `rd 10.255.0.1:100`, RT `65000:100` | `route-distinguisher 10.255.0.3:101`, `vrf-target target:65000:101` | ✓ per-PE RD, per-service RT |
| eBGP GTSM (RFC 5082) | `ttl-security` | `group CE ttl 1` | ✓ both enforce GTSM |
| Families on the wire | (implicit XR) | `family iso` + `family mpls` on each unit | ✓ Junos-specific must-have, present |
| Mgmt / no telnet | VRF MGMT, SSH-only | `delete system services telnet`, SSH, TACACS+ | ✓ |
| Control-plane protect | LPTS + CoPP intent | `lo0 filter RE-PROTECT` | ✓ same intent, platform-correct |

## Where intent needs a watch (multivendor-translator flag)
- **TI-LFA** is the same outcome but a different knob per platform — verify behaviour is equivalent in test, not just that both lines exist.
- **CoS vs MQC:** Junos `class-of-service` and IOS-XR `policy-map` express the same 5-class model in different vocabularies — confirm DSCP→forwarding-class mapping matches end-to-end.

## VERDICT: **PASS**
No CRITICAL/HIGH/MEDIUM from the pre-pass; cross-vendor intent preserved. The one carried open item
(TI-LFA HW dependency, HLD Q3) is operational, closed in migration Phase 3 — not a config defect.
