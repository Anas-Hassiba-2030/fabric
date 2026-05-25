# Telemetry catalog — reference for the Assurance Architect

Starting map of promise → KPI → source. Sensor-path *shapes* are illustrative (OpenConfig-style);
**verify the exact path against the platform's YANG model** before committing (House Rule 4) — paths
differ across IOS-XR / Junos / NX-OS / EOS and OS versions.

## Promise → KPI → source
| Promise (SLA/SLO) | KPI | Telemetry source (shape) | Cadence |
|---|---|---|---|
| Availability | interface/oper-state, BGP/IGP session state | `openconfig-interfaces:/interfaces/interface/state/oper-status`; `…/network-instances/.../protocols/.../bgp/neighbors/neighbor/state/session-state` | on-change |
| Latency / jitter / loss | path RTT, one-way delay | synthetic probe (IP-SLA / TWAMP / model-driven OAM) | sampled 10–60s |
| Capacity / utilization | in/out octets, queue depth, drops | `…/interface/state/counters/{in,out}-octets`, qos drop counters | sampled 30s |
| Convergence | reroute events, TI-LFA activations | protocol event streams / syslog | on-change |
| Control-plane health | CPU, CoPP/LPTS drops, RP memory | platform sensor paths | sampled 30–60s |
| Optics health | Rx/Tx power, temp, FEC errors | `…/components/component/optical-channel/...` | sampled 60s |

## Telemetry transport
- **gNMI (Subscribe)** over gRPC — the modern default; `ON_CHANGE` for state, `SAMPLE` for counters.
- gRPC dial-out / dial-in per platform support; fall back to SNMP only where MDT isn't available.
- Encode/transport secured (TLS); collector in the management/assurance plane.

## SLO catalog shape
| SLI | SLO target | Source | Warning | Page | Action |
|---|---|---|---|---|---|
| Core link util | < 70% avg / 5m | octet counters | 70% | 85% | capacity review / TE shift |
| PE BGP session | 100% Established | session-state | — | any down | NOC investigate per RCA playbook |
| Edge RTT | < 20ms p95 | TWAMP probe | 20ms | 30ms | path/QoS investigation |

## Closed-loop — safe vs gated
- **Safe/reversible (auto-OK):** raise a ticket, annotate dashboards, shift traffic via a pre-approved
  TE policy that is itself revertible, scale a collector.
- **Gated (House Rule 6):** anything that pushes config to a device, drops/blocks traffic, or changes
  routing policy — propose it, never auto-apply.
