# To Do

The current feature is the `count-only` field gap for `parse_regions`, which `backlog.md` names: regions are
parsed but reach no output, so the property scan cannot measure a read for a region field, and no rule yet states
what a `count-only` container may claim. `docs/ARCHITECTURE.md` §2.4 records the parse fact (F3.10).

Pieces:

- [ ] Decide what the rule states for a `count-only` row. Today the per-entry report lists each region row as a
      gap, so the operator sees it, and the parse writes no output for a region. A gap becomes a finding only
      when a rule exists: either an emitter exists for the container, or the report writer reads the field it
      names.
- [ ] Decide which reader the rule names. `docs/COVERAGE_MATRIX.md` §1 states the rule for a `report` container:
      the report line reads the field it prints through the captured object. A `count-only` row has no such
      reader, so the scan scope stays the entries an `emitted` row covers
      (`tests/test_property_coverage.py::test_scan_scope_is_the_entries_a_matrix_row_covers`).
- [ ] Decide the pin before the code: the scan-scope pin already holds that a `count-only` row is outside the
      scan scope, so a rule that reports a `count-only` field gap must change the row kind first, and a row that
      moves from `count-only` to `emitted` changes the property scan, the per-entry report and the `.tf` goldens
      together.
- [ ] No fixture change until the rule states what a region output is, because the corpus pins are keyed by
      fixture name and the goldens read the bytes of a run on the fixture.

The rule this feature rests on is `docs/COVERAGE_MATRIX.md` §1 for the report container, and
`docs/ARCHITECTURE.md` §2.4 for the regions parse.

## Rules the layout keeps

- `docs/ARCHITECTURE.md` §1.1 is the owner document for the layout. `AGENTS.md` names the tracking markdown set,
  and each index names every document under it, so a file outside an index is a finding.
- Import rule: `src/` is one flat namespace, so a module may import any `src/` module without a cycle. The
  one test that checks the rule reads only `src/`. A test may import `src` modules and `tests/conftest.py`
  through `importlib`; nothing under `tests/` may import another test module. `src/` may not import from
  `tests/`. `tools/` is not on the test path, so `tests/test_build_kitchen_sink.py` reads the fixture assembler
  through `importlib` on the path `tests/conftest.py` builds once.
- The corpus is the directory the scan runs over. A hostile fixture in it changes the set the scan reports for
  the other fixtures, so pins that state the printed set name the fixture count. The fixture assembler reads the
  same set by rule: a fixture the F3.8 input rule refuses is skipped, and the record is not an input
  (`tests/test_build_kitchen_sink.py`).
