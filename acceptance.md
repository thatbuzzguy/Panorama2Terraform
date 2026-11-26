# Acceptance criteria

This file carries the record for the current task. Piece 14A.2 is committed at `67f2fae`, so its record lives in the
git history and is not restated here. The epic records stay as pointers: Epic 13's rules are in
`docs/INPUT_SHAPES.md`, and Epic 14's criteria are not restated here because that epic still has open pieces in
`to-do.md` and its decisions are in `docs/IMPORT_BINDING.md` §2.

## Piece 14A.3, the declaration argument (main, the current task)

Decision 3 of `docs/IMPORT_BINDING.md` §2, taken 2026-11-26 by the operator, is the decision this piece needs. The
four answers it took:

1. **The shape is `scope=mode` pairs, one per declared scope**, repeatable, sorted by the scope name, so no answer
   depends on the order the pairs were declared (`docs/ARCHITECTURE.md` §6, the same rule that decided the archive
   member selection, `docs/INPUT_SHAPES.md` §2 rule 4). A declaration that reads the pair order is refused, so the
   piece takes the explicit list of scopes and states no order rule.
2. **The name is `--import-mode`**, in the set both entry points read.
3. **A mode a run declares must agree with the mode the merged record names for the same unit.** A run that states
   two modes for one unit is refused before it writes any file, exits 1, and prints the input-refusal line, naming
   the unit, the mode the record names, and the mode the run declares.
4. **`--import-blocks` is removed.** A unit the declaration marks as `imported` writes its `imports.tf` blocks, a
   unit marked `added` writes none, and a run that declares nothing writes no import block and every manifest row
   states `unit_manifest.EMPTY_ANSWER`, so a default run's bytes are unchanged. The pins that read the old flag
   move in this commit; no path stays for it.

One goal: record the decision as taken, land the declaration rule in the owner it names, and move the pins that read
the removed flag.

### Criteria

1. `docs/IMPORT_BINDING.md` §2 decision 3 records the decision as taken with the date and the four answers, with the
   owner it names for the declaration rule, the reader the rule reads through, and the exit code it takes. §1 fact 1
   moves with it, because the argument is no longer one flag with no value.
2. The rule owner is `src/unit_manifest.py`, the owner of the `mode` field, `EMPTY_ANSWER` and `parse_rows`, so the
   piece adds rule 6 there: the pair names the units that hold the fact the place names, read through
   `container_coverage.path_place` and `path_segments` and through this module's own `units` and `fact`, so the
   argument states no path shape, no unit rule, no directory and no second unit set, and `src/import_blocks.py`
   still states no field name, no reader and no mode rule, and `src/codebase_state.py` stays rule-free. The argument
   itself is held by the CLI, and the rule owner states no flag of its own, which is the rule the no-flag scan holds
   (`tests/test_write_path.py::test_no_flag_names_the_write_path`), so the owner states a rule function and not
   `add_arguments`.
3. The pair shape is the CLI's own rule, following `--data-blocks` and `--selection`: `shared_arguments` holds the
   argument, and the argument rule reads the scope shape through `container_coverage.is_scope_path` and
   `SCOPE_PATH_ROOTS`, the place through `container_coverage.path_place`, and the two values through
   `import_blocks.MODE_VALUES`. A pair that is not `scope=mode`, a mode outside the pair, a scope the one scope path
   definition refuses, a pair that names the place only, and a pair whose place names no fact are argument errors:
   exit 2, and no file is written. Only the two-mode conflict is an input refusal, so it exits 1.
4. The place-to-fact pair is a new fact, so it needs the owner that already names both sets:
   `src/container_coverage.py` states the fact a place names, read through its own scope-walk rows, and every reader
   reads it through that module, so no module holds a second mapping. A place that names no fact answers the answer
   for a fact a unit does not state, which is why `shared` names no unit for a declaration.
5. The conflict is an input refusal, so it raises `xml_input.UnsafeInputError`, the kind `is_refusal` states, and
   `is_refusal` keeps exactly two kinds: nothing in this piece adds a third. A plain `ValueError` keeps the `failed()`
   shape, so the refusal is the input kind, following `state_input.py` rule 5 and `state_input._refusal`. The
   refusal happens before the run writes a file, so the reference-source read half moves before the emitters; the
   merge half stays after them, because the run's own rows are the values the emitters printed. The read step still
   reads the four records through `sanity_checks.DATA_FILES`, `write_path.root_path`, each `parse_rows`, and
   `codebase_state.merge_rows`, and it states no key, shape, reader, path rule, unit rule or list of record names of
   its own.
6. `build_rows` takes the declaration, so a unit the run declared prints its mode and a unit the run did not declare
   prints `EMPTY_ANSWER`. The write step answers whether a unit writes blocks through a rule function in
   `unit_manifest.py`, because the run sequence cannot name a value of the pair: the pair is read through
   `import_blocks.MODE_VALUES`, and no module states a value of the pair a second time.
7. Pins measure content or names, never document wording, and no test module imports another test module. A fact
   more than one test module reads lives in `tests/conftest.py`, which already holds the pair as one definition read
   through its owner, and the declaration pairs more than one test module builds are read through the owners there.
   Pins that read the removed flag move in this commit: `tests/test_import_blocks.py` groups 3, 4, 6, 7 and 8,
   `tests/test_site_data.py::test_the_import_rule_compares_a_mapped_field_by_name` group run pin,
   `tests/test_api_path.py`'s accepted-name pin, and the pins named in criteria 8.
8. Pins this piece adds, in the module that owns the rule they measure:
   - `tests/test_container_coverage.py::test_the_fact_a_place_names_is_read_through_the_one_mapping`
   - `tests/test_unit_manifest.py::test_the_declaration_names_the_units_inside_the_scope_through_the_one_unit_rule`
   - `tests/test_unit_manifest.py::test_the_declaration_pairs_are_sorted_by_name_so_no_answer_depends_on_the_order`
   - `tests/test_unit_manifest.py::test_a_declared_unit_prints_its_mode_and_an_undeclared_unit_prints_the_empty_answer`
   - `tests/test_unit_manifest.py::test_two_modes_for_one_unit_are_refused_and_the_run_writes_no_file`
   - `tests/test_unit_manifest.py::test_a_declared_mode_that_disagrees_with_the_record_is_refused_and_writes_no_file`
   - `tests/test_unit_manifest.py::test_a_pair_that_names_no_unit_is_an_argument_error`
   - `tests/test_unit_manifest.py::test_the_declaration_is_held_by_the_cli_and_the_rule_owner_states_no_flag_of_its_own`
   - `tests/test_unit_manifest.py::test_the_write_step_reads_the_mode_through_the_row_owner_and_names_no_value`
   - `tests/test_import_blocks.py::test_a_unit_declared_the_block_value_writes_blocks_and_a_unit_declared_the_other_value_writes_none`
9. Documents that state the flag move in the same commit: `README.md` (the quick-start line, the `imports.tf` file
   line, the per-unit file list, and the test-set entry for `tests/test_unit_manifest.py`),
   `docs/README.md` (the index line for Epic 14 and the owner row that names the declaration rule),
   `docs/USAGE_GUIDE.md` (the argument table, the Import blocks section, and the path 2 argument list),
   `docs/CODEBASE_ASSEMBLY.md` §7 rules 1 and 2, `docs/ARCHITECTURE.md` §4.8, `docs/IMPORT_BINDING.md` §2, and the
   module docstrings `src/unit_manifest.py` rule 6, `src/container_coverage.py` and `src/import_blocks.py` rule 7,
   and the `check_import_blocks` condition wording, which is the rule that reads the files the run wrote. No
   document states a test count, and every pin name a document claims exists.
10. Every count that moves is recorded, including whether any committed golden byte moves, measured against the
    baseline commit `67f2fae`: 1,868 pins in 55 test modules, 1,864 passed, the same 4 `tflint` skips, `ruff check`
    and `ruff format --check` clean on 113 files, `python3 tools/check_documents.py` with no finding. `tflint` is
    absent on this machine, so its 4 pins skip; `terraform` is 1.16.2 and is present. The gate runs single-threaded
    in one process with no parallel plugin: `ruff check .`, `ruff format --check .`,
    `python3 tools/check_documents.py`, `python3 -m pytest -p no:cacheprovider`. `tests/golden` holds no data file,
    only 87 `.tf` files, so no committed golden byte moves unless an emitter changes.
11. Out of scope for this piece: decisions 4 to 9, the four `*_policy_rules` rule types, the device fact, the
    whole-block fact, the completeness half, the read-through order, permanence, and the report section that names
    the units a run bound (Piece 14A.4). The gate rule that reads an import block, the block shape, the id shape and
    the row shape are unchanged: this piece changes only which units the run writes blocks for, and what a manifest
    row states for a declared unit.
12. Standard library only, ASD-STE100 sentences, no marketing voice, no emoji, plain literal wording, no metaphor.
    `agent-status.md`, `to-do.md` and `backlog.md` are updated, and the change is committed in conventional-commits
    style with the completion history in the body. Nothing is pushed.

### Definition of done

Decision 3 is recorded as taken with the date and the four answers, the declaration rule is stated once in the owner
decision 3 names, the argument is held by the CLI and reads the shape, the place and the values through their owners,
the two-mode conflict is an input refusal that happens before the first write and exits 1, the pins that read the
removed flag moved to the declaration, the pins that read the declaration measure content or names through their
owners, every count that moves is recorded with the golden answer, and the document checks report no finding.
