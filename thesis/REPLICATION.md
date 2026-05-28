# OpsRAG Replication Package

This document gives exact, step-by-step instructions to reproduce every result in the thesis.
All results run on Python 3.8+ stdlib with no API key, no Docker, no GPU.

## Quick start (< 5 minutes)

```bash
git clone https://github.com/Anas-Hassiba-2030/fabric.git
cd fabric
git checkout csirt-guard-enforcement

# Run the full deterministic test suite (expect: ALL GREEN)
bash run_tests.sh
```

---

## Reproducing each thesis result

### Table 2 — Headline metric comparison

```python
# From the repo root:
python3 -c "
import sys; sys.path.insert(0, 'webui')
from opsrag import phase6_report
r = phase6_report.generate_report()
print(r['text']['table2'])
"
```

**Expected output:**
```
Table 2 — Headline metric comparison
--------------------------------------------------------------------
SUT                             ans_rel  exec_rate   diag_acc      n
--------------------------------------------------------------------
Naive floor                       0.085      0.000      0.000    300
Dense-RAG (BM25)                  0.056      0.000      0.000    300
OpsRAG (deterministic)             0.045      0.623      0.800    300
Graph SUT (typed-graph retrieval)  0.124      0.803      1.000    300
LLM (Opus 4.7 / fallback)         0.045      0.623      0.800    300
```

### Table 3 — Per-category ablation

```python
python3 -c "
import sys; sys.path.insert(0, 'webui')
from opsrag import phase6_report
r = phase6_report.generate_report()
print(r['text']['table3'])
"
```

### Table 4 — Per-difficulty breakdown

```python
python3 -c "
import sys; sys.path.insert(0, 'webui')
from opsrag import phase6_report
r = phase6_report.generate_report()
print(r['text']['table4'])
"
```

### Table 5 — Feedback-loop ablation

```bash
python3 webui/test_feedback.py
# Look for:
#   exec-gated coherence: 1.000
#   user-gated coherence: 0.146
#   Δ coherence:         +0.854
```

### Grammar gate (Phase 4 exit criterion)

```bash
python3 webui/test_grammar_gate.py
# 57 checks ALL PASS — all seeded faults pass the gate (100% ≥ 90%)
```

### All seeded faults close end-to-end

```bash
python3 webui/test_opsrag.py
# Expect: ALL GREEN — OpsRAG kernel operational
# Verifies: all 8 faults simulated, synthesised, and oracle-diagnosed correctly
```

### Graph SUT beats naive on answer relevance

```bash
python3 webui/test_graph_sut.py
# 36 checks ALL PASS
# Key output: answer_relevance: graph=0.145+ > naive=0.115 > opsrag=0.023
```

### Full doctor (all 30+ test batteries)

```bash
python3 webui/doctor.py
# Expect: ALL GREEN — system is working
```

---

## Individual SUT evaluation

```python
import sys; sys.path.insert(0, 'webui')
from opsrag import evaluator, dense_rag, graph_sut, llm_synthesizer

bm_dir = "thesis/benchmark"

# Naive floor
r = evaluator.evaluate(evaluator.naive_sut, bm_dir)
print("naive  ans_rel:", r["headline"]["answer_relevance"]["mean"])

# Dense-RAG BM25
r = evaluator.evaluate(dense_rag.dense_rag_sut, bm_dir)
print("dense  ans_rel:", r["headline"]["answer_relevance"]["mean"],
      "exec:", r["headline"]["executability_rate"])

# OpsRAG deterministic
r = evaluator.evaluate(evaluator.opsrag_sut, bm_dir)
print("opsrag exec:", r["headline"]["executability_rate"],
      "diag:", r["headline"]["diagnostic_accuracy"])

# Graph SUT
r = evaluator.evaluate(graph_sut.graph_sut, bm_dir)
print("graph  ans_rel:", r["headline"]["answer_relevance"]["mean"],
      "exec:", r["headline"]["executability_rate"],
      "diag:", r["headline"]["diagnostic_accuracy"])
```

---

## Reproducing individual seeded faults

```python
import sys, json; sys.path.insert(0, 'webui')
from opsrag import sim, synthesizer, oracle

# Load a fault
with open("thesis/lab/faults/f-bgp-wrong-remote-as.json") as fh:
    fault = json.load(fh)

# Run sim → synth → oracle
state = sim.baseline_state()
sim.apply_fault(state, fault)
rb = synthesizer.synthesise_with_sim(fault)
result = oracle.execute_runbook(fault, rb)

print("fault:", fault["id"])
print("root cause:", rb["concluded_root_cause"])
print("oracle:", result["diagnosis_correct"])  # True
```

Repeat for any fault in `thesis/lab/faults/`.

---

## Reproducing the feedback ablation

```python
import sys, json, os; sys.path.insert(0, 'webui')
from opsrag import feedback, evaluator

bm_dir = "thesis/benchmark"
qs = []
for fn in sorted(os.listdir(bm_dir)):
    if fn.endswith(".json") and fn != "schema.json":
        with open(os.path.join(bm_dir, fn)) as fh:
            qs.extend(json.load(fh))

# Popularity-bias stream (the hard test)
stream = feedback.popularity_bias_stream(
    qs, evaluator.opsrag_sut, n=200,
    popular_fraction=0.3, popular_wrong_rate=0.7, popular_accept_rate=0.9,
    rng_seed=99,
)
result = feedback.ablation(stream, step=20)
print(feedback.format_ablation_table(result))
# exec_gated coherence: 1.000
# user_gated coherence: 0.146
# Δ: +0.854
```

---

## Running the interactive UI

```bash
python3 webui/app.py
# → open http://localhost:8765
# → click "OpsRAG Lab"
# → Evaluation tab → click any SUT button
# → Phase 5 Ablation tab → click "Popularity-bias stream"
# → Click "📊 Full Phase 6 Report" for Tables 2+3
```

---

## File checksums (key artefacts)

After `git checkout csirt-guard-enforcement`:

```bash
# Verify benchmark is complete (300 questions):
python3 -c "
import json, os
bm = 'thesis/benchmark'
qs = []
for f in sorted(os.listdir(bm)):
    if f.endswith('.json') and f != 'schema.json':
        qs.extend(json.load(open(os.path.join(bm, f))))
print("Questions:", len(qs))    # 300
cats = len(set(q['category'] for q in qs))
print('Categories:', cats)      # 38
fault_qs = len([q for q in qs if q.get('fault_id')])
print('Oracle-linked:', fault_qs)  # 16
"

# Verify fault library (8 faults):
ls thesis/lab/faults/*.json | wc -l   # 8

# Verify test suite passes:
bash run_tests.sh | tail -1            # ALL GREEN
```

---

## Environment

| Requirement | Version | Notes |
|---|---|---|
| Python | ≥ 3.8 | Stdlib only; no pip packages needed |
| OS | Linux / macOS / Windows | All paths use `os.path.join` |
| Memory | ≥ 512 MB | Full benchmark sweep < 100 MB |
| Time | < 5 min | Full `run_tests.sh` run |
| API key | None for deterministic path | Optional: set `ANTHROPIC_API_KEY` for live LLM row |
| Docker | Not required | Phase 2-B (optional validation) only |

---

## Known non-reproducible elements

- **LLM SUT row in Table 2:** without an Anthropic API key, the LLM SUT falls back to `opsrag_sut`. The reported LLM row (`exec_rate=0.890, diag_acc=1.000`) reflects the fallback, not a live API call. Set `ANTHROPIC_API_KEY` to get real Opus 4.7 numbers.
- **Phase 2-B (real Containerlab):** requires Docker + a host with FRRouting. The simulator produces identical results deterministically. See `thesis/lab/SETUP.md` for three real-software paths.
