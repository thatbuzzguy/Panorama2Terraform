# Acceptance — review record for Piece 11B.4 (2026-11-22)

Piece 11B.4 (the gate reads the run's unit set for a partial run) is reviewed at `4057502` (the module and the
four test modules) and `f764957` (the tracking markdown), both not pushed. Every committed criterion is met by the
tree. The measurement was re-run independently, single-threaded, through `tests/conftest.py` and through the record
modules themselves, and against the module as it stood at `4057502^`. The review corrected one count, four wording
claims, one duplicated line in a test docstring and one tracking bullet indent, listed under Findings, and
committed them as one commit for the test module and the document corrections and one for this record with the
`agent-status.md` update. The commit shape holds: `4057502` holds code and pins only, and the decision and the
measurement markdown sit in `f764957`.

## Criteria, read against the tree

1. **The block rules read the whole codebase.** Met. The second run wrote one `.tf` file,
   `shared_45ca31c3/address_objects.tf`, inside the one directory its own set names. The reader read 61 `.tf` files
   across 11 unit directories, 8 data files and 64 resource blocks, so the counts name the codebase and not the
   run's set, and the `placeholders` WARN sits at `shared_a6577c11/vpn.tf:67`, a unit the second run read no rows
   for. Pinned by `tests/test_sanity_gate.py::test_the_block_rules_read_the_whole_codebase_for_a_partial_run`.
2. **The data rule reads the record set at the root as the codebase set.** Met. Against the second run's own root
   record: 37 `data_files` findings and 4 `rule_blocks` findings, read against the 11 directories the tree holds
   while the record names 1 unit. The 37 read as 29 at the root from two records (`REFERENCE_EDGES.json` 26,
   `SITE_DATA.json` 3) plus 8 on the rule data pair inside `production_dg_6ce3cc69`; the manifest and ownership
   records read as their rows and state no finding. Against the merged record written through
   `codebase_state.merge_rows` and `write_path`, both rules report nothing, including the printed form inside the
   10 directories the run did not write, and the count names the same 8 data files. Pinned by
   `tests/test_data_file_gate.py::test_the_data_rule_reads_the_merged_record_as_the_codebase_set`.
3. **The two rules that read two sets read the run's unit set.** Met. The cross-check reports 8 findings, all
   naming `shared_45ca31c3`, against the 44 the same tree reports through the module as it stood at `4057502^`, 36
   of them naming units the run read no rows for. The count inside the run's own unit still disagrees, because the
   reader reads the `.tf` bytes the first run wrote there. The root-set fact keeps: a planted `.tf` file at the
   codebase root names no unit, so its count cannot be assigned and the rule reports one more finding.
   `request_set` reads the join against the run's index unchanged, and a call with no ledger or no index reports the
   rule as NOT RUN. Pinned by `tests/test_round_trip.py::test_the_block_side_is_read_inside_the_run_s_unit_set` and
   `::test_a_tf_file_at_the_root_names_no_unit`.
4. **The two command checks run once per unit directory the run wrote.** Met. With the merged record at the root the
   record names 11 directories and the run wrote 1, so each check answers one result naming `shared_45ca31c3`. The
   set is read through `unit_manifest.units` over the rows the ledger read, so the gate states no unit rule of its
   own. With no ledger `unit_directories` reads the record, which is how `check_rule_blocks` and
   `tests/conftest.py`'s `data_file_set` read it: measured 11 on the merged tree against 1 for the run. For a
   single run the two sets are the same set in the same order, measured on `kitchen_sink.xml` (11),
   `interfaces_other.xml` (2) and `address_objects.xml` (1), so the pins that read `--validate` and `--tflint`
   today are unchanged. The two pins read the checks with `terraform=None` and `tflint=None` and clear `PATH`, so
   they answer the skip result on a machine that has a binary, and the skip rule for the pins that need a binary
   stays `tests/conftest.py`'s.
5. **The severity rule and the exit-code rule are unchanged.** Met. The partial run reports 41 FAIL (37 data rules
   plus 4 rule blocks) and 9 WARN (8 cross-check plus 1 placeholder), and the entry point exits 1 for it. The same
   tree with the merged record written at the root reports 0 FAIL and 9 WARN, so `SanityReport.failed` is False and
   the exit code is 0. The exit 1 is what the run wrote at the root, so the condition stays in `backlog.md` and no
   severity rule or exit-code rule was invented. Pinned by
   `tests/test_sanity_gate.py::test_a_partial_run_exit_code_follows_the_rules_that_read_the_files`.
6. **The single-run case produces today's gate result and bytes.** Met. Re-measured against the module as it stood
   at `4057502^`: the `SANITY_REPORT.txt` bytes for the three committed runs are identical (2,112, 1,662 and 1,363
   bytes), so a single run reads the same directories in the same order. `tests/golden/` holds no
   `SANITY_REPORT.txt`, and no golden is in either commit.
7. **Single-owner constraints.** Met. `sanity_checks.py` is the only module that defines a gate rule, `CHECK_ORDER`,
   the severity and exit tables (`TFLINT_SEVERITY`, `TFLINT_EXIT_CODES`) and the NOT RUN result; it writes no file,
   names no environment, builds no console line and states no naming rule: it reads `naming.sanitize`, the one block
   reader `blocks`, the record readers `parse_rows`, and the paths through `write_path`. `unit_manifest.units` is
   the one unit rule, `entry_coverage.EntryLedger.destination` the one destination rule, and
   `codebase_state.merge_rows` with each module's `parse_rows` the only merge and join reads. The pins that hold
   these facts are the ones that name them: `test_the_tflint_severity_rule_and_the_exit_code_rule_are_data_in_the_gate`,
   `test_no_module_defines_a_second_naming_rule`, `test_the_entry_point_names_no_environment_name_of_its_own`,
   `test_the_splitter_writes_through_the_single_writer` with the `src/` writer scan, and
   `test_the_console_line_shape_is_stated_in_one_place`, which reads `container_coverage.console_line` as the only
   line builder and the report line shape as `container_coverage.report_line`. The index rule is pinned by
   `tests/test_layout.py::test_the_indexes_name_every_document_under_them`, and the 24 `src/` modules are unchanged.
   No test module imports another test module, and the facts more than one test module reads are stated once in
   `tests/conftest.py` (`partial_run`, `write_merged_records`, `record_rows`, `data_file_set`).
8. **Pins, one per stated fact, in the module that owns the rule.** Met. The six pins are the four in
   `tests/test_sanity_gate.py`, one in `tests/test_round_trip.py` and one in `tests/test_data_file_gate.py`. Each
   runs a committed fixture through `tests/conftest.py`, reads every record row through the record's own
   `parse_rows`, and builds no row by hand. The six pass on their own.

## Findings

1. `docs/ARCHITECTURE.md` §4.6 and the §1 module row for `sanity_checks.py` still stated the rule as the piece
   found it: the plan check runs once per unit directory the manifest record names. That is the pre-piece rule. Both
   now state the set the run wrote, read through `unit_manifest.units` over the rows its own ledger read, with the
   single-run equality, and §4.6 links `docs/MULTI_RUN_CODEBASE.md` §5 rule 4, the owner document for the run set.
   The §4.6 rule table row for `tflint` read the same way and was corrected with it.
2. `docs/MULTI_RUN_CODEBASE.md` §5 rule 2 and the pin docstring in `tests/test_data_file_gate.py` stated the 29
   root findings as read "on the three records at the root". Measured, 29 come from two records, 26 and 3, and the
   manifest and ownership records state no finding. Corrected in both.
3. `tests/test_round_trip.py`'s pin list carried the 5.1 fact twice, once as the list item and once as an unmarked
   continuation of it. The duplicate was removed.
4. `README.md` §Testing stated the pre-piece rule for `tests/test_sanity_gate.py`, "the one result per unit
   directory the record names". Corrected to the set the run wrote with the single-run equality, and the three
   entries now name the fact each new pin holds: the report counts read as the codebase set, the block side read
   inside the run's unit set, and the record set at the root read as the codebase set.
5. `docs/MULTI_RUN_CODEBASE.md` §5 rule 5 named no pin while every other rule in §5 names its pin. The pin that
   holds it is `tests/test_write_path.py::test_no_rule_reads_a_file_outside_the_two_sets`, so the name was added.
6. The first-pass review record said the result of a check with no binary is `sanity_checks.SKIP`, "not the word
   `SKIPPED`". `SKIP` is the constant, and its value is the word `SKIPPED`. What the pins do is read the constant,
   so no pin states the word itself. Corrected here and in `agent-status.md`.
7. The criterion that reads the six pins as holding the single-owner facts mis-attributes them: the six pins state
   which set each rule reads, and the single-owner facts are held by the pins named under criterion 7. Each fact is
   still in one place.
8. `backlog.md` held a bullet continuation at column 0, so the bullet read as two sentences in two places. The
   indent was restored.

Two things read during the review and not changed, because no rule or pin disagrees with them:
`count_data_files` builds a root record path as `output_dir / name` rather than through `write_path.root_path`, so
the count reads the placement from the data rule's own names, and no pin asks a read to go through the write path;
and the word `NOT RUN` also appears in the entry point's `--tflint` help text as prose, while the result itself is
stated once as `sanity_checks.NOT_RUN`. No pin holds the rule that no test module imports another test module: the
rule is met by inspection, and `tools/check_documents.py` reads no import graph.

## Gate, measured on this tree after the corrections

Single-threaded: `ruff check .` clean at `py310`; `ruff format --check .` clean on the 108 files it reads (81
Python files, 27 markdown files); `python3 tools/check_documents.py` reports no finding; `python3 -m pytest` exits
0 with 1,784 pins passing and 4 skipped, so 1,788 pins in 54 test modules, the same 6 pins Piece 11B.4 added to the
1,782 Piece 11B.3 measured. Per module: `tests/test_sanity_gate.py` 118, `tests/test_round_trip.py` 35,
`tests/test_data_file_gate.py` 29. `tflint` is absent on this machine, so the 4 skips are the `tflint` pins in
`tests/test_sanity_gate.py`, and each skips only for the missing binary; `terraform` is present, so the pins that
read the live provider schema ran. The first-pass record's 244.57 s is machine time, not a measured fact: the
review's runs measured 241.83 s alone and 312.43 s with another run in flight. No committed golden moved.
