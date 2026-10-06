# To-Do — next: Epic 3 (F3.2 Preserve device-group association)

**Epic 2 is complete** (F2.1–F2.11, 2026-10-05). Marked COMPLETE in
`PLAN.md`; detail is in the git history.

Direction: work the lowest-numbered unfinished epic. F3.1 (keyed data
model) landed: the parser visits each entry once and records
`device_group` + `vsys` on every object; `name_ref` resolves by the
referrer's context. The next task is **F3.2 Preserve device-group
association** — carry the source device group from parse to emit so
same-named objects in different device groups both survive in the
generated output (the parser half is done; the emit half remains).

Acceptance criteria for the current task go in `acceptance.md` before
code.

## Deferred (tracked in PLAN.md)

- **Epic 3:** F3.2 next, then F3.3–F3.10.
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
- F3.1 kept the F2.7 naming contract and the goldens byte-identical:
  shared objects keep the legacy `'Shared'` context, template-scoped
  objects keep the contextless convention, and the profile categories
  keep their pre-F3.1 contextless digest (the true DG/template identity
  for those lands with F3.6).
