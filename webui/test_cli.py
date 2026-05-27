#!/usr/bin/env python3
"""Proof that headless WRATH runs end-to-end and emits a faithful bundle — no API key.

Run:  python webui/test_cli.py
"""
import os
import sys
import tempfile
import time

# Make the demo pacing instant for the test.
time.sleep = lambda *a, **k: None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli  # noqa: E402
import export_run  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


print("=== 1. A headless run converges and produces the full stack ===")
rec = cli.run_headless("Design an SR-MPLS L3VPN core for a 3-DC provider, multi-vendor", "demo", "standard")
check("record returned", bool(rec))
check("problem carried", "SR-MPLS" in rec.get("problem", ""))
for sid in ("discovery", "hld", "validate", "standards", "trust"):
    check(f"deliverable present: {sid}", sid in rec.get("deliverables", {}))
check("trust report computed", bool(rec.get("trust")))
check("standards stage blocked the fabricated RFC", rec["grounding"]["standards"]["status"] == "grounded"
      and any(c["verdict"] == "BLOCKED" for c in rec["grounding"]["standards"]["checks"]))

print("=== 2. The exported bundle is faithful ===")
md = export_run.to_markdown(rec)
check("bundle has the run header", "# WRATH run —" in md)
check("bundle includes the trust summary", "Trust summary" in md)
check("bundle tags provenance (REAL gate)", "REAL" in md)

print("=== 3. The intensity dial flows through headless (Max -> revised HLD) ===")
rec_max = cli.run_headless("Design an SR-MPLS core", "demo", "max")
check("Max produced a revised HLD (v3)", "v3" in rec_max["deliverables"]["hld"]["content"])

print("=== 4. main() writes a file and exits 0 ===")
out = os.path.join(tempfile.mkdtemp(), "bundle.md")
rc = cli.main(["Design an SR-MPLS core for an SP", "--out", out])
check("exit code 0", rc == 0)
check("file written with content", os.path.isfile(out) and os.path.getsize(out) > 200)

print()
print("RESULT:", "ALL GREEN — headless WRATH works." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
