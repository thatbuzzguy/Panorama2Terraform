# To Do — Epic 5 open features

F5.1 (the read door), F5.2 (the cached API export), F5.3 (the provenance record) and F5.4 (the
cross-source shadow report) landed; their records are in the git history. No feature is in
progress. Write `acceptance.md` with the acceptance criteria before the code and the tests.

## F5.6 Terraform state as a source (next)

Pieces to decide, then build:

1. Decide how a state document enters the door. A state file is JSON, so the size check and the DTD
   rule still apply to its bytes, but the container table, the parent walk, and the expat line map
   are keyed on the ElementTree tree. One rule is needed for the shape a scan can read.
2. Decide the ownership fact: which entries another workspace already owns, and the drift fact:
   which owned entry has a value the run does not match. Both are property-level facts, so the
   F4.4 property scan reads them.
3. Decide where each fact prints, and whether it changes the exit code. The gate reads `.tf` files,
   so a new fact needs its own rule before it can fail a run.
4. Keep `--offline` honest: a state read is a file read, so no network rule changes, and every test
   uses a committed fixture.
5. Extend the record: `kind` names the source kind, and `scope` names the workspace. The record
   shape does not change, so `parse_records` reads a state record with no new field.

## F5.5 Read-through data blocks (after F5.6)

1. `DATA_SOURCE_SCHEMA` in `resource_mapping.py`, verified against the provider
   `data_source_schemas`. The provider facts are in `backlog.md`.
2. One gate rule for a `data` block, because a data source schema declares no required attributes.
3. Plain strings stay the default for a name outside the run; a declared upstream scope may emit a
   `data` block instead.

## Open items that are not in a feature

- The prune action. The rule is in `provenance.py` (F5.3), and the reference is data, but no
  command runs the prune. Recorded in `backlog.md`.
- Property gaps in a container no matrix row covers (report, inventory, bookkeeping, count-only,
  nested-block): recorded in `backlog.md`, and pinned as out of scope by
  `tests/test_property_coverage.py::test_scan_scope_is_the_entries_a_matrix_row_covers`.
- The console prints the gap lines only; printing a property finding or a shadow needs the console
  line shape decided first.
- The shadow parent index key names the matrix row and the name, not the parent scope. Recorded in
  `backlog.md`.
- `panos_aggregate_layer3_subinterface` has no corpus entry to measure, so its declared properties
  are grounded in the emitter source only.
- `AGENTS.md` points to `lib_docs/` for API cheat sheets. The directory is not in the repo. Recorded
  in `backlog.md`.
