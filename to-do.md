# To-Do — current task: F3.4 Full object types (Epic 3)

**F3.3 is complete** (committed this session). Detail is in the git history.

Direction: work the lowest-numbered unfinished feature in Epic 3. F3.4 —
full object types: address types beyond static and range, and service
types beyond single-port.

Acceptance criteria for the current task go in `acceptance.md` before
code (overwrite the F3.3 record when F3.4 starts).

## F3.4 sub-tasks

- [ ] Overwrite `acceptance.md` with F3.4 criteria.
- [ ] Confirm the v2.0.14 address shapes for `ip-wildcard`, `external`,
      and `location` types against the live schema (no attribute from
      memory).
- [ ] Parse the remaining address `type` values in
      `parse_addresses` (currently static / range / group only).
- [ ] Parse multi-port services and combined tcp+udp services in
      `parse_services`.
- [ ] Emit each verified type/shape; keep the F2.7 + F3.2 naming
      contract (digest input includes vsys, per-type domains, no
      dangling references).
- [ ] Fixtures and tests per new shape; `COVERAGE_MATRIX` rows only for
      newly emitted types.
- [ ] Regenerate both goldens; review the diff.
- [ ] Gates: ruff clean, pytest green, terraform validate green.
- [ ] Commit; update PLAN.md, to-do.md, agent-status.md, backlog.md.

## Deferred (tracked in PLAN.md)

- **Epic 3:** F3.5–F3.10 after F3.4.
- **Epic 4:** F4.1 (post-run sanity gate; its dead-variable check
  reuses the F2.10 test), F4.2 (container table + line tracking; may
  land during Epic 3), F4.3 (per-entry `CONVERSION_REPORT.txt`; after
  F3.1), F4.4 (property-level matrix extending the landed F2.8
  type-level matrix; after F3.1, last in Epic 4).

## Notes

- Naming contract (F2.7 + F3.2): sanitized base + 8-hex digest of
  (scope, context, vsys, name); order-independent; per-type domains;
  references resolve through the (context, vsys) chain then the flat
  fallback. Every emitter passes the object's own vsys.
- Interface name convention (F3.3): the emitted `name` is the PAN-OS
  display name (`vlan.10`, `ethernet1/1.0`, `ae1.101`), with `parent`
  as a separate attribute. Subinterface `tag` is emitted only for the
  layer-3 subinterface resource types, which are the only types that
  carry it in the schema.
- Interface `location` is template-scoped for every interface kind
  (`_TEMPLATE_SCOPED_TYPES`), verified against the v2.0.14 schema.
- The static no-dangling-reference rule already exists as a test in
  `tests/test_dependency_wiring.py`; F4.1 shares that rule with the
  runtime check instead of copying it.
- The coverage report (F4.3/F4.4) keys on logical entries
  (`<entry name>` plus its properties), not physical lines; the
  reported line number is the entry's opening tag. Decision recorded
  in `backlog.md`.
