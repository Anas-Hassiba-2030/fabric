---
description: Verify the whole WRATH system is working — run the full test suite and the doctor, then report.
allowed-tools: Bash(bash run_tests.sh), Bash(python webui/doctor.py)
---

Confirm WRATH is functional and not hallucinating:

1. Run `bash run_tests.sh` and report the green/red line for every check (especially the anti-hallucination, clarify-gate, validator, citation-guard, trust, routing, and pipeline-integrity proofs).
2. Run `python webui/doctor.py` and report the diagnosis. If `ANTHROPIC_API_KEY` is set, note the real Opus 4.7 call result.
3. If anything is RED, diagnose the root cause and propose the fix — do not paper over it.

Report a concise PASS/FAIL summary and the total number of checks.
