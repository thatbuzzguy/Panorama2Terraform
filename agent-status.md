# Agent Status

## Current position

Piece 11A.2 landed, 2026-11-21: the targeted read set in `src/api_requests.py`, and the rule that a name the
selection excludes is not an index entry, so the join reports no finding for it. The next piece is 11A.3, the byte
agreement between a targeted run and a full run for the same unit. The design record for Epic 11, the codebase
several runs write into, is `docs/MULTI_RUN_CODEBASE.md`, the pieces are in `to-do.md`, and the result of Piece
11A.2 is recorded in `acceptance.md`.

Four decisions are agreed, and they are the shape of the record:

1. The four root records become accumulated codebase state: a run reads the existing record through its own
   module's `parse_rows`, replaces the rows for the units it built, and keeps the rows for the units it did not.
   The merge is keyed by row identity, not by run, so no record can state which run wrote it, which is what keeps
   the no-timestamp rule and the determinism rule intact. The reports and `SOURCE.txt` stay per run.
2. The selection names the read set, not what the run writes. A run that reads a whole export declares no
   selection, so `unit_manifest.units` stays the only unit set.
3. The run overwrites the files it owns in a unit directory it wrote into, names the units it wrote in its report,
   and holds no record of what it wrote before; the byte difference between two runs is read through git.
4. The merged records are the codebase-level view. The run's report gains one section that names the units the run
   built and the codebase units it did not read, so no fifth root-set file states the unit set a second time.

What Piece 11A.2 landed:

- `api_requests.targeted_read_set` states the lists a targeted run reads. It is the four membership lists for both
  shapes, because `parse_associations` reads a membership fact only from the response that holds the container the
  list names, and the response for an entry holds the entry itself, so an entry read states no membership fact and no
  list states a fact the selected unit can state on its own. The set narrows through the names, not through the lists.
- `api_requests.targeted_names` states the scopes a targeted run reads, as the pairs the join answers them with: no
  selection is every name the tables read; a place selection is the names inside that place; an entry selection is
  the entry plus the names the tables hold for it, which are the membership facts its identity cannot state on its
  own. A name the selection excludes is not in the set, and a table key names no entry.
- `api_requests.scope_index` takes the selection as an optional argument and filters its set through `targeted_names`,
  so a name the selection excludes gains no entry and `unit_findings` reports no finding for it, while the entry the
  selection names enters through `scope_path` because the run read the response for it. With no selection the index
  is the index it builds today.
- `api_to_terraform.run_order` reads the read set through `api_requests.targeted_read_set` and passes the selection
  to `api_requests.scope_index`, and `lists_read` reads the read set through its owner, so the entry point states no
  read set and no name rule of its own and gains no function. `run_order` stays the only place the read order is
  stated.
- The join, the unit rule, the gate rule, the naming rule, the console line and the report rule are unchanged: the
  targeted index flows through `join_units`, `unit_findings`, `check_request_set` and the record, so a place read
  that holds a name the selection excludes is not refused and the gate reports no finding for it.
- Nine pins are new, six in `tests/test_api_requests.py` (group 8) and three in `tests/test_api_path.py` (group 10).
  Three pins changed: the run order pin reads the order through `api_requests.targeted_read_set`, the entry point
  owners pin holds `targeted_read_set` and `targeted_names` as `api_requests`' rules, and
  `test_a_selection_that_names_no_unit_is_an_argument_error_on_a_run` reads the difference the read rule creates
  instead of byte equality with a run that declares no selection. The committed goldens are unchanged.

Gate, measured 2026-11-21 on the tree that holds this piece, single-threaded: `ruff check .` is clean at `py310`,
`ruff format --check .` is clean on the 106 files it reads (79 Python files, 27 markdown files),
`python3 tools/check_documents.py` reports no finding, and `python3 -m pytest` passes 1,754 pins with the same 4
skips for the missing `tflint` binary — 1,758 pins in 53 test modules, 9 more than the 1,749 pins the previous piece
measured, in 311.05 s. Read through the per-module collection counts: `tests/test_api_requests.py` collects 32 and
`tests/test_api_path.py` collects 39, so the nine new pins are 6 and 3 in those two modules. `terraform` is present
on this machine, so the pins that read the live provider schema ran, and the 4 skips are the `tflint` pins in
`tests/test_sanity_gate.py`.

Piece 11A.3 is open: the byte agreement between a targeted run and a full run for the same unit, for content that
names no read-through name. `backlog.md` holds the items that need a fact a live target states:
the device the operator adds to a device group for a new site, and the device serial a push target names
(`docs/TEMPLATE_STACK_DEPLOYMENT.md` §4);
the rulebase value string and the rule position (F3.5), which also gate the `rulebase` row column and the import
block for a rule entry; a config entry inside a stack needs a provider location shape; the EDL `certificate_profile`
field needs a rule that makes the EDL site resolve names; the per-entry report `profile_name` column needs a value the
provider does not declare; and the path 2 live facts in `docs/API_CONVERSION_PATH.md` §4. It also holds the two
shapes the comparison table cannot state as one name: the address `value`, which the run prints under four names, and
the tag text, which `parse_tags` stores only as `comments`, so the `description` key the row declares is never filled.

## Acceptance review of Piece 11A.2 (2026-11-21)

The piece is reviewed at `153dbf2` and `3067372`, both not pushed, and the review record is `acceptance.md`. Every
criterion is met, and nothing was wrong: no code, pin or document disagreed, so the only change is the record, which
now states each criterion as met and carries the review's timings. The measurement is confirmed by an independent re-run through the tool's
own modules on the committed response set and on the content `tests/test_api_path.py` holds: the run that declares no
selection reads `device-group`, `templates`, `device-group/entry/Office-FW` and `templates/entry/HQ-Networks`, the run
that selects `device-group` reads the first three, the join reports a finding for `HQ-Networks` on the whole set and
none on the targeted set, the unit rule names the same units both ways, and the committed entry read answers no
membership fact while the committed `device-group` read holds `Office-FW` and `Unassigned-DG`. A targeted run writes
the same file set as a run that declares none, and its bytes differ.

Each of the nine new pins passes on its own, in the module that owns its rule, and the three changed pins pass on
their own: the run order pin reads the order through `api_requests.targeted_read_set`, the entry point owners pin holds
`targeted_read_set` and `targeted_names` as `api_requests`' rules, and
`tests/test_api_path.py::test_a_selection_that_names_no_unit_is_an_argument_error_on_a_run` keeps the argument-error
part and reads the file set and the difference. No pin was removed. The index rule pin
`tests/test_layout.py::test_the_indexes_name_every_document_under_them` passes, and the import rule reads clean: no
test module imports another test module, `src/` imports nothing from `tests/`, and the shared facts are read from
`tests/conftest.py`. The pins that hold the single-owner claims pass unchanged.

The gate was re-measured single-threaded at `3067372`: `ruff check .` clean, `ruff format --check .` clean on the
106 files it reads (79 Python, 27 markdown), `python3 tools/check_documents.py` reports no finding, and
`python3 -m pytest` passes 1,754 pins with the same 4 `tflint` skip — 1,758 pins in 53 test modules,
`tests/test_api_requests.py` at 32 and `tests/test_api_path.py` at 39. The piece measured 311.05 s and the review's two
confirmation runs measured 310.75 s and 316.00 s on the same counts, so run-to-run time varies.
Piece 11A.3 stays open.

## Acceptance review of Piece 11A.1 (2026-11-21)

The piece is reviewed at `22e4401`, `f2a20b8` and `c23920b`, none pushed, and the review record is `acceptance.md`.
Every criterion is met. Three things were wrong and are corrected, and no pin changed:

- The gate line stated the 106 files `ruff format --check .` reads as Python files. Measured: 79 Python files (23 in
  `src/`, 54 in `tests/`, 2 in `tools/`) and 27 markdown files.
- The single-split wording read as a rule for all of `src/`. It holds for the two rules that read the shape
  definition; eight places split a path string for a fact of their own, so the two docstrings in
  `src/container_coverage.py` now state the scope the pins ground, and the split sites are recorded in `backlog.md`.
- `acceptance.md` criterion 3 named "the group that holds the `--path` pins" in `tests/test_api_requests.py`. That
  module holds no `--path` pin, so the criterion now names group 5, the group that reads the module's rules through
  their owners.

Each pin the review record names passes on its own, and the import rule reads clean: no test module imports another
test module. The gate was re-measured single-threaded, 1,745 passed and 4 skipped, 1,749 pins in 53 test modules:
317.05 s at `c23920b` and 436.09 s on the tree that holds the corrections; `ruff check .` is clean, `ruff format
--check .` is clean
on the 106 files it reads, and `python3 tools/check_documents.py` reports no finding. Piece 11A.2 stays open.

## Acceptance review of Piece F5.6 (2026-11-21)

The piece is reviewed at `43d6101` and `bff26d6`, both not pushed. The measurement is confirmed by an
independent re-run through the tool's own modules on the 42 matrix rows: 42 rows, 26 types reach a pair, 16
rows reach no field at the block's own level, four pairs name the parse key and a different attribute name and
are the table rows, and no printed field answers for more than one parse key. Every pin in group 7 passes on its
own, the mapped-pair pins read the run's ledger, and the drift line shape is pinned. The gate is confirmed
single-threaded at 1,738 passed and 4 skipped, 1,742 pins in 53 modules, `tests/test_state_coverage.py` at 30:
273.93 s before the corrections and 247.73 s after them.

Six things were wrong and are corrected, and no pin changed:

- The `tags`/`tag` example was still stated in `docs/USAGE_GUIDE.md` (two places) and in the `docs/ARCHITECTURE.md`
  limitations, and both stated that the scan compares only a property both sides name the same way, which the
  table contradicts. The three places now state the rule and name `docs/ARCHITECTURE.md` §3.2, the owner document.
- The reason given for the 16 rows was stated as the nested level or the `for_each` map for all of them, which is
  true for 10. The measured split is now stated in §3.2, in the `src/state_coverage.py` comment, and in the test
  comment.
- The tag entry in `backlog.md` said the parse reads the tag text as `comments` or as `description`; `parse_tags`
  stores only `comments`, so `description` is a declared property the parse never fills.
- The row-by-row list of the four table rows in §3.2 and in `agent-status.md` restates a machine-readable table,
  so both now name the table and its count instead.
- `acceptance.md` criterion 4 named five pins for a group that holds six, so the missing fact — the parse key the
  run prints under four names — is added there.
- `tests/test_state_coverage.py` numbered its sections 1 to 5 and 7 and held the property-read-parity pin inside
  the drift section, which contradicted its own group list, so that pin is now under its own group 5 heading and
  the record section is group 6.

## Acceptance review of Piece E10.3 (2026-11-21)

The piece is reviewed at `1977366` and `73764c2`, both not pushed, and every measurement §4 states is
confirmed by an independent re-read through the tool's own modules on `tests/fixtures/template_no_device.xml`.
The review record is `acceptance.md`. Two things were wrong and are corrected:

- `docs/CODEBASE_ASSEMBLY.md` still named Pieces E10.2 and E10.3 as open work in three places (the top of
  the document, the end of §2, the end of §14), which contradicts the landed state in `PLAN.md` and
  `docs/README.md`. The three sentences are removed, and the zero-change plan half of §7 is the only part
  of that document that stays open.
- The pin-delta baseline. Six is the delta from Piece E10.2's 1,730 pins, not from the 1,726 measured at
  `4351ca0`, which is ten. Read through the per-module collection counts, as the convention states.

Also recorded in the review record: `acceptance.md` as written named `entry_coverage.identity_of`, while
`identity_of` is `panorama_to_terraform.PanoramaParser.identity_of`. No code or pin changed, so no pin moved.

Each of the five pins passes on its own, in the module that owns the rule, and states only the fact §4 reads
through that module. The index rule pin `tests/test_layout.py::test_the_indexes_name_every_document_under_them`
passes, and the import rule reads clean: no test module imports another test module, and no `src/` module
imports anything from `tests/`.

## Rules to keep when writing documents

- One owner document per rule; every other document links to it.
- Machine-readable tables are code. A document explains a table and never restates it
  row by row, so a regenerated table cannot drift.
- No test counts in a document. A document names the test that pins a rule; the
  count lives in `agent-status.md` and the git history.
- A document that names a test names a test that exists.
- A pin measures content or a name, never the wording of a document. A wording check is a document review, so it
  lives in `tools/check_documents.py`, which the test set does not read.
- A claim about what the tool does must name the module or the test that holds it. A
  feature id is written only when a module or a test uses it as a name.
- ASD-STE100 Simplified Technical English, no marketing voice, no emoji.
- A historical record is not kept in the markdown. The git history is the record, and the
  markdown states the current state.
- A record is data, so a document describes its fields and never restates a record. The
  example in `docs/USAGE_GUIDE.md` is an illustration with a shortened hash, not a pin.
- Completed epic, phase, feature and task detail is removed from the tracking markdown after
  the work is committed; `AGENTS.md` states the rule.

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
  matrix legs skip them.

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
- The write path landed (`docs/CODEBASE_ASSEMBLY.md` §14): the run writes one directory per unit the manifest
  names, and the codebase root holds the root set. A new file shape must name which set it belongs to, and the
  report counts, the console line and the tests that read the file set change with it.
- `unit_manifest.units` is the run's unit set, so a rule that names a unit for a directory, an owner, or an
  edge reads it through that one function. A unit exists only when the ledger has a row in it, and the fact
  order is the identity join, so a new fact changes every digest and every golden in the same commit.
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
- A plan check reads the directory the plan runs on, so a validate pin runs `sanity_checks.check_terraform` once
  per unit directory the manifest record names, never at the codebase root, where no configuration file sits. A
  value the provider constrains in its code, not in the schema JSON, is not data the gate can read, so it stays
  outside the static rules and the plan check reports it (`docs/ARCHITECTURE.md` §4.6), and a fixture a plan pin
  reads states the accepted value.
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
  table's names in both. Field order is the table order, so the order a row states is the order the block
  prints, and a row change that moves the order moves the goldens. A level that holds no entry has no container
  row, so the property scan measures nothing for it and the matrix row stays grounded by the table. An entry
  inside an entry is not in the scan scope unless a row names the path with the `entry` segment the parent entry
  is: the certificate profile's list objects are that case, because the field the profile row names is also the
  spelling of the `certificate` section row, so the row that holds the `entry` segment wins by length and the
  profile row measures them. Every other entry inside an entry is grounded by the table instead.
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
- Actions need Terraform 1.14 or later; the committed goldens now declare it, so a change to the minimum is a
  golden change.
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
  already holds. The fact is read through `RecordingDict.value()`, so the decision records no property use and
  the order of `mark` and the field cannot change the answer; `mark_skipped` records no object, so a skipped
  entry answers through the mark. The cross-check counts only `emitted` rows, so an entry the run reports enters
  no count.
- A coverage fact that comes from a run must be read from the run's ledger, so the scan tests run the pipeline
  in process. The round-trip cross-check reads the run's ledger as an argument, so its pins run the pipeline in
  process too, and a `run_checks` call that passes no ledger reports the check as NOT RUN rather than guessing a
  count.
- A cycle test needs two units that each declare a name the other one uses, because the rule resolves a name
  only inside the unit that declared it (`tests/fixtures/reference_cycle.xml`).
- The splitter (`src/split_device_groups.py`) reads the rules its owners state and defines none of its own: the
  single writer for the bytes of a split file, `naming.py` §5 for the file name, and the source line as the
  identity of an entry for its three tables. It owns its own output path, so it names no builder from
  `write_path.py`, and the writer scan reads the element-writer shape so no module can add a writer of its own.
  A file name two entries read to is a refusal, not a numbering, because a numbering depends on the order the
  entries appear in (§6). The shared merge dedupes the pair (path, name) at the level the path names, so an
  entry stays at its own path and one name at two depths is two entries.
- The LF rule is a byte rule, so the goldens and the no-change tests change with the write path. The rule is in
  the one write function, and `docs/ARCHITECTURE.md` §6 states it.
- Path 2 adds `api_requests.py` and `api_to_terraform.py`, and both are read by the pins that scan the `src/`
  set: the writer scan, the environment-name scan, the console-line scan, and the second-naming-rule scan. So
  path 2 states no second rule of any kind, and each new path 2 rule names the module that holds it and the test
  that pins it. Its rules are in `docs/API_CONVERSION_PATH.md`.
