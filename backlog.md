# Backlog

Tech debt, out-of-scope items, and nice-to-haves. Promote items to `PLAN.md` when they become in-scope.
Completed work is not recorded here; the git history and the owner document hold it.

## Tech Debt

- **Repository layout (open).** State the layout as a rule, then move the files that break it:

  - The root holds `AGENTS.md`, the two readme indexes (`README.md` and `docs/README.md`), and the tracking
    markdown (`PLAN.md`, `backlog.md`, `to-do.md`, `acceptance.md`, `agent-status.md`).
  - `docs/` holds every other document. `tests/` holds every test. `src/` holds the tool's modules.
    `tools/` holds the developer scripts. `examples/` holds the sample input and the two example text
    files, and the canonical sample output is the golden set `tests/golden/` pins byte for byte
    (`examples/example_terraform_output.txt`). `terraform_output/` is the default value of `--output-dir`
    and is ignored, so it holds no committed sample.
  - Each index names every document under it, so a file outside an index is a finding.

  Out of place today:

  - `conftest.py` is at the root, while every test is in `tests/`. Move it to `tests/conftest.py`. It holds
    the helpers the tests read the layout through (`tf_files`, `parts`, `file_text`, `written_bytes`), so it
    stays one file.
  - The tool's 20 modules are flat at the root. The move to `src/` needs the import rule decided first,
    because the tests import a module by name (`import sanity_checks`) and `conftest.py` builds a module path
    from `REPO_ROOT`. The pins that read module sources (`tests/test_safe_input.py`, the writer scan, the
    property grounding test) read those paths, so they change with the move.
  - `tests/` is flat: the test files sit beside `fixtures/` and `golden/`. Group the tests by rule area, or
    state that a flat test directory is the rule, so the layout does not change again.
  - `quick_start.sh` and `sample_panorama_config.xml` are at the root. `quick_start.sh` is a developer script,
    so it belongs in `tools/`; the sample config and the example output text belong in `examples/`, with
    `examples/README.md` as its index.
  - The `.gitignore` exception for `examples/**/*.xml` matches nothing until the sample config moves there, and
    the comment in `.gitignore` names the test corpus by a path the move changes.
  - `AGENTS.md` says "read all the markdown files in the root directory". The tracking set above is what that
    means; state the set in `AGENTS.md`, so a document move does not depend on habit.

  Do the moves as one commit with `git mv`, after the open feature work lands, and change no code other than
  the paths the pins read. Run `ruff check .` and `pytest` after the move, so the suite stays green.

- `tools/build_kitchen_sink.py` still calls `ET.parse` directly. Accepted
  (F3.8): it is a developer tool that assembles the kitchen-sink fixture
  from files already committed to this repository, not an entry point that
  reads an operator's export. Leave it alone unless it ever takes a
  command-line path.

- Property gaps the scan does not report, because the container that holds them has
  no matrix row: only an `emitted` container can name the properties an emitter reads.
  The scan scope rule pins this in
  `tests/test_property_coverage.py::test_scan_scope_is_the_entries_a_matrix_row_covers`.
  Measured on the corpus:
  - `report` containers: `description` and `destination_addresses` on an application
    override rule. The report prints the rule but does not read these fields.
  - `count-only` (`parse_regions`): `addresses`. Nothing reads a region at all.
  - `nested-block` (a layer-3 subinterface inside its parent interface row): `parent`.
    The nested block prints the parent name from the parent object, not through the
    child object, so the read is not recorded on the child.
  - `bookkeeping` (association table and scope facts): `devices`, `templates`.
  These are not findings today, and each one needs a rule before it can become one: an
  emitter must exist, or the report writer must read the field it names.

- The console prints the gap lines only; a property finding and a shadow print in
  `CONVERSION_REPORT.txt`, because each names a matrix row. Printing findings on
  the console needs the console line shape decided first, so a run does not print a
  matrix row it has no room for. A shadow line also names a source, so its shape needs
  the source field decided with it.

- The shadow parent index is keyed by (matrix row, entry name), so a parent name the export
  declares in two scopes gives one key and the first parent row wins, in report order. Identity
  is (device group, vsys, type, name) (`docs/ARCHITECTURE.md` §2.1), so a key that also named the
  parent scope would say which parent entry the child repeats. Not built: one child entry is one
  finding today, and the parent scope is not a row key.

- `panos_aggregate_layer3_subinterface` has no corpus entry to measure: the container
  table maps an aggregate subinterface to the ethernet subinterface row, so no entry
  reaches it. That row's properties are grounded in the emitter source only
  (`tests/test_coverage_matrix.py::test_declared_property_is_a_key_the_emitter_reads`),
  and the parity test names it as the one unmeasured row. A fixture entry that reaches
  the aggregate shape closes this.

- `AGENTS.md` points to `lib_docs/` for API cheat sheets. The directory is not in the
  repo. Add the cheat sheets, or remove the reference.

- Parser extraction gaps found by the parse unit tests (each drops data; fix each
  when a report confirms it in a fixture):
  - Application filter `description` is not extracted.
  - Schedule `description` is not extracted.
  - Security rule profile group references are not extracted.
  - NAT rule `service` in member-list form is captured as whitespace text; only text form works.
  - `disable-override` is extracted for `panos_address` (F3.4) and for `panos_service` (F6.2).
    The pinned schema declares the flag for 25 types, so a matrix row that does not name the
    property states `unknown` in `OWNERSHIP.json`. The parsed types that can carry the flag are not
    extracted: `panos_address_group`, `panos_administrative_tag`, `panos_application_group`,
    `panos_custom_url_category`, `panos_external_dynamic_list`, `panos_security_profile_group`,
    `panos_service_group`.
  - Regions are parsed but reach no output: `parse_regions` returns objects
    that only the console count uses. Recorded by F3.10 (`docs/ARCHITECTURE.md`
    §2.4). The per-entry report lists each region row as a gap, so the operator sees
    it; the parse still writes no output for a region.

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
  the provider to state a config location inside a stack, so the entry stays a report finding until then.

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

- Certificate entries have no coverage matrix row, so a certificate entry is an
  `unaccounted` finding today (`device-group/entry/certificate`, pinned in
  `tests/test_container_coverage.py::EXPECTED_FINDINGS`). `panos_certificate_import`
  is a resource with no data source, and `panos_certificate_profile` is a resource
  that is in `LOCATION_SCHEMA` but in neither `EMITTED_TYPES` nor
  `NOT_EMITTED_TYPES`. The open work is: a `certificate` container row, an emitter
  that prints `local.pem.certificate` as the value and the key as the variable
  reference, and a decision for the profile row (emit, or state it in
  `NOT_EMITTED_TYPES` with the reason). A certificate the run writes no block for
  cannot be read through a data source, because the certificate entry has no name
  a reference resolves.

- A per-device template variable override has no place the provider can put it:
  `panos_template_variable.location` declares `template` and `template_stack` only,
  and neither sub-block has a device field. So the tool cannot generate the
  per-serial value the Panorama GUI holds. The parse must report a variable entry
  whose value is stated for one device instead of taking the stack value as the
  entry value. Not built: the corpus holds no such entry, so the rule needs a
  fixture that shows how an export states a device-level value.

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
- Dual-license legal review.
- The state source has no write path (F5.6). A run reports what a state document holds and never
  writes one, so a drift finding is an operator action, not an update.

## Nice-to-Haves

- Adopt `ruff format` as a gate. A one-time format pass of both legacy scripts is required first
  (about 1500 changed lines in `panorama_to_terraform.py`). Do it as its own task so the diff stays
  reviewable.
- Deeper post-run checks (beyond the gate (F4.1): parse the generated HCL and cross-check object
  counts against the input (round-trip; needs the F4.3/F4.4 coverage data); `tflint` integration.
  `sanity_checks.py` is the runtime home for the static rules.

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
- The sanity gate (F4.1) reads the output files, so it cannot see an entry that produced no file.
  F4.3 is the accounting for that case; the gate cannot replace it.
- The gate `location` check is presence only, for both block kinds. The resource sub-block and field
  shape stays pinned by `tests/test_multi_vsys_location.py`, because `terraform validate` accepts an
  unknown sub-block and drops it silently. The `data` shape is checked by the gate, because
  `DATA_SOURCE_SCHEMA` is data the gate can read (F5.5). A `resource` shape stays inside
  `LOCATION_SCHEMA`, which is the generator's subset, until the emitted shape becomes data the gate
  can read for both kinds.
- The placeholder check lists the VPN pre-shared key only. When F4.3 adds per-entry accounting, the
  expected placeholders should come from the same table that decides the report entries.
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
- The `parse_device_groups` row moved from `count-only` to `bookkeeping`. A device
  group name reaches the output through `location`, so the entry does produce output;
  only the entry itself is not a resource.
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
  change the exit code. The console prints the gap lines only.
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
- Open: the pruning rule, stated in `provenance.py` (F5.3). A cache entry
  is not pruned while a written record references it, and the reference is the `cache_entry`
  field of a parsed record, so the rule reads data and not a printed line. The prune action
  itself is not built: it needs the record directory decided first, because a record is
  written per output directory and a later run cannot know which records a prune action will
  read. A two-source run writes two records in one file, so the prune action reads a record
  file, not one record.
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
  needed. The gaps that stay are the choice levels, which state their alternatives as `selects`
  keys and no fields: the `one_of` rows and the auth profile levels. Measured 2026-11-03 against
  provider 2.0.14. A level becomes printable when a parse method reads it and the table has a row
  for it, because the emitter, the gate and the report all read that table.
- Decision for the redistribution route-map entry (F7.8): the row scope stops at the `match`
  and `set` rows, because those two rows state leaf fields only. The six levels inside them —
  `match.ipv4.address`, `match.next_hop`, `match.route_source`, `set.metric`, `set.ipv4`,
  `set.ipv6` — are therefore not table rows, so no parse method reads them and the gate refuses
  them in a hand-written file. `tests/fixtures` cannot state one of the choice alternatives for
  the community-list `type` level and keep a valid run, because the provider enforces exactly one
  entry for `type` (`regular`, `extended`, `large`), so `FILTER_XML_NAME_EXCEPTIONS` is grounded
  by the five pairs the fixture states, and the other ten pairs are the spellings the pango
  source measures.
- Open: the provider reads two attributes of one level as a choice, which the table has no word
  for, so the gate rule does not refuse a hand-written file that states both. Measured 2026-11-03
  with `terraform validate` (provider 2.0.14): an `ospfv3` auth profile entry accepts `ah` or
  `esp`, not both, and a `peer` entry refuses a `peer_address` that states `ip` and `fqdn` ("2
  attributes specified when one (and only one) of
  [...peer_address.ip.<.ip,...peer_address.ip.<.fqdn] is required").
  `tests/fixtures/auth_profile.xml` states the two levels in two entries, and
  `tests/fixtures/bgp.xml` states one attribute for `peer_address`, so both fixtures validate.
  The word for a choice between two fields of one level is F7.12, which F7.11 did not reach: the
  two other `single` levels inside a peer entry (`connection_options`,
  `subsequent_address_family_identifier`) accept more than one attribute, so they hold no choice.
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

## Design Decisions (the value the parse cannot carry)

- Decided 2026-10-31: a value the parse cannot carry prints as the variable reference, never as a
  literal. The provider marks these attributes `sensitive`: `panos_certificate_import`
  `local.pem.private_key` and `local.pem.passphrase`, the BGP, OSPF and RIP auth profile keys, the
  external dynamic list credentials, and the VPN pre-shared key. One table decides the shape, so the
  emitter, the gate and the `.tfvars` writer read `resource_mapping.VALUE_VARIABLES`; the literal half
  is held by `tests/test_robustness.py` (no generated file may contain the secret).
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
- `panos_certificate_profile` declares `certificate`, `block_expired_certificate`,
  `block_unknown_certificate`, `block_timeout_certificate`, `block_unauthenticated_certificate`,
  `use_crl`, `use_ocsp`, `certificate_status_timeout`, `crl_receive_timeout`, `domain` and
  `username_field`. The v1 names (`certificate_profile_certificates`, `block_expired_cert`) are not in
  the pinned schema, so an emitter for the profile row must use the v2 names.

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
- The credential rule needs one statement that covers both the fetch layer (the key from the
  environment only, never a generated file) and the generated provider block, which declares
  `panos_username` and `panos_password` variables. The provider reads `PANOS_API_KEY` from the
  environment, so the codebase shape is a host variable plus the key, not a credential pair.
- Local inspection mode (`config_file`, `panos_version`) exists in the pinned provider schema and
  could let CI plan against a committed export with no server. It is not a rule in this project, and
  a plan in that mode cannot show drift, so it is not a replacement for the state scan.
- The tool cannot derive a module from an export: a module is a standard a person writes. The tool's
  part is the data file a module consumes.
- Reports are per run. A codebase-level view (the units, the entries each owns, the managed boundary)
  is not built.
