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
| `resource_mapping.py` | The verified provider contract: `EMITTED_TYPES`, `REPORT_ONLY_TYPES`, `NOT_EMITTED_TYPES`, `LOCATION_SCHEMA`, `INTERFACE_RESOURCE_TYPES`, `COVERAGE_MATRIX` | the single source of truth; no resource name or attribute from memory |
| `split_device_groups.py` | Optional pre-processing: one XML file per device group | joins scopes on the device the export lists; copies with `copy.deepcopy` |
| `container_coverage.py` | The container table (§3.1) and the section rule | the table is data, so a parse method cannot exist without a row |
| `entry_coverage.py` | The per-entry report (§3.2) | a destination comes from the table row, or from the mark when the method knows better |
| `shadow_coverage.py` | The cross-source shadow scan (§3.2): a child entry name that repeats a parent entry name | the key is the matrix row, not the name alone; both sources are read with the same row rule, so no second naming rule exists; a run with no declared parent has no parent to read |
| `state_input.py` | The state producer (F5.6): a Terraform state document read as a reference source, through the same door | the two byte checks run on the state bytes, and only the parse step is chosen by the kind, so a `<!DOCTYPE` inside a JSON value is not a refusal; a document the identity key cannot read is an input refusal; the state source writes no output, so no `.tf` byte changes |
| `state_coverage.py` | The state scan (§3.2): the ownership fact and the drift fact | the matrix row is the same table the property scan uses, keyed by the resource type; the ownership key is §2.1 identity with the declared facts, never the `Shared` fallback; the scan is not an output, so it reads captured values without recording |
| `sanity_checks.py` | The post-run gate (F4.1): each static rule stated once | the gate reads the written files, not the generator's state |
| `provenance.py` | The provenance record (F5.3): what the run read, as `SOURCE.txt`, one record per source read (F5.4) | the record states the bytes the door parsed and never the credential; the cache reference a prune action reads is the `cache_entry` field, not a printed line |
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

- `CONVERSION_REPORT.txt` — one line per config entry the parse pipeline read (§3.2). Section
  order is fixed: report header, summary, gaps, property findings, shadows, then the grouped entry
  lines. Each section prints only when it has content, and the shadow section prints only for a run
  that declares a parent source (`--path` with `--parent`, the api source only; a path that is not
  a scope path is an argument error, exit 2).
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
  both, and the conversion report uses it for the property section and the shadow section, so
  they cannot disagree.

The post-run gate writes `SANITY_REPORT.txt` on every run (§4.6). The five files
above are the complete set the generator writes; `main()` adds `README.md` and the
provenance record `SOURCE.txt` (§3.3), which every completed run writes.

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
- The provenance record (§3.3) states no timestamp and no value the run did not receive, so
  two runs with the same arguments write the same record bytes. Its `path` field is the path
  the run received, so the cache name is the only cache-derived value in it, and that name
  comes from the request identity, not from the cache directory. Pinned by
  `tests/test_provenance.py::test_two_runs_on_the_same_bytes_write_the_same_record` and
  `::test_a_cache_derived_name_repeats_across_cache_dirs`.
  Determinism is pinned by test, not paid in the CLI.
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
attribute `tag` are not compared), and a state source is read only: it has no
write path. Each one is recorded in `backlog.md`.
