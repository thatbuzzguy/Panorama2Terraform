# Acceptance — Piece 11B.2 (2026-11-22)

Piece 11B.2 is the run's unit set against the codebase's unit set, and the rule that the run writes no
directory for a unit it read only through the record. The design rule is `docs/MULTI_RUN_CODEBASE.md`
§2 rule 5 and §6 rule 2. The criteria are offline work on fixtures and the pinned rules; no test calls a
network. `terraform` is present, so the pins that read the live provider schema run; the 4 skips are the
`tflint` pins.

## Criteria

1. **One unit rule, read both ways.** `unit_manifest.units` is the one rule that names a unit for a
   directory, an owner, or an edge. The codebase unit set is read through `unit_manifest.units` applied to
   the merged manifest rows read through `unit_manifest.parse_rows`. `codebase_state.py` restates no row
   shape and names no unit set of its own, so no second unit rule and no second unit set appears anywhere:
   the module reads the unit rule through `unit_manifest` or not at all, and the `src/` scans read the
   24-module set clean with `codebase_state.py` in it. Pinned in `tests/test_unit_manifest.py`, in the
   module that owns the unit rule.
2. **The two sets are two facts, and their difference names the units read only through the record.** The
   run's set is `unit_manifest.units` over the run's ledger; the codebase's set is `unit_manifest.units`
   over the merged manifest rows. The run's set is inside the codebase's set, and the units the codebase set
   names that the run set does not are the units the run read only through the record. For a run that read
   nothing from the record the two sets are the same set. Pinned on committed runs, not on hand-built rows:
   `tests/fixtures/kitchen_sink.xml` as the codebase and `tests/fixtures/address_objects.xml` as the second
   run, each read through `parse_rows`, the pattern Piece 11B.1 established.
3. **The write path states the rule, and the run writes no directory for a unit it read only through the
   record.** `write_path.py` is the single writer that forces LF, and the run writes one directory per unit
   the manifest names. The rule that the run writes no directory for a unit it read only through the record
   is stated in the write path's owner rule, read through `unit_manifest.units` (the run set) against the
   codebase set, with no new path rule, no new file shape, no new builder, and no unit rule of its own. The
   pin measures it on a real run that writes into an existing codebase. Pinned in `tests/test_write_path.py`.
4. **The single-run case is unchanged.** A run that reads nothing from the record — the single-run case,
   every committed golden — must produce byte-identical output today. The committed goldens are unchanged
   unless the rule genuinely changes the single-run case, and the measurement is recorded before the decision
   is taken. Confirm no committed golden moved.
5. **Scope.** The join, the ownership rule, the edge rule, the order rule, the gate for a partial run
   (Piece 11B.4), and the update run (Phase 11C) are not this piece: no cross-run edge, no cross-run
   ownership, no plan order over the merged set, no gate change. The run-set-against-codebase-set comparison
   and the no-directory fact are the whole piece.
6. **Pins, one per fact the piece states, in the module that owns the fact:** the unit set pins in
   `tests/test_unit_manifest.py`, the write-path pins in `tests/test_write_path.py`, the merge pins in
   `tests/test_codebase_state.py`. No test module imports another test module; a fact more than one test
   module reads is stated once in `tests/conftest.py`. No `src/` module imports anything from `tests/`.
7. **No second rule of any kind.** This piece states no console line, no environment name, no naming rule,
   no writer, no file shape, no path rule, and no reader. The console line shape stays
   `container_coverage.console_line` (`docs/ARCHITECTURE.md` §3.2), and the pins that scan the `src/` set —
   the writer scan, the environment-name scan, the console-line scan and the second-naming-rule scan — read
   the existing modules unchanged.
8. **Gate measured single-threaded:** `ruff check .`, `ruff format --check .`,
   `python3 tools/check_documents.py`, `python3 -m pytest`. Counts are read from the per-module collection
   counts, and the baseline is the 1,767 passed plus 4 skipped recorded for Piece 11B.1 plus the pins this
   piece adds.
9. **Documents.** `docs/MULTI_RUN_CODEBASE.md` names the module that holds the rule and the test that pins
   it, states no test count and no row-by-row restatement, and keeps one owner document per rule with links.
   The wording is plain and literal, ASD-STE100, no metaphor, no emoji, no historical record in markdown.
   `to-do.md`, `agent-status.md` and this record carry the piece's result.

## Measured before the decision, on committed material

Offline, through the record modules themselves: the kitchen-sink run as the codebase, the
`address_objects.xml` run as the second run, both read through `unit_manifest.parse_rows` and merged
through `codebase_state.merge_rows`.

1. The codebase unit set is 11 units; the second run's unit set is 1 unit (the shared unit,
   `shared_45ca31c3`); the merged set is 11 units, and the run set is inside the merged set. The 10 units the
   merged set names and the run set does not are the units the second run read only through the record:
   `Branch-Stack`, `fw-2.example.com`, `Shared` (`shared_a6577c11`), `FW-Template`, `template-vsys`,
   `vsys1` twice, `vsys2`, `Dev-DG`, `Production-DG`.
2. `unit_manifest.units` reads a ledger today, so it answers nothing for rows read back through
   `parse_rows`: `AttributeError: 'list' object has no attribute 'rows'`. The codebase set could not be read
   through the one unit rule before this piece.
3. The write path writes no directory for a unit read only through the record. Measured on a real run: the
   second run wrote into a copy of the kitchen-sink output. It added no directory, wrote no file inside any
   of the 10 directories the record names, and every byte inside them is the byte the first run wrote. The
   only unit file the run wrote is its own unit's: `shared_45ca31c3/address_objects.tf`. The run wrote the
   root records as its own 1 row, because `generate_run` does not call the merge — that step is Phase 11C.
4. The single-run case is unchanged: for both runs, the merged set against no existing file is the run's own
   set and the record bytes agree with the bytes the run wrote, so no committed golden moves.
5. The second run into the existing codebase exited 1, because the gate read the whole codebase — the block
   rules read the 61 `.tf` files the first run wrote and the cross-check compared them against the second
   run's ledger, which names no row for those units. That is Piece 11B.4's gate for a partial run, and this
   piece changes no gate rule.

## Decision

The measured behaviour already matches the rule, so the piece states the rule and pins it, and changes one
thing: `unit_manifest.units` reads the same rule over the row set read back through `parse_rows`, so the
codebase unit set is read through the one unit rule instead of through a second set. No path rule, no file
shape, no writer, and no gate rule change; the single-run bytes are unchanged, so no committed golden moves.

## Result

Landed 2026-11-22. One change to the code, and no golden moved: `unit_manifest.units` reads the same rule
over either row set — the rows the run's ledger read, or the rows a record read back through `parse_rows` — so
the codebase unit set is read through the one unit rule instead of through a second set. `codebase_state.py`
still defines no row shape, no reader, no identity key, no naming rule, no writer, no path rule, no console line
and no unit set of its own, so the `src/` scans read it unchanged, and `src/` still holds 24 modules. The
no-directory fact is stated as rule 4 of `write_path.py`, which keeps its two builders and its one writer, and
reads both sets through `unit_manifest`.

Five pins, one per fact the piece states, each in the module that owns the fact:

- `tests/test_unit_manifest.py::test_the_codebase_unit_set_is_read_through_the_one_unit_rule` — the rule answers
  the same units for the ledger set and the read-back set of the same run, and a reader with no ledger and no
  record names no unit;
- `tests/test_unit_manifest.py::test_the_two_unit_sets_differ_only_by_the_units_read_through_the_record` — the
  run set is inside the codebase set, the 10 units only the codebase set names are read as the record states them,
  and a run that read nothing from the record answers its own set, which is the single-run case the goldens measure;
- `tests/test_codebase_state.py::test_the_merged_manifest_set_is_the_codebase_unit_set_read_through_the_one_unit_rule`
  — the merge names no unit set of its own and adds no unit on the committed pair;
- `tests/test_write_path.py::test_the_run_writes_no_directory_for_a_unit_it_read_only_through_the_record` — a real
  run writing into an existing codebase added no directory, wrote no file inside the 10 directories the record
  names, left every byte inside them as the first run wrote them, and wrote only inside its own unit directory plus
  the codebase root set;
- `tests/test_write_path.py::test_the_write_path_states_the_run_set_rule_and_reads_the_unit_set_through_its_owner`
  — the rule is stated in the module that owns the write path, and the module holds the byte rule, the two builders
  and the one writer, with no unit rule, naming rule or file shape of its own.

No committed golden moved. Gate, measured single-threaded on the tree that holds this piece: `ruff check .` is
clean at `py310`, `ruff format --check .` is clean on the 108 files it reads (81 Python files, 27 markdown files),
`python3 tools/check_documents.py` reports no finding, and `python3 -m pytest` passes 1,772 pins with the same 4
skips for the missing `tflint` binary — 1,776 pins in 54 test modules, 5 more than the 1,767 pins Piece 11B.1
measured, in 236.45 s. Read through the per-module collection counts: `tests/test_unit_manifest.py` collects 41,
`tests/test_write_path.py` collects 23, and `tests/test_codebase_state.py` collects 10, so the 5 new pins are 2,
2 and 1. `terraform` is present, so the pins that read the live provider schema ran.

Two measured facts that this piece did not change and that the pins read as they are: a run writing into an
existing codebase exits 1 because the gate reads the whole codebase against the run's own ledger, which is
Piece 11B.4's gate for a partial run; and the run writes its own root records rather than the merged set, because
`generate_run` does not call the merge, which is Phase 11C.
