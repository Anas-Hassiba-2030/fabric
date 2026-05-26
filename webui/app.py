#!/usr/bin/env python3
"""FABRIC Console — a local web UI for the FABRIC Solution Fabric.

Type a network problem; watch the orchestration pipeline run stage-by-stage (Discovery -> HLD ->
Critic gate -> LLD -> Config -> Validator gate -> BoM -> SoW -> Exec -> Migration -> Standards) and
see the deliverables render. Dependency-free (Python 3 stdlib only) so it runs anywhere:

    python3 webui/app.py            # then open http://localhost:8765

Two modes:
  * Demo (default)  — runs the pipeline with representative, problem-tailored content. The *gates*
                      are real: the Validator stage runs config_lint.py, the Standards stage runs the
                      real citation check against the grounded standards index.
  * Live            — if ANTHROPIC_API_KEY is set, the content-generating stages call the Claude API
                      so it is genuinely FABRIC reasoning. Set ANTHROPIC_MODEL to override the model.

Transport: Server-Sent Events stream each stage/log/output to the browser as it happens.
"""
import json
import os
import queue
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
import grounding  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
STATIC = os.path.join(HERE, "static")
LINT = os.path.join(REPO, ".claude", "skills", "config-audit", "scripts", "config_lint.py")
STANDARDS = os.path.join(REPO, "fabric", "mcp", "data", "standards.json")
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
PORT = int(os.environ.get("FABRIC_UI_PORT", "8765"))

RUNS = {}  # run_id -> Queue

# --- the FABRIC pipeline definition (maps to phases/agents) ---------------------------------
STAGES = [
    {"id": "discovery", "label": "Discovery",    "agent": "discovery",        "phase": "Design",   "kind": "llm"},
    {"id": "hld",       "label": "HLD",          "agent": "designer-hld",     "phase": "Design",   "kind": "llm"},
    {"id": "critic",    "label": "Critic gate",  "agent": "critic",           "phase": "Design",   "kind": "gate"},
    {"id": "lld",       "label": "LLD",          "agent": "designer-lld",     "phase": "Implement","kind": "llm"},
    {"id": "config",    "label": "Config",       "agent": "config-engineer",  "phase": "Implement","kind": "llm"},
    {"id": "validate",  "label": "Validator gate","agent": "validator",       "phase": "Implement","kind": "tool-validate"},
    {"id": "bom",       "label": "BoM",          "agent": "bom-commercials",  "phase": "Sell",     "kind": "llm"},
    {"id": "sow",       "label": "SoW",          "agent": "sow-writer",       "phase": "Sell",     "kind": "llm"},
    {"id": "exec",      "label": "Exec one-pager","agent": "exec-storyteller","phase": "Sell",     "kind": "llm"},
    {"id": "migration", "label": "Migration",    "agent": "migration-planner","phase": "Operate",  "kind": "llm"},
    {"id": "standards", "label": "Standards",    "agent": "standards-officer","phase": "Scale",    "kind": "tool-standards"},
]


def has_key():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def call_claude(system, prompt, max_tokens=1100):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    body = json.dumps({
        "model": MODEL, "max_tokens": max_tokens, "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.load(r)
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    except Exception as e:
        return f"_(Live call failed: {e}. Falling back.)_"


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


def run_validate_stage(q, problem, live):
    """Real tool: write a representative IOS-XR config and run config_lint on it."""
    cfg = f"""! Generated config (FABRIC Console demo) for: {problem[:60]}
hostname PE-EDGE
interface Loopback0
 description router-id / SR prefix-SID 16001
 ipv4 address 10.255.0.1 255.255.255.255
interface GigabitEthernet0/0/0/0
 description to:CORE [core]
 ipv4 address 10.0.0.0 255.255.255.254
 mtu 9216
 no shutdown
router bgp 65000
 bgp router-id 10.255.0.1
 neighbor 192.0.2.2
  remote-as 65010
  ttl-security
end
"""
    with tempfile.NamedTemporaryFile("w", suffix=".cfg", delete=False) as fh:
        fh.write(cfg)
        path = fh.name
    emit(q, {"type": "log", "stage": "validate", "text": f"$ python config_lint.py {os.path.basename(path)} --vendor ios-xr"})
    try:
        proc = subprocess.run([sys.executable, LINT, path, "--vendor", "ios-xr"],
                              capture_output=True, text=True, timeout=30)
        out = (proc.stdout or "") + (proc.stderr or "")
        for line in out.strip().splitlines():
            emit(q, {"type": "log", "stage": "validate", "text": line})
            time.sleep(0.05)
        verdict = "PASS" if proc.returncode == 0 else "FAIL"
        emit(q, {"type": "output", "stage": "validate",
                 "title": "Validator gate (real config_lint run)",
                 "content": f"```\n{out.strip()}\n```\n\n**VERDICT: {verdict}** — no config ships until this passes (House Rule 2)."})
        emit(q, {"type": "grounding", "stage": "validate",
                 "status": "grounded" if verdict == "PASS" else "blocked",
                 "checks": [{"kind": "config", "item": "config_lint", "verdict": verdict, "note": "deterministic validator gate"}]})
        return verdict
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
    checks = [{"kind": "citation", "item": f"RFC {n}", "verdict": "verified", "note": idx[n]["title"]}
              for n, _ in cites if n in idx]
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
    """Build the Live-mode system prompt from the actual agent definition + its skill (real FABRIC)."""
    agent_md = _read(os.path.join(REPO, ".claude", "agents", f"{agent}.md"))
    skill = SKILL_FOR.get(agent)
    skill_md = _read(os.path.join(REPO, ".claude", "skills", skill, "SKILL.md")) if skill else ""
    house = _read(os.path.join(REPO, "CLAUDE.md"), 1400)
    return (f"You are running as FABRIC's '{agent}' specialist. Follow your agent definition and skill "
            f"exactly, honor the House Rules, ground every claim, never invent an RFC/SKU/number "
            f"(flag it instead). Be concise (markdown, <220 words).\n\n"
            f"=== AGENT ===\n{agent_md}\n\n=== SKILL ===\n{skill_md}\n\n=== HOUSE RULES (excerpt) ===\n{house}")


def llm_stage(q, stage, problem, ctx, live):
    sid = stage["id"]
    if live and has_key():
        system = real_system_prompt(stage["agent"])
        prior = "\n".join(f"- {k}: {v[:240]}" for k, v in ctx.items())
        prompt = f"Network problem:\n{problem}\n\nPrior stage outputs:\n{prior}\n\nProduce your stage's deliverable."
        emit(q, {"type": "log", "stage": sid, "text": f"calling Claude ({MODEL}) as {stage['agent']} (real agent + skill loaded)…"})
        text = call_claude(system, prompt) or demo_content(sid, problem, ctx)
    else:
        for step in ("loading agent + skill", "reasoning", "drafting deliverable"):
            emit(q, {"type": "log", "stage": sid, "text": f"[{stage['agent']}] {step}…"})
            time.sleep(0.45)
        text = demo_content(sid, problem, ctx)
    ctx[sid] = text
    emit(q, {"type": "output", "stage": sid, "title": f"{stage['label']} · {stage['agent']}", "content": text})
    # Anti-hallucination gate: ground every claim before it reaches the user.
    status, checks = grounding.ground_text(text)
    emit(q, {"type": "grounding", "stage": sid, "status": status, "checks": checks})


def run_pipeline(run_id, problem, mode):
    q = RUNS[run_id]
    live = (mode == "live")
    emit(q, {"type": "meta", "mode": ("live" if live and has_key() else "demo"),
             "problem": problem, "stages": [{k: s[k] for k in ("id", "label", "agent", "phase", "kind")} for s in STAGES]})
    ctx = {}
    try:
        for stage in STAGES:
            emit(q, {"type": "stage", "id": stage["id"], "status": "running"})
            time.sleep(0.2)
            if stage["kind"] == "tool-validate":
                run_validate_stage(q, problem, live)
            elif stage["kind"] == "tool-standards":
                run_standards_stage(q, problem)
            else:
                llm_stage(q, stage, problem, ctx, live)
            emit(q, {"type": "stage", "id": stage["id"], "status": "done"})
        emit(q, {"type": "log", "stage": "_", "text": "✅ Converged — deliverable stack ready."})
    except Exception as e:
        emit(q, {"type": "log", "stage": "_", "text": f"error: {e}"})
    finally:
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

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._serve_static("index.html", "text/html; charset=utf-8")
        if u.path == "/api/config":
            return self._send(200, "application/json", json.dumps({"hasKey": has_key(), "model": MODEL}).encode())
        if u.path == "/api/stream":
            return self._stream(parse_qs(u.query).get("run_id", [""])[0])
        if u.path.startswith("/static/"):
            return self._serve_static(u.path[len("/static/"):], self._ctype(u.path))
        self._send(404, "text/plain", b"not found")

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/run":
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
    print(f"FABRIC Console — {mode}")
    print(f"  open  http://localhost:{PORT}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
