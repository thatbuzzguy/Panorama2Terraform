# Acceptance criteria

This file carries the record for the current task. The Piece 13B.3 record is main's, the current task on main. The
other epic records are pointers: Epic 13's rules are in `docs/INPUT_SHAPES.md`, and Epic 14's criteria are not
restated here because that epic still has open pieces in `to-do.md` and its decisions are in
`docs/IMPORT_BINDING.md` §2.

## Piece 13B.3, the provenance facts for an archive read (main, the current task on main)

Piece 13B.3 of Epic 13, the shapes an input can be. The piece lands decision 5 of `docs/INPUT_SHAPES.md` §2, which
was taken 2026-11-24: for an archive read the record names the decompressed bytes, `SourceOrigin.kind` names the
archive, and the member name enters the record as a field the file case does not have. The piece also settles the
cache rule through the owner that already states it, `docs/ARCHITECTURE.md` §3.3 rule 4, and moves the shape-table
row that names this piece from `pending` to `held`.

Out of scope, and not pinned here: the member-selection rule and the refusal it prints for a bundle with more than
one XML member (Piece 13B.4), the Phase 13C documents, the exit-code rules, the gate rules, `check_bytes`, the DTD
rule, and the `docs/LICENSING.md` counts.

### Criteria

1. **The record names the decompressed bytes for an archive read.** The F5.3 rule is unchanged: the byte facts come
   from the door, and the door checks the bytes the producer hands it, which for an accepted archive shape are the
   expanded bytes. The pins hold that the record's `size` and `sha256` name the bytes the door parsed and are not the
   facts of the stream the table row holds, so no second size definition and no second hash rule appear.
2. **One decision, stated once.** The record shape gains the member field, and `src/provenance.py` rule 1 stays the
   only place that states the field order. The record module states no naming rule, builds no path, and states no
   second version of the F5.3 rule. The producer is the only place that reads the member name, through the gzip
   header field and the tar header field. The pins that read the field order sit in group 1 of
   `tests/test_provenance.py`, the group that holds the rule the field order states, so the pins that read another
   rule do not state the count again.
3. **`SourceOrigin.kind` names the archive for an accepted archive read**, through one constant the archive producer
   states, as `source_fetch.py` states `SOURCE_KIND` and `state_input.py` states `STATE_KIND`. The origin shape is
   one definition, so the record reads the kind and the member through the origin and restates neither. A row that is
   not an accepted archive read keeps the kind its producer states, and the refusal wording does not move, because
   `origin_phrase` names the path or the name and never the kind.
4. **The member field reads `-` for the case that has no member.** The `-` rule in `src/provenance.py` rule 1 is the
   one rule for a field that does not apply to the source kind, so a file record, an api record and a state record
   state `-` for it, and an archive read whose stream states no member name states `-`. The pins measure the field
   for an archive read that states a name and for the file case.
5. **The cache rule reads through its existing owner, `source_fetch.py`, and is not restated.** An archive record
   states `-` for the cache field when the read came through the file producer, so `cache_reference` answers None and
   the record prunes nothing, measured through `prunable_entries`. The condition that differs is recorded as a
   measurement, not as a rule: the api producer hands its bytes to `parse_bytes` and never to the archive producer,
   so no archive read has a cache entry today, the entry holds the bytes as they arrived, and no record names them.
6. **The row that names Piece 13B.3 moves to `held` with an owner the pins can call**, `provenance.record_for`, and
   the pins read it back through `provenance.parse_record`. The row's content is the smallest stream that shows both
   facts the record reads for an archive read: the bytes the door checks, and a member name the stream states. The
   row that names Piece 13B.4 stays pending, because its rule still has no owner. The record row is now measured
   through `provenance.record_for`, so `provenance` is added to `OWNERS` in `tests/test_input_shapes.py` and the pins
   call the build rule through the row's own `measured_through`. Every pin that reads the row shape, the status
   counts, and the pending set moves in the same commit, in `tests/test_input_shapes.py` and
   `tests/test_provenance.py`, and the origin-kind pin that reads the archive shape moves in `tests/test_safe_input.py`.
7. **The pins hold no content of their own.** They read the shape through the table's own content, the kind through
   `xml_input.ARCHIVE_KIND`, the absent shape through `provenance.ABSENT`, and the byte facts through the source the
   producer returned.
8. **No committed golden holds a record**, so no golden moves for a new field. Measured 2026-11-24: `tests/golden/`
   holds no `SOURCE.txt`, so the field order moves the pins that state the field count and nothing else. The pins
   that read the origin kind for the archive shape move with the producer, in `tests/test_safe_input.py`.
9. **No new module and no new test file.** The field lands in `src/provenance.py`, the kind and the member fact land
   in `src/xml_input.py`, so the `docs/ARCHITECTURE.md` §1 table, the root index, and the `docs/LICENSING.md` counts
   do not move.
10. **`tools/check_documents.py` reports no finding**, including check 7, so no document restates a shape-table row.
    The documents state the piece through their own wording and name the pins that exist, and no document states a
    test count.
11. Writing stays in ASD-STE100 Simplified Technical English, plain and literal, with no marketing voice and no
    emoji.
12. The gate stays green, measured single-threaded and conservatively: `ruff check .`, `ruff format --check .`,
    `python3 tools/check_documents.py`, `python3 -m pytest` in one process with no parallel plugin. The Piece 13B.2
    baseline at `920ce60` is 1,841 passed and 4 `tflint` skips, so 1,845 pins in 55 test modules. Any count that
    moves is recorded.
13. One commit for the piece, in conventional-commits style with the completion history in the body, including the
    tracking markdown. Nothing is pushed. `to-do.md` keeps Piece 13B.4 and Phase 13C, `agent-status.md` records the
    position, and `backlog.md` keeps the live-target facts and the finding this piece opens.

### Definition of done

The record states nine fields in one declared order, and the member field names the member an archive read took.
`SourceOrigin.kind` names the archive for an accepted archive read, through the constant the producer states. The
byte facts name the decompressed bytes, measured through the producer and read back as data through `parse_record`.
The cache rule is read through `source_fetch`, and the condition that differs is recorded as a measurement. The row
that names Piece 13B.3 is held and measured through the record build rule, the row that names Piece 13B.4 stays
pending, the pins that state the counts agree with the table, the gate is green, the counts are recorded, and the
piece is committed.
