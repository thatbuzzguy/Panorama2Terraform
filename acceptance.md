# Acceptance — Piece 11C.1 (the existing records as a reference source, and the units the run names)

Piece 11C.1 states how an update run reads the codebase records it did not write, and the rule that the run names
the units it wrote. The work is offline: every criterion is read against committed material through
`tests/conftest.py`, so a criterion that needs a fact a live target states is recorded in `backlog.md` and is not
decided here.

## Criteria

1. **The read shape.** The run reads each existing record as data through the module that owns its shape
   (`parse_rows`), one entry per row. The state document's tree rule does not apply to a record: the container
   table, the parent walk and the expat line map are keyed on the ElementTree tree, so the state door gives the
   scan one shape per entry, and a record gives the rules one entry per row. `state_coverage.py` names no file, no
   path and no reader, so the reference-source read is a data read, not a door read. The two row sets combine only
   through `codebase_state.merge_rows`, the one merge rule, so no test module and no module states a merge of its
   own.
2. **Where the read stops.** The read reaches the ownership fact half: the identity and the five facts, read
   through `state_coverage.ownership_key`, which answers the same key for a state entry and for a committed record
   row on the committed pair. The property-value half is not in a record: `ownership.FIELD_ORDER` holds no property
   field, so the drift half reads the value from the state document and the identity from the record, and the record
   gains no field. The finding half reads fields `parse_rows` does not read back (`line`, `container`, `reason`,
   `chain`, `from_parent`), so that half stays in `backlog.md` and the run reports findings for the rows it built.
3. **`SOURCE.txt` names only the sources the door read.** A record read through `parse_rows` is a data read, not a
   door source, so an update run names no existing record and gains no source kind, no field, no record entry, no
   run field and no timestamp on a row. Measured on the committed pair: the update run's record is byte-identical
   to the standalone run's record.
4. **The units the run names.** The run's set is `unit_manifest.units` over the rows its own ledger read, and that
   set is the set of directories the run wrote files inside. The codebase's set is the same rule over the merged
   rows read back through `parse_rows`; on the committed pair it names 11 units and the run's set names 1, so the
   difference is 10 units the run read only through the record and wrote no file inside. The path for both sets is
   `write_path`'s, with the directory name read through `unit_manifest.directory_name` and `naming.sanitize`, the one
   naming rule.
5. **The run states no rule an owner states.** The read step in `generate_run` reads the file set through
   `sanity_checks.DATA_FILES`, the path through `write_path.root_path`, each row set through its own module's
   `parse_rows`, the combination through `codebase_state.merge_rows`, the unit set through `unit_manifest.units`,
   and the order through `reference_edges.order`. It states no key, shape, reader, path rule, unit rule, writer or
   console line of its own.
6. **The single-run cases produce today's bytes and today's report.** A run that reads nothing merges into the set
   it built, so the four committed goldens are unchanged, and the report for the committed pair is unchanged. No
   gate rule, severity rule or exit-code rule changes, so the numbers `tests/test_sanity_gate.py` and
   `tests/test_data_file_gate.py` read for the committed pair are unchanged. A golden moves only if the measurement
   shows the rule genuinely changes it, and a moved golden is regenerated from a real run in the same commit.
7. **Pins.** One pin per stated fact, in the module that owns the fact, grounded on committed runs through
   `tests/conftest.py` and never on hand-built rows. No test module imports another test module, and a fact shared
   by two modules is stated once in `tests/conftest.py`. A fact that already has a pin is not pinned twice.
8. **The gate.** `ruff check .`, `ruff format --check .`, `python3 tools/check_documents.py`, and
   `python3 -m pytest` single-threaded. Baseline: 1,784 passed + 4 skipped, 1,788 pins in 54 test modules, 81 Python
   files. The pin counts are read from the per-module collection counts.
9. **Not this piece.** Piece 11C.2 (the report section that names the two sets), Piece 11C.3 (the write boundary:
   whether the run writes its own rows or the merged record at the root), the `--prune-cache` consequence, and the
   blocked halves in `backlog.md`. The write boundary stays as today: the run writes the rows it built, so the exit
   code and the data-rule findings `tests/test_sanity_gate.py` and `tests/test_data_file_gate.py` read for the
   committed pair are not moved by this piece.

## Pins

| Fact | Module that owns it | Pin |
|---|---|---|
| The record is read as data through its own reader, with no tree rule, no container table, no parent walk and no expat line map, and `state_coverage` names no file, path or reader | `state_coverage.py` | `tests/test_state_coverage.py::test_the_reference_source_is_read_as_data_through_the_readers_the_shape_owners_state` |
| The read reaches the ownership half through `ownership_key`, and a record row holds no property value, so the drift half reads the identity from the record and the value from the state document | `state_coverage.py` | `tests/test_state_coverage.py::test_the_reference_read_reaches_the_ownership_half_and_no_property_value` |
| The run reads the existing records through each record's `parse_rows` before the rules that read a merged set, and the run states no key, shape, reader, path rule or unit rule of its own | `codebase_state.py` | `tests/test_codebase_state.py::test_the_run_reads_the_existing_records_through_the_readers_the_shapes_owners_state` |
| The record names only the sources the door read: an update run names no existing record and gains no source kind, field or record entry | `provenance.py` | `tests/test_provenance.py::test_an_update_run_names_only_the_sources_the_door_read` |
| The run's set is the units it wrote, read through `units` over its own ledger and verified against the directories the run wrote files inside | `unit_manifest.py` | `tests/test_unit_manifest.py::test_the_units_the_run_names_are_the_units_it_wrote_files_inside` |

The two unit sets and their difference, the write path's rule that the run writes no directory for a unit it read
only through the record, the merge rule, the join key per record, the order rule over a merged set and the gate's
read of the run's unit set are already pinned by Pieces 11A, 11B.1–11B.4, so this piece adds no pin for them.

## Result

Every criterion was read against the tree and met. The gate, measured 2026-11-22 single-threaded: `ruff check .`
clean at `py310`, `ruff format --check .` clean, `python3 tools/check_documents.py` reports no finding, and
`python3 -m pytest` exits 0 with the same `tflint` skips the baseline had, and with the pins this piece added. The
per-module collection counts are recorded in `agent-status.md`, and no new module appeared, so no document that names
a module gained a name.

Criterion 1, the read shape. The five pins read each record through its own module's `parse_rows` and combine the
two sets only through `codebase_state.merge_rows`. Measured on the committed pair: 11, 61, 9 and 3 rows read back,
1, 5, 9 and 3 rows the run built, 11, 62, 9 and 3 merged. `state_coverage.py` defines no reader, writer, path rule,
row shape or unit rule of its own, read through `ast` defined names, so the entry point is the only reader and it
reads through the owners. No test module states a merge, a file set or a join key of its own, and no test module
imports another test module.

Criterion 2, where the read stops. `state_coverage.ownership_key` answers the same key for the state entry
(`panos_address_group`, `Web-Servers`) and for the merged ownership row, and the row holds no field of the
comparison table's one pair for that type, so the comparison half has nothing to read from the record. The finding
half stays on the rows the run built; the fields it reads (`line`, `container`, `reason`, `chain`, `from_parent`) are
not read back by `parse_rows`, and that condition was already recorded in `backlog.md`.

Criterion 3, `SOURCE.txt`. The update run's record is one record, kind `file`, name `address_objects.xml`, and is
byte-identical to the record the same run wrote standalone, so it names no existing record and gained no source kind,
no field and no record entry. No run field and no timestamp was added to a row.

Criterion 4, the units. The run's own set names 1 unit, `shared_45ca31c3`, and the merged set names 11, so the
difference is 10. Inside the 1 directory the run's own set names the tree holds 12 files and the only byte the update
run changed there is `shared_45ca31c3/address_objects.tf`, the file it wrote; inside the 10 directories only the
merged set names, all 60 bytes are the bytes the first run wrote and no file there is new. Both sets are named
through `unit_manifest.directory_name` and `naming.sanitize`.

Criterion 5, the read step. It reads the file set through `sanity_checks.DATA_FILES`, the path through
`write_path.root_path`, each shape through its module's `parse_rows`, the combination through the join key and the
merge rule, and the unit sets through `unit_manifest.units`; the pin forbids `open(`, `write_text`, `.json`,
`CONSOLE_PREFIX`, `os.environ`, `row_key`, `ownership_key`, `FIELD_ORDER` and `SITE_ROW_FIELDS` in that source, so the
step states no rule an owner states. It reads the four records only, so it reads no report as data.

Criterion 6, the single-run cases. The four committed goldens read nothing, so the merged set is the set each run
built, and no golden moved. The report for the committed pair is byte-identical, the gate reads the same numbers as
before (61 `.tf` files, 8 data files, 64 blocks, 41 FAIL, 9 WARN, exit 1), and the order rule and the acyclic rule
answer the same for the run's own row read through the merged set, so no existing pin moved. No gate rule, severity
rule or exit-code rule changed.

Criterion 7, the pins. One pin per stated fact, in the module that owns the fact, as the table above names: two read
by `state_coverage.py`, one by `codebase_state.py`, one by `provenance.py` and one by `unit_manifest.py`, each
grounded on committed runs through `tests/conftest.py` and none building a row by hand. No fact already pinned was
pinned twice, and the committed pair the pins read is stated once, in `tests/conftest.py`.

Criterion 8, the gate, measured above. Criterion 9 held: Piece 11C.2, Piece 11C.3, the `--prune-cache` consequence
and the blocked halves were not decided here, and the write boundary stays as today.

Re-measured 2026-11-23 through `tests/conftest.py` on the committed pair, apart from the pins: the rows read back are
11, 61, 9 and 3, the rows the second run built 1, 5, 9 and 3, the merged set 11, 62, 9 and 3; the second run's own
unit set names 1 unit and the merged set names 11; the pair trees, including the six report files, are byte-identical
between the module as it stood at `3b221b4` and the tree that holds this change, so no golden and no report moved.
The five pins pass on their own. The independent acceptance review of this piece has not run yet.
