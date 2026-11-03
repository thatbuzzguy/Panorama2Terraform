# Agent Status

## Current position

F7.5 is complete and committed on `development`. `resource_mapping.PROTOCOL_SHAPE` states the `rip` levels the
pinned provider declares, `parse_rip` reads them through the table, `_parse_router` builds the `protocol` dict
from the fields the `protocol` row states, and the emitter, the gate rule `protocol_object` and the property scan
read the same rows. The suite is 1330 tests, all green (1322 at the start of this slice), and `ruff check .` is
clean. No golden set moved, because no golden fixture states `rip`.

The next feature is F7.6: the BGP `policy` level (`to-do.md`).

`acceptance.md` holds this slice's criteria and must be overwritten for the next one.

### Decision 1: the `rip` levels are rows, and `rip` declares no area

Measured 2026-11-02 against the pinned provider 2.0.14, `protocol` declares `rip`, so the `protocol` row gained
the `rip` field and the subtree gained 11 rows. `rip` declares no `router_id`, no `area` and no `neighbor`, so it
has no area row and no choice row outside `default_route`. `mode` is a string, so the interfaces row states no
`selects` for it. The two `auth_profile` rows state the `sensitive` decision only, the same rule as the `bgp` and
`ospf` rows, so `parse_rip` reads no value for them and the fixture states no auth profile entry.

### Decision 2: an entry can hold its own choice

`_protocol_body` takes the element that holds the shapes a level dict cannot hold. For an area type that element
is the chosen flag element; for a `rip` interface entry it is the entry itself, so the same rule fills the
`one_of` field the row states for the entry. `terraform validate` (measured 2026-11-02) accepts an interface
entry with no `default_route` key, so the choice level is not required and such an entry prints nothing for it.
The report case is a choice element that states none of the alternatives, which is the same shape as a `range`
entry, so no new tolerance was needed in `_protocol_presence_choice`.

### Decision 3: the matrix row gained the four properties an interface entry measures

`COVERAGE_MATRIX` row `panos_virtual_router` gained `authentication`, `bfd`, `default_route` and `mode`, the keys
a run reads from a `rip` interface entry. `bfd` is measured as the field of the entry, not as the level inside
it, because the level dict the parse builds is not a recorded object. `timers` and `global_bfd` are
single-object levels, so they hold no entry and nothing is measured for them. `enable` and `metric` were already
in the row.

### Pins that changed

- `tests/test_protocol_object.py`: `test_the_shape_table_is_the_measured_provider_shape` no longer names `rip` as
  outside the table, and `test_the_rule_reports_an_undeclared_field_and_a_wrong_shape` uses `redist_profile` for
  a level the table does not state. The new pins are `test_the_rip_levels_are_rows_the_parse_reads`,
  `test_an_rip_level_prints_the_shape_the_table_states`,
  `test_the_gate_reads_a_choice_inside_an_entry_level`, and `test_a_rip_auth_profile_field_prints_the_reference_only`.
  `test_the_table_is_the_only_shape_owner` reads `parse_rip` and `_parse_router` as owners.
- `tests/test_parse_network.py::test_parse_rip_reads_the_levels_the_table_states` pins the parse read and the
  report row for an entry that states a choice with no alternative, and
  `::test_parse_rip_absent` pins a router with no `rip` element.
- `tests/test_property_coverage.py::test_the_scan_measures_a_rip_entry_and_not_a_level_inside_it` pins the
  measurement scope.
- `tests/fixtures/rip.xml` is the new device-level fixture: it states every field the new rows declare, and one
  interface entry the report names.
- `parse_rip` is registered in the two test helpers that call a parse method for every router
  (`tests/test_entry_coverage.py::_parse_every`, `tests/test_multi_vsys_location.py`).
- The suite gained eight tests.

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
  never spells a field name: `_protocol_xml_name` and `_protocol_field_name` are the two rules, and
  `resource_mapping.XML_NAME_EXCEPTIONS` is the one exception the `-` rule cannot produce. `_parse_router` builds
  the `protocol` dict from the fields the `protocol` row states, so the level names are the table's names there
  too. A level that holds no entry has no container row, so the property scan measures nothing for it and the
  matrix row stays grounded by the table. An entry inside an entry is not in the scan scope either, because
  `covering_row` cannot match a section path that holds an entry segment, so the table grounds that level.
  `_protocol_areas` is the area rule the two OSPF levels share, `_protocol_choice` takes the element that holds
  the chosen body, `_protocol_entries` fills a `string_list` level, and `_protocol_body` fills the two shapes a
  level dict cannot hold: the choice the export states by presence, and the entries inside the level. An entry can
  hold its own choice, so `_protocol_body` takes the entry as the element that holds it. A presence choice states
  exactly one alternative, and the choice level is not required, so a level that states no choice element prints
  nothing for it while an element that states none is a report row.
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
