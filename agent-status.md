# Agent Status

## Current position (main, Piece 14A.2, the mode as a manifest row field, 2026-11-25)

Piece 14A.2 is complete on main, 2026-11-25, and is not pushed. Decision 2 of `docs/IMPORT_BINDING.md` §2 is taken
by the operator on 2026-11-25: the mode is a field of the unit-manifest row, read through `unit_manifest.parse_rows`,
merged through `codebase_state.py` rule 2, and read by the `data_files` gate rule. One goal: record the decision as
taken, land the field as data in the owner the decision names, and add the pins that read it as data through that
owner. Decision 3 is untaken, so this piece states no CLI argument and no flag, and no run marks a mode. The previous
piece, Piece 14A.1, is committed, so its record lives in the git history. The baseline this piece starts from is that
piece's measurement: 1,861 passed and the same 4 `tflint` skips, so 1,865 pins in 55 test modules. The writing rules
are in their owner document `docs/WRITING_RULES.md`, so this file keeps the status and the links and states no writing
rule of its own.

- Placement, and the reason: `src/unit_manifest.py` is the owner decision 2 names, so `mode` enters `FIELD_ORDER`
  after `unit`. `MODE_LEVEL` names the unit as the level the values apply to, and `unit` is the field that states that
  level on the row, so the mode prints next to it. The two halves sit in two owners, and the reason: the pair is
  decision 1's data and stays in `import_blocks.MODE_VALUES`, so `unit_manifest.py` reads the pair through that owner
  instead of naming the values a second time, and `import_blocks.py` states no field name and defines no reader, so it
  cannot trip the pins that hold it as data. `parse_rows` refuses a mode that is not a value of the pair or the empty
  answer, and the gate reports that refusal as its finding 1 through `unit_manifest`, so the gate states no value set.
  `src/codebase_state.py` changed no code: rule 2 takes the whole row through the reader its owner states, so the
  merge carries the field with no key, shape or reader of its own.
- The empty answer is stated once, in `src/unit_manifest.py` as `EMPTY_ANSWER`, in the style of `provenance.py`
  rule 1, which prints `-` for a field that does not apply. Inside a JSON row the same answer is the empty string, and
  `build_rows` already writes it for a field the unit does not state, so the writer reads the field from that one
  definition. `tests/conftest.py` holds the pair as one definition that reads through its owner, because four test
  modules read it: `tests/test_import_blocks.py` group 8, `tests/test_unit_manifest.py`, `tests/test_data_file_gate.py`
  and `tests/test_codebase_state.py`. The empty answer is read through `unit_manifest`, its owner, so the harness holds
  no copy of it.
- The pins. Three are added and one is renamed.
  `tests/test_unit_manifest.py::test_the_mode_field_reads_back_as_a_value_of_the_pair_through_its_owner` reads a mode
  as data by planting the row through `render` and reading it back through `parse_rows`.
  `tests/test_data_file_gate.py::test_a_mode_that_is_not_a_value_of_the_pair_is_a_finding_through_the_reader` reads the
  gate's answer for a mode outside the pair, and reads the data rule's source for the names it does not state.
  `tests/test_codebase_state.py::test_the_merge_carries_the_mode_as_the_record_states_it` reads the merged row through
  the record's own reader, so it builds no row, and
  `tests/test_codebase_state.py::test_the_module_states_no_rule_an_owner_states_and_writes_no_file` gained the check
  that the module names no field and states no value set. One pin in `tests/test_import_blocks.py` group 8 is renamed,
  because it read that no shape names a field for the mode and contradicted decision 2: it is
  `test_the_field_name_and_the_pair_are_each_stated_once_in_their_owner`, and it reads each shape through the module
  that owns it. Four pins that state the row shape as a list moved in the same commit:
  `tests/test_unit_manifest.py::test_the_row_fields_are_the_declared_shape_in_order`,
  `::test_the_row_states_placement_through_the_fact_keys_it_already_reads`,
  `::test_a_row_that_is_not_the_declared_shape_is_refused`, and the row builder
  `tests/test_data_file_gate.py::_manifest_row`, which reads the shape through its module and so could not break. The
  pins that read a record as data through its own module read the shape and state no list, so they did not move.
- Documents that state the row shape moved in the same commit: `docs/IMPORT_BINDING.md` §1 fact 11 and §2 decision 2,
  `docs/ARCHITECTURE.md` §3.4, `docs/CODEBASE_ASSEMBLY.md` §3 rule 4, the `docs/README.md` index line for Epic 14,
  `docs/USAGE_GUIDE.md` §The unit manifest, and rule 7 of `src/import_blocks.py`.
- Gate, measured 2026-11-25 single-threaded on the tree that holds this work, in one process: `ruff check .` clean at
  `py310` with the 120-character line length, `ruff format --check .` clean on the same 113 files,
  `python3 tools/check_documents.py` reports no finding, and `python3 -m pytest -p no:cacheprovider` with no parallel
  plugin exits 0 with 1,864 passed and the same 4 `tflint` skips, so 1,868 pins in 55 test modules, in 259.42 s. The
  pin count moved from 1,865 to 1,868: one pin each in `tests/test_unit_manifest.py` (44),
  `tests/test_data_file_gate.py` (31) and `tests/test_codebase_state.py` (14); `tests/test_import_blocks.py` stayed at
  37, because one of its pins is renamed and not added. The test module count stayed 55 and the format file count
  stayed 113. `tflint` is absent on this machine, so the four skips are the four `tflint` pins in
  `tests/test_sanity_gate.py`, and `terraform` is present, so the provider-schema pins ran. No committed golden byte
  moves: `tests/golden` holds no data file and only 87 `.tf` files, and the pins that compare the goldens read `.tf`
  bytes. Run times on this machine move between runs, so each figure here is one measurement.
- Document review: the finding fact 11 answered is closed, because fact 11 now names the pins it means and states that
  no committed data file exists. The open process-debt items in `backlog.md` are unchanged by this piece, and this
  piece opened no new finding.

Files this piece read: `AGENTS.md`, `PLAN.md`, `to-do.md`, `backlog.md`, `agent-status.md`, `acceptance.md`,
`commit.md`, `README.md`, `docs/README.md`, `docs/WRITING_RULES.md`, `docs/IMPORT_BINDING.md`,
`docs/ARCHITECTURE.md` §1, §3.3, §3.4, §4.6, §5, §6, `docs/CODEBASE_ASSEMBLY.md` §3, §7, §9, §11, §14,
`docs/MULTI_RUN_CODEBASE.md` §2 to §6, `docs/USAGE_GUIDE.md` §The unit manifest, `tools/check_documents.py`,
`src/unit_manifest.py`, `src/import_blocks.py`, `src/codebase_state.py`, `src/provenance.py`, `src/sanity_checks.py`,
`tests/conftest.py`, `tests/test_unit_manifest.py`, `tests/test_data_file_gate.py`, `tests/test_codebase_state.py`,
`tests/test_import_blocks.py`, `tests/test_round_trip.py`, `tests/test_layout.py`.

The next piece: Piece 14A.3, the declaration argument, is blocked on decision 3, which is also the decision that an
order-dependent declaration is refused. Piece 14A.4, the report section, needs a report rule that names the units a
run marked, so it cannot be written from decision 2 alone. The two open process-debt pieces, the gate and CI document
and the watch list document, are in `to-do.md` and `backlog.md`. Decision 2 is taken, so the field is landed; decision
3, the declaration rule, is the next decision to take.

## Rules to keep when writing documents

The writing rules have an owner document, `docs/WRITING_RULES.md`, named by `docs/README.md` and by the root index.
This file keeps the status and the links and states no writing rule of its own.

## Test gate and CI

- Gate size, decided 2026-11-13: no smaller default gate is adopted. The full run stays the default gate, and
  the plan check pins and the corpus pins stay inside it; nothing is removed from the full run. A smaller run is
  a working loop on one area only, as an explicit command-line selection, followed by the full run before a
  result is recorded or the work is committed. It is recorded in the report and in `docs/ARCHITECTURE.md` §1.1,
  and not in the tests, because the suite states no marks and a mark would make the smaller set the default.
- The shared test definitions are in `tests/conftest.py`, so a test module reads them there instead of
  defining its own copy, and no test module imports another test module (`docs/ARCHITECTURE.md` §1.1).
  `conftest.py` states the two resource-line patterns as data, both requiring the block brace, each with the
  rule it serves: `RESOURCE_RE` answers the resource type for the pins that read the emitted type set, and
  `RESOURCE_ADDRESS_RE` answers the type and the local name for `tests/test_dependency_wiring.py`, which reads
  `findall` as pairs.
- The CI gate reads the Python floor as 3.10, and the matrix legs are 3.10, 3.11, 3.12 and 3.13, each a minor
  version, never an exact patch. `pyproject.toml` states the floor, and `README.md` and `docs/USAGE_GUIDE.md`
  state the same value. `target-version` equals that floor, so the lint gate enforces the spelling the project
  writes: the PEP 604 union for an optional value, the call rule read from `collections.abc`, and `strict`
  stated at every `zip` call. No pin reads the workflow file, and the workflow states no level of its own, so
  the CI legs read `pyproject.toml`; no leg runs a Python below the level the gate enforces.
- The pins that run the `tflint` rule set and the pins that run `terraform` skip only for a missing binary and
  assert on a non-zero run, so the `terraform-gate` CI job, which has the binaries, is where they run; the
  matrix legs skip them. A pin that reads which directory one of those two checks ran on passes no binary, so it
  runs on a machine that has neither and reads the directory from the result.
- The Terraform version CI runs is stated in the `terraform-gate` job of `.github/workflows/python-tests.yml`, which
  is the CI owner for the tool pins, and the documents read it as the CI statement of that pin. Each pin has one
  owner: the Terraform minimum at `src/commit_actions.py::TERRAFORM_MINIMUM`, the provider version at
  `tests/conftest.py::declared_provider`, and the CI Terraform version in the workflow. A document names the owner it
  reads the value through and states a version only as the pin itself or as the measurement it made, so the recorded
  answers name the binary that answered them: Terraform 1.16.2 is the binary on this machine, and a gate answer
  measured on the CI line names the CI version.

## Watch for the shape tables and the write path

- The input shape table is data with one owner module (`src/input_shapes.py`, `SHAPE_TABLE`), so a document links to
  it and restates no row, which `tools/check_documents.py` check 7 reads, and each held row is measured through the
  owner its `measured_through` names, so an owner that rewords a refusal moves the row in the same commit. A pending
  row states no line and names no owner, so no pin measures a line for it, and a pending row names the piece that
  will give its rule an owner once its decision is taken: a decision cannot hold a row by itself, because the pins
  read a held row only through an owner function they call. A row whose line is a console line holds no prefix,
  because the prefix is the part `container_coverage` states, so the pin reads the prefix through that owner.
- `state_coverage.ownership_key` is the one identity key rule, so the shadow scan, the ownership order and the
  state scan read their keys through it and no module states a second key. The key names the parent scope for a
  shadow, so the report line names which parent entry the child repeats, and the parent entry stays in the
  report, because the console shape names one identity.
- The console line shape is stated in one place, `container_coverage.console_line` (`docs/ARCHITECTURE.md`
  §3.2), so a scan states its fact phrase and its block header and calls it. A finding kind that prints on
  the console must fit the four parts: one position, one identity, one fact. A source named on a console
  line is the source name, never the path, and a fact that compares two entries or two units prints in the
  report only. The five kinds that print are the container coverage finding, the gap entry, the property
  finding, the shadow line, and the splitter line, which names the fact its own row set read.
- The captured part of a report line is stated in one place, `entry_coverage.captured_part`, so `entry_line` and
  `gap_fact` print the same words for the same finding. `PRINTS_VALUE_KINDS` names which kinds print a value, and
  it must stay data: no writer branch may decide the shape per kind. `NAMES_NO_FIELD_KINDS` is the matching data set
  for the kinds that name no field, so a `bookkeeping` row states the row identity only, because the fact its row
  records is the relation the entry carries no value for. A row that prints a value must carry the captured
  object through `row_for`, because `fields` holds the names only, and the value shape is
  `report_value`. A read through the recorded object is what the property scan counts, so a rule that prints a
  value is a rule about a read, and the pin that holds it must run the pipeline, not build a row by hand. A kind
  that names field names must name only fields a read reaches: for a `nested-block` row the print is the only
  output its entry reaches, so the names come from the read record, and for a `bookkeeping` row no read reaches a
  field, because the fact the row records is a relation the entry carries no value for
  (`docs/COVERAGE_MATRIX.md` §1, pinned by
  `tests/test_property_coverage.py::test_the_nested_block_line_names_only_the_fields_the_emitter_reads` and
  `tests/test_property_coverage.py::test_the_bookkeeping_line_names_no_field_for_the_membership_entry_it_marks`).
- The write path landed (`docs/CODEBASE_ASSEMBLY.md` §14): the run writes one directory per unit the manifest
  names, and the codebase root holds the root set. A new file shape must name which set it belongs to, and the
  report counts, the console line and the tests that read the file set change with it.
- The write boundary (`docs/MULTI_RUN_CODEBASE.md` §6, stated in `src/write_path.py` rules 5, 6 and 7) is pinned in
  `tests/test_write_path.py`: the run overwrites the file shapes it has content for inside the unit directory its own
  set names, removes no file and no directory, owns only the files in the two sets so an operator file at the
  codebase root is left as the operator wrote it, and holds no record of what it wrote, so the difference between two
  runs is read through git. A write-boundary pin cannot read which shapes a run wrote from the tree, because a byte
  that agrees with an earlier run is not marked, so it reads a solo run of the same fixture as the shape set. The only
  file-removal call in `src/` is `provenance.prune`, which acts on cache entries outside the two sets, so a delete
  rule anywhere in `src/` would need a new pin.
- `unit_manifest.units` is the run's unit set, so a rule that names a unit for a directory, an owner, or an
  edge reads it through that one function. A unit exists only when the ledger has a row in it, and the fact
  order is the identity join, so a new fact changes every digest and every golden in the same commit.
- The gate reads two unit sets through one rule (`docs/MULTI_RUN_CODEBASE.md` §5): the set the run wrote, read
  through `unit_manifest.units` over the rows its own ledger read, and the set the codebase record names, read
  through `unit_manifest.parse_rows`. A gate rule that names the unit a finding sits in reads the codebase set, and
  a rule that compares two sets reads the run's set, so a unit the run read no rows for enters no count. A call that
  passes no ledger names no run, so `sanity_checks.unit_directories` reads the record, and the block rules, the data
  rule and the report counts read the codebase set. So no gate rule states a unit rule of its own, and no rule reads
  the run's set as the codebase set.
- `VALUE_VARIABLES` is the single shape owner and `sensitive = true` is the `REFERENCE_ONLY` row's rule alone, so
  a new shape word must be read in the table and not by a name list. A reference-only name can be the §5 name of
  the entry that holds the field, so the pin that reads the declaration set walks the fixture through the table
  (`tests/test_variables.py::_reference_names`). The pin that reads the declaration set reads the names the table
  records with no value (`tests/test_variables.py`), and the pin that reads the report rule carves the
  `README.md` file-inventory exception. A change to a shape word moves both pins in the same commit.
- A rule that pins an absence by scanning module sources cannot read a source that names the words it
  forbids, so a scan reads the tool's own modules, and the test name and the module docstring carry no
  forbidden word. The writer scan reads the `src/` set and excludes `src/write_path.py` (the single writer);
  `tests/conftest.py` is the test harness, so it sits outside the set. The pin for the outputs rule is group 7
  of `tests/test_reference_edges.py`; the pins for the file shape are in `tests/test_write_path.py`.
- The fixture assembler is a generator, not a pin, so no document or test may claim that its output is the
  committed fixture. Its read rule is the two F3.8 checks read on the committed bytes, so a hostile fixture is
  skipped by rule and not by name, and the tool names no fixture in its source except its own record. `tools/`
  is not on the test path, so `tests/test_build_kitchen_sink.py` reads the tool's functions through `importlib`
  on the path `tests/conftest.py` builds once, and the tool writes no file, so a run cannot change the record the
  goldens read.
- The block reader in `sanity_checks.py` serves every kind, and the same field reader serves the fields inside a
  container value and the elements of a list value, so a new block shape uses them rather than writing a second
  reader. The round-trip cross-check reads the block set through it with `kinds = ('resource',)`, so it states
  no reader of its own. Its fact compares two sets, so its finding is a coverage fact and prints no console
  line: it is a WARN, the decision `entry_coverage.PROPERTY_RULE` already states for a gap, and the exit code
  stays with the rules that read the files.
- A test that reads the `.tf` set reads it as the gate reads it, keyed by the path from the output directory, so
  a run that names two units is not read as one file. A plan check that runs writes a `.terraform` cache inside
  the directory it ran on, so a pin that reads a corpus run uses a copy of it.
- A plan check reads the directory the run wrote, so a validate pin runs `sanity_checks.check_terraform` once per
  unit directory the run wrote, never at the codebase root, where no configuration file sits. A value the provider
  constrains in its code, not in the schema JSON, is not data the gate can read, so it stays outside the static
  rules and the plan check reports it (`docs/ARCHITECTURE.md` §4.6), and a fixture a plan pin reads states the
  accepted value.
- A field reader must read at the block's own level and stop at the closing quote, or a sub-block field or an
  escaped quote answers for the block's field. Both are pinned in `tests/test_import_blocks.py`, and the scope
  rule reads at the block's own level through the same reader, which takes the sub-block it reads as an argument
  (the action rule reads inside `config`). The same reader also tells a quoted value from a `var.` reference, so
  no second rule decides the shape of a field.
- `PROTOCOL_SHAPE` is the one table for the `protocol` object, `FILTER_SHAPE` is the one table for the filter
  containers, which sit outside it, and `CERTIFICATE_SHAPE` is the one table for the two certificate containers.
  A level either table does not state is not read. A new routing level needs a table row before an emitter, a
  gate rule or a report can read it, and `SHAPE_TO_SCHEMA` is the one pin between a table word and the schema
  word for all three tables. A parse method states a path and never spells a field name: `_protocol_field_name`
  and `_protocol_xml_name` are the two rules; `XML_NAME_EXCEPTIONS` is the protocol table's exception map, and
  `FILTER_XML_NAME_EXCEPTIONS` is the filter table's map, keyed by the container path because one idea spells two
  ways in two containers. All three shape tables are the same row shape read as `resource_mapping.ShapeTable`,
  so the readers and the gate helpers take the table as an argument and state no table name in their finding
  wording, and one helper group (`_shape_level_findings`, `_shape_field_findings`, `_shape_choice_findings`)
  serves all three. A level the export holds as entries states its row as `string_list`, so the walk reads it as
  a `[` value and each element as an entry, which is the certificate profile's `certificate` row.
  `_parse_router` builds the `protocol` dict from the fields the `protocol` row states, and
  `parse_filter_containers` builds each entry dict from the fields its own row states, so the level names are the
  table's names in both. Field order is the table order, so the order a row states is the order the block prints,
  and a row change that moves the order moves the goldens. A level that holds no entry has no container row, so the
  property scan measures nothing for it and the matrix row stays grounded by the table. An entry inside an entry is
  not in the scan scope unless a row names the path with the `entry` segment the parent entry is: the certificate
  profile's list objects are that case, because the field the profile row names is also the spelling of the
  `certificate` section row, so the row that holds the `entry` segment wins by length and the profile row measures
  them. Every other entry inside an entry is grounded by the table instead.
  `_protocol_areas` is the area rule the two OSPF levels share, `_protocol_branch` walks the segments between a
  level dict and an entry level, `_protocol_entries` fills a `string_list` level, `_protocol_entry_level` fills
  an entry level the row states as a field, because its entries live under the element the field names, and
  `_protocol_body` fills the three shapes a level dict cannot hold: the choice the export states by presence, the
  entries inside the level, and the entries inside an `object` field. An entry can hold its own choice, so
  `_protocol_body` takes the entry as the element that holds it, and it reads an entry as a direct child, so an
  entry inside an entry belongs to the level the field names. A presence choice states exactly one alternative,
  and the choice level is not required, so a level that states no choice element prints nothing for it while an
  element that states none is a report row. A choice level can state its alternatives as values, in which case
  `_protocol_choice` reads the value from the element the choice lives under and the print writes it as the reader
  read it. A `member_list` field is read by `_protocol_level`, because its members are values, so no level row
  stands under it and the walk never enters it: `sanity_checks.SHAPE_READS_AS` states which word the reader reads
  each specialization as, and `SHAPE_LEVELS` states which words name a level the walk enters. A parse method
  that reads a container reads only the level its own row states, which `entry_coverage.covering_row` decides. A
  row that states leaf fields only is the walk's stop point, so a field inside it is a gate finding: the
  redistribution entry's `match` and `set` rows are that case, and the six levels inside them are in
  `backlog.md`. A `sensitive` field cannot name itself, so `_protocol_fields` carries the name of the entry that
  holds the level: an entry names itself, and a level inside an entry prints the reference the entry that holds
  it names. `selects` is the one place a row states a choice the provider reads as exactly one, so the level or
  the entry states one of the keys `selects` names, and the gate reads that rule at the level the walk enters and
  at each entry of a `string_list` row through `_shape_choice_findings`. The two rows that state it are
  `peer_address`, where the choice is the whole value, and the `ospfv3` auth profile entry, where the choice is
  two of the entry's fields. The three filter levels `terraform validate` refuses to hold more than one
  (`source_address`, `prefix`, and the redistribution entry's `bgp`) state their alternatives as fields and no
  `selects`, so the choice rule reads nothing for a filter block; that decision is in `backlog.md`.
- The parse method that takes the router element is named in the test helpers that call it for each router:
  `tests/test_entry_coverage.py::_parse_every` and `tests/test_multi_vsys_location.py`. A new level method must
  be added there, or the corpus checks run no method for it.
- A container row that moves from `report` to `emitted` changes the property scan scope, the per-entry report,
  and the `.tf` goldens together, so it cannot be a print-only change. A moved row must be `emitted` with the
  provider type in its note, because the matrix row and the report both read the note. A row must also name the
  type the emitter prints for the entries in that container, so the matrix element names an entry inside the
  container the row names: a shape the emitter reaches through a name fact is not a container the row can
  state, and no entry measures such a row.
- `SCOPE_PLACEMENT` and the location sub-block are one fact: a new scope type needs both the placement key and
  the `SCOPE_ANSWER` entry, and the emitter reads the placement key as the location, so a new row cannot place
  itself in a scope it does not name. A placement key can only name a sub-block that declares `name`, so a row
  that states no key answers that its type has no location field for a container name; the decision for the two
  template-chain rows is owned by `docs/TEMPLATE_STACK_DEPLOYMENT.md` §3 and pinned by
  `tests/test_scope_objects.py::test_a_placement_key_names_a_sub_block_that_can_hold_a_scope_name`. A config type
  has no `template_stack` sub-block, so a config entry inside a stack writes no block and is a finding recorded in
  `backlog.md`.
- A unit that names no device fact answers for the empty fact, so no output states a device for it: `unit_manifest`
  reads the identity from the facts `facts_of` keeps, `Shared` in `device_group` stays the parse fallback, the site
  record holds no row because the run read no value, `provider.tf` names no `target`, and both action blocks name the
  fact `named_fact` selects. The decision for the new-site shape is owned by `docs/TEMPLATE_STACK_DEPLOYMENT.md` §4,
  which names the five owner test modules that pin it.
- The entry name is never a property. A row whose provider type declares no `name` reaches the block through
  `entry_coverage.name_field`; no emitter, gate rule, or test should state the field again.
- One place decides the shape of a value: `resource_mapping.VALUE_VARIABLES`, read at the print site. A new
  field a table row maps must be read by the emitter, the gate and the `.tfvars` writer through the same table,
  and the table must cover every field `LOCATION_SCHEMA` declares.
- The §5 naming rule lives in `naming.py`. No module may define a second one; `TerraformGenerator.sanitize_name`
  is a delegate and the data modules take the rule as an argument.
- One place decides the shape of a reference field: `TerraformGenerator.name_ref`, read at the print site. The
  mechanism for a name it cannot resolve is the plain name it returns, so a write path that runs the rule per
  unit changes the corpus pin lists, not the rule.
- The import position for the four `*_policy_rules` types must be the position the live config holds, and the
  F3.5 rulebase decision gates it. No block is written for a rule entry until both land.
- The generated `README.md` names `imports.tf`, `SITE_DATA.json` and `site.auto.tfvars`, and it names `target`
  as a fact the tool names as a variable. It states no row, no value, no mapping result, no count, no path and
  no timestamp, so the report rule holds for the site record with the README as the file-inventory exception
  (`tests/test_site_data.py`).
- Actions need the Terraform minimum, and the value `src/commit_actions.py::TERRAFORM_MINIMUM` states it, so the
  committed goldens carry the same value and a change to the minimum is a golden change. The level the action shape
  needs is 1.14, measured with `terraform validate`, which is a language fact and is stated separately from the
  minimum.
- The credential rule has one statement and one owner document, `docs/CODEBASE_ASSEMBLY.md` §11, so every other
  document links to it. `source_fetch.py` is the only tool module that states the environment name, and the pin
  `tests/test_variables.py::test_the_generated_block_names_the_environment_the_fetch_layer_reads` holds both
  halves: the generated block names that name, and no other `src/` module states it. `VALUE_VARIABLES` decides
  the shape, so the host is an `operator_supplied` row and no name list decides a provider argument or a marking.
- The prune action reads the record file the run wrote, because the record directory is the output directory and
  `SOURCE.txt` is a codebase root-set file. `provenance.prune` decides through `prunable_entries` and builds no
  path, so no path rule for a record directory can appear in the module that owns the record. A state record
  references nothing, so it prunes nothing and protects nothing, and the action reads a record file, not one
  record. `--prune-cache` is an opt-in flag that gates the step; it names no part of the layout, so the no-flag
  scan holds, and it cannot change what the gate counts or the exit code the gate decides.
- One place answers a destination: `entry_coverage.EntryLedger.destination`, in the order the per-entry fact on
  the recorded object, the destination `mark` recorded, the container table row. `mark` states no destination of
  its own, so a call site that states `destination='report'` for a report-only entry restates a fact the entry
  already holds. The fact is read through `RecordingDict.value()`, so the decision records no property use and the
  order of `mark` and the field cannot change the answer; `mark_skipped` records no object, so a skipped entry
  answers through the mark. The cross-check counts only `emitted` rows, so an entry the run reports enters no
  count.
- A coverage fact that comes from a run must be read from the run's ledger, so the scan tests run the pipeline
  in process. The round-trip cross-check reads the run's ledger as an argument, so its pins run the pipeline in
  process too, and a `run_checks` call that passes no ledger reports the check as NOT RUN rather than guessing a
  count.
- A cycle test needs two units that each declare a name the other one uses, because the rule resolves a name
  only inside the unit that declared it (`tests/fixtures/reference_cycle.xml`).
- The splitter (`src/split_device_groups.py`) reads the rules its owners state and defines none of its own: the
  single writer for the bytes of a split file, `naming.py` §5 for the file name, the source line as the
  identity of an entry for its three tables, and `container_coverage.console_line` for the shape of the fact its own
  row set read. It owns its own output path, so it names no builder from `write_path.py`, and the writer scan reads
  the element-writer shape so no module can add a writer of its own. A file name two entries read to is a refusal,
  not a numbering, because a numbering depends on the order the entries appear in (§6). The shared merge dedupes the
  pair (path, name) at the level the path names, so an entry stays at its own path and one name at two depths is two
  entries. A block prints only when it has a finding, so a run that read rows prints no diagnostic line.
- The LF rule is a byte rule, so the goldens and the no-change tests change with the write path. The rule is in
  the one write function, and `docs/ARCHITECTURE.md` §6 states it.
- Path 2 adds `api_requests.py` and `api_to_terraform.py`, and both are read by the pins that scan the `src/`
  set: the writer scan, the environment-name scan, the console-line scan, and the second-naming-rule scan. So
  path 2 states no second rule of any kind, and each new path 2 rule names the module that holds it and the test
  that pins it. Its rules are in `docs/API_CONVERSION_PATH.md`.

## The version pins (planning, 2026-11-22)

This work was planned in the `pin-update` worktree, which merged into main on 2026-11-23. Nothing was pinned at the
time of the plan: the decisions are in `PLAN.md`, the pieces are in `to-do.md`, and `acceptance.md` holds the
criteria and the measurements the decisions rest on.

The measurements taken 2026-11-22, single-threaded, in `/tmp/opencode`:

- `terraform providers schema -json` answers byte for byte the same for provider 2.0.14 and 2.0.15: 2,146,209
  bytes, md5 `dfab791bae568bdd5ccdc69ca066a5b4`. So the provider move changes no measured provider fact and changes
  only the bytes the pin states.
- The 17 golden unit directories validate on provider 2.0.15 with Terraform 1.16.2, and the same 17 validate with
  Terraform 1.17.2, so the action grammar is accepted on both lines.
- `tests/tflint/probe.json` reproduces byte for byte on tflint v0.66.0 with the bundled ruleset v0.17.0, for the
  probe at either provider version, read through the flags `sanity_checks.TFLINT_FLAGS` and
  `sanity_checks.TFLINT_RULE_FLAG` state.
- The gate answers the same on the pinned tool versions as on the newer ones, apart from the one ruff finding listed
  in `backlog.md`.

The two decisions, taken 2026-11-22: the floor is `>= 1.16` with CI at 1.16.7, so no statement in the documents
reaches past what was measured, and the Terraform minimum gets one owner the way the provider version has one. The
pieces are 12A.1 to 12A.3 in `to-do.md`. The gate baseline this task starts from is the Piece 11C.1 measurement in
the Current position above; the measurements below were taken on the tree before Piece 11C.1 landed.

## Position in the `import-pairing` worktree (Epic 14 planning, 2026-11-23)

Epic 14, the blocks a run binds to the live config, is planned in the `import-pairing` worktree on branch
`import-pairing`, based on main `c845f07`. The design record is `docs/IMPORT_BINDING.md`, the pieces are in
`to-do.md`, the criteria are in `acceptance.md`, and the facts that need a live target are in `backlog.md`. No
decision is taken, so no piece can be written from one yet, and no `src/` file is touched until a piece lands. The
shared tracking markdown needs a manual join against main at merge.

What the record states, measured offline: the binding decision is run-wide and reaches no record, so a later run
cannot read it back and no gate rule can name a unit that should have written blocks; the address half is already
stable across runs; no id can name a device because an id states only what the block states; the four
`*_policy_rules` types cannot be bound with the shape the emitter writes; a read-through name is never bound; the
whole-block fact is measurable today and has no name and no owner; the change half of a plan is not the tool's
output; the mode cannot ride on the selection; a mode field is a shape change, so the committed rows move with it.

The nine pending decisions are in the record §2, each naming what it needs: the mode values and the level, the
mode's owner, the declaration rule, the whole-block fact's name and owner and severity, the completeness half, the
device fact, the rule types, the read-through order, and permanence. One Terraform behaviour stays a decision to
take on measurement, because a pin cannot read it without a device.

Gate, measured 2026-11-23 single-threaded on the tree that holds this work: `ruff check .` clean at `py310`,
`ruff format --check .` clean on the 110 files it reads (81 Python, 29 markdown),
`python3 tools/check_documents.py` reports no finding, `python3 -m pytest` in one process exits 0 with 1,796
passed and the same 4 `tflint` skips in 256.8 s, the same counts as the main baseline this branch starts from,
because no test and no `src/` file changed. `tflint` is absent, so the 4 skips are the `tflint` pins in
`tests/test_sanity_gate.py`; `terraform` is present, so the provider-schema pins ran. The new document is named in
the `docs/README.md` index and carries its owner row, which
`tests/test_layout.py::test_the_indexes_name_every_document_under_them` holds.

Files this piece read: `AGENTS.md`, `PLAN.md`, `to-do.md`, `backlog.md`, `agent-status.md`, `acceptance.md`,
`commit.md`, `docs/README.md`, `docs/INPUT_SHAPES.md` for the record shape, `docs/CODEBASE_ASSEMBLY.md` §7 and
§13, `docs/ARCHITECTURE.md` §3.2 and §4.6, `docs/MULTI_RUN_CODEBASE.md` §1 rules 1 and 2,
`src/import_blocks.py`, `src/rule_data.py`, `src/unit_manifest.py`, `src/ownership.py`, `src/entry_coverage.py`,
`src/codebase_state.py`, `src/sanity_checks.py`, `tools/check_documents.py`, `tests/test_layout.py`.

The next step is the acceptance review of the criteria, then the first decision, which is whether the mode stops at
the unit (record §2 decision 1). The second decision is the shape cost in fact 11, because it names the committed
files a piece would move. `acceptance.md` holds the Epic 14 criteria until the first piece lands.

Merge, 2026-11-23: the branch merged into main at `9fe33c7` with a merge commit, so the Epic 14 pieces run on main
and the `import-pairing` worktree holds no further work. No manual join was needed, because main had not moved past
`c845f07`, the commit the branch was based on. Neither was pushed. The gate re-measured 2026-11-23 single-threaded
on the merged tree: `ruff check .` clean at `py310`, `ruff format --check .` clean on the 110 files it reads,
`python3 tools/check_documents.py` reports no finding, and `python3 -m pytest` in one process exits 0 with 1,796
passed and the same 4 `tflint` skips in 271.5 s, the same counts as the measurement above, because no test and no
`src/` file changed by the merge.
