# Acceptance criteria — F8.3, the response-to-request join (Epic 8, Phase 8A)

Scope: one new function in `src/api_requests.py` (the join), the one element-name rule in
`src/source_fetch.py` read through it, the join pins in `tests/test_source_fetch.py` (the shape) and
`tests/test_api_requests.py` (the join with the index), and `docs/API_CONVERSION_PATH.md` §2.3 stated in
the present tense. No response is committed (the committed harness is F8.4), no parse method runs over a
response (F8.5), no gate rule is added (F8.8), no entry point is added (F8.9), and path 1 is unchanged.

## 1. The join is one function, and it reads the shape through its owner

1.1 `api_requests.join_response(source, entry, index)` takes the response the door parsed and the index
    entry whose request made it, and returns the entry names inside the response in sorted order.

1.2 A response is accepted only when the element it holds is the element its own request names. That
    check is read through `source_fetch.py`: the join runs the one wrapper decision
    (`source_fetch.unwrap_config_root`), which names the element through the one rule in that module
    (`source_fetch.names_element`), so the join states no shape rule, no wrapper rule, no command-to-element
    table, no second element-name rule, and no second response success check.

1.3 A response the fetch layer refuses is refused through the same rule and the same error type, so the
    join cannot accept a shape its own request does not state: a whole-config response handed to a
    per-scope entry, and a per-scope response whose element is another container, are refused.

1.4 The join reads only a response the index made a request for. The index makes only per-scope requests,
    so the join refuses a request that names no scope path: a whole-config response holds no scope entry,
    and a device fact names no scope, so which element a command names is not a fact the join can read
    offline. That fact stays recorded in `backlog.md`.

1.5 The join is a reader, not a writer: it parses nothing, builds no path, writes no file, states no
    naming rule, no console line, no environment name, and no membership reader, so the pins that scan the
    `src/` set read it with the other modules unchanged. It keeps the origin and the line map, so a report
    line still names the line the response carries (F8.5).

## 2. The entry name inside the response agrees with the scope index

2.1 For a request that names an entry, the response holds that entry, so the entry name inside it equals
    the name the index names for that entry.

2.2 For a request that names a place, the entry names inside the response are the names the index read for
    that container, so a response that holds no entry for a name the index read is refused.

2.3 The join is checked, not assumed: a container response that holds the names the index read for a
    different container is refused even when the shape rule passes, because the shape rule reads the path
    and the join reads the index.

2.4 An entry inside a response that lists no membership name gains no entry in the index
    (`api_requests.names_read`, F8.2), so the join compares no name for it and accepts the response. No
    association is better than a guessed one, and the join states no rule of its own for that case.

2.5 An entry inside a membership entry names no scope (`docs/ARCHITECTURE.md` §2.4), so the join reads only
    the entries at the level its own request names, and an entry with no name is refused.

## 3. The pins

3.1 `tests/test_source_fetch.py` (the join group, the shape side):
    `test_the_join_reads_the_element_name_rule_through_the_fetch_layer` — a per-scope response whose element
    is another container is refused by the fetch layer's words, `names_element` is the only element-name rule
    in the `src/` set, and the join's only module call is the wrapper decision, so `api_requests.py` states no
    shape rule and no wrapper rule of its own.
    `test_the_element_name_rule_names_no_element_for_a_device_fact` — the rule names no element for a request
    that declares a command and no path, so the join has no element name to read for a device fact, and no
    module states a command-to-element table.

3.2 `tests/test_api_requests.py` (the join group, the join with the index):
    `test_the_join_accepts_only_the_response_for_the_request_that_made_it` — every response read through the
    injected producer for its own index entry is accepted, and the names inside it agree with the index.
    `test_the_entry_name_inside_a_response_agrees_with_the_index` — the entry name inside an entry response
    equals the index name, and the names inside a container response hold the names the index read for that
    container; a response that holds the names the index read for another container is refused although the
    shape rule passes, because the shape rule reads the path and the join reads the index.
    `test_the_join_refuses_a_response_whose_element_is_not_the_element_its_request_names` — the same bytes
    handed to another entry's request are refused, and the refusal names the path the entry states.
    `test_the_join_refuses_a_response_the_index_made_no_request_for` — a device fact names no index entry, and
    a whole-config response holds no scope entry, so the join refuses both.
    `test_an_entry_that_lists_no_name_names_no_entry_for_the_join` — the F8.2 entry that lists no name is
    accepted by the join, because the index read no name for it, and the join states no rule of its own for
    that case.
    `test_the_join_returns_the_entry_names_inside_the_response_in_sorted_order` — the names the run (F8.5)
    keys its parse on, in the same order for another document order.
    `test_an_entry_inside_a_response_with_no_name_is_refused` — an entry inside a response that carries no
    name gives the join nothing to compare, so it is refused rather than guessed.
    `test_the_join_reads_the_same_response_the_door_parsed` — the join builds no second tree and calls no
    producer, so the origin and the line map are the ones the door recorded, and a cached response reads
    through the join the same way.
    `test_the_join_states_no_second_shape_rule_or_wrapper_rule` — the join reads the shape through
    `source_fetch.py`, states no command-to-element table, reads the entry rule through `xml_input.py`, and
    owns only the index agreement.

## 4. The checks

4.1 `ruff check .` is clean.

4.2 `python3 -m pytest` passes with no skip: the baseline 1586 pins, plus the pins above. No existing pin
    regresses, and no test calls the network: every response is handed by an injected producer.

4.3 The commit is one ASD-STE100 message. When the rule lands, `docs/API_CONVERSION_PATH.md` §2.3 states it
    in the present tense and names the pins, `docs/ARCHITECTURE.md` §1 names the join in the module row, the
    F8.1 sentence about a command's element name is made honest in §3, the completed piece leaves `to-do.md`,
    the findings the join touches are updated in `backlog.md`, and `agent-status.md` names the next piece
    (F8.4, the offline harness).
