# To Do

The housekeeping task (clean the root markdown, remove completed work) is complete and committed;
the change is in the git history. No code feature is in progress.

The next feature in `PLAN.md` is F6.7 (the commit action). Before writing code or tests for it,
overwrite `acceptance.md` with its acceptance criteria. It needs the Terraform minimum decision,
and the gate rule for an `action` block must read through the one block reader.

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
