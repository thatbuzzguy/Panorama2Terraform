# Piece 11A.2 acceptance review — the targeted read set

Review record for commits `153dbf2` (the two rules, the entry point's read of them, and the pins) and `3067372`
(the documents and the tracking markdown), read at `3067372`. The piece was not redone here: each criterion is met,
and only what the review found wrong is changed. Nothing was wrong, so no code, pin or document disagreed, and the
change is the record itself, which now states each criterion as met and carries the review's two confirmation
timings. The commits are not pushed. Piece 11A.1 landed at `a4ead15` and is not reopened.

## Criteria, as measured

1. **Offline only** (met). Every response a pin reads is a committed file in `tests/responses/`, read through
   `tests/conftest.py::api_producer`, or the module's own fixture bodies read through the injected producer. The
   committed set holds five responses: the whole-config export, `show system info`, the `device-group` place, the
   `shared` place, and `device-group/entry/Production-DG`. The `templates` and `template-stack` places have no
   committed response, so the pins for those facts read the fixture bodies. The `vsys` and device selection needs the
   live-target fact that names which device the run read, so it stays in `backlog.md` and no pin asserts it.
2. **The targeted read set** (met). `api_requests.targeted_read_set` answers `membership_lists()` for both shapes, so
   no list is dropped for a selection, and `api_to_terraform.run_order` and `lists_read` read the set through that
   rule, so the entry point states no read rule of its own and gains no function. The reason no list is dropped is
   grounded on the committed entry response (`device-group/entry/Production-DG`): `parse_associations` answers an
   empty table for each of the four, because the response holds the entry its own request names and the method reads
   the entries inside the container. With no selection the run reads the four lists; measured on the committed set,
   one of those four requests is answered by a committed response.
3. **The targeted name set** (met). `api_requests.targeted_names` answers the names inside the place for a place
   selection, and the entry the selection names plus the names the tables hold for it for an entry selection, read
   through `LIST_JOIN`. `template-stack/entry/Branch-Stack` answers `(template-stack, Branch-Stack)` and
   `(templates, HQ-Networks)`; `Datacenter-FW`, which the selection excludes, is not in the set, and
   `fw-1.example.com`, a table key, is not in it. With no selection the set is every name the tables read.
4. **The join's answer** (met). A name the selection excludes is not an index entry, so `unit_findings` reports no
   finding for it, and `sanity_checks.check_request_set` turns the pairs into findings without stating a name rule.
   `unit_manifest.units` names the same units both ways, and `join_units` answers an excluded unit with the place
   entry, so it stays a pair. The entry the selection names enters the index through `scope_path`, because the run
   read the response for it: `device-group/entry/Production-DG` is not in the whole set and is in the targeted set.
5. **A place read that holds an excluded name is not refused** (met). `join_response` checks the names inside a
   response against the names the targeted index read for that container. On the committed `device-group` response
   the whole set read `Datacenter-FW`, which the response holds no entry for, so the same bytes are refused for the
   whole set and accepted for the targeted set, which reads `Office-FW` only.
6. **The pins** (met). Six new pins in group 8 of `tests/test_api_requests.py` and three in group 10 of
   `tests/test_api_path.py`, each in the module that owns the rule, each reading its fact through its owner. No pin
   reads a document word. The import rule reads clean: no test module imports another test module, `src/` imports
   nothing from `tests/`, and the shared facts are read from `tests/conftest.py`. Each new pin passes on its own.
7. **The standing rules are not broken** (met). `unit_manifest.units` is the only unit set,
   `container_coverage.is_scope_path` the only path shape, `api_requests.LIST_JOIN` the only join,
   `source_fetch` the only reader, `container_coverage.console_line` the only console line, and
   `naming`/`unit_manifest.directory_name` the only naming rule. `run_order` stays the only place the read order is
   stated, and the entry point reads `targeted_read_set`, `targeted_names`, `scope_index`, `list_container` and
   `scope_path` through `api_requests` and states no sort, no path list and no name rule of its own. The join stays a
   data module that prints no console line. No second join, reader, console line, naming rule, merge rule or report
   rule is written here, and no new module is added, so the `docs/ARCHITECTURE.md` §1 table is unchanged.
8. **The changed pin** (met).
   `tests/test_api_path.py::test_a_selection_that_names_no_unit_is_an_argument_error_on_a_run` keeps the argument-error
   part — exit 2 and no file, the shape `--path` already states — and reads the accepted case as the same file set
   with different bytes, which is the difference the read rule creates. The pins that changed are the three the record
   names, and no pin was removed.
9. **The gate** (met), run single-threaded; the counts are in the section below. No committed golden changed.
10. **The documents** (met). `docs/MULTI_RUN_CODEBASE.md` §2 rule 3 names the module and the pins, and
    `docs/API_CONVERSION_PATH.md` names the rule in the three places its owners hold it: §2.2 for the read set and the
    name set, §3 for the join's answer for a targeted run, and §6 for the run order and the record. Plain literal
    wording, no metaphor, no emoji, no test count in a document, and every test a document names exists.

## Pins, run one at a time

Each pin passes on its own, in the module that owns its rule:

`tests/test_api_requests.py`, group 8:

- `test_the_targeted_read_set_keeps_every_list_a_single_read_cannot_state` — the four lists for both shapes, with the
  entry read answered empty on the committed response.
- `test_the_targeted_name_set_is_the_names_inside_the_place_or_the_names_the_selection_owns` — the set read through
  `LIST_JOIN` and `names_read`, no name rule stated by the pin.
- `test_a_name_the_selection_excludes_gains_no_index_entry` — the whole set holds an entry for the excluded name, the
  targeted set holds none, and the place the selection names keeps its entry.
- `test_the_join_reports_no_finding_for_a_name_the_selection_excludes` — the unit set read through
  `unit_manifest.units` agrees both ways, and the pair for the excluded unit names the place entry.
- `test_a_place_read_that_holds_an_excluded_name_is_not_refused` — the same committed bytes are refused for the whole
  set and accepted for the targeted set.
- `test_the_entry_the_selection_names_enters_the_index_through_the_one_path_definition` — the path built through
  `api_requests.scope_path`, read through `container_coverage.is_scope_path`.

`tests/test_api_path.py`, group 10:

- `test_a_targeted_run_reads_the_lists_and_the_names_the_selection_states` — the read set through
  `api_requests.targeted_read_set`, the names through `api_requests.targeted_names`, the order read as the run read it.
- `test_the_join_reports_no_finding_for_a_name_the_selection_excludes` — the findings read through
  `sanity_checks.check_request_set` for both sets, and the pair through the unit rule.
- `test_the_record_names_the_read_set_in_run_order_for_a_targeted_run` — the record read through
  `provenance.parse_records` as data, with the rows compared against the read set and the name set.

The three changed pins, and the index rule pin:

- `tests/test_api_path.py::test_the_run_order_is_the_membership_lists_then_the_index_entries` — reads the order
  through `api_requests.targeted_read_set`, pins no sort and no path list in the entry point, and pins that no other
  module states the order.
- `tests/test_api_path.py::test_the_entry_point_states_no_rule_an_owner_states` — holds `targeted_read_set` and
  `targeted_names` as `api_requests`' rules.
- `tests/test_api_path.py::test_a_selection_that_names_no_unit_is_an_argument_error_on_a_run` — the argument-error
  part unchanged, the accepted case read as the same file set with different bytes.
- `tests/test_layout.py::test_the_indexes_name_every_document_under_them`.

The pins that hold the single-owner claims pass unchanged:
`tests/test_api_requests.py::test_the_four_membership_lists_are_the_container_table_rows` and
`test_the_module_reads_the_layout_rules_through_their_owners`,
`tests/test_unit_manifest.py::test_the_join_reads_the_unit_set_through_this_rule`,
`tests/test_container_coverage.py::test_the_definitions_rule_reads_the_place_the_declared_path_names`,
`test_a_predefined_path_is_read_by_the_one_scope_path_definition` and `test_the_console_line_shape_is_stated_in_one_place`,
`tests/test_sanity_gate.py::test_the_join_prints_no_console_line_and_stays_a_warn`,
`tests/test_site_data.py::test_site_data_defines_no_second_naming_rule`,
`tests/test_variables.py::test_the_entry_point_names_no_environment_name_of_its_own`, and
`tests/test_write_path.py::test_the_splitter_writes_through_the_single_writer`.

## What the review corrected

Nothing. Every criterion is met, no pin changed, and the document check reports no finding. The only change is the
record: it states each criterion as met and adds the review's two confirmation timings to the gate measurement below.

## Gate, re-measured by the review

At `3067372`, single-threaded: `ruff check .` clean at `py310`; `ruff format --check .` clean on the 106 files it
reads, 79 Python files and 27 markdown files; `python3 tools/check_documents.py` reports no finding;
`python3 -m pytest` passes 1,754 pins with the same 4 skip for the missing `tflint` binary — 1,758 pins in 53 test
modules. The piece measured 311.05 s; the review's two confirmation runs measured 310.75 s and 316.00 s on the same
counts, so run-to-run time varies while the counts agree. Read through the per-module collection counts:
`tests/test_api_requests.py` 32 and `tests/test_api_path.py` 39, which is the 26 and 36 before the piece plus the 6
and 3 new pins. `terraform` is present on this machine, so the pins that read the live provider schema ran, and the
4 skips are the `tflint` pins in `tests/test_sanity_gate.py`. No committed golden changed.

## Tracking markdown

`to-do.md` holds Piece 11A.3 as the open piece and no completed-piece detail; `PLAN.md` names Epic 11 as open with
the design record; `backlog.md` holds the live-target items, including the `vsys` and device selection, and the eight
path-split sites; the documents and the indexes state no test count, and every test a document names exists.
