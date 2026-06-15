#!/usr/bin/env python3
"""WRATH run export — turn a saved run into one shareable Markdown bundle (P1).

The whole deliverable stack of a run (recalled memory, every stage's deliverable in pipeline order
with its grounding verdict, and the closing trust report) rendered as a single Markdown document you
can hand to a colleague, attach to a ticket, or print to PDF. Stdlib-only, no key.

    python webui/export_run.py <run-id>        # bundle a specific saved run
    python webui/export_run.py --latest        # bundle the most recent run
Also served at GET /api/export?id=<run-id> by the Console.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import provenance  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MEM = os.path.join(REPO, "wrath", "memory", "runs")


def to_markdown(rec):
    """Render a saved run record into a single Markdown document."""
    L = [f"# WRATH run — {rec.get('problem', '(untitled)')}", "",
         f"_mode: {rec.get('mode', '')} · {rec.get('ts', '')} · "
         "engine: Claude Opus 4.7 (Live) / deterministic gates (Demo)_"]

    if rec.get("recall"):
        L += ["", "## Recalled from memory (House Rule 8)"]
        for m in rec["recall"]:
            L.append(f"- _{m.get('kind', '')}_ **{m.get('title', '')}** "
                     f"(`{m.get('ref', '')}`) — {m.get('why', '')}")

    deliverables = rec.get("deliverables", {})
    stages = rec.get("stages", [])
    kind_of = {s["id"]: s.get("kind", "") for s in stages}
    mode = rec.get("mode", "demo")
    order = [s["id"] for s in stages] or list(deliverables.keys())
    grounding = rec.get("grounding", {})
    for sid in order:
        d = deliverables.get(sid)
        if not d:
            continue
        L += ["", "---", "", f"## {d['title']}"]
        L.append(f"> source: **{provenance.label(provenance.classify(kind_of.get(sid, ''), mode))}**")
        g = grounding.get(sid)
        if g:
            L.append(f"> grounding: **{g.get('status', '')}**")
        L += ["", d["content"]]

    t = rec.get("trust")
    if t:
        L += ["", "---", "", f"## Trust summary — confidence: {t.get('confidence', '')}",
              f"_{t.get('headline', '')}_"]

    L += ["", "---", "_WRATH — Workbench for Reasoned Architecture, Testing & Handover._"]
    return "\n".join(L)


def _load(rid):
    p = os.path.join(MEM, rid + ".json")
    return json.load(open(p)) if os.path.isfile(p) else None


def _latest():
    idx = os.path.join(MEM, "index.json")
    try:
        entries = json.load(open(idx))
        return _load(entries[0]["id"]) if entries else None
    except Exception:
        return None


def main(argv):
    if len(argv) < 2:
        print("usage: export_run.py <run-id> | --latest", file=sys.stderr)
        return 2
    rec = _latest() if argv[1] == "--latest" else _load(argv[1])
    if not rec:
        print("run not found", file=sys.stderr)
        return 1
    print(to_markdown(rec))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
