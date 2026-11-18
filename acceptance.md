# Acceptance — `README.md` §Testing names each module once (Piece 14)

Criteria set 2026-11-18 for the `backlog.md` finding Piece 13 recorded: `README.md` §Testing states
that each module is named once there, and the section names test modules twice. This piece measures
the duplication again, decides which side is wrong, and records the measurement.

Owners: `docs/ARCHITECTURE.md` §1.1 owns the layout rule and the index rule, and states that a pin
holds a name being present and cannot hold how a document words it, so the document-review checks
sit in `tools/check_documents.py`, which the test set does not read. `tests/test_layout.py` holds
the one pin for the index rule and reads names only. `README.md` is the root index, so it owns
naming the test set; its §Testing section states the rule that each module is named once there,
which is wording, so the check that reads it is the document-review script and not a pin.
`agent-status.md` and `acceptance.md` hold the measurement.

Rules this piece works under, from `agent-status.md` §Rules to keep when writing documents:

One owner document per rule; every other document links to it. A pin measures content or a name,
never the wording of a document, so a wording check lives in `tools/check_documents.py`, which the
test set does not read. No pin is weakened or removed. If this piece writes no pin, the reason is
recorded here. No document states a test count; `agent-status.md` and `acceptance.md` hold the
measurement. Standard library only; everything stays offline and deterministic.
`tools/check_documents.py` reads the tool's tables through `ast` and the license split through
`git`, imports no tool module, and writes no file. The repository root stays clean: this piece
changes no output, no golden and no fixture.

## Item 1 — which side is wrong

**Decision: the README is wrong, not the rule.** The section states one rule (a module is named
once, because the root index names the test set) and then repeats a block of rows it had already
listed. Each duplicate is a repeat of the same facts in another place, not a second fact about one
module, so the section agrees with its own rule once the repeated rows are gone. The rule stays as
it is: the section lists each module in its own area, so a module has one row.

AC-1.1: measure the duplication again before fixing it, and report the count before and after. The
`backlog.md` entry says 24 test modules named twice, with `tests/test_sanity_gate.py` three times;
the count is re-read on the current tree, because it moves with Pieces 10 to 13. AC-1.2: each
duplicate is read as a pair before any row is removed, and a pair is removed only when the two rows
state the same facts. A pair that states different facts is merged into one row instead of deleted.
AC-1.3: every module the section named before is still named after, in one row, in its own area, so
the index pin still reads every test module name in the root index. AC-1.4: the sentence that states
the rule stays, and names where the rule is checked, so the document does not claim a check the
project does not have.

## Item 2 — the check that reads the rule

**Decision: the duplicate-name check goes in `tools/check_documents.py`, as a document-review
check.** The project rule puts a wording rule there, because a pin can hold a name being present and
cannot hold a name appearing once. The check reads the section as a list of names, so it measures
the names and not the prose, and it reports the section disagreeing with the rule the section
states.

AC-2.1: the check is in the document-review script, not in a test. No pin is added, and no pin reads
document wording. AC-2.2: the script keeps its own rules: standard library only, no tool module
import, no file written, not part of the gate, and the test set does not read it. AC-2.3: the check
reports the duplication before the fix, so the finding it was written for is measured by the check
itself, and reports no finding after the fix. AC-2.4: the check reads only the section that states
the rule, so it cannot read a name in another document as a duplicate of a name in §Testing.

## Item 3 — the layout and the index pins

AC-3.1: no document is moved, renamed, or deleted, so no index changes and the index pin is
unchanged. AC-3.2: `tools/check_documents.py` is named by `tools/README.md`, and `tests/` keeps no
index of its own, so both stay as §1.1 states. AC-3.3: the pin count is recorded before and after
and is expected unchanged, because this piece adds no pin.

## Item 4 — the measurement

Before, measured 2026-11-18 on `README.md` §Testing (read from `## Testing` to the next heading, the
list entries read as the name at the start of each entry):

81 entries, 55 distinct names: 52 test modules, `python3 -m pytest`, and the two lint and format
legs. The 52 test modules are the whole test set, so the index pin reads the same names before and
after. 26 names are named more than once, each exactly twice: 24 test modules and the two legs. No
name is named three times, so the `backlog.md` claim of three for `tests/test_sanity_gate.py` does
not hold on the current tree. Read as the entry text from the name to the next entry or heading, 25
of the 26 pairs are identical word for word, and the pair for `ruff format --check .` is the same
line: the text that read as different is the prose paragraph that follows its second occurrence, the
flat layout rule. So no pair states two different facts, and nothing needed merging. The repeated
block is the 26 entries that follow the first occurrence of the two lint and format legs, in the
order the earlier areas list them, so the fix removes that block and keeps each module's row in its
own area.

After, measured the same way: 55 entries, 55 names, each named once: the same 52 test modules,
`python3 -m pytest`, and the two legs.

## Item 5 — a finding recorded during the piece

`tests/test_layout.py` reads one half of the index rule twice: the block that compares every `src/`
module with the §1 module table is stated twice in the same pin, at lines 68 to 73 and at lines 74
to 78, measured 2026-11-18. This is repetition, not a rule finding: the pin passes either way, so
the fix is to remove the second block. It is outside this piece, so it stays in `backlog.md`. The
piece changed no test file.

## Gate

Run in order, with no parallel runner: `ruff check .`, `ruff format --check .`, `python3 -m pytest`,
`python3 tools/check_documents.py`. Conservative threads.

Before, on the committed tree at `d2ca9fd`: `ruff check .` clean at `py310`, `ruff format --check .`
clean on the 100 Python files, 1,697 pins in 52 test modules, all pass, no skips, 335.42 s, and
`python3 tools/check_documents.py` reports no finding. The count is read from the per-module
collection counts, because `pyproject.toml` sets `addopts = "-q"`.

After, measured 2026-11-18 on the tree with this piece's edits, in that order, with tflint 0.66.0
present: `ruff check .` clean at `py310`, `ruff format --check .` clean on the 100 Python files,
1,697 pins in 52 modules, all pass, no skips, 360.33 s, and `python3 tools/check_documents.py`
reports no finding, read at 6.20 s. The count is unchanged, so no pin was added, removed, or
weakened (AC-3.3). The check reads the committed README as 26 findings and the fixed README as none,
so the finding it was written for is measured by the check itself (AC-2.3). The same 1,697 pins in the
same 52 modules passed in 299.71 s on the run before the final document wrapping, so the wrapping
changed no pin.
