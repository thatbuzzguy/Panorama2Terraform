# Acceptance Criteria — F5.5 Read-through data blocks (opt-in)

A read-through data block is a `data` block for a name the run did not read. The parse reads
the entries an export holds; a reference site that names an entry outside the export cannot
resolve it, so today it writes a plain string. This feature lets a run declare which scopes it
may read through, and then writes one `data` block for each name in those scopes that the run
cannot resolve.

All eight criteria are met, and the feature is committed. Two criteria changed shape during the work:

- AC-5 clause 2: the `name` half of the argument rule cannot fire today, because every reference scope
  declares `name` (`tests/test_data_blocks.py::test_the_data_path_targets_only_types_that_declare_name`).
  The refusal stands for a reference scope a future feature adds.
- AC-2 clause 4: the console summary counts resource blocks only, so a run that writes `data` blocks
  reports the same resource count as the same run without them.

The rest of this file is the criteria as they were written before the code.

## AC-1 The data source table (`DATA_SOURCE_SCHEMA`)

1. `DATA_SOURCE_SCHEMA` in `resource_mapping.py` holds one row per provider data source type
   (128 rows), written from `data_source_schemas` through the `provider_schema` fixture. No type
   name, sub-block name, or field name comes from memory.
2. Each row states the two facts the gate rule needs:
   - whether the type declares `name`;
   - the `location` sub-blocks it declares, with the fields each sub-block declares.
3. The table is the complete declared shape, not a subset. `LOCATION_SCHEMA` is a deliberate
   subset because the generator only needs the sub-blocks it can use; the gate rule must refuse a
   sub-block the provider does not declare for a data source, so this table lists every declared
   sub-block. `terraform validate` accepts an unknown `location` sub-block and drops it silently,
   so the table is the offline check.
4. Pins against the live schema: every type in the table exists in `data_source_schemas`; every
   sub-block and every field matches the live shape; no declared sub-block is missing from the
   row; `location` is required for every data source; `name` is required for every data source
   that has a `name` attribute (106 types).
5. The 22 types with no `name` attribute are rows with `False`. The gate rule must not require a
   `name` for them, because a settings or policy data block that is correct has no `name`.
6. `LOCATION_SCHEMA` stays the generator's location rule. The pin between the two tables: for a
   type in both, every sub-block `LOCATION_SCHEMA` lists is in the data row, with the same fields.
7. Decision recorded: the table test keeps the fixture's skip marker and writes no committed
   schema snapshot. The `provider_schema` fixture already skips when the terraform binary or the
   provider cache is absent, so a snapshot would be a second copy of the same fact and could
   drift from the pinned provider version.
8. The two name-level mismatches between the resource and data source sets stay facts of the
   table, not facts of the gate: `panos_certificate_import` and `panos_virtual_router_interface`
   (a resource with no data source), `panos_certificate` and `panos_predefined_dlp_file_type`
   (a data source with no resource).

## AC-2 One block reader

1. `sanity_checks.py` reads one block shape for four kinds: `resource`, `data`, `import`,
   `action`. Epic 6 (F6.4, F6.7) adds the rules for `import` and `action` blocks, so this is the
   reader they use. No second block reader appears.
2. `blocks(files)` returns each block as (file, line, kind, type, local name, body), in file
   order then line order.
3. `resource_blocks()` stays as the wrapper for `resource` blocks, so the existing callers and
   tests do not change.
4. `SanityReport.resource_count` counts `resource` blocks only, so the console summary line
   stays the same for a run that writes no `data` block.

## AC-3 The gate rule for a `data` block

1. A new check, `data_blocks`, reads only `data` blocks. It is in `CHECK_ORDER` after
   `location_present` and before `references`, so the report order stays fixed.
2. The rule, per block:
   - the type is in `DATA_SOURCE_SCHEMA`;
   - the block carries a `location` block;
   - every `location` sub-block is one the row declares for that type;
   - every field inside a sub-block is one the row declares for that type;
   - `name` is present when the row declares one for that type, and a row with `False` is not
     refused for having no `name`.
3. `location_present` reads every `resource` and `data` block, because the provider requires
   `location` on both. The findings for a run with no `data` block are unchanged.
4. The gate reports no finding on a `data` block that follows the table, so a read-through run
   that is correct still passes, and the corpus stays clean.
5. The report and the console summary are byte-identical between two runs with the same
   arguments. One more check row appears in every report, which the determinism pin allows.

## AC-4 A reference resolves to a block of its own kind

1. `check_references` keys a declared block by (kind, type, local name).
2. `data.<type>.<local>.name` resolves to a declared `data` block; `<type>.<local>.name`
   resolves to a declared `resource` block. A `data` block cannot answer a plain reference, and a
   `resource` block cannot answer a `data.` reference.
3. The finding names the reference as the file writes it.

## AC-5 The emit path (opt-in)

1. Off by default. A run that declares no read-through scope writes the same bytes as before,
   so both golden sets are unchanged.
2. `--data-blocks <scope>` names one scope the run may read through. The argument is repeatable
   and takes a comma-separated list. The scope must be a type in `DATA_SOURCE_SCHEMA` that the
   generator resolves names against (the reference scope sets), and that declares `name`. A scope
   outside those sets, or a no-name type, is an argument error (exit 2), because such a block
   cannot hold the entry name a reference needs.
3. A reference site resolves inside the run first. Only when no scope in its lookup order has a
   declaration does the read-through branch run, and the block type is the first scope in that
   order. A name that resolves inside the run, or that stays ambiguous under the F3.5 and F3.6
   device rules, stays a plain string.
4. The block holds the type, the local name, `name`, and `location`. Nothing else.
5. The local name is the F2.7 shape (sanitized name plus digest), allocated in the data registry.
   The read-through path cannot change a resource name, so the goldens are unchanged when the
   feature is off.
6. One block per identity: (scope, context, vsys, name). A repeated reference site with the same
   identity uses the same block; two sites with different identities write two blocks, because
   PAN-OS resolves a name in the referrer's own scope first, so two scopes can hold two entries
   with the same name.
7. One file per run: `read_through.tf`, written only when it has blocks, in sorted (type, local
   name) order.
8. The block's location is the location the referrer's identity names, written by
   `location_block`. There is one location rule, and the tool does not guess which scope holds a
   name outside the run. When the referrer names no location, the existing F3.6 placeholder rule
   applies.

## AC-6 The report rule

1. No coverage section names a read-through name: the entry report (F4.3), the property scan
   (F4.4), and the shadow scan (F5.4) read entries the parse captured, and a read-through name is
   not one of them. No matrix row covers a `data` block, so a property finding cannot name one.
2. The one report that may name a read-through name is `MANUAL_SETUP_REPORT.txt`, through the
   existing F3.5 and F3.6 location rules: a read-through block whose location cannot be resolved
   is reported by the rule that already reports an unplaceable location. No new report rule.
3. The record of a read-through run is `read_through.tf` plus the `README.md` label.

## AC-7 The generated `README.md` label

1. A run that declares read-through scopes labels itself in the generated `README.md`: the
   declared scopes, in sorted order, and the number of blocks written.
2. The label states why the run needs a label: a `data` block resolves at plan time, so a wrong
   scope or a missing entry fails at `terraform plan`, not at `terraform validate`.
3. A run that declares no read-through scope writes the same `README.md` as before, with no
   label section.

## AC-8 Gates and determinism

1. The gates do not change: `ruff check .` clean, `pytest` green, both golden sets
   byte-identical, report and record determinism pinned, exit codes unchanged (input refusal 1,
   argument error 2), every test offline.
2. Two runs with the same arguments on the same bytes write the same bytes. The data block list
   is sorted by type then local name, and the data registry keeps the first block for an identity
   in generation order, so the file is byte-identical between runs.
3. Recorded caveat for the documents: a declared read-through scope turns every name outside the
   run into a `data` block, including a built-in name such as `any`, because no verified built-in
   name table exists. This is why a read-through run must be labelled.
