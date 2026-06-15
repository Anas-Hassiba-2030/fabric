#!/usr/bin/env python3
"""CSIRT guard — Cisco IT/CSIRT hard enforcement (repo-scoped port of csirt-guard-install-prompt.md).

A Claude Code PreToolUse hook on Write/Edit/MultiEdit/Bash. It does NOT spawn agents (hooks can't) —
it is a pure pattern check. Unlike the destructive-action-guard (which returns an "ask" decision),
this is a HARD BLOCK: a policy violation writes `BLOCKED by CSIRT policy: <reason>` to stderr and
exits 2. The model cannot talk its way around it.

Rules enforced:
  1. Plugin installs are restricted to the "claude-plugins-official" marketplace.
  2. Skills/files targeting forbidden AI-agent platform dot-directories are blocked:
       .openclaw .hermes .kiro .factory .slate .gbrain .opencode .agents
     ".cursor" is intentionally permitted (Cursor IDE is approved).

On unparseable input the hook fails OPEN (exit 0) — it cannot enforce policy on garbage, and must
not block real work because the payload was malformed.
"""
import json
import re
import sys

ALLOWED_MARKETPLACE = "claude-plugins-official"
FORBIDDEN_PLATFORMS = [
    "openclaw", "hermes", "kiro", "factory",
    "slate", "gbrain", "opencode", "agents",
]

# Structural JSON keys inside known_marketplaces.json that are NOT marketplace names.
STRUCTURAL_KEYS = {
    "source", "github", "restrictions", "compliance_taints",
    "installLocation", "lastUpdated", "repo",
}

# A forbidden platform dir requires a literal "/." so that "/.claude/agents/" and "/.cursor/"
# (no leading dot before the segment we forbid) are unaffected.
_FORBIDDEN_DIR_RE = re.compile(r"/\.(" + "|".join(FORBIDDEN_PLATFORMS) + r")(/|$)")
# Same set, but for matching inside a shell command string (path may end at whitespace/quote/EOL).
_FORBIDDEN_IN_CMD_RE = re.compile(r"\.(" + "|".join(FORBIDDEN_PLATFORMS) + r")(/|\s|\"|'|$)")
_MARKETPLACE_KEY_RE = re.compile(r"\"([a-zA-Z][a-zA-Z0-9_-]*)\"\s*:\s*\{")
_CREATION_VERBS_RE = re.compile(r"\b(mkdir|cp|ln|mv|tar|rsync|unzip|touch|tee)\b")
# A redirect (> or >>) writing into a path; captures the target token.
_REDIRECT_TARGET_RE = re.compile(r">>?\s*([^\s;|&]+)")
_PIPE_TO_SHELL_RE = re.compile(r"\|\s*(sudo\s+)?(sh|bash|zsh)\b")
_FETCH_RE = re.compile(r"\b(curl|wget)\b")


def deny(reason):
    msg = "\n".join([
        f"BLOCKED by CSIRT policy: {reason}",
        "",
        "This action violates the Cisco IT/CSIRT policy enforced by",
        ".claude/hooks/csirt_guard.py and documented in CLAUDE.md.",
        "",
        "Do NOT attempt to bypass. If you believe this is a false positive,",
        "surface it to the user and let them adjust the rule.",
    ])
    sys.stderr.write(msg + "\n")
    sys.exit(2)


def check_file(file_path):
    mp = re.search(r"/\.claude/plugins/marketplaces/([^/]+)", file_path)
    if mp and mp.group(1) != ALLOWED_MARKETPLACE:
        deny(f"writing to non-official plugin marketplace dir: {mp.group(1)} "
             f"(only \"{ALLOWED_MARKETPLACE}\" is permitted)")

    cache = re.search(r"/\.claude/plugins/cache/([^/]+)", file_path)
    if cache and cache.group(1) != ALLOWED_MARKETPLACE:
        deny(f"writing to plugin cache for non-official marketplace: {cache.group(1)}")

    if _FORBIDDEN_DIR_RE.search(file_path):
        deny(f"writing to forbidden AI-agent platform directory: {file_path}")


def check_known_marketplaces(content):
    for m in _MARKETPLACE_KEY_RE.finditer(content):
        key = m.group(1)
        if key in STRUCTURAL_KEYS:
            continue
        if key != ALLOWED_MARKETPLACE:
            deny(f"adding non-official marketplace \"{key}\" to known_marketplaces.json")


def check_bash(cmd):
    if (re.search(r"\b(git\s+clone|gh\s+repo\s+clone)\b", cmd)
            and "/.claude/plugins/marketplaces/" in cmd
            and ALLOWED_MARKETPLACE not in cmd):
        deny("cloning non-official repo into ~/.claude/plugins/marketplaces/")

    install_cmd = (
        re.search(r"\b(npm|pnpm|yarn|bun)\s+(install|i|add|create)\b", cmd)
        or re.search(r"\bpip\s+install\b", cmd)
        or re.search(r"\bbrew\s+install\b", cmd)
        or re.search(r"\bcargo\s+install\b", cmd)
    )
    if install_cmd and re.search(
        r"\b(openclaw|hermes-cli|kiro-cli|factory-cli|slate-agent|gbrain|opencode)\b",
        cmd, re.IGNORECASE,
    ):
        deny(f"package install of forbidden AI-agent platform: {cmd}")

    if _CREATION_VERBS_RE.search(cmd) and _FORBIDDEN_IN_CMD_RE.search(cmd):
        deny(f"shell command would create/touch forbidden AI-agent platform path: {cmd}")

    # GAP FIX 1 — a shell redirect (> / >>) into a forbidden platform path.
    for target in _REDIRECT_TARGET_RE.findall(cmd):
        if _FORBIDDEN_IN_CMD_RE.search(target):
            deny(f"shell redirect would write into a forbidden AI-agent platform path: {cmd}")

    # GAP FIX 2 — fetch piped to a shell that pulls a forbidden platform / non-official MP.
    if _FETCH_RE.search(cmd) and _PIPE_TO_SHELL_RE.search(cmd):
        if (_FORBIDDEN_IN_CMD_RE.search(cmd)
                or re.search(r"\b(openclaw|hermes|kiro|factory|slate|gbrain|opencode)\b",
                             cmd, re.IGNORECASE)):
            deny(f"piping a remote installer for a forbidden AI-agent platform to a shell: {cmd}")


def main():
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        # Fail open — cannot enforce on unparseable input.
        sys.exit(0)

    tool = event.get("tool_name") or ""
    ti = event.get("tool_input") or {}

    if tool in ("Write", "Edit", "MultiEdit"):
        file_path = ti.get("file_path") or ""
        if file_path:
            check_file(file_path)
        if file_path.endswith("/.claude/plugins/known_marketplaces.json"):
            content = ti.get("content") or ti.get("new_string") or ""
            check_known_marketplaces(content)
    elif tool == "Bash":
        cmd = ti.get("command") or ""
        if cmd:
            check_bash(cmd)

    sys.exit(0)


if __name__ == "__main__":
    main()
