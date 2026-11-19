# Acceptance — the rule data write path (Epic 9, Piece 18, Phase 9B)

Criteria set 2026-11-18 for Piece 18: the rule row set is written. The run writes the consumed JSON file and
the printed CSV file for each rule type inside each unit directory the manifest names, and it writes both
through `src/write_path.py`, the single writer. Piece 17 declared the row shape `RULE_ROW_FIELDS` and the two
forms of the same rows; this piece lands the file set those two forms are written into. The iterated block is
Piece 19, and the gate rule that reads the rows is Piece 20.

Owners this piece reads and does not restate: the row shape through `rule_data.RULE_ROW_FIELDS`; the two forms
through `rule_data.render` and `rule_data.render_csv`; the file name through the coverage matrix row's
`output_file`, as `rule_data.data_file` reads it; the four rule types through `import_blocks.rule_types`, the
one place that names them; the run order through `PARSE_ORDER`; the parse method that reads a rule container
through `container_coverage.CONTAINER_TABLE`; the unit join through `unit_manifest.facts_of` and
`unit_manifest.directory_name`; the path, the two sets and the byte rule through `write_path.py`; the naming
rule through `naming.py`, taken as the argument `build_rows` already takes.

## The rules this piece states

1. **The rule data pair is a unit-set file set.** One pair per rule type per unit, written inside the unit
   directory the manifest row names (`docs/CODEBASE_ASSEMBLY.md` §14), because the rows of one rule type are the
   rows of one unit: the chain grouping keys on the device group and the virtual system, which are two of the
   five unit facts, so the file a unit reads holds that unit's rows and names its unit only by its directory. The
   name states the rule type, not the unit, which is the rule `write_path.py` states for a per-unit file. This is
   the new file shape, so §14 names the set it belongs to, and the pins that read the file set read the pair as
   the unit set.
2. **Two files, the same rows.** The JSON file is the form a Terraform object reads and the form a reader reads
   back through `parse_rows`. The `.csv` file is the printed form of the same rows, the way `site.auto.tfvars`
   is the printed form of the site record, so the printed form is compared and not counted, and `parse_rows`
   still refuses the printed form read as data.
3. **Written only when it has content.** The rule the report files and the four data files already share: a
   rule type that has no rows for a unit writes no pair for that unit, so the file set is the units that have
   rows, not a grid of rule types times units, and a run that reads no rule writes no rule data file.
4. **`rule_data.py` holds no writer and states no path.** The module keeps its single writer as `write_path.py`,
   states no path of its own, and writes no file of its own; the run's write step calls `write_path.unit_path`
   and `write_path.write_file`. The module owns the row shape, the two forms, and the two file names, the second
   name read through the same matrix row as the first.
5. **No gate rule reads the pair in this piece.** The data rule keeps reading the four records at the codebase
   root as one rule over the rows of every unit, and it reads no file inside a unit directory, so the report's
   two counts do not move and the pin that holds that boundary stays. The gate that reads the rule rows through
   the declared shape and joins on `directory` is Piece 20, where the `data_files` table gains the rule data file
   and the count moves with it.
6. **The write step states no type table and no join table.** The four rule types come from
   `import_blocks.rule_types`; the rules for one type are the parse answer the run order names for the parse
   method the container table names for that matrix row. The pair is written per unit by joining the rows on
   `directory`, the way `commit_actions` and `import_blocks` join their rows to the unit.
7. **The generated `README.md` names the two forms as files** and states no row, no value, no count, no path and
   no timestamp, which is the file-inventory exception `docs/CODEBASE_ASSEMBLY.md` §9 rule 9 states. Two runs on
   the same bytes write the same bytes, so the byte rule and the LF rule cover the new files, and no golden moves:
   the golden set is the `.tf` set, and the records and the reports are not in it.

## Pins

Ten pins in `tests/test_rule_data.py`, in the order the rules above state them (the eight Piece 17 pins stay,
with AC-8 read as the write path rule), and one new pin in `tests/test_write_path.py` group 1.

- AC-1 to AC-7: unchanged from Piece 17.
- AC-8: `test_the_rule_data_layer_states_no_second_rule_and_writes_no_file` — as before, read as the write-path
  rule: the module holds no writer and states no path, so the run writes the pair through `write_path` only.
- AC-9: `test_the_two_file_forms_are_unit_set_files_named_through_the_matrix_row` — `data_file` and
  `printed_file` read the same matrix row, so the two names are that row's `output_file` stem with the two
  suffixes; each name states the rule type and not the unit, so the path is the only place the file states the
  unit; the pair is not one of the four root records, so the data rule counts neither; the generated `README.md`
  names the two forms as files and states no row, no value, no count, no path and no timestamp.
- AC-10: `test_the_run_writes_one_pair_per_rule_type_per_unit_through_the_write_path` — measured through the run
  on the two fixtures the chain pins read. On `tests/fixtures/policy_order.xml` the manifest names five unit
  directories and the three chains name three of them, so `panos_security_policy_rules` writes one pair in each of
  those three, `panos_nat_policy_rules` writes one pair in the one of them that has nat rows, and the two rule
  types with no rows write no pair in any unit. On `tests/fixtures/kitchen_sink.xml` all four rule types have rows
  in one unit, so each writes one pair there and no pair in the other ten, and no rule data file sits at the
  codebase root. Each written JSON reads back through `parse_rows` as the rows `build_rows` built for that unit,
  each written CSV is `render_csv` of the same rows, and the bytes hold no CR, which is the byte rule
  `write_path.py` states in the one write function.
- AC-11, in `tests/test_write_path.py`:
  `test_a_new_unit_set_file_shape_names_the_unit_set_and_the_two_counts_do_not_move` — the pair names exactly one
  set, the unit set, so the membership rule holds for the corpus run with the new shapes present; the data rule
  reads no file inside a unit directory, so the report's data count names only the four records at the root and
  the printed form stays compared and not counted; the two counts name the two sets; the run writes one directory
  per unit the manifest names, so a rule data file sits inside the directory its rows name. The pair is read as a
  derivation through `rule_data`, not as a restated list.

## Indexes and measurement the piece moves

- `docs/CODEBASE_ASSEMBLY.md` §14 names the set the new file shape belongs to, and `docs/USAGE_GUIDE.md`
  §Output files names the two forms.
- `docs/ARCHITECTURE.md` §1 module table row for `rule_data.py`: the rule column states the two file names read
  through the matrix row, and the write column changes from "writes no file" to "holds no writer: the run writes
  the two forms per rule type per unit through `write_path.py`".
- `README.md` §Testing names `tests/test_rule_data.py` once; the entry gains the two pins this piece writes, and
  `tests/test_write_path.py`'s entry gains the file-set pin. No new test module, so no index name moves.
- The report counts do not move, because no gate rule reads the new files in this piece; the measurement is
  recorded below and the pins read the counts as derivations.
- `docs/LICENSING.md` measures the `src/` module count from the working tree: no new module, so the counts stay.

## Gate

`ruff check .`, `ruff format --check .`, `python3 -m pytest`, `python3 tools/check_documents.py`, in that
order, conservative threads, single process.

Before, measured 2026-11-18 on the committed tree at `e4ffe7b`: `ruff check .` clean at `py310`,
`ruff format --check .` clean on the 102 Python files, 1,705 pins in 53 test modules — 1,701 pass and the same
4 skip for the missing `tflint` binary — 320.31 s, and `python3 tools/check_documents.py` reports no finding,
read at 12.15 s.

After, measured 2026-11-19 on the final tree at commit `eda2d1a`: `ruff check .` clean at `py310`,
`ruff format --check .` clean on the 102 Python files, 1,708 pins in 53 test modules — 1,704 pass and the same
4 skip for the missing `tflint` binary — in 507.48 s, against 280.70 s for the same set read on the tree before the
final document edits, and `python3 tools/check_documents.py` reports no finding, read at 23.20 s after those edits.
`tests/test_rule_data.py` reads 10 pins and `tests/test_write_path.py` reads 21, against 8 and 20 before the piece.
No golden, fixture, response or tflint file changes: the golden set is the `.tf` set, so the golden bytes read the
same as before, and the pins that name the printed sets read the same counts as before.
