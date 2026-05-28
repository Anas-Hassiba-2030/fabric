#!/usr/bin/env python3
"""OpsRAG runbook synthesiser — deterministic baseline (Phase 2-A).

Given a fault scenario and an `executor` callable that runs `(device, command)` against the sandbox
(real Containerlab or `sim.exec_cmd`), this module:

  1. Picks a small set of *discovery* commands from the symptom (no peeking at ground truth).
  2. Runs them via the executor; collects realistic FRR-like stdout.
  3. Matches deterministic signals in that output to one of the seeded fault categories.
  4. Emits a typed runbook: `{commands, command_outputs, concluded_root_cause, synthesised_by}`.

The Phase-4 LLM-driven synthesiser will replace step 3 with retrieval over the typed graph plus an
LLM grounded by the CLI grammar gate. The contract (input + output shape) stays the same so the
oracle and the rest of the loop don't move.
"""
import re
from typing import Callable, Dict, List, Optional


# Canonical root-cause strings — match the ground_truth wording of the three seeded faults.
# These are deliberately the same strings the fault files carry so the oracle's diagnosis check
# is straightforward; richer matching arrives with the LLM synthesiser in Phase 4.
_CANONICAL = {
    "wrong-remote-as":
        "remote-as mismatch on R2 toward R3 (configured wrong, peer is 65010)",
    "md5-mismatch":
        "TCP-MD5 password mismatch on R2<->R3 — TCP segments fail authentication, BGP never establishes",
    "mtu-mismatch":
        "MTU mismatch on the R2<->R3 link (1500 vs 9000) — large BGP UPDATEs are dropped, session resets",
}


def _discovery_commands(symptom: str) -> List[Dict[str, str]]:
    """Symptom-keyword → small, ordered discovery sweep on R2 (the PE in the seeded topology).

    Conservative on purpose: when in doubt we cover BGP + the customer-facing interface, which
    surfaces the signals for all three seeded faults.
    """
    s = symptom.lower()
    cmds: List[Dict[str, str]] = [{"device": "R2", "cmd": "show bgp summary"}]
    if any(k in s for k in ("bgp", "neighbor", "session", "established", "idle", "active", "peer", "open")):
        cmds.append({"device": "R2", "cmd": "show ip bgp neighbors 192.0.2.2"})
    if any(k in s for k in ("mtu", "large", "flap", "reset", "drop", "intermittent")):
        cmds.append({"device": "R2", "cmd": "show interface eth2"})
    return cmds


def _infer_category(outputs: List[Dict]) -> Optional[str]:
    """Read the collected stdout and pick the seeded fault category, or None if no signal hits.

    Signals are intentionally cheap string matches against the FRR-like text the simulator emits
    (which is also what real FRR produces). Each branch checks an unambiguous joint condition —
    e.g., MD5 alone isn't enough; the session also has to fail to establish.
    """
    joined = "\n".join(str(o.get("stdout", "")) for o in outputs).lower()

    if "tcp-md5 password: set" in joined and ("idle" in joined or "active" in joined):
        return "md5-mismatch"

    # Wrong remote-as: the show-neighbor block separates "Configured remote-as" from
    # "Peer actual AS"; when they disagree, the session also sits in Active/Idle.
    m_cfg = re.search(r"configured remote-as:\s*(\d+)", joined)
    m_peer = re.search(r"peer actual as:\s*(\d+)", joined)
    if m_cfg and m_peer and m_cfg.group(1) != m_peer.group(1) and "active" in joined:
        return "wrong-remote-as"

    if "mtu 1500" in joined and ("active" in joined or "reset" in joined):
        return "mtu-mismatch"

    return None


def synthesise(fault: Dict, executor: Optional[Callable[[str, str], Dict]] = None) -> Dict:
    """Produce a runbook for `fault`. If `executor` is given, actually run discovery and conclude;
    otherwise emit a discovery-only runbook (useful for static graph-shape testing).

    The runbook is the same shape the oracle scores: `commands` (typed `{device,cmd}` list),
    `command_outputs` (executor results, when run), `concluded_root_cause` (canonical string for
    the inferred category, or `""` when no signal hits — better an honest blank than a guess).
    """
    cmds = _discovery_commands(fault.get("symptom", ""))
    outputs: List[Dict] = []
    if executor is not None:
        for c in cmds:
            try:
                outputs.append(executor(c["device"], c["cmd"]))
            except Exception as e:  # executor errors are recorded, never raised — synth must be robust
                outputs.append({"rc": 99, "stdout": f"% executor error: {e}", "device": c["device"], "cmd": c["cmd"]})

    category = _infer_category(outputs) if outputs else None
    return {
        "commands": cmds,
        "command_outputs": outputs,
        "concluded_root_cause": _CANONICAL.get(category, "") if category else "",
        "synthesised_by": "baseline-signal-match",
        "category": category,
    }


# Convenience: bind a synth to the deterministic in-repo simulator (no Docker).
def synthesise_with_sim(fault: Dict) -> Dict:
    """Synthesise against `webui/opsrag/sim.py`. Pure stdlib, no host requirements."""
    from . import sim
    state = sim.baseline_state()
    sim.apply_fault(state, fault)
    return synthesise(fault, executor=lambda dev, cmd: sim.exec_cmd(state, dev, cmd))


# Alias for users who prefer the US spelling.
synthesize = synthesise
synthesize_with_sim = synthesise_with_sim
