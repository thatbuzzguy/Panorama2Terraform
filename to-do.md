# To Do

No feature in progress. F6.3 (the reference between units as an edge list, and the unit order as data) is
complete; its pieces are recorded in the git history and in `agent-status.md`.

The next feature in `PLAN.md` is **F6.4 — import blocks**. Its acceptance criteria are not written yet.

Open pieces for Epic 6, held here until the next feature takes them:

- The directory write path: F6.1, F6.2 and F6.3 name the unit, the owner, the pair and the order, and
  write no directory.
- The gate rule that reads a data file: the gate reads `.tf` files only, so no data file is a gate input
  today.
- The outputs rule for a name another unit owns, which F6.3 left open: the generator writes no outputs, so
  the edge record states the pair and the order and cannot resolve the name.
- F6.4 import blocks, the rulebase decision for the four `*_policy_rules` types, the site data layer
  (F6.6), and the commit action (F6.7).
