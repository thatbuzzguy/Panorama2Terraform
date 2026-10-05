# Agent Status

## Current position
**F2.9 Real resources or explicit reports landed 2026-10-04** (worked
before F4.1 per direction). Decryption, PBF, and PBF path monitoring
profiles now emit as real v2.0.14 resources with the full parsed body;
app override, QoS, IPsec tunnel monitor, log forwarding, zone
protection, and schedules go to `MANUAL_SETUP_REPORT.txt` with their
captured data and the reason. Every comment-only `.tf` generator is
gone; `resource_mapping.py` carries `NOT_EMITTED_TYPES` (v2 exists, body
not parsed) with an existence guard. `to-do.md` points at **F4.1
Post-run sanity gate** as the next task; Epic 2 keeps F2.10 and F2.11.

## Session log

### F2.9 — Real resources or explicit reports (this session)
- Direction: work F2.9 now, not the F4.1 tracked in `to-do.md`.
  `acceptance.md` rewritten for it first.
- Emit-vs-report decision (verified against the v2.0.14 schema and
  provider/pango source):
  - EMIT: decryption rules (`panos_decryption_policy_rules`), PBF rules
    (`panos_pbf_policy_rules`), PBF path monitoring profiles
    (`panos_monitor_profile` — `network/profiles/monitor-profile`; the
    v2 resource is template-scoped and has no `description` attribute).
  - REPORT: app override rules, QoS profiles, IPsec tunnel monitor
    profiles (all three: no v2 resource — `panos_monitor_profile` is a
    different PAN-OS object, verified in
    `internal/provider/monitor_profile.go` and pango), log forwarding +
    zone protection (v2 exists, only name/description parsed), schedules
    (v2 exists, only entry names parsed; v2.0.14 has no monthly
    schedule support).
- Parser: `parse_decryption_rules` gains `device_group`, `log_start`,
  `log_end`; `parse_pbf_rules` gains `device_group`, `schedule`,
  `forward_to_vsys`, and the forward-action `monitor` block;
  new `parse_pbf_monitor_profiles()`.
- Generators: `generate_decryption_rules` and `generate_pbf_rules` reuse
  the F2.5 per-rule chain model (first rule `where = "last"`, later rules
  `where = "after"` + `directly = true` + pivot + `depends_on`). New
  `generate_pbf_monitor_profiles` writes `monitor_profiles.tf`.
  Deleted comment-only generators: app override, QoS, log settings, zone
  protection, tunnel monitor, schedules — all six areas now have report
  sections in `generate_manual_setup_report` (data + reason).
- **Decryption action mapping (caught by `terraform validate`):** the v2
  `action` is an enum (`no-decrypt`/`decrypt`/`decrypt-and-forward`) and
  the inspection mode is a `type { <key> = {} }` block. Modern exports
  pass through; legacy PAN-OS 9 exports put the mode in `action`
  (`ssl-forward-proxy`, `ssh-proxy`, `ssl-inbound-inspection`) and map
  to `action = "decrypt"` plus the matching `type` block; unknown values
  pass through so `terraform validate` fails loudly instead of
  misconfiguring silently.
- `resource_mapping.py`: +3 `EMITTED_TYPES`; +3 `REPORT_ONLY_TYPES`
  (`panos_application_override`, `panos_qos_profile`,
  `panos_tunnel_monitor_profile` — the name is deliberate: it must not
  exist in the schema, and it doesn't); new `NOT_EMITTED_TYPES` dict
  (type -> reason): `panos_log_forwarding_profile`,
  `panos_zone_protection_profile`, `panos_schedule`. `COVERAGE_MATRIX`
  +3 rows.
- Tests: new `tests/test_real_or_report.py` (emission chains + bodies,
  both monitor-profile action values, report sections, six removed
  `.tf` files, no-report early return); `test_resource_mapping.py`
  gains the `NOT_EMITTED_TYPES` existence guard (inverse of the
  report-only absence guard); parser tests updated.
- Fixtures: `decryption_rules.xml` gains a legacy-shape rule
  (action=ssh-proxy); `pbf_rules.xml` gains the full action set and a
  path-monitoring block; new `pbf_monitor_profiles.xml` (both action
  enum values); `kitchen_sink.xml` gains a monitor profile and a PBF
  monitor block.
- Goldens (kitchen sink): +`monitor_profiles.tf`, updated
  `decryption_rules.tf`/`pbf_rules.tf`, removed the six comment-only
  `.tf` files.
- Docs: `docs/RESOURCE_MAPPING.md` (status counts 23/10/2, per-rule
  policy section, monitor-profile row, +3 report-only rows, inverse
  guard), `README.md` (resource table, report-only section split into
  no-v2-resource and v2-exists-but-not-emitted).
- Gate: ruff clean. pytest 285 passed, 1 xfailed. `terraform validate`
  green on sample, kitchen sink, crypto-profile-only, decryption,
  PBF, and monitor-profile outputs.

### F2.8 — Coverage matrix (previous session)
- Direction: ignore the Epic 4 re-planning and finish the previously
  active task, F2.8. `acceptance.md` rewritten for it first.
- `COVERAGE_MATRIX` in `resource_mapping.py`: one row per
  `EMITTED_TYPES` type (20 rows). Row fields: `resource`,
  `xml_element` (Panorama tag path, any scope prefix), `xml_name`
  (fixture `<entry name>`), `emitted_name` (the `name` the output
  resource must carry; the `.0` subinterface row differs on purpose),
  `fixture`, `output_file`.
- `tests/test_coverage_matrix.py` (61 tests): (1) row set is exactly
  `EMITTED_TYPES` (drift guard both directions vs
  `REPORT_ONLY_TYPES`); (2) per row, the fixture exists and contains
  the row's element with the named entry; (3) per row, the CLI run on
  the fixture emits a `resource "<type>"` block in `output_file`
  carrying `name = "<emitted_name>"`. Per-fixture runs are cached per
  session; block end = first column-0 `}` line (nested values close on
  indented lines). pytest calls the `ids` callable once per parameter
  value, not on the list (first attempt failed at collection).
- **Bug found by the matrix and fixed:** `generate_vpn_config` (and its
  `main()` caller) gated `vpn.tf` on `ike_gateways or ipsec_tunnels`,
  so a config with only crypto profiles emitted nothing — inconsistent
  with the emit-everything-that-maps design. Gate relaxed to any
  non-empty VPN section; the key-management report stays gated on a
  gateway or tunnel. Verified valid standalone against v2.0.14.
- `tests/test_terraform_validate.py`: third case added —
  `ike_crypto_profiles.xml` (profiles only) must init + validate.
- Docs: `docs/COVERAGE_MATRIX.md` (matrix table, row schema, testing
  methodology, how the project verifies Terraform output, maintenance
  duty); README links it and its Testing section now states the
  canonical commands and the `terraform providers schema -json`
  schema source.
- Gate: ruff clean. pytest 260 passed, 1 xfailed (the F3.1 item).
  terraform validate green on sample, kitchen-sink, and the new
  crypto-profile-only output.

### Roadmap — Epic 4 planning (previous session)
- Added Goal 4 and Epic 4 to `PLAN.md`: F4.1 post-run sanity gate (`--validate` flag, static check module, `SANITY_REPORT.txt`, non-zero exit on FAIL), F4.2 container table + line-tracking `TreeBuilder`, F4.3 per-entry `CONVERSION_REPORT.txt` with consumed-entry marks, F4.4 property-level matrix.
- **F2.8 moved out of Epic 2 into Epic 4 as F4.4.** Rationale: the matrix becomes a live coverage structure with a permanent maintenance duty (not an end-of-Epic-2 measurement), and it must key on the F3.1 keyed data model, so it lands after F3.1.
- F2.10 stays in Epic 2 as the one-time dead-variable cleanup; its permanent check (every variable consumed) lands in F4.1.
- Sequencing: F4.1 is next (independent of the parser). F4.2 may land during Epic 3. F4.3/F4.4 after F3.1.
- Design decisions recorded in `backlog.md`: reports key on logical entries (line = opening tag), the matrix is a permanent duty with a drift-detecting test, and the known extraction gaps get fixed when the report confirms them.
- `acceptance.md` rewritten for F4.1; `to-do.md` now tracks F4.1 with its sub-tasks and a deferred list for Epics 2–4.

### F2.7 — Collision-safe naming (previous session)
- Design: the local name is the sanitized PAN-OS name plus an 8-hex
  sha256 digest of the object's source identity — the path of the entry
  in the export: resource type (scope), defining device group or
  template (context), and the raw name. The raw name is in the digest,
  not the sanitized one, so `a-b` and `a_b` (same base) stay apart
  deterministically. The digest makes the name independent of emission
  order and run count (the old `a_b_2` counter was order-dependent).
  Empty names get a stable `unnamed_<digest>`. A taken-address counter
  (`<name>_<digest>_2`) still guards true duplicates, so two resources
  never share an address.
- `name_ref` is unchanged: `(scope, name)` registry, first declaration
  wins, plain string for undeclared names. One improvement falls out for
  free: each raw name now resolves to its own resource (`name_ref('a_b')`
  no longer lands on the first-declared `a-b`), but a name that exists
  in two device groups still resolves first-wins (F3.1 context-keyed
  registry).
- Every declare site already passed the object's `device_group` or
  `template` as `context`, so the change is confined to
  `declare_resource_name` (plus `import hashlib`). No parser changes.
- Tests: `tests/test_robustness.py` collision test rewritten to the
  `base_<digest>` shape with per-raw-name reference resolution; new
  `test_declare_resource_name_is_order_independent` (two generators,
  opposite declaration orders, identical address sets),
  `test_declare_empty_name_gets_a_stable_name`; `test_name_ref_never_
  dangles` and the two-context test now assert the hashed shape.
  `tests/test_dependency_wiring.py` no longer hardcodes local names:
  all lookups resolve by the PAN-OS `name` attribute (`_local_of`,
  new `_iface_locals` helper), plus a new scheme-level test that every
  declared local name matches `[a-z0-9_]+_[0-9a-f]{8}(_\d+)?` and no
  address is declared twice.
- Goldens regenerated: 24 .tf files changed (sample 6, kitchen-sink 18),
  all within emitted resources and their references/depends_on; provider,
  variables, and reports unchanged except the `# Resource:` comment
  lines in security_profiles.tf.
- Docs: README gains a "Resource naming" section; backlog `name_ref`
  note updated (context now in the digest, first-wins resolution stays
  with F3.1); the F2.7 foundation note removed.
- Gate: ruff clean. pytest 198 passed, 1 xfailed (the F3.1 item).
  terraform validate green on sample, kitchen-sink, and the
  dependency-wiring output.

### F2.6 — Dependency wiring (previous session)
- Rule: emit a `.name` reference only when the target is declared in
  the same run; names pointing outside the export stay plain
  brown-field strings. The old `unique_resource_name` violated this:
  it declared a phantom resource for any referenced name (dangling
  reference, `terraform validate` failure). Removed; `name_ref(name,
  scopes, key=None)` replaces it — registry lookup only, plain string
  fallback, and `HclRef.__str__` returns the raw expression as a
  defense-in-depth measure.
- Wired sites: address-group `static`, address `tags`,
  service-group `members`, security rule zones/addresses/services,
  NAT rule zones/addresses/service and the dynamic-ip-and-port
  translation `interface`, zone `layer3` members, virtual-router
  `interfaces`, subinterface `parent` (both tagged and `.0` auto sites),
  IKE gateway `ike_crypto_profile` and `local_address.interface`,
  tunnel `ike_gateway` and `ipsec_crypto_profile`. Not wired: rule
  `applications` (built-in app names), profile-group members (profiles
  are report-only), zone-protection and interface-management
  (F3), `tunnel.interface`, comment-only emitters (decryption, PBF,
  app-override).
- Object scope wins over group scope on name collisions (scope tuples
  are ordered: `panos_address` before `panos_address_group`,
  `panos_service` before `panos_service_group`). Case-sensitive names
  keep the brown-field default (kitchen-sink tag "Web" does not match
  declared tag "web" — golden unchanged, correct).
- `main()` now emits `generate_ethernet_interfaces` before zones and
  virtual routers: `name_ref` resolves during emission, so declaration
  order matters.
- New fixture `tests/fixtures/dependency_wiring.xml` (collisions
  `both`/`svc-both`, ghost names, VPN chain + brown-field gateway) and
  `tests/test_dependency_wiring.py` (10 tests): mixed ref/plain lists
  per site, collision precedence, brown-field fallback, the
  no-phantom-gateway regression (exactly one `panos_ike_gateway`
  declared), a no-dangling-reference invariant scan over the whole
  output, and a terraform init+validate gate on that output.
- `tests/test_robustness.py`: collision test migrated to
  `declare_resource_name` + `name_ref`; new `test_name_ref_never_dangles`
  (a name declared in one scope is not reachable through another).
- Goldens regenerated: 10 .tf files changed, all within the wired
  emitters (sample: address_groups, service_groups, security_rules,
  nat_rules; kitchen-sink: address_groups, service_groups,
  security_rules, zones, virtual_routers, interfaces). VPN goldens
  unchanged (their refs were already wired).
- Docs: README gains a "Dependency wiring" section; backlog
  `unique_resource_name` notes updated to `name_ref`.
- Gate: ruff clean. pytest 195 passed, 1 xfailed (the F3.1 item).
  terraform validate green on sample, kitchen-sink, and the new
  dependency-wiring output.

### F2.5 — Order-preserving policy (previous session)
- Design (verified against provider v2.0.14 source and schema):
  `position.where` must be first/last/before/after; `after`/`before`
  require BOTH `pivot` (an existing rule name) and `directly` (bool),
  and the move fails when the pivot is missing. So a rule that pivots on
  a rule created in the same apply must also `depends_on` it.
- Keep the F2.4 one-resource-per-rule structure. Rules group into
  per-device-group chains in first-seen DG order, XML order within a
  chain (`_policy_rule_chains`). First rule of a chain: `position =
  { where = "last" }` (anchor: the managed block appends to the end of
  the rulebase, least disruptive for brown-field rulebases). Rule i > 1:
  `position = { where = "after", directly = true, pivot = <previous XML
  name> }` plus `depends_on = [<type>.<previous local name>]`
  (`_policy_position_block`). Same semantics for security and NAT rules.
- New fixture `tests/fixtures/policy_order.xml` (3 DGs: 3+2+1 security
  rules, 2 NAT rules) and `tests/test_policy_order.py` (8 tests):
  per-DG XML order, anchor semantics, after/directly/pivot chaining,
  exact depends_on, no cross-DG pivots or dependencies, NAT parity,
  and the same chain contract asserted on all four committed golden
  rule files.
- Goldens regenerated: only the four rule files changed (sample
  security 3-rule chain, sample nat 2-rule chain, kitchen-sink
  security 2-rule chain, kitchen-sink nat 2-rule chain). All other
  goldens byte-identical.
- Docs: README policy line corrected to the per-rule chain design;
  to-do/PLAN mark F2.5 complete; backlog notes the pre/post/shared
  rulebase tracking gap (F3.1) and the unused `context` argument of
  `declare_resource_name` (F2.7/F3.1).
- Known limit (F3.1 territory): rules still deduplicate by name across
  device groups (pinned xfail), so a same-named rule in a second DG is
  dropped rather than chained in its own DG. The chain logic already
  groups by the parser-recorded device group, so F3.1 only needs to
  stop the dedup.
- Gate: ruff clean. pytest 184 passed, 1 xfailed (the F3.1 item).
  terraform validate green on both sample and kitchen-sink output.

### F2.4 — Rewrite emitters to the v2 schemas (previous session)
- Every emitter now uses the v2.0.14 nested-attribute shapes (verified
  against `/tmp/schema_2014.json`): `protocol { tcp = {} }`,
  `layer3 { ipv4 = { ip_address = [...] } }`, `auto_key { ike_gateway,
  proxy_id }`, `position { where = "last" }`, `dynamic = { dynamic =
  { filter } }`, tag colors `color1`..`color7`, `nat_type = "ipv4"`
  (protocol family, not direction). Proxy-ids merged into
  `panos_ipsec_tunnel`; the standalone proxy-id resource is gone.
- `hcl_value()` helper renders nested dicts/lists with indentation;
  `HclRef` emits raw HCL references (static-route `virtual_router`).
  All call sites pass the two-space indent explicitly except the
  primitive list renderer; f-strings that reused outer quotes (Python
  3.12-only syntax, a portability bug for the 3.9 target) are removed.
- Two-tier naming: `declare_resource_name(name, scope, context)` for
  declarations (context = defining DG or template, so same-named objects
  in different DGs get unique addresses), `unique_resource_name(name,
  scope)` for references (resolves the first declared name). F1.7
  semantics preserved by tests.
- Report-only types (BGP x3, OSPF x3, application filter, security
  profile bodies) go to `MANUAL_SETUP_REPORT.txt` instead of comments in
  scattered .tf files. Security profile bodies stay report-only: the
  v2 resources exist but the parser captures only name/description, and
  emitting empty profiles would silently create misconfigured objects
  (F2.9 decides).
- `resource_mapping.py` restructured to the post-rewrite spec:
  `EMITTED_TYPES` (20, must match goldens exactly) + `REPORT_ONLY_TYPES`
  (7, each verified absent from the schema). `tests/test_resource_mapping.py`
  rewritten to match. `docs/RESOURCE_MAPPING.md` rewritten to the new spec.
- Parser additions: IPv6 address objects (`<ipv6>`, `<ipv6-range>` ->
  `ip_netmask`, the only v2 address attribute that takes them), dynamic
  address-group filter serialization (`_dynamic_filter_expr` ->
  `tag == "web"` style expression). Empty address groups emit a
  manual-setup comment (v2 requires exactly one of static/dynamic).
- README rewritten: accurate v2 resource table, report-only list, removed
  stale v1 type names, marketing claims, and version-history claims that
  contradict the current code.
- `test_terraform_validate.py`: xfails removed; kitchen-sink gate added.
  `test_schema_conformance.py`: xfails removed. `test_edge_cases.py`:
  IPv6 xfail removed (now passes); same-named-objects-across-DGs xfail
  kept (parser last-wins dedup is F3.1 territory).
- Goldens regenerated (sample 8 .tf, kitchen-sink 26 .tf; the old
  application_filters/bgp/ospf .tf files are gone, their data now in the
  manual-setup report). `.terraform.lock.hcl` added to .gitignore.
- Gate: ruff clean (55 violations found and fixed during the session).
  pytest 176 passed, 1 xfailed (the F3.1 item). terraform validate green
  on both sample and kitchen-sink output.

### F2.3 — location on every resource
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
- Python 3.12.3 locally; the code targets **Python 3.9** (ruff
  `target-version="py39"`). Python 3.12-only syntax (for example
  reusing the outer quote inside an f-string) is a bug even when it
  runs locally; ruff catches it.
- Tests: `python3 -m pytest` (pytest 9.1.1 is preinstalled; pinned in
  requirements.txt) or `uvx --with pytest==9.1.1 pytest`; lint:
  `uvx --with ruff==0.16.10 ruff` (PEP 668 blocks system pip installs).
- The provider schema is NOT a pip package. It comes from `terraform
  init` + `terraform providers schema -json` against the source/version
  in the golden provider.tf (conftest `provider_schema` fixture;
  skipped when terraform or the registry is unavailable).
- terraform 1.16.1 available at /usr/bin/terraform.
- Converter CLI: `python3 panorama_to_terraform.py <input.xml> [--output-dir DIR]`
  (output dir is a flag, default `terraform_output`).
- Splitter CLI: `python3 split_device_groups.py <input.xml> [--output-dir DIR]`.
- Provider v2.0.14 schema (128 types) cached at /tmp/schema_2014.json;
  shape extract at /tmp/v2_shapes2.txt (the earlier /tmp/v2_shapes.txt is
  unreliable). Refetch with `terraform providers schema -json` if needed.
- v2.0.14 uses nested-type ATTRIBUTES (object/list argument syntax), not
  block types, for all nested structures. `location` is a required
  nested object argument. `where` accepts first/last/before/after.
- 7 PAN-OS config types have no v2 resource (BGP x3, OSPF x3, application
  filter) and go to the manual-setup report; the 20 emitted types are in
  `resource_mapping.py`.

## Conventions
- One task at a time; `acceptance.md` overwritten before each task.
- ASD-STE100 in commits and docs.
- Red→green: failing checks are xfail(strict=False) with the fixing
  Epic's task reference; flip them to plain asserts when the epic lands.
- Commit per feature; completed items leave markdown when the epic completes.
