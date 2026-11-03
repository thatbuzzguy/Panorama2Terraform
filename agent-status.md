# Agent Status

## Current position

F7.8 is complete and committed on `development`. `FILTER_SHAPE` states the shape of the six
routing-profile filter
containers, which sit outside the `protocol` object, and every one of them is an `emitted`
`CONTAINER_TABLE` row
for `parse_filter_containers`: the pinned provider declares a resource for all six. The parse read,
the emitter,
the gate rule `filter_blocks` and the property scan all read the same table through
`resource_mapping.FILTER_TABLE`.
The suite is 1423 tests, all green (1346 at the start of this slice), and `ruff check .` is clean.
Two golden
cases moved, and both came from a real run: `tests/golden/filter_containers` is the new case, and
`tests/golden/kitchen_sink` gained `filters.tf` for the filter entry `ACL-Kitchen`, so the scan scope,
the
per-entry report and the `.tf` goldens moved together. The gate reports `PASS (0 FAIL, 0 WARN)` on
the filter
fixture, and `terraform validate` accepts the blocks the run writes for it.

The next feature is F7.9: the `ospf` fields `PROTOCOL_SHAPE` does not state (`to-do.md`).

`acceptance.md` holds this slice's criteria and must be overwritten for the next one.

### Decision 1: a filter container is its own resource, so all six are emitted

Measured 2026-11-03 with the pinned provider: the provider declares a resource for each of the six
filter containers, so no container is a `report` row and each `CONTAINER_TABLE` row is `emitted` with the
provider type in its note. `FILTER_TYPES` is that same fact read the other way (path to type), so the emitter
and the gate do not decide a type by themselves, and the pin compares the map with the row notes.

### Decision 2: `selects` is empty, because the schema states a filter choice as optional fields

No filter level is declared as required-exactly-one, so `selects` states nothing for any row. Three levels are
the ones `terraform validate` refuses to hold more than one attribute, so the fixture answers each with one
element: `access-list/type/ipv4/ipv4_entries/source_address` (`address`),
`prefix-list/type/ipv4/ipv4_entries/prefix` (`entry`), and `redist-entry/bgp` (`ospf`). The table states no
word for that choice, because the rule is the provider's and not the table's, and the pin that a run reports no
finding is the pin that says the fixture is written the way the provider accepts.

### Decision 3: the row scope stops at the `match` and `set` rows

The redistribution entry mirrors every level the provider declares, except that its `match` and `set` rows state
leaf fields only, so no row stands under them. That is the scope decision this slice states, and it is the
reason the walk does not enter a `match`: a field inside one is a finding. The table is 121 rows and 397 fields,
73 of them under the redistribution entry, 17 of those stated as `string_list`, and 34 `match` or `set` rows.
The six levels inside a `match` or `set` row are recorded in `backlog.md`.

### Decision 4: an entry-list field is the singular container element, so the spelling map is path-keyed

`FILTER_XML_NAME_EXCEPTIONS` is keyed by the container path, because one idea spells two ways in the input:
`extended_community_regexes` is `ec-regex` inside a community-list entry, and `extended_communities` is
`extended-community` inside a route-map match. The map holds 15 pairs, and `ipv4_entries` and `ipv6_entries`
spell the same way in two containers, so 13 distinct spellings, and none is a spelling the `-` rule produces.
Five pairs are in the fixture; the other ten are the spellings the pango source measures, because one entry
states one entry-list spelling only, which is also why the fixture cannot state `ec-regex` beside
`regular-entry`. `XML_NAME_EXCEPTIONS` stays the protocol table's own map.

### Decision 5: the readers take the table as an argument, so one reader serves both tables

`_protocol_level`, `_protocol_body`, `_protocol_field`, `_protocol_choice`, `_protocol_presence_choice`,
`_protocol_presence_fields`, `_protocol_field_name`, `_protocol_xml_name` and `_protocol_fields` take an
optional `table` that defaults to `PROTOCOL_TABLE`, so `FILTER_TABLE` reaches them through the same code.
`_protocol_xml_name` now takes the path as well, because the exception map is keyed by the container path. The
gate helpers are `_shape_level_findings` and `_shape_field_findings`, and `ShapeTable` gained `word` and `rule`
so one reader states neither table name: the finding wording is the table's word. `SHAPE_TO_SCHEMA` is the one
shape-word to schema-word definition, and both shape pins read it.

### Pins that changed

- `tests/test_filter_containers.py` is the new file: the table against the live schema, the row scope, the six
  container rows, the six matrix rows, the parse constants, the parse marks, the emitter print, the choice
  levels, the gate reading a real run, one finding per rule, the path-keyed spellings, and the golden case.
- `tests/test_protocol_object.py` reads both tables through `FILTER_TABLE` and `PROTOCOL_TABLE`, the renamed
  gate helpers, `ShapeTable.field_name` and `ShapeTable.xml_name`, `parse_filter_containers` and
  `generate_filter_containers`, and `allowed` gained `entry` for the input spelling `entry`.
- `tests/test_coverage_matrix.py` grounds the `generate_filter_containers` emitter against `FILTER_SHAPE`.
- `tests/test_data_file_gate.py` reads `filter_blocks` in `CHECK_ORDER`.
- `tests/test_golden_files.py` gained the `filter_containers` case.
- `tests/test_terraform_validate.py` validates each unit directory the manifest names for the filter fixture,
  because the run writes no `.tf` file at the codebase root.
- `tests/test_entry_coverage.py::_parse_every` and
  `tests/test_multi_vsys_location.py::test_every_parse_method_records_the_five_scope_facts` reach
  `parse_filter_containers` without a change, because it takes no argument and marks every entry it reads.
- The suite gained 77 tests (1423 green).

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

- The write path landed (`docs/CODEBASE_ASSEMBLY.md` §14): the run writes one directory per
unit the manifest
    names, and the codebase root holds the root set. A new file shape must name which set it
  belongs to, and the
  report counts, the console line and the tests that read the file set change with it.
- `unit_manifest.units` is the run's unit set, so a rule that names a unit for a directory, an
owner, or an
    edge reads it through that one function. A unit exists only when the ledger has a row in
  it, and the fact
    order is the identity join, so a new fact changes every digest and every golden in the same
  commit.
- `VALUE_VARIABLES` is the single shape owner and `sensitive = true` is the `REFERENCE_ONLY`
row's rule alone, so a
new shape word must be read in the table and not by a name list. F7.7: a reference-only name
can be the §5 name
of the entry that holds the field, so the pin that reads the declaration set walks the fixture
through the
table (`tests/test_variables.py::_reference_names`). The test that pins the declaration set
reads the
    names the table records with no value (`tests/test_variables.py`), and the test that pins
  the report rule carves
    the `README.md` file-inventory exception. A change to a shape word moves both pins in the
  same commit.
- A rule that pins an absence by scanning module sources cannot read a source that names the
words it
    forbids, so a scan reads the tool's own modules, and the test name and the module docstring
  carry no
    forbidden word. The writer scan excludes `write_path.py` (the single writer) and
  `conftest.py` (the test
    harness). The pin for the outputs rule is group 7 of `tests/test_reference_edges.py`; the
  pins for the file
  shape are `tests/test_write_path.py`.
- The block reader in `sanity_checks.py` serves every kind, and the same field reader serves
the fields inside a
    container value and the elements of a list value, so a new block shape uses them rather
  than writing a second
  reader.
- A test that reads the `.tf` set reads it as the gate reads it, keyed by the path from the
output directory, so
    a run that names two units is not read as one file. A plan check that runs writes a
  `.terraform` cache inside
  the directory it ran on, so a pin that reads a corpus run uses a copy of it.
- A field reader must read at the block's own level and stop at the closing quote, or a
  sub-block field or an escaped quote answers for the block's field. Both are pinned in
  `tests/test_import_blocks.py`, and the scope rule reads at the block's own level through the
  same reader, which takes the sub-block it reads as an argument (the action rule reads inside
  `config`). The same reader also tells a quoted value from a `var.` reference, so no second
  rule decides the shape of a field.
- `PROTOCOL_SHAPE` is the one table for the `protocol` object, and `FILTER_SHAPE` is the one table for the filter
  containers, which sit outside it. A level either table does not state is not read. A new routing level needs a
  table row before an emitter, a gate rule or a report can read it, and `SHAPE_TO_SCHEMA` is the one pin between a
  table word and the schema word for both tables. A parse method states a path and never spells a field name:
  `_protocol_field_name` and `_protocol_xml_name` are the two rules; `XML_NAME_EXCEPTIONS` is the protocol table's
  exception map, and `FILTER_XML_NAME_EXCEPTIONS` is the filter table's map, keyed by the container path because
  one idea spells two ways in two containers. Both tables are the same row shape read as `resource_mapping.ShapeTable`,
  so the readers and the gate helpers take the table as an argument and state no table name in their finding
  wording. `_parse_router` builds the `protocol` dict from the fields the `protocol` row states, and
  `parse_filter_containers` builds each entry dict from the fields its own row states, so the level names are the
  table's names in both. A level that holds no entry has no container row, so the property scan measures nothing
  for it and the matrix row stays grounded by the table. An entry inside an entry is not in the scan scope either,
  because `covering_row` cannot match a section path that holds an entry segment, so the table grounds that level.
  `_protocol_areas` is the area rule the two OSPF levels share, `_protocol_branch` walks the
  segments between a
    level dict and an entry level, `_protocol_entries` fills a `string_list` level, and
  `_protocol_body` fills the
    three shapes a level dict cannot hold: the choice the export states by presence, the
  entries inside the level,
    and the entries inside an `object` field. An entry can hold its own choice, so
  `_protocol_body` takes the entry
    as the element that holds it, and it reads an entry as a direct child, so an entry inside
  an entry belongs to
    the level the field names. A presence choice states exactly one alternative, and the choice level is not
  required, so a level that states no choice element prints nothing for it while an element that states none is a
  report row. A choice level can state its alternatives as values, in which case `_protocol_choice` reads the
  value from the element the choice lives under and the print writes it as the reader read it. A `member_list`
  field is read by `_protocol_level`, because its members are values, so no level row stands under it and the
  walk never enters it: `sanity_checks.SHAPE_READS_AS` states which word the reader reads each specialization as,
  and `SHAPE_LEVELS` states which words name a level the walk enters. A parse method that reads a container
  reads only the level its own row states, which `entry_coverage.covering_row` decides. A row that states leaf
  fields only is the walk's stop point, so a field inside it is a gate finding: the redistribution entry's
  `match` and `set` rows are that case, and the six levels inside them are in `backlog.md`. A `sensitive` field
  cannot name itself, so `_protocol_fields` carries the name of the entry that holds the level: an entry names
  itself, and a level inside an entry prints the reference the entry that holds it names. One entry states `ah`
  or `esp` for an `ospfv3` profile, and one filter entry states one alternative for the three levels
  `terraform validate` refuses to hold more than one (`source_address`, `prefix`, and the redistribution entry's
  `bgp`), so the table states no word for those choices.
- The parse method that takes the router element is named in the test helpers that call it for
each router:
    `tests/test_entry_coverage.py::_parse_every` and `tests/test_multi_vsys_location.py`. A new
  level method
  must be added there, or the corpus checks run no method for it.
- A container row that moves from `report` to `emitted` changes the property scan scope, the
per-entry
    report, and the `.tf` goldens together, so it cannot be a print-only change. A moved row
  must be
    `emitted` with the provider type in its note, because the matrix row and the report both
  read the note.
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
    writer through the same table, and the table must cover every field `LOCATION_SCHEMA`
  declares.
- The §5 naming rule lives in `naming.py`. No module may define a second one;
  `TerraformGenerator.sanitize_name` is a delegate and the data modules take the rule as an
  argument.
- One place decides the shape of a reference field: `TerraformGenerator.name_ref`, read at the
print site.
    The mechanism for a name it cannot resolve is the plain name it returns, so a write path
  that runs the
  rule per unit changes the corpus pin lists, not the rule.
- The import position for the four `*_policy_rules` types must be the position the live config
    holds, and the F3.5 rulebase decision gates it. No block is written for a rule entry until
  both
  land.
- The generated `README.md` names `imports.tf`, `SITE_DATA.json` and `site.auto.tfvars`, and it
names
    `target` as a fact the tool names as a variable. It states no row, no value, no mapping
  result, no count,
  no path and no timestamp, so the report rule holds for the site record with the README as the
  file-inventory exception (`tests/test_site_data.py`).
- Actions need Terraform 1.14 or later; the committed goldens now declare it, so a change to
the
  minimum is a golden change.
- The credential rule needs one statement that covers both the fetch layer and the generated
  provider block.
- The prune action still needs the record directory decided. A state record references nothing,
  so it prunes nothing, and the prune rule reads a record file, not one record.
- A coverage fact that comes from a run must be read from the run's ledger, so the scan tests
run
  the pipeline in process.
- A cycle test needs two units that each declare a name the other one uses, because the rule
resolves a
  name only inside the unit that declared it (`tests/fixtures/reference_cycle.xml`).
- The LF rule is a byte rule, so the goldens and the no-change tests change with the write
path. The rule is in
  the one write function, and `docs/ARCHITECTURE.md` §6 states it.
