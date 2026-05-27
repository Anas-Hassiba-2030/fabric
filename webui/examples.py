#!/usr/bin/env python3
"""WRATH worked-example reader — browse the reference engagements in the Console (read-only, jailed).

Lists the worked examples under deliverables/ and serves their .md/.cfg files. **Path-jailed**: a
request can only reach a real file *inside* deliverables/ (no traversal, no other extensions), so the
viewer can't be used to read arbitrary files. Pure — see webui/test_examples.py.

    list_examples() -> [ {name, files:[...]} ]
    read_example(relpath) -> str | None
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BASE = os.path.join(REPO, "deliverables")
ALLOW_EXT = {".md", ".cfg"}


def list_examples():
    out = []
    try:
        for d in sorted(os.listdir(BASE)):
            p = os.path.join(BASE, d)
            if not os.path.isdir(p) or d.startswith("_"):
                continue
            files = sorted(f for f in os.listdir(p) if os.path.splitext(f)[1] in ALLOW_EXT)
            if files:
                out.append({"name": d, "files": files})
    except Exception:
        pass
    return out


def _safe(relpath):
    full = os.path.normpath(os.path.join(BASE, relpath or ""))
    if not (full == BASE or full.startswith(BASE + os.sep)):
        return None  # traversal escape
    if os.path.splitext(full)[1] not in ALLOW_EXT:
        return None
    if not os.path.isfile(full):
        return None
    return full


def read_example(relpath):
    f = _safe(relpath)
    if not f:
        return None
    with open(f, encoding="utf-8") as fh:
        return fh.read()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(read_example(sys.argv[1]) or "(not found / not allowed)")
    else:
        for e in list_examples():
            print(e["name"], "->", ", ".join(e["files"]))
