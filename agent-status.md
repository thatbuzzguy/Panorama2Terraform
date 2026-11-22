# Agent Status

## Current position

Piece 11B.2 landed, 2026-11-22: `unit_manifest.units` is the one unit rule over either row set, so the codebase
unit set is read through the same rule as the run's set, and the rule that the run writes no directory for a unit
it read only through the record is stated in `write_path.py` rule 4. Five pins, no golden moved, not pushed. The
piece is reviewed at `c079d02` and `e28c5d7`: every committed criterion is met by the tree, the measurement was
re-run independently through the record modules on committed material, and two document lines were corrected —
`docs/LICENSING.md` stated 19 modules without a notice while `src/` holds 24 and 4 carry one, and `README.md`
§Testing named the facts `tests/test_write_path.py` holds but not its run set rule. No code and no pin changed.
The next piece is 11B.3, ownership, edges and the plan order read over the merged set. The design record for Epic 11,
the codebase several runs write into, is `docs/MULTI_RUN_CODEBASE.md`, the pieces are in `to-do.md`, and
`backlog.md` holds the conditions this piece could not state as rules. `acceptance.md` is this piece's record.

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

What Piece 11B.2 landed:

- `src/unit_manifest.py` rule 4 now reads the same unit rule over both row sets: `units` answers for the rows the
  run's ledger read and for the rows a record read back through `parse_rows`, because `facts_of` already reads a
  ledger row and a read-back row the same way. A reader that has no ledger and no record names no unit, so it gets
  the empty set. No second unit rule and no second unit set appears: `codebase_state.py` still restates no row
  shape and names no unit set of its own, and the `src/` scans read the 24-module set clean.
- The two facts and their difference, measured on the committed pair: the kitchen-sink run as the codebase answers
  11 units, the `address_objects.xml` run answers 1 unit, the merged set answers the same 11, the run set is inside
  the merged set, and the 10 units only the codebase set names are read as the record states them. For a run that
  read nothing from the record the two sets are the same set, so no committed golden moves.
- The write fact, measured on a real run that wrote into a copy of the kitchen-sink output: the run added no
  directory, wrote no file inside the 10 directories the record names, and left every byte inside them as the first
  run wrote them; it wrote inside the one directory its own set names. The rule is stated in `write_path.py` rule 4,
  which keeps the two builders and the one writer and reads both sets through `unit_manifest`.
- Five pins, one per fact, in the module that owns the fact: 2 in `tests/test_unit_manifest.py`, 2 in
  `tests/test_write_path.py`, 1 in `tests/test_codebase_state.py`. Each pin is grounded on a committed run read
  through `parse_rows`, and none builds a row by hand.
- Two measured facts the piece left as they are, because they belong to another piece: a run writing into an
  existing codebase exits 1 because the gate reads the whole codebase against the run's own ledger (Piece 11B.4),
  and the run writes its own root records rather than the merged set because `generate_run` does not call the merge
  (Phase 11C).

Gate, measured 2026-11-22 on the tree that holds this piece, single-threaded: `ruff check .` is clean at `py310`,
`ruff format --check .` is clean on the 108 files it reads (81 Python files, 27 markdown files),
`python3 tools/check_documents.py` reports no finding, and `python3 -m pytest` passes 1,772 pins with the same 4
skips for the missing `tflint` binary — 1,776 pins in 54 test modules, 5 more than the 1,767 pins Piece 11B.1
measured, in 236.45 s. Read through the per-module collection counts: `tests/test_unit_manifest.py` collects 41,
`tests/test_write_path.py` collects 23, and `tests/test_codebase_state.py` collects 10, so the 5 new pins are 2, 2
and 1. `terraform` is present on this machine, so the pins that read the live provider schema ran, and the 4 skips
are the `tflint` pins in `tests/test_sanity_gate.py`. `src/` holds 24 modules, which is the count
`docs/LICENSING.md` states. No committed golden changed. Measured again on the tree that holds the review record,
also single-threaded: the same 1,772 pins and the same 4 `tflint` skips, read from the run's progress output, in
282.0 s of wall time, `ruff check .` clean at `py310`, `ruff format --check .` clean on the same 108 files, and
`python3 tools/check_documents.py` reports no finding with the two corrected document lines in the tree.

What Piece 11B.1 landed and was reviewed:

- `src/codebase_state.py` states `JOIN_KEYS`, one row per record with the fields the key is built from and the fact
  the key joins on, and `merge_rows`, the merge rule in one function: the run's rows replace the codebase's rows for
  the rows the run named, and the rows for the units the run did not build stay as the record states them. The module
  defines no row shape, no reader, no writer, no path rule, no console line, no environment name and no naming rule,
  so the `src/` scans read it clean, and it names no file, so `sanity_checks.DATA_FILES` stays the only data rule.
- The join key per record, measured on the accepted corpus and pinned: the manifest on `directory`, which is the §5
  shape of the five scope facts; the ownership record on (`type`, `entry`) with the facts, read through
  `state_coverage.ownership_key`; the edge record on the pair of entry identities with the matrix row and the entry
  name; the site record on `directory`. The key is unique per row for every accepted fixture, so no second key is
  needed.
- The order of a merged set is read through each record module's own order rule, not through which side a row came
  from: `unit_manifest.FACT_KEYS`, `ownership.row_key`, `reference_edges.FIELD_ORDER`. `site_data.py` states no order
  rule for a row it reads back, so a merged site set is read in the join-key order, which is the order the committed
  fixtures already show.
- The byte rule: a record with no existing file is the run's own set, so the merge writes the bytes a single run
  writes today. The run path is unchanged, because the merge is not called by `generate_run` — that step is
  Phase 11C — so no committed golden moved.
- Ten pins, one per stated fact, grounded on committed material: the codebase's rows are the rows a run wrote for
  `tests/fixtures/kitchen_sink.xml` and the run's rows are the rows a run wrote for
  `tests/fixtures/address_objects.xml`, each read back through its own module's `parse_rows`. No pin builds a row by
  hand.
- Two conditions the piece cannot state as rules are in `backlog.md`, and no rule was invented for either: the site
  record's order for a row it reads back, and the ownership key holding one row for an entry two sources state.

Gate as Piece 11B.1 measured it, single-threaded, the baseline this piece reads: `ruff check .` is clean at `py310`,
`ruff format --check .` is clean on the 108 files it reads (81 Python files, 27 markdown files),
`python3 tools/check_documents.py` reports no finding, and `python3 -m pytest` passes 1,767 pins with the same 4
skips for the missing `tflint` binary — 1,771 pins in 54 test modules, 10 more than the 1,761 pins the previous piece
measured, in 246.53 s. Read through the per-module collection counts: `tests/test_codebase_state.py` collects 9 and
`tests/test_data_file_gate.py` collects 28, so the new pins are 9 in the new module and 1 in the module that holds the
data rule's pins. `terraform` is present on this machine, so the pins that read the live provider schema ran, and the
4 skips are the `tflint` pins in `tests/test_sanity_gate.py`. `src/` holds 24 modules, which is the count
`docs/LICENSING.md` states. No committed golden changed.

The next piece is 11B.3. `backlog.md` holds the conditions the pieces recorded and the items that need a fact a live
target states:
the device the operator adds to a device group for a new site, and the device serial a push target names
(`docs/TEMPLATE_STACK_DEPLOYMENT.md` §4);
the rulebase value string and the rule position (F3.5), which also gate the `rulebase` row column and the import
block for a rule entry; a config entry inside a stack needs a provider location shape; the EDL `certificate_profile`
field needs a rule that makes the EDL site resolve names; the per-entry report `profile_name` column needs a value the
provider does not declare; and the path 2 live facts in `docs/API_CONVERSION_PATH.md` §4. It also holds the two
shapes the comparison table cannot state as one name: the address `value`, which the run prints under four names, and
the tag text, which `parse_tags` stores only as `comments`, so the `description` key the row declares is never filled.

The Phase 11A review records for Pieces 11A.1, 11A.2 and 11A.3 are not kept here: the phase is complete, and the git
history holds them. `acceptance.md` holds the record for the current piece.

## Acceptance review of Piece 11B.1 (2026-11-22)

The piece is reviewed at `4a5b871` and `0ee48a8`, both not pushed, and every committed criterion is met by the
tree. The review changed nothing and committed nothing; the review record is the git history. The join keys were
re-measured on the 67 accepted fixtures through the record modules' own `parse_rows`: the key is unique per row
for every record on every fixture, and `ownership.row_key`'s `source` part separates no pair the join key does
not already separate. The site file order is the join-key order on all 7 fixtures with site rows, and the manifest
fact order differs from the join-key order on 26 fixtures, which is the count the order pin holds. The two-run
counts reproduce: manifest 11 against 1 gives 11, ownership 61 against 5 gives 62, edges 9, site 3. Every pin in
`tests/test_codebase_state.py` passes on its own, as does the new pin in `tests/test_data_file_gate.py` and the
index pin in `tests/test_layout.py`; the four `src/` scans read the 24-module set clean with `codebase_state.py`
in it, no test module imports another test module, and no `src/` module imports anything from `tests/`. The gate
was re-run single-threaded and agrees with the counts recorded above: `ruff check .` clean at `py310`,
`ruff format --check .` clean on 108 files, `tools/check_documents.py` reports no finding,
`python3 -m pytest` passes 1,767 pins with the same 4 `tflint` skips — 1,771 pins in 54 test modules, 81 Python
files — in 256.60 s, against the 246.53 s recorded when the piece landed.

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
