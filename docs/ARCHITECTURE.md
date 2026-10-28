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
| `panorama_to_terraform.py` | The converter: `PanoramaParser` (model), `TerraformGenerator` (model and write), `main()` (order) | the parser consumes only the producer contract (`ParsedSource`); it reads no file and opens no connection itself, so a source is either the file producer or the api producer |
| `xml_input.py` | The only input read, shared by every entry point, through one producer boundary (F5.1), and the scope vocabulary a source states (F5.4) | the two byte checks are one function (`check_bytes`) every source kind runs, so the size cap and the DTD refusal are kind-independent and only the parse step is chosen by the kind; one definition of the scope a source holds (`DEFAULT_SCOPE`) and of the path segment that names an entry (`ENTRY_SEGMENT`) |
| `source_fetch.py` | The api producer (F5.2): the https request, the cached copy, the response wrapper, and the per-scope request shape (F5.4) | https only; a redirect that changes the scheme is refused; the cache holds exactly the bytes the boundary parsed; the key comes from the environment only; the declared path is part of the request identity, so each scope gets its own entry |
| `resource_mapping.py` | The verified provider contract: `EMITTED_TYPES`, `REPORT_ONLY_TYPES`, `NOT_EMITTED_TYPES`, `LOCATION_SCHEMA`, `DATA_SOURCE_SCHEMA`, `INTERFACE_RESOURCE_TYPES`, `COVERAGE_MATRIX` | the single source of truth; no resource name or attribute from memory |
| `split_device_groups.py` | Optional pre-processing: one XML file per device group | joins scopes on the device the export lists; copies with `copy.deepcopy` |
| `container_coverage.py` | The container table (§3.1) and the section rule | the table is data, so a parse method cannot exist without a row |
| `entry_coverage.py` | The per-entry report (§3.2) | a destination comes from the table row, or from the mark when the method knows better |
| `shadow_coverage.py` | The cross-source shadow scan (§3.2): a child entry name that repeats a parent entry name | the key is the matrix row, not the name alone; both sources are read with the same row rule, so no second naming rule exists; a run with no declared parent has no parent to read |
| `state_input.py` | The state producer (F5.6): a Terraform state document read as a reference source, through the same door | the two byte checks run on the state bytes, and only the parse step is chosen by the kind, so a `<!DOCTYPE` inside a JSON value is not a refusal; a document the identity key cannot read is an input refusal; the state source writes no output, so no `.tf` byte changes |
| `state_coverage.py` | The state scan (§3.2): the ownership fact and the drift fact | the matrix row is the same table the property scan uses, keyed by the resource type; the ownership key is §2.1 identity with the declared facts, never the `Shared` fallback; the scan is not an output, so it reads captured values without recording |
| `sanity_checks.py` | The post-run gate (F4.1): each static rule stated once | the gate reads the written files, not the generator's state; one block reader serves every block kind a rule reads, so a fact about a block is reported once |
| `provenance.py` | The provenance record (F5.3): what the run read, as `SOURCE.txt`, one record per source read (F5.4) | the record states the bytes the door parsed and never the credential; the cache reference a prune action reads is the `cache_entry` field, not a printed line |
| `unit_manifest.py` | The unit as data (F6.1): one row per declared scope, as `CODEBASE_MANIFEST.json` (§3.4) | the rows come from the ledger, so the module adds no parse data; it takes the §5 naming rule as an argument, so no second naming rule exists; the reference names arrive from §4.3, so this module resolves no name |
| `ownership.py` | The owner of a repeated name (F6.2): one row per entry a matrix row covers, as `OWNERSHIP.json` (§3.5), and the report finding for a case the rule cannot decide | the row scope is the F4.4 rule read through the report row, so no second scope rule exists; the identity key and the naming rule are read through `state_coverage` and `unit_manifest`, so no second key or naming rule exists; `disable_override` names the entry that cannot be overridden, not the owner; the scan reads a captured value without recording |
| `reference_edges.py` | The reference between units (F6.3): one row per pair, as `REFERENCE_EDGES.json` (§3.6), the acyclic rule, and the unit order on the manifest row | the edge set is the names §4.3 recorded, so this module records no name and resolves no name; the target is the ownership `owner`, so the pair joins to §3.4 on `directory` and to §3.5 on (`type`, `entry`); a row that names one unit is refused; the order comes from the three bases §6 of `CODEBASE_ASSEMBLY.md` states, read through the module that holds each fact |
| `import_blocks.py` | The import block (F6.4): one block per entry, as `imports.tf` (§4.8), and the id shape | the block is built from the same data the resource block uses, so this module states no location rule and no naming rule; the id is the base64 JSON object the provider documents, and `decode_id` refuses a shape it does not declare; the four `*_policy_rules` types are the rows `LOCATION_SCHEMA` declares `rulebase` for, so no second table names them |
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

A captured field that no output reads is a property gap, and the property scan reports
it for a container the matrix covers (§3.2). A destination with no matrix row has no
declared property list, so its field gaps are recorded in `backlog.md` instead.

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

   **The api producer** (`source_fetch.py`, F5.2) is a second producer behind the same
   boundary, so the two checks apply to a response exactly as they apply to a file. Three
   rules:

   - **The wrapper is normalised, one shape per request shape.** A Panorama API response is not
     a configuration export: it is a transport envelope, `response/result/config`, and the
     converter reads a `config` element. The producer moves the root to the element the request
     shape names, and it does not guess a shape the request does not state. A whole-config
     request takes the `config` element under `result`; accepted shapes are
     `response/result/config`, `result/config`, and a plain `config`. A per-scope request (F5.4)
     declares a path, and its `result` must hold exactly one element: the container the path
     names, or the entry with the name the path states. `result` itself becomes the root, read as
     the place the path names (§3.1). A shape that does not match its own request is refused: a
     `result` with no `config` element read by a whole-config request, a `result` that holds
     nothing, more than one element, or an element the path does not name, and a whole-config
     shape read by a per-scope request. The producer does not reparse, so the origin and the line
     map are the same objects, and a report line still names the line the response carries. The
     response check (type `success`, code `0`) runs for both shapes, before the cache entry is
     written. The cache holds the response as it arrived: normalising before the cache write would
     put bytes in the file that the parser never saw. Pinned by
     `tests/test_source_fetch.py::test_fetch_root_is_the_config_element_under_result` (the origin
     and the line map are the same objects), `::test_one_shape_per_request_shape`,
     `::test_a_per_scope_response_holds_the_element_the_path_names`,
     `::test_a_per_scope_response_that_does_not_match_its_path_is_refused`,
     `::test_the_response_check_runs_for_both_shapes`,
     `::test_result_root_and_plain_config_root_are_accepted`, and
     `::test_container_table_names_no_wrapper_row`.
   - **The cache holds the parsed bytes under a key-free name.** An entry is named by the
     SHA-256 hex of the host and the sorted request parameters. The key is not part of the
     name, so the credential never appears in a file name, and two requests with the same
     parameters but different keys share one entry. `--offline` reads only this cache and
     refuses a missing entry; it needs no key, so a CI run on a committed cache connects to
     no server. The declared path is part of the identity (F5.4), so each scope gets its own
     entry, and `--offline` covers both requests of a two-source run. The checks must pass
     before a write, so a refused response never reaches the cache, and two runs on the same
     cache write byte-identical output. Pinned by
     `tests/test_source_fetch.py::test_cache_miss_then_hit_reopens_the_same_bytes`,
     `::test_cache_entry_name_is_the_request_identity_without_the_key`,
     `::test_the_declared_path_is_part_of_the_request_identity`,
     `::test_cache_hit_over_the_limit_is_refused_through_the_door`,
     `::test_offline_refuses_a_missing_entry_and_calls_no_producer`,
     `::test_offline_refuses_a_missing_entry_for_the_second_request`,
     `::test_offline_reopens_an_entry_with_no_key`, and
     `::test_two_runs_on_the_same_cache_bytes_write_identical_bytes`.
   - **https only, with no silent downgrade.** The request uses https; `--insecure` is the
     explicit choice to skip certificate verification. A redirect that changes the scheme is
     refused, because following it would send the credential over a plain connection. The
     key is read from the environment (`PANOS_API_KEY`) only, never from a command line, so
     it does not appear in a shell history or in a process list. Standard library only: the
     planned `pan-os-python` producer cannot enforce the redirect rule, so it is not a
     dependency (see `backlog.md`). Pinned by
     `tests/test_source_fetch.py::test_the_producer_accepts_https_only`,
     `::test_a_redirect_that_changes_the_scheme_is_refused`,
     `::test_verification_is_on_by_default_and_insecure_is_explicit`, and
     `::test_the_key_never_reaches_the_cache_name_or_the_output`.

   **The state producer** (`state_input.py`, F5.6) is a third producer behind the same door, so the
   two checks run on a state document exactly as they run on a file: `check_bytes` measures the size
   and asks the parser for the DTD. Only XML has a prolog, so a JSON document reaches no DOCTYPE and
   a `<!DOCTYPE` inside a JSON value is not a refusal: only the parse step is chosen by the kind. The
   tree rule does not apply to a JSON document, because the container table, the parent walk, and the
   line map are keyed on the ElementTree tree, so a state document gives the scan one shape per
   entry: the entry name, the resource type, the attribute values, and the position. The position is
   the resource address (`type.name`, or `module.path:type.name` inside a module instance), because
   no source line exists. A document the identity key cannot read is refused: bytes that are not
   JSON, a document that is not one object with a `resources` array, a `resources` item that is not
   an object, and a resource that names no `type` or no `name`. The state source is a reference
   source, so the run writes no output from it and no `.tf` byte changes, and a state read calls no
   producer, so `--offline` needs no new rule. Pinned by `tests/test_state_input.py`, including
   `::test_the_size_check_runs_on_the_state_bytes`,
   `::test_the_dtd_check_refuses_nothing_for_a_json_document`,
   `::test_the_producer_keeps_both_nested_block_shapes`,
   `::test_a_document_the_scan_cannot_key_is_an_input_refusal`, and
   `::test_a_state_read_calls_no_producer`.

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
   monitor paths, `parse_bgp` and `parse_ospf` reading one
   `network/virtual-router/entry` path). `tests/test_coverage_matrix.py` and
   `tests/test_container_coverage.py` keep the paths and the table in step.
   Each parse method also marks the entries it reads (F4.3): `self.mark(entry,
   captured)` at the point it builds the object, and `self.mark_skipped(entry,
   reason)` for an entry it visits and does not model. `mark` returns the recorded
   object, so a parse method must work through the object it returns: a field added
   after the mark is still reported, and that object records the keys an output reads
   from it (F4.4, §3.2). Pinned by
   `tests/test_entry_coverage.py::test_every_parse_method_that_reads_entries_marks_them`,
   `::test_fields_added_through_the_recorded_object_are_recorded`, and
   `::test_corpus_entries_in_a_covered_container_are_all_marked`.
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

Three rules the scan uses:

- A container is a **section** when no config-object entry lies between it and a
  config root: the `config` element, or an entry whose container is one of the
  four scope containers in §2.2. A container inside a config-object entry is a
  property level, and the property scan (F4.4) covers it (§3.2). The scan scope is
  the entries a matrix row covers, so a report, inventory, bookkeeping, count-only,
  or nested-block container is not a property finding: it has no row, and only a row
  can name the properties an emitter reads. Those field gaps are recorded in
  [`../backlog.md`](../backlog.md).
- A section no row covers is a finding. The scan reports it in
  `MANUAL_SETUP_REPORT.txt` with its source line and entry count, and prints one
  console line per finding. An absent section is not a finding, an empty known
  section is not a finding, and an entry container under `predefined` is not a
  finding: those entries are PAN-OS built-in definitions, not operator objects.
- **The envelope is never a scanned container** (`container_coverage.ENVELOPE`:
  `response` and `result`). For a per-scope source (F5.4) `result` is read as the place the
  declared path names, so the entry under it is the declared scope entry, and a container inside
  that entry is a section. `container_coverage.container_tag` is the one function that gives the
  tag for a source, and the scan, the entry ledger, and the parser scope walk all read it, so an
  entry in a per-scope run takes the declared scope as its scope fact instead of the `Shared`
  fallback. Pinned by `tests/test_container_coverage.py::test_the_envelope_is_never_a_scanned_container`,
  `::test_the_scan_reads_a_per_scope_root_as_the_place_the_path_names`, and
  `tests/test_shadow_coverage.py::test_the_declared_scope_fact_replaces_the_shared_fallback`.

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

Six rules, in `entry_coverage.py`, pinned by `tests/test_entry_coverage.py`:

- **One entry is one report row**, at section level only. An entry inside a
  config-object entry is a property level (§3.1), so the property scan reports it and
  this report shows the count on the parent row instead. Entries
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
- **Every row names the source that holds the entry** (F5.4): `source` is the report value of the
  source, never a path (rule 6 below). It is row data for the cross-source scan, and `entry_line`
  does not print it, so the entry-line bytes are unchanged for a one-source run. Pinned by
  `tests/test_entry_coverage.py::test_every_row_names_the_source_that_holds_the_entry` and
  `::test_the_entry_line_prints_no_source`.
- **A property the parse captured and no output read is a finding**, and the report
  prints findings in their own section after the gap section:

  ```text
    line <source line>  <object type>/<entry name>  <matrix row>  no output read: <properties>
  ```

  The scan measures reads at run time: the captured object records the keys an output
  reads from it, and the record starts after the parse, so a key the parse method read
  off the XML element is not a property an output used. Only an entry a matrix row
  covers is in scope, so a report, inventory, bookkeeping, count-only, or nested-block
  container is not a finding (§3.1). Pinned by `tests/test_property_coverage.py`,
  including the corpus findings, the parity with the matrix row, the scan scope, and the
  report section. The console prints the gap lines only; a property finding prints in
  the report, because it names a matrix row.

**The cross-source shadow scan** (F5.4) adds one finding kind, in `shadow_coverage.py`, and the
report prints it in its own section after the property section:

```text
  line <source line>  <object type>/<entry name>  <matrix row>  parent source: <parent name> (parent line <n>)
```

A child entry is a shadow when its name repeats a parent entry name and both entries are covered
by the same matrix row. The key is the matrix row, not the name alone, so a shadow is a fact
within one container kind: an address that repeats a shared address of the same name is a shadow,
and a service group with the same name is not. The scan scope is the rule above, and the parent
source is read with the same container helpers and the same row rule, so no second naming rule
exists. A run with no declared parent has no parent to read, so it prints no shadow section. The
second source is what makes the name visible: a per-device-group run cannot see its parent, so an
inherited name stays a plain string and the parent entry is invisible. The console prints no shadow
line, and a shadow is an operator action, so it does not change the exit code. Pinned by
`tests/test_shadow_coverage.py`, including the fixed line shape, the row key, the scan scope, the
grouping, and the no-parent run.

**The repeated-name scan** (F6.2) prints its findings in its own section, after the shadow section and
before the two state sections:

```text
  line <source line>  <object type>/<entry name>  <matrix row>  <reason>
```

The scan adds no fact kind of its own: it decides the owner for the entries §3.1 covers, and the
report prints the case it cannot decide. Its rules are in §3.5. A finding is an operator action, so it
does not change the exit code, which the F4.1 gate decides, and the console prints no line for it.
Pinned by `tests/test_ownership.py`, including the fixed line shape, the grouping, the section order,
and the no-console-line run.

**The state scan** (F5.6) adds two fact kinds, in `state_coverage.py`, and the report prints them in
their own two sections after the shadow section, in this order: ownership, then drift. Each section
prints only when it has a finding, and both use one fixed shape:

```text
  line <source line>  <object type>/<entry name>  <matrix row>  state source: <state name> (<resource address>)
```

The drift line is the ownership line with the values added:

```text
  ...  state source: <state name> (<resource address>)  value differs: <property> (<run value> vs <state value>)
```

The line names the run entry's source line, the same line the entry rows print, because a state entry
has no line of its own. Values are printed as their JSON text and properties are in sorted order, so
one finding stays on one line.

The ownership key is §2.1 identity as the F3.9 rule reads it: the matrix row, the entry name, and the
four declared facts, read from the `location` block the state document holds, through the block names
`LOCATION_SCHEMA` declares. The `Shared` fallback is never in the key, because it is a parse fallback
and not a declared fact; the `shared` block states no name, so it fills no fact; `localhost.localdomain`
names no device (F3.5); and a sub-block the table does not declare for the row names a scope this
converter never emits, so an entry placed there is not keyed. The first state entry that carries a key
wins, in document order, because one run entry is one finding (the F5.4 rule). The scan scope is the
property rule on both sides: an entry no row covers is not a finding, and a state resource whose type
has no row is not in the index. A run with no declared state source has no state to read, so it prints
neither section.

Drift compares only a property the row declares that both sides hold by the same name, because no rule
maps a parse key to a provider attribute name: the parse key `tags` and the provider attribute `tag`
are not compared, and that limit is recorded in [`../backlog.md`](../backlog.md). A value is compared as
the two sides hold it, so member order is part of the value. A drift fact needs an ownership fact, so
the drift section is a subset of the ownership section. The state scan is not an output, so it reads
captured values through the non-recording read (`entry_coverage.RecordingDict.value`) and cannot move a
property finding. Both facts are grouped by the same F3.9 scope rule, the console prints no state line,
and both are operator actions, so neither changes the exit code, which the F4.1 gate still decides.
Pinned by `tests/test_state_coverage.py`, including the fixed line shapes, the key, the scan scope on
both sides, the grouping, the property-read parity, and the no-state run.

Rows are grouped with the F3.9 scope rule (`_report_scope_path`), the same rule
the interface and manual reports use, so the same name in two device groups is two
sections. A scope name is read from the scope `<entry>`, not from the container
element, so the report prints the device group, template, and device sections for a
row inside a scope. The report names the input file name, never the path (§4.4), and two
runs on the same input write the same bytes. The gap section lists every row whose
destination writes nothing. A gap is an operator action, so it does not change the
exit code, which the F4.1 gate still decides (§4.6). A run with no entries writes
no report file, and a run with no gaps prints no extra console line.

### 3.3 Provenance record

`main()` writes one record per source the run read, as `SOURCE.txt` in the output directory, in
read order: the main source, then a declared parent source (F5.4), then the state source (F5.6). A
one-source run writes the same bytes as the F5.3 rule. The record names the bytes a reader can
reopen, so a report line can be checked against the file it describes. Eight fields, in this order:
`kind`, `name`, `path`, `scope`, `request`, `cache_entry`, `size`, `sha256`. A field that does not
apply to the source kind is `-`, so one shape reads. Records are separated by one blank line, which
is the whole record shape. The rule lives in `provenance.py`.

Four rules the record keeps:

- **The record is data.** One `field: value` line per field, in the fixed order, with no
  prose and no timestamp, so two runs on the same bytes write the same record.
  `parse_record` reads one record and `parse_records` reads a record file, so a tool can act on
  it, and a line that is not a declared field is refused. Pinned by
  `tests/test_provenance.py::test_the_record_round_trips_as_data`,
  `::test_a_record_line_that_is_not_a_field_is_refused`,
  `::test_one_record_writes_the_same_bytes_as_the_f5_3_rule`, and
  `::test_the_record_file_holds_one_record_per_source_read`.
- **The record is not a report body.** A report body names the source name only, never the
  path (F4.2 rule 6), so the path field here cannot move a report byte. The label a report
  body uses for the source is `Source:` (`container_coverage.SOURCE_LABEL`), for both
  sources, and both report writers read that one constant. Pinned by
  `tests/test_provenance.py::test_the_report_bodies_still_name_the_name_not_the_path` and
  `::test_one_label_for_both_sources`, and by the pins in `tests/test_container_coverage.py`
  and `tests/test_entry_coverage.py`.
- **The byte facts come from the door.** `xml_input.ParsedSource` records the size and the
  SHA-256 hex of the bytes it parsed, and `state_input.StateSource` records the same two facts for
  the bytes its door checked (F5.6), so the record names the bytes the door checked, not a file that
  may have changed since the run. Pinned by
  `tests/test_provenance.py::test_a_file_run_record_names_bytes_a_reader_can_reopen`,
  `::test_an_api_run_record_names_the_request_identity_and_the_cache_entry`, and
  `tests/test_state_input.py::test_the_producer_states_the_record_facts`.
- **The pruning rule.** A cache entry is not pruned while a written record references it, so
  the reference is the `cache_entry` field of a parsed record, never a printed line. A shadow
  line prints a source name, and that printed line protects nothing. A state record has no request
  and no cache entry, so it references nothing and prunes nothing (F5.6).
  `provenance.prunable_entries` states the rule; no command runs the prune yet (see
  [`../backlog.md`](../backlog.md)). Pinned by
  `tests/test_provenance.py::test_the_reference_is_data_not_a_printed_line`,
  `::test_a_printed_parent_source_is_not_a_reference`, and
  `tests/test_state_input.py::test_a_state_record_references_nothing_so_it_prunes_nothing`.

The record names no credential: the `request` field is the key-free identity the cache name
is hashed from, for both requests of a two-source run (F5.2 key rule, pinned by
`tests/test_provenance.py::test_the_record_never_names_the_key` and
`::test_the_record_file_holds_one_record_per_source_read`). A run that refuses its
input writes no record, like every other input refusal. The `scope` field names the scope the
source holds: `whole-config` when the producer declares none (the one definition is
`xml_input.DEFAULT_SCOPE`), the declared path for a per-scope source (F5.4), and the declared
workspace for a state source (F5.6). No new field is needed, so `parse_records` reads a state record
with no change; this is pinned by
`tests/test_state_input.py::test_the_producer_states_the_record_facts` and
`tests/test_state_coverage.py::test_the_state_record_reads_back_with_no_new_field`.

### 3.4 Unit manifest (F6.1)

`main()` writes one row per unit, as `CODEBASE_MANIFEST.json` in the output directory. A unit is
one combination of the four scope facts (§2.2), and a unit exists when the ledger has a report
row in it (§3.2), so the manifest is built from `entry_coverage.EntryLedger` and adds no parse
data. An entry inside a config-object entry is a property level (§3.1), so the parent row's count
covers it.

The rule lives in `unit_manifest.py`, and it holds six facts:

- **The unit name.** The deepest scope the export declares names the unit, in the F3.9 level
  order, read innermost first: `vsys`, `vsys_device`, `template`, `device_group`. `Shared` names
  the unit whose four facts are empty, because the four facts alone cannot name the shared
  section. The placeholder device names no unit (§2.2), so the scope above it names the unit.
- **The identity.** `facts_of` reads a ledger row or a parsed object through one function, so both
  land on the same unit: it drops the `Shared` parse fallback from `device_group` (§2.2 rule).
- **The directory name.** `sanitize(unit name) + '_' + 8-hex digest of the identity`, in the §5
  shape. The digest is always present, not only on a collision, so a name never depends on the
  other units in the run. The module takes the §5 rule as an argument, so it defines no second
  naming rule. It names the directory; it writes no directory.
- **The row shape.** `unit`, `device_group`, `vsys`, `template`, `vsys_device`, `directory`,
  `entry_count`, `references`. Fields print in the declared order, the rows sort by the identity,
  and the reference names are sorted. `parse_rows` reads a written file back, and a row that is
  not the declared shape is a refusal, the way `parse_record` refuses a line (§3.3 rule).
- **One file per codebase run.** The edge list needs the whole set of units, so one file holds one
  row per unit. A manifest row for a unit with no ledger row adds nothing, so every recorded name
  belongs to a unit the ledger shows.
- **The content rule.** The file is written only when it has content, following the rule for the
  report files (§4.5). A run that reads no entry writes no manifest, and the record is still
  written. A plain run writes it, so the CLI takes no flag for it.

The `references` field holds the names the reference rule resolved outside the run (§4.3), keyed
by the referrer's four facts. The record is made at the site that applies the rule, so no second
resolution rule exists. The ambiguous-device case (§4.3 rule 1) is recorded as an outside name,
because the row cannot name the other unit until the edge list exists.

Pinned by `tests/test_unit_manifest.py`, including
`::test_the_shared_unit_is_the_unit_with_empty_facts_and_is_named_shared`,
`::test_shared_in_device_group_is_not_a_fact_value`,
`::test_the_deepest_declared_scope_names_the_unit`,
`::test_the_placeholder_device_names_no_unit`,
`::test_the_property_level_is_counted_on_the_parent_row`,
`::test_the_manifest_is_one_file_for_the_codebase`,
`::test_the_manifest_is_written_only_when_it_has_content`,
`::test_a_plain_run_writes_the_manifest_without_a_flag`,
`::test_a_contextless_call_site_records_the_name_for_the_referrers_unit`,
`::test_a_name_the_run_declares_is_not_recorded`,
`::test_the_ambiguous_device_name_is_recorded_as_an_outside_name`,
`::test_a_read_through_name_is_recorded`,
`::test_every_recorded_name_belongs_to_a_unit_the_ledger_shows`,
`::test_a_name_is_stored_once_per_unit`, `::test_the_exit_codes_are_unchanged`, and
`::test_the_manifest_names_no_path_and_no_timestamp`.

### 3.5 Ownership record (F6.2)

`main()` writes one row per entry the coverage matrix covers, as `OWNERSHIP.json` in the output
directory. Ownership is a per-entry fact, so this file holds one row per entry while §3.4 holds one
row per unit, and the two data files join on `directory`. The rules are in `ownership.py` and in
[`CODEBASE_ASSEMBLY.md`](CODEBASE_ASSEMBLY.md) §4; this section states only the shape.

- **The row shape.** `type`, `entry`, `source`, the four scope facts, `directory`, `owner`, `kind`,
  `override`. `kind` is one of `declared`, `definition`, `override`, `ambiguous`; `override` is the
  flag as the parse read it: `yes`, `no`, or `unknown`; `owner` is empty when the rule names no owner.
- **The row order.** The §2.1 identity through `state_coverage.ownership_key`, then `source`, because
  two sources can state the same identity. Fields print in the declared order, not alphabetically.
- **The bytes.** `json.dumps(rows, indent=2)` with one trailing newline, ASCII output, no timestamp
  and no path, so two runs on the same bytes write the same bytes.
- **The refusal rule.** `parse_rows` reads a written file back as data and refuses a row that is not
  the declared shape, the way `parse_record` refuses a line (§3.3).
- **The content rule.** Written only when it has content, following the rule for the report files
  (§4.5). A plain run writes it, so the CLI takes no flag for it, and the gate reads no data file.

The scan result keeps `line`, `container`, and `reason` as run facts, so they are not written: the
record states a fact, the report states a finding. The scan reads the captured flag through
`entry_coverage.RecordingDict.value`, so it is not an output read and cannot move a property finding
(the F5.6 rule).

Pinned by `tests/test_ownership.py`, including
`::test_the_fields_print_in_the_declared_order`,
`::test_the_record_writes_only_the_declared_fields`,
`::test_the_record_names_no_path_and_no_timestamp`,
`::test_the_record_reads_back_as_the_rows_it_wrote`,
`::test_parse_rows_refuses_a_row_that_is_not_the_declared_shape`,
`::test_two_runs_on_the_same_bytes_write_the_same_bytes`,
`::test_the_record_is_written_only_when_it_has_content`,
`::test_the_gate_reads_no_data_file`, and
`::test_no_report_names_a_field_the_record_states`.

### 3.6 Reference edge record (F6.3)

`main()` writes one row per reference pair, as `REFERENCE_EDGES.json` in the output directory. A pair
cannot be a manifest field (§3.4 holds one row per unit) or an ownership row (§3.5 holds one row per
entry), so it has its own file. The rules are in `reference_edges.py` and in
[`CODEBASE_ASSEMBLY.md`](CODEBASE_ASSEMBLY.md) §5 and §6; this section states only the shape.

- **The row shape.** `referrer`, `target`, `type`, `entry`. `referrer` is the unit that uses the name,
  from the §4.3 record; `target` is the `owner` field of the §3.5 row for (`type`, `entry`); `type` is
  the matrix row that covers the target entry. A name no unit declares writes no row, and a row whose
  target is the referrer writes no row.
- **The join.** `referrer` and `target` join to §3.4 on `directory`, and (`type`, `entry`) joins to
  §3.5, so the record states no path and no second identity key.
- **The row order.** The four fields in field order, one row per pair, no repeated row.
- **The bytes.** `json.dumps(rows, indent=2)` with one trailing newline, ASCII output, no timestamp
  and no path, so two runs on the same bytes write the same bytes.
- **The refusal rule.** `parse_rows` reads a written file back as data and refuses a row that is not
  the declared shape, including a row that names one unit instead of two, the way `parse_record`
  refuses a line (§3.3).
- **The content rule.** Written only when it has content, following the rule for the report files
  (§4.5). A plain run writes it, so the CLI takes no flag for it, and the gate reads no data file.
- **The two order fields** `rank` and `after` print on the §3.4 row, after the eight F6.1 fields,
  because §3.4 is the file that names each unit. `rank` is the position from 1, or 0 for a unit in a
  cycle; `after` is the sorted list of directories the unit must be planned after.

The scan result keeps the cycle walk, the names on each hop, and the reason as run facts, so they are
not written: the record states a pair, the report states a finding. A finding reads its grouping facts
through the manifest row of the unit the cycle is read from, so the report groups it with the F3.9 rule
and no second fact order appears. The finding prints in its own section, after the repeated-names
section and before the state sections (§4.5), one line per cycle, read from its smallest unit; the
console prints no cycle line and a cycle does not change the exit code, which the gate decides.

Pinned by `tests/test_reference_edges.py`, including
`::test_the_rows_are_the_declared_shape_in_field_order`,
`::test_the_row_joins_to_the_manifest_and_to_the_ownership_record`,
`::test_the_record_round_trips_as_data`, `::test_a_row_that_is_not_the_declared_shape_is_refused`,
`::test_the_record_names_no_path_and_no_timestamp`,
`::test_the_record_is_written_only_when_it_has_content`,
`::test_the_gate_reads_no_data_file_and_check_order_is_unchanged`,
`::test_no_report_names_the_record_or_a_field_it_states`,
`::test_the_cycle_line_shape_is_fixed`, and `::test_two_runs_write_the_same_bytes`.

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
4. A read-through `data` block, when the run declares one of the scopes in this
   site's lookup order (§4.7). The block type is the first opted-in scope in that
   order, which is the order PAN-OS resolves a name in.
5. Otherwise the plain name.

Object scopes come before group scopes, so a name that both an object and a
group carry resolves to the object.

A `data` block is the only block `name_ref` creates, and only for a scope the run
declares. A name that resolves inside the run, or that stays ambiguous under
rule 1, stays a plain string.

The rule also records what it resolved outside the run (F6.1). `name_ref` takes the object
the reference site belongs to and records each outside name against that object's four scope
facts, so the manifest row can state the names a unit references from outside itself (§3.4).
The record is made here, at the site that applies the rule, so no second resolution rule
exists. The same record is the edge set (§3.6), because an edge is a recorded name that an
ownership row also covers. Pinned by `tests/test_unit_manifest.py::test_the_reference_names_are_recorded_for_the_referrers_facts`
and `::test_a_name_the_run_declares_is_not_recorded`.

Pinned by `tests/test_robustness.py::test_name_ref_never_dangles`,
`::test_name_ref_prefers_referrers_own_context`,
`::test_name_ref_falls_back_to_shared_then_contextless`,
`::test_name_ref_prefers_referrers_own_vsys`,
`tests/test_multi_vsys_location.py::test_interface_reference_stays_inside_its_device`,
`::test_virtual_router_reference_stays_inside_its_device`,
`tests/test_multi_device_template.py::test_reference_resolves_inside_the_template_target_device`,
`::test_ambiguous_template_keeps_a_plain_interface_name`,
`::test_single_device_declaration_still_resolves_without_a_device`, and the
read-through part by `tests/test_data_blocks.py::test_a_name_that_resolves_inside_the_run_stays_a_resource_reference`,
`::test_an_ambiguous_device_name_stays_a_plain_string`,
`::test_the_block_type_is_the_first_opted_in_scope_in_the_lookup_order`.

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

- `CONVERSION_REPORT.txt` — one line per config entry the parse pipeline read (§3.2). Section
  order is fixed: report header, summary, gaps, property findings, shadows, repeated names (§3.5),
  reference cycles (§3.6), state ownership, state drift, then the grouped entry lines. Each section
  prints only when it has content, and the shadow section prints only for a run that declares a
  parent source (`--path` with `--parent`, the api source only; a path that is not a scope path is
  an argument error, exit 2).
- `MANUAL_SETUP_REPORT.txt` — report-only areas, the location facts a type
  cannot carry, and the placeholder template. The BGP and OSPF blocks name the scope
  and the router, because two routers in two scopes can hold the same values, and they
  use the same grouping rule as the other two reports. A field the parse captures for
  these sections is either printed or reported as a property no output read (§3.2),
  so it cannot be held and left out. Pinned by
  `tests/test_reports.py::test_bgp_and_ospf_sections_name_the_scope_and_the_router`,
  `::test_device_router_section_names_the_device`, and
  `::test_bgp_section_prints_what_the_parse_captured`.
- `INTERFACE_MIGRATION_REPORT.txt` and `VPN_MIGRATION_REPORT.txt` — one section
  per scope the export declares: device group first, then the template, then the
  device, then the object kind inside the section. One shared rule
  (`_report_scope_path`, `_group_by_scope`, `_report_section_header`) serves
  both, and the conversion report uses it for the property section, the shadow section, and the
  repeated-name section, so they cannot disagree.

The post-run gate writes `SANITY_REPORT.txt` on every run (§4.6). The generator
also writes `read_through.tf` for a run that declares read-through scopes (§4.7), and
`imports.tf` for a run that declares import blocks (§4.8), and `main()` adds
`README.md`, the provenance record `SOURCE.txt` (§3.3), the unit manifest
`CODEBASE_MANIFEST.json` (§3.4), and the ownership record `OWNERSHIP.json` (§3.5).
`SANITY_REPORT.txt` and `SOURCE.txt` are written on every completed run, and the four report files
above, `read_through.tf`, `imports.tf`, and the three data files are written only when they have
content. These files are the complete set a run writes.

The three data files are not report bodies, so no report names them or restates a row, and the gate
reads only `.tf` files, so none is a gate input. `imports.tf` is a `.tf` file, so the gate reads it
(§4.6). Pinned by
`tests/test_unit_manifest.py::test_no_report_names_a_field_the_manifest_states` and
`::test_the_gate_reads_no_data_file`, and by
`tests/test_ownership.py::test_no_report_names_a_field_the_record_states` and
`::test_the_gate_reads_no_data_file`.

A coverage section cannot name a read-through name, because the three scans read
entries the parse captured and a read-through name is not one of them (§4.7). The
manual report is the one report that may name one, through the location rules
above.

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
| `location_present` | every `resource` and `data` block carries a `location` block | FAIL |
| `data_blocks` | every `data` block matches the `DATA_SOURCE_SCHEMA` row for its type | FAIL |
| `import_blocks` | every `import` block agrees with the `resource` block it names: the type, the local name, the entry name, and the location | FAIL for a violation; WARN for a rule type the shape cannot state (§4.8) |
| `references` | every `.name` reference resolves to a block declared in the same run, by kind | FAIL |
| `variables` | every declared variable has a `var.` consumer | FAIL |
| `control_chars` | no raw control character or DEL in a `.tf` file | FAIL |
| `placeholders` | an expected placeholder, such as the VPN key `***CHANGE_ME***`, is listed | WARN |
| `terraform` | `terraform init` + `terraform validate`, with `--validate` | FAIL, or SKIPPED when the binary is absent |

One block reader serves every block kind the gate reads: `resource`, `data`,
`import`, and `action`. F5.5 added the `data` rule and F6.4 added the `import` rule
with the same reader (§4.8), so no second reader appears. A block is read up to the
first column-0 brace, which is how the generator writes one and how the tests read
one. A block is reported once for a fact: `location_present` reads both kinds, so
the `data_blocks` rule reports the shape inside the block, not the missing block.
An `import` block has no header names, so the reader takes the type and the local name
from `to` inside the body, which is the same pair a reference names.

`data_blocks` checks the type, the `location` sub-block, the fields inside it, and
`name` when the row declares one. A row that declares no `name` (the settings,
policy, and collection shapes, 22 rows) is not refused for having none, so the rule
is stated per row. `references` keys a block by (kind, type, local name): a `data.`
reference answers to a `data` block and a plain reference to a `resource` block.

`import_blocks` compares a written block with the block it names: `to` must name a
`resource` block this run declares (a `data` block cannot answer, because an import
object names a resource), `id` must decode to the declared shape, the decoded name must
equal the block's `name`, and the decoded location must equal the block's `location`
sub-block, field for field. A rule entry of the four `*_policy_rules` types writes no
block, so the rule reports it as WARN with the reason (§4.8). The finding names the file
and the line the one reader read.

- A WARN does not fail the gate: a placeholder is correct output that still needs
  an operator action, so the run exits 0.
- A FAIL finding exits 1. A SKIPPED check never changes the exit code, so an
  offline run still reports the checks it could not run.
- The gate writes `SANITY_REPORT.txt` and a console summary.
- Each rule exists once, in `sanity_checks.py`. `tests/test_dependency_wiring.py`,
  `tests/test_variables.py`, `tests/test_schema_conformance.py` and
  `tests/test_robustness.py` call the module instead of restating a rule.
- For a `resource` block the gate checks `location` presence only. That shape stays
  pinned by `tests/test_multi_vsys_location.py`, because `terraform validate`
  accepts an unknown sub-block and drops it silently. For a `data` block the gate
  reads the shape, because the shape is data the gate can read
  (`DATA_SOURCE_SCHEMA`).
- The console summary names resource blocks only, so a run that writes `data` blocks
  reports the same resource count as the same run without them.

Pinned by `tests/test_sanity_gate.py`: the gate runs on a conversion,
every check detects its own violation, the gate reports no FAIL finding on every
fixture, the report is byte-identical between two runs, the exit code follows the
findings, and `--validate` runs the terraform check or reports it as SKIPPED. The
`data` rules are pinned by `tests/test_data_blocks.py`, and the table itself by
`tests/test_data_source_schema.py` against the live provider schema.

### 4.7 Read-through data blocks (opt-in)

A read-through `data` block is the record of one name a reference site needed and
this run did not read. The feature is opt-in, and off by default: a run that
declares no read-through scope keeps the plain-string rule, so both golden sets
write the same bytes and no read-through file is written.

`--data-blocks SCOPE` declares the scopes a run may read through. It is repeatable
and takes a comma-separated list. A scope must be one the reference rule resolves
against, and its `DATA_SOURCE_SCHEMA` row must declare `name`: a data source with no
`name` cannot hold the entry name a reference needs. An empty value, a scope outside
the reference sets, or a no-name scope is an argument error (exit 2).

One block per identity (type, context, vsys, name):

| Part | Value |
|---|---|
| type | the first opted-in scope in the reference site's lookup order (§4.3) |
| local name | the name rule in §5, one rule for both block kinds |
| `name` | the PAN-OS name the reference names |
| `location` | `location_block` for the identity the referrer holds (§4.2) |

A second site with the same identity uses the same block, and a site in another
context writes its own, because PAN-OS resolves a name in the referrer's own scope
before the shared section. The blocks go in one file for the run,
`read_through.tf`, so a reader can separate what the run read from what the plan
will read. The file is written only when it has blocks, in sorted (type, local
name) order, so it is byte-identical between runs.

Two rules hold for a read-through run:

- A read-through name is not an entry the parse read, so the entry report, the
  property scan, and the shadow scan cannot name it (§3.2, §4.5). No matrix row
  covers a `data` block, so a property finding cannot name one either. The record of
  the run is `read_through.tf` plus the `README.md` label.
- The run labels itself, because a `data` block resolves at plan time and fails at
  plan, not at validate. A declared scope turns every name outside the run into a
  `data` block, including a built-in such as `any`, because no verified built-in name
  table exists, so the label names the declared scopes and the block count and states
  what a reader must check.

The gate reads these blocks with the same reader (§4.6). Pinned by
`tests/test_data_blocks.py`.

### 4.8 Import blocks (opt-in)

An `import` block binds a resource block to the object the live config already has, so the first plan
for a unit reads `N to import, 0 to add, 0 to change, 0 to destroy` for the entries the parse models.
The shape is opt-in and off by default: a run that declares no `--import-blocks` writes no import file
and the same `.tf` bytes as before, so both golden sets stay byte-identical. This is the §4.7 precedent.

The file is `imports.tf`, one file for the run, one block per entry the run declares, written only when
the run declares the shape and has a block to write. A `.tf` file is the choice, because the gate rule
reads `.tf` files only (§4.5); a data file could not be a gate input.

One block per entry:

| Part | Value |
|---|---|
| `to` | the block address, `<resource type>.<local name>` |
| `id` | base64 of the JSON object: `{"location": <the location sub-block as the block states it>, "name": <the entry name>}` |

The two fields come from the same data the resource block uses. `location_data` is the one location
rule, and `declare_block_name` is the one naming rule, so the block and the id cannot state two
different facts. `import_blocks.py` states the id shape, the row shape, and the order; it resolves no
name, picks no location, and defines no naming rule. The JSON keys sort at every level with compact
separators, and the file is ASCII, so two runs on the same bytes write the same bytes. `decode_id` is
the inverse of `build_id` and refuses a value that is not the declared shape, the way the data-file
readers refuse a row that is not the declared shape.

A field the generator does not emit is not in the id. The provider's `location.device_group` row has a
`panorama_device` field, and the docs example states one, but no parse fact names a device, so the tool
states no device fact. Blocks print in unit order, then local-name order, and no block names a
timestamp or a path.

The four `*_policy_rules` types write no block, and each rule entry is one WARN finding, because their
import object names the rulebase, the position in the live rulebase, and a list of names. The parse
records no rulebase for an entry (F3.5 gates the accepted value), and `position` is live-config state,
because a chain anchors at `where = "last"` (§4.4). The four types are the rows `LOCATION_SCHEMA`
declares `rulebase` for, so no second table names them. The rule types stay out of the id until F3.5
decides the rulebase and a source states the position.

Pinned by `tests/test_import_blocks.py`, including the id round trip, each violation type the gate rule
detects, the rule-types decision, the no-false-positive run across the fixture corpus, the order, the
byte equality between two runs, and the golden no-change rule. The provider example is pinned in
`docs/CODEBASE_ASSEMBLY.md` §12.

## 5. Naming rules

The local name of a block is **the sanitized PAN-OS name plus an 8-hex digest of
the source identity**. One rule serves both block kinds (F5.5): a read-through
`data` block takes the name the object would have had as a `resource` (§4.7).

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
- The unit directory name (F6.1) reads through this one rule as an argument, so the rule it owns
  is the digest input: the four scope facts, joined by `|`, in `SCOPE_FACT_KEYS` order
  (`unit_manifest.py`, §3.4). No second naming rule exists, and the test pins that the module
  defines none.
- Taken names are tracked per type (one domain per `scope`), for both block kinds.
  A true duplicate gets a numeric suffix (`_2`), so the output is always valid HCL.
  The suffix is a validity guard, not the identity mechanism: two different
  identities never need it.
- `device` is not in the digest. It indexes a declaration so a reference from one
  device cannot resolve to another device's resource of the same name.
- A block a reference site creates (a read-through `data` block, §4.7) enters no
  declaration index, because it stands for an entry this run did not read, so a
  plain reference cannot resolve to it.

Pinned by `tests/test_dependency_wiring.py::test_local_names_are_sanitized_name_plus_digest`,
`tests/test_robustness.py::test_declare_resource_name_is_order_independent`,
`::test_declare_resource_name_avoids_collisions`,
`::test_sanitization_collisions_get_unique_names`,
`::test_declare_empty_name_gets_a_stable_name`,
`::test_declare_same_name_in_two_contexts_gets_unique_names`,
`::test_declare_same_name_in_two_vsys_gets_unique_names`,
`tests/test_edge_cases.py::test_dup_names_across_vsys_emit_distinct_digests`,
`::test_identity_to_name_assignment_survives_entry_order_flip`,
`tests/test_multi_device_template.py::test_same_interface_name_on_two_devices`, and
`tests/test_data_blocks.py::test_the_read_through_path_cannot_change_a_resource_name`.

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
  claim testable. The goldens are the bytes of a run that declares no read-through
  scope, so the plain-string default stays pinned. A read-through run pins its own
  bytes: the block list sorts by type then local name, the block for an identity is
  the first block written for it, and the `README.md` label states the sorted scopes
  and the block count
  (`tests/test_data_blocks.py::test_the_read_through_file_is_byte_identical_between_runs`).
- The provenance record (§3.3) states no timestamp and no value the run did not receive, so
  two runs with the same arguments write the same record bytes. Its `path` field is the path
  the run received, so the cache name is the only cache-derived value in it, and that name
  comes from the request identity, not from the cache directory. Pinned by
  `tests/test_provenance.py::test_two_runs_on_the_same_bytes_write_the_same_record` and
  `::test_a_cache_derived_name_repeats_across_cache_dirs`.
  Determinism is pinned by test, not paid in the CLI.
- The manifest sorts rows by the unit identity and sorts the reference names, and no field states
  a timestamp or a path, so two runs on the same bytes write the same bytes from two different
  output directories
  (`tests/test_unit_manifest.py::test_two_runs_write_the_same_bytes` and
  `::test_the_manifest_names_no_path_and_no_timestamp`). A directory name comes from the unit
  identity digest and not from the set of units in the run, so a name does not move when an
  unrelated scope is added (`::test_a_directory_name_does_not_move_when_an_unrelated_unit_is_added`).
- The import file prints one block per entry in unit order, then local-name order, sorts the JSON keys
  at every level, and states no timestamp or path, so two runs with the same arguments write the same
  bytes (`tests/test_import_blocks.py::test_two_runs_write_the_same_bytes` and
  `::test_the_file_names_no_timestamp_and_no_path`). The goldens are the bytes of a run that declares no
  import block, so the default stays pinned
  (`::test_a_run_that_declares_no_import_blocks_writes_the_golden_bytes`).
- The shadow scan sorts findings by line, then object type, then name, and the parent index keeps
  the first parent row for a key, so two runs on the same two sources write the same bytes
  (`tests/test_shadow_coverage.py::test_two_runs_on_the_same_sources_write_the_same_bytes`).
- The state scan keeps the first state entry for an ownership key, in document order, and sorts
  findings by line, then object type, then name, so two runs on the same arguments and the same
  bytes write the same bytes
  (`tests/test_state_coverage.py::test_two_runs_on_the_same_bytes_write_the_same_bytes`). A state
  read is a file read, so no cache-derived value enters its record.

## 7. What this document does not claim

These are planned (`PLAN.md`) and not implemented:

- **Rulebase** — not recorded, so not emitted.

F4.1 is implemented (§4.6): the static rules run on every conversion, and the
result is `SANITY_REPORT.txt`. F4.2 is implemented (§3.1): the container table is
code, the parse records the source line of every element, and an uncovered section
is reported. F4.3 is implemented (§3.2): one report row per entry the parse read,
with its destination, and a gap section for the rows that write nothing. F4.4 is
implemented (§3.1, §3.2, `docs/COVERAGE_MATRIX.md`): each matrix row names the
properties its emitter reads, and a captured property no output read is reported for
an entry a row covers. A field gap in a container no row covers is not reported; it
is recorded in `backlog.md`.

These are decided limits, not bugs: the rulebase is not emitted, security profile
bodies are not parsed, EDL credentials are never written, a service emits one
protocol leg, `location.template_stack` is never used, a template that
targets two devices keeps interface names as strings, a state scan compares only
a property both sides name the same way (the parse key `tags` and the provider
attribute `tag` are not compared), a state source is read only: it has no
write path, and a read-through run cannot name the scope that holds a name outside
the run or recognise a built-in name, because no verified table for either exists,
so such a run is labelled (§4.7). Each one is recorded in `backlog.md`.
