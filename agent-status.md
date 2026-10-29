# Agent Status

## Current position

F6.5 (scope objects as output: one `resource` block per scope entry for the six types the pinned schema
declares for the scopes, in `scope.tf`, and the gate rule that a name inside a scope block's `location`
names a scope the run declares) is complete and committed as `F6.5: scope objects as output`. No feature
is in progress. The next feature in `PLAN.md` is F6.6 (the site data layer), which takes the template
variable literal F6.5 prints. F6.1 to F6.5 name the unit, the owner, the pair, the order, the block and
the scope object, and write no directory, so the write path and the gate rule that reads the three data
files are still open. The outputs rule for a name another unit owns is still open in `backlog.md`.

State at the commit: `ruff check .` clean, `pytest` 1141 passed (1062 before this feature: 79 added),
every existing golden `.tf` byte identical, and the two golden sets each gained one file, `scope.tf`. The
report, manifest, ownership, edge and provenance determinism rules are unchanged, exit codes are
unchanged (0, input refusal 1, argument error 2), no CLI flag changed, `CHECK_ORDER` gained
`scope_blocks` after `import_blocks`, and every test runs offline.

Test count by file, before → after: `tests/test_coverage_matrix.py` 141 → 171,
`tests/test_schema_conformance.py` 57 → 69, `tests/test_scope_objects.py` 0 → 26,
`tests/test_resource_mapping.py` 42 → 48, `tests/test_golden_files.py` 31 → 33,
`tests/test_sanity_gate.py` 78 → 80, `tests/test_ownership.py` 36 → 37.

## What F6.5 changed

- `resource_mapping.py`: six `COVERAGE_MATRIX` rows with `output_file` `scope.tf` and the emitter
  `generate_scope_objects`; `EMITTED_TYPES` and `LOCATION_SCHEMA` gained the six types, and each new
  `LOCATION_SCHEMA` row equals its `DATA_SOURCE_SCHEMA` row. New tables: `SCOPE_TYPES`,
  `SCOPE_PLACEMENT` (the parsed key that names the scope each type places itself in), `SCOPE_ANSWER` (the
  type that answers a name inside a `location`), `SCOPE_LEVEL_ORDER` (the block order inside the file),
  and `SCOPE_SHAPE` (the provider shape of each property the block prints at its own level).
- `panorama_to_terraform.py`: `SCOPE_FILE`, `generate_scope_objects`, `_scope_name_field`,
  `_scope_property`; `parse_device_groups` now captures `parent`, `devices` and `templates`, and
  `parse_templates`, `parse_template_stacks`, `parse_template_variables` and `parse_vsys` are new.
  `_scope_container_of` walks the parent map for the placement, `_variable_type` returns the
  `{kind: value}` object, `_list_names` marks the membership entries it reads, `location_data` gained the
  scope branch (branch 0), and `main()` calls the emitter after `generate_variables`.
- `entry_coverage.py`: `name_field(resource_type)` is the one rule for the field that carries an entry
  name into a block, read from `DATA_SOURCE_SCHEMA` and `REPORT_SCOPE_KEYS`. `EntryLedger.destination`
  lost the `is_scope_entry` exception, because the container table row now decides the destination.
- `container_coverage.py`: the five scope container rows read `emitted`; the membership rows stay
  `bookkeeping`, and `parse_associations` marks nothing itself.
- `sanity_checks.py`: `check_scope_blocks` and `CHECK_ORDER`, read through the one block reader;
  `check_import_blocks` now reads the name through `entry_coverage.name_field`.
- `ownership.py`: `parent_map`, `chain_of`, and the `chain` run fact on the scan row, so rule 4 can name
  an ancestor for two device groups in one source.
- `import_blocks.py` rule 4 states the name-field rule.
- Tests: `tests/test_scope_objects.py` (26 tests: emission and order, the name field, the value shape,
  the device member rule, placement and the skipped entry, the gate rule, determinism),
  `tests/fixtures/scope_objects.xml`, `tests/fixtures/ownership_parent.xml`, four scope entries added to
  `tests/fixtures/kitchen_sink.xml`, and `scope.tf` in both golden sets.
- Docs: `docs/CODEBASE_ASSEMBLY.md` §2, §4, §6, §8, §10 and §14, `docs/ARCHITECTURE.md` §1, §3.2, §3.5,
  §4.1, §4.2, §4.5 and §4.6, `docs/COVERAGE_MATRIX.md` (the row count and the six rows),
  `docs/USAGE_GUIDE.md` (the outputs table), `README.md` (the outputs list, the typical outputs, the row
  count, and the test list), and `acceptance.md`.

## Facts measured during F6.5

- Provider 2.0.14, read from the schema the `provider_schemas` fixture writes: `devices` is a list of
  objects for `panos_device_group` (`{name, vsys}`) and for `panos_template_stack` (`{name}`), `templates`
  is a list of strings, and `type` is one nested object. `terraform validate` refuses a string where the
  provider takes an object, which is why the shape is a table. `panos_device_group_parent` declares no
  `name`: its fields are `device_group`, `parent` and `location`.
- `test_data_source_schema.py::test_the_shared_types_mirror_the_resource_shape` pins that a row declares
  `name` only when the provider declares it, so `name_field` falls back to the scope field for
  `panos_device_group_parent`, and to `name` for the four `*_policy_rules` types, which print the name
  inside `location`.
- The property scan measures a row through the entries its container covers, so the two rows whose block
  carries the entry name and the location only have no read of their own to measure:
  `panos_device_group_parent` and `panos_vsys`. `test_property_coverage.py` pins the unmeasured set.
- `tests/test_coverage_matrix.py` allows an empty property list only for `panos_vsys`
  (`NAME_ONLY_ROWS`).
- Corpus facts re-measured after the change: `report_grouping.xml` has a vsys entry inside a device-group
  entry, so that entry is now `skipped` with the reason that no template holds it; the sample and
  kitchen-sink device groups list only the placeholder device, so their blocks print no `devices` line.
  `CORPUS_FINDINGS`, `GROUPING_UNITS`, `EXPECTED_FINDINGS`, `ASSOCIATIONS` and the gate console summary
  (`9 .tf files, 20 resources` for `tests/test_sanity_gate.py`) were re-read from the runs, not assumed.
- The goldens compare `.tf` files, so the new file is pinned by
  `tests/test_golden_files.py::test_golden_file_set_matches` for both cases.
- `scope.tf` is written only when it has content, so a run with no scope entry writes no file and the
  golden file set for such a run is unchanged.

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

- F6.5, F6.6 and F6.7 still write no directory. The three data files name the unit, the entry and the
  pair, so the write path is the step that turns a `directory` field into a real directory, and `scope.tf`
  is one file for the run.
- The block reader in `sanity_checks.py` serves every kind, so the `action` rule (F6.7) must use
  `blocks(files, kinds)`; no second block reader should appear.
- The gate reads `.tf` files only, so no data file is a gate input today. `scope.tf` and `imports.tf` are
  `.tf` files and are gate inputs. If a codebase feature makes a data file a gate input, the file set
  statement in `ARCHITECTURE.md` §4.5 and the no-change tests must change together.
- A field reader must read at the block's own level and stop at the closing quote, or a sub-block field or
  an escaped quote answers for the block's field. Both are pinned in `tests/test_import_blocks.py`, and the
  scope rule reads at the block's own level through the same reader.
- `SCOPE_PLACEMENT` and the location sub-block are one fact: a new scope type needs both the placement key
  and the `SCOPE_ANSWER` entry, and the emitter reads the placement key as the location, so a new row
  cannot place itself in a scope it does not name.
- The entry name is never a property. A row whose provider type declares no `name` reaches the block
  through `entry_coverage.name_field`; no emitter, gate rule, or test should state the field again.
- The import position for the four `*_policy_rules` types must be the position the live config holds, and
  the F3.5 rulebase decision gates it. F6.4 writes no block for a rule entry until both land.
- The generated `README.md` does not name `imports.tf`; the F5.5 label precedent says an opt-in shape
  labels itself.
- Actions need Terraform 1.14 or later; the committed goldens declare no Terraform minimum.
- The credential rule needs one statement that covers both the fetch layer and the generated provider
  block.
- The value-to-variable mapping must be a pinned table, the way `LOCATION_SCHEMA` and
  `DATA_SOURCE_SCHEMA` are. F6.5 prints the template variable value as a literal until it lands.
- The prune action still needs the record directory decided. A state record references nothing, so it
  prunes nothing, and the prune rule reads a record file, not one record.
- A coverage fact that comes from a run must be read from the run's ledger, so the scan tests run the
  pipeline in process.
- A cycle test needs the referrer entry and the declaring entry in the same unit, for the reason recorded
  in the git history for F6.3.
