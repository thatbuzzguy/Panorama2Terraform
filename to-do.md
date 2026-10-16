# To-Do — current task: F3.10 Architecture document (Epic 3)

**F3.9 is complete** (per-device-group reports: one section per declared scope
in both migration reports, through one shared grouping rule). Evidence is in
the commit log and in `acceptance.md`. Direction: work the lowest-numbered
unfinished feature in Epic 3. F3.10 is the last one.

**Before writing code: overwrite `acceptance.md` with the F3.10 criteria.**

## Why this task

The naming rules, the location rules and the report grouping rule are each
written down in a different place (a docstring, a doc, an acceptance record),
and they are the three things a reader must hold together to understand why
the output looks the way it does. Epic 3 is the architecture epic; its
deliverable is one document that states the whole pipeline in one place.

## F3.10 sub-tasks

- [ ] Overwrite `acceptance.md` with the criteria for the document: what
      sections it must contain, and what each claim must be checked against.
- [ ] Data model: the keyed identity (device group, vsys, type, name), the
      four scope facts `identity_of` records, and `report_only` entries.
- [ ] Parse pipeline: safe input (`xml_input.py`), the parent map, the
      association tables, and the containers each parse method reads.
- [ ] Emit pipeline: `location` chosen from `LOCATION_SCHEMA`, the
      reference-resolution order, the deterministic naming rule, and the
      report-only path.
- [ ] Naming rules: sanitized base + 8-hex digest of (scope, context, vsys,
      name), per-type domains, and why the order does not matter.
- [ ] Cross-check every claim against the code and the tests: no statement
      that a test does not pin, no claim that contradicts `backlog.md`.
- [ ] Link the document from README and from the docs it replaces or
      duplicates; remove duplicated prose rather than repeating it.
- [ ] Gates: ruff clean, pytest green, terraform validate green (no code
      change expected).
- [ ] Commit; update PLAN.md, to-do.md, agent-status.md, backlog.md.

## Deferred (tracked in PLAN.md and backlog.md)

- **Epic 4:** F4.1 (post-run sanity gate; its dead-variable check reuses the
  F2.10 test), F4.2 (container table + line tracking; may land during Epic 3),
  F4.3 (per-entry `CONVERSION_REPORT.txt`), F4.4 (property-level matrix
  extending the landed F2.8 matrix; last in Epic 4).

## Notes

- Safe input (F3.8) lives in `xml_input.py`: `parse_xml(path,
  max_input_bytes)` is the only way either script reads an export — a size cap
  checked before the read (default 64 MiB, `--max-input-bytes N`), and a DTD
  refusal made by the parser (an expat prolog scan that stops at the root
  element), not by a text search. A new entry point must import it; do not add
  another `ET.parse(path)`.
- Naming contract (F2.7, F3.2, F3.6): sanitized base + 8-hex digest of
  (scope, context, vsys, name), where context is the device group, the
  template, or the owning device. Order-independent; per-type domains;
  references resolve through the (context, vsys) chain then the flat fallback.
- `location` is chosen from `LOCATION_SCHEMA`, never from the resource name.
  `terraform validate` accepts an unknown `location` sub-block and drops it
  silently, so a wrong sub-block is an apply-time failure, not a validate
  failure.
- Reference resolution order (F3.6): a name a device declared resolves inside
  that device, and for a deviceless referrer only when exactly one device
  declares it; every other name goes through the (context, vsys) chain, then
  `Shared`, then contextless, then the flat first-declaration index.
- Report grouping rule (F3.9): device group first, then the template or the
  device the export places the entry in, then the object kind. A device group
  prints only when the export declares one — `device_group_of` returns `Shared`
  as a fallback for an entry it cannot place, so that value names the shared
  section, not a device group. `localhost.localdomain` is the PAN-OS "this
  device" placeholder and names no firewall.
- Policy rules do not record their rulebase (pre/post/shared), and
  `location.*.rulebase` stays unemitted until the provider's accepted value
  string is verified. Recorded in `backlog.md`.
- Object types with no v2 attribute are report-only since F3.4 (`report_only`
  on the parsed entry, section in `MANUAL_SETUP_REPORT.txt`). Any new "cannot
  emit" case follows that pattern.
- ElementTree `append` does not reparent: it makes one element object a child
  of two trees. Copy with `copy.deepcopy` when taking an element out of a tree
  another tree still uses (the splitter does).
- The static no-dangling-reference rule already exists as a test in
  `tests/test_dependency_wiring.py`; F4.1 shares that rule with the runtime
  check instead of copying it.
- The coverage report (F4.3/F4.4) keys on logical entries (`<entry name>` plus
  its properties), not physical lines; the reported line number is the entry's
  opening tag. Decision recorded in `backlog.md`.
