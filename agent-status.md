# Agent Status

## Current position

The filter input-spelling grounding is complete and committed on `development` (`244ddef`); this tracking
markdown is the next commit. Decision: a pair of `FILTER_XML_NAME_EXCEPTIONS` is a fact only when the run
reads it, so `tests/fixtures/filter_containers.xml` holds one entry per choice alternative the fixture states,
not one entry per container. All 15 pairs are grounded, so no pair is a spelling the pango source measures
alone, and no pair stays in `backlog.md` as ungroundable. No exception row is added, removed, or reworded.

- The fixture gains 5 entries: `ACL-Filter-v6`, `Prefix-Filter-v6`, `Community-Filter-Extended`,
  `Community-Filter-Large`, and `Redist-Filter-Set`. The last one states the 4 redist pairs in one `set`,
  because `aspath_prepends` is reachable only through a `set` row under a `bgp` child level. The fixture now
  holds 11 entries.
- Pins changed in `tests/test_filter_containers.py`: `_fixture_entries` reads every entry per container, and
  `_entry_level` walks a level the way the parse walks it, so the entry inside a `string_list` element is read
  at the level the row names it (F7.6). The parse mark pin, the emitter print pin, the choice pin and the gate
  pin read every entry; the choice pin covers 10 of the 14 choice rows, where it covered 5, and the gate pin
  states the run's summary as `PASS (0 FAIL, 0 WARN)`. The new pin
  `test_the_run_prints_the_field_for_each_pair_the_fixture_states` reads each pair from the run's output and
  runs `terraform validate` on the output the run wrote; the hand-written list of 5 grounded pairs is removed
  from `test_the_path_keyed_exceptions_are_the_spellings_the_input_uses`.
- Goldens: only `tests/golden/filter_containers/fw_template_00a08cdc/filters.tf` changed, and it is the bytes
  of a real run. `docs/ARCHITECTURE.md` §4.10 rule 3 and `README.md` state the grounding as the pin states it.
- `ruff check .` is clean, and `python3 -m pytest` passes 1462 tests (about 2 minutes).

The housekeeping layout rule is unchanged: `docs/ARCHITECTURE.md` §1.1 is its owner document, `AGENTS.md`
names the tracking markdown set, and each index names every document under it (commits `ccf93a3` and
`b3465f1`).

The next feature is the coverage row the corpus cannot measure, which `backlog.md` names:
`panos_aggregate_layer3_subinterface`. The container table maps an aggregate interface entry to the ethernet
subinterface row, so no entry reaches the aggregate row and the parity pin names it as one of the two rows
with no read of its own (`tests/test_property_coverage.py`). The feature is to decide whether an aggregate
entry is covered by its own row, then state it with a fixture entry that reads `type = aggregate`, so the scan
measures the row through a real entry and the goldens move with it.

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

## Watch for the shape tables and the write path

- The console line shape is stated in one place, `container_coverage.console_line` (`docs/ARCHITECTURE.md`
  §3.2), so a scan states its fact phrase and its block header and calls it. A finding kind that prints on
  the console must fit the four parts: one position, one identity, one fact. A source named on a console
  line is the source name, never the path, and a fact that compares two entries or two units prints in the
  report only.
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
- A rule that pins an absence by scanning module sources cannot read a source that names the words it
  forbids, so a scan reads the tool's own modules, and the test name and the module docstring carry no
  forbidden word. The writer scan reads the `src/` set and excludes `src/write_path.py` (the single writer);
  `tests/conftest.py` is the test harness, so it sits outside the set. The pin for the outputs rule is group 7
  of `tests/test_reference_edges.py`; the pins for the file shape are `tests/test_write_path.py`.
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
  table's names in both. Field order is the table order, so the order a row states is the order the block
  prints, and a row change that moves the order moves the goldens. A level that holds no entry has no container row, so the property scan measures nothing
  for it and the matrix row stays grounded by the table. An entry inside an entry is not in the scan scope either,
  because `covering_row` cannot match a section path that holds an entry segment, so the table grounds that level.
  `_protocol_areas` is the area rule the two OSPF levels share, `_protocol_branch` walks the
  segments between a
    level dict and an entry level, `_protocol_entries` fills a `string_list` level, `_protocol_entry_level` (F7.10)
fills an entry level the row states as a field, because its entries live under the element the field names, and
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
  itself, and a level inside an entry prints the reference the entry that holds it names. F7.12: `selects` is the
  one place a row states a choice the provider reads as exactly one, so the level or the entry states one of the
  keys `selects` names, and the gate reads that rule at the level the walk enters and at each entry of a
  `string_list` row through `_shape_choice_findings`. The two rows that state it are `peer_address`, where the
  choice is the whole value, and the `ospfv3` auth profile entry, where the choice is two of the entry's fields.
  The three filter levels `terraform validate` refuses to hold more than one (`source_address`, `prefix`, and the
  redistribution entry's `bgp`) state their alternatives as fields and no `selects`, so the choice rule reads
  nothing for a filter block; that decision is in `backlog.md`.
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
- The prune action reads the record file the run wrote, because the record directory is the output directory
  and `SOURCE.txt` is a codebase root-set file. `provenance.prune` decides through `prunable_entries` and
  builds no path, so no path rule for a record directory can appear in the module that owns the record. A state
  record references nothing, so it prunes nothing and protects nothing, and the action reads a record file, not
  one record. `--prune-cache` is an opt-in flag that gates the step; it names no part of the layout, so the
  no-flag scan holds, and it cannot change what the gate counts or the exit code the gate decides.
- A coverage fact that comes from a run must be read from the run's ledger, so the scan tests
  run
  the pipeline in process.
- A cycle test needs two units that each declare a name the other one uses, because the rule
  resolves a
  name only inside the unit that declared it (`tests/fixtures/reference_cycle.xml`).
- The LF rule is a byte rule, so the goldens and the no-change tests change with the write
  path. The rule is in
  the one write function, and `docs/ARCHITECTURE.md` §6 states it.
