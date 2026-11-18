# Acceptance — the index pin reads the module-table half once (Piece 15)

Criteria set 2026-11-18 for the `backlog.md` finding Piece 14 recorded: the index pin reads the half
of the index rule that compares every `src/` module with the `docs/ARCHITECTURE.md` §1 module table
twice inside the same pin, so the same set is read twice on every run. This piece measures the
repetition again, removes the second block, and records the measurement.

Owners: `docs/ARCHITECTURE.md` §1.1 owns the layout rule and the index rule, and states that a pin
holds a name being present and cannot hold how a document words it, so the document-review checks sit
in `tools/check_documents.py`, which the test set does not read.

`tests/test_layout.py` holds the one pin for the index rule and reads names only, so this piece
changes no other test file. `agent-status.md` and `acceptance.md` hold the measurement.

Rules this piece works under, from `agent-status.md` §Rules to keep when writing documents:

- One owner document per rule; every other document links to it.
- A pin measures content or a name, never the wording of a document. A wording check is a document
  review, so it lives in `tools/check_documents.py`, which the test set does not read.
- A pin is not weakened or removed: the pin keeps the same fact, the same name, and the same reads.
- No document states a test count; `agent-status.md` and `acceptance.md` hold the measurement.
- Standard library only; everything stays offline and deterministic.
- The repository root stays clean: this piece changes no output, no golden and no fixture.

## Item 1 — the instance, measured before the fix

`tests/test_layout.py`, measured 2026-11-18 on the tree at commit `5c70949`. The file is 78 lines,
the pin runs from line 28 to line 78, and it holds 8 asserts. Its AC-4 half is stated twice:

- Block one, lines 68 to 72: the AC-4 comment, the read of `docs/ARCHITECTURE.md`, the split to the
  §1 module table, and the loop that asserts each `src/` module is named in it.
- Line 73 is the blank line between the two blocks, which is why `backlog.md` read the first block as
  lines 68 to 73.
- Block two, lines 74 to 78: the same five lines, word for word, so the pin reads the same 22 `src/`
  modules against the same table text a second time on every run.

The two blocks are identical, so they state one fact, not two: every module in `src/` is named in the
§1 module table. Nothing needs merging, so the fix removes the second block, and the pin keeps the
fact, the name, the comment, the reads and the assertion.

- AC-1.1: the repetition is measured before any line is removed, and the count is reported before and
  after.
- AC-1.2: the removed lines are the second block only. The first block is unchanged, including its
  AC-4 comment, so the pin's AC wording stays honest: one AC-4 block remains, and this file names one.
- AC-1.3: the pin's name, its docstring, the set it reads, and its assertion are unchanged. The assert
  count falls from 8 to 7 because one duplicate assert is removed, and the pin count does not change,
  because a pin is the test function, not an assert.
- AC-1.4: after, measured on the tree with the change: the file is 72 lines, the pin holds 7 asserts,
  and the AC-4 comment and the read of the §1 module table each appear once, so the pin reads the same
  22 `src/` modules against the table text once per run. The pin passes.

## Item 2 — is there a rule that a pin block is not repeated

**Decision: no such rule exists, and this piece does not invent one.** The rule that a pin measures
content or a name, never the wording of a document, says nothing about a pin reading the same set
twice. The checks that read documents are `tools/check_documents.py` checks 1 to 6, and none of them
reads a test file for a repeated block, so a pin block that repeats is not a finding a check can
print. The pins that read test files read a name or a needle, not a repeated block.

- AC-2.1: the decision is recorded here and in `backlog.md`, and no check and no pin is added for it,
  so this piece fixes the instance, not the rule.
- AC-2.2: the rule that a pin reads names and not wording stays where its owner states it, and
  `tools/check_documents.py` stays the place a wording check lives, so nothing moves.

## Item 3 — the gate

Run in order, with no parallel runner: `ruff check .`, `ruff format --check .`, `python3 -m pytest`,
`python3 tools/check_documents.py`. Conservative threads. The count is read from the per-module
collection counts, because `pyproject.toml` sets `addopts = "-q"`.

Before, measured 2026-11-18 on the committed tree at `5c70949`: `ruff check .` clean at `py310`,
`ruff format --check .` clean on the 100 Python files, 1,697 pins in 52 test modules, all pass, no
skips, 271.38 s with tflint 0.66.0 present, and `python3 tools/check_documents.py` reports no finding.

After, measured 2026-11-18 on the final tree with the change, in that order, with tflint 0.66.0
present: `ruff check .` clean at `py310`, `ruff format --check .` clean on the 100 Python files,
1,697 pins in 52 modules, all pass, no skips, 258.53 s, and `python3 tools/check_documents.py` reports
no finding, read at 6.54 s after the final document edits. The same set measured 263.54 s on the run
before those document edits, and 271.38 s on the tree before the change, so the document edits changed
no pin. The pin count is unchanged, so AC-1.3 holds, and `tests/test_layout.py` still reads 1 pin.

## Item 4 — the files this piece changes

`tests/test_layout.py` (the second block removed), `acceptance.md`, `to-do.md`, `backlog.md` (the
finding closed), `agent-status.md`. `AGENTS.md` is not changed and not committed: it holds an
uncommitted user edit. `agent-status.md` keeps its name, because the tree holds `agent-status.md` even
though `AGENTS.md` names `agent-status.html`.
