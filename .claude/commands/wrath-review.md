---
description: Red-team the current design with a fresh Critic before it goes to Kamal (post-design-review gate).
argument-hint: [path to the HLD/LLD/config, or leave blank for the latest deliverable]
---

Run the **post-design-review** gate (CLAUDE.md §4). Spawn the `critic` agent with **fresh context** (it must not have written what it reviews) on:

$ARGUMENTS

The Critic must:
1. Red-team the design/config adversarially — failure modes, blast radius, security posture, convergence claims and their hardware dependencies, MTU/rollback coverage, standards grounding.
2. Return a verdict (ACCEPT / ACCEPT-WITH-FIXES) with a severity-tagged defect list.
3. On ACCEPT-WITH-FIXES, route the findings back to the producing agent and re-review after revision.

Honor the Critic-intensity expectation: demand fixes for HIGH/MEDIUM findings; nothing customer-facing ships un-critiqued.
