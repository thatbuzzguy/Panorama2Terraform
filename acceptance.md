# Decision — the application override report line — acceptance criteria

This slice applies the rule `docs/COVERAGE_MATRIX.md` §1 states to the next `report` container: a report line must
read the field it prints through the captured object. The container is the application override rule.

## Facts measured before the change

- Measured 2026-11-04 by running the tool on `tests/fixtures/application_override_rules.xml`. The per-entry report
  names `Override-443` as a `report` entry with `captured: application, description, destination_addresses,
  destination_zones, disabled, port, protocol, source_addresses, source_zones`.
- `MANUAL_SETUP_REPORT.txt` prints the line
  `Override-443: from=['Trust'] to=['Untrust'] source=['Internal-Network'] port=8443 protocol=tcp
  application=https disabled=False`, so the line reads eight captured keys and leaves `description` and
  `destination_addresses` unread. The fixture entry carries both (`<description>Override 8443 as HTTPS</description>`,
  and one `destination` member).
- `panos_application_override_rule` is not a resource in the pinned provider (`PaloAltoNetworks/panos ~> 2.0.14`,
  terraform v1.16.2, 128 resources, read at `block.attributes`), so no emitter can read the container and the
  report is the only output for its entries.
- The scan cannot measure this: a `report` container has no matrix row, so `matrix_row_for` answers `None` for it.
  The rule is held by a pin, not by the scan.

## Decision

1. `generate_manual_setup_report` prints `description` and `destination_addresses` on the override rule line,
   through the captured object, in the field order the report already uses for its other override fields.
2. A captured field with no value prints no field, so an entry with no description prints nothing for it (F4.3
   rule 3). The pin must cover both an entry with the value and one without.

## Acceptance criteria

1. The report line for `Override-443` names the description the parse read, and the captured object records the
   read as an output use.
2. `destination_addresses` is read the same way, so the captured object shows no unused captured key for the entry.
3. An entry that carries neither field prints neither, and its captured object records no read for them.
4. The pin is one test in group 6 of `tests/test_property_coverage.py`, in the shape of
   `test_the_report_reads_the_application_filter_description_it_prints`: it names the fixture entry, the parse read,
   the line the report prints, and the scan scope. Extend the parse-read pin in `tests/test_parse_objects.py` or
   `tests/test_parse_rules.py`, and the report pin in `tests/test_real_or_report.py`.
5. `ruff check .` is clean, `python3 -m pytest` passes, and the fixture run reports `PASS (0 FAIL, 0 WARN)`.
