# Acceptance — Piece 11B.4, the gate for a partial run (2026-11-22)

Piece 11B.4 is the gate for a partial run, as `docs/MULTI_RUN_CODEBASE.md` §5 states it: the block rules read the
whole codebase, the data rule reads the merged records, the two two-set rules read the run's unit set, and the plan
check and the rule-set check run once per directory the run wrote. The open behaviour this piece closes is the exit
code a second run gets when it writes into an existing codebase, measured below.

The pattern every pin reads: `tests/fixtures/kitchen_sink.xml` as the codebase (11 units), and
`tests/fixtures/address_objects.xml` as the second run writing into a copy of its output (1 unit,
`shared_45ca31c3`), both offline on committed fixtures. The pattern and the merged record set are stated once in
`tests/conftest.py` (`partial_run` and `write_merged_records`), so no test module states them a second time; the
merged root records are written through `codebase_state.merge_rows` over rows read back through each record's
`parse_rows` and printed through `write_path`, so no pin builds a row by hand.

## Criteria

1. **The block rules read the whole codebase, unchanged.** For the committed pair the block rules read 61 `.tf`
   files, 64 resource blocks and 8 data files, while the second run wrote one `.tf` file in one directory
   (`shared_45ca31c3/address_objects.tf`); the other 10 directories hold the first run's bytes. A finding names the
   path from the codebase root, so a finding can name a unit the run did not write: measured, the `placeholders`
   WARN at `shared_a6577c11/vpn.tf:67` in a unit the second run read no rows for.
2. **The data rule reads the record set at the root as the codebase set, unchanged as a rule.** Measured against the
   second run's own root record: `data_files` reports 37 FAIL findings and `rule_blocks` 4, all read against the 11
   directories the tree holds while the record names 1 unit. Measured against the merged record written through
   `codebase_state.merge_rows` and `write_path`: both rules report nothing, including the printed form inside a unit
   the run did not write. So the exit code the second run gets today is what the run wrote at the root, not a gate
   rule.
3. **The two rules that read two sets read the run's unit set.** `round_trip` reads the block side inside
   `unit_manifest.units(ledger)`, so a unit the run read no rows for enters no count: measured, 44 findings become 8
   for the committed pair, all inside `shared_45ca31c3`, and the 10 units read only through the record name no
   finding. The root-set fact is unchanged: a `.tf` file at the codebase root names no unit, so its count cannot be
   assigned, and that pin keeps. `request_set` reads the join against the run's index, unchanged, and a call with no
   ledger or no index reports the rule as NOT RUN, unchanged.
4. **The plan check and the rule-set check run once per unit directory the run wrote, and each result names its
   directory.** The run's set is read through `unit_manifest.units` over the rows its own ledger read, so the gate
   states no unit rule of its own; a call that passes no ledger names no run, so it keeps reading the set the record
   names through `unit_directories`, which is how `check_rule_blocks` and `tests/conftest.py`'s data file set read it.
   Measured for the committed pair with the merged record at the root: the run wrote 1 directory and the merged record
   names 11, so each check reports one result naming `shared_45ca31c3`. For a single run the two sets are the same set
   in the same order, so the pins that hold today for `--validate` and `--tflint` are unchanged. The pins read the two
   checks with `terraform=None` or `tflint=None`, so they run on a machine with no binary, and the binary skip rule
   stays `tests/conftest.py`'s.
5. **The severity rule and the exit-code rule are unchanged, and no new severity rule appears.** FAIL for the rules
   that read the files, WARN for the two rules that compare two sets, NOT RUN for a check that cannot run, and the
   entry point decides on `SanityReport.failed`. So the second run's exit code is still decided by the rules that
   read the files, and the cross-check findings cannot change it. Measured: the second run reports 41 FAIL and 9 WARN
   and the entry point exits 1; on the same tree with the merged record written at the root the gate reports 0 FAIL
   and 9 WARN (8 cross-check plus 1 placeholder), so the exit code is 0. The fact that the run writes the merged
   record at the root is Piece 11C, so the condition is recorded in `backlog.md` and no severity rule is invented.
6. **The single-run case produces today's gate result and bytes.** Measured on three committed runs,
   `kitchen_sink.xml` (11 units), `interfaces_other.xml` (2) and `address_objects.xml` (1): the run's set equals the
   record's set in the same order, so the block side reads the same directories as today and the report bytes are
   unchanged. No committed golden moved; `tests/golden/` holds no `SANITY_REPORT.txt`, so there is no report golden to
   regenerate.
7. **Single-owner constraints.** Only `src/sanity_checks.py` changes. `sanity_checks.py` is the only place that
   states the gate rules, `CHECK_ORDER`, the severity and exit tables, the report shape and the NOT RUN result;
   `unit_manifest.units` is the only unit rule, `entry_coverage.EntryLedger.destination` the only destination rule,
   `codebase_state.merge_rows` and `parse_rows` the only merge and join reads, and `tools/check_documents.py` the only
   reader of the document rules. `sanity_checks.py` states no second naming rule, no second reader, no second writer,
   no console line, no environment name, no path rule and no new module. `unit_directories` stays the gate's one
   reader of a unit set for the two checks that run through an external command. No test module imports another test
   module; a fact more than one test module reads stays in `tests/conftest.py`.
8. **Pins**, one per stated fact, in the module that owns the rule, each run through committed material and reading
   every record row through the record's own `parse_rows`.

## Pins

`tests/test_sanity_gate.py`:

- `test_the_block_rules_read_the_whole_codebase_for_a_partial_run` — criterion 1.
- `test_the_two_command_checks_run_once_per_directory_the_run_wrote` — criterion 4, the partial-run half.
- `test_for_a_single_run_the_run_set_and_the_record_set_are_the_same_set` — criteria 4 and 6.
- `test_a_partial_run_exit_code_follows_the_rules_that_read_the_files` — criterion 5.

`tests/test_round_trip.py`:

- `test_the_block_side_is_read_inside_the_run_s_unit_set` — criterion 3, and the root-set fact it keeps.

`tests/test_data_file_gate.py`:

- `test_the_data_rule_reads_the_merged_record_as_the_codebase_set` — criterion 2.

## Review record

Every criterion was read against the tree and met. Two things the first pass did not hold and were corrected: the
result of a check with no binary is `sanity_checks.SKIP`, not the word `SKIPPED`, and the single-run pin reads the
directory a plan result names through the finding, because with no binary every result names it as a SKIPPED finding
rather than in its note.

Gate, measured single-threaded on the tree that holds this piece: `ruff check .` clean at `py310`,
`ruff format --check .` clean on the 108 files it reads (81 Python files, 27 markdown files),
`python3 tools/check_documents.py` reports no finding, and `python3 -m pytest` passes 1,784 pins with the same 4
`tflint` skips — 1,788 pins in 54 test modules, 6 more than the 1,782 pins Piece 11B.3 measured — in 244.57 s. Read
through the per-module collection totals: `tests/test_sanity_gate.py` 118 (114 before), `tests/test_round_trip.py` 35
(34 before), `tests/test_data_file_gate.py` 29 (28 before). No committed golden moved.
