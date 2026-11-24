# Acceptance criteria

This file carries the record for the current task. The Piece 13B.1 record is main's, the current task on main. The
other epic records are pointers: Epic 13's rules are in `docs/INPUT_SHAPES.md`, and Epic 14's criteria are not
restated here because that epic still has open pieces in `to-do.md` and its decisions are in
`docs/IMPORT_BINDING.md` §2.

## Piece 13B.1, the two decisions taken (main, the current task on main)

Piece 13B.1 of Epic 13, the shapes an input can be. The owner took two `docs/INPUT_SHAPES.md` §2 decisions on
2026-11-24: the member rule, and which bytes the provenance record names for an archive read. This piece records
both decisions and moves the shape table rows and the pins those decisions settle. It builds no archive producer,
so it lands no rule as code.

Out of scope, and not pinned here: the size rule during decompression (Piece 13B.2), the cache rule for an archive
entry (Piece 13B.3), the archive producer and its pins (Piece 13B.4), Phase 13C, and `docs/LICENSING.md` counts.

### Criteria

1. Both decisions are recorded in `docs/INPUT_SHAPES.md` §2 as taken, each with the date 2026-11-24, each naming
   what it settled and what stays open. The document stays the one owner of the decisions, so the table module
   holds no copy of them and no decision becomes a field of a row.
2. A row moves from `pending` to `held` only for a fact these decisions settle that a pin can measure today,
   which means the row names an owner function that exists and the pins call it on committed material. A row whose
   rule has no owner stays pending, because `held` is a row the pins measure today. Every pending row must show its
   shape in bytes, so a shape the pins cannot read from bytes stays pending.
3. A pending row states no line and names the piece that will give its rule an owner, because no §2 decision is
   open now. The pins read each pending row as data, so no pending row names a taken decision.
4. The provenance facts stay pending on the piece that states the cache rule, and the accepted archive row stays
   pending on the size rule during decompression, so no code lands for an unsettled fact.
5. No archive producer, no new check, no second size definition, no second DTD rule, no second reader, and no new
   fixture. A pin measures a row through an owner function, so a pin that read archive bytes through a reader of its
   own would state a second rule and is not written. No committed archive file is added, because no pin can decide
   a member shape from a name or read a member list through an existing owner.
6. The pins move in the same commit as the rows they read: the pins that read the pending set as data, and the pin
   that names what a pending row states. If a fixture is added, every file under the index must be named
   (`tests/test_layout.py::test_the_indexes_name_every_document_under_them`) and the fixture-count pins move in the
   same commit, with the counts stated in the commit body.
7. `tools/check_documents.py` reports no finding, including check 7, so no document restates a shape-table row:
   four consecutive words of a row's line inside a quotation or a code span, or six consecutive words anywhere, is
   a finding. The decisions are written as the document's own rules, not as row wording.
8. A document that names a test names a test that exists, and no document states a test count. Writing stays in
   ASD-STE100 Simplified Technical English, plain and literal, with no marketing voice and no emoji.
9. The gate stays green, measured single-threaded and conservatively: `ruff check .`, `ruff format --check .`,
   `python3 tools/check_documents.py`, `python3 -m pytest` in one process with no parallel plugin. The Piece 13A.4
   baseline at `81eb6b0` is 1,835 passed and 4 `tflint` skips, so 1,839 pins in 55 modules. A pin that is renamed
   does not change a count; any count that moves is recorded.
10. One commit for the piece, in conventional-commits style with the completion history in the body, including the
    tracking markdown. Nothing is pushed. `to-do.md` keeps Phase 13B pieces 13B.2 to 13B.4 and Phase 13C, and
    `backlog.md` keeps the live-target facts and any finding this piece opens.

### Definition of done

The two decisions are recorded with the date, each naming what it settled and what stays open. Each row that names
a fact these decisions settled is held, or states why it cannot be held: no owner function can read a member list
or the decompressed bytes today, and the pins read a held row only through an owner function they call. The pins
read the pending rows as data, so the pins and the rows move in the same commit. The gate is green, the counts are
recorded, and the piece is committed.
