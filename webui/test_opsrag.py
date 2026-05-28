#!/usr/bin/env python3
"""Proof: OpsRAG schema validates, bootstrap lifts memory into typed nodes, oracle's loop closes.

Run:  python webui/test_opsrag.py     (no key, deterministic, no Docker)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opsrag import bootstrap, oracle, sim, synthesizer  # noqa: E402
from opsrag.schema import Edge, Graph, Node, Provenance, validate  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


print("=== 1. Schema validates clean graphs + flags real defects ===")
g = Graph()
g.add(Node(id="c:bgp", type="Concept", name="BGP", provenance=Provenance(source="rfc4271")))
g.add(Node(id="rb:bgp-flap", type="Runbook", name="BGP flap RCA", provenance=Provenance(source="patterns/bgp-flap.md")))
g.link("rb:bgp-flap", "c:bgp", "depends_on", Provenance(source="patterns/bgp-flap.md"))
v = validate(g)
check("clean graph -> ok=True", v["ok"] is True and v["errors"] == [])
check("counts node types", v["by_type"].get("Concept") == 1 and v["by_type"].get("Runbook") == 1)

bad = Graph()
bad.add(Node(id="n1", type="Mystery", name="x", provenance=Provenance(source="src")))
bad.edges.append(Edge(src="n1", dst="nope", rel="diagnoses", provenance=Provenance(source="src")))
b = validate(bad)
check("invalid node type detected", any("invalid type" in e for e in b["errors"]))
check("dangling dst edge detected", any("dangling dst" in e for e in b["errors"]))

print("=== 2. Bootstrap lifts existing memory into typed nodes ===")
g2 = bootstrap.from_memory(REPO)
v2 = validate(g2)
check("bootstrapped graph validates", v2["ok"])
check("has at least one Runbook (a learned pattern)", v2["by_type"].get("Runbook", 0) >= 1)
check("has Concept nodes (vocab / customers)", v2["by_type"].get("Concept", 0) >= 1)
check("every node carries provenance.source",
      all(n.provenance.source for n in g2.nodes.values()))

print("=== 3. Oracle closes the execution loop (deterministic simulator) ===")
fault = {
    "id": "f-bgp-wrong-remote-as",
    "expected_evidence": ["show bgp summary"],
    "ground_truth": {"root_cause": "remote-as mismatch on R2 toward R3 (configured wrong, peer is 65010)"},
}
runbook_ok = {
    "commands": [{"device": "R2", "cmd": "show bgp summary"}],
    "concluded_root_cause": "remote-as mismatch on R2 toward R3 (configured wrong, peer is 65010)",
}
runbook_wrong = {"commands": [{"device": "R2", "cmd": "show ip route"}],
                 "concluded_root_cause": "link down"}
r_ok = oracle.execute_runbook(fault, runbook_ok)
r_wrong = oracle.execute_runbook(fault, runbook_wrong)
check("correct runbook -> diagnosis_correct=True", r_ok["diagnosis_correct"] is True)
check("correct runbook -> evidence_hit + executable", r_ok["evidence_hit"] and r_ok["executable"])
check("wrong runbook -> diagnosis_correct=False", r_wrong["diagnosis_correct"] is False)

print("=== 4. The schema is the cross-RAG/agent contract (no missing types) ===")
from opsrag.schema import NODE_TYPES, EDGE_TYPES  # noqa: E402
check("six node types as per thesis O1", NODE_TYPES == {"Concept", "Command", "Configuration", "Symptom", "RootCause", "Runbook"})
check("five edge types as per thesis O1", EDGE_TYPES == {"verifies", "diagnoses", "depends_on", "supersedes", "contradicts"})

print("=== 5. Sandbox simulator emits realistic FRR signals per seeded fault ===")
faults_dir = os.path.join(REPO, "thesis", "lab", "faults")
fault_files = sorted(f for f in os.listdir(faults_dir) if f.startswith("f-") and f.endswith(".json"))
check("three seeded faults present", len(fault_files) >= 3)

loaded_faults = []
for fname in fault_files:
    with open(os.path.join(faults_dir, fname), encoding="utf-8") as fh:
        loaded_faults.append(json.load(fh))

# Healthy baseline first: nothing should show Active/Idle, no MD5 set, MTUs at 9216.
baseline = sim.baseline_state()
healthy_out = sim.exec_cmd(baseline, "R2", "show bgp summary")
check("healthy R2 summary shows Established peers",
      "Active" not in healthy_out["stdout"] and "Idle" not in healthy_out["stdout"])

# Each fault, when applied, should leave a recoverable signal in at least one expected-evidence command.
_FAULT_SIGNALS = (
    "active", "idle", "mtu 1500", "tcp-md5 password: set",
    # new faults (phase 6)
    "unreachable", "route-map for incoming", "maximum prefix reached",
    "ttl = 1, multihop", "hold timer expired", "notification sent", "not in table",
    "deny", "prefixes received and rejected",
)

def has_fault_signal(state, fault):
    for cmd in fault.get("expected_evidence", []):
        out = sim.exec_cmd(state, fault["inject"]["device"], cmd)
        text = out["stdout"].lower()
        if any(k in text for k in _FAULT_SIGNALS):
            return True
    return False

for f in loaded_faults:
    s = sim.baseline_state()
    sim.apply_fault(s, f)
    check(f"sim emits a recoverable signal for {f['id']}", has_fault_signal(s, f))

print("=== 6. End-to-end loop (sim -> synthesiser -> oracle) closes on every seeded fault ===")
for f in loaded_faults:
    rb = synthesizer.synthesise_with_sim(f)
    check(f"synth picks discovery commands for {f['id']}", len(rb["commands"]) >= 1)
    check(f"synth infers category for {f['id']} (deterministic baseline)", rb["category"] is not None)
    res = oracle.execute_runbook(f, rb)
    check(f"oracle: {f['id']} executable", res["executable"])
    check(f"oracle: {f['id']} evidence_hit", res["evidence_hit"])
    check(f"oracle: {f['id']} diagnosis_correct", res["diagnosis_correct"])

print("=== 7. Honest negatives — a non-diagnostic runbook does not falsely pass ===")
red_herring = {"commands": [{"device": "R2", "cmd": "show interface eth1"}],
               "concluded_root_cause": "link down somewhere"}
res_bad = oracle.execute_runbook(loaded_faults[0], red_herring)
check("wrong runbook does not get credit for diagnosis", not res_bad["diagnosis_correct"])

print()
print("RESULT:", "ALL GREEN — OpsRAG kernel (schema + bootstrap + sim + synth + oracle) is operational." if not fails
      else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
