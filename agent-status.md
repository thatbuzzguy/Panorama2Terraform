# Agent Status

## Current position
Epic 2 (complete provider-v2 support). F2.1–F2.3 complete. Next: **F2.4 Rewrite emitters to the v2 schemas**.

## Session log

### F2.3 — location on every resource (this session)
- v2.0.14 schema fact (corrected from earlier notes): `location` is a
  required nested BLOCK, and the allowed sub-blocks differ per type.
  Objects/rules take `device_group`; zones, VRs, static routes,
  interfaces, VPN resources take `template` (plus ngfw/vsys variants).
- Parser: `PanoramaParser._parent_map` (ElementTree has no parent
  pointers) + `device_group_of(elem)`; 12 parse methods now record
  `device_group` on each object (Shared for shared/top-level entries).
- Generator: `location_block(resource_type, device_group)` helper +
  `_TEMPLATE_SCOPED_TYPES` set; inserted as the first attribute of all
  29 emission points (13 types). DG-scoped resources use the object's
  defining DG; template-scoped ones use `template { name = "Shared" }`
  (exact template tracking is F2.4).
- New green test: every golden resource block carries `location`.
- Goldens regenerated (24 .tf files changed; provider/variables intact).
- Conformance shift as designed: test 2 xpasses for all 13 existing
  types (was xfailed). Suite: 136 passed, 33 xfailed, 26 xpassed.

### F2.2 — Resource mapping (this session)
- Ground truth verified against the live v2.0.14 schema (128 types):
  15 of the 28 emitted types are missing from v2, 13 exist. The audit's
  "13 missing" list omitted `panos_application_filter` and
  `panos_external_list`; the F1.4 test split (15 type-XFAIL / 13
  type-XPASS) confirms 15. Docs corrected.
- `resource_mapping.py` (repo root): `RESOURCE_MAPPING` dict, old type ->
  v2 type, or None for report-only. 13 identity, 7 renames
  (panos_address, panos_service, panos_virtual_router_static_route_ipv4,
  panos_security_policy_rules, panos_nat_policy_rules,
  panos_external_dynamic_list, panos_ethernet_layer3_subinterface), 1
  merge (proxy-id into `panos_ipsec_tunnel.auto_key.proxy_id`), 7
  report-only (application_filter, bgp x3, ospf x3).
- `docs/RESOURCE_MAPPING.md`: rationale table for F2.4.
- `tests/test_resource_mapping.py` (29 tests, all green): mapping keys ==
  emitted types from goldens; every target exists in the schema; every
  report-only entry is genuinely absent.
- Refactor: `provider_schema` fixture + `declared_provider()` +
  `emitted_types()` moved to conftest.py; test_schema_conformance.py uses
  them (same split: 43 xfail, 13 xpass).
- Corrected a wrong note: `location` is a required nested BLOCK (e.g.
  `location { device_group { name } }`), not a string. F2.3 must emit
  blocks.
- Gate: ruff clean. pytest 135 passed, 46 xfailed, 13 xpassed.

### F2.1 — Provider baseline (this session)
- The registry's latest 2.x release is 2.0.14 (verified via the registry
  versions API; it is also the audit's reference version). The old pin
  `~> 2.0.7` predates six 2.0.x releases.
- `generate_provider_config` now emits `~> 2.0.14` with a comment
  recording 2.0.14 as the verified v2 baseline.
- Goldens regenerated (sample + kitchen-sink). Only `provider.tf`
  changed in each set, as expected.
- README current-support line updated to 2.0.14; the v4.0.0 changelog
  entry stays historical.
- Verified `terraform init` resolves the pin to exactly v2.0.14
  (signed install). The F1.4 conformance and F1.5 validate gates run
  against that version. Same split: 43 xfailed, 13 xpassed.
- Gate: ruff clean. pytest 106 passed, 46 xfailed, 13 xpassed.

### F1.7 — Security and robustness (this session)
- Added `tests/test_robustness.py` (10 tests, all green) plus six fixtures
  under `tests/fixtures/`: hostile_billion_laughs, hostile_xxe,
  hostile_bad_control_char (raw 0x01 byte), robust_tab_cr_names
  (names carry `&#9;`/`&#13;` char refs that survive attribute
  normalization), robust_empty_names, robust_name_collisions.
- Found: ElementTree resolves internal DTD entities, so a deep entity
  chain is a memory DoS. Fix (in both scripts): reject any input
  containing `<!DOCTYPE` before parsing. Panorama exports never carry a
  DTD, so this is safe.
- Fix: `escape_string` now escapes `\t` and `\r` and strips remaining C0
  control characters and DEL, so generated .tf files never carry raw
  control bytes (invalid HCL).
- Fix: sanitization collisions. `a-b`, `a_b`, `A-B` all sanitized to
  `a_b`, emitting duplicate resource addresses (invalid HCL). New
  `TerraformGenerator.unique_resource_name(name, scope)` registry assigns
  per-type collision-free names (`a_b`, `a_b_2`, `a_b_3`) and is stable
  for repeated input, so cross-resource references (which recompute the
  same input string) resolve to the same name. Migrated all 34 call
  sites with per-resource-type scopes.
- Fix: `main()` catches `ValueError` (DTD rejection) with a clean message.
  Hostile input now exits non-zero with no traceback.
- Goldens byte-identical (no collisions in sample/kitchen-sink).
- Gate: ruff clean. pytest 106 passed, 46 xfailed, 13 xpassed.

### Epic 1 summary (complete; detail in git history)
- F1.1/F1.8 tooling + lint gate (ruff, pytest, CI matrix, pre-commit).
- F1.2 parser unit tests: 42 tests, 34 fixtures; 5 parser bugs fixed.
- F1.3 golden-file tests: sample + kitchen-sink (29 .tf), 39 tests.
- F1.4 schema conformance: 56 cases; 43 xfailed (15 types missing from
  provider v2, missing `location`), 13 xpassed (the 13 types that exist).
- F1.5 CI terraform gate: init green, validate xfail until Epic 2.
- F1.6 edge corpus: 6 fixtures, 12 tests; splitter quote bug fixed.

## Environment notes
- Python 3.12.3; use `uvx --with pytest==9.1.1 pytest` and
  `uvx --with ruff==0.16.10 ruff` (PEP 668 blocks system pip installs).
- terraform 1.16.1 available at /usr/bin/terraform.
- Converter CLI: `python3 panorama_to_terraform.py <input.xml> [--output-dir DIR]`
  (output dir is a flag, default `terraform_output`).
- Splitter CLI: `python3 split_device_groups.py <input.xml> [--output-dir DIR]`.
- Provider v2 schema (128 types) was fetched to /tmp/panos_schema.json in a
  previous session; refetch with `terraform providers schema -json` if needed.
- 15 emitted types are missing from v2 (F2.2 mapping targets). `location`
  is a required nested block (e.g. `location { device_group { name } }` or
  `location { template { name } }`), not a plain string (verified in the
  v2.0.14 schema; the earlier "string attribute" note was wrong).

## Conventions
- One task at a time; `acceptance.md` overwritten before each task.
- ASD-STE100 in commits and docs.
- Red→green: failing checks are xfail(strict=False) with the fixing
  Epic's task reference; flip them to plain asserts when the epic lands.
- Commit per feature; completed items leave markdown when the epic completes.
