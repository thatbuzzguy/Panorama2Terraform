# Gate and CI

This document is the owner of the gate and CI rules. `docs/README.md` names it, and `README.md`, the root
index, names it too. `agent-status.md` keeps the status, the links and the measurements it recorded, and it
states no rule of its own.

Each rule here names the test that pins it. A rule with no pin is stated as a rule a person follows when they
run the commands, and that is recorded as such. This document states no test count; the count lives in
`agent-status.md` and the git history (`docs/WRITING_RULES.md` rule 2).

Three rule sets are outside this document and are not restated here:

| Rule | Owner |
|---|---|
| The layout, the flat test rule, `tests/conftest.py` as the one shared helper file and the one place the path to each test set is built, and the rule that the full run is the default gate | `docs/ARCHITECTURE.md` §1.1 |
| The writing rules, including the rule that a wording check lives in `tools/check_documents.py`, which the test set does not read | `docs/WRITING_RULES.md` rule 4 |
| The post-run gate on the output a run wrote, the two checks it gates by a flag, and the NOT RUN answer when the call asked for neither | `docs/ARCHITECTURE.md` §4.6 |

## Gate size

1. No smaller default gate is adopted. The full run `docs/ARCHITECTURE.md` §1.1 states is the default gate,
   and nothing is taken out of it.
2. A smaller run is a working loop on one area, as an explicit command-line selection. The full run runs after
   it, before a result is recorded or the work is committed.
3. A working loop is not a mark or a skip, for the reason `docs/ARCHITECTURE.md` §1.1 states. The suite states
   no marks, and `tests/conftest.py` states none, so a smaller set cannot become the default.
4. The plan check pins and the corpus pins stay inside the full run, because they carry the tool's promises and
   they are the slowest pins. `docs/ARCHITECTURE.md` §1.1 owns that reason, so this document keeps the decision.
5. The document review is not part of the test set, so a recorded gate measurement names it as its own run and
   keeps a document-review result separate from a pin result (`tools/README.md`).
6. No pin holds the gate size, because a pin holds code and a name, not how a person runs the commands. The pin
   that holds this document's place in the index is
   `tests/test_layout.py::test_the_indexes_name_every_document_under_them`.

## The shared test definitions

The rule that `tests/conftest.py` is the one shared helper file, that a fact more than one test module reads is
stated once there, and that no test module imports another test module is owned by `docs/ARCHITECTURE.md` §1.1.
This section names the two resource-line patterns and the rule each serves. No test module defines a pattern of
its own.

1. `tests/conftest.py::RESOURCE_RE` answers the resource type for the pins that read the emitted type set. The
   set is read through `tests/conftest.py::emitted_types` over the committed goldens, and the pin that reads it is
   `tests/test_resource_mapping.py::test_emitted_types_match_goldens`.
2. `tests/conftest.py::RESOURCE_ADDRESS_RE` answers the same line with the local name captured, for the pins that
   read `findall` as pairs: `tests/test_dependency_wiring.py::test_local_names_are_sanitized_name_plus_digest` and
   `tests/test_dependency_wiring.py::test_vpn_references_and_brown_field_fallback`. A pattern with one capture
   group cannot serve a pin that reads pairs, so the two patterns stay two.
3. Both patterns require the block brace, so neither pattern is broader than the other, and no pin passes because
   a merged pattern is wider. The measurement that settled this is recorded in `backlog.md`. No pin holds the
   patterns as data: the pins read them as data from `tests/conftest.py`.

## The Python floor and the CI legs

1. `pyproject.toml` is the owner of the Python floor, and the CI legs read the floor through it. The floor is the
   pin `pyproject.toml` holds, 3.10, and `target-version` equals the floor, so the lint gate enforces the spelling
   the project writes.
2. The CI legs are the four minor versions `.github/workflows/python-tests.yml` names, 3.10, 3.11, 3.12 and 3.13.
   Each is a minor version and never an exact patch, because a runner image has no hosted build for an exact patch.
   The workflow names the legs and states no floor of its own, so no leg runs a Python below the floor the lint
   gate enforces.
3. The spelling the gate enforces at the floor is one spelling: `X | None` for an optional value, the callable rule
   read from `collections.abc`, and `strict` stated at every `zip` call. The pins that read the `collections.abc`
   spelling are `tests/test_reference_edges.py::test_the_module_resolves_no_name_and_records_no_name` and
   `tests/test_source_fetch.py::test_source_fetch_imports_are_standard_library`.
4. No pin reads `pyproject.toml` or the workflow file, so a floor or a leg moves by hand. `README.md` and
   `docs/USAGE_GUIDE.md` state the same value as the run requirement, and the owner they read it through is
   `pyproject.toml`, so the wording they state and the level the gate enforces cannot move apart.

## The pins that run an external command

1. A pin that runs `tflint` or `terraform` skips only for a missing binary, and it asserts on a non-zero run. With
   the binary present, a failed run is a finding and not a skip, so a missing provider cache or an unreachable
   registry reads as a failure.
2. The `terraform-gate` CI job is where these pins run, because that job has both binaries. The matrix job runs the
   same set on runners with no binary, where the pins skip.
3. The test set resolves each binary in one place, `tests/conftest.py::TERRAFORM` and `tests/conftest.py::TFLINT`,
   so no pin resolves a binary a second time and the skip rule stays one rule.
4. `tests/conftest.py::provider_schemas` is the owner of the skip rule for the pins that read the provider schema
   through it. It skips only when no `terraform` binary is present, and a failed `terraform init` is a failure.
5. The two skip pins clear `PATH`, so they measure the same answer on a machine that has the binary, and they run
   in every CI job:
   `tests/test_sanity_gate.py::test_validate_without_the_binary_is_skipped_not_failed` and
   `tests/test_sanity_gate.py::test_tflint_without_the_binary_is_skipped_not_failed`.
6. A pin that reads which directory one of the two checks ran on passes no binary, so it runs on a machine that has
   neither and reads the directory from the result:
   `tests/test_write_path.py::test_the_plan_check_runs_on_one_directory_per_unit`. The pins that read a non-zero run
   through a binary are
   `tests/test_sanity_gate.py::test_a_non_zero_tflint_run_with_nothing_to_report_is_a_fail_finding` and
   `tests/test_sanity_gate.py::test_terraform_check_failure_is_a_fail_finding`.

## The tool pins and their owners

Each tool pin has one owner, and a document names the owner it reads the value through. A document states a version
only as the pin itself, or as the measurement it made.

| Pin | Owner | The test reads it through |
|---|---|---|
| The Terraform minimum | `src/commit_actions.py::TERRAFORM_MINIMUM` | `tests/conftest.py::declared_terraform_minimum` |
| The provider version | `tests/conftest.py::declared_provider`, read from the golden `provider.tf` | `tests/conftest.py::provider_schemas` |
| The CI Terraform version | the `terraform-gate` job of `.github/workflows/python-tests.yml` | no pin reads the workflow |
| The tflint version | the same job, and the committed answer measured on it, `tests/tflint/probe.json` | no pin reads the workflow |

1. The pins that read the Terraform minimum read it through its owner and state no copy of it:
   `tests/test_commit_actions.py::test_the_generated_terraform_block_declares_the_minimum`,
   `tests/test_commit_actions.py::test_the_generated_readme_names_the_file_and_the_minimum`, and
   `tests/test_commit_actions.py::test_the_action_file_header_states_the_minimum_through_its_owner`. The committed
   goldens carry the same value, so a change to the minimum is a golden change.
2. The provider version has its owner in the test set, and `src/` reads nothing under `tests/`, so the print site
   in `src/panorama_to_terraform.py` states the version as a literal. `backlog.md` records that the one-owner rule
   holds in the test set for this pin, and that the fan-out is accepted.
3. A recorded measurement names the binary that answered it. The machine measurement names the binary on the
   machine, and a measurement taken on the CI line names the CI version, so the two lines are not read as one
   number. A gate number measured on the CI line needs a binary held outside the repository, which `backlog.md`
   records.

## What this document does not cover

The shape-table and write-path watch list is outside this document. It needs one owner document named by
`docs/README.md`, holding each watched rule with the link to the owner document or module that already states it and
stating no restatement. Its name is taken as `docs/WATCHED_RULES.md`, and the piece stays open in `to-do.md`.
