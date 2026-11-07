# The API-only conversion path (Epic 8)

The design record for the second conversion path. It states what that path reads, what it may
decide, and what it must not state twice. Each rule names the module and the test that holds it.
The parts that are enforced (§2.1, §2.2, §2.3, and the response set in §5) are stated in the present
tense with their pins; the rest names the module and the test that will hold it.

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

**2.4 The request set is not one tree.** Path 2 never assembles one tree from many responses,
because the line map, the entry ledger, and the parent walk are keyed on the source that was
parsed. Each response is its own `ParsedSource` with its own line map, and each parse method runs
over the response that holds its container. The report row names the source that holds the entry,
which `tests/test_entry_coverage.py::test_every_row_names_the_source_that_holds_the_entry` already
pins. A run that reads N scopes has N sources, so its report names the response the entry came
from. `tests/test_api_path.py` pins that a merged tree is not built.

**2.5 The record holds one record per request the run read.** The eight fields and the fixed order
are unchanged (`docs/ARCHITECTURE.md` §3.3). The `scope` field names the path the request declared,
and the `request` field names the key-free identity of that request. The prune action reads the
record file the same run wrote, so a run that read N scopes protects N entries. No new field is
needed. `tests/test_provenance.py::test_the_record_file_holds_one_record_per_source_read` is the
pin that grows.

## 3. The join to the codebase model

- **The unit set.** `unit_manifest.units` is still the one unit rule, so path 2 states no second
  unit rule. Path 2 adds one fact the join can read: the scope the run read for a unit. A unit with
  no request, and a request that answers no unit, is a finding. `tests/test_api_path.py` pins both
  directions, and `tests/test_unit_manifest.py` keeps the join rule.
- **The source field on the ownership row.** `OWNERSHIP.json` already names the source for each
  entry, so path 2 writes the same row shape with a response name instead of a file name, and
  `tests/test_ownership.py` keeps it.
- **The order rule.** The three bases `CODEBASE_ASSEMBLY.md` §6 states do not read the input
  shape, so path 2 writes the same order. `tests/test_reference_edges.py` is unchanged.
- **The gate.** Every existing gate rule reads the files the run wrote, so path 2 output is read by
  the same rules. Path 2 adds one rule: the request set must agree with the scope the run read. Its
  position in `sanity_checks.CHECK_ORDER` is a decision inside that module, not a second order. The
  round-trip cross-check reads the run's ledger, so path 2 must feed the same ledger through the
  same `mark` rule. `tests/test_round_trip.py` and `tests/test_sanity_gate.py` gain the path 2
  pins.
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

## 6. What path 2 does not close

Path 2 is an input mechanism. It does not close a parse gap, so these stay where they are:

- The security profile bodies, the schedules, the regions, and the application filter properties:
  an export already holds these containers, so path 2 adds nothing. They stay in `backlog.md`.
- A value the parse cannot carry. A live device does not return a private key or a password hash,
  so the reference-only rule (`docs/ARCHITECTURE.md` §4.6, `VALUE_VARIABLES`) is unchanged.
- The state write path, the orchestrator, the Day 1 device bootstrap, and the plan: out of scope
  (`backlog.md`, Out of Scope).
- The PAN-OS version matrix: a device fact is version dependent, and version matrix testing is out
  of scope.

## 7. Modules path 2 adds

`src/` is one flat namespace, so both modules import their siblings by plain name, and each is
named in the `docs/ARCHITECTURE.md` §1 table when it lands.

| Module | Role | Rule it keeps |
|---|---|---|
| `api_requests.py` | the scope index (§2.2), and the response-to-request join (§2.3) | the set is read from the membership responses, in sorted order, one entry per scope, and every response is checked against the request that made it |
| `api_to_terraform.py` | the path 2 entry point | the run order, the arguments, the exit codes, and no rule restated. It reads `PanoramaParser`, `TerraformGenerator`, `unit_manifest`, `sanity_checks`, and `write_path` |

Both modules write no file except through `write_path.py`, and neither states the environment name.

## 8. Piece order

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
