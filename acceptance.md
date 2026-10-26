# Acceptance Criteria — F5.1 Source read boundary (current task)

Scope: the input door takes bytes from a producer instead of taking a path. The two
F3.8 checks stay inside `xml_input.py`, so no producer can bypass them. The parse
layer keeps the ElementTree tree, because the container table, the entry ledger, the
parent walk and the line map are keyed on it.

The record of the previous task is in the git history.

Out of scope for this task:

- The fetch, the cache and the provenance record (F5.2, F5.3). This task adds the
  boundary they need; it does not add a source.
- The report label change (`Input file:` to `Source:`). It lands with the provenance
  record, so report bytes do not change here.
- `pan-os-python`, any network call, and any test that needs one.
- F4.4 and the two report defects that land with it.

## AC-1 — One door, one shape

1. `parse_bytes(data, origin, max_input_bytes)` is the only place the two checks run,
   and it parses the bytes that passed them.
2. `parse_xml(path)` is the file producer: the size check before the read, then
   `parse_bytes`. Its name and signature do not change, so both entry points and the
   test that pins the single door keep passing.
3. `tools/build_kitchen_sink.py` is not an entry point and does not use the door. That
   F3.8 exemption is unchanged.

## AC-2 — The checks hold for any producer, not only for a file

1. `parse_bytes` refuses bytes over the limit before it parses them, and the refusal
   names the origin.
2. `parse_bytes` refuses a DTD in bytes from any producer, through the parser, not a
   text search.
3. `read_input` keeps the pre-allocation size check for a file and the size check on
   the bytes it read.
4. A test pins that a producer with no file behind it is refused for size and for a
   DTD the same way a file is. This is the fact F5.2 depends on, so it is pinned here
   and not assumed there.
5. A test pins that the input is still read once: `parse_xml` reads the file once and
   `parse_bytes` opens nothing.

## AC-3 — Source identity

1. `SourceOrigin` holds `kind` and `name`, and `path` when a file can be reopened.
   `kind` is `file` for the file producer.
2. `name` is what a report prints. For a file it is the file name with no directory,
   so a report line does not depend on the path.
3. `ParsedSource` keeps `root`, the line map and `line_of`. The line rule is unchanged:
   only the parse records a line, so an element copied out of the tree has none.
4. An error message names the origin: the path when the origin has one, the origin name
   when it has none.

## AC-4 — No behaviour change

1. `ruff check .` clean and `pytest` green with no existing expectation changed.
2. Both golden sets byte-identical.
3. The four report files and the sanity report are byte-identical for the same input,
   including the committed example report.
4. Exit codes unchanged: a size or DTD refusal still exits non-zero and writes no
   output.

## AC-5 — Documents

1. `docs/ARCHITECTURE.md` §1 and §3 name the producer boundary as the single door, and
   state that the checks run on the bytes a producer hands.
2. `README.md` Safe input states the two checks apply to bytes from any producer.
3. `xml_input.py` states what the boundary holds and what a producer must not bypass.
4. `PLAN.md` F5.1 records that the report label change moved to F5.3, so F5.1 changes
   no report output.

## Gate

`ruff check .`, `pytest`, goldens byte-identical, reports byte-identical, exit codes
unchanged.

## Result — complete

1. `parse_bytes(data, origin, max_input_bytes)` is the boundary. `parse_xml(path)` is
   the file producer and keeps its signature, so both entry points still import it.
2. `SourceOrigin` holds `kind`, `name` and `path`. `ParsedSource.name` reads the origin,
   so no report text changed. Error messages name the origin: the path when there is
   one, the origin name when there is not.
3. Six tests added, in the F5.1 section of `tests/test_safe_input.py`. No existing
   expectation changed.
4. Gate: `ruff check .` clean, 572 tests passed, the kitchen-sink output is byte-identical
   against the same run at the commit before this task, a size refusal still exits 1 and
   writes no output, and both entry points still share one door.
