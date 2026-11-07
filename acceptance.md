# Acceptance criteria — F8.5, the run over many sources (Epic 8, Phase 8B)

Scope: the rule that one response is one source, the section-to-response join in `src/api_requests.py`,
the pins in `tests/test_api_path.py`, and the decision about the predefined read. No new module, no entry
point (F8.9), no gate rule (F8.8), no unit join (F8.7), no record change (F8.6), and path 1 is unchanged.
The run order is the entry point, so this piece states the rule and the join; no module here calls a parse
method, and the pins run the parse per response.

## 1. One response is one source

1.1 Each response read through the door is its own `ParsedSource` with its own line map, keyed by the
elements of the tree that was parsed. An element of one response has no line in another response's map, so
a report position can only name a line inside the response that holds the entry.

1.2 The parent walk, the entry ledger, and the scope walk are keyed on one tree, so each response gets its
own. A parent map or a ledger built for one response holds no element of another.

1.3 The run builds no tree from many responses. `src/api_requests.py` keeps no parser and states no merge
rule, so the join answers one response per section, and no section needs a tree across responses.

## 2. Each parse method runs over the response that holds its container

2.1 `api_requests.response_for_section(section, index, name)` answers the index entry whose response holds
the container a section names, in two parts, both read through their owners: the place the section names
first, and the entry inside that place that the run read. The path is built through `xml_input.ENTRY_SEGMENT`
and validated through `container_coverage.is_scope_path`, so the join states no second path rule and no
second membership rule.

2.2 `name` is data the run states, because a section names a container and never the entry it sits inside.
For a place read the join answers the response for the place; for an entry read it answers the response for
the entry the run read.

2.3 A section whose first segment names no place the one definition validates is refused: the run reads such
a container inside the response for the scope that holds it, and the section names no scope. A section inside
a place the index has no entry for is refused, because the index reads its set from the membership responses
and no membership row reads that scope.

2.4 A parse method run over one response marks only the entries inside that response, so the rows it
produces name that response.

## 3. The report position and the source name for a path 2 run

3.1 A report row's `source` is the response name, which is the key-free request identity
(`ApiRequest.cache_name()`) and holds no path. The existing pin
`tests/test_entry_coverage.py::test_every_row_names_the_source_that_holds_the_entry` holds unchanged, and the
row's source is the same value the join answers.

3.2 The report position is the line inside the response the request made, read through that response's own
line map, in the shape `container_coverage.position_part` states. The printed entry line names the position
and the identity; the source stays row data and the report section header value.

3.3 A name that appears in two responses gives two rows, each naming the response that holds it with the line
inside it, and the two lines are read from two different maps.

3.4 The report names the place a section names once. For a place read the chain starts at the place, and the
element under `result` is the element the request names, so the same content read as a per-scope place
response and as a whole-config export names the same container path, and the two reports disagree only on the
source name (`docs/API_CONVERSION_PATH.md` §5).

## 4. The predefined read

4.1 No container table row names a built-in container, so the run runs no parse method over a predefined
response and the entry report names no row for a built-in entry. The ledger counts the built-in entry through
`predefined_total`, and `container_coverage.is_predefined` keeps it out of the report.

4.2 A predefined place read keeps the `predefined` element in the tree, so the built-in rule reaches it and the
scan names no finding. A predefined entry read puts the entry at the place level, so the scan reports the place
as a finding: the scan has no rule that a predefined source is definitions, and this piece adds none, so
`backlog.md` keeps the finding.

4.3 The join answers no response for a built-in place, because the index reads its set from the membership
responses and no membership row reads `predefined`. The fact the built-in name table needs stays blocked on a
live target (`docs/API_CONVERSION_PATH.md` §4).

## 5. No test calls a network

5.1 Every response in `tests/test_api_path.py` is handed by an injected producer through
`source_fetch.fetch`, as `tests/test_source_fetch.py` does, and the default producer stands in as one that
fails the test when called.

5.2 The committed response set (`tests/responses/`) is read through the injected producer, and the committed
per-scope response is one source whose report rows name it, so the run reads one response per scope.

## 6. The pins

6.1 `tests/test_api_path.py` (16 pins):

1. `test_each_response_keeps_its_own_line_map`
2. `test_the_parent_walk_answers_within_one_response`
3. `test_the_join_answers_one_response_per_section`
4. `test_a_section_that_names_no_scope_is_refused`
5. `test_the_join_refuses_a_section_inside_an_entry_the_run_read_no_response_for`
6. `test_the_join_names_the_response_the_parse_method_runs_over`
7. `test_a_parse_method_marks_only_the_entries_in_its_own_response`
8. `test_the_same_name_in_two_responses_gives_two_rows_naming_two_sources`
9. `test_the_report_position_is_the_line_inside_the_response`
10. `test_a_path_2_report_row_names_the_response_by_name_only`
11. `test_the_same_content_agrees_with_path_1_except_for_the_source`
12. `test_no_table_row_names_a_builtin_container` (AC-4.1, which covers the no-row-for-a-built-in-entry half)
13. `test_the_join_answers_no_response_for_a_builtin_place`
14. `test_a_predefined_entry_read_reports_the_place_as_a_finding`
15. `test_the_committed_response_is_one_source_and_names_itself_in_the_report`
16. `test_no_test_in_this_file_calls_a_network_producer`

6.2 The existing pins that read `src/api_requests.py` (the import list, the names the module must not define,
and the string constants the join must not state) pass unchanged, so the join states no rule its owners state.

## 7. The checks

7.1 `ruff check .` is clean.

7.2 `python3 -m pytest` passes with no skip: the baseline 1604 pins, plus the pins above. No existing pin
regresses, and `tests/test_entry_coverage.py::test_every_row_names_the_source_that_holds_the_entry` passes
unchanged.

7.3 The commit is one ASD-STE100 message. When the rule lands, `docs/API_CONVERSION_PATH.md` §2.4 states it in
the present tense with the pins named, `README.md` names `tests/test_api_path.py` in the testing list, the
completed piece leaves `to-do.md`, the predefined decision and the two findings stay honest in `backlog.md`, and
`agent-status.md` names the next piece (F8.6, one record per request).
