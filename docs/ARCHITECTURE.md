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

Every file in this table is a module in `src/`, except the test harness, which is in `tests/` (§1.1).

| File | Role | Rule it keeps |
|---|---|---|
| `panorama_to_terraform.py` | The converter: `PanoramaParser` (model), `TerraformGenerator` (model and write), `main()` (order) | the parser consumes only the producer contract (`ParsedSource`); it reads no file and opens no connection itself, so a source is either the file producer or the api producer |
| `xml_input.py` | The only input read, shared by every entry point, through one producer boundary (F5.1), and the scope vocabulary a source states (F5.4) | the two byte checks are one function (`check_bytes`) every source kind runs, so the size cap and the DTD refusal are kind-independent and only the parse step is chosen by the kind; one definition of the scope a source holds (`DEFAULT_SCOPE`) and of the path segment that names an entry (`ENTRY_SEGMENT`) |
| `source_fetch.py` | The api producer (F5.2): the https request, the cached copy, the response wrapper, and the per-scope request shape (F5.4) | https only; a redirect that changes the scheme is refused; the cache holds exactly the bytes the boundary parsed; the key comes from the environment only, and `API_KEY_ENV` is the only module that states its name (`CODEBASE_ASSEMBLY.md` §11); the declared path is part of the request identity, so each scope gets its own entry |
| `resource_mapping.py` | The verified provider contract: `EMITTED_TYPES`, `REPORT_ONLY_TYPES`, `NOT_EMITTED_TYPES`, `LOCATION_SCHEMA`, `DATA_SOURCE_SCHEMA`, `INTERFACE_RESOURCE_TYPES`, `COVERAGE_MATRIX`, and the scope tables `SCOPE_TYPES`, `SCOPE_PLACEMENT`, `SCOPE_ANSWER`, `SCOPE_LEVEL_ORDER` and `SCOPE_SHAPE` (F6.5), plus the value-to-variable table `VALUE_VARIABLES` (F6.6) | the single source of truth; no resource name or attribute from memory; `SCOPE_SHAPE` is the shape the provider takes, so a membership cannot be printed as a string where the provider takes an object; `VALUE_VARIABLES` covers every field `LOCATION_SCHEMA` declares, so the emitter and the gate read one table and no emitter branch decides the shape for one type |
| `split_device_groups.py` | Optional pre-processing: one XML file per device group | joins scopes on the device the export lists; copies with `copy.deepcopy` |
| `container_coverage.py` | The container table (§3.1) and the section rule | the table is data, so a parse method cannot exist without a row |
| `entry_coverage.py` | The per-entry report (§3.2) | a destination comes from the table row, or from the mark when the method knows better; `name_field` is the one rule for the field that carries an entry name into a block, so the emitter, the gate, and the matrix test read the same rule |
| `shadow_coverage.py` | The cross-source shadow scan (§3.2): a child entry name that repeats a parent entry name | the key is `state_coverage.ownership_key` read with the facts the parent row declares, so one key names one parent entry; the scan compares the matrix row and entry name part of the key; both sources are read with the same row rule, so no second naming rule exists |
| `state_input.py` | The state producer (F5.6): a Terraform state document read as a reference source, through the same door | the two byte checks run on the state bytes, and only the parse step is chosen by the kind, so a `<!DOCTYPE` inside a JSON value is not a refusal; a document the identity key cannot read is an input refusal; the state source writes no output, so no `.tf` byte changes |
| `state_coverage.py` | The state scan (§3.2): the ownership fact and the drift fact | the matrix row is the same table the property scan uses, keyed by the resource type; the ownership key is §2.1 identity with the declared facts, never the `Shared` fallback; the scan is not an output, so it reads captured values without recording |
| `sanity_checks.py` | The post-run gate (F4.1): each static rule stated once | the gate reads the written files, not the generator's state; one block reader serves every block kind a rule reads, so a fact about a block is reported once; the plan check runs once per unit directory the record names, so the report prints one result per unit and names the directory it ran on |
| `provenance.py` | The provenance record (F5.3): what the run read, as `SOURCE.txt`, one record per source read (F5.4), and the prune action `--prune-cache` gates | the record states the bytes the door parsed and never the credential; the cache reference a prune action reads is the `cache_entry` field, not a printed line; the record file is a codebase root-set file, so the action reads the record file the same run wrote |
| `naming.py` | The §5 sanitizing rule, stated in one module (F6.6): the shape a PAN-OS name takes when it becomes a Terraform name, and the `var.` text a block prints for a site value | one rule, three callers: the local name of a block, the unit directory name, and the variable name of a site value. The gate reads it without the generator, so `TerraformGenerator.sanitize_name` is a delegate and every other module takes the rule as an argument or reads it here |
| `unit_manifest.py` | The unit as data (F6.1): one row per declared scope, as `CODEBASE_MANIFEST.json` (§3.4) | the rows come from the ledger, so the module adds no parse data; it takes the §5 naming rule as an argument, so no second naming rule exists; the reference names arrive from §4.3, so this module resolves no name |
| `ownership.py` | The owner of a repeated name (F6.2): one row per entry a matrix row covers, as `OWNERSHIP.json` (§3.5), and the report finding for a case the rule cannot decide | the row scope is the F4.4 rule read through the report row, so no second scope rule exists; the identity key and the naming rule are read through `state_coverage` and `unit_manifest`, so no second key or naming rule exists; `disable_override` names the entry that cannot be overridden, not the owner; the scan reads a captured value without recording |
| `reference_edges.py` | The reference between units (F6.3): one row per pair, as `REFERENCE_EDGES.json` (§3.6), the acyclic rule, and the unit order on the manifest row | the edge set is the names §4.3 recorded, so this module records no name and resolves no name; the target is the ownership `owner`, so the pair joins to §3.4 on `directory` and to §3.5 on (`type`, `entry`); a row that names one unit is refused; the order comes from the three bases §6 of `CODEBASE_ASSEMBLY.md` states, read through the module that holds each fact |
| `site_data.py` | The site as data (F6.6): one row per site that names a value, as `SITE_DATA.json` (§3.7), and the `.tfvars` written from the rows | the row joins to §3.4 on `directory`, so no second unit rule exists; the module resolves no name and names no value the run did not print; the `.tfvars` is the printed form of the data, not the generator's state; `parse_rows` refuses a shape it does not declare; the name is the §5 rule read through `naming.py` |
| `import_blocks.py` | The import block (F6.4): one block per entry, as `imports.tf` (§4.8), and the id shape | the block is built from the same data the resource block uses, so this module states no location rule and no naming rule; the id is the base64 JSON object the provider documents, and `decode_id` refuses a shape it does not declare; the four `*_policy_rules` types are the rows `LOCATION_SCHEMA` declares `rulebase` for, so no second table names them |
| `write_path.py` | The write path (F6.10.3): the one function that writes a file, and the two path builders, one per file set (§6) | the LF rule is enforced here and nowhere else, so no module of the tool writes a file outside it; `bytes` are written without translation, because the cache holds the bytes the input door parsed; the module states no unit rule and no naming rule, because a per-unit file names its unit only by its directory (§14 of `CODEBASE_ASSEMBLY.md`) |
| `tests/conftest.py` | The test harness and the paths the tests read the layout through | the tests call the same implementation the tool uses, so a rule is stated once; each rule in this document names the test that pins it |

### 1.1 The repository layout

The layout is a rule, and this section is its owner document. `AGENTS.md` names the tracking markdown set,
and the four readme indexes (`README.md`, `docs/README.md`, `examples/README.md`, `tools/README.md`) name
every document under them, so a file outside an index is a finding.

- The root holds `AGENTS.md`, the readme indexes, the tracking markdown, the two license files
  (`LICENSE-AGPL` and `LICENSE-COMMERCIAL`), and the two tool-config files (`pyproject.toml`, which states
  the rules below, and `requirements.txt`, the pinned development tools). The root index names each of them.
- `docs/` holds every other document. `tests/` holds every test. `src/` holds the tool's modules.
  `tools/` holds the developer scripts. `examples/` holds the sample input and the two example text files.
  Each directory that holds files names them through its own index.
- The canonical sample output is the golden set `tests/golden/`, which pins the bytes of a real run.
  `terraform_output/` is only the default value of `--output-dir` and holds no committed sample.
- `tests/` is flat: the test files sit beside `fixtures/` and `golden/`, and `tests/conftest.py` is the one
  shared helper file. No test is grouped by rule area, so the layout does not change again.

The import rule: `src/` is one flat namespace, so a module in `src/` imports its siblings by plain module
name, and no module builds a path. `pyproject.toml` `[tool.pytest.ini_options] pythonpath = ["src"]` is the
only place the path is stated for tests; `testpaths = ["tests"]` keeps discovery at the repository root,
where no test file sits. A run from `src/` gets the same namespace from Python's script-directory rule, so an
entry point adds no path code. The project is standard library only, so every import stays offline and
deterministic, and there is no package build. `tools/` needs no import rule, because `tools/build_kitchen_sink.py`
assembles the fixture corpus from committed files and imports no tool module: it is a developer tool, not an
entry point, so it does not use `xml_input` and states the F3.8 checks itself, and the tool takes no
command-line path. It is a generator, not a pin: `tests/fixtures/kitchen_sink.xml` is the record the golden set
and the corpus pins read, and the record is curated by hand, so the tool prints the tree it assembles and writes
no file. Its read rule is the two F3.8 checks read on the committed bytes, so a fixture that declares a DTD, or
that the parse cannot read, is skipped by rule and not by name, and the record is not an input. `tools/` is not
on the test path, so `tests/test_build_kitchen_sink.py` reads the tool's functions through `importlib` on the
path `tests/conftest.py` builds once. `tools/quick_start.sh` runs the sample input and is a demonstration, not
part of the converter.

A pin that reads a module source reads it through the import rule (`Path(module.__file__)`) or through the
paths `tests/conftest.py` builds once. The writer scan reads the `src/` set: the single writer
`src/write_path.py` is the exception, and the test harness is not a tool module, so it is outside the set
(`tests/test_write_path.py`).

## 2. Data model

### 2.1 Identity

Identity is **(device group, vsys, type, name)**. No object is keyed by name
alone. A name that repeats in two device groups, or in two virtual systems, is
two objects.

Pinned by `tests/test_edge_cases.py::test_dup_names_across_dgs_both_survive`,
`tests/test_edge_cases.py::test_dup_names_across_vsys_both_survive`, and
`tests/test_robustness.py::test_declare_same_name_in_two_contexts_gets_unique_names`.

### 2.2 The five scope facts

`PanoramaParser.identity_of(elem)` returns five facts. Every parse method
splats them onto every object it returns, so the emitter can place a resource
without reading the XML again.

| Fact | Value | Rule |
|---|---|---|
| `device_group` | the defining device group | `Shared` is the parser fallback for an entry it cannot place, not a declared device group |
| `vsys` | the declared virtual system | `''` when the export declares none; never an invented `vsys1` |
| `template` | the declared template | `''` when the export declares none |
| `vsys_device` | the device that owns the entry | `localhost.localdomain` is the PAN-OS "this device" placeholder and names no firewall |
| `template_stack` | the stack that owns the entry (F6.10.5) | `''` when the export declares no stack. The entry that defines a stack names the stack, so this fact is what names a stack unit (§3.4) |

`template_stack` was added by F6.10.5. Before it, a variable inside a stack took the stack name as
the `template` fact, so one fact carried two meanings: the template the entry sits inside, and the
stack the codebase unit is named for. The fact order is the unit identity join (§5), so it is
appended rather than inserted, and every unit digest is re-measured.

Pinned by `tests/test_multi_vsys_location.py::test_parser_records_declared_scope`,
`::test_parser_records_no_invented_scope`, and
`::test_every_parse_method_records_the_five_scope_facts` (the rule holds for
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

One parse method returns a table instead of an object: `parse_associations` (the
membership the export declares). `parse_bgp` and `parse_ospf` return one level of
the router's `protocol` object (§4.9), and the router entry is marked once by
`_parse_router`, so they fill the `protocol` field of that mark instead of keeping
a record of their own.

### 2.4 Where each parsed entry goes

Eight destinations. Every entry lands in one of them.

| Destination | What it means |
|---|---|
| Emitted resource | the type is in `EMITTED_TYPES` |
| Report entry | `REPORT_ONLY_TYPES` (no v2 resource) or `NOT_EMITTED_TYPES` (v2 resource exists, body not parsed), plus the `report_only` address entries |
| Inventory comment | `security_profiles.tf`: names and descriptions only, with the resource name the emitter would use |
| Count only | `parse_regions`: no resource and no report entry. The per-entry report line (§3.2) is the only output its entry reaches, so it prints what the entry captured. The honesty rule for that line is in [`COVERAGE_MATRIX.md`](COVERAGE_MATRIX.md) §1 |

The container table in §3.1 adds two kinds for what a parse method reads but
does not turn into an entry of its own:

| Kind | What it means |
|---|---|
| Bookkeeping | an association table or a scope fact (§2.2), and a sub-shape that only selects a shape. The per-entry report line (§3.2) is the only output a membership entry reaches, and the fact the row records is the relation between that entry and the container that lists it, so the entry carries no value for it and the line names no field. The honesty rule for that line is in [`COVERAGE_MATRIX.md`](COVERAGE_MATRIX.md) §1 |
| Nested block | lines written inside a parent resource block, not a resource of its own. The per-entry report line (§3.2) is the only output its entry reaches, so it names only the fields the print reads through the captured object. The honesty rule for that line is in [`COVERAGE_MATRIX.md`](COVERAGE_MATRIX.md) §1 |

The per-entry report (§3.2) adds two kinds for a single entry, because a
container row cannot state a per-entry fact:

| Kind | What it means |
|---|---|
| Skipped | a parse method visited the entry and did not model it: no name, or an `id` reference pointer |
| Unaccounted | no parse method read the entry, so no table row covers its container |

The `count-only` row is the destination the converter cannot model today: measured
against the pinned provider, no resource or data source names a region, so no emitter
can exist for a region entry. The F4.3 per-entry report lists it as a gap, so the
operator sees which entry it is instead of the document claiming every entry is
accounted for.

A captured field that no output reads is a property gap, and the property scan reports
it for a container the matrix covers (§3.2). A destination with no matrix row has no
declared property list, so the rule that keeps such a field honest names the output that
reads it (`COVERAGE_MATRIX.md` §1). The gap that has no rule yet is recorded in
`backlog.md` instead.

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
     key is read from the environment only, never from a command line, so it does not appear
     in a shell history or in a process list; the environment name is stated once, in
     `API_KEY_ENV`, and `CODEBASE_ASSEMBLY.md` §11 owns the rule for both layers, so this
     section names no name. Standard library only: the
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
   child → parent map once. The five scope facts walk that map.
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
  five scope containers in §2.2. A container inside a config-object entry is a
  property level, and the property scan (F4.4) covers it (§3.2). The scan scope is
  the entries a matrix row covers, so a report, inventory, bookkeeping, count-only,
  or nested-block container is not a property finding: it has no row, and only a row
  can name the properties an emitter reads. Those field gaps are recorded in
  [`../backlog.md`](../backlog.md).
- A section no row covers is a finding. The scan reports it in
  `MANUAL_SETUP_REPORT.txt` with its source line and entry count, and prints one
  console line per finding in the shape §3.2 states. An absent section is not a finding, an empty known
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
  content is `report`, and a skipped entry is `skipped`. A scope entry takes the
  destination its table row states (F6.5): the five scope containers and `variable`
  are `emitted` rows, so a scope entry is an object the output writes, and the
  membership lists inside a scope entry stay `bookkeeping`, because no provider
  resource exists for a device.
- **An entry the output cannot express is a report row, and the file holds no half of it** (F7.1): a
  peer no peer group names, an OSPF interface outside an area, a `one_of` value the mapping cannot state,
  and an OSPF `range` entry that states neither choice are marked `report` with the reason, and the parse
  does not put them in the printed list. The report names the whole entry, so an operator sees the choice
  the tool could not make. Pinned by `tests/test_parse_network.py` and
  `tests/test_protocol_object.py::test_an_unmapped_one_of_value_prints_nothing_and_is_reported`.
- **Captured fields** are the keys of the object the method built, minus the entry
  name and the five scope facts (§2.2), minus keys with no value, in sorted order.
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
  including the corpus findings, the parity with the matrix row, the scan scope, the report
  section, and the console line for a finding. The console prints that line too, in the shape
  this section states at the end: the entry, its position, and the fact, and no matrix row,
  because a console line has no room for a fixed-width column.

**The cross-source shadow scan** (F5.4) adds one finding kind, in `shadow_coverage.py`, and the
report prints it in its own section after the property section:

```text
  line <source line>  <object type>/<entry name>  <matrix row>  parent entry: <parent scope> / <object type>/<entry name>  parent source: <parent name> (parent line <n>)
```

The `parent entry` field names which parent entry the child repeats: the parent scope read through the
F3.9 grouping rule, then the parent entry identity. The child entry name and the parent entry name are
the same text, so this field is what tells the two entries apart. One finding names one parent entry, so
a child entry whose name matches parent entries in two scopes gives one finding per parent entry: no
parent entry is dropped, and report order puts the findings for one child entry in the parent report
order.

A child entry is a shadow when its name repeats a parent entry name and both entries are covered
by the same matrix row. The matrix row is the part of the key the scan compares, so a shadow is a
fact within one container kind: an address that repeats a shared address of the same name is a
shadow, and a service group with the same name is not. The key itself is the ownership key rule
this section states below for the state scan, read with the facts the parent row declares, so the key
names the parent scope and one key is one parent entry; the child entry is compared on the matrix
row and entry name part, because the child names its own scope. The scan scope is the rule above,
and the parent source is read with the same container helpers and the same row rule, so no second
naming rule exists. A run with no declared parent has no parent to read, so it prints no shadow
section. The second source is what makes the name visible: a per-device-group run cannot see its
parent, so an inherited name stays a plain string and the parent entry is invisible. The console
prints the shadow line too, in the shape at the end of this section, and its source field is the
minimum actionable part of the record: the parent source named by its report value, because the
operator's action is to open that source, and the name identifies it. The path is in the provenance
record (§3.3), and the parent entry and the parent line stay in the report, because the shape names
one position and one identity. A shadow is an operator action, so it does not change the exit code.
Pinned by `tests/test_shadow_coverage.py`, including the fixed line shape, the parent entry field, the
key read through `state_coverage.ownership_key`, one finding per parent entry, the scan scope, the
grouping, the console line and its source field, and the no-parent run.

**The repeated-name scan** (F6.2) prints its findings in its own section, after the shadow section and
before the two state sections:

```text
  line <source line>  <object type>/<entry name>  <matrix row>  <reason>
```

The scan adds no fact kind of its own: it decides the owner for the entries §3.1 covers, and the
report prints the case it cannot decide. Its rules are in §3.5. A finding is an operator action, so it
does not change the exit code, which the F4.1 gate decides, and the console prints no line for it,
because its fact compares two entries and the console shape names one identity.
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
five declared facts, read from the `location` block the state document holds, through the block names
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
property finding. Both facts are grouped by the same F3.9 scope rule, the console prints no state line
because each fact names two identities and a second position, and both are operator actions, so neither
changes the exit code, which the F4.1 gate still decides.
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

**The console line shape.** One function states it, `container_coverage.console_line`, and no module
defines a second one: a scan states its fact phrase and its block header, and calls that function. A
console line names four parts, in this order, and nothing else:

```text
  - <scope>  <position>  <identity>  <fact>
```

- `<scope>` is the F3.9 grouping rule above, so a console line names the scope the report section
  names. A finding the report does not group prints no scope part.
- `<position>` is one position: the entry's source line, or `position unknown`. The console keys a
  finding on the same line number the report row keys it on, so the console line and the report row
  name the same entry. A fact that needs a second position, such as the parent line or a state
  resource address, keeps it in the report.
- `<identity>` is the F4.3 row identity `<object type>/<entry name>`, or the container path for a
  container finding, because a container finding names a container rather than one entry. One
  identity per line, so a fact that compares two entries, or two units, stays in the report.
- `<fact>` is the words the report line already uses for the finding, so the console and the report
  cannot disagree. It may name the captured fields, which are the parsed-object key names, never the
  XML tag (F4.3 rule 5), and the entries the fact covers.

A console line names no fixed-width matrix-row column, so the matrix row stays in the report. The
source field it may name is the minimum actionable part of the provenance record (§3.3): the source
name, the same report value the report bodies use (F4.2 rule 6). The path, the kind, the request, the
cache entry, the size and the hash are not on a console line, because a printed line protects nothing
and the record is where the eight fields live. A block prints only when it has a finding, so a run with
no finding in that kind prints nothing new. Four kinds print: the container coverage finding, the gap
entry, the property finding, and the shadow line. The ownership, state and edge scans print in the
report only, because their facts compare two identities or need a second position. Pinned by
`tests/test_container_coverage.py::test_the_console_line_shape_is_stated_in_one_place`,
`tests/test_property_coverage.py`, and `tests/test_shadow_coverage.py`.

### 3.3 Provenance record

`main()` writes one record per source the run read, as `SOURCE.txt` in the output directory, in
read order: the main source, then a declared parent source (F5.4), then the state source (F5.6). A
one-source run writes the same bytes as the F5.3 rule. The record names the bytes a reader can
reopen, so a report line can be checked against the file it describes. Eight fields, in this order:
`kind`, `name`, `path`, `scope`, `request`, `cache_entry`, `size`, `sha256`. A field that does not
apply to the source kind is `-`, so one shape reads. Records are separated by one blank line, which
is the whole record shape. The rule lives in `provenance.py`.

Five rules the record keeps:

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
- **The pruning rule, and the action that runs it.** A cache entry is not pruned while a written record
  references it, so the reference is the `cache_entry` field of a parsed record, never a printed line. A
  shadow line prints a source name, and that printed line protects nothing. A state record has no request
  and no cache entry, so it references nothing and prunes nothing (F5.6). `provenance.prunable_entries` is
  the decision, and `provenance.prune` is the action that runs it: it reads the record file back through
  `parse_records` and removes what the decision names. `--prune-cache` gates the step, off by default, and
  applies to `--source api` only (exit 2), because a file record states `-` for the cache field. The step
  runs after the record is written, because the written record is the reference, and after the gate, so the
  exit code the gate decided does not move: a prune that removes nothing changes nothing, and a record the
  action cannot read is a refusal (exit 1). A cache directory that holds no entry has nothing to prune, so
  it is not a refusal. The run prints one line per entry the action removed, and prints nothing when it
  removed nothing, because the action is not a finding kind and the console shape belongs to findings.
  Pinned by `tests/test_provenance.py::test_the_reference_is_data_not_a_printed_line`,
  `::test_a_printed_parent_source_is_not_a_reference`, and
  `tests/test_state_input.py::test_a_state_record_references_nothing_so_it_prunes_nothing`; the action is
  pinned by group 6 of `tests/test_provenance.py`.
- **The record directory.** The record directory is the output directory, so the action reads the record
  file the same run wrote and no record directory exists. `SOURCE.txt` is a codebase root-set file, named
  through `write_path.root_path`, and the two-set decision is in
  [`CODEBASE_ASSEMBLY.md`](CODEBASE_ASSEMBLY.md) §14, the owner document for the file sets. A record
  directory of its own would be a third set, and `write_path.py` states two builders, one per set, so the
  module that owns the record states no path rule: the caller names the record path through the builder for
  the set the record belongs to. Pinned by
  `tests/test_write_path.py::test_the_record_directory_is_the_output_directory_for_the_prune`.

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
one combination of the five scope facts (§2.2), and a unit exists when the ledger has a report
row in it (§3.2), so the manifest is built from `entry_coverage.EntryLedger` and adds no parse
data. An entry inside a config-object entry is a property level (§3.1), so the parent row's count
covers it.

The rule lives in `unit_manifest.py`, and it holds six facts:

- **The unit name.** The deepest scope the export declares names the unit, in the F3.9 level
  order, read innermost first: `vsys`, `vsys_device`, `template`, `template_stack`,
  `device_group` (F6.10.5). A template inside a stack names its template, because the template is
  deeper than the stack. `Shared` names the unit whose five facts are empty, because the five facts
  alone cannot name the shared section. The placeholder device names no unit (§2.2), so the scope above it names the unit.
- **The identity.** `facts_of` reads a ledger row or a parsed object through one function, so both
  land on the same unit: it drops the `Shared` parse fallback from `device_group` (§2.2 rule).
- **The directory name.** `sanitize(unit name) + '_' + 8-hex digest of the identity`, in the §5
  shape. The digest is always present, not only on a collision, so a name never depends on the
  other units in the run. The module takes the §5 rule as an argument, so it defines no second
  naming rule. It names the directory, and the write path (§6) writes the directory it names.
- **The row shape.** `unit`, `device_group`, `vsys`, `template`, `vsys_device`, `template_stack`,
  `directory`, `entry_count`, `references`. Fields print in the declared order, the rows sort by
  the identity, and the reference names are sorted. `parse_rows` reads a written file back, and a row that is
  not the declared shape is a refusal, the way `parse_record` refuses a line (§3.3 rule).
- **One file per codebase run.** The edge list needs the whole set of units, so one file holds one
  row per unit. A manifest row for a unit with no ledger row adds nothing, so every recorded name
  belongs to a unit the ledger shows.
- **The content rule.** The file is written only when it has content, following the rule for the
  report files (§4.5). A run that reads no entry writes no manifest, and the record is still
  written. A plain run writes it, so the CLI takes no flag for it.

The `references` field holds the names the reference rule could not resolve inside the referrer's own
unit (§4.3), keyed by the referrer's five facts. The record is made at the site that applies the rule,
so no second resolution rule exists. A name another unit declares is recorded for the referrer's unit,
because the rule records the referrer's fact and the edge row names the other unit (§3.6).

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
`::test_a_name_the_referrers_unit_declares_is_not_recorded`,
`::test_the_record_names_the_referrers_unit_not_the_declaring_unit`,
`::test_a_read_through_name_is_recorded`,
`::test_every_recorded_name_belongs_to_a_unit_the_ledger_shows`,
`::test_a_name_is_stored_once_per_unit`, `::test_the_exit_codes_are_unchanged`, and
`::test_the_manifest_names_no_path_and_no_timestamp`.

### 3.5 Ownership record (F6.2)

`main()` writes one row per entry the coverage matrix covers, as `OWNERSHIP.json` in the output
directory. Ownership is a per-entry fact, so this file holds one row per entry while §3.4 holds one
row per unit, and the two data files join on `directory`. The rules are in `ownership.py` and in
[`CODEBASE_ASSEMBLY.md`](CODEBASE_ASSEMBLY.md) §4; this section states only the shape.

- **The row shape.** `type`, `entry`, `source`, the five scope facts, `directory`, `owner`, `kind`,
  `override`. `kind` is one of `declared`, `definition`, `override`, `ambiguous`; `override` is the
  flag as the parse read it: `yes`, `no`, or `unknown`; `owner` is empty when the rule names no owner.
- **The row order.** The §2.1 identity through `state_coverage.ownership_key`, then `source`, because
  two sources can state the same identity. Fields print in the declared order, not alphabetically.
- **The bytes.** `json.dumps(rows, indent=2)` with one trailing newline, ASCII output, no timestamp
  and no path, so two runs on the same bytes write the same bytes.
- **The refusal rule.** `parse_rows` reads a written file back as data and refuses a row that is not
  the declared shape, the way `parse_record` refuses a line (§3.3).
- **The content rule.** Written only when it has content, following the rule for the report files
  (§4.5). A plain run writes it, so the CLI takes no flag for it, and the gate rule `data_files`
  reads it back through `parse_rows` (§4.6, F6.8).

The scan result keeps `line`, `container`, `reason`, and the device-group `chain` as run facts, so they
are not written: the record states a fact, the report states a finding. `chain` is the device-group
ancestors the export states for a row's unit (F6.5), and the scan reads the `parent` field through
`entry_coverage.RecordingDict.value`, so it is not an output read and cannot move a property finding
(the F5.6 rule). The scan reads the captured flag through the same non-recording read.

Pinned by `tests/test_ownership.py`, including
`::test_the_fields_print_in_the_declared_order`,
`::test_the_record_writes_only_the_declared_fields`,
`::test_the_record_names_no_path_and_no_timestamp`,
`::test_the_record_reads_back_as_the_rows_it_wrote`,
`::test_parse_rows_refuses_a_row_that_is_not_the_declared_shape`,
`::test_two_runs_on_the_same_bytes_write_the_same_bytes`,
`::test_the_record_is_written_only_when_it_has_content`,
`::test_the_gate_reads_the_record_through_ownership`, and
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
  (§4.5). A plain run writes it, so the CLI takes no flag for it, and the gate rule `data_files`
  reads it back through `parse_rows` (§4.6, F6.8).
- **The two order fields** `rank` and `after` print on the §3.4 row, after the nine F6.1 fields,
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
`::test_the_gate_reads_the_record_through_reference_edges_and_check_order_pins_the_position`,
`::test_no_report_names_the_record_or_a_field_it_states`,
`::test_the_cycle_line_shape_is_fixed`, and `::test_two_runs_write_the_same_bytes`.

### 3.7 Site data record (F6.6)

`main()` writes one row per site that names a value, as `SITE_DATA.json` in the output directory, and the
`.tfvars` the platform reads from those rows. A site is a unit, so the row joins to §3.4 on `directory`,
the join §3.5 and §3.6 use. The rules are in `site_data.py` and in
[`CODEBASE_ASSEMBLY.md`](CODEBASE_ASSEMBLY.md) §9; this section states only the shape.

- **The row shape.** `directory`, `variables`. `directory` is the §3.4 join; `variables` is
  `{the variable name: the value}`, sorted by name. The name is the §5 rule read through `naming.py`, so
  the row states no value twice: the value is the fact and the name is the mapping result.
- **The join.** `directory` joins to §3.4, so the record states no path and no second unit rule: the
  identity and the directory name are read through `unit_manifest.facts_of` and
  `unit_manifest.directory_name`.
- **The row order.** The two fields in field order, one row per site that names a value, no repeated row,
  rows in identity order.
- **The bytes.** `json.dumps(rows, indent=2)` with one trailing newline, ASCII output, no timestamp and no
  path, so two runs on the same bytes write the same bytes.
- **The refusal rule.** `parse_rows` reads a written file back as data and refuses a row that is not the
  declared shape, including a variable name that is not the §5 shape of its string value, the way
  `parse_record` refuses a line (§3.3).
- **The content rule.** Written only when it has content, following the rule for the report files (§4.5),
  so a run that names no site value writes neither file, and the gate rule `data_files` reads the record
  back through `parse_rows` and compares the printed form with `render_tfvars` (§4.6, F6.8).
- **The printed form.** `site.auto.tfvars` is written from the rows, not from the generator's state, one
  line per variable in name order. The run writes one file per unit inside the directory the row names
  (`CODEBASE_ASSEMBLY.md` §14), so one file prints one row. Terraform loads a `*.auto.tfvars` file
  automatically, so
  `terraform.tfvars` stays the operator's own file for the credentials (`CODEBASE_ASSEMBLY.md` §11), and the
  tool writes no credential. A string prints as `json.dumps(value)`, the same escape set
  `import_blocks.unescape` reads back (§4.8); a list prints inline as `[ "a", "b" ]` and an empty list as
  `[]`. A value that is neither, and a name two rows state with two different values, are refusals: the print
  rule decides them across the record, so the gate reads the refusal only against the row it compares. The
  file is read by the data rule against the record, and it is not one of the four data files, so the
  report count names only the records (§4.5, F6.8). A printed-form finding names the path from the codebase
  root, so it names the unit the row belonged to (§14).

- **A name the tool cannot fill.** `operator_supplied` is the shape word for `target`, the NGFW serial the export
  cannot state, because it states a device as a hostname. The run records the name with no value, so no row and no
  printed-form line is written for it, and the operator supplies the value. The name is the §5 rule applied to the
  field, because an unread fact has no value to name it from. `provider.tf` is the consumer, and the declaration
  file marks a held name `sensitive` only when its row is `reference_only`, so no name list decides a marking. The
  rule is in `CODEBASE_ASSEMBLY.md` §9 rule 8, and the README names the site files (§4.5).

The values the rows state are the pairs `TerraformGenerator.printed_value` recorded at the site that
applied the value-to-variable table, keyed by the unit's five facts, the way §4.3 records a reference
name, and the shape each name came from is recorded with it (F6.10.4). This record resolves nothing, so
`variables.tf` declares exactly what the run consumed and the gate rule `variables` (§4.6) cannot see a
declaration with no consumer.

Pinned by `tests/test_site_data.py`, including `::test_the_fields_print_in_the_declared_order`,
`::test_the_row_joins_to_the_manifest_on_directory`, `::test_parse_rows_refuses_a_row_that_is_not_the_declared_shape`,
`::test_the_tfvars_bytes_for_a_string_value`, `::test_a_list_prints_inline_and_an_empty_list_prints_empty`,
`::test_a_value_that_is_neither_a_string_nor_a_list_is_a_refusal`,
`::test_the_tfvars_file_is_written_only_when_it_has_content`,
`::test_a_fact_the_tool_cannot_read_names_a_variable_and_holds_no_value`,
`::test_a_name_the_tool_cannot_fill_writes_no_row_and_no_line`,
`::test_the_provider_block_prints_target_only_for_a_unit_that_names_a_device`,
`::test_the_readme_names_the_site_files_and_states_no_row`,
`::test_the_gate_reads_the_record_and_its_printed_form_through_site_data`, `::test_no_report_names_a_field_the_site_data_states`, and
`::test_two_runs_on_the_same_bytes_write_the_same_bytes`.

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

The run writes the unit set inside the directory the manifest row names, and the codebase root set at the
codebase root (§14). Inside one unit, the file order is the order `main()` calls the emitters, so the pinned
file order is read as paths from the output directory.

The scope objects (F6.5) are a unit-set file, `scope.tf`, written inside the unit directory after
`provider.tf` and before the object files, so the reader sees
the unit before the config inside it (`docs/CODEBASE_ASSEMBLY.md` §6 and §8 rule 2).
Inside the file, blocks print in the F3.9 level order that
`resource_mapping.SCOPE_LEVEL_ORDER` states, and within a type in document order.
`variables.tf` (F2.10) is a unit-set file written after the emitters, because F6.6 made its declaration set the
values the run consumed: the file cannot state a variable the run has not printed. Pinned by
`tests/test_scope_objects.py::test_the_scope_file_is_written_before_the_config_inside_it` and
`tests/test_site_data.py::test_the_declaration_file_is_written_after_the_emitters`.
Pinned by `tests/test_scope_objects.py::test_the_scope_file_is_written_before_the_config_inside_it`,
`::test_blocks_print_in_the_level_order_the_table_states`,
`::test_entries_print_in_document_order_within_a_type`, and
`::test_the_file_is_written_only_when_it_has_content`.

### 4.2 Location

Provider v2 requires `location` on every resource. The choice comes from
`LOCATION_SCHEMA`, never from the resource name, in five branches:

0. **A scope object places itself in the scope the export puts it in** (F6.5), read through
   `SCOPE_PLACEMENT`. The four Panorama scopes place themselves, so the sub-block prints empty,
   the `shared = {}` shape. A template variable and a virtual system place inside a template or a
   template stack, and an entry the export places in neither reaches no block: the parse reports it
   as `skipped`, because the converter does not guess a place (the F3.6 rule). Branch 4 would
   report a device group as "device group dropped", which is wrong for the object that defines the
   group.
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

A location field prints as `VALUE_VARIABLES` says (F6.6): `var.<name>` for a field the table maps to a
variable, and the quoted value for every other field, so no emitter branch decides the shape for one type.
The value stays the fact in `location_data`, because the import id (§4.8) encodes the value and a variable
name is not a device name. The pair is recorded at the print site, keyed by the referrer's five facts
(§3.4), the way `name_ref` records a reference name, so the site record (§3.7) states what the run printed.
`localhost.localdomain` never enters a location (F3.5), so it never enters the mapping and names no
variable.

Pinned by `tests/test_multi_vsys_location.py`: `::test_schema_table_matches_provider_shape`
(against the live provider schema), `::test_schema_table_covers_every_emitted_type`,
`::test_location_choice`, `::test_shared_is_not_a_device_group`,
`::test_no_sub_block_outside_the_schema`, `::test_only_template_scoped_types_declare_ngfw`
(the six scope types are the scopes, not objects inside one, so they are not in
`_TEMPLATE_SCOPED_TYPES`), `::test_template_scoped_types_derive_from_schema`,
`::test_object_types_never_emit_ngfw`, `::test_placeholder_device_never_becomes_ngfw`,
the four report tests, `tests/test_schema_conformance.py::test_every_block_has_location`,
`tests/test_site_data.py::test_the_emitter_prints_a_mapped_field_as_the_table_says` and
`::test_a_field_the_table_does_not_map_still_prints_as_a_literal`, and
`tests/test_scope_objects.py::test_the_four_panorama_scopes_print_the_empty_sub_block` and
`::test_a_variable_and_a_vsys_place_in_the_scope_the_export_declares`.

### 4.3 Reference resolution (F6.10.2)

`name_ref` resolves a name inside one unit: the referrer's own. A name that points outside the
export (a built-in such as `any`, or an object in another tenant) stays a plain string. The
converter never declares a resource just to make a reference work.

Order, first match wins:

1. A name the referrer's own unit declares resolves inside the unit, as
   `<scope>.<local>.name`, where `local` is the name the naming rule (§5) gave for that unit.
2. A name another unit in the run declares is the plain name, because one plan runs against one
   root and one state, so a reference cannot name an address another unit declares. A name a
   device declared (an interface) is one case of this rule: the interface belongs to the device
   unit, so a referrer outside that unit keeps the plain name (F3.5, F3.6). The mechanism that
   carries the name is the decision in `docs/CODEBASE_ASSEMBLY.md` §5 rule 5, so this section
   states only the shape.
3. A name no unit in the run declares, when the run declares one of the scopes in this site's
   lookup order with `--data-blocks`: one read-through `data` block for the unit the site belongs
   to (§4.7). The block type is the first opted-in scope in that order, which is the order PAN-OS
   resolves a name in. The read-through branch answers a name outside the codebase, so it never
   runs for a name one unit declares and another unit uses.
4. Otherwise the plain name.

Object scopes come before group scopes, so a name that both an object and a group carry resolves
to the object.

The rule reads the unit through `unit_manifest.facts_of` at both ends: the referrer's unit here,
and the declaring unit from the record the naming site made (§5). No second unit rule and no
second naming key exists, so no call site names a context, a vsys, or a device: the referrer states
them. `key` stays for a registry key that differs from the PAN-OS name (a VPN composite key such as
`ike_gw_<name>`), and `scopes` is the lookup order.

The rule also records what it could not resolve inside the referrer's own unit (F6.1, F6.10.2).
`name_ref` takes the object the reference site belongs to and records each such name against that
object's five scope facts, so the manifest row can state the names a unit references from outside
itself (§3.4).
The record is made here, at the site that applies the rule, so no second resolution rule
exists. The same record is the edge set (§3.6), because an edge is a recorded name that an
ownership row also covers. Pinned by
`tests/test_unit_manifest.py::test_the_reference_names_are_recorded_for_the_referrers_facts` and
`::test_a_name_the_referrers_unit_declares_is_not_recorded`.

For a name another unit in the codebase owns, rule 2 above is the shape the rule returns: the plain
name. The mechanism that carries that name is decided in the design record,
`docs/CODEBASE_ASSEMBLY.md` §5 rule 5 (F6.9), so this section does not state it.

Pinned by `tests/test_robustness.py::test_name_ref_never_dangles`,
`::test_name_ref_resolves_inside_the_referrers_own_unit`,
`::test_a_name_another_unit_declares_stays_a_plain_name`,
`::test_name_ref_resolves_inside_the_referrers_own_vsys`,
`::test_name_ref_vsys_resolution_is_declaration_order_independent`,
`tests/test_multi_vsys_location.py::test_interface_reference_stays_inside_its_unit`,
`::test_virtual_router_reference_stays_inside_its_device`,
`tests/test_multi_device_template.py::test_a_template_referrer_keeps_the_plain_name_for_an_interface_another_unit_declares`,
`::test_a_referrer_that_names_no_unit_keeps_the_plain_name`,
`::test_ambiguous_template_keeps_a_plain_interface_name`, and the read-through part by
`tests/test_data_blocks.py::test_a_name_the_referrers_unit_declares_stays_a_resource_reference`,
`::test_a_name_another_unit_declares_is_the_plain_name_not_a_block`,
`::test_two_reference_sites_in_one_unit_share_one_block`, `::test_two_units_write_two_blocks`,
`::test_a_name_two_devices_declares_stays_a_plain_name_for_a_third_unit`,
`::test_the_block_type_is_the_first_opted_in_scope_in_the_lookup_order`,
`::test_a_data_block_enter_no_declaration_index`, and the fixture run by
`tests/test_dependency_wiring.py::test_security_rule_zone_address_service_refs`.

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
  cannot carry, and the placeholder template. The routing section prints only the rows the ledger marks
  `report` (`entry_coverage.protocol_report_rows`), so it holds no duplicate of the `.tf`: an entry the
  emitter printed is not named here. Each row names the scope and the router, because two routers in two
  scopes can hold the same values, and it uses the same grouping rule as the other two reports. The row's
  level is the last part of the shape table's path, and its reason is the mark detail; a row whose reason is
  the container row's note states no detail of its own. The fields are the ledger's field list, read through
  the captured object, so the report cannot state a field the shape table does not declare, and the property
  scan counts the report's read as an output use. Pinned by
  `tests/test_reports.py::test_protocol_report_sections_name_the_scope_and_the_router`,
  `::test_protocol_report_prints_only_what_the_file_cannot_hold`,
  `::test_protocol_report_is_byte_identical_between_runs`, and
  `::test_device_router_section_names_the_device`.
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
`CODEBASE_MANIFEST.json` (§3.4), the ownership record `OWNERSHIP.json` (§3.5), the edge record
`REFERENCE_EDGES.json` (§3.6), the site record `SITE_DATA.json` (§3.7), and the `.tfvars` written from
the site record, `site.auto.tfvars`.
`SANITY_REPORT.txt` and `SOURCE.txt` are written on every completed run, and the four report files
above, `scope.tf` (§4.1), `read_through.tf`, `imports.tf`, and the four data files are written only
when they have content. These files are the complete set a run writes.

The four data files are not report bodies, so no report names them or restates a row. `README.md` is the file
inventory, so it names the site record and its printed form as files (F6.10.4, `CODEBASE_ASSEMBLY.md` §9 rule 9),
and states no row, no value, no mapping result, no count, no path and no timestamp. The gate reads the
`.tf` files for the block rules, and it reads the four data files for the data rule (F6.8), which reads
each row shape through the module that owns it, so no second shape rule appears. `site.auto.tfvars` is the
printed form of the site record, so the data rule compares it with `site_data.render_tfvars` and does not
count it as a data file. `imports.tf` is a `.tf` file, so the block rules read it (§4.6). Pinned by
`tests/test_unit_manifest.py::test_no_report_names_a_field_the_manifest_states` and
`::test_the_gate_reads_the_manifest_through_unit_manifest`, by
`tests/test_ownership.py::test_no_report_names_a_field_the_record_states` and
`::test_the_gate_reads_the_record_through_ownership`, by
`tests/test_site_data.py::test_no_report_names_a_field_the_site_data_states` and
`::test_the_gate_reads_the_record_and_its_printed_form_through_site_data`, and by the whole of
`tests/test_data_file_gate.py`.

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
conversion. It reads the `.tf` files for the block rules and the four data files
for the data rule (F6.8), and the report names both counts. The splitter writes
XML, so it has no `.tf` file and no data file to check.

The reader walks the codebase root and the directories under it and keys each `.tf` file by the path from the
codebase root, so a finding names the unit the file belongs to: a per-unit file names its unit only by its
directory (§14 of `CODEBASE_ASSEMBLY.md`). The plan check runs once per unit directory the manifest record
names, because a unit is one plan and one root, so the report prints one result per unit and names the
directory it ran on — the finding names it, or the note names it when the plan passed. `result_of` is the worst
result the check produced, so a unit that failed is not hidden behind a unit that passed. The two report counts
name the two sets: the `.tf` files the reader read, and the four records at the root
(`tests/test_write_path.py`, `tests/test_sanity_gate.py`).

A value constraint the provider carries in its code, not in the schema JSON, is not data the gate can read, so
it cannot become a gate rule: the gate is static, and its input is the files it wrote plus the tables it reads
offline. The emitter prints the value the export states, and the `terraform` check is the rule that reports
such a value as FAIL when the run uses `--validate`, so the report is the operator's notice. A fixture a plan
pin reads is test data, so it states the value the provider accepts. Pinned by
`tests/test_terraform_validate.py::test_terraform_validate_kitchen_succeeds`, which runs the plan once per unit
directory the record names so the pin reads the files the run wrote, and
`tests/test_sanity_gate.py::test_kitchen_sink_gate_passes_with_validate`, which reads the report the run wrote.
The provider fact itself is recorded in `backlog.md`, as a fact the tool cannot read offline.

| Check | Rule | Severity |
|---|---|---|
| `emitted_types` | every resource type is in `EMITTED_TYPES` | FAIL |
| `location_present` | every `resource` and `data` block carries a `location` block | FAIL |
| `data_blocks` | every `data` block matches the `DATA_SOURCE_SCHEMA` row for its type | FAIL |
| `import_blocks` | every `import` block agrees with the `resource` block it names: the type, the local name, the entry name, and the location | FAIL for a violation; WARN for a rule type the shape cannot state (§4.8) |
| `scope_blocks` | a name written inside a scope block's `location` names a scope this run declares, by the type that defines that scope | FAIL |
| `actions` | every `action` block matches its `ACTION_SCHEMA` row inside `config` and names one unit | FAIL |
| `protocol_object` | every `protocol` object on a `panos_virtual_router` block matches its `PROTOCOL_SHAPE` row (§4.9) | FAIL |
| `filter_blocks` | every filter container block matches its `FILTER_SHAPE` row (§4.10) | FAIL |
| `certificate_blocks` | every certificate block matches its `CERTIFICATE_SHAPE` row (§4.11) | FAIL |
| `references` | every `.name` reference resolves to a block declared in the same run, by kind | FAIL |
| `variables` | a declared variable has a `var.` consumer, and a `var.` consumer names a variable this run declares (F6.6) | FAIL |
| `data_files` | every data file reads as its declared rows and agrees with the rules that produced it (F6.8) | FAIL |
| `control_chars` | no raw control character or DEL in a `.tf` file | FAIL |
| `placeholders` | an expected placeholder, such as the VPN key `***CHANGE_ME***`, is listed | WARN |
| `terraform` | `terraform init` + `terraform validate`, with `--validate` | FAIL, or SKIPPED when the binary is absent |

One block reader serves every block kind the gate reads: `resource`, `data`,
`import`, and `action`. F5.5 added the `data` rule and F6.4 added the `import` rule
with the same reader (§4.8), so no second reader appears; F6.5 reads the scope blocks
with the same reader too, and F6.7 reads the action blocks with the same reader and the
same field reader, given the sub-block it reads (`config`). F7.1 reads the `protocol` object
with the same two readers, and the field reader gained the two shapes of a value an object
holds: the fields inside a container value (`import_blocks.fields_at`) and the elements of a
list value (`import_blocks.elements_of`), so the action rule and the protocol rule read fields
the same way. A block is read up to the
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
sub-block, field for field. The name is read through `entry_coverage.name_field`, the one
rule for the field that carries the entry name: `name` for a type that declares one, and the
field that names the scope for a type that declares none (`device_group` for
`panos_device_group_parent`, F6.5). A rule entry of the four `*_policy_rules` types writes no
block, so the rule reports it as WARN with the reason (§4.8). The finding names the file
and the line the one reader read.

The location is read as the block states it (F6.6): the unescaped value for a quoted field, and the
reference text `var.<name>` for a field `VALUE_VARIABLES` maps to a variable. For a mapped field the rule
compares the printed name against the §5 name of the value the id states, through `naming.py` and the table,
so no second location rule and no second naming rule appear. The id keeps the value, because the provider
parses the id and a variable name is not a device name. Pinned by
`tests/test_site_data.py::test_the_import_rule_compares_a_mapped_field_by_name`, including a block that
prints the literal for a mapped field and an unmapped field whose value does not agree with the id.

`variables` now reads both directions (F6.6): every declared variable has a `var.` consumer, and every
`var.` consumer names a variable this run declares. The second direction is what makes a generated
declaration set checkable, because the set comes from the site record (§3.7) and the run declares exactly
what it consumed. Pinned by `tests/test_sanity_gate.py::test_variable_check_detects_an_unconsumed_variable`
and `::test_variable_check_detects_a_consumer_with_no_declaration`, and by
`tests/test_site_data.py::test_the_variable_rule_reads_both_directions` and `::test_the_corpus_trips_neither_rule`.
`CHECK_ORDER` is unchanged, because F6.6 added no check.

`scope_blocks` reads the name inside a scope block's `location`, because the reference rule
cannot reach it: a name inside `location` names the scope the block sits in, not a reference.
The answering type is `resource_mapping.SCOPE_ANSWER`, and only a `resource` block answers, the
same way an import names a resource. Two shapes state no name to resolve, so the rule reads
neither: an empty sub-block (the `panorama = {}` shape), and a field that names a device rather
than a scope (`panorama_device`, `ngfw_device`). Pinned by `tests/test_scope_objects.py`: one
test per violation type, the `data` block that cannot answer, the two shapes that state nothing
to resolve, the one-reader pin, and `::test_no_false_positive_across_the_corpus`.

`actions` (F6.7) reads an `action` block against `resource_mapping.ACTION_SCHEMA`, the two rows
the pinned schema declares. Measured: the action grammar keeps its fields inside `config`, because
`terraform validate` refuses a field at the block's own level, so the one field reader takes the
sub-block it reads as an argument and no second reader appears. The rule answers the fact a filter
names through `SCOPE_ANSWER`, not against a block this run declares, because a run scoped to an API
scope writes no block for the scope it read. What makes an action a unit action is the address: the
local name is the §5 name plus the digest of the identity the names inside the block build, so the
block answers its own address. F6.10.4: the rule reads the two block kinds through the same mapping, and
`commit_actions.read_block` states the field that named the fact, so a push block reports `name` and not the
filter field the fact would answer for; the emitter prints through `filter_field`, so the two cannot disagree.
Pinned by `tests/test_commit_actions.py`: one test per violation
type, the one-reader pin, and `::test_no_false_positive_across_the_corpus`.

`protocol_object` (F7.1) reads the `protocol` object of a `panos_virtual_router` block against
`resource_mapping.PROTOCOL_SHAPE` (§4.9), through the same block reader and the same field reader. Five
findings, each read from the file text: `protocol` must be a field, because the provider reads
`protocol = { ... }` and refuses `protocol { ... }`; a level, a field, or a value must be the shape the row
states, where `one_of` and `block` are read as `object` because a choice level states one key and a `block`
field states nothing but its presence; a row that states `selects` names the attributes the provider reads as
exactly one, so the level, or the entry inside a `[` container, states one of them (F7.12), and a key the row
does not select is a finding for a `one_of` level; a
field the row marks `sensitive` prints as the variable reference, never as a literal; and an element inside
a `[` container states the name the row reads as the entry name. The rule reads no data file: the block text
and the tables are the whole input. Pinned by `tests/test_protocol_object.py`, one test per finding, and
`::test_the_shape_table_is_the_measured_provider_shape` for the table itself. The gate order is pinned by
`::test_the_rule_runs_after_actions_in_the_gate_order`, and the goldens by the run inside
`::test_a_one_of_level_prints_one_key`.

`filter_blocks` (F7.8) reads a filter container block against `resource_mapping.FILTER_SHAPE` (§4.10), through
the same block reader and the same field reader. Three findings, each read from the file text: a level, a field,
or a value must be the shape the row states; a row that states `selects` names the attributes the provider reads
as exactly one, and the choice is read at the level or the entry the walk enters, which for a filter block
includes the block's own level, so a hand-written filter block that states two alternatives is refused (F7.13);
and an element inside a `[` container states the name the row reads as the entry name. `location` is the
placement fact, so the rule reads the fields at the block's own level and not the sub-block; `location_present`
is the rule that asks for it. The table states no `sensitive` field, so the sensitive rule cannot fire for a
filter block. The choice is read before the field rule, as in `_shape_level_findings`, so a selected key is not
read twice. Pinned by `tests/test_filter_containers.py`, one test per finding, and
`::test_the_gate_reads_the_run_and_reports_nothing` for the gate order.

`certificate_blocks` (F7.14) reads a certificate block against `resource_mapping.CERTIFICATE_SHAPE` (§4.11),
through the same block reader and the same field reader. Five findings, each a FAIL, read from the file text: a
level, a field, or a value must be the shape the row states; the block states the entry name through
`entry_coverage.name_field`, because a certificate entry has no name a reference resolves and the field rule
reads only the fields the block states; a row that states `selects` names the attributes the provider reads as
exactly one, so `local` states one key (F7.12); a field the row marks `sensitive` prints as the variable
reference, never as a literal; and an element inside a `[` container states the name the row reads for the entry
name. `location` is the placement fact, so the rule reads the fields at the block's own level and not the
sub-block. The name is read first, because the block states it before its content, which is the print order the
emitter uses. The choice is read before the field rule, as in `_shape_level_findings`, so a selected key is not
read twice. The level finding cannot fire for a certificate block, because every field the walk enters has a row
under it. `CHECK_ORDER` puts the rule after `filter_blocks`, so the three shape-table rules are grouped. Pinned
by `tests/test_certificate_blocks.py`, one test per finding, the two-reader pin, the lookup pin, and
`::test_the_gate_reads_the_run_and_reports_nothing` for the gate order; the rule is read as a shape owner by
`tests/test_protocol_object.py::test_the_table_is_the_only_shape_owner`, and the report order is pinned by
`tests/test_data_file_gate.py::test_check_order_puts_the_data_rule_after_the_block_rules`.

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

The data rule (`data_files`, F6.8) reads the four data files, each through the module that owns the row
shape, so no second shape rule appears, and it reads no `.tf` file, so no block rule reads a data file.
Six findings, each a FAIL:

- a data file that does not read as its declared rows, or a data file with no rows, because the content
  rule writes a data file only when it has content;
- a field `naming.py` decides, stated as a row instead of as the rule states it: the manifest `unit` and
  `directory`, and the ownership `directory`;
- a join: a `directory` another record names must name a unit the manifest names, or a directory the
  ownership record names, because the tool writes an ownership row for an entry from a declared parent
  source and the manifest names no unit for it (F5.4); an edge row must join on (`type`, `entry`) to an
  ownership row whose `owner` names the `target`; a `kind` `ambiguous` row states no owner, so it cannot
  name one;
- an order: the manifest `rank` and `after` must be what `reference_edges.order` produces from the three
  records read back, so `after` names only units the manifest names (`reference_edges.py` rule 7);
- a printed form: `site.auto.tfvars` must equal `site_data.render_tfvars` of the site rows, and the record
  and its printed form stand or fall together on the content rule;
- a position: a data-file finding is stated at its row ordinal, because a data row spans many lines, and a
  finding about a whole file states no row.

Pinned by `tests/test_sanity_gate.py`: the gate runs on a conversion,
every check detects its own violation, the gate reports no FAIL finding on every
fixture, the report is byte-identical between two runs, the exit code follows the
findings, and `--validate` runs the terraform check or reports it as SKIPPED. The
`data` rules are pinned by `tests/test_data_blocks.py`, and the table itself by
`tests/test_data_source_schema.py` against the live provider schema. The data rule is
pinned by `tests/test_data_file_gate.py`, one test per finding, and the rule that the
order graph reads only manifest units is pinned by
`tests/test_reference_edges.py::test_a_declared_parent_source_adds_no_dependency`.

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

One block per unit the reference site belongs to (F6.10.2), for a name no unit in the run declares:

| Part | Value |
|---|---|
| type | the first opted-in scope in the reference site's lookup order (§4.3) |
| local name | the name rule in §5, one rule for both block kinds |
| `name` | the PAN-OS name the reference names |
| `location` | `location_block` for the unit the referrer belongs to (§4.2) |

A second site in the same unit uses the same block, and a site in another unit writes its own,
because PAN-OS resolves a name in the referrer's own scope before the shared section. A name one
unit declares and another unit uses is never a block: it is the plain name (§4.3 rule 2). The blocks
go in that unit's `read_through.tf` (§14), so a reader can separate what the run read from what
the plan will read. The file is written only when it has blocks, in sorted (type, local name) order,
so it is byte-identical between runs.

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

The file is `imports.tf`, one file per unit inside the directory the manifest row names (§14), one block per
entry the run declares, written only when
the run declares the shape and has a block to write. A `.tf` file is the choice, because the block rules
read `.tf` files and the data rule reads the four data files (§4.5); `imports.tf` is read by the block rule.

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

### 4.9 The protocol object (F7.1)

`panos_virtual_router.protocol` is an object attribute. `resource_mapping.PROTOCOL_SHAPE` is the one table
that states its shape: one row per level this converter prints, with the nesting mode or the leaf shape, the
fields the level declares, the value that selects a `one_of` key, and the `sensitive` flag. The emitter
(`TerraformGenerator._protocol_fields`), the gate rule (§4.6) and the test read that table, so no second
table names a shape. A level is printable only when a parse method reads it and the table has a row for it:
`parse_bgp`, `parse_ospf`, `parse_ospfv3` and `parse_rip` read the levels, `_parse_router` builds the
`protocol` dict from the fields the `protocol` row states, and `_protocol_areas` is the area rule the two OSPF
levels share. F7.4 put the four area sub-levels into the table, so the rule fills the entries of
`virtual_link`, `neighbor` and `nssa_ext_range` through `_protocol_entries`, and the choice inside a chosen
body through `_protocol_body`. F7.5 put the `rip` levels into the table. F7.6 put the `policy` subtree into the
table: `policy` is a `single` level with four children, and the four levels below it that hold entries are the
four the container table names, so `parse_bgp` fills them through `_protocol_branch`, which walks the path's
segments and states no field name of its own. A level inside an entry is filled by `_protocol_body`, so the code
states no path for it and the container table states no row for it. A level the table states no row for is
read by no method, so it prints nothing and the gate refuses it in a hand-written file. F7.7 put the four
`auth_profile` levels into the table, so the four methods read them through `_protocol_branch`, and the levels
inside a profile entry (`md5`, `ah`, `esp`, `esp/authentication`, `esp/encryption`) are filled by
`_protocol_body` through the field the profile row states. One entry states one alternative, because the provider
reads the choice as exactly one, so the row states the choice as `selects` (F7.12) and the fixture states one
alternative per entry. F7.9 put
the four `ospf` levels outside `area` into the table (`timers`, `global_bfd`, `graceful_restart`,
`export_rules`) and the three fields the `ospf` row did not state (`rfc1583`,
`allow_redist_default_route`, `reject_default_route`), which the provider declares as `bool` values and not
as blocks, so `parse_ospf` reads them through the row and states one path for the entry level, which
`_protocol_branch` fills. F7.10 put the two redistribution profile lists into the `protocol` row as entry
levels and the dampening profile into the `bgp` row, and completed the `protocol`, `protocol/bgp` and
`protocol/ospfv3` rows against the measurement. An entry level the row states as a field is read by
`_protocol_entry_level`, which states the path and no field name, and the methods the field names give
(`parse_redist_profile`, `parse_redist_profile_ipv6`) call it; `_protocol_branch` is the same rule for an entry
level inside a level dict. `action` states its two alternatives as `block` fields and no `selects`, because the
provider declares both as optional, so no choice rule reaches it. F7.11 completed the six entry
rows that held the report decision (`peer_group`, `peer`, `redist_rules`, the two
`area/interface` rows, and the `ospfv3` `area` row), so each of those rows states every field
the provider declares for its level, and the seven `single` levels inside those entries are rows
the walk enters. Field order is the print order, so the order the row states is the order the
block prints: a completed row keeps the order it already stated and appends the fields it gained
in the order the schema names them. F7.12 decided how the table states a choice, and the answer is not a shape
word: the schema states no fact for a choice, because it declares every alternative as an optional attribute of a
`single` level. `selects` is the one place the table states a choice, so a row that states `selects` names the
attributes the provider reads as exactly one, and the gate reads that rule at the level the walk enters and at
each entry of a `string_list` row. The two rows that gained it are `protocol/bgp/peer_group/peer/peer_address`,
where the choice is the whole value, and `protocol/ospfv3/auth_profile`, where the choice is two of the four
fields the entry states. `SHAPE_WORDS`, `SHAPE_TO_SCHEMA`, `SHAPE_READS_AS` and `SHAPE_LEVELS` did not change,
because `value_shape` reads both levels as an object value. F7.13 read the same rule for the filter table
(§4.10), which states the choice for the 14 rows the measurement names, so the gate reads a filter choice at the
block's own level as well as at each level below.

1. **`protocol` prints as one field of the block**: `protocol = { ... }`. `terraform validate` accepts the
   value and refuses the block shape, so the gate rule reports a `protocol` the field reader cannot read as
   a field. Pinned by `tests/test_protocol_object.py::test_protocol_prints_as_an_object_field_not_a_block`.
2. **One table path is one nesting level of the printed value.** A `single` level prints as an object, a
   `list` level prints one object per element, a `one_of` level prints the one key the row's mapping states,
   a `block` field prints `{}`, because the export states it by presence, and a `member_list` field prints as
   the values the element holds, because a member is a value and not an entry (rule 9). Field order is the table
   order and `hcl_value` is the only printer, so two runs on the same bytes write the same bytes.
3. **One rule names a field.** The entry name inside a list element prints as the `name` field, the rule
   `entry_coverage.name_field` states (§3.2). The table states the provider spelling, the export spells it
   with `-`, and `PanoramaParser._protocol_xml_name` is the one rule that turns one into the other. The rule has
   one exception: `resource_mapping.XML_NAME_EXCEPTIONS`, because the provider splits an initialism the export
   does not (`strict_l_s_a_checking` for `strict-lsa-checking`). The key a
   parse method writes is the field the table path names (`_protocol_field_name`), so no parse method spells
   a field name of its own. Pinned by `tests/test_protocol_object.py::test_the_table_is_the_only_shape_owner`.
4. **The mapping is the one lookup, and the entry it cannot state is the entry the report names.**
   `_protocol_choice` returns the printed value and the reason it cannot be printed; the parse marks the
   entry for the report with that reason and does not put it in the printed list, so the report names the
   whole entry and the file holds no half of it (§3.2). The same rule covers a peer no peer group names, an
   interface outside an area, a link type the mapping does not state, and a `range` entry that states neither
   choice, for either OSPF level, because `_protocol_areas` is one reader. Pinned by
   `tests/test_protocol_object.py::test_an_unmapped_one_of_value_prints_nothing_and_is_reported` and
   `tests/test_protocol_object.py::test_an_ospfv3_interface_at_the_level_is_reported`.
5. **A choice level states one key, and one element holds its body.** `peer_group.type` maps the four export
   values to the four provider sub-shapes; `area.type` and `area.interface.link_type` are the identity for the
   `ospf` and the `ospfv3` level, because the export states the provider key. `import_nexthop` and
   `remove_private_as` exist only under `ebgp`, so each sub-shape row states its own fields. The fields of a
   chosen body live inside the element the export puts them in: the chosen flag element for an area type, and
   the entry's own level for a BGP peer group, which is the holder `_protocol_choice` reads. Pinned by
   `tests/test_protocol_object.py::test_the_one_of_mapping_is_the_decision_the_report_prints` and
   `tests/test_protocol_object.py::test_a_choice_body_prints_the_fields_it_declares`.
6. **Membership is the parent entry.** A peer prints inside the peer-group element that holds it, and an
   interface prints inside the area element that holds it, for either OSPF level, because the table states no
   peer outside a peer group and no interface outside an area. A peer group name is not a field the block
   prints, because the entry it names is the parent. Pinned by
   `tests/test_protocol_object.py::test_an_ospfv3_area_prints_the_shape_the_table_states`.
7. **A choice states exactly one alternative**, so the row states the alternatives as `block` fields or as the
   `selects` keys, which are the whole value for a `one_of` level and part of the value for a row that states
   other fields (F7.12). A `range` entry and an `nssa_ext_range` entry state
   `advertise` or `suppress`, and the alternatives are the row's `block` fields, so the rule reads the table
   and the two levels are one shape. A `default_route` level states `advertise` or `no`, and the key the print
   states for `no` is `disable`. The choice level itself is not required, so a level that states no choice
   element prints nothing for it, and the element that states none of the alternatives has no `.tf` shape, so it
   is a report row. The report names the entry that holds the choice element, which can be the entry the choice
   is inside: the area entry for an OSPF level, and the interface entry for a `rip` interface, because F7.5
   showed an entry can hold its own choice and `_protocol_body` reads the element under it the same way. Pinned
   by `tests/test_parse_network.py::test_parse_ospf`, `tests/test_parse_network.py::test_parse_ospfv3`,
   `tests/test_parse_network.py::test_parse_rip` and
   `tests/test_protocol_object.py::test_the_gate_reads_a_choice_inside_an_entry_level`.
   F7.12: `selects` is the one place the table states a choice, so the gate reads it as exactly one at the level
   the walk enters and at each entry of a `string_list` row, and a level or an entry that states both
   alternatives, or none, is a FAIL finding. Measured 2026-11-03 with `terraform validate` (provider 2.0.14,
   Terraform 1.16.2), which refuses 2 attributes when one (and only one) is required for `peer_address` and for
   the `ospfv3` profile entry, and refuses none for both. The print path is unchanged: a run that states one
   alternative prints one key. Pinned by
   `tests/test_protocol_object.py::test_the_choice_rows_state_the_choice_the_provider_reads` and
   `tests/test_protocol_object.py::test_the_choice_rule_reads_a_level_and_an_entry`. The same rule and the same
   wording serve the filter table (F7.13), where the gate also reads the choice at the block's own level, which
   is the entry row the walk enters for a filter block (§4.10 rule 1).
8. **A sensitive field prints as the variable reference**, through `VALUE_VARIABLES`
   (`docs/CODEBASE_ASSEMBLY.md` §9 rule 2), and no generated file states the value. F7.7: the run can
   read a value for such a field inside an entry, and the name it prints is the §5 name of the entry
   that holds the field, because a value cannot name itself. The entry names itself when the field is
   its own, and a level inside an entry names the entry that holds it. The run writes no `.tfvars` line
   and no site row for the name, and `variables.tf` declares it with `sensitive = true`.
   `SHAPE_WORDS` is the word list the table uses, and `sanity_checks.value_shape` is its reader inverse.
   A specialization is read back as its family word through `sanity_checks.SHAPE_READS_AS`, and
   `sanity_checks.SHAPE_LEVELS` states which words name a level the walk enters, so a member list is
   never walked. Pinned by
   `tests/test_protocol_object.py::test_value_shape_is_the_reader_inverse_for_every_shape_word`,
   `tests/test_protocol_object.py::test_an_auth_profile_prints_the_reference_the_entry_names`,
   `tests/test_variables.py::test_a_variable_block_is_sensitive_when_the_table_marks_its_name_reference_only`
   and `tests/test_robustness.py::test_a_parsed_secret_never_reaches_a_generated_file`.

9. **A `member_list` field is a `[` value whose members are values.** The provider declares 45 fields as
   `['list', 'string']`: the five `from_peer`, `nexthop`, `append`, `overwrite`, `used_by` names F7.6 recorded,
   and the nine names F7.10 added inside a redist profile entry (`area`, `community`, `destination`,
   `extended_community`, `interface`, `path_type`, `tag`, `type`), which `string_list` already
   covers as a `[` value, so the table needs the word `member_list` to say that the level holds no entry. The
   field reader reads the `member` children, the print writes them as the list, and rule 4 never reaches a
   member. Pinned by
   `tests/test_protocol_object.py::test_member_list_is_the_word_for_a_field_whose_members_are_values`
   and `tests/test_protocol_object.py::test_the_gate_reads_a_member_list_as_values_and_not_as_entries`.

10. **A choice level can state its alternatives as values.** `terraform validate` (Terraform 1.16.2, provider
    2.0.14) refuses a policy level that states more than one of the attributes it declares, so the nine levels
    `aggregate_route_attributes/{as_path,community,extended_community}` and
    `{export,import}/rules/action/allow/update/{as_path,community,extended_community}` are `one_of` rows with the
    identity mapping, and the three levels that hold them state those fields as `one_of`. When the chosen
    alternative is a field the row states, the field reader reads it and the print writes the value as it was
    read, so the walk never enters a value. A mapping key is the spelling the export states, so
    `remove-regex` and `remove-and-prepend` are keys. The provider can also enforce exactly one
    of two attributes of one level, which the schema has no word for, so a row that states both
    fields cannot be refused by the gate: `peer_address` (`ip` or `fqdn`) is measured 2026-11-03
    and recorded in [`../backlog.md`](../backlog.md). Pinned by
    `tests/test_protocol_object.py::test_the_one_of_mapping_is_the_decision_the_report_prints`
    and `tests/test_protocol_object.py::test_a_one_of_level_prints_one_key`.

The container rows for the levels this converter prints are `emitted` with the note
`panos_virtual_router` (`container_coverage.CONTAINER_TABLE`), so the property scan measures them against the
router row. A level that holds no entry has no container row, so the scan measures nothing for it and the matrix
row is grounded by the table instead. The same holds for an entry the parse reaches through a field the parent
row names, such as a `neighbor` entry inside an interface entry: the section path holds an entry segment the row
path cannot match, so `PROTOCOL_SHAPE` grounds that level. F7.7: the four `auth_profile` levels are
container rows, so the scan measures a profile entry against the router row, and an `md5` entry inside a
profile entry is not in the scan scope, so `key` stays grounded by the table. F7.9: `protocol/ospf/export-rules`
is a container row, so the scan measures an `ospf` export rule entry against the router row, and the three
single-object levels stay grounded by the table, because they hold no entry. F7.10: the three entry levels
(`protocol/redist-profile`, `protocol/redist-profile-ipv6`, `protocol/bgp/dampening-profile`) are container rows,
so a redist profile entry and a dampening entry are measured against the router row, and the single levels
inside an entry (`action`, `filter`, `filter/bgp`, `filter/ospf`) hold no entry, so they stay grounded by the
table. Pinned by
`tests/test_container_coverage.py`, `tests/test_coverage_matrix.py` and `tests/test_property_coverage.py`.
F7.11: the seven `single` levels inside the peer entry have no container row, because none of
them holds an entry, so the scan measures the fields of the entry that holds the level. An
interface entry is inside an area entry, so its section path holds an `entry` segment a row path
cannot match, and the two interface rows stay grounded by the table.

### 4.10 The filter containers (F7.8)

The six routing-profile filter containers sit outside the `protocol` object, so each one is its own resource
block. `resource_mapping.FILTER_SHAPE` is the one table that states their shape, with the same row shape an
existing config container uses: `shape`, `fields`, `selects`, `sensitive`. `resource_mapping.FILTER_TABLE` is
the reader both the parse method and the gate rule use, so no second table names a filter shape, and
`SHAPE_TO_SCHEMA` is the one mapping between a table word and the schema word for both tables.

`resource_mapping.FILTER_TYPES` is the lookup from a container path to the provider type, and
`container_coverage.CONTAINER_TABLE` holds one `emitted` row per container whose note names the same type, so
the decision has one owner. `FILTER_PATHS` is the sorted set of the six entry rows, which `COVERAGE_MATRIX`
reads as the property scope: a filter entry is a section entry, so the scan measures it against its own row,
and the properties that row declares are the entry row's fields without the entry name.

Three things the filter table states:

1. **`selects` is the one place either table states a choice** (F7.12), so the filter rows that hold one state
   it there. Measured 2026-11-03 with `terraform validate` (provider 2.0.14, Terraform 1.16.2), 14 filter rows
   are levels the provider reads as exactly one attribute: each refuses more than one of its alternatives and
   also refuses none. The schema states no fact for a choice, because it declares every alternative as an
   optional attribute of a `single` level, so no shape word carries it and `SHAPE_WORDS`, `SHAPE_TO_SCHEMA`,
   `SHAPE_READS_AS` and `SHAPE_LEVELS` did not change: a filter choice row keeps the word the measurement gives
   it (`object`), and `one_of` keeps its meaning as the word for a row whose whole value is the choice. The
   choice is the identity, because the export spells the provider key at a filter choice level, so
   `FILTER_XML_NAME_EXCEPTIONS` gained no row. `redist-entry` is the filter case where the choice is part of the
   value, because the row also states `name` and `description`; the other 13 state only their alternatives. The
   choice is data in the row, so one rule (`_shape_choice_findings`) reads both tables and one wording covers
   both, and the gate reads it at the block's own level as well as at each level below (§4.6). The fixture
   answers each choice level it covers with one element, so the run prints one alternative and reports nothing.
2. **`sensitive` is empty for every row**, because no filter field is marked `sensitive` in the pinned
   schema, so `VALUE_VARIABLES` gains no row for a filter field.
3. **The row scope stops at a `match` or `set` row.** The redistribution entry mirrors the levels the provider
   declares, but its `match` and `set` rows state leaf fields only, so no row stands under them and the walk
   stops there. The six levels inside them (`match.ipv4.address`, `match.next_hop`, `match.route_source`,
   `set.metric`, `set.ipv4`, `set.ipv6`) are recorded in `backlog.md`.

The input spelling is the `-` rule with one path-keyed exception map,
`resource_mapping.FILTER_XML_NAME_EXCEPTIONS`: the map is keyed by the container path, because the same idea
spells differently in two containers — `extended_community_regexes` is `ec-regex` inside a community-list entry,
and `extended_communities` is `extended-community` inside a route-map match. An entry-list field is the singular
container element that holds its entries, so those fields are in the map too. The map holds 15 pairs, and
`ipv4_entries` and `ipv6_entries` spell the same way in two containers, so 13 distinct spellings, and none of
them is a spelling the `-` rule can produce. Each pair is grounded by an entry in
`tests/fixtures/filter_containers.xml`, because one entry states one choice alternative, so a container that
holds a choice holds one entry per alternative the fixture states. The pin reads the pair from a real run: the
entry states the element the exception names, the block the run wrote for that entry prints the name the row
declares, and `terraform validate` accepts the block. Pinned by `tests/test_filter_containers.py`.

### 4.11 The certificate containers (F7.14)

The two certificate containers are each one resource block per entry. `resource_mapping.CERTIFICATE_SHAPE` is the
one table that states their shape, with the same row shape the protocol and filter tables use: `shape`, `fields`,
`selects`, `sensitive`. `resource_mapping.CERTIFICATE_TABLE` is the object the two parse methods
(`PanoramaParser.parse_certificates`, `PanoramaParser.parse_certificate_profiles`), the two emitters
(`TerraformGenerator.generate_certificates`, `TerraformGenerator.generate_certificate_profiles`) and the gate rule
(`sanity_checks.check_certificate_blocks`) read it through, so no second table names a certificate shape.
`resource_mapping.CERTIFICATE_TYPES` is the lookup from an entry row to the provider type, and
`resource_mapping.certificate_path` reads it the other way for the gate rule, so the rule states no type.

Three things the table states:

1. **`selects` states the choice by presence** for `certificate/local` (F7.12), because the provider reads
   `local` as exactly one of `pem` or `pkcs12` and `terraform validate` refuses a `local` stating both. The row
   states no field, so the alternative is read from the key the block states. `SHAPE_READS_AS` keeps `one_of`
   reading as `object`, so the gate needs no new shape word.
2. **`sensitive` is stated only inside `local`**: the `private_key` and `passphrase` rows of
   `resource_mapping.VALUE_VARIABLES` are the same fact the table marks, which
   `tests/test_protocol_object.py::test_the_sensitive_rows_are_the_reference_only_names` pins. The block prints
   the reference, and no generated file states the value (`tests/test_robustness.py`).
3. **`certificate_profile/certificate` is an entry-list row**, so its shape word is `string_list`, the word the
   reader reads for a `[` value, as the filter table's entry rows state it. The fields the row states are the
   fields one entry inside the list states, so the walk reads each element as an entry.

The entry name is read through `entry_coverage.name_field`. `panos_certificate_import` is the first emitted type
with no data source, so the name fact comes from `RESOURCE_NAME_FIELDS`, which
`tests/test_data_source_schema.py::test_the_name_fact_for_a_resource_only_type` pins against the live schema. The
emitter prints the entry name before the row's other fields, in the row's order, and the gate rule reads the name
in the same order.

The table itself is pinned by `tests/test_data_source_schema.py::test_the_certificate_table_is_the_live_shape`,
the emitter by the grounding branch in `tests/test_coverage_matrix.py`, the print by the goldens from one real run
on `tests/fixtures/kitchen_sink.xml`, and the gate rule by `tests/test_certificate_blocks.py`. The facts that stay
open are in `backlog.md`.

## 5. Naming rules

The local name of a block is **the sanitized PAN-OS name plus an 8-hex digest of
the source identity**. One rule serves both block kinds (F5.5), and the identity is what the site
named: the export path for a `resource`, and the unit for a read-through `data` block, because a
`data` block stands for an entry the run did not read (§4.7).

```
local = sanitize(name) + '_' + sha256('scope|identity|name')[:8]
identity = context + '|' + vsys            for a resource
identity = identity_digest(facts)           for a data block
```

A run that declares no read-through scope writes the same bytes as before, because no `data` block
is written there.

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
  is the digest input: the five scope facts, joined by `|`, in `SCOPE_FACT_KEYS` order
  (`unit_manifest.py`, §3.4). No second naming rule exists, and the test pins that the module
  defines none.
- **The rule lives in `naming.py`** (F6.6), because the post-run gate must read it without the generator:
  the `import_blocks` rule compares the variable name a block prints against the value an id states, so the
  gate and the emitter read one rule. `TerraformGenerator.sanitize_name` is a delegate, and the data modules
  keep taking the rule as an argument. A site value read through the rule is the variable name
  (`naming.variable_name`), and the text a block prints for it is `var.` plus that name
  (`naming.variable_text`), so the emitter, the gate, and the tests cannot give one value two shapes. The rule
  is idempotent, so an id that states the mapping result instead of the value cannot be detected: the writer
  keeps the value in the id, and the gate reads the id as the value.
- Taken names are tracked per type (one domain per `scope`), for both block kinds.
  A true duplicate gets a numeric suffix (`_2`), so the output is always valid HCL.
  The suffix is a validity guard, not the identity mechanism: two different
  identities never need it.
- `device` is not in the digest, and no device index exists. The naming site takes the object the
  declaration belongs to, so it records the declaring unit (`unit_manifest.facts_of`) in the
  declaration index: one local name per unit that declared the name, and the first declaration of
  one identity wins. The reference rule (§4.3) reads the referrer's unit in that same record, so no
  second unit rule and no second naming key exists (F6.10.2).
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
`tests/test_data_blocks.py::test_a_data_block_enter_no_declaration_index`.

## 6. Determinism

Two runs on the same input produce identical bytes.

**The byte rule lives in the write path.** One function writes a file (`write_path.py` `write_file`), so the
rule is enforced in one place and not in an operator note: `open(..., 'w')` writes `os.linesep`, so a run on a
Windows desktop writes CRLF and the goldens stop matching byte for byte. Text takes `newline=LF`; `bytes` are
written without translation, because the write path receives the source cache bytes the input door parsed, and
the rule for those bytes is "no change". No module of the tool writes a file outside the write path, and no
module builds a path for a file it does not own: the two builders name the two sets (§14 of
`CODEBASE_ASSEMBLY.md`). Pinned by `tests/test_write_path.py`
`test_one_function_writes_bytes_and_no_other_module_writes_a_file`,
`test_the_write_path_states_two_builders_one_per_set`, and `test_the_bytes_a_run_writes_hold_no_cr`.

- Association tables sort names. Report sections sort by level, entries by name.
- Names come from the identity digest, not from emission order.
- Order that the input states is preserved on purpose: XML order inside a policy
  chain, and first-seen order of chains.
- The goldens pin every emitted `.tf` file byte for byte, read as paths from the case directory, so each
  path names one unit directory (`tests/test_golden_files.py`). Reports are not in the golden set, so report
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
- The shadow scan sorts findings by line, then object type, then name, then the parent entry the finding
  names in the parent report order, so two runs on the same two sources write the same bytes. The parent
  index keys by identity, so one key holds one parent entry and no parent row is dropped
  (`tests/test_shadow_coverage.py::test_two_runs_on_the_same_sources_write_the_same_bytes`).
- The state scan keeps the first state entry for an ownership key, in document order, and sorts
  findings by line, then object type, then name, so two runs on the same arguments and the same
  bytes write the same bytes
  (`tests/test_state_coverage.py::test_two_runs_on_the_same_bytes_write_the_same_bytes`). A state
  read is a file read, so no cache-derived value enters its record.
- The site record (§3.7) keeps the rows in identity order and sorts the names inside a row, the `.tfvars`
  prints in name order inside the file of the unit the row names, and no field states a timestamp or a path, so
  two runs on the same
  bytes write the same bytes from two different output directories
  (`tests/test_site_data.py::test_the_fields_print_in_the_declared_order` and
  `::test_two_runs_on_the_same_bytes_write_the_same_bytes`). A name comes from the value through `naming.py`,
  so it is the mapping result and not a second rule (`::test_site_data_defines_no_second_naming_rule`).

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
