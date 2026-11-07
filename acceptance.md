# Acceptance criteria — F8.7, the unit join (Epic 8, Phase 8B)

Scope: the join between the run's unit set and the request set (`docs/API_CONVERSION_PATH.md` §3), stated in
`src/api_requests.py` as `join_units`, and the ownership `source` field for a path 2 row. The pins are in
`tests/test_api_path.py` (both directions of the join), `tests/test_unit_manifest.py` (the join reads the unit
set through the one rule), and `tests/test_ownership.py` (the `source` field names a response name). Path 1 is
unchanged.

What this piece does not do: no second unit rule, no second naming rule, no second writer, no second console
line, no report section for the findings, no environment name, no cache rule, no path rule, no membership
reader, no merge rule, no request-set gate rule (F8.8), no entry point and no run order (F8.9).
`tests/test_reference_edges.py` is unchanged, because the order rule reads no input shape.

## 1. The unit set is read through the one rule

1.1 `unit_manifest.units` stays the one unit rule: one unit is one combination of the five scope facts, and a
unit exists when the ledger has a report row in it. `api_requests.join_units` reads the unit set through that
function and through `unit_manifest.facts_of`, so path 2 states no second unit rule and counts no unit a second
way.

1.2 The join names no field of its own. The fact order comes from `unit_manifest`, and the field name for the
row's source comes from `ownership.SOURCE_FIELD`, so `src/api_requests.py` holds no field name as a string
constant, and the join adds no field to the declared manifest row shape or to the declared record shape.

1.3 The join answers the pair for each unit: the unit identity as the one rule states it, and the index entry
whose request made the response the unit's rows came from.

## 2. The fact path 2 adds

2.1 Path 2 adds one fact the join can read: the scope the run read for a unit. Each ledger row names the
response its entry came from, and that value is the key-free request identity `source_fetch` hashes, so the join
matches the row to the index entry through `source_fetch`'s name rule (`cache_name`) and states no cache rule and
no identity rule of its own.

2.2 The join answers which scope the run read for the unit, not which scope the unit sits in: the place response
for a place read, and the entry response for an entry read (F8.5). Same content, two reads, two answers.

2.3 The join reads the row set through one ledger, because the join is per response (F8.5). For a run that read
one response, the row set is that response's rows. Which row set a run that read more than one response joins is
the run order's decision, so this piece states no merge rule and the finding stays in `backlog.md`.

## 3. The two directions are findings

3.1 Direction 1: a unit the join answers no entry for, because the response its rows name is one the index made
no request for. A whole-config response holds no scope entry, and a scope no membership row reads gains no entry,
so a run that read the same content as a whole-config export, or as a predefined read, has a unit with no request.

3.2 Direction 2: an index entry the run read no rows for, so no unit answers it. The set is read from the
membership responses, so an entry the index names can exist while the run read no row for it.

3.3 The join reports both directions as data rows and nothing else: no console line, no writer, no report
section, no exit code, and no new gate rule (F8.8). A finding is data the join reports, so this piece decides no
predefined rule and no vsys rule.

## 4. The ownership source field

4.1 `OWNERSHIP.json` keeps the same row shape and the same field order for a path 2 run, with a response name on
the `source` field instead of a file name. No new field, no change to the order rule, and `parse_rows` reads a
path 2 record back as itself.

4.2 The `source` value is the source name, never its path, so a path 2 value holds no `/` and no credential.

## 5. The pins

5.1 `tests/test_api_path.py` (the new unit join group):

1. `test_the_unit_join_answers_the_scope_the_run_read_for_a_unit` — AC-1.3, AC-2.1, AC-2.2, AC-2.3.
2. `test_a_unit_the_index_made_no_request_for_is_a_finding` — AC-3.1.
3. `test_an_index_entry_the_run_read_no_rows_for_is_a_finding` — AC-3.2.
4. `test_the_join_reports_the_findings_as_data_through_the_owners_names` — AC-1.2, AC-3.3.

5.2 `tests/test_unit_manifest.py` gains `test_the_join_reads_the_unit_set_through_this_rule` (AC-1.1, AC-1.2).

5.3 `tests/test_ownership.py` gains `test_a_path_2_row_names_the_response_name_on_the_source_field`
(AC-4.1, AC-4.2, AC-1.2). The existing pins that read the record shape, the order, the round trip, the refusal
rule, and the gate are unchanged.

5.4 The pin `tests/test_api_requests.py::test_the_module_reads_the_layout_rules_through_their_owners` gains the
two names the join reads through their owners (`unit_manifest`, and `ownership` for the field name). The pin that
reads the string constants and the names the module must not define passes unchanged.

5.5 Every response in these pins is handed by an injected producer, so no test calls a network.

## 6. The checks

6.1 `ruff check .` is clean.

6.2 `python3 -m pytest` passes with no skip: the baseline 1623 pins, plus the pins above. No existing pin
regresses.

6.3 The commit is one ASD-STE100 message. When the rule lands, `docs/API_CONVERSION_PATH.md` §3 states it in the
present tense with the pins named, `README.md` and `docs/README.md` name the join and the pins as needed, the
completed piece leaves `to-do.md`, the cross-response row set and the names the join cannot read stay findings in
`backlog.md`, and `agent-status.md` names the next piece (F8.8, the request-set gate).
