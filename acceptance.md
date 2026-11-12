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

Criterion 4. 156 claims read across the markdown set in the `tests/test_*.py::test_name` form. 6 name a test
that does not exist, across 3 names, each claimed twice: the profile-name pin (`backlog.md`),
`test_parse_rip` (`backlog.md` and `docs/ARCHITECTURE.md`), and `test_the_module_defines_no_second_naming_rule`
(`backlog.md` and `docs/API_CONVERSION_PATH.md`; the function is
`test_site_data_defines_no_second_naming_rule`, line 708). One further claim names a constant, not a pin
(`docs/COVERAGE_MATRIX.md` names `tests/test_scope_objects.py::PRINTED_BY_ANOTHER_BLOCK`).
`docs/ARCHITECTURE.md:1015` names `test_policy_order` as a module, not a pin. The nine F8.9 pins earlier
recorded under commit `380ed26` are a disproof: that commit's acceptance file names no pin, and the pins
`docs/API_CONVERSION_PATH.md` §6 names for F8.9 all exist.

Criterion 5. Re-measured: `COVERAGE_MATRIX` holds 42 rows against the document claim of 40 and the README
claim of 34 (`panos_certificate_import` and `panos_certificate_profile` are in the code table but not in the
document table). The ruff `py310` count agrees (101 = 80 UP045 + 16 B905 + 4 UP035 + 1 UP007 measured with
`--target-version py310`), `target-version` stays `py39`. The CI legs (3.10-3.13), the `pytest==9.1.1` pin, and
the pre-commit hooks agree. The fixture set measures 71 (68 accepted, 3 refused by the F3.8 rule).
`docs/LICENSING.md` §The split, measured states 2,172 upstream and 57,157 ours against 2,155 and 57,245
measured with `git blame`, 50,008 against 50,012 for `src/`, `tests/` and `tools/`, and 121 commits against 127.
`agent-status.md` agrees with the measurement (1,641 pins, 991 test functions, 50 modules); the 1,638 figure
earlier recorded as internal drift is a disproof, because no markdown states it.

Criterion 6. The first `src/` read (2026-11-11) found no silent drops in the coverage and record modules.
The 2026-11-12 read of the parse set, the emitter set and `src/split_device_groups.py` measured silent drops,
second rule owners and unguarded paths; they are recorded in `backlog.md`, section "Codebase audit findings
(measured 2026-11-12)". Five of them are measured by a probe run: an entry a name guard skips has no report
line at all, against the report's own rule of one line per entry the parse read (`skipped` reads 0 for it);
a nameless schedule child raises `TypeError`, exit 1, and leaves half-written output; two device-group names
that read the same after the file-name rule write one file, and the second write replaces the first; the
written file has no trailing LF; a device group that states `  spaced  ` prints `description = "  spaced  "`.
Claims that did not survive re-measurement against the actual files are not recorded: `display_name` (the name
is nowhere in `src/`), `entry_name_field` (no such function), `parse_rules` (the parse set has no method of
that name), `_device_names` as a parse helper (it is the splitter's, at `src/split_device_groups.py:56`),
`sanitize` taking a name kind with a 40-character maximum and a trailing-underscore form
(`src/naming.py:30` takes one argument and states no length), `docs/STE_VOCABULARY.md` and
`tests/test_naming.py` (neither file exists), a whitespace pin at `tests/test_parse_helpers.py:439` (no pin
names the whitespace rule), the splitter running no gate against `src/api_to_terraform.py:20`
(`docs/DEVICE_GROUP_SPLITTING.md:71-72` states the gate run for it), `tools/sweep_facts.py` and
`tools/sweep_facts_report.txt` (neither file exists, and no markdown names `sweep_facts`), `tests/test_real_or_report.py`
described by `tools/README.md` as the read report (that index lists two scripts and no test file), the
interface matrix row naming `zone` and `virtual_router` (the row names `tag` only), and a §6 sorted-key rule
for `hcl_value` (no such rule), an entry skipped by a name guard being counted as `emitted` (the measured probe
counts `skipped` as 0 and prints no line for it), and the tool being silent for a device group with no address
or group objects (not measured).

Criterion 7. `to-do.md` lists F8.9 as open while `git log` records its steps 1 to 3 committed
(`720da9f`, `3d54163`, `88921c2`); `agent-status.md` names F8.9 as the next piece. `to-do.md` keeps completed
Phase 8A and Phase 8B detail.

Criterion 8. All actionable findings are recorded in `backlog.md`, section "Codebase audit findings
(measured 2026-11-11)", plus the additions this response records: the nine missing F8.9 pins, the corrected
schema-pin count, and the licensing line drift. No document outside an index was created.
