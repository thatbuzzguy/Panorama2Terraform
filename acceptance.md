# Decision — the shadow parent index key — acceptance criteria

This slice decides what `shadow_coverage.parent_index` keys by, so the shadow report line can name which
parent entry the child repeats. The scan is F5.4, in `src/shadow_coverage.py`, and `docs/ARCHITECTURE.md`
§3.2 is the owner document for it.

## Facts measured before the change

- Measured 2026-11-04 by reading `tests/fixtures/ownership_parent.xml` through the parse: two
  `Printer-Pool` entries sit under the `panos_address` row, one in `Parent-DG` (line 18) and one in
  `Child-DG` (line 26). `parent_index` answers one key for both, so the first parent row in report order
  wins, and the report line names no parent scope, so it cannot say which of the two the child repeats.
- Measured 2026-11-04 through the wrapper decision on `tests/fixtures/scope_parent.xml`: the parent row is
  `address`/`Web-Server-1` at line 10, its grouping scope part is `SHARED SECTION`, and its key facts are
  all `''`. So the parent scope is visible only as data, never as a printed field, today.
- Measured 2026-11-04 on the same two rows of `tests/fixtures/ownership_parent.xml`: read through
  `state_coverage.ownership_key`, the two keys differ at the `device_group` position
  (`Parent-DG` and `Child-DG`), so the identity key is what names which parent entry.
- The project has one identity key rule: `state_coverage.ownership_key` (§2.1 identity as the F3.9 grouping
  rule reads it), and `ownership.row_key` reads its order through it. A ledger row carries the five declared
  facts, so the shadow scan reads the key through that rule rather than stating a second one.
- The shadow scan reads its own row set (`ledger.rows()`), so the key is read through the row rule the scan
  already uses. The unit option is rejected: the shadow rule names no unit, and reading the key through
  `unit_manifest.units` would need the §5 naming rule as an argument.
- A per-scope response holds exactly the element the path names, so one parent path names one device group:
  two parent entries that share a name under one row can only come from a whole-config parent source.
  `--parent` applies to `--source api` with `--path`, so the pin reads the parent through a parse run on
  `tests/fixtures/ownership_parent.xml` and an inline per-scope response for the child. No new fixture: the
  corpus pins are keyed by fixture name, and the child entry is line 10 of the shape the pins build.

## Decision

1. `parent_index` keys each parent entry through `state_coverage.ownership_key(matrix row, entry name, the
   parent row's declared facts)`, the project's one identity key rule, so the key carries the parent scope.
   The key rule is stated once, in §3.2, and no second key rule is added.
2. The scan compares a child entry with a parent key on the (matrix row, entry name) part, because the child
   names its own scope: the fact is that one name sits under one row in two scopes.
3. Two parent entries with the same name under the same row are two keys, so a child that matches both is
   one finding per parent entry, and each finding names its own parent entry. This replaces "the first
   parent row wins": identity is unique per entry, so no parent entry is dropped.
4. Report order gains the parent entry as the tie-break: line, then object type, then name, then the parent
   entry the finding names, in the parent report order.
5. The report line gains the parent entry field: the parent scope read through the F3.9 grouping rule, then
   the entry identity read through the F4.3 row identity rule. `shadow_line` takes the grouping rule as an
   argument, the same argument `console_lines` takes.
6. The console line stays as decided: its source field is the parent source name only, because the console
   shape names one position, one identity and one fact. The parent entry stays in the report.

## Acceptance criteria

1. Key: `parent_index` on the parse run for `tests/fixtures/ownership_parent.xml` answers two
   `panos_address` keys for `Printer-Pool`, and each key equals `state_coverage.ownership_key` read on that
   row, so the key names the device group that holds the parent entry. The pin reads the key through data.
2. The finding names which parent entry: one child entry against the two parent entries is two findings, and
   the two lines name the `Parent-DG` entry and the `Child-DG` entry.
3. Order: the two findings are in the parent report order, line 18 then line 26, so the tie-break is the
   parent entry and the report order pins stay.
4. Line shape: the shadow line prints the parent entry field, and the parent scope part is the F3.9 grouping
   rule read on the parent row (`SHARED SECTION` for `tests/fixtures/scope_parent.xml`,
   `DEVICE GROUP: Parent-DG` for the whole-config parent).
5. The offline run that reads both cache entries finds the same shadow from the same bytes, and its report
   line names the parent entry.
6. A shadow does not change the exit code, and the console line gains no parent identity: its fact part stays
   the parent source name only, so `tests/test_container_coverage.py` group 4 stays green.
7. `tests/fixtures/ownership_parent.xml` reports `PASS (0 FAIL, 0 WARN)` and no corpus pin moves, because this
   change adds no fixture.
8. `ruff check .` is clean and `python3 -m pytest` passes. Reports are not goldens, so no golden moves.
9. Pins in `tests/test_shadow_coverage.py` groups 2, 4, 5 and 6. Move the stale comment in
   `src/panorama_to_terraform.py` that says the console prints no shadow line, and the two `src/ownership.py`
   comments that name the key the shadow scan uses.
