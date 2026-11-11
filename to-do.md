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

F8.5 is complete: one response is one source with its own line map, the parent walk and the ledger are
keyed on that one tree, and each parse method runs over the response that holds its container. The join is
`api_requests.response_for_section`, which answers the index entry for the place a section names plus the
entry the run read, and `api_requests.entry_for_path` is the lookup it reads. The rule is stated in
`docs/API_CONVERSION_PATH.md` §2.4 with the pins named, in `tests/test_api_path.py`. The piece also fixed
`container_coverage.section_path`, which stated the place twice for a per-scope place read; the guard reads
a per-scope source, so path 1 is unchanged, and the two paths now name the same container path for the same
content. The predefined decision this piece took is recorded in `backlog.md`.

F8.6 is complete: the record file holds one record per request the path 2 run read, with the eight fields and
the fixed order unchanged. For each request, `scope` names the path that request declared and `request` names
its key-free identity, so `cache_entry` names the entry that identity names. The prune action reads the record
file the same run wrote, so a run that read N requests protects N entries, and no new field is needed. The rule
is stated in `docs/API_CONVERSION_PATH.md` §2.5 with the pins named.

Phase 8B is closed: one response is one source with its own line map, the parse methods run per response, the
report position names the line inside the response that held the entry, the record holds one record per request
the run read, and the unit join reads the scope the run read for each unit. The rules are stated in
`docs/API_CONVERSION_PATH.md` §2.4, §2.5 and §3 with their pins named, in `tests/test_api_path.py`,
`tests/test_unit_manifest.py` and `tests/test_ownership.py`. The findings F8.7 recorded stay in `backlog.md`.

Phase 8C, the gate and the entry point:

F8.8 is complete: the request-set gate rule is `sanity_checks.check_request_set`, and it reads the join rows
through `api_requests.unit_findings`, the unit through `unit_manifest.directory_name` and `naming.sanitize`, and
the index through `api_requests`. The position, the severity, the report section, the console line and the exit
code are the gate's decision, stated in `docs/API_CONVERSION_PATH.md` §3 with the pins named, in
`tests/test_sanity_gate.py` and `tests/test_round_trip.py`. `run_checks` takes the index as an argument, so a path
1 run reports the rule as NOT RUN, and the path 2 entry point passes the index it built (F8.9).

F8.9 is complete: the entry point `src/api_to_terraform.py` states the run order, the arguments, and the exit
codes. It reads the membership responses first, in the order `api_requests.membership_lists()` names them, then
the entries `api_requests.scope_index()` names in index order, and it is the only place that states that order;
the record file the run wrote is the order's own statement. It joins the per-response tables in run order through
the one join rule in `panorama_to_terraform.py`, and `generate_run` takes the run view as an argument, so the join
is the entry point's decision. It adds no argument of its own, accepts no argument that names one source, reads
the environment name through `source_fetch.API_KEY_ENV`, prints only through the owners' console lines, writes no
file outside `write_path.py`, and calls `generate_run`, so it states no parse order and no block builder. The gate
gets the index it built, and the generated `README.md` names the entry point that wrote the codebase as an
argument. The rule is stated in `docs/API_CONVERSION_PATH.md` §6 with the pins named, in
`tests/test_api_path.py`, `tests/test_variables.py`, and `tests/test_site_data.py`, and the module is in the
`docs/ARCHITECTURE.md` §1 table. The findings the run order closed are removed from `backlog.md`.

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

- [ ] The history rewrite landing. Point `development`, `dev` and `main` at the branch
      `history-rewrite`, which needs a force-push, and drop the two PR merge commits on
      `origin/main`. The criteria and the measured result are in `acceptance.md`.
- [ ] The `licensing` branch: 4 commits on top of `development` need the same rebase, through
      `git rebase --onto history-rewrite <merge-base> licensing`.
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
