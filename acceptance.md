# Acceptance — `tflint` integration (Piece 11)

Criteria set 2026-11-18 for the `backlog.md` Nice-to-Haves item: the post-run gate gains the check that runs
`tflint` over the files it wrote. One section per decision, each with the pin or the measurement that holds it.

Owners: `docs/ARCHITECTURE.md` §4.6 for the gate rule, the severity rule, and the exit-code rule;
`docs/ARCHITECTURE.md` §3.2 for the console line shape; `src/sanity_checks.py` for the runtime home of the static
rules and for the rule set as data; `tests/conftest.py` for the binary and for the committed test material the pins
read; `docs/CODEBASE_ASSEMBLY.md` §14 for the file sets; `README.md` for the index and the command line;
`.github/workflows/python-tests.yml` for the CI gate; `tests/test_sanity_gate.py` for the pins.

Rules this piece works under, from `agent-status.md` §Rules to keep when writing documents:

- One owner document per rule; every other document links to it.
- No test counts in a document. A document names the test that pins a rule.
- A pin measures content or a name, never the wording of a document.
- A historical record is not kept in the markdown; the git history is the record.
- No pin is weakened. When a pin changes what it asserts, the reason is recorded here.

## Item 1 — tflint is an external command, and the check that runs it is gated

**Decision.** The tool imports only the standard library, so `tflint` cannot be a module the tool reads: it is an
external command the gate runs, the way `sanity_checks.check_terraform` runs `terraform`. `sanity_checks.py` stays
the runtime home for the static rules, and `check_tflint` is the check that runs the command.

The check is gated by a flag, `--tflint`, because the default gate reads only offline data and runs no external
binary. A call that did not ask for the check reports it as NOT RUN, the shape `check_terraform` already reports
for a caller that did not pass `--validate`.

- AC-1.1: `run_checks` runs no external command by default, and reports the tflint check as NOT RUN with the reason
  when the caller did not ask for it. Held by
  `tests/test_sanity_gate.py::test_the_tflint_check_reports_not_run_when_the_caller_did_not_ask_for_it`.
- AC-1.2: `--tflint` adds the check to a conversion, so the report names one result per unit directory and each
  result names the directory it ran on. Held by
  `tests/test_sanity_gate.py::test_the_tflint_flag_runs_the_check_on_a_conversion`.
- AC-1.3: `tflint` sits in `CHECK_ORDER` with the other rule that runs a command, in the position before it,
  because the two command checks sit together and the plan check stays last. Held by
  `tests/test_data_file_gate.py::test_check_order_puts_the_data_rule_after_the_block_rules` and by the report order,
  which the byte rule pins (`tests/test_sanity_gate.py::test_report_is_byte_identical_between_runs`).
- AC-1.4: the gate's existing offline rules are unchanged: the report counts, the report order, and the exit code
  are the same for a run that did not ask for the check. Held by the pins that read the report shape, unchanged by
  this piece. Four pins gained the new rule because the gate gained a rule, and none is weakened: each measures a
  list that names every rule, every argument, every check that did not run, or the checks a pin asked the gate to
  run, so the assertion is the same assertion over one more name —
  `tests/test_sanity_gate.py::test_gate_runs_and_writes_the_report` (the set that reports NOT RUN),
  `tests/test_data_file_gate.py::test_check_order_puts_the_data_rule_after_the_block_rules` (the order tuple),
  `tests/test_api_path.py::test_the_entry_point_accepts_the_arguments_of_one_run_and_refuses_the_ones_that_name_one_source`
  (the argument names), and
  `tests/test_api_path.py::test_content_with_no_live_only_fact_writes_the_same_tf_bytes_as_path_1`, which read the
  gate without running a command and so excluded one check from its PASS agreement; it now excludes the two command
  checks and asserts each is NOT RUN for both runs, so the agreement is measured over the checks the gate ran.

## Item 2 — the rule set is data in the runtime home, so no config file restates it

**Decision.** `sanity_checks.py` states the enabled rule set as data (`TFLINT_RULES`), and the run names each rule
through `--only`. `--only` also enables a rule that is off by default, measured 2026-11-18 with
`terraform_naming_convention`. So the codebase holds no `.tflint.hcl`: a config file would be a second statement of
the set the module already holds.

The §14 question answers to no set, because no file exists. Had the config file been a codebase root-set file, the
generated `README.md` file inventory and the two path builders in `write_path.py` would have to name it, which is
the reason it is not written. The committed probe pair is test material, so it is a set `README.md` names beside
the response set: `tests/tflint/probe.tf` and `tests/tflint/probe.json`, read through `tests/conftest.py`. No tool
rule reads it, so it is not corpus material.

- AC-2.1: the rule set is stated once, as data in `src/sanity_checks.py`, and the argument builder names exactly
  that set in sorted order. Held by
  `tests/test_sanity_gate.py::test_the_tflint_rule_set_is_data_in_the_gate`.
- AC-2.2: no `.tflint.hcl` exists in the tree, so no config file can restate the set, and the file inventory of
  both sets is unchanged. Held by the same pin, and by `tests/test_layout.py`, which reads the index names.
- AC-2.3: the run reads the files through the directory it ran on, so the answer names the file name inside the
  directory and no path above it. Measured 2026-11-18: with `--chdir` the answer names a path that climbs out of
  the tree, so the check sets the working directory instead, and the finding names the path from the codebase root,
  which is the unit directory plus the file name (`docs/CODEBASE_ASSEMBLY.md` §14).

## Item 3 — the findings tflint adds beyond the existing static rules

**Decision.** The enabled set is the eight rules that state a fact the gate states no rule for. Each is a fact
about the printed text, so a hand-written file is still a file the gate can refuse.

| Rule | What tflint reports | The gate rule it adds |
|---|---|---|
| `terraform_comment_syntax` | a `//` comment | none before: no gate rule reads the comment shape |
| `terraform_deprecated_index` | the legacy dot index on a list | none before |
| `terraform_deprecated_interpolation` | an interpolation-only expression | none before |
| `terraform_deprecated_lookup` | `lookup()` with two arguments | none before |
| `terraform_empty_list_equality` | a collection compared with `[]` | none before |
| `terraform_map_duplicate_keys` | a key stated twice in one map | none before |
| `terraform_naming_convention` | a block label outside `snake_case` | none before: the gate reads `naming.py` §5, which lowercases and keeps consecutive underscores |
| `terraform_unused_required_providers` | a declared provider no block in the unit uses | none before |

Rules the gate or the generator already state, so they are not in the enabled set:
`terraform_typed_variables` and `terraform_documented_variables` (every generated declaration carries `type` and
`description`), `terraform_required_version` and `terraform_required_providers` (the generated `provider.tf` states
both), `terraform_unused_declarations` for a variable (the `variables` gate rule reads both directions, and the tool
writes no `locals` or `output` block), `terraform_documented_outputs` (the tool writes no output block).

Rules that read a shape the tool writes none of, so they are out of scope:
`terraform_standard_module_structure` (a unit directory is the section-file set `write_path` states, not a standard
module, so it fires on every unit directory — measured 2026-11-18 on the committed goldens),
`terraform_json_syntax` (no `.tf.json`), `terraform_module_pinned_source`, `terraform_module_version`,
`terraform_module_shallow_clone`, `terraform_workspace_remote` (no module block, no workspace).

- AC-3.1: the enabled set and the already-stated set are data in `sanity_checks.py` and are disjoint. Held by
  `tests/test_sanity_gate.py::test_the_tflint_rule_set_is_data_in_the_gate`.
- AC-3.2: each rule in the enabled set answers for the committed probe content, so the pin compares the committed
  tflint output with the derivation from the set: one finding per rule. Held by
  `tests/test_sanity_gate.py::test_the_committed_tflint_output_reads_as_findings_through_the_harness`.
- AC-3.3: the gate states no naming rule of its own; `naming.py` §5 is the owner, and `check_tflint` reports what
  tflint answers. `naming.sanitize` answers consecutive underscores, which is the shape the naming rule reports.
  Held by `tests/test_sanity_gate.py::test_the_gate_states_no_second_naming_rule_for_the_shape_tflint_reports`.
- AC-3.4: the corpus instance of the naming fact is a measured fact, not an exception list: the enabled set answers
  nothing on the committed goldens and one finding on the accepted corpus, in `edge_quoted_dg_names`, file
  `scope.tf`, line 1, and the name it names is already the §5 shape, so the two rules disagree only on the doubled
  underscore the §5 shape keeps. Held by the binary pin
  `tests/test_sanity_gate.py::test_the_enabled_rule_set_answers_nothing_on_the_goldens_and_one_fact_on_the_corpus`.
  Measured 2026-11-18: 17 golden unit directories, nothing; 66 accepted fixtures, 174 unit directories, one finding,
  28.2 s for the pin.

## Item 4 — the severity rule and the exit-code rule

**Decision.** tflint reports three severities, and the gate maps them through one table it holds as data
(`TFLINT_SEVERITY`): `error` → FAIL, `warning` → FAIL, `info` → WARN. A warning is a shape the printed file holds,
so it is a broken output, the way `control_chars` reads a file; an info finding is an operator action, so it does
not change the exit code.

The tool's own exit codes are the check's exit-code rule, stated as data (`TFLINT_EXIT_CODES`): 0 answers no
finding, 1 answers an error entry, 2 answers an issue. The gate's exit code stays its own rule: 0 when no finding is
FAIL, 1 when one is.

- AC-4.1: the severity mapping and the exit-code table are data in `src/sanity_checks.py`, read by the check, so the
  check states no second mapping. Held by
  `tests/test_sanity_gate.py::test_the_tflint_severity_rule_and_the_exit_code_rule_are_data_in_the_gate`.
  Measured 2026-11-18, per rule on a probe that violates it: every rule in the enabled set answers exit 2, and seven
  rules report `warning`, which the mapping answers FAIL, while one rule reports `info`, `terraform_naming_convention`,
  which the mapping answers WARN. So the committed probe holds seven FAIL findings and one WARN finding.
- AC-4.2: a run that answers non-zero with nothing to report is a FAIL finding that names the exit code, never a
  silent pass. Held by
  `tests/test_sanity_gate.py::test_a_non_zero_tflint_run_with_nothing_to_report_is_a_fail_finding`.
- AC-4.3: a WARN does not change the exit code. Held by
  `tests/test_sanity_gate.py::test_the_enabled_rule_set_answers_nothing_on_the_goldens_and_one_fact_on_the_corpus`,
  which asserts the corpus fact is WARN, that the check reports WARN for it, and that the report is not failed.

## Item 5 — the skip, and what a pin may skip for

**Decision.** `check_tflint` reports SKIPPED for a missing binary, the shape `check_terraform` already states, and
the exit code stays with the rules that read the files. A pin that runs the binary skips only for a missing binary
and asserts on a non-zero run, so a skipped pin cannot hide a failure. A pin that does not run the binary reads the
committed tflint output, so it runs in every CI job.

- AC-5.1: `tests/conftest.py` is the one place the test set resolves the binary (`TFLINT`), the way it resolves
  `TERRAFORM`, so no pin resolves it a second time.
- AC-5.2: a missing binary is SKIPPED and the conversion still exits 0. Held by
  `tests/test_sanity_gate.py::test_tflint_without_the_binary_is_skipped_not_failed`, which runs no binary, so it runs
  in every job.
- AC-5.3: the pins that run the binary — the flag pin, the committed output agreement, the golden and corpus
  measurement, and the directory shape — skip only for a missing binary and assert on a non-zero answer. Held by
  those four pins.

## Item 6 — the report line and the console line

**Decision.** The check reports one finding per issue: the path from the codebase root, the line tflint names, the
rule name, and the message tflint wrote. Findings are sorted by (file, line, detail), which is the key the byte rule
needs. A tflint finding names no entry identity, so it cannot be a `container_coverage.console_line` line, and the
check states no console shape of its own: the gate's one finding shape prints it in the report and on the console, so
the two cannot disagree. A check that ran and reported nothing names the directory it ran on in the note, the shape
the plan check states.

- AC-6.1: the finding shape and the sort key are the gate's, read through `Finding.render()`. Held by
  `tests/test_sanity_gate.py::test_the_committed_tflint_output_reads_as_findings_through_the_harness`.
- AC-6.2: no module states a second console shape, and `sanity_checks.py` states no fact wording beyond the rule
  name and the message. Held by `tests/test_container_coverage.py::test_the_console_line_shape_is_stated_in_one_place`.
- AC-6.3: one result per unit directory the manifest names, and the result names the directory it ran on. Held by
  `tests/test_sanity_gate.py::test_the_tflint_check_runs_once_per_unit_directory_and_names_the_directory_it_ran_on`.
- AC-6.4: a tflint run writes nothing inside the directory it ran on, so a pin that reads a committed golden
  directory needs no copy of it. Measured 2026-11-18: the bytes of the committed goldens are unchanged after the pin
  ran the rule set over all 17 golden unit directories. Held by the same pin.
- AC-6.5: the gate holds one shape rule, and it is the answer of the command it runs, because the answer is not a
  file the tool wrote. The shapes of the files the tool wrote belong to the modules that wrote them, so the data rule
  states no shape rule of its own. Held by
  `tests/test_sanity_gate.py::test_the_tflint_rule_set_is_data_in_the_gate` (the gate has one read site, and it reads
  the answer) and by
  `tests/test_data_file_gate.py::test_no_block_rule_reads_a_data_file_and_the_data_rule_reads_no_tf_file`, which
  reads each row shape through its module. The second pin's shape assertion moved from the whole module to the data
  rule, because this piece gave the gate a shape rule for a set it did not write; the fact that the data rule states
  no shape rule is the same fact, measured on the rule that holds it.

## Item 7 — the committed test material, and what keeps it from drifting

**Decision.** The pins read two committed files, in the test material set `README.md` names: `tests/tflint/probe.tf`
(the content that violates each rule in the enabled set) and `tests/tflint/probe.json` (the answer tflint v0.66.0
with the bundled ruleset 0.17.0 gave for it, measured 2026-11-18). The pins read them through `tests/conftest.py`.

- AC-7.1: every rule in the enabled set names one finding in the committed output, so the pin compares the set with
  the answer instead of holding a count. Held by
  `tests/test_sanity_gate.py::test_the_committed_tflint_output_reads_as_findings_through_the_harness`.
- AC-7.2: the committed answer is the answer the binary gives for the same content, so a committed fact cannot
  drift from the rule it records. Held by
  `tests/test_sanity_gate.py::test_the_committed_tflint_output_agrees_with_the_binary`, which runs the binary and
  skips only for a missing binary.

## Item 8 — the CI gate

**Decision.** The pins that run the binary run in the `terraform-gate` job, which is the job that runs the whole
test set with the tool binaries present, so a new tflint step goes there and the job name stays, because six skip
messages and the tracking markdown name it. The step installs the pinned version, because the measured facts are
dated facts read from that version. The bundled Terraform Language ruleset needs no `--init` and no plugin install,
so the rule set runs with no network at test time. The matrix legs have no tflint, so the pins that run the binary
skip there.

- AC-8.1: the `terraform-gate` job installs `tflint` 0.66.0 before it runs `pytest`. Held by
  `.github/workflows/python-tests.yml`, the owner of the CI gate. No pin reads the workflow file, so this is recorded
  as the CI measurement, not as a pin.
- AC-8.2: no pin asserts a tflint version, so a newer binary is not a failure on its own. The pin that compares the
  committed answer with the live answer reports a difference as a finding, which is what a dated committed fact
  needs: a version that changes the answer for the same content is a drift, not a pass.

## Gate

Run in order, with no parallel runner: `ruff check .`, `ruff format --check .`, `python3 -m pytest`,
`python3 tools/check_documents.py`. Record the pin count before and after, the module count, and the time. The
baseline measured 2026-11-18 is 1,686 pins in 52 modules in 313.68 s, with no skips, `ruff check .` clean,
`ruff format --check .` clean on the 100 Python files, and `check_documents.py` reporting no finding. No pin is
removed from the full run.

The binary pins are measured twice: on this machine, where `tflint` is absent and those pins skip, and with the
binary present, where the same set passes with no skips. Record both.

Measured 2026-11-18, in that order: `ruff check .` clean, `ruff format --check .` clean on the same 100 Python
files, and `python3 tools/check_documents.py` reports no finding. 1,697 pins in 52 modules, all pass: 1,686 before,
11 new, all in `tests/test_sanity_gate.py` (99 to 110). Measured both ways, as two runs of the same set, so the two
times differ by run noise and not by the pins that skipped: without the binary, 1,693 pass and 4 skip for the missing
binary, 286.45 s; with tflint 0.66.0 present, all 1,697 pass, 280.97 s. No pin is removed from the full run, and the
four pins that changed what they read are recorded in Item 1 and Item 6.

Finished 2026-11-18: Piece 11 is marked complete in `to-do.md`, the Nice-to-Haves entry in `backlog.md` is narrowed
to what stays open, `agent-status.md` §Current position names the piece, and the commit holds only the files this
piece changed; `AGENTS.md` is not staged, committed, reverted or modified, because it holds an uncommitted user edit.
