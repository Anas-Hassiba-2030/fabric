#!/usr/bin/env python3
"""OpsRAG typed knowledge-graph schema (thesis O1).

Six node types and five edge types — the formalisation that the WRATH memory tree (`patterns/`,
`customers/`, saved runs) gets lifted into. Pure stdlib dataclasses; no new dependencies.

    NODE_TYPES = {Concept, Command, Configuration, Symptom, RootCause, Runbook}
    EDGE_TYPES = {verifies, diagnoses, depends_on, supersedes, contradicts}

Every node and edge carries provenance pointing to the source (file/RFC/span), a confidence score,
and an `authored` flag so curated artefacts can be distinguished from feedback-loop-learned ones.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


NODE_TYPES = {"Concept", "Command", "Configuration", "Symptom", "RootCause", "Runbook"}
EDGE_TYPES = {"verifies", "diagnoses", "depends_on", "supersedes", "contradicts"}


@dataclass
class Provenance:
    source: str                    # file path, RFC id, URL — never empty
    span: Optional[str] = None     # line range, paragraph id, or section anchor
    confidence: float = 0.5
    authored: bool = True          # True = curated; False = learned via feedback loop


@dataclass
class Node:
    id: str
    type: str                      # one of NODE_TYPES
    name: str
    provenance: Provenance
    attrs: Dict = field(default_factory=dict)


@dataclass
class Edge:
    src: str
    dst: str
    rel: str                       # one of EDGE_TYPES
    provenance: Provenance


@dataclass
class Graph:
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)

    def add(self, n: Node):
        self.nodes[n.id] = n

    def link(self, src: str, dst: str, rel: str, prov: Provenance):
        self.edges.append(Edge(src=src, dst=dst, rel=rel, provenance=prov))


def validate(g: Graph) -> dict:
    """Referential-integrity + type check. Returns {ok, errors, nodes, edges, by_type}."""
    errors = []
    by_type: Dict[str, int] = {}
    for nid, n in g.nodes.items():
        if n.type not in NODE_TYPES:
            errors.append(f"node {nid}: invalid type {n.type!r}")
        if not (n.provenance and n.provenance.source):
            errors.append(f"node {nid}: missing provenance.source")
        by_type[n.type] = by_type.get(n.type, 0) + 1
    for i, e in enumerate(g.edges):
        if e.rel not in EDGE_TYPES:
            errors.append(f"edge[{i}]: invalid rel {e.rel!r}")
        if e.src not in g.nodes:
            errors.append(f"edge[{i}]: dangling src {e.src!r}")
        if e.dst not in g.nodes:
            errors.append(f"edge[{i}]: dangling dst {e.dst!r}")
    return {"ok": not errors, "errors": errors,
            "nodes": len(g.nodes), "edges": len(g.edges), "by_type": by_type}


def to_dict(g: Graph) -> dict:
    return {"nodes": {k: asdict(v) for k, v in g.nodes.items()},
            "edges": [asdict(e) for e in g.edges]}
