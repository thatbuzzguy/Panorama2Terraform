# Acceptance criteria — F8.9, the path 2 entry point (Phase 8C)

## Scope

The rule F8.9 states: the entry point is the place that decides the run order, and nothing
else. `api_requests.py` owns the scope fact table, `container_coverage.py` owns the section
model, `entry_coverage.py` owns the entry protocol, and each data file owner builds its own
bytes. What is left, and what only an entry point can decide, is which response the run reads
first, how the per-response tables are joined into one set for a run that read more than one
response, and how the run reports what it read.

F8.9 covers:

- The entry point `src/api_to_terraform.py`: the arguments, the run order, the cross-response
  join, the gate call, and the exit codes.
- The run view for a set of responses: the entry protocol answered through the ledger that
  holds the entry, and the parse methods answered per response and joined in run order.
- The one run sequence, stated in one function that both entry points call, so path 2 writes
  the same `.tf` bytes as path 1 for the same content.
- The `README.md` label that names which entry point wrote the codebase.
- `docs/API_CONVERSION_PATH.md` §6 states the run order and the join rule in the present
  tense and names the pins that hold them.

F8.9 does not cover the byte agreement pin between the two paths for a fixture with no
live-only fact, which is F8.10. The vsys scope fact, the device-fact record scope, and the
live-only facts stay in `backlog.md`.

## The rule, in one sentence

The entry point decides the run order and joins the per-response tables; every other rule has
one owner, and both entry point call the same run sequence.

## The criteria

1. **The run order is the entry point's decision, and it is stated once.** The run reads the
   membership responses first, in the order `api_requests.membership_lists()` names them, then
   the entries `api_requests.scope_index()` names in index order. No module states this order:
   `api_requests.py` states no read order, and `provenance.py` rule 6 says the read order for a
   path 2 run is the run order's decision. The order is read back from the record file the run
   wrote, because the record is the run's own statement of what it read and in what order.

2. **The cross-response join is the entry point's decision.** `api_requests.py` keeps no merge
   rule, so the tables `parse_associations` answers stay per response, and the entry point is
   what joins them. The join names the response each membership fact came from, which path 1
   cannot state: the same content read as one whole-config export gives one fact, and read as
   two per-scope responses gives two. The run view answers the join as the set the index reads,
   in run order.

3. **The run sequence is stated in one place, and both entry points call it.** The parse order
   and the emission order cannot be derived from data: `container_coverage.CONTAINER_TABLE` is
   not the parse order, it holds no `service_object` row, and the emission order is not the
   parse order. So the sequence lives in one function, `panorama_to_terraform.generate_run`, and
   neither entry point states a parse order of its own. Path 1 calls it with one response and
   writes the same bytes as before; path 2 calls it with the set it read, which is what makes
   F8.10 possible.

4. **The run view answers the entry protocol and states no rule.** It holds the responses in run
   order and answers the protocol through the ledger that holds the entry: `row_for`, `entries`,
   `mark_for`, `parents`, `destination`, `is_report_entry`, `line_of`, `scope`, and the source
   part. It states no row shape, no field name, no naming rule, no sort rule, no writer, no
   console line, and no environment name. It builds no tree across responses, because F8.5 keeps
   one line map per response.

5. **The arguments mirror path 1's api source.** The entry point accepts `--host`, `--cache-dir`,
   `--offline`, `--insecure`, `--output-dir`, `--max-input-bytes` through
   `source_fetch.add_max_input_argument`, `--validate`, `--data-blocks`, `--import-blocks`,
   `--state`, `--workspace`, and `--prune-cache`. It accepts no argument that names one source:
   no input file, no `--source`, no `--path`, no `--parent`, because the request set is the
   scope set and the parent walk stays inside one response (F8.5). The words and the exit codes
   are the same as path 1's: an argument error exits 2, a refused input exits 1 and writes no
   file.

6. **The gate gets the index the entry point built.** `run_checks` reports `request_set` as NOT
   RUN when it has no index, so the entry point passes the index it built and the run view. Path
   1 still passes no index, because it read no request. The join findings print through the gate,
   so the entry point prints no join block of its own, and the exit code stays the gate's
   decision.

7. **The entry point states no rule an owner states.** It names no environment name of its own:
   it reads `source_fetch.API_KEY_ENV`. It defines no second naming rule, no second writer, no
   second console line, no container part, no position part, no scope fact, no section fact, no
   unit rule, no join rule, no check, no report section, and no block builder. It prints the
   blocks through the owners' block builders.

8. **The report names each response the run read, in run order.** `generate_conversion_report`
   answers the source line as the run's name, and a run of one response names that response, so a
   path 1 report is byte-identical. The parts that need a full ledger are answered per response
   and concatenated in run order; the parts that read the row set read the merged set.

9. **The `README.md` label names the entry point that wrote the codebase.** The label is fixed
   text, it states no row, no value, no mapping result, and no count, so the path name it states
   is digit-free. Path 1's label names `panorama_to_terraform.py` and path 2's names
   `api_to_terraform.py`; two runs on the same bytes write the same bytes.

10. **No pin calls a network, and no pin names a path outside `conftest.py`.** Every path 2 pin
    runs the pipeline in process with the injected producer, and a fact read from a run comes
    from the run's own ledger or from the record file the run wrote.

## The pins that hold these criteria

In `tests/test_api_path.py`, the entry point group:

- `test_the_run_order_is_the_membership_lists_then_the_index_entries` — criterion 1, read from
  the record file the run wrote.
- `test_the_entry_point_joins_the_tables_across_the_responses_it_read` — criterion 2.
- `test_the_run_sequence_is_stated_once_and_both_entry_points_call_it` — criterion 3, including
  the pins that read the sequence, which are migrated from `main()` to the run function.
- `test_the_run_view_answers_the_entry_protocol_through_the_ledger_that_holds_the_entry` —
  criterion 4.
- `test_the_run_view_states_no_row_shape_and_no_field_name_of_its_own` — criterion 4.
- `test_the_entry_point_accepts_the_arguments_of_one_run_and_refuses_the_ones_that_name_one_source`
  — criterion 5, and the exit code for a bad argument.
- `test_the_entry_point_passes_the_index_it_built_to_the_gate_and_keeps_the_gate_code` —
  criteria 6, and the exit code for a refused input.
- `test_the_entry_point_states_no_rule_an_owner_states` — criterion 7.
- `test_the_report_names_each_response_the_run_read_in_run_order` — criterion 8.

In `tests/test_variables.py`:

- `test_the_entry_point_names_no_environment_name_of_its_own` — criterion 7, in the shape of the
  pin that scans the `src/` set for the environment name.

In `tests/test_site_data.py`:

- `test_the_readme_names_the_entry_point_that_wrote_the_codebase` — criterion 9.

The three pins that read the run sequence from `main()` — `tests/test_scope_objects.py`,
`tests/test_commit_actions.py`, and `tests/test_site_data.py` — are migrated to read the run
function, because the sequence moved there.
