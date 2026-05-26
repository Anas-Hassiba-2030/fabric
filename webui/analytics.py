#!/usr/bin/env python3
"""WRATH analytics — aggregate across saved runs (Phase 1).

Cross-run intelligence: how many engagements, demo vs live, the trust-confidence distribution, total
grounded/flagged/blocked claims (does the anti-hallucination net keep biting?), the most-worked
technologies, and how much memory has compounded. Pure + deterministic — see webui/test_analytics.py.

    summarize(records) -> dict
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recall  # noqa: E402


def summarize(records):
    runs = len(records)
    by_mode, trust = {}, {"High": 0, "Medium": 0, "Guarded": 0}
    grounding = {"verified": 0, "flagged": 0, "blocked": 0}
    config_gate = {"pass": 0, "fail": 0}
    tagc, stages_total = {}, 0
    for r in records:
        m = r.get("mode", "?")
        by_mode[m] = by_mode.get(m, 0) + 1
        t = r.get("trust") or {}
        if t.get("confidence") in trust:
            trust[t["confidence"]] += 1
        c = t.get("counts") or {}
        grounding["verified"] += c.get("verified", 0)
        grounding["flagged"] += c.get("flagged", 0)
        grounding["blocked"] += c.get("blocked", 0)
        config_gate["pass"] += c.get("config_pass", 0)
        config_gate["fail"] += c.get("config_fail", 0)
        stages_total += len(r.get("stages", []))
        for tg in recall.terms(r.get("problem", "")):
            tagc[tg] = tagc.get(tg, 0) + 1
    top_tags = sorted(tagc.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
    return {
        "runs": runs,
        "by_mode": by_mode,
        "trust": trust,
        "grounding_totals": grounding,
        "config_gate": config_gate,
        "top_tags": top_tags,
        "avg_stages": round(stages_total / runs, 1) if runs else 0,
    }


if __name__ == "__main__":
    import json
    MEM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wrath", "memory", "runs")
    recs = []
    idx = os.path.join(MEM, "index.json")
    if os.path.isfile(idx):
        for e in json.load(open(idx)):
            p = os.path.join(MEM, e["id"] + ".json")
            if os.path.isfile(p):
                recs.append(json.load(open(p)))
    print(json.dumps(summarize(recs), indent=2))
