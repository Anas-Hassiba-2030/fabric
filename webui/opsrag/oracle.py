#!/usr/bin/env python3
"""OpsRAG execution oracle harness (thesis O4) — Containerlab today, deterministic sim today.

Given a fault scenario + a typed Runbook, run it and return a structured outcome:
    {executable, evidence_hit, diagnosis_correct, commands_run, mode, ...}

If `containerlab` is on PATH, the harness *will* spin up the topology, inject the fault, exec each
command and capture output. While the real path is being brought up (Phase 2), the **simulator** path
runs deterministically off the fault file so the rest of the loop (synthesiser → oracle → feedback)
can be wired and tested end-to-end now. Same return contract either way.

Pure stdlib; no Docker required to test.

    execute_runbook(fault, runbook) -> result dict
"""
import json
import os
import shutil
import sys


def has_containerlab() -> bool:
    return shutil.which("containerlab") is not None or shutil.which("clab") is not None


def load_fault(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _cmd_text(c) -> str:
    if isinstance(c, str):
        return c.strip()
    if isinstance(c, dict):
        return str(c.get("cmd", "")).strip()
    return ""


def execute_runbook(fault: dict, runbook: dict) -> dict:
    """Run `runbook` against `fault`. Real Containerlab path if available, simulator otherwise."""
    if has_containerlab():
        return _real_execute(fault, runbook)
    return _simulate(fault, runbook)


def _simulate(fault: dict, runbook: dict) -> dict:
    """Deterministic simulation: command is `executable` if non-empty; the runbook `diagnoses
    correctly` iff it (a) issues at least one of the fault's `expected_evidence` commands AND
    (b) concludes a root cause that matches the fault's ground truth."""
    cmds = runbook.get("commands", [])
    expected = set(s.strip() for s in fault.get("expected_evidence", []))
    cmd_texts = [_cmd_text(c) for c in cmds]
    executable = bool(cmds) and all(t != "" for t in cmd_texts)
    evidence_hit = any(t in expected for t in cmd_texts)
    rc_concluded = str(runbook.get("concluded_root_cause", "")).strip().lower()
    rc_truth = str(fault.get("ground_truth", {}).get("root_cause", "")).strip().lower()
    rc_correct = bool(rc_concluded) and rc_concluded == rc_truth
    return {
        "mode": "simulated",
        "fault": fault.get("id", "?"),
        "executable": executable,
        "evidence_hit": evidence_hit,
        "diagnosis_correct": evidence_hit and rc_correct,
        "commands_run": len(cmd_texts),
    }


def _real_execute(fault: dict, runbook: dict) -> dict:
    """Real Containerlab integration goes here in Phase 2 — spin topo, inject fault, docker exec,
    capture output, compare to ground truth. For now we keep the same return shape and route through
    the simulator so the loop's contract is stable while the lab plumbing is built."""
    return {**_simulate(fault, runbook), "mode": "containerlab-pending",
            "note": "Containerlab detected; real execution lands in Phase 2 of the OpsRAG roadmap."}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: oracle.py <fault.json> <runbook.json>", file=sys.stderr)
        sys.exit(2)
    fault = load_fault(sys.argv[1])
    with open(sys.argv[2], encoding="utf-8") as fh:
        rb = json.load(fh)
    print(json.dumps(execute_runbook(fault, rb), indent=2))
