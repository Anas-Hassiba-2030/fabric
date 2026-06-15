#!/usr/bin/env python3
"""WRATH inbox — a saved-results workspace (Phase: Inbox).

When Kamal tests several problems he wants to keep the good ones with a note and revisit them later.
The inbox is a small persistent collection of bookmarked runs (run_id + note), separate from the
auto-history. Pure file ops over a JSON list, so it is testable — see webui/test_inbox.py.

    add(path, run_id, note, meta, ts) -> item
    set_note(path, run_id, note) -> items
    remove(path, run_id) -> items
    load(path) -> items
"""
import json
import os
import sys
import time


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save(path, items):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(items[:200], fh)


def add(path, run_id, note="", meta=None, ts=None):
    items = [i for i in load(path) if i.get("run_id") != run_id]  # dedupe -> newest wins
    item = {"run_id": run_id, "note": note or "",
            "saved_at": ts or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    item.update(meta or {})
    items.insert(0, item)
    save(path, items)
    return item


def set_note(path, run_id, note):
    items = load(path)
    for i in items:
        if i.get("run_id") == run_id:
            i["note"] = note or ""
    save(path, items)
    return items


def remove(path, run_id):
    items = [i for i in load(path) if i.get("run_id") != run_id]
    save(path, items)
    return items


if __name__ == "__main__":
    MEM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wrath", "memory")
    for it in load(os.path.join(MEM, "inbox.json")):
        print(f"{it.get('saved_at','')}  {it.get('run_id','')[:8]}  {it.get('note','')}")
    sys.exit(0)
