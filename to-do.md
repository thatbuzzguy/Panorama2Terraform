# To Do

F6.10.1 (the shape of the write path) is complete and committed: it is a decision, so it
writes no output byte. `docs/CODEBASE_ASSEMBLY.md` §14 records it, and
`tests/test_write_path.py` pins what the decision can pin.

Current feature: F6.10 — the write path (Epic 6). The print-site rule is decided
(`docs/CODEBASE_ASSEMBLY.md` §5 rule 5, F6.9), so this feature is the step that turns the
manifest `directory` field into a real directory per declared scope, holding the unit set §14
states. The slices run in order, one at a time. Each slice commits its own work.

## F6.10 slices, in order

1. **F6.10.2 — the print site per unit.** `name_ref` runs per unit, so a name the flat chain
   resolves across scopes today becomes a plain name when the run names more than one unit.
   The edge record and the manifest `references` field grow to name every cross-unit use, so
   the corpus pin lists change (`tests/test_reference_edges.py::CORPUS_EDGES` and
   `tests/test_unit_manifest.py::GROUPING_REFERENCES`).
2. **F6.10.3 — the directory write.** One directory per unit the manifest names, holding the
   unit set §14 states; the codebase root keeps the root set. The `.tf` files print per unit. The
   LF rule lands (a byte rule, so the goldens and the no-change tests change with it). The block
   rules read the per-unit `.tf` files through the one reader, keyed by the path from the codebase
   root, and the data rule keeps reading the records through `parse_rows` as one rule over the
   records of every unit, not one rule per unit. The goldens regenerate with the per-unit layout,
   so the golden pin reads the `.tf` set as paths from the case directory, and the gate finding for
   a per-unit file names the path. The plan check runs once per unit directory.
3. **F6.10.4 — the site half.** The per-unit `.tfvars` that names one `target` serial. The
   `panos_push_to_devices` shape decision that the `.tfvars` `target` fact unlocks. The
   generated `README.md` names `imports.tf`, `SITE_DATA.json` and `site.auto.tfvars`, by the
   F5.5 label precedent.
4. **F6.10.5 — close Epic 6.** Decide the held pieces the write path can now decide: the
   template stack unit (a fifth fact, or `template` read as the stack name); the module
   parameter rule for a template variable value and a membership list; `scope.tf` per unit.
   The four `*_policy_rules` types stay gated by the F3.5 rulebase decision and stay in
   `backlog.md` if they cannot land. Clear the completed slices, clean the tracking markdown,
   and commit.

## Rules the write path must keep

- The LF rule is a byte rule, so the goldens and the no-change tests change with the write
  path (`backlog.md`).
- The gate reads the `.tf` files for the block rules and the four data files for the data
  rule; the two file sets stay distinct. A new file shape must name which set it belongs to.
- One place decides the shape of a value (`resource_mapping.VALUE_VARIABLES`) and one place
  decides the shape of a reference field (`TerraformGenerator.name_ref`); the write path
  applies them per unit and defines no second rule.
- The §5 naming rule lives in `naming.py`; the data modules take it as an argument.
- A cycle test needs the referrer entry and the declaring entry in the same unit
  (`tests/test_reference_edges.py`, group for F6.3).
