# Deliverables

Where WRATH run outputs land — versioned (charter §5: "version every design, config, runbook").
Scratch goes under `deliverables/_scratch/` (gitignored); everything else is tracked.

## Worked examples
- **`example-acme-sp/`** — an SP-core engagement (SR-MPLS / BGP-L3VPN, **IOS-XR**) threaded through
  **every phase**, with connected artifacts (the LLD's addressing shows up in the config; the validator
  runs on that config; the BoM quantities trace to the design). The reference for each deliverable's shape.
- **`example-dc-evpn/`** — a data-center fabric engagement (**EVPN-VXLAN, NX-OS**) — a different domain
  and vendor, to show breadth: the LLD's VNI/IPAM plan realizes in the leaf config, which passes the
  `config_lint` audit gate (`--vendor nxos`, 0 findings) and is checked on every `run_tests.sh`.
