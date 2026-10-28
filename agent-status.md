# Agent Status

## Current position

F6.4 (import blocks: one block per entry, and the gate rule that a block agrees with the resource block it
names) is complete and committed as `F6.4: import blocks per entry, the import agreement gate rule`. No
feature is in progress. The next feature in `PLAN.md` is F6.5 (scope objects as output). F6.1, F6.2, F6.3
and F6.4 name the unit, the owner, the pair, the order and the block, and write no directory, so the write
path and the gate rule that reads the three data files are still open. The outputs rule for a name another
unit owns is still open in `backlog.md`.

State at the commit: `ruff check .` clean, `pytest` 1062 passed (1030 before this feature: 32 added in
`tests/test_import_blocks.py`), both golden `.tf` sets byte-identical, the report and record determinism
rules unchanged, exit codes unchanged (0, input refusal 1, argument error 2), `--help` gained
`--import-blocks`, `CHECK_ORDER` gained `import_blocks` after `data_blocks`, and every test runs offline.
The goldens compare `.tf` files only, so `imports.tf` is compared when the flag is on; it is off by
default, so no golden byte changed.

## What F6.4 changed

- `import_blocks.py` (new): `IMPORT_FILE`, `ROW_FIELDS`, `RULE_DECISION`, `rule_types()`, `build_id`,
  `decode_id`, `row`, `render`, `read_block`, `block_value`, `unescape`. The module states the id shape, the
  row shape, and the order; it defines no naming rule, no location rule, and no identity key.
- `panorama_to_terraform.py`: `location_data()` is the single location rule and returns
  `{sub-block: {field: value}}` in the print order; `location_block()` renders from it and records the row
  when a local name is passed; `self.import_rows` in `__init__`; `record_import_row()` after
  `unit_references()`; 25 emitter call sites pass the local name, and the read-through site at
  `panorama_to_terraform.py:2552` does not, because a `data` block is not an import target;
  `--import-blocks` after `--data-blocks`;
  `main()` writes `imports.tf` only when the run declares it and a row states an id.
- `sanity_checks.py`: `import_blocks` in `CHECK_ORDER` after `data_blocks`; `IMPORT_BLOCK_RE` and `TO_RE`
  read the `import {` shape in the one pass `blocks()` already makes; `Block.attribute()` reads a field at
  the block's own level through `import_blocks.block_value`; `Block.location_values()` returns the sub-block
  as the shape `decode_id` states; `check_import_blocks()` added to `run_checks()`.
- Tests: `tests/test_import_blocks.py`, 32 tests in seven groups: the id encoding, the agreement rule, the
  no-false-positive run across the corpus, the rule types, the one location rule and the one naming rule,
  order and bytes, and the file shape, the reader and the opt-in.
- Docs: `docs/CODEBASE_ASSEMBLY.md` §1, §2, §5, §7, §10, §12 and §14, `docs/ARCHITECTURE.md` §1, §4.5, §4.6,
  §4.8 and §6, `docs/USAGE_GUIDE.md` (the flags table, the outputs table, and the opt-in section), and
  `README.md` (the flag, the gate table, the outputs list, and the test list).

## Facts measured during F6.4

- The corpus writes no FAIL finding for the agreement rule with `--import-blocks`. The rule types are the
  four `*_policy_rules` types `LOCATION_SCHEMA` declares `rulebase` for, and each rule entry is a WARN
  finding, so the corpus check compares FAIL findings only.
- The pinned provider docs object for `panos_address` round-trips through `build_id` and `decode_id`. The
  provider parses the JSON, so the object is the fact; the byte form is the tool's choice, fixed by sorting
  the keys at every level with compact separators.
- `panorama_device` is a field of `location.device_group` in the pinned schema and the docs example states
  one, but the generator's location rule emits no device fact, so no id states one. Recorded in
  `backlog.md`.
- `block_value` must read at the block's own level. A first version read any indent, so `name = "DG-A"`
  inside `location` answered for the block's `name` and the rule reported a wrong name for a block that
  agreed with its id.
- A quoted value may carry an escaped quote, so the field reader must stop at the closing quote.
  `tests/fixtures/edge_quoted_dg_names.xml` is the fixture that showed it: a greedy `[^"]*` mis-read the
  name and produced a finding on a run that writes no finding.
- The gate console prints one line per check, then each finding under it, so a WARN finding prints under
  `import_blocks`. The earlier statement that the console prints no line for a WARN was wrong; the finding
  prints, and the exit code stays 0.
- `import_blocks.py` cannot import `sanity_checks` (that would be a cycle), so a written block is read back
  through `read_block(block)`, not through a `parse_rows`-style reader.
- `tests/test_sanity_gate.py` iterates `CHECK_ORDER` rather than pinning its length, so adding a check does
  not break it. `tests/test_ownership.py::test_the_gate_reads_no_data_file` pins that the check list equals
  `CHECK_ORDER`, so the new name is covered by that test.
- The data-block call site is deliberately not recorded: an import object names a resource, so a `data`
  block cannot answer a `to` address, and the rule reports it as FAIL.
- `render([])` writes the header only, so `main()` writes no file for a run that declares the shape and has
  no entry.

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

- F6.5, F6.6 and F6.7 still write no directory. The three data files name the unit, the entry and the pair,
  so the write path is the step that turns a `directory` field into a real directory, and `imports.tf` is
  one file for the run.
- The block reader in `sanity_checks.py` serves every kind, so the `action` rule (F6.7) must use
  `blocks(files, kinds)`; no second block reader should appear.
- The gate reads `.tf` files only, so no data file is a gate input today. `imports.tf` is a `.tf` file and
  is a gate input. If a codebase feature makes a data file a gate input, the file set statement in
  `ARCHITECTURE.md` §4.5 and the no-change tests must change together.
- A field reader must read at the block's own level and stop at the closing quote, or a sub-block field or an
  escaped quote answers for the block's field. Both are pinned in `tests/test_import_blocks.py`.
- The import position for the four `*_policy_rules` types must be the position the live config holds, and
  the F3.5 rulebase decision gates it. F6.4 writes no block for a rule entry until both land.
- The generated `README.md` does not name `imports.tf`; the F5.5 label precedent says an opt-in shape labels
  itself.
- Actions need Terraform 1.14 or later; the committed goldens declare no Terraform minimum.
- The credential rule needs one statement that covers both the fetch layer and the generated provider
  block.
- The value-to-variable mapping must be a pinned table, the way `LOCATION_SCHEMA` and
  `DATA_SOURCE_SCHEMA` are.
- The prune action still needs the record directory decided. A state record references nothing, so it
  prunes nothing, and the prune rule reads a record file, not one record.
- A coverage fact that comes from a run must be read from the run's ledger, so the scan tests run the
  pipeline in process.
- A cycle test needs the referrer entry and the declaring entry in the same unit, for the reason recorded in
  the git history for F6.3.
