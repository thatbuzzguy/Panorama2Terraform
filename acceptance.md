# Acceptance criteria — F8.2, the scope index (Epic 8, Phase 8A)

Scope: `src/api_requests.py` (the module path 2 adds first), its pins in
`tests/test_api_requests.py`, and the `docs/ARCHITECTURE.md` §1 table row that names it. No
response is committed (the committed harness is F8.4), no response is checked against the request
that made it (the join is F8.3), no parse method runs over a response, no entry point is added, and
path 1 is unchanged.

## 1. The four membership lists

1.1 The four lists are the `parse_associations` rows in `container_coverage.CONTAINER_TABLE`, read
    through the table, so the module states no second list of membership containers.

1.2 The join between a list and the table `parse_associations` returns for it, and the scope
    container that defines the entries its names belong to, is stated once in the module and nowhere
    else. The fourth list names the templates a stack applies, which are entries inside the
    `templates` container, so its names join to that container and not to the stack.

1.3 The module reads no membership itself: it takes what `parse_associations` returned as data, so
    no module states a second reader of membership, and no module builds a path.

1.4 The four lists name three of the five scope facts, so `vsys` and `devices` name no entry: the
    index requests no scope no membership row reads, and the run reads such a scope as its declared
    scope (`tests/test_api_requests.py::test_the_four_membership_lists_are_the_container_table_rows`).

1.5 The module takes the four tables as data, so it states no merge rule and owns no reader; the join
    between a list, the table it returns, and the container that defines its names is stated once, as
    data, and the pin reads the tables the parse method returned.

## 2. The set is read, not guessed

2.1 Two levels, no more: one entry per scope container the run read, then one entry per scope entry
    those containers name. No entry is a third level.

2.2 The names in the set are the names the lists the run read hold. A name no membership list read
    is not in the set, so no scope is guessed.

2.3 No request is made for a scope the run did not read. A name read through a list whose entries
    belong to a container the run did not read enters no entry.

2.4 A device names no entry in the index. `parse_associations` keys its tables on the entry that owns
    a list, which is a device for three tables and the stack for the fourth, and a membership entry
    inside a list is a `bookkeeping` entry (`docs/ARCHITECTURE.md` §2.4), so a key is never a scope
    entry the module can request.

2.5 A container that lists no name gains no entry, the same way an export that lists no device gives
    empty tables: no association is better than a guessed one.

## 3. Order and identity

3.1 The set is read in sorted order, one entry per scope: the containers first, then the entries in
    path order, so the same names in a different document order give the same set.

3.2 A name two lists read gives one entry.

3.3 One entry names the level, the scope container that defines it, the entry name, the scope path,
    and the request that reads it. The entry name and the request are what the response-to-request
    join (F8.3) reads, so the join is a new function in this module and not a change to this rule.

## 4. The rules the module reads through their owners

4.1 Every path in the index is a path `container_coverage.is_scope_path` validates. The module builds
    a path through `xml_input.ENTRY_SEGMENT` and refuses one the one definition does not validate, so
    it states no second path rule.

4.2 Each entry's request is a per-scope request built by `source_fetch.ApiRequest`, so the module
    states no request shape, no cache rule, and no request identity rule of its own.

4.3 The module states no naming rule, no writer, no console line, and no environment name, so the
    pins that scan the `src/` set read it with the other modules: the writer scan, the environment-name
    scan, the console-line scan, and the second-naming-rule scan pass unchanged. It writes no file, so
    `write_path.py` stays the single writer.

4.4 `api_requests.py` is named in the `docs/ARCHITECTURE.md` §1 table.

4.5 No test calls the network. The pins run `fetch` through an injected producer, as
    `tests/test_source_fetch.py` does, and the module imports the standard library and its `src/`
    siblings only.

## 5. The pins (`tests/test_api_requests.py`)

5.1 `test_the_four_membership_lists_are_the_container_table_rows` — the lists are the rows, the join
    names the four lists and no other path, and the join names three of the five scope facts.

5.2 `test_the_scope_set_comes_from_the_membership_responses_the_run_read` — the index equals the names
    the four lists read for the responses the run read, read through the injected producer and the same
    parse rule, and the join names the tables `parse_associations` returns.

5.3 `test_no_request_is_made_for_a_scope_the_run_did_not_read` — a partial read, and a name whose
    entries belong to a container the run did not read.

5.4 `test_a_container_that_lists_no_name_gains_no_entry` — an entry with no membership name.

5.5 `test_a_device_key_names_no_entry_in_the_index` — a key is not a scope entry.

5.6 `test_the_index_makes_one_request_per_scope_container_then_one_per_entry` — two levels, no more.

5.7 `test_the_index_is_read_in_sorted_order_and_names_one_entry_per_scope` — the order, and a name two
    lists read.

5.8 `test_every_index_path_is_a_path_the_one_scope_path_definition_validates` — the module refuses a
    name that builds a path the definition does not validate.

5.9 `test_each_entry_names_the_request_the_fetch_layer_reads` — the per-scope shape, one cache entry
    per entry, and no identity rule stated in the module.

5.10 `test_the_module_reads_the_layout_rules_through_their_owners` — no second naming rule, no second
    writer, no second console line, no environment name, no membership reader, no merge rule.

5.11 `test_the_module_is_named_in_the_architecture_module_table` — the §1 row.

## 6. The checks

6.1 `ruff check .` is clean.

6.2 `python3 -m pytest` passes with no skip: the baseline 1575 pins, plus the pins in
    `tests/test_api_requests.py`. The pins that scan the `src/` set read the new module with the other
    modules and pass unchanged.

6.3 The commit is one ASD-STE100 message. When the rule lands, `docs/API_CONVERSION_PATH.md` §2.2
    states it in the present tense and names the pin, `docs/ARCHITECTURE.md` §1 names the module, and
    the completed piece leaves `to-do.md`.
