# Import Binding

Design record for Epic 14, planning. This document is the owner of the rules about which block a run
binds to the object the live config already has, how that fact is recorded, and which facts an id needs
that the tool cannot read offline. The block shape itself stays owned by
[ARCHITECTURE.md](ARCHITECTURE.md) §4.8 and [CODEBASE_ASSEMBLY.md](CODEBASE_ASSEMBLY.md) §7, and this
document restates neither. The naming rule it reads is `ARCHITECTURE.md` §5, the determinism rule is §6,
the console-line shape and the report rule are §3.2, the property scan scope rule is
[COVERAGE_MATRIX.md](COVERAGE_MATRIX.md) §1, the records-as-state rule is
[MULTI_RUN_CODEBASE.md](MULTI_RUN_CODEBASE.md), and the state scan is `ARCHITECTURE.md` §3.2. The
document index is in [README.md](README.md). The pieces are in `to-do.md`, the criteria are in
`acceptance.md`, and the facts that need a live target are in `backlog.md`.

Binding is the word this project already uses for an `import` block: the address that binds a written
block to the object the live config already has. This epic adds the decision about which blocks carry an
id, and the facts an id needs for a codebase that manages a device instead of building a new one.

## 1. Facts measured offline

1. **The binding decision is per unit, because decision 3 was taken on 2026-11-26.** The argument names one pair
   per declared scope, so a declaration names units, and the decision reaches the output twice: as the blocks for a
   unit the declaration marks, and as the row field decision 2 names, so a later run reads the decision back through
   `unit_manifest.parse_rows`. Before that decision the argument was one flag with no value, so no part of a run
   could be bound while another part was not, no record stated which units a run bound, and a gate rule could not
   name a unit that should have written blocks. The gate rule that reads a block still reads the files the run wrote,
   and the half that names an emitted entry with no block stays decision 5's.

2. **The address half is already stable, which is what makes a bound codebase readable after the first
   plan.** The §5 rule puts the identity digest in a local name, and `unit_manifest.py` rule 2 puts the
   same digest in the directory name, so the same entry keeps the same address across runs and one unit's
   name does not depend on the other units in the run. A change to one of the five scope facts moves the
   address, the directory, and the id together, which is the move fact recorded in `backlog.md`.

3. **An id states only what the block states (`CODEBASE_ASSEMBLY.md` §7 rule 5), so no id can name a
   device.** `VALUE_VARIABLES` maps `ngfw_device` to a variable, so the block prints the reference and the
   id states the value the run read. The export states a device as a hostname, so no value reaches the
   parse, and `unit_manifest.FACT_KEYS` holds no serial. Every unit that places an entry in a `vsys`, a
   template `vsys`, or an `ngfw` location therefore writes an id with no device, and `location.device_group`
   declares `panorama_device` in the pinned schema while the generator emits no field for it. For a
   migration these ids are placeholders the operator fills; for a bound unit they are not ids.

4. **The four `*_policy_rules` types cannot be bound with the shape the emitter writes.** The block is one
   object per rule type per unit that iterates that unit's rows, so an instance address is
   `<type>.<block name>[<key>]`, where the block name and the map name are one name, `rule_data.locals_name`,
   and `IMPORT_ROW_FIELDS` states no field for the key. The provider's import object for those types names
   the rulebase, the position, and a list of names, so it is one object for a rulebase and not one per
   entry. `rule_data.RULE_ROW_FIELDS` states `key` as the chain ordinal and `pivot` as the entry the rule is
   placed after, the block anchors the first rule of a chain at `position = { where = "last" }`, and a chain
   groups across rulebases today (F2.5), so neither field is the position a live rulebase holds.

5. **A read-through name is never bound.** `sanity_checks.check_import_blocks` refuses an `import` block
   that names a `data` block, because an import names a resource. A built-in name such as `any` has no
   verified name table, so the run cannot tell a built-in from an operator object, and a built-in has no
   object to bind to. So a run that declares a read-through scope can write blocks for a unit it marked, and
   the record names that unit through the mode field decision 2 took; the half that compares those blocks with
   the entries the run's ledger read is decision 5's.

6. **The whole-block fact is measurable today and has no name.** A block that reads fewer properties than
   its coverage matrix row declares is a partial block, and a plan that compares a partial block with the
   live object shows change. The property scan already reads the pair, per container kind, on a run
   (`tests/test_property_coverage.py`), and `entry_coverage.py` prints the same fact as a captured field no
   output read. The fact has no name and no owner, so no report can state which entries of a bound unit can
   read as zero change.

7. **A bound codebase covers only what a matrix row emits.** The live objects outside the scan scope stay
   outside the state, so a plan names nothing for them, and the report is the only place that names them.
   The rows that hold this are the property gaps in `backlog.md`, and the pinned schema declares no raw XML
   or xpath resource, so there is no in-provider way to cover an uncovered entry.

8. **The change half of a plan is not the tool's output.** The tool writes no lifecycle rule, no state, and
   runs no plan (`CODEBASE_ASSEMBLY.md` §13), so a bound unit whose plan shows change is an operator action,
   the way a drift finding is (F5.6). The state scan reads a state document as a reference source, and the
   join between a written block and a state entry is `state_coverage.ownership_key`, so the offline half of
   the drift check already exists for a bound unit; the state side stays read-only.

9. **The mode cannot ride on the selection.** `MULTI_RUN_CODEBASE.md` §2 rule 1 states that `--selection` names
   the read set and not what the run writes, and the record rule states that reports are per run while the four records are
   codebase state. So the mode must be a record field read through its own `parse_rows`, and no report or
   gate rule may state a second unit set or a second mode rule.

10. **An `import` block for a resource that is already in state is a Terraform behaviour the project has not
    measured.** Whether a plan reports it again, and whether apply reads the live object through it a second
    time, decides whether `imports.tf` is permanent codebase content or a first-run file. A pin cannot read
    it, because a plan needs a device, so this stays a decision to take on measurement.

11. **A mode field is a shape change, so the pins that state the row shape move with it.** `unit_manifest.render`
    prints every key of `FIELD_ORDER` for every row, so a field that names the mode is printed for a run that
    declared no mode. Measured 2026-11-25 when decision 2 was taken: `tests/golden` holds no data file, only 87 `.tf`
    files, so no committed golden byte moves. What moves is the pins that state the row shape as a list, in the same
    commit as the field: `tests/test_unit_manifest.py::test_the_row_fields_are_the_declared_shape_in_order`,
    `::test_the_row_states_placement_through_the_fact_keys_it_already_reads`, and
    `::test_a_row_that_is_not_the_declared_shape_is_refused`, plus the row builder
    `tests/test_data_file_gate.py::_manifest_row`, which builds a row from the shape it reads through its module and
    so cannot break. The pins that read a record as data through its own module, such as
    `tests/test_codebase_state.py::test_the_merge_adds_no_field_so_a_merged_row_reads_back_as_itself`, read the shape
    and state no list, so they do not move.

## 2. The decisions to take

Each decision names what it needs. Decisions 1, 2 and 3 are taken, so the pieces that read them can be written; the
rest are untaken, so no piece can be written from them yet.

1. **The mode values, and the level the mode sits at. Taken 2026-11-25: the mode stops at the unit.** Two
   values, and each names the plan outcome for one unit: the entries are imported, or the entries are added. The
   mode sits at the unit level, because one plan runs inside one unit directory against one state, and a device, a
   virtual system, a device group, and a template are already units, so a per-device or per-device-group request
   needs no new level. An entry level is not part of this decision: `OWNERSHIP.json` is the record that holds one
   row per entry the run emits, so an entry-level mode would need a field on that row, and this decision takes no
   field of its own: the field is decision 2's, and no module states a second mode rule.

   What the decision settles: the pair, the level, and the fact that it takes no field of its own. The pair and the
   level are data in `src/import_blocks.py` (`MODE_VALUES`, `MODE_LEVEL`), the module that already holds the binding
   decision as data (`RULE_DECISION`), owns the block shape and the row shape, and defines no unit rule and no
   naming rule, so a data constant there adds no row field and moves no committed data file. Decision 2 names
   `unit_manifest.py` as the owner of the field, so `unit_manifest.parse_rows` is the reader that uses the pair, and
   this module states no field, no reader and no shape rule of its own. Pinned by
   `tests/test_import_blocks.py::test_the_two_mode_values_are_data_read_through_the_owner`,
   `tests/test_import_blocks.py::test_the_mode_level_is_the_unit_the_one_unit_rule_answers`,
   `tests/test_import_blocks.py::test_the_field_name_and_the_pair_are_each_stated_once_in_their_owner`, and
   `tests/test_import_blocks.py::test_the_mode_data_adds_no_unit_rule_and_no_mode_rule_to_the_owner`.

   What the decision did not settle, and decision 2 settled on 2026-11-25: the owner as a record field, and the
   answer a run with no mode prints. Piece 14A.2 landed that half.

2. **The mode's owner. Taken 2026-11-25: the mode is a field of the unit-manifest row.** The manifest row is the
   record that names each unit and holds the unit facts, so the field is stated in `unit_manifest.py`, read through
   its `parse_rows`, merged through `codebase_state.py` rule 2, and read by the `data_files` gate rule, so no second
   shape rule and no second reader appears. `codebase_state.py` names no field and states no value set, because rule
   2 takes the whole row through the reader its owner states, and the gate reports a row its reader refuses as its
   finding 1, so the gate states no value set either.

   The two halves sit in two owners, and the reason: the pair is decision 1's data and stays in
   `import_blocks.MODE_VALUES`, so `unit_manifest.py` states the field and reads the pair through that owner instead
   of naming the values a second time. The answer for a unit the run did not mark is stated once, in
   `unit_manifest.py` as `EMPTY_ANSWER`, in the style of `provenance.py` rule 1, which prints `-` for a field that
   does not apply: inside a JSON row the same answer is the empty string, and `build_rows` already writes it for a
   field the unit does not state. Decision 3 was taken on 2026-11-26, so an argument declares the mode for the units
   it names, and every other row states the answer for a unit the run did not mark, which is the answer a run that
   declares nothing prints on every row.

   The field prints after `unit`, because `MODE_LEVEL` names the unit as the level the values apply to and `unit` is
   the field that states that level on the row. Fact 11 names what moves: no committed golden byte, because no
   committed data file exists, and the pins that state the row shape as a list. Pinned by
   `tests/test_unit_manifest.py::test_the_mode_field_reads_back_as_a_value_of_the_pair_through_its_owner`,
   `tests/test_codebase_state.py::test_the_merge_carries_the_mode_as_the_record_states_it`,
   `tests/test_data_file_gate.py::test_a_mode_that_is_not_a_value_of_the_pair_is_a_finding_through_the_reader`,
   `tests/test_import_blocks.py::test_the_field_name_and_the_pair_are_each_stated_once_in_their_owner`, and the
   three pins fact 11 names.

3. **The declaration rule. Taken 2026-11-26: the declaration names units through pairs.** Four answers, and the
   owner each answer needs.

   - **The shape is `scope=mode` pairs, one pair per declared scope**, repeatable, sorted by the name of the place
     the pair states, so no answer depends on the order the pairs were declared. The declaration is the explicit
     list of scopes, so no order rule is needed, and `ARCHITECTURE.md` §6, the rule that decides the archive member
     selection (`INPUT_SHAPES.md` §2 rule 4), holds.
   - **The name is `--import-mode`**, in the set both entry points read.
   - **A mode a run declares must agree with the mode the merged record names for the same unit.** A run that
     states two modes for one unit is refused before it writes any file, exits 1, and prints the input-refusal
     line, naming the unit, the mode the record names, and the mode the run declares. The refusal is
     `xml_input.UnsafeInputError`, so `is_refusal` keeps the two kinds it already states, following
     `state_input.py` rule 5. A pair that is not one path and one value joined by `=`, a value outside the pair, a
     place the one scope path definition refuses, a pair that names the place only, and a place that names no fact
     are argument errors, so they exit 2 and write no file.
   - **`--import-blocks` is removed, and no path stays for it.** A unit the declaration marks with the value that
     writes blocks writes its `imports.tf` blocks, a unit marked with the other value writes none, and a run that
     declares no pair writes no block and prints `unit_manifest.EMPTY_ANSWER` on every row, so a default run's
     bytes are unchanged. The pins that read the old flag moved in the same commit as the decision.

   The rule owner is `src/unit_manifest.py` rule 6, the owner of the `mode` field, `EMPTY_ANSWER` and `parse_rows`.
   The pair reaches a unit through `container_coverage.fact_of_place`, the one place that states the pair between a
   place and the fact it names, so `unit_manifest.py` holds no mapping of its own, and the unit is read through
   `units` and `fact`: the argument states no path shape, no unit rule, no directory and no second unit set, and
   `import_blocks.py` states no field name, no reader and no mode rule. The shape is read through
   `container_coverage.is_scope_path` and `SCOPE_PATH_ROOTS`, the place through `path_place`, and the two values
   through `import_blocks.MODE_VALUES`, so no module states a value of the pair a second time, and the write step
   answers whether a unit writes blocks through `unit_manifest.unit_writes_blocks`. The argument is held by the CLI,
   inside `shared_arguments`, and read through `import_modes`, so the rule owner states no flag of its own, which is
   the rule the no-flag scan holds (`tests/test_write_path.py::test_no_flag_names_the_write_path`), and the owner
   states a rule function and not an argument of its own. The half of the read step that reads the reference records
   moves before the emitters, because the agreement check runs before the first write.

   Pinned by `tests/test_container_coverage.py::test_the_fact_a_place_names_is_read_through_the_one_mapping`,
   `tests/test_unit_manifest.py::test_the_declaration_names_the_units_inside_the_scope_through_the_one_unit_rule`,
   `::test_the_declaration_pairs_are_sorted_by_name_so_no_answer_depends_on_the_order`,
   `::test_a_declared_unit_prints_its_mode_and_an_undeclared_unit_prints_the_empty_answer`,
   `::test_two_modes_for_one_unit_are_refused_and_the_run_writes_no_file`,
   `::test_a_declared_mode_that_disagrees_with_the_record_is_refused_and_writes_no_file`,
   `::test_a_pair_that_names_no_unit_is_an_argument_error`,
   `::test_the_declaration_is_held_by_the_cli_and_the_rule_owner_states_no_flag_of_its_own`, and
   `::test_the_write_step_reads_the_mode_through_the_row_owner_and_names_no_value`, plus
   `tests/test_import_blocks.py::test_a_unit_declared_the_block_value_writes_blocks_and_a_unit_declared_the_other_value_writes_none`
   for the unit that writes the blocks.

4. **The whole-block fact needs a name, an owner, and a severity.** It compares two sets: the properties a
   matrix row declares, and the fields the emitter reads on a run. By `ARCHITECTURE.md` §4.6 a fact that
   compares two sets is a coverage fact, so it is a WARN and the exit code stays with the rules that read the
   files. Its owner is the property scan through `entry_coverage.py`, and the report section that names it
   must follow the F3.9 grouping rule, so no module states a second grouping rule. The finding must fit the
   four parts of the console-line shape (`container_coverage.console_line`), or print in the report only.

5. **The completeness rule for a bound unit.** Today `check_import_blocks` reads one block against the block
   it names. For a bound unit the rule needs the other half: one block per entry the run's ledger reads as
   `emitted`, so an emitted entry with no block is a finding. That half compares the block set the reader
   read with the entry set the run's ledger read, so it is the same shape as the round-trip cross-check, and
   it reads the unit through `unit_manifest.units` and the mode through the record, so it states no unit rule
   of its own. Decision needed: whether the completeness half is the same rule or a second rule.

6. **The device fact for a bound unit.** An id for a `vsys`, a template `vsys`, or an `ngfw` location needs the
   serial the export cannot carry. Decision needed: which declared source states it. The two shapes are a site
   value the operator declares, read through `site_data.py` so the block and the id print the same fact
   through `VALUE_VARIABLES`, and the device fact a live target states, which no committed response holds
   (`API_CONVERSION_PATH.md` §4). The first shape is measurable offline on a committed fixture, so it is the
   half the project can write; the second stays in `backlog.md`. The value must come from a source the
   provenance record can name, so `ARCHITECTURE.md` §3.3 reaches it, and the rule that a run with no network
   passes CI is unchanged.

7. **The rule types need a shape decision before an entry can be bound.** Either the emitter writes one object
   per rule, which moves the iterated block rule, the order rule, and the goldens, so it cannot be a
   print-only change, and `IMPORT_ROW_FIELDS` gains the instance half; or the rule set stays outside the
   state and the report names it, which is the decision F6.4 wrote. Both halves need the F3.5 rulebase value,
   and both need a source that states the position the live rulebase holds.

8. **The read-through order.** Decision needed: a unit that binds its entries writes no `data` block for a
   name it binds, so the two opt-ins cannot both claim the same name. The built-in name table is the condition
   for the second half, so a run that declares a read-through scope stays labelled in the generated
   `README.md` until that table lands (`backlog.md`).

9. **Permanence.** Recorded as a decision to take on measurement (fact 10). If a plan reports an import for a
   block whose resource is already in state, then `imports.tf` is permanent content and the report must name
   the bound units on every run. If it does not, the file still stays, because a run that writes a codebase
   cannot know what a state holds, and only the generated `README.md` wording changes. Either way the report
   rule that a run names the units it built is unchanged.

## 3. What a bound unit can state offline

The report rule already names the entries that cannot reach zero change, and the zero-change plan half of
`CODEBASE_ASSEMBLY.md` §7 stays open. For a bound unit, that half needs one more fact: the plan expectation
holds only for a whole block, so the report section names which entries of a bound unit can read as zero
change and which cannot, per unit and per matrix row. No test can pin the plan itself, because a plan needs a
device, so the offline reading is the property scan measured on a run, and the plan fact stays a live fact.

## 4. Facts only a live target states

Recorded in `backlog.md`, in the codebase-assembly and provider-fact sections, so this document names no
live fact: the device serial for a bound unit, the rulebase value, the position a live rulebase holds, the id
shape for the types that carry the entry name under another field, whether `panorama_device` is needed in an
id, the built-in name table, and the Terraform behaviour for an import block whose resource is already in
state.
