# Agent Status

## Current position

F6.1 (the unit boundary as data, the codebase manifest) is complete and committed. No feature is in
progress. The next feature in `PLAN.md` is F6.2 (ownership as data), which is not started. F6.1 names
the directory a codebase needs and writes no directory, so the write path and the gate rule that reads
the manifest are still open.

State at the commit: `ruff check .` clean, `pytest` 960 passed (928 before this feature, 32 added),
both golden sets byte-identical, report and record determinism pinned, exit codes unchanged (input
refusal 1, argument error 2), every test offline.

## What F6.1 changed

- `unit_manifest.py` (new): `MANIFEST_FILE`, `FIELD_ORDER`, `FACT_KEYS` (read through
  `container_coverage.SCOPE_FACT_KEYS`), `NAME_LEVELS`, `DIGEST_HEX`, `SHARED_UNIT`, `UNNAMED`,
  `facts_of`, `fact`, `unit_name`, `identity_digest`, `directory_name`, `build_rows`, `render`,
  `parse_rows`. The module defines no sanitizing rule: it takes `TerraformGenerator.sanitize_name` as
  an argument, so the §5 rule stays one rule.
- `panorama_to_terraform.py`: `name_ref` is now a recording wrapper around `_resolve_reference`, with
  `_is_outside_reference`, `unit_references()`, `self._unit_references` in `__init__`, and the
  `referrer` argument at 34 call sites. `main()` writes `CODEBASE_MANIFEST.json` after the provenance
  record, only when the rows have content.
- Tests: `tests/test_unit_manifest.py` (32 tests, seven groups: the unit, the naming rule, the row
  shape, the reference names, the no-change rule, the CLI and the content rule, determinism).
- Docs: `docs/CODEBASE_ASSEMBLY.md` §1, §3 and §14, `docs/ARCHITECTURE.md` §1, §3.4, §4.3, §4.5, §5
  and §6, `docs/USAGE_GUIDE.md`, `README.md`.

## Facts measured during F6.1

- `tests/fixtures/report_grouping.xml` shows 11 units and 23 ledger rows, and 4 units have a recorded
  reference name. Two units hold the same unit name (`fw-2.example.com`) in two device groups, so the
  digest alone keeps their directory names apart.
- The unit whose four facts are empty is `shared_be5be69f` in that fixture. The sample run's shared
  unit carries the placeholder device, so it is `shared_0bc98741`: the digest is the identity, not the
  name.
- The sample run shows 2 units and 21 entries: `Shared` (4) and `Production-DG` (17, 11 recorded
  names).
- With `--data-blocks panos_address,panos_zone`, the sample run writes 6 blocks and records 11 names.
  Every block name is a recorded name; the other 6 stayed plain because their type is not an opted-in
  scope.
- A name recorded for the shared unit comes from a referrer in the shared section, not from the shared
  chain a contextless call site resolves through.
- The F3.6 ambiguous-device case is recorded as an outside name, because the reference rule returns a
  plain string. The name is declared inside the run, so the row cannot separate "outside the run" from
  "ambiguous" until the edge list (F6.3) names the other unit.
- The gate reads `*.tf` only, so a data file cannot change a gate result or a golden byte.
  `SANITY_REPORT.txt` already contains the word `references` as a check name, and the generated
  `README.md` prose contains "directory", so the no-change test names the report bodies and the fields
  `entry_count` and `unit`, not those words generally.
- A test that wants the reference record needs both the ledger and the generator, so the test file hooks
  `TerraformGenerator.__init__` the way `conftest.run_pipeline` hooks the parser. The run must be in
  process, because the record is made during emission.

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

- F6.2 needs the owner of a repeated name, and F6.3 needs the target unit of an edge, so both need the
  unit F6.1 landed. `unit_manifest.facts_of` is the identity both should read, so no second identity key
  appears.
- F6.3 should decide whether the reference fact stays one fact (outside the run) or splits into two
  kinds (outside the run, ambiguous inside the run). The record today is names per unit; the edge needs
  (referrer unit, target unit).
- The block reader in `sanity_checks.py` serves every kind, so the `import` (F6.4) and `action` (F6.7)
  rules must use `blocks(files, kinds)`; no second block reader should appear.
- A gate rule that reads a data file has no rule today, because the gate reads `.tf` files only. If a
  codebase feature makes the manifest a gate input, the file set statement in `ARCHITECTURE.md` §4.5 and
  the no-change test must change together.
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
