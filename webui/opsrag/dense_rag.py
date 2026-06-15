#!/usr/bin/env python3
"""Phase 3 (remaining) — Dense-RAG baseline comparator.

Provides a flat-chunk retrieval SUT that runs over the same BGP corpus as OpsRAG but WITHOUT
the typed graph structure.  This is the academic baseline: same questions, same corpus, different
representation (flat text chunks vs typed knowledge graph).

Retrieval: TF-IDF-style BM25-approximate scoring over character-level 500-token chunks.
Generation: deterministic template (no LLM) — returns the top-chunk text as the "answer" and
extracts any show commands from it.  This isolates the retrieval contribution.

The LLM-driven dense-RAG variant (where the same chunks feed Claude claude-opus-4-7) is Phase 6 work;
this module provides the non-LLM floor for the ablation table.

SUT contract (same as every other SUT in this system):
    dense_rag_sut(question_dict) -> {"answer": str, "retrieved_context": str, "commands": []}
"""
import json
import math
import os
import re
from typing import Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))

# ---------------------------------------------------------------------------
# Chunker — split any text into fixed-size overlapping windows
# ---------------------------------------------------------------------------

_CHUNK_SIZE = 500    # characters
_CHUNK_STEP = 250    # 50% overlap


def chunk_text(text: str, source: str = "") -> List[Dict]:
    """Split text into overlapping chunks, each tagged with its source."""
    text = text.strip()
    if not text:
        return []
    # Short texts return a single chunk without the trailing-fragment guard.
    if len(text) <= _CHUNK_SIZE:
        return [{"text": text, "source": source, "offset": 0}]
    chunks = []
    for i in range(0, len(text), _CHUNK_STEP):
        c = text[i: i + _CHUNK_SIZE]
        if len(c) < 50 and i > 0:  # skip tiny trailing fragments only
            break
        chunks.append({"text": c, "source": source, "offset": i})
    return chunks


# ---------------------------------------------------------------------------
# Corpus loader — reads the OpsRAG graph nodes as flat-text chunks
# (same corpus, different representation — the controlled comparison)
# ---------------------------------------------------------------------------

def _load_corpus() -> List[Dict]:
    """Build the flat-chunk corpus from the same sources as the typed graph.

    Priority sources:
    1. wrath/memory/patterns/ — curated playbook knowledge
    2. wrath/memory/customers/ — estate context
    3. thesis/lab/faults/ — seeded fault descriptions
    Falls back to the OpsRAG typed graph node names+content when those are available.
    """
    chunks: List[Dict] = []

    def _ingest_dir(path: str, ext: str = ".md"):
        if not os.path.isdir(path):
            return
        for fname in os.listdir(path):
            if fname.endswith(ext):
                with open(os.path.join(path, fname), encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
                chunks.extend(chunk_text(text, source=fname))

    _ingest_dir(os.path.join(_REPO, "wrath", "memory", "patterns"))
    _ingest_dir(os.path.join(_REPO, "wrath", "memory", "customers"))

    faults_dir = os.path.join(_REPO, "thesis", "lab", "faults")
    if os.path.isdir(faults_dir):
        for fname in os.listdir(faults_dir):
            if fname.endswith(".json"):
                with open(os.path.join(faults_dir, fname), encoding="utf-8") as fh:
                    f = json.load(fh)
                text = f.get("title", "") + ". " + f.get("symptom", "") + ". " + \
                       f.get("ground_truth", {}).get("root_cause", "")
                chunks.extend(chunk_text(text, source=fname))

    # Also pull typed graph node content (same corpus, flat representation)
    try:
        from . import bootstrap
        g = bootstrap.from_memory(_REPO)
        for node in g.nodes.values():
            text = node.name + " " + node.attrs.get("content", "")
            chunks.extend(chunk_text(text, source=f"graph:{node.type}"))
    except Exception:
        pass

    return chunks


# ---------------------------------------------------------------------------
# BM25-approximate retrieval (no external library)
# ---------------------------------------------------------------------------

_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "of", "to", "in", "on",
    "at", "by", "for", "with", "as", "from", "this", "that", "and", "or", "but", "if", "then",
    "it", "its", "what", "which", "who", "when", "where", "how", "you", "your", "we", "they",
    "have", "has", "had", "can", "could", "may", "might", "must", "should", "would", "will", "not",
})
_K1 = 1.5
_B = 0.75


def _tokens(text: str) -> List[str]:
    s = re.sub(r"[^\w\s]", " ", text.lower())
    return [t for t in s.split() if len(t) >= 3 and t not in _STOPWORDS]


class _BM25Index:
    def __init__(self, corpus: List[Dict]):
        self._corpus = corpus
        self._n = len(corpus)
        self._tok = [_tokens(c["text"]) for c in corpus]
        avgdl = sum(len(t) for t in self._tok) / max(1, self._n)
        self._avgdl = avgdl
        # IDF: df per term
        self._df: Dict[str, int] = {}
        for tok in self._tok:
            for t in set(tok):
                self._df[t] = self._df.get(t, 0) + 1

    def score(self, query: str, top_k: int = 5) -> List[Tuple[float, Dict]]:
        q_toks = _tokens(query)
        if not q_toks:
            return []
        scored = []
        for i, (chunk, toks) in enumerate(zip(self._corpus, self._tok)):
            dl = len(toks)
            tf_map: Dict[str, int] = {}
            for t in toks:
                tf_map[t] = tf_map.get(t, 0) + 1
            s = 0.0
            for qt in q_toks:
                tf = tf_map.get(qt, 0)
                if tf == 0:
                    continue
                df = self._df.get(qt, 0)
                idf = math.log((self._n - df + 0.5) / (df + 0.5) + 1)
                num = tf * (_K1 + 1)
                den = tf + _K1 * (1 - _B + _B * dl / self._avgdl)
                s += idf * num / den
            if s > 0:
                scored.append((s, chunk))
        scored.sort(key=lambda x: -x[0])
        return scored[:top_k]


# Module-level index (lazy, built once per process)
_INDEX: Optional[_BM25Index] = None


def _get_index() -> _BM25Index:
    global _INDEX
    if _INDEX is None:
        _INDEX = _BM25Index(_load_corpus())
    return _INDEX


# ---------------------------------------------------------------------------
# Command extractor — pulls show commands from chunk text
# ---------------------------------------------------------------------------

_CMD_PATTERN = re.compile(
    r"(show\s+(?:bgp|ip\s+bgp|ipv6\s+bgp|interface|ip\s+route|route-map|running-config|"
    r"mpls|isis|ospf|bfd|log|l2route|processes|version)[^\n]{0,80})",
    re.IGNORECASE,
)


def _extract_commands(text: str) -> List[Dict]:
    found = []
    seen = set()
    for m in _CMD_PATTERN.finditer(text):
        cmd = m.group(1).strip()
        if cmd.lower() not in seen:
            seen.add(cmd.lower())
            found.append({"device": "R1", "cmd": cmd})
    return found[:4]  # cap at 4 commands per chunk


# ---------------------------------------------------------------------------
# Public SUT
# ---------------------------------------------------------------------------

def dense_rag_sut(question: Dict) -> Dict:
    """Dense-RAG baseline SUT.  Same contract as naive_sut / opsrag_sut / llm_sut.

    Retrieval: BM25 over flat corpus chunks (no typed structure).
    Generation: deterministic — top chunk text becomes the answer, show commands extracted.
    This is the ablation baseline isolating the typed-graph contribution.
    """
    q_text = question.get("question", "") + " " + question.get("category", "")
    idx = _get_index()
    results = idx.score(q_text, top_k=5)

    if not results:
        return {"answer": "", "retrieved_context": "", "commands": []}

    top_chunks = [chunk for _, chunk in results]
    ctx_text = "\n---\n".join(c["text"] for c in top_chunks)

    # Answer = text of the top-scoring chunk (deterministic generation floor)
    top_text = top_chunks[0]["text"]

    # Extract any show commands from all retrieved chunks
    all_cmds: List[Dict] = []
    seen_cmds: set = set()
    for c in top_chunks:
        for cmd in _extract_commands(c["text"]):
            key = cmd["cmd"].lower()
            if key not in seen_cmds:
                seen_cmds.add(key)
                all_cmds.append(cmd)
        if len(all_cmds) >= 5:
            break

    return {
        "answer": top_text,
        "retrieved_context": ctx_text,
        "commands": all_cmds,
        "_source": "dense-rag-bm25",
    }


# ---------------------------------------------------------------------------
# Index invalidation hook (call when corpus changes between tests)
# ---------------------------------------------------------------------------

def invalidate_index():
    global _INDEX
    _INDEX = None
