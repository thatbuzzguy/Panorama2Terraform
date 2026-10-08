# To-Do — current task: F3.6 Multi-device, template-aware parsing (Epic 3)

**F3.5 is complete** (multi-vsys identity and `location`; evidence in the
commit log and in `acceptance.md`). Direction: work the lowest-numbered
unfinished feature in Epic 3. F3.6 — use the explicit device-group →
template association instead of substring matching, and give
template-scoped objects their real template name.

**Before writing code: overwrite `acceptance.md` with the F3.6 criteria.**

## F3.6 sub-tasks

- [ ] Overwrite `acceptance.md` with F3.6 criteria.
- [ ] Audit the current template handling: `template_of()` (parser),
      `context=router.get('template')` and the `template` pass sites
      (generator), and the `_TEMPLATE_PLACEHOLDER = 'Shared'` fallback in
      `location_block`.
- [ ] Record the real association the export declares: which template a
      device group attaches (`device-group/entry/*/templates` or the
      template's `devices/entry`), and which device a template targets.
      Replace the substring matching that infers a template from a name.
- [ ] Use the recorded template as the naming digest context for
      template-scoped objects (zones, interfaces, routers, VPN objects,
      monitor profiles), replacing the `''` context those types carry
      today, and regenerate the affected goldens with a reviewed diff.
- [ ] Emit `template { name = <real name> }` instead of the `Shared`
      placeholder wherever the association is known; keep the placeholder
      plus a report entry where the export declares no template.
- [ ] Extend the report: a template-scoped object whose template cannot be
      resolved is listed with the reason (the placeholder is a guess).
- [ ] Tests: association parsing, context-at-emit, placeholder report,
      template-aware reference resolution (a name that exists in two
      templates resolves inside its own template).
- [ ] Fixtures: a two-template export, a device group that attaches two
      templates, a template that nests a vsys.
- [ ] Gates: ruff clean, pytest green, terraform validate green.
- [ ] Commit; update PLAN.md, to-do.md, agent-status.md, backlog.md.

## Deferred (tracked in PLAN.md and backlog.md)

- **Epic 3:** F3.7–F3.10 after F3.6.
- **Epic 4:** F4.1 (post-run sanity gate; its dead-variable check reuses
  the F2.10 test), F4.2 (container table + line tracking; may land during
  Epic 3), F4.3 (per-entry `CONVERSION_REPORT.txt`), F4.4 (property-level
  matrix extending the landed F2.8 matrix; last in Epic 4).

## Notes

- Naming contract (F2.7 + F3.2): sanitized base + 8-hex digest of
  (scope, context, vsys, name); order-independent; per-type domains;
  references resolve through the (context, vsys) chain then the flat
  fallback. F3.6 changes the context for template-scoped types, so those
  digests change and their goldens regenerate.
- `location` is chosen from `LOCATION_SCHEMA`, never from the resource
  name. `terraform validate` accepts an unknown `location` sub-block and
  drops it silently, so a wrong sub-block is an apply-time failure, not a
  validate failure.
- Reference resolution order (F3.5): a name a device declared (an
  interface) resolves inside that device or not at all; every other name
  goes through the (context, vsys) chain, then `Shared`, then contextless,
  then the flat first-declaration index. F3.6 gives template-scoped objects
  a real context, so the flat fallback stops being their primary route.
- Policy rules do not record their rulebase (pre/post/shared), and
  `location.*.rulebase` stays unemitted until the provider's accepted value
  string is verified. Recorded in `backlog.md`.
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
  separate attribute.
- The static no-dangling-reference rule already exists as a test in
  `tests/test_dependency_wiring.py`; F4.1 shares that rule with the
  runtime check instead of copying it.
- The coverage report (F4.3/F4.4) keys on logical entries
  (`<entry name>` plus its properties), not physical lines; the reported
  line number is the entry's opening tag. Decision recorded in
  `backlog.md`.
