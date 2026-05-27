#!/usr/bin/env python3
"""WRATH root-cause analysis — isolate a fault from the read-only network state (Troubleshooter).

Gives the `troubleshooter` agent / `rca-playbook` skill a runnable engine: from a symptom + the
read-only state snapshot, walk a layered hypothesis tree (physical/link → BGP/service), attach the
evidence each hypothesis stands on, and isolate a *proven* causal chain when the evidence supports one
(e.g. an eBGP session stuck Idle because its next-hop interface — whose subnet contains the neighbor —
is down). Honest: it claims a root cause only with evidence, never pushes to a device (House Rules 6/7).

Pure + deterministic (stdlib `ipaddress`) — see webui/test_rca.py.

    analyze(symptom, state) -> {symptom, hypotheses, root_cause, fix, verify}
    render(symptom, state) -> markdown
"""
import ipaddress
import sys


def _anomalies(state):
    down, bad = [], []
    for dev, d in (state.get("devices", {}) or {}).items():
        for itf in d.get("interfaces", []):
            if itf.get("oper") == "down" and itf.get("name") != "Loopback0":
                down.append({"dev": dev, "name": itf["name"], "ip": itf.get("ip"), "desc": itf.get("desc", "")})
        for nb in d.get("bgp_neighbors", []):
            if nb.get("state") != "Established":
                bad.append({"dev": dev, "neighbor": nb.get("neighbor"), "afi": nb.get("afi"),
                            "state": nb.get("state"), "prefixes": nb.get("prefixes", 0)})
    return down, bad


def _in_down_subnet(neighbor_ip, downifs):
    try:
        nip = ipaddress.ip_address(neighbor_ip)
    except ValueError:
        return None
    for itf in downifs:
        ip = itf.get("ip")
        if not ip or "/" not in ip:
            continue
        try:
            if nip in ipaddress.ip_interface(ip).network:
                return itf
        except ValueError:
            continue
    return None


def analyze(symptom, state):
    down, bad = _anomalies(state or {})
    hyps = []
    if down:
        hyps.append({"layer": "Physical / link", "hypothesis": "a relevant interface is down",
                     "evidence": "; ".join(f"{i['dev']} {i['name']} ({i['desc']}, {i['ip']}) DOWN" for i in down),
                     "verdict": "confirmed"})
    else:
        hyps.append({"layer": "Physical / link", "hypothesis": "interfaces up",
                     "evidence": "no down interfaces in state", "verdict": "ruled-out"})
    root = fix = verify = None
    if bad:
        hyps.append({"layer": "BGP / service", "hypothesis": "a BGP session is not Established",
                     "evidence": "; ".join(f"{b['dev']}→{b['neighbor']} {b['afi']} {b['state']} ({b['prefixes']} pfx)" for b in bad),
                     "verdict": "confirmed"})
        for b in bad:
            itf = _in_down_subnet(b["neighbor"], down)
            if itf:
                root = (f"BGP session {b['dev']} → {b['neighbor']} ({b['afi']}) is **{b['state']}** because its "
                        f"next-hop interface {itf['dev']} {itf['name']} ({itf['desc']}, {itf['ip']}) is **down** — "
                        f"the neighbor {b['neighbor']} sits in that link's subnet, so the session cannot form.")
                fix = (f"Restore {itf['dev']} {itf['name']} — check L1/cabling, admin state (`no shutdown`), and the far end. "
                       "Pushing to the device is irreversible — Kamal confirms first (House Rule 6).")
                verify = (f"After the link is up: the {b['afi']} session to {b['neighbor']} reaches **Established** with "
                          "prefixes > 0, and the affected reachability test passes.")
                break
    else:
        hyps.append({"layer": "BGP / service", "hypothesis": "BGP sessions Established",
                     "evidence": "all neighbors Established", "verdict": "ruled-out"})
    if not root:
        root = ("Anomalies found but no single proven causal chain — gather the evidence above to isolate."
                if (down or bad) else
                "No fault visible in the read-only state. Confirm the symptom, scope and timeframe, and "
                "gather targeted show/telemetry before concluding (House Rule 7).")
    return {"symptom": symptom or "(unspecified)", "hypotheses": hyps, "root_cause": root, "fix": fix, "verify": verify}


def render(symptom, state):
    a = analyze(symptom, state)
    L = ["## Root-cause analysis", "", f"**Symptom:** {a['symptom']}", "",
         "**Layered hypothesis tree (evidence from read-only state):**", "",
         "| Layer | Hypothesis | Evidence | Verdict |", "|---|---|---|---|"]
    mk = {"confirmed": "🔴 confirmed", "ruled-out": "✅ ruled out", "unknown": "• unknown"}
    for h in a["hypotheses"]:
        L.append(f"| {h['layer']} | {h['hypothesis']} | {h['evidence']} | {mk.get(h['verdict'], h['verdict'])} |")
    L += ["", "**Isolated root cause:**", a["root_cause"]]
    if a["fix"]:
        L += ["", "**Fix (proposed — needs Kamal):**", a["fix"]]
    if a["verify"]:
        L += ["", "**Verify after fix:**", a["verify"]]
    L += ["", "_Read-only, evidence-based diagnosis — no claim beyond what the state shows (House Rule 7); "
          "WRATH never pushes to a device (House Rule 6)._"]
    return "\n".join(L)


if __name__ == "__main__":
    import json
    import os
    sd = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wrath", "mcp", "state", "sample-testbed.json")
    print(render(" ".join(sys.argv[1:]) or "Customer A has lost connectivity", json.load(open(sd))))
