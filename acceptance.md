# Acceptance criteria — piece 3, pins that measure nothing

## Scope

Five findings from the 2026-11-11 audit (`backlog.md`), each about a pin that passes without reading
content. The owners are `tests/conftest.py` and the fifteen test modules the findings name:
`test_api_requests.py`, `test_commit_actions.py`, `test_container_coverage.py`, `test_data_blocks.py`,
`test_data_file_gate.py`, `test_entry_coverage.py`, `test_import_blocks.py`, `test_ownership.py`,
`test_parse_profiles.py`, `test_parse_rules.py`, `test_property_coverage.py`, `test_reference_edges.py`,
`test_round_trip.py`, `test_sanity_gate.py`, and `test_unit_manifest.py`, including the two that carry the
corpus guard outside the eight name-rule sites the audit named. No functional code of the tool changes, and
no new rule is stated: each pin is changed so that it reads the material its own rule names.

1. The four pins that compare an empty set with an empty set.
2. The guarded vacuity in `tests/test_commit_actions.py`.
3. The self-referential length pin in `tests/test_api_requests.py`.
4. The hostile-fixture exclusion, which has two definitions: the tool's read rule and a name rule.
5. The order pins that read dict insertion order.

## The criteria

1. **The golden byte pins read the set the layout rule states.** A golden case holds no `.tf` file at the
   case root, because the run writes one directory per unit (`docs/CODEBASE_ASSEMBLY.md` §14). Each of the
   four pins reads the `.tf` set through `rglob`, keyed by the path from the case directory, as
   `tests/test_golden_files.py` does, for both sides of the comparison. Keyed by the file name, two units
   that write the same file name collapse, so the key is the path. Each pin also states that the set it
   reads is not empty, so a run of the pin measures content. The pins are
   `tests/test_data_blocks.py::test_a_run_that_declares_no_read_through_scope_writes_the_golden_bytes`,
   `tests/test_ownership.py::test_the_goldens_are_byte_identical`,
   `tests/test_reference_edges.py::test_the_golden_tf_bytes_are_unchanged`, and
   `tests/test_unit_manifest.py::test_the_generated_tf_bytes_are_unchanged`. The read shape is `tf_bytes`,
   stated once in `tests/conftest.py`, because more than one module reads it.

2. **The actions pin asserts the file exists.** `tests/test_commit_actions.py::
   test_no_false_positive_across_the_corpus` asserted only when the run wrote a file, so a fixture that wrote
   nothing counted as a pass. The guard is removed. The pin reads the fixtures the input rule accepts, asserts the
   run wrote at least one `.tf` file for each, and states the two cases separately: for a fixture the generator
   answers with action rows, the actions file exists; for a fixture it answers with no row, no actions file exists,
   which is the content rule the module already pins. The decision about which fixture writes the file is read
   through `commit_actions.build_rows`, the rule owner, so the test states no second rule and names no fixture.

3. **The harness pin reads the module's table.** `tests/test_api_requests.py::
   test_one_committed_response_per_request_shape_names_the_request_identity_that_produced_it` asserted the length
   of this file's own harness list, so it measured nothing. The pin reads `source_fetch.SHAPE_PARAMS` instead: one
   entry per accepted request shape the module states, and the shape literal the table states is inside the
   identity that names the committed response. The pin that compares the two file sets
   (`test_the_committed_responses_are_not_corpus_material`) is read the same way, so no pin in this module states
   the shape set as a literal count.

4. **One exclusion rule for the corpus.** The name rule (`startswith('hostile_')`) is gone from every corpus
   pin. `tests/conftest.py` states the exclusion once, through the tool's read rule on the committed bytes:
   `xml_input.check_bytes`, then the parse. The pins that read the corpus read that set, and the pins that read
   the refusal path keep their own pins (`tests/test_robustness.py`, `tests/test_build_kitchen_sink.py`). The
   two definitions must agree on the committed corpus, which `tests/test_build_kitchen_sink.py` already pins,
   so the set the pins read does not change: 68 accepted, 3 refused. A pin that reads an accepted fixture must
   not need a guard, because the parse cannot fail for it. The guard is therefore removed from the corpus pins,
   including the two sites the audit did not name: `tests/test_reference_edges.py::_sets` and
   `tests/test_property_coverage.py::_corpus_ledgers`.

5. **The order pins state which rule they hold.** `tests/test_parse_rules.py:12,41,122,163` and
   `tests/test_parse_profiles.py:91` assert `list(by_name) == [...]`. Decision: these pins hold the document
   order the policy-chain rule states (`docs/ARCHITECTURE.md` §4.4), so each asserted list is the order the
   fixture names its entries. The name-keyed read is kept, because each pin reads one rule by name, so each
   pin also states the uniqueness rule for its fixture: the name-keyed read holds one row per name only when
   the fixture names each rule once, which the pin asserts. The decision is stated in both module headers.

6. **The gate stays green.** `ruff check .` is clean, and `python3 -m pytest` passes with no skips. No pin is
   weakened, and no pin passes because it reads less material than before. Where a pin starts measuring real
   content and fails, the result is reported as a finding and recorded in `backlog.md` with its owner, not
   asserted away.

7. **The tracking markdown records the piece.** The five findings leave `backlog.md` when they are fixed, the
   piece stays in `to-do.md` until it is committed, and `agent-status.md` holds the pin counts and the gate
   result. Test counts appear only in `agent-status.md` and the git history. No new pin reads the tracking
   markdown.

## Out of scope

- `tests/fixtures/api_response.xml`, which sits inside the corpus, and the pin at
  `tests/test_api_requests.py:649-650` that keeps it there. That is the layout finding, and its fix moves a
  file; it stays in `backlog.md`.
- The pins that restate an owner table as a measured count, the `tests/` index, the document pin claims, and
  the provider-schema pins that do not run in CI. They are other pieces of this series.
- The parse set, the naming and printing rules, and the splitter, which are pieces 4 to 6.

## Measurement (before, 2026-11-13)

Gate before: `ruff check .` clean, `python3 -m pytest` passes with no skips, 1,651 pins. `terraform` is
present, Python 3.12.3. The pin count is recorded in `agent-status.md`.

Measured on the committed material:

- Corpus: 71 fixture files, 68 accepted by the read rule, 3 refused (`hostile_billion_laughs.xml`,
  `hostile_xxe.xml` by the DTD check; `hostile_bad_control_char.xml` by the parse). The name rule answers the
  same 68 names, so the two definitions agree today and diverge only for a fixture that is refused without the
  name, or named without the refusal.
- Goldens: 87 `.tf` files, all inside unit directories, so no `.tf` file sits at a case root. The four empty-set
  pins read `glob('*.tf')` at the case root, so both sides of each comparison are empty today.
- Actions: every one of the 68 accepted fixtures writes at least one `.tf` file, so the guarded pin is not
  empty today, and 25 fixtures write `actions.tf` with 96 blocks while 43 write none. The file exists for
  exactly the fixtures `commit_actions.build_rows` answers with rows. `tests/fixtures/scope_child.xml` writes
  no manifest, so the pin reads no rows for it.
- Order: for the five fixtures the order pins read, each asserted list is the entry order in the file, and no
  fixture repeats a rule name, so both readings agree today. The pins therefore hold the document order, and
  the uniqueness rule is a fact that no pin states.

## Measured results (after, 2026-11-13)

Gate after, measured 2026-11-13: `ruff check .` clean, `python3 -m pytest` passes with no skips, 1,651 pins in
293.0 s — the same count as before, so no pin was added, removed, or weakened, and no pin failed once it measured
content. The count is recorded in `agent-status.md`.

What each pin now measures:

1. The four golden byte pins read the `.tf` set through `tests/conftest.py::tf_bytes` (the `.tf` subset of
   `written_bytes`, keyed by the path from the case directory) and assert both sides are not empty. Each pin
   reads the two cases it names, `sample` and `kitchen_sink`, so each compares 14 entries and 61 entries
   instead of two empty sets. The goldens still hold no `.tf` file at a case root, which the criteria assumed,
   and the two sides agree.
2. `tests/test_commit_actions.py::test_no_false_positive_across_the_corpus` asserts the read set is not empty
   for each of the 68 accepted fixtures, and states the two cases separately through `commit_actions.build_rows`:
   25 fixtures answer with rows and have the actions file, 43 answer with no row and have no file. `_manifest`
   answers no row for the fixture that writes no manifest (`scope_child.xml`), so the pin reads no row for it.
3. `tests/test_api_requests.py::test_one_committed_response_per_request_shape_names_the_request_identity_that_produced_it`
   reads the shape set through `source_fetch.SHAPE_PARAMS` and asserts each stated `key=value` pair is inside the
   identity that names the committed response; `test_the_committed_responses_are_not_corpus_material` reads the
   same table instead of a literal 3. Both pass on the 3 committed responses.
4. The exclusion is the tool's read rule, stated once in `tests/conftest.py` (`input_refusal`, read as
   `corpus_fixtures()`). No test module states the name rule, and no corpus pin needs a guard: 18 read sites in
   12 test modules read the accepted set, including the six sites the audit did not name. The accepted set is the
   same 68 fixtures, so no pin's read set changed.
5. The five order pins hold the document order the policy-chain rule states, and each asserts the uniqueness
   rule the name-keyed read depends on (`len(by_name) == len(rules)`). All five pass, so the two readings agree
   on the committed fixtures.

The four comments that pointed at "the module header" now name `tests/conftest.py`, because the rule they read
is the shared read rule there.

No pin failed once it started measuring content, so `backlog.md` gains no new finding for this piece; the five
findings leave it.
