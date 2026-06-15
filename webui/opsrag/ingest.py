#!/usr/bin/env python3
"""OpsRAG typed corpus ingestion — Phase 3 foundation.

Turns raw BGP text sources (FRR/IOS/Junos command output, RFC sections, `router bgp` stanzas)
into typed nodes that can be merged into the OpsRAG knowledge graph.

Extractors:
  cli_extractor(text, source)     → list[Node] (Command + Configuration nodes)
  rfc_extractor(text, source)     → list[Node] (Concept + RootCause candidates)
  link_nodes(nodes)               → list[Edge]  (depends_on edges inferred from cross-references)

Phase 3 adds these into the bootstrapped graph from `bootstrap.from_memory()`. The dense-RAG
baseline (the "generic RAG" comparator for RQ1) runs over the same text without the typing step.

Pure stdlib. No external NLP library required for the baseline; the LLM-driven extractor in
Phase 4 will call the Anthropic API for richer entity extraction.
"""
import re
from typing import List, Tuple

from .schema import EDGE_TYPES, NODE_TYPES, Edge, Graph, Node, Provenance


# CLI command patterns that map to typed nodes.
_SHOW_CMD_RE = re.compile(
    r"^(show\s+(?:bgp|ip\s+bgp|interface|ip\s+route|mpls|isis|ospf)\S*)",
    re.IGNORECASE | re.MULTILINE,
)
_ROUTER_BGP_RE = re.compile(
    r"(router\s+bgp\s+\d+(?:\n(?:[ \t]+.+)?)*)",
    re.IGNORECASE,
)
_NEIGHBOR_RE = re.compile(
    r"neighbor\s+(\S+)\s+(remote-as|password|route-map|prefix-list|update-source)\s*(\S*)",
    re.IGNORECASE,
)

# RFC section patterns — lines that start a normative clause ("MUST", "SHALL", "REQUIRED").
_RFC_NORMATIVE_RE = re.compile(r"\b(MUST|SHALL|REQUIRED|SHOULD|RECOMMENDED|MAY|OPTIONAL)\b")
_RFC_SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*\.?\s+\S.{5,60})\s*$", re.MULTILINE)


def _make_provenance(source: str, confidence: float = 0.8) -> Provenance:
    return Provenance(source=source, authored=False, confidence=confidence)


def cli_extractor(text: str, source: str) -> List[Node]:
    """Extract Command and Configuration nodes from CLI text (command output or config stanza)."""
    nodes: List[Node] = []
    seen: set = set()

    for m in _SHOW_CMD_RE.finditer(text):
        cmd = " ".join(m.group(1).lower().split())
        nid = "cmd:" + cmd.replace(" ", "-")
        if nid not in seen:
            seen.add(nid)
            nodes.append(Node(id=nid, type="Command", name=cmd,
                              attrs={"tags": _cmd_tags(cmd)},
                              provenance=_make_provenance(source)))

    for m in _ROUTER_BGP_RE.finditer(text):
        block = m.group(1).strip()
        asn_m = re.search(r"router bgp (\d+)", block, re.I)
        asn = asn_m.group(1) if asn_m else "?"
        nid = f"cfg:router-bgp-{asn}"
        if nid not in seen:
            seen.add(nid)
            nodes.append(Node(id=nid, type="Configuration", name=f"router bgp {asn}",
                              attrs={"content": block[:400], "tags": ["bgp", f"as{asn}"]},
                              provenance=_make_provenance(source)))

        for nm in _NEIGHBOR_RE.finditer(block):
            peer, attr, val = nm.group(1), nm.group(2).lower(), nm.group(3)
            nid2 = f"cfg:neighbor-{peer}-{attr}"
            if nid2 not in seen:
                seen.add(nid2)
                tag = _neighbor_attr_tag(attr)
                nodes.append(Node(id=nid2, type="Configuration",
                                  name=f"neighbor {peer} {attr}",
                                  attrs={"content": f"neighbor {peer} {attr} {val}".strip(),
                                         "tags": ["bgp", "neighbor", tag]},
                                  provenance=_make_provenance(source)))
    return nodes


def rfc_extractor(text: str, source: str) -> List[Node]:
    """Extract Concept and RootCause candidates from RFC / normative prose."""
    nodes: List[Node] = []
    seen: set = set()

    # Sections as Concept nodes: title + the following text (up to 300 chars).
    sections = list(_RFC_SECTION_RE.finditer(text))
    for i, m in enumerate(sections):
        title = m.group(1).strip()
        start = m.end()
        end = sections[i + 1].start() if i + 1 < len(sections) else start + 400
        body = text[start:end].strip()[:300]
        nid = "concept:" + re.sub(r"\W+", "-", title.lower())[:60]
        if nid not in seen:
            seen.add(nid)
            tags = _rfc_tags(body)
            nodes.append(Node(id=nid, type="Concept", name=title,
                              attrs={"content": body, "tags": tags},
                              provenance=_make_provenance(source, 0.85)))

    # Normative sentences as RootCause candidates if they describe failure conditions.
    failure_keywords = re.compile(
        r"\b(fail|error|mismatch|invalid|reject|reset|collision|incorrect|drop|discard|loop)\b",
        re.I,
    )
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if _RFC_NORMATIVE_RE.search(sent) and failure_keywords.search(sent) and len(sent) > 40:
            nid = "rc:" + re.sub(r"\W+", "-", sent[:50].lower())
            if nid not in seen:
                seen.add(nid)
                nodes.append(Node(id=nid, type="RootCause",
                                  name=sent[:80].rstrip("."),
                                  attrs={"content": sent[:300], "tags": _rfc_tags(sent)},
                                  provenance=_make_provenance(source, 0.7)))
    return nodes


def link_nodes(nodes: List[Node]) -> List[Edge]:
    """Infer `depends_on` edges between nodes: Command nodes that reference a Configuration node's
    name, and RootCause nodes that co-occur with a Concept from the same source."""
    edges: List[Edge] = []
    cmds = [n for n in nodes if n.type == "Command"]
    cfgs = [n for n in nodes if n.type == "Configuration"]
    rcs = [n for n in nodes if n.type == "RootCause"]
    concepts = [n for n in nodes if n.type == "Concept"]

    for cmd in cmds:
        for cfg in cfgs:
            cmd_tags = set(cmd.attrs.get("tags", []))
            cfg_tags = set(cfg.attrs.get("tags", []))
            # A show command verifies a configuration when they share at least one protocol/category
            # tag (e.g., both "bgp", or both "interface"). Authentic "depends_on" edges come from
            # RFC concepts; verifies is for the command→config relationship.
            if cmd_tags & cfg_tags:
                src = cfg.provenance.source
                edges.append(Edge(src=cmd.id, dst=cfg.id, rel="verifies",
                                  provenance=_make_provenance(src, 0.6)))
                break

    for rc in rcs:
        for con in concepts:
            if con.provenance.source == rc.provenance.source:
                edges.append(Edge(src=rc.id, dst=con.id, rel="depends_on",
                                  provenance=_make_provenance(rc.provenance.source, 0.55)))
                break

    return edges


def ingest_text(graph: Graph, text: str, source: str) -> Tuple[int, int]:
    """Convenience: run all extractors on `text`, merge into `graph`. Returns (nodes_added, edges_added)."""
    nodes = cli_extractor(text, source) + rfc_extractor(text, source)
    edges = link_nodes(nodes)
    n0, e0 = len(graph.nodes), len(graph.edges)
    for node in nodes:
        if node.id not in graph.nodes:
            graph.add(node)
    for edge in edges:
        if not any(e.src == edge.src and e.dst == edge.dst and e.rel == edge.rel for e in graph.edges):
            graph.edges.append(edge)
    return len(graph.nodes) - n0, len(graph.edges) - e0


# --- helpers -----------------------------------------------------------------

def _cmd_tags(cmd: str) -> List[str]:
    tags = ["bgp"] if "bgp" in cmd else []
    if "neighbor" in cmd:
        tags.append("neighbor")
    if "interface" in cmd:
        tags.append("interface")
    if "route" in cmd:
        tags.append("routing")
    if "summary" in cmd:
        tags.append("summary")
    return tags


def _neighbor_attr_tag(attr: str) -> str:
    return {"remote-as": "session", "password": "auth", "route-map": "policy",
            "prefix-list": "policy", "update-source": "session"}.get(attr, attr)


def _rfc_tags(text: str) -> List[str]:
    tags = []
    t = text.lower()
    if any(k in t for k in ("bgp", "border gateway")):
        tags.append("bgp")
    if any(k in t for k in ("session", "established", "open", "notification")):
        tags.append("session")
    if any(k in t for k in ("md5", "password", "authentication", "tcp")):
        tags.append("auth")
    if any(k in t for k in ("mtu", "path mtu", "pmtu", "fragment")):
        tags.append("mtu")
    if any(k in t for k in ("as_path", "as-path", "remote-as", "autonomous")):
        tags.append("as-path")
    return tags
