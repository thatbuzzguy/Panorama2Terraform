# To-Do — current task: F3.5 Multi-vsys (Epic 3)

**F3.4 is complete** (committed this session). Detail is in the git history.

Direction: work the lowest-numbered unfinished feature in Epic 3. F3.5 —
multi-vsys: represent vsys in the data model and in `location`.

Acceptance criteria for the current task go in `acceptance.md` before
code (overwrite the F3.4 record when F3.5 starts).

## F3.5 sub-tasks

- [ ] Overwrite `acceptance.md` with F3.5 criteria.
- [ ] Confirm against the live v2.0.14 schema where vsys can appear in
      `location` per resource type (the F3.3 note says object types have no
      vsys sub-block; verify per type, do not assume).
- [ ] Audit what the keyed model already covers: F3.1 records `vsys` on
      every object, F3.2 puts it in the naming digest and the reference
      chain, and policy chains key on (device group, vsys). Record the
      remaining gap instead of re-doing landed work.
- [ ] Check every parse path finds vsys correctly for a multi-vsys export
      (vsys1/vsys2 siblings, member lists, objects under a device group).
- [ ] Emit vsys where the schema accepts it; report it where it does not,
      so an operator can place the object in the right virtual system.
- [ ] Fixtures and tests for a two-vsys export; both goldens reviewed.
- [ ] Gates: ruff clean, pytest green, terraform validate green.
- [ ] Commit; update PLAN.md, to-do.md, agent-status.md, backlog.md.

## Deferred (tracked in PLAN.md)

- **Epic 3:** F3.6–F3.10 after F3.5.
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
- Object types with no v2 attribute are report-only since F3.4
  (`report_only` on the parsed entry, section in
  `MANUAL_SETUP_REPORT.txt`). Any new "cannot emit" case follows that
  pattern: keep the data in the parse model, emit nothing invalid, and
  name the captured values in the report.
- `panos_service` takes one protocol leg only (verified with
  `terraform validate`); `primary_service_protocol` picks tcp first and the
  dropped leg is reported. Do not "fix" this by emitting both legs.
- Interface name convention (F3.3): the emitted `name` is the PAN-OS
  display name (`vlan.10`, `ethernet1/1.0`, `ae1.101`), with `parent` as a
  separate attribute. Subinterface `tag` is emitted only for the layer-3
  subinterface resource types, which are the only types that carry it in
  the schema.
- Interface `location` is template-scoped for every interface kind
  (`_TEMPLATE_SCOPED_TYPES`), verified against the v2.0.14 schema.
- The static no-dangling-reference rule already exists as a test in
  `tests/test_dependency_wiring.py`; F4.1 shares that rule with the
  runtime check instead of copying it.
- The coverage report (F4.3/F4.4) keys on logical entries
  (`<entry name>` plus its properties), not physical lines; the
  reported line number is the entry's opening tag. Decision recorded
  in `backlog.md`.
