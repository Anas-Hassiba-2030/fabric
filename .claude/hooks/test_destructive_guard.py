#!/usr/bin/env python3
"""Unit test for the destructive-action-guard decision logic.

Run: python .claude/hooks/test_destructive_guard.py
Asserts the guard ASKS on device-push commands and ALLOWS ordinary dev/source-control commands.
"""
import importlib.util
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "guard", os.path.join(_here, "destructive_action_guard.py")
)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)

ALLOW = [
    "git push origin main",          # source control, NOT a device push
    "git commit -m 'wip'",
    "ls -la",
    "python deploy_app.py",
    "npm run build",
    "pytest tests/",
    "grep -r config .",
    "scp report.pdf user@host:/tmp",  # scp of a non-config file
]

ASK = [
    "ssh router1 conf t",
    "ssh admin@10.0.0.1 'configure terminal'",
    "python push.py --napalm",
    "ansible-playbook deploy-core.yml --apply",
    "scp core.cfg admin@10.0.0.1:/",
    "clogin -x cmds.txt pe1",
    "netmiko_send_config.py",
    "write memory",
    "copy running-config startup-config",
]

def main():
    failures = []
    for cmd in ALLOW:
        decision, _ = guard.evaluate(cmd)
        if decision != "allow":
            failures.append(f"  EXPECTED allow, GOT {decision}: {cmd}")
    for cmd in ASK:
        decision, reason = guard.evaluate(cmd)
        if decision != "ask":
            failures.append(f"  EXPECTED ask,   GOT {decision}: {cmd}")

    total = len(ALLOW) + len(ASK)
    if failures:
        print(f"FAIL — {len(failures)}/{total} cases wrong:")
        print("\n".join(failures))
        sys.exit(1)
    print(f"PASS — all {total} cases correct "
          f"({len(ALLOW)} allow, {len(ASK)} ask). git push allowed; device-push flagged.")


if __name__ == "__main__":
    main()
