#!/usr/bin/env python3
"""Proof: OpsRAG typed corpus ingestion (Phase 3 foundation).

Runs the CLI + RFC extractors against representative FRR config and RFC 4271 text and asserts
that the resulting graph holds the typed contract that downstream phases depend on.

    python webui/test_ingest.py    (no key, no Docker, no host requirements)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opsrag import ingest  # noqa: E402
from opsrag.schema import Graph, validate  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


# Representative FRR config + show output (the kind of text Phase 3 will sweep over the corpus).
FRR_TEXT = """
router bgp 65001
 bgp router-id 10.255.0.2
 neighbor 192.0.2.2 remote-as 65010
 neighbor 192.0.2.2 password s3cr3t
 neighbor 192.0.2.2 route-map RM-CUST-IN in
 neighbor 192.0.2.2 update-source eth2
exit

show bgp summary
show ip bgp neighbors 192.0.2.2
show interface eth2
show ip route bgp
"""

# Representative RFC-shaped normative text (excerpt-style; mirrors the language used in RFC 4271/7606).
RFC_TEXT = """
4.  Message Formats

A BGP speaker MUST send a NOTIFICATION message when it detects an error condition.
The OPEN message MUST be the first message sent by each side after the TCP connection is established.

4.1.  TCP MD5 Authentication

When TCP-MD5 authentication is configured, the receiver MUST drop any TCP segment
whose MD5 digest fails verification. An incorrect password will cause the session to fail
and remain in Idle state.

6.  Error Handling

If the AS_PATH attribute contains a loop, the route MUST be rejected.
If the OPEN message carries an unsupported version, the receiver MUST respond with a NOTIFICATION
and the TCP connection MUST be reset to Idle.
"""

print("=== 1. CLI extractor yields typed Command + Configuration nodes ===")
cli_nodes = ingest.cli_extractor(FRR_TEXT, "test/frr-config")
by_type = {}
for n in cli_nodes:
    by_type[n.type] = by_type.get(n.type, 0) + 1
check("found at least one Command node", by_type.get("Command", 0) >= 1)
check("found at least one Configuration node", by_type.get("Configuration", 0) >= 1)
check("every node carries provenance.source", all(n.provenance.source for n in cli_nodes))
check("router bgp 65001 captured as a Configuration node",
      any(n.type == "Configuration" and "65001" in n.name for n in cli_nodes))
check("neighbor 192.0.2.2 password captured (auth tag)",
      any("password" in n.name and "auth" in n.attrs.get("tags", []) for n in cli_nodes))
check("show bgp summary captured as a Command node",
      any(n.type == "Command" and "bgp" in n.name for n in cli_nodes))

print("=== 2. RFC extractor yields typed Concept + RootCause candidates ===")
rfc_nodes = ingest.rfc_extractor(RFC_TEXT, "rfc4271")
by_type_r = {}
for n in rfc_nodes:
    by_type_r[n.type] = by_type_r.get(n.type, 0) + 1
check("found at least one Concept node", by_type_r.get("Concept", 0) >= 1)
check("found at least one RootCause candidate", by_type_r.get("RootCause", 0) >= 1)
check("RootCause candidates carry failure tokens",
      any("fail" in n.attrs.get("content", "").lower() or "reject" in n.attrs.get("content", "").lower()
          for n in rfc_nodes if n.type == "RootCause"))
check("RFC nodes are not flagged authored (learned, not curated)",
      all(not n.provenance.authored for n in rfc_nodes))

print("=== 3. Link extractor infers cross-type edges (graph is connected) ===")
edges = ingest.link_nodes(cli_nodes + rfc_nodes)
check("at least one verifies edge inferred", any(e.rel == "verifies" for e in edges))
check("at least one depends_on edge inferred", any(e.rel == "depends_on" for e in edges))

print("=== 4. ingest_text merges cleanly into an existing graph; result validates ===")
g = Graph()
added_n, added_e = ingest.ingest_text(g, FRR_TEXT + RFC_TEXT, "test/combined")
v = validate(g)
check("merged graph validates green", v["ok"])
check("nodes were added (no silent drop)", added_n > 0)
check("no dangling edges after merge", not any("dangling" in e for e in v.get("errors", [])))

print("=== 5. Idempotent ingest — same text twice does not double-count ===")
g2 = Graph()
n1, e1 = ingest.ingest_text(g2, FRR_TEXT, "test/dup")
n2, e2 = ingest.ingest_text(g2, FRR_TEXT, "test/dup")
check("second ingest is a no-op", n2 == 0 and e2 == 0)

print()
print("RESULT:", "ALL GREEN — Phase-3 ingestion foundation works (typed nodes + safe merge)." if not fails
      else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
