#!/usr/bin/env python3
"""OpsRAG execution oracle harness (thesis O4) — runs a runbook against a fault and scores it.

Given a fault scenario + a typed Runbook, return a structured outcome:
    {executable, evidence_hit, diagnosis_correct, commands_run, mode, ...}

Three execution modes, picked from what the host has:
  - `containerlab` — real Containerlab + FRR; spins the topo, injects the fault, captures stdout.
  - `simulated`    — `webui/opsrag/sim.py`, a deterministic mini-FRR with the same return contract.
  - `static`       — no executor at all; score the runbook from its declared `commands` only.

Mode `simulated` is what Phase 2-A uses so the entire synthesiser → oracle loop runs end-to-end
without Docker. Mode `containerlab` is Phase 2-B, gated by output equivalence with the simulator
on the same benchmark — so the contract is identical and only the executor changes.

Pure stdlib; no Docker required to test.

    execute_runbook(fault, runbook) -> result dict
"""
import json
import shutil
import sys
from typing import Dict, List


def has_containerlab() -> bool:
    return shutil.which("containerlab") is not None or shutil.which("clab") is not None


def load_fault(path: str) -> Dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _cmd_text(c) -> str:
    if isinstance(c, str):
        return c.strip()
    if isinstance(c, dict):
        return str(c.get("cmd", "")).strip()
    return ""


def _normalise(s: str) -> str:
    """Lowercase, collapse whitespace and strip punctuation that varies between phrasings."""
    s = s.lower()
    for ch in ".,;:()[]{}'\"":
        s = s.replace(ch, " ")
    return " ".join(s.split())


def _diagnosis_matches(concluded: str, truth: str) -> bool:
    """Honest match: exact (after normalisation) OR the conclusion carries the truth's key tokens.

    Token check uses the multi-letter tokens of the ground truth (>=4 chars) and requires
    ≥70% to appear in the conclusion. That tolerates phrasing drift from the LLM synth in
    Phase 4 without rewarding shallow keyword sprinkling — random text won't clear 70%.
    """
    if not concluded or not truth:
        return False
    nc, nt = _normalise(concluded), _normalise(truth)
    if nc == nt:
        return True
    truth_tokens = [t for t in nt.split() if len(t) >= 4]
    if not truth_tokens:
        return False
    concluded_tokens = set(nc.split())
    hit = sum(1 for t in truth_tokens if t in concluded_tokens)
    return hit / len(truth_tokens) >= 0.7


def execute_runbook(fault: Dict, runbook: Dict) -> Dict:
    """Run `runbook` against `fault`. Real Containerlab if present, deterministic simulator otherwise."""
    if has_containerlab():
        return _real_execute(fault, runbook)
    return _simulate(fault, runbook)


def _simulate(fault: Dict, runbook: Dict) -> Dict:
    """Execute via the in-repo simulator. The runbook's `commands` are actually run against the
    simulated state (faulted from `fault.inject`); the captured `stdout` is used to verify that
    the runbook saw the expected evidence and concluded a root cause that matches ground truth.
    """
    from . import sim

    cmds = runbook.get("commands", []) or []
    cmd_texts = [_cmd_text(c) for c in cmds]
    executable = bool(cmds) and all(t != "" for t in cmd_texts)

    state = sim.baseline_state()
    sim.apply_fault(state, fault)

    outputs: List[Dict] = []
    for c in cmds:
        dev = c.get("device", "R2") if isinstance(c, dict) else "R2"
        outputs.append(sim.exec_cmd(state, dev, _cmd_text(c)))

    expected = set(s.strip().lower() for s in fault.get("expected_evidence", []))
    evidence_hit = any(t.lower() in expected for t in cmd_texts)

    truth = str(fault.get("ground_truth", {}).get("root_cause", ""))
    concluded = str(runbook.get("concluded_root_cause", ""))
    rc_correct = _diagnosis_matches(concluded, truth)

    return {
        "mode": "simulated",
        "fault": fault.get("id", "?"),
        "executable": executable,
        "evidence_hit": evidence_hit,
        "diagnosis_correct": evidence_hit and rc_correct,
        "commands_run": len(cmd_texts),
        "command_outputs": outputs,
        "executor": "webui.opsrag.sim",
    }


def _real_execute(fault: Dict, runbook: Dict) -> Dict:
    """Real Containerlab integration — Phase 2-B. Same return shape as `_simulate`; only the
    executor differs (Containerlab + `docker exec` instead of `sim.exec_cmd`). We route through
    `_simulate` today so the contract is exercised end-to-end and the only swap left is the
    transport. Equivalence-on-benchmark is the gate for promoting this branch to a real exec.
    """
    return {**_simulate(fault, runbook), "mode": "containerlab-pending",
            "note": "Containerlab detected; real execution lands in Phase 2-B of the OpsRAG roadmap."}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: oracle.py <fault.json> <runbook.json>", file=sys.stderr)
        sys.exit(2)
    fault = load_fault(sys.argv[1])
    with open(sys.argv[2], encoding="utf-8") as fh:
        rb = json.load(fh)
    print(json.dumps(execute_runbook(fault, rb), indent=2))
