# To Do

The current feature is the report-read rule applied to the next `report` container: the application override rule.
Pieces:

- [ ] Confirm the gap through a run: `parse_application_override_rules` captures `description` and
      `destination_addresses` for `Override-443` in `tests/fixtures/application_override_rules.xml`, and the report
      line prints neither. Add an entry that carries neither field, so the pin covers both sides.
- [ ] Print both fields on the report line through the captured object, in the field order the report already uses
      for its override fields.
- [ ] Pin the rule in group 6 of `tests/test_property_coverage.py` in the shape of
      `test_the_report_reads_the_application_filter_description_it_prints`: the fixture entry, the parse read, the
      line the report prints, and the scan scope. Extend the parse read pin and the report pin.

The rule this feature rests on is in `docs/COVERAGE_MATRIX.md` §1: a `report` line reads the field it prints through
the captured object, because a `report` container has no matrix row. `panos_application_override_rule` is not a
resource in the pinned provider, so no emitter can read this container.

## Rules the layout keeps

- `docs/ARCHITECTURE.md` §1.1 is the owner document for the layout. `AGENTS.md` names the tracking markdown
  set, and each index names every document under it, so a file outside an index is a finding.
- Import rule: `src/` is one flat namespace, so a module may import any `src/` module without a cycle. The
  one test that checks the rule reads only `src/`. A test may import `src` modules and `tests/conftest.py`
  through `importlib`; nothing under `tests/` may import another test module. `src/` may not import from
  `tests/`.
- The corpus is the directory the scan runs over. A hostile fixture in it changes the set the tool prints for
  other fixtures, so pins that state the printed set name the fixture count.
