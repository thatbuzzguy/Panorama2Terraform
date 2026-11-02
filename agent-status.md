# Agent Status

## Current position

F6.9 (the outputs rule for a name another unit in the codebase owns) is complete and committed. It is a
decision, so it adds no module: it writes no byte, changes no gate rule, and adds no file, so the goldens,
the reports, the file sets and the report counts are unchanged.

The decision: a name another unit in the codebase owns prints as the plain name string at the print site,
in the order the reference edge rule states (the owner unit before the referrer unit), because Panorama
resolves an object name through its own inheritance at commit time. The tool defines no outputs writer and
reads no remote-state data source, because the state backend is out of scope and a module is a standard a
person writes. The `data` block stays the mechanism for a name outside the codebase (F5.5). `name_ref`
stays the one place that decides the shape of a reference field, so no second rule decides which name
crosses a unit.

The rule is written once, in `docs/CODEBASE_ASSEMBLY.md` §5 rule 5, which is the owner document for it.
`reference_edges.py` rule 6 states the same rule, and `docs/ARCHITECTURE.md` §4.3 links to it instead of
restating it. The pin is
`tests/test_reference_edges.py::test_the_mechanism_defines_no_writer_and_no_reader`, which scans the tool's
own modules for the mechanism. The positive half is held by the pins that already read the rule: the plain
name in `tests/test_data_blocks.py` and `tests/test_robustness.py`, the pair in
`tests/test_reference_edges.py::test_the_record_is_one_row_per_edge_the_data_can_name`, and the order in the
order group of the same file. The suite is 1245 tests.

The next feature is not chosen. `to-do.md` keeps the Epic 6 write path as the open step, and the rules it
must keep are in the watch list below.

Facts the decision rests on:

- The reference rule already returns a plain string for a name it cannot resolve, so the decision added no
  shape rule. A single-unit run is the flat run today, so a plain run writes the same bytes as before.
- Order carries existence: the order rule ranks the owner unit before the referrer unit, and the platform
  plans in the order the data states, so no plan-time read of another unit's state is needed, and no
  remote-state data source appears.
- A pin that reads module sources cannot read a source that names the words it forbids, so the scan reads
  the tool's own modules only, and the module docstring cites the test by its name without the mechanism
  words.
- The consequence for the write path: `name_ref` runs per unit, so a name the flat chain resolves across
  scopes today becomes a plain name. The edge set and the manifest `references` field grow to name every
  cross-unit use, so `tests/test_reference_edges.py::CORPUS_EDGES` and
  `tests/test_unit_manifest.py::GROUPING_REFERENCES` change with that step.

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

- The codebase modules name the unit, the owner, the pair, the order, the block, the scope
  object and the site, and write no directory. The write path is the step that turns a
  `directory` field into a real directory, and `scope.tf`, `imports.tf` and `site.auto.tfvars`
  are one file for the run until it lands. The print-site rule it applies is decided
  (`docs/CODEBASE_ASSEMBLY.md` §5 rule 5), so the step has no open decision.
- A rule that pins an absence by scanning module sources cannot read a source that names the words it
  forbids, so a scan reads the tool's own modules, and the test name and the module docstring carry no
  forbidden word. The pin for the outputs rule is group 7 of `tests/test_reference_edges.py`.
- The block reader in `sanity_checks.py` serves every kind, and the same field reader serves the
  fields inside a container value and the elements of a list value, so a new block shape uses them
  rather than writing a second reader.
- The gate reads the `.tf` files for the block rules and the four data files for the data rule, so the two
  file sets are distinct: a block rule reads a `.tf` file, and the data rule reads a record through the
  module that owns its row shape. `scope.tf`, `imports.tf` and `actions.tf` are `.tf` files, so the block
  rules read them. `site.auto.tfvars` is the printed form of the site record, so the data rule compares it
  and does not count it as a data file, and `SOURCE.txt` is read by no rule. A new file shape must name
  which of the two sets it belongs to, and the report counts, the console line and the tests that pin the
  file set change with it. No data rule reads a `.tf` file, and no block rule reads a data file.
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
- A cycle test needs the referrer entry and the declaring entry in the same unit, for the reason
  recorded in the git history for F6.3.
- The LF rule is a byte rule, so the goldens and the no-change tests change with the write path.