# Reusable SoW clauses — reference for the SoW Writer

Proven clause patterns to adapt (not paste blindly). Tune to the engagement and the customer's MSA.

## Assumptions (common, adapt)
- Customer provides timely access to devices, jump hosts, credentials, and the change-management window.
- Existing documentation (topology, addressing, configs) is accurate and current as provided.
- Maintenance windows are available as scheduled; customer resources attend go/no-go gates.
- Third-party/carrier dependencies (circuits, DNS, licensing portals) are delivered by the customer.
- Pricing assumes the BoM quantities and license tiers as quoted; changes re-scope.

## Exclusions (common, adapt — be specific)
- Hardware/optics/licenses not listed in the BoM.
- Application, server, or endpoint changes; anything above L3 unless named.
- Physical cabling, power, rack, and environmental work.
- Remediation of pre-existing faults discovered during the engagement (raised as a change).
- 24×7 standby beyond the named maintenance windows; out-of-scope sites.
- Data migration, security audit, or compliance certification unless explicitly in scope.

## Acceptance criteria (objective patterns)
- All configured BGP/IGP adjacencies **Established/Up** and expected prefixes present on each node.
- Service reachability test matrix passes (named source→dest flows, with results recorded).
- Failover test: on link/node failure, convergence within the agreed target; traffic restored.
- Telemetry/assurance dashboards show the agreed KPIs reporting.
- Zero P1/P2 defects open against the delivered scope at sign-off.

## RACI shape
| Deliverable | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| LLD sign-off | FABRIC team | **Customer net lead** | Security | PMO |
| Cutover execution | Joint | **Customer change mgr** | NOC | Exec sponsor |
Exactly one **Accountable** per row.

## Change control
Any change to scope, BoM, or timeline is handled via written change request; effort and price are
re-estimated before work proceeds. No verbal scope changes.
