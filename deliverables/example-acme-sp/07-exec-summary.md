# Executive Summary — Acme SP core modernization (one page)

*Phase: Sell. Skill: `exec-deck`. Agent: `exec-storyteller`. Status: worked example.*

## Why this matters (three sentences)
1. Today Acme's core runs two aging protocols whose complexity is a recurring source of outage risk and slows every customer change.
2. Modernizing to a single, traffic-engineered core makes link and node failures self-heal before customers notice, and cuts the time to turn up a new business-VPN customer.
3. The decision now: approve the design and the phased, zero-downtime migration.

## The business outcome
- **Resilience:** a single failure becomes invisible instead of an outage — protecting the SLA Acme sells.
- **Agility:** simpler core = faster, lower-risk customer turn-ups (the L3VPN service revenue engine).
- **Cost trajectory:** one protocol to operate instead of two; 100G-ready platforms remove the next forklift.

## The approach (one line + one picture)
Replace LDP+RSVP-TE with **Segment Routing (SR-MPLS)** carrying **BGP L3VPN**, multi-vendor, migrated
one site at a time with a rollback at every step. (Architecture: `01-hld.md` topology.)

## Cost & risk (honest)
- **Investment:** 5 routers + redundant route reflectors + 100G optics + license/support (see BoM; figures to be finalized with Acme's contract terms).
- **Risk named:** the sub-50ms self-heal depends on specific linecard hardware — **verified during design validation before it's promised in the SLA**. Migration risk is bounded by per-site phasing with tested rollback.

## The ask
Approve the HLD + migration plan to proceed to build and the first (lowest-risk) site cutover.
