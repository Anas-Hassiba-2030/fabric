# Validation Report — PE1 config

*Phase: Implement (gate). Skill: `config-audit`. Agent: `validator`. Status: worked example.*
*Gates `03-config-pe1.cfg` before it could touch a device (House Rule 2).*

## Layer 1 — deterministic lint pre-pass (actual tool output)
```
$ python .claude/skills/config-audit/scripts/config_lint.py \
        deliverables/example-acme-sp/03-config-pe1.cfg --vendor ios-xr

# config_lint — vendor: ios-xr — 1 finding(s)
[MEDIUM] inconsistent MTU values [1500, 9216] — verify end-to-end path MTU
# pre-pass: clean — judgment still required
```
(exit 0 — no CRITICAL/HIGH)

## Layer 2 — judgment (the script can't reason about intent)
| Area | Finding | Disposition |
|---|---|---|
| MTU [1500, 9216] | pre-pass MEDIUM | **Expected by design** — core links are jumbo (9216) for MPLS/label overhead; the customer-facing `Gi0/0/0/1` is 1500 to match the CE. No end-to-end jumbo path crosses the 1500 link. **Accepted.** |
| Correctness | loopback 10.255.0.1, prefix-SID index 1 (→16001), NET `…0001.00`, RD `10.255.0.1:100` | All match `02-lld.md`. ✓ |
| Security | mgmt in VRF MGMT, SSH-only, TACACS+ key not plaintext, no telnet; LPTS noted | ✓ control + mgmt plane covered (House Rule 5) |
| eBGP edge | `ttl-security` (GTSM, RFC 5082) + `maximum-prefix 1000 80` + inbound route-policy | ✓ session-killer + spoofing covered |
| Idempotency | two-stage commit, merge semantics, `no shutdown` present | ✓ safe to re-apply |
| Order of ops | mgmt/AAA staged first, lockout-risky change behind `commit confirmed 5` | ✓ |
| Open item | TI-LFA depends on linecard BFD-in-HW (HLD Q3) | ⚠ **carry to go/no-go** — verify before relying on the sub-50ms SLA |

## VERDICT: **PASS** (with one carried open item)
Defects:
- *(none CRITICAL/HIGH)*
- [MEDIUM] MTU mix — reviewed, **expected by design**, accepted.
- [INFO] TI-LFA HW dependency (Q3) — not a config defect; verify operationally before SLA sign-off.

Config may proceed to staged deployment via the migration runbook (still gated by the
destructive-action-guard + Kamal for any live push).
