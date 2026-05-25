# Worked example — Acme SP core modernization

A single engagement threaded through **every FABRIC phase**, with **connected** artifacts: values flow
forward and each gate acts on the previous output. This is the proof the phases work together, and a
reference for the shape of each deliverable.

## The chain (and how the artifacts connect)
| # | Artifact | Phase / Agent / Skill | Connects to |
|---|---|---|---|
| 00 | [requirements-brief](00-requirements-brief.md) | Discovery · `discovery` · `requirements-intake` | sets R1–R7, scale, the open questions |
| 01 | [hld](01-hld.md) | Design · `designer-hld` · `hld-generator` | answers the brief with trade-offs + topology; raises Q3 (TI-LFA HW) |
| 02 | [lld](02-lld.md) | Implement · `designer-lld` · `lld-generator` | turns the HLD into IPAM/SID/BGP — **PE1 = 10.255.0.1, prefix-SID 16001** |
| 03 | [config-pe1.cfg](03-config-pe1.cfg) | Implement · `config-engineer` · `config-generator` | builds PE1 (IOS-XR) **from the LLD values** (loopback, SID, RD, GTSM) |
| 03b | [config-pe3.cfg](03b-config-pe3.cfg) | Implement · `config-engineer` + `multivendor-translator` | builds PE3 (**Junos**) — same intent, different vendor (R4) |
| 04 | [validation-report](04-validation-report.md) | Implement gate · `validator` · `config-audit` | runs `config_lint.py` **on 03**; PASS with the MTU note cleared by judgment |
| 04b | [validation-pe3](04b-validation-pe3.md) | Implement gate · `validator` + `multivendor-translator` | lints **03b** (clean) + a **cross-vendor parity** table (intent survives the crossing) |
| 05 | [bom](05-bom.md) | Sell · `bom-commercials` · `bom-builder` | quantities trace to the **LLD node/link tables** |
| 06 | [sow](06-sow.md) | Sell · `sow-writer` · `sow-writer` | scope/acceptance tied to the **brief's success criteria** |
| 07 | [exec-summary](07-exec-summary.md) | Sell · `exec-storyteller` · `exec-deck` | the business framing of the same solution |
| 08 | [migration-runbook](08-migration-runbook.md) | Operate · `migration-planner` · `migration-runbook` | cutover with rollback every step; Phase 3 **closes HLD Q3** |

## The thread to notice
`10.255.0.1` / prefix-SID `16001` / RD `10.255.0.1:100` originate in the **LLD (02)**, appear verbatim
in the **config (03)**, are checked by the **validator (04)**, and the device count drives the **BoM
(05)**. The HLD's honest open question **Q3 (TI-LFA depends on linecard BFD-in-HW)** is carried — never
silently resolved — through the validation report and is explicitly closed in **migration Phase 3**.
That carry-through is House Rules 1, 4, and 7 in action.

> Worked example for demonstration. A real engagement verifies SKUs/standards live and is gated by the
> Critic on each design and the destructive-action-guard before any live push.
