#!/usr/bin/env python3
"""WRATH clarifying-questions gate (P0 — the biggest single quality lever).

Before any design is attempted, Discovery must ask the *right* missing questions instead of
assuming (House Rule 7). This module detects which architecture-critical dimensions the problem
statement already pins down and which are still unknown, and turns each gap into a specific,
answerable question. A problem with an unanswered *blocking* dimension is **not ready for design**.

Deterministic and dependency-free, so it is fully testable without an API key (see
webui/test_clarify.py). The same dimension set is documented for humans in
.claude/skills/requirements-intake/references/clarifying-questions.md — keep the two in sync.

    python webui/clarify.py "design me a campus network"   # prints the gate analysis
"""
import re
import sys

# Each dimension: a label, whether a missing answer BLOCKS design, the regex signals that count as
# "the problem already says this", and the canonical question to ask when it is missing.
DIMENSIONS = [
    {"id": "deployment", "label": "Greenfield vs brownfield", "blocking": True,
     "signals": [r"brownfield", r"greenfield", r"existing", r"migrat", r"new build",
                 r"day[\s-]?0", r"\breplace", r"\bupgrade", r"current\b", r"legacy"],
     "question": "Is this greenfield or brownfield? If brownfield, a per-step rollback and migration "
                 "plan are mandatory (House Rule 3)."},
    {"id": "scale", "label": "Scale & growth", "blocking": True,
     "signals": [r"\b\d+[\s-]*(sites?|nodes?|routers?|devices?|pe|ce|users?|prefixes?|routes?)",
                 r"\b\d+\s*(k|m)?\s*(g|gb|gbps|tbps|t)\b",
                 r"scale", r"throughput", r"bandwidth", r"capacity", r"growth"],
     "question": "What is the scale — device/site count, route/prefix scale, today's and 3-year "
                 "traffic volumes, and growth assumptions?"},
    {"id": "resilience", "label": "SLA / SLO targets", "blocking": True,
     "signals": [r"\bsla\b", r"\bslo\b", r"availab", r"\d+\s*nines", r"99\.", r"five nines",
                 r"convergence", r"\brto\b", r"\brpo\b", r"uptime", r"latency", r"jitter"],
     "question": "What are the SLA/SLO targets — availability, convergence (end-to-end vs IGP-only, "
                 "and is it contractual?), latency/jitter?"},
    {"id": "platform", "label": "Vendor / platform / version", "blocking": True,
     "signals": [r"ios[\s-]?xr", r"ios[\s-]?xe", r"nx[\s-]?os", r"junos", r"cisco", r"juniper",
                 r"arista", r"nokia", r"\basr\b", r"\bncs\b", r"catalyst", r"nexus", r"\bsros\b",
                 r"\bversion\b", r"\brelease\b"],
     "question": "Which vendor(s), platforms and software versions are in play or mandated? This "
                 "drives feature availability and EoL checks."},
    {"id": "security", "label": "Security & compliance baseline", "blocking": False,
     "signals": [r"security", r"\bpci\b", r"hipaa", r"\bnist\b", r"\bcis\b", r"segmentation",
                 r"encrypt", r"zero[\s-]?trust", r"firewall", r"macsec", r"ipsec", r"compliance"],
     "question": "What security/compliance baseline applies (NIST/CIS/PCI/customer policy), and what "
                 "segmentation/encryption is required?"},
    {"id": "timeline", "label": "Timeline, change windows & budget", "blocking": False,
     "signals": [r"timeline", r"deadline", r"budget", r"\bcost\b", r"maintenance window",
                 r"change window", r"\bq[1-4]\b", r"\b\d+\s*(week|month|day)", r"by\s+\w+\s+\d{4}"],
     "question": "What is the timeline, are there fixed change/maintenance windows, and is there a "
                 "budget envelope?"},
    {"id": "services", "label": "Services & traffic profile", "blocking": False,
     "signals": [r"l3vpn", r"l2vpn", r"evpn", r"vxlan", r"multicast", r"voice", r"\bqos\b",
                 r"internet", r"peering", r"\bvpn\b", r"sd[\s-]?wan", r"\bservices?\b"],
     "question": "What services and traffic profiles must this carry (L2/L3VPN, multicast, voice/QoS, "
                 "internet/peering)?"},
]


def analyze(problem):
    """Return the gate analysis for a problem statement.

    {present:[id], missing:[{id,label,question,blocking}], blocking:[id], ready:bool}
    `ready` is False whenever any *blocking* dimension is unanswered — design must not start.
    """
    p = (problem or "").lower()
    present, missing = [], []
    for d in DIMENSIONS:
        hit = any(re.search(s, p) for s in d["signals"])
        (present if hit else missing).append(d)
    missing_q = [{"id": d["id"], "label": d["label"], "question": d["question"],
                  "blocking": d["blocking"]} for d in missing]
    return {
        "present": [d["id"] for d in present],
        "missing": missing_q,
        "blocking": [m["id"] for m in missing_q if m["blocking"]],
        "ready": not any(m["blocking"] for m in missing_q),
    }


def render_brief(problem, a):
    """Markdown for the Discovery stage output (demo mode / no-key)."""
    have = ", ".join(a["present"]) or "—"
    out = [f"**Problem (restated):** {problem}", "",
           f"**Dimensions already specified:** {have}", ""]
    blocking = [m for m in a["missing"] if m["blocking"]]
    soft = [m for m in a["missing"] if not m["blocking"]]
    if blocking:
        out.append("**⛔ Must answer before design (architecture-critical — House Rule 7):**")
        for i, m in enumerate(blocking, 1):
            out.append(f"{i}. _{m['label']}_ — {m['question']}")
        out.append("")
    if soft:
        out.append("**Should clarify (improves the design, not blocking):**")
        for m in soft:
            out.append(f"- _{m['label']}_ — {m['question']}")
        out.append("")
    out.append("**Gate:** " + ("✅ ready for design — no architecture-critical gaps."
                               if a["ready"] else
                               "🔒 NOT ready for design — resolve the blocking questions with Kamal first."))
    return "\n".join(out)


def live_extra(a):
    """Instruction appended to the Live-mode Discovery prompt so the real agent asks these."""
    if a["ready"]:
        return ("All architecture-critical dimensions appear specified; confirm them and list any "
                "remaining detail questions.")
    qs = "; ".join(m["question"] for m in a["missing"] if m["blocking"])
    return ("These architecture-critical dimensions are NOT specified — you MUST ask, not assume "
            f"(House Rule 7), and mark the brief NOT ready for design until answered: {qs}")


def main(argv):
    problem = " ".join(argv[1:]).strip() or "design me a network"
    a = analyze(problem)
    print(render_brief(problem, a))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
