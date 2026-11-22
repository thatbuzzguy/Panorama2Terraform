# Piece 11A.3 acceptance record — the bytes two runs write for one unit

The criteria for this piece, written before the pins, and the measurement that decided it. The
measurement is on the committed response set for one unit read both ways: the run that declares no
selection, and the run that selects `device-group/entry/Office-FW`. The agreement already holds, so
no rule in `src/` is changed and no new module is added: the piece is three pins in
`tests/test_api_path.py` group 11 and the record. The commits are not pushed. Piece 11A.1 landed at
`a4ead15` and Piece 11A.2 at `153dbf2` and `3067372`; neither is reopened here.

## Criteria

1. **Offline only** (met). Every response both runs read is a committed file in `tests/responses/`,
   read through `tests/conftest.py::api_producer`, and both runs read through one cache, so the
   bytes compared are the bytes of the same response. No pin calls a network.
2. **What the agreement covers** (met): the unit's `.tf` bytes, read as paths from the unit
   directory through `tests/conftest.py::tf_bytes`, and the printed form of its site row, read
   through `write_path.unit_path` with the names `site_data` states. Both are unit-set files
   (`docs/CODEBASE_ASSEMBLY.md` §14). The unit is read through `unit_manifest.units` and its
   directory through `unit_manifest.directory_name`, so the pins state no unit rule, no path rule,
   no file-shape rule and no directory rule of their own.
3. **Measured before the pins** (met). The measurement is the section below, taken before any pin
   was written, so the pins hold facts the measurement had already shown.
4. **The read-through exception stays grounded by the existing F5.5 rule** (met). The rule that
   answers a name the codebase owns and the run read no unit for is the read-through branch of
   `TerraformGenerator._resolve_reference`, pinned in `tests/test_data_blocks.py`. This piece states
   no read-through rule of its own and pins only that the committed content answers nothing for
   either run.
5. **One pin per stated fact**, in the module that owns the fact (met): `tests/test_api_path.py`
   group 11, three pins, one for the `.tf` bytes, one for the printed form, one for the read-through
   condition. Each reads its fact through its owner, and no test module imports another test module.
6. **The byte difference between two runs is read through git** (met). The tool records no
   difference, so the write path, the records, the console line, the report rule, the join, the
   naming rule and the gate rules are unchanged, and no committed golden changed.
7. **The standing rules are not broken** (met). `unit_manifest.units` is the one unit set,
   `container_coverage.is_scope_path` the one path shape, `api_requests.LIST_JOIN` the one join,
   `source_fetch` the one reader, `container_coverage.console_line` the one console line, `naming`
   and `unit_manifest.directory_name` the one naming rule, `write_path` the one writer,
   `resource_mapping.VALUE_VARIABLES` the one value-shape table, `sanity_checks.blocks` the one block
   reader. No environment name, no second console line, no new module, so the `docs/ARCHITECTURE.md`
   §1 table is unchanged.
8. **A half that cannot be pinned offline without a new rule goes to `backlog.md`** (met). The
   printed form is measured as agreement on absence, because no unit on the committed set names a
   value; the condition that would measure it as content is recorded in `backlog.md`, no rule was
   invented for it, and that half of the piece stays open.
9. **The gate**, single-threaded, with the counts measured (met). The numbers are in the last
   section.
10. **The documents** (met). `docs/MULTI_RUN_CODEBASE.md` §2 rule 6 names the module, the pins, the
    owners the pins read through, and the printed-form condition; it states no test count and no
    row-by-row statement of the agreement. Plain literal wording, no metaphor, no emoji, and every
    test a document names exists.

## The measurement on the committed response set, before the pins

Both runs read through `tests/conftest.py::api_producer` and one cache, so both read the same bytes.

- Both runs exit 0, read the same single committed response (the `device-group` place) and no other
  response, because `templates` and `template-stack` have no committed response and
  `api_requests.targeted_read_set` keeps every membership list.
- The scope index is the same for both: `device-group`, and `device-group/entry/Office-FW`, the entry
  the selection names, read through `api_requests.scope_index` with the selection and without it.
- The join answers the same pair for both runs and the gate reports the same finding for both:
  `the join answers no row for the index entry device-group/entry/Office-FW`, one WARN, read through
  `sanity_checks.check_request_set`, which states no name rule of its own.
- The unit set is the same for both, read through `unit_manifest.units`: `Office-FW`, `Office-FW`
  with the device `fw-1.example.com`, and `Unassigned-DG`; the three directories agree.
- The file set is 16 files for each run, the same names both ways, byte for byte the same for every
  file. The unit the selection names, `office_fw_4507d824`, holds four `.tf` files — `actions.tf`,
  `provider.tf`, `scope.tf`, `variables.tf` — non-empty and byte for byte the same.
- No run writes `SITE_DATA.json` and neither writes `site.auto.tfvars`, so the printed form agrees as
  absence: no unit names a value. `resource_mapping.VALUE_VARIABLES` maps only `ngfw_device` to a
  variable, so a site row needs a device value the run read, and the device fact for a unit on path 2
  is a §4 live-only fact (`docs/API_CONVERSION_PATH.md` §4). The `fw_1_example_com_69e71770` unit
  declares `target` as a fact the tool cannot read, not as a site value.
- Neither run writes a `data` block and neither writes `read_through.tf`. Measured on the response
  bytes: no committed response holds a reference field, so the F5.5 branch had nothing to answer for
  either run.
- The gate reports the same result for both runs: 0 FAIL, 1 WARN with the same finding, 10 `.tf`
  files, 2 data files, 2 resources, and the same result for every check.
- What can differ between two runs is the record, not the unit: `SOURCE.txt` names the cache entry,
  so two runs that read through different caches differ in that file. It is a run fact
  (`docs/MULTI_RUN_CODEBASE.md` §3 rule 6), so the pins read both runs through one cache and state no
  rule for a record file.

After the pins: the same facts, read through the pins, with the counts in the last section. No
committed golden changed.

## Pins, run one at a time

All three are in `tests/test_api_path.py` group 11, in one helper that runs both ways through
`conftest.api_producer` on one cache, and each passes on its own:

- `test_a_targeted_run_writes_the_same_tf_bytes_as_the_full_run_for_the_unit_it_selects` — the `.tf`
  bytes for the unit the selection names, read as paths from the unit directory, asserted non-empty
  so the pin measures content.
- `test_the_printed_form_of_the_unit_agrees_between_the_two_runs` — the site record and the printed
  form read through `site_data` and `write_path.unit_path`; on the committed set both are absent for
  both runs, so the pin holds agreement on absence, and the unit-set file set agrees.
- `test_neither_run_writes_a_read_through_block_for_content_that_names_no_read_through_name` — the
  block set read through `sanity_checks.blocks` and the read-through file name through its owner,
  `READ_THROUGH_FILE`, read as a path from the directory the manifest row names; nothing for either
  run. The pin holds the consequence of the condition, and the condition itself is the measurement
  above: no committed response holds a reference field, so the branch had nothing to answer.

The pins that hold the single-owner claims pass unchanged:
`tests/test_unit_manifest.py::test_the_join_reads_the_unit_set_through_this_rule`,
`tests/test_write_path.py::test_the_splitter_writes_through_the_single_writer`,
`tests/test_site_data.py::test_site_data_defines_no_second_naming_rule`,
`tests/test_api_requests.py::test_the_module_reads_the_layout_rules_through_their_owners`,
`tests/test_data_blocks.py` groups 4, 5 and 6, and
`tests/test_layout.py::test_the_indexes_name_every_document_under_them`.

## The decision the measurement produced

No rule change. The agreement holds on the committed response set as the rule states it, so the piece
is the pins and the record, and `docs/MULTI_RUN_CODEBASE.md` §2 rule 6 now names the module, the
pins, the owners the pins read through, and the printed-form condition. The two halves the committed
set cannot measure as content — the site row, and the read-through name — are not pinned as content,
and the condition for each is stated in the record. The piece is open on the printed-form half.

## Gate, measured single-threaded

`ruff check .` clean at `py310`; `ruff format --check .` clean on the 106 files it reads (79 Python
files, 27 markdown files); `python3 tools/check_documents.py` reports no finding; `python3 -m pytest`
passes 1,757 pins with the same 4 skips for the missing `tflint` binary — 1,761 pins in 53 test
modules, 3 more than the 1,758 the previous piece measured, in 218.96 s, and 214.10 s on the
confirmation run that read this record, so run-to-run time varies while the counts agree. Read through the per-module
collection counts: `tests/test_api_path.py` 42, the 39 before the piece plus the 3 new pins, and
`tests/test_api_requests.py` 32, unchanged. `terraform` is present on this machine, so the pins that
read the live provider schema ran, and the 4 skips are the `tflint` pins in
`tests/test_sanity_gate.py`. No committed golden changed.

## Tracking markdown

`to-do.md` shows Phase 11A complete, so its piece detail is removed and the open pieces are Phase
11B; `PLAN.md` names Epic 11 as open with the design record; `backlog.md` holds the site-row
condition this piece could not measure as content, the read-through half that needs the built-in name
table, and the live-target items. The documents and the indexes state no test count, and every test a
document names exists.
