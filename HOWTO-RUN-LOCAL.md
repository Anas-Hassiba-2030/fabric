# Running WRATH + OpsRAG Lab on your Windows PC

> **Why localhost:8765 was empty:** Claude Code on the web runs in an ephemeral Linux cloud
> container, not on your PC. When I start `python webui/app.py` in the container, it binds to
> the container's localhost — your browser's `localhost` is your own machine, where nothing is
> listening. You need to run the server on your Windows PC to see the UI.

---

## Option A — Git Bash (recommended, fastest)

Git Bash ships with Git for Windows and gives you a real bash shell. If you installed Git, you
already have it.

### 1. Clone / pull the repo

Open **Git Bash**:

```bash
cd /c/Users/YourName/Projects          # adjust to where you keep code
git clone https://github.com/Anas-Hassiba-2030/fabric.git
cd fabric
git checkout csirt-guard-enforcement
git pull
```

### 2. Run the deterministic proofs

```bash
bash run_tests.sh
```

Expected last line: `ALL GREEN`. This proves the entire system (40+ checks) including the OpsRAG
loop. No Docker, no Anthropic key, no extra installs.

### 3. Start the console

```bash
python webui/app.py
```

Leave this terminal open — you'll see:

```
WRATH Console on http://localhost:8765
```

### 4. Open in Chrome / Edge

Navigate to `http://localhost:8765`.

Click **🧪 OpsRAG Lab** in the toolbar → pick any fault → click **▶ Run Loop** → see the
FRR-like terminal output + `✓ executable  ✓ evidence hit  ✓ diagnosis correct` oracle verdict.

---

## Option B — PowerShell or Command Prompt

If you prefer PowerShell / `cmd`:

```powershell
cd C:\Users\YourName\Projects\fabric
git checkout csirt-guard-enforcement
git pull
python webui\app.py
```

`run_tests.sh` needs Git Bash for the `bash` command. To run individual Python tests in
PowerShell:

```powershell
python webui\test_opsrag.py    # OpsRAG kernel (32 checks)
python webui\test_ingest.py    # Phase 3 ingestion (16 checks)
python webui\doctor.py         # full doctor check
```

To set environment variables in PowerShell:

```powershell
$env:ANTHROPIC_API_KEY = "sk-..."
$env:WRATH_UI_PORT = "9000"       # if 8765 is taken
python webui\app.py
```

---

## Option C — WSL 2 (best for Phase 2-B Containerlab later)

If you have WSL 2 installed, run everything inside it — Linux commands work exactly as in the
cloud container, and Containerlab + Docker Desktop also work under WSL 2 when Phase 2-B starts.

```bash
# inside WSL2 Ubuntu terminal:
cd ~/projects/fabric
git pull origin csirt-guard-enforcement
bash run_tests.sh
python3 webui/app.py
```

Then open `http://localhost:8765` in your Windows browser — WSL 2 ports are forwarded to Windows
automatically.

---

## Requirements (all options)

| Requirement | Where to get it | Check |
|---|---|---|
| Python 3.8+ | python.org → Windows installer (check "Add to PATH") | `python --version` |
| Git | git-scm.com | `git --version` |
| No `pip install` needed | stdlib only | — |
| No Docker needed | for OpsRAG Lab demo | — |
| No Anthropic key needed | for OpsRAG Lab demo | — |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `localhost refused to connect` | The server isn't running. Run `python webui\app.py` in a terminal and leave it open. |
| `python: command not found` | Python not on PATH — re-run installer, check "Add to PATH". Or use `py webui\app.py`. |
| Port 8765 in use | `set WRATH_UI_PORT=9000 && python webui\app.py` (cmd) or `$env:WRATH_UI_PORT=9000; python webui\app.py` (PS). |
| Windows Defender firewall pop-up | Allow access — the server only listens on localhost, not the network. |
| `bash: command not found` in cmd | Use Git Bash or install it via git-scm.com. `run_tests.sh` requires bash. |
| `ModuleNotFoundError` | Make sure you're in the `fabric` directory before running; the imports use relative paths. |
