#!/usr/bin/env python3
"""WRATH Docs/Standards MCP (read-only) — grounded RFC / IEEE / framework lookup.

Backs the Standards & Compliance Officer (charter §5: "Docs / Standards MCP — wrap a docs index").
Serves a curated, hand-verified index (data/standards.json) so citations are grounded even when egress
is locked down; when the network allows it, lookups also try the live rfc-editor record and report it.
The MCP never fabricates a reference — if it isn't in the index and can't be fetched, it says so, which
is exactly what the citation-guard gate needs (House Rule 4).

Tools (all read-only):
  lookup_standard(ref)            -> details for an RFC number / IEEE id / framework name
  search_standards(query)         -> index entries whose title/topic match the query
  verify_citation(ref, claim?)    -> does the reference exist + (optionally) does its title support a claim
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _mcpserver import MCPServer, log  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "standards.json")


def _load():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


INDEX = _load()


def _norm_rfc(ref):
    r = ref.strip().lower().replace("rfc", "").replace(" ", "")
    return r if r.isdigit() else None


def _find(ref):
    """Return (kind, key, entry) or (None, None, None)."""
    rfc = _norm_rfc(ref)
    if rfc and rfc in INDEX["rfc"]:
        return "RFC", rfc, INDEX["rfc"][rfc]
    up = ref.strip().upper().replace("IEEE", "").strip()
    for key, entry in INDEX["ieee"].items():
        if key.upper() == up or key.upper() == ref.strip().upper():
            return "IEEE", key, entry
    for key, entry in INDEX["framework"].items():
        if key.lower() == ref.strip().lower() or ref.strip().lower() in key.lower():
            return "FRAMEWORK", key, entry
    return None, None, None


def _try_live_rfc(rfc_num):
    """Best-effort live confirmation; returns a short note or None. Never blocks/raises."""
    url = f"https://www.rfc-editor.org/rfc/rfc{rfc_num}.txt"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WRATH-standards-mcp"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            head = resp.read(400).decode("utf-8", "replace")
        return f"live rfc-editor reachable (HTTP {resp.status}); first bytes confirm document exists"
    except Exception as e:
        return f"live fetch unavailable ({type(e).__name__}) — using curated index"


server = MCPServer("wrath-standards", "0.1.0")


@server.tool(
    "lookup_standard",
    "Look up a standard by reference (e.g. 'RFC 5082', '5082', 'IEEE 802.1AE', 'NIST SP 800-53'). "
    "Returns the verified title, topic, and source URL from the curated index, plus a best-effort live check.",
    {"type": "object", "properties": {"ref": {"type": "string", "description": "the standard reference"}}, "required": ["ref"]},
)
def lookup_standard(args):
    ref = str(args.get("ref", ""))
    kind, key, entry = _find(ref)
    if not entry:
        return (f"NOT FOUND in curated index: '{ref}'. Do not cite it unverified — confirm via web "
                f"search/official source first, then add it to the index (House Rule 4).")
    lines = [f"{kind} {key}", f"  title: {entry['title']}", f"  topic: {entry.get('topic','')}"]
    if entry.get("url"):
        lines.append(f"  source: {entry['url']}")
    if kind == "RFC":
        lines.append("  " + _try_live_rfc(key))
    lines.append("  status: in curated index (verify currency/obsoletes before customer use)")
    return "\n".join(lines)


@server.tool(
    "search_standards",
    "Search the curated standards index by keyword (matches title and topic). Returns candidate "
    "references to then confirm with lookup_standard. Does not invent references.",
    {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
)
def search_standards(args):
    q = str(args.get("query", "")).lower().strip()
    if not q:
        return "empty query"
    hits = []
    for kind, bucket in (("RFC", INDEX["rfc"]), ("IEEE", INDEX["ieee"]), ("FRAMEWORK", INDEX["framework"])):
        for key, entry in bucket.items():
            if q in entry["title"].lower() or q in entry.get("topic", "").lower():
                hits.append(f"{kind} {key} — {entry['title']} ({entry.get('topic','')})")
    if not hits:
        return f"no curated entry matches '{q}'. Use web search to ground a citation, then add it."
    return "\n".join(hits)


@server.tool(
    "verify_citation",
    "Verify a reference exists in the grounded index and, if a claim is given, whether the reference's "
    "title/topic plausibly supports it. Returns VERIFIED / UNVERIFIED — the citation-guard needs this.",
    {"type": "object",
     "properties": {"ref": {"type": "string"}, "claim": {"type": "string", "description": "optional claim the citation is used to support"}},
     "required": ["ref"]},
)
def verify_citation(args):
    ref = str(args.get("ref", ""))
    claim = str(args.get("claim", "")).lower().strip()
    kind, key, entry = _find(ref)
    if not entry:
        return f"UNVERIFIED — '{ref}' is not in the grounded index. BLOCK this citation until confirmed (House Rule 4)."
    supports = ""
    if claim:
        hay = (entry["title"] + " " + entry.get("topic", "")).lower()
        overlap = [w for w in claim.split() if len(w) > 3 and w in hay]
        supports = (f" Title/topic plausibly relates to the claim (matched: {', '.join(overlap)})."
                    if overlap else " WARNING: title/topic shows no obvious overlap with the claim — read the RFC text before citing.")
    return f"VERIFIED — {kind} {key}: {entry['title']}.{supports}"


if __name__ == "__main__":
    log("wrath-standards MCP (read-only) starting")
    server.run()
