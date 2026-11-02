# Acceptance criteria — F6.10.5 (close Epic 6)

This is the closing slice of Epic 6 (`docs/CODEBASE_ASSEMBLY.md`, `PLAN.md`). It decides two rules,
closes one housekeeping item, verifies the gated pieces, and closes the epic. `ruff check .` and
`python3 -m pytest` must pass at the end.

## 1. The template stack unit rule (decided)

**Decision: the stack is the fifth scope fact.** The unit rule names a unit by a fact, so a scope that
names no fact cannot name a unit. `docs/CODEBASE_ASSEMBLY.md` §1 rule 1 names the template stack as a
scope a unit is, and `container_coverage.SCOPE_CONTAINERS` holds `template-stack`, so the fact set must
cover it.

Do not read `template` as the stack name. Three rules already name `template_stack` as its own key, and
reading `template` as the stack name gives one fact two meanings:

- `resource_mapping.ACTION_FILTERS` maps `template_stacks` → `template_stack`, so a stack unit's commit
  block prints `type = "template_stack"`. With `template` as the stack name, the same filter field would
  name a template, and `SCOPE_ANSWER['template']` would answer `panos_template` for a stack name.
- `resource_mapping.SCOPE_PLACEMENT` gives `panos_template_variable` the two sub-blocks `template` and
  `template_stack`, so an entry inside a stack must print the stack sub-block, not the template sub-block.
- `entry_coverage.REPORT_SCOPE_KEYS` maps a scope container to the field the block carries the name in.
  Adding the fact puts `template-stack` in that mapping, and the property scan stops counting
  `template_stack` as captured content for the variable row.

Criteria:

1. `container_coverage.SCOPE_FACT_KEYS` is the one place that names the facts, and it holds five:
   `device_group`, `vsys`, `template`, `vsys_device`, `template_stack`. No module defines a second fact
   order.
2. The parser walks the stack the same way it walks the other scope containers
   (`container_coverage.parent_map`, one walk per fact), and every parse method records it through
   `identity_of`. A stack entry names its own stack; an entry the export places in no stack states `''`.
3. `unit_manifest.NAME_LEVELS` reads innermost first: `vsys`, `vsys_device`, `template`,
   `template_stack`, `device_group`. A template inside a stack names its template, because the template is
   deeper than the stack. A stack entry names the stack, so a run that declares a stack writes one unit
   directory for it, and the commit and push blocks for that unit come from `ACTION_FILTERS`.
4. The unit identity join is `SCOPE_FACT_KEYS` order (`docs/ARCHITECTURE.md` §5), so every unit digest
   changes. The goldens regenerate from a real run, never by hand, and the measured pins in the tests
   that name a digest are re-measured from the same run.
5. `CODEBASE_MANIFEST.json` gains the field for the fifth fact, in the same position as the fact order,
   and `parse_rows` still refuses a row that is not the declared shape.
6. `state_coverage.STATE_SCOPE_KEYS` maps the `template_stack` location sub-block to the fact, so a state
   entry placed inside a stack is keyed. The rule that a block naming no fact is not keyed still holds for
   the sub-blocks the table does not declare.
7. The variable inside a stack stops being a captured property, so `COVERAGE_MATRIX` row
   `panos_template_variable` lists four properties, not five. The printed bytes for that block do not
   change, because the emitter already prints the stack sub-block from the placement key.
8. `docs/ARCHITECTURE.md` §2.2 stays the owner of the fact set, and every other document links to it. The
   statement that no stack unit is named today is removed from `docs/CODEBASE_ASSEMBLY.md` §3.

## 2. The module parameter rule (decided)

**Decision: the tool does not decide module parameters.** A module is a standard a person writes
(`docs/CODEBASE_ASSEMBLY.md` §13), so the tool writes the data a module consumes and cannot know which
values a module takes. A template variable value, and a membership list in `scope.tf`, stay the literal
the export states: the variable block *is* the PAN-OS variable. This closes with no byte change; the open
item is removed from `backlog.md`, and §9 rule 2 stays the owner of the behavior.

Criteria:

1. No new shape word in `resource_mapping.VALUE_VARIABLES`, and no new rule that decides a shape a second
   time. `VALUE_VARIABLES` stays the single shape owner.
2. The emitter prints a template variable value as the export states it, and the property scan measures the
   same list the row declares.
3. The open item is removed from `backlog.md`, and no document restates the decision.

## 3. Housekeeping: the sample output

**Decision: the repository holds no committed sample output.** `terraform_output/` is the default value of
`--output-dir`, and `.gitignore` ignores it, so a regenerated sample cannot be committed. The canonical
sample output is the pinned golden set (`tests/golden/sample/`, `tests/golden/kitchen_sink/`,
`tests/golden/single_unit/`), which cannot drift from what the converter writes.

Criteria:

1. `git ls-files terraform_output/` is empty, so there is nothing to regenerate and nothing to delete; the
   stale claim in `backlog.md` is removed.
2. `examples/example_terraform_output.txt` names the golden set as the canonical sample output, and no
   document calls `terraform_output/` committed sample output.
3. The layout work that renames paths (`src/`, the module set, `quick_start.sh`) stays in `backlog.md`,
   because it renames the paths the tests read.

## 4. The gated pieces

The four `*_policy_rules` types stay gated by the F3.5 rulebase decision. They are not part of this slice
and stay in `backlog.md`, not in `to-do.md`. No import block, no action, and no gate rule changes for them.

The write path gate keeps its rules: one writer, the two path builders, the `.tf` set read by the block
rules and the four records read by the data rule, no new CLI flag, and the exit codes unchanged.

## 5. Tracking markdown

1. `PLAN.md`: Epic 6 is closed, so its feature detail is removed; the open work is the next feature queue.
2. `to-do.md`: the completed F6.10.5 pieces are removed.
3. `agent-status.md`: the position, the test count, and the pins that changed.
4. No document restates a rule another document owns, and no document states a test count.
5. Every claim names the module or the test that holds it.

## 6. Commit

One commit whose message starts with `F6.10.5:`, states the two decisions and the housekeeping choice in
ASD-STE100, and states that Epic 6 is closed.
