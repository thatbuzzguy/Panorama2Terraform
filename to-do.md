# To Do — F4.4 Property-level coverage matrix (next feature)

F4.3 (per-entry conversion report) is complete and committed. Its pieces are
recorded in `acceptance.md` (Result) and in the git history:

- `entry_coverage.py`: the mark mechanism (`mark`, `mark_skipped`), the row rules,
  the captured-field rule, `entry_line`, the report text, the gap section and the
  console lines.
- `TerraformGenerator.generate_conversion_report` writes `CONVERSION_REPORT.txt`
  and groups rows with the F3.9 rule (`_report_scope_path`).
- `container_coverage.DESTINATION_KINDS` gained `skipped` and `unaccounted`; the
  `parse_device_groups` row changed from `count-only` to `bookkeeping`, because a
  device group name reaches the output through `location`.
- Every parse method marks the entries it reads, at the point it builds the object.
- Tests: `tests/test_entry_coverage.py` (26), fixture
  `tests/fixtures/entry_gaps.xml`.

F4.4 is not started. Its pieces, when it starts:

- [ ] Overwrite `acceptance.md` with the F4.4 criteria before code or tests.
- [ ] Decide what one property row states: the property path, the value, and the
  output it produced.
- [ ] Reconcile `COVERAGE_MATRIX` with `EMITTED_TYPES` and `resource_name_map`.
- [ ] Report a property the parser captured but no output used (the extraction gaps
  in `backlog.md`), per property, not per entry.
- [ ] Tests: a fixture where an entry is read but one property is dropped, and a
  test that every captured property appears in the matrix.
- [ ] Keep the gate green: ruff, pytest, golden tests, `terraform validate`,
  and the F4.1/F4.2/F4.3 exit codes.

Scope guard: F4.4 does not change the F4.3 report row rules. Property entries stay
counted on the parent row until the matrix covers them per property.
