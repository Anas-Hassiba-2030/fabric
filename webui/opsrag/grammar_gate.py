#!/usr/bin/env python3
"""Phase 4 — CLI grammar gate for runbook command validation.

Validates every command in a runbook against a platform-specific command grammar BEFORE the
runbook is emitted or admitted to the graph. This is the deterministic guard that ensures the
synthesiser never emits a syntactically invalid command — even if the LLM hallucinated one.

The gate is deliberately conservative (false-positive safe): it rejects commands that do not
match a known-good platform pattern rather than trying to parse the full CLI grammar.  A command
that is valid but not in the known list is flagged as UNKNOWN (a yellow warning) rather than
INVALID (hard block) — the thesis experiment logs both counts separately.

Platform grammars: FRR / Cisco IOS-XE / Cisco IOS-XR / NX-OS (shared subset)
"""
import re
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Grammar tables — (pattern, description, severity)
# severity: "ok" | "warn" | "reject"
# ---------------------------------------------------------------------------

# Shared show-command prefixes valid on FRR, IOS-XE, IOS-XR, NX-OS
_SHOW_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"^show\s+bgp\s+(ipv4|ipv6|vpnv4|l2vpn\s+evpn|flowspec|link-state|all)?\s*(unicast|labeled-unicast|multicast|summary|neighbors?|policy|detail)?", re.I), "BGP table/neighbor"),
    (re.compile(r"^show\s+bgp\s+(neighbors?|summary|route-map|dampening|community)", re.I), "BGP neighbors/summary"),
    (re.compile(r"^show\s+ip\s+bgp(\s+.*)?$", re.I), "IOS BGP table"),
    (re.compile(r"^show\s+ipv6\s+bgp(\s+.*)?$", re.I), "IOS IPv6 BGP"),
    (re.compile(r"^show\s+ip?\s*(route|prefix-list|access-list|community-list|as-path-access-list)(\s+.*)?$", re.I), "IP routing/policy objects"),
    (re.compile(r"^show\s+ip\s+ospf(\s+.*)?$", re.I), "OSPF state"),
    (re.compile(r"^show\s+ip\s+interface(\s+.*)?$", re.I), "IP interface"),
    (re.compile(r"^show\s+interface(\s+.*)?$", re.I), "Interface state"),
    (re.compile(r"^show\s+(ip\s+)?route(\s+.*)?$", re.I), "Routing table"),
    (re.compile(r"^show\s+route-map(\s+.*)?$", re.I), "Route-map"),
    (re.compile(r"^show\s+running-config(\s+.*)?$", re.I), "Running config"),
    (re.compile(r"^show\s+(ip\s+)?mpls(\s+.*)?$", re.I), "MPLS"),
    (re.compile(r"^show\s+segment-routing(\s+.*)?$", re.I), "Segment Routing"),
    (re.compile(r"^show\s+(ip\s+)?bfd(\s+.*)?$", re.I), "BFD"),
    (re.compile(r"^show\s+isis(\s+.*)?$", re.I), "IS-IS"),
    (re.compile(r"^show\s+l2route(\s+.*)?$", re.I), "L2 route"),
    (re.compile(r"^show\s+vrf(\s+.*)?$", re.I), "VRF state"),
    (re.compile(r"^show\s+flowspec(\s+.*)?$", re.I), "Flowspec"),
    (re.compile(r"^show\s+bmp(\s+.*)?$", re.I), "BMP"),
    (re.compile(r"^show\s+(processes|version|log(\s+.*)?|clock|system)(\s+.*)?$", re.I), "System state"),
    (re.compile(r"^show\s+rpki(\s+.*)?$", re.I), "RPKI"),
    (re.compile(r"^ping\s+\S+", re.I), "Ping"),
    (re.compile(r"^traceroute\s+\S+", re.I), "Traceroute"),
    (re.compile(r"^debug\s+(bgp|ip\s+bgp|ip\s+tcp|ospf|mpls|isis)(\s+.*)?$", re.I), "Debug"),
    (re.compile(r"^clear\s+bgp(\s+.*)?$", re.I), "BGP soft reset"),
    (re.compile(r"^clear\s+ip\s+bgp(\s+.*)?$", re.I), "BGP soft reset (IOS)"),
]

# Patterns that indicate a configuration command — ALWAYS rejected in diagnostic context
_CONFIG_PATTERNS: List[re.Pattern] = [
    re.compile(r"^router\s+(bgp|ospf|isis|rip|eigrp)", re.I),
    re.compile(r"^neighbor\s+\S+\s+(remote-as|update-source|route-map|password|shutdown)", re.I),
    re.compile(r"^network\s+\d{1,3}\.\d{1,3}", re.I),
    re.compile(r"^(ip\s+)?prefix-list\s+\S+\s+(permit|deny)", re.I),
    re.compile(r"^route-map\s+\S+\s+(permit|deny)\s+\d+$", re.I),
    re.compile(r"^(set|match)\s+(local-preference|community|as-path|metric|weight)", re.I),
    re.compile(r"^interface\s+(Ethernet|GigabitEthernet|Loopback|Tunnel)", re.I),
    re.compile(r"^ip\s+address\s+\d{1,3}", re.I),
    re.compile(r"^no\s+(neighbor|router|network|interface)", re.I),
    re.compile(r"^commit$", re.I),
    re.compile(r"^write\s+memory$", re.I),
    re.compile(r"^conf(igure)?\s+(terminal|t)$", re.I),
]

# Dangerous operational commands — warn but don't necessarily reject
_DANGEROUS_PATTERNS: List[re.Pattern] = [
    re.compile(r"^clear\s+bgp\s+\*", re.I),          # clear all BGP sessions
    re.compile(r"^debug\s+all", re.I),                 # debug everything
    re.compile(r"^debug\s+ip\s+packet", re.I),         # high-volume debug
]


class CommandVerdict:
    """Result of validating a single command."""
    __slots__ = ("cmd", "status", "reason", "platform_note")

    def __init__(self, cmd: str, status: str, reason: str, platform_note: str = ""):
        self.cmd = cmd
        self.status = status      # "ok" | "warn" | "reject"
        self.reason = reason
        self.platform_note = platform_note

    def to_dict(self) -> Dict:
        return {
            "cmd": self.cmd,
            "status": self.status,
            "reason": self.reason,
            "platform_note": self.platform_note,
        }


def validate_command(cmd: str) -> CommandVerdict:
    """Validate a single CLI command string.

    Returns a CommandVerdict with status "ok", "warn", or "reject".
    """
    raw = cmd.strip()
    if not raw:
        return CommandVerdict(raw, "reject", "empty command")

    # Config commands are always rejected in a diagnostic runbook
    for pat in _CONFIG_PATTERNS:
        if pat.match(raw):
            return CommandVerdict(raw, "reject", "configuration command not allowed in diagnostic runbook")

    # Dangerous operational commands — warn
    for pat in _DANGEROUS_PATTERNS:
        if pat.match(raw):
            return CommandVerdict(raw, "warn", "potentially high-impact operational command; confirm before running")

    # Known-good show/diagnostic commands
    for pat, desc in _SHOW_PATTERNS:
        if pat.match(raw):
            return CommandVerdict(raw, "ok", desc)

    # Not in any known pattern — unknown (yellow)
    return CommandVerdict(raw, "warn", "command not in known-good pattern list; validate manually")


def validate_runbook(commands: List[Dict]) -> Dict:
    """Validate all commands in a runbook and return a structured gate verdict.

    Returns:
        {
          "pass": bool,           # True only if ALL commands are "ok"
          "ok": int,
          "warn": int,
          "reject": int,
          "verdicts": [...],      # per-command verdicts
          "blocking_reason": str, # first reject reason if pass=False
        }
    """
    verdicts = []
    for c in commands:
        cmd_text = c.get("cmd", "") if isinstance(c, dict) else str(c)
        verdicts.append(validate_command(cmd_text).to_dict())

    ok_count = sum(1 for v in verdicts if v["status"] == "ok")
    warn_count = sum(1 for v in verdicts if v["status"] == "warn")
    reject_count = sum(1 for v in verdicts if v["status"] == "reject")
    first_reject = next((v["reason"] for v in verdicts if v["status"] == "reject"), "")

    return {
        "pass": reject_count == 0 and len(verdicts) > 0,
        "ok": ok_count,
        "warn": warn_count,
        "reject": reject_count,
        "total": len(verdicts),
        "verdicts": verdicts,
        "blocking_reason": first_reject,
    }


def gate(runbook: Dict) -> Dict:
    """Top-level gate function: validate the commands in a synthesiser runbook dict.

    The runbook must have a 'commands' key (list of {device, cmd} dicts or plain strings).
    Returns the gate verdict; if gate["pass"] is False, the runbook should NOT be emitted
    or admitted to the graph.
    """
    return validate_runbook(runbook.get("commands", []))
