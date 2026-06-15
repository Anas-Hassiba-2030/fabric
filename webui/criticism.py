#!/usr/bin/env python3
"""WRATH Critic-intensity dial — tune the red-team aggressiveness of the Critic gate (Phase 4).

The Critic is the adversarial reviewer (House Rule discipline). Kamal can dial how hard it pushes:
Lenient passes unless there's a clear blocker; Standard does one revision cycle; Aggressive demands
fixes for HIGH/MEDIUM findings; Max runs two adversarial passes. Pure + deterministic plan — the demo
engine uses `rounds`, Live mode injects `hint` into the Critic prompt. See webui/test_criticism.py.

    plan(intensity) -> {rounds, label, hint}
"""
import sys

LEVELS = ["low", "standard", "high", "max"]
PLAN = {
    "low": {"rounds": 0, "label": "Lenient",
            "hint": "Do a light review. Accept unless there is a clear, shipping-blocking defect."},
    "standard": {"rounds": 1, "label": "Standard",
                 "hint": "Red-team normally. Require one revision cycle if HIGH findings exist."},
    "high": {"rounds": 1, "label": "Aggressive",
             "hint": "Be a harsh adversary. Demand fixes for every HIGH and MEDIUM finding; assume the design is wrong until proven."},
    "max": {"rounds": 2, "label": "Max · 2 passes",
            "hint": "Two full adversarial passes. Nitpick everything; nothing passes until all findings are addressed."},
}


def plan(intensity):
    return PLAN.get((intensity or "standard").lower(), PLAN["standard"])


if __name__ == "__main__":
    for lv in LEVELS:
        p = plan(lv)
        print(f"{lv:9} rounds={p['rounds']} label={p['label']!r}")
    sys.exit(0)
