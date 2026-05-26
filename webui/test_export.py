#!/usr/bin/env python3
"""Proof that WRATH run export bundles the stack faithfully — WITHOUT an API key.

A saved run record must render to one Markdown document that preserves pipeline order, every
deliverable, grounding verdicts, recalled memory, and the trust summary.

Run:  python webui/test_export.py     (no key, deterministic)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_run  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


rec = {
    "id": "x", "ts": "2026-05-26T00:00:00Z", "problem": "SR-MPLS L3VPN core", "mode": "demo",
    "stages": [{"id": "discovery"}, {"id": "hld"}, {"id": "trust"}],
    "recall": [{"kind": "pattern", "title": "SR-MPLS core", "ref": "p.md", "why": "shares: sr-mpls"}],
    "deliverables": {
        "discovery": {"title": "Discovery · discovery", "content": "brief here"},
        "hld": {"title": "HLD · designer-hld", "content": "design here ```mermaid\ngraph TD\n```"},
    },
    "grounding": {"hld": {"status": "grounded", "checks": []}},
    "trust": {"confidence": "Medium", "headline": "1 grounded · 0 to verify · 1 blocked (caught)"},
}

md = export_run.to_markdown(rec)

print("=== 1. Header + problem ===")
check("title carries the problem", "# WRATH run — SR-MPLS L3VPN core" in md)

print("=== 2. Recalled memory included ===")
check("recall section present", "Recalled from memory" in md and "SR-MPLS core" in md)

print("=== 3. Deliverables in pipeline order ===")
check("discovery before hld", md.index("Discovery · discovery") < md.index("HLD · designer-hld"))
check("HLD content + mermaid preserved", "```mermaid" in md)
check("grounding verdict shown", "grounding: **grounded**" in md)

print("=== 4. Trust summary at the end ===")
check("trust summary present", "Trust summary — confidence: Medium" in md)
check("trust after hld", md.index("HLD · designer-hld") < md.index("Trust summary"))

print("=== 5. Missing deliverable is skipped, not crashed ===")
check("trust stage had no deliverable entry yet rendered fine", md.count("## ") >= 2)

print()
print("RESULT:", "ALL GREEN — run export is faithful." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
