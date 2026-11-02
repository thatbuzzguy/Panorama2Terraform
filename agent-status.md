# Agent Status

## Current position

F6.10.1 (the shape of the write path) is complete and committed. It is a decision, so it writes no output
byte: the goldens, the reports, the gate rule set, the report counts and the file sets the corpus run writes
are unchanged. One code change carries the reading rule: `sanity_checks.read_tf_files` now walks the tree
below the codebase root and keys each file by the path from the root, so the same block rule reads today's
flat run and the split run, and a finding names the path. For a flat run the path is the file name, so the
bytes a report names are unchanged.

The decision, written once in `docs/CODEBASE_ASSEMBLY.md` §14 (the owner document):

- **The unit set** is the files one plan reads, so one directory holds them: the `.tf` files for that unit
  and the printed form of that unit's site row. `provider.tf` and `variables.tf` are unit-set files, because
  a plan reads the declarations in its own root.
- **The codebase root set** is the files that describe the whole codebase, one per run: the four records, the
  report files, `README.md`, `SOURCE.txt`. The records stay at the root, because the edge record needs the
  whole unit set and a reader cannot find a per-unit file before it knows the directory name.
- **The two sets are distinct**, and every file a run writes names one set. The printed form is compared and
  not counted. A new file shape must name which set it belongs to, and the two counts change with it.
- **Default output, not an opt-in.** The committed goldens pin what a default run emits, so a shape a run
  writes only when a flag is on cannot be pinned. A flag for the layout would give the reference rule two
  shapes and force a second gate reader. Consequence: both committed golden sets move to the per-unit layout
  and regenerate in the same step as the LF rule.
- **A per-unit file names its unit only by the directory it is written in**, so the manifest row stays the
  only place that states the unit set, and a gate finding names the path from the codebase root.
- **The gate reading:** the block rules read every `.tf` file below the codebase root, keyed by the path from
  the root; the data rule keeps reading the four records at the root as one rule over the rows of every unit;
  the plan check runs once per unit directory; no rule reads a report, `README.md` or `SOURCE.txt`.

The pins are `tests/test_write_path.py`, 12 tests, in the scan style of `tests/test_reference_edges.py`
group 7. The pins that measure the corpus read the pinned measurements, not a restated rule: the corpus unit
count (10), the file sets the corpus run writes, and the two report counts. The golden pin reads the `.tf`
set as paths from the case directory (`tests/test_golden_files.py`), so it holds for a golden set that holds
unit directories, and the committed goldens are byte-identical. The suite is 1257 tests.

The pin names: `test_the_unit_set_and_the_codebase_root_set_are_distinct`,
`test_a_per_unit_file_names_no_path_so_the_reader_names_the_unit`,
`test_the_unit_set_is_one_set_per_unit_and_the_data_set_is_one_file_for_the_codebase`,
`test_the_block_reader_walks_the_tree_and_a_finding_names_the_path`,
`test_for_a_flat_run_the_path_is_the_file_name_so_no_report_byte_changes`,
`test_the_data_rule_reads_the_records_at_the_codebase_root_only`,
`test_the_data_rule_is_one_rule_over_the_rows_of_every_unit`,
`test_no_rule_reads_a_file_outside_the_two_sets`,
`test_the_plan_check_runs_on_one_directory_and_a_unit_is_one_directory`,
`test_no_flag_names_the_write_path`,
`test_the_golden_set_can_hold_unit_directories_so_only_default_output_can_be_pinned`,
`test_no_unit_directory_is_written_yet`. The last one changes when F6.10.3 writes the directories.

The next slice is F6.10.2 (the print site per unit). `acceptance.md` holds F6.10.1's criteria and must be
overwritten for it. `name_ref` runs per unit, so `tests/test_reference_edges.py::CORPUS_EDGES` and
`tests/test_unit_manifest.py::GROUPING_REFERENCES` change with that step. F6.10.3 finds each unit's printed
form by its site row's `directory`, reads the golden set as paths, and regenerates the goldens with the LF
rule.

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
  (`docs/CODEBASE_ASSEMBLY.md` §5 rule 5), and the file shape is decided (§14), so the step has
  no open decision.
- A rule that pins an absence by scanning module sources cannot read a source that names the words it
  forbids, so a scan reads the tool's own modules, and the test name and the module docstring carry no
  forbidden word. The pin for the outputs rule is group 7 of `tests/test_reference_edges.py`; the pins for
  the file shape are `tests/test_write_path.py`.
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
