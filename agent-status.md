# Agent Status

## Current position

F6.3 (the reference between units as an edge list, and the unit order as data) is complete and committed
(`b098c8b`). No feature is in progress. The next feature in `PLAN.md` is F6.4 (import blocks). F6.1, F6.2
and F6.3 name the unit, the owner, the pair and the order, and write no directory, so the write path and
the gate rule that reads the three data files are still open. The outputs rule for a name another unit
owns is still open in `backlog.md`.

State at the commit: `ruff check .` clean, `pytest` 1030 passed (997 before this feature: 32 added in
`tests/test_reference_edges.py`, and the new fixture adds one parametrized case), both golden `.tf` sets
byte-identical, report and record determinism pinned, exit codes unchanged (0, input refusal 1, argument
error 2), `--help` unchanged, every test offline. The report bytes change only for the fixture with a
cycle finding; no other report body changed.

## What F6.3 changed

- `reference_edges.py` (new): `EDGE_FILE`, `FIELD_ORDER`, `FACT_KEYS` (read through `unit_manifest`),
  `LEVEL_KEYS` (the F3.9 level order), `CYCLE_HEADING`, `CYCLE_RULE`, `CYCLE_REASON`, `NO_RANK`,
  `build_rows`, `render`, `parse_rows`, `graph`, `cycles`, `findings`, `cycle_line`, `dependencies`,
  `order`. The module defines no naming rule, no identity key and no resolution rule: it takes
  `TerraformGenerator.sanitize_name` as an argument and reads the unit identity through `unit_manifest`.
- `unit_manifest.py`: `FIELD_ORDER` gained `rank` and `after` at the end, `parse_rows` validates them as
  a position and a list of directories, and rule 5 states that the row shape lives here while the order
  rules live in `reference_edges.py`.
- `panorama_to_terraform.py`: `main()` builds the edge rows, fills the two order fields on the manifest
  rows before the report (because a cycle finding reads its grouping facts through the manifest row),
  writes `REFERENCE_EDGES.json` only when it has content, and passes the cycle findings to
  `generate_conversion_report`, which prints them in a new section after the repeated-names section and
  before the state sections.
- Tests: `tests/test_reference_edges.py` (32 tests, six groups: the edge row and the join, the reference
  fact, the acyclic rule, the unit order, the report section and the exit codes, the gates and
  determinism). `tests/test_unit_manifest.py::test_the_manifest_is_one_file_for_the_codebase` now names
  the three data files, and the row-shape pins name the two added fields. New fixture
  `tests/fixtures/reference_cycle.xml`.
- Docs: `docs/CODEBASE_ASSEMBLY.md` §1, §2, §3, §5, §6 and §14, `docs/ARCHITECTURE.md` §1, §3.6, §4.3 and
  §4.5, `docs/USAGE_GUIDE.md`, `README.md`.

## Facts measured during F6.3

- The corpus writes seven edge rows from three fixtures: `kitchen_sink.xml` (3),
  `multi_device_templates.xml` (2), `reference_cycle.xml` (2). 109 names are recorded across the corpus,
  and only the ones that join to an ownership row become edges.
- No fixture but `reference_cycle.xml` produces a cycle finding, and no fixture produces a row that names
  one unit, so the self-reference rule and the acyclic rule are pinned on their own input as well as on
  the corpus.
- `after` comes from three bases, and each base has a fixture: `ownership_override.xml` for the owner
  before the override, `multi_device_templates.xml` for the level chain, `kitchen_sink.xml` for the edge.
- `rank` is a total order for every acyclic fixture in the corpus, and the two units of the cycle fixture
  are the only units that state 0.
- A cycle fixture must put the referrer entry in the same unit as the declaring entry, because a
  template-scoped zone and its device are two units, and the reference rule keeps a device-declared name
  inside the device that declared it (`ARCHITECTURE.md` §4.3 rule 1).
- `findings` reads the grouping facts through the manifest row, so the report can group a cycle with the
  F3.9 rule without a second fact order, and `render` writes only the four declared fields.
- The record is a data file, so no report names it, and the cycle line names units by their directory
  instead of by a field name.

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

- F6.4, F6.5, F6.6 and F6.7 still write no directory. The three data files name the unit, the entry and
  the pair, so the write path is the step that turns a `directory` field into a real directory.
- The block reader in `sanity_checks.py` serves every kind, so the `import` (F6.4) and `action` (F6.7)
  rules must use `blocks(files, kinds)`; no second block reader should appear.
- A gate rule that reads a data file has no rule today, because the gate reads `.tf` files only. If a
  codebase feature makes a data file a gate input, the file set statement in `ARCHITECTURE.md` §4.5 and
  the no-change tests must change together.
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
- A cycle test needs the referrer entry and the declaring entry in the same unit, for the reason recorded
  above.
