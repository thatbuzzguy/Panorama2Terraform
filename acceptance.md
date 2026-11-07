# Acceptance criteria — F8.4, the offline harness (Epic 8, Phase 8A)

Scope: the committed response set, the layout path `tests/conftest.py` builds for it, the harness pins in
`tests/test_api_requests.py`, one no-network pin in `tests/test_source_fetch.py`, one read-set pin in
`tests/test_build_kitchen_sink.py`, and the decision named in `docs/ARCHITECTURE.md` §1.1 and
`docs/API_CONVERSION_PATH.md` §5. No `src/` module changes: the three request shapes, the wrapper decision,
the request identity rule and the record are already landed, and a harness adds no rule. No parse method runs
over a response (F8.5), no record per request is written (F8.6), no gate rule is added (F8.8), no entry point
is added (F8.9), and path 1 is unchanged.

## 1. Where the response fixtures live

1.1 `tests/` is flat with three sets: `fixtures/` (the corpus, the directory the scan runs over), `golden/`
(the pinned bytes of a run), and `responses/` (the committed API responses). `tests/conftest.py` is the one
shared helper file and the one place the path to each set is built, so a harness pin reads the response set
through it and states no path of its own.

1.2 A committed response is not a Panorama export, so it is not corpus material. The scan runs over the
corpus, and `tools/build_kitchen_sink.py` reads the committed fixtures under the F3.8 input rule, so a
response file enters neither the set the scan reports nor the assembler's merge set. The pins that state the
printed fixture set read the corpus directory, so they are undisturbed by this piece. The decision is named in
`docs/ARCHITECTURE.md` §1.1, which is the owner document for the layout.

1.3 A committed response is read through the fetch layer, never through the file producer, because the wrapper
decision belongs to the request that produced it. The existing committed response fixtures that the corpus pins
read (`tests/fixtures/api_response.xml`, `scope_child.xml`, `scope_parent.xml`) stay in the corpus and are not
moved, so the printed fixture set is unchanged.

## 2. One committed response per request shape, named by the request identity

2.1 The response set holds exactly one file per accepted shape: the whole-config export, the per-scope read,
and the device fact.

2.2 Each file is named by the key-free request identity that produced it, in the shape the record reads as
`cache_entry`: the SHA-256 hex of the host and the sorted params. The file states the same identity in its
prolog comment, so a reader can see which request produced it, and no file names a credential.

2.3 The three requests state their own shape through what they declare (F8.1): nothing else is the
whole-config export, a path is the per-scope shape, a command is the device fact shape.

## 3. The producer stays injected

3.1 No test calls a network. The harness injects a producer that hands the committed bytes, and the default
producer stands in as one that fails the test when called.

3.2 For each shape, `fetch()` through the injected producer reads the committed bytes through the door, hands
back the shape its own request states, and writes the cache entry under the name the fixture is named by, with
the committed bytes unchanged.

3.3 A harness pin reads the same bytes the record names: the record built through `provenance.record_for` names
the fixture as `cache_entry`, names the key-free identity as `request`, and states the size and the SHA-256 hex
of the committed bytes. No record names a credential.

## 4. The join, read through the committed fixtures

4.1 The committed per-scope response is the membership read the index is built from, so the index and the join
read the same bytes: the names inside it are the names the index read, and the join accepts the response for
the entry whose request made it and answers them in sorted order. The F8.3 pins are unchanged, so the join is
not weakened.

4.2 The committed device fact response shows the shape one command gives, and names no fact. The fetch layer
states no command-to-element table, so `names_element` names no element for a command and the join has nothing
to read a command's element name against. The fixture is an illustration, not a measurement, and it holds no
live fact, so the facts in `docs/API_CONVERSION_PATH.md` §4 stay blocked and are not unblocked here.

## 5. The pins

5.1 `tests/test_api_requests.py` (the harness group):
`test_one_committed_response_per_request_shape_names_the_request_identity_that_produced_it`,
`test_a_committed_response_reads_through_the_injected_producer_and_the_record_names_the_same_bytes`,
`test_the_committed_responses_are_not_corpus_material`,
`test_the_join_reads_the_committed_per_scope_response_through_the_injected_producer`,
`test_the_committed_op_response_shows_one_shape_and_names_no_live_fact`.

5.2 `tests/test_source_fetch.py` (the no-network rule, read for the committed set):
`test_a_committed_response_is_read_through_the_injected_producer`.

5.3 `tests/test_build_kitchen_sink.py` (the read set, read for the response set):
`test_the_assembler_reads_the_corpus_and_not_the_response_set`.

## 6. The checks

6.1 `ruff check .` is clean.

6.2 `python3 -m pytest` passes with no skip: the baseline 1597 pins, plus the pins above. No existing pin
regresses, and the pins that state the printed fixture set answer the same set as before this piece.

6.3 The commit is one ASD-STE100 message. When the rule lands, `docs/API_CONVERSION_PATH.md` §5 states the
harness in the present tense and names the pins, `docs/ARCHITECTURE.md` §1.1 names the response set as a set
and the rule that it is not corpus material, `docs/README.md` names the owner of that decision, the completed
piece leaves `to-do.md`, the finding about a command's element name is made honest in `backlog.md` (the shape
is shown, not verified), and `agent-status.md` names the next piece (F8.5, the run over many sources).
