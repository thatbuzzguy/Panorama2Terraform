# To Do

The open feature is Epic 8, the API-only conversion path. Its design record is
`docs/API_CONVERSION_PATH.md`, and each piece below names the rule it holds, the module that will
state it, and the test that will pin it. F8.1 is complete: the three request shapes and the op
wrapper rule are in `src/source_fetch.py`, the `predefined` decision is inside
`container_coverage.SCOPE_PATH_ROOTS`, and the pins are named in
`docs/API_CONVERSION_PATH.md` §2.1. F8.2 is complete: the scope index is in `src/api_requests.py`,
the set is read through the four membership lists, the rule is stated in
`docs/API_CONVERSION_PATH.md` §2.2, the module is in the `docs/ARCHITECTURE.md` §1 table, and the
pins are named there. F8.3 is complete: the join is `api_requests.join_response`, the element-name rule is
read through `source_fetch.names_element`, and the rule is stated in `docs/API_CONVERSION_PATH.md` §2.3 with
the pins named. Phase 8A is complete: F8.4 landed the committed response set, one file per request shape,
each named by the key-free request identity that produced it and read through the injected producer, and the
decision about where it lives is stated in `docs/ARCHITECTURE.md` §1.1 with its pins named.

## Epic 8 — path 2 pieces

Phase 8B, the run over many sources:

- [ ] F8.5 No merged tree. Each response stays its own `ParsedSource` with its own line map, and each
      parse method runs over the response that holds its container. The report position is the line
      inside that response, and the report row names the source that holds the entry. Pin:
      `tests/test_api_path.py`, and the existing pin
      `tests/test_entry_coverage.py::test_every_row_names_the_source_that_holds_the_entry`.
- [ ] F8.6 One record per request. The eight fields and the fixed order are unchanged, and the `scope`
      and `request` fields name the request that made the response. The prune action reads the record
      file, so a run that read N scopes protects N entries. Pins: `tests/test_provenance.py`,
      `tests/test_write_path.py::test_the_record_directory_is_the_output_directory_for_the_prune`.
- [ ] F8.7 The unit join. `unit_manifest.units` stays the one unit rule, and path 2 adds the fact of
      which scope the run read for a unit. A unit with no request, and a request that answers no unit,
      is a finding. Pins: `tests/test_api_path.py`, `tests/test_unit_manifest.py`,
      `tests/test_ownership.py`.

Phase 8C, the gate and the entry point:

- [ ] F8.8 The request-set gate rule, read inside `sanity_checks.py` at one position in
      `CHECK_ORDER`, and the path 2 pins for the gate rules that already read the files. The
      round-trip cross-check reads the run's ledger, so path 2 feeds the same ledger through the same
      `mark` rule. Pins: `tests/test_sanity_gate.py`, `tests/test_round_trip.py`.
- [ ] F8.9 The entry point `api_to_terraform.py`: the arguments, the run order, the exit codes, the
      rule that it writes no file outside `write_path.py` and states no environment name, and the
      generated `README.md` label that names which path wrote the codebase. Pins:
      `tests/test_api_path.py`, `tests/test_variables.py`, `tests/test_site_data.py`.
- [ ] F8.10 The agreement pin. For a fixture with no live-only fact, path 2 writes the same `.tf`
      bytes as path 1. The reports do not agree, because a report names its source. Pin:
      `tests/test_api_path.py`.

Feature-sized items that stay blocked on a fact the tool cannot read offline are recorded in
`backlog.md` and are not pieces here: the four `*_policy_rules` types wait for the F3.5 rulebase
decision and a live target, a config entry inside a stack needs a provider location shape, the EDL
`certificate_profile` field needs a rule that makes the EDL site resolve names, the per-entry report
`profile_name` column needs a value the provider does not declare, the two `.github/` template files
outside the indexes are findings, and the path 2 live facts in `docs/API_CONVERSION_PATH.md` §4 need a
live target: the committed response set shows one shape per accepted request shape and names no fact.

## Other open pieces

- [ ] `ruff format` as a gate, its own task per `backlog.md` (Nice-to-Haves). The one-time format pass
      of the legacy scripts comes first, so the diff stays reviewable. `tflint` integration is the
      following item.

## Rules the layout keeps

- `docs/ARCHITECTURE.md` §1.1 is the owner document for the layout. `AGENTS.md` names the tracking
  markdown set, and each index names every document under it, so a file outside an index is a finding.
- Import rule: `src/` is one flat namespace, so a module may import any `src/` module without a cycle.
  The one test that checks the rule reads only `src/`. A test may import `src` modules and
  `tests/conftest.py` through `importlib`; nothing under `tests/` may import another test module. `src/`
  may not import from `tests/`. `tools/` is not on the test path, so `tests/test_build_kitchen_sink.py`
  reads the fixture assembler through `importlib` on the path `tests/conftest.py` builds once.
- Path 2 adds two modules, `api_requests.py` and `api_to_terraform.py`, and both must be named in the
  `docs/ARCHITECTURE.md` §1 table. Both state no second naming rule, no second writer, no second
  console line, and no environment name, so the pins that scan the `src/` set read them with the other
  modules.
- The corpus is the directory the scan runs over. A hostile fixture in it changes the set the scan
  reports for the other fixtures, so pins that state the printed set name the fixture count. The fixture
  assembler reads the same set by rule: a fixture the F3.8 input rule refuses is skipped, and the record
  is not an input (`tests/test_build_kitchen_sink.py`). A committed API response is not corpus material, so
  it sits in its own set (`tests/responses/`), and the pins that state the printed fixture set are not
  changed by it (`docs/ARCHITECTURE.md` §1.1).
