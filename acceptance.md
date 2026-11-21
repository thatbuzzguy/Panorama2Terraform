# Piece 11A.1 acceptance criteria — the selection vocabulary and the argument rule

Record for Piece 11A.1, commit `22e4401` (the argument rule and the pins); the decision and the measurement are
carried in the tracking markdown that follows it. The criteria below are the agreed criteria and are not restated
as a result. Every criterion is met, and the result is recorded at the end. The commits are not pushed.

Current task: state the shape a run names as its read set, and the argument rule for a selection that names no
unit in that set. The design rule is `docs/MULTI_RUN_CODEBASE.md` §2, rules 1 and 2. No code is written until
these criteria are agreed.

This piece adds no rule of its own. It states the selection as data read through the rules that already own the
shape, so acceptance is that no second rule appears anywhere.

## Criterion 1 — what is already pinned and must not change

- `container_coverage.is_scope_path` is the one scope path definition, and the pin
  `tests/test_container_coverage.py::test_a_predefined_path_is_read_by_the_one_scope_path_definition` holds the
  shape: the path names the place or one entry inside it. A selection must be read through this function, so a
  piece that defines a second path shape is a finding.
- `unit_manifest.units` is the run's unit set, and a unit exists only when the ledger has a row in it. A
  selection that dropped units from the set the ledger names would give the unit rule two shapes, so a run that
  reads a whole export declares no selection and no piece may add one.
- The argument-error shape is the one `--path` already states: a path that names no unit the run read is an
  argument error, exit 2, and the run writes no file. The selection reads the same shape, so no second error
  shape appears.
- `--parent` names the ancestor the run reads as a reference source, and the pin
  `tests/test_reference_edges.py::test_a_declared_parent_source_adds_no_dependency` holds that such a source names
  no unit. A selection that names an ancestor must keep that fact: the ancestor enters the read set and names no
  unit.
- `tests/test_layout.py::test_the_indexes_name_every_document_under_them` holds the index rule, so
  `docs/MULTI_RUN_CODEBASE.md` must be named in `docs/README.md`, which it is, and the §1 module table names
  `codebase_state.py` only when that module lands, so this piece adds no module and the table is unchanged.
- The pins that scan the `src/` set read every module: the writer scan, the environment-name scan, the
  console-line scan, and the second-naming-rule scan. This piece adds no writer, no environment name, no console
  line, and no naming rule, so those pins are unchanged.

## Criterion 2 — what the piece must state

1. A selection names the read set only. The run's unit set stays `unit_manifest.units(ledger)`, so the selection
   never names a directory.
2. A selection is a scope path read through `container_coverage.is_scope_path`, so it applies to the api source
   the way `--path` and `--parent` do, and no file-source piece can state a selection of its own: for a file
   source, targeted conversion is the splitter's one file per device group plus `--parent`.
3. A selection that names no unit in the run's read set is an argument error, exit 2, and writes no file, read
   through the shape `--path` already states.
4. A selection is data: it states no unit rule, no identity rule, no naming rule, no path rule, and no console
   line. The vocabulary lives in `panorama_to_terraform.py` (`shared_arguments` and `shared_checks`), which states
   no rule the owners state.
5. A run that declares no selection behaves exactly as it does today, so the committed goldens and the report
   goldens are unchanged, and the pins that read the argument set gain only the new argument.

## Criterion 3 — the pins this piece writes

- The selection shape is pinned in `tests/test_api_requests.py`, in the group that holds the `--path` pins, and
  each pin reads the shape through `container_coverage.is_scope_path` rather than through a string the test
  states.
- The argument error is pinned in `tests/test_api_path.py`, on the run, so the exit code and the no-file fact are
  read from a run, not from a function that looks like the rule.
- No pin reads a document word. A wording check for the vocabulary is a document review, so it lives in
  `tools/check_documents.py`, which the test set does not read.

## Criterion 4 — what stays outside the piece

- The targeted read set itself, the membership facts a unit identity cannot state on its own, and the rule that a
  name the selection excludes is not an index entry are Piece 11A.2, so this piece states no read rule.
- The byte agreement with a full run is Piece 11A.3. A pin for it cannot be written before Piece 11A.2 lands,
  because the run has no targeted read set to run.
- The selection for a `vsys` or a device unit needs the fact that names which device the run read, which is a
  live-target fact, so it stays in `backlog.md` and no pin for it is written here.
- The merge rule and the report section are Phase 11B and 11C, so this piece writes no record rule and no report
  rule, and the four root records stay as `CODEBASE_ASSEMBLY.md` §14 defines them for this piece.

## Result, measured 2026-11-21

Every criterion is met as written, and no criterion had to be read another way.

- Criterion 1: the pins named there are unchanged and pass. `is_scope_path` is still the one shape definition, and
  the selection reads through it; `unit_manifest.units` is still the only unit set, and the piece adds no filter
  to it; the error shape is the one `--path` states, read on a run; the `--parent` pin passes unchanged; no module
  is added, so the `docs/ARCHITECTURE.md` §1 table and the `src/` scans are unchanged.
- Criterion 2: `shared_arguments` declares `--selection`, so both entry points read one argument set, and
  `shared_checks` states the argument rule for it. It reads the shape through `container_coverage.is_scope_path`,
  the place through `container_coverage.path_place`, and the built-in fact through
  `container_coverage.PREDEFINED_PLACE`, so it states no path shape, no unit rule, no naming rule, no writer, no
  console line and no environment name of its own. `path_segments` is the one place a path is split and
  `path_place` is the one place the place is read, so the shape rule and the argument rule read the same segments;
  `path_place` holds no copy of the built-in name, so the pin that counts the constant's uses inside
  `container_coverage.py` reads the same count, 4.
  The file-source refusal sits in path 1's `main()`, next to the `--path` and `--parent` block, because `--source`
  is path 1's argument and path 2 has none, so `shared_checks` cannot state a rule for a source it does not read.
- Criterion 3, as measured: the no-unit fact is decidable at argument time for the built-in place, the only place
  inside the shape that no container table row names — `unit_manifest.units` answers empty for its read, while the
  first membership place answers a unit and `shared` answers `Shared` through `unit_manifest.SHARED_UNIT`. `devices`
  and `vsys` are accepted at argument time because the fact that names which device the run read is a live-target
  fact, which is criterion 4 and stays in `backlog.md`. The argument reads no content, so it cannot decide a
  device or a vsys read, and no second rule is written for it.
- Criterion 4: the read rule is not written here, so a run that declares a selection reads the set it reads today
  and writes the same bytes as the same run that declares none, which is how the committed goldens stay unchanged.

Four pins, one per fact: `tests/test_api_requests.py::test_a_selection_shape_is_read_through_the_one_scope_path_definition`
(the shape, read through `is_scope_path`, and the unit answer, read through `unit_manifest.units`),
`tests/test_api_requests.py::test_the_selection_argument_states_no_rule_an_owner_states` (the argument reads the
shape, the place and the built-in fact through their owners and states none of its own, and asserts no exit code),
`tests/test_api_path.py::test_a_selection_that_names_no_unit_is_an_argument_error_on_a_run` (the exit code and the
no-file fact read from a run), and `tests/test_shadow_coverage.py::test_a_selection_applies_to_the_api_source_only`
(the file-source refusal, read on a run). The pin
`tests/test_api_path.py::test_the_entry_point_accepts_the_arguments_of_one_run_and_refuses_the_ones_that_name_one_source`
gained `selection` in the accepted name list and the refusal word list is unchanged, because the selection names the
read set and not a source. No test module imports another test module: the pins read `PREDEFINED_PLACE_BODY`,
`per_scope_response` and `written_bytes` through `tests/conftest.py`. A wording check for the vocabulary is a
document review in `tools/check_documents.py`, which the test set does not read, and no pin reads a document word.

Gate, measured 2026-11-21 on the tree that holds this piece, single-threaded: `ruff check .` clean at `py310`,
`ruff format --check .` clean on the 106 Python files, `python3 tools/check_documents.py` reports no finding, and
`python3 -m pytest` passes 1,745 pins with the same 4 skip for the missing `tflint` binary — 1,749 pins, 4 more
than the 1,745 pins the per-module collection counts measured at `f376a6a` (1,741 passed plus the 4 skip), in 53
test modules, in 469.96 s on the recorded run. Read through the
per-module collection counts: `tests/test_api_requests.py` collects 26, `tests/test_api_path.py` 36, and
`tests/test_shadow_coverage.py` 23, so the four new pins are 2, 1 and 1 in those three modules. The new pins run
the pipeline for the places they read, so the gate time is above the 306.61 s the previous piece measured;
run-to-run time varies, and the recorded runs of this tree measured 469.96 s and 695.56 s.
