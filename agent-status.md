# Agent Status

## Current position

F7.7 is complete and committed on `development`. `PROTOCOL_SHAPE` states the four
`auth_profile` levels the
pinned provider declares, the four level methods read them through `_protocol_branch`, and the
emitter, the gate
rule `protocol_object` and the property scan read the same rows. A field the provider marks
`sensitive` prints as
the variable reference the entry names, never as the value the export stated. The suite is 1346
tests, all green
(1336 at the start of this slice), and `ruff check .` is clean. No golden set moved, because no
golden fixture
states an auth profile. `terraform validate` accepts the block the run writes for
`tests/fixtures/auth_profile.xml`.

The next feature is F7.8: the filter containers (`to-do.md`).

`acceptance.md` holds this slice's criteria and must be overwritten for the next one.

### Decision 1: the entry that holds a `sensitive` field names the variable

A value cannot name itself, so the name the block prints is the §5 name of the entry that holds
the field: the
entry names itself when the field is its own, and a level inside an entry names the entry that
holds it.
`TerraformGenerator._protocol_fields` carries the entry name down the walk as `entry_name`. The
parse stores the
value, because the gate and the property scan read the captured object, and `printed_value`
records the name with
no value for it, so `site_data.py` rule 2 writes no row and the run writes no `.tfvars` line.
The declaration
description now says the reference prints and no file states the value, because the run reads a
value it never
writes.

### Decision 2: the measured rows for `ospfv3` follow the `policy` convention

Measured 2026-11-03 with the pinned provider: `ah` and `esp/authentication` are choice levels,
so each
alternative that declares an attribute is its own row, and `none`, which declares none, is the
`block` field of
the row that holds it with `none` in its `selects`. The provider accepts `ah` or `esp` for one
entry, which
`terraform validate` reports, so the table states no word for a choice between two levels, the
gate does not
refuse a file that states both, and the fixture uses two entries. The 15 new rows are the
`ospfv3` subtree: the profile row and 14 rows for the levels inside a profile entry, and the
the two `md5` rows gained `preferred`, because the reader now reaches them through the table.

### Decision 3: a reference-only name is a property of the row that covers the entry

The emitter reads a `sensitive` field to print the reference, so the field is a read the scan
measures, and the
matrix row that covers the entry gains it. The four `auth_profile` rows are `emitted` `sub-
shape` rows with the
note `panos_virtual_router`, so `panos_virtual_router` gained `ah`, `esp`, `md5`, `password`,
`secret` and `spi`.
`key` is not a property, because it is read inside an entry inside an entry, and `covering_row`
cannot match a
section path that holds an extra `entry` segment, so `PROTOCOL_SHAPE` stays the only place that
states it. The
four container rows use the input spelling, the same rule as `protocol/rip/interfaces`, because
`covers` matches
a row path against the tag chain the scan reads.

### Decision 4: one new fixture, so the existing print pins stay intact

`tests/fixtures/auth_profile.xml` states one router with an auth profile entry at each of the
four levels, and
each entry states every field its row declares. The four level fixtures stay unchanged, so the
whole-block print
pins that read them still pass. Each value is distinct, so the pin that no generated file holds
a parsed value can
name each one.

### Pins that changed

- `tests/test_protocol_object.py`: the new pins are
  `test_the_auth_profile_rows_are_the_levels_the_four_methods_read`,
    `test_an_auth_profile_prints_the_reference_the_entry_names` (the block a real run writes),
  and
  `test_the_gate_reads_a_choice_level_inside_an_auth_profile`;
    `test_the_shape_table_is_the_measured_provider_shape` now reads every row as a level a
  parse method reads;
    `test_a_sensitive_field_is_never_written_as_a_value` names the pin in
  `tests/test_robustness.py`.
- `tests/test_property_coverage.py`:
`test_the_scan_measures_an_auth_profile_entry_and_not_the_entry_inside_it`
  pins the scan scope.
- `tests/test_variables.py`: `_reference_names` reads the names the run records through
`PROTOCOL_SHAPE`, the
    `string_list` shape and `_protocol_xml_name`, so the pin states no name list; the
  declaration set and the
  `sensitive` marking pins read it, and `auth_profile.xml` joined `CASES`.
- `tests/test_site_data.py`: `test_the_table_holds_no_property` reads the reference-only names
through the table
  instead of excluding them.
- `tests/test_robustness.py`: `test_a_parsed_secret_never_reaches_a_generated_file` pins the
values a real run
  must not write.
- `tests/test_container_coverage.py`: `_segments_of_method` already reads each path segment
through
  `_protocol_xml_name`, so the four new rows match the four methods.
- No new parse method, so no test helper changed: the auth profile read lives inside the four
level methods,
  which the two helpers already call.
- The suite gained ten tests.

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
- `PROTOCOL_SHAPE` is the one table for the protocol object, and a level it does not state is
not read.
    A new routing level needs a table row before an emitter, a gate rule or a report can read
  it, and
    `WORD_TO_SCHEMA` is the pin between a table word and the schema word. A parse method states
  a path and
    never spells a field name: `_protocol_xml_name` and `_protocol_field_name` are the two
  rules, and
    `resource_mapping.XML_NAME_EXCEPTIONS` is the one exception the `-` rule cannot produce.
  `_parse_router` builds
    the `protocol` dict from the fields the `protocol` row states, so the level names are the
  table's names there
    too. A level that holds no entry has no container row, so the property scan measures
  nothing for it and the
    matrix row stays grounded by the table. An entry inside an entry is not in the scan scope
  either, because
    `covering_row` cannot match a section path that holds an entry segment, so the table
  grounds that level.
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
    the level the field names. A presence choice states exactly one alternative, and the choice
  level is not
    required, so a level that states no choice element prints nothing for it while an element
  that states none is a
    report row. A choice level can state its alternatives as values, in which case
  `_protocol_choice` reads the
    value from the element the choice lives under and the print writes it as the reader read
  it. A `member_list`
    field is read by `_protocol_level`, because its members are values, so no level row stands
  under it and the
    walk never enters it: `sanity_checks.SHAPE_READS_AS` states which word the reader reads
  each specialization as,
    and `SHAPE_LEVELS` states which words name a level the walk enters. A parse method that
  reads a container
    reads only the level its own row states, which `entry_coverage.covering_row` decides. A
  `sensitive` field cannot name itself, so `_protocol_fields` carries the name of the
entry that holds the level: an entry names itself, and a level inside an entry prints the
reference the entry
that holds it names. One entry states `ah` or `esp` for an `ospfv3` profile, which
`terraform validate` reports, so the table states no word for it.
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
