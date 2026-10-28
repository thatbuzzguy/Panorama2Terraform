# Backlog

Tech debt, out-of-scope items, and nice-to-haves. Promote items to `PLAN.md` when they become in-scope.

## Tech Debt

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
  - Service object `disable-override` is not extracted (the address parser
    extracts it since F3.4; the service parser does not).
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
  credential material into generated HCL is not acceptable (F3.4). An EDL
  that authenticates to its fetch URL needs the credentials configured by
  hand; the converter cannot express them safely. Revisit only with an
  explicit secret-manager design (e.g. a `var.` reference, never a literal).
- Policy rules do not record which rulebase (pre, post, or shared) they came from. F2.5 chains are ordered per device group across all rulebases, which matches PAN-OS evaluation order for a single rulebase but mixes rulebases when a device group has both pre- and post-rules. F3.5 confirmed the provider can express it: `panos_security_policy_rules`, `panos_nat_policy_rules`, `panos_decryption_policy_rules` and `panos_pbf_policy_rules` all declare `location.device_group.rulebase` and `location.shared.rulebase` (v2.0.14 schema). F3.5 decision (2026-10-08): do not emit it. The parser does not record the rulebase, and the accepted value string is unverified — the provider binary carries the literal `pre-rulebase` and no `post-rulebase` literal, so the omitted-attribute default is the only safe output. Verify the value against a live target, then record the rulebase per rule, chain within one rulebase, and emit `rulebase` for the four rule types. Note that `location.vsys` declares no `rulebase` field, so a vsys-scoped rule cannot carry it at all and must be reported instead.
- Security profile bodies are not parsed (antivirus, anti-spyware, vulnerability, URL filtering, file blocking, WildFire, zone protection). The v2 provider has resources for them, but emitting empty profile objects would silently create misconfigured resources. F2.9 decision (2026-10-04): the names and descriptions go to `MANUAL_SETUP_REPORT.txt` with the reason; real emission waits for the profile body parsing.
- Schedules: `panos_schedule` exists in v2, but only entry names are parsed (day/time ranges not captured) and v2.0.14 has no monthly schedule support. F2.9 decision (2026-10-04): report entry; revisit when schedule parsing lands.
- IPsec tunnel monitor profiles have no v2 resource: `panos_monitor_profile` is the PBF path monitoring profile (`network/profiles/monitor-profile`), a different PAN-OS object — verified in the provider/pango source. F2.9 decision (2026-10-04): report entry.
- The six security profile categories are declared with an empty naming
  context (F3.1) because their emitter is a stub that writes no `location`
  at all: the objects carry `device_group` and `vsys`, but putting either in
  the digest would promise a scope the emitted resource does not have.
  F3.6 left them alone for that reason. When real profile bodies land, give
  them their device group or template context and regenerate the digests.
- Reference resolution order (F3.2, acceptance-recorded): the keyed chain is
  (referrer context, referrer vsys), then (Shared, referrer vsys), then
  (contextless, referrer vsys), then the flat first-declaration index. The
  flat index is not vsys-aware, so a name that exists only in another vsys
  still resolves through it. F3.6 gave the template-scoped types a real
  context (their template, else their device), so the flat index is no
  longer their primary route; it stays for call sites that pass no vsys.
- Device-aware resolution (F3.5, F3.6) covers only names a device declared,
  and only the interface generators declare a device. A name a device
  declared resolves inside that device; a deviceless referrer resolves it
  only when exactly one device declares it, and keeps the plain name when
  several do. A zone, address or profile name that repeats on two firewalls
  still resolves first-wins through the context chain. Extend the rule when
  a generator declares per-device objects other than interfaces.
- A template that targets two or more devices cannot say which device an
  unqualified interface name means, so a virtual router or logical router in
  such a template keeps `interfaces = ["ethernet1/1"]` as strings instead of
  referencing one firewall's resource (F3.6). The fix is per-target-device
  emission of the template's config, not a guess; it needs a fixture that
  shows how a real export distinguishes the two.
- `location.template_stack` is never emitted (F3.6). A stack holds device and
  template members, not config, so nothing in an export is placed in one. If
  an export ever nests config under a stack, report it rather than placing it
  there.
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

## Out of Scope

- The orchestrator is not this tool's job. The tool writes data an orchestrator reads: the unit
  manifest, the reference edges, the import blocks, and the `.tfvars`. It runs no plan, no apply,
  and no commit, and it manages no secrets. The rule is in `docs/CODEBASE_ASSEMBLY.md` §13.
- The Day 1 device bootstrap cannot be expressed in the pinned provider schema: no resource
  registers a device, defines an HA pair, sets a management interface, or holds an auth key. Serial
  registration, HA grouping, management IP, DNS, NTP, and the admin account stay outside the
  codebase. The fact is in `docs/CODEBASE_ASSEMBLY.md` §12.
- PAN-OS version matrix testing.
- Dual-license legal review (audit §6.8).
- The state source has no write path (F5.6). A run reports what a state document holds and never
  writes one, so a drift finding is an operator action, not an update.

## Nice-to-Haves

- Adopt `ruff format` as a gate. A one-time format pass of both legacy scripts is required first (about 1500 changed lines in `panorama_to_terraform.py`). Do it as its own task so the diff stays reviewable.
- Deeper post-run checks (beyond the gate (F4.1): parse the generated HCL and cross-check object counts against the input (round-trip; needs the F4.3/F4.4 coverage data); `tflint` integration. `sanity_checks.py` is the runtime home for the static rules; it now holds the F1.7 control-character rule and the placeholder rule.

## Notes on Already-Completed Work

- F3.6 (multi-device) found a wrong claim about ElementTree worth keeping:
  `ElementTree.append` does **not** reparent. It keeps no parent bookkeeping,
  so appending an element that already has a parent makes one element object
  a child of two trees, and a later mutation of either shows in both. The
  splitter therefore copies with `copy.deepcopy` for every element it takes
  out of the source export.
- F3.5 (multi-vsys) corrected a wrong assumption held since F2.3: v2
  `location` **does** have a `vsys { name, ngfw_device }` sub-block for the
  object types and the four policy-rule types. `panos_security_profile_group`
  is the emitted type that lacks it. `localhost.localdomain` is the PAN-OS
  placeholder for "this device", so it is never emitted as `ngfw_device`;
  the resource is reported instead. Shared entries emit `shared = {}`, not
  `device_group = { name = "Shared" }`.
- F3.9 (per-device-group reports) settled two facts worth keeping: `Shared` in
  `device_group` is the parser fallback for an entry it cannot place, so it is
  **not** a device group for an entry whose scope is a template or a device —
  the report prints a device group only when the export declares one, and the
  shared section is named `Shared`. And the report groups by the scope the
  export states, never by an association the converter could infer: a template
  section does not name the device group that device belongs to, because the
  export states the membership for the device, not for the entry.

- F3.4 (full object types) closed two F1.2 extraction gaps: service object
  tags are extracted and emitted, and dual-protocol services keep both legs
  in the parse model (the emit limit is a provider constraint, recorded
  above). Address `ip-wildcard`, `disable-override`, EDL `exception_list`,
  `expand_domain`, `certificate_profile` and the recurring schedules are
  parsed and emitted; address types with no v2 attribute (location, external)
  are report-only.
- F3.8 (safe XML input) closed the input risks and corrected two wrong
  claims held since F1.7: the `<!DOCTYPE` text search was **not** encoding
  safe (a UTF-16 export hid the DTD from it while expat parsed and expanded
  it — reproduced), and it refused legal input that only mentioned
  `<!DOCTYPE` in a prolog comment. The check now asks the parser. Also
  verified and relied on: with no DTD, expat expands no entity (`&a;` is a
  hard parse error) and fetches no external entity, because `xml.etree`
  installs no `ExternalEntityRefHandler`. `defusedxml` was considered and
  rejected — it would not cover the size risk, and the scripts stay
  standard-library only.
- F5.1 and F5.2 (source producers, landed 2026-10-26 and 2026-10-27) closed the producer
  boundary: the two checks run once, inside the door, so a producer cannot hand bytes
  different from the bytes it parses. The fetch producer asks for no `Accept-Encoding`, so
  the bytes it hands are the bytes on the wire; a `Content-Encoding: gzip` response would be
  a decompression bomb only if the cap ran on the compressed body. The cache entry name
  excludes the credential, so two different keys for the same request find one entry — the
  fact a shared CI cache depends on.
- F2.4 (emitter rewrite) also fixed two F1.6 extraction gaps: dynamic address group filters are serialized from the structured `<filter>` XML, and IPv6 address objects (`<ipv6>`, `<ipv6-range>`) are parsed and emitted.

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

- The conversion report (F4.3) keys on logical entries — an `<entry name>` plus its properties — not physical lines; one entry spans many lines in the XML. The reported line number is the entry's opening tag.
- The coverage matrix (F4.4, former F2.8) is a permanent maintenance duty: every
  emitter change must keep the property list on its row honest, or the property
  section of `CONVERSION_REPORT.txt` silently lies. The entry-mark rule (F4.3) is
  the test that makes an unmarked element read fail CI.
- The parser extraction gaps listed above will surface in the F4.2/F4.3 reports; fix each gap when the report confirms it in a fixture, rather than fixing them speculatively now.
- The sanity gate (F4.1, landed) reads the output files, so it cannot see an entry that produced no file. F4.3 is the accounting for that case; the gate cannot replace it.
- The gate `location` check is presence only, not shape. The sub-block and field shape
  stays pinned by `tests/test_multi_vsys_location.py`, because `terraform validate`
  accepts an unknown sub-block and drops it silently. Move the shape rule into the gate
  when the location shape is data the gate can read, not a per-type literal inside an
  emitter. The property matrix (F4.4, landed) names the properties a row reads, which
  is the data a shape check needs; the location sub-blocks are not that data yet.
- The placeholder check lists the VPN pre-shared key only. When F4.3 adds per-entry accounting, the expected placeholders should come from the same table that decides the report entries.
- Consider a `--checks` selector on the converter CLI if the gate grows; today every check runs on every conversion, and a WARN never changes the exit code.

## Design Decisions (F4.2, landed 2026-10-20)

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
## Design Decisions (F4.3, landed 2026-10-20)

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

## Design Decisions (F4.4, landed 2026-10-26)

- The read record is a run-time measurement, so `mark` returns the recorded object and a
  parse method must build its object through what it returns. The record stays off during
  the parse and the run turns it on before the first generator call, because a key the
  parse method read off the XML element is not a property an output used.
- A property name is the measured key name, so the grounding test can find it as a string
  in the emitter source. `declared_type` and `other` stay on the `panos_address` row
  because the manual setup report reads them for a report-only address.
- The entry name and the four scope facts are the row identity, not properties, so the
  parity check compares the captured fields only.
- `emitter` names two methods when a report writer reads properties the `.tf` emitter does
  not. Only `panos_address` has this today, because the manual setup report prints a
  report-only address from the same parsed object.
- The scan scope is the entries an `emitted` container row covers, because only a row can
  name the properties an emitter reads. A finding is an operator action, so it does not
  change the exit code. The console prints the gap lines only.
- A manual report section prints what the parse captured for it, so a captured field is
  either printed or reported as unread. The BGP and OSPF sections now name the scope and
  the router, print the peer-group nexthops and the redist rules, and read the routers
  through one path.
- The conversion report reads a scope name from the scope `<entry>`, not from the container
  element, so a run inside a declared scope prints its device-group, template, and device
  sections instead of a blank scope.

## Design Decisions (Epic 5 sources)

- The parse layer keeps the ElementTree tree. The fetch layer is a byte producer, never the
  input model, because four things are keyed on the tree: the container table rows (XML
  paths), the entry ledger marks, the parent walk that gives the four scope facts (§2.2),
  and the expat line map (`ET.TreeBuilder` reports no line, so only the expat handler path
  can record one). A device-object model has no line number, so the F4.2 reporting cannot
  survive it.
- Standard library only, closed by F5.2 (landed 2026-10-27). `source_fetch.py` uses
  `urllib.request`. This supersedes the planned `pan-os-python` producer: the SDK exposes no
  redirect hook, so the scheme rule cannot be enforced through it, and a standard-library
  producer enforces all three https rules and needs no test skip. No module in the project
  imports a third-party package, so the F3.8 rule needed no narrowing after all.
- The response wrapper is normalised, one shape per request shape (F5.2 and F5.4, landed
  2026-10-27); the rule is in `ARCHITECTURE.md` §3. The fetch layer checks the response against
  the request it made, so a per-scope shape is not guessed from what it looks like, and the
  container table still names no wrapper row.
- Open: the pruning rule, stated in `provenance.py` (F5.3, landed 2026-10-27). A cache entry
  is not pruned while a written record references it, and the reference is the `cache_entry`
  field of a parsed record, so the rule reads data and not a printed line. The prune action
  itself is not built: it needs the record directory decided first, because a record is
  written per output directory and a later run cannot know which records a prune action will
  read. A two-source run writes two records in one file (F5.4), so the prune action reads a
  record file, not one record.
- Corrected by the check on 2026-10-27: a data source schema does declare required attributes.
  For every one of the 128 data sources `location` is required, and for every data source that has a
  `name` attribute `name` is required (106 types have both; 22 have no `name`, the settings, policy and
  collection shapes). So `terraform validate` can enforce `name` and `location` on a `data` block for
  those 106 types. The gate rule F5.5 still needs is the one that reads a `data` block at all:
  `sanity_checks.py` reads only `resource` blocks, so a run without `--validate` checks no `data`
  block, and validate accepts a `location` sub-block the type does not declare by dropping it
  silently.
- Open: the provenance record names the host and the scope, never the credential. The key
  rule itself (environment only, never argv, never a generated file) is in `ARCHITECTURE.md` §3.
- Provider data sources, verified against 2.0.14 with
  `terraform providers schema -json`: 128 data sources mirror the 128 resources, and
  every emitted type has one. 126 types have the identical attribute set and the
  identical `location` sub-blocks. The two mismatches are name level:
  `panos_certificate_import` and `panos_virtual_router_interface` have a resource and
  no data source; `panos_certificate` and `panos_predefined_dlp_file_type` have a data
  source and no resource. Only `panos_addresses` returns a collection (a map keyed by
  name). `panos_device_group`, `panos_template` and `panos_template_stack` return the
  membership facts `parse_associations` builds from the export; a data source resolves
  at plan time, so it cannot feed a generation-time report. The check ran again on
  2026-10-27 for F5.6 and the counts and the name-level mismatches hold, so
  `DATA_SOURCE_SCHEMA` can be written from that schema, not from memory.
- A data source schema declares no required attributes, so `terraform validate` cannot
  enforce `name` and `location` on a `data` block. That rule needs its own gate check,
  for the same reason the `location` sub-block shape is pinned by test and not by
  validate.
- BGP and OSPF have neither a resource nor a data source, so read-through cannot cover
  the report-only areas.
- Read-through is opt-in per declared scope. A plain string already applies, because
  Panorama resolves an object name through its own inheritance at commit time, and one
  `data` block is one plan-time API call. A `data` block for a name that does not exist
  fails at plan, not at validate, so a read-through run must be labelled in the
  generated `README.md`.
- The state document is a reference source, so it reads through the same door and the same row rule
  (F5.6, landed 2026-10-27); the rules are in `ARCHITECTURE.md` §3 and §3.2. A state entry has no
  source line, because only the expat handler path records one, so its position is its resource
  address, and the scan reads the matrix row through the resource type instead of through a container
  path.
- Open: the state scan compares only a property both sides hold by the same name (F5.6). The matrix
  row names the key the emitter reads and the state document names the attribute the provider stored,
  so no mapping rule exists between them: the parse key `tags` and the provider attribute `tag` are
  not compared. A comparison table would have to be verified per type against the provider schema, the
  way `LOCATION_SCHEMA` is, so the scan keeps the same-name rule until such a table exists.

## Design Decisions (Epic 6, planned)

The design record is `docs/CODEBASE_ASSEMBLY.md`. Each item below is a decision, not a rule the code
holds.

- The reference between units: the provider `data` block (F5.5), or the state of another unit through
  a remote state data source or a platform output. The remote state route needs outputs, and the
  generator writes no outputs today. The choice decides which gate rule the codebase needs.
- The owner of a repeated name. Panorama resolves it through inheritance at commit time, so a repeated
  name is one object on the device and two entries in the export. `panos_address` declares
  `disable_override`, and the service parser does not extract it (the extraction gap above). Until the
  rule names the owner, two units can claim one object.
- Import agreement: the gate reads `resource` blocks only, so an `import` block is not checked today. A
  codebase that writes import blocks needs a rule that an import block agrees with the resource block it
  names (the same type, the same local name, the same location).
- The import position for the four `*_policy_rules` types must be the position the live config holds,
  not the create-time position the generator emits: a chain anchors at `where = "last"`, which is not
  the position of a rule that already exists. The F3.5 rulebase decision gates this, because the rulebase
  is part of the import object for those types.
- Actions: the pinned schema declares `panos_commit` and `panos_push_to_devices`. Actions need Terraform
  1.14 or later, the committed goldens declare no Terraform minimum, and the gate reads no `action`
  block, so a codebase that emits actions needs both a minimum and a gate rule.
- The credential rule needs one statement that covers both the fetch layer (the key from the environment
  only, never a generated file) and the generated provider block, which declares `panos_username` and
  `panos_password` variables. The provider reads `PANOS_API_KEY` from the environment, so the codebase
  shape is a host variable plus the key, not a credential pair.
- The value-to-variable mapping must be a pinned table, the way `LOCATION_SCHEMA` is, not a choice
  inside an emitter. The site data format stays JSON, because the project keeps the standard library
  only (F5.2).
- Local inspection mode (`config_file`, `panos_version`) exists in the pinned provider schema and could
  let CI plan against a committed export with no server. It is not a rule in this project, and a plan in
  that mode cannot show drift, so it is not a replacement for the state scan.
- The tool cannot derive a module from an export: a module is a standard a person writes. The tool's
  part is the data file a module consumes.
- Reports are per run. A codebase-level view (the units, the entries each owns, the managed boundary) is
  not built.
- Hygiene: the committed sample output directory `terraform_output/` states provider `~> 2.0.7` in
  `provider.tf` and declares a `device_group` variable in `variables.tf` that the generator no longer
  emits (F2.10). The generator pins `~> 2.0.14`. Regenerate the sample or drop it.
