#!/usr/bin/env python3
"""Pipeline integrity — every stage is backed by a real subagent + skill, and routing matches.

This enforces "a subagent per stage" and stops the web Console from drifting away from the real agent
system: each pipeline stage must map to an agent definition that exists on disk, with valid frontmatter,
the skill it loads must exist, and the model the router picks must match the agent's declared tier.

Run:  python webui/test_agents.py     (no key)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import app  # noqa: E402
import routing  # noqa: E402

AGENTS = os.path.join(REPO, ".claude", "agents")
SKILLS = os.path.join(REPO, ".claude", "skills")
TIERS = {"opus", "sonnet", "haiku"}
fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


def frontmatter(path):
    t = open(path, encoding="utf-8").read()
    if not t.startswith("---"):
        return {}
    end = t.find("\n---", 3)
    d = {}
    for line in t[3:end].splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            d[k.strip()] = v.strip().strip('"')
    return d


print("=== 1. Every pipeline stage is backed by a real subagent (or the orchestrator) ===")
for s in app.STAGES:
    agent = s["agent"]
    if agent == "orchestrator":
        check(f"stage '{s['id']}' -> orchestrator (CLAUDE.md)", os.path.isfile(os.path.join(REPO, "CLAUDE.md")))
    else:
        check(f"stage '{s['id']}' -> agent '{agent}.md' exists", os.path.isfile(os.path.join(AGENTS, agent + ".md")))

print("=== 2. Every stage's skill exists (the agent can load it) ===")
for agent, skill in app.SKILL_FOR.items():
    if skill:
        check(f"{agent} -> skill '{skill}/SKILL.md'", os.path.isfile(os.path.join(SKILLS, skill, "SKILL.md")))

print("=== 3. Every agent has valid frontmatter, and routing matches its declared tier ===")
agent_files = [f[:-3] for f in os.listdir(AGENTS) if f.endswith(".md")]
check("at least 16 specialist agents", len(agent_files) >= 16)
for a in sorted(agent_files):
    fm = frontmatter(os.path.join(AGENTS, a + ".md"))
    check(f"[{a}] name matches filename", fm.get("name") == a)
    check(f"[{a}] has a description", bool(fm.get("description")))
    model = fm.get("model", "")
    check(f"[{a}] model tier valid ({model})", model in TIERS)
    if model in TIERS:
        check(f"[{a}] router tier == declared tier", routing.tier_for(a) == model)

print("=== 4. Every skill has name + description frontmatter ===")
skill_dirs = [d for d in os.listdir(SKILLS) if os.path.isfile(os.path.join(SKILLS, d, "SKILL.md"))]
check("at least 15 skills", len(skill_dirs) >= 15)
for d in sorted(skill_dirs):
    fm = frontmatter(os.path.join(SKILLS, d, "SKILL.md"))
    check(f"[{d}] has name + description", bool(fm.get("name")) and bool(fm.get("description")))

print("=== 5. Slash commands are present and well-formed (Claude Code primitive) ===")
CMDS = os.path.join(REPO, ".claude", "commands")
cmd_files = [f for f in os.listdir(CMDS) if f.endswith(".md")] if os.path.isdir(CMDS) else []
check("has WRATH slash commands", len(cmd_files) >= 3)
check("the /wrath entry command exists", "wrath.md" in cmd_files)
for c in sorted(cmd_files):
    fm = frontmatter(os.path.join(CMDS, c))
    check(f"[/{c[:-3]}] has a description", bool(fm.get("description")))

print()
print("RESULT:", "ALL GREEN — every stage is wired to a real subagent + skill, routing consistent."
      if not fails else f"{fails} FAILURE(S) — pipeline/agent drift.")
sys.exit(1 if fails else 0)
