# Agent Status

## Current position

This commit wrote the round-trip cross-check and its pins: `sanity_checks.check_round_trip`, its
`CHECK_ORDER` position between `data_files` and `control_chars`, the ledger argument on `run_checks` that
`main()` now passes, and `tests/test_round_trip.py` (33 tests, one per criterion in `acceptance.md`). The
measurements are in the `acceptance.md` Result, and the facts that stay open are in `backlog.md`.

What landed:

- The rule reads the `.tf` block set through `sanity_checks.blocks` with `kinds = ('resource',)`, and the entry
  set through the run's `entry_coverage.EntryLedger`. It joins them through `entry_coverage.matrix_row_for`,
  `entry_coverage.MATRIX_BY_RESOURCE` and `unit_manifest` (`facts_of`, `directory_name`, `units`), so it states
  no reader, no count, no scope, no kind, no type, no field name, no file name and no unit rule of its own. It
  is the gate's one boundary exception: the gate reads the files it wrote plus the run's ledger for this rule.
  `run_checks` takes the ledger as an argument, `main()` passes it, and a call with no ledger reports the check
  as NOT RUN with a note, so a pin that reads only the output directory is unchanged.
- The finding: one finding per unit and per `COVERAGE_MATRIX` row where the two counts do not agree, and the
  fact is the two counts, so the rule names no entry. The position is the line of the first block the reader
  read for that unit and row, or the file as a whole (`line` 0) when the reader read no block, which names the
  unit directory plus the row's `output_file`. A `.tf` file at the codebase root names no unit, so the rule
  states the count as not assignable. Findings sort by (file, line, detail), the order `check_data_files`
  already uses, so the report stays byte-identical between runs. The rule prints no scan console line, because
  its fact compares two sets and the console shape names one identity.
- The severity is WARN, not the FAIL `acceptance.md` stated. Measured with FAIL: `main()` exits 1 on the corpus
  fixtures, so `python3 -m pytest` fails 111 tests and errors 115. Measured with WARN: 2 tests fail. The
  decision follows `entry_coverage.PROPERTY_RULE`: a disagreeing count names no broken output, so the exit code
  stays with the rules that read the files.

The measured facts that could not hold as written are in the `acceptance.md` Result and in `backlog.md`: the
corpus is not silent, so the rule reports 22 findings on 10 fixtures in three categories (5, 16 and 1);
`matrix_row_for` answers no row only for the `nested-block` container, so the entry side reads no count for a
nested-block entry while the block side counts the block it wrote; `report_only` is recorded after `mark`, so
`destination` answers `emitted` for a report-only address and the count includes it.

Pins that moved with the rule: `tests/test_data_file_gate.py` (the order tuple gained the name, and the data
rule's source slice now ends at `check_round_trip`), `tests/test_write_path.py` (the same slice boundary), and
`tests/test_sanity_gate.py::test_kitchen_sink_gate_passes_with_validate` (the kitchen run now reports 6 WARN:
the cross-check's five findings and the placeholder).

Every pin that reads the entry side runs the pipeline in process, because `run_script` loses the ledger with
the process. The suite runs offline.

Next step, for the documents agent: `docs/ARCHITECTURE.md` §4.6 and §1, `docs/COVERAGE_MATRIX.md` §1,
`README.md` and `docs/README.md`. `sanity_checks.py` already states the check in its own table and names the
ledger exception in its module docstring.

`ruff check .` is clean and `python3 -m pytest` passes 1566 tests (1533 before this commit, plus the 33 new
ones), with no skip and no golden change.

The gated pieces that stay open are the four `*_policy_rules` types, a config entry inside a stack, the EDL
reference decision, and the profile-name report column. The config entry inside a stack is a count mismatch
this rule reports, so `backlog.md` keeps the fact with the rule named.



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

- `state_coverage.ownership_key` is the one identity key rule, so the shadow scan, the ownership order and the
  state scan read their keys through it and no module states a second key. The key names the parent scope for a
  shadow, so the report line names which parent entry the child repeats, and the parent entry stays in the
  report, because the console shape names one identity.
- The console line shape is stated in one place, `container_coverage.console_line` (`docs/ARCHITECTURE.md`
  §3.2), so a scan states its fact phrase and its block header and calls it. A finding kind that prints on
  the console must fit the four parts: one position, one identity, one fact. A source named on a console
  line is the source name, never the path, and a fact that compares two entries or two units prints in the
  report only.
- The captured part of a report line is stated in one place, `entry_coverage.captured_part`, so `entry_line` and
  `gap_fact` print the same words for the same finding. `PRINTS_VALUE_KINDS` names which kinds print a value, and
  it must stay data: no writer branch may decide the shape per kind. `NAMES_NO_FIELD_KINDS` is the matching data set
  for the kinds that name no field, so a `bookkeeping` row states the row identity only, because the fact its row
  records is the relation the entry carries no value for. A row that prints a value must carry the
  captured object through `row_for`, because `fields` holds the names only, and the value shape is
  `report_value`. A read through the recorded object is what the property scan counts, so a rule that prints a
  value is a rule about a read, and the pin that holds it must run the pipeline, not build a row by hand. A kind
that names field names must name only fields a read reaches: for a `nested-block` row the print is the only
output its entry reaches, so the names come from the read record, and for a `bookkeeping` row no read reaches a
field, because the fact the row records is a relation the entry carries no value for
(`docs/COVERAGE_MATRIX.md` §1, pinned by
`tests/test_property_coverage.py::test_the_nested_block_line_names_only_the_fields_the_emitter_reads` and
`tests/test_property_coverage.py::test_the_bookkeeping_line_names_no_field_for_the_membership_entry_it_marks`).
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
- The fixture assembler is a generator, not a pin, so no document or test may claim that its output is the
  committed fixture. Its read rule is the two F3.8 checks read on the committed bytes, so a hostile fixture is
  skipped by rule and not by name, and the tool names no fixture in its source except its own record. `tools/`
  is not on the test path, so `tests/test_build_kitchen_sink.py` reads the tool's functions through `importlib`
  on the path `tests/conftest.py` builds once, and the tool writes no file, so a run cannot change the record the
  goldens read.
- The block reader in `sanity_checks.py` serves every kind, and the same field reader serves
the fields inside a
    container value and the elements of a list value, so a new block shape uses them rather
than writing a second
  reader. The round-trip cross-check reads the block set through it with `kinds = ('resource',)`, so it states
  no reader of its own. Its fact compares two sets, so its finding is a coverage fact and prints no console
  line: it is a WARN, the decision `entry_coverage.PROPERTY_RULE` already states for a gap, and the exit code
  stays with the rules that read the files.
- A test that reads the `.tf` set reads it as the gate reads it, keyed by the path from the
output directory, so
    a run that names two units is not read as one file. A plan check that runs writes a
`.terraform` cache inside
  the directory it ran on, so a pin that reads a corpus run uses a copy of it.
- A plan check reads the directory the plan runs on, so a validate pin runs `sanity_checks.check_terraform` once per
  unit directory the manifest record names, never at the codebase root, where no configuration file sits. A value the
  provider constrains in its code, not in the schema JSON, is not data the gate can read, so it stays outside the
  static rules and the plan check reports it (`docs/ARCHITECTURE.md` §4.6), and a fixture a plan pin reads states the
  accepted value.
- A field reader must read at the block's own level and stop at the closing quote, or a
  sub-block field or an escaped quote answers for the block's field. Both are pinned in
  `tests/test_import_blocks.py`, and the scope rule reads at the block's own level through the
  same reader, which takes the sub-block it reads as an argument (the action rule reads inside
  `config`). The same reader also tells a quoted value from a `var.` reference, so no second
  rule decides the shape of a field.
- `PROTOCOL_SHAPE` is the one table for the `protocol` object, `FILTER_SHAPE` is the one table for the filter
  containers, which sit outside it, and `CERTIFICATE_SHAPE` is the one table for the two certificate containers
  (F7.14). A level either table does not state is not read. A new routing level needs a table row before an
  emitter, a gate rule or a report can read it, and `SHAPE_TO_SCHEMA` is the one pin between a table word and the
  schema word for all three tables. A parse method states a path and never spells a field name:
  `_protocol_field_name` and `_protocol_xml_name` are the two rules; `XML_NAME_EXCEPTIONS` is the protocol table's
  exception map, and `FILTER_XML_NAME_EXCEPTIONS` is the filter table's map, keyed by the container path because
  one idea spells two ways in two containers. All three shape tables are the same row shape read as `resource_mapping.ShapeTable`,
  so the readers and the gate helpers take the table as an argument and state no table name in their finding
  wording, and one helper group (`_shape_level_findings`, `_shape_field_findings`, `_shape_choice_findings`) serves
  all three. A level the export holds as entries states its row as `string_list`, so the walk reads it as a `[`
  value and each element as an entry, which is the certificate profile's `certificate` row. `_parse_router` builds the `protocol` dict from the fields the `protocol` row states, and
  `parse_filter_containers` builds each entry dict from the fields its own row states, so the level names are the
  table's names in both. Field order is the table order, so the order a row states is the order the block
  prints, and a row change that moves the order moves the goldens. A level that holds no entry has no container row, so the property scan measures nothing
  for it and the matrix row stays grounded by the table. An entry inside an entry is not in the scan scope unless a
  row names the path with the `entry` segment the parent entry is: the certificate profile's list objects are that
  case, because the field the profile row names is also the spelling of the `certificate` section row, so the row
  that holds the `entry` segment wins by length and the profile row measures them. Every other entry inside an entry
  is grounded by the table instead.
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
- A container row that moves from `report` to `emitted` changes the property scan scope, the per-entry report,
  and the `.tf` goldens together, so it cannot be a print-only change. A moved row must be `emitted` with the
  provider type in its note, because the matrix row and the report both read the note. A row must also name the
  type the emitter prints for the entries in that container, so the matrix element names an entry inside the
  container the row names: a shape the emitter reaches through a name fact is not a container the row can
  state, and no entry measures such a row.
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
- The credential rule has one statement and one owner document, `docs/CODEBASE_ASSEMBLY.md` §11, so every other
  document links to it. `source_fetch.py` is the only tool module that states the environment name, and the pin
  `tests/test_variables.py::test_the_generated_block_names_the_environment_the_fetch_layer_reads` holds both halves:
  the generated block names that name, and no other `src/` module states it. `VALUE_VARIABLES` decides the shape, so
  the host is an `operator_supplied` row and no name list decides a provider argument or a marking.
- The prune action reads the record file the run wrote, because the record directory is the output directory
  and `SOURCE.txt` is a codebase root-set file. `provenance.prune` decides through `prunable_entries` and
  builds no path, so no path rule for a record directory can appear in the module that owns the record. A state
  record references nothing, so it prunes nothing and protects nothing, and the action reads a record file, not
  one record. `--prune-cache` is an opt-in flag that gates the step; it names no part of the layout, so the
  no-flag scan holds, and it cannot change what the gate counts or the exit code the gate decides.
- A coverage fact that comes from a run must be read from the run's ledger, so the scan tests
  run
  the pipeline in process. The round-trip cross-check reads the run's ledger as an argument, so its
  pins run the pipeline in process too, and a `run_checks` call that passes no ledger reports the check
  as NOT RUN rather than guessing a count.
- A cycle test needs two units that each declare a name the other one uses, because the rule
  resolves a
  name only inside the unit that declared it (`tests/fixtures/reference_cycle.xml`).
- The LF rule is a byte rule, so the goldens and the no-change tests change with the write
  path. The rule is in
  the one write function, and `docs/ARCHITECTURE.md` §6 states it.
