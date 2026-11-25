# Acceptance criteria

This file carries the record for the current task. The Piece 13B.4 record below is complete on main, 2026-11-25, and
the next task, Piece 13C.1, has no criteria written yet. The other epic records are pointers: Epic 13's rules are in `docs/INPUT_SHAPES.md`, and Epic 14's criteria are not
restated here because that epic still has open pieces in `to-do.md` and its decisions are in
`docs/IMPORT_BINDING.md` §2.

## Piece 13B.4, the owner for the member rule (main, the current task on main)

Piece 13B.4 of Epic 13, the shapes an input can be. The piece lands decision 4 of `docs/INPUT_SHAPES.md` §2, taken
2026-11-24: one member is accepted, and a bundle that holds more than one member is read only when the operator
declares which member, so with no declaration the run refuses. The piece gives that decision an owner and moves the
shape-table row that names this piece from `pending` to `held` in the same commit.

The declaration is the operator's argument, held by the CLI and not by a rule owner, so this piece states no member
rule the CLI holds instead, and the argument rule states no path rule and no naming rule of its own.

### Criteria

1. `check_bytes` stays the one definition of the two checks, and the checks answer on the bytes a declared member
   expands to, not on the compressed bundle. The pins read the member bytes through the owner that reads the members,
   so the pins hold no shape rule and no content of their own, and no second definition of a size or hash rule
   appears anywhere.
2. `src/input_shapes.py` states no rule as a function, so the refusal wording lives as a literal in the owner and the
   table mirrors it as data. The pins read the wording as data from the table and hold that the table module holds no
   wording builder, and no test module holds archive bytes, a row, or a refusal wording of its own.
3. The refusal shape is the same as the other refusal rows, so the run's printed line for a row that states a
   declaration is the row's own wording with only the measured parts filled in: `{origin}`. The pins read the declared
   member name as row data through `SHAPE_ROW_FIELDS`, which gains the `member` field, and no row states a member
   count the pins cannot read from it. A row that states no declaration states `""`.
4. The pins that measure a refusal line through its owner call the owner with the row's declaration, so no pin
   invents a reader or a declaration of its own, and the pins hold no refusal wording of their own.
5. A declared member the bundle does not hold is refused by the existing rules: the producer reads no member, so the
   bytes reach the door unchanged and the parse answers with the line the table already holds for them, read through
   `xml_input.parse_archive` with the row's declaration. A selection by member order stays refused by the determinism
   rule (`docs/ARCHITECTURE.md` §6), so no rule reads member order, and the pins hold that as an absence.
6. The CLI argument for the declaration is defined in `src/` in the `--max-input-bytes` style and is read through
   `shared_arguments`, so both entry points read one set. The pins hold that the argument states no path rule and no
   naming rule of its own, that it decides nothing an owner decides, that a run declaring no member is refused
   nothing, and that a run reading no bundle is refused nothing by the argument.
7. End-to-end: the pins read the rows as data, run them through the owners the rows name, print the answer through
   the entry points' own print site, and hold that both entry points print the same line for the same bytes, read
   through the argument, that both checks answer on the decompressed bytes through the door, that no producer bypasses
   them, and that the archive path adds a producer and no check. The origin-kind pins move with the producer: a bundle
   refused by the member rule is refused before the door is handed any bytes, so its origin keeps the kind its
   producer states.
8. Every pin that reads the shape-table counts moves in the same commit, and every shape row is data with no file
   name, no extension, and no fixture named. Every document that names a test names an existing test, and no document
   restates a row's wording. The gate is measured single-threaded: `ruff check .`, `ruff format --check .`,
   `python3 tools/check_documents.py`, `python3 -m pytest`, and every count that moves is recorded.

### Out of scope

- A bundle read through the api producer: `source_fetch.fetch()` runs the checks through `parse_bytes` and never
  through the archive producer, so no archive read reaches a cache entry today (`docs/INPUT_SHAPES.md` §1 fact 6). The
  argument names the member for the producer that reads the bundle, so this piece states no cache rule.
- The file form the UI download writes, and whether a bundle can hold more than one XML member on a live target, stay
  in `backlog.md`.
- No new module: `src/` is one flat namespace, `src/` imports nothing from `tests/`, and `src/input_shapes.py` states
  no rule as a function, so the owner sits in `src/xml_input.py` next to `check_bytes` and the table mirrors the
  wording as data.

### Definition of done

The owner, the CLI argument, the rows, the pins, and the documents agree on the measured gate: no finding from
`tools/check_documents.py`, no lint or format finding, and every pin passes on one single-threaded run. The counts
that move are recorded, `agent-status.md`, `to-do.md`, `backlog.md`, and this file are updated, and the piece is
committed in the conventional-commits style with the completion history in the body. Nothing is pushed.

### Measured result, 2026-11-25

Every criterion holds. `ruff check .` is clean, `ruff format --check .` is clean on the 112 files it reads,
`python3 tools/check_documents.py` reports no finding, and `python3 -m pytest` in one process with no parallel plugin
exits 0 with 1,857 passed and the same 4 `tflint` skips, so 1,861 pins in 55 test modules.

The table reads 25 rows: 16 held rows that state a line, 15 of them refusal rows, 1 console line row, 9 accepted
rows, 0 pending rows, and 4 rows read through a declaration. Eight pins are added and two are removed, so the pins
move 1,848 → 1,861. The refusal order is as criterion 7 states it: a bundle with more than one member and no
declaration is refused before the door is handed any bytes, and for a declared member both checks answer on the bytes
that member expands to, with the cap applied during the expansion.
