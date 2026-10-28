# To Do

No feature is in progress. F6.2 (ownership as data) is complete and committed
(`44496dd`), so its task list is removed here.

The next feature in `PLAN.md` is F6.3 (the reference between units as an edge list). It is not started.

Open pieces for Epic 6, held here until the next feature takes them:

- The directory write path: F6.1 and F6.2 name the unit and the owner and write no directory.
- The gate rule that reads a data file: the gate reads `.tf` files only, so neither data file is a
  gate input today.
- F6.3 must decide whether the reference fact stays one fact (names per unit) or splits into two kinds
  (outside the run, ambiguous inside the run), and the record shape that holds (referrer unit, target
  unit).
- F6.4 import blocks, the rulebase decision for the four `*_policy_rules` types, the site data layer
  (F6.6), and the commit action (F6.7).
