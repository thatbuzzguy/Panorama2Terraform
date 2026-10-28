# To Do

No feature in progress. F6.4 (import blocks, one block per entry, and the import agreement gate rule) is
complete; its pieces are recorded in the git history and in `agent-status.md`.

The next feature in `PLAN.md` is **F6.5 — scope objects as output**. Its acceptance criteria are not
written yet.

Open pieces for Epic 6, held here until the next feature takes them:

- The directory write path: F6.1, F6.2, F6.3 and F6.4 name the unit, the owner, the pair, the order and
  the block, and write no directory. `imports.tf` is one file for the run; the step that splits the output
  per unit directory is still open.
- The gate rule that reads a data file: the gate reads `.tf` files only, so no data file is a gate input
  today. `imports.tf` is a `.tf` file, so the agreement rule reads it.
- The outputs rule for a name another unit owns, which F6.3 left open: the generator writes no outputs, so
  the edge record states the pair and the order and cannot resolve the name.
- The rule types: F6.4 writes no import block for the four `*_policy_rules` types and reports each rule
  entry as a WARN. The position must be the position the live config holds, and the F3.5 rulebase decision
  gates it.
- The generated `README.md` does not name `imports.tf`. The F5.5 label precedent says an opt-in shape
  labels itself.
- F6.5 scope objects, the site data layer (F6.6), and the commit action (F6.7).
