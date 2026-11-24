# Acceptance criteria

This file carries the record for each active task, joined by hand at each merge. Each section names the worktree or
branch that owns it. The Piece 13A.1 record is main's, the current task on main. The Epic 14 record is a pointer:
that epic still has open pieces in `to-do.md`, and its criteria are not restated here.

## Piece 13A.1, the shape table (main, the current task on main)

Piece 13A.1 of Epic 13, the shapes an input can be. The criteria cover the shape table and nothing else. The design
record is `docs/INPUT_SHAPES.md`, whose §3 moves from planning to rules with this piece.

Out of scope, and not pinned here: the archive producer (`to-do.md` Phase 13B), the splitter diagnostic (13A.2), the
committed fixture pair (13A.3), and the two open §2 decisions. No fixture is added, so the fixture-count pins do not
move.

The owner is `src/input_shapes.py`, the module that states the table as data, and the pins are in
`tests/test_input_shapes.py`. Both are new, so the module must be named in the `docs/ARCHITECTURE.md` §1 table and the
test module in `README.md` §Testing in the same commit, which
`tests/test_layout.py::test_the_indexes_name_every_document_under_them` holds. The module states no check, no reader,
no writer, no console line, no naming rule and no environment name, so the `src/` scans read it with the other
modules.

### Criteria

1. One table, in one owner module. Each row states the byte shape, the entry point that accepts it, the line the run
   prints for it, the status, and the decision a pending row waits for. The row shape is `SHAPE_ROW_FIELDS`, the
   `docs/ARCHITECTURE.md` §1 rule column names it for `input_shapes.py`, and `tools/check_documents.py` reads the row
   shape through the SHAPES list.
2. The module states no rule an owner states. It defines no size check, no DTD check, no reader, no parser, no
   writer, no print, no console line, no naming rule and no environment name. The two byte checks stay
   `xml_input.check_bytes`, and the refusal wording stays with the module that builds it, so the table holds each line
   as the measured wording of its owner, and a pin holds the agreement: the pin builds the refusal through the owner
   and compares it with the row.
3. A pin measures each row, so the table cannot drift from the tool. For a refused row, the pin runs the door on the
   row's content and holds that the door refuses it with the wording the row states, and that the run prints that
   wording at the entry point the row names. For an accepted row, the pin runs the same read rule through
   `tests/conftest.py::input_refusal` and holds that it answers no refusal, so the row states no line.
4. The shape is read from the bytes. The pins decide acceptance from the row's content through the shared read rule,
   not from a file name, and no row names a file name, an extension or a fixture. The pin measures the DTD row's
   content in an encoding the parser decodes, so the row's answer does not depend on a text search.
5. A pending row states no line, because no line exists for it yet. The pending rows are the two open §2 decisions
   and the splitter diagnostic line, which is pending Piece 13A.2. The pins hold that a pending row states no line,
   names the decision or the piece it waits for, and that no entry point reads its content today.
6. The documents link to the table and restate no row. `docs/INPUT_SHAPES.md` §3 states the table as rules that name
   `input_shapes.py`, `README.md` and `docs/README.md` link to it, and no document holds a row's line wording. The
   document-review check for this is in `tools/check_documents.py`, because a pin measures a name and not a wording.
7. The gate stays green on the tree that holds the piece, measured single-threaded and conservatively: `ruff check .`,
   `ruff format --check .`, `python3 tools/check_documents.py`, `python3 -m pytest`, one process, no parallel plugin.
   The Piece 11C.3 baseline is 1,801 passed and 4 `tflint` skips, so 1,805 pins in 54 modules; the pins this piece
   adds move the counts, which are recorded in `agent-status.md`.
8. The counts `docs/LICENSING.md` states for the notice set are read from the working tree, so the module count moves
   with a new `src/` module in the same commit. No notice is added: the document is the authority for a module with
   no upstream line.

### Definition of done

The table has one owner module and is read as data by the pins, every held row is measured against the door or the
shared read rule, every pending row is marked pending in the table, the document and the pins, the documents link to
the table and restate no row, the new module and the new test module are named by the indexes and the §1 table, and
the gate is green on the tree that holds the piece. Piece 13A.1 is then removed from `to-do.md`, leaving the pieces
that need a decision or a fixture.
