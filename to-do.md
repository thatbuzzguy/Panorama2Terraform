# To Do

F7.1 (the `protocol` object as output on `panos_virtual_router`) is complete and committed. The next
feature is not chosen, so this file holds only the open pieces that a later feature takes.

## Open pieces for Epic 6

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
- The `panos_push_to_devices` shape: the gate reads a push block through `ACTION_SCHEMA`, but the
  emitted shape needs the `devices` decision, which is the `.tfvars` `target` fact the write path
  holds (`backlog.md`).

## Open pieces for Epic 7

- A parse method for a routing level `PROTOCOL_SHAPE` does not state: `ospfv3`, `rip`, the BGP
  `policy`, the timer levels, the auth profile bodies, and the filter containers. A level becomes
  printable only when a parse method reads it and the table has a row for it, because the emitter,
  the gate and the report all read that table.
