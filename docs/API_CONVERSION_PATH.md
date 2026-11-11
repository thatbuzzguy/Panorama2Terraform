# The API-only conversion path (Epic 8)

The design record for the second conversion path. It states what that path reads, what it may
decide, and what it must not state twice. Each rule names the module and the test that holds it.
The parts that are enforced (§2.1, §2.2, §2.3, §2.4, the response set in §5, and the run order in §6) are
stated in the present tense with their pins; the rest names the module and the test that will hold it.

Path 1 reads one declared source: a file, or the whole-config API export
(`docs/ARCHITECTURE.md` §3). Path 2 reads only responses, and it reads one response per scope
instead of one response for the whole config. It is parallel: it shares the tables, the naming
rule, the write path, and the gate with path 1, and it shares no input producer.

## 1. The two paths

| Part | Path 1 (export) | Path 2 (api) |
|---|---|---|
| Input | one declared source: a file, or one whole-config response | the request set: one response per scope |
| Scope set | the scopes the source holds | the scopes the membership responses name |
| Report position | the source line | the line inside the response the request made |
| Parse methods | the same methods | the same methods, run once per response |
| Tables | `resource_mapping.py`, `container_coverage.py` | the same tables |
| Naming rule | `naming.py` | the same rule |
| Write path | `write_path.py` | the same single writer |
| Gate | `sanity_checks.py` | the same rules, plus the response join |

Rule 1: path 2 states no second version of any part of that table. The pins that read the `src/`
set read path 2's modules with the other modules, so a second naming rule, a second writer, or a
second console line in path 2 fails CI. The pins are `tests/test_write_path.py`,
`tests/test_variables.py`, `tests/test_container_coverage.py`, and
`tests/test_site_data.py::test_the_module_defines_no_second_naming_rule`.

Rule 2: path 2 changes no path 1 rule. A table row that path 2 needs must be a row both paths
read, so the coverage matrix, the container table, and the entry ledger stay one set.

## 2. The request set

**2.1 The accepted request shapes.** Path 2 accepts three shapes, and one response shape per
request shape. `source_fetch.py` states them as `SHAPE_PARAMS`, and the request states its shape
through what it declares: a command is the device fact shape, a path is the per-scope shape, and
nothing else is the whole-config export.

| Shape | Request | Response element the run reads |
|---|---|---|
| whole-config export | `type=export&category=configuration` | the `config` element under `result` |
| per-scope read | `type=config&action=get&path=<scope path>` | the element the path names |
| device fact | `type=op&cmd=<command>` | the one element under `result` the command names |

For the device fact shape, `result` holds exactly one element and `result` becomes the root, read
as the place the command names, the same way the per-scope rule reads the place the path names. The
response is a device fact, not a config, so the source states no scope and the container table names
no row for a fact element. A response that does not match its own request is refused, not guessed,
and the response check runs before the cache entry is written. The command is part of the request
identity, so each command gets its own cache entry, and its value reaches the request URL encoded.
Pinned by `tests/test_source_fetch.py` (the op-shape group):
`test_the_request_states_which_of_the_three_shapes_it_is`,
`test_an_op_response_holds_the_one_element_the_command_names`,
`test_an_op_response_that_breaks_the_op_shape_is_refused`,
`test_the_op_shape_checks_the_shape_and_the_join_checks_the_element_name`,
`test_the_response_check_runs_for_the_op_shape`,
`test_the_command_is_part_of_the_request_identity`, and
`test_an_op_response_is_not_a_config_source`.

`container_coverage.SCOPE_PATH_ROOTS` is the one definition that validates a scope path, so the
`predefined` decision is stated inside that set and nowhere else: `predefined` is a place a scope
path may read, so `/<predefined>` and `/<predefined>/entry/<name>` are scope paths. It is read as a
place, not as a scope, so `SCOPE_CONTAINERS` keeps the five scope facts and `is_scope_entry` answers
False for a built-in entry. The path shape is unchanged, so a path that names a container inside
`predefined` stays outside the shape rule, and the scan rule for a built-in container is unchanged.
Pinned by `tests/test_container_coverage.py::test_a_predefined_path_is_read_by_the_one_scope_path_definition`,
and by `test_predefined_entries_are_not_findings` unchanged.

**2.2 The scope set is read, not guessed.** Path 2 builds its scope set from the membership
responses it read, through the four membership lists `parse_associations` reads
(`docs/ARCHITECTURE.md` §3, rule 3). Two levels, no more: one request per scope container the run
read, then one request per scope entry those containers name. The set is read in sorted order, one
entry per scope, so a name two lists read gives one entry. Each list joins to the table
`parse_associations` returns for it, and to the scope container that defines the entries its names
belong to, so a name counts only when the run read the response for that container: the fourth list
names the templates a stack applies, which are entries inside the `templates` container, so its names
join to `templates` and not to the stack. A device names no entry, because `parse_associations` keys
its tables on the device that owns a list. So path 2 makes no request for a scope the run did not
read, and it guesses no scope. `src/api_requests.py` states this rule, and the pins are
`tests/test_api_requests.py::test_the_four_membership_lists_are_the_container_table_rows`,
`test_the_scope_set_comes_from_the_membership_responses_the_run_read`,
`test_no_request_is_made_for_a_scope_the_run_did_not_read`,
`test_a_container_that_lists_no_name_gains_no_entry`,
`test_the_index_makes_one_request_per_scope_container_then_one_per_entry`,
`test_a_device_key_names_no_entry_in_the_index`, and
`test_the_index_is_read_in_sorted_order_and_names_one_entry_per_scope`. The module reads no
membership itself: it takes the tables as data, so no module states a second membership reader, and
it builds a path only through `xml_input.ENTRY_SEGMENT` and `container_coverage.is_scope_path`, so no
second path rule exists. The response-to-request join (§2.3) reads the two parts this rule names: the
entry name, and the request that made the response.

**2.3 One response per request, checked against the request that made it.** `api_requests.join_response`
reads one response against the index entry whose request made it, and answers the entry names inside
it in sorted order, which is what the run (§2.4) keys its parse on. A response is accepted only when
the element it holds is the element its own request names, and the entry name inside it agrees with the
scope index, so the join is checked rather than assumed. The first half is read through `source_fetch.py`:
the join runs the one wrapper decision, which names the element through the one rule in that module
(`names_element`), so the join states no shape rule, no wrapper rule, no command-to-element table, and no
second response success check. The second half is what the join owns: for a request that names an entry,
the name inside equals the index name; for a request that names a place, the entry names inside hold the
names the index read for that container, so a name the index read must appear inside. The check is
one-way, so an entry inside a response that lists no name compares no name, which is the §2.2 rule that
such an entry gains no entry. The join reads no membership and builds no second tree, so the origin and
the line map a report needs stay the door's.

The join reads only a response the index made a request for, because the index makes only per-scope
requests: a whole-config response holds no scope entry, and a device fact names no scope, so a command's
element name is a fact the tool cannot read offline (`backlog.md`).

Pinned by `tests/test_source_fetch.py` (the join group):
`test_the_join_reads_the_element_name_rule_through_the_fetch_layer`, and
`test_the_element_name_rule_names_no_element_for_a_device_fact`. Pinned by `tests/test_api_requests.py`
(the join group): `test_the_join_accepts_only_the_response_for_the_request_that_made_it`,
`test_the_entry_name_inside_a_response_agrees_with_the_index`,
`test_the_join_refuses_a_response_whose_element_is_not_the_element_its_request_names`,
`test_the_join_refuses_a_response_the_index_made_no_request_for`,
`test_an_entry_that_lists_no_name_names_no_entry_for_the_join`,
`test_an_entry_inside_a_response_with_no_name_is_refused`,
`test_the_join_returns_the_entry_names_inside_the_response_in_sorted_order`,
`test_the_join_reads_the_same_response_the_door_parsed`, and
`test_the_join_states_no_second_shape_rule_or_wrapper_rule`.

**2.4 The request set is not one tree.** Path 2 assembles no tree from many responses, because the
line map, the entry ledger, and the parent walk are keyed on the source that was parsed. One response
is one source: each response read through the door is its own `ParsedSource` with its own line map,
and each parse method runs over the response that holds its container, so a report position can only
name a line inside the response that holds the entry. `api_requests.response_for_section` answers the
index entry whose response holds the container a section names, in two parts read through their owners:
the place the section names first, which `list_container` states, and the entry inside that place that
the run read, built through `scope_path` and validated through `is_scope_path`, so the join states no
second path rule. `name` is data the run states, because a section names a container and never the entry
it sits inside: for a place read the join answers the response for the place, and for an entry read it
answers the response for the entry the run read. A run that reads N scopes has N sources, so its report
names the response the entry came from, and the report names that source by its name only, which is the
key-free request identity. The join refuses a section whose first segment names no place the one
definition validates, and a section inside a place the index has no entry for, because the set is read
from the membership responses.

The join keeps no parser and states no merge rule, so the run order calls the parse method: the join
answers which response a section belongs to. `api_requests.py` takes the four tables as data, so a run
that read one response holds one table set, and the join across responses is the run order's decision (§6).

Two consequences the pins hold. The report names the place a section names once, inside
`container_coverage.section_path`, which reads `result` as the place the path names and keeps the `entry`
segment only when the path names an entry, so the same content read as a per-scope place response and as a
whole-config export names the same container path, and the two reports disagree only on the source they
name (§5). And no container table row names a built-in container, so the run runs no parse method over a
predefined response and the entry report names no row for a built-in entry: the ledger counts it through
`predefined_total`. A predefined place read keeps the `predefined` element in the tree, so
`is_predefined` reaches it and the scan names no finding; a predefined entry read puts the entry at the
place level, so the scan reports the place, which is the finding `backlog.md` keeps. The join answers no
response for a built-in place, because no membership row reads `predefined`. This changes no path 1 rule,
because the guard reads a per-scope source.

Pinned by `tests/test_api_path.py`: `test_each_response_keeps_its_own_line_map`,
`test_the_parent_walk_answers_within_one_response`, `test_the_join_answers_one_response_per_section`,
`test_a_section_that_names_no_scope_is_refused`,
`test_the_join_refuses_a_section_inside_an_entry_the_run_read_no_response_for`,
`test_the_join_names_the_response_the_parse_method_runs_over`,
`test_a_parse_method_marks_only_the_entries_in_its_own_response`,
`test_the_same_name_in_two_responses_gives_two_rows_naming_two_sources`,
`test_the_report_position_is_the_line_inside_the_response`,
`test_a_path_2_report_row_names_the_response_by_name_only`,
`test_the_same_content_agrees_with_path_1_except_for_the_source`,
`test_no_table_row_names_a_builtin_container`,
`test_the_join_answers_no_response_for_a_builtin_place`,
`test_a_predefined_entry_read_reports_the_place_as_a_finding`,
`test_the_committed_response_is_one_source_and_names_itself_in_the_report`, and
`test_no_test_in_this_file_calls_a_network_producer`. The pin
`tests/test_entry_coverage.py::test_every_row_names_the_source_that_holds_the_entry` holds unchanged, and
the pins that read `src/api_requests.py` (the import list, the names the module must not define, and the
string constants the join must not state) pass unchanged.

**2.5 The record holds one record per request the run read.** The eight fields and the fixed order
are unchanged (`docs/ARCHITECTURE.md` §3.3). For each request the run read, the `scope` field names the path
that request declared, which is the fact the door records, and the `request` field names the key-free identity
of that request, which is the shape the cache entry is hashed from; `cache_entry` names the entry that identity
names. The record file holds the records in the order the run read them, which `provenance.py` rule 6 states
for the sources it owns; for a path 2 run the read order is the entry point's decision (§6), so the record
module states no read rule for it, and the record file is the order's own statement. The record
directory is the output directory, so the prune action reads the record file the same run wrote, and a run that
read N requests protects the N entries its own record names. No new field is needed, so `parse_records` reads a
path 2 record file back as itself. A device fact request declares no path, so its record states the
door's default for `scope`, and the index makes no device fact request, so that case stays a finding in
`backlog.md`. Pinned by
`tests/test_provenance.py`: `test_the_record_file_holds_one_record_per_source_read` (the path 2 case),
`test_the_path_2_record_names_the_request_that_made_each_response`,
`test_a_path_2_record_file_reads_back_with_no_new_field`, and
`test_the_prune_protects_every_entry_a_path_2_run_read`; and by
`tests/test_write_path.py::test_the_record_directory_is_the_output_directory_for_the_prune`. Every response in
those pins is handed by an injected producer, and the `device-group` read is the committed response set (§5).

## 3. The join to the codebase model

- **The unit set.** `unit_manifest.units` is still the one unit rule, so path 2 states no second unit rule and
  counts no unit a second way: a unit exists when the ledger has a row in it, and the facts are in the order the
  one rule states. The fact path 2 adds is the scope the run read for a unit, so `api_requests.join_units` answers,
  for each unit, the index entry whose request produced the response name that unit's rows carry. The join reads the
  field name for the row's source through `ownership.SOURCE_FIELD`, so it names no field of its own and adds no
  field to the declared row shape, and it reads the name through the one name rule in `source_fetch.py`
  (`cache_name`), so it states no cache rule and no request identity rule. The join reads the row set through one
  ledger, because the join is per response (§2.4), so for a run that read one response the row set is that
  response's rows. The same content read as a place and as an entry answers the same unit twice, once for each
  response, which is the fact path 1 cannot state.

  `api_requests.unit_findings` reports the two directions as data rows: a unit the join answers no entry for,
  because the response its rows name is one the index made no request for; and an index entry the run read no rows
  for, so no unit answers it. Each row is the pair the join answers, and the side the join has no fact for is None.
  The join reports these as data rows only: no console line, no writer, no report section, and no exit code, which
  the gate decides. Pinned by `tests/test_api_path.py` (the unit join group):
  `test_the_unit_join_answers_the_scope_the_run_read_for_a_unit`,
  `test_a_unit_the_index_made_no_request_for_is_a_finding`,
  `test_an_index_entry_the_run_read_no_rows_for_is_a_finding`, and
  `test_the_join_reports_the_findings_as_data_through_the_owners_names`. The pin
  `tests/test_unit_manifest.py::test_the_join_reads_the_unit_set_through_this_rule` keeps the one unit rule, and the
  pins that read `src/api_requests.py` (the import list and the string constants) hold it read through its owners.
- **The source field on the ownership row.** `ownership.SOURCE_FIELD` is the one statement of the field name, and
  `FIELD_ORDER`, `row_key`, `scan_row` and the unit join read it through that statement. For a response read the
  field names the response through the name rule in `source_fetch.py`, so the declared row shape is unchanged and
  carries a response name for path 2 and the file name for path 1. Pinned by
  `tests/test_ownership.py::test_a_path_2_row_names_the_response_name_on_the_source_field`, and the record shape
  pins in that file pass unchanged.
- **The order rule.** The three bases `CODEBASE_ASSEMBLY.md` §6 states do not read the input
  shape, so path 2 writes the same order. `tests/test_reference_edges.py` is unchanged.
- **The gate.** Every existing gate rule reads the files the run wrote, so path 2 output is read by
  the same rules. Path 2 adds one rule: the request set must agree with the scope the run read.
  `sanity_checks.check_request_set` reads the join's rows and the scope index through their owners, so it states
  no join rule, no membership rule, no unit rule, no naming rule, no cache rule, and no reader of its own, and
  `api_requests.py` keeps no check, no report section, and no render, so the gate is the only module that turns a
  join row into a finding. Its position in `sanity_checks.CHECK_ORDER` is after the cross-check and before the
  byte rules, because the two rules that read two sets sit together and a rule that reads two sets is not a byte
  rule. `run_checks` takes the index as an argument, so a call that is missing the index or the ledger reports the
  rule as NOT RUN, which is the shape a rule that reads a run's ledger already uses; a path 1 run reads no
  request, so `main()` passes no index and reports NOT RUN, and the path 2 entry point (F8.9) passes the index the
  run built. A join fact names no position in a file, so its `line` is 0, its file is the unit directory the data
  rule names through `naming.sanitize`, and the run-wide direction names no file and prints in the root shape the
  plan check already uses. The report section orders findings by the data rule's key, so the gate order and the
  order the join states its rows in differ. A join fact is a fact about the source, not a broken output file, so
  the rule states WARN and the exit code follows the rules that read the files. The join prints no console line of
  its own, because the join stays a data module, and the gate prints every finding it reads through the shape
  §3.2 states. Pinned by `tests/test_sanity_gate.py` (the join group):
  `test_the_gate_checks_the_join_through_the_owners`,
  `test_a_fact_that_the_join_and_the_ledger_do_not_agree_on_prints_in_the_report`,
  `test_the_run_wide_findings_print_through_the_join`, `test_the_join_findings_sort_by_the_data_rule`,
  `test_the_join_prints_no_console_line_and_stays_a_warn`,
  `test_the_rule_reports_not_run_when_the_gate_has_no_index`,
  `test_two_runs_read_the_same_files_and_report_the_same_findings`, and
  `test_a_path_2_run_and_a_path_1_run_report_the_same_findings`; and by
  `tests/test_round_trip.py::test_the_cross_check_reads_the_join_ledger_on_a_path_2_run`, where the cross-check
  compares the block set with the same ledger the join reads and names the same unit. Every join pin runs the
  pipeline in process with an injected producer, because a fact from a run must be read from the run's ledger.
- **The credential rule.** `CODEBASE_ASSEMBLY.md` §11 is the owner, and `source_fetch.py` is the
  only `src/` module that states the environment name. Path 2's entry point must not state it, so
  `tests/test_variables.py::test_the_generated_block_names_the_environment_the_fetch_layer_reads`
  holds it for path 2 too.

## 4. The facts only a live target states

These are the facts an export cannot carry. Path 1 cannot state them, and path 2 cannot read them
offline, so each one stays blocked until a committed response shows its shape, and until a live target
states the fact itself. Each fact names the request shape that gives it, and each is recorded in
`backlog.md` while it is blocked. The committed response for the device fact shape shows the shape
(§5), so that row needs the live fact only.

| Fact | Request shape | What it unlocks | Blocked on |
|---|---|---|---|
| rulebase per rule | per-scope read under a `pre-rulebase` or `post-rulebase` path | the four `*_policy_rules` types, and the import block for a rule entry | the accepted value string, verified against a live target (F3.5) |
| rule position | the same request, read in document order | the import position for a rule entry | the rulebase value above |
| device serial | the device fact shape | `target`, and `ngfw_device` as a value the run can print | a committed response for the accepted op shape (§2.1) |
| per-device template variable override | the device fact shape | the per-serial value `panos_template_variable` cannot carry | a response that shows how a device states it |
| built-in name table | a `predefined` read | the read-through rule can skip a built-in name such as `any` | a committed response for a `predefined` path (§2.1 landed the definition decision) |

For the rulebase, path 2 has one advantage path 1 does not: the request path names the rulebase,
so the value is a request fact and not a guess. The rule is that the parse records the rulebase
only from the request that read the entry, and no parse method reads it off the element.

## 5. Offline proof

- Path 2 reads no network in a test. The producer is injected, as `tests/test_source_fetch.py` does, so Goal 1
  holds for path 2, and it holds for the committed set:
  `tests/test_source_fetch.py::test_a_committed_response_is_read_through_the_injected_producer`.
- The committed responses are one file per request shape, and each one names the request identity that produced
  it. They live in the set `docs/ARCHITECTURE.md` §1.1 names for them (`tests/responses/`), because a response
  is not a Panorama export and is not corpus material: the scan never runs over it, and the fixture assembler
  never merges it. Each file name is the key-free identity hash the record reads as `cache_entry`, and the file
  states the same identity in its prolog comment, so a reader can see which request produced it. A test reads a
  committed response through the injected producer, so `fetch()` reads it through the door against the request
  that produced it, writes the cache entry the record names, and answers the shape its own request states. The
  record names the same bytes. Pinned by `tests/test_api_requests.py` (the harness group):
  `test_one_committed_response_per_request_shape_names_the_request_identity_that_produced_it`,
  `test_a_committed_response_reads_through_the_injected_producer_and_the_record_names_the_same_bytes`,
  `test_the_committed_responses_are_not_corpus_material`,
  `test_the_join_reads_the_committed_per_scope_response_through_the_injected_producer`, and
  `test_the_committed_op_response_shows_one_shape_and_names_no_live_fact`.
- The committed per-scope response is the membership read the scope index (§2.2) is built from, so the index and
  the join (§2.3) read the same committed bytes. The committed device fact response shows the shape one command
  gives and names no fact, so it does not unblock §4: the fetch layer states no command-to-element table, so the
  one element-name rule names no element for a command, and the device serial stays blocked on a live target.
- A run that reads only committed responses writes byte-identical output between two runs, the same
  rule the corpus pins for path 1.
- For content that holds none of the facts in §4, path 2 writes the same `.tf` bytes as path 1 on
  the same fixture. The report files do not agree, because the report names the source. This is the
  pin that keeps the two paths honest to each other: `tests/test_api_path.py`.

## 6. The run order, and the join across responses

**The run order is the entry point's decision.** `src/api_to_terraform.py` is the only place that states it:
the run reads the membership responses first, in the order `api_requests.membership_lists()` names them, then
the entries `api_requests.scope_index()` names, in index order. One response is read once, so a container two
lists name (the two `template-stack` lists name one container) enters the order at the first place a list names
it, and a container the run already read as a membership response is not read again for its index entry.
`api_requests.py` states no read order and `provenance.py` rule 6 states no read rule for a path 2 run, so the
record file the run wrote is the order's own statement (§2.5). Pinned by
`tests/test_api_path.py::test_the_run_order_is_the_membership_lists_then_the_index_entries`, which reads the
order through the owners' names and compares it with the record file the same run wrote.

**The join across responses.** The four tables stay per response in `api_requests.py`, so a run that read N
responses needs one set before the index can read them. The join rule is stated once, in
`panorama_to_terraform.py` (`join_value`), and the entry point applies it in run order through `join_results`:
a list concatenates in run order; a dict merges by key in run order, and its nested values recurse; two numbers
for the same key add; a value that is neither of those is the later part's. One part answers the value
unchanged, so a run that read one source writes the same bytes as before. The join is the entry point's
decision, because `generate_run` takes the run view as an argument, and the view holds the parts in run order
and answers the entry protocol through the ledger that holds the entry. The view states no row shape and no
field name of its own. Pinned by `tests/test_api_path.py::test_the_entry_point_joins_the_tables_across_the_responses_it_read`
and `test_the_run_view_answers_the_entry_protocol_through_the_ledger_that_holds_the_entry`.

**What the entry point holds, and what it reads through an owner.** It states the run order, the arguments, and
the exit codes, and nothing else. The parse order and the emission order are `generate_run`'s, so both entry
points call it and neither names a block builder; the entry point reads the parser through one method,
`parse_associations`, because the index needs the tables the run read. The arguments and their checks are
`panorama_to_terraform.shared_arguments` and `shared_checks`, so the entry point adds no argument of its own and
accepts no argument that names one source. It prints only through the owners' console lines, it writes no file
outside `write_path.py`, and it states no environment name of its own. The gate decides the exit code, and the
gate gets the index the entry point built, so a join finding prints through the gate rather than through a block
the entry point states. Pinned by `tests/test_api_path.py::test_the_run_sequence_is_stated_once_and_both_entry_points_call_it`,
`test_the_entry_point_accepts_the_arguments_of_one_run_and_refuses_the_ones_that_name_one_source`,
`test_the_entry_point_passes_the_index_it_built_to_the_gate_and_keeps_the_gate_code`, and
`test_the_entry_point_states_no_rule_an_owner_states`; and by
`tests/test_variables.py::test_the_entry_point_names_no_environment_name_of_its_own`.

The report names one source per response the run read, in run order, through the ledger that holds it, and the
generated `README.md` names the entry point that wrote the codebase, where the name is an argument rather than a
word the label builder holds. Pinned by
`tests/test_api_path.py::test_the_report_names_each_response_the_run_read_in_run_order` and
`tests/test_site_data.py::test_the_readme_names_the_entry_point_that_wrote_the_codebase`.

## 7. What path 2 does not close

Path 2 is an input mechanism. It does not close a parse gap, so these stay where they are:

- The security profile bodies, the schedules, the regions, and the application filter properties:
  an export already holds these containers, so path 2 adds nothing. They stay in `backlog.md`.
- A value the parse cannot carry. A live device does not return a private key or a password hash,
  so the reference-only rule (`docs/ARCHITECTURE.md` §4.6, `VALUE_VARIABLES`) is unchanged.
- The state write path, the orchestrator, the Day 1 device bootstrap, and the plan: out of scope
  (`backlog.md`, Out of Scope).
- The PAN-OS version matrix: a device fact is version dependent, and version matrix testing is out
  of scope.

## 8. Modules path 2 adds

`src/` is one flat namespace, so both modules import their siblings by plain name, and each is
named in the `docs/ARCHITECTURE.md` §1 table.

| Module | Role | Rule it keeps |
|---|---|---|
| `api_requests.py` | the scope index (§2.2), and the response-to-request join (§2.3) | the set is read from the membership responses, in sorted order, one entry per scope, and every response is checked against the request that made it |
| `api_to_terraform.py` | the path 2 entry point: the run order (§6), the arguments, and the exit codes | the run order is stated here and nowhere else, and one response is read once; the arguments and their checks are read through `panorama_to_terraform.py`, so the entry point adds no argument of its own and accepts none that names one source; it calls `generate_run`, so it states no parse order and no block builder; it prints only through the owners' console lines and writes no file outside `write_path.py` |

Both modules write no file except through `write_path.py`, and neither states the environment name.

## 9. Piece order

1. The accepted request shapes, including the op shape, and the `SCOPE_PATH_ROOTS` decision for
   `predefined` (§2.1). Nothing else in path 2 can be written before this decision.
2. The scope index, read from the membership responses (§2.2), and the response-to-index join
   (§2.3).
3. The offline harness: one committed response per request shape, the injected producer, and the
   rule that no test calls a producer (§5).
4. The run over many sources: the parse methods per response, the report position, and the record
   per request (§2.4, §2.5).
5. The unit join, and the ownership source field (§3).
6. The gate: the request-set rule, and the path 2 pins for the rules that already read the files
   (§3).
7. The entry point: the arguments, the run order, the exit codes, and the generated `README.md`
   label that names which path wrote the codebase.
8. The live facts in §4, in the order the table names them, each gated on its own condition.
