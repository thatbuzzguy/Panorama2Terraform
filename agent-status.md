# Agent Status

## Current position

Housekeeping session (2026-10-29): the root markdown is cleaned and completed work is removed.
`ADVERSARIAL_AUDIT_REPORT.md` is gone; the audit is closed and the git history holds the report.
`PLAN.md`, `backlog.md`, `to-do.md`, `agent-status.md`, and `acceptance.md` now hold only the
current state, the goals, the open items, and the design decisions that are still live rules.
No code feature is in progress. The next feature in `PLAN.md` is F6.7 (the commit action), which
needs the Terraform minimum decision.

The completed features F6.1 to F6.6 are committed; each feature's change list and measured facts
are in the git history. The open pieces are in `to-do.md`, and the open decisions are in
`backlog.md`.

State at the commit: `ruff check .` clean, `pytest` 1169 passed, exit codes unchanged (0, input
refusal 1, argument error 2), no test logic changed. Docstring pointers that named removed
markdown now name the owner document: `import_blocks.py` rule 5, `tests/test_scope_objects.py`,
`tests/test_site_data.py`, `tests/test_unit_manifest.py`, `tests/test_ownership.py`,
`tests/test_reference_edges.py`, and `tests/test_smoke.py`.

## Rules to keep when writing documents

- One owner document per rule; every other document links to it.
- Machine-readable tables are code. A document explains a table and never restates it
  row by row, so a regenerated table cannot drift.
- No test counts in a document. A document names the test that pins a rule; the
  count lives in `agent-status.md` and the git history.
- A claim about what the tool does must name the module or the test that holds it. A
  feature id is written only when a module or a test uses it as a name.
- ASD-STE100 Simplified Technical English, no marketing voice, no emoji.
- A historical record is not kept in the markdown. The git history is the record, and the
  markdown states the current state.
- A record is data, so a document describes its fields and never restates a record. The
  example in `docs/USAGE_GUIDE.md` is an illustration with a shortened hash, not a pin.
- Completed epic, phase, feature and task detail is removed from the tracking markdown after
  the work is committed; `AGENTS.md` states the rule.

## Watch for Epic 6

- The codebase modules name the unit, the owner, the pair, the order, the block, the scope
  object and the site, and write no directory. The write path is the step that turns a
  `directory` field into a real directory, and `scope.tf`, `imports.tf` and `site.auto.tfvars`
  are one file for the run until it lands.
- The block reader in `sanity_checks.py` serves every kind, so the `action` rule (F6.7) must use
  `blocks(files, kinds)`; no second block reader should appear.
- The gate reads `.tf` files only, so no data file is a gate input today. `scope.tf` and
  `imports.tf` are `.tf` files and are gate inputs. If a codebase feature makes a data file a
  gate input, the file set statement in `ARCHITECTURE.md` §4.5, the `.tfvars` statement in §4.5,
  and the no-change tests must change together.
- A field reader must read at the block's own level and stop at the closing quote, or a
  sub-block field or an escaped quote answers for the block's field. Both are pinned in
  `tests/test_import_blocks.py`, and the scope rule reads at the block's own level through the
  same reader. The same reader also tells a quoted value from a `var.` reference, so no second
  rule decides the shape of a field.
- `SCOPE_PLACEMENT` and the location sub-block are one fact: a new scope type needs both the
  placement key and the `SCOPE_ANSWER` entry, and the emitter reads the placement key as the
  location, so a new row cannot place itself in a scope it does not name.
- The entry name is never a property. A row whose provider type declares no `name` reaches the
  block through `entry_coverage.name_field`; no emitter, gate rule, or test should state the
  field again.
- One place decides the shape of a value: `resource_mapping.VALUE_VARIABLES`, read at the print
  site. A new field a table row maps must be read by the emitter, the gate and the `.tfvars`
  writer through the same table, and the table must cover every field `LOCATION_SCHEMA` declares.
- The §5 naming rule lives in `naming.py`. No module may define a second one;
  `TerraformGenerator.sanitize_name` is a delegate and the data modules take the rule as an
  argument.
- The import position for the four `*_policy_rules` types must be the position the live config
  holds, and the F3.5 rulebase decision gates it. No block is written for a rule entry until both
  land.
- The generated `README.md` does not name `imports.tf`, `SITE_DATA.json` or `site.auto.tfvars`;
  the F5.5 label precedent says an opt-in shape labels itself.
- Actions need Terraform 1.14 or later; the committed goldens declare no Terraform minimum.
- The credential rule needs one statement that covers both the fetch layer and the generated
  provider block.
- The prune action still needs the record directory decided. A state record references nothing,
  so it prunes nothing, and the prune rule reads a record file, not one record.
- A coverage fact that comes from a run must be read from the run's ledger, so the scan tests run
  the pipeline in process.
- A cycle test needs the referrer entry and the declaring entry in the same unit, for the reason
  recorded in the git history for F6.3.
