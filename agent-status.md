# Agent Status

## Current position

F6.10.3 (the directory write) is complete and committed. The suite is 1303 tests, all green, and
`ruff check .` is clean.

The write path (`write_path.py`):

- `write_file` is the only function that writes a file, and text takes `newline=LF`, so the byte rule is enforced
  in one place. `bytes` are written without translation, because the cache holds the bytes the input door
  parsed, so `source_fetch.py` writes the cache through it.
- `unit_path` and `root_path` are the two builders, one per file set. The tool writes through
  `write_unit_file` and `write_root_file`, so no module builds a path for a file it does not own.
- The generator groups its emitters through `UnitText`, keyed by the unit directory, and the file order is the
  order `main()` calls the emitters. `TerraformGenerator.unit_set()` is the run's unit set, read through
  `unit_manifest.units`, so a unit the manifest names gets a directory even when the run writes no block inside
  it. `variables.tf` and `provider.tf` are unit-set files, so every unit directory holds at least those two.

The gate:

- `read_tf_files` walks the codebase root and keys each `.tf` file by the path from the root, so a finding names
  the unit directory the file is in.
- `check_data_files` reads the four records at the root through `parse_rows`, over the rows of every unit, and
  its printed-form half reads each unit's file inside the directory the row names, so that finding names the path.
- `check_terraform` runs once per unit directory `unit_directories` names, and each result names the directory it
  ran on: the finding names it, or the note names it when the plan passed. `result_of` is the worst result, so a
  unit that failed is not hidden. A missing binary is a SKIPPED result, so the suite runs offline. A record that
  names no unit runs the plan check on the codebase root, which the result names as `.`.
- `SanityReport.results(check)` is one result per unit directory, and `findings(check)` reads the findings across
  the results.

The goldens moved to the per-unit layout, regenerated from a real run: `tests/golden/sample/`,
`tests/golden/kitchen_sink/`, and the new `tests/golden/single_unit/` (`tests/fixtures/address_objects.xml`, one
unit). The golden pin reads the `.tf` set as paths from the case directory, so
`tests/test_policy_order.py` reads the parts per unit and no golden test skips. `conftest.py` holds the helpers
the tests read the layout through: `tf_files`, `parts`, `file_text`, and `written_bytes` for the two-run byte
pins.

`tests/test_write_path.py::test_no_unit_directory_is_written_yet` is replaced by
`test_the_run_writes_one_directory_per_unit_the_manifest_names`, which names the directory the run writes.

The next slice is F6.10.4 (the site half): the `.tfvars` `target` fact, the `panos_push_to_devices` shape, and
the generated `README.md` label. `acceptance.md` holds F6.10.3's criteria and must be overwritten for it.

## Rules to keep when writing documents

- One owner document per rule; every other document links to it.
- Machine-readable tables are code. A document explains a table and never restates it
  row by row, so a regenerated table cannot drift.
- No test counts in a document. A document names the test that pins a rule; the
  count lives in `agent-status.md` and the git history.
- A claim about what the tool does must name the module or the test that holds it. A
  feature id is written only when a module or a test uses it as a name.
- ASD-STE100 Simplified Technical English, no marketing voice, no emoji.
- A historical record is not kept in the markdown. The git history is the record, and the
  markdown states the current state.
- A record is data, so a document describes its fields and never restates a record. The
  example in `docs/USAGE_GUIDE.md` is an illustration with a shortened hash, not a pin.
- Completed epic, phase, feature and task detail is removed from the tracking markdown after
  the work is committed; `AGENTS.md` states the rule.

## Watch for Epic 6 and Epic 7

- The write path landed (`docs/CODEBASE_ASSEMBLY.md` §14): the run writes one directory per unit the manifest
  names, and the codebase root holds the root set. A new file shape must name which set it belongs to, and the
  report counts, the console line and the tests that read the file set change with it. The open facts F6.10.4
  names are the `.tfvars` `target` serial and the `panos_push_to_devices` shape.
- A rule that pins an absence by scanning module sources cannot read a source that names the words it
  forbids, so a scan reads the tool's own modules, and the test name and the module docstring carry no
  forbidden word. The writer scan excludes `write_path.py` (the single writer) and `conftest.py` (the test
  harness). The pin for the outputs rule is group 7 of `tests/test_reference_edges.py`; the pins for the file
  shape are `tests/test_write_path.py`.
- The block reader in `sanity_checks.py` serves every kind, and the same field reader serves the fields inside a
  container value and the elements of a list value, so a new block shape uses them rather than writing a second
  reader.
- A test that reads the `.tf` set reads it as the gate reads it, keyed by the path from the output directory, so
  a run that names two units is not read as one file. A plan check that runs writes a `.terraform` cache inside
  the directory it ran on, so a pin that reads a corpus run uses a copy of it.
- A field reader must read at the block's own level and stop at the closing quote, or a
  sub-block field or an escaped quote answers for the block's field. Both are pinned in
  `tests/test_import_blocks.py`, and the scope rule reads at the block's own level through the
  same reader, which takes the sub-block it reads as an argument (the action rule reads inside
  `config`). The same reader also tells a quoted value from a `var.` reference, so no second
  rule decides the shape of a field.
- `PROTOCOL_SHAPE` is the one table for the protocol object, and a level it does not state is not read.
  A new routing level needs a table row before an emitter, a gate rule or a report can read it, and
  `WORD_TO_SCHEMA` is the pin between a table word and the schema word. A parse method states a path and
  never spells a field name: `_protocol_xml_name` and `_protocol_field_name` are the two rules.
  `_protocol_areas` is the area rule the two OSPF levels share, and `_protocol_choice` takes the element that
  holds the chosen body: the flag element for an area type, the entry's own level for a BGP peer group.
- The parse method that takes the router element is named in the test helpers that call it for each router:
  `tests/test_entry_coverage.py::_parse_every` and `tests/test_multi_vsys_location.py`. A new level method
  must be added there, or the corpus checks run no method for it.
- A container row that moves from `report` to `emitted` changes the property scan scope, the per-entry
  report, and the `.tf` goldens together, so it cannot be a print-only change. A moved row must be
  `emitted` with the provider type in its note, because the matrix row and the report both read the note.
- `SCOPE_PLACEMENT` and the location sub-block are one fact: a new scope type needs both the
  placement key and the `SCOPE_ANSWER` entry, and the emitter reads the placement key as the
  location, so a new row cannot place itself in a scope it does not name.
- The entry name is never a property. A row whose provider type declares no `name` reaches the
  block through `entry_coverage.name_field`; no emitter, gate rule, or test should state the
  field again.
- One place decides the shape of a value: `resource_mapping.VALUE_VARIABLES`, read at the print
  site. A new field a table row maps must be read by the emitter, the gate and the `.tfvars`
  writer through the same table, and the table must cover every field `LOCATION_SCHEMA` declares.
- The §5 naming rule lives in `naming.py`. No module may define a second one;
  `TerraformGenerator.sanitize_name` is a delegate and the data modules take the rule as an
  argument.
- One place decides the shape of a reference field: `TerraformGenerator.name_ref`, read at the print site.
  The mechanism for a name it cannot resolve is the plain name it returns, so a write path that runs the
  rule per unit changes the corpus pin lists, not the rule.
- The import position for the four `*_policy_rules` types must be the position the live config
  holds, and the F3.5 rulebase decision gates it. No block is written for a rule entry until both
  land.
- The generated `README.md` does not name `imports.tf`, `SITE_DATA.json` or `site.auto.tfvars`;
  the F5.5 label precedent says an opt-in shape labels itself.
- Actions need Terraform 1.14 or later; the committed goldens now declare it, so a change to the
  minimum is a golden change.
- The credential rule needs one statement that covers both the fetch layer and the generated
  provider block.
- The prune action still needs the record directory decided. A state record references nothing,
  so it prunes nothing, and the prune rule reads a record file, not one record.
- A coverage fact that comes from a run must be read from the run's ledger, so the scan tests run
  the pipeline in process.
- A cycle test needs two units that each declare a name the other one uses, because the rule resolves a
  name only inside the unit that declared it (`tests/fixtures/reference_cycle.xml`).
- The LF rule is a byte rule, so the goldens and the no-change tests change with the write path. The rule is in
  the one write function, and `docs/ARCHITECTURE.md` §6 states it.
