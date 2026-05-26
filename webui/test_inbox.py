#!/usr/bin/env python3
"""Proof that the WRATH inbox saves/edits/removes bookmarked runs and persists — no API key.

Run:  python webui/test_inbox.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inbox  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


d = tempfile.mkdtemp()
path = os.path.join(d, "inbox.json")

print("=== 1. Empty inbox loads as [] ===")
check("missing file -> []", inbox.load(path) == [])

print("=== 2. Add bookmarks; newest first; meta carried ===")
inbox.add(path, "run-a", "first design", {"problem": "SR-MPLS core", "confidence": "Medium"}, ts="2026-01-01T00:00:00Z")
inbox.add(path, "run-b", "the SRv6 variant", {"problem": "SRv6 core", "confidence": "High"}, ts="2026-01-02T00:00:00Z")
items = inbox.load(path)
check("2 items saved", len(items) == 2)
check("newest (run-b) first", items[0]["run_id"] == "run-b")
check("note + meta carried", items[0]["note"] == "the SRv6 variant" and items[0]["confidence"] == "High")

print("=== 3. Re-adding a run dedupes and moves it to top (no duplicates) ===")
inbox.add(path, "run-a", "updated note", {"problem": "SR-MPLS core"}, ts="2026-01-03T00:00:00Z")
items = inbox.load(path)
check("still 2 items (deduped)", len(items) == 2)
check("run-a moved to top with updated note", items[0]["run_id"] == "run-a" and items[0]["note"] == "updated note")

print("=== 4. set_note edits in place ===")
inbox.set_note(path, "run-b", "renamed")
check("run-b note updated", next(i for i in inbox.load(path) if i["run_id"] == "run-b")["note"] == "renamed")

print("=== 5. remove deletes; persists across reload ===")
inbox.remove(path, "run-a")
items = inbox.load(path)
check("run-a removed", all(i["run_id"] != "run-a" for i in items))
check("run-b still present (persisted)", any(i["run_id"] == "run-b" for i in items))

print()
print("RESULT:", "ALL GREEN — inbox saves, edits, removes, and persists." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
