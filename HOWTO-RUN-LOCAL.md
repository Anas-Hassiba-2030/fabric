# Running WRATH + OpsRAG Lab on your Mac

> Honest framing: when Claude Code runs in the **web environment** (the one I use to push to GitHub),
> the server starts inside an ephemeral cloud container, not on your Mac. `localhost:8765` on your
> browser is *your laptop* — it has nothing running unless **you** start it. Here is exactly how.

## 1. One-time setup (≈30 seconds)

```bash
cd ~/where-you-keep-projects
git clone https://github.com/Anas-Hassiba-2030/fabric.git  # if not already cloned
cd fabric
git checkout csirt-guard-enforcement
git pull
```

Requirements: Python 3.8+ (every Mac since Big Sur has this). No `pip install`, no Docker, no
Anthropic key needed to demo OpsRAG.

## 2. Run the deterministic proofs first (≈8 seconds)

Before opening the browser, prove every check is green on your machine:

```bash
bash run_tests.sh
```

Expected ending: `ALL GREEN`. 40+ PASS lines including:
- `opsrag schema + bootstrap from memory + oracle loop`
- `ingest extractors (CLI + RFC -> typed nodes, idempotent merge)`

If anything fails, stop and tell me — the suite is the contract.

## 3. Start the console

```bash
python3 webui/app.py
# leave that terminal open; you'll see "WRATH Console on http://localhost:8765"
```

Then open `http://localhost:8765` in **the same Mac's** browser. (Not Chrome on a different machine,
not localhost in your remote SSH session — your laptop's own browser.)

## 4. Demo the OpsRAG Lab in 30 seconds

1. Click **🧪 OpsRAG Lab** in the toolbar (right-hand side, between 🔧 Troubleshoot and 📊 Analytics).
2. Modal opens with: typed knowledge-graph stats + three seeded BGP faults.
3. On any fault card, click **▶ Run Loop**.
4. The card expands to show:
   - the discovery commands the synthesiser picked (e.g. `R2: show bgp summary`),
   - the FRR-like terminal output per command,
   - **three verdict badges**: `✓ executable`, `✓ evidence hit`, `✓ diagnosis correct`,
   - synthesised root cause vs ground truth side-by-side + the fix command.

That is the **action-grounded retrieval loop**. No Docker, no API key.

## 5. (Optional) Live-mode demo

Set an Anthropic key first:

```bash
export ANTHROPIC_API_KEY=sk-...
python3 webui/app.py
```

In the console, flip the **Demo / Live** toggle to Live. Type a problem (or click ⊞ Blueprints).
The pipeline now calls real Claude Opus/Sonnet/Haiku per agent tier. The OpsRAG Lab still works
without a key — it is the deterministic side of the system.

## 6. (Optional) Run the doctor

```bash
python3 webui/doctor.py
# with a key, this also makes ONE real call to Opus 4.7 to prove the live engine works.
ANTHROPIC_API_KEY=sk-... python3 webui/doctor.py
```

## Troubleshooting

- **"localhost refused to connect"** — the server isn't running on your Mac. Run step 3 again
  in a terminal on your laptop. Closing the terminal stops the server.
- **Port 8765 in use** — change it: `WRATH_UI_PORT=9000 python3 webui/app.py`.
- **macOS firewall popup** — allow it; the server only binds locally.
- **No `python3`** — `xcode-select --install` then re-try (ships Python 3 by default since macOS 10.15).
