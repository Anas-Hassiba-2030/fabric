#!/usr/bin/env python3
"""config_lint.py — deterministic syntactic pre-pass for the Config Audit skill.

Multi-vendor (IOS-XR / IOS-XE / NX-OS / Junos). Heuristic, NOT a full parser: it surfaces the
mechanical catches a regex can reliably find so the Validator can spend judgment on the rest.
Mechanics in the script, reasoning in the agent (charter §3).

Usage:
    python config_lint.py <config-file> [--vendor ios-xr|ios-xe|nxos|junos]
    python config_lint.py --self-test

Exit code: 0 if no CRITICAL/HIGH findings, 1 otherwise (so a CI/gate step can fail fast).
"""
import argparse
import ipaddress
import re
import sys
from collections import Counter

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def detect_vendor(text):
    t = text.lower()
    # Junos: 'set ...' stanzas or hierarchical braces with apply-groups.
    if re.search(r"(?m)^\s*set (interfaces|protocols|system|routing-options|class-of-service)\b", text) \
       or "apply-groups" in t:
        return "junos"
    # NX-OS: feature-gating, CoPP profile, nv overlay, or bare slot/port Ethernet + 'no switchport'.
    if re.search(r"(?m)^\s*feature [\w-]+", text) or "nv overlay evpn" in t or "copp profile" in t \
       or re.search(r"(?m)^\s*interface Ethernet\d+/\d+", text) or re.search(r"(?m)^\s*no switchport\b", text):
        return "nxos"
    # IOS-XR: four-tuple interface paths or the XR 'ipv4 address' + address-family idiom.
    if re.search(r"\binterface \S*\d+/\d+/\d+/\d+", text) \
       or (re.search(r"(?m)^\s*ipv4 address ", text) and "address-family" in t):
        return "ios-xr"
    # IOS-XE: classic long-form interface names.
    if re.search(r"\binterface (GigabitEthernet|TenGigE|TenGigabitEthernet|FortyGigE|Loopback|Port-channel)\d", text):
        return "ios-xe"
    return "unknown"


def add(findings, sev, msg, line=None):
    findings.append((sev, msg, line))


# ---- generic checks across all vendors -------------------------------------------------

PLAINTEXT_SECRET_RES = [
    (re.compile(r"\bpassword 0 \S+", re.I), "plaintext password (type 0)"),
    (re.compile(r"\bsecret 0 \S+", re.I), "plaintext secret (type 0)"),
    (re.compile(r"\bplain-text-password\b", re.I), "plaintext password keyword"),
    (re.compile(r"\bsnmp-server community (public|private)\b", re.I), "default/guessable SNMP community"),
    (re.compile(r"encrypted-password \"?\$1\$", re.I), "weak MD5 ($1$) password hash"),
]

PLACEHOLDER_RE = re.compile(r"\b(TODO|FIXME|XXX|CHANGEME|<[^>]+>|x\.x\.x\.x|a\.b\.c\.d)\b", re.I)
TELNET_RE = re.compile(r"transport input .*\btelnet\b|set system services telnet", re.I)


def check_generic(text, findings):
    for i, line in enumerate(text.splitlines(), 1):
        for rex, label in PLAINTEXT_SECRET_RES:
            if rex.search(line):
                add(findings, "CRITICAL", f"{label}", i)
        if PLACEHOLDER_RE.search(line) and not line.strip().startswith(("!", "#")):
            add(findings, "HIGH", "unresolved placeholder / template token left in config", i)
        if TELNET_RE.search(line):
            add(findings, "HIGH", "telnet enabled (use SSH only)", i)

    # duplicate IPv4 host/interface addresses within the file
    addrs = []
    for m in re.finditer(r"(?:ip(?:v4)? address |address )(\d+\.\d+\.\d+\.\d+)[ /]", text):
        addrs.append(m.group(1))
    for ip, n in Counter(addrs).items():
        if n > 1:
            add(findings, "CRITICAL", f"duplicate IP address {ip} used {n} times in this file")

    # invalid IPs
    for m in re.finditer(r"(\d+\.\d+\.\d+\.\d+)", text):
        try:
            ipaddress.ip_address(m.group(1))
        except ValueError:
            add(findings, "HIGH", f"invalid IPv4 address literal: {m.group(1)}")

    # eBGP multihop without TTL-security (session-killer / spoofing risk)
    if re.search(r"ebgp-multihop", text, re.I) and not re.search(r"ttl-security|ttl\s+\d", text, re.I):
        add(findings, "HIGH", "eBGP multihop without TTL-security/GTSM")

    # MTU sanity: jumbo on some links but not others is a classic black-hole
    mtus = set(int(m.group(1)) for m in re.finditer(r"\bmtu (\d{3,5})", text))
    if len(mtus) > 1 and (max(mtus) - min(mtus) >= 100):
        add(findings, "MEDIUM", f"inconsistent MTU values {sorted(mtus)} — verify end-to-end path MTU")


# ---- vendor-specific checks ------------------------------------------------------------

def check_ios_like(text, findings, vendor):
    # interfaces left shutdown / missing 'no shutdown'
    blocks = re.split(r"(?m)^(?=interface )", text)
    for b in blocks:
        if not b.startswith("interface"):
            continue
        name = b.splitlines()[0].strip()
        if re.search(r"^\s*shutdown\s*$", b, re.M) and not re.search(r"^\s*no shutdown", b, re.M):
            add(findings, "HIGH", f"{name}: interface is shutdown (no 'no shutdown')")
        if re.search(r"ip address|ipv4 address", b) and "description" not in b:
            add(findings, "LOW", f"{name}: addressed interface has no description")
    # CoPP / control-plane protection presence
    if vendor in ("ios-xe",) and "control-plane" not in text:
        add(findings, "MEDIUM", "no control-plane/CoPP policy (IOS-XE does not police the RP for you)")
    if vendor == "nxos":
        if not re.search(r"copp profile|policy-map type control-plane", text, re.I):
            add(findings, "MEDIUM", "no CoPP profile referenced (NX-OS ships one — don't remove it)")
        # feature-gating: used keywords that need a 'feature'
        feature_needs = {"router bgp": "bgp", "router ospf": "ospf", "router isis": "isis",
                         "nv overlay evpn": "nv overlay", "interface Vlan": "interface-vlan"}
        enabled = set(re.findall(r"^\s*feature ([\w-]+)", text, re.M))
        for kw, feat in feature_needs.items():
            if kw.lower() in text.lower() and not any(feat.split()[0] == e or feat == e for e in enabled) \
               and feat.split()[0] not in enabled:
                add(findings, "HIGH", f"uses '{kw}' but 'feature {feat}' not enabled")
    if vendor == "ios-xr":
        # IOS-XR script must commit
        if "router bgp" in text or "router isis" in text:
            pass  # commit is issued by the deploy tool, not the file; informational only


def check_junos(text, findings):
    if re.search(r"\bset protocols isis\b", text) and "family iso" not in text:
        add(findings, "HIGH", "IS-IS configured but no 'family iso' on any unit — adjacency won't form")
    if re.search(r"\bset protocols mpls\b", text) and "family mpls" not in text:
        add(findings, "HIGH", "MPLS configured but no 'family mpls' on any unit")
    if "set system services telnet" in text:
        add(findings, "HIGH", "telnet service enabled")
    if "lo0" not in text and "set protocols bgp" in text:
        add(findings, "MEDIUM", "BGP present but no lo0 control-plane protection filter referenced")


def lint(text, vendor=None):
    vendor = vendor or detect_vendor(text)
    findings = []
    check_generic(text, findings)
    if vendor in ("ios-xr", "ios-xe", "nxos"):
        check_ios_like(text, findings, vendor)
    elif vendor == "junos":
        check_junos(text, findings)
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f[0], 9), f[2] or 0))
    return vendor, findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?")
    ap.add_argument("--vendor", choices=["ios-xr", "ios-xe", "nxos", "junos"])
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    if not args.config:
        ap.error("config file required (or use --self-test)")
    with open(args.config, encoding="utf-8", errors="replace") as fh:
        text = fh.read()

    vendor, findings = lint(text, args.vendor)
    print(f"# config_lint — vendor: {vendor} — {len(findings)} finding(s)")
    for sev, msg, line in findings:
        loc = f" (line {line})" if line else ""
        print(f"[{sev}] {msg}{loc}")
    blocking = any(s in ("CRITICAL", "HIGH") for s, _, _ in findings)
    print(f"# pre-pass: {'FAIL (CRITICAL/HIGH present)' if blocking else 'clean'} — judgment still required")
    return 1 if blocking else 0


def _self_test():
    samples = {
        "ios-xe": "interface GigabitEthernet1\n ip address 10.0.0.1 255.255.255.0\n shutdown\nsnmp-server community public RO\n",
        "nxos": "router bgp 65000\n address-family l2vpn evpn\ninterface Ethernet1/1\n no switchport\n ip address 10.0.0.0/31\n",
        "junos": "set protocols isis interface ge-0/0/1.0 point-to-point\nset interfaces ge-0/0/1 unit 0 family inet address 10.0.0.0/31\n",
    }
    ok = True
    for v, cfg in samples.items():
        det = detect_vendor(cfg)
        vendor, findings = lint(cfg)
        sevs = [s for s, _, _ in findings]
        print(f"{v}: detected={det} findings={len(findings)} severities={sevs}")
        if not findings:
            ok = False
    print("SELF-TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
