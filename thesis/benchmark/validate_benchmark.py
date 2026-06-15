#!/usr/bin/env python3
"""Validate all benchmark question files for format consistency and completeness.

Checks:
  1. All files parse as valid JSON.
  2. Every question has required keys: id, category, question, provenance.
  3. Question IDs are unique across all files and sequential (q-001 .. q-NNN).
  4. Categories are non-empty strings.
  5. Oracle-linked questions (linked_fault) have expected_commands + ground_truth.
  6. Provenance source is non-empty.
  7. Total question count matches expectation.

Run: python thesis/benchmark/validate_benchmark.py
"""
import json
import os
import sys

_BM_DIR = os.path.dirname(os.path.abspath(__file__))
_REQUIRED = {"id", "category", "question", "provenance"}
_ORACLE_REQUIRED = {"expected_commands", "ground_truth"}

fails = 0


def fail(msg: str) -> None:
    global fails
    print(f"  FAIL  {msg}")
    fails += 1


def ok(msg: str) -> None:
    print(f"  PASS  {msg}")


def check(cond: bool, msg: str, detail: str = "") -> None:
    if cond:
        ok(msg)
    else:
        fail(msg + (f": {detail}" if detail else ""))


def main() -> int:
    print("=== Benchmark validation ===")

    # Load all files
    all_questions = []
    files_loaded = []
    for fname in sorted(os.listdir(_BM_DIR)):
        if not (fname.endswith(".json") and fname.startswith("q")):
            continue
        path = os.path.join(_BM_DIR, fname)
        try:
            with open(path, encoding="utf-8") as fh:
                qs = json.load(fh)
            if not isinstance(qs, list):
                fail(f"{fname}: top-level is not a list")
                continue
            all_questions.extend(qs)
            files_loaded.append(fname)
        except json.JSONDecodeError as e:
            fail(f"{fname}: JSON parse error: {e}")

    ok(f"loaded {len(files_loaded)} files: {', '.join(files_loaded)}")
    print(f"  total questions: {len(all_questions)}")

    # Unique IDs
    ids = [q.get("id", "") for q in all_questions]
    dup = [i for i in ids if ids.count(i) > 1]
    check(len(dup) == 0, "no duplicate question IDs", f"duplicates: {list(set(dup))[:5]}")

    # Required keys
    missing_keys = []
    for q in all_questions:
        missing = _REQUIRED - set(q.keys())
        if missing:
            missing_keys.append((q.get("id", "?"), missing))
    check(len(missing_keys) == 0, "all questions have required keys", str(missing_keys[:3]))

    # Category non-empty
    no_cat = [q.get("id") for q in all_questions if not q.get("category", "").strip()]
    check(len(no_cat) == 0, "all questions have non-empty category", str(no_cat[:5]))

    # Question text non-empty
    no_q = [q.get("id") for q in all_questions if not q.get("question", "").strip()]
    check(len(no_q) == 0, "all questions have non-empty question text", str(no_q[:5]))

    # Provenance source
    no_prov = [q.get("id") for q in all_questions
               if not (isinstance(q.get("provenance"), dict) and q["provenance"].get("source"))]
    check(len(no_prov) == 0, "all questions have provenance.source", str(no_prov[:5]))

    # Oracle-linked questions (linked_fault or fault_id — both conventions present in the corpus)
    oracle_qs = [q for q in all_questions if q.get("linked_fault") or q.get("fault_id")]
    ok(f"{len(oracle_qs)} oracle-linked questions")
    oracle_missing = []
    for q in oracle_qs:
        has_gt = "ground_truth" in q
        # expected_commands can live at top level (newer style) or inside ground_truth (older style)
        has_cmds = "expected_commands" in q or bool((q.get("ground_truth") or {}).get("commands"))
        if not has_gt:
            oracle_missing.append((q.get("id"), "missing ground_truth"))
        elif not has_cmds:
            oracle_missing.append((q.get("id"), "missing commands"))
    check(len(oracle_missing) == 0, "oracle-linked questions have commands + ground_truth",
          str(oracle_missing[:3]))

    # ID sequential check
    numbered = []
    for qid in ids:
        if qid.startswith("q-"):
            try:
                numbered.append(int(qid[2:]))
            except ValueError:
                pass
    if numbered:
        numbered.sort()
        gaps = [numbered[i] for i in range(1, len(numbered))
                if numbered[i] != numbered[i-1] + 1]
        check(len(gaps) == 0, "question IDs are sequential (no gaps)", f"gaps before: {gaps[:5]}")
        check(numbered[0] == 1, f"IDs start at q-001 (found q-{numbered[0]:03d})")

    # Category distribution
    cats: dict = {}
    for q in all_questions:
        c = q.get("category", "?")
        cats[c] = cats.get(c, 0) + 1
    thin = {c: n for c, n in cats.items() if n < 2}
    check(len(thin) == 0, f"all categories have >=2 questions (thin: {thin})")

    # Count
    n = len(all_questions)
    check(n >= 300, f"benchmark has >=300 questions ({n} found)")
    ok(f"{n} questions across {len(cats)} categories")

    print()
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
