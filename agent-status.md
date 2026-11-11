# Agent Status

## Current position — the git history

The main line is the branch `history-rewrite`, built in the worktree
`/home/ryan/.local/share/opencode/worktree/1670f9/history-rewrite`. It holds the 9 upstream commits
with their hashes and their author `devnullNZ <gordon@gswsystems.com>`, then the 46 phase 2 commits
with the author `rdavidbrown@live.com`, then the 124 commits after Feature Drop 2. The two squashed
Feature Drop commits are replaced by the 46 commits that produced them, so the per-commit detail is in
the main line. No file content, no commit message and no author date changed. The tree at the landing
point equals `development`'s tip tree. No branch pointer is moved and nothing is pushed, so
`development`, `dev` and `main` stay where they are until the landing is confirmed. The open pieces for
the landing are in `to-do.md`, and the criteria are in `acceptance.md`.

## Current position

F8.9 is complete (Epic 8, Phase 8C, the entry point), and it is the piece that decides the run order:
`src/api_to_terraform.py` reads the membership responses first, in the order
`api_requests.membership_lists()` names them, then the entries `api_requests.scope_index()` names in index order,
and it is the only place that states that order, because `api_requests.py` states no read order and
`provenance.py` rule 6 states no read rule for a path 2 run. One response is read once, so a container two lists
name (`template-stack`) enters the order at the first place a list names it. The entry point joins the
per-response tables in run order through the one join rule (`panorama_to_terraform.join_value`), and
`generate_run` takes the run view as an argument, so the join is the entry point's decision and path 1 builds the
same view for its one source. The entry point adds no argument of its own beyond the shared set, accepts no
argument that names one source, reads the environment name through `source_fetch.API_KEY_ENV`, prints only through
the owners' console lines, writes no file outside `write_path.py`, and calls `generate_run`, so it states no parse
order and no block builder. It passes the index it built to the gate, so the join findings print through the gate
and the exit code is the gate's decision. The generated `README.md` names the entry point that wrote the codebase,
and the name is an argument, so the label builder states no entry point of its own. The rule is stated in
`docs/API_CONVERSION_PATH.md` §6 with its pins named, and `README.md`, `docs/README.md` and
`docs/ARCHITECTURE.md` §1 name them.

The pins for this piece, in `tests/test_api_path.py` group 8:
`test_the_run_order_is_the_membership_lists_then_the_index_entries`,
`test_the_entry_point_joins_the_tables_across_the_responses_it_read`,
`test_the_run_sequence_is_stated_once_and_both_entry_points_call_it`,
`test_the_run_view_answers_the_entry_protocol_through_the_ledger_that_holds_the_entry`,
`test_the_run_view_states_no_row_shape_and_no_field_name_of_its_own`,
`test_the_entry_point_accepts_the_arguments_of_one_run_and_refuses_the_ones_that_name_one_source`,
`test_the_entry_point_passes_the_index_it_built_to_the_gate_and_keeps_the_gate_code`,
`test_the_entry_point_states_no_rule_an_owner_states`, and
`test_the_report_names_each_response_the_run_read_in_run_order`; plus
`tests/test_variables.py::test_the_entry_point_names_no_environment_name_of_its_own` and
`tests/test_site_data.py::test_the_readme_names_the_entry_point_that_wrote_the_codebase`. The three pins that read
the run sequence read `generate_run` rather than `main()`, because the sequence moved to the run function. No pin
calls a network: every path 2 pin runs the pipeline in process with the injected producer.

Measured run order for the committed set: `device-group`, `templates`, then `device-group/entry/Office-FW` and
`templates/entry/HQ-Networks`. The record file the run wrote names the same order, and the report names those four
sources in the same order. `panorama_to_terraform.failed` states the unexpected-error shape once, so both entry
points call it and neither prints a console line of its own.
The licensing rule is complete on branch `licensing`, in the worktree
`/home/ryan/.local/share/opencode/worktree/1670f9/licensing`. It added no pin, because it is a document rule,
and the choice to keep the notice set unpinned is recorded in `backlog.md`. `docs/LICENSING.md` is the owner
document: the fork source (`gswsystems/Panorama2Terraform`, v4.0.2, commit `92cb2a3`, 2025-12-09), the two
holders, the split measured through `git blame` (2,172 upstream lines against 57,157 ours, and 588 against
50,008 inside `src/`, `tests/` and `tools/`), the rule that the inherited file set is measured by `git blame`
and not decided, and the scope of each grant. `LICENSE-COMMERCIAL` is the upstream author's grant, so it covers
the upstream parts only, and this project grants no commercial terms for its own contributions. The word
"non-commercial" is not used as a license name, because AGPL v3 permits commercial use and §10 does not allow
an extra non-commercial condition on a derivative work, so the choice reads as "AGPL v3 only". Two notices were
corrected, `src/source_fetch.py` and `src/xml_input.py`, because they hold no upstream line; the two modules
that hold upstream lines keep the upstream notice, and no header was added to a module that has none.
`docs/DUAL-LICENSING-EXPLAINED.md` is removed, and `README.md`, `docs/README.md`, `docs/USAGE_GUIDE.md` and
`docs/ARCHITECTURE.md` §1.1 link to the owner document instead of restating the rule. Gate: `ruff check .`
clean, and 1,641 pins, the same count as before the change.
