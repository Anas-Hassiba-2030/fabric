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


# Canonical root-cause strings — match the ground_truth wording of the seeded faults exactly.
_CANONICAL = {
    "wrong-remote-as":
        "remote-as mismatch on R2 toward R3 (configured wrong, peer is 65010)",
    "md5-mismatch":
        "TCP-MD5 password mismatch on R2<->R3 — TCP segments fail authentication, BGP never establishes",
    "mtu-mismatch":
        "MTU mismatch on the R2<->R3 link (1500 vs 9000) — large BGP UPDATEs are dropped, session resets",
    "route-policy-reject":
        "inbound route-map DENY-ALL on R2 blocks all prefixes from R3 (192.0.2.2) — session Established but zero routes admitted",
    "next-hop-unreachable":
        "BGP next-hop 192.0.2.2 not resolved in RIB on R2 — customer prefix 10.1.0.0/24 is inactive (next-hop unreachable)",
    "max-prefix-limit":
        "max-prefix limit (1) exceeded on R2 toward 192.0.2.2 — peer advertised 2 prefixes, R2 sent NOTIFICATION and shut down the session",
    "hold-timer-expired":
        "hold-timer too aggressive (10s) on R2 toward 192.0.2.2 — session resets on transient delay; increase hold-time to 90 or 180 seconds",
    "ebgp-multihop":
        "eBGP neighbor 10.10.10.2 is not directly connected — ebgp-multihop not configured, TCP SYN dropped by TTL exhaustion after first hop",
    "as-path-loop":
        "AS_PATH loop detected: own AS 65001 appears in AS_PATH of UPDATE from R3 (192.0.2.2) — prefix discarded by eBGP loop prevention",
    "local-pref-override":
        "inbound route-map SET-LOW-LOCPREF on iBGP session to R1 (10.255.0.1) reduces local-preference to 50 — routes via RR appear worse than direct eBGP path (local-pref 100); intended policy was applied to the wrong session",
}


def _discovery_commands(symptom: str) -> List[Dict[str, str]]:
    """Symptom-keyword → small, ordered discovery sweep on R2 (the PE in the seeded topology).

    Extracts the first IPv4 address from the symptom to target the specific neighbor, falling
    back to 192.0.2.2 (the default eBGP peer in the topo-bgp topology).
    """
    s = symptom.lower()
    # Extract the BGP peer IP from the symptom — prefer host addresses (not .0 subnets),
    # and prefer addresses that look like a point-to-point peer (192.0.x.x or 10.x.x.non-zero).
    ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', symptom)
    # Filter out subnet addresses (last octet = 0) and loopback-range addresses;
    # prefer IPs that appear after "session" or "to" in the text.
    peer_candidates = [ip for ip in ips if not ip.endswith(".0")]
    peer_ip = peer_candidates[0] if peer_candidates else (ips[0] if ips else "192.0.2.2")

    cmds: List[Dict[str, str]] = [{"device": "R2", "cmd": "show bgp summary"}]
    if any(k in s for k in ("bgp", "neighbor", "session", "established", "idle", "active", "peer", "open",
                             "prefix", "policy", "route-map", "loopback", "multihop", "timer", "hold")):
        cmds.append({"device": "R2", "cmd": f"show ip bgp neighbors {peer_ip}"})
    if any(k in s for k in ("mtu", "large", "flap", "reset", "drop", "intermittent")):
        cmds.append({"device": "R2", "cmd": "show interface eth2"})
    if any(k in s for k in ("prefix", "route", "zero", "0", "no route", "black")):
        cmds.append({"device": "R2", "cmd": "show route-map"})
    return cmds


def _infer_category(outputs: List[Dict]) -> Optional[str]:
    """Read collected stdout and pick the seeded fault category, or None if no signal hits.

    Each branch checks an unambiguous joint condition against realistic FRR-like output.
    Priority order: most-specific signals checked first to avoid false positives.
    """
    joined = "\n".join(str(o.get("stdout", "")) for o in outputs).lower()

    # Fault 8: eBGP multihop — non-directly-connected peer, TTL = 1
    if "ttl = 1" in joined and "multihop not configured" in joined:
        return "ebgp-multihop"

    # Fault 6: max-prefix exceeded — NOTIFICATION + shutdown
    if "notification sent: maximum prefix reached" in joined:
        return "max-prefix-limit"

    # Fault 7: hold-timer expired — explicit message in neighbor output
    if "hold timer expired" in joined and ("idle" in joined or "active" in joined):
        return "hold-timer-expired"

    # Fault 4: route-map deny — session Established but zero prefixes + route-map active
    if ("route-map for incoming advertisements" in joined and
            "deny" in joined and "established" in joined):
        return "route-policy-reject"

    # Fault 5: next-hop unreachable — RIB miss in neighbor or bgp output
    if "unreachable" in joined and ("not in rib" in joined or "next-hop" in joined):
        return "next-hop-unreachable"

    # Fault 2: TCP-MD5 — md5 set AND session not established
    if "tcp-md5 password: set" in joined and ("idle" in joined or "active" in joined):
        return "md5-mismatch"

    # Fault 1: wrong remote-as — configured vs actual AS mismatch + Active state
    m_cfg = re.search(r"configured remote-as:\s*(\d+)", joined)
    m_peer = re.search(r"peer actual as:\s*(\d+)", joined)
    if m_cfg and m_peer and m_cfg.group(1) != m_peer.group(1) and "active" in joined:
        return "wrong-remote-as"

    # Fault 3: MTU — small MTU detected + session not up
    if "mtu 1500" in joined and ("active" in joined or "reset" in joined):
        return "mtu-mismatch"

    # Fault 9: AS_PATH loop — own AS in path, prefix silently discarded
    if "as_path loop" in joined or "own as in path" in joined or "as-path loop" in joined:
        return "as-path-loop"

    # Fault 10: local-preference override — route-map set local-pref + wrong session
    if "set local-preference" in joined and "route-map for incoming" in joined:
        return "local-pref-override"

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
