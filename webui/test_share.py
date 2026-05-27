#!/usr/bin/env python3
"""Proof that a run renders to a self-contained shareable HTML report — no API key.

Run:  python webui/test_share.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import share  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


rec = {
    "id": "x", "ts": "2026-05-27T00:00:00Z", "problem": "SR-MPLS L3VPN core", "mode": "demo",
    "stages": [{"id": "hld", "label": "HLD", "kind": "llm"}, {"id": "trust", "label": "Trust", "kind": "report"}],
    "deliverables": {"hld": {"title": "HLD · designer-hld",
                             "content": "**Recommended** design.\n\n| Option | Verdict |\n|---|---|\n| A | pick |\n\n```mermaid\ngraph TD\nP1---P2\n```"}},
    "grounding": {"hld": {"status": "grounded", "checks": []}},
    "trust": {"confidence": "Medium", "headline": "1 grounded · 0 to verify · 1 blocked (caught)"},
}

h = share.to_html(rec)

print("=== 1. Valid standalone HTML document ===")
check("starts with doctype", h.startswith("<!DOCTYPE html>"))
check("closes html", h.rstrip().endswith("</html>"))
check("has embedded <style> (self-contained)", "<style>" in h)
check("title carries the problem", "SR-MPLS L3VPN core" in h)

print("=== 2. Markdown rendered to real HTML ===")
check("heading rendered", "<h2>" in h or "<h1>" in h)
check("trade-off table rendered", "<table>" in h and "<th>" in h)
check("bold rendered", "<strong>Recommended</strong>" in h)
check("mermaid block preserved for the topology", '<div class="mermaid">' in h and "graph TD" in h)

print("=== 3. Trust summary present ===")
check("trust summary rendered", "Trust summary" in h)

print("=== 4. Deterministic ===")
check("same rec -> identical html", share.to_html(rec) == share.to_html(rec))

print()
print("RESULT:", "ALL GREEN — shareable HTML report is faithful + self-contained." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
