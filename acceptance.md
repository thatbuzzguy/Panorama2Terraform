# Acceptance Criteria — F6.4 Import Blocks

Status: complete. Every criterion below is pinned by `tests/test_import_blocks.py`.

F6.1 names the unit (`unit_manifest.py`), F6.2 names the unit that owns each entry (`ownership.py`), and
F6.3 names the reference between units (`reference_edges.py`). F6.4 writes the block that binds an entry to
the object the provider already has: one `import` block per entry, built from the same identity data the
resource block uses. The gate rule that reads an `import` block is the second gate rule for a block kind
(F5.5 reads `data`), and it uses the one block reader (`sanity_checks.blocks`).

## Verified provider facts (the only inputs this feature may state)

1. The import id is base64 of a JSON object. `docs/CODEBASE_ASSEMBLY.md` §12.
2. For an ordinary object type the object is `{"location": <the location object>, "name": <the entry name>}`,
   as the pinned provider docs show for `panos_address`. The location object in the id is the same sub-block
   and the same declared fields `LOCATION_SCHEMA` states, so the id and the resource block state one fact.
3. For the four `*_policy_rules` types the object is `{"location": <location with rulebase>,
   "names": [<names>], "position": {...}}`. The rule types name the rulebase, the position in the live
   rulebase, and a list of names, so no per-entry import object exists. `LOCATION_SCHEMA` declares `rulebase`
   for exactly these four types.
4. `panorama_device` is a field of `location.device_group` in the pinned schema, and the docs example states
   it. The generator's location rule emits no device fact, so the id states no device fact. Recorded in
   `backlog.md`.

## Decision 1 — the file shape

1. **`imports.tf`, one file per codebase, one `import` block per entry.** The gate reads `.tf` files only
   (`ARCHITECTURE.md` §4.5), so the agreement rule can only read a `.tf` file: a data file is not a gate
   input. F6.1 rule 4 still refuses a per-unit file, because this feature writes no directory.
2. **Opt-in: `--import-blocks`.** Off by default, so a run that declares nothing writes the same `.tf` bytes
   as before, and both golden `.tf` sets stay byte-identical. This is the F5.5 `--data-blocks` precedent.
3. **Block shape.** One block, two fields, in this order: `to`, then `id`. `to` is the block address
   `<resource type>.<local name>`; `id` is the base64 string.
4. **Order inside the file.** Units in the manifest identity order (`unit_manifest.build_rows`), entries
   inside a unit in local-name order. Both are already the order the data files print, so the file is
   byte-identical between two runs on the same bytes.
5. **Written only when it has content**, following the rule for the report files and the three data files.

## Decision 2 — the import id

1. The id is base64 of the JSON object, with JSON keys sorted at every level and compact separators, so the
   same entry always encodes to the same bytes. `ensure_ascii=True` keeps the file ASCII.
2. The location object comes from `TerraformGenerator.location_data`, the single location rule.
   `location_block` renders from it, so no second location rule exists.
3. The local name comes from `declare_block_name` at the site that applies the naming rule, and the entry
   name is the name the block states. No second naming rule.
4. `decode_id` is the inverse of `build_id` and refuses a value that is not the declared shape, the way
   `unit_manifest.parse_rows` refuses a row that is not the declared shape.

## Decision 3 — the four `*_policy_rules` types

1. **No import block for a rule entry. Each rule entry is a WARN finding.** The id cannot be built offline:
   the parse records no rulebase for an entry (F3.5 gates it), `position` is live-config state and the
   generator's chains anchor at `where = "last"`, and the object names a list of names rather than one
   entry.
2. The finding names the check (`import_blocks`), the file and line the one block reader read, and the reason.
   A WARN is an operator action, so it does not change the exit code, which the gate decides. It prints in the
   gate report and in the gate console summary, as every gate finding does, and no new console line appears.
3. The decision for the accepted `rulebase` value stays in `backlog.md` with F3.5. This feature writes no
   unverified value.

## Decision 4 — the agreement gate rule

`sanity_checks.check_import_blocks`, added to `CHECK_ORDER` after `data_blocks`, reads `import` blocks with
the one block reader. An `import` block must agree with the resource block it names:

1. `to` names a `resource` block that this run declares. A wrong type and a wrong local name are both
   detected here, and a `data` block cannot answer, because an import object names a resource.
2. `id` decodes to the declared shape.
3. The decoded `name` equals the block's `name`.
4. The decoded location equals the block's `location` sub-block: the same sub-block, the same fields, the
   same values.
5. No false positive: the corpus writes no finding for this rule.

## AC-1 The id round trip

1. `build_id` then `decode_id` returns the same location object and the same entry name.
2. The bytes match the pinned provider example for `panos_address` in a device group.
3. A name that is not ASCII, and a location sub-block with no field (`shared`), round-trip.
4. `decode_id` refuses a value that is not base64, not a JSON object, or not the declared shape.

## AC-2 The agreement rule

1. Each violation type is detected: wrong type, wrong local name, wrong location, wrong name, and an `import`
   block that names a `data` block.
2. No false positive across the fixture corpus, with `--import-blocks`.
3. The rule uses `sanity_checks.blocks` only: no second block reader.

## AC-3 The rule types

1. A rule entry writes no block and one WARN finding that names the reason.
2. The finding does not change the exit code, which the gate decides: the gate result stays PASS. It prints
   in the gate report and in the console summary, as every gate finding does, under its own check line; no
   new console shape is introduced.

## AC-4 Determinism and the no-change rule

1. Two runs with the same arguments write the same bytes for `imports.tf`.
2. A run without `--import-blocks` writes no `imports.tf` and the same `.tf` bytes as before: both golden sets
   byte-identical.
3. `imports.tf` names no timestamp, no source path, and no absolute path.
4. `ruff check .` clean, `pytest` green, every test offline.

## AC-5 The file shape, the reader, and the opt-in

1. One block, two fields, in this order: `to`, then `id`. One file per codebase run, `imports.tf`, written
   only when the run declares the shape and has a block to write.
2. The reader is `sanity_checks.blocks`, and it reads the `import {` shape by taking the pair from `to`, so
   one pass answers both block shapes.
3. `imports.tf` is a `.tf` file, so it is a gate input and `CHECK_ORDER` names `import_blocks` after
   `data_blocks`.
4. `--import-blocks` appears in `--help`, and the default is off.
