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


if __name__ == "__main__":
    print(mermaid_block(" ".join(sys.argv[1:]) or "SR-MPLS L3VPN core"))
