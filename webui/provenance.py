#!/usr/bin/env python3
"""WRATH provenance — label what produced each deliverable (Phase 2: no ambiguity).

The honest truth, made visible: some stages are *deterministic gates* that run real code in ANY mode
(the Validator runs config_lint; Standards runs the citation check; Cost and the Trust report are
computed) — those are REAL. The reasoning stages are produced by Claude Opus 4.7 in LIVE mode, or by
representative content in DEMO mode. This classifier is the single source of truth, mirrored by the UI.

    classify(kind, mode) -> "real" | "live" | "demo"
    label(p) -> human string
"""
import sys

# Stage kinds whose output is produced by real deterministic code/gates regardless of mode.
REAL_KINDS = {"tool-validate", "tool-standards", "tool-cost", "report"}

LABELS = {
    "real": "REAL · deterministic gate",
    "live": "LIVE · Claude Opus 4.7",
    "demo": "DEMO · representative",
}


def classify(kind, mode):
    if kind in REAL_KINDS:
        return "real"
    return "live" if mode == "live" else "demo"


def label(p):
    return LABELS.get(p, p)


if __name__ == "__main__":
    for k in ("tool-validate", "tool-standards", "tool-cost", "report", "llm", "gate"):
        print(f"{k:16} demo->{classify(k, 'demo'):5} live->{classify(k, 'live')}")
    sys.exit(0)
