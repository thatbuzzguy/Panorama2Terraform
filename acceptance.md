# Acceptance criteria

This file carries the record for each active task, joined by hand at each merge. Each section names the worktree or
branch that owns it. The Piece 13A.3 record is main's, the current task on main. The Epic 14 record is a pointer:
that epic still has open pieces in `to-do.md`, and its criteria are not restated here.

## Piece 13A.3, the committed fixture pair (main, the current task on main)

Piece 13A.3 of Epic 13, the shapes an input can be. The criteria cover the two committed fixtures that show the two
config shapes and the pins that state the printed fixture set, and nothing else. The design record is
`docs/INPUT_SHAPES.md`, whose §1 fact 3 states the two shapes and whose §3 rules hold the shape table.

Out of scope, and not pinned here: the Phase 13B archive producer and its pins, the two open `docs/INPUT_SHAPES.md`
§2 decisions, the 10.2 documentation comparison leg (13A.4), the splitter diagnostic behaviour Piece 13A.2 wrote,
and `docs/LICENSING.md` counts. The pair is test material, not a module, so the document indexes, the §1 module
table and the license counts do not move.

The read rule is `src/xml_input.py`'s F3.8 rule, read through `tests/conftest.py::corpus_fixtures` and through the
tool's own `refusal_reason`. The pair adds no row to `src/input_shapes.py` (rule 7), so this piece changes no `src/`
file.

### Criteria

1. The pair is two committed files under `tests/fixtures/`. `tests/fixtures/panorama_shape.xml` shows the Panorama
   export shape: the config root with one `device-group` entry, one `templates` entry and one `template-stack` entry.
   `tests/fixtures/firewall_shape.xml` shows the firewall export shape: one `devices/entry` with no device-group row.
   Each file holds the smallest content that shows its shape, so it shows the shape and nothing else.
2. Each half enters the read set through the rule and not through a name. The F3.8 rule accepts both files, so both
   enter the set the corpus pins read and the set the fixture assembler merges. The tool names no fixture in its
   source except its own record, and it writes no file, so a name cannot put a file in the merge set and a run cannot
   change the record the goldens read.
3. The shape is read from the bytes. The pin reads each half's shape through the two owners the shape table names for
   it (`split_device_groups.parse_device_groups` and `split_device_groups.tree_shape`), so it states no shape rule of
   its own, and it reads the same bytes under the other half's name, so nothing in the pair's file names decides its
   shape.
4. The pair adds no row to the shape table, and no row's `measured_through` names a pin that reads a committed
   fixture: the two rows that show the two shapes stay measured through `xml_input.parse_bytes`, and no row names a
   file name, an extension, or a committed fixture. No invented row is added for a pending decision.
5. Every pin that states the printed fixture set moves in the same commit as the pair, and each states the value the
   rule answers: `tests/test_build_kitchen_sink.py`, `tests/test_api_requests.py`, `tests/test_policy_order.py`,
   `docs/ARCHITECTURE.md` §5.1, and `backlog.md`. Measured 2026-11-24 through the read rule on the tree that holds
   the pair: 72 files under `tests/fixtures/`, 69 accepted, 68 read, 3 skipped.
6. The pair holds the smallest content that shows each shape, so the corpus pins measure the new count with no new
   finding. Measured 2026-11-24: the container coverage rule, the round-trip rule, the ownership set, the
   reference-edge set, the policy order rule and the entry coverage pins answer for the pair as they answer for the
   other accepted fixtures, no pin table gained a row, and the gate reads no FAIL finding for either half. The two
   runs write 14 `.tf` files through `conftest.tf_files`: 12 for the Panorama half, one set per unit its three
   entries name, and 2 for the firewall half, where the device entry names a unit that writes no scope block. The
   record still holds 17 comment blocks and 13 entry names no accepted fixture carries, so the pin that holds that
   the tool is not a pin on the record did not move.
7. `tests/` stays flat and `tests/conftest.py` stays the only shared helper, so no test module imports another test
   module, and the new pins read the pair through `conftest.py` and the tool through `importlib` on the path
   `conftest.py` builds. The new material does not break the index rule
   (`tests/test_layout.py::test_the_indexes_name_every_document_under_them`).
8. The gate stays green on the tree that holds the piece, measured single-threaded and conservatively:
   `ruff check .`, `ruff format --check .`, `python3 tools/check_documents.py`, `python3 -m pytest`, one process, no
   parallel plugin. The Piece 13A.2 baseline was 1,832 passed and 4 `tflint` skips, so 1,836 pins in 55 modules, in
   385.6 s. Measured 2026-11-24 on the tree that holds the pair: `ruff check .` clean at `py310`,
   `ruff format --check .` clean on the 112 files it reads (82 Python, 30 markdown),
   `python3 tools/check_documents.py` reports no finding, and `python3 -m pytest` in one process exits 0 with 1,835
   passed and the same 4 `tflint` skips, so 1,839 pins in 55 modules, in 278.5 s. The count moved by 3: the pin this
   piece adds, and the 2 cases the `tests/test_sanity_gate.py` fixture parametrization gains for the two accepted
   fixtures.

### Definition of done

The two committed files show the two shapes, the read rule accepts both by rule, the pins read each shape from the
bytes and not from the file name, the shape table gains no row, every pin that states the printed fixture set carries
the measured value, the corpus pins gain no finding, and the gate is green on the tree that holds the piece. Piece
13A.3 is then removed from `to-do.md`, leaving Piece 13A.4 and the Phase 13B pieces.

Complete on main, 2026-11-24, in one commit with the tracking markdown. `to-do.md` now lists Piece 13A.4 for Epic 13,
and this file is overwritten with the Piece 13A.4 criteria when that piece starts.
