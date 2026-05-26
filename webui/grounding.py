#!/usr/bin/env python3
"""FABRIC grounding engine — the anti-hallucination gate for the Console (Phase 1).

Every stage output passes through here before it reaches the user. A claim is allowed only if it is
(a) grounded in a real source, (b) passes a deterministic gate, or (c) explicitly flagged
"needs verification". This module is PURE + DETERMINISTIC (no LLM, no API key) so the safety net can
be proven offline — see test_grounding.py.

ground_text(text)  -> (status, checks)   status in {"grounded","flagged","blocked"}
ground_config(cfg) -> (status, checks)   runs the real config_lint
Each check is a dict: {kind, item, verdict, note}.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
STANDARDS = os.path.join(REPO, "fabric", "mcp", "data", "standards.json")
LINT = os.path.join(REPO, ".claude", "skills", "config-audit", "scripts", "config_lint.py")

_RFC_RE = re.compile(r"\bRFC[\s-]?(\d{3,5})\b", re.I)
_MONEY_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?")
_LATENCY_RE = re.compile(r"\bsub-?\d+\s?ms\b|\b\d+(?:\.\d+)?\s?ms\b", re.I)
# crude vendor part-number shape (e.g. NCS-540, C9300-48U) — flag, never assert as fact
_SKU_RE = re.compile(r"\b[A-Z]{1,4}\d{3,4}[A-Z0-9-]{1,8}\b")


def _rfc_index():
    try:
        with open(STANDARDS, encoding="utf-8") as fh:
            return json.load(fh).get("rfc", {})
    except Exception:
        return {}


def _worst(a, b):
    rank = {"grounded": 0, "flagged": 1, "blocked": 2}
    return a if rank[a] >= rank[b] else b


def ground_text(text):
    """Verify citations against the grounded index; flag numbers/SKUs that need human verification."""
    text = text or ""
    idx = _rfc_index()
    checks = []
    status = "grounded"

    for num in sorted(set(_RFC_RE.findall(text))):
        if num in idx:
            checks.append({"kind": "citation", "item": f"RFC {num}", "verdict": "verified",
                           "note": idx[num]["title"], "url": idx[num].get("url", "")})
        else:
            checks.append({"kind": "citation", "item": f"RFC {num}", "verdict": "BLOCKED",
                           "note": "not in the grounded standards index — cannot ship (House Rule 4)"})
            status = _worst(status, "blocked")

    for m in sorted(set(_MONEY_RE.findall(text))):
        checks.append({"kind": "price", "item": m, "verdict": "flag",
                       "note": "price not verified — needs human/quote"})
        status = _worst(status, "flagged")

    for m in sorted(set(_LATENCY_RE.findall(text))):
        checks.append({"kind": "perf", "item": m, "verdict": "flag",
                       "note": "convergence/latency figure is hardware-dependent — verify by test, don't assert"})
        status = _worst(status, "flagged")

    for m in sorted(set(_SKU_RE.findall(text)))[:6]:
        checks.append({"kind": "sku", "item": m, "verdict": "flag",
                       "note": "part number must be confirmed current (not EoL) before quoting"})
        status = _worst(status, "flagged")

    return status, checks


def ground_config(cfg_text, vendor=None):
    """Run the real config_lint pre-pass on a config blob. status grounded(PASS)/blocked(FAIL)."""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".cfg", delete=False) as fh:
        fh.write(cfg_text or "")
        path = fh.name
    try:
        cmd = [sys.executable, LINT, path] + (["--vendor", vendor] if vendor else [])
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        out = (proc.stdout or "") + (proc.stderr or "")
        status = "grounded" if proc.returncode == 0 else "blocked"
        return status, [{"kind": "config", "item": "config_lint", "verdict": "PASS" if status == "grounded" else "FAIL",
                         "note": out.strip()}]
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def summarize(status, checks):
    label = {"grounded": "✓ grounded", "flagged": "⚠ needs verification", "blocked": "⛔ blocked"}[status]
    lines = [f"**Grounding: {label}**"]
    for c in checks:
        mark = {"verified": "✅", "PASS": "✅", "flag": "⚠", "BLOCKED": "⛔", "FAIL": "⛔"}.get(c["verdict"], "•")
        lines.append(f"- {mark} {c['item']} — {c['note']}")
    return "\n".join(lines)


if __name__ == "__main__":
    s, c = ground_text(" ".join(sys.argv[1:]) or "Use RFC 5082 and RFC 9999 with sub-50ms failover at $1,200 on NCS-540.")
    print(summarize(s, c))
