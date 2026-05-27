#!/usr/bin/env python3
"""WRATH headless — run the whole pipeline from a script/CI and emit the deliverable bundle.

No browser, no server: drives the same orchestration engine and prints the exported Markdown stack
(or JSON). Honest about mode (demo vs live with a key) and respects the Critic-intensity dial.

    python webui/cli.py "Design an SR-MPLS L3VPN core for a 3-DC provider"
    python webui/cli.py "Secure hospital edge, PCI/HIPAA" --mode live --intensity max --out run.md
    python webui/cli.py "EVPN-VXLAN DCI" --format json
"""
import argparse
import json
import os
import queue
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app  # noqa: E402
import export_run  # noqa: E402


def run_headless(problem, mode="demo", intensity="standard"):
    """Run one problem end-to-end through the engine; return the saved run record."""
    rid = "cli-" + uuid.uuid4().hex[:8]
    app.RUNS[rid] = queue.Queue()
    app.run_pipeline(rid, problem, mode, intensity)  # runs synchronously to convergence + saves
    return app.load_run(rid)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="wrath", description="Run WRATH headless and emit the deliverable bundle.")
    ap.add_argument("problem", nargs="*", help="the network problem to solve")
    ap.add_argument("--mode", default="demo", choices=["demo", "live"], help="live needs ANTHROPIC_API_KEY")
    ap.add_argument("--intensity", default="standard", choices=["low", "standard", "high", "max"],
                    help="Critic red-team intensity")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    ap.add_argument("--out", help="write to this file instead of stdout")
    a = ap.parse_args(argv)
    problem = " ".join(a.problem).strip()
    if not problem:
        ap.error("a problem is required, e.g.  wrath \"Design an SR-MPLS core\"")
    rec = run_headless(problem, a.mode, a.intensity)
    if not rec:
        print("run failed", file=sys.stderr)
        return 1
    out = json.dumps(rec, indent=2) if a.format == "json" else export_run.to_markdown(rec)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(out)
        t = rec.get("trust") or {}
        print(f"wrote {a.out} — trust: {t.get('confidence', '?')} ({t.get('headline', '')})", file=sys.stderr)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
