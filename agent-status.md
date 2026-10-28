# Agent Status

## Current position

F6.2 (ownership as data, the repeated-name rule) is complete and committed. No feature is in
progress. The next feature in `PLAN.md` is F6.3 (the reference between units as an edge list). F6.1 and
F6.2 name the unit and the owner and write no directory, so the write path and the gate rule that reads
the two data files are still open.

State at the commit: `ruff check .` clean, `pytest` 997 passed (961 before this feature, 36 added),
both golden `.tf` sets byte-identical, report and record determinism pinned, exit codes unchanged (0,
input refusal 1, argument error 2), every test offline. The report bytes changed for the three fixtures
with a finding group; no other report body changed.

## What F6.2 changed

- `ownership.py` (new): `OWNERSHIP_FILE`, `FIELD_ORDER`, `FACT_KEYS` (read through
  `container_coverage.SCOPE_FACT_KEYS`, the same order `unit_manifest.FACT_KEYS` holds), `KINDS`,
  `OVERRIDE_VALUES`, `FLAG_KEY`, `FINDING_HEADING`, `FINDING_RULE`, the reason strings
  (`NO_RELATION`, `FLAG_NOT_ANCESTOR`, `FLAG_FORBIDS_OVERRIDE`), `row_facts`, `row_key`, `in_chain`,
  `override_value`, `scan_row`, `decide`, `is_ancestor`, `build_rows`, `render`, `parse_rows`,
  `findings`, `finding_line`. The module defines no identity key and no naming rule: it reads
  `state_coverage.ownership_key` and takes `TerraformGenerator.sanitize_name` as an argument.
- `panorama_to_terraform.py`: `parse_service_objects` captures `disable_override`, and
  `generate_service_objects` prints it after `description`, as the string the parse read.
  `generate_conversion_report` gained the repeated-name section, after the shadow section and before the
  two state sections. `main()` builds the rows and writes `OWNERSHIP.json` only when it has content.
- `resource_mapping.py`: the `panos_service` row gained `disable_override`, so the declared property and
  the emitter read agree.
- Tests: `tests/test_ownership.py` (36 tests, seven groups: the row scope, the declaring unit and the
  join, the owner rule, the service leg, the record shape, determinism and the content rule, the report
  section). `tests/test_unit_manifest.py::test_the_manifest_is_one_file_for_the_codebase` now names both
  data files. New fixture `tests/fixtures/ownership_override.xml`.
- Docs: `docs/CODEBASE_ASSEMBLY.md` §2, §4, §5 and §14, `docs/ARCHITECTURE.md` §1, §3.5, §4.5,
  `docs/USAGE_GUIDE.md`, `README.md`.

## Facts measured during F6.2

- The corpus writes 204 ownership rows. Findings come from three fixtures only:
  `edge_dup_names_across_dgs.xml` (2), `ownership_override.xml` (4), `report_grouping.xml` (6). Seven
  groups, twelve lines, no false positive.
- The pinned provider schema declares `disable_override` for 25 resource types. The coverage matrix names
  the property for two rows, `panos_address` and `panos_service`. `terraform providers schema -json`
  against the committed provider fixture confirms the 2026-10-27 measurement.
- A test that needs the read record must run the pipeline in process, the way the shadow and manifest
  tests do, because `RecordingDict` records during the parse.
- `tests/test_property_coverage.py::test_measured_reads_equal_the_declared_properties` is green for
  `panos_service` only because the new fixture carries the flag on a service entry: the matrix row now
  names the property, so the corpus must show a read of it.
- A single fixture cannot print all four report sections at once, so the section-order test feeds four
  scan results to `generate_conversion_report`.
- `main()` builds the parent ledger from entry names and never runs the parse methods, so a parent-source
  row states `override` as `unknown` while the owner rule still names the parent as the ancestor.
- The CLI takes no flag for the record, so `--help` text is unchanged; the test asserts the help does not
  name `OWNERSHIP`.

## Rules to keep when writing documents

- One owner document per rule; every other document links to it.
- Machine-readable tables are code. A document explains a table and never restates it
  row by row, so a regenerated table cannot drift.
- No test counts in a document. A document names the test that pins a rule; the
  count lives in `agent-status.md` and the git history.
- A claim about what the tool does must name the module or the test that holds it. A
  feature id is written only when a module or a test uses it as a name.
- ASD-STE100 Simplified Technical English, no marketing voice, no emoji.
- A historical record (the audit report) keeps its findings and states the current
  state separately, so a reader does not take an old finding as a fact.
- A record is data, so a document describes its fields and never restates a record. The
  example in `docs/USAGE_GUIDE.md` is an illustration with a shortened hash, not a pin.

## Watch for Epic 6

- F6.3 needs the target unit of an edge. `ownership.py` names the declaring unit and the owner, so the
  edge can point at a directory the manifest already names; the reference record is names per unit today,
  so the pair shape must be decided. `unit_manifest.facts_of` is the identity both should read, so no
  second identity key appears.
- F6.3 should decide whether the reference fact stays one fact (outside the run) or splits into two
  kinds (outside the run, ambiguous inside the run). The ownership scan cannot settle this, because a name
  a unit uses but does not declare writes no ownership row.
- The block reader in `sanity_checks.py` serves every kind, so the `import` (F6.4) and `action` (F6.7)
  rules must use `blocks(files, kinds)`; no second block reader should appear.
- A gate rule that reads a data file has no rule today, because the gate reads `.tf` files only. If a
  codebase feature makes a data file a gate input, the file set statement in `ARCHITECTURE.md` §4.5 and
  both no-change tests must change together.
- The import position for the four `*_policy_rules` types must be the position the live config holds,
  and the F3.5 rulebase decision gates it.
- Actions need Terraform 1.14 or later; the committed goldens declare no Terraform minimum.
- The credential rule needs one statement that covers both the fetch layer and the generated provider
  block.
- The value-to-variable mapping must be a pinned table, the way `LOCATION_SCHEMA` and
  `DATA_SOURCE_SCHEMA` are.
- The prune action still needs the record directory decided. A state record references nothing, so it
  prunes nothing, and the prune rule reads a record file, not one record.
- A coverage fact that comes from a run must be read from the run's ledger, so the scan tests run the
  pipeline in process.
