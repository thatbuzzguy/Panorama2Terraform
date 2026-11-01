# Agent Status

## Current position

F7.2 (the `ospfv3` level of the protocol object) is complete and committed. `PanoramaParser.parse_ospfv3`
reads the level and its area subtree, `_protocol_areas` is the area rule it shares with `parse_ospf`,
`resource_mapping.PROTOCOL_SHAPE` states a row for each level the method reads, and the emitter, the gate rule
`protocol_object` and the report read that table. The pins are
`tests/test_protocol_object.py` (the table against the live schema, the printed shape for
`tests/fixtures/ospfv3.xml`, the mapping for the two choice levels, the choice-body rule, and the interface the
file cannot express) and `tests/test_parse_network.py::test_parse_ospfv3`. The suite is 1244 tests.

The next feature is not chosen. The open pieces are in `to-do.md`, and the rules they must keep are in the
watch list below.

Facts measured while the work landed, and the rules that follow from them:

- The provider declares the same fields for the `ospf` and the `ospfv3` area subtrees, so one area reader
  (`_protocol_areas`) serves both, and the table keeps one row per level. A row states only the fields the
  method that reaches that level reads.
- The fields of a `one_of` body live inside the chosen flag element, not inside `type`. Before the fix the
  parse read them from the wrong element, so a flag field printed nothing: measured `type = { nssa = {} }` for
  an area whose export stated `accept-summary` inside `nssa`. Both fixtures state one, and
  `tests/test_protocol_object.py::test_a_choice_body_prints_the_fields_it_declares` pins the print.
- `protocol/ospfv3/area/name` is a `string`, the way the `ospf` area name is, so the entry name prints as the
  name field and not as a list.
- A property-level entry is counted on the parent row, so an entry inside an area entry is not measured by the
  property scan, and a `range` entry is a nested block row, so the scan reads nothing for it. The area entry
  itself is measured through the router row.
- The parse method that takes the router element is named in the test helpers that call it for each router:
  `tests/test_entry_coverage.py::_parse_every` and `tests/test_multi_vsys_location.py`. A new level method
  must be added there, or the corpus checks run no method for it.
- A container row path is read from the method's own string constants plus the constants of the helpers it
  calls, so a helper that takes the level path as an argument keeps the pin true.

The next feature is not chosen. The open pieces are in `to-do.md`, and the rules they must keep are in the
watch list below.

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
  are one file for the run until it lands.
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
