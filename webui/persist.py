#!/usr/bin/env python3
"""WRATH persistence — commit distilled patterns to git so learning survives (Phase 3).

Compounding memory is only real if it outlives the process. When Kamal accepts a run and it distils
into a pattern, this commits that pattern file to the repo — **path-scoped**, so it never sweeps up
his other working changes — with an optional push. Safe no-ops outside a git repo or when there's
nothing to commit.

    commit_paths(repo, paths, message, push=False) -> {ok, committed, sha?, pushed?, detail?}
"""
import os
import subprocess
import sys


def _git(repo, *args, timeout=60):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=timeout)


def is_repo(repo):
    try:
        return _git(repo, "rev-parse", "--is-inside-work-tree").returncode == 0
    except Exception:
        return False


def commit_paths(repo, paths, message, push=False):
    if not is_repo(repo):
        return {"ok": False, "committed": False, "detail": "not a git repo"}
    add = _git(repo, "add", "--", *paths)
    if add.returncode != 0:
        return {"ok": False, "committed": False, "detail": (add.stderr or "git add failed").strip()[:200]}
    # Path-scoped commit: only these paths are committed; any other staged work is left untouched.
    c = _git(repo, "commit", "-m", message, "--", *paths)
    if c.returncode != 0:
        return {"ok": True, "committed": False, "detail": (c.stdout + c.stderr).strip()[:200]}
    sha = _git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
    res = {"ok": True, "committed": True, "sha": sha}
    if push:
        p = _git(repo, "push", timeout=180)
        res["pushed"] = p.returncode == 0
        res["push_detail"] = (p.stdout + p.stderr).strip()[:200]
    return res


if __name__ == "__main__":
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(commit_paths(repo, sys.argv[1:] or [], "WRATH: manual persist", push=False))
