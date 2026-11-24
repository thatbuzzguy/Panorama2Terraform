# Acceptance criteria

This file carries the record for the current task. The Piece 13B.2 record is main's, the current task on main. The
other epic records are pointers: Epic 13's rules are in `docs/INPUT_SHAPES.md`, and Epic 14's criteria are not
restated here because that epic still has open pieces in `to-do.md` and its decisions are in
`docs/IMPORT_BINDING.md` §2.

## Piece 13B.2, the size cap during decompression (main, the current task on main)

Piece 13B.2 of Epic 13, the shapes an input can be. The piece lands the archive producer in `src/xml_input.py`, so
the F5.1 size cap is applied while the bytes expand and a bundle that expands past the cap is refused before a tree
is built. It adds a producer and no check: `check_bytes` stays the one definition of the two checks, and the door
runs them on the bytes the producer hands it.

Out of scope, and not pinned here: the cache rule for an archive entry and the provenance record for an archive read
(Piece 13B.3), the member-selection argument and the refusal it prints for a bundle with no declaration
(Piece 13B.4), Phase 13C, the exit-code rules, the gate rules, and `docs/LICENSING.md` counts.

### Criteria

1. The cap holds during decompression, as decision 2 of `docs/INPUT_SHAPES.md` §2 states it. The producer expands at
   most as far as the read cap `read_input` already states, `max_input_bytes + 1`, so an over-cap bundle is refused
   without the whole expansion being allocated, and without a tree being built.
2. `check_bytes` is the one definition of the two checks, and it runs on the decompressed bytes. The producer states
   no size rule of its own, no DTD rule of its own, no reader of its own, and no refusal wording of its own. A shape
   the producer does not accept is handed to the door unchanged, so the parse answers it with the line the table
   already holds for the magic-bytes row, and no new refusal line is written.
3. The accepted shapes are read from the bytes, not from a name, as §2 rule 3 states: a single-member gzip, and a
   gzip stream that holds a tar archive with exactly one member. A stream with more than one member is not an
   accepted shape today, because the refusal §2 rule 4 states for it has no owner yet, so this piece pins no
   member-selection answer and no bundle refusal.
4. The shape decision stays out of `parse_bytes`, which is the door: the door keeps the answer the held magic-bytes
   row states, so the producer sits between the read and the door. The file producer reads the bytes and hands them
   to the producer, which is why the read rule accepts an accepted shape under any name.
5. The refusal names the origin: the path for a file, the source for a producer that has no file behind it, through
   `origin_phrase`. It builds no tree, and it writes no file. The producer opens nothing, so the boundary rule
   (`tests/test_safe_input.py::test_boundary_opened_no_file`) still holds for it.
6. The pins run offline on committed material. The committed material for a shape is the table's own content, as
   rule 7 of `src/input_shapes.py` states, so no fixture is added: `tests/fixtures/` is corpus material that the
   assembler's read rule reads, and a compressed stream cannot be corpus material because the read rule cannot
   decompress. No file is added under any index, so the index pin does not move and no fixture-count pin moves: the
   printed fixture set stays 72 `*.xml` files, 69 accepted and 3 skipped.
7. A pending row moves to `held` only for what this piece makes measurable through the row's `measured_through`
   owner. The accepted archive row states two shapes, so it becomes two rows, one per shape, each with the content
   that shows it, because the pins read a row through one content. The decompression row is added as a held refusal
   row, measured through the producer. The rows for Piece 13B.3 and Piece 13B.4 stay pending, and each keeps the
   bytes it showed, so the pins can still read a pending row through a held row.
8. The pins that state the table counts move in the same commit, and every count that moves is recorded in the commit
   body. The pins measure the compressed row against a limit that sits above its content and below what the content
   expands to, so the refusal can only come from the expansion, which is the rule the row states. Every other size
   row is measured against the pins' own limit, which is under its content.
9. `tools/check_documents.py` reports no finding, including check 7, so no document restates a shape-table row: four
   consecutive words of a row's line inside a quotation or a code span, or six consecutive words anywhere, is a
   finding. The documents state this piece through their own wording and name the pins.
10. The `docs/ARCHITECTURE.md` §1 module table and the root index name every `src/` module and every test module, so
    a new module is not added: the producer is a function in `src/xml_input.py`. §3.1 names the producer as a
    producer behind the door, and §1 fact 1 of `docs/INPUT_SHAPES.md` states what the producer does now that it
    exists.
11. Writing stays in ASD-STE100 Simplified Technical English, plain and literal, with no marketing voice and no
    emoji, and no document states a test count.
12. The gate stays green, measured single-threaded and conservatively: `ruff check .`, `ruff format --check .`,
    `python3 tools/check_documents.py`, `python3 -m pytest` in one process with no parallel plugin. The Piece 13B.1
    baseline at `752f756` is 1,835 passed and 4 `tflint` skips, so 1,839 pins in 55 modules. A pin that is renamed
    does not change a count; any count that moves is recorded.
13. One commit for the piece, in conventional-commits style with the completion history in the body, including the
    tracking markdown. Nothing is pushed. `to-do.md` keeps Phase 13B pieces 13B.3 and 13B.4 and Phase 13C, and
    `backlog.md` keeps the live-target facts and any finding this piece opens.

### Definition of done

The producer is one function in `src/xml_input.py` that reads the shape from the bytes, expands exactly one accepted
member, stops at the read cap, and hands the bytes to the door. A bundle that expands past the cap is refused by the
size rule before a tree is built, and the refusal names the origin. No second size definition, no second DTD rule, no
second reader and no new refusal wording exists. The two accepted shape rows and the decompression row are held and
measured through the producer, the pins that state the table counts agree with the table, the gate is green, the
counts are recorded, and the piece is committed.
