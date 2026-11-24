# Acceptance criteria

This file carries the record for each active task, joined by hand at each merge. Each section names the worktree or
branch that owns it. The Piece 13A.2 record is main's, the current task on main. The Epic 14 record is a pointer:
that epic still has open pieces in `to-do.md`, and its criteria are not restated here.

## Piece 13A.2, the splitter diagnostic (main, the current task on main)

Piece 13A.2 of Epic 13, the shapes an input can be. The criteria cover the line the splitter prints for the shape it
read and the pins that read the printed set, and nothing else. The design record is `docs/INPUT_SHAPES.md`, whose §4
is the diagnostic rule and whose §3 rules hold the shape table.

Out of scope, and not pinned here: the Phase 13B archive producer, the committed fixture pair (13A.3), so the
fixture-count pins do not move, the 10.2 documentation comparison leg (13A.4), the two open §2 decisions, and any
change to an exit code.

The owner of the printed line is `src/split_device_groups.py`, the module that reads its own row set, and the owner of
the line shape is `container_coverage.console_line`, which this piece does not change. The pins are in
`tests/test_split_device_groups.py` and `tests/test_input_shapes.py`; the console-line shape pin in
`tests/test_container_coverage.py` names the modules that call the shape, so it moves in the same commit. No new
module is added, so the indexes, the §1 table and the license counts do not move.

### Criteria

1. The printed fact names three parts and nothing else: the row count of `device-group/entry` rows the run read, the
   shape the tree holds instead, and the source line the read layer records for the entry that shows the shape. The
   fact names one position, one identity and one fact, so it prints through `container_coverage.console_line`, which
   is the one place the shape is stated; the report branch applies only to a fact that compares two sets, and this
   fact does not. The splitter writes no report, so the console line is the only path for it.
2. The splitter defines no rule of its own. It reads the byte rule from `write_path.py`, the name rule from `naming.py`
   §5, the key rule as the source line, and it owns its output path. For the printed fact it states its own fact
   phrase and its own block header and calls the shape, so it builds no prefix, defines no second shape, and states no
   lookup rule beyond the row rule and the walk rule it already states: the walk enters the container and stops at the
   entry, and an entry keeps the path it sits at.
3. A part the run cannot name is the honest statement, not a guess. The position part is
   `container_coverage.position_part` for a finding with no line, and the identity part is the module's own statement
   for a tree that holds no entry at any path, read through `container_coverage.CONSOLE_WARNING`. A block prints only
   when it has a finding, so a run that read rows prints nothing new.
4. The exit code does not change. The exit code stays with the rules that read the files (`docs/ARCHITECTURE.md`
   §4.6), so a run that reads no `device-group/entry` row still exits 1, and a refusal still prints through the read
   layer's own print site.
5. The pins that read the printed set move in the same commit: the console-line shape pin names the splitter as a
   module that calls the shape, and the shape table row for the splitter moves from pending to held because the line
   now exists. The held row is measured by running the row's content through the owner the row names, so the pins read
   the row through `split_device_groups` and compare the printed line with the row. The row holds no console prefix,
   because the prefix is the part `container_coverage` states, so the pin reads the prefix through that owner. The
   held, accepted and pending counts in the pins move with the row, and the pending set is the two open §2 decisions.
6. The documents link to the table and restate no row. The troubleshooting rows name the shape and describe what the
   run prints without quoting the line, which `tools/check_documents.py` reads. `docs/ARCHITECTURE.md` §3.2 names the
   kinds that print, and `docs/INPUT_SHAPES.md` §4 states the parts and which path the fact takes.
7. The gate stays green on the tree that holds the piece, measured single-threaded and conservatively: `ruff check .`,
   `ruff format --check .`, `python3 tools/check_documents.py`, `python3 -m pytest`, one process, no parallel plugin.
   The Piece 13A.1 baseline was 1,829 passed and 4 `tflint` skips, so 1,833 pins in 55 modules. Measured 2026-11-24 on
   the tree that holds this piece: `ruff check .` clean at `py310`, `ruff format --check .` clean on the 112 files it
   reads, `python3 tools/check_documents.py` reports no finding, and `python3 -m pytest` in one process exits 0 with
   1,832 passed and the same 4 skips, so 1,836 pins in 55 modules, in 385.6 s. The 3 pins this piece adds are the
   count, recorded in `agent-status.md`.

### Definition of done

The run prints the fact it read through the console-line owner, with the three parts measured through the owners that
state them, no second shape and no second rule; the shape table row is held and measured through its own owner; the
pins that read the printed set name the splitter; the documents link to the table and restate no row; the exit code is
unchanged; and the gate is green on the tree that holds the piece. Piece 13A.2 is then removed from `to-do.md`,
leaving the pieces that need a decision or a fixture.

Complete on main, 2026-11-24, in one commit with the tracking markdown. `to-do.md` now lists Piece 13A.3 and Piece
13A.4 for Epic 13, and this file is overwritten with the Piece 13A.3 criteria when that piece starts.

## Epic 14, the blocks a run binds to the live config

The criteria are not restated here; the record is `docs/IMPORT_BINDING.md` §2 and the pieces are in `to-do.md`. This
section is the pointer `AGENTS.md` asks for, so the file carries one record per active task.
