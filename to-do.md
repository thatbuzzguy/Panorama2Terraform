# To-Do — current task: F3.9 Per-device-group reports (Epic 3)

**F3.8 is complete** (safe XML input: one capped, DTD-refusing read in
`xml_input.py`, used by both entry points). Evidence is in the commit log
and in `acceptance.md`. Direction: work the lowest-numbered unfinished
feature in Epic 3. F3.9 — the two operator-facing migration reports must
say which device group (and which firewall) each line belongs to.

**Before writing code: overwrite `acceptance.md` with the F3.9 criteria.**

## Why this task

`INTERFACE_MIGRATION_REPORT.txt` and `VPN_MIGRATION_REPORT.txt` are the
two reports an operator reads per firewall. Both today list every entry in
one flat list: the interface report groups by interface type, the VPN
report by object kind. In a multi-device-group export the same interface
name appears once per firewall and the reader cannot tell them apart —
the same ambiguity F3.5/F3.6 removed from `location` and from resource
naming.

## F3.9 sub-tasks

- [ ] Audit the two report generators (`generate_interface_report`,
      `generate_vpn_report`) and the fields each entry already carries
      (`device_group`, `template`, `device`, `vsys` — the F3.1/F3.5/F3.6
      parse model).
- [ ] Decide the grouping order and write the criteria: device group
      first, then the scope the export declares (template or device), then
      the existing type/kind grouping inside it.
- [ ] Interface report: one section per device group; name the firewall
      for an entry the export places under a device; keep the migration
      checklist and platform notes as one shared footer, not per section.
- [ ] VPN report: same grouping; keep the pre-shared-key placeholder
      warning at the top of the file and repeat the per-gateway
      `***MUST BE UPDATED***` line where it is today.
- [ ] Shared entries: name the section `Shared` (the PAN-OS shared
      section), and never print a device group for an entry whose scope is
      a template or a device.
- [ ] Tests: a fixture with two device groups and one shared entry per
      report; assert each section lists only its own entries, that a
      same-named interface on two device groups appears twice under
      different sections, and that the pre-shared-key warning survives.
- [ ] Goldens: regenerate if a report is in the golden set (check
      `tests/golden/`); review the diff.
- [ ] Gates: ruff clean, pytest green, terraform validate green.
- [ ] Commit; update PLAN.md, to-do.md, agent-status.md, backlog.md.

## Deferred (tracked in PLAN.md and backlog.md)

- **Epic 3:** F3.10 (`docs/ARCHITECTURE.md`: data model, parse pipeline,
  emit pipeline, naming rules).
- **Epic 4:** F4.1 (post-run sanity gate; its dead-variable check reuses
  the F2.10 test), F4.2 (container table + line tracking; may land during
  Epic 3), F4.3 (per-entry `CONVERSION_REPORT.txt`), F4.4 (property-level
  matrix extending the landed F2.8 matrix; last in Epic 4).

## Notes

- Safe input (F3.8) lives in `xml_input.py`: `parse_xml(path,
  max_input_bytes)` is the only way either script reads an export — a size
  cap checked before the read (default 64 MiB, `--max-input-bytes N`), and
  a DTD refusal made by the parser (an expat prolog scan that stops at the
  root element), not by a text search. A new entry point must import it;
  do not add another `ET.parse(path)`.
- pyexpat calls `StartDoctypeDeclHandler` with `(name, systemId, publicId,
  standalone)` — not the order the Python documentation states. Verified
  against pyexpat; `xml_input.py` therefore never labels the two ids.
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
