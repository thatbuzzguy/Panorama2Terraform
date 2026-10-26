# Agent Status

## Current position
**F4.3 (per-entry conversion report) is committed** as c9a1f6b and closes the
third Epic 4 feature. Gate: ruff clean, pytest 566 passed (26 new), both golden sets byte-identical, terraform
validate green on all four outputs. Next feature: F4.4 property-level matrix
(`to-do.md`).

Files changed: `entry_coverage.py` (new), `container_coverage.py` (two destination
kinds, `SCOPE_FACT_KEYS`, the `parse_device_groups` row is now `bookkeeping`),
`panorama_to_terraform.py` (`PanoramaParser.mark` / `mark_skipped`, `ledger`,
marks in every parse method, `TerraformGenerator.generate_conversion_report`,
`main()` console), `tests/test_entry_coverage.py` (new),
`tests/fixtures/entry_gaps.xml` (new), `tests/test_container_coverage.py`
(docstring: eight destinations), `README.md`, `docs/ARCHITECTURE.md` §2.4 and the
new §3.2.

Rules F4.3 pinned:
- One report row is one `<entry name>` element at section level. A container inside
  a config-object entry is a property level, so the parent row counts the property
  entries instead of printing a row (F4.4 covers them).
- Object type is the F4.2 `section_path` rule; no second naming rule.
- Destination is the longest matching container row, with two per-entry overrides:
  `report_only` content is `report`, a skipped entry is `skipped`, and an entry no
  parse method read is `unaccounted`. A scope entry is `bookkeeping`.
- Captured fields are the object keys minus the entry name and the four scope facts,
  minus empty values, sorted; `captured: name only` when there is nothing else.
- The mark stores the object by reference, so a field added after the mark is
  reported.
- Gap kinds write nothing: `count-only`, `skipped`, `unaccounted`. A `report` row is
  not a gap because the manual report is its output.
- Rows are grouped by the F3.9 rule, ordered by line then object type then name, the
  report names the file name only, two runs write the same bytes, no entries means no
  file, no gaps means no extra console line, and the exit code stays with the F4.1 gate.

Watch during F4.4: the mark rule is an AST check over parse methods and their helper
calls, so a method that reads entries through a variable path is accepted only when it
marks somewhere in the call chain (`tests/test_entry_coverage.py::_reads_entries`).
The report line shape is pinned field by field in `entry_coverage.entry_line`.
