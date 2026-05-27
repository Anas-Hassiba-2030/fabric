#!/usr/bin/env python3
"""Proof that pattern persistence commits to git safely — no API key, uses a throwaway repo.

Run:  python webui/test_persist.py
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import persist  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


d = tempfile.mkdtemp()


def git(*a):
    return subprocess.run(["git", "-C", d, *a], capture_output=True, text=True)


git("init", "-q")
git("config", "user.email", "t@wrath.test")
git("config", "user.name", "wrath-test")
git("config", "commit.gpgsign", "false")
open(os.path.join(d, "seed.txt"), "w").write("seed")
git("add", "seed.txt")
git("commit", "-qm", "seed")

os.makedirs(os.path.join(d, "wrath", "memory", "patterns"))
open(os.path.join(d, "wrath", "memory", "patterns", "srv6.md"), "w").write("# Pattern — SRv6")
open(os.path.join(d, "unrelated.txt"), "w").write("dirty working change")  # must NOT be committed

print("=== 1. Commits the pattern (path-scoped) ===")
res = persist.commit_paths(d, ["wrath/memory/patterns/srv6.md"], "WRATH: learn pattern srv6")
check("committed=True", res.get("committed") is True)
check("returns a short sha", bool(res.get("sha")))
check("commit message recorded", "WRATH: learn pattern srv6" in git("log", "--oneline", "-1").stdout)
check("pattern file is now tracked", "wrath/memory/patterns/srv6.md" in git("ls-files").stdout)

print("=== 2. Unrelated working changes are NOT swept into the commit ===")
check("unrelated.txt left untracked (not committed)", "unrelated.txt" not in git("ls-files").stdout)

print("=== 3. Re-committing an unchanged pattern is a safe no-op ===")
res2 = persist.commit_paths(d, ["wrath/memory/patterns/srv6.md"], "WRATH: again")
check("ok but committed=False (nothing to commit)", res2.get("ok") is True and res2.get("committed") is False)

print("=== 4. Outside a git repo: safe failure, no crash ===")
res3 = persist.commit_paths(tempfile.mkdtemp(), ["x.md"], "m")
check("ok=False, committed=False", res3.get("ok") is False and res3.get("committed") is False)

print()
print("RESULT:", "ALL GREEN — patterns persist to git, safely and scoped." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
