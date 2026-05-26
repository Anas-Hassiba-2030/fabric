# Clarifying-question bank — the architecture-critical dimensions

The single biggest quality lever in WRATH: **ask the right missing question before designing, never
assume** (House Rule 7). A wrong assumption here poisons every downstream agent. Walk these
dimensions on every engagement; for each one the input does *not* answer, raise the question and mark
the brief **not ready for design** until a blocking dimension is resolved.

The deterministic gate in `webui/clarify.py` mirrors this list (its `analyze()` flags the same
dimensions). Keep the two in sync when you add a dimension.

## Blocking — design must NOT start until these are answered

| Dimension | Why it changes the architecture | Ask |
|---|---|---|
| **Greenfield vs brownfield** | Brownfield ⇒ a per-step rollback + phased migration are mandatory (House Rule 3); greenfield frees the design. | "Is this greenfield or brownfield? If brownfield, what is live today and what is the change-window tolerance?" |
| **Scale & growth** | Device/route/bandwidth scale sets platform class, RR/area design, and headroom. | "Device/site count, route/prefix scale, today's and 3-year traffic volumes, and growth assumptions?" |
| **SLA / SLO targets** | Availability + convergence targets drive redundancy, FRR/TI-LFA, and whether HW support is required. | "Availability target, convergence (end-to-end vs IGP-only, contractual?), latency/jitter targets?" |
| **Vendor / platform / version** | Feature availability, EoL, and config dialect all hinge on this. | "Which vendor(s), platforms and software versions are mandated or in play?" |

## Should-clarify — improves the design, not blocking

| Dimension | Ask |
|---|---|
| **Security & compliance baseline** | "Which baseline applies (NIST/CIS/PCI/customer policy), and what segmentation/encryption is required?" (Security is designed in — House Rule 5.) |
| **Timeline, change windows & budget** | "Timeline, fixed maintenance/change windows, and budget envelope?" |
| **Services & traffic profile** | "What must this carry — L2/L3VPN, multicast, voice/QoS, internet/peering?" |

## How to ask well
- **Specific, answerable, one decision each.** Not "what are the requirements?" but *"Is the 50ms
  convergence target end-to-end service restoration or IGP-only, and is it contractual?"*
- **Prioritize architecture-critical over cosmetic.** Lead the brief with the blocking questions.
- **State an assumption only when you must proceed without an answer** — flagged, never buried, and
  reflected in the confidence of the deliverable.
