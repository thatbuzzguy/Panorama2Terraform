# Acceptance — F4.4: the `count-only` field gap for `parse_regions`

## Measurement

Measured 2026-11-04 against the pinned provider `PaloAltoNetworks/panos ~> 2.0.14`, read through
`tests/conftest.py::provider_schemas` (`terraform providers schema -json`):

- 128 resources and 128 data sources. No type in either kind names `region`.
- `panos_address` declares no `region` attribute, so a region entry cannot reach output through the
  address row either.

So no emitter can exist for a region entry, and the `region` row cannot become an `emitted` row: the
matrix row set is exactly `EMITTED_TYPES`, and only an `emitted` row can name a property. No
speculative emitter is built. The rule must therefore be on the report side.

## The rule this slice states

A `count-only` row has no matrix row and no report section, so the per-entry report line is the only
output its entry reaches. The line is honest only when it prints the value of each field it names, read
through the captured object, in the sorted field order the report already uses
(`entry_coverage.captured_fields`). The read through the recorded object is the property use the
property scan counts. A field the entry carries no value for is not a captured field (F4.3 rule 3), so
the line prints `captured: name only` when it has none.

The rule is stated in one owner document, `docs/COVERAGE_MATRIX.md` §1, and every other document links
to it. `docs/ARCHITECTURE.md` §2.4 states only the destination fact and the link.

## Acceptance criteria

1. The measurement above is recorded, and the row stays `count-only`: no emitter is built for a region.
2. `src/entry_coverage.py` holds the rule: the report line prints the captured value for a `count-only`
   row, read through the captured object. `row_for` carries the captured object so the line can read
   through it. The other two gap kinds are unchanged: a skipped entry is recorded with no captured
   object, and an unaccounted entry has no mark, so only a `count-only` row can print a value.
3. The console fact uses the same words as the report line, so the console and the report cannot
   disagree (`docs/ARCHITECTURE.md` §3.2). The console line shape — `  - <scope>  <position>
   <identity>  <fact>` — is unchanged, and no module states a second shape.
4. `tests/test_property_coverage.py` group 6 gains one pin on `tests/fixtures/regions.xml`, in the shape
   of `test_the_report_reads_the_application_filter_description_it_prints`: the entry, the read the parse
   made, the report line that prints the field, the read through the captured object, and the row that
   answers `matrix_row_for` as None.
5. `tests/test_property_coverage.py::test_scan_scope_is_the_entries_a_matrix_row_covers` stays honest
   with the decision: the scan scope rule is unchanged (a `count-only` row has no matrix row, so it is
   not a finding), and the pin no longer claims the region field is unread, because the only output for
   that entry now reads it.
6. The entry-mark rule stays green (`tests/test_entry_coverage.py`), the exit codes are unchanged, and a
   `count-only` row stays a gap row: the gap section still lists it.
7. The regions fixture run reports `PASS (0 FAIL, 0 WARN)`, and the report names the region entry with
   the value it captured: `captured: addresses=[US, CA, MX]`.
8. `ruff check .` is clean and `python3 -m pytest` passes. No `.tf` output changes, so no golden is
   regenerated: the golden set pins `.tf` paths and bytes only.
9. No fixture changes, because the rule names no new output use and the fixture already holds the field.
10. Tracking markdown after the commit: `backlog.md` loses the closed `count-only` line, `to-do.md`
   closes this feature and names the next one (the nested-block `parent` read rule), `agent-status.md`
   records the position and the pins changed, `PLAN.md` names the rule that now exists for `count-only`.
    ASD-STE100, no test counts outside `agent-status.md`.
