#!/usr/bin/env python3
"""WRATH doctor — one command to confirm everything is working.

Checks the environment, the deterministic safety nets, and — if ANTHROPIC_API_KEY is set — makes ONE
real call to Claude Opus 4.7 to prove the live engine actually works and answers.

Run:
    python webui/doctor.py            # full check (real Opus call only if a key is set)
    ANTHROPIC_API_KEY=sk-... python webui/doctor.py   # also proves Opus 4.7 live
"""
import json
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import app  # noqa: E402

fails = 0


def line(ok, msg):
    global fails
    print(("  ✓ " if ok else "  ✗ ") + msg)
    if not ok:
        fails += 1


def run(desc, argv):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=120, cwd=REPO)
        line(p.returncode == 0, desc)
        return p.returncode == 0
    except Exception as e:
        line(False, f"{desc} ({e})")
        return False


print("WRATH doctor")
print("=== environment ===")
line(sys.version_info >= (3, 8), f"python {sys.version.split()[0]}")
line(app.MODEL == "claude-opus-4-7", f"default engine = {app.MODEL}")
line(os.path.isfile(os.path.join(REPO, ".claude/skills/config-audit/scripts/config_lint.py")), "config_lint present")
line(os.path.isfile(os.path.join(REPO, "wrath/mcp/data/standards.json")), "grounded standards index present")

print("=== safety nets (deterministic, no key) ===")
run("anti-hallucination grounding proof", [sys.executable, "webui/test_grounding.py"])
run("clarifying-questions gate proof", [sys.executable, "webui/test_clarify.py"])
run("memory recall proof", [sys.executable, "webui/test_recall.py"])
run("auto topology diagram proof", [sys.executable, "webui/test_topology.py"])
run("cost/TCO + risk register honesty proof", [sys.executable, "webui/test_tco.py"])
run("trust report fidelity proof", [sys.executable, "webui/test_trust.py"])
run("provenance labelling proof", [sys.executable, "webui/test_provenance.py"])
run("multi-model routing proof", [sys.executable, "webui/test_routing.py"])
run("critic-intensity dial proof", [sys.executable, "webui/test_criticism.py"])
run("audience reframing proof", [sys.executable, "webui/test_audience.py"])
run("compliance pack proof", [sys.executable, "webui/test_compliance.py"])
run("run export proof", [sys.executable, "webui/test_export.py"])
run("what-if compare proof", [sys.executable, "webui/test_whatif.py"])
run("engagement blueprints proof", [sys.executable, "webui/test_blueprints.py"])
run("self-improving pattern distil proof", [sys.executable, "webui/test_distill.py"])
run("pattern git-persist proof", [sys.executable, "webui/test_persist.py"])
run("cross-run analytics proof", [sys.executable, "webui/test_analytics.py"])
run("inbox (saved results) proof", [sys.executable, "webui/test_inbox.py"])
run("live-mode wiring proof (mocked)", [sys.executable, "webui/test_live.py"])
run("config_lint self-test", [sys.executable, ".claude/skills/config-audit/scripts/config_lint.py", "--self-test"])

print("=== live engine (Claude Opus 4.7) ===")
key = os.environ.get("ANTHROPIC_API_KEY")
if not key:
    print("  • no ANTHROPIC_API_KEY set — skipping the real call.")
    print("    To prove Opus 4.7 live:  set ANTHROPIC_API_KEY and re-run this doctor.")
else:
    try:
        body = json.dumps({"model": "claude-opus-4-7", "max_tokens": 64,
                           "messages": [{"role": "user", "content": "Reply with exactly: WRATH-OK"}]}).encode()
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
                                     headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
        model_used = data.get("model", "")
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        line("opus-4-7" in model_used or "opus" in model_used, f"real API call returned model: {model_used}")
        line("WRATH-OK" in text, f"Opus 4.7 answered: {text.strip()[:40]!r}")
    except Exception as e:
        line(False, f"real Opus call failed: {e}")

print()
print("DIAGNOSIS:", "ALL GREEN — system is working." if not fails else f"{fails} problem(s) above.")
sys.exit(1 if fails else 0)
