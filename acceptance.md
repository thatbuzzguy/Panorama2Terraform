# Acceptance criteria — the destination a report-only entry answers (task for this commit)

Scope: `entry_coverage.EntryLedger.destination`, the `report_only` branch inside `mark`, the report-only call
site in `panorama_to_terraform.parse_address_objects`, the report line and the counts that read the
destination, and the pins that read the destination. The fix writes no block, so no `.tf` golden moves. This is
the design record for the implementing agent: it states where the destination is decided, what the report line
says, what the cross-check counts, and which pins move. The facts that stay open stay in `backlog.md`.

The rule is one place. `mark` records what the parse method took and only the destination the caller states;
the destination itself is answered by `EntryLedger.destination`, which every reader of a destination already
calls. No module gets a second destination rule.

## 1. One place answers the destination

1.1 `EntryLedger.destination` is the only place that decides a destination, in this order: the per-entry fact
on the recorded object (`report_only` answers `report`), then the destination `mark` recorded, then the
container table row. `mark` keeps recording what the parse method took and the destination the caller states,
and the `report_only` branch inside `mark` is removed. Pinned by the existing
`tests/test_entry_coverage.py::test_a_row_names_the_destination_the_mark_records` (no entry fact, so the mark
answers), and rewritten as `::test_report_only_entry_destination_is_report`, which marks first with the table
row's destination, then adds `report_only` through the recorded object, then reads `destination` and gets
`report`.

1.2 The per-entry fact is read from the recorded object at read time, so the order of `mark` and the field
cannot change the answer. New pin:
`tests/test_entry_coverage.py::test_the_destination_is_read_from_the_recorded_object_after_the_mark`, with the
same fixture, read in the order the parse method works: mark, then the field, then the destination. The
decision it depends on is already pinned by
`::test_fields_added_through_the_recorded_object_are_recorded`, which states that a field added after the mark
is still the recorded fact. Pinned also by the `skipped` half, which keeps its answer through the second step:
`::test_skipped_entry_destination_beats_the_table_row`.

1.3 The fact is read through `RecordingDict.value()`, not `get()`, so the destination decision records no
property use. The captured part of a report line stays a measurement of output reads, so
`::test_fields_added_through_the_recorded_object_are_recorded` keeps its list, and the property scan's finding
set does not move: `tests/test_property_coverage.py::CORPUS_FINDINGS` keeps
`('address', 'Country-US', 'panos_address', ('description',))` for both fixtures. Measured before and after:
`declared_type, device_group, name, other, report_only, vsys` for all three entries. Pinned by
`tests/test_ownership.py::test_the_scan_read_is_not_an_output_read`.

1.4 No second destination rule: `row_for`, `matrix_row_for`, the report line, the gap section, the ownership
row, and `sanity_checks.check_round_trip` all read `EntryLedger.destination`. The property scan scope stays the
container row read through `matrix_row_for` (F4.4), so the destination rule is not the scan scope and the
destination is not a scope. Pinned by
`tests/test_property_coverage.py::test_scan_scope_is_the_entries_a_matrix_row_covers`, which does not move.

## 2. The report line

2.1 The three report-only entries in the corpus answer `report`: `address/Ext-Dynamic`
(`tests/fixtures/address_objects.xml`, source line 30), `address/Country-US` (the same fixture, line 34), and
`address/Country-US` (`tests/fixtures/kitchen_sink.xml`, line 52). Measured: the destination column changes
`emitted` → `report` on those 3 lines and on no other line. `examples/sample_panorama_config.xml` holds no
report-only entry, so the sample run's report does not move.

2.2 The summary counts move, because they count the destination: `address_objects.xml` emitted 7 → 5 and
report 0 → 2; `kitchen_sink.xml` emitted 62 → 61 and report 8 → 9. The detail column does not move, because
the detail for a report entry is the container row's `row_detail` (`panos_address`), not the destination. The
gap section does not move, because `report` is not in `GAP_KINDS`.

2.3 No `.tf` file moves: measured byte-identical for the three runs, so `tests/test_golden_files.py` and
`tests/test_ownership.py::test_the_goldens_are_byte_identical` do not move. The golden set holds no report, so
"golden report bytes" here means the pinned report lines in 2.1, the counts in 2.2, and the pins in 3 and 4,
not a golden file.

2.4 The pins that name the entries by name keep their shape: `tests/test_edge_cases.py` keeps both names in the
report and out of the `.tf` text, and `tests/test_real_or_report.py` keeps `Country-US` in the report. Neither
reads the destination column, so neither moves.

## 3. The cross-check count

3.1 `check_round_trip` counts the entry side through `row['destination']`, so the three report-only entries
leave the count. The comment that states the measured fact (`report_only` is recorded after `mark`, so a
report-only address answers `emitted`) is replaced by the rule. Pinned by
`tests/test_round_trip.py::test_an_entry_the_run_reports_is_not_counted`, which must read a run that still
disagrees, so the planted `panos_address` block for `Country-US` becomes the whole fact:
`('panos_address', 'shared_45ca31c3', 5, 6)`. No fixture is added, because
`tests/test_build_kitchen_sink.py` pins the fixture count.

3.2 Measured corpus: 22 findings on 10 fixtures → 20 findings on 9 fixtures.
`tests/fixtures/address_objects.xml` leaves `CORPUS_GAPS`, because the run reads clean after the fix, and
`test_the_rule_reports_nothing_across_the_corpus` moves it to the clean branch. `kitchen_sink.xml` keeps 4
findings and loses `('panos_address', 'shared_45ca31c3', 61, 60)`, so its positions move from 16, 3, 17, 85, 95
to 16, 17, 85, 95.

3.3 `CATEGORY_COUNTS` moves: 'entry side counts more' 5 → 3, 'block read for a property level' 16 (unchanged),
'entry writes more than one block' 1 (unchanged). The three survivors name the shape the rule cannot join:
`dependency_wiring.xml` (`panos_address` 3 against 2), `interfaces_other.xml` (`panos_aggregate_interface` 2
against 1), `kitchen_sink.xml` (`panos_aggregate_interface` 2 against 1). So the "no v2 attribute" shape has no
measured instance left, and `backlog.md` keeps it open with the config entry inside a stack.

3.4 `test_the_rule_reports_the_gaps_the_corpus_contains` changes only its numbers: 22 → 20, 10 fixtures → 9,
and the 'entry side counts more' count 5 → 3. The categories and the shape of the pin stay, because the pin
reads what the rule reports rather than what a document claimed.

3.5 `GAP_FIXTURE` in `tests/test_round_trip.py` must name a fixture the rule still reports, because
`address_objects.xml` reads clean after the fix. It moves to `interfaces_other.xml`, the surviving instance of
an emitted entry that writes no block (`ae1`, an aggregate group with no content the provider models). Measured
fact: `('panos_aggregate_interface', 'shared_45ca31c3', 2, 1)`, so the pinned counts in those pins move from 7
and 5 to 2 and 1, and the no-block-read pins keep their shape through `check_round_trip({}, ledger)`: 2 against
0 on `shared_45ca31c3/interfaces.tf`. The 22 pins that read `GAP_FIXTURE` keep their structure; only the
fixture, the row name and the two counts move.

3.6 The severity stays WARN, and the exit code stays with the rules that read the files, so
`tests/test_round_trip.py::test_the_cross_check_finding_is_a_coverage_fact_not_a_broken_output` keeps its
decision and gains the new numbers. The sample run stays clean (`Result: PASS (0 FAIL, 0 WARN)`), so
`test_not_run_does_not_change_the_exit_code` and
`tests/test_sanity_gate.py::test_console_summary_reports_the_result` do not move.

3.7 `tests/test_sanity_gate.py::test_kitchen_sink_gate_passes_with_validate` moves: 6 WARN → 5 WARN, and the
`round_trip` block 5 findings → 4. `tests/test_data_file_gate.py` does not move, because the rule reads no
report and no data file.

## 4. Pins that move (measured)

Measured with `python3 -m pytest` before the fix, against the fix applied in place: 21 pins fail, 20 in
`tests/test_round_trip.py` and 1 in `tests/test_sanity_gate.py`. Each names the number or the fixture the fix
moves, so the implementing agent changes the pins, not the rule:

- `tests/test_round_trip.py`: `test_the_rule_reads_the_block_set_through_the_gate_reader`,
  `test_the_entry_count_is_read_through_the_ledger_and_the_scan_scope_rule`,
  `test_the_unit_is_read_through_the_one_unit_rule`,
  `test_the_rule_reports_not_run_when_the_caller_passes_no_ledger`,
  `test_a_count_that_does_not_agree_is_one_finding_per_unit_and_row`, `test_the_rule_names_no_entry`,
  `test_a_finding_names_the_file_and_the_line_the_reader_read`, `test_the_rule_states_no_type_of_its_own`,
  `test_the_rule_detects_a_block_with_no_entry`, `test_the_rule_detects_an_entry_with_no_block`,
  `test_the_rule_reports_an_emitted_entry_that_writes_no_block`, `test_a_tf_file_at_the_root_names_no_unit`,
  `test_an_entry_the_run_reports_is_not_counted`, `test_a_kind_that_writes_no_block_is_not_counted`,
  `test_no_other_block_kind_enters_the_count`, `test_the_rule_states_no_field_name_of_its_own`,
  `test_the_rule_reads_no_file_name_rule`, `test_the_rule_reports_nothing_across_the_corpus`,
  `test_the_rule_reports_the_gaps_the_corpus_contains`,
  `test_the_cross_check_finding_is_a_coverage_fact_not_a_broken_output`.
- `tests/test_sanity_gate.py`: `test_kitchen_sink_gate_passes_with_validate`.
- `tests/test_entry_coverage.py`: `test_report_only_entry_destination_is_report` is rewritten to read the
  destination after the field was added through the recorded object, and the new pin in 1.2 is added. It passes
  today only through the branch in `mark`, so the rewrite is what holds the rule.

## 5. Documents

5.1 `docs/ARCHITECTURE.md` §1.1 module-owner row for `entry_coverage.py`: the destination is answered in one
place, in the order 1.1, and `mark` records the destination only when the caller states it.

5.2 `docs/ARCHITECTURE.md` §3.2 destination bullet: the mark override becomes the ordered rule, and the
sentence that names `report_only` content as `report` names the recorded object rather than the mark branch.

5.3 `docs/ARCHITECTURE.md` §4.6 and `docs/COVERAGE_MATRIX.md` §1: the cross-check reads the destination per
entry, so an entry the run reports enters no count. `docs/README.md` names `entry_coverage.py` as the owner of
the destination rule.

5.4 `README.md` gate table: the round-trip row states the entry side through the destination rule, so the
report entry is not counted.

5.5 `backlog.md`: the `report_only` timing fact moves out of the backlog into this task, and the 'entry side
counts more' entry moves from 5 findings to 3 with the surviving instances named. The open facts that stay:
the four `*_policy_rules` types, a config entry inside a stack, the EDL `certificate_profile` field, the
profile-name report column, the two `.github/` template files outside the indexes.

5.6 `to-do.md` keeps the implementation pieces, and `agent-status.md` names the position and the next step.

## 6. What this commit does not do

6.1 `parse_address_objects` is not restructured. `mark` still records what the parse method took, and the
caller still sets the `report_only` fact through the recorded object. No new `mark` argument, no new key, no
`destination='report'` at the address call site, because that would restate a fact the entry already holds.

6.2 No property-scan scope change, no new destination kind, no new shape word, no change to a container row,
no change to `GAP_KINDS`, no change to `CHECK_ORDER`.

6.3 No fixture is added and no golden moves, because the fix writes no block. No report gains a section, so the
data-file counts do not move.

6.4 The cross-check stays a WARN, and the gate's boundary exception stays the run's ledger.

## Result

Measured with the fix applied. `ruff check .` is clean, `python3 -m pytest` passes 1567 pins with no skip, and
`git status` names no `.tf` golden: the commit holds `src/entry_coverage.py`, `src/sanity_checks.py`,
`tests/test_entry_coverage.py`, `tests/test_round_trip.py`, and `tests/test_sanity_gate.py`.

### 1. One place answers the destination

1.1 `mark` records only the destination the caller states, and `destination` answers in the order 1.1.
`tests/test_entry_coverage.py::test_report_only_entry_destination_is_report` measures the mark answering
`emitted` with no fact on the recorded object, then `report` after the fact is added through that object. The
pin this document named for the second step, `::test_a_row_names_the_destination_the_mark_records`, does not
exist; the second step is held by `::test_skipped_entry_destination_beats_the_table_row` and the third by
`::test_scope_entry_destination_comes_from_the_table_row`, both unchanged.

1.2 The new pin `::test_the_destination_is_read_from_the_recorded_object_after_the_mark` measures `report` read
in the order mark, field, destination, and measures the same answer for the same entry read in the other
order, so the call order states nothing.

1.3 Inside a recording, the read through `value()` leaves `used_keys() == ('name',)`, and the same key read
through `get()` records `('name', 'report_only')`, so the decision records no property use.
`tests/test_property_coverage.py::CORPUS_FINDINGS` keeps `('address', 'Country-US', 'panos_address',
('description',))` for both fixtures, and `used_keys()` reads `declared_type, device_group, name, other,
report_only, vsys` for the three report-only entries before and after. `::test_fields_added_through_the_recorded_object_are_recorded`
keeps its list, and `tests/test_ownership.py::test_the_scan_read_is_not_an_output_read` is unchanged.

1.4 `tests/test_property_coverage.py::test_scan_scope_is_the_entries_a_matrix_row_covers` is unchanged: no
destination kind is in the scan scope, and no count row is named through the destination rule.

### 2. The report line

2.1 The three lines move from `emitted` to `report` and no other line moves: `address/Ext-Dynamic` and
`address/Country-US` in `address_objects.xml`, and `address/Country-US` in `kitchen_sink.xml`. The sample run
holds no report-only entry, so its report is unchanged (emitted 20, report 0).

2.2 Measured counts: `address_objects.xml` emitted 5, report 2; `kitchen_sink.xml` emitted 61, report 9. The
detail column reads `panos_address` for those lines, and the gap section is unchanged.

2.3 No `.tf` file moves, so `tests/test_golden_files.py` and
`tests/test_ownership.py::test_the_goldens_are_byte_identical` are unchanged.

2.4 `tests/test_edge_cases.py` and `tests/test_real_or_report.py` are unchanged.

### 3. The cross-check count

3.1 The comment in `src/sanity_checks.py` states the rule. `check_round_trip` counts the entry side through
`row['destination']`, so the two report-only address entries leave the count and the fixture reads clean. The
pin reads the planted block fact `('panos_address', 'shared_45ca31c3', 5, 6)` as this document recorded, and no
fixture was added.

3.2 Measured: 20 findings on 9 fixtures; `address_objects.xml` is in the clean branch. `kitchen_sink.xml` keeps
4 findings at positions 16, 17, 85, 95.

3.3 `CATEGORY_COUNTS` reads 3, 16, 1 as recorded, and the three survivors are `dependency_wiring.xml` (3
against 2), `interfaces_other.xml` (2 against 1), and `kitchen_sink.xml` (2 against 1). The 'no v2 attribute'
shape has no measured instance left.

3.4 `test_the_rule_reports_the_gaps_the_corpus_contains` reads 20, 9 and 3.

3.5 Measured, in two places where this document recorded the wrong fact. The run names
`vsys1_b3e94a35` for `interfaces_other.xml`, because its entries sit under a declared vsys and not under
`Shared`, so the fact is `('panos_aggregate_interface', 'vsys1_b3e94a35', 2, 1)`. The no-block-read pins read 4
findings on `vsys1_b3e94a35/interfaces.tf`, not 1, because four rows in that unit have an entry side; the
aggregate row reads 2 against 0. The entry with no block of the row's type is `ae1.101`, not `ae1`: the
aggregate row counts `ae1` and `ae1.101`, and the one block it reads is `ae1`'s, because `ae1.101` wrote the
blocks the reader reads for the subinterface row.

3.6 The severity stays WARN, and the exit code stays with the rules that read the files: 2 findings on the gap
run, `Result: PASS (0 FAIL, 2 WARN)`. The sample run stays `PASS (0 FAIL, 0 WARN)`, so
`test_not_run_does_not_change_the_exit_code` and `tests/test_sanity_gate.py::test_console_summary_reports_the_result`
did not move.

3.7 `tests/test_sanity_gate.py::test_kitchen_sink_gate_passes_with_validate` reads `PASS (0 FAIL, 5 WARN)` with
4 findings in the `round_trip` block. `tests/test_data_file_gate.py` did not move.

### 4. Pins that moved, as the run measured them

22 pins moved: 21 in `tests/test_round_trip.py` and 1 in `tests/test_sanity_gate.py`. This document named 20
in `tests/test_round_trip.py`; the pin it did not name is `test_the_rule_prints_no_scan_line`, which moved
because the gate prints no property finding for `interfaces_other.xml`, so the half that says the scans that
print still print reads `address_objects.xml`, where the property scan reports 2 findings. Two pins moved only
after `GAP_FIXTURE` changed, not after the fix alone: `test_the_rule_reads_no_report_and_no_data_file` reads 5
`.tf` files instead of 3, and `test_the_rule_detects_a_block_with_no_entry` plants a block for a row the entry
side reads no row for in that unit, so its fact is `('panos_address', 'vsys1_b3e94a35', 0, 1)` and the two
findings the run reports stay.

Numbers that moved with the counts: 1.1 blocks 5 → 6 and findings 1 → 2; 1.2 entries 7 → 2 and the block side
read for that row and unit; 1.3 the run writes two unit directories, so the unit set is 2; 1.4 the report counts
read 5 `.tf` files for the new fixture; 1.5 `round_trip WARN (2)`; 2.1 kitchen facts 5 → 4 and units 3 → 2; 2.7
findings 2 → 3; 2.8 finding lines 1 → 2; 3.8 blocks 8 → 9 and 5 → 6, findings 1 → 2; 4.3 22 → 20, 10 → 9,
5 → 3; the severity pin reads 2 WARN and the resource count 6.

Shape that moved because the pin reads a set rather than one entry: `test_the_rule_names_no_entry` and
`test_the_rule_states_no_field_name_of_its_own` read the names the fact counts, because a one-character entry
name (`1`) and the scope name (`vsys1`) are inside the unit name the fact states;
`test_a_kind_that_writes_no_block_is_not_counted` states that the count reads only `emitted` rows, because the
`report` half now holds the report-only address entry inside `address`, the container the scope rule answers;
`test_a_finding_names_the_file_and_the_line_the_reader_read` states four whole-file positions for the gap unit.

### 5. Documents

Not written here. `README.md`, `docs/ARCHITECTURE.md` §1.1, §3.2 and §4.6, `docs/COVERAGE_MATRIX.md` §1,
`docs/README.md` and `backlog.md` (the `report_only` timing fact moves out, and the 'entry side counts more'
entry reads 3 with the surviving instances named) are the next step.
