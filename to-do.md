# To Do — F4.3 Per-entry coverage report (next feature)

F4.2 (Entry coverage, parse side) is complete and committed. Its pieces are
recorded in `acceptance.md` (Result) and in the git history:

- `xml_input.ParsedSource` records the opening line of every element.
- `container_coverage.CONTAINER_TABLE` is the container table in code.
- `container_coverage.scan()` reports a section no row covers; the converter
  writes the section to `MANUAL_SETUP_REPORT.txt` and prints one console line.
- Tests: `tests/test_container_coverage.py` (24), line tracking in
  `tests/test_safe_input.py` (30), fixture
  `tests/fixtures/unknown_containers.xml`.

F4.3 is not started. Its pieces, when it starts:

- [ ] Overwrite `acceptance.md` with the F4.3 criteria before code or tests.
- [ ] State what "accounted for" means for one entry: emitted, reported,
  inventory, count-only, or dropped.
- [ ] Record which fields of an entry the parser captured, per entry.
- [ ] Write `CONVERSION_REPORT.txt`: one line per entry, with file, line
  (`ParsedSource.line_of`), object type, and destination.
- [ ] Report an entry whose captured fields produce no output (the `parse_regions`
  gap and the extraction gaps in `backlog.md`).
- [ ] Tests: a fixture where an entry is read but nothing is written, and a test
  that every entry in the corpus appears in the report.
- [ ] Keep the gate green: ruff, pytest, golden tests, `terraform validate`,
  and the F4.1/F4.2 exit codes.

Scope guard: F4.4 (property-level coverage, `EMITTED_TYPES` reconciliation,
`resource_name_map`) is not in this slice.
