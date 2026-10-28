# Agent Status

## Current position

F5.5 (read-through data blocks, opt-in) is complete and committed. Epic 5 is complete. No feature is
in progress; the next code feature is Epic 6 F6.1 (unit boundary as data), which needs the directory
naming rule and the manifest shape decided first (`to-do.md`). F5.5 landed the reference mechanism half
of `docs/CODEBASE_ASSEMBLY.md` §5, so F6.3 follows it.

State at the commit: `ruff check .` clean, `pytest` 928 passed (758 before this feature, 170 added),
both golden sets byte-identical, report and record determinism pinned, exit codes unchanged (input
refusal 1, argument error 2), every test offline. The data source table test keeps the fixture's skip
marker, so it skips without the terraform binary or registry access.

## What F5.5 changed

- `resource_mapping.py`: `DATA_SOURCE_SCHEMA`, 128 rows, one per provider data source type. Each row
  states whether the type declares `name`, and every `location` sub-block it declares with its fields.
  Written from `terraform providers schema -json`, not from memory. It is the complete declared shape,
  not the generator's subset `LOCATION_SCHEMA`, because the gate must refuse a sub-block the type does
  not declare and the field sets differ per type.
- `conftest.py`: `provider_schemas` (one provider schema block for both kinds) with the
  `provider_schema` and `provider_data_schemas` wrappers, so the table pin reads the same fixture the
  resource pin uses.
- `sanity_checks.py`: one block reader for every kind a rule reads (`resource`, `data`, `import`,
  `action`), `blocks(files, kinds)`, the `Block` dataclass (kind, address, `has_location`,
  `location_body`, `sub_blocks`), the `resource_blocks` and `data_blocks` wrappers, the new
  `data_blocks` check in `CHECK_ORDER` after `location_present`, `check_location_present` covering both
  kinds, and `check_references` keying a block by (kind, type, local name). `SanityReport.resource_count`
  counts resource blocks only, so the console summary line is unchanged.
- `panorama_to_terraform.py`: `data_scopes` constructor arg, `--data-blocks` (repeatable,
  comma-separated), `REFERENCE_SCOPES` (the scopes a reference resolves against), the read-through
  branch in `name_ref`, `declare_block_name` with `declare_resource_name` as the resource wrapper, the
  data block index, `generate_read_through` (`read_through.tf`, one file per run, sorted by type then
  local name, written only when it has blocks), and the `README.md` label for a run that declares
  scopes.
- Tests: `tests/test_data_source_schema.py` (135 tests, the table against the live schema) and
  `tests/test_data_blocks.py` (35 tests, eight groups: the reader, the gate rule, the reference kind
  rule, the emit path, the CLI, the reports, the label, determinism and the exit code).
- Docs: `docs/ARCHITECTURE.md` §4.3, §4.5, §4.6, §4.7 and §5, `docs/USAGE_GUIDE.md`, `README.md`.

## Facts measured during F5.5

- Among the 126 types a resource and a data source both have, no `name` flag differs. The two
  differences between the two sets are set membership only: `panos_certificate_import` and
  `panos_virtual_router_interface` have a resource and no data source; `panos_certificate` and
  `panos_predefined_dlp_file_type` have a data source and no resource. The earlier note called these
  "name-level mismatches"; that wording was wrong.
- `location` is required for all 128 data sources, and `name` is required for every data source that
  declares one (106). 22 rows declare no `name`: the settings, policy and collection shapes.
- 26 distinct `location` shapes and 20 distinct sub-block name sets across the 128 rows, so a shape
  group naming scheme would need ambiguous names. The table stays flat, one row per type, in the
  `LOCATION_SCHEMA` style.
- The shape differs per type even for the same sub-block name, so a row per sub-block name would be
  wrong; the table is per type.
- `LOCATION_SCHEMA` is a subset of each data row for the shared types. A gate rule that reads only the
  generator subset would accept a sub-block the data source does not declare, so the data table holds
  the full declared shape.
- A read-through scope turns every name outside the run into a `data` block, including a built-in such
  as `any`, because no verified built-in name table exists. The sample run with `panos_address` and
  `panos_zone` writes 6 blocks, two of them built-in. This is why a read-through run is labelled.
- A block a reference site creates enters no declaration index, so a plain reference cannot resolve to
  it; only a `data.` reference resolves to a `data` block.
- Adding a gate check changes `SANITY_REPORT.txt` bytes for every run, because the report carries one
  more row. Reports are not golden, so the determinism pins still hold.
- Every reference scope has a data row, declares `name`, and has a `location` row the generator can
  render, so the CLI's "declares no name" refusal cannot fire today. It stands for a reference scope a
  future feature adds, and the test that pins it names that.

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

- F6.1 needs the directory naming rule and the manifest data shape decided. F6.2, F6.3 and F6.4 all
  need the unit.
- The block reader in `sanity_checks.py` serves every kind, so the `import` (F6.4) and `action` (F6.7)
  rules must use `blocks(files, kinds)`; no second block reader should appear.
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
