# Acceptance — the gate for the rule row set (Epic 9, Piece 20, Phase 9D)

Criteria set 2026-11-19 for Piece 20: the gate reads the rule row set. Three parts, in the order the rules
state them:

1. `check_data_files` reads the rule data pair inside the unit directories the rows name, through the module
   that owns the row shape, and joins on `directory`. This closes the boundary `backlog.md` recorded at Piece 18:
   an out-of-shape row inside a unit directory reported nothing, because the data rule read only the four
   records at the codebase root.
2. `check_round_trip` counts the four rule matrix rows against the row set read through `rule_data.parse_rows`,
   and not against a block count. Piece 19 landed the half that reads the printed map's keys; this part reads the
   data form of the same rows, so the two forms of one row set are read by one shape rule.
3. One new block rule, `rule_blocks`, reads the iterated rule block against `resource_mapping.LOCATION_SCHEMA`:
   the block's name and its map name, the field list, the body fields, one block per rule type per unit, and each
   map entry against the rows `parse_rows` reads.

The cross-check half of this phase landed in Piece 19 and is not restated here. Piece 21 re-measures the goldens
and the pins that name the printed rule output as a whole.

Owners this piece reads and does not restate: the row shape and the three forms through `rule_data`
(`RULE_ROW_FIELDS`, `parse_rows`, `render_csv`, `data_file`, `printed_file`, `locals_name`, `printed_entries`);
the entry field names, the shape words, the reader-named fields and the one body default through
`rule_data.RULE_ENTRY_FIELDS`, `RULE_ENTRY_READERS` and `RULE_BODY_DEFAULTS`, which move from the emitter to
`rule_data.py`, the module that owns the row shape and the three forms, because `sanity_checks` cannot import the
emitter (`docs/ARCHITECTURE.md` §1.1 forbids a cycle); the field order through the matrix row's `properties` and
the name field through `entry_coverage.name_field`; the rule-type set through `import_blocks.rule_types`; the
location through `resource_mapping.LOCATION_SCHEMA`; the block through the one block reader `sanity_checks.blocks`
with `kinds = ('resource',)`; the value text through the one field reader `import_blocks` (`field_at`,
`fields_at`, `elements_of`, `unescape`) and the one shape rule `sanity_checks.value_shape`; the unit set through
`unit_manifest` and the manifest read `sanity_checks.unit_directories`; the path through `write_path.unit_path`;
the console line through `container_coverage.console_line`.

## Gate boundary

- Offline data only. The two external-command checks stay flag-gated and report NOT RUN on a call that sets
  neither flag.
- The cross-check and the join stay WARN, and the exit code still follows the rules that read the files. The new
  block rule reads the files the operator receives, so its findings are FAIL, like every other block rule.
- No rule prints a scan console line: the console shape names one identity, and a fact that compares two sets is
  printed through the gate's own summary.
- The gate states one shape rule. `tools/check_documents.py` and `tests/test_sanity_gate.py` pin that the gate
  holds one `json.loads`; the new rules read the row shape through `rule_data.parse_rows` and the value shape
  through `value_shape`, so neither states a shape rule of its own.

## Pin honesty

No pin is weakened and no pin measures nothing. A retargeted pin measures content through a pipeline run, not a
hand-built row, where the property-scan rule requires it. Where a pin stated a boundary this piece moves — the
data rule read no file inside a unit directory, the cross-check read no record — the retargeted pin states the
new boundary and still measures the same fact: which file set each rule reads.

## Part 1 — the data rule reads the pair

1. `DATA_FILES` stays the codebase root set: the four records, one per run, read as one rule over the rows of
   every unit. The rule data pair is not a fifth row of that table, because it is a unit-set file: one pair per
   rule type inside the unit directory its own rows name.
2. The rule reads the pair inside each unit directory through `rule_data.parse_rows` and the two names through
   `rule_data.data_file` and `rule_data.printed_file`, so it states no file name and no shape rule of its own.
3. A pair member that does not read as its declared rows, and a pair member with no rows, is a finding, the same
   finding the four records already produce. A pair member the run did not write is not a finding, because the
   content rule writes a pair only when the unit has rows.
4. The join is `directory`: a rule row's `directory` must name a unit the manifest names, and the pair sits in the
   directory its rows name, so a member found at the codebase root names no unit and a member inside a directory a
   row does not name is a finding.
5. The two members stand or fall together, and the printed member must equal `rule_data.render_csv` of the same
   rows, the way `site.auto.tfvars` must equal `site_data.render_tfvars` of the site rows.
6. The position is the row ordinal the record states, and a whole-file finding states row 0.
7. The two report counts move with the read. The data count names the records at the root plus the pair's data
   member inside each unit directory; the printed member is not a data file, the way the site print is not. The
   `.tf` count does not move, because the pair is not a `.tf` file. Both counts are pinned as measurements on a
   real run.

## Part 2 — the cross-check counts the row set

1. The block side for the four rule matrix rows is the row set read through `rule_data.parse_rows` from the data
   member inside the unit directory the rows name. The rule states no reader for the map, no shape rule, no count,
   no scope, no kind, no type, no field name, no file name and no unit rule of its own; the three forms are one
   row set, and the printed form is compared by the `rule_blocks` rule.
2. A file that `parse_rows` refuses is the data rule's finding, so it enters no count here: the cross-check reads
   the row set and states no shape rule, so it cannot report the same fact twice.
3. The fact is still the two counts and names no entry, and the position is the line of the first block the reader
   read for that unit and row, or the file as a whole when the reader read no block.
4. The rule needs the output directory to read the row set, so its signature gains it and `run_checks` passes it.
   A call with no ledger still reports the check as NOT RUN, so a pin that reads only the output directory is
   unchanged.
5. The findings stay WARN, the exit code stays with the rules that read the files, and the corpus table is
   re-measured honestly: the four rule rows read clean on every fixture, so the corpus table names no rule row,
   and the rule-row fact that a planted pair produces is pinned through a run.

## Part 3 — the block rule reads the iterated block

`check_rule_blocks(files, output_dir)`, added to `CHECK_ORDER` among the block rules, one finding per fact, FAIL,
sorted by (file, line, detail):

1. One block per rule type per unit, for the units the rows name. A rule type with no rows writes no block, so a
   unit with no rows produces no fact, the way the pair is written only when it has content.
2. The block's local name and the `for_each` map name are `rule_data.locals_name` for the type.
3. The block's `location` is a level `LOCATION_SCHEMA` names for the type, and every field inside it is one the
   row names for that level.
4. The block body's field list is the name field plus the fields the matrix row declares, in the table order, read
   through `entry_coverage.name_field` and `row["properties"]`, with the provider name `RULE_ENTRY_FIELDS` states,
   plus the one field `RULE_BODY_DEFAULTS` states. Every field prints as `each.value.<field>`, and the default
   field prints the word the table states, because no row column names it.
5. The map holds one entry per row for that unit, keyed by the row `key`, read through `rule_data.printed_entries`
   and the one field reader. The entry field's shape is the shape word the table states, read through
   `SHAPE_READS_AS`; the entry's content is the row's value read back through `unescape` for a scalar and member by
   member for a list, `null` for a field the row states no value for, and the shape word only for a field the table
   names a reader for, because a reader builds that value from another column. A value the print rule states as a
   reference is the naming rule's answer, so the rule compares its shape and not its content.
6. A printed block and a hand-written block are read the same way: the rule reads the files the operator receives,
   so a hand-written block that disagrees with the rows is a finding, and a block for a unit no row names is a
   finding.
7. The position is the line of the block the one block reader read, because the block and the map it reads are one
   object in one file. When the reader read no block, the position is the file as a whole, read through `position`.

## Pins

- `tests/conftest.py`: the shared facts this piece reads — the rule-type set, the unit set, and the pair names — are
  stated once there if more than one test module reads them. No test module imports another test module, and no
  test calls a network.
- `tests/test_data_file_gate.py`: the file set and the two counts (retargeted), the pair read through
  `parse_rows`, the join on `directory`, the printed member compared through `render_csv`, and the position rule.
- `tests/test_round_trip.py`: pin 1.4 retargeted (the cross-check reads the row set through `parse_rows` and no
  other record), the signature and the NOT RUN path, the corpus re-measurement, and a planted disagreeing pair
  read through a run.
- `tests/test_sanity_gate.py`: the new check in `CHECK_ORDER`, the report order, the moved counts read through
  the shared derivation, the one shape rule, and the new block rule read on a printed run and on a hand-written
  file: one pin per finding group, the entry that is not the row it names, the block for a unit no rule row names,
  and the rows the reader read no block for.
- `tests/test_write_path.py`: the pin that said the two counts do not move is retargeted; the pair still names the
  unit file set, and the printed member is still not a data file.
- `tests/test_coverage_matrix.py`: the rule row's grounding table is read in its new home, `rule_data`.
- `tests/test_rule_data.py`: the third-form pin reads the entries, not only the keys, through the one printed-map
  reader.

## Indexes and measurement the piece moves

- `README.md` §Testing names the modules this piece retargets or adds pins in.
- `docs/ARCHITECTURE.md` §1's row for `rule_data.py` gains the entry tables it now owns, and §4.6's check table
  gains the `rule_blocks` row and the two counts the data rule now reads.
- `docs/CODEBASE_ASSEMBLY.md` §14 names the pair as the set the data rule now reads inside the unit directory.
- `docs/USAGE_GUIDE.md` names the data-file count as the records plus the pair's data member.

## Gate

`ruff check .`, `ruff format --check .`, `python3 tools/check_documents.py`, `python3 -m pytest`, in that
order, single process, conservative threads.

Before, measured 2026-11-19 on the committed tree at `5d38f98`: `ruff check .` clean at `py310`,
`ruff format --check .` clean on the 103 Python files, 1,709 pins in 53 test modules — 1,705 pass, with the same
4 skip for the missing `tflint` binary — and `python3 tools/check_documents.py` reports no finding. Per module for
the modules this piece touches: `tests/test_data_file_gate.py` 21, `tests/test_round_trip.py` 34,
`tests/test_sanity_gate.py` 110, `tests/test_rule_data.py` 11, `tests/test_write_path.py` 21,
`tests/test_coverage_matrix.py` 211, `tests/test_property_coverage.py` 33, `tests/test_golden_files.py` 91,
`tests/test_edge_cases.py` 19, `tests/test_real_or_report.py` 5, `tests/test_dependency_wiring.py` 11,
`tests/test_policy_order.py` 8.

## After, measured 2026-11-19 on the final tree (commit `5a6780e`)

- Pins: 1,718 in 53 test modules, up from 1,709. The modules this piece moved:
  `tests/test_data_file_gate.py` 21 -> 27 (six pins: the pair read inside the unit its rows name, a member at the
  codebase root naming no unit, a member inside a directory no row names, the two members standing or falling
  together, the printed member equal to `render_csv`, and a row `directory` disagreement at the row ordinal), and
  `tests/test_sanity_gate.py` 110 -> 113 (three pins: the entry that is not the row it names, the block for a unit
  no rule row names, and the rows the reader read no block for). Every other module keeps its count, including the
  retargeted pins that named `printed_keys`.
- Corpus, 66 fixtures read through the pipeline: `check_data_files` 0 findings, `check_rule_blocks` 0 findings,
  and the round-trip cross-check unchanged at 19 findings on 8 fixtures.
- Sample run: 14 `.tf` files and 4 data files (2 records at the root plus the pair's data member for 2 rule types
  inside the unit its rows name), `data_files PASS` and `rule_blocks PASS`.
- Gate: `ruff check .` clean, `ruff format --check .` clean on 103 files, `python3 tools/check_documents.py`
  reports no finding, `python3 -m pytest` 1,714 passed and 4 skipped for the missing `tflint` binary.

