#!/usr/bin/env python3
"""WRATH auto topology — infer a sensible reference topology from the problem (P1).

Every HLD should show a picture, not just prose. This infers a reference topology (roles, redundancy
pairs, failure domains) from the problem keywords and renders it as an inline Mermaid block. The
*mechanics* of JSON-spec -> Mermaid live in the topology-diagram skill's to_mermaid.py (single source
of truth); this module supplies the *judgment* of what a reasonable starting topology is.

Deterministic (no LLM/key), so it is fully testable — see webui/test_topology.py.

    infer_spec(problem) -> {direction, groups, nodes, edges}
    mermaid_block(problem) -> "```mermaid ... ```"
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
_HELPER = os.path.join(REPO, ".claude", "skills", "topology-diagram", "scripts", "to_mermaid.py")

# Reuse the skill's converter so spec->Mermaid logic has exactly one implementation.
_spec = importlib.util.spec_from_file_location("to_mermaid", _HELPER)
_tm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tm)
to_mermaid = _tm.to_mermaid


def _is_dc(p):
    return any(k in p for k in ["data center", "datacenter", "evpn", "vxlan", "dci", "leaf", "spine"])


def infer_spec(problem):
    """Infer a reference topology spec. Always a redundant core; a leaf-spine DC fabric for
    data-center problems, otherwise two dual-homed PE sites with CEs."""
    p = (problem or "").lower()
    nodes = {"P1": "P1 / RR", "P2": "P2 / RR"}
    groups = {"Core (SR-MPLS)": ["P1", "P2"]}
    edges = [["P1", "P2", "iBGP RR mesh"]]

    if _is_dc(p):
        nodes.update({"S1": "Spine1", "S2": "Spine2", "L1": "Leaf1", "L2": "Leaf2", "H1": "Host / CE"})
        groups["Data center (EVPN-VXLAN)"] = ["S1", "S2", "L1", "L2"]
        groups["Workload"] = ["H1"]
        edges += [["L1", "S1"], ["L1", "S2"], ["L2", "S1"], ["L2", "S2"],
                  ["S1", "P1"], ["S2", "P2"],
                  ["H1", "L1"], ["H1", "L2", "dual-homed (ESI-LAG)"]]
    else:
        for i in (1, 2):
            pe, peb, ce = f"PE{i}", f"PE{i}b", f"CE{i}"
            nodes.update({pe: pe, peb: f"{pe}-b", ce: f"CE{i}"})
            groups[f"Site {i}"] = [pe, peb, ce]
            edges += [[pe, "P1"], [peb, "P2"], [ce, pe], [ce, peb, "dual-homed"]]

    return {"direction": "TD", "groups": groups, "nodes": nodes, "edges": edges}


def mermaid_block(problem):
    return "```mermaid\n" + to_mermaid(infer_spec(problem)) + "\n```"


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def to_svg(spec):
    """Render the spec to a standalone dark-theme SVG — dependency-free, works offline.

    Groups become columns; nodes stack within a column; edges are drawn between node centres."""
    groups, nodes, edges = spec.get("groups", {}), spec.get("nodes", {}), spec.get("edges", [])
    COLW, NW, NH, VGAP, TOP, PAD = 210, 168, 46, 20, 64, 22
    pos, cols = {}, list(groups.items())
    for ci, (_g, members) in enumerate(cols):
        x = PAD + ci * COLW
        for ri, nid in enumerate(members):
            y = TOP + ri * (NH + VGAP)
            pos[nid] = (x, y)
    rows_max = max((len(m) for _g, m in cols), default=1)
    W = PAD * 2 + max(len(cols), 1) * COLW
    H = TOP + rows_max * (NH + VGAP) + PAD
    L = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="system-ui,Segoe UI,Arial">',
         f'<rect width="{W}" height="{H}" rx="14" fill="#0b1120"/>',
         '<defs><marker id="a" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto">'
         '<path d="M0,0 L7,3 L0,6 Z" fill="#36e0c8"/></marker></defs>']
    # edges first (under nodes)
    for e in edges:
        if e[0] in pos and e[1] in pos:
            ax, ay = pos[e[0]][0] + NW / 2, pos[e[0]][1] + NH / 2
            bx, by = pos[e[1]][0] + NW / 2, pos[e[1]][1] + NH / 2
            L.append(f'<line x1="{ax:.0f}" y1="{ay:.0f}" x2="{bx:.0f}" y2="{by:.0f}" stroke="#33405e" stroke-width="2" marker-end="url(#a)"/>')
            if len(e) >= 3 and e[2]:
                L.append(f'<text x="{(ax + bx) / 2:.0f}" y="{(ay + by) / 2 - 4:.0f}" fill="#8a96b4" font-size="10" text-anchor="middle">{_esc(e[2])}</text>')
    # group labels
    for ci, (g, _m) in enumerate(cols):
        x = PAD + ci * COLW
        L.append(f'<text x="{x:.0f}" y="{TOP - 24:.0f}" fill="#6ea8ff" font-size="12" font-weight="700">{_esc(g)}</text>')
    # nodes
    for nid, (x, y) in pos.items():
        L.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{NW}" height="{NH}" rx="10" fill="#16213a" stroke="#3a486a"/>')
        L.append(f'<text x="{x + NW / 2:.0f}" y="{y + NH / 2 + 4:.0f}" fill="#eef2fb" font-size="12.5" font-weight="600" text-anchor="middle">{_esc(nodes.get(nid, nid))}</text>')
    L.append("</svg>")
    return "\n".join(L)


def svg_for(problem):
    return to_svg(infer_spec(problem))


if __name__ == "__main__":
    print(mermaid_block(" ".join(sys.argv[1:]) or "SR-MPLS L3VPN core"))
