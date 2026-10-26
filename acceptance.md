# Acceptance Criteria — F4.3 Per-Entry Conversion Report

Scope: F4.3 only. The parse side records which entries each parse method read
and what it captured from each entry. `CONVERSION_REPORT.txt` states one line
per entry: source line, object type, entry name, destination, and captured
fields. An entry that produced no output is reported as a gap.

Out of scope for this task (tracked in PLAN.md Epic 4 and backlog.md):
- F4.4 property-level coverage: the property matrix per emitter, the
  `EMITTED_TYPES` reconciliation, `resource_name_map`, `tests/COVERAGE.md`.
- Property entries inside a config-object entry: F4.2 AC-3.2 assigns them to
  F4.4, so this task counts them on the parent row instead of listing them.
- Field-by-field extraction gaps (application filter `description`, schedule
  `description`, service `disable-override`, NAT `service` member form): F4.4
  owns the field matrix. This task reports the entry-level result only.
- Gate severity: a coverage gap is an operator action, so this task adds no
  FAIL finding and changes no F4.1 exit code.
- Report redesign for the existing reports (F3.9 layout stays as it is).

---

## AC-1 — Every parse method marks the entries it reads

1. `entry_coverage.EntryLedger` holds one mark per entry a parse method read,
   keyed by the element. The ledger is built on the parsed source, so it uses
   the same line map F4.2 added.
2. `PanoramaParser.mark(entry, captured, detail='', destination=None)` records
   the entry and returns the captured object, so a parse method marks at the
   point it builds the object.
3. `PanoramaParser.mark_skipped(entry, reason)` records an entry a parse method
   visited and chose not to model.
4. The mark stores the object by reference. Fields a method adds after the mark
   are recorded, because the report is built after the parse finishes.
5. Every parse method that reads config-object entries marks each entry it
   visits. A parse method that reads entries without marking them fails the
   gate. Pinned by a test that reads each parse method's source (following the
   helper calls it makes) and by a test that runs the parse methods over the
   corpus.

## AC-2 — One entry is one report row

1. One entry is one `<entry name>` element — the logical entry, not the physical
   lines it spans. The reported line is the entry's opening tag
   (`ParsedSource.line_of`).
2. Object type is the entry's container path from the config root, which is the
   F4.2 `section_path` rule. No second naming rule.
3. Destination is the destination kind of the container table row that covers
   the container. The longest matching row wins, so a sub-shape row beats a
   general row.
4. A per-entry destination wins over the row when the parse method knows
   better: `report_only` content is `report`, and a skipped entry is `skipped`.
5. An entry inside a config-object entry is a property level (F4.2 AC-3.2). It
   is not a report row; the parent row shows the count of property entries.
6. Entries under `predefined` are not report rows (F4.2 rule). The header gives
   the count so the report does not look incomplete.
7. A scope entry (an entry whose container is one of `SCOPE_CONTAINERS`) is
   `bookkeeping`: it defines a scope, so it is not an object inside one. The
   `parse_device_groups` row is `bookkeeping` for the same reason: a device
   group name reaches the output through `location`, not as a resource.
8. Two destination kinds are added for an entry: `skipped` and `unaccounted`.
   The documented set is now eight, and one test pins it.

## AC-3 — Captured fields

1. Captured fields are the keys of the object the parse method built from the
   entry, minus the entry name and the four scope facts (F3.1, F3.2).
2. A key with no value is not a captured field: the report shows what the parser
   actually took.
3. A field captured inside a type sub-shape is reported under the object key the
   parser stored it in (`fields`), not under the XML tag.
4. The report names the captured fields in sorted order. An entry with nothing
   but its name says `captured: name only`.
5. A captured field that reached no output is a gap. The gap rule: a destination
   kind that writes nothing (`count-only`, `skipped`, `unaccounted`).

## AC-4 — `CONVERSION_REPORT.txt`

1. One line per report row. Fields, in this order: source line, object type,
   entry name, destination, detail, captured fields.
2. Detail is the table row note, or the resource type for an emitted row. A mark
   detail is appended when the parse method stated one.
3. Rows are grouped by the F3.9 scope rule (`_report_scope_path`), so a section
   names only the scope the export declares. Entries inside a section are in
   file order (line, then object type, then name).
4. The header states the rule, the input file name, the totals per destination
   kind, and the property-entry and predefined counts.
5. A gap section lists every row whose destination writes nothing, in the same
   order as the entry sections.
6. The report names the input file name, never the path.
7. Two runs on the same input write the same bytes.
8. The report is written on every run that has at least one report row. A run on
   an input with no entries writes no report file.
9. The console prints the entry totals and one line per gap when a run has gaps,
   and prints nothing extra when it has none.
10. A gap does not change the conversion exit code. The F4.1 gate still decides
    the exit code.

## AC-5 — Tests pin the rules

1. Mark mechanism: `mark` records and returns the object; a field added after
   the mark is recorded; `mark_skipped` records the reason.
2. Read-but-not-marked fails: a parse method that reads entries without marking
   them fails the test; on the corpus, every config-object entry in a section
   container is marked. A scope entry is not a config-object entry, so the rule
   does not reach it.
3. Destination rules: table row wins, per-entry override wins, scope entry is
   bookkeeping, property entries are counted, `predefined` is excluded.
4. Captured fields: sorted, value-only, scope facts excluded.
5. The gap section: a fixture where an entry is read and nothing is written (the
   `parse_regions` gap) plus an entry with no name.
6. Report bytes: one line per row, header totals, file name only, byte-identical
   between two runs.
7. The conversion report uses the same grouping rule as the other two reports.
8. The corpus: every committed fixture and `sample_panorama_config.xml` produces
   no unaccounted config-object entry, except the fixture that tests a container
   the table does not cover (`unknown_containers.xml`), where the report lists
   those entries.
9. No report file when the input has no entries. No console line when there is
   no gap. Exit code 0 for a run with gaps.

## AC-6 — Gate stays green

- `ruff check .` clean.
- `pytest` passes. The F4.2 tests change only where a criterion changed (the
  destination-kind set and the `parse_device_groups` row).
- Golden `.tf` output unchanged for every fixture.
- `terraform validate` passes.
- Exit codes unchanged: 0 for a clean run, 1 for a broken output or a refused
  input.
- `docs/ARCHITECTURE.md` §2.4 lists the eight kinds and points at the ledger;
  §3 states the entry-mark rule and names the test that pins it. README names
  `CONVERSION_REPORT.txt` in its output list.

---

## Audit Against The Current Code (2026-10-20)

| Criterion | Current state | Action |
|---|---|---|
| AC-1 | No per-entry record. `identity_of` is called per object by 31 parse methods, but a mark needs the entry and the object together, and skipped entries are never seen. | New `entry_coverage.py` with `EntryLedger`; `mark` / `mark_skipped` on the parser; mark at each parse method's entry read site. |
| AC-2 | `container_coverage.CONTAINER_TABLE` has the destination per container, but nothing joins an entry to a row. | `covering_row` + `entry_destination` in the module; longest match. |
| AC-2.7 | The `parse_device_groups` row is `count-only`, so every device group would read as a gap. | Change that row to `bookkeeping`. A device group is the scope, not an object inside one. |
| AC-3 | Nothing records which fields a parse method took. | Captured fields come from the object the method built, at mark time. |
| AC-4 | `MANUAL_SETUP_REPORT.txt` has a coverage section for containers (F4.2), but no per-entry report. | New `CONVERSION_REPORT.txt`, rendered by `TerraformGenerator.generate_conversion_report` so the F3.9 grouping rule is shared. |
| AC-5 | 539 tests pass, ruff clean, goldens and `terraform validate` green. | Must stay green. |

Corpus state measured before the change: every section container in every
committed fixture is covered by a table row (F4.2 AC-5.5), so every
config-object entry in a section container is read by a parse method. The
corpus should therefore report no unaccounted entry after the marks land. The
fixtures `unknown_containers.xml` (unaccounted entries), `regions.xml`
(read, nothing written) and `robust_empty_names.xml` (entry with no name) are
the corpus cases the report will show; `tests/fixtures/entry_gaps.xml` is the
one fixture added to demonstrate the gap section in one file.

---

## Result (2026-10-20) — F4.3

To be filled when the work is done.

## Result (2026-10-20) — F4.3

- Implementation: `entry_coverage.py` (ledger, row rules, `entry_line`, report text,
  console lines). `PanoramaParser.mark` / `mark_skipped`, the `ledger`, marks in
  every parse method at the point it builds the object,
  `TerraformGenerator.generate_conversion_report`, `main()` prints the entry totals
  and one line per gap.
- `container_coverage.DESTINATION_KINDS` gained `skipped` and `unaccounted`;
  `SCOPE_FACT_KEYS` is now named so the captured-field rule uses it; the
  `parse_device_groups` row is `bookkeeping` (the name reaches the output through
  `location`).
- Tests: `tests/test_entry_coverage.py` (26), in the five acceptance groups; new
  fixture `tests/fixtures/entry_gaps.xml`.
- Gate: ruff clean. pytest 470 passed. Both golden sets byte-identical. terraform
  validate green on all four outputs. A gap does not change the exit code
  (`test_a_gap_does_not_change_the_exit_code`).
- Two test expectations changed for the criteria that moved: the destination-kind set
  in `tests/test_container_coverage.py` (five to eight), and the
  `parse_device_groups` row destination (`count-only` to `bookkeeping`).
- Docs: `docs/ARCHITECTURE.md` §2.4 (eight destinations, the two per-entry kinds),
  §3 step 4 (the mark rule), new §3.2 (the per-entry report rules). README output
  list names `CONVERSION_REPORT.txt`.
- Report line shape, verified on `tests/fixtures/kitchen_sink.xml`:

  ```text
  Per-entry report: 78 entries read
    emitted        53
    report         8
    inventory      6
    count-only     1  (writes nothing: gap)
    bookkeeping    8
    nested-block   0
    skipped        2  (writes nothing: gap)
    unaccounted    0  (writes nothing: gap)
    line   21  address-group/Reference-Only  skipped  panos_address_group - reference pointer (id only)  captured: name only
    line   26  address/Web-Server-1           emitted  panos_address                       captured: description, tags, type, value
  ```

## Open items for F4.4

- Property entries inside a config-object entry are counted on the parent row, not
  listed. The matrix must state them per property.
- `COVERAGE_MATRIX`, `EMITTED_TYPES` and `resource_name_map` are not reconciled.
- `name_ref` first-wins resolution is unchanged, so a name declared in two device
  groups resolves to the first.
- The mark rule is an AST check over parse methods and the helper calls they make; it
  does not follow a path held in a variable.
