# LLD Patterns — reference for the LLD Generator

Starting frames for the mechanical parts of an LLD. Adapt to the customer's existing conventions
(House Rule 8) and ground any platform-specific limit before committing (House Rule 4).

## Addressing / IPAM
| Block | Convention | Notes |
|---|---|---|
| Loopback0 (router-id / SR) | one /32 per node from a tight, summarizable range | drives router-id, prefix-SID, iBGP peering, mgmt of record |
| Point-to-point links | /31 (IPv4) or /127 (IPv6) | halves address burn; document the "low end = lower router-id" rule |
| Anycast / VIP | shared /32 across a pair | RR anycast, default-gateway, DNS/NTP anycast |
| Management | out-of-band /24 per site, separate VRF | never share with data plane |

Keep one **authoritative allocation table**. Summarize loopbacks per region so the IGP/SR plan stays
clean. No overlaps — this is the #1 Critic catch.

## IGP (IS-IS shown; OSPF analogous)
- Single L2 domain for a flat SP core, or L1/L2 with summarization at the boundary for scale.
- Wide metrics; reference bandwidth set so 10/40/100G are distinguishable.
- **TI-LFA** enabled for sub-50ms protection — but state the **hardware/BFD-in-hardware dependency**.
- Authentication on; BFD for fast detection (echo vs async per platform).
- `overload-bit on-startup` so a rebooting node doesn't black-hole transit before BGP converges.

## SR-MPLS SID / label plan
- **SRGB**: pick one range and keep it identical fabric-wide (e.g. 16000–23999). Document it.
- **Prefix-SID** = deterministic function of the loopback (e.g. node-id offset from SRGB base) so the
  loopback table and SID table are one lookup apart.
- **Adjacency-SIDs**: dynamic is fine; use manual/persistent only where TE policy needs a stable label.
- **Anycast-SID** for RR/GW pairs so traffic follows the nearest of the pair.
- Verify no SID overlaps SRGB-vs-SID and no two nodes claim the same prefix-SID.

## BGP
- iBGP via **redundant RRs**; assign **cluster-IDs** so a client doesn't lose diverse paths
  (path-hiding is a classic Critic catch); consider `add-path` for diversity.
- Address-families per service: VPNv4/VPNv6 (L3VPN), L2VPN-EVPN, etc.
- **RT/RD plan**: RD per-PE-per-VRF (`<loopback>:<vrf-id>`); RT per service/topology (hub/spoke).
- eBGP edges: **TTL-security / GTSM**, max-prefix, prefix-lists/RPKI, BFD.

## QoS (end-to-end)
| Class | Marking | Treatment |
|---|---|---|
| Network control | CS6 | strict, protected |
| VoIP / realtime | EF | priority queue, policed |
| Business / signalling | AF31/CS3 | guaranteed bandwidth |
| Best effort | DF | default |
| Scavenger | CS1 | minimal / first to drop |
Mark/classify at the **edge**, **trust** in the core. Keep the class map identical across platforms;
note where a platform's queue model forces a compromise (hand to the Multi-Vendor Translator).

## Security zones (House Rule 5)
- Map HLD segments → VRFs / zones; per-zone ACL **intent** (the Config Engineer writes the rules).
- **CoPP/iACL** target profile for the control plane; management-plane separation (its own VRF, ACL,
  AAA, no plaintext).
- Encryption where the HLD calls for it: MACsec (link), IPsec (overlay/WAN).

## Naming
Apply the customer convention to hostnames, interface descriptions, VRFs, policies, prefix-lists,
route-maps. Descriptions carry intent + neighbor (e.g. `to:PE1.Gi0/0/0/1 [L3VPN-CustA]`).
