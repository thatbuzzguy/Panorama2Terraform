# Agent Status

## Current position — the git history

The main line is the rewritten history. `development`, `main` and `dev` point at it: 177 commits, the
9 upstream commits with their hashes and their author `devnullNZ <gordon@gswsystems.com>`, then the 46
phase 2 commits with the author `rdavidbrown@live.com`, then the 124 commits after Feature Drop 2. The
two squashed Feature Drop commits are replaced by the 46 commits that produced them, so the per-commit
detail is in the main line. No file content, no commit message and no author date changed. The tree at
the landing point equals the tree at the pre-rewrite `development` tip, kept as the tag
`pre-rewrite-development`. The rewrite is local: the pushed branches still hold the old history until
the force-push, and `origin/main` loses the two PR merge commits (`708f546`, `3ae014f`) when it is
pushed. `licensing` holds its 4 commits on top of the rewritten line. The open pieces are in
`to-do.md`, and the criteria and the measurement are in `acceptance.md`.

## Current position

F8.9 is complete (Epic 8, Phase 8C, the entry point), and it is the piece that decides the run order:
`src/api_to_terraform.py` reads the membership responses first, in the order
`api_requests.membership_lists()` names them, then the entries `api_requests.scope_index()` names in index order,
and it is the only place that states that order, because `api_requests.py` states no read order and
`provenance.py` rule 6 states no read rule for a path 2 run. One response is read once, so a container two lists
name (`template-stack`) enters the order at the first place a list names it. The entry point joins the
per-response tables in run order through the one join rule (`panorama_to_terraform.join_value`), and
`generate_run` takes the run view as an argument, so the join is the entry point's decision and path 1 builds the
same view for its one source. The entry point adds no argument of its own beyond the shared set, accepts no
argument that names one source, reads the environment name through `source_fetch.API_KEY_ENV`, prints only through
the owners' console lines, writes no file outside `write_path.py`, and calls `generate_run`, so it states no parse
order and no block builder. It passes the index it built to the gate, so the join findings print through the gate
and the exit code is the gate's decision. The generated `README.md` names the entry point that wrote the codebase,
and the name is an argument, so the label builder states no entry point of its own. The rule is stated in
`docs/API_CONVERSION_PATH.md` §6 with its pins named, and `README.md`, `docs/README.md` and
`docs/ARCHITECTURE.md` §1 name them.

The pins for this piece, in `tests/test_api_path.py` group 8:
`test_the_run_order_is_the_membership_lists_then_the_index_entries`,
`test_the_entry_point_joins_the_tables_across_the_responses_it_read`,
`test_the_run_sequence_is_stated_once_and_both_entry_points_call_it`,
`test_the_run_view_answers_the_entry_protocol_through_the_ledger_that_holds_the_entry`,
`test_the_run_view_states_no_row_shape_and_no_field_name_of_its_own`,
`test_the_entry_point_accepts_the_arguments_of_one_run_and_refuses_the_ones_that_name_one_source`,
`test_the_entry_point_passes_the_index_it_built_to_the_gate_and_keeps_the_gate_code`,
`test_the_entry_point_states_no_rule_an_owner_states`, and
`test_the_report_names_each_response_the_run_read_in_run_order`; plus
`tests/test_variables.py::test_the_entry_point_names_no_environment_name_of_its_own` and
`tests/test_site_data.py::test_the_readme_names_the_entry_point_that_wrote_the_codebase`. The three pins that read
the run sequence read `generate_run` rather than `main()`, because the sequence moved to the run function. No pin
calls a network: every path 2 pin runs the pipeline in process with the injected producer.

Measured run order for the committed set: `device-group`, `templates`, then `device-group/entry/Office-FW` and
`templates/entry/HQ-Networks`. The record file the run wrote names the same order, and the report names those four
sources in the same order. `panorama_to_terraform.failed` states the unexpected-error shape once, so both entry
points call it and neither prints a console line of its own.

F8.8 is complete (Epic 8, Phase 8C, the gate), and it is the gate piece for the join: the request-set rule
`sanity_checks.check_request_set` reads the join's rows through `api_requests.unit_findings`, the unit through
`unit_manifest.directory_name` and `naming.sanitize`, and the index through `api_requests`, so the rule states no
join rule, no membership rule, no unit rule, no naming rule, no cache rule and no reader of its own. The severity,
the report section, the console line, the order and the exit code are the gate's decision. `CHECK_ORDER` puts
`request_set` after `round_trip` and before `control_chars`, because the two rules that read two sets sit together
after every rule that reads one set, and the reason for that position is the join's own document. A join finding is
a fact about the source, so it is WARN and the exit code follows the rules that read the files; the join prints no
console line of its own, and the gate prints every finding it reads through the shape §3.2 states. `run_checks`
takes the index as an argument, so a call that is missing the index or the ledger reports NOT RUN, and `main()`
still passes no index, because the path 2 entry point (F8.9) is what will pass the index it builds. The rule is
stated in `docs/API_CONVERSION_PATH.md` §3 with its pins named, and `README.md` and `docs/README.md` name them.

The pins for this piece, in `tests/test_sanity_gate.py`: `test_the_gate_checks_the_join_through_the_owners`,
`test_a_fact_that_the_join_and_the_ledger_do_not_agree_on_prints_in_the_report`,
`test_the_run_wide_findings_print_through_the_join`, `test_the_join_findings_sort_by_the_data_rule`,
`test_the_join_prints_no_console_line_and_stays_a_warn`,
`test_the_rule_reports_not_run_when_the_gate_has_no_index`,
`test_two_runs_read_the_same_files_and_report_the_same_findings`, and
`test_a_path_2_run_and_a_path_1_run_report_the_same_findings`; and in `tests/test_round_trip.py`,
`test_the_cross_check_reads_the_join_ledger_on_a_path_2_run`, where the cross-check compares the block set with
the join's own rows through the same ledger and names the same unit. Two pins were migrated, not dropped: the
order pin `tests/test_data_file_gate.py::test_check_order_puts_the_data_rule_after_the_block_rules` now reads the
tuple with `request_set` after `round_trip`, and
`tests/test_sanity_gate.py::test_gate_runs_and_writes_the_report` reads `request_set` as NOT RUN on a path 1 run.
Every join pin runs the pipeline in process with an injected producer, because a fact from a run must be read from
the run's ledger; the run and the producer are in `tests/conftest.py`, because both files read the same run.

Measured against the committed whole-config export, the only committed response: 7 join rows, 3 on the unit side
and 4 on the entry side, so every pair is a fact that does not agree. The cross-check reports nothing on that run,
because the join's rows and the block set agree, so the pin plants one `panos_address` block for a unit the join
names and both rules name the same unit. The gate order puts the run-wide findings first and the unit findings
second, which is not the order the join states its rows in.

F8.7 is complete (Epic 8, Phase 8B, the run over many sources), and with it Phase 8B: the unit join reads the
run's unit set through `unit_manifest.units`, so path 2 states no second unit rule and counts no unit a second
way. The fact path 2 adds is the scope the run read for a unit, so `api_requests.join_units` answers, for each
unit, the index entry whose request produced the response name that unit's rows carry. `api_requests.unit_findings`
reports the two directions as data rows: a unit the join answers no entry for, because the response its rows name
is one the index made no request for, and an index entry the run read no rows for, so no unit answers it. The join
names no field of its own: the fact order comes from `unit_manifest` and the field name for the row's source comes
from `ownership.SOURCE_FIELD`, which `FIELD_ORDER`, `row_key` and `scan_row` also read, so the name is stated once,
and the response name is read through the one name rule in `source_fetch.py` (`cache_name`). The join reads the row
set through one ledger, because the join is per response (F8.5), so for a run that read one response the row set is
that response's rows. The join reports data rows only: no console line, no writer, no report section, and no exit
code, which the gate decides. The rule is stated in `docs/API_CONVERSION_PATH.md` §3 with its pins named, and
`README.md` and `docs/README.md` name them.

The pins for this piece: `tests/test_api_path.py` (the unit join group) gained
`test_the_unit_join_answers_the_scope_the_run_read_for_a_unit`,
`test_a_unit_the_index_made_no_request_for_is_a_finding`,
`test_an_index_entry_the_run_read_no_rows_for_is_a_finding` and
`test_the_join_reports_the_findings_as_data_through_the_owners_names`;
`tests/test_unit_manifest.py::test_the_join_reads_the_unit_set_through_this_rule` keeps the one unit rule, and
`tests/test_ownership.py::test_a_path_2_row_names_the_response_name_on_the_source_field` keeps the field name. The
import-list pin `tests/test_api_requests.py::test_the_module_reads_the_layout_rules_through_their_owners` gained
`ownership` and `unit_manifest`, because the join now reads those two rules through their owners. The string
constant pin and `tests/test_reference_edges.py` are unchanged.

Findings F8.7 recorded in `backlog.md`: the join reads the row set through one ledger, so which row set a run that
read more than one response joins is the run order's decision (F8.9); the join states no rule that a source the
index made no request for is definitions, so the predefined half stays with the F8.1 finding; and no rule decides
yet how a finding of this kind prints or whether it changes the exit code, which is the gate's work (F8.8).

F8.6 is complete (Epic 8, Phase 8B, the run over many sources): the record file holds one record per request the
path 2 run read, and the eight fields and their fixed order are unchanged. For each request the run read, `scope`
names the path that request declared, which is the fact the door records, and `request` names its key-free
identity, which is the shape the cache entry is hashed from, so `cache_entry` names the entry that identity names.
The record file holds the records in the order the run read them; `provenance.py` rule 6 states that order for the
sources it owns and states no read rule for a path 2 run, because the order a path 2 run reads is the run order's
decision (F8.9). The record directory is the output directory, so the prune action reads the record file the same
run wrote, and a run that read N requests protects the N entries its own record names. No new field is needed, so
`parse_records` reads a path 2 record file back as itself. The rule is stated in `docs/API_CONVERSION_PATH.md` §2.5
with its pins named, in `tests/test_provenance.py` and
`tests/test_write_path.py::test_the_record_directory_is_the_output_directory_for_the_prune`, and `README.md` and
`docs/README.md` name them. This piece changed no functional code: `provenance.record_for` already took the
request as an argument, so the pins build records through the fetch layer with an injected producer and write the
record file through `write_path.root_path` and `write_path.write_file`, because the path 2 entry point does not
exist yet.

F8.5 is complete (Epic 8, Phase 8B, the run over many sources): one response is one source with its own line
map, the parent walk and the entry ledger are keyed on the one tree that was parsed, and each parse method runs
over the response that holds its container. The rule is stated in `docs/API_CONVERSION_PATH.md` §2.4 with its
pins named, in `tests/test_api_path.py`, and `README.md` names that test module. The join is
`api_requests.response_for_section`, which answers the index entry whose response holds the container a section
names, in two parts read through their owners: the place the section names first, through `list_container`, and
the entry inside that place that the run read, built through `scope_path` and validated through
`is_scope_path`. `api_requests.entry_for_path` is the index lookup the join reads. `name` is data the run
states, because a section names a container and never the entry it sits inside. The join keeps no parser and
states no merge rule, so the run order calls the parse method, and the module's import list is unchanged.
The join refuses a section whose first segment names no place the one definition validates, and a section
inside a place the index has no entry for.

The two things this piece fixed or decided:

- `container_coverage.section_path` stated the place twice for a per-scope place read
  (`device-group/device-group/entry/address`). The chain now states the place once, so path 2 and path 1 name
  the same container path for the same content and the two reports disagree only on the source they name. The
  guard reads a per-scope source, so path 1 is unchanged, and the F5.4 entry-read pin holds.
- The predefined read: no container table row names a built-in container, so the run runs no parse method over
  a predefined response and the entry report names no row for a built-in entry, which the ledger counts through
  `predefined_total`. A predefined place read keeps the `predefined` element in the tree, so `is_predefined`
  reaches it and the scan names no finding; a predefined entry read puts the entry at the place level, so the
  scan reports the place. The join answers no response for a built-in place, because no membership row reads
  `predefined`. Both findings stay in `backlog.md`; this piece added no rule.

F8.4 is complete, and with it Phase 8A (Epic 8, the read boundary): the offline harness is one committed
response per accepted request shape in `tests/responses/`, each named by the key-free request identity that
produced it, read through the injected producer, and read as data by the record. The rule is stated in
`docs/API_CONVERSION_PATH.md` §5 with the pins named, and the decision about where the set lives is in
`docs/ARCHITECTURE.md` §1.1. `docs/README.md` names the owner of that decision, and `README.md` names the
test module `tests/test_api_requests.py`, which its index did not name before this piece.

The decisions F8.4 took: a committed response is not a Panorama export, so it is not corpus material and lives
in its own set beside `fixtures/` and `golden/`; `tests/conftest.py` is the one place the path to each set is
built, so a harness pin reads the response set through it and states no path of its own. Each file name is the
identity hash the record reads as `cache_entry`, and each file states the same identity in its prolog comment, so
a reader can see which request produced it and no name can carry a credential. A committed response is read
through the fetch layer and never through the file producer, because the wrapper decision belongs to the request
that produced it and the file producer has no request to read a shape against. The three files are the
whole-config export, the per-scope read of `device-group`, and the device fact for `show system info`. The
per-scope file is the membership read the scope index is built from, so the index and the join read the same
committed bytes. The device fact file shows the shape one command gives and names no fact, so
`docs/API_CONVERSION_PATH.md` §4 stays blocked on a live target. The response set changes no count the corpus
pins state, so the printed fixture set (68 accepted, 67 read, 3 skipped) is unchanged.

Phase 8A landed four rules, and each is stated in `docs/API_CONVERSION_PATH.md` §2.1, §2.2 and §2.3 with its
pins: the three accepted request shapes and the op wrapper rule; the scope index read from the four membership
lists in sorted order, one entry per scope; and the response-to-request join, checked against the request that
made the response through the one element-name rule (`source_fetch.names_element`). The join keeps no parser and
calls no producer, so the origin and the line map stay the ones the door recorded.

Next: piece F8.10, the agreement pin between the two paths for a fixture with no live-only fact (`to-do.md`,
Phase 8C).

Findings F8.6 recorded in `backlog.md`: a device fact request declares no path, so its record states the door's
default for `scope`, and the scope index makes no device fact request, so no rule decides which scope such a
record should name; that finding stays open. The other F8.6 finding, that the order a path 2 run reads is not a
record rule, is closed: F8.9 stated the order in the entry point, and its pins read it back from the record the
same run wrote.

Findings F8.2 recorded in `backlog.md`: the four lists name three of the five scope facts, so a
vsys scope cannot be read from membership; `container_coverage.ContainerRow` has no field for the table
its method returns, so the join lives as data in `api_requests.LIST_JOIN`; and the join of the four tables
across the responses a run read belongs to the run order, because the module states no merge rule and F8.5
decided that no tree is built across responses. F8.9 closed that finding for the tables: the entry point applies
the one join rule in run order. The row half stays open, because the join still cannot know which response the
run read. F8.3 recorded one finding there: `names_element` names no
element for a device fact request, so the join has no fact to read a command's element name against, and it
sits with the F8.1 finding about a predefined read, because both need a fact a request cannot state; the
committed response for the device fact shape shows the shape and names no fact, so the finding stays open. The
findings the F8.1 decision recorded stay there too, and F8.5 recorded what it measured against them: for a
predefined place read the parent walk reaches the `predefined` element and the scan names no finding, for an
entry read inside the place the entry sits at the place level so the scan reports the place, and the join
answers no response for a built-in place because no membership row reads `predefined`. F8.5 added no rule that
a predefined source is definitions.

Test count: `python3 -m pytest` reads 1650 pins (1638 before F8.9), with no skips, and `ruff check .` is clean.

The pieces that stay blocked on a fact the tool cannot read offline are in `backlog.md`: the path 2 live
facts in `docs/API_CONVERSION_PATH.md` §4, the four `*_policy_rules` types, a config entry inside a
stack, the EDL `certificate_profile` field, the profile-name report column, and the two `.github/`
template files outside the document indexes. `ruff format` as a gate stays the next actionable slice
outside Epic 8.

The CI gate reads the Python floor as 3.10, and the matrix legs are 3.10, 3.11, 3.12 and 3.13. The 3.9
leg is dropped, not moved to an older runner image, because two facts make it unusable:
`actions/setup-python` has no hosted build for 3.9 on Ubuntu 26.04, the image `ubuntu-latest` names
from November 2026, and `requirements.txt` pins `pytest==9.1.1`, which requires 3.10. Each leg is a
minor version, never an exact patch, because the build manifest for 26.04 holds only the newest
patches for the older minors. `pyproject.toml` states the floor, and `README.md` and
`docs/USAGE_GUIDE.md` state the same value. `target-version` stays `py39`: it states the syntax level
the lint gate enforces, not the floor, and the codebase still writes pre-3.10 typing and `zip`
without `strict` (101 findings at `py310`), which `backlog.md` records as its own task. No pin reads
the workflow file.



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
- One place answers a destination: `entry_coverage.EntryLedger.destination`, in the order the per-entry fact on
  the recorded object, the destination `mark` recorded, the container table row. `mark` states no destination of
  its own, so a call site that states `destination='report'` for a report-only entry restates a fact the entry
  already holds. The fact is read through `RecordingDict.value()`, so the decision records no property use and
  the order of `mark` and the field cannot change the answer; `mark_skipped` records no object, so a skipped
  entry answers through the mark. The cross-check counts only `emitted` rows, so an entry the run reports enters
  no count.
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
- Path 2 (Epic 8) adds `api_requests.py` and `api_to_terraform.py`, and both are read by the pins that
  scan the `src/` set: the writer scan, the environment-name scan, the console-line scan, and the
  second-naming-rule scan. So path 2 states no second rule of any kind, and each new path 2 rule names
  the module that holds it and the test that pins it. Its rules are in `docs/API_CONVERSION_PATH.md`.
