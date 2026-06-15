#!/usr/bin/env python3
"""Bootstrap the OpsRAG graph from WRATH's existing memory (thesis O2, initial step).

Lift `wrath/memory/patterns/*.md` -> Runbook nodes; `wrath/memory/customers/*.md` -> Concept nodes;
extract network-term tags as Concepts and link them via `depends_on`. The point: the graph starts with
the curated semantic memory we already accumulated, so the thesis doesn't begin from an empty graph.

Deterministic; pure stdlib.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_WEBUI = os.path.dirname(_HERE)
sys.path.insert(0, _WEBUI)
import recall  # noqa: E402
from .schema import Graph, Node, Provenance  # noqa: E402


def _title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("#"):
            return line.lstrip("# ").strip()
    return "(untitled)"


def from_memory(repo: str) -> Graph:
    g = Graph()
    base = os.path.join(repo, "wrath", "memory")

    # patterns -> Runbook nodes + linked Concept nodes from extracted tags
    pdir = os.path.join(base, "patterns")
    if os.path.isdir(pdir):
        for fn in sorted(os.listdir(pdir)):
            if not fn.endswith(".md"):
                continue
            path = os.path.join(pdir, fn)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            nid = "pattern:" + fn[:-3]
            prov = Provenance(source=f"wrath/memory/patterns/{fn}", confidence=0.85, authored=True)
            tags = sorted(recall.terms(text))
            g.add(Node(id=nid, type="Runbook", name=_title(text), provenance=prov, attrs={"tags": tags}))
            for t in tags[:6]:
                cid = "concept:" + t
                if cid not in g.nodes:
                    g.add(Node(id=cid, type="Concept", name=t,
                               provenance=Provenance(source="opsrag/vocab", confidence=1.0)))
                g.link(nid, cid, "depends_on",
                       Provenance(source=prov.source, confidence=0.7, authored=True))

    # customers -> Concept nodes (episodic context anchors)
    cdir = os.path.join(base, "customers")
    if os.path.isdir(cdir):
        for fn in sorted(os.listdir(cdir)):
            if not fn.endswith(".md") or fn.startswith("_"):
                continue
            path = os.path.join(cdir, fn)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            cid = "customer:" + fn[:-3]
            g.add(Node(id=cid, type="Concept", name=_title(text),
                       provenance=Provenance(source=f"wrath/memory/customers/{fn}",
                                             confidence=0.9, authored=True),
                       attrs={"tags": sorted(recall.terms(text))}))

    return g


if __name__ == "__main__":
    import json
    from .schema import to_dict, validate
    repo = os.path.dirname(_WEBUI)
    g = from_memory(repo)
    v = validate(g)
    print(json.dumps({"validation": v, "nodes": list(g.nodes)[:10]}, indent=2))
