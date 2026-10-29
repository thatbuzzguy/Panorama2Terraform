# Agent Status

## Current position

F6.6 (the site data layer: one JSON data file per site, the `.tfvars` the tool writes from it, the device
name as a variable instead of a literal, and the value-to-variable mapping as a pinned table) is complete
and committed as `F6.6: the site data layer, the value-to-variable table`. No feature is in progress. The
next feature in `PLAN.md` is F6.7 (the commit action), which needs the Terraform minimum decision.

F6.1 to F6.6 name the unit, the owner, the pair, the order, the block, the scope object and the site, and
write no directory, so the write path and the gate rule that reads the four data files are still open. The
outputs rule for a name another unit owns is still open in `backlog.md`, and so is the per-unit `.tfvars`
that names one `target` serial.

State at the commit: `ruff check .` clean, `pytest` 1169 passed (1141 before this feature: 28 added),
exit codes unchanged (0, input refusal 1, argument error 2), no new CLI flag, `CHECK_ORDER` unchanged, and
every test runs offline.

Test count by file, before → after: `tests/test_site_data.py` 0 → 27, `tests/test_sanity_gate.py` 80 → 81.

## Golden change, and why

The goldens changed for the kitchen-sink case only, and the change is the mapping, not a style:
`address_objects.tf`, `service_objects.tf`, `zones.tf`, `virtual_routers.tf` print
`ngfw_device = var.fw_2_example_com` instead of the literal, and `variables.tf` gains that variable for the
case. The sample set is byte-identical, because its only device entry is the "this device" placeholder,
which names no device and no variable (F3.5). A run that reads no mapped value writes the same bytes as
before, so `tests/test_golden_files.py` still pins the default shape for a run that names no site value.

## What F6.6 changed

- `naming.py` (new): the `ARCHITECTURE.md` §5 sanitizing rule stated in one module, because the post-run
  gate must read it without the generator. `sanitize`, `variable_name`, `variable_text`, `UNNAMED`.
  `TerraformGenerator.sanitize_name` is now a delegate, and the data modules keep taking the rule as an
  argument.
- `site_data.py` (new): `SITE_DATA_FILE`, `TFVARS_FILE`, `ROW_FIELDS`, `build_rows`, `render`, `parse_rows`,
  `value_text`, `render_tfvars`. The row joins to the manifest on `directory`, read through
  `unit_manifest.facts_of` and `unit_manifest.directory_name`.
- `resource_mapping.py`: `VARIABLE`, `LITERAL` and `VALUE_VARIABLES` next to `LOCATION_SCHEMA`. One row per
  field `LOCATION_SCHEMA` declares, so the emitter and the gate read one table.
- `panorama_to_terraform.py`: `location_field` prints one field as the table says and records the pair at the
  print site, keyed by `unit_manifest.facts_of(obj)`; `value_variables()` returns the record;
  `generate_variables()` declares the credentials plus what the run consumed; `main()` calls it after the
  emitters and writes `SITE_DATA.json` and `site.auto.tfvars`, each only when it has content.
- `sanity_checks.py`: `Block.location_values` reads a field as the block states it, `location_agrees`
  compares a mapped field by name, `check_variables` reads both directions, and the module imports `naming`
  instead of restating the rule.
- Tests: `tests/test_site_data.py` (new), `tests/test_variables.py`, `tests/test_sanity_gate.py`,
  `tests/test_scope_objects.py` (the new position of `variables.tf`), `tests/test_unit_manifest.py`,
  `tests/test_reference_edges.py` (one output directory per fixture, so a stale `.tf` file cannot answer for
  a run), `tests/test_multi_device_template.py`, `tests/test_multi_vsys_location.py`.
- Docs: `docs/CODEBASE_ASSEMBLY.md` §3 rule 4, §6, §7 rule 5, §8, §9, §13 and §14, `docs/ARCHITECTURE.md`
  §1, §3.7, §4.1, §4.2, §4.5, §4.6, §5 and §6, `docs/USAGE_GUIDE.md` (the outputs table, the site data
  section, the gate table, the deploy step, and the output-shape list), `README.md` (the feature list, the
  outputs list, the typical outputs, the gate table, and the test list), `unit_manifest.py` docstring, and
  `acceptance.md`.

## Facts measured during F6.6

- Kitchen-sink run: `ngfw_device = var.fw_2_example_com`, the site row for the unit whose directory is
  `fw_2_example_com_5cef6fb6`, and `variables.tf` declares 4 variables (3 credentials plus
  `fw_2_example_com`). The `CORPUS_ROWS` values in `tests/test_site_data.py` are run-measured digests, not
  assumed names; `virtual_routers.xml` states `fw_1_example_com`, not `fw_2_example_com`.
- `naming.variable_name` is idempotent, so the gate cannot tell an id that states the mapping result from an
  id that states the value. The rule compares the printed name, and the writer keeps the value in the id, so
  a tool-built id cannot carry the name. Recorded in `backlog.md`.
- The gate reads `.tf` files only, so `SITE_DATA.json` and `site.auto.tfvars` are not gate inputs. A stale
  `.tf` file left in a shared output directory trips the new consumer-without-declaration direction, which is
  why `tests/test_reference_edges.py` now uses one directory per fixture.
- No table row maps a field to a list today, so a corpus run writes only string values; the `.tfvars` writer
  prints a list because the row shape declares one, and that path is pinned by test.

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

- F6.5, F6.6 and F6.7 still write no directory. The four data files name the unit, the entry, the pair and
  the site, so the write path is the step that turns a `directory` field into a real directory, and
  `scope.tf`, `imports.tf` and `site.auto.tfvars` are one file for the run.
- The block reader in `sanity_checks.py` serves every kind, so the `action` rule (F6.7) must use
  `blocks(files, kinds)`; no second block reader should appear.
- The gate reads `.tf` files only, so no data file is a gate input today. `scope.tf` and `imports.tf` are
  `.tf` files and are gate inputs. If a codebase feature makes a data file a gate input, the file set
  statement in `ARCHITECTURE.md` §4.5, the `.tfvars` statement in §4.5, and the no-change tests must change
  together.
- A field reader must read at the block's own level and stop at the closing quote, or a sub-block field or
  an escaped quote answers for the block's field. Both are pinned in `tests/test_import_blocks.py`, and the
  scope rule reads at the block's own level through the same reader. The same reader now also tells a quoted
  value from a `var.` reference, so no second rule decides the shape of a field.
- `SCOPE_PLACEMENT` and the location sub-block are one fact: a new scope type needs both the placement key
  and the `SCOPE_ANSWER` entry, and the emitter reads the placement key as the location, so a new row
  cannot place itself in a scope it does not name.
- The entry name is never a property. A row whose provider type declares no `name` reaches the block
  through `entry_coverage.name_field`; no emitter, gate rule, or test should state the field again.
- One place decides the shape of a value: `resource_mapping.VALUE_VARIABLES`, read at the print site. A new
  field a table row maps must be read by the emitter, the gate and the `.tfvars` writer through the same
  table, and the table must cover every field `LOCATION_SCHEMA` declares.
- The §5 naming rule lives in `naming.py`. No module may define a second one; `TerraformGenerator.sanitize_name`
  is a delegate and the data modules take the rule as an argument.
- The import position for the four `*_policy_rules` types must be the position the live config holds, and
  the F3.5 rulebase decision gates it. F6.4 writes no block for a rule entry until both land.
- The generated `README.md` does not name `imports.tf`, `SITE_DATA.json` or `site.auto.tfvars`; the F5.5
  label precedent says an opt-in shape labels itself.
- Actions need Terraform 1.14 or later; the committed goldens declare no Terraform minimum.
- The credential rule needs one statement that covers both the fetch layer and the generated provider
  block.
- The prune action still needs the record directory decided. A state record references nothing, so it
  prunes nothing, and the prune rule reads a record file, not one record.
- A coverage fact that comes from a run must be read from the run's ledger, so the scan tests run the
  pipeline in process.
- A cycle test needs the referrer entry and the declaring entry in the same unit, for the reason recorded
  in the git history for F6.3.