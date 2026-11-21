# Piece 11A.1 acceptance criteria — the selection vocabulary and the argument rule

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
