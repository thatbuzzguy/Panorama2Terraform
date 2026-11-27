# Acceptance criteria

This file carries the record for the current task. Piece 14A.3 is committed at `663245b`, so its record lives in the
git history and is not restated here. The epic records stay as pointers: Epic 13's rules are in
`docs/INPUT_SHAPES.md`, and Epic 14's criteria are not restated here because that epic still has open pieces in
`to-do.md` and its decisions are in `docs/IMPORT_BINDING.md` §2.

## Piece 14A.4, the whole-block fact and the report section that names the units a run marked
(main, the current task, 2026-11-26)

Decision 4 of `docs/IMPORT_BINDING.md` §2, taken 2026-11-26 by the operator, is the decision this piece needs. The
four answers it took:

1. **The name is `whole_block`**, the same name the record already carries in `docs/IMPORT_BINDING.md` §1 fact 6,
   so the decision does not rename anything.
2. **The owner is the property scan, `src/entry_coverage.py`**, the module that already answers the pair the fact
   compares: the properties a matrix row declares and the fields an output read on a run, per entry, through
   `property_findings` and `captured_fields`. This piece is the record's half that a matrix row can answer on its
   own, so the fact is stated in that module and read through it, not through the report.
3. **The severity is `WARN`**, by `docs/ARCHITECTURE.md` §4.6 rule 1: a fact that compares two sets is a coverage
   fact, and the exit code stays with the rules that read files. So the fact cannot move the exit code, and the
   existing exit-code pins hold.
4. **The print shape is the report**, through the report rule in `docs/IMPORT_BINDING.md` §3, the half that names
   the units a run marked plus which of their entries read as zero change. Because the fact prints in the report
   only, the §3.2 five-console-kinds rule is not touched: no sixth kind, and no console line for the fact. The
   console shape is pinned by `tests/test_container_coverage.py::test_the_console_line_shape_is_stated_in_one_place`,
   and that pin's kind list stays at five. The fact's severity is carried through the report shape by the existing
   §3.2 rule that a report line carries the kind the console would have printed, so the report line prints the fact
   name with its `WARN` severity without restating a severity rule.

### The pair the fact answers

Per entry, the scan answers which side of the pair it saw. When the output read nothing from a matrix row, the
answer already printed is `no output read` (F4.3). When the answer is that the whole row is present, the new fact
name `whole_block` is the pair answer, so one fact name is printed per entry, not two, and no entry prints both.

The pair the fact compares is the properties a matrix row declares (`property_fact`, from
`resource_mapping.PROPERTY_FIELD_MAP`) and the fields the run stored for the entry (`captured_fields`). It is
answered per entry, not per kind. A field that was stored empty or never stored is not in `captured_fields`, so the
blind side the F4.4 rule names is inherited: `test_property_scan_only_counts_fields_it_has_seen` is the pin that
records it, and the fact is stated as inheriting it rather than as answering it.

### The report section

1. **It prints only when the run marked a unit**, so a default run's report bytes are unchanged; a run with no
   marked unit prints nothing here, and the report bytes the pins read stay as they are.
2. **It names the unit through the record**, read through `unit_manifest` (`unit_name`, `facts_of`, and the row's
   `mode` field read through `parse_rows`), never through a report module: `unit_manifest.unit_writes_blocks` is the
   place a mode answer is decided, and the report reads it there, so the report states no mode value of its own.
   The unit set is read positionally through `unit_manifest.units` as the report already reads it in the Epic 11
   section, so the new section does not add a second path to the unit set.
3. **It groups by the F3.9 rule**, through `_report_scope_path` and `_group_by_scope`, inside its own heading and
   before the entry lines, consistent with `docs/MULTI_RUN_CODEBASE.md` §7's grouping rule.
4. **Per unit, and per matrix row inside a unit, one line** names the matrix row, the entry identity through
   `entry_identity`, and the pair answer. The `no output read` fact name is reused for a difference, so the section
   prints the two names the scan already answers, not new names.
5. **The sort is the report sort**, line then container then name, the rule `docs/ARCHITECTURE.md` §4.5 states, so
   the section is byte-identical between runs on the same input.
6. **The section's place in the report order** is after the Epic 11 unit section and before the entry lines, and the
   order pin `tests/test_reports.py::test_the_unit_section_prints_after_the_sections_the_report_rule_already_orders`
   is extended to hold it. `docs/ARCHITECTURE.md` §4.5 names the section order, so the section's position is added
   to the §4.5 list in the same commit.

### Pins this piece writes

`tests/test_property_coverage.py` gains:

- the fact name is data, read through the owner, so the pin reads `entry_coverage.WHOLE_BLOCK_FACT` rather than
  stating the name;
- the pair answer per entry, through the scan, so the pin reads the answer from the scan's own row shape and does
  not build a row by hand;
- the inherited blind side, pinned against the existing pin that records it;
- the severity, read through the §4.6 rule that a fact comparing two sets is a coverage fact, so the pin asserts the
  fact carries `WARN` and cannot move the exit code, consistent with the existing exit-code pin;
- the report-only print shape, through the existing single-statement pin for the report shape, so no new copy of the
  line shape appears.

`tests/test_reports.py` gains:

- the section names the units a run marked through the record, per unit and per matrix row inside a unit;
- the section is grouped by the F3.9 rule, and the grouping pin is extended to cover it;
- the section prints nothing when no unit is marked, so a default run's report bytes are unchanged, and the
  existing report-bytes pins still pass;
- the section order, through the pin that already holds the order;
- the exit code and the console output are unchanged by a marked unit;
- the section is byte-identical between two runs on the same input, through the existing report-shape pins.

`tests/conftest.py` holds the shared fact if a pin needs it, because no test module imports another test module.

### Documents that move in the same commit

- `docs/IMPORT_BINDING.md` §2 records decision 4 as taken, with the four answers.
- `docs/IMPORT_BINDING.md` §1 fact 6 and §3 keep the fact half and the report half, and now name the owner the
  decision picked, so the two halves point at one fact instead of at two places.
- `docs/ARCHITECTURE.md` §4.5 gains the section's position, and §3.2 gains that the fact is report-only so no sixth
  console kind exists; both already have pins, so the documents are moved against the pins, not the other way around.

### Measurement

The baseline this piece starts from, measured 2026-11-26: `1,874 passed + 4 tflint skips = 1,878 pins in 55 test
modules`; `ruff check .` and `ruff format --check .` clean on 113 files; `python3 tools/check_documents.py` with no
finding. Every count that moves is recorded at commit, including whether a committed golden byte moves.
`tests/golden` holds no data file, only the 87 `.tf` files, so no golden byte is expected to move; the corpus pins
that state printed sets in `tests/test_property_coverage.py`, `tests/test_reports.py`, and
`tests/test_round_trip.py::test_the_rule_reports_the_gaps_the_corpus_contains` are re-measured at commit and the
count recorded, including the fixture's `entry_type` and `matrix_row` values.

### Out of scope

- Decisions 5 to 9 of `docs/IMPORT_BINDING.md` §2: no code, no rule, and no test is written for any of them, in this
  piece or in any other part of it.
- The plan half of the zero-change fact, which no offline measurement can pin because a plan needs a device, and the
  live facts recorded in `backlog.md`. This piece lands the report half through the pins named above, so the
  `backlog.md` entry records the report half as landed and keeps the plan fact open.
- The console line for the fact, because the decision took the report shape.
- Any unit, entry or mode reading path that `unit_manifest` or the report already owns.

### Gate

Run single-threaded, one process, no parallel plugin, in the order `AGENTS.md` and the gate rule state:
`ruff check .`, `ruff format --check .`, `python3 tools/check_documents.py`, then
`python3 -m pytest -p no:cacheprovider`.
