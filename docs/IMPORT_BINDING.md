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

1. **The binding decision is run-wide today.** The argument is one flag with no value
   (`src/panorama_to_terraform.py`), so no part of a run can be bound while another part is not. The row
   shape `import_blocks.IMPORT_ROW_FIELDS` states no field for the decision, so the decision reaches the
   output only as blocks. No record states which units a run bound, so a later run cannot read the
   decision back, and a gate rule cannot name a unit that should have written blocks.

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
   object to bind to. So a run that declares a read-through scope writes blocks it cannot bind, and nothing
   names which blocks those are.

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

11. **A mode field is a shape change, so the committed rows move with it.** `unit_manifest.render` prints every
    key of `FIELD_ORDER` for every row, so a field that names the mode is printed for a run that declared no
    mode, and the golden data files move in the same commit as the pins that read the row. The mode can be
    recorded inside a declared shape, which is a golden change, or outside it, which is no record at all, so the
    decision cannot be taken without naming which committed files move.

## 2. The decisions to take

Each decision names what it needs. No decision here is taken, so no piece can be written from it yet.

1. **The mode values, and the level the mode sits at.** Two values, and each names the plan outcome for one
   unit: the entries are imported, or the entries are added. The mode sits at the unit level first, because
   one plan runs inside one unit directory against one state, and a device, a virtual system, a device group,
   and a template are already units, so a per-device or per-device-group request needs no new level. An
   entry-level exception is a separate decision: `OWNERSHIP.json` is the record that holds one row per entry
   the run emits, so an entry-level mode needs a field on that row, and no module may state a second mode
   rule. Decision needed: whether the mode stops at the unit.

2. **The mode's owner.** The manifest row is the record that names each unit and holds the unit facts, so the
   unit mode is a manifest field: `unit_manifest.parse_rows` reads it, `codebase_state.py` rule 2 merges it,
   and the `data_files` gate rule reads it, so no second shape rule or second reader appears. Fact 11 states
   the cost: the field moves the committed rows. Decision needed: the value that a run with no mode prints, so
   the empty answer is stated once — either the field carries an empty value for an unmarked unit, or the mode
   is not a record field and a run states it only in its report. A run that declares no mode writes the same
   bytes as today only under the second shape, which is the F5.5 and F6.4 opt-in precedent.

3. **The declaration rule.** A mode is declared by an argument that names scopes, read through
   `container_coverage.is_scope_path` and `SCOPE_PATH_ROOTS`, the one scope-path definition, so a mode names
   no directory and no second unit set. The argument sits with the CLI and not with the record module, which
   is the rule the no-flag scan holds, and the rule owner states no flag of its own. A mode a run declares
   must agree with the mode the merged record names for the same unit, so a run cannot state two modes for
   one unit. A mode that depends on the order the entries appear in is refused by `ARCHITECTURE.md` §6, the
   same rule that decides the archive member selection (`INPUT_SHAPES.md` §2 rule 4), so the declaration is
   either an explicit list of scopes or a refusal.

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
