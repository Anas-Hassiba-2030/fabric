# OpsRAG sandbox — three ways to stand it up

Honest answer to "do we need a Docker host?" — **no, not strictly.** The execution-oracle loop
runs end-to-end **today** without any virtualisation, because `webui/opsrag/sim.py` is a
deterministic mini-FRR with the same return contract as a real Containerlab exec. The full
benchmark sweep + the academic "running on real software" demo prefer a real sandbox, but the
thesis loop itself is not gated by it. Pick whichever path your machine supports.

## Path A — Containerlab + FRRouting (preferred for the killer demo)

What you need: Linux host, Docker, `containerlab`. Mac/Windows can do it inside a Linux VM.

```bash
sudo containerlab deploy  -t thesis/lab/topo-bgp.clab.yml
sudo containerlab inspect -t thesis/lab/topo-bgp.clab.yml
# inject a fault on the relevant node
docker exec -i clab-opsrag-R2 vtysh -c "configure terminal" \
                                    -c "router bgp 65001"   \
                                    -c "neighbor 192.0.2.2 remote-as 65999"
# run the troubleshooter; oracle returns {executable, diagnosis_correct}
sudo containerlab destroy -t thesis/lab/topo-bgp.clab.yml
```

The WRATH read-only network-state MCP server (`wrath-netstate`) switches its source from a static
snapshot to a `containerlab inspect` adapter via `WRATH_NETSTATE_URL` — same loader, different
backing store.

This is the **Phase 2-B** target. It is gated by output equivalence with the simulator on the
seed benchmark, so promoting to this branch is a swap of executor, not a re-write.

## Path B — Mininet + native FRR (no Docker on Linux)

If Docker is unavailable but you have Linux + root: install `mininet` + `frr` from the distro
packages, write a small `Topo` subclass that mirrors `topo-bgp.clab.yml` (three hosts, two links,
one FRR daemon per host with the same config). The oracle's executor adapter is `mn h R2 vtysh
-c "<command>"` instead of `docker exec`. Same FRR. Same outputs.

## Path C — FRR in network namespaces (Linux, no Docker, no Mininet)

The lightest real-software path. Create three Linux network namespaces, run one `frr` instance
per namespace, wire `veth` pairs to match the topology. `ip netns exec R2 vtysh -c "<command>"`
is the executor. This is the route I'd take on a stock Linux box without privileges to install
Docker.

## Path D — the in-repo deterministic simulator (no host requirements, **today**)

`python webui/test_opsrag.py` runs the full loop right now:

- `webui/opsrag/sim.py` — baseline state + fault application + `exec_cmd` returning realistic
  FRR-like stdout for the three seeded faults.
- `webui/opsrag/synthesizer.py` — symptom → discovery commands → signal match → typed runbook.
- `webui/opsrag/oracle.py` — runs the runbook against the simulated state, returns
  `{executable, evidence_hit, diagnosis_correct, command_outputs}`.

This is **Phase 2-A** — done. It lets the entire thesis loop (sim → synthesiser → oracle →
graph admission → evaluation) be wired and tested without owning a Docker host. Phase 2-B
swaps the executor for real Containerlab and asserts identical scoring on the same fault
library. Anything that doesn't agree is a sim bug to fix, not a research result.

## Why this matters for the proposal

Kamal asked whether a Docker host is necessary. The thesis is **not blocked** on it: the kernel
+ loop + benchmark scoring runs today on any laptop with Python. The Docker host is needed only
to validate that the simulator's FRR-like outputs match real FRR — which is a separate, much
smaller piece of work than the thesis as a whole.
