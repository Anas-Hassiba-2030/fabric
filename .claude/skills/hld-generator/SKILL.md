---
name: hld-generator
description: Drives a High-Level Design — requirements brief → technology-selection trade-off tables → reference topology → decision log, with security designed in from the start. Use when producing an HLD for a network solution. Loaded by the Designer-HLD agent.
---

# HLD Generator

Drive a High-Level Design that survives the Critic. The core discipline (House Rule 1): **every major
choice is a trade-off table with a recommendation and a reason — never a bare verdict.**

## Procedure

1. **Frame** — design goals, hard constraints, explicit out-of-scope (from the requirements brief).
2. **Decide the major technology choices**, each as a trade-off table. See `references/tech-tradeoffs.md` for the common ones (transport, services, redundancy, control-plane). Score options on: fit, complexity, cost, risk, operability, vendor support, future-proofing. Recommend one; state why-this/why-not-the-others.
3. **Design security in** (House Rule 5): segmentation, zero-trust stance, encryption (MACsec/IPsec), control-plane protection (CoPP/iACL/GTSM), management-plane hardening. This is part of the architecture, not an appendix.
4. **Reference topology** — use the `topology-diagram` skill (Mermaid). Show roles, redundancy, failure domains.
5. **Resiliency analysis** — what breaks, what survives, the honest convergence story (and what hardware/feature it depends on).
6. **Decision log** — decision → alternatives → why → underlying assumption.

## Trade-off table shape
```
| Option | Fit | Complexity | Cost | Risk | Operability | Verdict |
|--------|-----|-----------|------|------|-------------|---------|
| A      | ... | ...       | ...  | ...  | ...         | ◄ recommend — <reason> |
| B      | ... | ...       | ...  | ...  | ...         | rejected — <reason>    |
```

## Pre-empt the Critic
Before returning, self-check: convergence claim honest about its hardware dependency? security in, not
bolted on? failure domains bounded? scale ceiling stated? unstated assumption surfaced? Grounding
verified (House Rule 4)? Fixing these now saves a reject-loop.

## Output
HLD doc (the 8-section contract in `agents/designer-hld.md`) written to `deliverables/`, + a summary.
