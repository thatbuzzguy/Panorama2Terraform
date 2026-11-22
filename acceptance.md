# Piece 11A.1 acceptance review — the selection vocabulary and the argument rule

Review record for commits `22e4401` (the argument rule and the pins), `f2a20b8` (the decision and the measurement)
and `c23920b` (the repair of the duplicated pin line), read at `c23920b`. The piece was not redone here: each
criterion is met, and only what the review found wrong is changed. The commits are not pushed.

## Criteria, as measured

1. What was already pinned is unchanged and passes (met). `container_coverage.is_scope_path` is still the one scope
   path definition the selection reads through; `unit_manifest.units` is still the only unit set and the piece adds
   no filter to it; the argument-error shape is the one `--path` states, read on a run;
   `tests/test_reference_edges.py::test_a_declared_parent_source_adds_no_dependency` passes unchanged;
   `tests/test_layout.py::test_the_indexes_name_every_document_under_them` passes, and the piece adds no module, so
   the `docs/ARCHITECTURE.md` §1 table names `codebase_state.py` only as pending work; the `src/` scans that read the
   writer, the environment name, the console line and the second naming rule pass unchanged.
2. What the piece states (met). `shared_arguments` declares `--selection`, so both entry points read one argument
   set, and `shared_checks` states the argument rule for it. It reads the shape through
   `container_coverage.is_scope_path`, the place through `container_coverage.path_place`, and the built-in fact
   through `container_coverage.PREDEFINED_PLACE`, so it states no path shape, no unit rule, no naming rule, no
   writer, no console line and no environment name of its own, and it asserts no exit code. The selection names the
   read set only, so `unit_manifest.units` stays the unit set. The file-source refusal is in path 1's `main()`, next
   to the `--path` and `--parent` block, because `--source` is path 1's argument and path 2 has none, so
   `shared_checks` cannot state a rule for a source it does not read.
3. The pins (met), with one wording correction at finding 3 below: each pin reads its fact through its owner rather
   than through a string the test states, the argument error is read from a run, and no pin reads a document word.
4. What stays outside the piece (met). No read rule, no merge rule and no report rule is written here, so a run that
   declares a selection writes the same bytes as the same run that declares none, which is what the pin
   `tests/test_api_path.py::test_a_selection_that_names_no_unit_is_an_argument_error_on_a_run` measures on the
   accepted case, and the committed goldens are unchanged. The `vsys` and device selection needs the live-target
   fact that names which device the run read, so it stays in `backlog.md` and no pin is written for it.
5. What the argument can decide (met, as measured). The no-unit fact is decidable at argument time for the built-in
   place only: no container table row names a built-in container, so no parse method runs over its response, the
   ledger holds no row, and `unit_manifest.units` names no unit for it. `shared` is accepted because a shared read
   builds a report row and `unit_manifest.SHARED_UNIT` names its unit. `devices` and `vsys` are accepted because the
   fact that names which device the run read is a live-target fact, and the argument reads no content, so it cannot
   decide that fact and no second rule is written for it.

## Pins, run one at a time

Each pin passes on its own, in the module that owns its rule:

- `tests/test_api_requests.py::test_a_selection_shape_is_read_through_the_one_scope_path_definition` — the shape
  through `is_scope_path`, the unit answer through `unit_manifest.units`, the shapes built through
  `api_requests.scope_path`, and the table paths outside the shape read through the table. It states no exit code.
- `tests/test_api_requests.py::test_the_selection_argument_states_no_rule_an_owner_states` — the argument rule read as
  a function body, so the pin reads what it states: the three owners are present, and no path shape, no unit rule, no
  naming rule, no writer, no console line and no environment name appears in it. It also reads that a run declaring
  no selection declares nothing.
- `tests/test_api_path.py::test_a_selection_that_names_no_unit_is_an_argument_error_on_a_run` — the exit code and the
  no-file fact read from a run, and the accepted case reads that a selection which names no read rule writes the same
  bytes as the run that declares none.
- `tests/test_shadow_coverage.py::test_a_selection_applies_to_the_api_source_only` — the file-source refusal read on a
  run, exit 2 and no file.
- `tests/test_container_coverage.py::test_a_predefined_path_is_read_by_the_one_scope_path_definition` — the shape, and
  the count of `PREDEFINED_PLACE` inside `container_coverage.py`, 4: the constant, the definition that reads it, and
  the definitions rule that reads it twice. `path_place` holds no copy of the name.
- `tests/test_api_path.py::test_the_entry_point_accepts_the_arguments_of_one_run_and_refuses_the_ones_that_name_one_source`
  — `selection` is in the accepted name list and the refusal word list is unchanged, because the selection names the
  read set and not a source.
- `tests/test_reference_edges.py::test_a_declared_parent_source_adds_no_dependency`, and the import rule: no test
  module imports another test module, and the pins read `PREDEFINED_PLACE_BODY`, `per_scope_response` and
  `written_bytes` through `tests/conftest.py`.
- `tests/test_api_requests.py` says seven groups and holds seven group headings, so the count its docstring states
  agrees with the file.

## What the review corrected

Three things were wrong, and no pin changed.

1. The gate line read "the 106 Python files". Measured at `c23920b`, `ruff format --check .` reads 106 files: 79
   Python files (`src/` 23, `tests/` 54, `tools/` 2) and 27 markdown files. The number is ruff's file count, not a
   count of Python files, so the gate line in `agent-status.md` and here now reads the 106 files it reads, 79 Python
   files and 27 markdown files.
2. "path_segments is the one place a path is split" and "path_place is the one place the place is read" are true for
   the two rules Piece 11A.1 put on the path, and they are not true for the `src/` set. Eight places split a path
   string for a fact of their own: `api_requests.list_container` (the container a membership row names first),
   `xml_input.ParsedSource.scope_container` (the place the record's own `scope` field states),
   `container_coverage.py` (the entry segment inside the record's scope), `entry_coverage.py` (the matrix row's
   element), `source_fetch.py` (the request path, and the element a response names), and
   `panorama_to_terraform.py` (the report's scope field, and the path suffix inside a state reference). No pin holds
   a single-split rule for the whole `src/` set, so the two docstrings in `src/container_coverage.py` now state the
   scope the pins ground, and the split sites are recorded in `backlog.md`. The pins that ground the scoped claim are
   `tests/test_api_requests.py::test_the_selection_argument_states_no_rule_an_owner_states`, which reads the shape,
   the place and the built-in fact through their owners and asserts `shared_checks` states no split, and
   `tests/test_api_requests.py::test_every_index_path_is_a_path_the_one_scope_path_definition_validates`, which reads
   the path the module builds through `ENTRY_SEGMENT` against the one definition.
3. Criterion 3 named "the group that holds the `--path` pins" in `tests/test_api_requests.py`. That module holds no
   `--path` pin: the `--path` pins are in `tests/test_api_path.py`. The two selection pins sit in group 5, the group
   that reads the module's rules through their owners, so the criterion now names that group.

## Gate, re-measured by the review

At `c23920b`, single-threaded: `ruff check .` clean at `py310`; `ruff format --check .` clean on the 106 files it
reads, 79 Python files and 27 markdown files; `python3 tools/check_documents.py` reports no finding;
`python3 -m pytest` passes 1,745 pins with the same 4 skip for the missing `tflint` binary — 1,749 pins in 53 test
modules, in 317.05 s, and the same 1,745 passed and 4 skipped on the tree that holds the corrections, in 436.09 s.
Run-to-run time varies, so both recorded runs are named. The per-module collection counts agree with the piece's
record: `tests/test_api_requests.py`
26, `tests/test_api_path.py` 36, `tests/test_shadow_coverage.py` 23, so the four new pins are 2, 1 and 1 in those
three modules. The 4 skips are the `tflint` pins in `tests/test_sanity_gate.py`.

## Tracking markdown

`to-do.md` holds Piece 11A.2 open and no completed-piece detail; `PLAN.md` names Epic 11 as open with the design
record; `backlog.md` holds the live-target items and the single-split finding; the documents and the indexes state no
test count, which `tools/check_documents.py` reads, and every test a document names exists.
