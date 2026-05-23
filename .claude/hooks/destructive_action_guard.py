#!/usr/bin/env python3
"""FABRIC destructive-action-guard (House Rule 6: the irreversible needs a human).

A Claude Code PreToolUse hook on Bash/PowerShell. It does NOT spawn agents (hooks can't) — it is a
pure pattern check. When a command looks like it pushes config to a live device or deploys/cuts over
a network, it returns an "ask" decision so Kamal must confirm before it runs, with the full command
shown. Everything else passes untouched.

Deliberately ALLOWS `git push` — that is source control, not a device push.

Output: a PreToolUse permission decision on stdin->stdout JSON. Exit 0 always (the decision, not the
exit code, gates the tool); on any internal error it fails OPEN (allows) to avoid blocking real work.
"""
import json
import re
import sys

# Patterns that indicate pushing/deploying to a live network device. Tuned to avoid false positives
# on ordinary dev commands (git, npm, python, file ops). Case-insensitive.
DEVICE_PUSH_PATTERNS = [
    (r"\bssh\b[^\n]*\b(conf(ig)?\s+t(erm)?|configure\s+terminal)\b", "SSH into device + config mode"),
    (r"\bnapalm", "NAPALM (multi-vendor device push)"),
    (r"\bnetmiko", "Netmiko (SSH device automation)"),
    (r"\bncclient|\bnetconf\b[^\n]*\b(edit-config|commit)\b", "NETCONF edit-config / commit"),
    (r"\bscp\b[^\n]*\.(cfg|conf|ios|nxos|junos)\b", "SCP of a config file to a device"),
    (r"\bansible-playbook\b[^\n]*\b(push|deploy|cutover|apply|config)\b", "Ansible config deploy/cutover"),
    (r"\b(clogin|jlogin|rancid)", "rancid/clogin device login"),
    (r"\bpyats\b[^\n]*\b(configure|push|apply)\b", "pyATS device configure"),
    (r"\b(write\s+mem(ory)?|copy\s+run(ning-config)?\s+start(up)?)", "save running-config to a device"),
]

# Explicit allow — short-circuit common safe commands so a broad rule can never catch them.
ALLOW_PREFIXES = ("git push", "git ", "gh ", "npm ", "pip ", "python ", "pytest", "node ")


def _command_from_event(event):
    tool_input = event.get("tool_input") or {}
    # Bash tool and PowerShell tool both use "command".
    cmd = tool_input.get("command")
    return cmd if isinstance(cmd, str) else ""


def evaluate(command):
    """Return (decision, reason). decision is 'ask' or 'allow'."""
    stripped = command.strip()
    low = stripped.lower()

    # git push and other clearly-safe tooling are never device pushes.
    if low.startswith("git push") or any(low.startswith(p) for p in ALLOW_PREFIXES):
        # Still scan for an embedded device push chained after a safe prefix (e.g. `git ... && ssh ... conf t`).
        if not _matches_device_push(low):
            return "allow", ""

    matched = _matches_device_push(low)
    if matched:
        return "ask", matched
    return "allow", ""


def _matches_device_push(low):
    for pattern, label in DEVICE_PUSH_PATTERNS:
        if re.search(pattern, low):
            return label
    return None


def main():
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        # Fail open — never block real work because the hook choked.
        sys.exit(0)

    command = _command_from_event(event)
    if not command:
        sys.exit(0)

    decision, reason = evaluate(command)
    if decision == "ask":
        out = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": (
                    f"FABRIC destructive-action-guard (House Rule 6): this looks like it touches a "
                    f"live network device — {reason}. Confirm before it runs.\n\n"
                    f"Command:\n{command}"
                ),
            }
        }
        print(json.dumps(out))
    # decision == allow -> print nothing, exit 0.
    sys.exit(0)


if __name__ == "__main__":
    main()
