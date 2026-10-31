# To Do

The current feature is F7.1 (the protocol object as output, Epic 7). Its acceptance criteria
are written here before code or tests, and `acceptance.md` carries them when the feature starts.

- [ ] Overwrite `acceptance.md` with the F7.1 acceptance criteria.
- [ ] The print shape for an object attribute, since `protocol` is not a block. The block reader
  reads a field at the block's own level, so the gate rule that reads an object attribute is a new
  shape of the same reader, not a second reader.
- [ ] The one-of `type` choice inside `peer_group` and inside `area`: the provider requires exactly
  one sub-shape, so the emitter prints the one the export names and reports a name it cannot map.
- [ ] The peer belongs to the peer group entry that holds it, so the parse record needs the group,
  not a flat peer list with a `peer_group` text field.
- [ ] The sensitive field prints as the variable reference, so `VALUE_VARIABLES` needs the row for
  the auth profile key, and the declaration set gains it.
- [ ] The two container rows move from `report` to `emitted`, which changes the property scan scope,
  the per-entry report, and the `.tf` goldens.
- [ ] `ruff check .` clean, `pytest` green, the gate reports no finding on the goldens, and the
  change is committed.

Open pieces for Epic 6, held here until the next feature takes them:

- The directory write path: the codebase modules name the unit, the owner, the pair, the order,
  the block, the scope object and the site, and write no directory. The step that splits the
  output per unit directory is still open, and the per-unit `.tfvars` that names one `target`
  serial is part of it, with the LF rule.
- The gate rule that reads a data file: the gate reads `.tf` files only, so no data file is a
  gate input today. `imports.tf`, `scope.tf` and `actions.tf` are `.tf` files, so the gate rules
  read them.
- The outputs rule for a name another unit owns, which the reference edge rule left open.
- The rule types: the import shape writes no block for the four `*_policy_rules` types.
- The generated `README.md` does not name `imports.tf`, `SITE_DATA.json` or `site.auto.tfvars`; it
  names `scope.tf` and `actions.tf`.
- A template stack is a scope container but not one of the four scope facts, so the manifest
  names no stack unit. A stack unit needs a fifth fact, or the decision to read `template` as
  the stack name.
- A module parameter cannot be named by the tool, so a template variable value and a membership
  list in `scope.tf` stay literals until the write path decides what a module takes.
- The site row shape for a variable the run cannot value: a sensitive field prints as a reference, so
  the row names a variable with no value, or the record splits. This is the open half of the decision
  in `backlog.md`.
- The `panos_push_to_devices` shape: the gate reads a push block through `ACTION_SCHEMA`, but the
  emitted shape needs the `devices` decision, which is the `.tfvars` `target` fact the write path
  holds (`backlog.md`).
