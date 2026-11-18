# Acceptance — the membership entry read (Piece 8)

Criteria set 2026-11-18 for the finding `backlog.md` recorded from the F8.10 measurement. The finding is the
case `docs/API_CONVERSION_PATH.md` §2.4 and §6 do not cover: an entry a membership list names is also the entry
the run read as its own scope, so the run reads it twice.

Owners: `docs/API_CONVERSION_PATH.md` §2.4 and §6 for the rule; `src/api_requests.py` for the join's answer for
the entry the run read; `src/panorama_to_terraform.py` for the parse method that reads it;
`tests/test_api_path.py` for the pins. `sanity_checks.check_round_trip` is read through its owner, so this piece
states no round-trip rule of its own.

Rules this piece works under, from `agent-status.md` §Rules to keep when writing documents:

- One owner document per rule; every other document links to it.
- No test counts in a document. A document names the test that pins a rule.
- A pin measures content or a name, never the wording of a document.
- A historical record is not kept in the markdown; the git history is the record.

## The decision

**1. The double read stands, and both answers stand.** The run order reads the membership response and then the
entries the index names, so an entry a membership list names is read twice: once inside the membership response,
once as the response its own request made. Path 2 states no rule that one of the two answers is the answer for
the entry, so the run keeps both.

**2. One response is one source, so each response records its own rows.** The same entry read twice is two report
rows, each naming the response that holds it with the line inside it. The run view states no merge rule, so the
row set is the parts in run order. This is what `tests/test_api_path.py::test_the_same_name_in_two_responses_gives_two_rows_naming_two_sources`
and `test_the_entry_point_joins_the_tables_across_the_responses_it_read` already hold; this piece adds no dedupe.

**3. The entry read answers the entry its own request names.** A parse method reads the entries at the level its
container-table row names. A whole-config source and a place read reach that level through the container element,
so they are unchanged. A per-scope entry response holds no container element: `result` is the place the path names
(`container_coverage.container_tag`, the one statement of the per-scope shape), so the entry under the root is the
entry at the level the path names first, and the method named by the row reads it. The membership read stays on the
place rule: `parse_associations` reads its lists inside the place the response names, so a per-scope entry response
answers no membership table and the index still reads its set from the membership responses.

**4. Path 2 writes the content of each response it read.** With no merge rule, the joined answer holds one value
per response for the same entry, so the writer writes one block per response that holds the entry. The name rule
(`naming.py`, read through `declare_block_name`) gives the second block the `_2` suffix. Path 1 read one response,
so it writes one block per entry, so the byte agreement between the two paths holds only for content that states
no membership list. `tests/test_api_path.py::test_content_with_no_live_only_fact_writes_the_same_tf_bytes_as_path_1`
keeps that content and is unchanged.

**5. The cross-check counts agree for the double read.** `check_round_trip` counts the `emitted` rows against the
blocks the reader read, per unit and per row. For the double read both counts read 2 for the same unit and row, so
the rule reports nothing, and `check_request_set` reports nothing because both responses are in the read set. Path 1
reports nothing on the same content. The gate is not changed by this piece; the pin measures what the existing rule
reads for the double read.

## The pins this piece adds

Each pin measures content read through an injected producer, and the content shows a membership list, which the
F8.10 content does not. No pin calls a network. New content: `MEMBERSHIP` and `MEMBERSHIP_EXPORT`, the same two
scope entries with a membership list in each.

- `test_the_entry_read_answers_the_entry_its_own_request_names` — criterion 3: the parse method named by the row
  for the scope level reads the entry the response holds, so the entry read answers its own entry, and the
  membership read answers no table for an entry response.
- `test_an_entry_two_responses_hold_gives_one_block_per_response` — criteria 1, 2 and 4: the run read four
  responses for the content, the same entry gives two rows naming two sources, path 2 writes two blocks per unit
  with the `_2` name on the second, and path 1 writes one block per unit for the same entry, so the bytes do not
  agree for content that states a membership list.
- `test_the_double_read_agrees_with_the_gate` — criterion 5: `check_round_trip` and `check_request_set` report
  nothing for the path 2 run on this content, path 1 reports nothing, and the join answers the entry response for
  the row the entry read and the place response for the row the place read.

No existing pin is weakened. The run-order pin, the join pins, the unit-join pins, the round-trip pins and the
gate pins are re-measured after the change.

## Measurement, before the change

Baseline measured 2026-11-18, on the content `MEMBERSHIP` (two scope entries, a membership list in each, one
address entry inside each):

- The run order reads 4 responses: `device-group`, `templates`, then `device-group/entry/Office-FW` and
  `templates/entry/HQ-Networks`.
- 8 report rows: 2 per entry, each naming its own response.
- Path 2 writes 4 address blocks (2 per unit, the second named `_2`) and 1 scope block per unit.
- `check_round_trip`: 2 WARN findings, one per unit, each stating that the ledger reads 2 entries and the reader
  reads 1 block, because the entry read records a row for the entry its own request names and answers no object
  for it. `check_request_set`: nothing. Path 1 on the same content: nothing.

Gate baseline: `ruff check .` clean, `ruff format --check .` clean, 1,685 pins in 52 test modules, all pass, no
skips, 333.87 s; `python3 tools/check_documents.py` reports no finding.

## Measurement, after the change

Measured 2026-11-18 on `MEMBERSHIP`, read through `_membership_producer`:

- Path 2 reads 4 responses: `device-group`, `templates`, then `device-group/entry/Office-FW` and
  `templates/entry/HQ-Networks`. Each entry response answers the entry its own request names, and answers no
  membership table.
- 8 emitted report rows: 2 per entry name, each naming its own response. The 4 names are `Office-FW`,
  `HQ-Networks`, `10.0.0.7`, `10.0.0.9`.
- Path 2 writes 8 resource blocks: 4 per unit, one scope block and one address block per response that holds the
  entry, and the second block for a name carries the `_2` the naming rule states. Path 1 writes 4 blocks for the
  same content read as one export, so the two file sets are not the same bytes.
- `check_round_trip`: no finding for either run; for the double read both counts read 2 for the same unit and the
  same row. `check_request_set`: no finding for path 2 (both responses are in the read set) and NOT RUN for path 1.
- The join answers the entry response for the row the entry read built for its own scope entry, and the place
  response for the row the place read built for the same entry.

Gate after the change: `ruff check .` clean, `ruff format --check .` clean, `python3 -m pytest` passes
1,688 pins in 52 test modules with no skips in 305.56 s; `python3 tools/check_documents.py` reports no finding.
`tests/test_api_path.py` reads 33 pins (30 before this piece). No existing pin was weakened: the run-order pin,
the join pins, the unit-join pins, the round-trip pins and the gate pins pass unchanged.
