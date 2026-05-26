#!/usr/bin/env python3
"""Prove the LIVE-mode wiring works — WITHOUT a real API key.

We monkeypatch the Anthropic call with a scripted fake that simulates Claude, including a
HALLUCINATED citation and a BROKEN first config, then run the real pipeline in live mode and assert:
  - stages chain and all complete,
  - the Validator catches the bad config, bounces it back, and it re-passes (FAIL -> PASS),
  - the Critic bounces the HLD back once then accepts,
  - the grounding gate flags the live hallucination (fake RFC) as BLOCKED.

Run:  python webui/test_live.py     (no key, no network)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app  # noqa: E402

BAD_CFG = ("```\nhostname PE1\nsnmp-server community public RO\n"
           "interface Loopback0\n description router-id\n ipv4 address 10.255.0.1 255.255.255.255\n"
           "interface GigabitEthernet0/0/0/0\n description to:CORE\n ipv4 address 10.0.0.0 255.255.255.254\n mtu 9216\n no shutdown\nend\n```")
GOOD_CFG = ("```\nhostname PE1\nsnmp-server host 10.30.0.10 traps version 3 priv\n"
            "interface Loopback0\n description router-id\n ipv4 address 10.255.0.1 255.255.255.255\n"
            "interface GigabitEthernet0/0/0/0\n description to:CORE\n ipv4 address 10.0.0.0 255.255.255.254\n mtu 9216\n no shutdown\n"
            "router bgp 65000\n bgp router-id 10.255.0.1\nend\n```")

_state = {"critic": 0}


def fake_call(system, prompt, **kw):
    m = re.search(r"WRATH's '([\w-]+)' specialist", system or "")
    agent = m.group(1) if m else ""
    p = (prompt or "")
    if agent == "config-engineer":
        return GOOD_CFG if "REJECTED" in p else BAD_CFG
    if agent == "critic":
        _state["critic"] += 1
        return ("VERDICT: ACCEPT-WITH-FIXES\n- [HIGH] state HW dependency."
                if _state["critic"] == 1 else "VERDICT: ACCEPT — clears the findings.")
    if agent == "designer-lld":
        return "LLD: addressing + SR-SID plan. Uses RFC 9999 for the magic label."  # planted hallucination
    return f"{agent} deliverable: grounded, concise, honest about confidence."


class FakeQ:
    def __init__(self): self.events = []
    def put(self, o): self.events.append(o)


def main():
    app.has_key = lambda: True
    app.call_claude = fake_call
    q = FakeQ()
    app.RUNS["t-live"] = q
    app.run_pipeline("t-live", "Design an SR-MPLS L3VPN core, multi-vendor", "live")
    ev = q.events

    rejects = [(e["gate"], e["producer"]) for e in ev if e.get("type") == "reject"]
    done = [e["id"] for e in ev if e.get("type") == "stage" and e["status"] == "done"]
    vverdicts = [("PASS" if "VERDICT: PASS" in e["content"] else "FAIL")
                 for e in ev if e.get("type") == "output" and e["stage"] == "validate"]
    grounding = {}
    for e in ev:
        if e.get("type") == "grounding":
            grounding[e["stage"]] = e["status"]
    meta = [e for e in ev if e.get("type") == "meta"]

    fails = 0
    def check(d, c):
        nonlocal fails
        print(("  PASS  " if c else "  FAIL  ") + d)
        fails += 0 if c else 1

    print("=== LIVE-mode wiring (mocked Claude, no key) ===")
    check("meta emitted (pipeline booted in live)", bool(meta) and meta[0]["mode"] == "live")
    check("all 12 stages completed", len(set(done)) == 12)
    check("Critic bounced HLD back then accepted", ("critic", "hld") in rejects and _state["critic"] >= 2)
    check("Validator rejected the bad config", ("validate", "config") in rejects)
    check("Validator verdicts went FAIL -> PASS (real fix loop)", vverdicts[:2] == ["FAIL", "PASS"] or ("FAIL" in vverdicts and vverdicts[-1] == "PASS"))
    check("grounding BLOCKED the live hallucination (fake RFC in LLD)", grounding.get("lld") == "blocked")
    check("standards stage grounded", grounding.get("standards") == "grounded")

    trust_ev = [e for e in ev if e.get("type") == "trust"]
    check("trust report emitted at run close", bool(trust_ev))
    check("trust report counted the blocked hallucination", trust_ev and trust_ev[0]["counts"]["blocked"] >= 1)
    check("trust confidence is Guarded (a stage was blocked)", trust_ev and trust_ev[0]["confidence"] == "Guarded")

    print()
    print("RESULT:", "ALL GREEN — live wiring chains, gates bite, and hallucinations are caught."
          if not fails else f"{fails} FAILURE(S).")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
