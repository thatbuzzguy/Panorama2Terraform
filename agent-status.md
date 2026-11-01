# Agent Status

## Current position

F6.8 (the gate rule that reads the data files) is complete and committed. `sanity_checks.check_data_files`
is the sixth gate rule for a file set: it reads the four data files, each row shape through the module that
owns it, and reports a data file that does not read as its declared rows, a field `naming.py` decides stated
as a row, a join that names no unit or no row, an order that is not what `reference_edges.order` produces,
and a printed form that is not `site_data.render_tfvars` of the rows. The tests are
`tests/test_data_file_gate.py` (21), one negative test per finding, plus the rewritten file-set tests in
`tests/test_unit_manifest.py`, `tests/test_ownership.py`, `tests/test_reference_edges.py`,
`tests/test_site_data.py`, `tests/test_provenance.py` and the new negative test in
`tests/test_sanity_gate.py`. The suite is 1238 tests.

Facts measured while the work landed, and the rules that follow from them:

- The gate reads `.tf` files for the block rules and the four data files for the data rule, so the report
  names both counts: `Files checked: N .tf files, M data files.` The console line names both, then the
  resource count.
- `site.auto.tfvars` is the printed form of the site record, so the data rule compares it with
  `render_tfvars` and does not count it as a data file. `SOURCE.txt` names paths and is read by no rule.
- The position of a data finding is the row ordinal in the declared order, because a data row spans many
  lines; a whole-file finding states no row, and `Finding.render` prints `file  detail` for it.
- Bug fix: `reference_edges.dependencies` now guards the inheritance rule with the node set, so `after`
  names only manifest units. Before the guard, an override row whose owner is a parent-source unit put a
  directory the manifest does not name into `after`, and the rule could not read the order back.
- `parse_rows` re-sorts the rows in the declared identity order, so the row ordinal is that order, not the
  file order.
- The rule reports a refusal as a finding, because a data file a person hand-wrote is an input; the gate
  cannot assume the writer used the module. A data file that reads as no rows is a finding, because the
  content rule writes the file only when it has content.

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
