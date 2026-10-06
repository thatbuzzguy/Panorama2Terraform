# To-Do — next: Epic 3 (F3.1 Keyed data model)

**Epic 2 is complete** (F2.1–F2.11, 2026-10-05). Marked COMPLETE in
`PLAN.md`; detail is in the git history.

Direction: work the lowest-numbered unfinished epic. The next task is
**F3.1 Keyed data model** — replace name-keyed dictionaries with keys
of (device group, vsys, type, name); remove first-wins and last-wins
deduplication. It unblocks F3.2, F3.5, and the F3.1-pinned xfail in
`tests/test_edge_cases.py`.

Acceptance criteria for the current task go in `acceptance.md` before
code.

## Deferred (tracked in PLAN.md)

- **Epic 3:** F3.1 first, then F3.2–F3.10.
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
- F3.1 must keep the F2.7 naming contract: `declare_resource_name`
  already digests (type, defining device group or template, raw name),
  so keyed objects map 1:1 onto existing local resource names.
- F2.5 rule chains group by the parser-recorded device group; F3.1
  only needs to stop the cross-DG name dedup so same-named rules in
  different device groups both survive inside their own chains.
