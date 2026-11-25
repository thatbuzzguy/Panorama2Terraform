# Acceptance criteria

This file carries the record for the current task. Piece 13C.1 is committed at `cadd33a` and the writing-rules
piece at `077cdce`, so their records live in the git history and are not restated here. The epic records stay as
pointers: Epic 13's rules are in `docs/INPUT_SHAPES.md`, and Epic 14's criteria are not restated here because that
epic still has open pieces in `to-do.md` and its decisions are in `docs/IMPORT_BINDING.md` §2.

## Piece, the five pins read the committed pair through the constants (main, the current task)

The process-debt item in `backlog.md` named "The committed pair is stated once as constants, but five pins name it
inline". One goal: the five pins read the pair through the constants `tests/conftest.py` owns. Nothing else moves.

The five pins, named by the test that holds them:

- `tests/test_data_file_gate.py::test_the_data_rule_reads_the_merged_record_as_the_codebase_set`
- `tests/test_round_trip.py::test_the_block_side_is_read_inside_the_run_s_unit_set`
- `tests/test_sanity_gate.py::test_the_block_rules_read_the_whole_codebase_for_a_partial_run`
- `tests/test_sanity_gate.py::test_the_two_command_checks_run_once_per_directory_the_run_wrote`
- `tests/test_sanity_gate.py::test_a_partial_run_exit_code_follows_the_rules_that_read_the_files`

### Criteria

1. Each of the five pins calls `tests/conftest.py::partial_run` with `CODEBASE_FIXTURE` and `RUN_FIXTURE` and
   states no name of the pair inline. The fifth pin also builds the argv for the entry point from the second
   fixture of the same pair; that name is part of the pair this pin reads, so it reads through `RUN_FIXTURE` as
   well.
2. `CODEBASE_FIXTURE` and `RUN_FIXTURE` are added to the import set of each of the three modules. No test module
   defines a pair of its own, and no test module imports another test module (`docs/ARCHITECTURE.md` §1.1). The
   rule that `tests/conftest.py` is the one place the path to each set is built stays where it is, in
   `tests/conftest.py` and `docs/ARCHITECTURE.md` §1.1, and does not move into a test module.
3. `tests/conftest.py::partial_run` still takes the two names as arguments and states no fixture name of its own,
   so the pins read the pair through the constants and the helper stays the pattern, not the names.
4. A pin that names a fixture for its own fact, and not for the pair the pattern names, is unchanged. The three
   modules hold fixture names of their own for their own facts, so the piece reports what it found and changes
   nothing that is not one of the five pins.
5. No pin reads a test module's wording, so this change cannot trip a pin that reads names. The piece checks that
   no pin in these three modules reads a test module source for a fixture name, and reports what it finds; a pin
   that reads a `src/` module source is not affected, because no `src/` file changes.
6. A docstring that states the two fixture names as prose stays as it is unless the code now contradicts it, and
   the piece says what it found.
7. The gate is measured single-threaded: `ruff check .`, `ruff format --check .`,
   `python3 tools/check_documents.py`, and `python3 -m pytest -p no:cacheprovider` in one process with no parallel
   plugin. The full run is the gate and takes 5 to 8 minutes, so it runs in the background. The answer must agree
   with the baseline the piece starts from: 1,857 passed and the same 4 `tflint` skips, so 1,861 pins in 55 test
   modules. This piece adds no pin, so the pin count cannot move. Every count that moves is recorded.
8. The tracking markdown is updated: `agent-status.md` Current position for this piece, `to-do.md` and
   `backlog.md` for the item, which is closed when the pins read the constants and so is removed from
   `backlog.md`. The two open process-debt pieces the previous piece recorded stay open. No Epic 14 piece moves:
   the decisions in `docs/IMPORT_BINDING.md` §2 are untaken, so Piece 14A.1 stays blocked on decision 1. No
   decision is taken by this piece.
9. The piece is committed as a `test` commit with the completion history in the body, in the shape of
   `git log -1 --format=%B`, as `commit.md` states. Nothing is pushed.

### Out of scope

- No `src/` file, no fixture, no golden and no `docs/LICENSING.md` count changes, so no pin, no rule and no
  document rule moves for this piece.
- A fixture name a pin holds for its own fact is not the pair the pattern names, so those names stay where they
  are. Moving them would be a different piece.
- The names of the two documents the open process-debt pieces need stay open decisions that measurement cannot
  answer, and no decision in `docs/IMPORT_BINDING.md` §2 is taken.
- No pin is added. A pin that reads a test module for its own names would be a new pin, which this piece does not
  write.

### Definition of done

The five pins read the pair through the constants `tests/conftest.py` owns, the three import sets name the two
constants, no test module defines a pair of its own, the import rule holds, and the gate answers with no finding:
`ruff check .` clean, `ruff format --check .` clean, `python3 tools/check_documents.py` reports no finding, and
`python3 -m pytest -p no:cacheprovider` in one process with no parallel plugin exits 0 with the same pin count as
the baseline. Every count that moves is recorded here, the tracking markdown is updated, the item is closed in
`backlog.md`, and the piece is committed in the conventional-commits style with the completion history in the
body. Nothing is pushed. If a pin cannot read the constants, the reason is recorded in `backlog.md` instead of
being guessed.

### Measured result, 2026-11-25

Gate, single-threaded on the tree that holds this work: `ruff check .` clean at `py310` with the 120-character line
length. `ruff format --check .` clean on 113 files, the same 113 as the baseline, because no file was added.
`python3 tools/check_documents.py` reports no finding, in 8.91 s. The fast path answered 1 passed in 0.56 s for
`tests/test_layout.py`. The full run, `python3 -m pytest -p no:cacheprovider` in one process with no parallel
plugin, exits 0 with 1,857 passed and the same 4 `tflint` skips, so 1,861 pins in 55 test modules, in 378.12 s. `tflint`
is absent on this machine, so the four skips are the four `tflint` pins in `tests/test_sanity_gate.py`, and
`terraform` is present, so the provider-schema pins ran. The counts did not move: the piece adds no pin, and the
five pins are the same five pins read a different way. `python3 -m pytest --collect-only -q` names 55 test modules
and 1,861 pins on the tree before the change and on the tree that holds it, so the pin count is confirmed.

Document review, criterion by criterion. Criterion 1, the five pins read the pair through the constants, and the
fifth pin's argv line reads it through `RUN_FIXTURE`, which is the extra line this piece changed inside that pin.
Criterion 2, the three import sets name both constants, no test module defines a pair of its own for the pattern,
no test module imports another test module, and the rule that `tests/conftest.py` is the one place the path to each
set is built stayed in `tests/conftest.py` and `docs/ARCHITECTURE.md` §1.1. Criterion 3, `partial_run` takes the two
names as arguments and states no fixture name of its own. Criterion 4, the names the three modules hold for their
own facts are reported in `backlog.md` and were not changed. Criterion 5, no pin in these three modules reads a test
module source, so nothing that reads names can move; the pins in these three modules that read a source read
`sanity_checks.py`, and `tests/test_layout.py` reads names, which agrees before and after the change. Criterion 6,
the prose that states the fixture names is the measurement the pins read, and no docstring contradicts the code, so
the prose stays. Criterion 7, the counts above, and no count moved. Criterion 8, the tracking markdown is updated,
the item is closed, the two open process-debt pieces stay open, and no Epic 14 piece moved. Criterion 9, the piece
is committed as a `test` commit. No decision was taken by this piece, and no document-review finding was opened by
it. Nothing is pushed.
