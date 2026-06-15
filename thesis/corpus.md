# OpsRAG BGP corpus (curated)

Authoritative sources the typed-ingestion pipeline (thesis O2) will parse. Every source is
referenceable and grounded — **no invented RFCs** (House Rule 4). The MCP `wrath-standards` index
already grounds the RFC layer; this list extends it with the CVD / vendor / FRR layer.

## Normative (RFCs)
| RFC | Title | URL |
|---|---|---|
| 4271 | A Border Gateway Protocol 4 (BGP-4) | https://www.rfc-editor.org/rfc/rfc4271 |
| 4456 | BGP Route Reflection | https://www.rfc-editor.org/rfc/rfc4456 |
| 4760 | Multiprotocol Extensions for BGP-4 | https://www.rfc-editor.org/rfc/rfc4760 |
| 5065 | Autonomous System Confederations for BGP | https://www.rfc-editor.org/rfc/rfc5065 |
| 5082 | Generalized TTL Security Mechanism (GTSM) | https://www.rfc-editor.org/rfc/rfc5082 |
| 7606 | Revised Error Handling for BGP UPDATE Messages | https://www.rfc-editor.org/rfc/rfc7606 |
| 7911 | Advertisement of Multiple Paths in BGP | https://www.rfc-editor.org/rfc/rfc7911 |
| 8212 | Default EBGP Route Propagation Behaviour without Policies | https://www.rfc-editor.org/rfc/rfc8212 |
| 9234 | Route Leak Prevention using Roles in OPEN | https://www.rfc-editor.org/rfc/rfc9234 |

## Vendor / implementation (informative)
- **Cisco BGP design guide** (IOS-XR / IOS-XE) — public Cisco docs.
- **Juniper Networks BGP feature guide** — Junos docs.
- **FRRouting BGP** — `https://docs.frrouting.org/en/latest/bgp.html`. **This is the platform of the
  sandbox**, so its CLI grammar is the validator's source of truth.

## Sandbox-implementable scope (Phase 2 seed)
Faults derived from the literature above and realised in `thesis/lab/faults/`:
- session-formation (remote-as, GTSM, TCP-MD5) — RFC 4271, RFC 5082.
- path/policy (default deny per RFC 8212, role/OTC per RFC 9234, AS-path edge cases).
- MTU and link-level failure paths (operational; not RFC-normative).
- RR scoping (cluster-id, no-path-hiding) — RFC 4456.

## Provenance discipline
Every ingested artefact (Concept / Command / Configuration / Symptom / RootCause / Runbook) carries:
- `source`: file path or RFC id + section anchor;
- `confidence`: 1.0 for RFC-normative, 0.85 for curated vendor doc, ≤0.7 for learned;
- `authored`: True (curated) vs False (learned via execution-grounded feedback loop).

Decontamination note: all 300 questions in the benchmark are authored by Kamal Hassiba from
RFC text and operational experience (no LLM-generated questions). Questions requiring composition
across two RFCs are present in the `diagnose` and `apply` categories. No decontaminated split
is reported separately; the authorship guarantee is the contamination defence.
