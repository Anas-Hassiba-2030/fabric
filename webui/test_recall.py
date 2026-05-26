#!/usr/bin/env python3
"""Proof that WRATH's memory recall surfaces relevant prior knowledge — WITHOUT an API key.

House Rule 8 (compounding memory) / session-start rule: never start cold. We assert recall finds the
committed SR-MPLS pattern for a matching problem, prefers curated knowledge, ignores unrelated
problems, and matches on whole words only (no substring noise).

Run:  python webui/test_recall.py     (no key, deterministic; reads the committed memory tree)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recall  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


print("=== 1. A matching problem recalls the committed SR-MPLS pattern ===")
m = recall.recall("Design an SR-MPLS L3VPN core for a multi-site SP")
check("at least one match", len(m) >= 1)
check("top match is curated (pattern or customer), not a raw run", m and m[0]["kind"] in ("pattern", "customer"))
check("a pattern is among the matches", any(x["kind"] == "pattern" for x in m))
check("shared terms include sr-mpls and l3vpn", m and {"sr-mpls", "l3vpn"} <= set(m[0]["shared"]))
check("each match carries a 'why'", all(x["why"] for x in m))

print("=== 2. An unrelated problem recalls nothing (no false positives) ===")
check("office wifi captive portal -> no match", recall.recall("office wifi captive portal") == [])

print("=== 3. Term matching is whole-word (no substring noise) ===")
t = recall.terms("we scored a corecard for the typescript pipeline")
check("'core' not matched inside 'corecard'/'scored'", "core" not in t)
check("real term still matched", "evpn" in recall.terms("an EVPN data center"))

print("=== 4. Below-threshold overlap does not match ===")
check("a single shared term is below min_score", recall.recall("just the core, nothing else") == []
      or all(x["score"] >= 2 for x in recall.recall("just the core, nothing else")))

print("=== 5. Rendered block cites the source ref; empty stays empty ===")
block = recall.render(m)
check("render shows the memory heading", "Recalled from memory" in block)
check("render cites a ref path", any(x["ref"] in block for x in m))
check("no matches -> empty render", recall.render([]) == "")

print("=== 6. Deterministic ===")
check("same problem -> identical matches", recall.recall("SR-MPLS L3VPN core") == recall.recall("SR-MPLS L3VPN core"))

print()
print("RESULT:", "ALL GREEN — memory recall compounds (no key needed)." if not fails
      else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
