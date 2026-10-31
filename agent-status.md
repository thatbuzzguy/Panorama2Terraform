# Agent Status

## Current position

F6.7 (the commit action per unit) is complete and committed: `commit_actions.py` writes one
`panos_commit` action block per unit as `actions.tf`, and the gate rule `actions` reads those blocks
against `ACTION_SCHEMA` through the one block reader. The rules are in `docs/CODEBASE_ASSEMBLY.md` §10,
the tests are in `tests/test_commit_actions.py`. The push half stays open in `backlog.md`.

Facts measured while the work landed, and the rules that follow from them:

- An action keeps its fields inside `config`: `terraform validate` refuses a field at the action's own
  level. So the one field reader takes the sub-block it reads as an argument, and no second reader
  appears.
- The fact a filter names is answered by `SCOPE_ANSWER`, not resolved against a declared block, because
  an API scope run writes no block for the scope it read.
- The action's local name carries the digest of the identity as the block states it, so the gate reads a
  block back on its own and the address answers the names inside it. That digest is not the unit's
  directory digest.
- Emission is default, not a flag, so the goldens pin what a default run emits; `actions.tf` is the last
  `.tf` file `main()` writes.

Decisions taken on 2026-10-31 that the work confirms: the Terraform minimum is 1.14 and both committed
goldens declare it; a value the parse cannot carry prints as the variable reference; the write path
forces LF.

The next feature is F7.1 (the protocol object as output, Epic 7). Its pieces are in `to-do.md`, and its
acceptance criteria go in `acceptance.md` before code or tests.

## Rules to keep when writing documents

- One owner document per rule; every other document links to it.
- Machine-readable tables are code. A document explains a table and never restates it
  row by row, so a regenerated table cannot drift.
- No test counts in a document. A document names the test that pins a rule; the
  count lives in `agent-status.md` and the git history.
- A claim about what the tool does must name the module or the test that holds it. A
  feature id is written only when a module or a test uses it as a name.
- ASD-STE100 Simplified Technical English, no marketing voice, no emoji.
- A historical record is not kept in the markdown. The git history is the record, and the
  markdown states the current state.
- A record is data, so a document describes its fields and never restates a record. The
  example in `docs/USAGE_GUIDE.md` is an illustration with a shortened hash, not a pin.
- Completed epic, phase, feature and task detail is removed from the tracking markdown after
  the work is committed; `AGENTS.md` states the rule.

## Watch for Epic 6 and Epic 7

- The codebase modules name the unit, the owner, the pair, the order, the block, the scope
  object and the site, and write no directory. The write path is the step that turns a
  `directory` field into a real directory, and `scope.tf`, `imports.tf` and `site.auto.tfvars`
  are one file for the run until it lands.
- The block reader in `sanity_checks.py` serves every kind, so the F7.1 rule for an object attribute
  must use `blocks(files, kinds)` and the same field reader, given the sub-block it reads; no second
  block reader should appear.
- The gate reads `.tf` files only, so no data file is a gate input today. `scope.tf`, `imports.tf` and
  `actions.tf` are `.tf` files and are gate inputs. If a codebase feature makes a data file a
  gate input, the file set statement in `ARCHITECTURE.md` §4.5, the `.tfvars` statement in §4.5,
  and the no-change tests must change together.
- A field reader must read at the block's own level and stop at the closing quote, or a
  sub-block field or an escaped quote answers for the block's field. Both are pinned in
  `tests/test_import_blocks.py`, and the scope rule reads at the block's own level through the
  same reader, which takes the sub-block it reads as an argument (the action rule reads inside
  `config`). The same reader also tells a quoted value from a `var.` reference, so no second
  rule decides the shape of a field.
- `SCOPE_PLACEMENT` and the location sub-block are one fact: a new scope type needs both the
  placement key and the `SCOPE_ANSWER` entry, and the emitter reads the placement key as the
  location, so a new row cannot place itself in a scope it does not name.
- The entry name is never a property. A row whose provider type declares no `name` reaches the
  block through `entry_coverage.name_field`; no emitter, gate rule, or test should state the
  field again.
- One place decides the shape of a value: `resource_mapping.VALUE_VARIABLES`, read at the print
  site. A new field a table row maps must be read by the emitter, the gate and the `.tfvars`
  writer through the same table, and the table must cover every field `LOCATION_SCHEMA` declares.
- The §5 naming rule lives in `naming.py`. No module may define a second one;
  `TerraformGenerator.sanitize_name` is a delegate and the data modules take the rule as an
  argument.
- The import position for the four `*_policy_rules` types must be the position the live config
  holds, and the F3.5 rulebase decision gates it. No block is written for a rule entry until both
  land.
- The generated `README.md` does not name `imports.tf`, `SITE_DATA.json` or `site.auto.tfvars`;
  the F5.5 label precedent says an opt-in shape labels itself.
- Actions need Terraform 1.14 or later; the committed goldens now declare it, so a change to the
  minimum is a golden change.
- The credential rule needs one statement that covers both the fetch layer and the generated
  provider block.
- The prune action still needs the record directory decided. A state record references nothing,
  so it prunes nothing, and the prune rule reads a record file, not one record.
- A coverage fact that comes from a run must be read from the run's ledger, so the scan tests run
  the pipeline in process.
- A cycle test needs the referrer entry and the declaring entry in the same unit, for the reason
  recorded in the git history for F6.3.
- An object attribute (`protocol`) is a field whose value is an object, not a block, so the gate rule
  for it is a new shape of the one block reader. No second reader should appear for F7.1.
- The sensitive field rule needs one table that the emitter, the gate and the report all read, so the
  placeholder check and `tests/test_robustness.py` state the same fact once.
- A container row that moves from `report` to `emitted` changes the property scan scope, the per-entry
  report, and the `.tf` goldens together, so it cannot be a print-only change.
- The LF rule is a byte rule, so the goldens and the no-change tests change with the write path.
