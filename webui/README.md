# FABRIC Console — local web UI

A modern, dependency-free front-end for FABRIC. Type a network problem and watch the orchestration
pipeline run stage-by-stage (Discovery → HLD → **Critic gate** → LLD → Config → **Validator gate** →
BoM → SoW → Exec → Migration → Standards), then read the deliverables.

## Run it (no install — stock Python 3)
```bash
python3 webui/app.py
# then open http://localhost:8765
```
Change the port with `FABRIC_UI_PORT=9000 python3 webui/app.py`.

## Two modes
- **Demo** (default, zero config) — the pipeline runs with representative, problem-tailored content.
  **The gates are real:** the Validator stage actually runs `config_lint.py`, and the Standards stage
  runs the real citation-guard against the grounded standards index (it verifies real RFCs and
  **blocks a fabricated one** — House Rule 4).
- **Live** — set your key and FABRIC's reasoning stages call the Claude API:
  ```bash
  export ANTHROPIC_API_KEY=sk-ant-...
  export ANTHROPIC_MODEL=claude-sonnet-4-6   # optional; opus/haiku also fine
  python3 webui/app.py
  ```
  The UI auto-detects the key and enables the **Live** toggle.

## How it works
- `app.py` — stdlib HTTP server. `POST /api/run` starts a run; `GET /api/stream?run_id=…` streams
  stage/log/output events over Server-Sent Events. The Validator and Standards stages shell out to the
  real repo tools; the reasoning stages call Claude in Live mode or use tailored demo content otherwise.
- `static/index.html` — single-file SPA (no build step): animated stage pipeline grouped by phase, a
  live log, and deliverables rendered from markdown.

## Run it beyond localhost (Phase 5 — productionize)
The server already binds `0.0.0.0`, so it's reachable on your LAN at `http://<your-ip>:8765`. Knobs:
```bash
FABRIC_UI_PORT=9000          # change the port
FABRIC_UI_TOKEN=some-secret  # require a token: the console + API are gated (open if unset)
FABRIC_UI_MAX_ACTIVE=8       # cap concurrent runs
```
With a token set, the page prompts for it once (stored in the browser) and every API call must carry it.
- **Health check:** `GET /api/health` → `{status, version, active_runs, hasKey, auth}` (for uptime monitors).
- **Expose to the internet:** put it behind a tunnel (e.g. `cloudflared`/`ngrok`) or a reverse proxy with
  TLS — and **always set `FABRIC_UI_TOKEN`** if you do.

## Anti-hallucination + Live mode (hardened)
Every stage output passes through `grounding.py` before you see it: RFC citations are verified against
the grounded index (**fabricated ones are blocked**), prices/SKUs/latency claims are **flagged** as
"needs verification", and configs are run through the real `config_lint`. Gates have teeth — a failing
config or HLD is **rejected and routed back** to be fixed, then re-checked.

Live mode (`ANTHROPIC_API_KEY`) loads each specialist's **real agent definition + skill** as its prompt,
chains context forward, retries the API with backoff, and surfaces failures honestly (never passes an
error off as a deliverable). On a Validator reject it re-prompts Claude with the actual lint findings to
fix the config.

## Proof tests + doctor (no API key needed for the proofs)
```
python webui/doctor.py           # full system check; with ANTHROPIC_API_KEY also makes a real Opus 4.7 call
python webui/test_grounding.py   # fabricated RFC blocked, bad config failed, numbers flagged
python webui/test_live.py        # live wiring chains, gates bite, live hallucination caught (mocked Claude)
```
The first two proofs are part of `bash run_tests.sh`. **Engine: Claude Opus 4.7** (`claude-opus-4-7`,
override with `ANTHROPIC_MODEL`).

## Tested
Backend + data flow verified end-to-end: page serves, a run streams all 11 stages in order with
reject→revise loops, the Validator runs real `config_lint` (FAIL→PASS), the citation-guard
verifies/*blocks* citations, and both proof tests pass. Browser visual rendering should be confirmed on
first open (not visually QA'd in the build env).
