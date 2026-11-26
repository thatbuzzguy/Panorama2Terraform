# Acceptance criteria

This file carries the record for the current task. Piece 13C.1 is committed at `cadd33a` and the writing-rules
piece at `077cdce`, so their records live in the git history and are not restated here. The epic records stay as
pointers: Epic 13's rules are in `docs/INPUT_SHAPES.md`, and Epic 14's criteria are not restated here because that
epic still has open pieces in `to-do.md` and its decisions are in `docs/IMPORT_BINDING.md` §2.

## Piece 14A.1, the two mode values and the level the mode sits at (main, the current task)

Decision 1 of `docs/IMPORT_BINDING.md` §2, taken 2026-11-25: the mode stops at the unit, and the two values each
name the plan outcome for one unit. One goal: record the decision as taken, and state the pair and the level as data
with the pins that read them as data. Decision 2 is untaken, so the piece states no record field, moves no row
shape, and moves no committed byte of data.

### Criteria

1. `docs/IMPORT_BINDING.md` §2 decision 1 records the decision as taken, with the date 2026-11-25, the facts it
   settles (the pair, the level, and that the decision takes no field), the module it names as the owner of the
   data, and the pins that hold it named. The §2 line that states no decision is taken is changed so that decision
   1 is named as taken and the rest stay untaken.
2. Decision 2 stays untaken. The piece states no record field for the mode, does not change
   `unit_manifest.FIELD_ORDER` or any other row shape, and moves no committed data file and no golden. The value a
   run with no mode prints is not guessed here.
3. The pair and the level are data in `src/import_blocks.py`, the owner decision 1 names, for these reasons: that
   module already holds the binding decision as data (`RULE_DECISION`), owns the block shape and the row shape, and
   defines no unit rule and no naming rule, so a data constant there adds no row field and moves no committed byte.
   `unit_manifest.py` is not the owner, because its row shape is what decision 2 decides. The choice is stated in
   the module comment and in `docs/README.md` §Who owns each rule.
4. The pins read the pair and the level as data through the owner, and not through document wording. They hold:
   the pair has two members and reads as `imported` and `added`; the level is the unit identity the one unit rule
   answers, so it is the unit field the manifest row states and not one of the five scope facts, and no entry level
   is named; no row shape names a field for the mode, so a run writes no key for it; and the owner states no unit
   rule, no level rule and no mode reader of its own, and no module holds the pair or the level a second time.
5. The pins run the pipeline in process and read each row shape through the module that owns it, so no test module
   states a shape rule, a unit rule or a file set of its own, and no test module imports another test module
   (`docs/ARCHITECTURE.md` §1.1).
6. No document restates the data. `docs/README.md` names the owner, and `docs/IMPORT_BINDING.md` names the owner
   and the pins. A pin measures content or a name, so a wording check stays in `tools/check_documents.py`, which the
   test set does not read.
7. ASD-STE100, no marketing voice, no emoji, and no test count in a document.
8. The gate is measured single-threaded: `ruff check .`, `ruff format --check .`,
   `python3 tools/check_documents.py`, and `python3 -m pytest -p no:cacheprovider` in one process with no parallel
   plugin. The answer must agree with the baseline the piece starts from: 1,861 pins in 55 test modules (1,857
   passed and the same 4 `tflint` skips). This piece adds 4 pins in `tests/test_import_blocks.py`, so the expected
   answer is 1,865 pins in 55 test modules, and the file count the format check reads cannot move because no file
   is added. Every count that moves is recorded.
9. The tracking markdown is updated: `agent-status.md` Current position for this piece, `to-do.md` for the piece,
   and `backlog.md` for the half that stays blocked on decision 2 and fact 11 and for the pair that has no reader
   yet. The two open process-debt pieces stay open, and all the untaken Epic 14 decisions stay. Piece 14A.2 stays
   blocked on decision 2 and fact 11.
10. The piece is committed in the conventional-commits style with the completion history in the body, in the shape
    of `git log -1 --format=%B`, as `commit.md` states. Nothing is pushed. If the data cannot be placed without a
    row shape moving, the reason is recorded in `backlog.md` instead of being guessed.

### Out of scope

- Decision 2, the mode's owner as a record field and the value a run with no mode prints. Decision 3, the
  declaration argument. The report section that names the units a run bound. The rule types (decision 7). The
  whole-block fact (decision 4). The completeness half (decision 5). The device fact, the read-through order and
  permanence. No piece that needs an untaken decision is written.
- No `src/` module is added, so `tools/check_documents.py` check 3 reads the same `src/` module count the document
  names, and no golden, no fixture and no `docs/LICENSING.md` count changes.
- No gate rule, no report rule and no writer changes: the mode has no reader until decision 2 or decision 3 lands.

### Definition of done

Decision 1 is recorded as taken in `docs/IMPORT_BINDING.md` §2 with the date, the facts it settles, the owner it
names and the pins named. The pair and the level are data in `src/import_blocks.py`, and the pins read them as data
and hold that no module states a record field for the mode, a second unit rule or a second level. No row shape and
no committed data file moves. The gate answers with no finding: `ruff check .` clean, `ruff format --check .` clean
on the same 113 files, `python3 tools/check_documents.py` reports no finding, and
`python3 -m pytest -p no:cacheprovider` in one process with no parallel plugin exits 0 with 1,865 pins in 55 test
modules. Every count that moves is recorded here, the tracking markdown is updated, and the piece is committed in
the conventional-commits style with the completion history in the body. Nothing is pushed.
