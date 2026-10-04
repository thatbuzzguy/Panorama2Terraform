# Acceptance Criteria — F2.8: Coverage matrix

## Goal
Track, by test, that every provider v2 resource the converter emits is
fed by a known Panorama XML element. Today the mapping between "XML
element in the export" and "provider resource in the output" exists only
in the parser code and the goldens; nothing states it, and nothing would
catch an emitter silently going away. F2.8 makes the
provider-resource ↔ Panorama-XML-element matrix the tracked source of
truth and gives every supported row a fixture test that runs the full
pipeline (parse + generate) on a dedicated fixture.

## Design

`resource_mapping.py` gains `COVERAGE_MATRIX`: one row per emitted
provider resource type. A row records:

- `resource` — the provider v2 resource type (must be in
  `EMITTED_TYPES`).
- `xml_element` — the Panorama XML element (tag path) whose `<entry>`
  feeds the resource (for example `address/entry`,
  `security/rules/entry`, `tunnel/ipsec/entry`).
- `xml_name` — the `<entry name=...>` in the row's fixture that feeds
  the resource.
- `emitted_name` — the `name` attribute the emitted resource must
  carry. Equal to `xml_name` except where the converter derives a
  name (the `.0` layer-3 subinterface).
- `fixture` — the XML fixture under `tests/fixtures/` that exercises
  the row.
- `output_file` — the `.tf` file (relative to the output directory)
  that must contain the resource block.

`tests/test_coverage_matrix.py` enforces the matrix:

- the row set is exactly `EMITTED_TYPES` (one row per type; no row for
  a type the converter does not emit; a report-only type can never
  gain a row without first leaving `REPORT_ONLY_TYPES`).
- every row's fixture exists and actually contains the row's
  `xml_element` with an entry named `xml_name`.
- for every row, running the converter on the fixture emits a
  `resource "<type>"` block in `output_file` whose body carries
  `name = "<emitted_name>"`.

`docs/COVERAGE_MATRIX.md` renders the matrix as a table and records
the maintenance duty: an emitter change that adds, renames, or drops a
resource type must update the matrix in the same change; the drift
tests fail when the two disagree.

## Definition of Done

1. **Matrix completeness.** The matrix has exactly one row per
   `EMITTED_TYPES` type (20 rows). A test pins the exact set match.
2. **Element grounding.** A test proves each row's `xml_element`
   exists in the row's fixture with the named entry — the element
   column cannot drift from the real Panorama structure.
3. **Row fixture tests.** For all 20 rows, the pipeline run on the
   row's fixture emits the provider resource with the expected
   `name` in the expected output file.
4. **Docs.** `docs/COVERAGE_MATRIX.md` holds the human-readable matrix
   plus the maintenance duty; the README links it.
5. **Tracking.** PLAN.md, to-do.md, and agent-status.md record the
   landing; commit with an ASD-STE100 message.

## Gate

- `ruff check .` clean
- `pytest` green (new matrix tests plus all existing gates)
- `terraform validate` green on the sample and kitchen-sink outputs
