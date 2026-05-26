#!/usr/bin/env python3
"""WRATH what-if compare — diff two run records stage-by-stage (P2).

Re-run a problem with one changed constraint (SR-MPLS vs SRv6, 2 RRs vs 4, …) and see exactly what
moved: which deliverables changed, by how much, and how the trust/grounding metrics shifted. Pure +
deterministic (no LLM/key), so it is testable — see webui/test_whatif.py.

    compare(rec_a, rec_b) -> {a, b, stages:[{id,label,status,changed,ratio,added,removed}], changed_count, total}
"""
import difflib
import sys


def _content(rec, sid):
    d = (rec.get("deliverables") or {}).get(sid)
    return d.get("content") if d else None


def _order(a, b):
    order = [s["id"] for s in a.get("stages", [])]
    for s in b.get("stages", []):
        if s["id"] not in order:
            order.append(s["id"])
    return order


def _metrics(rec):
    t = rec.get("trust") or {}
    return {"id": rec.get("id", ""), "problem": rec.get("problem", ""), "mode": rec.get("mode", ""),
            "confidence": t.get("confidence", ""), "counts": t.get("counts", {}),
            "recall": len(rec.get("recall", []))}


def compare(a, b):
    labels = {}
    for rec in (a, b):
        for s in rec.get("stages", []):
            labels[s["id"]] = s.get("label", s["id"])
    stages = []
    for sid in _order(a, b):
        ca, cb = _content(a, sid), _content(b, sid)
        if ca is None and cb is None:
            continue
        if ca is None or cb is None:
            stages.append({"id": sid, "label": labels.get(sid, sid),
                           "status": "only-b" if ca is None else "only-a",
                           "changed": True, "ratio": 0.0, "added": 0, "removed": 0})
            continue
        la, lb = ca.splitlines(), cb.splitlines()
        sm = difflib.SequenceMatcher(None, la, lb)
        ratio = round(sm.ratio(), 3)
        add = rem = 0
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "replace":
                rem += i2 - i1
                add += j2 - j1
            elif tag == "delete":
                rem += i2 - i1
            elif tag == "insert":
                add += j2 - j1
        stages.append({"id": sid, "label": labels.get(sid, sid),
                       "status": "same" if ratio >= 0.999 else "changed",
                       "changed": ratio < 0.999, "ratio": ratio, "added": add, "removed": rem})
    return {"a": _metrics(a), "b": _metrics(b), "stages": stages,
            "changed_count": sum(1 for s in stages if s["changed"]), "total": len(stages)}


if __name__ == "__main__":
    import json
    import os
    MEM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wrath", "memory", "runs")
    if len(sys.argv) < 3:
        print("usage: whatif.py <run-id-a> <run-id-b>", file=sys.stderr)
        sys.exit(2)
    a = json.load(open(os.path.join(MEM, sys.argv[1] + ".json")))
    b = json.load(open(os.path.join(MEM, sys.argv[2] + ".json")))
    print(json.dumps(compare(a, b), indent=2))
