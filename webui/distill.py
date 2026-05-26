#!/usr/bin/env python3
"""WRATH self-improving pattern library — distil an accepted run into reusable memory (★ signature).

This closes the compounding-memory loop (House Rule 8): when Kamal accepts a converged run, it is
distilled into a customer-agnostic *pattern* (transport/service/resilience/security shape + grounded
references) written to wrath/memory/patterns/. The next similar problem then recalls it via Memory RAG
— so the system gets better with every engagement instead of solving from scratch.

distil() is pure + deterministic (no LLM/key) and is tested in webui/test_distill.py. The file *write*
lives in the /api/distill endpoint so tests never touch the repo.

    distil(rec) -> {slug, title, tags, refs, markdown}
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recall  # noqa: E402

TRANSPORTS = ["sr-mpls", "srv6", "evpn", "vxlan", "sd-wan", "mpls"]
SERVICES = ["l3vpn", "l2vpn", "multicast"]
CONTEXTS = ["data center", "datacenter", "dci", "campus", "wan", "core"]


def _first(cands, tags, exclude=None):
    for x in cands:
        if x in tags and x != exclude:
            return x
    return None


def _title(tags, problem):
    t = _first(TRANSPORTS, tags)
    s = _first(SERVICES, tags)
    c = _first(CONTEXTS, tags, exclude=t)
    parts = []
    if t:
        parts.append(t.upper())
    if c:
        parts.append(c)
    base = " ".join(parts) if parts else (problem[:46].strip() or "network design")
    title = "Pattern — " + base
    if s:
        title += " with " + s.upper()
    return title


def slugify(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower().replace("pattern —", "")).strip("-")
    return (s or "pattern")[:60]


def _verified_refs(rec):
    refs = set()
    for _sid, g in (rec.get("grounding") or {}).items():
        for c in g.get("checks", []):
            if c.get("verdict") == "verified" and str(c.get("item", "")).upper().startswith("RFC"):
                refs.add((c["item"], c.get("note", ""), c.get("url", "")))
    return sorted(refs)


def distil(rec):
    problem = rec.get("problem", "")
    tags = sorted(recall.terms(problem))
    title = _title(tags, problem)
    slug = slugify(title)
    refs = _verified_refs(rec)
    trust = rec.get("trust") or {}
    transport = _first(TRANSPORTS, tags)
    service = _first(SERVICES, tags)
    context = _first(CONTEXTS, tags, exclude=transport)

    fits = (f"A {context or 'multi-site'} design"
            + (f" using {transport.upper()}" if transport else "")
            + (f", delivering {service.upper()}" if service else "")
            + ". Reuse the shape below; adapt to the customer's scale and conventions (House Rule 4).")

    shape = []
    if transport:
        shape.append(f"- **Transport:** {transport.upper()} — one fabric-wide plan (SRGB/label or VNI); "
                     "protection via TI-LFA/FRR — **state the BFD-in-HW dependency**.")
    if service:
        shape.append(f"- **Service:** {service.upper()} — RD/RT plan with no overlaps; documented.")
    shape.append("- **Resilience:** redundant core / route-reflectors with distinct cluster-IDs; "
                 "validate convergence under each modeled failure.")
    shape.append("- **Security in:** segmentation + control-/mgmt-plane hardening + encryption where "
                 "required (House Rule 5).")

    L = [f"# {title}", "",
         "*Semantic memory (House Rule 8): reusable, customer-agnostic. Distilled automatically from an "
         "accepted WRATH run — always adapt to the customer's conventions and ground platform specifics "
         "(House Rule 4).*", "",
         "## When this fits", fits, "",
         "## The shape", *shape, "",
         "## Grounded references"]
    if refs:
        L += [f"- {item} — {note}" + (f" ({url})" if url else "") for item, note, url in refs]
    else:
        L.append("- _none captured in this run; verify and add before relying on standards claims._")
    L += ["", "## Provenance",
          f"- Distilled from run `{rec.get('id', '?')}` ({rec.get('ts', '')}); "
          f"trust at distillation: **{trust.get('confidence', 'n/a')}**.",
          f"- Signals: {', '.join(tags) if tags else '—'}"]

    return {"slug": slug, "title": title, "tags": tags, "refs": refs, "markdown": "\n".join(L)}


if __name__ == "__main__":
    import json
    MEM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wrath", "memory", "runs")
    if len(sys.argv) < 2:
        print("usage: distill.py <run-id>", file=sys.stderr)
        sys.exit(2)
    rec = json.load(open(os.path.join(MEM, sys.argv[1] + ".json")))
    print(distil(rec)["markdown"])
