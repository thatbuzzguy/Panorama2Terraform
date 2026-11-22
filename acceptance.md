# Piece 11A.3 acceptance review — the bytes two runs write for one unit

Review record for commits `44eb37b` (the three pins in `tests/test_api_path.py` group 11) and `7bfb55b` (the piece's
record, `docs/MULTI_RUN_CODEBASE.md` §2 rule 6, and the tracking markdown), read at `7bfb55b`. The piece was not
redone here: each criterion is met, and only what the review found wrong is changed. The measurement was re-run
independently through `tests/conftest.py::api_producer` on the committed response set, one cache, both ways, and
every fact the piece recorded agrees. Three document lines disagreed with the landed state, and they are the only
other change. The commits are not pushed. Pieces 11A.1 and 11A.2 landed at `a4ead15`, `153dbf2` and `3067372` and
are not reopened; Phase 11A is complete.

## Criteria, as measured

1. **Offline only** (met). Every response both runs read is a committed file in `tests/responses/`, read through
   `tests/conftest.py::api_producer`, and both runs read through one cache, so the bytes compared are the bytes of
   the same response. No pin calls a network.
2. **What the agreement covers** (met): the unit's `.tf` bytes, read as paths from the unit directory through
   `tests/conftest.py::tf_bytes`, and the printed form of its site row, read through `write_path.unit_path` with the
   names `site_data` states. Both are unit-set files (`docs/CODEBASE_ASSEMBLY.md` §14). The unit set is the owner's
   set: the pins read the unit through `api_requests.join_units`, which reads the unit set through
   `unit_manifest.units`, and the directory through `unit_manifest.directory_name` with `naming.sanitize`, so the
   pins state no unit rule, no join rule, no path rule, no file-shape rule and no directory rule of their own.
3. **Measured before the pins** (met). The piece measured before any pin was written, and the review's independent
   re-run answers the same facts, so the pins hold what the measurement had already shown.
4. **The read-through exception stays grounded by the existing F5.5 rule** (met). The rule that answers a name the
   codebase owns and the run read no unit for is the read-through branch of `TerraformGenerator._resolve_reference`,
   pinned in `tests/test_data_blocks.py`. This piece states no read-through rule of its own and pins only that the
   committed content answers nothing for either run.
5. **One pin per stated fact**, in the module that owns the fact (met): `tests/test_api_path.py` group 11, three
   pins, one for the `.tf` bytes, one for the printed form, one for the read-through condition, in one helper that
   runs both ways on one cache. Each reads its fact through its owner, and no test module imports another test
   module.
6. **The byte difference between two runs is read through git** (met). The tool records no difference, so the write
   path, the records, the console line, the report rule, the join, the naming rule and the gate rules are unchanged,
   and no committed golden changed. `SOURCE.txt` is the only file that can differ, and no pin reads it as a byte rule.
7. **The standing rules are not broken** (met). `unit_manifest.units` is the one unit set,
   `container_coverage.is_scope_path` the one path shape, `api_requests.LIST_JOIN` the one join, `source_fetch` the
   one reader, `container_coverage.console_line` the one console line, `naming` and
   `unit_manifest.directory_name` the one naming rule, `write_path` the one writer,
   `resource_mapping.VALUE_VARIABLES` the one value-shape table, `sanity_checks.blocks` the one block reader. No
   environment name, no second console line, no new module, so the `docs/ARCHITECTURE.md` §1 table is unchanged.
8. **A half that cannot be pinned offline without a new rule goes to `backlog.md`** (met). The printed form is
   measured as agreement on absence, because no unit on the committed set names a value; the condition that would
   measure it as content is recorded in `backlog.md`, no rule was invented for it, and that half of the piece stays
   open.
9. **The gate**, single-threaded, with the counts measured (met). The numbers are in the last section.
10. **The documents** (met). `docs/MULTI_RUN_CODEBASE.md` §2 rule 6 names the module, the pins, the owners the pins
    read through, and the printed-form condition; it states no test count and no row-by-row statement of the
    agreement. Plain literal wording, no metaphor, no emoji, and every test a document names exists.

## The measurement, re-run by the review

Both runs read through `tests/conftest.py::api_producer` and one cache, so both read the same bytes.

- Both runs exit 0 and read the same single committed response, the `device-group` place
  (`tests/responses/181d42732d20ea918cb4ea333000da9280a02de1e818ee6d26300cf4b98d759c.xml`), and no other response:
  `api_requests.targeted_read_set` answers `membership_lists()` for both shapes, and the producer answers nothing for
  a request with no committed response, so the `templates` and `template-stack` requests enter no part.
- The scope index is the same for both: `device-group`, and `device-group/entry/Office-FW`, read through
  `api_requests.scope_index` with the selection and without it. That entry is inside the place the run read, so it
  names no request of its own, which is why the join reports no row for it.
- The join answers the same three pairs for both runs: the `Office-FW` place unit, the `Office-FW` unit with the
  device `fw-1.example.com`, and `Unassigned-DG`. The place response lists `Unassigned-DG` with no name, so that unit
  comes from the entry the place holds, not from a second read. The gate reports the same finding for both:
  `the join answers no row for the index entry device-group/entry/Office-FW`, one WARN, read through
  `sanity_checks.check_request_set`, which states no name rule of its own.
- The unit set is the same for both, read through `unit_manifest.units`, and the three directories agree through
  `unit_manifest.directory_name`.
- The file set is 16 files for each run, the same names both ways, byte for byte the same for every file. The unit
  the selection names, `office_fw_4507d824`, holds four `.tf` files — `actions.tf`, `provider.tf`, `scope.tf`,
  `variables.tf` — non-empty and byte for byte the same.
- No run writes `SITE_DATA.json` and neither writes `site.auto.tfvars`, so the printed form agrees as absence: no
  unit names a value. `resource_mapping.VALUE_VARIABLES` maps only `ngfw_device` to a variable, so a site row needs
  a device value the run read, and the device fact for a unit on path 2 is a §4 live-only fact
  (`docs/API_CONVERSION_PATH.md` §4). The `fw_1_example_com_69e71770` unit declares `target` as a fact the tool
  cannot read, not as a site value.
- Neither run writes a `data` block and neither writes `read_through.tf`. Measured on the response bytes: no
  committed response holds a reference field, so the F5.5 branch had nothing to answer for either run.
- The gate reports the same result for both runs: 0 FAIL, 1 WARN with the same finding, 10 `.tf` files, 2 data
  files, 2 resources, and the same result for every check.
- What can differ between two runs is the record, not the unit. Measured with two different caches on the same
  committed bytes: the 16-file set agrees and only `SOURCE.txt` differs, because the record names the cache entry it
  read through its `path` field. `SOURCE.txt` is a run fact (`docs/MULTI_RUN_CODEBASE.md` §3 rule 6), so the pins read
  both runs through one cache and state no rule for a record file.

## Pins, run one at a time

All three are in `tests/test_api_path.py` group 11, in one helper that runs both ways through
`conftest.api_producer` on one cache, and each passes on its own:

- `test_a_targeted_run_writes_the_same_tf_bytes_as_the_full_run_for_the_unit_it_selects` — the `.tf` bytes for the
  unit the selection names, read as paths from the unit directory, asserted non-empty so the pin measures content.
- `test_the_printed_form_of_the_unit_agrees_between_the_two_runs` — the site record and the printed form read through
  `site_data` and `write_path.unit_path`; on the committed set both are absent for both runs, so the pin holds
  agreement on absence, and the unit-set file set agrees.
- `test_neither_run_writes_a_read_through_block_for_content_that_names_no_read_through_name` — the block set read
  through `sanity_checks.blocks` and the read-through file name through its owner, `READ_THROUGH_FILE`, read as a
  path from the directory the manifest row names; nothing for either run. The pin holds the consequence of the
  condition, and the condition itself is the measurement above: no committed response holds a reference field, so the
  branch had nothing to answer.

The pins that hold the single-owner claims pass unchanged:
`tests/test_unit_manifest.py::test_the_join_reads_the_unit_set_through_this_rule`,
`tests/test_write_path.py::test_the_splitter_writes_through_the_single_writer`,
`tests/test_site_data.py::test_site_data_defines_no_second_naming_rule`,
`tests/test_api_requests.py::test_the_module_reads_the_layout_rules_through_their_owners`,
`tests/test_data_blocks.py` groups 4, 5 and 6, and
`tests/test_layout.py::test_the_indexes_name_every_document_under_them`. The import rule reads clean: no test module
imports another test module, `src/` imports nothing from `tests/`, and the shared facts are read from
`tests/conftest.py`. No pin was removed: the group gained its entry and the three pins.

## What the review corrected

Three document lines disagreed with the landed state. No code, no pin and no measurement changed.

- `docs/MULTI_RUN_CODEBASE.md` named only Piece 11A.1 and Piece 11A.2 as landed and said every §2 rule other than 1,
  2, 3 and 4 was pending a pin, which its own rule 6 contradicts: rule 6 names three pins that hold. It now names
  Piece 11A.3 and rules 1, 2, 3, 4 and 6 as pinned.
- `PLAN.md` listed Phase 11A as one of three phases of the open epic. The phase is complete, so its detail is removed
  and the open phases are 11B and 11C.
- `backlog.md` said the rules in the design record are design rules pending a pin. A rule there that has pins is read
  through the test module that holds them, so the entry now states that.
- This record said `to-do.md` shows Phase 11A complete. `to-do.md` holds no Phase 11A detail, and its open pieces are
  11B.1 to 11B.4 and 11C.1 to 11C.3, with 11B.1 next, so the record now states that.

## Gate, re-measured by the review

At `7bfb55b`, single-threaded: `ruff check .` clean at `py310`; `ruff format --check .` clean on the 106 files it
reads, 79 Python files and 27 markdown files; `python3 tools/check_documents.py` reports no finding;
`python3 -m pytest` passes 1,757 pins with the same 4 skips for the missing `tflint` binary — 1,761 pins in 53 test
modules, the same counts the piece measured. Read through the per-module collection counts: `tests/test_api_path.py`
42, the 39 before the piece plus the 3 new pins, and `tests/test_api_requests.py` 32, unchanged. The piece measured
218.96 s; the review's run measured 265.94 s on the same counts, so run-to-run time varies while the counts agree.
`terraform` is present on this machine, so the pins that read the live provider schema ran, and the 4 skips are the
`tflint` pins in `tests/test_sanity_gate.py`. No committed golden changed.

## Tracking markdown

`to-do.md` holds no Phase 11A detail: the phase is complete and the git history holds it. Its open pieces are Phase
11B (11B.1 next) and Phase 11C. `PLAN.md` names Epic 11 as open with the design record and Phase 11A complete;
`backlog.md` holds the site-row condition this piece could not measure as content, the read-through half that needs
the built-in name table, the move fact, the stale-file boundary, the `vsys` and device selection, and the live-target
items. The documents and the indexes state no test count, and every test a document names exists.
