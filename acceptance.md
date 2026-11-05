# Acceptance criteria — the round-trip cross-check (task for this commit)

Scope: `sanity_checks.check_round_trip`, its `CHECK_ORDER` position, the entry-side count it reads, the pins
in `tests/test_round_trip.py`, and the documents that name the rule. The gate writes no file, so no golden
moves. This is the design record for the implementing agent: it states what the rule reads, what the finding
is, and which types the rule can compare. The facts that stay open stay in `backlog.md`.

The rule is one gate rule: it compares the block set the reader read with the entry set the parse read, for
one unit and one coverage matrix row. It states no reader, no count, no scope, no kind, no type and no file
name of its own.

## 1. What the rule reads

1.1 One block reader serves the rule: `sanity_checks.blocks`, given `kinds = ('resource',)`. The rule writes
no reader of its own, so no second reader appears. It reads no field, because a count is a fact about blocks,
not about fields, so `import_blocks.fields_at` is not called by this rule. Pinned by
`tests/test_round_trip.py::test_the_rule_reads_the_block_set_through_the_gate_reader`.

1.2 The entry side is read through the run's ledger (`entry_coverage.EntryLedger`) and the one scope rule
`entry_coverage.matrix_row_for`, so no second scope rule appears. Each count comes from the module that owns
it: `entry_coverage` states the entries the parse read, and `sanity_checks.blocks` states the blocks the
reader read. `sanity_checks` compares the two counts and states no count of its own. Pinned by
`::test_the_entry_count_is_read_through_the_ledger_and_the_scan_scope_rule`.

1.3 The unit is read through `unit_manifest` (`facts_of`, `directory_name`, `units`), the one unit rule, so a
block's unit and its entry's unit land on the same directory and the rule states no second key or naming rule.
The block's unit is the directory part of the path the reader read. Pinned by
`::test_the_unit_is_read_through_the_one_unit_rule`.

1.4 The rule reads two things only: the `.tf` block set and the run's ledger. It reads no report and no data
file, so the data rule's input and the report bodies are unchanged. Pinned by the source slice in
`tests/test_data_file_gate.py` (its boundaries move to `check_data_files` … `check_round_trip` …
`check_control_chars`) and by `tests/test_round_trip.py::test_the_rule_reads_no_report_and_no_data_file`.

1.5 `run_checks` takes the ledger as an argument, and `main()` passes the run's ledger. A call with no ledger
reports the check as NOT RUN with a note, so a pin that reads only the output directory is unchanged, and a
real run reports the check as a rule that ran. Pinned by
`tests/test_round_trip.py::test_the_rule_reports_not_run_when_the_caller_passes_no_ledger`, and by the report
line in `tests/test_sanity_gate.py::test_gate_runs_and_writes_the_report`.

1.6 The rule reads the ledger for the source the run wrote output from, so a declared parent source (F5.4)
and a state source (F5.6) add no count: the run writes no output from them. Pinned by
`tests/test_round_trip.py::test_a_second_source_adds_no_count`.

1.7 The report's two counts are unchanged — the `.tf` files the reader read, and the four records at the root
— and the cross-check is not a third count, so `tests/test_sanity_gate.py::test_console_summary_reports_the_result`
does not move. Pinned by the same test.

## 2. The finding

2.1 One finding per unit and per coverage matrix row where the two counts do not agree. The fact is the two
counts, and the rule names no entry: `docs/ARCHITECTURE.md` §3.2 owns one entry, and the gap section names the
entries that write nothing, so the gate cannot restate the per-entry report. Pinned by
`tests/test_round_trip.py::test_a_count_that_does_not_agree_is_one_finding_per_unit_and_row` and
`::test_the_rule_names_no_entry`.

2.2 The position is the position the reader read: the path from the codebase root, and the line of the first
block the reader read for that unit and row. When the reader read no block, the position is the file as a
whole (`line` 0), and the file is the unit directory plus the row's `output_file` read from the row, so the
rule states no file name of its own. Pinned by
`tests/test_round_trip.py::test_a_finding_names_the_file_and_the_line_the_reader_read`.

2.3 The fact names the row through `COVERAGE_MATRIX` (`row['resource']`), so no `panos_` name appears in the
rule as a string constant. Pinned by `tests/test_round_trip.py::test_the_rule_states_no_type_of_its_own`.

2.4 Both directions are findings, and each is a FAIL: a block the reader read that no entry produced (the
gate reads the files as the operator receives them, so a hand-written block is an input), and an entry the
parse read and modelled that has no block (the silent drop the cross-check exists for). The rule adds no WARN
and no exit-code rule: the exit code follows the findings through `tests/test_sanity_gate.py`. Pinned by
`::test_the_rule_detects_a_block_with_no_entry` and `::test_the_rule_detects_an_entry_with_no_block`.

2.5 The config entry inside a stack case is reported by this rule, because its report line names the entry as
`emitted` and the unit directory holds no block for it. No committed fixture shows one, so the corpus pin
still reports nothing, and `backlog.md` keeps the fact with this rule named as the rule that states it. Pinned
by `::test_the_rule_reports_an_emitted_entry_that_writes_no_block`, read from a hand-written case, and by
`backlog.md`.

2.6 Findings sort by (file, line, detail), the rule `check_data_files` already uses, so the report is
byte-identical between runs on the same files. Pinned by
`tests/test_round_trip.py::test_the_report_is_byte_identical_between_two_runs` and
`tests/test_sanity_gate.py::test_report_is_byte_identical_between_runs`.

2.7 A `.tf` file the reader read at the codebase root names no unit, so the rule states it as a count that
cannot be assigned, because `write_path.py` writes no `.tf` file in the root set. Pinned by
`tests/test_round_trip.py::test_a_tf_file_at_the_root_names_no_unit`.

2.8 The cross-check does not print a scan console line, because its fact compares two sets and the console
shape names one identity (`docs/ARCHITECTURE.md` §3.2). The four kinds that print do not gain one, and the
gate's own console summary prints the finding as it already prints every finding. Pinned by
`tests/test_container_coverage.py::test_the_console_line_shape_is_stated_in_one_place` and
`tests/test_round_trip.py::test_the_rule_prints_no_scan_line`.

## 3. Which types the rule can compare

3.1 The count scope is the property-scan scope, read through `entry_coverage.matrix_row_for`: only an
`emitted` container row names the entries an emitter writes a block for, so the rule states no kind list of
its own. Pinned by `tests/test_property_coverage.py::test_scan_scope_is_the_entries_a_matrix_row_covers` and
`tests/test_round_trip.py::test_the_count_scope_is_the_scan_scope_read_through_one_rule`.

3.2 The destination is read per entry through `EntryLedger.destination`, so an entry the run reports is not in
the count even when its container row is `emitted` — a `report_only` address is that case. Pinned by
`tests/test_round_trip.py::test_an_entry_the_run_reports_is_not_counted`.

3.3 A `nested-block` row writes lines inside a parent block, so its entry's count is not one block, and
`matrix_row_for` answers None for it, so the rule cannot compare it. Pinned by
`tests/test_round_trip.py::test_a_nested_block_row_is_not_counted`, read on
`tests/fixtures/interfaces_ethernet.xml` (`ethernet1/4.1`).

3.4 A `bookkeeping` row names no field and writes no block, so it is not counted: the fact its row records is
the relation between the entry and the container that lists it. Pinned by
`tests/test_round_trip.py::test_a_bookkeeping_row_is_not_counted`, read on
`tests/fixtures/multi_device_templates.xml`.

3.5 `count-only`, `inventory`, `skipped` and `unaccounted` write no block, so they are not counted; the report
section and the console line are the output for those entries, so the rule states nothing about them. Pinned
by `tests/test_round_trip.py::test_a_kind_that_writes_no_block_is_not_counted`.

3.6 The scope rows are in the count through the same rule, because the five scope containers and `variable` are
`emitted` rows that `matrix_row_for` answers. The rule names the row through `row['resource']`, so it states no
scope type of its own. Pinned by
`tests/test_round_trip.py::test_the_scope_rows_are_counted_through_the_same_rule` on
`tests/fixtures/scope_objects.xml`.

3.7 A matrix row that `matrix_row_for` can never answer is not a count row, because no entry maps to it:
`panos_device_group_parent` is that case, because one device-group entry feeds the scope block and the parent
record. The rule states no exception list; the pin lists the rows through `matrix_row_for`, the same rows
`tests/test_coverage_matrix.py` grounds by the table. Pinned by
`tests/test_round_trip.py::test_a_row_no_entry_measures_is_not_a_count_row`.

3.8 A `data` block, an `import` block, an `action` block and a `variable` declaration enter no count, because
a read-through name is not an entry the parse read (§4.7), an import block names an entry the run already
wrote a block for and `import_blocks` already reads it, an action names no entry and no row covers it (the
F5.5 decision), and `variables.tf` writes no block. The decision is the reader's `kinds` argument, not a list
the rule states. Pinned by `tests/test_round_trip.py::test_no_other_block_kind_enters_the_count`.

3.9 The rule reads no field, so it reads no name, so `entry_coverage.name_field` is not called: the count join
is the matrix row and the unit. If the rule ever names the field that carries an entry name, it must read it
through `name_field`, so no second naming rule appears. Pinned by
`tests/test_round_trip.py::test_the_rule_states_no_field_name_of_its_own`.

3.10 The rule checks no file name. The count is a fact about a unit and a row, so a block for a row written in
another file of the same unit is not a finding; `tests/test_golden_files.py` pins the file names. Pinned by
`tests/test_round_trip.py::test_the_rule_reads_no_file_name_rule`.

## 4. Gate order, determinism, and no false positive

4.1 `CHECK_ORDER` puts `round_trip` after `data_files` and before `control_chars`. The report order is the
order the rules read: the rules that state one fact about one block, then the rules that state a whole-file
text fact, then the rule that reads the records back through their modules, then the rule that compares the
block set with the run's ledger, then the byte rules, then the plan. The cross-check is the only rule that
reads two sets, so it sits after every rule that reads one set, and the two agreement rules stay together.
Pinned by `tests/test_round_trip.py::test_check_order_puts_the_cross_check_after_the_data_rule` and by the
order pin in `tests/test_data_file_gate.py`, which gains the name.

4.2 The report names the checks in that order, and the cross-check is a static rule, so `terraform` stays the
last result. Pinned by `tests/test_round_trip.py::test_the_report_names_the_checks_in_the_pinned_order`.

4.3 The corpus and `tests/fixtures/kitchen_sink.xml` trip no finding, so the gate reports PASS for the new
check on every fixture. Pinned by `tests/test_round_trip.py::test_the_rule_reports_nothing_across_the_corpus`.

4.4 The report stays byte-identical between two runs on the same input, and names no timestamp and no absolute
path. Pinned by `tests/test_sanity_gate.py::test_report_is_byte_identical_between_runs` and
`::test_report_names_no_timestamp_and_no_absolute_path`, and by
`tests/test_round_trip.py::test_the_report_is_byte_identical_between_two_runs`.

4.5 No golden moves, because the gate writes no file. Pinned by `tests/test_golden_files.py::test_golden_file_set_matches`.

4.6 The exit code follows the findings: a cross-check FAIL exits 1, a NOT RUN result changes nothing, and a
WARN cannot come from this rule. Pinned by `tests/test_sanity_gate.py::test_a_fail_finding_exits_non_zero` and
`tests/test_round_trip.py::test_not_run_does_not_change_the_exit_code`.

## 5. Documents

5.1 `README.md` names the check in the gate table, in the same report order, and names `tests/test_round_trip.py`
in the Testing list. The paragraph that says the gate reads the files gains the ledger as its one exception for
this rule, so it still states no count of the rule's own.

5.2 `docs/ARCHITECTURE.md` §4.6 states the rule, names the test file, and states the position. The
`sanity_checks.py` row in §1's module table states the gate's input as the files it wrote plus the run's ledger
for this rule, so the sentence "the gate reads the written files, not the generator's state" gains the
cross-check as its one exception.

5.3 `docs/COVERAGE_MATRIX.md` §1 gains one sentence: the cross-check reads the same scan scope through
`matrix_row_for`, so the rule about a read has one owner and one reader.

5.4 `docs/README.md` names the owner for the cross-check rule: `ARCHITECTURE.md` §4.6, and
`entry_coverage.py`.

5.5 `sanity_checks.py` states the check in its own table, in report order.

5.6 The tracking markdown closes the design piece: `to-do.md` keeps the implementation pieces as the next
agent's list, `backlog.md` keeps the facts that stay open and loses the round-trip half of the Deeper
post-run checks item, `agent-status.md` names the position and the next step. The `backlog.md` sentence that the
gate cannot see an entry that produced no file moves to §4.6, because the cross-check reads the ledger for that
case.

## 6. What this commit does not do

6.1 No new shape word, no new destination kind, no change to `VALUE_VARIABLES`, no change to a container row,
and no change to `CHECK_ORDER` beyond one name.

6.2 The rule writes no reader, no regular expression, no field rule, no file-name rule, no kind list, no type
list and no unit rule.

6.3 No report gains a section: the cross-check findings live in `SANITY_REPORT.txt`, so `CONVERSION_REPORT.txt`
bytes do not move and the data-file counts do not move.

6.4 The facts that stay open in `backlog.md`: the four `*_policy_rules` import position, a config entry inside
a stack, `tflint` integration, the six levels inside the filter rows' `match` and `set`, the state scan's
same-name comparison limit, and the matrix rows no entry measures.

## Result

Pending. The implementing agent fills this section with the measurements, one entry per criterion.
