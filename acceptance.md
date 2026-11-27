# Acceptance criteria

This file carries the record for the current task. Piece 14A.4 is committed at `2826d7e`, so its record lives in the
git history and is not restated here. The epic records stay as pointers: Epic 13's rules are in
`docs/INPUT_SHAPES.md`, and Epic 14's criteria are not restated here because that epic still has open pieces in
`to-do.md` and its decisions are in `docs/IMPORT_BINDING.md` §2.

## Piece 14B.1, the device serial fact for a bound unit
(main, the current task, 2026-11-27)

Decision 6 of `docs/IMPORT_BINDING.md` §2 is the decision this piece needs. It was taken 2026-11-26 by the
operator, and the four answers it took are recorded below before any code is written. The live-target half of the
decision stays out of this piece: the serial a live target states is a fact in `backlog.md`, no code path in this
piece reads a network, and no pin calls one, so a run with no network passes CI.

### Decision 6, as taken

1. **The source is the state document, read as a reference source.** The serial for an entry is the value the
   state document holds for it, read through `src/state_coverage.py`, the one state reader. The provenance record
   names that document, so `docs/ARCHITECTURE.md` §3.3 reaches the fact with no change. No new source kind, and no
   new row in `src/input_shapes.py`: the document reaches the run through the door the state read already uses.
2. **Block and id state the same fact through `src/resource_mapping.py` `VALUE_VARIABLES`.** The table already
   states the `ngfw_device` row as a variable, so it gains nothing (measured 2026-11-27, which corrects the plan's
   "the table gains the `serial` row"), so the block prints the variable reference for it and the id states the value
   the run read from the state document. The table is the only place that decides the shape, the comparison reads it
   through `sanity_checks.location_agrees`, and no second shape rule or name list appears.
3. **A run that reads no state document declares no serial.** It reads no entry, so it holds no value, the
   declaration set holds no serial name, and the ids for entries that need one stay the placeholders the report
   already names for the operator. A run with no state source writes the bytes it writes today.
4. **A bound unit with no serial for an entry that needs one is a report-only finding.** No sixth console kind, so
   `tests/test_container_coverage.py::test_the_console_line_shape_is_stated_in_one_place` is unchanged and its kind
   list stays at five. The fact names an operator action, so by `docs/ARCHITECTURE.md` §4.6 rule 1 it is WARN and
   the exit code stays with the rules that read the files. The lines are grouped by the F3.9 rule, and the identity
   is read through `state_coverage.ownership_key`, so no second identity key appears.

### The reading rule, in its owner

The rule lands in `src/state_coverage.py` as rule 7, stated once there:

1. The serial for a state entry is the value the state document holds for it in its `location` block, read through
   the location walk rule 2 already states, not through the property table. The module names the value once:
   `STATE_SERIAL_KEY` is the field the document declares it with and `STATE_SERIAL_FACT` is the §2.2 fact that field
   fills through `STATE_SCOPE_KEYS`. `serial_of` answers the value, or the empty answer for an entry that holds none.
2. Measured 2026-11-27, which corrects the plan's "the name joins `STATE_IDENTITY_KEYS`": the serial is read inside
   the `location` block, and `location` is already an identity key, so `STATE_IDENTITY_KEYS` gains no key, the
   property scan reads no property for the serial, and no drift line can compare it.
3. An entry needs the serial when the location the document holds for it places it in a sub-block that declares the
   field, which `entry_needs_serial` answers through `LOCATION_SCHEMA`, so this piece states no name list of its
   own. Measured 2026-11-27: the answer is the entry's own location, so a `shared` entry needs none, and a sub-block
   the row declares for another fact declares no field and needs none.
4. `unit_manifest.FACT_KEYS` holds no serial, because `FACT_KEYS` already holds the fact `STATE_SERIAL_FACT` names,
   so `FACT_KEYS` gains no key and `ownership_key` stays the only identity the finding reads.
5. The module states no reader, path rule, row shape, unit rule, or severity rule of its own: the bound unit is
   read through `unit_manifest.mode_of` and `marked_units`, and the line shape stays in this module as the state
   report shapes already do.

### The block, the id, and the pair

1. `src/import_blocks.py` states the id shape. Measured 2026-11-27, which corrects the plan: `build_id` already
   writes the location object as the block states it, so the value rides inside it and the module gains nothing, the
   pinned provider docs example stays byte for byte, and `decode_id` declares no field for the serial. `row` takes
   the value from the caller and reads no state, so the module holds no state rule.
2. The block prints the shape the table states for the name, through the print site `printed_value` already uses,
   and the pair is recorded through `site_data.record_pair`, the one statement of the rule that one name names one
   source. The `.tfvars` writer prints the value from the data, so the declared serial has a consumer: the block
   prints the reference. Measured 2026-11-27: the run records the pair for the value it read, and prints no line for
   a name it read no value for.
3. The gate reads the printed fact and the id value as one fact through the table. Measured 2026-11-27, which
   corrects the plan: `sanity_checks.field_agrees` does not exist, and `sanity_checks.location_agrees` is the one
   comparison the location rule already uses, so it gains no branch of its own.

### The finding

1. One line per entry that needs a serial and has none, inside its own report section, printed only when the run
   read a state document and marked a unit, so a run that reads no state document and a run that declares no pair
   write the report bytes they write today.
2. The line names the unit, the identity through `ownership_key`, and the fact, in the shape the state report
   shapes already use: the identity is read through the one key rule, and the group is the F3.9 scope rule.
3. The gate reports nothing for the fact, so the exit code is decided by the rules that read the files. The console
   prints no line for it.
4. Two runs on the same arguments and the same bytes write the same report bytes.

### Pins, one per rule

New pins, in `tests/test_state_coverage.py` group 9 (the module held eight groups before the piece):

1. `test_the_serial_is_read_through_the_entry_shape_and_the_one_name` — the location walk carries the value, the
   module names it once, and the property scan reads no property for it.
2. `test_the_block_and_the_id_state_the_same_fact_through_the_shape_table` — the block prints the reference, the id
   states the value the run read inside its location object, and the gate reads the two as one fact through
   `VALUE_VARIABLES` and `location_agrees`.
3. `test_a_run_that_reads_no_state_document_declares_no_serial_and_writes_the_bytes_it_writes_today` — the ids for
   entries that need one stay placeholders.
4. `test_a_bound_unit_with_an_entry_that_needs_a_serial_and_has_none_reports_one_line` — one line per entry, read
   through `ownership_key` and `marked_units`, grouped by the F3.9 rule.
5. `test_the_serial_finding_does_not_move_the_exit_code_and_prints_no_console_line` — the gate answers nothing for
   it and the console keeps the five kinds.
6. `test_the_serial_fact_adds_no_source_kind_and_no_input_shape_row` — the state document is read through the door,
   and `SHAPE_TABLE` gains no row.
7. `test_the_serial_fact_names_no_second_identity_key_and_no_new_fact_key` — `FACT_KEYS` holds no serial and the key
   rule is read through its owner.

New pins, in `tests/test_reports.py`: the section prints only when the run read a state document and marked a unit,
read as three runs on the same content so the run that read a document and declared no pair is its own run, and it
is byte-identical between two runs on the same arguments. New pin, in `tests/test_variables.py`: the declaration set
holds the serial name only for a run that read a value for it, through the table.

Pins that measure names and therefore move in the same commit: `tests/test_reports.py::
test_the_unit_section_prints_after_the_sections_the_report_rule_already_orders` reads the new heading through its
owner. Measured 2026-11-27: `tests/test_import_blocks.py` does not move, because the id shape gained no field, and
`tests/test_variables.py::test_the_provider_block_prints_only_the_names_the_table_states` does not move, because the
table gained no provider argument. The console-shape pin is not touched.

Shared facts go in `tests/conftest.py`, because more than one test module reads them; no test module imports
another test module. The pair content is written there as `serial_content`, and the three runs on it as `serial_run`,
because three test modules read the same runs. The committed state fixture holds no entry that needs the serial
inside a unit a declaration can mark, so the finding pins write their own content, and no committed golden byte
moves.

### Documents that move in the same commit

1. `docs/IMPORT_BINDING.md` §2 decision 6, recorded as taken with the date and the four answers; §1 fact 3 for the
   device fact; §4 for the live half that stays in `backlog.md`.
2. `docs/ARCHITECTURE.md` §4.8 for the value that reaches an id through the table, and §3.2 for the third fact kind,
   its line shape, its printing condition and its pins, which the report rule owns. Measured 2026-11-27, which
   corrects the plan's "§3.2 is not touched": §3.2 owns the report sections, so the new section and its line shape
   are stated there, and §3.3 keeps the provenance record unchanged because the document reaches the run through the
   door the state read already uses.
3. `docs/CODEBASE_ASSEMBLY.md` §9 rule 8, for the row the table already states and the declaration half, and its pin
   list. Measured 2026-11-27, which corrects the plan's "§10 for the report section that names the fact": §10 owns
   the commit action, so the report section is stated in `docs/ARCHITECTURE.md` §3.2 instead, and §10 does not move.

### Gate measurement

Run at the end, single-threaded in one process with no parallel plugin:

1. `ruff check .` and `ruff format --check .` clean.
2. `python3 tools/check_documents.py` reports no finding.
3. `python3 -m pytest -p no:cacheprovider` passes. Record every count that moves, including whether any committed
   golden byte moves. `tflint` is absent on this machine, so its four pins skip, as they did at the baseline.

### Out of scope

Decisions 5, 7, 8 and 9 of `docs/IMPORT_BINDING.md` §2: no piece writes anything for them, and the four
`*_policy_rules` types keep writing no import block. The live-target serial stays in `backlog.md`. The completeness
half of the bound-unit rule is decision 5's.

### Baseline

From `agent-status.md` Piece 14A.4, measured 2026-11-26: 1,887 passed plus 4 `tflint` skips, 1,891 pins in 55 test
modules; `ruff check .` and `ruff format --check .` clean on 113 files; `python3 tools/check_documents.py` reports no
finding. `tests/golden` holds no data file, only 87 `.tf` files, so this piece moves no committed golden byte unless
a report or `.tf` shape changes. No fixture is added, so the prose corpus counts in `tests/test_build_kitchen_sink.py`,
`tests/test_api_requests.py`, `tests/test_policy_order.py`, `docs/ARCHITECTURE.md` §5.1 and the pair-read facts in
`backlog.md` do not move.
