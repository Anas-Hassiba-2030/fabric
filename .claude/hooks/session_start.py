#!/usr/bin/env python3
"""FABRIC session-start hook (House Rule 8: never start cold).

A Claude Code SessionStart hook. It does NOT spawn the Librarian (hooks can't spawn agents) — it just
surfaces the active customer's memory file into context so the Orchestrator starts warm. For a deeper
pull, the Orchestrator routes to the `librarian` agent.

Reads fabric/memory/customers/active.md (if present) and returns it as additionalContext.
Silent (exit 0, no output) when there's nothing to surface.
"""
import json
import os
import sys

MAX_CHARS = 4000


def project_dir():
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def main():
    try:
        active = os.path.join(project_dir(), "fabric", "memory", "customers", "active.md")
        if not os.path.isfile(active):
            sys.exit(0)
        with open(active, "r", encoding="utf-8") as fh:
            content = fh.read().strip()
        if not content:
            sys.exit(0)
        if len(content) > MAX_CHARS:
            content = content[:MAX_CHARS] + "\n…(truncated — route to the librarian for the full record)"
        context = (
            "FABRIC memory — active customer context (House Rule 8, loaded at session start):\n\n"
            + content
        )
        out = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        }
        print(json.dumps(out))
    except Exception:
        # Never break a session over a memory read.
        sys.exit(0)


if __name__ == "__main__":
    main()
