# Hypothesis tree — reference for the Troubleshooter

Work bottom-up by layer; at each layer, the decisive test that confirms or kills the hypothesis.
Commands are illustrative — adapt to platform (IOS-XR/XE, NX-OS, Junos).

## Layered causes → decisive test
| Layer | Hypothesis | Confirm / kill with |
|---|---|---|
| Physical | bad optic / fiber / CRC | interface counters: CRC, input errors, light levels (Rx/Tx dBm), flaps |
| Link / L2 | MTU mismatch, LACP down, duplex | `show interface`, LACP state, ping with DF + size sweep |
| IGP | adjacency down/flapping, metric, auth | `show isis/ospf neighbor`, adjacency log, area/level mismatch, auth |
| Label / SR | missing label, SRGB mismatch, LFA | `show mpls forwarding`, prefix-SID vs SRGB, label for the prefix |
| BGP | session down, no route, policy filter | `show bgp neighbor` (state, last error), `show bgp <pfx>`, in/out policy, max-prefix hit |
| Service | VRF RT/RD wrong, EVPN type missing | `show vrf`, RT import/export, EVPN route types, MAC/IP table |
| Policy/QoS/ACL | ACL drop, QoS starvation, RPF | ACL hit counters, queue drops, uRPF, policer |
| Control-plane | CoPP/LPTS drops, CPU, RP memory | CoPP/LPTS drop counters, CPU/mem, process logs |
| Software | known defect / PSIRT | version + WebSearch the bug/advisory (ground it — House Rule 4) |

## "What changed?" — highest-yield first
Config change, software upgrade, hardware swap, traffic/scale shift, a peer's change, a maintenance
window, time-correlated event. Correlate the symptom's start time against change logs.

## Ranking tests (likelihood × ease)
Run cheap, decisive tests before expensive ones:
- A single `show <neighbor>` that proves the session is down beats reading 10k lines of config.
- A DF-bit ping sweep confirms/kills MTU in seconds.
- Counter deltas (run twice, diff) prove "actively dropping now" vs "historical".

## Root cause vs contributing factor
- **Root cause**: remove it and the incident does not happen.
- **Contributing**: made it worse, larger blast radius, or harder to detect (e.g. missing alert).
State both; fix the root, note the contributing for Prevention.
