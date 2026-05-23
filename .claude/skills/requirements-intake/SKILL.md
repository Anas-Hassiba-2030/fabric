---
name: requirements-intake
description: Structured capture of network requirements from messy input (RFP, RFI, call notes, email chains, topology dumps) into a gap-free brief, and generation of the right clarifying-question set. Use at the start of any engagement or whenever the problem is underspecified. Loaded by the Discovery agent.
---

# Requirements Intake

Turn messy input into a structured, gap-free brief — and surface the questions that actually change
the design. The discipline: **never invent a value for an architecture-critical field; ask for it.**

## Procedure

1. **Read everything provided** + prior memory for this customer (`fabric/memory/customers/<name>.md`).
2. **Populate the brief** (`assets/brief-template.md`). Fill only what's stated.
3. **Score each empty field**: does it change the *architecture* (scale, SLA, security baseline, vendor constraint, brownfield/greenfield) or just a detail? Tag accordingly.
4. **Write clarifying questions** for the architecture-critical gaps — specific and answerable, not "what do you need?" Example: *"Is the 50ms convergence target end-to-end service restoration or IGP-only, and is it contractual?"*
5. **State assumptions** for anything you must proceed on without an answer — flagged, never buried.

## Architecture-critical fields (always pin these down)
- Greenfield vs brownfield (brownfield ⇒ rollback + migration plan are mandatory)
- Scale: device count, route scale, bandwidth, user/site count, growth horizon
- SLA/SLO: availability, convergence, latency/jitter — and whether contractual
- Security baseline: NIST/CIS/PCI/customer policy; segmentation; encryption needs
- Vendor constraints / existing estate
- Timeline + change windows + budget envelope

## Output
The completed brief + a numbered, prioritized open-questions list (architecture-critical first). Hand
back to the Orchestrator as a summary.
