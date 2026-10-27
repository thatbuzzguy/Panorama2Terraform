# Agent Status

## Current position

F5.3 (the provenance record, `SOURCE.txt`, and the report label change to `Source:`) is
complete. Gate at the commit: `ruff check .` clean, `pytest` 682 passed, both golden sets
byte-identical (the goldens cover `.tf` files only, so the label change regenerated
nothing), report determinism pinned, exit codes unchanged.

The next feature is F5.4, the cross-source shadow report. Its pieces are in `to-do.md`.

## What F5.3 changed

- `provenance.py`, the record as data: `FIELD_ORDER` (eight fields, and each field name is
  the printed key), `ABSENT` for a field that does not apply to the source kind,
  `DEFAULT_SCOPE` (`whole-config`), `record_for`, `render`, `parse_record`,
  `cache_reference`, `prunable_entries`. `provenance.py` imports `source_fetch` for the
  request identity; `source_fetch` does not import it, so there is no cycle.
- `xml_input.ParsedSource` records `size` and `sha256` of the bytes the door parsed, so the
  record names the bytes it checked, not a file that may have changed since the run.
- `container_coverage.SOURCE_LABEL` is the one label, and both report writers read it. A
  report body names the source name, never the path.
- `main()` writes `SOURCE.txt` after the reports and before the gate, prints its path, and
  the generated `README.md` lists it.
- Tests: `tests/test_provenance.py` (16 tests, five groups: what the record states, the
  record as data outside the report bodies, the label, the pruning rule, determinism and the
  gate). The three `Input file:` pins moved to `Source:` in `tests/test_container_coverage.py`,
  `tests/test_entry_coverage.py` and `tests/test_source_fetch.py`, and the two-run cache test
  now compares the record too.
- No gate check was added: the gate reads `.tf` files, so a record cannot change what it
  counts or decides.

## Facts measured during F5.3

- The golden sets cover `.tf` files only (`tests/test_golden_files.py`), so the label change
  regenerated no golden. The F5.3 to-do premise that the goldens pin the report bytes was
  wrong, and the acceptance criteria stated the corrected rule before the code.
- A dataclass field cannot be a printed key that contains a space, so every record field name
  is the printed key and `parse_record` reads a written record back as the same record. The
  byte count field is `size`, because `bytes` is a builtin.
- A record names the path as the run received it, so a relative path stays relative: the
  determinism claim is the same arguments and the same bytes, not the same bytes from any
  directory. `cache_entry` is the only cache-derived value in a record, and it does not depend
  on the cache directory, which is the fact a determinism test can compare across two caches.
- `run_script` and `run_main` both write the record, so a test can read it from either path.
  A property-level test still needs `conftest.run_pipeline`, because the read record is a
  run-time fact.

## Rules to keep when writing documents

- One owner document per rule; every other document links to it.
- Machine-readable tables are code. A document explains a table and never restates it
  row by row, so a regenerated table cannot drift.
- No test counts in a document. A document names the test that pins a rule; the
  count lives in `agent-status.md` and the git history.
- A claim about what the tool does must name the module or the test that holds it. A
  feature id is written only when a module or a test uses it as a name.
- ASD-STE100 Simplified Technical English, no marketing voice, no emoji.
- A historical record (the audit report) keeps its findings and states the current
  state separately, so a reader does not take an old finding as a fact.
- A record is data, so a document describes its fields and never restates a record. The
  example in `docs/USAGE_GUIDE.md` is an illustration with a shortened hash, not a pin.

## Watch during F5.4

- A `result` with no `config` element is refused today because it is not the shape the
  container table knows. F5.4 owns the rule for that shape, and the wrapper decision in
  `source_fetch.py` must not be widened by guessing.
- A shadow is a property-level fact, so a shadow test must run the pipeline in process
  (`conftest.run_pipeline`), not through `run_script`.
- The record `scope` field is the hook F5.3 left: `whole-config` is the only value a source
  writes today, and a per-scope source names its own scope.
- The pruning rule reads parsed records. A report line that shows a cache entry name is not a
  reference, so a new report section must not be read as one.
