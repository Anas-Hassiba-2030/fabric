---
name: config-audit
description: Adversarially audits device config/automation before it touches a device — runs a deterministic rule-based syntactic pre-pass (script), then applies judgment for correctness, security, idempotency, drift, and the session-killers. Returns PASS/FAIL with severity-tagged defects and fixes. Loaded by the Validator agent.
---

# Config Audit

You are the gate (House Rule 2). Assume the config is wrong until proven right. Two layers:
**deterministic pre-pass (script)** for the mechanical catches, then **judgment** for everything a
regex can't see.

## Procedure
1. **Run the lint pre-pass** on each config file:
   ```
   python .claude/skills/config-audit/scripts/config_lint.py <config-file> [--vendor ios-xr|ios-xe|nxos|junos]
   ```
   It auto-detects vendor if `--vendor` is omitted. It emits severity-tagged findings and exits
   non-zero if any CRITICAL/HIGH is found. Treat its output as **leads, not the verdict** — it is
   heuristic and multi-vendor-aware, not a full parser.
2. **Apply judgment** on top (the script cannot reason about intent or topology):
   - **Correctness** — values resolve against the LLD (addresses/ASNs/SIDs/RTs); no typos; references exist.
   - **Security (House Rule 5)** — CoPP/iACL or lo0 filter present; mgmt-plane hardened; no plaintext
     secrets; ACLs match the design's zones.
   - **Idempotency & drift** — safe to re-apply; nothing that fights itself; commit/feature model correct.
   - **Session-killers** — TTL/GTSM on multi-hop eBGP; MTU/MSS consistency; timer mismatches;
     order-of-operations lockout; missing `no shutdown`; risky mgmt/routing change without a confirm net.
   - **Best practice** — per vendor and per the customer's baseline.
3. **Verdict.**

## Output
```
VERDICT: PASS | FAIL
Defects (severity-tagged):
- [CRITICAL] <issue> — <impact> — <fix>
- [HIGH] / [MEDIUM] / [LOW] ...
```

## Discipline
- A FAIL with **specific fixes** beats a vague PASS. Cite the line/stanza.
- You **audit, you do not edit** — the Config Engineer applies fixes. A FAIL routes back to them
  carrying your findings; re-audit after they fix.
- Ground best-practice claims (House Rule 4); don't invent a "rule" that isn't real.
