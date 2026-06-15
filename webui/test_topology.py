#!/usr/bin/env python3
"""Proof that WRATH's auto topology produces a valid, sensible Mermaid diagram — no API key.

Every HLD should show a picture. We assert the inferred topology has a redundant core, adapts to the
problem (leaf-spine for a data center, dual-homed PE sites otherwise), every edge endpoint is a
declared node, the Mermaid is renderable (bare subgraph ids, fenced block), and it is deterministic.

Run:  python webui/test_topology.py     (no key, deterministic)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import topology  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


def endpoints(spec):
    ids = set(spec["nodes"])
    for g in spec["groups"].values():
        ids.update(g)
    return ids


print("=== 1. Service-provider problem -> redundant core + dual-homed PE sites ===")
sp = topology.infer_spec("Design an SR-MPLS L3VPN core")
check("redundant RR core present", {"P1", "P2"} <= set(sp["nodes"]))
check("has PE devices", any(n.startswith("PE") for n in sp["nodes"]))
check("every edge endpoint is a declared node",
      all(e[0] in endpoints(sp) and e[1] in endpoints(sp) for e in sp["edges"]))

print("=== 2. Data-center problem -> leaf-spine fabric ===")
dc = topology.infer_spec("Build an EVPN-VXLAN data center fabric")
check("has spines", {"S1", "S2"} <= set(dc["nodes"]))
check("has leaves", {"L1", "L2"} <= set(dc["nodes"]))
check("leaf dual-homed to both spines",
      ["L1", "S1"] in dc["edges"] and ["L1", "S2"] in dc["edges"])

print("=== 3. Rendered Mermaid is well-formed ===")
block = topology.mermaid_block("SR-MPLS L3VPN core")
check("fenced mermaid block", block.startswith("```mermaid") and block.rstrip().endswith("```"))
check("declares a graph", "graph TD" in block)
check("a redundancy edge is labeled", "dual-homed" in block or "iBGP RR mesh" in block)
subgraph_ids = re.findall(r"subgraph (\S+) \[", block)
check("subgraph ids are bare tokens (no spaces/parens — Mermaid-valid)",
      all(re.fullmatch(r"[0-9A-Za-z_]+", s) for s in subgraph_ids) and subgraph_ids)

print("=== 4. Standalone SVG export (dependency-free, offline) ===")
svg = topology.svg_for("SR-MPLS L3VPN core")
check("is an <svg> document", svg.startswith("<svg") and svg.rstrip().endswith("</svg>"))
check("contains node rects", "<rect" in svg)
check("contains edges", "<line" in svg)
check("labels the redundant core", "P1 / RR" in svg)
check("labels a PE device", "PE1" in svg)
dcsvg = topology.svg_for("EVPN-VXLAN data center fabric")
check("DC svg shows a spine", "Spine1" in dcsvg)

print("=== 5. Deterministic ===")
check("same problem -> identical diagram", topology.mermaid_block("x core") == topology.mermaid_block("x core"))
check("same problem -> identical svg", topology.svg_for("x core") == topology.svg_for("x core"))

print()
print("RESULT:", "ALL GREEN — auto topology renders a valid, sensible diagram." if not fails
      else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
