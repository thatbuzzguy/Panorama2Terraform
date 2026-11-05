# Acceptance — F4.4: the `bookkeeping` field rule for `devices` and `templates`

## Measurement

Measured 2026-11-04 with a real run on `tests/fixtures/multi_device_templates.xml`
(`python3 src/panorama_to_terraform.py`, gate `PASS (0 FAIL, 0 WARN)`), read through `tests/conftest.py`:

- The `bookkeeping` rows are the four `parse_associations` association rows, the five scope-fact rows, and the two
  sub-shape selector rows. The report counts 7 `bookkeeping` rows for this fixture and 13 across the corpus.
- A membership entry carries no captured field, so its entry line prints `captured: name only`. Measured on
  `device-group/entry/devices/fw-1.example.com`: the read record is empty, because `_list_names` marks the entry
  with an empty object, and the association table is built from names read off the XML element before the run
  starts the outputs. The row states the relation in the detail column (`association table`).
- The entry that owns the membership container is an `emitted` row, and its block prints the list. Measured on the
  `Office-FW` entry: the read record names `description, devices, parent, templates`, and the block prints
  `devices = [ { name = "fw-1.example.com" } ]`. So `devices` is a field an output reads through the captured
  object of the entry that owns the list.
- `panos_template` declares no device field (`resource_mapping.SCOPE_SHAPE`), so `parse_templates` keeps no value
  for a template's device members and the entry line for `HQ-Networks` prints `captured: name only`. No output can
  read that field. The association is read as a table, by the location rule (`template_of`, `device_of`) and by the
  manual report section that names the templates a device takes, so it is never a captured field.
- The fixture extended so both fields of `parse_device_groups` are measured by one real run:
  `tests/fixtures/multi_device_templates.xml` gains a `templates` member on `Office-FW`. The entry line reads
  `captured: devices, templates`, the block prints `templates = [ "HQ-Networks" ]`, and the gate stays
  `PASS (0 FAIL, 0 WARN)`. No other file of the run changes but the report line, the `scope.tf` block, and the
  source name.
- Measured across the corpus, none of the 13 `bookkeeping` report entries carries a captured field, so the rule
  moves no report bytes.

## The rule this slice states

The scan scope rule in `docs/COVERAGE_MATRIX.md` §1 says the output that reaches an entry outside the scan scope
must read the field it names. For a `bookkeeping` row there is no output and no captured object, so the rule is:
a `bookkeeping` entry line names no field, because the fact the row records is a relation between the entry and the
container that lists it, and the entry carries no value for that relation. The row states the relation in the detail
column, and the entry line prints `captured: name only`: the membership entry contributes its name, which is the
row identity (`entry_coverage.NON_FIELD_KEYS`). The value of the relation belongs to the entry that owns the
membership container, so a `bookkeeping` field is honest only when that owning entry is covered by an `emitted` row
whose emitter reads the list through that entry's captured object. Where the owning entry's row declares no field
for the list, the parse method keeps no value for it, because no output can read it. So `devices` and `templates`
are fields the output reads through the captured object of the entry that owns the list, and never fields of the
entry the list holds.

The option not taken — naming `devices` on the membership entry's line, because `parse_associations` reads the
membership container — is refused by the measurement: the parse marks those entries with an empty object, so the
line would name a field the entry carries no value for, and the read that builds the table happens off the element
at parse time, which the property scan does not count.

## Acceptance criteria

1. The measurement above is recorded in the owner document, `docs/COVERAGE_MATRIX.md` §1, as the fourth shape of
   the scan-scope rule. `docs/ARCHITECTURE.md` §2.4 keeps only the destination fact and the link to §1.
2. `entry_coverage.captured_part` names no field for a `bookkeeping` row, through a data set in the same shape as
   `PRINTS_VALUE_KINDS`, so no writer branch decides the shape per kind. `gap_fact` reads the same captured part, so
   the console names the same words.
3. `parse_associations` marks each membership entry with an empty object, and `parse_templates` keeps no device
   value, so `entry_coverage.captured_fields` answers empty for these entries. The modules state the rule the
   measurement shows: the table is read as a table, not through a captured object.
4. `tests/fixtures/multi_device_templates.xml` gains a `templates` member on `Office-FW`, so one real run measures
   both fields of `parse_device_groups` through a printed block, and the entry line names them.
5. `tests/test_property_coverage.py` group 6 gains gap 8, in the shape of the group 6 pins: the fixture entry, the
   empty object the parse marked, the entry line that names no field, the owning entry that carries the value, and
   the block that prints it.
6. `tests/test_property_coverage.py::test_scan_scope_is_the_entries_a_matrix_row_covers` names the `bookkeeping`
   shape: `matrix_row_for` answers None for the membership entry, so the scan measures nothing there, and the pin
   is the only thing that can keep the field honest.
7. The entry-mark rule stays green, the report line shape, the console line shape, the exit codes, and the eight
   destination kinds are unchanged, and no destination kind moves.
8. The extended fixture run reports `PASS (0 FAIL, 0 WARN)`, the entry line for `Office-FW` reads
   `captured: devices, templates`, and the membership entry line reads `captured: name only`.
9. `ruff check .` is clean and `python3 -m pytest` passes. No golden is regenerated: the golden set pins `.tf`
   paths and bytes only, and no golden holds this fixture.
10. Tracking markdown after the commit: `backlog.md` loses the closed `bookkeeping` line, `to-do.md` closes this
    feature and names the next one (the credential rule single statement), `agent-status.md` records the position
    and the pins changed, `PLAN.md` names the rule that now exists for `bookkeeping`. ASD-STE100, no test counts
    outside `agent-status.md`.
