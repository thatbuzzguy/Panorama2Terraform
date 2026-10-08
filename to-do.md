# To-Do — current task: F3.8 Safe XML input (Epic 3)

**F3.6 and F3.7 are complete** (multi-device, template-aware parsing; the
splitter rewrite landed inside it). Evidence is in the commit log and in
`acceptance.md`. Direction: work the lowest-numbered unfinished feature in
Epic 3. F3.8 — the converter must refuse input it cannot parse safely.

**Before writing code: overwrite `acceptance.md` with the F3.8 criteria.**

## F3.8 sub-tasks

- [ ] Audit what both entry points accept today: `panorama_to_terraform.py`
      and `split_device_groups.py` read the whole file into memory as text,
      reject a `<!DOCTYPE`, then hand the path to ElementTree.
- [ ] Decide the two remaining risks and write the criteria for them:
      input size (a huge file exhausts memory before the parse starts) and
      entity/billion-laughs expansion (DTD rejection covers the declared
      case; confirm nothing else expands).
- [ ] Pick one mechanism and use it in both scripts: a size limit, or
      `defusedxml` (a new dependency — check it is acceptable, and note that
      `xml.etree` and `defusedxml` must not be mixed in one code path).
- [ ] Report the refusal clearly: name the file, the limit, and the measured
      value; exit non-zero; write no output files.
- [ ] Tests: over-limit input refused, at-limit input accepted, the refusal
      message, no partial output written, and both scripts behave the same.
- [ ] Gates: ruff clean, pytest green, terraform validate green.
- [ ] Commit; update PLAN.md, to-do.md, agent-status.md, backlog.md.

## Deferred (tracked in PLAN.md and backlog.md)

- **Epic 3:** F3.9 (per-device-group reports), F3.10
  (`docs/ARCHITECTURE.md`).
- **Epic 4:** F4.1 (post-run sanity gate; its dead-variable check reuses
  the F2.10 test), F4.2 (container table + line tracking; may land during
  Epic 3), F4.3 (per-entry `CONVERSION_REPORT.txt`), F4.4 (property-level
  matrix extending the landed F2.8 matrix; last in Epic 4).

## Notes

- Naming contract (F2.7, F3.2, F3.6): sanitized base + 8-hex digest of
  (scope, context, vsys, name), where context is the device group, the
  template, or the owning device. Order-independent; per-type domains;
  references resolve through the (context, vsys) chain then the flat
  fallback.
- `location` is chosen from `LOCATION_SCHEMA`, never from the resource
  name. `terraform validate` accepts an unknown `location` sub-block and
  drops it silently, so a wrong sub-block is an apply-time failure, not a
  validate failure.
- Reference resolution order (F3.6): a name a device declared resolves
  inside that device, and for a deviceless referrer only when exactly one
  device declares it; every other name goes through the (context, vsys)
  chain, then `Shared`, then contextless, then the flat first-declaration
  index.
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
- ElementTree `append` does not reparent: it makes one element object a
  child of two trees. Copy with `copy.deepcopy` when taking an element out
  of a tree another tree still uses (the splitter does).
- The static no-dangling-reference rule already exists as a test in
  `tests/test_dependency_wiring.py`; F4.1 shares that rule with the
  runtime check instead of copying it.
- The coverage report (F4.3/F4.4) keys on logical entries
  (`<entry name>` plus its properties), not physical lines; the reported
  line number is the entry's opening tag. Decision recorded in
  `backlog.md`.
