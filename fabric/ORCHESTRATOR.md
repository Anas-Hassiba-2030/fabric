# Where the Orchestrator lives

The Orchestrator is **not** a subagent you invoke. In Claude Code there is no way to "call the main
thread" — and subagents cannot spawn subagents. So the conductor must live at the top level.

**The operative Orchestrator is [`../CLAUDE.md`](../CLAUDE.md).** It is auto-loaded into every session,
which makes the main Claude thread *be* the FABRIC Orchestrator: it decomposes the problem, builds the
graph, routes to the specialist subagents in `.claude/agents/`, applies the gate rules, and converges.

- **Operative routing + house rules + gate rules + failure-mode defenses:** `../CLAUDE.md`
- **Verbatim charter (source of truth, never edit):** `PROTOCOL.md`
- **Specialists:** `../.claude/agents/`
- **Skills:** `../.claude/skills/`
- **The one real hook (destructive-action-guard) + session-start:** `../.claude/settings.json`
- **Memory:** `memory/`

If you're looking for "how the orchestrator decides what to do," read `../CLAUDE.md` §3–§6.
