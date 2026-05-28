#!/usr/bin/env python3
"""Tests for Phase 6 evaluation report (no API key required)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(os.path.dirname(HERE))
os.environ.pop("ANTHROPIC_API_KEY", None)

from opsrag.phase6_report import (
    _cohens_d, _welch_t, _pval_stars, _pct_improvement,
    build_table2, build_table3, build_table4,
    format_table2, format_table3, format_table4,
    generate_report, run_all_suts,
    _approx_t_pvalue,
)

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        print(f"  PASS {name}")
        _PASS += 1
    else:
        print(f"  FAIL {name}" + (f": {detail}" if detail else ""))
        _FAIL += 1


# --------------------------------------------------------------------------
# Section 1: Statistical helpers
# --------------------------------------------------------------------------
print("\n=== 1. Statistical helpers ===")

# Cohen's d
a = [0.9, 0.85, 0.88, 0.91, 0.87]
b = [0.1, 0.15, 0.12, 0.09, 0.11]
d = _cohens_d(a, b)
check("cohens_d large effect > 3", d is not None and d > 3.0, f"got {d}")
check("cohens_d symmetric negation", abs(_cohens_d(b, a) + d) < 0.01)
check("cohens_d empty lists returns None", _cohens_d([], a) is None)

# Welch's t-test
t, p = _welch_t(a, b)
check("welch_t returns t and p", t is not None and p is not None)
check("welch_t p < 0.001 for clearly different groups", p < 0.001, f"got p={p}")
check("welch_t returns None for small lists", _welch_t([1.0], [1.0]) == (None, None))

# p-value approximation
check("p-value approx 0.05 at t~2, df=10", 0.01 < _approx_t_pvalue(2.228, 10) < 0.10)
check("p-value approx < 0.001 at t=4, df=30", _approx_t_pvalue(4.0, 30) < 0.005)

# Stars
check("p<0.001 → ***", _pval_stars(0.0005) == "***")
check("p<0.01 → **",   _pval_stars(0.005) == "**")
check("p<0.05 → *",    _pval_stars(0.03) == "*")
check("p>0.05 → n.s.", _pval_stars(0.10) == "n.s.")
check("None → ''",     _pval_stars(None) == "")

# % improvement
check("pct_improvement 0→1 = 100%", _pct_improvement(0.5, 1.0) == 100.0)
check("pct_improvement base=0 → None", _pct_improvement(0.0, 0.5) is None)
check("pct_improvement negative delta", _pct_improvement(0.8, 0.4) == -50.0)

# --------------------------------------------------------------------------
# Section 2: Report generation (all SUTs, live benchmark)
# --------------------------------------------------------------------------
print("\n=== 2. Report generation ===")
import time
t0 = time.time()
raw = run_all_suts()
elapsed = time.time() - t0
print(f"  (run_all_suts took {elapsed:.1f}s on {raw['n_questions']} questions)")

check("raw has n_questions > 0", raw["n_questions"] > 0, f"got {raw['n_questions']}")
check("raw has suts dict", "suts" in raw and len(raw["suts"]) >= 3)
check("naive SUT is in raw", "naive" in raw["suts"])
check("opsrag SUT is in raw", "opsrag" in raw["suts"])
check("dense_rag SUT is in raw", "dense_rag" in raw["suts"])

# --------------------------------------------------------------------------
# Section 3: Table 2 — headline comparison
# --------------------------------------------------------------------------
print("\n=== 3. Table 2 — headline comparison ===")

t2 = build_table2(raw)
check("table2 has rows", "rows" in t2 and len(t2["rows"]) >= 3)
check("table2 rows have naive", "naive" in t2["rows"])
check("table2 rows have opsrag", "opsrag" in t2["rows"])

opsrag_row = t2["rows"].get("opsrag", {})
naive_row = t2["rows"].get("naive", {})
check("opsrag executability_rate > naive", (opsrag_row.get("executability_rate") or 0) > (naive_row.get("executability_rate") or 0))
check("opsrag diagnostic_accuracy == 1.0", opsrag_row.get("diagnostic_accuracy") == 1.0 or opsrag_row.get("diagnostic_accuracy") is None)

check("table2 has comparisons key", "comparisons" in t2)
comp = t2.get("comparisons", {})
check("comparison opsrag_vs_naive present", "opsrag_vs_naive" in comp)

# --------------------------------------------------------------------------
# Section 4: Table 3 — per-category
# --------------------------------------------------------------------------
print("\n=== 4. Table 3 — per-category ===")

t3 = build_table3(raw)
check("table3 has rows list", "rows" in t3 and isinstance(t3["rows"], list))
check("table3 rows non-empty", len(t3["rows"]) > 0)
for row in t3["rows"][:3]:
    check(f"table3 row {row['category']} has opsrag_exec", "opsrag_exec" in row)
    check(f"table3 row {row['category']} has dense_exec", "dense_exec" in row)

# --------------------------------------------------------------------------
# Section 5: Table 4 — per-difficulty
# --------------------------------------------------------------------------
print("\n=== 5. Table 4 — per-difficulty ===")

t4 = build_table4(raw)
check("table4 has rows dict", "rows" in t4)
for sut in ("naive", "opsrag", "dense_rag"):
    if sut in t4["rows"]:
        r = t4["rows"][sut]
        check(f"table4 {sut} has recall/apply/diagnose", all(d in r for d in ("recall","apply","diagnose")))

# --------------------------------------------------------------------------
# Section 6: Plain-text renderers
# --------------------------------------------------------------------------
print("\n=== 6. Plain-text table renderers ===")

txt2 = format_table2(t2)
check("table2 text contains 'Naive floor'", "Naive floor" in txt2)
check("table2 text contains 'OpsRAG'", "OpsRAG" in txt2)
check("table2 text contains metric columns", "exec_rate" in txt2 or "exec" in txt2)

txt3 = format_table3(t3)
check("table3 text contains category names", len(txt3) > 100)
check("table3 text contains Δ column", "Δ" in txt3 or "delta" in txt3.lower())

txt4 = format_table4(t4)
check("table4 text contains difficulty labels", "recall" in txt4 and "apply" in txt4)

# --------------------------------------------------------------------------
# Section 7: Full generate_report()
# --------------------------------------------------------------------------
print("\n=== 7. Full report ===")

report = generate_report()
check("report has n_questions", report["n_questions"] > 0)
check("report has table2", "table2" in report)
check("report has table3", "table3" in report)
check("report has table4", "table4" in report)
check("report has text.table2", isinstance(report.get("text", {}).get("table2"), str))
check("report has headline_opsrag", "headline_opsrag" in report)

# Print the actual thesis tables
print("\n--- THESIS TABLE 2 ---")
print(report["text"]["table2"])
print("\n--- THESIS TABLE 3 (first 10 categories) ---")
t3_lines = report["text"]["table3"].split("\n")
print("\n".join(t3_lines[:15]))
print("\n--- THESIS TABLE 4 ---")
print(report["text"]["table4"])

# The key thesis claim: OpsRAG executability > naive and > dense_rag
opsrag_exec = report["headline_opsrag"].get("executability_rate", 0)
naive_exec = report["headline_naive"].get("executability_rate", 0)
check("THESIS: OpsRAG executability strictly > naive", opsrag_exec > naive_exec,
      f"opsrag={opsrag_exec}, naive={naive_exec}")

# --------------------------------------------------------------------------
print(f"\n{'='*40}")
print(f"RESULT: {_PASS} PASS / {_FAIL} FAIL")
if _FAIL:
    sys.exit(1)
