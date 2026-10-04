# Acceptance Criteria — F2.5: Order-preserving policy

## Scope
Replace the blanket `position = { where = "last" }` on every policy rule
with order-preserving `position` values. Rules emit in XML order per
(device group, rulebase). Terraform applies each chain in a defined order.
Covers `panos_security_policy_rules` and `panos_nat_policy_rules`.

## Provider v2.0.14 semantics (verified from provider source)
- `position.where` must be one of `first`, `last`, `before`, `after`
  (provider `ValidateConfig` rejects anything else).
- `where = "after"` or `"before"` requires BOTH `pivot` (an existing rule
  name) and `directly` (bool). `directly = true` places the rule
  immediately after the pivot.
- If the pivot does not exist on the server, the move fails
  (`ErrPivotNotInExisting`). So a rule that pivots on a rule created in
  the same apply must declare a `depends_on` on that rule.

## Design
- Keep the F2.4 one-resource-per-rule structure.
- Group rules into chains by the parser-recorded `device_group`,
  preserving XML document order within each chain. Chains emit in
  first-seen order.
- First rule of a chain: `position = { where = "last" }`. This anchors
  the managed block at the end of the rulebase, the least disruptive
  choice for a brown-field rulebase (existing rules keep their relative
  order and evaluation priority).
- Rule i (i > 1): `position = { where = "after", directly = true,
  pivot = "<XML name of rule i-1>" }` plus
  `depends_on = [<type>.<local name of rule i-1 resource>]`.
- `pivot` uses the Panorama (XML) rule name; `depends_on` uses the
  generated Terraform local name.

## Tests (new `tests/test_policy_order.py` + fixture `policy_order.xml`)
- Fixture: three device groups (3 + 2 + 1 security rules, 2 NAT rules in
  the first group), known XML order.
- Per-chain rule order in the .tf equals the XML order.
- First rule of each chain: `where = "last"`, no `pivot`, no
  `depends_on`.
- Rule i > 1: `where = "after"`, `directly = true`, `pivot` = previous
  rule's XML name, `depends_on` = exactly the previous rule's resource.
- Chains are independent: no `depends_on` crosses device groups.
- NAT rules follow the same semantics.
- Single-rule chain (Gamma-DG) has only the anchor position.
- The same position assertions hold on the committed goldens.

## Goldens and docs
- Regenerate sample + kitchen-sink goldens (rule files change; other
  files byte-identical).
- README policy line corrected to the actual per-rule chain design.
- `to-do.md`, `PLAN.md`, `agent-status.md` updated; `backlog.md` notes
  the pre/post/shared rulebase tracking gap.

## Gate
- ruff clean.
- Full pytest suite green; no new xfails.
- `terraform validate` green on both generated corpora.
- Commit with a detailed ASD-STE100 message.
