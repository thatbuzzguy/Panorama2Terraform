# Decision — the application override report line — acceptance criteria

This slice applies the rule `docs/COVERAGE_MATRIX.md` §1 states to the next `report` container: a report line
reads the field it prints through the captured object, because a `report` container has no matrix row. The
container is the application override rule.

## Facts measured before the change

- Measured 2026-11-04 by running the tool on `tests/fixtures/application_override_rules.xml`. The per-entry
  report names `Override-443` as a `report` entry with `captured: application, description,
  destination_addresses, destination_zones, disabled, port, protocol, source_addresses, source_zones`.
- `MANUAL_SETUP_REPORT.txt` prints the line
  `Override-443: from=['Trust'] to=['Untrust'] source=['Internal-Network'] port=8443 protocol=tcp
  application=https disabled=False`, so the line reads seven captured keys and leaves `description` and
  `destination_addresses` unread. The fixture entry carries both: `<description>Override 8443 as
  HTTPS</description>`, and one `destination` member.
- Measured 2026-11-04 across the corpus: the application override rule is the only `report` container entry
  with a captured field no output read. It is read in two fixtures (`application_override_rules.xml` and
  `kitchen_sink.xml`), and both entries carry the same fields.
- `panos_application_override_rule` is not a resource in the pinned provider
  (`PaloAltoNetworks/panos ~> 2.0.14`, terraform v1.16.2, 128 resources), so no emitter can read this
  container and the report is the only output for its entries.
- The scan cannot measure this: a `report` container has no matrix row, so `matrix_row_for` answers `None` for
  it. The rule is held by a pin, not by the scan.

## Decision

1. `generate_manual_setup_report` prints `description` and `destination_addresses` on the override rule line,
   read through the captured object.
2. One rule states the line shape: the line prints the fields the report reads through the captured object, in
   the field order this section already uses for its override fields (the four member fields, then port,
   protocol, application, the flag, then the description). A field the entry carries no value for prints
   nothing, which is F4.3 rule 3, and `port` and `protocol` keep the `any` value the export means for a field
   the entry leaves empty.
3. The fixture gains one entry that carries neither field, so the pin covers both sides.

## Acceptance criteria

1. The report line for `Override-443` names the description the parse read, and the captured object records the
   read as an output use.
2. `destination_addresses` is read the same way, so the captured object shows no unused captured key for the
   entry.
3. The fixture entry that carries neither field prints neither field, and `captured_fields` keeps both out of
   its captured set (F4.3 rule 3).
4. The pin is one test in group 6 of `tests/test_property_coverage.py`, in the shape of
   `test_the_report_reads_the_application_filter_description_it_prints`: it names the fixture entry, the parse
   read, the line the report prints, and the scan scope. Extend the parse-read pin in
   `tests/test_parse_rules.py`, and the report pin in `tests/test_real_or_report.py`.
5. `tests/test_property_coverage.py::test_scan_scope_is_the_entries_a_matrix_row_covers` keeps the report
   container case through the new pin, which is the test that shows a `report` entry has no matrix row. It
   keeps `regions.xml` for the `count-only` container, where the field gap is still open.
6. The entry-mark rule stays green: the new fixture entry is marked by `parse_application_override_rules`,
   which stores the captured object by reference.
7. `ruff check .` is clean, `python3 -m pytest` passes, and the fixture run reports `PASS (0 FAIL, 0 WARN)`.
   Reports are not goldens, so no golden moves.
