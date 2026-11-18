# To Do

The tracking markdown for the completed pieces is removed here; the git history and the owner documents hold it.

Piece 15, committed 2026-11-18, is the last offline-actionable item and is complete, and it closed
the finding Piece 14 left open:
`tests/test_layout.py::test_the_indexes_name_every_document_under_them` reads the §1 module-table
half of the index rule twice inside the same pin. Re-measured 2026-11-18 on the tree at `5c70949`:
the pin holds 8 asserts and states its AC-4 check twice, at lines 68 to 72 and at lines 74 to 78,
word for word, with the blank line 73 between them, so the same 22 `src/` modules are read against
the same table text twice on every run. The two blocks state one fact, so nothing was merged: the
second block is removed and the pin keeps the fact measured once, with the same name, comment, reads
and assertion. Measured after: 7 asserts instead of 8, one AC-4 comment and one read of the module
table. The pin count is unchanged before and after, so no pin was added, weakened or removed.

The decision on the rule: no rule states that a pin block is not repeated, and this piece does not
invent one. The rule that a pin measures content or a name says nothing about reading a set twice,
and `tools/check_documents.py` reads documents, not test files, so a repeated block inside a pin is
not a finding a check can print. The instance is fixed, not the rule. The criteria and the
measurements are in `acceptance.md`.

No offline-actionable item remains. What stays open in `backlog.md` is blocked on a fact the tool
cannot read offline.

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
