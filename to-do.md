# To Do

The tracking markdown for the completed pieces is removed here; the git history and the owner
documents hold it. The items that need a fact a live target states are in `backlog.md`.

## Epic 11 — the codebase several runs write into

The design record is `docs/MULTI_RUN_CODEBASE.md`; each rule there names the pins that hold, and a rule whose pin
is pending says so. Acceptance criteria for the open piece are in `acceptance.md`.

### Phase 11C, the update run

- **11C.2** — the run's report section, the sets it names and the rule that it prints only when the codebase
  holds a unit the run did not read.
- **11C.3** — the write boundary: the run writes what it built and deletes nothing; the tool owns every file it
  writes and the byte difference between two runs is read through git.

The move fact, the stale-file boundary, the selection for a `vsys` or a device unit, and the `--prune-cache`
consequence are in `backlog.md`.

## The version pins (plan in `PLAN.md`, criteria in `acceptance.md`)

Run in the `pin-update` worktree, because main is held by another agent. The measurements the pieces rest on are
in `acceptance.md`; the pieces are the parts of the move, and none of them is open until the floor is decided.

- **P.1** — the floor decision. The provider half is settled by the measurement: the schema answer for 2.0.14 and
  2.0.15 is byte-identical, so `~> 2.0.14` moves to `~> 2.0.15` and no measured provider fact changes. The Terraform
  half is open: `>= 1.14` names a line upstream no longer supports, so the choice is the line the evidence covers
  (1.16, newest patch 1.16.7) against the current line (1.17, newest patch 1.17.2), which needs CI and the local
  tool to move first.
- **P.2** — one owner for the minimum. The provider version has one owner, `tests/conftest.py::declared_provider`.
  The minimum is written by three places (the `terraform` block in `src/panorama_to_terraform.py`, the generated
  `README.md`, and the generated `actions.tf` header in `src/commit_actions.py`) and read by one pin, so the piece
  decides whether the minimum gets one owner too, and moves the two pins in `tests/test_commit_actions.py` that
  state the version as a string.
- **P.3** — the bytes the pins state: the head comment and the `terraform` block in `src/panorama_to_terraform.py`,
  `tests/tflint/probe.tf`, the 17 golden `provider.tf` files, the 6 golden `actions.tf` files that carry the
  Terraform line, and `requirements.txt` and `.github/workflows/python-tests.yml` for the tool pins. A minimum
  change is a golden change, so the template and the goldens move in one commit.
- **P.4** — the statements that name the pinned provider: `README.md`, `docs/USAGE_GUIDE.md`,
  `docs/RESOURCE_MAPPING.md`, `docs/COVERAGE_MATRIX.md`, and `docs/CODEBASE_ASSEMBLY.md` §12. §12 is the one place
  that states why the 2.0.14 measurements hold for 2.0.15, so the dated measurements stay as they were measured and
  one sentence names the schema identity.

## Feature-sized items that stay blocked

Feature-sized items that stay blocked on a fact the tool cannot read offline are recorded in
`backlog.md` and are not pieces here: the rulebase value string and the rule position from a live
target (F3.5), which also gate the rule data column for `rulebase` and the import block for a
rule entry; a config entry inside a stack needs a provider location shape; the EDL
`certificate_profile` field needs a rule that makes the EDL site resolve names; the per-entry
report `profile_name` column needs a value the provider does not declare; the path 2 live facts in
`docs/API_CONVERSION_PATH.md` §4 need a live target; and the two shapes the F5.6 comparison table cannot
state as one name need a fixture that exercises them, because the table's content is read from a
measurement over the committed corpus rather than from a name; the tag half also needs the parse to fill the
`description` key its row declares, which `parse_tags` does not read.

## Rules the layout keeps

- `docs/ARCHITECTURE.md` §1.1 is the owner document for the layout. `AGENTS.md` names the tracking
  markdown set, and each index names every document under it, so a file outside an index is a
  finding.
- Import rule: `docs/ARCHITECTURE.md` §1.1 is its owner. `src/` is one flat namespace, so a module
  may import any `src/` module without a cycle, and nothing under `tests/` may import another test
  module: a fact more than one test module reads is stated once in `tests/conftest.py` and read
  from there. The one test that checks the rule reads only `src/`. A test may import `src` modules
  and `tests/conftest.py` through `importlib`. `src/` may not import from `tests/`. `tools/` is not
  on the test path, so `tests/test_build_kitchen_sink.py` reads the fixture assembler through
  `importlib` on the path `tests/conftest.py` builds once.
- Path 2 adds two modules, `api_requests.py` and `api_to_terraform.py`, and both must be named in
  the `docs/ARCHITECTURE.md` §1 table. `rule_data.py` is a tool module named in the same table, and the
  iterated block and the rule data files add no second naming rule, no second writer, no second console
  line, and no environment name, so the pins that scan the `src/` set read it with the other modules.
  `codebase_state.py` is a data module named in the same table, so the same pins read it: it holds no
  writer, names no file, and states no key or shape rule of its own.
- The corpus is the directory the scan runs over. A hostile fixture in it changes the set the scan
  reports for the other fixtures, so pins that state the printed set name the fixture count. The
  fixture assembler reads the same set by rule: a fixture the F3.8 input rule refuses is skipped,
  and the record is not an input (`tests/test_build_kitchen_sink.py`). A committed API response is
  not corpus material, so it sits in its own set (`tests/responses/`), and the pins that state the
  printed fixture set are not changed by it (`docs/ARCHITECTURE.md` §1.1).
