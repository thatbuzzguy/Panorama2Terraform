# Backlog

Tech debt, out-of-scope items, and nice-to-haves. Promote items to `PLAN.md` when they become in-scope.
Completed work is not recorded here; the git history and the owner document hold it.

## Tech Debt

- Property gaps the scan does not report, because the container that holds them has
  no matrix row: only an `emitted` container can name the properties an emitter reads.
  The scan scope rule pins this in
  `tests/test_property_coverage.py::test_scan_scope_is_the_entries_a_matrix_row_covers`.
  The rule now exists for each shape, in `docs/COVERAGE_MATRIX.md` §1: `report`, which closed the application
  filter, the schedule, and the application override gaps; `count-only`, which closed the regions `addresses`
  gap; `nested-block`, which closed the `parent` gap on `tests/fixtures/interfaces_ethernet.xml`; and
  `bookkeeping`, which closed the `devices` and `templates` fields, because the fact those rows record is the
  relation between an entry and the container that lists it, so the membership entry carries no value for it and
  its entry line names no field. Measured 2026-11-04 no container outside the scan scope has a captured field no
  output read, so no field gap is recorded here.

- Parser extraction gaps found by the parse unit tests: none. Each gap was a parse method that dropped data, and
  each was fixed when a report confirmed it in a fixture. What stays open is the fact a report cannot state, not
  a gap: no certificate type declares a `profile-name` attribute, so the per-entry report has no profile-name
  fact for the certificate container, and the pin that would hold the rule
  (`tests/test_container_coverage.py::test_report_declares_the_profile_name_column`) cannot be written from the
  schema.

- Service objects with both tcp and udp legs cannot be emitted whole. The v2
  `panos_service` schema declares `protocol.tcp` and `protocol.udp`, but the
  provider accepts one leg only: a config with both fails `terraform
  validate` with "Invalid Attribute Combination" (verified against 2.0.14,
  F3.4). F3.4 decision: emit the tcp leg (udp when tcp is absent), keep the
  dropped leg as a `# NOTE:` comment and a `MANUAL_SETUP_REPORT.txt` entry.
  A future release could offer a two-object split as an opt-in.

- External dynamic list `auth` (username/password) is not parsed. Writing
  credential material into generated HCL is not acceptable (F3.4). The rule decided
  2026-10-31 (`backlog.md`, the value the parse cannot carry) is the shape the emitter uses when
  the parse reaches this field: the block prints `var.<name>` and the run declares the variable. The
  report entry stays until a parse method reads the container, because the value itself cannot come
  from an export.

- Policy rules do not record which rulebase (pre, post, or shared) they came from. F2.5 chains are
  ordered per device group across all rulebases, which matches PAN-OS evaluation order for a single
  rulebase but mixes rulebases when a device group has both pre- and post-rules. F3.5 confirmed the
  provider can express it: `panos_security_policy_rules`, `panos_nat_policy_rules`,
  `panos_decryption_policy_rules` and `panos_pbf_policy_rules` all declare
  `location.device_group.rulebase` and `location.shared.rulebase` (v2.0.14 schema). F3.5 decision
  (2026-10-08): do not emit it. The parser does not record the rulebase, and the accepted value
  string is unverified — the provider binary carries the literal `pre-rulebase` and no
  `post-rulebase` literal, so the omitted-attribute default is the only safe output. Verify the
  value against a live target, then record the rulebase per rule, chain within one rulebase, and
  emit `rulebase` for the four rule types. Note that `location.vsys` declares no `rulebase` field,
  so a vsys-scoped rule cannot carry it at all and must be reported instead.

- Security profile bodies are not parsed (antivirus, anti-spyware, vulnerability, URL filtering,
  file blocking, WildFire, zone protection). The v2 provider has resources for them, but emitting
  empty profile objects would silently create misconfigured resources. F2.9 decision (2026-10-04):
  the names and descriptions go to `MANUAL_SETUP_REPORT.txt` with the reason; real emission waits
  for the profile body parsing.

- Schedules: `panos_schedule` exists in v2, but only entry names are parsed (day/time ranges not
  captured) and v2.0.14 has no monthly schedule support. F2.9 decision (2026-10-04): report entry;
  revisit when schedule parsing lands.

- IPsec tunnel monitor profiles have no v2 resource: `panos_monitor_profile` is the PBF path
  monitoring profile (`network/profiles/monitor-profile`), a different PAN-OS object — verified in
  the provider/pango source. F2.9 decision (2026-10-04): report entry.

- The six security profile categories are declared with an empty naming
  context (F3.1) because their emitter is a stub that writes no `location`
  at all: the objects carry `device_group` and `vsys`, but putting either in
  the digest would promise a scope the emitted resource does not have.
  F3.6 left them alone for that reason. When real profile bodies land, give
  them their device group or template context and regenerate the digests.

- A config entry the export nests inside a stack entry is read and placed in the stack unit
  (F6.10.5), but `resource_mapping.LOCATION_SCHEMA` declares no `template_stack` sub-block for a
  config type, so `TerraformGenerator.location_data` states no location for it and the run writes no
  block for it. Measured on an export that nests one `address` entry under a `template-stack` entry:
  the report line names the entry as `emitted`, and the unit directory holds no `address_objects.tf`.
  Only `panos_template_variable` and `panos_vsys` declare the `template_stack` sub-block. The fix needs
  the provider to state a config location inside a stack, so the entry stays a report finding until then. The
round-trip cross-check is the gate rule that states this case as a count that does not agree, so the fact stays
here with that rule named.

- The splitter copies a template only when the export lists a device in both
  the device group and the template (F3.6). An export whose device groups
  list devices and whose templates list none therefore copies no template and
  prints that fact; the operator fixes the export or the split file. Do not
  restore a name-based fallback for this case.

- An entry under `devices/entry/<device>` (not inside a device group) records
  `device_group = 'Shared'`, because `device_group_of` has no other fallback.
  F3.6 removed the naming consequence for template-scoped types (an interface
  or router there takes its device as digest context and is placed with
  `location.ngfw`), but an *object* entry under a device (an address, a
  service) still hashes `'Shared'` as its context, because object types take
  the device group as context and no device group is declared. Give
  device-level objects their own context when a fixture shows the collision.

- Certificate blocks: what stays open after the two container rows, the two parse methods, the two emitters and
  the gate rule landed. Measured 2026-11-05 against provider 2.0.14: `panos_certificate_import` is a resource
  with no data source, so `entry_coverage.name_field` reads its name fact through `RESOURCE_NAME_FIELDS`;
  `panos_certificate` is a data source with no resource, so the container cannot become an `emitted` row through
  a data source; no certificate type declares a `device_group` sub-block, so a certificate entry the export
  places in a device group prints the `Shared` template placeholder, which the location rule reports. A `local`
  that states both `pem` and `pkcs12` is refused by `terraform validate` and not by the schema JSON, so the
  choice is a measured fact written as `selects` data in the row, which the gate reads offline
  (`docs/ARCHITECTURE.md` §4.6), and the plan check reports the same block for a run that uses `--validate`.
  - The EDL `certificate_profile` field stays a plain string, so it records no reference edge: the EDL site
    resolves no names, so `name_ref` cannot reach it, and `tests/golden/kitchen_sink/shared_45ca31c3/external_lists.tf`
    is unchanged. If a later rule makes the EDL site resolve names, that field becomes a reference to the emitted
    profile block and the golden moves from a real run.
  - A `certificate` list member inside a profile entry prints its `name` as plain data, not as a reference to the
    certificate block the run wrote for the same name, because the object carries its own name and the emitter
    prints the list shape the provider declares. If a reference edge is wanted for those names, a rule must say
    which site records it.

- A per-device template variable override has no place the provider can put it:
  `panos_template_variable.location` declares `template` and `template_stack` only,
  and neither sub-block has a device field. So the tool cannot generate the
  per-serial value the Panorama GUI holds. The parse must report a variable entry
  whose value is stated for one device instead of taking the stack value as the
  entry value. Not built: the corpus holds no such entry, so the rule needs a
  fixture that shows how an export states a device-level value.

- The notice set is not pinned. `docs/LICENSING.md` names the 18 files that still hold upstream text and the
  four `src/` modules that carry a copyright notice, and `git blame` is the authority for the split. No test
  reads a notice, so a notice can name a holder the split does not support and the gate reports nothing. A pin
  would read every module source and compare the notice against the blame author, which is a document check
  rather than a rule the tool enforces, so it is not built.

## Out of Scope

- The orchestrator is not this tool's job. The tool writes data an orchestrator reads: the unit
  manifest, the ownership record, the reference edges, the site record, the import blocks, and the
  `.tfvars` written from the site record. It runs no plan, no apply, and no commit, and it manages
  no secrets. The parts a platform discussion reaches that stay out of scope: the key and
  certificate signing pipeline, a lifecycle block (`create_before_destroy` or
  `ignore_changes`), the state backend, the workspace layout, and the hosted platform.
  The tool writes the block shape and the variable reference; the platform supplies the
  value and runs the plan. The rule is in `docs/CODEBASE_ASSEMBLY.md` §13.
- The Day 1 device bootstrap cannot be expressed in the pinned provider schema: no resource
  registers a device, defines an HA pair, sets a management interface, or holds an auth key. Serial
  registration, HA grouping, management IP, DNS, NTP, and the admin account stay outside the
  codebase. A hardware replacement is therefore one `.tfvars` value change plus the
  operator's re-registration: the tool changes the site row, and no plan changes the Panorama
  device entry. The fact is in `docs/CODEBASE_ASSEMBLY.md` §12.
- PAN-OS version matrix testing.
- Lawyer review of the licensing rule. `docs/LICENSING.md` states the rule as this project understands it, and
  the split is measured through `git blame`, but no lawyer has read it.
- The state source has no write path (F5.6). A run reports what a state document holds and never
  writes one, so a drift finding is an operator action, not an update.

## Nice-to-Haves

- Adopt `ruff format` as a gate. A one-time format pass of both legacy scripts is required first
  (about 1500 changed lines in `panorama_to_terraform.py`). Do it as its own task so the diff stays
  reviewable.
- Raise `pyproject.toml` `target-version` to the Python floor (`py310`). `ruff check` reports 101
  findings at that level: 80 `UP045` (`Optional[X]`), 16 `B905` (`zip` without `strict`), 4 `UP035`,
  and 1 `UP007`. Do it as its own task so the diff stays reviewable. The gate stays green while
  `target-version` states the syntax level ruff enforces, which is below the floor.
- Deeper post-run checks (beyond the gate (F4.1): `tflint` integration. `sanity_checks.py` is the runtime home
  for the static rules.

## Design Decisions (multi-scope model)

- Policy chains key on (device group, vsys) since F3.2. Each chain anchors
  at `where = "last"`, so a vsys boundary restarts the chain; a rule never
  pivots on, or depends on, a rule in another vsys.
- `location` carries the source scope since F3.5 and F3.6: `vsys { name,
  ngfw_device }` for a declared vsys on a type that accepts it, `template {
  name }` (plus `vsys`, and `ngfw_device` when the export nests the entry
  under a device inside the template) for a declared template, `ngfw {
  ngfw_device }` for config an export places under one device, otherwise the
  device group, `shared = {}`, or the `Shared` template placeholder — which
  is emitted only when nothing in the export places the entry, and is listed
  in `MANUAL_SETUP_REPORT.txt` with the templates that device does take. A
  declared scope the type cannot carry is reported, never dropped silently.
- The multi-device association is data, never a name (F3.6). A device group,
  a template and a template stack belong together when the export lists the
  same device under each. `localhost.localdomain` is the PAN-OS placeholder
  for "this device", so it is never an `ngfw_device` and never joins two
  things.

## Design Decisions (coverage and gate)

- The conversion report (F4.3) keys on logical entries — an `<entry name>` plus its properties — not
  physical lines; one entry spans many lines in the XML. The reported line number is the entry's
  opening tag.
- The coverage matrix (F4.4) is a permanent maintenance duty: every
  emitter change must keep the property list on its row honest, or the property
  section of `CONVERSION_REPORT.txt` silently lies. The entry-mark rule (F4.3) is
  the test that makes an unmarked element read fail CI.
- The parser extraction gaps listed above will surface in the F4.3/F4.4 reports; fix each gap when
  the report confirms it in a fixture, rather than fixing them speculatively now.
- The sanity gate (F4.1) reads the output files, so a rule that reads only the files cannot see an entry that
  produced no file. Two gate rules read the run's ledger: the round-trip cross-check (F5.7,
  `docs/ARCHITECTURE.md` §4.6) and the request-set rule (F8.8, `docs/API_CONVERSION_PATH.md` §3). F4.3 is the
  accounting for the entries that write nothing, and the gate cannot replace it.
- The round-trip cross-check (`sanity_checks.check_round_trip`, pinned by `tests/test_round_trip.py`) compares
  the block set the reader read with the entry set the run's ledger read, per unit and row. It is one of the two
  gate rules that read two sets, so it is one exception to the boundary that the gate reads only the files it
  wrote (`docs/ARCHITECTURE.md` §4.6); the other is the request-set rule (`sanity_checks.check_request_set`,
  `docs/API_CONVERSION_PATH.md` §3, pinned by `tests/test_sanity_gate.py`). Its finding is a coverage fact, not
  a broken output, so it is a WARN and
  does not change the exit code, the decision `entry_coverage.PROPERTY_RULE` already states for a gap: every
  corpus fixture still exits 0, and the pins read WARN. Measured 2026-11-05 the corpus is not silent: the rule
  reports 20 findings on 9 fixtures, which `tests/test_round_trip.py` pins as `CORPUS_GAPS` and
  `CATEGORY_COUNTS`, and the entry side counts only the entries `entry_coverage.EntryLedger.destination` answers
  as `emitted`, so an entry the run reports enters no count. The rule states no exception list for the
  populations it cannot join, so they stay open here.
  - 3 findings: an `emitted` entry the row counts with no block of the row's type. The measured instances are
    `tests/fixtures/dependency_wiring.xml` (`panos_ethernet_interface`, 3 against 2),
    `tests/fixtures/interfaces_other.xml` (`panos_aggregate_interface`, 2 against 1), and the same aggregate
    case in `tests/fixtures/kitchen_sink.xml` (2 against 1). In each, the counted entry that has no block of the
    row's type is one whose name carries a unit, so the emitter prints its block as the subinterface type
    through the name rule and the reader reads that block for the subinterface row
    (`docs/COVERAGE_MATRIX.md` §1). The shape that held the instances before, an `emitted` entry whose content
    has no v2 attribute, has no measured instance left: the `report_only` address entries in
    `tests/fixtures/address_objects.xml` answer `report` through the destination rule and enter no count, so
    that fixture reads clean. The same shape stays open for a config entry inside a stack, above.
  - 16 findings: a block read for a property level, which has no ledger row, because the ledger records one row
    per config entry and a property level is not an entry.
  - 1 finding: one entry that writes more than one block, on `tests/fixtures/interfaces_ethernet.xml`, because
    the `nested-block` entry writes lines inside its parent block and `matrix_row_for` answers no row for that
    container, so the entry side reads no count while the block side counts the block.
  - The facts that stay open, each stated in its own entry in this document: the four `*_policy_rules` types,
    which wait for the F3.5 rulebase decision and a live target; a config entry inside a stack, which needs a
    provider location shape; the EDL `certificate_profile` field, which records no reference edge because the
    EDL site resolves no names; the profile-name report column, which no certificate type declares; and
    the two `.github/` template files outside the indexes. The certificate `sensitive` `REFERENCE_ONLY` fact is
    closed: `resource_mapping.VALUE_VARIABLES` holds the `private_key` and `passphrase` rows, and the pins that
    hold it are `tests/test_variables.py` and
    `tests/test_robustness.py::test_a_parsed_secret_never_reaches_a_generated_file`.
- The two template files under `.github/` (`ISSUE_TEMPLATE.md` and `PULL_REQUEST_TEMPLATE.md`) sit outside every
  index, so the layout rule (`docs/ARCHITECTURE.md` §1.1) reads them as a finding. They are not tool documents,
  so no index names them; either an index gains them or they leave the repository.
- The gate `location` check is presence only, for both block kinds. The resource sub-block and field
  shape stays pinned by `tests/test_multi_vsys_location.py`, because `terraform validate` accepts an
  unknown sub-block and drops it silently. The `data` shape is checked by the gate, because
  `DATA_SOURCE_SCHEMA` is data the gate can read (F5.5). A `resource` shape stays inside
  `LOCATION_SCHEMA`, which is the generator's subset, until the emitted shape becomes data the gate
  can read for both kinds.
- The placeholder check lists the VPN pre-shared key only. When F4.3 adds per-entry accounting, the
  expected placeholders should come from the same table that decides the report entries.
- A value the provider constrains in its code, not in the schema JSON, is a fact the tool cannot read offline, so no
  table states it. Measured 2026-11-04 against provider 2.0.14: `panos_administrative_tag` accepts one value for
  `disable_override`, while the pinned schema states no value list for the field. The rule that decides how the gate
  treats such a value is in `docs/ARCHITECTURE.md` §4.6, and `tests/fixtures/kitchen_sink.xml` states the accepted
  value for the entry a plan pin reads.
- Consider a `--checks` selector on the converter CLI if the gate grows; today every check runs on
  every conversion, and a WARN never changes the exit code.

## Design Decisions (line map and container table)

- `parse_xml` returns `ParsedSource`, not an element, because a line map needs
  the file it came from. The line is recorded by expat handlers:
  `ET.TreeBuilder` has no `CurrentLineNumber`, so `xml.etree` cannot report one.
  The F3.8 read order (size check, read, size check on the read bytes, DTD
  refusal, parse the same bytes) and the `ET.ParseError` type are unchanged.
- The line map covers the tree that was parsed. An element copied out of it has
  no line, which is why the device-group splitter, which builds new trees from
  copies, never asks for one.
- A container is reported only at section level: no config-object entry between
  it and a config root. A container inside a config-object entry is a property
  level, so F4.4 owns it. The table marks those rows `level='sub-shape'`.
- A `predefined` container is not a finding: those entries are PAN-OS built-in
  definitions, not operator objects. `container_coverage.is_predefined` states
  the rule, and the fixture keeps a `predefined` entry to pin it.
- `nested-block` is a destination kind: virtual-wire, TAP, `ip` and
  `ipv6/address` write lines inside a parent resource block and have no resource
  type of their own (provider v2.0.14, verified in F3.3).
- The table parity test matches a row path by segment presence, not by full path
  order, because a method can reach a container through a helper (`parse_bgp`
  reads `protocol/bgp` through a path list, `parse_interfaces` reaches `layer3`
  through the interface kinds). A row that names a segment no code path contains
  fails; a row with the right segments in the wrong order does not. Narrowing
  this to full-path comparison needs the pattern list to be data, not string
  literals inside methods.

## Design Decisions (per-entry report)

- A destination kind is a container fact in the table, so two per-entry kinds were
  added: `skipped` (a parse method visited the entry and did not model it) and
  `unaccounted` (no parse method read it, so no row covers its container). A
  `report` row is not a gap: the manual report is its output. The gap kinds are the
  three that write nothing.
- The `parse_device_groups` row is `emitted`, because the device group entry is an object the scope block writes;
  the membership containers inside it stay `bookkeeping`, because no provider resource exists for a device and the
  entry inside a membership container carries no value for the relation the row records.
- A report row is one entry at section level. A container inside a config-object
  entry is a property level, so the parent row shows the property-entry count and the
  matrix (F4.4) states the properties. F4.3 does not print property rows.
- Captured fields are the keys of the object the parse method built, not the XML tag.
  A field inside a type sub-shape is reported under the object key (`fields`), so the
  report reads through the data model, not through the XML.
- The mark stores the captured object by reference, so a field added after the mark is
  in the report. This is deliberate: it lets a method mark where it builds the object
  and still fill the rest.
- The read-but-not-marked check follows the helper calls a parse method makes, but it
  does not follow a `findall` path held in a variable. A method that reads entries
  through a variable path is accepted only when it marks somewhere in its call chain.
  The corpus check (every entry in a covered container is marked) is the check that
  cannot lie; the AST check is the early warning.
- `CONVERSION_REPORT.txt` groups rows with the F3.9 rule, so a report row and an
  interface report row for the same entry name sit in the same section. One shared
  grouping function, not two.

## Design Decisions (property coverage)

- The read record is a run-time measurement, so `mark` returns the recorded object and a
  parse method must build its object through what it returns. The record stays off during
  the parse and the run turns it on before the first generator call, because a key the
  parse method read off the XML element is not a property an output used.
- A property name is the measured key name, so the grounding test can find it as a string
  in the emitter source. `declared_type` and `other` stay on the `panos_address` row
  because the manual setup report reads them for a report-only address.
- The entry name and the five scope facts are the row identity, not properties, so the
  parity check compares the captured fields only.
- `emitter` names two methods when a report writer reads properties the `.tf` emitter does
  not. Only `panos_address` has this today, because the manual setup report prints a
  report-only address from the same parsed object.
- The scan scope is the entries an `emitted` container row covers, because only a row can
  name the properties an emitter reads. A finding is an operator action, so it does not
  change the exit code. The console prints one line per finding, in the shape
  `docs/ARCHITECTURE.md` §3.2 states, and the fact names the parsed-object key names.
- A manual report section prints what the parse captured for it, so a captured field is
  either printed or reported as unread. The routing section prints only the entries the `protocol` object
  cannot express, read through `entry_coverage.protocol_report_rows`, so the destination comes from the
  ledger and no second list names these entries. A row names the router, the level and the entry name, then
  the fields in the order the ledger's row declares, so the report reads every field it prints through the
  captured object and the property scan counts that read as an output use.
- The conversion report reads a scope name from the scope `<entry>`, not from the container
  element, so a run inside a declared scope prints its device-group, template, and device
  sections instead of a blank scope.

## Design Decisions (input sources)

- The parse layer keeps the ElementTree tree. The fetch layer is a byte producer, never the
  input model, because four things are keyed on the tree: the container table rows (XML
  paths), the entry ledger marks, the parent walk that gives the five scope facts (§2.2),
  and the expat line map (`ET.TreeBuilder` reports no line, so only the expat handler path
  can record one). A device-object model has no line number, so the F4.2 reporting cannot
  survive it.
- Standard library only. `source_fetch.py` uses `urllib.request`. The planned `pan-os-python`
  producer was superseded: the SDK exposes no redirect hook, so the scheme rule cannot be
  enforced through it, and a standard-library producer enforces all three https rules and needs
  no test skip. No module in the project imports a third-party package.
- The response wrapper is normalised, one shape per request shape; the rule is in
  `ARCHITECTURE.md` §3. The fetch layer checks the response against the request it made, so a
  per-scope shape is not guessed from what it looks like, and the container table still names no
  wrapper row.
- The record directory is the output directory, so the prune action reads the record file the same run
  wrote. The rule, the action, and the flag that gates it are in `ARCHITECTURE.md` §3.3:
  `provenance.prunable_entries` decides, `provenance.prune` removes, and `--prune-cache` gates the step for
  an api run, because a file record states `-` for the cache field and references nothing. A two-source run
  writes two records in one file, so the action reads a record file, not one record.
- Pinned by `tests/test_data_source_schema.py`: a data source schema does declare required
  attributes. For every one of the 128 data sources `location` is required, and for every data
  source that has a `name` attribute `name` is required (106 types have both; 22 have no `name`,
  the settings, policy and collection shapes). The gate rule that reads a `data` block is
  `data_blocks` (F5.5), because `terraform validate` accepts an unknown `location` sub-block and
  drops it silently.
- Provider data sources, verified against 2.0.14 with `terraform providers schema -json`: 128 data
  sources mirror the 128 resources, and every emitted type has one. 126 types have the identical
  attribute set and the identical `location` sub-blocks, and among those 126 no `name` flag differs.
  The two asymmetries are set membership, not attribute shape: `panos_certificate_import` and
  `panos_virtual_router_interface` have a resource and no data source; `panos_certificate` and
  `panos_predefined_dlp_file_type` have a data source and no resource. Only `panos_addresses` returns
  a collection (a map keyed by name). `panos_device_group`, `panos_template` and
  `panos_template_stack` return the membership facts `parse_associations` builds from the export; a
  data source resolves at plan time, so it cannot feed a generation-time report.
  `DATA_SOURCE_SCHEMA` is written from that schema, not from memory.
- The table is the complete declared shape, not the generator's subset: `LOCATION_SCHEMA` lists only
  the sub-blocks the generator can use, so a gate rule that refuses a sub-block the type does not
  declare needs every declared sub-block, per type, because the field sets differ per type. The pin
  between the two tables is `tests/test_data_source_schema.py`.
- Decision: the table test keeps the fixture's skip marker and writes no committed schema snapshot.
  The `provider_schemas` fixture already skips when the terraform binary or the provider cache is
  absent, so a snapshot would be a second copy of the same fact and could drift from the pinned
  provider version.
- BGP and OSPF have neither a resource nor a data source of their own, so read-through cannot cover
  them. Their data reaches output as the `protocol` object inside the `panos_virtual_router` block, so the
  property scan measures the routing levels through that row (`PROTOCOL_SHAPE`), and a level the table does
  not state is not read. A filter container is not inside the `protocol` object, so its levels are measured
  through `FILTER_SHAPE` instead (§4.10).
- Routing levels and fields `PROTOCOL_SHAPE` does not state are not read, so they reach no
  output and no report row. F7.10 closed the `ospfv3` fields, the `bgp` fields and the two
  redistribution profile lists, and F7.11 closed the six entry rows that held the report
  decision: `protocol/bgp/peer_group` (2 fields), `protocol/bgp/peer_group/peer` (9),
  `protocol/bgp/redist_rules` (7), `protocol/ospf/area/interface` (8), `protocol/ospfv3/area`
  (1), and `protocol/ospfv3/area/interface` (9). Every field the provider declares for those six
  levels is read and printed, and none is marked sensitive, so no `VALUE_VARIABLES` row is
  needed. The gaps that stay are the choice levels: `selects` is the one place a row states a choice the
  provider reads as exactly one (F7.12), so the two protocol rows that hold such a choice state it
  (`protocol/bgp/peer_group/peer/peer_address` and `protocol/ospfv3/auth_profile`), and the same rule serves the
  filter table (F7.13). Measured 2026-11-03 against provider 2.0.14. A level becomes printable when a parse
  method reads it and the table has a row for it, because the emitter, the gate and the report all read that
  table.
- Decision for the redistribution route-map entry (F7.8): the row scope stops at the `match`
  and `set` rows, because those two rows state leaf fields only. The six levels inside them —
  `match.ipv4.address`, `match.next_hop`, `match.route_source`, `set.metric`, `set.ipv4`,
  `set.ipv6` — are therefore not table rows, so no parse method reads them and the gate refuses
  them in a hand-written file.
- Read-through is opt-in per declared scope (F5.5). A plain string already applies, because
  Panorama resolves an object name through its own inheritance at commit time, and one `data` block
  is one plan-time API call. A `data` block for a name that does not exist fails at plan, not at
  validate, so a read-through run is labelled in the generated `README.md`.
- Decision for the 22 rows that declare no `name`: the gate rule is stated per row, so a settings or
  policy data block that is correct is not refused for having no `name`. A row that declares no
  `name` cannot be a read-through scope, because it cannot hold the entry name a reference needs.
- Decision: the collection data source `panos_addresses` is out of scope for the emit path, because
  it has no entry name to key and no reference names a collection.
- Decision: no coverage matrix row covers a `data` block, so a property finding cannot name a
  read-through name. The record of a read-through run is `read_through.tf` plus the `README.md`
  label, and `MANUAL_SETUP_REPORT.txt` is the one report that may name one through the existing
  location rules.
- Open: no verified built-in name table exists, so a declared read-through scope turns every name
  outside the run into a `data` block, including a built-in such as `any`. A built-in name table
  verified against a live target would let the emit path skip those names; until then the run is
  labelled.
- Open: the provenance record names the host and the scope, never the credential. The key
  rule itself (environment only, never argv, never a generated file) is in `ARCHITECTURE.md` §3.
- The state document is a reference source, so it reads through the same door and the same row rule
  (F5.6); the rules are in `ARCHITECTURE.md` §3 and §3.2. A state entry has no
  source line, because only the expat handler path records one, so its position is its resource
  address, and the scan reads the matrix row through the resource type instead of through a
  container path.
- Open: the state scan compares only a property both sides hold by the same name (F5.6). The matrix
  row names the key the emitter reads and the state document names the attribute the provider
  stored, so no mapping rule exists between them: the parse key `tags` and the provider attribute
  `tag` are not compared. A comparison table would have to be verified per type against the
  provider schema, the way `LOCATION_SCHEMA` is, so the scan keeps the same-name rule until such a
  table exists.

- Epic 8 (path 2) reads the facts an export cannot carry, and each one stays blocked until a live target
  states it. The committed response set (`tests/responses/`, F8.4) shows one shape per accepted request shape
  and names no fact, so the harness cannot close any of these. The shapes, what each one unlocks, and the
  condition per fact are in `docs/API_CONVERSION_PATH.md` §4, so this document names no shape a second time.
  The rule that keeps these items out of `to-do.md` is that a piece cannot be written from a response the
  project does not hold. The conditions are: the F3.5 rulebase value verified against a live target; the device
  serial, and which element a command names, against a live target; and a response that shows how a device
  states a per-device template variable override.
- Finding, opened by the F8.1 decision: the scan has no rule that a predefined source is definitions,
  so a run that reads a predefined scope reports its built-in containers as findings. `is_predefined`
  answers through the parent walk, and for a per-scope source the parent of the container under the
  root is `result`, read as the place, so the walk never reaches an element tagged `predefined`. The
  rule that a built-in entry container is not a finding holds for a file source, which the pin
  (`tests/test_container_coverage.py::test_predefined_entries_are_not_findings`) reads, and not for a
  predefined read. A piece must decide whether the scope path names the place only, and the built-in
  entries are read through the response that holds the container the name table needs.
  Measured by F8.5 (`tests/test_api_path.py::test_a_predefined_entry_read_reports_the_place_as_a_finding`):
  for a place read the response holds the `predefined` element, so the walk reaches it and the scan names no
  finding; for an entry read inside the place the entry sits at the place level, so the scan reports the place.
  No container table row names a built-in container, so no parse method runs over a predefined response and the
  entry report names no row for a built-in entry, which the ledger counts through `predefined_total`. The rule
  that decides whether a predefined source is definitions still has no owner, so the entry read stays a finding
  here.
- Finding, opened by F8.3: the join checks a response against the index entry whose request made it, so it
  reads only a response the index made a request for. The index makes only per-scope requests, and a device
  fact request names no scope path, so the one element-name rule (`source_fetch.names_element`) names no
  element for a command, and no module states a command-to-element table. Which element a command names is
  therefore a fact the tool cannot read offline. The committed response for the device fact shape
  (`tests/responses/`, F8.4) shows the shape and names no fact, so this stays here until a live target states
  which element a command names. This touches the F8.1 finding above, because both need a fact a request cannot
  state, and the pin `tests/test_api_requests.py::test_the_committed_op_response_shows_one_shape_and_names_no_live_fact`
  keeps the fixture an illustration rather than a measurement.
- Open, opened by F8.6: the record names the request that made each response, so `scope` names the path that
  request declared. A device fact request declares no path, so its record states the door's default,
  `whole-config`, and `request` is the only field that names the command. The scope index makes no device fact
  request, so a path 2 run writes such a record only when the run order reads a command as its own source, and
  no rule decides which scope that record should name. The pin
  (`tests/test_api_requests.py::test_a_committed_response_reads_through_the_injected_producer_and_the_record_names_the_same_bytes`)
  reads the default, so the record shape is unchanged and the decision stays here.
- Finding, opened by F8.2: the four membership lists name three of the five scope facts, so the index
  reaches no `vsys` and no device. A `vsys` is a scope fact (`ARCHITECTURE.md` §2.2), but no membership
  row reads it, so path 2 cannot request a vsys scope from membership: the run must read it as its
  declared scope, which names the device the vsys sits in. The pin
  (`tests/test_api_requests.py::test_the_four_membership_lists_are_the_container_table_rows`) holds the
  three. The entry point landed (F8.9) and reads no vsys, so a piece that reads one needs the fact that
  names which device the run read.
- Finding, opened by F8.2: `container_coverage.ContainerRow` has no field for the table its method
  returns, so a row cannot state which table `parse_associations` fills for a path. The join between a
  membership list, the table it returns, and the container that defines its names therefore lives in
  `api_requests.LIST_JOIN`, which is a second table beside the container table. If `ContainerRow` gains
  a `table` field, `LIST_JOIN` becomes data read through the table and the index states no join of its
  own.
- Finding: `is_scope_path` accepts the place or an entry inside it (`/<place>` and
  `/<place>/entry/<name>`), so a predefined read cannot name a container inside the place
  (`/predefined/url-list`), which is the shape the built-in name table read needs. The shape rule is
  unchanged by F8.1, so this stays outside the piece until the read that needs it is written.
- Open, opened by F8.7: the unit join reads the row set through one ledger, because the join is per response
  (F8.5), so for a run that read one response the row set is that response's rows. F8.9 closed the table half:
  the run order applies the one join rule in run order, so a run that read more than one response joins those
  tables before the index reads them. The row half stays open, because `api_requests.py` states no merge rule and
  the join cannot know which response the run read. F8.8 measures one path 2 pin through the committed
  single-response run, and that pin uses the response the run itself read: the whole read set is one response, so
  a cross-response read set needs its own rule before it can be pinned.
- Finding, opened by F8.7: the join reports a unit whose rows name a response the index made no request for, and
  states no rule that such a source is definitions. The two instances the pin reads are a whole-config export read
  and a predefined read; the predefined half stays with the F8.1 finding above, because no membership row reads a
  built-in place, so the index has no entry for it and the join can only report the unit.
- Measured by F8.8, the join's findings print through the gate's report shape (`docs/ARCHITECTURE.md` §3.2),
  which names no console line for this kind: the console prints one line per finding through the shape §3.2
  already states, so the gate's own line rule prints these findings too. The gate cannot name its own line in a
  module that states no shape, so the join prints no line of its own, and the join stays a data module. A join
  finding is a fact about the source, not a broken output file, so it is a WARN and the exit code does not
  change. F8.8 measures this through the committed single-response run and names the join position and its
  reason: `docs/API_CONVERSION_PATH.md` §3.

## Design Decisions (the value the parse cannot carry)

- Decided 2026-10-31: a value the parse cannot carry prints as the variable reference, never as a
  literal. The provider marks these attributes `sensitive`: `panos_certificate_import`
  `local.pem.private_key`, `local.pem.passphrase` and `local.pkcs12.passphrase` (measured 2026-11-05),
  the BGP, OSPF and RIP auth profile keys, the external dynamic list credentials, and the VPN pre-shared
  key. One table decides the shape, so the emitter, the gate and the `.tfvars` writer read
  `resource_mapping.VALUE_VARIABLES`; the literal half is held by `tests/test_robustness.py` (no generated
  file may contain the secret). Measured 2026-11-05: the three certificate `sensitive` facts sit inside the
  `local` object, not at the block's own level, and the shape table marks them in the `certificate` rows. The
  table holds the `REFERENCE_ONLY` row for `private_key` and `passphrase`, read by the emitter at the print
  site, and the gate and the `.tfvars` writer read both through the same table. The golden run proves the
  reference prints (`tests/golden/kitchen_sink/vsys1_78d8e4bc/certificates.tf`, with `vsys_cert` declared in
  `variables.tf`), and the pins that hold the rule are `tests/test_variables.py` (the declaration set read
  through the table) and `tests/test_robustness.py::test_a_parsed_secret_never_reaches_a_generated_file`. No
  other certificate attribute is `sensitive`, including the `panos_certificate` data source's `private_key`.
- Decided 2026-11-03 (F7.7): the rule is about the print, not about what the parse can carry. A parse
  method can read a `sensitive` value inside an entry and still print the reference, so the value is held
  only to decide the name, and the name is the §5 name of the entry that holds the field, because a field
  cannot name itself. The pin that no generated file holds a parsed value is
  `tests/test_robustness.py::test_a_parsed_secret_never_reaches_a_generated_file`.
- A FIPS-mode export carries no private key and no recoverable password hash, so the value cannot come
  from the source. The tool names the variable; the operator or the platform supplies the value. The
  placeholder check should read the same table that names the sensitive fields, so one table decides
  both the shape and the report line.
- Decided 2026-10-31 (F7.1): a reference-only name records no value, so the site row skips it
  (`site_data.build_rows` filters the names with no value) and the run writes no `.tfvars` line for it.
  The declaration is written by the generator with `sensitive = true` and no value, so the operator
  supplies the value in `terraform.tfvars`, which the tool never writes. The `variables` gate rule is the
  other half of the rule: it refuses a declaration with no consumer, so a declaration whose only consumer
  is a reference to an outside value is read through the same rule.

## Design Decisions (provider facts, re-measured 2026-10-31)

Measured against provider 2.0.14 through `terraform providers schema -json` and `terraform validate`.
These are the facts a provider discussion contradicts:

- No raw XML or xpath resource exists, so there is no in-provider fallback for a feature the matrix
  does not cover. The report path is the only output for an uncovered entry.
- `panos_virtual_router.protocol` is an object attribute, not a block: `terraform validate` refuses
  `protocol { ... }`. It carries `bgp`, `ospf`, `ospfv3`, `rip` and the two redistribution profile
  lists, and `protocol.bgp` carries `peer_group`, which carries the `peer` list.
  `resource_mapping.PROTOCOL_SHAPE` is the table that states the levels the tool prints, and
  `tests/test_protocol_object.py` pins it against this schema. The provider requires exactly one of
  `advertise` or `suppress` on a `range` element, and a `one_of` level can state exactly one key, so those
  two facts are gate findings rather than something `terraform validate` reports.
- `panos_template_variable.location` declares `template` and `template_stack` only, and neither
  sub-block has a device field, so a per-device override is not expressible.
- The provider argument is `hostname`, not `host`. `location.shared` is a sub-block, so the emitted
  shape is `shared = {}` and a boolean is refused. `panos_virtual_router` accepts no `device_group`
  location, which `LOCATION_SCHEMA` already states.
- The import id is base64 JSON of the location plus the name, so a colon-delimited id is the v1 shape
  and fails. The provider also declares the function `generate_import_id`; the tool builds the object
  itself, because the tool must be deterministic offline and the function resolves at plan time.
- The pinned schema has 128 resources, 128 data sources, 2 actions, 2 ephemeral resources
  (`panos_api_key`, `panos_vm_auth_key`), and the functions `address_value` and `generate_import_id`.
  `docs/CODEBASE_ASSEMBLY.md` §12 names the first three counts only. The last two are facts the tool
  does not use, because a run writes no secret and a run with no network must pass CI.
- `panos_certificate_profile` declares 15 attributes: the 13 fields `block_expired_certificate`,
  `block_unknown_certificate`, `block_timeout_certificate`, `block_unauthenticated_certificate`, `use_crl`,
  `use_ocsp`, `certificate_status_timeout`, `crl_receive_timeout`, `ocsp_exclude_nonce`,
  `ocsp_receive_timeout`, `domain`, `certificate`, `username_field`, plus `name` and `location`. Measured
  2026-11-05: `ocsp_exclude_nonce` and `ocsp_receive_timeout` are in the pinned schema, and `certificate` and
  `username_field` are objects, not fields — `certificate` is a list of objects whose `name` is required, so
  `terraform validate` refuses a single object there, and `username_field` states `subject` and `subject_alt`.
  The v1 names (`certificate_profile_certificates`, `block_expired_cert`) are not in the pinned schema, so an
  emitter for the profile row must use the v2 names.
- `panos_certificate_import` declares three attributes: `name`, `location` and `local`. `local` is one object
  with two sub-shapes, `pem` and `pkcs12`, and `terraform validate` refuses a `local` that states both
  (measured 2026-11-05), so `selects` is the one place a row states that choice. `certificate` is required
  inside each sub-shape, so the block cannot print the key reference on its own. Measured 2026-11-05: no
  certificate type declares a `device_group` sub-block, `panos_certificate_import` declares no `shared`, and
  `panos_certificate_profile` declares no `vsys`.

## Design Decisions (codebase assembly, open items)

The design record is `docs/CODEBASE_ASSEMBLY.md`, the owner document for the unit, ownership, edge,
order, import block, scope object, and site rules. The decisions that landed with those rules are not
restated here; they are in the record and the git history. Only the open items are below.

- Open: `check_import_blocks` compares a mapping result, so it cannot detect an id that states the
  name instead of the value, because the naming rule is idempotent. The writer keeps the value in
  the id, so an id the tool builds cannot carry the name.
- Finding: `location.device_group` declares a `panorama_device` field in the pinned schema, and the
  provider docs example states one, but the generator's location rule emits no device fact, so the
  tool writes no `panorama_device` in an id. An id states only what the block states. The value table
  records the field as a literal, so the block and the id print the same text for it. If a device
  fact becomes a rule, the id and the block change together.
- Open: a unit exists only when the ledger has a row in it, so a scope with no entry has no manifest
  row. A declared scope always has the entry that defines it, so no empty-unit case is possible
  today.
- Open, for the four `*_policy_rules` types: the position must be the position the live config
  holds, not the create-time position the generator emits, because a chain anchors at
  `where = "last"`. No import block is written for a rule entry until the F3.5 rulebase decision
  lands and a source states the position.
- Actions: the pinned schema declares `panos_commit` and `panos_push_to_devices`. Decided
  2026-10-31: the codebase declares Terraform 1.14 as the minimum, because actions need it, so the
  committed goldens state it. Both actions are emitted per unit (`docs/CODEBASE_ASSEMBLY.md` §10), and the
  push block states no `devices`, because the tool names no serial (`docs/CODEBASE_ASSEMBLY.md` §9 rule 8).
- Open: no coverage matrix row covers an `action` block, the decision F5.5 made for a `data` block,
  because an action names no entry, so a property finding cannot name one.
- Local inspection mode (`config_file`, `panos_version`) exists in the pinned provider schema and
  could let CI plan against a committed export with no server. It is not a rule in this project, and
  a plan in that mode cannot show drift, so it is not a replacement for the state scan.
- The tool cannot derive a module from an export: a module is a standard a person writes. The tool's
  part is the data file a module consumes.
- Reports are per run. A codebase-level view (the units, the entries each owns, the managed boundary)
  is not built.

## Codebase audit findings (measured 2026-11-11)

The audit read the test set (50 modules, 991 test functions, 1,641 collected pins) against the layout rule
and the import rule. Gate at both ends: `ruff check .` clean, 1,641 pins. Only the actionable findings are
below, each with the owner that would fix it. Nothing was changed by the audit.

- Import rule: `tests/test_real_or_report.py:33` imports `_check_chain_semantics` and `_rule_blocks` from
  `test_policy_order`. It is the only cross-test-module import in the suite. Fix: move both helpers to
  `tests/conftest.py`, the one shared helper file (§1.1). Owner: `tests/conftest.py`.
- Layout rule: `tests/fixtures/api_response.xml` is a committed API response inside the corpus, so the
  corpus scan reads it (`tests/test_container_coverage.py:315`, `tests/test_entry_coverage.py:204`) and the
  assembler merges it (its entry `web-server` is in the printed tree, and the record does not hold it). Fix:
  move it to `tests/responses/` under the key-free request identity that names it, and read it through the
  injected producer. Owner: `docs/ARCHITECTURE.md` §1.1, and `tests/test_api_requests.py:649-650`, which
  pins it as corpus material and so keeps the violation.
- The response-set pin cannot see that case: `tests/test_api_requests.py:646` compares names between the two
  sets, so a response that lives inside the corpus passes it. Fix: state the rule as a property of each file
  (a root element of `response` is not a Panorama export), not as a name comparison. Owner:
  `tests/test_api_requests.py`.
- `tests/` is the only directory that holds files with no index, so its 50 test modules and its three sets are
  named only in prose, and the three files in `tests/responses/` are named nowhere. Fix: give `tests/` an
  index, or state in §1.1 that the test set is named by the root index. Owner: `docs/ARCHITECTURE.md` §1.1.
- Path builder: `tests/test_golden_files.py:23` builds `GOLDEN_DIR` with `Path(__file__)`, the only set path
  built outside `tests/conftest.py`. Its regeneration note (lines 13-14) copies `.tf` files to the case root,
  which is not where the goldens live. Owner: `tests/conftest.py` and the file header.
- Pins that read the tracking markdown and require an open item to stay open: `tests/test_api_path.py:462-463`
  and `tests/test_sanity_gate.py:576-577` read `backlog.md`. `AGENTS.md` requires a completed finding to leave
  the markdown, so a housekeeping commit fails these pins. Fix: keep the fact in the test as data and name the
  open item in the document without asserting its wording. Owner: those two tests.
- Second definitions of one rule: `RESOURCE_RE` is defined four times (`tests/conftest.py:40`,
  `tests/test_coverage_matrix.py:43`, `tests/test_dependency_wiring.py:38`, `tests/test_scope_objects.py:48`)
  and the four patterns are not the same; `TERRAFORM` is defined four times (`tests/conftest.py:37`,
  `tests/test_dependency_wiring.py:35`, `tests/test_sanity_gate.py:68`, `tests/test_terraform_validate.py:33`).
  Fix: read both through `tests/conftest.py` and state the capture group once. Owner: `tests/conftest.py`.
- The §1 module table names 20 of the 22 `src/` modules: `commit_actions.py` and `api_to_terraform.py` are
  missing. `to-do.md` states that both path 2 modules must be in that table. Owner: `docs/ARCHITECTURE.md` §1.
- Pins that pass without measuring anything, because the golden case holds no `.tf` file at the case root:
  `tests/test_data_blocks.py:233-234`, `tests/test_ownership.py:530-532`,
  `tests/test_reference_edges.py:346-348`, `tests/test_unit_manifest.py:510-512` compare an empty set with an
  empty set, and they key by `p.name`, so two units that write the same file name collapse. Fix: read the set
  the way `tests/test_golden_files.py:42,50,54` reads it (`rglob`, keyed by the path from the case directory).
  Owner: those four tests.
- Guarded vacuity: `tests/test_commit_actions.py:329-330` asserts only when the run wrote a file, so a fixture
  that writes nothing counts as a pass. Owner: `tests/test_commit_actions.py`.
- Self-referential pin: `tests/test_api_requests.py:576` asserts the length of the test's own harness list.
  Owner: `tests/test_api_requests.py`.
- Provider-schema pins that never run in CI: 9 modules (20 pins read the schema fixture in their arguments,
  more reach it through module helpers) read the schema through `tests/conftest.py:107-147`, which skips
  without the terraform binary or the provider cache. The matrix job
  runs plain `pytest` on a runner with no terraform, and the `terraform-gate` job runs only
  `tests/test_terraform_validate.py`, so those pins hold only on a developer machine. Fix: run the nine
  modules in the terraform-gate job, or record the pins as measured facts with the date, as the provider-fact
  entries above do. Owner: `.github/workflows/python-tests.yml`.
- Skip that hides a failure: `tests/conftest.py:114` and `:138` report a missing provider cache as a skip, so
  a network failure reads as a pass. Owner: `tests/conftest.py`.
- Two ways to exclude a hostile fixture: the tool's read rule, and a name rule (`startswith('hostile_')`) in
  `tests/test_commit_actions.py:53`, `tests/test_data_blocks.py:41`, `tests/test_data_file_gate.py:40`,
  `tests/test_import_blocks.py:37`, `tests/test_round_trip.py:152`, `tests/test_ownership.py:289`,
  `tests/test_unit_manifest.py:483`, while `tests/test_container_coverage.py:318-321`,
  `tests/test_entry_coverage.py:205-208` and `tests/test_ownership.py:291-294` use the rule. The two agree on
  the three committed fixtures today and diverge when a fixture is refused by the rule but not named, or named
  but accepted. Fix: read the exclusion through `tool.refusal_reason` or `xml_input.check_bytes` in every
  corpus pin. Owner: `tests/conftest.py`.
- Pins that restate an owner table as a measured count, so they cannot detect a wrong table entry and fail only
  when the table changes: `tests/test_build_kitchen_sink.py:96-98,112,150,159`,
  `tests/test_filter_containers.py:330-333,373`, `tests/test_resource_mapping.py:72-76`,
  `tests/test_property_coverage.py:198`, `tests/test_data_file_gate.py:156-157,482`. Each carries a measured
  date instead of a derivation. Fix: state each as a property of the table (the count derived from the rows),
  and keep the measurement in the document. Owner: those tests.
- Order pins that read dict insertion order: `tests/test_parse_rules.py:12,41,122,163` and
  `tests/test_parse_profiles.py:91` assert `list(by_name) == [...]`, which pins document order and assumes the
  names inside one fixture are unique. Owner: those tests.
- Name collision in the flat `src/` namespace: `ROW_FIELDS` is three different row shapes
  (`src/site_data.py:63`, `src/commit_actions.py:75`, `src/import_blocks.py:53`) and a fourth meaning in
  `tests/test_coverage_matrix.py:166`. Owner: `docs/ARCHITECTURE.md` §1 (rename to one shape name per table).
- Tracking counts that do not agree with measurement: `docs/COVERAGE_MATRIX.md` §The matrix states 40 rows and
  `README.md:102` states 34, while `resource_mapping.COVERAGE_MATRIX` holds 42 (`panos_certificate_import` and
  `panos_certificate_profile` are in the code table but not in the document table); `docs/LICENSING.md`
  §The split, measured states 2,172 upstream lines and 57,157 ours against 2,155 and 57,245 measured with
  `git blame`, 50,008 in `src/`, `tests/` and `tools/` against 50,012 measured, and 121 commits against 127;
  `to-do.md` keeps completed phase detail for Phase 8A and Phase 8B, and lists F8.9 as open while `git log`
  records steps 1 to 3 committed (`src/api_to_terraform.py` exists). `agent-status.md` agrees: 1,641 pins
  against 1,641 collected, and the fixture set measures 71 (68 accepted, 3 refused by the F3.8 rule). Owner:
  the tracking markdown.
- Document pin claims that name a test that does not exist: `backlog.md:24`
  (`tests/test_container_coverage.py::test_report_declares_the_profile_name_column`), `docs/ARCHITECTURE.md:1527`
  (`tests/test_parse_network.py::test_parse_rip`, actual name `test_parse_rip_reads_the_levels_the_table_states`,
  line 549), `docs/API_CONVERSION_PATH.md:30` (`tests/test_site_data.py::test_the_module_defines_no_second_naming_rule`,
  actual name `test_site_data_defines_no_second_naming_rule`, line 708). Owner: the three documents.
- Documentation-wording pins: 4 pins read `docs/` prose (`tests/test_api_requests.py:292,294,695`,
  `tests/test_container_coverage.py:420,445`) and 2 read `backlog.md` (`tests/test_api_path.py:463`,
  `tests/test_sanity_gate.py:576`), including negative wording checks a tool cannot satisfy. No pin reads the
  root index, `AGENTS.md`, `examples/README.md` or `tools/README.md`, so the layout rule has no pin. A wording
  edit fails CI. Fix: keep these as document-review checks outside the test set, and pin the index rule in one
  place. Owner: those tests, `docs/ARCHITECTURE.md` §1.1.

## Codebase audit findings (measured 2026-11-12)

The audit read the parse set, the emitter set, and `src/split_device_groups.py` against the rule owners
(`entry_coverage.py`, `write_path.py`, `naming.py`, `resource_mapping.py`, `unit_manifest.py`,
`sanity_checks.py`). Each finding below was measured on a probe run or by a direct read. Nothing was changed
by the audit. The report is the chat response; only the actionable findings are here. Probe inputs and outputs
are in `/tmp/opencode/` and are not part of the tree.

### Parse set

- Silent drop: `parse_interfaces` stores `zone` and `virtual_router` as `None` and never assigns a value read
  from the XML (`src/panorama_to_terraform.py:1442-1443`), and it keeps `tag` only for a subinterface entry
  (1504). It reads the address list as `ip/entry` (1455-1458, 1496-1497), so the member form the export can
  state is dropped, while every other field it reads through `_get_single_value` (2928) accepts both shapes.
  No emitter prints these three fields. Measured probe `/tmp/opencode/probe5.xml`: an entry that stated tag 7,
  zone `trust`, virtual router `vr1`, and two member addresses printed `layer3 = {}` with no field line. Fix:
  read the three fields and both address shapes, or state them as report-only in the interface row. Owner:
  `parse_interfaces`, and the interface row of `resource_mapping.COVERAGE_MATRIX`.
- The property scan cannot report these drops: `captured_fields` skips a field whose value is empty
  (`src/entry_coverage.py:102, 405-411`), so a field the parse stored as `None` is never a finding, and a field
  the parse never stored is not in the set at all. Fix: state the scan's blind side in the F4.4 rule, or count a
  declared field that no parse method stores. Owner: `src/entry_coverage.py` §F4.4.
- Unrecorded read: 11 name guards `continue` without a record (`523, 1762, 1805, 2043, 2184, 2207, 2265,
  2305, 2389, 2409, 2469`), against the report rule that one line names every entry the parse read. Every other
  name guard (47 of the 58) calls `mark_skipped` in the same place, so its entry has a line. Measured probe
  `/tmp/opencode/probe_area.xml`: an unnamed `ospf/area` entry produced no block and no line, the report counted
  `skipped 0`, and only the parent `vr1` row named a gap; the same report rule states that an entry with no name
  is "recorded by design", which the 11 guards do not record. Fix: call `mark_skipped` in each guard. Owner:
  those parse methods.
- Unguarded path: `parse_schedules` stores a nameless recurring child as `{'name': None}` (1184-1187), and
  `generate_manual_setup_report` joins the names (5707) → `TypeError`, exit 1, and half-written output (probe
  `/tmp/opencode/probe_sched3.xml`: only `provider.tf` in the unit). Fix: skip a child with no name through the
  record.
  Owner: `parse_schedules`.
- Coverage gap: `_parse_router` reads only `routing-table/ip/static-route/entry` (1760), so an entry under
  `protocol/static-routes` produces no block and no row of its own; it appears only as a property count on
  the parent row. Measured probe `/tmp/opencode/probe_router.xml`: `Per-entry report: 2 entries read`,
  `Property entries inside config-object entries: 4`, and the route `r1` printed nothing. Fix: read both
  shapes, or state the second shape in the virtual-router row. Owner: `_parse_router`,
  `src/entry_coverage.py`.
- `_protocol_field` reads a `number` field with `text.isdigit()` (2676), so a negative or non-integer value is
  dropped with no report line (probe `/tmp/opencode/probe9.xml`: `set-med -1` printed only `name`), and
  `entry.find(xml_name)` (2665) takes only the first match. Fix: use the shape rule for a number and state the
  single-match limit. Owner: `_protocol_field`.

### Naming and printing

- Second digest: the static-route block name is built as `f"{resource_name}_{route['name']}"` (5105-5112) from
  an already-digested name, then `declare_block_name` sanitizes and digests it again (3211-3214) → measured
  `vr1_3f0e80e0_r1_8c64c16e`, against §5. The `_declaration_index` key holds that double-digested name, so a
  reference by the route's own name cannot resolve. Fix: pass the route name, not the built name. Owner:
  `generate_virtual_routers`, `declare_block_name`.
- Second source for one rule: `declare_block_name` hardcodes `'unnamed'` (3211) while `naming.UNNAMED` (27) is
  the §5 fallback. Fix: read `naming.UNNAMED`. Owner: `src/naming.py`.
- Collision: `printed_value` records each value under its §5 name in a dict keyed by that name (3657), so two
  values in one unit that sanitize to the same name hold one entry and the last value wins; two
  `REFERENCE_ONLY` entries whose names sanitize identically share one declaration. `naming.variable_name` maps
  `-`, `.` and `_` to the same separator (`src/naming.py:32-47`). Measured by read, not by probe. Fix: refuse a
  name collision inside a unit, or key the record by the entry. Owner: `printed_value`.
- Order rule split: `hcl_value` prints a dict in the order the parse built it (3740-3741), while the two
  emitters that call it sort the fields they print (3831, 3880), so one object prints in two orders at two
  levels. No document states which order a nested object takes. Fix: state the order for nested keys. Owner:
  `hcl_value`.
- Redundant gate, second rule: `check_control_chars` (`src/sanity_checks.py:1386`) reads the printed `.tf`
  text, and `escape_string` strips the remaining C0 control characters and DEL from a value (3366) before the
  text is printed, so for a value the gate can only re-check what the escape path already removed. The tool's
  own XML reader refuses a control character in text and in a character reference, measured both ways
  (`&#7;` → "reference to invalid character number", a raw `0x07` byte → "not well-formed (invalid token)"), so
  no value reaches the printer with one from the read layer. The escape rule stays needed for a value that
  arrives from the JSON state file, which states no control-character rule, so the two rules are not the same
  rule. Fix: state which layer owns the control-character rule, or make the gate read the value before the
  escape. Owner: `src/sanity_checks.py`, `escape_string`, `src/xml_input.py`.
  Whitespace is not one rule either: `_get_text` (2915), `_get_members` (2920), `_get_single_value` (2928)
  and `_protocol_field` (2658) return the text as the export states it, while `_list_names` (447) strips.
  the splitter's `_device_names` (`src/split_device_groups.py:56`) strips too. Measured probe
  `/tmp/opencode/probe_ws.xml`: a device group that states `  spaced  ` prints `description = "  spaced  "`,
  and the `control_chars` gate passes for the same run. Fix: state one rule for the value helpers. Owner: the
  value helpers, `src/split_device_groups.py`.
- Order contradiction: two emitters print fields in sorted order (3831, 3880) while their docstrings say the
  fields print in the table's order (3813, 3863). `parse_filter_containers` hardcodes the six filter paths
  (2699-2705) in an order that is not `FILTER_PATHS` (`src/resource_mapping.py:3793`, the sorted table) while
  claiming the table is the source. Fix: print in the table's order, or state the sorted rule. Owner: those
  emitters and `parse_filter_containers`.
- `UnitText.add_once` decides "stated once" by testing whether the text is a substring of the text already
  accumulated for the unit (3037-3042), so header prose that contains the section text stops the section from
  being written. Fix: keep a per-file once record. Owner: `UnitText`.
- Shape owner bypassed: `VALUE_VARIABLES` states `key` as `reference_only` (`src/resource_mapping.py:1261`), but
  the IKE gateway emitter prints it as a literal through `hcl_value` (6117), so no gate reads it. The parse
  always writes the placeholder (2799, 2847), so no credential reaches a file today. Fix: print the reference, or
  state the exception in the table. Owner: `generate_vpn_config`, `resource_mapping.VALUE_VARIABLES`.

### `src/split_device_groups.py`

- Write path: the splitter writes XML through `ElementTree.write` (281), outside `write_path.py`, and the files
  it writes have no trailing LF (measured with `od`). The writer scan lists `write_text`, `write_bytes`,
  `os.linesep` and `open(...'w')` (`tests/test_write_path.py:441-448`), so this writer is not seen by the gate.
  Fix: write through `write_path.py`, or add the element writer to the scan. Owner: `src/write_path.py`,
  `tests/test_write_path.py`.
- Naming: file names are built with two `replace` calls (275) instead of `naming.sanitize`, so a device-group
  name that states any other character keeps it, and two names that read the same after the two replaces
  collide. Measured probe: device groups `DG/A` and `DG A` wrote one file, `DG_A.xml`, and the second write
  replaced the first. Reading `naming.sanitize` would put the file name under the one rule but would not
  stop the collision, because both names sanitize to `dg_a`; the rule needs a collision decision. Fix: read
  `naming.sanitize` and refuse or number a collision. Owner: `src/naming.py`, `src/split_device_groups.py`.
- Identity: the splitter keeps name-keyed tables (45-53, 86-95) and takes the first entry with a name
  (149-152), against §2.3, so a repeated device-group name is never written and one entry answers for two.
  Fix: key by the source line, as the converter does. Owner: `src/split_device_groups.py`,
  `docs/ARCHITECTURE.md` §2.3.
- Shared-section merge (174-193): the dedupe reads `findall('.//entry')`, so a name matches at any depth and a
  matched entry from a later section is dropped; an unmatched entry is appended directly under the container, so
  its path is flattened. Measured probes: `/tmp/opencode/p1.xml` → `pout_split/DG1.xml` kept `y` as
  `interface/entry` instead of `interface/virtual-wire/units/entry`, and the converter reports that entry as
  `unaccounted` with "no parse method reads interface"; `/tmp/opencode/p2.xml` → `pout_split2/DG2.xml` dropped
  the second `x` entry because the first `x` matched at a different depth. Fix: merge by path and name, and keep
  the entry's path. Owner: `src/split_device_groups.py`, `docs/DEVICE_GROUP_SPLITTING.md`.
- Dead branch: `if dg_config is None` (270-272) cannot be true, because `parse_device_groups` (47-51) only
  names entries that exist in the tree. Fix: remove the branch or make the extraction able to fail. Owner:
  `src/split_device_groups.py`.

### Error rule

- `is_refusal` (6697-6701) counts any `ValueError` as an input refusal, against its own docstring ("anything
  else is an unexpected error and keeps its traceback"), so a `ValueError` raised inside the tool prints as a
  refusal with no traceback and exit 1. `main()` catches every exception (7281-7287). Fix: state the refusal
  kinds as the input-layer exceptions. Owner: `is_refusal`, `src/xml_input.py`.
