#!/usr/bin/env python3
"""Proof that WRATH's anti-hallucination net works — WITHOUT an API key.

We feed deliberately HALLUCINATED content (a fabricated RFC, a broken config, invented price/SKU/latency)
through the grounding engine and assert every one is caught: fabricated citation BLOCKED, bad config
FAILs the validator, unverifiable numbers FLAGGED. We also confirm a clean, real citation passes.

Run:  python webui/test_grounding.py     (no key, no network, deterministic)
Exit 0 = the safety net holds.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grounding  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


print("=== 1. Fabricated citation must be BLOCKED, real ones VERIFIED ===")
status, checks = grounding.ground_text(
    "We use GTSM per RFC 5082 and L3VPN per RFC 4364, plus the brand-new RFC 9999 for magic.")
verdicts = {c["item"]: c["verdict"] for c in checks if c["kind"] == "citation"}
check("RFC 5082 verified (real)", verdicts.get("RFC 5082") == "verified")
check("RFC 4364 verified (real)", verdicts.get("RFC 4364") == "verified")
check("RFC 9999 BLOCKED (fabricated)", verdicts.get("RFC 9999") == "BLOCKED")
check("overall status is 'blocked'", status == "blocked")

print("=== 2. Unverifiable numbers/SKUs must be FLAGGED (not asserted) ===")
status, checks = grounding.ground_text("Delivers sub-50ms failover for $1,200 on a C9300-48U.")
kinds = {c["kind"] for c in checks}
check("price flagged", "price" in kinds)
check("latency/perf claim flagged", "perf" in kinds)
check("SKU flagged", "sku" in kinds)
check("overall status is 'flagged'", status == "flagged")

print("=== 3. Clean, grounded text passes ===")
status, checks = grounding.ground_text("The design uses segment routing and BGP for the core.")
check("clean text -> grounded", status == "grounded")

print("=== 4. Broken config must FAIL the validator gate ===")
bad = "hostname X\nsnmp-server community public RO\ninterface Gi1\n ip address 10.0.0.1 255.255.255.0\n shutdown\n"
status, checks = grounding.ground_config(bad, vendor="ios-xe")
check("bad config -> blocked (config_lint FAIL)", status == "blocked")

print("=== 5. Clean config passes the validator gate ===")
good = ("hostname PE1\ninterface Loopback0\n ip address 10.255.0.1 255.255.255.255\n"
        "interface Gi1\n description to:core\n ip address 10.0.0.0 255.255.255.254\n mtu 9216\n no shutdown\n")
status, checks = grounding.ground_config(good, vendor="ios-xe")
check("clean config -> grounded (config_lint PASS)", status == "grounded")

print()
print("RESULT:", "ALL GREEN — the anti-hallucination net holds (no API key needed)." if not fails
      else f"{fails} FAILURE(S) — the net has a hole.")
sys.exit(1 if fails else 0)
