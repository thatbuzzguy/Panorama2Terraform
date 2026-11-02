# To Do

F6.10.4 (the site half) is complete and committed: `target` is one row in `resource_mapping.VALUE_VARIABLES` with
the shape word `operator_supplied`, so the run names the variable and holds no value for it and the operator
supplies the serial; `provider.tf` is the consumer for a unit that names a device; `panos_push_to_devices` prints
the fact and the fact key with no `devices`; and the generated `README.md` names `imports.tf`, `SITE_DATA.json` and
`site.auto.tfvars` (`docs/CODEBASE_ASSEMBLY.md` §9 rules 8 and 9, §10 rule 5).

Current feature: F6.10.5 — close Epic 6. The write path is landed (`docs/CODEBASE_ASSEMBLY.md` §14), so the open
work is the facts it can now decide.

## F6.10.5, in order

1. Decide the template stack unit: a fifth fact, or `template` read as the stack name. The stack is a scope
   container, so a stack can be a codebase unit, but the manifest names no stack unit today
   (`container_coverage.SCOPE_CONTAINERS`).
2. Decide the module parameter rule for a template variable value and a membership list: a module is a standard a
   person writes, so a value stays a literal until the tool states what a module takes.
3. The four `*_policy_rules` types stay gated by the F3.5 rulebase decision and stay in `backlog.md` if they
   cannot land.
4. Clear the completed slices, clean the tracking markdown, and commit.

## Rules the write path keeps

- One function writes a file (`write_path.py`), so the LF rule is enforced once (`ARCHITECTURE.md` §6), and the
  two path builders name the two sets. No module writes a file outside it.
- The gate reads the `.tf` files for the block rules and the four records for the data rule; the two file sets
  stay distinct. A new file shape must name which set it belongs to.
- One place decides the shape of a value (`resource_mapping.VALUE_VARIABLES`) and one place decides the shape of
  a reference field (`TerraformGenerator.name_ref`); the write path applies them per unit and defines no second
  rule.
- The §5 naming rule lives in `naming.py`; the data modules take it as an argument.
- A per-unit file names its unit only by its directory, so no per-unit file states a path in its bytes, and a
  gate finding names the path from the codebase root.
- The data rule reads the records at the codebase root only, as one rule over the rows of every unit. No rule
  reads a report, `README.md` or `SOURCE.txt`. No flag names the layout, and the exit codes are unchanged.
- A cycle test needs two units that each declare a name the other one uses, because the reference rule resolves
  only inside the referrer's own unit (`tests/test_reference_edges.py`, `tests/fixtures/reference_cycle.xml`).
