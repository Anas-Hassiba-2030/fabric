#!/usr/bin/env python3
"""Turn a compact JSON topology spec into a Mermaid `graph` block.

Usage:
    python to_mermaid.py spec.json            # spec from file
    python to_mermaid.py < spec.json          # spec from stdin

Spec shape:
    {
      "direction": "TD",                       # TD | LR | BT | RL  (default TD)
      "groups": {"Core": ["P1","P2"], ...},    # optional subgraphs (failure domains)
      "nodes": {"P1": "P1 / RR", ...},         # optional id -> display label
      "edges": [["PE1","P1"], ["P1","P2","iBGP"]]   # [src, dst] or [src, dst, label]
    }

Deterministic by design — keep judgment in the agent, mechanics in the script (charter §3 note).
"""
import json
import sys


def _label(node_id, labels):
    text = labels.get(node_id, node_id)
    return f'{node_id}["{text}"]'


def to_mermaid(spec):
    direction = spec.get("direction", "TD")
    if direction not in {"TD", "LR", "BT", "RL"}:
        direction = "TD"
    labels = spec.get("nodes", {})
    groups = spec.get("groups", {})
    edges = spec.get("edges", [])

    grouped = set()
    lines = [f"graph {direction}"]

    for group_name, members in groups.items():
        safe = group_name.replace(" ", "_")
        lines.append(f"  subgraph {safe} [{group_name}]")
        for node_id in members:
            lines.append(f"    {_label(node_id, labels)}")
            grouped.add(node_id)
        lines.append("  end")

    # Any node referenced in edges/labels but not placed in a group.
    loose = []
    for node_id in labels:
        if node_id not in grouped:
            loose.append(node_id)
    for edge in edges:
        for node_id in edge[:2]:
            if node_id not in grouped and node_id not in labels and node_id not in loose:
                loose.append(node_id)
    for node_id in loose:
        lines.append(f"  {_label(node_id, labels)}")

    for edge in edges:
        if len(edge) >= 3 and edge[2]:
            lines.append(f"  {edge[0]} ---|{edge[2]}| {edge[1]}")
        else:
            lines.append(f"  {edge[0]} --- {edge[1]}")

    return "\n".join(lines)


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as fh:
            spec = json.load(fh)
    else:
        spec = json.load(sys.stdin)
    print("```mermaid")
    print(to_mermaid(spec))
    print("```")


if __name__ == "__main__":
    main()
