#!/usr/bin/env python3
"""WRATH multi-model routing — the right Claude for each agent (mirrors the charter tiers).

CLAUDE.md assigns every specialist a tier: Opus for heavy reasoning (HLD, Critic, Migration, RCA),
Sonnet for the rest, Haiku for the Librarian. This routes each Live-mode call to that model — better
cost/speed without losing quality on the hard stages. An explicit ANTHROPIC_MODEL env overrides
everything (single-model mode). Pure + deterministic — see webui/test_routing.py.

    tier_for(agent) -> "opus"|"sonnet"|"haiku"
    model_for(agent, override=None) -> model id
    pretty(tier) -> "Opus 4.7" | ...
"""
import sys

# Mirrors the Tier column of the agent table in CLAUDE.md.
TIER = {
    "discovery": "sonnet", "designer-hld": "opus", "critic": "opus", "designer-lld": "sonnet",
    "config-engineer": "sonnet", "validator": "sonnet", "migration-planner": "opus",
    "troubleshooter": "opus", "standards-officer": "sonnet", "bom-commercials": "sonnet",
    "sow-writer": "sonnet", "exec-storyteller": "sonnet", "adoption-success": "sonnet",
    "assurance-architect": "sonnet", "multivendor-translator": "sonnet", "librarian": "haiku",
    "orchestrator": "opus",
}
MODELS = {"opus": "claude-opus-4-7", "sonnet": "claude-sonnet-4-6", "haiku": "claude-haiku-4-5-20251001"}
PRETTY = {"opus": "Opus 4.7", "sonnet": "Sonnet 4.6", "haiku": "Haiku 4.5"}


def tier_for(agent):
    return TIER.get(agent, "sonnet")


def model_for(agent, override=None):
    return override or MODELS[tier_for(agent)]


def pretty(tier):
    return PRETTY.get(tier, tier)


if __name__ == "__main__":
    for a in sorted(TIER):
        print(f"{a:24} {tier_for(a):7} {model_for(a)}")
    sys.exit(0)
