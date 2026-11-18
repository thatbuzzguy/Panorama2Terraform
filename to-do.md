# To Do

The tracking markdown for the completed pieces is removed here; the git history and the owner documents hold
it. The open pieces are the actionable findings the 2026-11-11 and 2026-11-12 audits recorded in `backlog.md`.
Each piece below names the rule it holds, the module that states it, and the test that pins it. One piece is
finished before the next is started. Pieces 3 to 9 are kept below with the pins they name; the piece
numbers follow the audit order, apart from Piece 9, which is a `backlog.md` Nice-to-Haves item.

## Current series

### Piece 3 — pins that measure nothing (complete, committed 2026-11-13)

Owner: `tests/conftest.py` and the pins the 2026-11-11 audit named. Each of the five items now measures content,
and no pin failed once it measured content. The criteria and the measurement are in `acceptance.md`.

- The golden byte pins read the `.tf` set through `tf_bytes`, keyed by the path from the case directory, and
  state that both sides hold content: `tests/test_data_blocks.py::
  test_a_run_that_declares_no_read_through_scope_writes_the_golden_bytes`, `tests/test_ownership.py::
  test_the_goldens_are_byte_identical`, `tests/test_reference_edges.py::test_the_golden_tf_bytes_are_unchanged`,
  `tests/test_unit_manifest.py::test_the_generated_tf_bytes_are_unchanged`.
- `tests/test_commit_actions.py::test_no_false_positive_across_the_corpus`: the guard is gone, and the pin states
  the two cases through `commit_actions.build_rows`.
- `tests/test_api_requests.py::
  test_one_committed_response_per_request_shape_names_the_request_identity_that_produced_it` and
  `test_the_committed_responses_are_not_corpus_material`: both read `source_fetch.SHAPE_PARAMS`.
- The hostile-fixture name rule is gone: the pins read `corpus_fixtures()`, which is `input_refusal`
  (`xml_input.check_bytes`, then the parse), in 12 test modules.
- The five order pins hold the document order `docs/ARCHITECTURE.md` §4.4 states and assert the uniqueness rule:
  `tests/test_parse_rules.py` (four pins) and `tests/test_parse_profiles.py::test_parse_pbf_monitor_profiles`.

### Piece 4 — the parse set reads what its rows state (complete, committed 2026-11-13)

Owner: `src/panorama_to_terraform.py`, `src/sanity_checks.py`, `src/entry_coverage.py`, and the coverage matrix
rows they read. The criteria and the measurement are in `acceptance.md`.

- `tag` is read for every entry kind through one rule, `TerraformParser._interface_tag`: the entry's own `tag`
  element, the `tag` inside the mode block, or the unit part of the name when the name carries the unit.
  `tests/test_interfaces.py::test_the_interface_object_holds_the_fields_its_row_declares`.
- Both address shapes are one field read by one rule, `TerraformParser._list_values`, the list form of
  `_get_single_value`, and only direct children count.
  `tests/test_interfaces.py::test_a_list_field_is_read_in_both_export_shapes`.
- `zone` and `virtual_router` are not interface fields and nothing reads them, so the interface object carries no
  key for either; `parent` is a field only for the kinds whose row declares it.
- The scan's blind side is stated in `src/entry_coverage.py` §F4.4, and
  `tests/test_property_coverage.py::test_the_scan_cannot_see_a_field_the_parse_stored_empty` measures it.
- Every entry name guard in the parse set records the entry it skips, and
  `tests/test_entry_coverage.py::test_every_name_guard_records_the_entry_it_reads` measures the set through
  `ast`; `tests/test_entry_coverage.py::test_a_nameless_entry_reaches_the_record_and_the_report` measures a
  nameless entry at a section level and inside a config-object entry.
- `parse_schedules` skips a nameless recurring child through the record, so the report writer joins only the names
  it kept: `tests/test_property_coverage.py::test_a_nameless_recurring_child_reaches_the_record_and_not_the_join`.
- `_parse_router` keeps reading only the shape the virtual-router row states and records each entry the export
  states under `protocol/static-routes` as skipped:
  `tests/test_entry_coverage.py::test_an_entry_at_a_level_the_table_states_no_row_is_recorded`, with the schema
  half in `tests/test_protocol_object.py::test_the_shape_table_states_no_row_for_the_level_the_router_records`.
- `_protocol_field` reads a `number` as the shape states it, so the reader's inverse
  `src/sanity_checks.py::value_shape` reads a signed integer back as `number`:
  `tests/test_protocol_object.py::test_value_shape_is_the_reader_inverse_for_every_shape_word`. The pin prints
  through the same branch, so a signed integer is printed as the shape states. The four `member_list` corrections
  the audit named are not applied, because the pinned provider schema states all four fields as `string`.

One part of the last finding stays open in `backlog.md`: a `number` text the value rule cannot read.


### Piece 5 — naming and printing state one rule (complete, committed 2026-11-15)

Owner: `src/naming.py`, `src/panorama_to_terraform.py`, `src/sanity_checks.py`, `src/xml_input.py`,
`src/site_data.py`, `src/unit_manifest.py`, and the pins `backlog.md` (measured 2026-11-12) named. Each item
states the rule, the decision, and the pin that measures content. The criteria, the pin changes, and the gate
measurement are in `acceptance.md`.

- Item 1 — static-route block name: `generate_virtual_routers` passes the route's own name to
  `declare_block_name`, so the digest is taken once and `_declaration_index` holds the name a reference reads.
  `tests/test_robustness.py::test_a_static_route_block_digests_the_route_name_once`, and the kitchen-sink
  `virtual_routers.tf` golden.
- Item 2 — the fallback word: `naming.UNNAMED` is the one statement, and `unit_manifest` and
  `declare_block_name` read it. `tests/test_unit_manifest.py::test_the_fallback_word_is_stated_once_in_src`
  (the scan pin, the pin that fails before the change),
  `tests/test_unit_manifest.py::test_the_word_prints_the_same_string_at_both_print_sites` (the content pin), and
  `tests/test_robustness.py::test_declare_empty_name_gets_a_stable_name`.
- Item 3 — one name names one source: the rule is `site_data.record_pair`, read by `printed_value` and
  `render_tfvars`; a second source for one name is a refusal. `tests/test_variables.py::
  test_the_record_refuses_two_entries_that_name_one_variable`, built on two names `sanitize_name` collapses.
- Item 4 — the order rule: `hcl_value` states that the row order is the print order at every level, and the two
  emitters read it, so both `sorted()` calls are gone and `parse_filter_containers` reads `FILTER_PATHS`.
  `tests/test_filter_containers.py::test_the_print_sites_state_no_second_order_rule` (the scan pin),
  `test_the_parse_reads_the_paths_the_table_states`, `test_the_emitter_prints_the_fields_the_entry_row_declares`
  with the filter goldens, and `tests/test_certificate_blocks.py::
  test_the_block_prints_the_fields_in_the_order_the_row_states`.
- Item 5 — the control-character rule is the read layer's (`xml_input.CONTROL_CHARS`): the door refuses it in
  both input shapes, `escape_string` keeps only the escape shapes, and the gate reads the definition.
  `tests/test_state_input.py::test_the_state_door_refuses_a_control_character_in_a_value`,
  `tests/test_robustness.py::test_escape_string_prints_the_shapes_it_escapes`, and the scan pin
  `tests/test_sanity_gate.py::test_the_control_character_rule_is_stated_once_in_src`.
- Item 6 — one whitespace rule: `xml_input.read_text` owns it and the six value helpers read it; an absent
  element answers `None`. `tests/test_parse_helpers.py::
  test_the_value_helpers_read_the_text_the_read_layer_states` and
  `test_a_value_with_surrounding_whitespace_prints_without_it`; `tests/test_entry_coverage.py::_name_guards`
  counts a name read through `read_text` as the same guard.
- Item 7 — `UnitText.add_once` keeps its own once record, so header prose cannot stop a section.
  `tests/test_write_path.py::test_add_once_keeps_its_own_once_record`.
- Item 8 — the placeholder: the block prints the reference only when the run read a value, so a
  `reference_only` field the export cannot carry prints the marker stated once as
  `resource_mapping.PLACEHOLDER_TEXT`, and the gate rule stays as the reader of the printed text.
  `tests/test_sanity_gate.py::test_a_reference_only_field_with_no_value_prints_the_marker`,
  `test_the_placeholder_is_stated_once_in_src`, `test_placeholder_check_warns_and_does_not_fail`, and
  `tests/test_reports.py::test_per_gateway_placeholder_line_survives`. `pre_shared_key` is dropped from the
  `COVERAGE_MATRIX` row for `panos_ike_gateway`, because the parse holds no value for it; the rule's owner is
  `docs/CODEBASE_ASSEMBLY.md` §11, and `tests/test_property_coverage.py` measures the row against what a run
  reads.

### Piece 6 — the splitter reads the owners' rules, and the error rule names its kinds (complete, committed 2026-11-15)

Owner: `src/split_device_groups.py`, `src/naming.py`, `src/write_path.py`, `src/xml_input.py`,
`src/panorama_to_terraform.py`, `docs/DEVICE_GROUP_SPLITTING.md`, `docs/ARCHITECTURE.md` §2.3. Each item states
the rule, the decision, and the pin that measures content. The criteria, the pin changes, and the gate
measurement are in `acceptance.md`.

- Item 1 — the single writer: the splitter serializes the tree to text and hands it to `write_path.write_file`, so
  the byte rule and the `LF` rule cover the split files, and the text ends with the final line the single writer
  states. The splitter owns its own output path, so it names no builder from `write_path.py`. The writer scan now
  reads the element-writer shape. `tests/test_write_path.py::
  test_one_function_writes_bytes_and_no_other_module_writes_a_file` (the scan pin, the pin that fails before the
  change), `test_the_splitter_writes_through_the_single_writer`, and the content pin
  `tests/test_split_device_groups.py::test_a_split_file_is_the_text_the_single_writer_writes`.
- Item 2 — the file name: `naming.variable_name` is the one name rule, so `DG-Internet` writes `dg_internet.xml`
  and a name that sanitizes to nothing writes `unnamed.xml`. The collision decision is refuse, not number, because
  the numbering a run would pick depends on the order the entries appear in (§6); the refusal is the input-layer
  kind, so the run stops before it writes and the output directory is never made.
  `tests/test_split_device_groups.py::test_the_split_file_name_is_the_naming_rule_applied_to_the_name` and
  `test_two_names_that_read_one_file_name_are_refused_and_no_file_is_written`.
- Item 3 — the tables are keyed by the source line: `parse_device_groups` answers one row per entry, the row holds
  the line, the path, the name, the entry and its devices, the join answers each entry's own devices, and the rows
  are in source line order, so the name sort is gone. `tests/test_split_device_groups.py::
  test_the_splitter_tables_are_keyed_by_the_source_line`,
  `test_two_entries_with_one_name_are_two_rows_that_answer_their_own_devices`, and
  `test_the_join_answers_the_rows_in_source_line_order`; the splitter pins in `tests/test_edge_cases.py` and
  `tests/test_multi_device_template.py` read the row and the parsed source through the door.
- Item 4 — the shared merge: the dedupe is the pair (path, name) at the level the path names, the first occurrence
  of a path is the container, an entry inside an entry travels with its parent copy, and an empty section writes no
  container. `tests/test_split_device_groups.py::test_the_merge_keeps_an_entry_at_the_path_it_sits_at`,
  `test_the_merge_dedupes_the_pair_path_and_name_at_its_own_level`,
  `test_the_run_writes_one_container_per_path`, and `test_an_empty_shared_section_writes_no_container`.
- Item 5 — the dead branch: `extract_device_group_config` takes the row, so the lookup cannot exist and the warning
  print and its troubleshooting row are gone.
  `tests/test_split_device_groups.py::test_the_extraction_states_no_lookup_and_no_warning` (the scan pin, for the
  reason `acceptance.md` states) and `test_the_extraction_answers_through_the_row_it_was_given`.
- Item 6 — the refusal kinds: `is_refusal` answers True only for `xml_input.UnsafeInputError` and
  `ET.ParseError`, so a plain `ValueError` raised inside the tool keeps the shape `failed()` states. `refused()`
  lost the branch that could no longer fire and its `read_name` argument, and both entry points pass the error
  alone. `tests/test_safe_input.py::test_the_refusal_kinds_name_only_the_input_layer_exceptions` and
  `tests/test_variables.py::test_the_record_refuses_two_entries_that_name_one_variable`.

Gate: `ruff check .` clean, 1,687 pins in 51 modules, all pass, no skips. The pins that fail before the change are
listed with their measurement in `acceptance.md`.

### Piece 7 — the indexes and the documents agree with measurement (complete, committed 2026-11-16)

Owner: the tracking markdown, `docs/ARCHITECTURE.md` §1 and §1.1, `README.md`, `tools/README.md`, and the pins
`backlog.md` named. The criteria, the two decisions, the pins that changed, and the gate measurement are in
`acceptance.md`. Each item states the rule, the decision, and what measures it.

- Item 1 — the module table names every `src/` module. `commit_actions.py` is now a row in the §1 table, which
  completes the set for all 22 modules. `tests/test_layout.py` measures it, so a module that is not named in the
  table fails.
- Item 2 — the test set is named by the root index, so `tests/` keeps no index of its own. `README.md` names
  every test module, `tests/conftest.py`, and the three files in `tests/responses/`; `docs/ARCHITECTURE.md` §1.1
  states the rule and names the four index scopes. `tests/test_layout.py` measures it.
- Item 3 — a document that names a test names a test that exists. Four claims took the real name
  (`docs/ARCHITECTURE.md` §4.9, `docs/API_CONVERSION_PATH.md` §1, `to-do.md` Piece 4, and the profile-name claim
  in `backlog.md` §Parser extraction gaps, which states no pin name because no pin holds the rule). The tool
  checks every claim, in every markdown file, at each run.
- Item 4 — no document states a count it did not measure. `docs/COVERAGE_MATRIX.md` shows the 42 rows and states
  the count as derived from the table; `docs/LICENSING.md` states the split measured with `git blame` at commit
  `ac7609e` and the inherited total as the sum of its rows; the notice table states the split as a measured share
  instead of "the upstream, unchanged", and names all four `src/` modules that carry the notice. `README.md`
  states no counts and links to the owner documents.
- Item 5 — one pin holds the index rule, and the wording checks sit outside the test set.
  `tests/test_layout.py::test_the_indexes_name_every_document_under_them` is the only index pin. Five wording
  asserts across three pins moved to `tools/check_documents.py`; two pins that read `backlog.md` keep their facts
  as data. The tool is a document-review script, not part of the gate, and the test set does not read it.
- Item 6 — each row shape has one name: `SITE_ROW_FIELDS` (`src/site_data.py`), `ACTION_ROW_FIELDS`
  (`src/commit_actions.py`), `IMPORT_ROW_FIELDS` (`src/import_blocks.py`), `MATRIX_ROW_FIELDS`
  (`tests/test_coverage_matrix.py`). Each is named in the rule column of its §1 table row, and no `ROW_FIELDS`
  is left in the flat namespace.

### Piece 8 — the membership entry read (complete, committed 2026-11-18)

Owner: `docs/API_CONVERSION_PATH.md` §2.4 and §6 for the rule, `src/panorama_to_terraform.py`
(`PanoramaParser._section_entries`) for the parse rule, and `tests/test_api_path.py` for the pins. The criteria
and the measurement are in `acceptance.md`.

- The decision: the double read stands and both answers stand. The run order reads the membership response and
  then the entries the index names, so an entry a membership list names is read twice: once inside the place
  response, once as the response its own request made. No rule makes one of the two answers the answer for the
  entry, so the run keeps both, and each response records its own rows.
- A parse method reads the entries at the level its container-table row names, so an entry response answers the
  entry its own request named; a whole-config source and a place read reach that level through the container
  element and are unchanged. A membership row names a level inside the entry the path names, so an entry response
  answers no membership table and the index keeps reading its set from the place responses.
- Path 2 writes the content of each response it read, so one block per response that holds the entry, and the name
  rule gives the second block the suffix it states for a repeated name. Path 1 read one response, so it writes one
  block per entry, and the byte agreement holds only for content that states no membership list, which is the
  content the F8.10 pin keeps.
- The gate reads the double read as two sets that agree, so it reports nothing for it: both counts read 2 for the
  same unit and the same row, and both responses are in the read set.
- Pins: `test_the_entry_read_answers_the_entry_its_own_request_names`,
  `test_an_entry_two_responses_hold_gives_one_block_per_response`, and
  `test_the_double_read_agrees_with_the_gate`. The content is `MEMBERSHIP` and `MEMBERSHIP_EXPORT`, read through an
  injected producer, so no pin calls a network and no committed response is added: the committed set stays at 3
  files.

Gate: `ruff check .` clean, `ruff format --check .` clean, 1,688 pins in 52 modules, all pass, no skips, 305.56 s.
`python3 tools/check_documents.py` reports no finding. The F8.10 finding is closed.

Next in the series (one piece finished before the next is started):

- Piece 10 — the open 2026-11-11 audit findings: the response-set rule as a file property, the skip that
  hides a failure, the pins that restate an owner table as a measured count, the provider-schema pins that
  do not run in CI, and the two `.github/` template files outside every index.
- Piece 11 — `tflint` integration (`backlog.md`, Nice-to-Haves), the next actionable slice outside this series.
- Piece 12 — `pyproject.toml` `target-version` to the Python floor (`py310`), 101 findings, as its own commit
  (`backlog.md`, Nice-to-Haves).

### Piece 9 — `ruff format` as a gate (complete, committed 2026-11-16)

Owner: `docs/ARCHITECTURE.md` §1.1 for the gate rule, `.github/workflows/python-tests.yml` for the CI step, and the
pins that read a module source spelling. The criteria, the two decisions, and the measurement are in
`acceptance.md`. The piece is a `backlog.md` Nice-to-Haves item, not an audit finding.

- Item 1 — the one-time pass covers the Python files of the repository: 22 modules in `src/`, 49 in `tests/`, 2 in
  `tools/`. Ruff's default double-quote style is adopted with no `pyproject.toml` change, and the pass is its own
  commit so the diff stays reviewable. Ten string literals over the 120-line limit cannot be split by ruff, so they
  are split by hand and the value is unchanged: `src/resource_mapping.py` (1), `tests/test_api_requests.py` (5),
  `tests/test_provenance.py` (2), `tests/test_write_path.py` (2).
- Item 2 — eight pins read the single-quote spelling of a module source, so they read the double-quote spelling the
  pass enforces: `tests/test_commit_actions.py` (1), `tests/test_ownership.py` (1), `tests/test_round_trip.py` (2),
  `tests/test_sanity_gate.py` (1), `tests/test_write_path.py` (3). Each pin holds the same fact, and no pin is
  weakened.
- Item 3 — the gate is the full run with the format check in it, stated in the CI workflow and in the documents that
  own the rule (`README.md` §Testing, `docs/ARCHITECTURE.md` §1.1, `docs/COVERAGE_MATRIX.md`,
  `docs/USAGE_GUIDE.md`, `PLAN.md` §Current State, `tools/README.md`), and not pinned by a test, because no pin
  reads the CI workflow file. `tools/check_documents.py` reads each notice's file total at the commit
  `docs/LICENSING.md` names, so the pass cannot move a document fact.

Gate: `ruff check .` clean, `ruff format --check .` clean, 1,685 pins in 52 modules, all pass, no skips, 333.87 s.
`python3 tools/check_documents.py` reports no finding. The finding the pass recorded is closed in `acceptance.md`.

## Feature-sized items that stay blocked

Feature-sized items that stay blocked on a fact the tool cannot read offline are recorded in
`backlog.md` and are not pieces here: the four `*_policy_rules` types wait for the F3.5 rulebase
decision and a live target, a config entry inside a stack needs a provider location shape, the EDL
`certificate_profile` field needs a rule that makes the EDL site resolve names, the per-entry report
`profile_name` column needs a value the provider does not declare, and the path 2 live facts in
`docs/API_CONVERSION_PATH.md` §4 need a live target: the committed response set shows one shape per
accepted request shape and names no fact.

`ruff format` as a gate is complete, so `tflint` integration (`backlog.md`, Nice-to-Haves) is the next actionable
slice outside this series.

## Rules the layout keeps

- `docs/ARCHITECTURE.md` §1.1 is the owner document for the layout. `AGENTS.md` names the tracking
  markdown set, and each index names every document under it, so a file outside an index is a finding.
- Import rule: `docs/ARCHITECTURE.md` §1.1 is its owner. `src/` is one flat namespace, so a module may import any
  `src/` module without a cycle, and nothing under `tests/` may import another test module: a fact more than one
  test module reads is stated once in `tests/conftest.py` and read from there. The one test that checks the rule
  reads only `src/`. A test may import `src` modules and `tests/conftest.py` through `importlib`. `src/`
  may not import from `tests/`. `tools/` is not on the test path, so `tests/test_build_kitchen_sink.py`
  reads the fixture assembler through `importlib` on the path `tests/conftest.py` builds once.
- Path 2 adds two modules, `api_requests.py` and `api_to_terraform.py`, and both must be named in the
  `docs/ARCHITECTURE.md` §1 table. Both state no second naming rule, no second writer, no second
  console line, and no environment name, so the pins that scan the `src/` set read them with the other
  modules.
- The corpus is the directory the scan runs over. A hostile fixture in it changes the set the scan
  reports for the other fixtures, so pins that state the printed set name the fixture count. The fixture
  assembler reads the same set by rule: a fixture the F3.8 input rule refuses is skipped, and the record
  is not an input (`tests/test_build_kitchen_sink.py`). A committed API response is not corpus material, so
  it sits in its own set (`tests/responses/`), and the pins that state the printed fixture set are not
  changed by it (`docs/ARCHITECTURE.md` §1.1).
