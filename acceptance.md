# Acceptance criteria — F3.6 Multi-device, template-aware parsing (Epic 3)

F3.6 replaces name guessing with what the export declares. A Panorama
export states the device relationships in data — a device group lists its
devices, a template lists the devices it targets, a template stack lists
its devices and its templates — and the converter must use those lists
instead of a naming convention or a substring match.

It also fixes the placement of device-specific config. An entry under
`devices/entry/<device>/network/...` is that firewall's own config, not a
template's. Provider v2 has a sub-block for exactly that:
`location.ngfw { ngfw_device }` ("Located in a specific NGFW device",
v2.0.14 schema; the provider rejects it unset with "NgfwDevice is
unspecified"). Today the converter emits the `template { name = "Shared" }`
placeholder for those entries, which names a template that does not exist.

## Schema facts verified for this task (v2.0.14)

- All 14 template-scoped emitted types declare `location.ngfw` with exactly
  one field, `ngfw_device`: `panos_aggregate_interface`,
  `panos_aggregate_layer3_subinterface`, `panos_ethernet_interface`,
  `panos_ethernet_layer3_subinterface`, `panos_ike_crypto_profile`,
  `panos_ike_gateway`, `panos_ipsec_crypto_profile`, `panos_ipsec_tunnel`,
  `panos_loopback_interface`, `panos_monitor_profile`,
  `panos_tunnel_interface`, `panos_virtual_router`,
  `panos_virtual_router_static_route_ipv4`, `panos_vlan_interface`.
  No object type and no policy-rule type declares it.
- `location.template` declares `name`, `ngfw_device`, `panorama_device`
  and (for zones, virtual routers and most interfaces) `vsys`.
  `template.ngfw_device` is the device-specific override inside a template,
  which is what `templates/entry/<T>/devices/entry/<D>/...` means.
- `location.template_stack` and the composite `template_vsys` /
  `template_stack_vsys` sub-blocks exist. The converter never places an
  entry in a stack: a stack holds device and template members, not config.
- `localhost.localdomain` is the PAN-OS placeholder for "this device"
  (F3.5). It is never a usable `ngfw_device`.

## Current state (the gaps F3.6 closes)

- `split_device_groups.py` associates a template with a device group by
  stripping a `DG-` prefix from the device group name and, failing that, by
  a case-insensitive substring test
  (`if device_group_name.lower() in t_name.lower()`). It also matches a
  template stack's `devices/entry` names against the *device group name*.
  Nothing reads the device lists the export provides.
- `location_block` has no `ngfw` branch, so every device-specific network
  object gets the `Shared` template placeholder, silently.
- Two firewalls that both declare `ethernet1/1` produce three resources
  that differ only by the taken-name counter (`ethernet1_1_5dadf948`,
  `..._2`, `..._3`) and carry identical locations, because the digest
  context for a template-scoped object is `''` when it declares no
  template. Verified on 2026-10-08 with a three-device generator run.

## Criteria

1. **Association parsing.** `PanoramaParser.parse_associations()` returns,
   from the export only: device → device groups, device → templates,
   device → template stacks, and template stack → templates. Sources are
   `device-group/entry/*/devices/entry`, `templates/entry/*/devices/entry`,
   `template-stack/entry/*/devices/entry` and
   `template-stack/entry/*/templates/member`; accept `<devices><member>`
   where an export uses the short form. An export with no device lists
   returns empty tables — no invented association.
2. **Effective templates.** `templates_for_device(device)` returns the
   device's direct templates plus the templates of the stacks it attaches
   to, de-duplicated and sorted; `''` or an unknown device returns `[]`.
3. **Device-specific placement.** An entry the export places under
   `devices/entry/<device>/` with no template ancestor, on a type that
   declares `location.ngfw`, emits `ngfw = { ngfw_device = "<device>" }`.
   Never for `localhost.localdomain`.
4. **Template placement keeps its name, and gains the device.** A declared
   template still emits `template = { name = "<template>" }`; when the
   entry sits under `templates/entry/<T>/devices/entry/<D>` and that type's
   `template` declares `ngfw_device`, the block also carries
   `ngfw_device = "<D>"`.
5. **Schema table.** `LOCATION_SCHEMA` gains `ngfw: ('ngfw_device',)` for
   the 14 types above and for no other emitted type. The existing live
   provider-schema test keeps every entry honest.
6. **Multi-device naming.** The digest context of a template-scoped object
   is its declared template, else its declared device, else `''`. Two
   devices that declare the same interface name produce two resources with
   two digests and two different locations, and a device-aware reference
   resolves to its own device's resource.
7. **Placeholder is reported, not silent.** A template-scoped entry with no
   declared template and no usable device keeps
   `template = { name = "Shared" }` and is listed in
   `MANUAL_SETUP_REPORT.txt` naming the templates the export associates
   with its device, or stating that the export associates none.
8. **Splitter uses the association.** A template is copied into a device
   group's split config when the template and the device group name the
   same device. The `DG-` prefix convention and the substring test are
   gone. A device group with no associated template copies no template and
   prints that fact. A template stack is copied when one of its devices is
   one of the device group's devices.
9. **No name guessing left.** No test or fixture relies on a device group
   and a template sharing a name; the association fixture gives them
   unrelated names (`Office-FW` device group, `HQ-Networks` template,
   shared device `fw-1.example.com`) and the splitter test proves the join.
10. **Fixtures and goldens.** A fixture covers two templates, two devices,
    a template stack, and the same interface name on two devices, with
    device group, template and device names that do not resemble each
    other. The kitchen-sink fixture keeps its single-device shape, so its
    diff shows the placement and digest changes only. Both golden sets
    regenerate with a reviewed diff, and every change traces to criteria
    3-7.
11. **Tests.** Association parsing and effective templates (1-2); location
    choice for the new branches (3-4); the schema table (5); two-device
    naming and reference resolution (6); the placeholder report (7); the
    splitter join and the no-template case (8-9).
12. **Gates:** ruff clean, pytest green, terraform validate green on the
    sample output, the kitchen-sink output and the two-device fixture (the
    only output that carries `location.ngfw`).

## Result (2026-10-08)

All twelve criteria hold. `ruff check .` clean, 395 tests pass, and
`terraform validate` passes for the sample, kitchen-sink, crypto-profile
and two-device outputs.

Evidence per criterion is `tests/test_multi_device_template.py` (21 tests)
plus the F3.5 suite, which keeps the scope rules it already pinned:

- 1-2: `test_parser_reads_the_declared_membership`,
  `test_templates_for_device_follows_the_stack`,
  `test_association_is_empty_when_the_export_lists_no_devices`,
  `test_association_names_are_sorted`.
- 3-4: `test_device_specific_config_uses_ngfw`,
  `test_object_types_never_emit_ngfw`,
  `test_placeholder_device_never_becomes_ngfw`,
  `test_template_override_inside_a_template_names_the_device`.
- 5: `test_only_template_scoped_types_declare_ngfw`, and the live
  provider-schema test that compares `LOCATION_SCHEMA` with the v2.0.14
  schema.
- 6: `test_same_interface_name_on_two_devices`,
  `test_reference_resolves_inside_the_template_target_device`,
  `test_ambiguous_template_keeps_a_plain_interface_name`,
  `test_single_device_declaration_still_resolves_without_a_device`.
- 7: `test_zone_with_a_device_and_no_vsys_is_reported`,
  `test_placeholder_report_without_a_device`.
- 8-9: `test_splitter_joins_template_and_device_group_by_device`,
  `test_splitter_copies_the_template_stack_by_device`,
  `test_splitter_copies_no_template_without_a_shared_device`.

Two decisions came out of the work:

- **A deviceless reference to a name two devices declare stays a plain
  string.** A virtual router in a template that targets two firewalls
  cannot say which `ethernet1/1` it means, so the converter emits the name
  and no cross-reference. Guessing the first declaration would build a
  reference to one specific firewall.
- **The splitter copies with `copy.deepcopy`.** ElementTree keeps no parent
  bookkeeping, so `append` makes one element object a child of two trees.
  The shared-section merge then appends into an element that is still in the
  export, so the export gained an entry per device group. Reproduced before
  the fix (two `<shared>` sections, two device groups: the source ended with
  `a1, a2, a2`), fixed, and pinned by
  `test_splitter_merges_shared_sections_without_touching_the_source` and
  `test_splitter_leaves_the_source_tree_intact`.
