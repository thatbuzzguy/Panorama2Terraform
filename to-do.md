# To-Do — current task: F3.3 Full interface types (Epic 3)

**F3.2 is complete** (committed this session). Detail is in the git history.

Direction: work the lowest-numbered unfinished feature in Epic 3. F3.3 —
full interface types: not only physical ethernet.

Acceptance criteria for the current task go in `acceptance.md` before
code (overwrite the F3.2 record when F3.3 starts).

## F3.3 sub-tasks

- [ ] Overwrite `acceptance.md` with F3.3 criteria.
- [ ] Confirm the v2.0.14 resource types for vlan, loopback, tunnel,
      aggregate-ethernet, and virtual-wire interfaces against the live
      schema before adding them to `EMITTED_TYPES` (no type from memory).
- [ ] Parse ethernet subinterface units (`ethernet/entry/units/entry`) as
      individual interfaces — the F1.6 extraction gap in `backlog.md`.
- [ ] Parse virtual-wire interface units
      (`network/interface/virtual-wire/units/entry`).
- [ ] Emitters for each kind: v2 nested shapes, `location`, dependency
      wiring, and the F3.2 (context, vsys) identity key.
- [ ] Fixtures and tests per kind; `COVERAGE_MATRIX` rows for each new
      emitted type.
- [ ] Regenerate both goldens; review the diff.
- [ ] Gates: ruff clean, pytest green, terraform validate green.
- [ ] Commit; update PLAN.md, to-do.md, agent-status.md, backlog.md.

## Deferred (tracked in PLAN.md)

- **Epic 3:** F3.4–F3.10 after F3.3.
- **Epic 4:** F4.1 (post-run sanity gate; its dead-variable check
  reuses the F2.10 test), F4.2 (container table + line tracking; may
  land during Epic 3), F4.3 (per-entry `CONVERSION_REPORT.txt`; after
  F3.1), F4.4 (property-level matrix extending the landed F2.8
  type-level matrix; after F3.1, last in Epic 4).

## Notes

- The static no-dangling-reference rule already exists as a test in
  `tests/test_dependency_wiring.py`; F4.1 shares that rule with the
  runtime check instead of copying it.
- The coverage report (F4.3/F4.4) keys on logical entries
  (`<entry name>` plus its properties), not physical lines; the
  reported line number is the entry's opening tag. Decision recorded
  in `backlog.md`.
- Naming contract (F2.7 + F3.2): sanitized base + 8-hex digest of
  (scope, context, vsys, name); order-independent; per-type domains;
  references resolve through the (context, vsys) chain then the flat
  fallback. Interface emitters must pass the interface's own vsys.
