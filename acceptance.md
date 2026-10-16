# Acceptance criteria — F3.9 Per-device-group reports (Epic 3)

F3.9 makes the two operator-facing migration reports say which device group
(and which firewall) each line belongs to.

## Audit of the two reports (2026-10-16)

- `generate_interface_report` writes one flat list grouped by interface type;
  `generate_vpn_report` writes one flat list grouped by object kind. Neither
  names the scope an entry came from.
- In a multi-device-group export the same interface name appears once per
  device group, so the reader cannot tell the entries apart. This is the same
  ambiguity F3.5/F3.6 removed from `location` and from resource naming.
- Every parsed entry already carries the four scope facts F3.1/F3.5/F3.6
  record: `device_group`, `template`, `vsys`, `vsys_device`. Both report
  generators can group from the parse model without reading the XML again.
- `device_group` is not always a declared device group. `device_group_of`
  returns `Shared` as a fallback for an entry it cannot place, which covers
  both the real shared section and an entry inside a template or under a
  device. Printing that fallback as a device group would name a scope the
  export does not state.
- Reports are not in the golden set (`tests/golden/` holds `.tf` files only),
  so F3.9 changes no golden.

## Grouping rule (decided for this task)

1. Device group first — only when the export declares one.
2. Then the scope the export declares: template, then device.
3. Then the existing type/kind grouping inside the section.
4. An entry the export places nowhere is the shared section, named `Shared`.
5. A section never prints a device group for an entry whose scope is a
   template or a device.
6. One shared footer per report: the checklist and the platform notes
   (interface report), the key management practices, checklist and security
   notes (VPN report). The pre-shared-key warning stays at the top of the VPN
   report, before the first section.

## Criteria

1. **One grouping rule, shared by both reports.** A helper pair on
   `TerraformGenerator` (`_report_scope_path`, `_group_by_scope`,
   `_report_section_header`) that both generators call. Neither report keeps
   its own copy of the rule.
2. **Declared scope only.** A device group is printed when the export declares
   one; a template or device scope is never printed as a device group; an
   unplaced entry is the shared section.
3. **Interface report:** one section per scope, the firewall named for an entry
   the export places under a device, per-type grouping inside each section,
   and the migration checklist plus platform notes as one shared footer.
4. **VPN report:** same grouping; the pre-shared-key warning stays at the top
   of the file; the per-gateway `***MUST BE UPDATED***` line stays with each
   pre-shared-key gateway; key management best practices, the checklist and the
   security notes are one shared footer.
5. **Same name, two sections.** A same-named interface (and a same-named
   gateway) in two device groups appears twice, once under each section.
6. **Counts are per section**, not global.
7. **vsys is printed when the export declares one**, and never invented.
8. **Deterministic.** Sections sorted by scope path, entries sorted by name;
   two runs on the same input produce identical bytes.
9. **No report when there is nothing to report** (unchanged behaviour).
10. **Tests:** a fixture with two device groups, one shared entry per report,
    one template-scoped entry and one device-scoped entry; assert each section
    lists only its own entries, that a same-named interface appears twice under
    different sections, that no device group is printed for a template or
    device scope, that the shared section is named `Shared`, that the
    pre-shared-key warning survives at the top, and that the footers appear
    once.
11. **Docs:** README and `docs/MIGRATION_GUIDE.md` state the grouping.
12. **Gates:** ruff clean, pytest green, terraform validate green. Goldens
    unchanged.

## Result (2026-10-16)

All twelve criteria hold. `ruff check .` clean, 438 tests pass (18 of them new
in `tests/test_reports.py`), `terraform validate` still green, and both golden
sets are byte-identical (reports are not in the golden set).

Evidence per criterion:

- 1: `_report_scope_path`, `_group_by_scope` and `_report_section_header` in
  `TerraformGenerator`; both report generators call them.
  `test_both_reports_use_the_same_grouping_rule` pins that the section titles
  of each report are the headers the shared helper produces for the parsed
  entries.
- 2: `test_template_and_device_scopes_are_not_printed_as_a_device_group`,
  `test_placeholder_device_is_not_named_as_a_firewall`.
- 3: `test_interface_report_has_one_section_per_scope`,
  `test_each_interface_section_lists_only_its_own_entries`,
  `test_interface_footer_is_one_shared_block`.
- 4: `test_vpn_report_has_one_section_per_scope`,
  `test_pre_shared_key_warning_survives_at_the_top`,
  `test_per_gateway_placeholder_line_survives`,
  `test_vpn_footer_is_one_shared_block`.
- 5: `test_same_named_interface_appears_under_each_device_group`,
  `test_same_named_gateway_appears_under_each_device_group`.
- 6: `test_interface_counts_are_per_section`.
- 7: `test_vsys_is_printed_only_when_the_export_declares_one`.
- 8: `test_sections_and_entries_are_in_a_stable_order`.
- 9: `test_no_report_when_there_is_nothing_to_report`.
- 10: `tests/fixtures/report_grouping.xml` plus the 18 tests.
- 11: README "Reports written to the output directory",
  `docs/MIGRATION_GUIDE.md` §4, `docs/USAGE_GUIDE.md` output tree.

Two decisions came out of the work:

- **The shared `Shared` fallback is not a device group.** `device_group_of`
  returns `Shared` for an entry it cannot place, which covers both the real
  shared section and an entry inside a template or under a device. The report
  prints a device group only when the export declares one, so a template or
  device scope is named by its own scope.
- **Sections sort by level, not by label text.** The scope path carries the
  level number, so device group sections come before template sections and
  template sections before device sections, whatever the names are.
