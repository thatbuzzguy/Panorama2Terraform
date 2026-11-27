# Acceptance criteria

This file carries the record for the current task. Piece 14B.1 is committed at `336671a`, so its record lives in the
git history and is not restated here. The epic records stay as pointers: Epic 13's rules are in
`docs/INPUT_SHAPES.md`, and Epic 14's criteria are not restated here because that epic still has open pieces in
`to-do.md` and its decisions are in `docs/IMPORT_BINDING.md` §2.

## Piece, the gate and CI rules, in `docs/GATE_AND_CI.md`
(the current task, main, 2026-11-27)

A documents-only piece. No `src/` file changes and no test module changes, except that the index pin may move because
a new document joins the index. The name was taken by the operator on 2026-11-27 as `docs/GATE_AND_CI.md`, so the
piece writes the document under that name.

### Criteria

1. The document is named by `docs/README.md`, which
    `tests/test_layout.py::test_the_indexes_name_every_document_under_them` holds, and it is in the owner table of the
    same index.
2. It holds the rule set `agent-status.md` stated with no owner document: the gate-size decision, the shared test
   definitions with the two resource-line patterns and the rule each serves, the Python floor rule, the missing-binary
   skip rule, and the one-owner rule for the tool pins.
3. It restates no rule another document owns. It links to `docs/ARCHITECTURE.md` §1.1 for the layout, the flat test
   rule, `tests/conftest.py` as the one shared helper file, and the rule that the full run is the default gate. It links
   to `docs/ARCHITECTURE.md` §4.6 for the post-run gate on the output a run wrote. It links to `docs/WRITING_RULES.md`
   rule 4 for the rule that a wording check lives in `tools/check_documents.py`, and states no writing rule of its own.
4. Every pin it names is a name the test module defines, read through check 1, and each rule names the pin that holds
   it or states that no pin holds it.
5. Plain wording: ASD-STE100 sentences, no architectural or tactile metaphor, no marketing voice, no emoji. No test
   count. A version is stated only as the pin itself or as the measurement the document recorded, and a version stated
   outside its owner is a finding.
6. `agent-status.md`'s gate and CI section keeps the status, the links and the recorded measurements and states no
   rule.
7. The gate and CI half of the `backlog.md` entry "Permanent rules have no owner document" closes, and the watch-list
   half stays open with its name recorded as `docs/WATCHED_RULES.md` and the piece recorded as running next.
8. `to-do.md` marks this piece complete, so its record lives in the git history, and leaves the watch-list piece open.

### Gate measurement, 2026-11-27

Run single-threaded, in one process, with no parallel plugin:

1. `ruff check .` clean at `py310` with the 120-character line length.
2. `ruff format --check .` clean on 114 files, measured, one more than the baseline's 113 because of the new
   markdown document.
3. `python3 tools/check_documents.py` reports no finding.
4. `python3 -m pytest -p no:cacheprovider` exits 0 with 1,897 passed and 4 `tflint` skips, so 1,901 pins in 55 test
   modules, in 411.32 s on the tree that holds this piece; the same set measured 464.24 s on the same tree before the
   tracking files were written, so the counts agree. No pin moved: no pin was added, no pin body changed, and no test
   module changed, so the pin count and the test module count are the baseline's. `tflint` is absent on this machine,
   so its four pins skip, as they did at the baseline; `terraform` is present at 1.16.2, so the provider-schema pins
   ran. No committed golden byte moved.

### Baseline

From `agent-status.md` Piece 14B.1, measured 2026-11-27: 1,897 passed plus 4 `tflint` skips, 1,901 pins in 55 test
modules, `ruff check .` and `ruff format --check .` clean on 113 files, and `python3 tools/check_documents.py` reports
no finding.