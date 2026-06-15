#!/usr/bin/env python3
"""WRATH memory recall — never start a problem cold (House Rule 8, session-start rule).

At run start, find the most relevant prior knowledge — reusable patterns (semantic memory), customer
files (episodic memory), and past saved runs — by network-term overlap with the new problem, so the
Orchestrator opens with "we've seen something like this" and cites it. Compounding memory is what
makes WRATH feel like Kamal's brain rather than a generic assistant.

Pure + deterministic (no LLM/key); reads the committed memory tree, so it is testable — see
webui/test_recall.py.

    recall(problem) -> [ {kind, ref, title, score, shared, why} ]   # best matches first
    render(matches) -> markdown
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# Domain vocabulary used to score relevance. Word-boundary matched, so "pe"/"rt"-style noise is
# avoided; keep terms specific enough to be meaningful signal.
VOCAB = [
    "sr-mpls", "srv6", "segment routing", "evpn", "vxlan", "l3vpn", "l2vpn", "mpls", "sd-wan", "dci",
    "bgp", "ospf", "is-is", "isis", "qos", "multicast", "ipsec", "macsec", "data center", "datacenter",
    "campus", "wan", "security", "migration", "brownfield", "greenfield", "pci", "hipaa", "nist", "cis",
    "ti-lfa", "frr", "anycast", "telemetry", "gnmi", "leaf", "spine", "route reflector", "vpnv4",
    "srgb", "prefix-sid", "gtsm", "core", "peering", "internet",
]
_COMPILED = [(t, re.compile(r"\b" + re.escape(t) + r"\b", re.I)) for t in VOCAB]


def terms(text):
    t = text or ""
    return {term for term, rx in _COMPILED if rx.search(t)}


def _candidates(repo):
    """Yield (kind, ref, title, text) from patterns, customers, and saved runs."""
    for path in sorted(glob.glob(os.path.join(repo, "wrath", "memory", "patterns", "*.md"))):
        text = _read(path)
        yield ("pattern", os.path.relpath(path, repo), _title(text, os.path.basename(path)), text)
    for path in sorted(glob.glob(os.path.join(repo, "wrath", "memory", "customers", "*.md"))):
        if os.path.basename(path).startswith("_"):
            continue
        text = _read(path)
        yield ("customer", os.path.relpath(path, repo), _title(text, os.path.basename(path)), text)
    idx = os.path.join(repo, "wrath", "memory", "runs", "index.json")
    try:
        for e in json.load(open(idx)):
            prob = e.get("problem", "")
            if prob:
                yield ("run", e.get("id", ""), prob[:80], prob)
    except Exception:
        pass


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return ""


def _title(text, fallback):
    for line in (text or "").splitlines():
        if line.startswith("#"):
            return line.lstrip("# ").strip()
    return fallback


def recall(problem, repo=REPO, limit=3, min_score=2):
    pt = terms(problem)
    if not pt:
        return []
    rank = {"pattern": 0, "customer": 1, "run": 2}
    scored = []
    for kind, ref, title, text in _candidates(repo):
        shared = pt & terms(text)
        if len(shared) >= min_score:
            scored.append({"kind": kind, "ref": ref, "title": title, "score": len(shared),
                           "shared": sorted(shared),
                           "why": "shares: " + ", ".join(sorted(shared))})
    # Best score first; on a tie prefer curated knowledge (pattern > customer > raw run).
    scored.sort(key=lambda m: (-m["score"], rank.get(m["kind"], 9), m["ref"]))
    out, seen = [], set()
    for m in scored:
        key = m["title"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
        if len(out) >= limit:
            break
    return out


def render(matches):
    if not matches:
        return ""
    label = {"pattern": "pattern", "customer": "customer memory", "run": "past run"}
    lines = ["**Recalled from memory (House Rule 8 — not starting cold):**"]
    for m in matches:
        lines.append(f"- _{label.get(m['kind'], m['kind'])}_ **{m['title']}** "
                     f"(`{m['ref']}`) — {m['why']}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(render(recall(" ".join(sys.argv[1:]) or "SR-MPLS L3VPN core")) or "(no relevant memory)")
