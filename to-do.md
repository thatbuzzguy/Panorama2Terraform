# To Do

The tracking markdown for the completed pieces is removed here; the git history and the owner documents hold it.

Piece 14, committed 2026-11-18, is the last offline-actionable item and is complete. `README.md`
§Testing now names each entry once. The decision: the section was wrong and not its rule, because 26
of its 81 entries were a block repeated after the gate area, and each pair states the same facts, so
nothing was merged. The rule stays as the section states it, and the check that reads it is
`tools/check_documents.py`, the document-review script, because a pin holds a name being present and
cannot hold a name appearing once. Measured before: 81 entries, 55 names, 26 named exactly twice and
none three times, so the `backlog.md` claim of three for `tests/test_sanity_gate.py` did not hold.
Measured after: 55 entries, each named once, the same 52 test modules, and the check reads the
committed README as 26 findings and the fixed README as none. No pin was added, weakened or removed:
1,697 pins in 52 modules before and after. The decision, the criteria and the gate measurement are
in `acceptance.md`.

One finding found while reading the index pin stays open in `backlog.md`: `tests/test_layout.py`
reads the `src/` module-table check twice inside the same pin. It is not part of this piece.

No offline-actionable item remains. What stays open in `backlog.md` is blocked on a fact the tool
cannot read offline, or is a repetition inside a pin that the rules put outside this piece.

## Feature-sized items that stay blocked

Feature-sized items that stay blocked on a fact the tool cannot read offline are recorded in
`backlog.md` and are not pieces here: the four `*_policy_rules` types wait for the F3.5 rulebase
decision and a live target, a config entry inside a stack needs a provider location shape, the EDL
`certificate_profile` field needs a rule that makes the EDL site resolve names, the per-entry report
`profile_name` column needs a value the provider does not declare, and the path 2 live facts in
`docs/API_CONVERSION_PATH.md` §4 need a live target: the committed response set shows one shape per
accepted request shape and names no fact.

## Rules the layout keeps

- `docs/ARCHITECTURE.md` §1.1 is the owner document for the layout. `AGENTS.md` names the tracking
  markdown set, and each index names every document under it, so a file outside an index is a finding.
- Import rule: `docs/ARCHITECTURE.md` §1.1 is its owner. `src/` is one flat namespace, so a module may import any
  `src/` module without a cycle, and nothing under `tests/` may import another test module: a fact more than one
  test module reads is stated once in `tests/conftest.py` and read from there. The one test that checks the rule
  reads only `src/`. A test may import `src` modules and `tests/conftest.py` through `importlib`. `src/`
  may not import from `tests/`. `tools/` is not on the test path, so `tests/test_build_kitchen_sink.py`
  reads the fixture assembler through `importlib` on the path `tests/conftest.py` builds once.
- Path 2 adds two modules, `api_requests.py` and `api_to_terraform.py`, and both must be named in the
  `docs/ARCHITECTURE.md` §1 table. Both state no second naming rule, no second writer, no second
  console line, and no environment name, so the pins that scan the `src/` set read them with the other
  modules.
- The corpus is the directory the scan runs over. A hostile fixture in it changes the set the scan
  reports for the other fixtures, so pins that state the printed set name the fixture count. The fixture
  assembler reads the same set by rule: a fixture the F3.8 input rule refuses is skipped, and the record
  is not an input (`tests/test_build_kitchen_sink.py`). A committed API response is not corpus material, so
  it sits in its own set (`tests/responses/`), and the pins that state the printed fixture set are not
  changed by it (`docs/ARCHITECTURE.md` §1.1).
