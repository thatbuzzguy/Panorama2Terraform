# Acceptance — rules as data: the decision record (Epic 9, Piece 16)

Criteria set 2026-11-18 for the new requirement: rule entries are written as a data file, and one
Terraform object iterates the file instead of the tool writing one block per rule. This task is the
decision record. No code, no test, no fixture, and no golden changed; the criteria for each piece
are set when that piece begins.

Owners unchanged: `docs/ARCHITECTURE.md` §1.1 owns the layout and names every module through the
§1 table; `entry_coverage.py` owns the destination rule; `naming.py` owns the §5 naming rule;
`write_path.py` is the one writer; `sanity_checks.py` owns the gate rules; `COVERAGE_MATRIX.md` §1
owns the honesty rule. This piece states no second rule for any of them.

## The four decisions

- D1: the tool writes the iterated object: one resource block with `for_each` per rule type per
  unit. The tool stays the writer of blocks and data files, and the iterated block is its own
  emitted shape. This extends the backlog line that a module is a standard a person writes and the
  tool's part is the data file: the tool's part becomes the data file plus its own iterated block.
- D2: the rule rows are a data file with two forms of the same rows. JSON is the form a Terraform
  object reads, because Terraform has no CSV decode function. CSV is the printed form, the way the
  `.tfvars` is the printed form of the site record. The declared row shape is `RULE_ROW_FIELDS`,
  read by `parse_rows` the way the other four data files are read.
- D3: one object per rule type per unit directory, so the rule rows join to the manifest on
  `directory` and the action blocks stay per unit.
- D4: the `for_each` key is the zero-padded chain ordinal joined to the identity digest, so the
  sorted key order is the XML order inside a chain. The pivot moves from the block to a row column.
  The `depends_on` fact drops with the per-rule block shape, because instances inside one block
  create in key order. This changes the F2.5 rule that `tests/test_policy_order.py` pins, so the
  change is measured as its own piece, not inside the decision record.

## Rules the decisions inherit

- Identity (`docs/ARCHITECTURE.md` §2.1): the key cannot be the rule name alone. A name in two
  device groups or two virtual systems is two rules, so the key carries the identity digest.
- Honesty (`COVERAGE_MATRIX.md` §1): every column names a field the parse captured through the
  recorded object, so `RULE_ROW_FIELDS` is the matrix field set for the four rule containers plus
  the scope facts, the chain ordinal, and the pivot.
- Site values: a block prints the variable reference, never the value, and a block cannot turn a
  column value into a variable reference, so a site column resolves through a `locals` map read
  from the site rows.
- References: F2.6 and F6.10.2 resolution runs through the one naming rule; the row records whether
  a name resolved inside the unit, so the edge rule reads the rows with no second naming rule.
- F3.5 stays open on its own conditions: the rulebase value string, the position from a live
  source, and the import block for a rule entry. The rulebase column prints nothing until the
  decision lands. The Terraform 1.14 floor already covers `for_each` on import blocks when the
  import rule lands.
- The cross-check keeps its boundary: the rule-container rows compare the row set against the
  ledger instead of the block set, because one iterated block holds N entries.

## Criteria for this task

- AC-1: `PLAN.md` names Epic 9, the four decisions, the four phases, the held conditions, and the
  definition of done.
- AC-2: `to-do.md` names the pieces in order and replaces the "no offline-actionable item
  remains" state with the open feature.
- AC-3: no `src/` module, no test module, no fixture, no golden, and no index changes, so the gate
  is unaffected and no pin changes.
- AC-4: this file holds the record; the piece measurements go to `agent-status.md` at the commit.

## Gate

`ruff check .`, `ruff format --check .`, `python3 -m pytest`, `python3 tools/check_documents.py`,
in that order, conservative threads. This task changes only documents, so a run reads the same pin
set as the committed tree at `ee72345`: 1,697 pins in 52 modules, unchanged. `check_documents.py`
must report no finding, because `PLAN.md`, `to-do.md`, and `acceptance.md` are the tracking set that
`AGENTS.md` names, and the root index names them.