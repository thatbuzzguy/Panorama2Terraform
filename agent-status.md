# Agent Status

## Current position

F5.2 (cached API export) is complete. Gate at the commit: `ruff check .` clean, `pytest`
666 passed, both golden sets byte-identical, report determinism pinned by test, exit codes
unchanged (a fetch refusal is an input refusal and exits 1; an invalid argument combination
exits 2; the gate still decides the conversion exit code).

The next feature is F5.3, the provenance record (`SOURCE.txt`) and the report label change.
Its pieces are in `to-do.md`.

## What F5.2 changed

- `source_fetch.py`, the second producer behind the door: `ApiRequest` (host and sorted
  params, no key field), `SourceFetchError` (an `UnsafeInputError` subclass, so `main()`
  prints and exits through the same path), `_SameSchemeRedirectHandler`, `_ssl_context`
  (verification on by default), `network_producer`, `unwrap_config_root` (the wrapper
  decision), and `fetch` (cache hit reads through `read_input`; a miss runs the checks
  through the door before any file is written).
- `PanoramaParser` takes a `ParsedSource`, not a path. Every call site is migrated; no
  backward path is kept, because the parser no longer reads.
- CLI: `input_file` is optional; `--source file|api`, `--host`, `--cache-dir` (default
  `panorama_cache`), `--offline`, `--insecure`. `--offline` and `--insecure` apply only to
  `--source api`, so a file source refuses them.
- `conftest.py`: `fetch_module` fixture, `run_main(module, argv)` helper for a CLI run inside
  the process, and `make_parser` now parses through the door.
- `tests/fixtures/api_response.xml`: the wrapper fixture. Its physical lines are pinned in the
  test (prolog 1, response 2, result 3, config 4), and it holds no unmarked entry, so the
  corpus pins do not move.
- `.gitignore`: `panorama_cache/`, because a cache holds fetched customer data.
- `tests/test_source_fetch.py` (23 tests, six groups: door, wrapper, cache, offline, https and
  key, CLI and gate). No test calls the network.

## Facts measured during F5.2

- `urllib.request.HTTPRedirectHandler.redirect_request` takes `msg` between `code` and
  `headers`. An override with fewer arguments is not the handler urllib calls, so the guard
  uses the parent signature.
- `urllib.request.Request` exposes `full_url`. `fullurl` is the removed alias, so nothing in
  the project uses it.
- The cache entry name is the SHA-256 hex of `host?sorted_params`. The key is not a field of
  the request, so no cache name can carry it, and two different keys for one request find one
  entry — the fact a shared CI cache depends on.
- The report label is still `Input file:` for both sources. F5.3 owns the change to `Source:`;
  the file-run report bytes are unchanged by F5.2.

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

## Watch during F5.3

- `SOURCE.txt` is written outside the report bodies, so the report byte rule still holds.
- The label change regenerates the golden sets: state it in the acceptance criteria before the
  code, and keep the byte-identical gate as the proof.
- The provenance record names the host, the scope and the cache entry. It never names the key.
- A cache entry is not pruned while a report references it, so the reference must be data.
- The property scan measures reads at run time, so a test that wants the read record must
  run the pipeline in process (`conftest.run_pipeline`), not through `run_script`.
