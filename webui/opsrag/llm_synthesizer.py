#!/usr/bin/env python3
"""Phase 4 — LLM-driven runbook synthesiser (OpsRAG thesis contribution).

Implements the same SUT contract as the deterministic synthesiser:

    sut(question_dict) -> {"answer": str, "retrieved_context": str, "commands": [{device,cmd}]}

The graph retrieval step pulls matching typed nodes from the OpsRAG graph (built from the BGP
corpus via bootstrap + ingest). The inference step calls Claude claude-opus-4-7 via the Anthropic API.
When no API key is set, the module falls back gracefully to the deterministic baseline so tests
and the evaluator never hard-fail.

Phase 6 will swap in the full RAGAs LLM-judge for scoring; this module only changes the
generation side of the pipeline.
"""
import json
import os
import re
import sys
import urllib.request
from typing import Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))

# ---------------------------------------------------------------------------
# Graph retrieval — keyword match over the typed OpsRAG graph
# ---------------------------------------------------------------------------

def _tokenise(text: str) -> List[str]:
    s = text.lower()
    for ch in ".,;:()[]{}'\"`":
        s = s.replace(ch, " ")
    return [t for t in s.split() if len(t) >= 3]


def _retrieve(question: Dict, top_k: int = 6) -> List[Dict]:
    """Return top-k typed nodes from the OpsRAG graph that best match the question.

    Scoring: TF-IDF-style token overlap between question text and node name + attrs content.
    Pure stdlib — no NLP library required. Phase 6 swaps for dense embedding retrieval.
    """
    try:
        from . import bootstrap
        g = bootstrap.from_memory(_REPO)
    except Exception:
        return []

    q_tokens = set(_tokenise(question.get("question", "") + " " + question.get("category", "")))
    if not q_tokens:
        return []

    scored = []
    for node in g.nodes.values():
        node_text = node.name + " " + json.dumps(node.attrs)
        node_tokens = set(_tokenise(node_text))
        overlap = len(q_tokens & node_tokens) / max(1, len(q_tokens | node_tokens))
        if overlap > 0:
            scored.append((overlap, node))

    scored.sort(key=lambda x: -x[0])
    return [
        {
            "type": n.type,
            "name": n.name,
            "content": n.attrs.get("content", n.name),
            "tags": n.attrs.get("tags", []),
            "source": n.provenance.source if n.provenance else "",
            "confidence": n.provenance.confidence if n.provenance else 0.0,
        }
        for _, n in scored[:top_k]
    ]


def _format_context(nodes: List[Dict]) -> str:
    """Format retrieved nodes as grounded context for the LLM prompt."""
    if not nodes:
        return "(no typed context retrieved)"
    lines = []
    for n in nodes:
        tag_str = ", ".join(n["tags"]) if n["tags"] else ""
        src = f" [{n['source']}]" if n["source"] else ""
        lines.append(f"[{n['type'].upper()}{src}] {n['name']}: {n['content'][:300]}")
        if tag_str:
            lines.append(f"  tags: {tag_str}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM call — Anthropic Messages API (direct HTTP, no SDK dependency)
# ---------------------------------------------------------------------------

_API_URL = "https://api.anthropic.com/v1/messages"
_MODEL = "claude-opus-4-7"
_MAX_TOKENS = 512


def _call_anthropic(prompt: str, api_key: str) -> Optional[str]:
    """Send one prompt to the Anthropic API and return the text response."""
    body = json.dumps({
        "model": _MODEL,
        "max_tokens": _MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        _API_URL,
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Response parsing — extract structured answer + command list from LLM output
# ---------------------------------------------------------------------------

_CMD_PREFIXES = (
    "show bgp", "show ip bgp", "show ipv6 bgp", "show bgp ipv4", "show bgp ipv6",
    "show bgp l2vpn", "show bgp vpnv4", "show interface", "show ip interface",
    "show ip route", "show ipv6 route", "show route-map", "show ip prefix-list",
    "show running-config", "show version", "show processes", "show log",
    "show bfd", "show mpls", "show isis", "show ospf", "show l2route", "show bgp neighbors",
    "ping", "traceroute", "debug bgp", "debug ip bgp",
)


def _parse_response(text: str) -> Dict:
    """Extract ANSWER and COMMANDS sections from the structured LLM response."""
    answer = ""
    commands = []

    # Extract ANSWER section
    m = re.search(r"ANSWER:\s*(.+?)(?=COMMANDS:|$)", text, re.DOTALL | re.IGNORECASE)
    if m:
        answer = m.group(1).strip()

    # Extract COMMANDS section — each non-empty line is a command
    m = re.search(r"COMMANDS:\s*(.+?)$", text, re.DOTALL | re.IGNORECASE)
    if m:
        raw = m.group(1).strip()
        for line in raw.splitlines():
            line = line.strip().lstrip("-•* ").strip()
            if not line or line.lower().startswith("none"):
                continue
            lower = line.lower()
            if any(lower.startswith(p) for p in _CMD_PREFIXES):
                commands.append({"device": "R1", "cmd": line})

    return {"answer": answer, "commands": commands}


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are OpsRAG, a network-operations reasoning engine for BGP troubleshooting.
You receive a question and grounded context retrieved from a typed knowledge graph.

Rules (all mandatory):
1. Answer ONLY from the retrieved context + RFC-grounded knowledge. Never fabricate RFC numbers.
2. Keep your answer concise (2-6 sentences). Cite the relevant RFC section inline.
3. List only read-only diagnostic commands (show, ping, traceroute, debug). Never emit config commands.
4. If you cannot answer from the evidence, say so explicitly rather than guessing.

Output format (exactly this structure):
ANSWER:
<your answer here>

COMMANDS:
<one show/diagnostic command per line, or NONE>
"""


def _build_prompt(question: Dict, context: str) -> str:
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"CATEGORY: {question.get('category', 'bgp')}\n"
        f"DIFFICULTY: {question.get('difficulty', 'recall')}\n\n"
        f"RETRIEVED CONTEXT:\n{context}\n\n"
        f"QUESTION: {question.get('question', '')}\n"
    )


# ---------------------------------------------------------------------------
# Public SUT — the Phase 4 LLM-driven system under test
# ---------------------------------------------------------------------------

def llm_sut(question: Dict) -> Dict:
    """LLM-driven SUT.  Same contract as evaluator.naive_sut / evaluator.opsrag_sut.

    Falls back to the deterministic OpsRAG synthesiser when ANTHROPIC_API_KEY is not set,
    so the evaluator and tests always produce a result without hard-failing.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    nodes = _retrieve(question, top_k=6)
    ctx_text = _format_context(nodes)

    if not api_key:
        # No key — fall through to the deterministic baseline so tests stay green.
        from .evaluator import opsrag_sut
        result = opsrag_sut(question)
        result["retrieved_context"] = ctx_text  # still surface the retrieved context
        result["_source"] = "deterministic-fallback"
        return result

    prompt = _build_prompt(question, ctx_text)
    raw = _call_anthropic(prompt, api_key)
    if not raw:
        from .evaluator import opsrag_sut
        result = opsrag_sut(question)
        result["retrieved_context"] = ctx_text
        result["_source"] = "api-error-fallback"
        return result

    parsed = _parse_response(raw)
    return {
        "answer": parsed["answer"],
        "retrieved_context": ctx_text,
        "commands": parsed["commands"],
        "_source": "llm-opus-4-7",
        "_raw": raw,
    }


# ---------------------------------------------------------------------------
# CLI convenience (for manual testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    q = {
        "id": "q-001",
        "category": "session-establishment",
        "difficulty": "diagnose",
        "question": "R2 shows BGP neighbor in Active state toward R1. What is the most likely cause and how do you verify it?",
        "fault_id": None,
    }
    import pprint
    pprint.pprint(llm_sut(q))
