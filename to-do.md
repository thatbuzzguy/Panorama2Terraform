# To Do

The tracking markdown for the completed pieces is removed here; the git history and the owner
documents hold it. Epic 9 (rules as data, one iterated object per rule type) closed 2026-11-19 with
Piece 21, in commit `fd72c09`.

## Epic 10 — template and stack deployment

Piece 24 (E10.1, the membership names that enter the edge set) is complete, committed 2026-11-20. The rule and the
measurement are in `docs/TEMPLATE_STACK_DEPLOYMENT.md` §2 and `acceptance.md`.

The pieces that stay open, in the order `PLAN.md` Epic 10 states them:

1. Piece E10.2 — the scope a template or a stack entry is declared inside, read through
   `resource_mapping.SCOPE_PLACEMENT`, which states a location sub-block for `panos_template_variable` and
   `panos_vsys` and an empty set for the six scope rows. The decision is what the read answers for a template entry
   and a stack entry, and whether the manifest row needs a field for it.
2. Piece E10.3 — a new site instantiated from an existing template: what the tool can state for a template entry the
   export declares and a device the export does not name. What needs the device the operator adds stays in
   `backlog.md`.

## Feature-sized items that stay blocked

Feature-sized items that stay blocked on a fact the tool cannot read offline are recorded in
`backlog.md` and are not pieces here: the rulebase value string and the rule position from a live
target (F3.5), which also gate the rule data column for `rulebase` and the import block for a
rule entry; a config entry inside a stack needs a provider location shape; the EDL
`certificate_profile` field needs a rule that makes the EDL site resolve names; the per-entry
report `profile_name` column needs a value the provider does not declare; the path 2 live facts in
`docs/API_CONVERSION_PATH.md` §4 need a live target.

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
- The corpus is the directory the scan runs over. A hostile fixture in it changes the set the scan
  reports for the other fixtures, so pins that state the printed set name the fixture count. The
  fixture assembler reads the same set by rule: a fixture the F3.8 input rule refuses is skipped,
  and the record is not an input (`tests/test_build_kitchen_sink.py`). A committed API response is
  not corpus material, so it sits in its own set (`tests/responses/`), and the pins that state the
  printed fixture set are not changed by it (`docs/ARCHITECTURE.md` §1.1).