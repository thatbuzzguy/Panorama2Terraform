# Acceptance criteria — codebase review and audit

## Scope

This task reviews the codebase and reports findings. It changes no functional code and adds no pin.
The audit covers: the module set, the test set, the rule pins the documents name, the layout rule
(`docs/ARCHITECTURE.md` §1.1), the import rule, and the tracking markdown.

## The criteria

1. **The baseline gate is measured.** `ruff check .` and `python3 -m pytest` run before and after the
   audit. The pin count is recorded. Any finding that changes a pin is recorded, not applied, because
   this task states findings.
2. **The layout rule is checked as the rule states it.** Every file under an index is named by that
   index. Every `src/` module is named in the `docs/ARCHITECTURE.md` §1 table. A file outside an index
   is a finding.
3. **The import rule is checked by scan.** `src/` imports only the standard library and its siblings;
   no `src/` module imports from `tests/`; no test module imports another test module; the test path is
   stated only in `pyproject.toml`.
4. **Every pin a document names exists.** Each `tests/test_*.py::test_name` claim in the markdown set is
   read against the test files. A named pin that does not exist is a finding.
5. **The tracked counts agree with the measurement.** The counts the documents state (matrix rows,
   data sources, fixture counts, the ruff `py310` finding count, the Python floor, the CI matrix legs)
   are re-measured. A count that does not agree is a finding.
6. **The code is reviewed for functional correctness.** The `src/` set is read for silent drops,
   rule owners that state a second rule, mutation of shared state, unguarded error paths, and findings
   that contradict the documented rule.
7. **The tracking markdown agrees with the git history.** A piece recorded as open in `to-do.md` or
   `agent-status.md` that is committed is a finding, because the rule says completed work leaves the
   markdown.
8. **Findings land in `backlog.md`.** Every actionable finding this audit measures gets an entry; the
   report itself is the chat response plus the backlog entries. No document outside an index is created.

## Out of scope

- Fixing the findings. This task reports; each finding names the owner module or document that would fix
  it.
- Live-target facts already gated on a live target in `backlog.md`.

## Measured results (2026-11-11/12)

Criterion 1. Gate before and after: `ruff check .` clean; `python3 -m pytest` collected 1,641 pins across
50 modules, all pass, no skips on the audit machine (the terraform binary is present locally). The audit
changed no code and added no pin.

Criterion 2. The §1 module table names 20 of the 22 `src/` modules; `commit_actions.py` and
`api_to_terraform.py` are findings. The indexes for `docs/`, `examples/` and `tools/` are complete; the two
`.github/` template files are findings already recorded. `tests/` holds files with no index.
`tests/fixtures/api_response.xml` is a committed response inside the corpus.

Criterion 3. `src/` imports only the standard library and its siblings, and no `src/` module imports from
`tests/`. The test path is stated only in `pyproject.toml`. One violation: `tests/test_real_or_report.py:33`
imports helpers from `test_policy_order`; no pin holds this rule, so the gate reports nothing.

Criterion 4. 153 pin claims read across the markdown set. 4 name a test that does not exist:
3 defensible (an unwritable pin named by rule, an abbreviated pin name, and the profile-name pin that
cannot be written from the schema), 1 real mismatch (`docs/API_CONVERSION_PATH.md` names
`test_the_module_defines_no_second_naming_rule`; the function is
`test_site_data_defines_no_second_naming_rule`). The nine F8.9 pins promised in acceptance commit `380ed26`
exist nowhere in `tests/`.

Criterion 5. Re-measured: `COVERAGE_MATRIX` holds 42 rows against the document claim of 40 and the README
claim of 34 (`panos_certificate_import` and `panos_certificate_profile` are in the code table but not in the
document table). `agent-status.md` states 1,641 pins at its top section but 1,638 at its test count line.
The ruff `py310` count (101 = 80 UP045 + 16 B905 + 4 UP035 + 1 UP007) agrees, `target-version` stays `py39`.
The CI legs (3.10-3.13), the `pytest==9.1.1` pin, and the pre-commit hooks agree. The fixture set measures
71 (68 accepted, 3 skipped by the F3.8 rule). `docs/LICENSING.md` states 59,329 tracked lines (2,172 upstream
against 57,157 ours); the tree now measures 59,370, so the ours side is 41 lines behind.

Criterion 6. The `src/` read found no silent drops, no second rule owners, and no contradiction with the
documented rules beyond the findings in `backlog.md`. Claims from the review agents that did not survive
re-measurement against the actual files are not recorded (for example: `mark()` returning a bare dict,
unsorted `rows()`, `sanitize` dropping digit-only names, `row_key` and `scan_row` in `api_requests.py`, a
tflint mention in `tests/test_data_file_gate.py`).

Criterion 7. `to-do.md` lists F8.9 as open while `git log` records its steps 1 to 3 committed
(`720da9f`, `3d54163`, `88921c2`); `agent-status.md` names F8.9 as the next piece. `to-do.md` keeps completed
Phase 8A and Phase 8B detail.

Criterion 8. All actionable findings are recorded in `backlog.md`, section "Codebase audit findings
(measured 2026-11-11)", plus the additions this response records: the nine missing F8.9 pins, the corrected
schema-pin count, and the licensing line drift. No document outside an index was created.
