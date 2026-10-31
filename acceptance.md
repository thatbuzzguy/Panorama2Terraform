# Acceptance criteria — F6.7: the commit action per unit

Feature record: `docs/CODEBASE_ASSEMBLY.md` §10. The module is `commit_actions.py`, the file is
`actions.tf`, and `main()` writes it. The Terraform minimum decision is taken (1.14); this task
lands it in the generator and the goldens. The gate rule for an `action` block is the open piece.

## Decisions

### 1. One action block per unit, one file for the run

- `actions.tf` holds one `panos_commit` action block per unit the manifest row names. It is a `.tf`
  file, so it is a gate input (`ARCHITECTURE.md` §4.5), and it is written only when it has content,
  following the rule for the report files and the four data files.
- Emission is default, not a flag. The committed goldens pin what a default run emits, so a shape a
  run writes only when a flag is on cannot be pinned (the F6.5 rule 1 argument). The goldens gain
  `actions.tf` for both cases, and `main()` writes `actions.tf` as the last `.tf` file, so the reader
  reads the action against the completed unit.
- Blocks print in the identity order the manifest rows already print. No block states a timestamp or
  a path. The LF rule stays with the write path (`backlog.md`).

### 2. The action names the fact its own unit declares, and no fact another unit owns

- The action names the fact `unit_manifest` already selects for the row (the `unit_name` rule,
  read through a `named_fact` helper so `unit_name` is a delegate and no second level rule appears),
  when that fact is one the provider can name in a commit filter: `device_group`, `template`,
  `template_stack`. The provider fact is measured: `panos_commit` declares `device_groups`,
  `templates`, `template_stacks` as filter lists and no vsys or device filter.
- A `vsys` fact and a `vsys_device` fact name no filter, so a unit whose selected fact is one of them
  writes no action; the unit commits through the parent unit's action, through the platform. The
  shared unit names no fact, so it writes no action: a commit that names no filter commits the whole
  config, not a unit. `localhost.localdomain` names no firewall (F3.5), so it never names a filter
  and never selects a fact, and a device-group unit whose only other fact is the placeholder still
  names its device group.
- An action states exactly one fact: its own unit's selected fact. A fact the unit declares but an
  ancestor unit owns is not its own fact, so the action never names it. The block cannot state a fact
  it cannot name, so the row join is the fact the block states.
- `ACTION_FILTERS` in `resource_mapping.py` is the one mapping from a filter field to the fact it
  names (`device_groups` → `device_group`, `templates` → `template`, `template_stacks` →
  `template_stack`; the `name` field names the fact its `type` states). The emitter reads it and the
  gate reads it, so no branch names the four fields again. `SCOPE_ANSWER` gains the `device_group`
  row so one table answers a scope name for both the scope rule and the action rule.

### 3. The block address names the identity the block states

The local name is the §5 rule (`naming.py`, taken as an argument, no second naming rule) applied to
the fact the block states, with the identity digest of the identity as the block states it — the
single fact in `FACT_KEYS` position, the other facts empty. So the block is data the gate can read
back on its own: the address and the names inside agree, and an action that states a second fact
cannot agree with its own address. This is the gate form of "no action names a scope another unit
owns", and it needs no data file.

### 4. The gate rule `actions`

The fifth gate rule for a block kind, read through the one block reader (`ARCHITECTURE.md` §4.6,
`blocks(files, ('action',))`). `CHECK_ORDER` names `actions` after `scope_blocks`. The action grammar
keeps its fields inside `config`: `terraform validate` refuses a field at the action's own level, so the
one field reader reads inside `config` for this rule, which is a new shape of the same reader, not a
second reader. Five findings, each a FAIL:

1. The action type is not in `ACTION_SCHEMA`, the data table written from the pinned provider schema
   and verified against the live schema the way `DATA_SOURCE_SCHEMA` is. A field inside `config` is not
   one the row declares, or a value is not the shape the row declares. `panos_push_to_devices` requires
   `name` and `type`.
2. The block states no fact. `panos_commit` declares no required field, so the codebase rule is what
   makes an action a unit action: a block that names no fact commits the whole config, not a unit.
3. A filter field does not name its fact through `ACTION_FILTERS`, or names a fact `SCOPE_ANSWER` does
   not answer. The name is not resolved against a scope block this run declares, because an API scope run
   writes no block for the scope it read (measured: the sample golden names `Production-DG` in a filter
   and declares no `panos_device_group` block). A name inside a filter is not a `.name` reference the
   `references` rule can reach, so `SCOPE_ANSWER` is the answer.
4. The block states more than one name. A second name is a second fact, so the block cannot name one
   unit.
5. The block's local name does not answer the names inside the block: it must equal the §5 name plus the
   digest of the identity the names inside build, which is the gate form of "no action names a scope
   another unit owns".

The gate still reads no data file: the rule reads the block text, the tables, and `naming.py`.

### 5. The Terraform minimum is in the generator and the goldens

The generated `terraform` block declares `required_version = ">= 1.14"` (actions need 1.14; the
provider needs 1.8). Both committed goldens change, deliberately. The CI validate job runs Terraform
1.16.1, and the local gate runs 1.16.2, so `terraform validate` accepts the action blocks. The
generated `README.md` names `actions.tf` and states the 1.14 minimum; `README.md` and
`docs/USAGE_GUIDE.md` state 1.14 instead of 1.0. These are report-shape changes, not golden bytes.

### 6. The push half stays open

`panos_push_to_devices` is not emitted. Its `name` and `type` are expressible, but `devices` names
site serials, which is the `.tfvars` decision the write path holds (`backlog.md`). The gate rule
reads a hand-written push block through `ACTION_SCHEMA` today; the emitted shape stays in
`backlog.md`. No coverage matrix row covers an `action` block, the decision F5.5 made for a `data`
block: an action names no entry, so the per-entry report cannot name one.

## Acceptance criteria

1. `commit_actions.py` states the rules and `main()` writes `actions.tf` only when it has content,
   as the last `.tf` file. Pinned by `tests/test_commit_actions.py`, including
   `::test_one_action_block_per_unit_the_manifest_names`,
   `::test_an_action_names_the_fact_its_own_unit_declares`,
   `::test_an_action_states_no_fact_an_ancestor_declares`,
   `::test_a_shared_unit_and_a_vsys_unit_and_a_device_unit_write_no_action`,
   `::test_the_placeholder_device_never_names_a_filter`,
   `::test_the_block_address_names_the_identity_the_block_states`, and
   `::test_the_file_is_written_only_when_it_has_content`.
2. The gate rule reads `action` blocks with the one block reader; `CHECK_ORDER` names `actions` after
   `scope_blocks`. Pinned by `tests/test_commit_actions.py`, including one test per violation type and
   `::test_the_rule_reads_action_blocks_with_the_one_reader` and
   `::test_no_false_positive_across_the_corpus`.
3. `ACTION_SCHEMA` is data the gate reads and the test pins against the live provider schema;
   `ACTION_FILTERS` is the one field mapping, `SCOPE_ANSWER` the one answer table, `naming.py` the one
   naming rule, `unit_manifest.named_fact` the one level rule. `tests/test_commit_actions.py` pins that
   no module defines a second one.
4. The committed goldens declare Terraform 1.14 and gain `actions.tf`; every other golden byte is
   unchanged. `terraform validate` accepts the new blocks.
5. The generated `README.md` names `actions.tf` and states the minimum; the root `README.md` and
   `docs/USAGE_GUIDE.md` state 1.14.
6. `docs/CODEBASE_ASSEMBLY.md` §10 states the landed rules and names the module and the tests; the
   open push half stays recorded in `backlog.md`.
7. Two runs on the same source write the same action bytes, pinned by
   `tests/test_commit_actions.py::test_two_runs_write_the_same_bytes`.
8. `ruff check .` is clean, `pytest` is green, the gate reports no finding on the goldens, and the
   change is committed. The tracking markdown loses the F6.7 detail, and the next feature is F7.1.
