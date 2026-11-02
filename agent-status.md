# Agent Status

## Current position

F6.10.5 is complete and committed on `development`, which closes Epic 6. The suite is 1315 tests, all
green (1310 at the start of this slice), and `ruff check .` is clean. The next feature is the open Epic 7
work: the routing levels `resource_mapping.PROTOCOL_SHAPE` does not state (`backlog.md`).

`acceptance.md` holds this slice's criteria and must be overwritten for the next one.

### Decision 1: the stack is the fifth scope fact

- `container_coverage.SCOPE_FACT_KEYS` holds five facts, and `template_stack` is appended, because that
  order is the unit identity join (`docs/ARCHITECTURE.md` §5). `unit_manifest.py`, `ownership.py`,
  `state_coverage.py`, `reference_edges.py`, and `entry_coverage.py` read the fact order through that one
  table, so no module states a second order.
- `PanoramaParser.identity_of` returns five facts, and `template_stack_of` is the scope-walk row for it in
  `container_coverage.CONTAINER_TABLE` (F6.10.5).
- Reading `template` as the stack name was rejected: `resource_mapping.ACTION_FILTERS` maps
  `template_stacks` → `template_stack`, `resource_mapping.SCOPE_ANSWER` answers `panos_template_stack` for
  the fact, `resource_mapping.SCOPE_PLACEMENT` gives `panos_template_variable` the two sub-blocks, and
  `entry_coverage.REPORT_SCOPE_KEYS` maps `template-stack` → `template_stack`. One fact with two meanings
  would make a filter field name both a template and a stack.
- `unit_manifest.NAME_LEVELS` reads innermost first: `vsys`, `vsys_device`, `template`, `template_stack`,
  `device_group`, so a template inside a stack names its template. A stack entry names its own unit, so a
  run that declares a stack writes one directory for it and the commit and push blocks for that unit come
  from `ACTION_FILTERS` (`tests/test_unit_manifest.py::test_the_stack_names_its_unit`).
- `reference_edges.LEVEL_KEYS` gained `template_stack`, so a unit inside a stack depends on the stack unit.
- `state_coverage.STATE_SCOPE_KEYS` gained `template_stack`, so an entry placed inside a stack is keyed. The
  test that pins a sub-block the row does not declare now uses a sub-block `LOCATION_SCHEMA` does not
  declare for `panos_address` (`tests/test_state_coverage.py::test_a_block_the_row_does_not_declare_is_not_keyed`).
- `panos_template_variable` no longer states `template_stack` as a captured property, so its
  `COVERAGE_MATRIX` row lists four properties (`tests/test_property_coverage.py`,
  `tests/test_entry_coverage.py::test_captured_fields_exclude_name_and_scope_facts`).

### Decision 2: the tool decides no module parameter

A module is a standard a person writes, so the tool writes the data a module consumes and decides no
parameter. A template variable value, and a membership list in `scope.tf`, stay the literal the export
states, because the block *is* the PAN-OS variable (`docs/CODEBASE_ASSEMBLY.md` §9 rule 2). This closed with
no byte change, and the open item is removed from `backlog.md`.

### Housekeeping: the sample output

The repository holds no committed sample output, so nothing was regenerated or deleted. `terraform_output/`
is the default value of `--output-dir` and `.gitignore` ignores it. The canonical sample output is the
golden set (`tests/golden/sample/`, `tests/golden/kitchen_sink/`, `tests/golden/single_unit/`), which
`tests/test_golden_files.py` pins byte for byte. The layout work that renames paths stays in `backlog.md`.

### Pins that changed

- The fact order is the digest input, so every unit digest moved. 71 old→new pairs were re-measured from a
  real run and applied to `tests/test_unit_manifest.py`, `tests/test_ownership.py`,
  `tests/test_reference_edges.py`, `tests/test_site_data.py`, and `tests/test_write_path.py`. The unit that
  holds no fact moved from `shared_be5be69f` to `shared_45ca31c3`, because the join gained one separator, and
  the sample run's shared unit moved from `shared_0bc98741` to `shared_a6577c11`: the placeholder names no
  unit, but it is still part of the identity.
- The three golden sets regenerated from a real run, never by hand. `tests/golden/kitchen_sink/` gained the
  stack unit directory `branch_stack_5c39384d`. The changed bytes are the action addresses, the data-block
  names that state the fact order, and the unit directory names. A resource local name did not change,
  because its identity is context plus vsys.
- The corpus unit counts moved: `tests/test_write_path.py` counts eleven units for the kitchen sink run, and
  `tests/test_golden_files.py` gained three cases for the new unit directory.
- Pins that name a unit moved where the stack entry stopped naming the shared unit, not only by digest: the
  kitchen sink run names the stack unit `branch_stack_5c39384d` instead of the shared unit, so
  `tests/test_reference_edges.py` (the level order group) reads the stack unit as the shallower scope, and
  `tests/test_unit_manifest.py::test_the_stack_names_its_unit` pins the stack unit and its two entries.
  `tests/test_container_coverage.py` reads the fact set the scope-walk rows cover, and
  `tests/test_state_coverage.py::test_a_stack_sub_block_keys_the_fact_it_names` pins the key for a state
  entry placed inside a stack.
- Test names that state the fact count: `test_one_row_per_combination_of_the_five_facts`,
  `test_every_parse_method_records_the_five_scope_facts`, `test_a_block_the_row_does_not_declare_is_not_keyed`.
- The suite gained five tests: `tests/test_unit_manifest.py::test_the_stack_names_its_unit`,
  `tests/test_state_coverage.py::test_a_stack_sub_block_keys_the_fact_it_names`, and three
  `tests/test_golden_files.py` cases for the new unit directory.
- `docs/CODEBASE_ASSEMBLY.md` §3 and `docs/ARCHITECTURE.md` §2.2 name the new test, and the sentence that
  said no stack unit is named today is removed.

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

## Watch for Epic 7 and the write path

- The write path landed (`docs/CODEBASE_ASSEMBLY.md` §14): the run writes one directory per unit the manifest
  names, and the codebase root holds the root set. A new file shape must name which set it belongs to, and the
  report counts, the console line and the tests that read the file set change with it.
- `unit_manifest.units` is the run's unit set, so a rule that names a unit for a directory, an owner, or an
  edge reads it through that one function. A unit exists only when the ledger has a row in it, and the fact
  order is the identity join, so a new fact changes every digest and every golden in the same commit.
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
  location, so a new row cannot place itself in a scope it does not name. A config type has no
  `template_stack` sub-block, so a config entry inside a stack writes no block and is a finding
  recorded in `backlog.md`.
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
- The generated `README.md` names `imports.tf`, `SITE_DATA.json` and `site.auto.tfvars`, and it names
  `target` as a fact the tool names as a variable. It states no row, no value, no mapping result, no count,
  no path and no timestamp, so the report rule holds for the site record with the README as the
  file-inventory exception (`tests/test_site_data.py`).
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
