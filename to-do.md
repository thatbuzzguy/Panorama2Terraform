# To Do

F6.10.3 (the directory write) is complete and committed: `write_path.py` is the one place a run writes a file,
the run writes one directory per unit the manifest names, the gate reads the unit set as paths from the codebase
root, the plan check runs once per unit directory, and both golden sets hold the per-unit layout with the LF rule
(`docs/ARCHITECTURE.md` §6).

Current feature: F6.10 — the write path (Epic 6). The shape is decided and landed
(`docs/CODEBASE_ASSEMBLY.md` §14), so the open work is the facts the write path can now decide. The slices run
in order, one at a time, and each slice commits its own work.

## F6.10 slices, in order

1. **F6.10.4 — the site half.** The per-unit `.tfvars` fact that names one `target` serial, and the
   `panos_push_to_devices` shape that fact unlocks. The generated `README.md` names `imports.tf`,
   `SITE_DATA.json` and `site.auto.tfvars`, by the F5.5 label precedent.
2. **F6.10.5 — close Epic 6.** Decide the held pieces the write path can now decide: the template stack unit (a
   fifth fact, or `template` read as the stack name), and the module parameter rule for a template variable
   value and a membership list. The four `*_policy_rules` types stay gated by the F3.5 rulebase decision and
   stay in `backlog.md` if they cannot land. Clear the completed slices, clean the tracking markdown, and
   commit.

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
