# Acceptance criteria

This file carries the record for the current task. Piece 13C.1 is committed at `cadd33a`, so its record lives in the
git history and is not restated here. The epic records stay as pointers: Epic 13's rules are in
`docs/INPUT_SHAPES.md`, and Epic 14's criteria are not restated here because that epic still has open pieces in
`to-do.md` and its decisions are in `docs/IMPORT_BINDING.md` §2.

## Piece, the writing rules with an owner document (main, the current task)

The process-debt entry in `backlog.md` named "Permanent rules have no owner document", the writing rules half. The
piece moves the writing rules out of `agent-status.md` into `docs/WRITING_RULES.md`, a new owner document, and
`agent-status.md` keeps the status and the links. One goal: the writing rules. The gate and CI rules and the shape
table and write-path watch list stay in `agent-status.md` for this piece and stay open in `backlog.md`.

### Criteria

1. `docs/WRITING_RULES.md` is the owner of the writing rules. The document states that it is the owner and that the
   other documents link to it, and `agent-status.md` keeps the status and the links and holds no writing rule of its
   own. The file name follows the plain, literal style of the other `docs/` files.
2. The new document is named by `docs/README.md`, which owns the rule that each rule lives in one document and names
   every document under `docs/`, and by the root index, `README.md`. `docs/README.md` gains the index row and the
   ownership row, and `README.md` gains the link in its Documentation section.
3. The writing rules separate cleanly from the gate and CI rules, or the piece says where one sentence covers both
   and does not split the rule. A writing rule states what a document may hold; a gate rule states what a run
   measures. The writing rule that a wording check lives in `tools/check_documents.py`, which the test set does not
   read, is part of the writing rules and moves with them, and the gate document a later piece writes links to it.
   The piece records this in `backlog.md`.
4. `backlog.md` records that the gate and CI rules and the watch list stay open and states which document each will
   need. The choice of those two names is a decision that measurement cannot answer, so it is recorded as an open
   item and not guessed.
5. `docs/WRITING_RULES.md` holds no test count, which check 5 of `tools/check_documents.py` reads, no test name
   that does not exist, which check 1 reads, no restatement of a machine-readable table, which check 7 reads, no
   wording that check 7 reads from a shape-table row's `printed_line`, and no claim about what the tool does that
   names no module or test. It is in ASD-STE100 Simplified Technical English, with no marketing voice and no emoji.
6. Nothing in `src/` or in `tests/` changes, so no pin, no fixture, no golden and no `docs/LICENSING.md` count
   moves. `tests/test_layout.py` is the pin that can move, because a new file under `docs/` is a markdown edit that
   the index rule reads, and it passes when `docs/README.md` names the file. The pin that holds the index rule is
   `tests/test_layout.py::test_the_indexes_name_every_document_under_them`.
7. The gate is measured single-threaded: `ruff check .`, `ruff format --check .`,
   `python3 tools/check_documents.py`, and `python3 -m pytest -p no:cacheprovider` in one process with no parallel
   plugin. The full run is the gate and takes 5 to 8 minutes, so it runs in the background and the answer must agree
   with the Piece 13C.1 baseline: 1,857 passed and the same 4 `tflint` skips. The files `ruff format --check .`
   reads can move, because it reads markdown. Every count that moves is recorded.
8. The tracking markdown is updated: `agent-status.md` Current position for this piece, `to-do.md` for the open
   process-debt pieces, `backlog.md` for the open rule sets, and this file for the measurements. No Epic 14 piece
   moves: the decisions in `docs/IMPORT_BINDING.md` §2 are untaken, so no Epic 14 piece can be written, and
   Piece 14A.1 stays blocked on decision 1.
9. The piece is committed as a `docs` commit with the completion history in the body, in the shape of
   `git log -1 --format=%B`, as `commit.md` states. Nothing is pushed.

### Out of scope

- The gate and CI rules and the watch list stay in `agent-status.md` for this piece, because one goal is one piece.
  `backlog.md` records them open with the document each needs.
- No decision is taken for the names of the two open documents, so no piece can be written from a decision, and
  nothing here is written from a decision.
- This piece writes no code, no new test module and no fixture. A wording check is a document review and not a pin,
  so nothing in the test set moves for this piece.

### Definition of done

The writing rules are stated once, in their owner document, both indexes name the document, `agent-status.md` holds
the status and the links, `backlog.md` holds the open rule sets with the document each needs, and the gate answers
with no finding: `ruff check .` clean, `ruff format --check .` clean, `python3 tools/check_documents.py` reports no
finding, and `python3 -m pytest -p no:cacheprovider` in one process with no parallel plugin exits 0. Every count
that moves is recorded here, the tracking markdown is updated, and the piece is committed in the
conventional-commits style with the completion history in the body. Nothing is pushed.

### Measured result, 2026-11-25

Gate, single-threaded on the tree that holds this work: `ruff check .` clean at `py310` with the 120-character line
length. `ruff format --check .` clean on 113 files, which is the 112 of the Piece 13C.1 baseline plus this piece's
new document, so that count moved. `python3 tools/check_documents.py` reports no finding, in 13.26 s, and the new
document passes its checks 1, 5 and 7. The fast path answered 1 passed in 0.62 s for `tests/test_layout.py`. The
full run, `python3 -m pytest -p no:cacheprovider` in one process with no parallel plugin, exits 0 with 1,857 passed
and the same 4 `tflint` skips, so 1,861 pins in 55 test modules, in 526.48 s; an earlier run of the same suite on
the same tree answered the same counts in 538.64 s. On these runs the terminal writer printed the progress lines and
no summary line, so the counts were read from the progress characters, the four skips being the `tflint` pins, and
confirmed against `python3 -m pytest --collect-only -q`, which names 55 test modules and 1,861 pins. No other count
moved, because nothing in `src/` or in `tests/` changed.

Document review, criterion by criterion: criterion 1, `docs/WRITING_RULES.md` states that it is the owner and that
the other documents link to it, and `agent-status.md` now holds the status and the link. Criterion 2, `docs/README.md`
gained the index row and the ownership row, and `README.md` gained the Documentation link, so both indexes name the
document, which `tests/test_layout.py` reads as names. Criterion 3, the writing rules separated cleanly from the gate
and CI rules; the one sentence that reaches both is the wording-check sentence, which moved with the writing rules,
and this is recorded in `backlog.md`. Criterion 4, the new document holds no test count, names one test,
`tests/test_layout.py::test_the_indexes_name_every_document_under_them`, which exists, restates no table row, and
names a module or a test for every claim about what the checks read. Criterion 5, `backlog.md` records the gate and
CI rules and the watch list open with the document each needs, and the choice of the two names recorded as open
decisions that measurement cannot answer. Criterion 6, nothing in `src/` or in `tests/` changed. Criterion 7, the
counts above. Criterion 8, the tracking markdown is updated and no Epic 14 piece moved.

No decision was taken by this piece. The file name `docs/WRITING_RULES.md` is a plain, literal name in the style of
the other `docs/` files, taken by the piece itself as the item asked; the names of the two open documents stay open
decisions. No document-review finding was opened by this piece. Nothing is pushed.
