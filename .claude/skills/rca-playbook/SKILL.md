---
name: rca-playbook
description: Structured root-cause analysis as a ReAct loop — symptom statement, layered hypothesis tree (physical→link→IGP→BGP→service→policy→control-plane), evidence per hypothesis (the show/telemetry/log that confirms or kills it), isolation to a proven cause, and fix + verification. Use when the problem is "it's broken/slow/flapping", not "design me X". Loaded by the Troubleshooter agent.
---

# RCA Playbook

Structured root-cause analysis, not guess-and-check. Work it as a ReAct loop: **hypothesize → gather
evidence → isolate → repeat until the cause is proven.** Core discipline: **don't declare a root cause
you haven't proven with evidence** (House Rule 7).

## Method
1. **Symptom statement** — what is observed, since when, what changed (the highest-yield question),
   blast radius (who/what is affected), and what is *still working* (bounds the problem).
2. **Hypothesis tree** — enumerate plausible causes **layer by layer**:
   physical → link/L2 → IGP → BGP → service (VRF/EVPN) → policy/QoS/ACL → control-plane/scale → software defect.
   Rank by **likelihood × ease-of-test** (cheap, decisive tests first). See `references/hypothesis-tree.md`.
3. **Evidence** — for each hypothesis, name the exact `show`/telemetry/log that confirms or kills it.
   Read what's provided; request specific outputs if missing. Suspect a version-specific defect? Look up
   the bug/PSIRT advisory via WebSearch and ground it (House Rule 4).
4. **Isolate** — narrow to the proven root cause. Separate **root cause** from **contributing factors**
   (the thing that broke vs the things that made it worse/possible).
5. **Fix + verify** — the change, and the test that proves it resolved (not just "errors stopped").

## Output contract
```
## RCA — <incident>
- Timeline (what happened, when)
- Root cause (proven, with the evidence)
- Contributing factors
- Fix (+ verification test)
- Prevention (what stops a recurrence)
```

## Discipline
- A correlation is not a cause — prove it.
- Any fix touching a live device is gated by the destructive-action-guard + Kamal (House Rule 6).
- If evidence is missing to prove the cause, say so and name the exact output you need — don't guess.

Return the RCA; lead with the proven root cause and the verification.
