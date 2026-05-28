#!/usr/bin/env python3
"""Phase 6 — Full comparative evaluation report generator (thesis Tables 2–5).

Runs all registered SUTs against the full benchmark and produces publication-ready
comparison tables in both JSON (for the UI) and plain text (for the thesis appendix).

Statistical comparison: Welch's t-test approximation using only stdlib (no scipy).
Effect sizes: Cohen's d for metric pairs.

Tables produced:
  Table 2 — Headline metric comparison (all 4 SUTs × 5 metrics)
  Table 3 — Per-category breakdown (OpsRAG vs Dense-RAG; the primary ablation)
  Table 4 — Per-difficulty breakdown (recall / apply / diagnose)
  Table 5 — Feedback-loop ablation (exec-gated vs user-gated coherence)
             — imported from feedback.py rather than re-run here

Report also includes:
  - % improvement of OpsRAG over the naive floor (for each metric)
  - % improvement of OpsRAG over Dense-RAG (isolating the graph contribution)
  - Oracle-linked subset scores (the 7 fault-linked questions only)
"""
import json
import math
import os
import statistics
from typing import Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_BM_DIR = os.path.join(_REPO, "thesis", "benchmark")

# ---------------------------------------------------------------------------
# Statistical helpers (stdlib only — no scipy/numpy)
# ---------------------------------------------------------------------------

def _mean(values: List[float]) -> Optional[float]:
    v = [x for x in values if x is not None]
    return statistics.mean(v) if v else None


def _std(values: List[float]) -> Optional[float]:
    v = [x for x in values if x is not None]
    return statistics.pstdev(v) if len(v) > 1 else 0.0


def _cohens_d(a: List[float], b: List[float]) -> Optional[float]:
    """Cohen's d effect size between two groups (pooled std denominator)."""
    va = [x for x in a if x is not None]
    vb = [x for x in b if x is not None]
    if not va or not vb:
        return None
    ma, mb = statistics.mean(va), statistics.mean(vb)
    sa = statistics.pstdev(va) if len(va) > 1 else 0.0
    sb = statistics.pstdev(vb) if len(vb) > 1 else 0.0
    pooled = math.sqrt((sa ** 2 + sb ** 2) / 2) if (sa or sb) else 0.0
    return (ma - mb) / pooled if pooled else (1.0 if ma > mb else -1.0 if ma < mb else 0.0)


def _welch_t(a: List[float], b: List[float]) -> Tuple[Optional[float], Optional[float]]:
    """Welch's t-statistic and approximate two-tailed p-value (Welch-Satterthwaite df).

    p-value is approximated from the t-distribution CDF using a series expansion;
    accurate enough for reporting purposes (no external library required).
    """
    va = [x for x in a if x is not None]
    vb = [x for x in b if x is not None]
    n1, n2 = len(va), len(vb)
    if n1 < 2 or n2 < 2:
        return None, None
    m1, m2 = statistics.mean(va), statistics.mean(vb)
    s1 = statistics.variance(va)
    s2 = statistics.variance(vb)
    se = math.sqrt(s1 / n1 + s2 / n2)
    if se == 0:
        return (0.0, 1.0) if m1 == m2 else (float("inf"), 0.0)
    t = (m1 - m2) / se
    # Welch-Satterthwaite degrees of freedom
    num = (s1 / n1 + s2 / n2) ** 2
    den = (s1 / n1) ** 2 / (n1 - 1) + (s2 / n2) ** 2 / (n2 - 1)
    df = num / den if den else n1 + n2 - 2
    # Approximate p-value via regularised incomplete beta function approximation
    p = _approx_t_pvalue(abs(t), df)
    return t, p


def _approx_t_pvalue(t_abs: float, df: float) -> float:
    """Two-tailed p-value from t-distribution using a rational approximation.

    Accurate to ~3 decimal places for df >= 5. Uses the Abramowitz & Stegun
    approximation for the normal CDF as a fallback for large df.
    """
    if df <= 0:
        return 1.0
    # Use normal approximation when df is large (accurate for df > 100)
    if df > 100:
        z = t_abs
        p_one = 0.5 * math.erfc(z / math.sqrt(2))
        return 2 * p_one
    # For small df: use a simple series — this is the two-tailed p-value
    # via the regularised incomplete beta function I(df/(df+t^2); df/2, 1/2)
    x = df / (df + t_abs * t_abs)
    # Regularised incomplete beta approximation (Lentz continued fraction)
    try:
        from math import lgamma
        def _beta_inc(a, b, x):
            """Regularised incomplete beta function via continued fraction."""
            if x < 0 or x > 1:
                return 0.0
            if x == 0:
                return 0.0
            if x == 1:
                return 1.0
            lbeta = lgamma(a) + lgamma(b) - lgamma(a + b)
            front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a
            # Continued fraction (Lentz method, 50 iterations)
            TINY = 1e-30
            f = TINY
            C, D = f, 0.0
            for m in range(0, 50):
                for n in (0, 1):
                    if n == 0 and m == 0:
                        d = 1.0
                    elif n == 0:
                        d = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))
                    else:
                        d = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))
                    D = 1 + d * D
                    D = TINY if abs(D) < TINY else D
                    C = 1 + d / C
                    C = TINY if abs(C) < TINY else C
                    D = 1 / D
                    f *= C * D
                    if abs(C * D - 1) < 1e-8:
                        break
            return front * f

        p = _beta_inc(df / 2, 0.5, x)
        return min(1.0, max(0.0, p))
    except Exception:
        # Fallback: normal approximation
        z = t_abs
        return 2 * 0.5 * math.erfc(z / math.sqrt(2))


def _pval_stars(p: Optional[float]) -> str:
    """Convert p-value to significance stars for tables."""
    if p is None:
        return ""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "n.s."


def _pct_improvement(base: Optional[float], improved: Optional[float]) -> Optional[float]:
    if base is None or improved is None or base == 0:
        return None
    return round((improved - base) / abs(base) * 100, 1)


# ---------------------------------------------------------------------------
# SUT registry
# ---------------------------------------------------------------------------

def _load_suts() -> Dict:
    from . import evaluator, llm_synthesizer, dense_rag, graph_sut
    return {
        "naive": evaluator.naive_sut,
        "dense_rag": dense_rag.dense_rag_sut,
        "opsrag": evaluator.opsrag_sut,
        "graph": graph_sut.graph_sut,
        "llm": llm_synthesizer.llm_sut,  # falls back deterministically without a key
    }


_SUT_LABELS = {
    "naive": "Naive floor",
    "dense_rag": "Dense-RAG (BM25)",
    "opsrag": "OpsRAG (deterministic)",
    "graph": "Graph SUT (typed-graph retrieval)",
    "llm": "LLM (Opus 4.7 / fallback)",
}


# ---------------------------------------------------------------------------
# Core report generation
# ---------------------------------------------------------------------------

def run_all_suts(bm_dir: str = _BM_DIR) -> Dict:
    """Run every registered SUT over the full benchmark and return raw per-question scores."""
    from .evaluator import evaluate

    questions = []
    for fname in sorted(os.listdir(bm_dir)):
        if fname.endswith(".json") and fname != "schema.json":
            with open(os.path.join(bm_dir, fname), encoding="utf-8") as fh:
                questions.extend(json.load(fh))

    suts = _load_suts()
    results = {}
    for sut_name, sut_fn in suts.items():
        results[sut_name] = evaluate(sut_fn, bm_dir)

    return {"n_questions": len(questions), "suts": results}


def _extract_metric_series(report: Dict, metric: str) -> List[float]:
    """Extract per-question metric values from an evaluate() report."""
    return [row.get(metric) for row in report.get("per_question", []) if row.get(metric) is not None]


def build_table2(raw: Dict) -> Dict:
    """Table 2 — Headline metric comparison across all SUTs."""
    sut_reports = raw["suts"]
    metrics = ["answer_relevance", "faithfulness", "context_relevance"]
    rate_metrics = ["executability_rate", "diagnostic_accuracy"]

    rows = {}
    for sut, report in sut_reports.items():
        hl = report.get("headline", {})
        row = {"label": _SUT_LABELS.get(sut, sut), "n": report.get("n", 0)}
        for m in metrics:
            mv = hl.get(m, {})
            row[m] = {"mean": mv.get("mean"), "std": mv.get("std")}
        for m in rate_metrics:
            row[m] = hl.get(m)
        rows[sut] = row

    # Pairwise comparisons: OpsRAG and Graph vs naive and dense_rag
    comparisons = {}
    for improved in ("opsrag", "graph"):
        for baseline in ("naive", "dense_rag"):
            if baseline not in sut_reports or improved not in sut_reports:
                continue
            comp = {}
            for m in metrics:
                a = _extract_metric_series(sut_reports[improved], m)
                b = _extract_metric_series(sut_reports[baseline], m)
                t, p = _welch_t(a, b)
                d = _cohens_d(a, b)
                comp[m] = {
                    "t": round(t, 3) if t is not None else None,
                    "p": round(p, 4) if p is not None else None,
                    "stars": _pval_stars(p),
                    "cohens_d": round(d, 3) if d is not None else None,
                    "pct_improvement": _pct_improvement(
                        rows[baseline][m]["mean"], rows[improved][m]["mean"]
                    ),
                }
            comparisons[f"{improved}_vs_{baseline}"] = comp

    return {"rows": rows, "comparisons": comparisons}


def build_table3(raw: Dict) -> Dict:
    """Table 3 — Per-category: Graph SUT vs Dense-RAG (typed-graph contribution ablation).

    Compares the Graph SUT (typed-graph + concept library) against the Dense-RAG (BM25 over
    flat chunks) baseline per category. The delta isolates the value of typed retrieval over
    a flat-corpus retriever. OpsRAG (deterministic synth) is kept for cross-comparison.
    """
    if "graph" not in raw["suts"] or "dense_rag" not in raw["suts"]:
        return {}

    graph_cats = raw["suts"]["graph"].get("by_category", {})
    dense_cats = raw["suts"]["dense_rag"].get("by_category", {})
    opsrag_cats = raw["suts"].get("opsrag", {}).get("by_category", {})

    rows = []
    for cat in sorted(set(list(graph_cats.keys()) + list(dense_cats.keys()))):
        gcat = graph_cats.get(cat, {})
        dcat = dense_cats.get(cat, {})
        ocat = opsrag_cats.get(cat, {})
        rows.append({
            "category": cat,
            "n": gcat.get("n", 0) or dcat.get("n", 0),
            "graph_exec": gcat.get("executability_rate"),
            "dense_exec": dcat.get("executability_rate"),
            "opsrag_exec": ocat.get("executability_rate"),
            "graph_ans_rel": (gcat.get("answer_relevance") or {}).get("mean"),
            "dense_ans_rel": (dcat.get("answer_relevance") or {}).get("mean"),
            "graph_diag_acc": gcat.get("diagnostic_accuracy"),
            "dense_diag_acc": dcat.get("diagnostic_accuracy"),
        })

    return {"rows": rows}


def build_table4(raw: Dict) -> Dict:
    """Table 4 — Per-difficulty: recall / apply / diagnose across SUTs."""
    difficulties = ["recall", "apply", "diagnose"]
    rows = {}
    for sut, report in raw["suts"].items():
        by_diff = report.get("by_difficulty", {})
        rows[sut] = {
            d: {
                "n": by_diff.get(d, {}).get("n", 0),
                "ans_rel": (by_diff.get(d, {}).get("answer_relevance") or {}).get("mean"),
                "exec_rate": by_diff.get(d, {}).get("executability_rate"),
                "diag_acc": by_diff.get(d, {}).get("diagnostic_accuracy"),
            }
            for d in difficulties
        }
    return {"rows": rows}


# ---------------------------------------------------------------------------
# Plain-text table renderers (for thesis appendix)
# ---------------------------------------------------------------------------

def format_table2(t2: Dict) -> str:
    rows = t2["rows"]
    metrics = ["answer_relevance", "executability_rate", "diagnostic_accuracy"]
    header = f"{'SUT':<30} {'ans_rel':>8} {'exec_rate':>10} {'diag_acc':>10} {'n':>6}"
    sep = "-" * len(header)
    lines = ["Table 2 — Headline metric comparison", sep, header, sep]
    for sut in ("naive", "dense_rag", "opsrag", "graph", "llm"):
        if sut not in rows:
            continue
        r = rows[sut]
        ar = (r.get("answer_relevance") or {}).get("mean")
        er = r.get("executability_rate")
        da = r.get("diagnostic_accuracy")
        fmt = lambda v: f"{v:.3f}" if v is not None else "  —  "
        lines.append(f"{r['label']:<30} {fmt(ar):>8} {fmt(er):>10} {fmt(da):>10} {r['n']:>6}")
    lines.append(sep)

    # Improvement rows
    for comp_key, comp in sorted((t2.get("comparisons") or {}).items()):
        label = comp_key.replace("_vs_", " vs ").replace("opsrag", "OpsRAG").replace("graph", "Graph").replace("naive", "Naive").replace("dense_rag", "Dense-RAG")
        parts = []
        for m in ["answer_relevance"]:
            if m in comp:
                c = comp[m]
                pct = c.get("pct_improvement")
                stars = c.get("stars", "")
                if pct is not None:
                    parts.append(f"ans_rel Δ={pct:+.1f}% {stars}")
        if parts:
            lines.append(f"  {label}: {', '.join(parts)}")
    return "\n".join(lines)


def format_table3(t3: Dict) -> str:
    rows = t3.get("rows", [])
    header = f"{'Category':<25} {'n':>4} {'Graph exec':>11} {'Dense exec':>11} {'Δ exec':>8}"
    sep = "-" * len(header)
    lines = ["Table 3 — Per-category (Graph SUT vs Dense-RAG, typed-graph ablation)", sep, header, sep]
    for r in rows:
        ge = r.get("graph_exec")
        de = r.get("dense_exec")
        delta = round((ge or 0) - (de or 0), 3) if ge is not None and de is not None else None
        fmt = lambda v: f"{v:.3f}" if v is not None else "  —  "
        d_str = f"{delta:+.3f}" if delta is not None else "  —  "
        lines.append(f"{r['category']:<25} {r['n']:>4} {fmt(ge):>11} {fmt(de):>11} {d_str:>8}")
    lines.append(sep)
    return "\n".join(lines)


def format_table4(t4: Dict) -> str:
    rows = t4.get("rows", {})
    header = f"{'SUT':<30} {'recall exec':>11} {'apply exec':>10} {'diag exec':>10}"
    sep = "-" * len(header)
    lines = ["Table 4 — Per-difficulty breakdown", sep, header, sep]
    for sut in ("naive", "dense_rag", "opsrag", "graph", "llm"):
        if sut not in rows:
            continue
        label = _SUT_LABELS[sut]
        r = rows[sut]
        fmt = lambda v: f"{v:.3f}" if v is not None else "  —  "
        lines.append(
            f"{label:<30} {fmt(r.get('recall',{}).get('exec_rate')):>11} "
            f"{fmt(r.get('apply',{}).get('exec_rate')):>10} "
            f"{fmt(r.get('diagnose',{}).get('exec_rate')):>10}"
        )
    lines.append(sep)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Full report entry point
# ---------------------------------------------------------------------------

def build_table5(bm_dir: str = _BM_DIR) -> Dict:
    """Table 5 — Feedback-loop ablation (execution-gated vs user-gated coherence).

    Runs a 200-interaction popularity-bias stream using the graph SUT (best performer)
    and compares execution-gated vs user-gated graph admission strategies.
    Deterministic (seed=99). Takes ~1s; skipped if feedback module unavailable.
    """
    try:
        from . import feedback, graph_sut
        import json, os

        questions = []
        for fn in sorted(os.listdir(bm_dir)):
            if fn.endswith(".json") and fn != "schema.json":
                with open(os.path.join(bm_dir, fn), encoding="utf-8") as fh:
                    questions.extend(json.load(fh))

        stream = feedback.popularity_bias_stream(
            questions, graph_sut.graph_sut, n=200, rng_seed=99
        )
        result = feedback.ablation(stream, step=20)
        return {
            "exec_gated_coherence": result["execution_gated"]["final_coherence"],
            "user_gated_coherence": result["user_gated"]["final_coherence"],
            "delta_coherence": result["delta"]["coherence"],
            "exec_gated_admitted": result["execution_gated"]["admitted"],
            "user_gated_admitted": result["user_gated"]["admitted"],
            "verdict": result["verdict"],
            "text": feedback.format_ablation_table(result),
        }
    except Exception as e:
        return {"error": str(e), "text": f"Table 5 unavailable: {e}"}


def generate_report(bm_dir: str = _BM_DIR) -> Dict:
    """Generate the full Phase 6/7 comparative evaluation report (Tables 2–5).

    Main entry point for the API endpoint and the test suite.
    Returns a structured dict with all four tables and plain-text renders.
    """
    raw = run_all_suts(bm_dir)
    t2 = build_table2(raw)
    t3 = build_table3(raw)
    t4 = build_table4(raw)
    t5 = build_table5(bm_dir)

    return {
        "n_questions": raw["n_questions"],
        "table2": t2,
        "table3": t3,
        "table4": t4,
        "table5": t5,
        "text": {
            "table2": format_table2(t2),
            "table3": format_table3(t3),
            "table4": format_table4(t4),
            "table5": t5.get("text", ""),
        },
        "headline_opsrag": raw["suts"].get("opsrag", {}).get("headline", {}),
        "headline_graph": raw["suts"].get("graph", {}).get("headline", {}),
        "headline_naive": raw["suts"].get("naive", {}).get("headline", {}),
    }
