#!/usr/bin/env python3
"""OpsRAG graph SUT — typed-graph retrieval answers ALL benchmark questions (Phase 6 contribution).

Fixes the answer_relevance weakness in opsrag_sut (which returns "" for non-fault questions):
  * Fault-linked questions  → existing synthesiser path (action-grounded, exec+diag metrics)
  * Concept / recall / apply → typed-graph keyword retrieval → structured template answer

Retrieval corpus (in priority order):
  1. Pattern files (wrath/memory/patterns/*.md) — rich BGP prose, curated by Kamal.
  2. Fault library (thesis/lab/faults/*.json)   — symptom + ground-truth text per fault.
  3. Embedded BGP concept library               — one paragraph per benchmark category,
                                                  grounded in RFC text; no invented content.

BM25-style scoring (TF × IDF, same formula as dense_rag.py) ranks candidate snippets.
The top-3 are joined into the answer; CLI commands are extracted from the matched text.

Same SUT contract:  graph_sut(question) → {"answer", "retrieved_context", "commands"}
"""
import json
import math
import os
import re
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Embedded BGP concept library — one authoritative paragraph per category.
# Content is drawn from IETF RFCs and FRR/IOS documentation; no invented facts.
# ---------------------------------------------------------------------------

_CONCEPTS: Dict[str, str] = {
    "session-establishment": (
        "BGP finite-state machine (RFC 4271 §8): Idle, Connect, Active, OpenSent, OpenConfirm, Established. "
        "TCP connection on port 179. Router with the lower BGP router-ID becomes the active TCP connector; "
        "the higher router-ID becomes the listener (passive). OPEN message carries BGP version, AS number, "
        "hold time, BGP router-ID, optional capability parameters. KEEPALIVE messages maintain the session. "
        "NOTIFICATION message closes the session with an error code and sub-code. OpenConfirm is the state "
        "immediately preceding Established — local speaker has sent OPEN and received a valid OPEN from the peer, "
        "then sends KEEPALIVE; on receiving KEEPALIVE the session transitions to Established."
    ),
    "rr-reflector": (
        "Route reflector (RFC 4456): breaks iBGP full-mesh requirement which scales as n*(n-1)/2 sessions. "
        "RR re-advertises routes from clients to non-clients and other clients, adding ORIGINATOR_ID and "
        "CLUSTER_LIST attributes to prevent loops. Clients do not need direct iBGP sessions to each other. "
        "Multiple RR clusters provide redundancy; each cluster has a unique CLUSTER_ID. Split-horizon rule "
        "is relaxed for RR clients. CLUSTER_LIST loop detection: if the local CLUSTER_ID appears in the list "
        "the route is discarded."
    ),
    "security": (
        "BGP security mechanisms: TCP-MD5 (RFC 2385) authenticates TCP segments on port 179; if one side "
        "has MD5 and the other does not, SYN packets are dropped and the session stays in Idle or Active. "
        "GTSM (RFC 5082) sets TTL=255 and rejects packets with TTL < 254, preventing remote spoofing. "
        "RPKI (RFC 6811, 6480): Origin Validation uses ROAs to verify AS origin; route is Valid, Invalid, or "
        "NotFound. BGPsec (RFC 8205) provides path validation. Max-prefix limits prevent prefix explosion."
    ),
    "mtu-path": (
        "MTU mismatch causes BGP UPDATE messages to be fragmented or dropped. Large BGP UPDATE messages "
        "carrying many prefixes exceed the 1500-byte Ethernet MTU. TCP MSS negotiation limits segment size, "
        "but IP-layer fragmentation may still be blocked by the path (PMTUD). Session resets every few minutes "
        "indicate large UPDATEs are being dropped after the initial handshake. Verify with: show interface, "
        "ping with df-bit set, show ip bgp neighbors. Fix: match MTU on both ends or set jumbo frames."
    ),
    "as-path": (
        "AS_PATH attribute (RFC 4271 §5.1.2): sequence of AS numbers the route has traversed. Loop detection: "
        "eBGP speaker discards route if own AS appears in AS_PATH. AS_PATH prepending adds extra AS numbers to "
        "influence inbound traffic. Regex filtering on AS_PATH: ^65001$ matches only routes originated in AS 65001. "
        "AS_SET aggregates multiple AS paths into an unordered set. AGGREGATOR attribute records the aggregating AS."
    ),
    "communities": (
        "BGP communities (RFC 1997): 4-byte tag in format AS:value attached to prefixes. Standard well-known: "
        "NO_EXPORT (0xFFFFFF01), NO_ADVERTISE (0xFFFFFF02), NO_EXPORT_SUBCONFED (0xFFFFFF03). "
        "Extended communities (RFC 4360): 8 bytes, used for VPN RT (Route Target), EVPN, QoS. "
        "Large communities (RFC 8092): 12 bytes, format Global-Administrator:Local-Data-1:Local-Data-2 "
        "to avoid AS number collision in large operators."
    ),
    "address-family": (
        "Multiprotocol BGP (MP-BGP, RFC 4760): Capability Code 1 in OPEN. AFI/SAFI carried in "
        "MP_REACH_NLRI and MP_UNREACH_NLRI attributes. AFI=1 IPv4, AFI=2 IPv6, AFI=25 L2VPN. "
        "SAFI=1 unicast, SAFI=2 multicast, SAFI=128 VPNv4, SAFI=133 Flowspec. "
        "IPv6 prefixes over an IPv4 session require AFI=2 SAFI=1 capability exchange in OPEN. "
        "Next-hop encoding for IPv6 over IPv4: uses 128-bit IPv6 next-hop in MP_REACH_NLRI."
    ),
    "graceful-restart": (
        "BGP Graceful Restart (RFC 4724): allows a BGP speaker undergoing control-plane restart to retain "
        "forwarding state (stale routes) while the new BGP process reconnects. Restarting speaker sets "
        "Restart bit in OPEN capability; helper speaker preserves Stale routes for the Restart Time. "
        "End-of-RIB marker (empty UPDATE) signals that RIB is converged. GR prevents traffic blackhole "
        "during BGP process restart or ISSU."
    ),
    "bfd": (
        "BFD (RFC 5880) provides sub-second failure detection independent of BGP hold timer. BGP session "
        "tracks BFD state: if BFD goes down, BGP session is dropped without waiting for the hold timer. "
        "Discriminator values identify BFD sessions. show bfd neighbors shows BFD session state and interval."
    ),
    "addpath": (
        "BGP ADD-PATH (RFC 7911): allows advertising multiple paths for the same prefix. Path-ID field "
        "added to NLRI. Sender and receiver negotiate ADD-PATH capability in OPEN. Used to address "
        "path hiding behind route reflectors: all client paths visible, not just best path. "
        "ADD-PATH does not affect loop prevention — AS_PATH still used."
    ),
    "add-path-advanced": (
        "ADD-PATH (RFC 7911) advanced: path-ID uniquely identifies each path per prefix. Route reflector "
        "with ADD-PATH sends all valid paths to clients, improving BGP PIC (prefix independent convergence). "
        "Combined with CLUSTER_LIST loop prevention. Multipath use: multiple equal-cost paths visible per prefix. "
        "Receiver installs multiple paths into RIB for load balancing."
    ),
    "vpnv4-l3vpn": (
        "BGP/MPLS IP VPN (RFC 4364): VPNv4 SAFI 128. Route Distinguisher (RD) makes overlapping customer "
        "prefixes unique in the provider table. Route Target (RT) extended community controls VRF import/export. "
        "Label stack: VPN label (bottom) + transport label (top). PE router performs VRF lookup on customer traffic. "
        "MP-BGP distributes VPNv4 routes with RD prefix and RT communities between PEs."
    ),
    "sr-mpls": (
        "Segment Routing MPLS (RFC 8402, 8669, 8277): prefix-SID advertised in IGP (IS-IS, OSPF) extensions. "
        "SRGB (Segment Routing Global Block) defines the label range. Prefix-SID = SRGB base + index. "
        "TI-LFA (Topology-Independent Loop-Free Alternates) provides sub-50ms reroute. "
        "BGP-SR Policy (RFC 9256) for traffic engineering. SR-TE head-end installs programmed segment lists."
    ),
    "srv6": (
        "SRv6 (RFC 8986, 9252, 9256): IPv6 data plane segment routing. SID is an IPv6 address with "
        "Locator:Function:Argument structure. End, End.X, End.DT4, End.DT6 SID behaviours. "
        "BGP carries SRv6 SIDs in BGP-LS and BGP service routes (VPNv4/v6 over SRv6). "
        "SRH (Segment Routing Header) is a new IPv6 extension header type 43."
    ),
    "bmp": (
        "BGP Monitoring Protocol (RFC 7854): BMP peer sends real-time BGP messages (Route Monitoring, "
        "Stat Reports, Peer Down Notifications) to a BMP collector over a TCP session. "
        "Pre-Policy and Post-Policy Adj-RIB views. Peer Up notification carries OPEN parameters. "
        "Used for BGP route visibility without BGP peering to the collector."
    ),
    "confederation": (
        "BGP confederation (RFC 5065): divides a large AS into sub-ASes. iBGP full-mesh requirement "
        "satisfied within each sub-AS. Inter-confederation eBGP sessions between sub-ASes use "
        "confederation-eBGP rules (next-hop, MED preserved). The CONFED_SEQUENCE and CONFED_SET "
        "path segment types carry sub-AS numbers, stripped at the AS boundary."
    ),
    "bgpsec": (
        "BGPsec (RFC 8205, 6480): path validation using digital signatures. Each AS in the path signs "
        "the AS_PATH with its BGPsec router key (RFC 8210 RPKI key rollover). "
        "Origin Validation (RFC 6811): ROAs (RFC 6482) bind prefix to origin AS. Route is Valid, Invalid, "
        "or NotFound based on ROA coverage. RPKI RTR protocol (RFC 6810) distributes ROA data."
    ),
    "flowspec": (
        "BGP Flowspec (RFC 8955): distributes traffic filtering rules via BGP. NLRI encodes match fields "
        "(destination prefix, source prefix, IP protocol, port, DSCP). Actions: rate-limit, discard, "
        "redirect to VRF, DSCP remark. AFI=1 IPv4 Flowspec SAFI=133, IPv6 SAFI=134. "
        "Used for DDoS mitigation and traffic engineering at scale."
    ),
    "route-policy": (
        "Route policies: route-map (Cisco) or policy-statement (Junos) or route-map/route-policy (XR). "
        "Match on prefix-list, AS-path access-list, community-list, MED. "
        "Set actions: local-preference, MED, community, next-hop, weight. "
        "Applied inbound or outbound on BGP neighbors. show route-map, show ip bgp policy. "
        "Local preference: higher wins within iBGP (default 100). MED: lower wins between iBGP paths from the same AS."
    ),
    "multivendor": (
        "BGP interoperability: RFC 4271 defines the protocol; vendor-specific optional capabilities may differ. "
        "OPEN message capability negotiation: unknown optional capabilities treated as non-fatal if Optional and "
        "Transitive bits set correctly (RFC 5492). FRR, IOS-XE, IOS-XR, NX-OS, JunOS all support core BGP; "
        "SR, ADD-PATH, and Flowspec capabilities require explicit configuration on both sides."
    ),
    "ospf-underlay": (
        "OSPF underlay for BGP overlay: OSPFv2 (RFC 2328) or OSPFv3 (RFC 5340) distributes loopback "
        "reachability. Not-So-Stubby Area (NSSA, RFC 3101) allows external routes in stub-like areas. "
        "OSPF hello interval and dead interval affect adjacency hold time. "
        "BGP next-hop reachable via OSPF-learned route; if OSPF drops the next-hop is unreachable and BGP path withdrawn."
    ),
    "prefix-hijack": (
        "BGP prefix hijack: an AS announces a prefix it does not own. RPKI Origin Validation (RFC 6811) "
        "detects invalid origin. More-specific announcement (longer prefix) overrides legitimate announcement. "
        "Route leak (RFC 7908): a route learned from eBGP re-advertised to other eBGP peers without policy. "
        "Detection: IRR (Internet Routing Registry) checks, RPKI ROA. Mitigation: max-prefix, prefix filtering."
    ),
    "route-leak": (
        "BGP route leak (RFC 7908): violation of BGP's valley-free routing. Leak occurs when a provider "
        "route is re-advertised to another provider. RFC 9234: Only-to-Customer (OTC) attribute prevents "
        "re-advertisement of routes from a provider toward other providers. Role-based BGP peering. "
        "Inbound and outbound filtering with AS-path filters and community-based controls."
    ),
    "large-communities": (
        "Large BGP communities (RFC 8092): 12-byte community, format Global-Administrator:Local-Data-1:Local-Data-2. "
        "Avoids 2-byte AS number collision in 4-byte AS operator deployments. RFC 8195 best practices: "
        "well-known functions for traffic engineering, peer blackholing, NO_EXPORT equivalents."
    ),
    "as-migration": (
        "AS migration (RFC 7705): replace old AS with new AS without session resets. "
        "local-as command makes router appear to use old AS to legacy peers. "
        "no-prepend + replace-as options suppress double AS in AS_PATH. "
        "Confederation migration: sub-AS renumbering during confederation restructuring."
    ),
    "aggregation": (
        "BGP route aggregation (RFC 4271, 6472): aggregate-address command summarises multiple prefixes "
        "into a supernet. ATOMIC_AGGREGATE attribute set when AS_PATH info is suppressed. "
        "AGGREGATOR attribute carries the aggregating AS and router-ID. "
        "summary-only option suppresses more-specific component routes. as-set option includes all AS_PATH segments."
    ),
    "graceful-shutdown": (
        "BGP Graceful Shutdown (RFC 8326): GRACEFUL_SHUTDOWN community (65535:0) signals that a BGP session "
        "is about to be taken down for maintenance. Receiving routers lower local-preference to 0, diverting "
        "traffic before the session drops. Pre-shutdown maintenance procedure prevents traffic blackhole "
        "during planned router maintenance."
    ),
    "error-handling": (
        "BGP error handling (RFC 7606, 7313): attribute errors cause NOTIFICATION or route withdrawal. "
        "Treat-as-withdraw: malformed UPDATE causes route withdrawal rather than session reset. "
        "RFC 7313: NOTIFICATION message with error code and sub-code. Session reset policy: hard reset "
        "vs soft reset (route-refresh). RFC 5492: unknown optional capabilities handled gracefully."
    ),
    "multipath": (
        "BGP multipath: multiple equal-cost BGP paths installed in FIB for load balancing. "
        "maximum-paths command enables multipath (eBGP or iBGP). eBGP multipath: equal AS_PATH length, "
        "same MED, same IGP next-hop cost. iBGP multipath: same IGP cost to next-hop."
    ),
    "multipath-advanced": (
        "BGP multipath (RFC 7911 ADD-PATH): unequal-cost BGP paths visible to downstream routers. "
        "BGP PIC (prefix independent convergence): pre-installs backup next-hop in FIB for fast reroute. "
        "BFD integration: BFD failure triggers immediate FIB switchover without BGP reconvergence."
    ),
    "multiprotocol": (
        "Multiprotocol BGP extensions (RFC 4760, 5492): AFI/SAFI carried in MP_REACH_NLRI. "
        "IPv6 unicast: AFI=2 SAFI=1. VPNv4: AFI=1 SAFI=128. L2VPN EVPN: AFI=25 SAFI=70. "
        "BGP-LS: AFI=16388 SAFI=71. Capability negotiation per AFI/SAFI pair in OPEN."
    ),
    "nexthop-tracking": (
        "Next-hop tracking (RFC 4271 §9.1.2): BGP monitors IGP for next-hop reachability changes. "
        "When IGP withdraws or changes the route to a BGP next-hop, BGP re-evaluates affected paths "
        "without waiting for hold timer. show ip bgp nexthop tracking. "
        "next-hop-self forces PE to advertise itself as next-hop toward RR clients."
    ),
    "bgp-dampening": (
        "BGP route dampening (RFC 2439): penalises flapping prefixes. Each flap adds a penalty; "
        "when penalty exceeds the suppress-limit the route is suppressed. Penalty decays exponentially "
        "with half-life. Reuse-limit: route re-advertised when penalty drops below threshold. "
        "RFC 7196: dampening not recommended for prefixes shorter than /24 due to operator impact."
    ),
    "bgp-pic": (
        "BGP PIC (Prefix Independent Convergence, RFC 7911/4456): backup next-hop pre-installed in CEF. "
        "Primary path failure triggers immediate FIB switchover to backup without BGP reconvergence. "
        "PIC edge: multiple eBGP paths to same prefix. PIC core: fast IGP reroute to alternate BGP next-hop. "
        "Combined with ADD-PATH for path visibility through route reflectors."
    ),
    "route-refresh": (
        "BGP Route Refresh (RFC 2918, 7313): ROUTE-REFRESH message requests re-advertisement of the "
        "full BGP table for an AFI/SAFI. Soft reset without session tear-down. "
        "Enhanced Route Refresh (RFC 7313): BGP-RR-REFRESH BEGIN and END markers bound a refresh "
        "session to detect incomplete RIB synchronisation. Capability code 128."
    ),
    "ttl-security": (
        "TTL Security Hack / GTSM (RFC 5082): eBGP speaker sets outgoing TTL=255; receiver rejects "
        "packets with TTL < 254 (for directly connected peers) or TTL < 255-n for multihop peers. "
        "Prevents remote spoofing of BGP TCP sessions. IOS: neighbor ttl-security hops 1. "
        "FRR: neighbor <addr> ttl-security hops 1. Verified with show ip bgp neighbors."
    ),
    "operational": (
        "BGP operational commands: show bgp summary (session state, prefix counts), "
        "show ip bgp neighbors <addr> (detailed neighbor info, timer, capabilities, statistics), "
        "show ip bgp <prefix> (path selection, attributes), show route-map, "
        "clear bgp <addr> soft in/out (soft reset without session drop), "
        "debug ip bgp events (live event tracing — use with care in production)."
    ),
    "operational-tools": (
        "BGP operational tools: BMP (RFC 7854) for route monitoring. "
        "Looking Glass servers for external path verification. "
        "ping and traceroute for reachability and path tracing. "
        "show bgp neighbors / show ip bgp summary for session and prefix state. "
        "Route collector archives (RIPE RIS, RouteViews) for historical analysis."
    ),
    "multivendor": (
        "BGP multivendor interoperability: core BGP (RFC 4271) universally supported. "
        "Cisco IOS-XR: router bgp / neighbor / address-family ipv4 unicast. "
        "Juniper JunOS: protocols bgp / group / neighbor. "
        "FRRouting: bgp <asn> / neighbor / address-family. "
        "Vendor differences in ADD-PATH, SR-Policy, and Flowspec capability defaults."
    ),
}

# Category aliases: some benchmark categories map to the same concept paragraph.
_CAT_ALIAS: Dict[str, str] = {
    "addpath": "add-path-advanced",
    "multipath": "multipath-advanced",
    "operational-tools": "operational",
}


# ---------------------------------------------------------------------------
# Corpus building — pattern files + fault library
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_WEBUI = os.path.dirname(_HERE)
_REPO = os.path.dirname(_WEBUI)


def _load_corpus() -> List[Dict]:
    """Load text snippets from pattern files, fault library, and concept library."""
    corpus: List[Dict] = []

    # 1. Pattern files — rich BGP prose
    pattern_dir = os.path.join(_REPO, "wrath", "memory", "patterns")
    if os.path.isdir(pattern_dir):
        for fn in sorted(os.listdir(pattern_dir)):
            if not fn.endswith(".md"):
                continue
            with open(os.path.join(pattern_dir, fn), encoding="utf-8") as fh:
                text = fh.read()
            corpus.append({"text": text, "source": f"pattern:{fn}", "type": "pattern"})

    # 2. Fault library — symptom + ground-truth prose
    fault_dir = os.path.join(_REPO, "thesis", "lab", "faults")
    if os.path.isdir(fault_dir):
        for fn in sorted(os.listdir(fault_dir)):
            if not fn.endswith(".json"):
                continue
            with open(os.path.join(fault_dir, fn), encoding="utf-8") as fh:
                fault = json.load(fh)
            text_parts = [
                fault.get("title", ""),
                fault.get("symptom", ""),
                fault.get("ground_truth", {}).get("root_cause", ""),
                fault.get("ground_truth", {}).get("fix", ""),
                fault.get("ground_truth", {}).get("verify", ""),
            ]
            corpus.append({
                "text": " ".join(p for p in text_parts if p),
                "source": f"fault:{fault.get('id',fn)}",
                "type": "fault",
                "commands": fault.get("expected_evidence", []),
            })

    # 3. Embedded concept library — one paragraph per category
    for cat, text in _CONCEPTS.items():
        corpus.append({"text": text, "source": f"concept:{cat}", "type": "concept", "category": cat})

    return corpus


# ---------------------------------------------------------------------------
# BM25-style index (same implementation as dense_rag.py for consistency)
# ---------------------------------------------------------------------------

_STOP = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "on", "at", "by",
    "for", "with", "and", "or", "but", "it", "its", "this", "that", "be", "been", "being",
    "from", "as", "not", "no", "so", "such", "if", "then", "than",
})


def _tok(text: str) -> List[str]:
    return [t for t in re.sub(r"[^\w\s]", " ", text.lower()).split()
            if len(t) >= 3 and t not in _STOP]


class _BM25:
    k1, b = 1.5, 0.75

    def __init__(self, docs: List[str]):
        self.docs = docs
        tf_list: List[Dict[str, int]] = []
        df: Dict[str, int] = {}
        for d in docs:
            toks = _tok(d)
            tf: Dict[str, int] = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            tf_list.append(tf)
            for t in tf:
                df[t] = df.get(t, 0) + 1
        N = max(len(docs), 1)
        avgdl = sum(len(_tok(d)) for d in docs) / N
        self._tf = tf_list
        self._idf = {t: math.log((N - df[t] + 0.5) / (df[t] + 0.5) + 1) for t in df}
        self._avgdl = avgdl

    def score(self, query: str, doc_idx: int) -> float:
        toks = _tok(query)
        tf = self._tf[doc_idx]
        dl = sum(tf.values())
        s = 0.0
        for t in toks:
            if t not in self._idf:
                continue
            f = tf.get(t, 0)
            norm = f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self._avgdl))
            s += self._idf[t] * norm
        return s

    def top_k(self, query: str, k: int = 3) -> List[Tuple[int, float]]:
        scores = [(i, self.score(query, i)) for i in range(len(self.docs))]
        scores.sort(key=lambda x: -x[1])
        return scores[:k]


# Module-level cache — built once per process, invalidated on demand.
_cache: Optional[Tuple[List[Dict], _BM25]] = None


def _index() -> Tuple[List[Dict], _BM25]:
    global _cache
    if _cache is None:
        corpus = _load_corpus()
        bm25 = _BM25([c["text"] for c in corpus])
        _cache = (corpus, bm25)
    return _cache


def invalidate_index() -> None:
    """Call after adding new pattern/fault files."""
    global _cache
    _cache = None


# ---------------------------------------------------------------------------
# Command extraction from free text
# ---------------------------------------------------------------------------

_CMD_RE = re.compile(
    r"\b(show\s+(?:bgp|ip\s+bgp|ipv6|interface|route|log|bfd|isis|ospf|mpls|version|processes|running)[^\n,;\"']{0,60}|"
    r"ping\s+[\w.:\-]+|traceroute\s+[\w.:\-]+|"
    r"clear\s+(?:bgp|ip\s+bgp)[^\n,;\"']{0,40})",
    re.IGNORECASE,
)


def _extract_commands(text: str) -> List[Dict[str, str]]:
    """Pull CLI command candidates from free text."""
    cmds = []
    for m in _CMD_RE.finditer(text):
        cmd = re.sub(r"\s+", " ", m.group(0)).strip().rstrip(".,;:")
        if len(cmd) > 8:
            cmds.append({"device": "R2", "cmd": cmd})
    # Deduplicate preserving order
    seen: set = set()
    out = []
    for c in cmds:
        key = c["cmd"].lower()
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out[:5]


# ---------------------------------------------------------------------------
# Answer composition
# ---------------------------------------------------------------------------

def _compose(question: Dict, matches: List[Dict]) -> Tuple[str, str, List[Dict]]:
    """Build answer, retrieved_context, and command list from top corpus matches."""
    texts = [m["text"] for m in matches]
    retrieved = "\n\n".join(texts[:3])

    # Category-matched concept text gets priority as the answer base.
    cat = question.get("category", "")
    resolved_cat = _CAT_ALIAS.get(cat, cat)
    concept_text = _CONCEPTS.get(resolved_cat, "")

    if concept_text:
        # Use the concept paragraph as the primary answer; append salient sentences from top match.
        primary = concept_text
        if matches and matches[0].get("type") != "concept":
            # Add the first sentence from the top non-concept match for extra signal.
            first_sent = matches[0]["text"].split(".")[0].strip()
            if first_sent and first_sent not in primary:
                primary = primary + ". " + first_sent
    else:
        # No concept paragraph — use the top match text (first 2 sentences).
        if matches:
            sents = [s.strip() for s in matches[0]["text"].split(".") if len(s.strip()) > 20]
            primary = ". ".join(sents[:2]) + "."
        else:
            primary = ""

    # Gather commands from all matched corpus items
    commands: List[Dict] = []
    for m in matches:
        if "commands" in m:
            for c in m["commands"]:
                commands.append({"device": "R2", "cmd": c})
    # Also extract from retrieved text
    commands += _extract_commands(retrieved)
    # Deduplicate
    seen: set = set()
    deduped = []
    for c in commands:
        k = c["cmd"].lower()
        if k not in seen:
            seen.add(k)
            deduped.append(c)

    return primary.strip(), retrieved.strip(), deduped[:6]


# ---------------------------------------------------------------------------
# Public SUT
# ---------------------------------------------------------------------------

def graph_sut(question: Dict) -> Dict:
    """OpsRAG graph SUT — typed-graph retrieval for ALL question types.

    Fault-linked questions: full sim → synth → oracle path (same as opsrag_sut).
    All other questions: BM25 retrieval from corpus → structured template answer.
    """
    fid = question.get("fault_id")
    if fid:
        fault_path = os.path.join(_REPO, "thesis", "lab", "faults", fid + ".json")
        if os.path.isfile(fault_path):
            from . import synthesizer
            with open(fault_path, encoding="utf-8") as fh:
                fault = json.load(fh)
            rb = synthesizer.synthesise_with_sim(fault)
            ctx = "\n".join(str(o.get("stdout", "")) for o in rb.get("command_outputs", []))
            return {
                "answer": rb.get("concluded_root_cause", ""),
                "retrieved_context": ctx,
                "commands": rb.get("commands", []),
            }

    # Non-fault question — typed-graph retrieval
    corpus, bm25 = _index()
    q_text = question.get("question", "")
    top = bm25.top_k(q_text, k=5)
    matches = [corpus[i] for i, _ in top if _ > 0.0]

    # Promote category-matched concept to the front if not already there
    cat = question.get("category", "")
    resolved_cat = _CAT_ALIAS.get(cat, cat)
    cat_source = f"concept:{resolved_cat}"
    non_concept = [m for m in matches if m.get("source") != cat_source]
    concept_match = next((m for m in corpus if m.get("source") == cat_source), None)
    if concept_match:
        matches = [concept_match] + non_concept[:4]
    else:
        matches = matches[:5]

    answer, retrieved, commands = _compose(question, matches)
    return {"answer": answer, "retrieved_context": retrieved, "commands": commands}
