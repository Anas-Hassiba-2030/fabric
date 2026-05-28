# OpsRAG sandbox — Containerlab + FRRouting

The execution oracle for the thesis (RQ2, RQ3). A generated **runbook** is executed against this
read-only sandbox; the oracle returns a structured outcome that drives both the evaluation and the
admission of new edges into the typed knowledge graph.

## What's here
- `topo-bgp.clab.yml` — the minimal BGP topology (R1 RR + R2 PE in AS 65001, R3 customer in AS 65010).
- `faults/*.json` — the fault library. Each file is a complete scenario: how to inject, what evidence
  a correct runbook should gather, and the ground-truth root cause + fix + verification.

## Why JSON for faults
Stdlib-parseable (`json` is in the standard library), so the harness and tests work without any
extra dependency. The Containerlab spec itself is YAML because that is what `containerlab` parses;
our Python code does not read it.

## How to bring it up (on a host with Docker + Containerlab)
```bash
sudo containerlab deploy   -t thesis/lab/topo-bgp.clab.yml
sudo containerlab inspect  -t thesis/lab/topo-bgp.clab.yml
sudo containerlab destroy  -t thesis/lab/topo-bgp.clab.yml
```

## How the oracle uses it
`webui/opsrag/oracle.py::execute_runbook(fault, runbook)`:
- if `containerlab` is on PATH → real path (Phase 2): deploy, inject the fault's patch on the named
  device, `docker exec` each runbook command, capture output, compare to ground truth.
- otherwise (today): **deterministic simulation** with the same return shape, so the loop is
  testable end-to-end before the lab is stood up.

## Initial fault library
| File | Symptom | Layer | Ground-truth cause |
|---|---|---|---|
| `f-bgp-wrong-remote-as.json` | eBGP stuck Idle | bgp | remote-as mismatch on R2→R3 |
| `f-bgp-mtu-mismatch.json` | session resets under load | link | MTU asymmetry (1500 vs 9000) |
| `f-bgp-md5-mismatch.json` | TCP never opens | tcp-auth | TCP-MD5 key mismatch |

This is the seed for the ~200-question BGP benchmark.
