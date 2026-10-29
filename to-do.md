# To Do

No feature is in progress. F6.5 (scope objects as output, Epic 6 Goal 6) is complete and committed as
`F6.5: scope objects as output`. Its rules are in `docs/CODEBASE_ASSEMBLY.md` §8 and §6,
`docs/ARCHITECTURE.md` §3.2, §4.1, §4.2, §4.6 and `docs/COVERAGE_MATRIX.md`, and its tests are in
`tests/test_scope_objects.py`.

The next feature in `PLAN.md` is F6.6 (the site data layer). It takes the template variable literal
F6.5 prints, so the value-to-variable mapping has to become a pinned table first.

Open pieces for Epic 6, held here until the next feature takes them:

- The directory write path: F6.1, F6.2, F6.3, F6.4 and F6.5 name the unit, the owner, the pair, the
  order, the block and the scope object, and write no directory. `scope.tf` is one file for the run; the
  step that splits the output per unit directory is still open.
- The gate rule that reads a data file: the gate reads `.tf` files only, so no data file is a gate
  input today. `imports.tf` and `scope.tf` are `.tf` files, so the gate rules read them.
- The outputs rule for a name another unit owns, which F6.3 left open.
- The rule types: F6.4 writes no import block for the four `*_policy_rules` types.
- The generated `README.md` does not name `imports.tf`; it names `scope.tf`.
- A template stack is a scope container but not one of the four scope facts, so the manifest names no
  stack unit. A stack unit needs a fifth fact, or the decision to read `template` as the stack name.
- F6.6 (the site data layer and the device name as a variable) and F6.7 (the commit action).
