# Acceptance criteria — the certificate gate rule (task for this commit)

Scope: `sanity_checks.check_certificate_blocks`, its `CHECK_ORDER` position, the pins in
`tests/test_certificate_blocks.py`, and the documents that name the rule. The gate writes no file, so no
golden moves. The certificate feature closes with this piece; the facts that stay open stay in `backlog.md`.

## 1. The rule reads the block through the readers that already exist

1.1 One block reader (`sanity_checks.blocks`) serves the rule, as it serves every block kind the gate
reads, and one field reader (`import_blocks.fields_at`) reads the fields. The rule writes no reader of
its own, so no second reader appears.

1.2 The rule reads the fields at the block's own level and not the `location` sub-block: `location` is the
placement fact, and `location_present` is the rule that asks for it.

1.3 The type to row lookup is `resource_mapping.CERTIFICATE_TYPES` read the other way, so the rule states no
resource type of its own. `resource_mapping.certificate_path` is that lookup, in the shape `filter_path`
already states.

1.4 The rule states no field name of its own. The entry name comes from `entry_coverage.name_field` (the one
naming rule for the field that carries an entry name), the choice comes from the row's `selects`, and the
sensitive marks come from the row's `sensitive`. The rule uses no new shape word: `one_of` keeps reading as
`object`, so `SHAPE_WORDS`, `SHAPE_TO_SCHEMA`, `SHAPE_READS_AS` and `SHAPE_LEVELS` do not change.

1.5 `tests/test_protocol_object.py::test_the_table_is_the_only_shape_owner` reads the certificate rule as an
owner, so a field name written as a string constant inside it is a finding.

## 2. Findings, each a FAIL

The rule reports five findings, each a FAIL, and adds no WARN and no exit-code rule. The exit code follows
the findings through the rule `tests/test_sanity_gate.py` already pins.

2.1 A level the table states no row for, a field the row does not declare, or a value whose shape the
reader reads differently from the shape the row states.

2.2 The block states no entry name. A certificate entry has no name a reference resolves, so the
`references` rule cannot reach it, and the field rule reads only the fields the block states, so an absent
name is read by the name rule and not by the field rule. The name is read first, because the block states it
before its content, which is also the order the emitter prints.

2.3 `local` states exactly one of the keys its row selects. This is the choice rule `selects` already states
(F7.12), read through `_shape_choice_findings`, so no new choice rule appears. A `local` that states both
alternatives is a finding, and a `local` that states none is a finding.

2.4 A field the row marks `sensitive` prints as `var.<name>`, never as a quoted value. The gate reads the
row's `sensitive` set, and `tests/test_protocol_object.py::test_the_sensitive_rows_are_the_reference_only_names`
pins that set against `resource_mapping.VALUE_VARIABLES`, the table the emitter reads at the print site. The
name is the §5 name of the entry that holds the field, read through `naming.py`, because a field cannot name
itself. The literal half is pinned by
`tests/test_robustness.py::test_a_parsed_secret_never_reaches_a_generated_file`.

2.5 An element inside the profile's `certificate` `[` container states the name the row reads for it.

## 3. Gate order, determinism, and no false positive

3.1 `certificate_blocks` sits after `filter_blocks` and before `references`, because the three shape-table
rules are grouped together in the report order.

3.2 The corpus and `tests/fixtures/certificates.xml` trip no finding, so the gate reports PASS for the new
check on every fixture.

3.3 The report is byte-identical between two runs on the same input, and a finding names the unit directory
the file is in, through the reader that already keys the `.tf` set.

3.4 No golden moves, because the gate writes no file.

## 4. Documents

4.1 `README.md` names the check in the gate table, `docs/ARCHITECTURE.md` §4.6 states the rule and names the
test file, and `sanity_checks.py` states the check in its own table.

4.2 The tracking markdown closes the piece: `to-do.md` loses the completed pieces, `backlog.md` loses the
findings this commit resolved and keeps the facts that stay open, `agent-status.md` names the position and the
next feature.

## 5. What this commit does not do

5.1 No change to a shape word, no change to `VALUE_VARIABLES`, and no data-file rule for a certificate row.

5.2 The facts that stay open in `backlog.md`: the EDL `certificate_profile` field is a plain string, so it
records no reference edge; `panos_certificate` is a data source with no resource; a certificate entry the
export places in a device group prints the `Shared` template placeholder, because no certificate type declares
a `device_group` sub-block; a `local` that states both alternatives is refused by `terraform validate`, not by
the schema JSON, so the choice is gate data read from `selects`.

## Result (measured 2026-11-05)

All criteria hold. `ruff check .` is clean and `python3 -m pytest` passes 1533 tests. No golden moved, because the
gate writes no file.

1.1 `check_certificate_blocks` calls `sanity_checks.blocks` and `import_blocks.fields_at` and writes no reader or
helper of its own, pinned by `tests/test_certificate_blocks.py::test_the_rule_reads_the_block_through_the_gate_readers`.

1.2 The rule reads the fields at the block's own level and excludes `location`, pinned by
`::test_the_gate_does_not_read_the_location_sub_block`.

1.3 `resource_mapping.certificate_path` is the lookup, read through `CERTIFICATE_TYPES`, pinned by
`::test_the_type_row_lookup_is_the_table_read_the_other_way`.

1.4 No shape word changed. `SHAPE_WORDS`, `SHAPE_TO_SCHEMA`, `SHAPE_READS_AS` and `SHAPE_LEVELS` are unchanged:
`one_of` keeps reading as `object`. The rule states no field name the table declares, which
`::test_the_entry_name_is_read_through_the_one_naming_rule` pins, and the only name it states is the placement
sub-block.

1.5 `tests/test_protocol_object.py::test_the_table_is_the_only_shape_owner` now reads three tables and names the
certificate rule as an owner.

2.1–2.5 One test per finding in `tests/test_certificate_blocks.py`: the undeclared field, the value read as
another shape, the block states no entry name, the choice at the level the walk enters (two keys, none, and a key
the row does not select), the `sensitive` field printed as a literal, and an element inside a `[` container that
states no name. Every finding is FAIL, and the rule produces no WARN.

3.1 `CHECK_ORDER` puts `certificate_blocks` after `filter_blocks` and before `references`; the report names the
checks in that order, pinned by `::test_the_gate_reads_the_run_and_reports_nothing` and by the order pin in
`tests/test_data_file_gate.py`.

3.2 The certificate fixture and every fixture trip no finding: the rule reports nothing on the run, the report
line reads `certificate_blocks PASS`, and the whole run reports
`Result: PASS (0 FAIL, 0 WARN)`.

3.3 Two runs on the same input write the same report bytes (`::test_the_report_is_byte_identical_between_two_runs`),
and a finding names the unit directory the file is in (`::test_a_finding_names_the_file_and_the_line_the_reader_read`).

3.4 No golden moved.

4.1 `README.md` names the check in the gate table, `docs/ARCHITECTURE.md` §4.6 states the rule and §4.11 names the
module and the test file, `docs/README.md` names the owner for the certificate shape, and `sanity_checks.py` states
the check in its own table. `docs/RESOURCE_MAPPING.md` no longer says the rule is unwritten.

5.1 One table change: `certificate_profile/certificate` is the entry-list row, so its shape word is `string_list`,
the word the reader reads for a `[` value, as the filter table's entry rows state it. The rule found the mismatch —
with the row read as `object`, the profile block a real run wrote was reported as an object value. The field set
and the `sensitive` flags are unchanged, so the provider pin and the goldens did not move.
