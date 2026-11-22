# Piece 11A.2 acceptance criteria — the targeted read set

Criteria for Piece 11A.2, the targeted read set in `src/api_requests.py` (`docs/MULTI_RUN_CODEBASE.md` §2 rule 3).
Piece 11A.1 landed at `a4ead15` and is not reopened here. The measured facts below are from the committed response
set, read through `tests/conftest.py::api_producer`; nothing here calls a network or a live target.

## Criteria

1. **Offline only.** Every response a pin reads is a committed file in `tests/responses/`, read through
   `tests/conftest.py::api_producer`, or the module's own fixture bodies read through the injected producer. A fact
   that cannot be read offline is recorded in `backlog.md` and not asserted: the `vsys` and device selection needs the
   live-target fact that names which device the run read, and it stays in `backlog.md`.
2. **The targeted read set is the selected scope plus the membership facts a unit identity cannot state on its
   own**, read through `api_requests`, so `api_to_terraform.run_order` states no read rule of its own. The reason no
   list is dropped for a selection is measured: `parse_associations` reads a membership fact only from the response
   that holds the container the list names, and the response for an entry holds the entry itself, so an entry read
   states no membership fact. With no selection the read set is `membership_lists()`, so a run that declares no
   selection is the run it is today.
3. **The targeted name set is the names inside the place the selection names, or the entry the selection names plus
   the names the membership tables hold for it**, read through `LIST_JOIN` and the tables `parse_associations`
   returns. A name the selection excludes is not in the set.
4. **A name the selection excludes is not an index entry, so the join reports no finding for it.** `scope_index`
   builds the targeted index from the targeted names, `unit_findings` and `join_units` read the unit set through
   `unit_manifest.units` and the index through the targeted index, and `sanity_checks.check_request_set` turns the
   pairs into findings without stating a name rule of its own. The entry the selection names enters the index through
   the one scope path definition, because the run read the response for it.
5. **A place read that holds a name the selection excludes is not refused.** `join_response` checks the names inside
   a response against the names the targeted index read for that container, so an extra name inside gains no entry,
   as the join already states.
6. **The pins**, in the module that owns the rule: a new group in `tests/test_api_requests.py` for the read set, the
   name set and the join's answer, and a new group in `tests/test_api_path.py` for the read set as the run reads it,
   the findings the gate reports for a targeted run, and the record the run wrote. Each pin reads its fact through its
   owner; no pin reads a document word; no test module imports another test module; shared test facts stay in
   `tests/conftest.py`.
7. **The standing rules are not broken.** `unit_manifest.units` is the only unit set, `container_coverage.is_scope_path`
   the only path shape, `api_requests.LIST_JOIN` the only join, `source_fetch` the only reader,
   `container_coverage.console_line` the only console line, and `naming`/`unit_manifest.directory_name` the only naming
   rule. The join stays a data module: findings print through the gate, and `run_order` stays the only place the read
   order is stated. No second join rule, no second reader, no second console line, no second naming rule, no merge
   rule, and no report rule is written here.
8. **The pin that asserts byte equality between a selection run and a full run changes**, because the selection now
   names a read rule. `tests/test_api_path.py::test_a_selection_that_names_no_unit_is_an_argument_error_on_a_run`
   currently asserts that a run with a selection writes the same bytes as the run that declares none; that assertion
   is false once the read set narrows, so the pin keeps the argument-error part and reads the difference the read rule
   creates instead.
9. **The gate**, run single-threaded: `ruff check .`, `ruff format --check .`, `python3 tools/check_documents.py`,
   `python3 -m pytest`. The measured counts are recorded below, and a golden is regenerated only if printed output
   changes. Before the piece: 1,749 pins in 53 modules, 1,745 passed and 4 skipped (the `tflint` pins), and
   `ruff format --check .` reads 106 files (79 Python, 27 markdown).
10. **The documents**: `docs/MULTI_RUN_CODEBASE.md` §2 rule 3 names the module and the pins, and
   `docs/API_CONVERSION_PATH.md` §3 names the join's answer for a targeted run; plain literal wording,
   ASD-STE100, no metaphor, no emoji, no test count in a document, and every test a document names exists.

## Measured on the committed response set, before the change

Read through `tests/conftest.py::api_producer` on the committed files, one ledger, no network:

- The committed set holds responses for: the whole-config export, `show system info`, the `device-group` place, the
  `shared` place, and `device-group/entry/Production-DG`. The `templates` and `template-stack` places have no
  committed response, so the pins for those facts read the module's fixture bodies through the injected producer.
- For any selection the run reads the four membership lists, so a selection narrows no list today. Measured with
  `--selection device-group/entry/Office-FW`: four requests, one answered by a committed response.
- `parse_associations` on the committed entry response (`device-group/entry/Production-DG`) returns no table, because
  the response holds the entry itself and the method reads `.//device-group/entry`: an entry read states no membership
  fact on its own.
- `join_response` refuses a place read when a name the index read for that container is missing inside the response:
  with the fixture tables the index read `Datacenter-FW`, and the committed `device-group` response holds only
  `Office-FW` and `Unassigned-DG`.
- `unit_manifest.units` names a unit for `Unassigned-DG`, a name inside the response with no index entry, because the
  ledger holds a row for it. `join_units` answers it with the place entry, so it is a pair, not a finding.
- `unit_findings` on the committed read reports three findings: the `template-stack` entry, the `templates` entry, and
  `device-group/entry/Office-FW`, each read with no rows. `check_request_set` prints those three as WARN findings.
- The selection `device-group/entry/Production-DG` is not an index entry today, because no membership list read it.

## Measured by the pins, after the change

The pins read the module's own fixture bodies through the injected producer; no pin reads the network.

- A targeted run reads the four membership containers and then only the names the name rule states. Measured on the
  content `tests/test_api_path.py` holds: the run that declares no selection reads `device-group`, `templates`,
  `device-group/entry/Office-FW` and `templates/entry/HQ-Networks`; the run that selects `device-group` reads the
  first three and not the fourth.
- `targeted_read_set` answers the four lists for every selection shape the pins read, so no list is dropped.
- `targeted_names` answers the names inside the selected place for a place selection, and the entry plus the names the
  tables hold for it for an entry selection. `template-stack/entry/Branch-Stack` answers
  `(template-stack, Branch-Stack)` and `(templates, HQ-Networks)`; `Datacenter-FW`, which the selection excludes, is
  not in the set, and `fw-1.example.com`, a table key, is not in it.
- The targeted index holds no entry for the excluded name, so `unit_findings` reports no finding for it: the whole set
  reports one for `templates/entry/HQ-Networks` and the targeted set reports none for it. `unit_manifest.units` names
  the same units both ways, and `join_units` answers the excluded unit with the place entry, so it stays a pair.
- A place read that holds a name the selection excludes is not refused: on the committed `device-group` response the
  whole set read `Datacenter-FW`, which the response holds no entry for, and the targeted set reads
  `Office-FW` only, so the same bytes are accepted.
- A targeted run writes the same file set as a run that declares no selection; its bytes differ because the name rule
  reads one entry fewer, and its record names only the read set.

## Gate, as measured by the piece

Measured on this piece, single-threaded:

- `ruff check .`: clean at `py310`.
- `ruff format --check .`: clean on 106 files (79 Python, 27 markdown).
- `python3 tools/check_documents.py`: no finding.
- `python3 -m pytest`: 1,754 passed and 4 skipped (the `tflint` pins), 1,758 pins in 53 test modules, which is the
  1,749 pins before the piece plus the 9 new pins. Read through the per-module collection counts:
  `tests/test_api_requests.py` collects 32 (was 26), `tests/test_api_path.py` collects 39 (was 36). The committed
  goldens are unchanged. Measured in 311.05 s.

## Pins that hold the piece

Nine new pins, in the module that owns the rule.

`tests/test_api_requests.py` (the targeted read set group):
`test_the_targeted_read_set_keeps_every_list_a_single_read_cannot_state`,
`test_the_targeted_name_set_is_the_names_inside_the_place_or_the_names_the_selection_owns`,
`test_a_name_the_selection_excludes_gains_no_index_entry`,
`test_the_join_reports_no_finding_for_a_name_the_selection_excludes`,
`test_a_place_read_that_holds_an_excluded_name_is_not_refused`, and
`test_the_entry_the_selection_names_enters_the_index_through_the_one_path_definition`.

`tests/test_api_path.py` (the targeted read set group):
`test_a_targeted_run_reads_the_lists_and_the_names_the_selection_states`,
`test_the_join_reports_no_finding_for_a_name_the_selection_excludes`, and
`test_the_record_names_the_read_set_in_run_order_for_a_targeted_run`.

Three pins changed, and no pin was removed:
`tests/test_api_path.py::test_the_run_order_is_the_membership_lists_then_the_index_entries` reads the order through
`api_requests.targeted_read_set` rather than `api_requests.membership_lists`, because the entry point now reads the
read set through that rule; `test_the_entry_point_states_no_rule_an_owner_states` holds `targeted_read_set` and
`targeted_names` as `api_requests`' rules; and
`test_a_selection_that_names_no_unit_is_an_argument_error_on_a_run` keeps the argument-error part and reads the
difference the read rule creates, because the byte equality it held is false once a selection names a read rule.
