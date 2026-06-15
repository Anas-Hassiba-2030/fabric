---
name: config-generator
description: Generates vendor-correct device configuration and the automation to deploy it from an approved LLD — multi-vendor (IOS-XR, IOS-XE, NX-OS, Junos) plus Python/Ansible (NETCONF-YANG, RESTCONF, pyATS). Output is idempotent, commented, mapped to the LLD, and never final until the Validator passes it. Loaded by the Config-Engineer agent.
---

# Config Generator

Turn an **approved** LLD into config an engineer can deploy — and the automation to deploy it safely.
Core discipline: **idempotent, re-runnable, commented for intent, and sequenced so you never lock
yourself out** (House Rule 2 — never final until the Validator passes).

## Inputs
1. The approved LLD + IPAM sheet from `deliverables/` (addressing, SIDs, BGP, interfaces, QoS, zones).
2. The target platform per device. **Load only the vendor reference you need** from `references/`:
   `ios-xr.md`, `ios-xe.md`, `nxos.md`, `junos.md`.

## Procedure
1. **Per device, build in dependency order** (see "Order of operations" below) directly from the LLD
   tables — every value (IP, SID, RT, description) traces to the LLD; invent nothing.
2. **Comment intent, not syntax.** `! anycast-SID for RR pair` — not `! configure bgp`.
3. **Make it idempotent.** No commands that fail or double-apply on a second run; use the platform's
   merge/replace model deliberately (see vendor refs).
4. **Build the automation package** appropriate to the estate:
   - Ansible (NETCONF-YANG / RESTCONF / CLI) for fleet rollout, or
   - Python (ncclient / RESTCONF / pyATS) for programmatic apply + structured verification.
   Include a **dry-run / check mode** and **post-checks** (does the session/route/label actually exist
   after apply?).
5. **Write a test plan**: pre-checks, apply, post-checks, and the rollback pointer (the Migration
   Planner owns full cutover; you own "this device, applied safely").

## Order of operations (the lockout trap)
Sequence so the management/routing path you depend on is the **last** thing you change and the **first**
thing you restore on rollback:
1. AAA / management plane / ACLs that could cut your session — stage, don't cut.
2. Interfaces + IGP (bring adjacency up) → SR/labels → BGP → services (VRF/EVPN) → QoS.
3. The change that could lock you out (mgmt ACL, routing to the jump host) goes behind a **commit
   confirmed / reload-in** safety net where the platform supports it.

## Outputs (to `deliverables/`)
- Config file per device (idempotent, commented, named per the LLD).
- Automation package (playbooks / scripts) with dry-run + post-checks.
- Test plan.

## Hard rule
Do **not** present config as done. Return a summary + paths and expect the Orchestrator to route it
through `validator`; fix what comes back, re-submit. Flag anything you're unsure a device will accept,
and any feature with no clean cross-vendor equivalent (hand to the Multi-Vendor Translator).
