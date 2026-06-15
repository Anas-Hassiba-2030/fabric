#!/usr/bin/env python3
"""WRATH trust report — the run's closing confidence scorecard + assumptions ledger (P1).

Clarify-gate asks the right questions *before* designing; this closes the loop *after*: it aggregates
every grounding verdict the run produced into one honest scorecard — how many claims were grounded,
how many are flagged for human verification, how many were blocked (hallucinations caught) — plus an
explicit ledger of what must be verified before the work reaches a customer, and any assumptions still
in play. Confidence is never asserted beyond the evidence (House Rule 7).

Pure + deterministic (no LLM/key), so it is fully testable — see webui/test_trust.py.

    report(grounding, assumptions=None) -> dict      # grounding == {stage: {status, checks}}
    render(report_dict) -> markdown
"""
import sys


def report(grounding, assumptions=None):
    """Aggregate per-stage grounding into a trust scorecard.

    grounding: {stage: {"status": grounded|flagged|blocked, "checks": [{kind,item,verdict,note}]}}
    """
    counts = {"verified": 0, "flagged": 0, "blocked": 0, "config_pass": 0, "config_fail": 0}
    stage_status = {"grounded": 0, "flagged": 0, "blocked": 0}
    ledger = []
    seen = set()
    for _stage, g in (grounding or {}).items():
        st = g.get("status", "grounded")
        if st in stage_status:
            stage_status[st] += 1
        for c in g.get("checks", []):
            v = c.get("verdict")
            item = c.get("item", "")
            note = c.get("note", "")
            kind = c.get("kind", "")
            if v == "verified":
                counts["verified"] += 1
            elif v == "flag":
                counts["flagged"] += 1
                if ("flag", item) not in seen:
                    seen.add(("flag", item))
                    ledger.append({"item": item, "kind": kind, "note": note,
                                   "action": "verify before customer release"})
            elif v == "BLOCKED":
                counts["blocked"] += 1
                if ("blocked", item) not in seen:
                    seen.add(("blocked", item))
                    ledger.append({"item": item, "kind": kind, "note": note,
                                   "action": "blocked & excluded (House Rule 4)"})
            elif v == "PASS":
                counts["config_pass"] += 1
            elif v == "FAIL":
                counts["config_fail"] += 1

    assume = list(assumptions or [])
    to_verify = [l for l in ledger if l["action"].startswith("verify")]
    if stage_status["blocked"] > 0:
        confidence = "Guarded"
        headline_conf = f"Guarded — {stage_status['blocked']} stage(s) blocked; resolve before proceeding"
    elif to_verify or assume:
        confidence = "Medium"
        bits = []
        if to_verify:
            bits.append(f"{len(to_verify)} item(s) to verify")
        if assume:
            bits.append(f"{len(assume)} assumption(s) in play")
        headline_conf = "Medium — " + " and ".join(bits) + " before release"
    else:
        confidence = "High"
        headline_conf = "High — every claim grounded; nothing pending"

    return {
        "counts": counts,
        "stage_status": stage_status,
        "ledger": ledger,
        "assumptions": assume,
        "confidence": confidence,
        "confidence_note": headline_conf,
        "headline": f"{counts['verified']} grounded · {len(to_verify)} to verify · "
                    f"{counts['blocked']} blocked (caught)",
    }


def render(rep):
    c = rep["counts"]
    to_verify = [l for l in rep["ledger"] if l["action"].startswith("verify")]
    blocked = [l for l in rep["ledger"] if not l["action"].startswith("verify")]
    lines = [f"**Trust report — confidence: {rep['confidence']}**",
             f"_{rep['confidence_note']}._", "",
             f"- ✅ grounded citations: **{c['verified']}**",
             f"- ⚠ flagged (verify before release): **{len(to_verify)}**",
             f"- ⛔ blocked & excluded (hallucination caught): **{c['blocked']}**",
             f"- 🔧 config gate: **{c['config_pass']} pass / {c['config_fail']} fail**"]
    if rep["assumptions"]:
        lines += ["", "**Assumptions in play (confirm with Kamal):**"]
        lines += [f"- {a}" for a in rep["assumptions"]]
    if to_verify:
        lines += ["", "**Verify-before-ship ledger:**", "| Item | Why |", "|---|---|"]
        lines += [f"| {l['item']} | {l['note']} |" for l in to_verify]
    if blocked:
        lines += ["", "**Blocked (not shipped):**"]
        lines += [f"- ⛔ {l['item']} — {l['note']}" for l in blocked]
    return "\n".join(lines)


if __name__ == "__main__":
    demo = {
        "hld": {"status": "grounded", "checks": [{"kind": "citation", "item": "RFC 4364", "verdict": "verified", "note": "L3VPN"}]},
        "bom": {"status": "flagged", "checks": [{"kind": "sku", "item": "NCS-540", "verdict": "flag", "note": "confirm not EoL"},
                                                {"kind": "price", "item": "$1,200", "verdict": "flag", "note": "needs a quote"}]},
        "standards": {"status": "grounded", "checks": [{"kind": "citation", "item": "RFC 9999", "verdict": "BLOCKED", "note": "fabricated"}]},
    }
    print(render(report(demo, assumptions=["Scale not specified — assumed 40 sites"])))
    sys.exit(0)
