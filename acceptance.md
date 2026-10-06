# F2.11 Acceptance Criteria

## Goal

Every user-facing claim about what the converter does must be verifiable
against the repository: the README describes the real output and points
at the tests that prove it, and the unverified success narratives are
gone. The stale v1-era output examples no longer show resource types
the converter does not emit.

## Verifiable checks

1. `docs/VERSION_4.0_COMPLETE_COVERAGE.md` is deleted. Its claims
   ("100% success rate", "95%+ coverage", "133,000-line production
   tested", "Production Ready") have no test evidence in the
   repository.
2. `README.md` "Typical outputs" matches the real converter output
   (verify against `tests/golden/kitchen_sink/`: `decryption_rules.tf`,
   `pbf_rules.tf`, and `monitor_profiles.tf` are present).
3. `README.md` coverage and validity claims reference the tests that
   prove them: the coverage matrix row (`tests/test_coverage_matrix.py`),
   the validate gate (`tests/test_terraform_validate.py`), and the
   no-dangling-reference rule (`tests/test_dependency_wiring.py`).
4. No user-facing doc presents a resource type the panos provider does
   not have as converter output: `panos_bgp`, `panos_bgp_peer`,
   `panos_ospf`, `panos_static_route_ipv4`, and
   `panos_security_rule_group` are absent from `docs/` and `examples/`
   (except the report-only table in RESOURCE_MAPPING.md, where they are
   named as captured data with no v2 target), and v1
   `panos_address_object` / `panos_service_object` appear only in the
   "Renamed from" column of that table.
5. `examples/example_terraform_output.txt` points at the canonical
   sample output (`tests/golden/sample/`, byte-gated by
   `tests/test_golden_files.py`) instead of showing a fabricated v1
   output.
6. `docs/ADVANCED-ROUTING-ENGINE-SUPPORT.md` states the real behavior:
   both virtual and logical routers parse and emit as
   `panos_virtual_router`, static routes as
   `panos_virtual_router_static_route_ipv4`, BGP/OSPF are report-only.
   No "Production Ready" status, no invented version numbers.
7. `docs/QUICK_REFERENCE.txt` is deleted. It claims zones, VPN,
   interfaces, and virtual routers are unsupported, which contradicts
   the converter, and only the docs removed or rewritten by this task
   reference it.
8. No dead doc references remain (grep for the removed file names).
9. `backlog.md` drops the stale-narrative-docs item (completed here).
10. Gate: `ruff check .` clean; `pytest` green.
