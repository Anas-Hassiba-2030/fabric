# Worked example — Acme DC EVPN-VXLAN fabric

A second engagement threaded through WRATH's phases — a **data-center fabric** (not an SP core), to
show breadth and that the gates work on a different domain/vendor (NX-OS instead of IOS-XR). Artifacts
**connect**: the LLD's VNI/IPAM plan shows up in the config, and the Validator's `config_lint` runs on
that config in `run_tests.sh`.

## The chain
| # | Artifact | Phase / Agent / Skill | Connects to |
|---|---|---|---|
| 00 | [requirements-brief](00-requirements-brief.md) | Discovery · `discovery` · `requirements-intake` | greenfield, 10-device leaf-spine, PCI, NX-OS; resolves underlay/BUM/multihoming |
| 01 | [hld](01-hld.md) | Design · `designer-hld` · `hld-generator` | EVPN-VXLAN trade-off + topology; raises the VTEP-scale HIGH |
| 02 | [lld](02-lld.md) | Implement · `designer-lld` · `lld-generator` | IPAM, VNI plan (L2VNI 10010 / L3VNI 50001), iBGP-EVPN, anycast GW |
| 03 | [config-leaf1.cfg](03-config-leaf1.cfg) | Implement · `config-engineer` · `config-generator` | NX-OS realization of the LLD — idempotent, lockout-safe, feature-gated |
| 04 | [validation](04-validation.md) | Implement · `validator` · `config-audit` | **PASS** (config_lint nxos, 0 findings) + judgment pass + acceptance criteria |

## Proof it's real
`03-config-leaf1.cfg` passes the audit gate (`config_lint --vendor nxos`, exit 0) and is part of the
repo's test suite — so it can't silently rot. The SP-core example lives in `../example-acme-sp/`.
