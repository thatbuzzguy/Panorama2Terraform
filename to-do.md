# To Do

The housekeeping task (clean the root markdown, remove completed work) is complete and committed;
the change is in the git history. No code feature is in progress.

The next feature in `PLAN.md` is F6.7 (the commit action). Before writing code or tests for it,
overwrite `acceptance.md` with its acceptance criteria. The Terraform minimum decision is taken
(1.14, goldens declare it), so the open piece is the gate rule for an `action` block, which must
read through the one block reader.

The open feature in Epic 7 is F7.1 (the protocol object as output). Its pieces:

- The print shape for an object attribute, since `protocol` is not a block. The block reader reads a
  field at the block's own level, so the gate rule that reads an object attribute is a new shape of
  the same reader, not a second reader.
- The one-of `type` choice inside `peer_group` and inside `area`: the provider requires exactly one
  sub-shape, so the emitter prints the one the export names and reports a name it cannot map.
- The peer belongs to the peer group entry that holds it, so the parse record needs the group, not a
  flat peer list with a `peer_group` text field.
- The sensitive field prints as the variable reference, so `VALUE_VARIABLES` needs the row for the
  auth profile key, and the declaration set gains it.
- The two container rows move from `report` to `emitted`, which changes the property scan scope, the
  per-entry report, and the `.tf` goldens.

Open pieces for Epic 6, held here until the next feature takes them:

- The directory write path: the codebase modules name the unit, the owner, the pair, the order,
  the block, the scope object and the site, and write no directory. The step that splits the
  output per unit directory is still open, and the per-unit `.tfvars` that names one `target`
  serial is part of it.
- The gate rule that reads a data file: the gate reads `.tf` files only, so no data file is a
  gate input today. `imports.tf` and `scope.tf` are `.tf` files, so the gate rules read them.
- The outputs rule for a name another unit owns, which the reference edge rule left open.
- The rule types: the import shape writes no block for the four `*_policy_rules` types.
- The generated `README.md` does not name `imports.tf`, `SITE_DATA.json`, or
  `site.auto.tfvars`; it names `scope.tf`.
- A template stack is a scope container but not one of the four scope facts, so the manifest
  names no stack unit. A stack unit needs a fifth fact, or the decision to read `template` as
  the stack name.
- A module parameter cannot be named by the tool, so a template variable value and a membership
  list in `scope.tf` stay literals until the write path decides what a module takes.
- The write path forces LF (decided 2026-10-31), so a run on a Windows desktop writes the same bytes
  as a run on CI.
- The site row shape for a variable the run cannot value: a sensitive field prints as a reference, so
  the row names a variable with no value, or the record splits. This is the open half of the decision
  in `backlog.md`.
