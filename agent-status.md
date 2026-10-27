# Agent Status

## Current position

F5.4 (the cross-source shadow report) is complete. Gate at the commit: `ruff check .` clean,
`pytest` 714 passed, both golden sets byte-identical (the goldens cover `.tf` files only), report
determinism pinned, exit codes unchanged (input refusal 1, argument error 2).

No feature is in progress. The next feature is F5.6 (Terraform state as a source), then F5.5
(read-through data blocks). `PLAN.md` holds the epic; `to-do.md` holds the pieces that need a
decision. Write `acceptance.md` before the code.

## What F5.4 changed

- `shadow_coverage.py` (new, the rule owner): `SHADOW_HEADING`, `SHADOW_RULE`, `parent_index`
  (keyed by matrix row and entry name, first row wins in report order), `shadow_findings`, and the
  fixed `shadow_line` shape. It owns no console wording, so a shadow prints only in the report.
- `container_coverage.py`: `ENVELOPE` (`response`, `result`), `SCOPE_PATH_ROOTS`, and
  `container_tag` as the one source-aware place rule the scan, the entry ledger, and the parser
  scope walk all read. `record_path` and `is_scope_path` hold the path shape the CLI checks.
- `entry_coverage.py`: every row carries `source` as data; `matrix_row_for(section)` is the F4.4
  scan-scope helper both the property scan and the shadow scan use; `entry_line` prints no source,
  so the entry-line bytes are unchanged for a one-source run.
- `xml_input.py`: `DEFAULT_SCOPE` and `ENTRY_SEGMENT` are the scope vocabulary, one definition,
  read by `provenance.py`, `container_coverage.py` and `source_fetch.py`. The import pin lets the
  fetch layer import only the door, so the segment cannot live in `container_coverage.py`.
  `ParsedSource.scope` records the declared path, and `is_per_scope` and `scope_container` read it.
- `source_fetch.py`: `ApiRequest.path`, `is_per_scope`, `segments`, `request_params` (the path is
  part of the request identity), `unwrap_config_root(source, request)` with two branches, and
  `fetch` passes the request. It still imports no ElementTree.
- `provenance.py`: `parse_records` and `render_records`; `record_for` reads `source.scope`. A file
  with one record writes the same bytes as the F5.3 rule.
- `main()`: `--path` and `--parent` (api source only, `--parent` needs `--path`, a path must name a
  scope path), the parent read, the parent ledger, `generate_conversion_report(ledger, shadows)`,
  and the record file written from the list of records.
- Fixtures: `tests/fixtures/scope_child.xml` and `tests/fixtures/scope_parent.xml`, one shared name
  on line 10 in each. As file inputs both are finding-free, so the corpus pins still hold.
- Tests: `tests/test_shadow_coverage.py` (18 tests, six groups), and the pins migrated in
  `tests/test_source_fetch.py` (the wrapper refusal now has two branches, and the offline test reads
  the second request), `tests/test_provenance.py` (the record file as data, and a printed parent
  source is not a reference), `tests/test_container_coverage.py` (the envelope), and
  `tests/test_entry_coverage.py` (the row source key, and the entry line prints no source).
  `conftest.run_pipeline` takes extra arguments, so a test can pass `--path` and `--parent`.

## Facts measured during F5.4

- `section_path` keeps the entry segment, so a per-scope child entry reads as
  `device-group/entry/address` and the same name in the parent scope reads as `address`. Both
  resolve to the same matrix row, which is what makes them one finding.
- A per-scope entry takes the declared scope as its scope fact, so the shadow section prints under
  the declared device group instead of `SHARED SECTION`. The grouping needs `container_tag`, not
  the raw element tag.
- The record `path` field is the path the run received, so two runs on the same bytes write the
  same record only when they read the same cache directory. The determinism test seeds one cache
  and runs twice against it.
- `fetch` checks `PANOS_API_KEY` before it calls an injected producer, so an in-process test sets
  the environment variable even when the producer is monkeypatched.
- The line map is the response bytes, not a reparse: `result` is line 7 of each fixture, and the
  entry the shadow names is line 10.

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

## Watch during F5.6

- A state source is a JSON document, so the door's DTD rule and the size check still apply to its
  bytes, but the container table, the parent walk, and the expat line map do not: they are keyed on
  the ElementTree tree (`backlog.md`, Epic 5 decisions). A rule is needed before the property scan
  can read a state document.
- The record `scope` field is the hook F5.3 left and F5.4 filled for a declared path. A state
  source names its own workspace, so the record shape does not change.
- The prune action still needs the record directory decided, and a two-source run writes two records
  in one file, so a prune action reads a record file, not one record.
- A shadow test runs the pipeline in process, because the shadow fact is a run fact read from the
  ledger. The same applies to a drift fact.
