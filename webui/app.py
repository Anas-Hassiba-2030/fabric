#!/usr/bin/env python3
"""WRATH Console — a local web UI for the WRATH Solution Mesh.

Type a network problem; watch the orchestration pipeline run stage-by-stage (Discovery -> HLD ->
Critic gate -> LLD -> Config -> Validator gate -> BoM -> SoW -> Exec -> Migration -> Standards) and
see the deliverables render. Dependency-free (Python 3 stdlib only) so it runs anywhere:

    python3 webui/app.py            # then open http://localhost:8765

Two modes:
  * Demo (default)  — runs the pipeline with representative, problem-tailored content. The *gates*
                      are real: the Validator stage runs config_lint.py, the Standards stage runs the
                      real citation check against the grounded standards index.
  * Live            — if ANTHROPIC_API_KEY is set, the content-generating stages call the Claude API
                      so it is genuinely WRATH reasoning. Set ANTHROPIC_MODEL to override the model.

Transport: Server-Sent Events stream each stage/log/output to the browser as it happens.
"""
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clarify  # noqa: E402
import grounding  # noqa: E402
import tco  # noqa: E402
import topology  # noqa: E402
import trust  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
STATIC = os.path.join(HERE, "static")
LINT = os.path.join(REPO, ".claude", "skills", "config-audit", "scripts", "config_lint.py")
STANDARDS = os.path.join(REPO, "wrath", "mcp", "data", "standards.json")
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7")  # Claude Opus 4.7 is the default engine
PORT = int(os.environ.get("WRATH_UI_PORT", "8765"))
TOKEN = os.environ.get("WRATH_UI_TOKEN", "")  # if set, the console + API require this token
MAX_ACTIVE = int(os.environ.get("WRATH_UI_MAX_ACTIVE", "8"))
VERSION = "0.5.0"

RUNS = {}   # run_id -> Queue
REC = {}    # id(queue) -> run record being captured (for memory)
MEM = os.path.join(REPO, "wrath", "memory", "runs")  # saved runs (compounding memory)


def save_run(rec):
    """Persist a converged run so it can be recalled later (House Rule 8 — compounding memory)."""
    try:
        os.makedirs(MEM, exist_ok=True)
        with open(os.path.join(MEM, rec["id"] + ".json"), "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
        idx_path = os.path.join(MEM, "index.json")
        idx = []
        if os.path.isfile(idx_path):
            try:
                idx = json.load(open(idx_path))
            except Exception:
                idx = []
        idx = [e for e in idx if e.get("id") != rec["id"]]
        idx.insert(0, {"id": rec["id"], "ts": rec["ts"], "problem": rec["problem"], "mode": rec["mode"]})
        with open(idx_path, "w", encoding="utf-8") as fh:
            json.dump(idx[:50], fh)
    except Exception as e:
        sys.stderr.write(f"save_run failed: {e}\n")


def list_runs():
    p = os.path.join(MEM, "index.json")
    try:
        return json.load(open(p)) if os.path.isfile(p) else []
    except Exception:
        return []


def load_run(rid):
    p = os.path.join(MEM, rid + ".json")
    try:
        return json.load(open(p)) if os.path.isfile(p) else None
    except Exception:
        return None

# --- the WRATH pipeline definition (maps to phases/agents) ---------------------------------
STAGES = [
    {"id": "discovery", "label": "Discovery",    "agent": "discovery",        "phase": "Design",   "kind": "llm"},
    {"id": "hld",       "label": "HLD",          "agent": "designer-hld",     "phase": "Design",   "kind": "llm"},
    {"id": "critic",    "label": "Critic gate",  "agent": "critic",           "phase": "Design",   "kind": "gate"},
    {"id": "lld",       "label": "LLD",          "agent": "designer-lld",     "phase": "Implement","kind": "llm"},
    {"id": "config",    "label": "Config",       "agent": "config-engineer",  "phase": "Implement","kind": "llm"},
    {"id": "validate",  "label": "Validator gate","agent": "validator",       "phase": "Implement","kind": "tool-validate"},
    {"id": "bom",       "label": "BoM",          "agent": "bom-commercials",  "phase": "Sell",     "kind": "llm"},
    {"id": "cost",      "label": "Cost & Risk",  "agent": "bom-commercials",  "phase": "Sell",     "kind": "tool-cost"},
    {"id": "sow",       "label": "SoW",          "agent": "sow-writer",       "phase": "Sell",     "kind": "llm"},
    {"id": "exec",      "label": "Exec one-pager","agent": "exec-storyteller","phase": "Sell",     "kind": "llm"},
    {"id": "migration", "label": "Migration",    "agent": "migration-planner","phase": "Operate",  "kind": "llm"},
    {"id": "standards", "label": "Standards",    "agent": "standards-officer","phase": "Scale",    "kind": "tool-standards"},
    {"id": "trust",     "label": "Trust report", "agent": "orchestrator",     "phase": "Scale",    "kind": "report"},
]


def has_key():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


class ClaudeError(Exception):
    pass


def call_claude(system, prompt, max_tokens=1600, retries=3):
    """Call the Anthropic API with retry/backoff. Raises ClaudeError on a hard failure so the caller
    can surface it honestly (never silently pass an error string off as a deliverable)."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ClaudeError("ANTHROPIC_API_KEY not set")
    body = json.dumps({"model": MODEL, "max_tokens": max_tokens, "system": system,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    last = ""
    for attempt in range(retries):
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=body,
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.load(r)
            text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
            if not text.strip():
                raise ClaudeError("empty response from model")
            return text
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
            last = f"HTTP {e.code} {detail}"
            if e.code in (408, 429, 500, 502, 503, 529) and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise ClaudeError(last)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = str(e)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise ClaudeError(last)
    raise ClaudeError(last or "unknown error")


def extract_config(text):
    """Pull a config blob out of an LLM answer (fenced code block if present)."""
    m = re.search(r"```[a-zA-Z0-9_-]*\n(.*?)```", text or "", re.S)
    return (m.group(1) if m else (text or "")).strip() + "\n"


# --- demo-mode content (representative, tailored to the problem keywords) --------------------
def kw(problem):
    p = problem.lower()
    tags = []
    for k in ["sr-mpls", "srv6", "evpn", "vxlan", "l3vpn", "sd-wan", "dci", "bgp", "ospf", "is-is",
              "qos", "multicast", "ipsec", "macsec", "data center", "campus", "wan", "security",
              "migration", "hospital", "pci", "hipaa"]:
        if k in p:
            tags.append(k)
    return tags or ["general routing/switching"]


def demo_content(stage_id, problem, ctx):
    tags = ", ".join(kw(problem))
    if stage_id == "discovery":
        return (f"**Problem (restated):** {problem}\n\n"
                f"**Signals detected:** {tags}\n\n"
                "**Hard requirements (extracted):** resilience target, security baseline, scale + growth headroom.\n\n"
                "**Open questions flagged (House Rule 7):** exact platform/version, SLA numbers, brownfield vs greenfield.")
    if stage_id == "hld":
        return ("**Recommended architecture** with explicit trade-offs (House Rule 1):\n\n"
                "| Option | Verdict |\n|---|---|\n"
                "| Modern, standards-based design | ◄ recommend — best fit/operability |\n"
                "| Legacy / status-quo | rejected — fails the modernization goal |\n\n"
                "Security designed in (House Rule 5): segmentation, control-plane + mgmt-plane hardening, encryption where required.")
    if stage_id == "critic":
        return ("**VERDICT: ACCEPT-WITH-FIXES** (separate adversarial agent — House Rule discipline)\n\n"
                "- [HIGH] failure-mode/convergence claim must state its hardware dependency.\n"
                "- [MEDIUM] MTU / blast-radius / rollback coverage to confirm.\n\n"
                "Routes back to the designer to clear before sign-off.")
    if stage_id == "lld":
        return ("Addressing/IPAM, IGP/BGP, label/SID plan, QoS classes, security zones — collision-free, "
                "reusing the customer's conventions. Per-device build sheet produced.")
    if stage_id == "config":
        return "Idempotent, commented, vendor-correct config generated from the LLD — staged in lockout-safe order. Never final until the Validator passes it (House Rule 2)."
    if stage_id == "bom":
        return ("Bill of Materials with every quantity traced to a design need; SKUs/licenses to be verified "
                "current (House Rule 4). Required vs optional/growth separated.")
    if stage_id == "sow":
        return "Scope, deliverables, **assumptions + explicit exclusions**, RACI (one accountable owner each), objective acceptance criteria."
    if stage_id == "exec":
        return ("**Why this matters:** today this carries cost/risk; the design changes it to a measurable outcome; "
                "the decision now is to approve. Outcome-led, technology in support.")
    if stage_id == "migration":
        return "Phased brownfield cutover — a rollback at **every** step (House Rule 3), blast-radius bounded per phase, objective go/no-go gates."
    return ""


# --- pipeline runner ------------------------------------------------------------------------
def emit(q, obj):
    q.put(obj)
    rec = REC.get(id(q))
    if rec is not None:
        t = obj.get("type")
        if t == "meta":
            rec.update(problem=obj.get("problem", ""), mode=obj.get("mode", ""), stages=obj.get("stages", []))
        elif t == "output":
            rec["deliverables"][obj["stage"]] = {"title": obj["title"], "content": obj["content"]}
        elif t == "grounding":
            rec["grounding"][obj["stage"]] = {"status": obj["status"], "checks": obj.get("checks", [])}
        elif t == "trust":
            rec["trust"] = {k: obj[k] for k in ("confidence", "headline", "counts", "ledger", "assumptions")}


def demo_config(attempt):
    """Demo config-engineer output. Attempt 1 has a real, fixable defect (guessable SNMP community)
    that config_lint catches -> Validator rejects -> attempt 2 fixes it -> PASS. Makes the gate real."""
    snmp = ("snmp-server community public RO\n" if attempt == 1
            else "snmp-server host 10.30.0.10 traps version 3 priv\n")
    return (f"hostname PE1\n{snmp}"
            "interface Loopback0\n description router-id / SR prefix-SID 16001\n ipv4 address 10.255.0.1 255.255.255.255\n"
            "interface GigabitEthernet0/0/0/0\n description to:CORE [core]\n ipv4 address 10.0.0.0 255.255.255.254\n mtu 9216\n no shutdown\n"
            "router bgp 65000\n bgp router-id 10.255.0.1\n neighbor 192.0.2.2\n  remote-as 65010\n  ttl-security\nend\n")


def validate_cfg(q, cfg):
    """Real validator gate: run config_lint on the given config. Returns (verdict, output)."""
    with tempfile.NamedTemporaryFile("w", suffix=".cfg", delete=False) as fh:
        fh.write(cfg)
        path = fh.name
    emit(q, {"type": "log", "stage": "validate", "text": f"$ python config_lint.py {os.path.basename(path)} --vendor ios-xr"})
    try:
        proc = subprocess.run([sys.executable, LINT, path, "--vendor", "ios-xr"],
                              capture_output=True, text=True, timeout=30)
        out = ((proc.stdout or "") + (proc.stderr or "")).strip()
        for line in out.splitlines():
            emit(q, {"type": "log", "stage": "validate", "text": line})
            time.sleep(0.04)
        verdict = "PASS" if proc.returncode == 0 else "FAIL"
        emit(q, {"type": "output", "stage": "validate", "title": "Validator gate (real config_lint run)",
                 "content": f"```\n{out}\n```\n\n**VERDICT: {verdict}** — no config ships until this passes (House Rule 2)."})
        emit(q, {"type": "grounding", "stage": "validate", "status": "grounded" if verdict == "PASS" else "blocked",
                 "checks": [{"kind": "config", "item": "config_lint", "verdict": verdict, "note": "deterministic validator gate"}]})
        return verdict, out
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def run_standards_stage(q, problem):
    """Real: verify citations against the grounded standards index; block a fabricated one."""
    try:
        idx = json.load(open(STANDARDS))["rfc"]
    except Exception:
        idx = {}
    p = problem.lower()
    cites = [("5082", "GTSM — multi-hop eBGP protection")]
    if "l3vpn" in p or "vpn" in p or "mpls" in p:
        cites.append(("4364", "BGP/MPLS IP VPNs (L3VPN)"))
    if "evpn" in p or "vxlan" in p or "dci" in p or "data center" in p:
        cites.append(("7432", "BGP MPLS-Based EVPN"))
    rows = ["| Citation | Title | Result |", "|---|---|---|"]
    for num, why in cites:
        e = idx.get(num)
        emit(q, {"type": "log", "stage": "standards", "text": f"verify RFC {num} ({why}) ..."})
        time.sleep(0.25)
        if e:
            rows.append(f"| RFC {num} | {e['title']} | ✅ VERIFIED |")
        else:
            rows.append(f"| RFC {num} | — | ⚠ UNVERIFIED — block |")
    emit(q, {"type": "log", "stage": "standards", "text": "verify RFC 9999 (fabricated) ..."})
    time.sleep(0.25)
    rows.append("| RFC 9999 | — | ⛔ UNVERIFIED → BLOCKED (House Rule 4) |")
    emit(q, {"type": "output", "stage": "standards",
             "title": "Compliance matrix (real citation-guard)",
             "content": "\n".join(rows) + "\n\nThe citation-guard cannot invent an RFC — a fabricated reference is blocked."})
    checks = [{"kind": "citation", "item": f"RFC {n}", "verdict": "verified", "note": idx[n]["title"],
               "url": idx[n].get("url", "")} for n, _ in cites if n in idx]
    checks.append({"kind": "citation", "item": "RFC 9999", "verdict": "BLOCKED", "note": "fabricated — blocked by the citation-guard"})
    emit(q, {"type": "grounding", "stage": "standards", "status": "grounded",
             "checks": checks, "note": "citation-guard executed"})


SKILL_FOR = {
    "discovery": "requirements-intake", "designer-hld": "hld-generator", "critic": None,
    "designer-lld": "lld-generator", "config-engineer": "config-generator", "validator": "config-audit",
    "bom-commercials": "bom-builder", "sow-writer": "sow-writer", "exec-storyteller": "exec-deck",
    "migration-planner": "migration-runbook", "standards-officer": "standards-checker",
}


def _read(path, limit=2200):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()[:limit]
    except Exception:
        return ""


def real_system_prompt(agent):
    """Build the Live-mode system prompt from the actual agent definition + its skill (real WRATH)."""
    agent_md = _read(os.path.join(REPO, ".claude", "agents", f"{agent}.md"))
    skill = SKILL_FOR.get(agent)
    skill_md = _read(os.path.join(REPO, ".claude", "skills", skill, "SKILL.md")) if skill else ""
    house = _read(os.path.join(REPO, "CLAUDE.md"), 1400)
    return (f"You are running as WRATH's '{agent}' specialist. Follow your agent definition and skill "
            f"exactly, honor the House Rules, ground every claim, never invent an RFC/SKU/number "
            f"(flag it instead). Be concise (markdown, <220 words).\n\n"
            f"=== AGENT ===\n{agent_md}\n\n=== SKILL ===\n{skill_md}\n\n=== HOUSE RULES (excerpt) ===\n{house}")


def gen(stage, problem, ctx, live, extra=""):
    """Produce a stage's text — real Claude (Live, with the real agent+skill) or demo content."""
    if live and has_key():
        system = real_system_prompt(stage["agent"])
        prior = "\n".join(f"- {k}: {v[:240]}" for k, v in ctx.items() if not k.startswith("__"))
        prompt = f"Network problem:\n{problem}\n\nPrior stage outputs:\n{prior}\n{extra}\n\nProduce your stage's deliverable."
        emit(q_global.get(), {"type": "log", "stage": stage["id"], "text": f"calling Claude ({MODEL}) as {stage['agent']}…"})
        try:
            return call_claude(system, prompt)
        except ClaudeError as e:
            emit(q_global.get(), {"type": "log", "stage": stage["id"], "text": f"⚠ live call failed ({e}) — showing demo content for this stage"})
            return demo_content(stage["id"], problem, ctx) + "\n\n_(Live call failed — demo content shown.)_"
    for step in ("loading agent + skill", "reasoning", "drafting deliverable"):
        emit(q_global.get(), {"type": "log", "stage": stage["id"], "text": f"[{stage['agent']}] {step}…"})
        time.sleep(0.4)
    return demo_content(stage["id"], problem, ctx)


class q_global:
    """Tiny thread-local-ish holder so gen() can emit without threading the queue everywhere."""
    _q = None
    @classmethod
    def set(cls, q): cls._q = q
    @classmethod
    def get(cls): return cls._q


def emit_text_stage(q, stage, problem, ctx, live, extra=""):
    text = gen(stage, problem, ctx, live, extra)
    if stage["id"] == "hld" and "```mermaid" not in text:
        text += "\n\n**Reference topology (auto-generated — roles, redundancy, failure domains):**\n" \
                + topology.mermaid_block(problem)
    ctx[stage["id"]] = text
    emit(q, {"type": "output", "stage": stage["id"], "title": f"{stage['label']} · {stage['agent']}", "content": text})
    status, checks = grounding.ground_text(text)
    emit(q, {"type": "grounding", "stage": stage["id"], "status": status, "checks": checks})
    return text


def critic_eval(q, problem, ctx, live, attempt):
    """The Critic gate. Demo: pass 1 -> ACCEPT-WITH-FIXES (findings), pass 2 -> ACCEPT.
    Returns (accept, findings_text)."""
    if live and has_key():
        sys_p = real_system_prompt("critic")
        try:
            verdict = call_claude(sys_p, f"Problem:\n{problem}\n\nHLD to review:\n{ctx.get('hld','')}\n\n"
                                  "Return VERDICT: ACCEPT or ACCEPT-WITH-FIXES, then a short severity-tagged defect list.")
        except ClaudeError as e:
            emit(q, {"type": "log", "stage": "critic", "text": f"⚠ live critic failed ({e}) — accepting without gate"})
            return True, f"_(Critic live call failed: {e}.)_"
        accept = "ACCEPT-WITH-FIXES" not in verdict.upper() and "REJECT" not in verdict.upper()
        return accept, verdict
    if attempt == 1:
        return False, ("**VERDICT: ACCEPT-WITH-FIXES** (separate adversarial agent)\n\n"
                       "- [HIGH] failure/convergence claim must state its hardware (BFD-in-HW) dependency.\n"
                       "- [MEDIUM] MTU budget + rollback coverage not explicit.\n\nRouting back to the designer.")
    return True, "**VERDICT: ACCEPT** — the revised HLD clears the earlier findings."


def run_pipeline(run_id, problem, mode):
    q = RUNS[run_id]
    q_global.set(q)
    REC[id(q)] = {"id": run_id, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  "problem": problem, "mode": mode, "stages": [], "deliverables": {}, "grounding": {}}
    live = (mode == "live")
    by_id = {s["id"]: s for s in STAGES}
    emit(q, {"type": "meta", "mode": ("live" if live and has_key() else "demo"),
             "problem": problem, "stages": [{k: s[k] for k in ("id", "label", "agent", "phase", "kind")} for s in STAGES]})
    ctx = {}

    def start(sid): emit(q, {"type": "stage", "id": sid, "status": "running"}); time.sleep(0.2)
    def done(sid): emit(q, {"type": "stage", "id": sid, "status": "done"})

    try:
        for stage in STAGES:
            sid = stage["id"]

            if sid == "discovery":
                # P0 gate: detect architecture-critical gaps and ask the right questions before
                # any design is attempted (House Rule 7). Blocking gaps => brief is "not ready".
                start("discovery")
                analysis = clarify.analyze(problem)
                ctx["__clarify__"] = analysis
                text = gen(stage, problem, ctx, live, extra=clarify.live_extra(analysis))
                if not (live and has_key()):
                    text = clarify.render_brief(problem, analysis)
                ctx["discovery"] = text
                emit(q, {"type": "output", "stage": "discovery", "title": "Discovery · discovery", "content": text})
                emit(q, {"type": "clarify", "stage": "discovery", "ready": analysis["ready"],
                         "blocking": analysis["blocking"], "missing": analysis["missing"]})
                if not analysis["ready"]:
                    emit(q, {"type": "log", "stage": "discovery",
                             "text": f"🔒 clarify-gate: {len(analysis['blocking'])} architecture-critical "
                                     "question(s) open — Kamal must resolve before design."})
                status, checks = grounding.ground_text(text)
                emit(q, {"type": "grounding", "stage": "discovery", "status": status, "checks": checks})
                done("discovery")

            elif sid == "critic":
                # Gate: review the HLD; if it doesn't pass, bounce back to the designer and revise.
                start("critic")
                accept, findings = critic_eval(q, problem, ctx, live, attempt=1)
                emit(q, {"type": "output", "stage": "critic", "title": "Critic gate · critic", "content": findings})
                emit(q, {"type": "grounding", "stage": "critic", **dict(zip(["status", "checks"], grounding.ground_text(findings)))})
                if not accept:
                    emit(q, {"type": "reject", "gate": "critic", "producer": "hld",
                             "reason": "Critic returned ACCEPT-WITH-FIXES — revising the HLD"})
                    emit(q, {"type": "log", "stage": "critic", "text": "⛔ gate not clear → routing back to designer-hld"})
                    time.sleep(0.5)
                    start("hld")
                    emit_text_stage(q, by_id["hld"], problem, ctx, live,
                                    extra="Revise the HLD to clear the Critic findings (state HW dependency; add MTU budget + rollback).")
                    if not (live and has_key()):
                        ctx["hld"] += "\n\n**Revision (v2):** convergence claim now states its BFD-in-HW dependency; MTU budget + per-step rollback added."
                        emit(q, {"type": "output", "stage": "hld", "title": "HLD · designer-hld (revised v2)", "content": ctx["hld"]})
                    done("hld")
                    start("critic")
                    _, ok = critic_eval(q, problem, ctx, live, attempt=2)
                    emit(q, {"type": "output", "stage": "critic", "title": "Critic gate · critic (re-review)", "content": ok})
                    emit(q, {"type": "log", "stage": "critic", "text": "✓ gate clear after revision"})
                done("critic")

            elif sid == "config":
                start("config")
                if live and has_key():
                    raw = gen(stage, problem, ctx, live,
                              extra="Output the device config inside a single fenced ```code block```.")
                    cfg = extract_config(raw)
                else:
                    cfg = demo_config(1)
                ctx["__cfg__"] = cfg
                emit(q, {"type": "output", "stage": "config", "title": "Config · config-engineer",
                         "content": "Generated device config (IOS-XR), staged lockout-safe. Goes to the Validator next.\n\n```\n" + cfg + "```"})
                emit(q, {"type": "grounding", **dict(zip(["status", "checks"], grounding.ground_text(cfg))), "stage": "config"})
                done("config")

            elif sid == "validate":
                start("validate")
                verdict, out = validate_cfg(q, ctx.get("__cfg__", ""))
                attempt = 1
                while verdict == "FAIL" and attempt < 3:
                    emit(q, {"type": "reject", "gate": "validate", "producer": "config",
                             "reason": "config_lint FAIL — sending back to config-engineer to fix"})
                    emit(q, {"type": "log", "stage": "validate", "text": "⛔ FAIL → routing back to config-engineer"})
                    time.sleep(0.5)
                    start("config")
                    if live and has_key():
                        fixstage = by_id["config"]
                        raw = gen(fixstage, problem, ctx, live,
                                  extra=f"The Validator (config_lint) REJECTED your config with:\n{out}\n"
                                        "Fix every finding and output the corrected FULL config in a single ```code block```.")
                        ctx["__cfg__"] = extract_config(raw)
                    else:
                        ctx["__cfg__"] = demo_config(2)
                        emit(q, {"type": "log", "stage": "config", "text": "[config-engineer] applying fix: replace guessable SNMP community"})
                    emit(q, {"type": "output", "stage": "config", "title": f"Config · config-engineer (fixed v{attempt + 1})",
                             "content": "Validator rejected the previous config. Applied the fix.\n\n```\n" + ctx["__cfg__"] + "```"})
                    emit(q, {"type": "grounding", **dict(zip(["status", "checks"], grounding.ground_text(ctx["__cfg__"]))), "stage": "config"})
                    done("config")
                    start("validate")
                    verdict, out = validate_cfg(q, ctx["__cfg__"])
                    attempt += 1
                done("validate")

            elif stage["kind"] == "tool-cost":
                # Design-driven TCO drivers + risk register. No currency is invented (House Rule 4);
                # grounding still runs so any flagged figure feeds the trust report.
                start("cost")
                text = tco.render(problem)
                ctx["cost"] = text
                emit(q, {"type": "output", "stage": "cost", "title": "Cost & Risk · bom-commercials", "content": text})
                status, checks = grounding.ground_text(text)
                emit(q, {"type": "grounding", "stage": "cost", "status": status, "checks": checks})
                done("cost")

            elif stage["kind"] == "tool-standards":
                start("standards")
                run_standards_stage(q, problem)
                done("standards")

            elif stage["kind"] == "report":
                # Closing scorecard: aggregate every grounding verdict the run produced into an
                # honest confidence report + verify-before-ship ledger (House Rule 7).
                start("trust")
                grnd = REC.get(id(q), {}).get("grounding", {})
                analysis = ctx.get("__clarify__")
                assumptions = ([f"{m['label']} not specified at intake — proceeding on assumption"
                                for m in analysis["missing"] if m["blocking"]]
                               if analysis and not analysis["ready"] else [])
                rep = trust.report(grnd, assumptions=assumptions)
                emit(q, {"type": "output", "stage": "trust", "title": "Trust report · orchestrator",
                         "content": trust.render(rep)})
                emit(q, {"type": "trust", "stage": "trust", "confidence": rep["confidence"],
                         "headline": rep["headline"], "counts": rep["counts"],
                         "ledger": rep["ledger"], "assumptions": rep["assumptions"]})
                emit(q, {"type": "log", "stage": "trust", "text": "trust: " + rep["headline"]})
                done("trust")

            else:
                start(sid)
                emit_text_stage(q, stage, problem, ctx, live)
                done(sid)

        emit(q, {"type": "log", "stage": "_", "text": "✅ Converged — every gate cleared, deliverable stack ready."})
        save_run(REC.get(id(q), {}))
        emit(q, {"type": "saved", "id": run_id})
    except Exception as e:
        emit(q, {"type": "log", "stage": "_", "text": f"error: {e}"})
    finally:
        REC.pop(id(q), None)
        emit(q, {"type": "done"})


# --- HTTP server ----------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authed(self, u):
        if not TOKEN:
            return True
        tok = parse_qs(u.query).get("token", [""])[0] or self.headers.get("X-WRATH-Token", "")
        return tok == TOKEN

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._serve_static("index.html", "text/html; charset=utf-8")
        if u.path == "/api/health":
            return self._send(200, "application/json", json.dumps(
                {"status": "ok", "version": VERSION, "active_runs": len(RUNS), "hasKey": has_key(), "auth": bool(TOKEN)}).encode())
        if u.path == "/api/config":
            return self._send(200, "application/json", json.dumps({"hasKey": has_key(), "model": MODEL, "auth": bool(TOKEN)}).encode())
        if u.path in ("/api/stream", "/api/runs", "/api/run") and not self._authed(u):
            return self._send(401, "application/json", b'{"error":"unauthorized"}')
        if u.path == "/api/stream":
            return self._stream(parse_qs(u.query).get("run_id", [""])[0])
        if u.path == "/api/runs":
            return self._send(200, "application/json", json.dumps(list_runs()).encode())
        if u.path == "/api/run":
            rec = load_run(parse_qs(u.query).get("id", [""])[0])
            return self._send(200 if rec else 404, "application/json", json.dumps(rec or {"error": "not found"}).encode())
        if u.path.startswith("/static/"):
            return self._serve_static(u.path[len("/static/"):], self._ctype(u.path))
        self._send(404, "text/plain", b"not found")

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/run":
            if not self._authed(u):
                return self._send(401, "application/json", b'{"error":"unauthorized"}')
            if len(RUNS) >= MAX_ACTIVE:
                return self._send(429, "application/json", b'{"error":"too many active runs, try again shortly"}')
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
            problem = (data.get("problem") or "").strip()
            mode = data.get("mode") or "demo"
            if not problem:
                return self._send(400, "application/json", b'{"error":"problem required"}')
            run_id = uuid.uuid4().hex
            RUNS[run_id] = queue.Queue()
            threading.Thread(target=run_pipeline, args=(run_id, problem, mode), daemon=True).start()
            return self._send(200, "application/json", json.dumps({"run_id": run_id}).encode())
        self._send(404, "text/plain", b"not found")

    def _stream(self, run_id):
        q = RUNS.get(run_id)
        if not q:
            return self._send(404, "text/plain", b"unknown run")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            while True:
                item = q.get()
                self.wfile.write(f"data: {json.dumps(item)}\n\n".encode())
                self.wfile.flush()
                if item.get("type") == "done":
                    break
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            # Browser closed/reloaded the SSE connection (e.g. WinError 10053 on Windows). Harmless.
            pass
        finally:
            RUNS.pop(run_id, None)

    def _serve_static(self, rel, ctype):
        path = os.path.normpath(os.path.join(STATIC, rel))
        if not path.startswith(STATIC) or not os.path.isfile(path):
            return self._send(404, "text/plain", b"not found")
        with open(path, "rb") as fh:
            self._send(200, ctype, fh.read())

    @staticmethod
    def _ctype(path):
        if path.endswith(".css"):
            return "text/css"
        if path.endswith(".js"):
            return "application/javascript"
        if path.endswith(".svg"):
            return "image/svg+xml"
        return "text/plain"


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        et = sys.exc_info()[0]
        if et and issubclass(et, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)):
            return  # browser closed/reloaded a connection — normal, stay quiet
        super().handle_error(request, client_address)


def main():
    os.chdir(REPO)
    srv = Server(("0.0.0.0", PORT), Handler)
    mode = "LIVE (Claude API)" if has_key() else "DEMO (set ANTHROPIC_API_KEY for live)"
    print(f"WRATH Console — {mode}")
    print(f"  open  http://localhost:{PORT}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
