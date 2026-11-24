# Acceptance criteria

This file carries the record for the current task. Each section names the worktree or branch that owns it. The
Piece 13A.4 record is main's, the current task on main. The other epic records are pointers: Epic 13's rules are in
`docs/INPUT_SHAPES.md`, and Epic 14's criteria are not restated here because that epic still has open pieces in
`to-do.md` and its decisions are in `docs/IMPORT_BINDING.md` §2.

## Piece 13A.4, the documentation comparison (main, the current task on main)

Piece 13A.4 of Epic 13, the shapes an input can be. The criteria cover the 10.2 leg of the "XML and XPath"
comparison and what the piece records about it, and nothing else. The comparison record is `docs/INPUT_SHAPES.md`
§1 fact 4. The documentation-to-fixture relationship is owned by `docs/API_DOCUMENTATION_AND_MOCKS.md`, and this
piece adds no second rule for it.

Out of scope, and not pinned here: the Phase 13B archive producer and its pins, the two open `docs/INPUT_SHAPES.md`
§2 decisions, the shape table rows, the committed fixture pair (Piece 13A.3), the splitter diagnostic
(Piece 13A.2), and `docs/LICENSING.md` counts. This piece measures a documentation page, so it changes no code, no
test, and no fixture.

### Criteria

1. The 10.2 leg answers in one of two ways, and the record states which one it answered:
   - the leg is read, and the record names the page it read, the date, and the answer it got; or
   - the leg cannot be read, and the redirect is recorded as the finding with the date and the URL that answered.
2. The entry shape the leg states is compared with the shape the read layer implements: `xml_input.ENTRY_SEGMENT`
   names the `entry` segment, and the entry name is read from the `name` attribute. The committed corpus states
   entries in that shape. The record states the comparison, not a version difference.
3. Version facts stay measurements. No document states a version difference the project cannot name a measurement
   for. A leg that is not measured stays open as an unfinished leg, not as a stated difference.
4. No fixture, no `src/` file, and no test changes. The shape table gains no row, and no row's `measured_through`
   moves, because the piece measures what a page states and not a byte shape a pin can read.
5. Each fact lands in one place. The measurement is in the comparison record in `docs/INPUT_SHAPES.md` §1. The live
   site fact — the URL the leg's address answers today — is a finding in `backlog.md`. `to-do.md` keeps no completed
   phase detail, and no document restates a row or a fact another document owns.
6. A document that names a test names a test that exists, and no document states a test count.
   `tools/check_documents.py` reports no finding on the tree that holds the piece, including the exact-phrase checks
   that read the shape table's row wording, because the piece must not quote a row.
7. The gate stays green on the tree that holds the piece, measured single-threaded and conservatively:
   `ruff check .`, `ruff format --check .`, `python3 tools/check_documents.py`, `python3 -m pytest` in one process
   with no parallel plugin. The Piece 13A.3 baseline is 1,835 passed and 4 `tflint` skips, so 1,839 pins in 55
   modules; no code changes, so the counts do not move.
8. The writing stays in ASD-STE100 Simplified Technical English, plain and literal, with no marketing voice and no
   emoji.

If web access is unavailable, the piece records that as a blocker and reports it; no assumed fact is written into the
documents.

### Definition of done

The 10.2 leg is measured, or its redirect is recorded as the finding with the URL that answered. The comparison
record names the page it read, the date, and the answer it got. The documents name no unmeasured version difference.
No code, test, or fixture changes. The gate is green. Phase 13A then closes, and `to-do.md` keeps Phase 13B and
Phase 13C only.
