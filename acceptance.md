# Acceptance criteria

This file carries the record for each active task, joined by hand at each merge. Each section names the worktree or
branch that owns it. The Piece 11C.3 record is main's, the current task on main. The Epic 13 and Epic 14 records are
pointers: both epics still have open pieces in `to-do.md`, and their criteria are not restated here.

## Piece 11C.3, the write boundary (main, the current task on main)

Piece 11C.3 of Epic 11, the codebase several runs write into. The criteria cover the three rules of
`docs/MULTI_RUN_CODEBASE.md` §6 and nothing else. Decision 3 of the epic is the shape this piece pins: the run
overwrites the files it owns in a unit directory it wrote into, names the units it wrote in its report, and holds no
record of what it wrote before, so the byte difference between two runs is read through git.

Out of scope, and not pinned here: the move fact, the stale-file boundary, the selection for a `vsys` or a device
unit, the `--prune-cache` consequence, and the half that writes the merged record at the root, which is the exit-code
condition recorded in `backlog.md`. This piece changes no behaviour, so no pin reads a gate result or an exit code.

The owner is `src/write_path.py`, the single writer, and the pins are in `tests/test_write_path.py`. No new `src/`
module and no new test module, so the §1 module table and the root index change only in the wording that names the
rules.

### Criteria

1. Each rule the piece states names its owner and its pin. The rules are: the run set rule, already landed as rule 4
   of `write_path.py` and already pinned; the overwrite rule; the delete rule; the ownership rule; the no-record rule.
   Each names `write_path.py` as its owner and one pin in `tests/test_write_path.py`, and no rule is stated in a
   second module.
2. The overwrite rule pins that the writer replaces the bytes for a file shape this run has content for, inside the
   unit directory its own set names, and that a shape it has no content for is not written, so the bytes an earlier
   run wrote for that shape stay. Measured on the committed pair, `tests/fixtures/kitchen_sink.xml` as the codebase
   and `tests/fixtures/address_objects.xml` as the second run: the second run's own unit is `shared_45ca31c3`, the
   first run wrote 12 files inside it, the second run wrote the 3 shapes it has content for, and `address_objects.tf`
   is the file whose bytes differ. The pin compares the files the second run wrote against a solo run of the same
   fixture and holds that they agree byte for byte, so the run wrote what it built.
3. The delete rule pins that a run removes nothing: every file present before the run is present after it, at the
   codebase root and inside every unit directory, including a unit it read only through the record. The write path
   holds no file-removal call, and the only file removal in `src/` is `provenance.prune`, which acts on cache entries
   outside the two sets. The pin reads the `src/` set as calls and not as words, so the module that owns the rule can
   state it in prose.
4. The ownership rule pins that the two sets are the files the tool owns, and that a file outside them is not the
   tool's: a run writes no file outside the two sets and does not touch one. Measured with an operator
   `terraform.tfvars` in the codebase root: a run leaves it byte for byte as the operator wrote it. `write_path.py`
   names no file, and the printed form's name is read through `site_data.TFVARS_FILE`, so the piece states no second
   file-name rule; the operator-file rule stays with `docs/CODEBASE_ASSEMBLY.md` §11.
5. The no-record rule pins that the tool holds no record of what it wrote: no record shape names a run, a writer, or
   a timestamp, read through each record module's declared field set; `SOURCE.txt` names what the door read and names
   no file inside the output tree; and the module that owns the writer names no file. The git half of the rule is a
   document rule, so no pin runs git.
6. The pins run offline on committed material through `tests/conftest.py`, and no pin calls a network or a binary.
7. No committed golden moves and no committed bytes change, because no behaviour changes.
8. The document rules hold: `docs/MULTI_RUN_CODEBASE.md` §6 names each rule's owner and its pins,
   `docs/ARCHITECTURE.md` §1 names the rules `write_path.py` keeps, and `README.md` §Testing names what
   `tests/test_write_path.py` pins. No document states a test count, and `python3 tools/check_documents.py` reports
   no finding on the final tree. The three exact phrases the script reads are not changed.
9. The gate is measured single-threaded and conservatively: `ruff check .`, `ruff format --check .`,
   `python3 tools/check_documents.py`, `python3 -m pytest`, one process, no parallel plugin. The Piece 12A.3 baseline
   is 1,796 passed and 4 `tflint` skips, so 1,800 pins in 54 modules. This piece adds five pins, all in
   `tests/test_write_path.py`.

### Definition of done

The five write-boundary rules each name `write_path.py` as their owner and one pin in `tests/test_write_path.py`, the
pins run offline on the committed pair and hold, no behaviour and no committed byte changes, the documents name the
pins, and the gate is green on the tree that holds the piece. Epic 11 then closes, so the Epic 11 piece list is
removed from `to-do.md` and the Epic 11 planning section from `PLAN.md`, leaving the facts that moved to
`backlog.md`.

## Epic 13, the shapes an input can be (the `input-shapes` worktree)

Pointer. The design record is `docs/INPUT_SHAPES.md`, the pieces are in `to-do.md` §Epic 13, and the live facts are in
`backlog.md`. The criteria this file held for that worktree are in `d4996b5`; they are not restated here, and no piece
of Epic 13 is open on main for this task.

## Epic 14, the blocks a run binds to the live config (the `import-pairing` worktree)

Pointer. The design record is `docs/IMPORT_BINDING.md`, the pieces are in `to-do.md` §Epic 14, the decisions are in
the record §2, and the live facts are in `backlog.md`. The criteria this file held for that worktree are in `0b917e7`;
they are not restated here. No decision is taken, so no piece can be written from one yet, and no `src/` file is
touched until a piece lands.
