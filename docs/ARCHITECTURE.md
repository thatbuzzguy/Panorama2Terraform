# Architecture

This document states the whole pipeline in one place: how the converter reads
an export, what it stores, how it names and places a resource, and what it
reports instead of emitting.

Read this page when you need to know why the output looks the way it does.
User-facing summaries live in [README.md](../README.md). Per-type mapping lives
in [RESOURCE_MAPPING.md](RESOURCE_MAPPING.md). The coverage matrix lives in
[COVERAGE_MATRIX.md](COVERAGE_MATRIX.md).

Each rule below names the test that pins it. A rule with no test is labelled as
a design rule enforced by construction.

## 1. Modules

| File | Role | Rule it keeps |
|---|---|---|
| `panorama_to_terraform.py` | The converter: `PanoramaParser` (read and model), `TerraformGenerator` (model and write), `main()` (order) | reads input only through `xml_input.parse_xml` |
| `xml_input.py` | The only input read, shared by both entry points, through one producer boundary (F5.1) | size cap checked before the read for a file, and on the bytes handed by any producer; DTD refused by the parser |
| `resource_mapping.py` | The verified provider contract: `EMITTED_TYPES`, `REPORT_ONLY_TYPES`, `NOT_EMITTED_TYPES`, `LOCATION_SCHEMA`, `INTERFACE_RESOURCE_TYPES`, `COVERAGE_MATRIX` | the single source of truth; no resource name or attribute from memory |
| `split_device_groups.py` | Optional pre-processing: one XML file per device group | joins scopes on the device the export lists; copies with `copy.deepcopy` |
| `container_coverage.py` | The container table (§3.1) and the section rule | the table is data, so a parse method cannot exist without a row |
| `entry_coverage.py` | The per-entry report (§3.2) | a destination comes from the table row, or from the mark when the method knows better |
| `sanity_checks.py` | The post-run gate (F4.1): each static rule stated once | the gate reads the written files, not the generator's state |
| `conftest.py`, `tests/` | The gate | each rule in this document names the test that pins it |

`tools/build_kitchen_sink.py` assembles the fixture corpus from committed files.
It is a developer tool, not an entry point, so it does not use `xml_input`.

## 2. Data model

### 2.1 Identity

Identity is **(device group, vsys, type, name)**. No object is keyed by name
alone. A name that repeats in two device groups, or in two virtual systems, is
two objects.

Pinned by `tests/test_edge_cases.py::test_dup_names_across_dgs_both_survive`,
`tests/test_edge_cases.py::test_dup_names_across_vsys_both_survive`, and
`tests/test_robustness.py::test_declare_same_name_in_two_contexts_gets_unique_names`.

### 2.2 The four scope facts

`PanoramaParser.identity_of(elem)` returns four facts. Every parse method
splats them onto every object it returns, so the emitter can place a resource
without reading the XML again.

| Fact | Value | Rule |
|---|---|---|
| `device_group` | the defining device group | `Shared` is the parser fallback for an entry it cannot place, not a declared device group |
| `vsys` | the declared virtual system | `''` when the export declares none; never an invented `vsys1` |
| `template` | the declared template | `''` when the export declares none |
| `vsys_device` | the device that owns the entry | `localhost.localdomain` is the PAN-OS "this device" placeholder and names no firewall |

Pinned by `tests/test_multi_vsys_location.py::test_parser_records_declared_scope`,
`::test_parser_records_no_invented_scope`, and
`::test_every_parse_method_records_the_four_scope_facts` (the rule holds for
every parse method except `parse_device_groups`, which returns the device groups
themselves).

### 2.3 Parsed object shape

- One `<entry>` produces one dict. Each parse method returns a list of those dicts,
  except `parse_security_profiles`, which groups them by profile category.
- No parse method deduplicates by name, and no method keeps a name-keyed dict.
- An entry with no `name` is skipped. An entry whose only content is an `<id>`
  pointer is skipped too (`_is_reference_pointer`): it references a shared
  definition and has no content of its own.
- An entry the provider cannot model is marked `report_only` and keeps its
  captured values, so the report can name the reason.

Pinned by `tests/test_robustness.py::test_entry_without_name_is_skipped`,
`tests/test_edge_cases.py::test_address_emit_covers_v2_types_and_reports_the_rest`,
and the duplicate-name tests above.

Two parse methods return tables instead of objects: `parse_associations` (the
membership the export declares) and `parse_bgp` / `parse_ospf` (settings with no
v2 resource).

### 2.4 Where each parsed entry goes

Eight destinations. Every entry lands in one of them.

| Destination | What it means |
|---|---|
| Emitted resource | the type is in `EMITTED_TYPES` |
| Report entry | `REPORT_ONLY_TYPES` (no v2 resource) or `NOT_EMITTED_TYPES` (v2 resource exists, body not parsed), plus the `report_only` address entries |
| Inventory comment | `security_profiles.tf`: names and descriptions only, with the resource name the emitter would use |
| Count only | `parse_regions`: no resource and no report entry. The per-entry row (§3.2) records it as a gap, so the operator sees which entry it is |

The container table in §3.1 adds two kinds for what a parse method reads but
does not turn into an entry of its own:

| Kind | What it means |
|---|---|
| Bookkeeping | an association table or a scope fact (§2.2), and a sub-shape that only selects a shape |
| Nested block | lines written inside a parent resource block, not a resource of its own |

The per-entry report (§3.2) adds two kinds for a single entry, because a
container row cannot state a per-entry fact:

| Kind | What it means |
|---|---|
| Skipped | a parse method visited the entry and did not model it: no name, or an `id` reference pointer |
| Unaccounted | no parse method read the entry, so no table row covers its container |

The `count-only` row is the destination the converter cannot model today. It is
recorded in `backlog.md`. The F4.3 per-entry report lists it as a gap, so the
operator sees which entry it is instead of the document claiming every entry is
accounted for.

## 3. Parse pipeline

1. **Safe read.** `xml_input.parse_bytes` is the producer boundary (F5.1): it checks
   the size of the bytes it is handed, then refuses a DTD through an expat prolog scan
   that stops at the root element, and parses those same bytes. A DTD is the only
   entity door: with no DTD expat expands nothing and fetches nothing. The input is
   read once, so a check cannot be handed different bytes from the bytes it parses.
   `parse_xml(path)` is the file producer: it keeps the size check before the read, so
   an over-limit file is never allocated, and hands its bytes to the boundary.
   `SourceOrigin` (kind, name, path) lets a producer with no file behind it be refused
   with the same words, naming the origin instead of a path. The tree shape is
   unchanged, so the container table, the entry ledger, the parent walk and the line
   map are unchanged.
   Pinned by `tests/test_safe_input.py`, including
   `::test_read_input_refuses_before_allocating`, `::test_utf16_dtd_is_refused`,
   `::test_dtd_in_a_prolog_comment_is_not_a_refusal`,
   `::test_parse_reads_the_file_once`, and the boundary tests
   `::test_boundary_refuses_producer_bytes_over_the_limit`,
   `::test_boundary_refuses_a_dtd_in_producer_bytes`, `::test_boundary_opened_no_file`,
   and `::test_file_producer_runs_the_checks_through_the_boundary`.
2. **Parent map.** ElementTree keeps no parent pointers, so the parser builds a
   child → parent map once. The four scope facts walk that map.
3. **Association tables.** `parse_associations` reads the four membership lists
   the export declares (device group, template, template stack, stack →
   template) and `templates_for_device` resolves a device's effective templates.
   An export that lists no device yields empty tables: no association is better
   than a guessed one. Names are sorted, so the tables do not depend on document
   order.
   Pinned by `tests/test_multi_device_template.py::test_parser_reads_the_declared_membership`,
   `::test_templates_for_device_follows_the_stack`,
   `::test_association_is_empty_when_the_export_lists_no_devices`,
   `::test_association_names_are_sorted`.
4. **Entry scan.** Each parse method walks its container once and builds one
   object per entry. Design rule enforced by construction: one path per element
   kind, so no entry is visited twice. The multi-path methods read disjoint
   element kinds (6 interface kinds, 6 profile categories, the two tunnel
   monitor paths). One exception is open: `parse_bgp` and `parse_ospf` list two
   patterns that match the same element when the router sits under a device, so
   those entries are read twice and the manual report prints their lines twice.
   That case is recorded in [`../backlog.md`](../backlog.md).
   Each parse method also marks the entries it reads (F4.3): `self.mark(entry,
   captured)` at the point it builds the object, and `self.mark_skipped(entry,
   reason)` for an entry it visits and does not model. The mark stores the object
   by reference, so a field added after the mark is still reported. Pinned by
   `tests/test_entry_coverage.py::test_every_parse_method_that_reads_entries_marks_them`
   and `::test_corpus_entries_in_a_covered_container_are_all_marked`.
5. **Splitter (optional).** `split_device_groups.py` joins a device group, a
   template and a template stack on the devices they list, and copies each entry
   with `copy.deepcopy`, because ElementTree `append` does not reparent: it makes
   one element a child of two trees.
   Pinned by `tests/test_multi_device_template.py::test_splitter_joins_template_and_device_group_by_device`
   and `::test_splitter_leaves_the_source_tree_intact`.

### 3.1 Container table

The table is code, not documentation: `container_coverage.CONTAINER_TABLE`. One
row per parse method, with the container the method reads, the destination of its
entries (§2.4), and how the method reaches the container — a `find`/`findall`
pattern or the parent walk of §2.2. This document does not restate the table;
`tests/test_container_coverage.py` keeps the table and the code in step, so a
parse method cannot exist without a row and a row cannot name a path the method
does not read.

Two rules the scan uses:

- A container is a **section** when no config-object entry lies between it and a
  config root: the `config` element, or an entry whose container is one of the
  four scope containers in §2.2. A container inside a config-object entry is a
  property level. The property-level scan (F4.4) does not exist yet, so this
  section does not report it and the per-entry row counts the entries instead.
- A section no row covers is a finding. The scan reports it in
  `MANUAL_SETUP_REPORT.txt` with its source line and entry count, and prints one
  console line per finding. An absent section is not a finding, an empty known
  section is not a finding, and an entry container under `predefined` is not a
  finding: those entries are PAN-OS built-in definitions, not operator objects.

The parse records the opening line of every element
(`xml_input.ParsedSource.line_of`), so a finding names the line the container was
defined on. A finding is an operator action, not a broken output: it does not
change the exit code, which the F4.1 gate still decides (§4.6).

### 3.2 Per-entry report

§3.1 covers the container. F4.3 covers the entry: `CONVERSION_REPORT.txt` prints
one line per config entry the parse pipeline read, in this order:

```text
  line <source line>  <object type>/<entry name>  <destination>  <detail>  captured: <fields>
```

Four rules, in `entry_coverage.py`, pinned by `tests/test_entry_coverage.py`:

- **One entry is one report row**, at section level only. An entry inside a
  config-object entry is a property level (§3.1), so the property-level scan
  covers it and this report shows the count on the parent row instead. Entries
  under `predefined` are not rows; the header gives the count.
- **Object type is the F4.2 `section_path`** of the entry's container. No second
  naming rule.
- **Destination comes from the table row that covers the container**, longest
  matching row wins, so a sub-shape row beats the general row for its container.
  A per-entry mark overrides the row when the method knows better: `report_only`
  content is `report`, and a skipped entry is `skipped`. A scope entry is
  `bookkeeping`: it defines a scope, so it is not an object inside one.
- **Captured fields** are the keys of the object the method built, minus the entry
  name and the four scope facts (§2.2), minus keys with no value, in sorted order.
  An entry with nothing but its name says `captured: name only`. A field the
  method stored inside a type sub-shape is reported under the object key, not the
  XML tag.

Rows are grouped with the F3.9 scope rule (`_report_scope_path`), the same rule
the interface and manual reports use, so the same name in two device groups is two
sections. The report names the input file name, never the path (§4.4), and two
runs on the same input write the same bytes. The gap section lists every row whose
destination writes nothing. A gap is an operator action, so it does not change the
exit code, which the F4.1 gate still decides (§4.6). A run with no entries writes
no report file, and a run with no gaps prints no extra console line.

## 4. Emit pipeline

### 4.1 Order

`main()` declares an object before any site references it, because
`name_ref` resolves at emit time. Interfaces emit before zones and routers;
objects emit before the rules that reference them; crypto profiles emit before
gateways, and gateways before tunnels.

Pinned by `tests/test_dependency_wiring.py` (one test per wired site) and
`::test_every_emitted_reference_resolves_to_a_declared_resource`.

Each area generator returns early when its input is empty, so a file with no
content is not written. Pinned by
`tests/test_golden_files.py::test_golden_file_set_matches` and
`tests/test_real_or_report.py::test_no_report_when_no_report_only_items`.

### 4.2 Location

Provider v2 requires `location` on every resource. The choice comes from
`LOCATION_SCHEMA`, never from the resource name, in four branches:

1. A declared vsys, with no declared template, on a type that accepts `vsys` →
   `vsys { name, ngfw_device }`.
2. A declared template, on a type that accepts `template` → `template { name }`,
   plus `vsys` where that sub-block declares the field, plus `ngfw_device` when
   the export nests the entry under a device inside the template.
3. A device the export names, on a type that accepts `ngfw` →
   `ngfw { ngfw_device }`. Config the export puts under `devices/entry/<device>`
   belongs to that firewall, not to a template.
4. Otherwise the device group, the shared section (`shared = {}`), or the
   `Shared` template placeholder — emitted only when nothing in the export
   places the entry, and reported with the templates that device does take.

A declared scope the type cannot carry is reported, never dropped silently. No
sub-block or field is emitted that `LOCATION_SCHEMA` does not declare, because
`terraform validate` accepts an unknown `location` sub-block and drops it
silently: a wrong sub-block fails at apply, not at validate.

Pinned by `tests/test_multi_vsys_location.py`: `::test_schema_table_matches_provider_shape`
(against the live provider schema), `::test_schema_table_covers_every_emitted_type`,
`::test_location_choice`, `::test_shared_is_not_a_device_group`,
`::test_no_sub_block_outside_the_schema`, `::test_only_template_scoped_types_declare_ngfw`,
`::test_template_scoped_types_derive_from_schema`,
`::test_object_types_never_emit_ngfw`, `::test_placeholder_device_never_becomes_ngfw`,
the four report tests, and `tests/test_schema_conformance.py::test_every_block_has_location`.

### 4.3 Reference resolution

`name_ref` returns a `.name` reference only for an object declared in the same
run. A name that points outside the export (a built-in such as `any`, or an
object in another tenant) stays a plain string. The converter never declares a
resource just to make a reference work.

Order, first match wins:

1. A name a device declared resolves inside that device. A referrer that names
   no device resolves it only when exactly one device declares it; two devices
   is a guess, so the name stays plain.
2. The context chain, each stop paired with the referrer's vsys: the referrer's
   own context, then `Shared`, then contextless declarations.
3. The flat `(scope, name)` first-declaration index.
4. Otherwise the plain name.

Object scopes come before group scopes, so a name that both an object and a
group carry resolves to the object.

Pinned by `tests/test_robustness.py::test_name_ref_never_dangles`,
`::test_name_ref_prefers_referrers_own_context`,
`::test_name_ref_falls_back_to_shared_then_contextless`,
`::test_name_ref_prefers_referrers_own_vsys`,
`tests/test_multi_vsys_location.py::test_interface_reference_stays_inside_its_device`,
`::test_virtual_router_reference_stays_inside_its_device`,
`tests/test_multi_device_template.py::test_reference_resolves_inside_the_template_target_device`,
`::test_ambiguous_template_keeps_a_plain_interface_name`,
`::test_single_device_declaration_still_resolves_without_a_device`.

### 4.4 Policy chains

Policy rules emit as one resource per rule. `_policy_rule_chains` groups rules
by (device group, vsys). XML document order is preserved inside a chain, and
chains appear in first-seen order. The first rule of a chain anchors the managed
block at the end of the rulebase (`where = "last"`). Each later rule is placed
directly after the previous rule (`where = "after"`, `directly = true`, `pivot`)
and declares `depends_on` on it, because the pivot must exist before the move.

A rule never pivots on, or depends on, a rule in another vsys or another device
group. The rulebase (pre, post, shared) is not recorded and not emitted; see
`backlog.md`.

Pinned by `tests/test_policy_order.py` and
`tests/test_edge_cases.py::test_rule_chains_do_not_cross_vsys`.

### 4.5 Report path

Four report files, each written only when it has content:

- `CONVERSION_REPORT.txt` — one line per config entry the parse pipeline read (§3.2).
- `MANUAL_SETUP_REPORT.txt` — report-only areas, the location facts a type
  cannot carry, and the placeholder template.
- `INTERFACE_MIGRATION_REPORT.txt` and `VPN_MIGRATION_REPORT.txt` — one section
  per scope the export declares: device group first, then the template, then the
  device, then the object kind inside the section. One shared rule
  (`_report_scope_path`, `_group_by_scope`, `_report_section_header`) serves
  both, so they cannot disagree.

The post-run gate writes `SANITY_REPORT.txt` on every run (§4.6). The five files
are the complete set the generator writes, plus `README.md`.

A device group prints only when the export declares one. `Shared` names the
shared section, not a device group. `localhost.localdomain` prints as the "this
device" placeholder. Sections sort by level order, entries by name.

Pinned by `tests/test_reports.py`, including
`::test_both_reports_use_the_same_grouping_rule`,
`::test_template_and_device_scopes_are_not_printed_as_a_device_group`,
`::test_shared_section_is_named_shared`,
`::test_placeholder_device_is_not_named_as_a_firewall`,
`::test_sections_and_entries_are_in_a_stable_order`.

### 4.6 Post-run sanity gate

`main()` runs `sanity_checks.run_checks` after it writes the output. The gate
reads the files in the output directory, so a rule is satisfied by a file, not
by a bookkeeping value that never reached one. The gate runs on every
conversion. The splitter writes XML, so it has no `.tf` to check.

| Check | Rule | Severity |
|---|---|---|
| `emitted_types` | every resource type is in `EMITTED_TYPES` | FAIL |
| `location_present` | every resource block carries a `location` block | FAIL |
| `references` | every `.name` reference resolves to a resource declared in the same run | FAIL |
| `variables` | every declared variable has a `var.` consumer | FAIL |
| `control_chars` | no raw control character or DEL in a `.tf` file | FAIL |
| `placeholders` | an expected placeholder, such as the VPN key `***CHANGE_ME***`, is listed | WARN |
| `terraform` | `terraform init` + `terraform validate`, with `--validate` | FAIL, or SKIPPED when the binary is absent |

A resource block is read up to the first column-0 brace, which is how the
generator writes one and how the tests read one.

- A WARN does not fail the gate: a placeholder is correct output that still needs
  an operator action, so the run exits 0.
- A FAIL finding exits 1. A SKIPPED check never changes the exit code, so an
  offline run still reports the checks it could not run.
- The gate writes `SANITY_REPORT.txt` and a console summary.
- Each rule exists once, in `sanity_checks.py`. `tests/test_dependency_wiring.py`,
  `tests/test_variables.py`, `tests/test_schema_conformance.py` and
  `tests/test_robustness.py` call the module instead of restating a rule.
- The gate checks that `location` is present. The sub-block and field shape stays
  pinned by `tests/test_multi_vsys_location.py`, because `terraform validate`
  accepts an unknown sub-block and drops it silently.

Pinned by `tests/test_sanity_gate.py`: the gate runs on a conversion,
every check detects its own violation, the gate reports no FAIL finding on every
fixture, the exit code follows the findings, and `--validate` runs the terraform
check or reports it as SKIPPED.

## 5. Naming rules

The local name of a resource is **the sanitized PAN-OS name plus an 8-hex
digest of the source identity**.

```
local = sanitize(name) + '_' + sha256('scope|context|vsys|name')[:8]
```

- `sanitize` replaces every character outside `[A-Za-z0-9_]` with `_`, strips
  leading and trailing `_`, prefixes `_` when the result starts with a digit, and
  lowercases. An empty name becomes `unnamed`.
- `scope` is the provider resource type. `context` is the defining device group,
  the template, or the owning device (`scope_context`). `vsys` is the declared
  virtual system. `name` is the raw PAN-OS name, not the sanitized one, so two
  names that sanitize to the same base (`a-b` and `a_b`) stay apart.
- The digest makes the name independent of emission order and run count. The
  same object always gets the same local name.
- Taken names are tracked per type (one domain per `scope`). A true duplicate
  gets a numeric suffix (`_2`), so the output is always valid HCL. The suffix is
  a validity guard, not the identity mechanism: two different identities never
  need it.
- `device` is not in the digest. It indexes a declaration so a reference from one
  device cannot resolve to another device's resource of the same name.

Pinned by `tests/test_dependency_wiring.py::test_local_names_are_sanitized_name_plus_digest`,
`tests/test_robustness.py::test_declare_resource_name_is_order_independent`,
`::test_declare_resource_name_avoids_collisions`,
`::test_sanitization_collisions_get_unique_names`,
`::test_declare_empty_name_gets_a_stable_name`,
`::test_declare_same_name_in_two_contexts_gets_unique_names`,
`::test_declare_same_name_in_two_vsys_gets_unique_names`,
`tests/test_edge_cases.py::test_dup_names_across_vsys_emit_distinct_digests`,
`::test_identity_to_name_assignment_survives_entry_order_flip`, and
`tests/test_multi_device_template.py::test_same_interface_name_on_two_devices`.

## 6. Determinism

Two runs on the same input produce identical bytes.

- Association tables sort names. Report sections sort by level, entries by name.
- Names come from the identity digest, not from emission order.
- Order that the input states is preserved on purpose: XML order inside a policy
  chain, and first-seen order of chains.
- The goldens pin every emitted `.tf` file byte for byte
  (`tests/test_golden_files.py`). Reports are not in the golden set, so report
  determinism is pinned by
  `tests/test_reports.py::test_sections_and_entries_are_in_a_stable_order` and,
  for the sanity report, by
  `tests/test_sanity_gate.py::test_report_is_byte_identical_between_runs`. The
  sanity report names no timestamp and no absolute path, which is what makes that
  claim testable.
  Determinism is pinned by test, not paid in the CLI.

## 7. What this document does not claim

These are planned (`PLAN.md`) and not implemented:

- **Property-level coverage** — `COVERAGE_MATRIX` is type level. No scan reports
  a property the parse captured but no output used.
- **Rulebase** — not recorded, so not emitted.

F4.1 is implemented (§4.6): the static rules run on every conversion, and the
result is `SANITY_REPORT.txt`. F4.2 is implemented (§3.1): the container table is
code, the parse records the source line of every element, and an uncovered section
is reported. F4.3 is implemented (§3.2): one report row per entry the parse read,
with its destination, and a gap section for the rows that write nothing.

These are decided limits, not bugs: the rulebase is not emitted, security profile
bodies are not parsed, EDL credentials are never written, a service emits one
protocol leg, `location.template_stack` is never used, and a template that
targets two devices keeps interface names as strings. Each one is recorded in
`backlog.md`.
