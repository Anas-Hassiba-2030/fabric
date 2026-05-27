#!/usr/bin/env python3
"""Proof that the worked-example reader lists + serves files and is path-jailed — no API key.

Run:  python webui/test_examples.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import examples  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


print("=== 1. Lists both worked examples ===")
names = {e["name"] for e in examples.list_examples()}
check("example-acme-sp listed", "example-acme-sp" in names)
check("example-dc-evpn listed", "example-dc-evpn" in names)
check("scratch (_) excluded", not any(n.startswith("_") for n in names))

print("=== 2. Serves a real file inside deliverables/ ===")
c = examples.read_example("example-dc-evpn/03-config-leaf1.cfg")
check("leaf config served", c and "LEAF1" in c)
hld = examples.read_example("example-acme-sp/01-hld.md")
check("acme HLD served", bool(hld))

print("=== 3. Path-jailed: traversal + bad extensions are refused ===")
check("../ escape refused", examples.read_example("../README.md") is None)
check("deep traversal refused", examples.read_example("../../etc/passwd") is None)
check("normalized escape refused", examples.read_example("example-dc-evpn/../../webui/app.py") is None)
check("non-md/cfg extension refused", examples.read_example("../webui/app.py") is None)
check("missing file -> None", examples.read_example("example-dc-evpn/nope.md") is None)

print("=== 4. Deterministic ===")
check("same path -> identical content", examples.read_example("example-dc-evpn/02-lld.md") == examples.read_example("example-dc-evpn/02-lld.md"))

print()
print("RESULT:", "ALL GREEN — example reader works and stays jailed." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
