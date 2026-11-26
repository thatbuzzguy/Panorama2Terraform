# Acceptance criteria

This file carries the record for the current task. Piece 13C.1 is committed at `cadd33a` and the writing-rules
piece at `077cdce`, so their records live in the git history and are not restated here. The epic records stay as
pointers: Epic 13's rules are in `docs/INPUT_SHAPES.md`, and Epic 14's criteria are not restated here because that
epic still has open pieces in `to-do.md` and its decisions are in `docs/IMPORT_BINDING.md` §2.

## Piece 14A.2, the mode as a manifest row field (main, the current task)

Decision 2 of `docs/IMPORT_BINDING.md` §2, taken 2026-11-25 by the operator: the mode is a field of the unit-manifest
row, read through `unit_manifest.parse_rows`, merged through `MULTI_RUN_CODEBASE.md` §2 rule 2, and read by the
`data_files` gate rule. One goal: record the decision as taken, land the field as data in the owner the decision
names, and add the pins that read it as data through that owner. Decision 3 is untaken, so the piece states no CLI
argument and no flag, so no run marks a mode: every row writes the answer a unit that states no mode has.

### Criteria

1. `docs/IMPORT_BINDING.md` §2 decision 2 records the decision as taken with the date, the owner it names
   (`unit_manifest.py`), the reader it names (`parse_rows`), the merge rule it reads through (`codebase_state.py`
   rule 2), the gate rule that reads it, and the empty answer for a unit the run did not mark, stated once, in the
   style of `provenance.py` rule 1. Decision 1 keeps what it settled (the pair, the level, and that it takes no
   field of its own) and its pin claims name the names the modules define after the rename.
2. Fact 11 states what actually moves: `tests/golden` holds no data file, so no committed golden byte moves; the
   pins that read the row shape state the shape, so they move in the same commit as the field. The pins named are
   `tests/test_unit_manifest.py::test_the_row_fields_are_the_declared_shape_in_order`,
   `::test_the_row_states_placement_through_the_fact_keys_it_already_reads`,
   `::test_a_row_that_is_not_the_declared_shape_is_refused` and `tests/test_data_file_gate.py::_manifest_row`.
3. The value pair is stated once, in `src/import_blocks.py` (`MODE_VALUES`, decision 1), and `unit_manifest.py`
   reads it through that owner instead of naming the values a second time. The empty answer is stated once, in
   `unit_manifest.py`, because that is the module that writes the row. If the field and the values are read through
   two different owners, the piece says which one and why. `tests/conftest.py` holds the pair as one definition read
   through its owner, because more than one test module reads it.
4. `src/unit_manifest.py` lands the field: `mode` enters `FIELD_ORDER` in the position the piece states with the
   reason, `build_rows` writes the empty answer for every unit, and `parse_rows` refuses a mode that is not a value
   of the pair or the empty answer, which the `data_files` gate rule reports as its finding 1 through
   `unit_manifest`. `src/import_blocks.py` states no field of its own and keeps the pair and the level as data.
5. `src/codebase_state.py` changes no code: rule 2 takes the whole row, so the merge carries the field with no key,
   shape or reader of its own. Only pins read it.
6. Pins that read the field as data through its owner: one in `tests/test_unit_manifest.py` (a row that states a
   value of the pair reads back as itself, and a mode outside the pair is refused), one in
   `tests/test_data_file_gate.py` (the gate reports a mode outside the pair as its finding 1 through
   `unit_manifest`, and a clean row with a mode reads as no finding), one in `tests/test_codebase_state.py` (the
   merged row carries the field and reads back as itself, and a row the second run did not build keeps the mode the
   record stated), and `tests/test_import_blocks.py` group 8 moves from "no shape names a field for the mode" to the
   shape that does, read through the pair's owner. Pins measure content or names, never document wording.
7. Documents that state the row shape move in the same commit: `docs/ARCHITECTURE.md` §3.4,
   `docs/CODEBASE_ASSEMBLY.md` §3 rule 4, the `docs/README.md` index line for Epic 14, and
   `docs/USAGE_GUIDE.md` §The unit manifest, which lists the fields and shows one row. `src/import_blocks.py` rule 7
   names `unit_manifest.parse_rows` as the reader of the pair.
8. Every count that moves is recorded, including whether any committed golden byte moves, measured against the
   baseline commit `723607b`: 1,865 pins in 55 test modules, 1,861 passed, the same 4 `tflint` skips, `ruff check .`
   and `ruff format --check .` clean on 113 files, `python3 tools/check_documents.py` with no finding. The gate runs
   single-threaded in one process with no parallel plugin: `ruff check .`, `ruff format --check .`,
   `python3 tools/check_documents.py`, `python3 -m pytest -p no:cacheprovider`. No document states a test count.
9. Out of scope for this piece: the declaration rule (decision 3, so no CLI argument and no flag), the report
   section (Piece 14A.4), the rule types (decision 7), the device fact (decision 6), the whole-block fact
   (decision 4), the completeness half (decision 5), the read-through order (decision 8), and permanence
   (decision 9). A mode value that no run can declare yet stays data that a hand-written record can state.
10. Standard library only, ASD-STE100 sentences, no marketing voice, no emoji. `agent-status.md`, `to-do.md` and
    `backlog.md` are updated, and the change is committed in conventional-commits style with the completion history
    in the body. Nothing is pushed.

### Definition of done

The decision is recorded as taken, the field is data in the owner decision 2 names, the values are stated once and
read through that owner, the empty answer is stated once, the merge and the gate read the field with no rule of
their own, the pins that read it as data pass, every pin that states the row shape moved in the same commit, every
count that moves is recorded, and the document checks report no finding.
