# Agent Status

## Current position

F6.10.4 (the site half) is complete and committed. The suite is 1310 tests, all green, and `ruff check .` is
clean.

The three decisions:

- `target` is one row in `resource_mapping.VALUE_VARIABLES` with the new shape word `OPERATOR_SUPPLIED`: the run
  names the variable, holds no value for it, and the operator supplies the value in `terraform.tfvars`. The corpus
  states no serial, because every device entry name is a hostname, so the tool cannot name one without guessing.
  `sensitive = true` stays the `REFERENCE_ONLY` row's rule alone, so the table is read in one place and no name
  list decides a marking. The name is `naming.variable_name(field)`, because a fact the tool cannot read has no
  value to name it from. No site row and no `.tfvars` line is written for it.
- `printed_value(key, value, facts)` now takes the unit's facts, so the print site records the pair and the shape
  through `unit_manifest.facts_of`; `value_shapes()` is the accessor for the shape. `generate_variables()` reads
  the shape to decide the marking, and `generate_provider_config()` records the pair before it runs, because
  `main()` calls the provider block first.
- `provider.tf` prints `target = var.target` only for a unit whose manifest row names a device, so the declaration
  has a consumer in the same directory. The sample set names no device, so it holds no `target`.

The push half:

- `commit_actions.py` emits one push block per unit through `ACTION_FILTERS`, `SCOPE_ANSWER` and `ACTION_SCHEMA`:
  `name` prints the fact the unit declares and `type` prints the fact key. No `devices`, because the tool names no
  serial, so the provider's documented default pushes to all devices in the target. A shared, vsys or device unit
  writes no push block. Within one unit the blocks print in the `ACTION_SCHEMA` order (commit, then push), and the
  commit block and the push block for one unit share one address, because the action address is
  `action.<type>.<label>`.
- `ROW_FIELDS` gained `action`, `FACT_KEY_FIELD` is `type`, `filter_field(fact, action)` takes the action, and
  `block_fields` and `field_text` are the emitter's two shape helpers. `read_block` records the stated field and
  the action, so the gate reports what a block states instead of the filter field the fact would answer for.
- `test_commit_actions.py` gained group 7 for the push block, and the address pins read the pair
  (`action`, address) as the key for one row.

The README: the generated file now names `imports.tf`, `SITE_DATA.json` and `site.auto.tfvars` and names `target`
as a fact the tool names as a variable. It states no row, no value, no mapping result, no count, no path and no
timestamp, so the rule that no report names a field the site data states holds for the site record with the README
as the file-inventory exception (`tests/test_site_data.py::test_no_report_names_a_field_the_site_data_states`,
`::test_the_readme_names_the_site_files_and_states_no_row`).

Pins that changed: `tests/test_site_data.py` (the table rows, the README exception, the golden print pins),
`tests/test_variables.py` (the declaration set is the credentials plus the site values plus the names the table
records with no value), and `tests/test_protocol_object.py` (`printed_value` takes facts). Both golden sets
regenerated from a real run: `provider.tf` and `actions.tf` changed.

The next slice is F6.10.5, which closes Epic 6: the template stack unit, and the module parameter rule.
`acceptance.md` holds F6.10.4's criteria and must be overwritten for it.

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
  report counts, the console line and the tests that read the file set change with it. F6.10.4 landed the `target`
  name and the push shape. What F6.10.5 can decide is the template stack unit and the module parameter rule.
- `VALUE_VARIABLES` is the single shape owner and `sensitive = true` is the `REFERENCE_ONLY` row's rule alone, so a
  new shape word must be read in the table and not by a name list. The test that pins the declaration set reads the
  names the table records with no value (`tests/test_variables.py`), and the test that pins the report rule carves
  the `README.md` file-inventory exception. A change to a shape word moves both pins in the same commit.
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
