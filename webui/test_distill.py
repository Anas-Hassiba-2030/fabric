#!/usr/bin/env python3
"""Proof that WRATH distils an accepted run into a reusable, RAG-discoverable pattern — no API key.

The compounding-memory loop only works if the distilled pattern (a) captures the design shape, (b)
carries the grounded references, and (c) is itself discoverable by Memory RAG on the next similar
problem. This test checks all three.

Run:  python webui/test_distill.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import distill  # noqa: E402
import recall  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


rec = {
    "id": "run123", "ts": "2026-05-26T00:00:00Z",
    "problem": "Brownfield migration of a 40-site SP core to SR-MPLS L3VPN on Cisco IOS-XR",
    "stages": [{"id": "hld", "label": "HLD"}], "deliverables": {"hld": {"title": "HLD", "content": "x"}},
    "grounding": {"standards": {"status": "grounded", "checks": [
        {"kind": "citation", "item": "RFC 4364", "verdict": "verified", "note": "BGP/MPLS IP VPNs", "url": "https://www.rfc-editor.org/rfc/rfc4364"},
        {"kind": "citation", "item": "RFC 9999", "verdict": "BLOCKED", "note": "fabricated"}]}},
    "trust": {"confidence": "Medium"}}

d = distill.distil(rec)

print("=== 1. Title / slug capture the design ===")
check("title mentions SR-MPLS", "SR-MPLS" in d["title"])
check("title mentions the L3VPN service", "L3VPN" in d["title"])
check("slug is filesystem-safe", d["slug"] and all(c.isalnum() or c == "-" for c in d["slug"]))

print("=== 2. Markdown has the reusable sections ===")
for sec in ("When this fits", "The shape", "Grounded references", "Provenance"):
    check(f"has '{sec}'", sec in d["markdown"])
check("transport shape line present", "Transport:" in d["markdown"])

print("=== 3. Only VERIFIED references are carried (no fabricated/blocked) ===")
check("verified RFC 4364 included", "RFC 4364" in d["markdown"])
check("blocked RFC 9999 NOT carried into the pattern", "RFC 9999" not in d["markdown"])
check("confidence recorded in provenance", "Medium" in d["markdown"])

print("=== 4. The pattern is itself RAG-discoverable (compounding loop closes) ===")
shared = recall.terms(rec["problem"]) & recall.terms(d["markdown"])
check("pattern shares >=2 network terms with the problem", len(shared) >= 2)

print("=== 5. Deterministic ===")
check("same run -> identical pattern", distill.distil(rec) == distill.distil(rec))

print()
print("RESULT:", "ALL GREEN — accepted runs compound into reusable patterns." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
