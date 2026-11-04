# Acceptance — F4.4: the `nested-block` field rule for `parent`

## Measurement

Measured 2026-11-04 against the pinned provider `PaloAltoNetworks/panos ~> 2.0.14`, read through
`tests/conftest.py::provider_schemas` (`terraform providers schema -json`):

- 128 resources and 128 data sources. Three resource types declare a `parent` attribute:
  `panos_ethernet_layer3_subinterface`, `panos_aggregate_layer3_subinterface`, `panos_device_group_parent`.
  `panos_ethernet_interface` declares none, so a block of that type cannot print a parent, and
  `terraform validate` refuses one.
- On `tests/fixtures/interfaces_ethernet.xml`, entry `ethernet1/4.1` sits in
  `network/interface/virtual-wire/units`, the `nested-block` row. The run writes one block for it:
  `resource "panos_ethernet_interface"`, `name = "ethernet1/4.1"`, `virtual_wire = {}`.
- The parse marks that entry with `parent` built from `name.split('.')[0]`. The read record for the entry
  names `comment, device_group, ip_addresses, ipv6_addresses, management_profile, mode, name, tag, template,
  template_stack, type, vsys, vsys_device` and names no `parent`, so the entry line names a field no output
  reads. The entry is outside the property scan scope, because `matrix_row_for` answers None for the row, so
  no finding can name it: the entry line is the only output that can be honest about it.
- Of the three fields the line names, the print reads two: `mode` picks the block key (`virtual_wire = {}`),
  and `type` picks the resource type through `INTERFACE_RESOURCE_TYPES`. `parent` is read only by
  `TerraformGenerator._emit_interface_resource`, and only for a kind whose matrix row declares it. The row that
  covers this entry declares no `parent`, and the provider declares none for its type.

## The rule this slice states

The scan scope rule in `docs/COVERAGE_MATRIX.md` §1 says the output that reaches an entry outside the scan scope
must read the field it names. For a `nested-block` entry the output is the block the emitter prints, and the
block can print only the attributes its type declares. So the `nested-block` shape is: the entry line names only
the fields the print reads through the captured object.

`parent` is not such a field for a `nested-block` entry. It is a fact of the parent entry, not a property of the
child, and the parent part of a unit name is stated by the child's own name (`ethernet1/4.1` is unit `1` of
`ethernet1/4`), which the `name` line prints as the row identity. So `parse_interfaces` records no `parent`
value for a `nested-block` entry, and the entry line names the fields the print reads. `parent` stays a captured
property for the kinds whose matrix row declares it, where the emitter reads it through the child object and
prints `parent = <parent>.name`.

The option not taken — the print reading `parent` through the child's captured object for a `nested-block`
entry — is refused by the measurement: the type the block prints declares no `parent` attribute, so such a read
would record nothing on the output and the line would still name a field the print does not use.

## Acceptance criteria

1. The measurement above is recorded in the owner document, and no emitter is built for a `nested-block` entry.
2. `docs/COVERAGE_MATRIX.md` §1 states the `nested-block` shape as the third shape of the scan-scope rule, one
   owner document. `docs/ARCHITECTURE.md` §2.4 keeps only the destination fact and the link to §1.
3. `parse_interfaces` records no `parent` value for an entry in `network/interface/virtual-wire/units`, so
   `entry_coverage.captured_fields` names only what the print reads. The print reads the parent part through the
   name, which is the row identity, and no module reads `parent` for a `nested-block` entry.
4. `tests/fixtures/interfaces_ethernet.xml` gains a `comment` on `ethernet1/4.1`, so the entry carries a field
   the print reads and prints, and the pin measures the rule on a real run.
5. `tests/test_property_coverage.py` group 6 gains gap 7,
   `test_the_nested_block_line_names_only_the_fields_the_emitter_reads`, in the shape of the group 6 pins: the
   entry, the fields the parse kept, the entry line that names them, the reads through the captured object, the
   printed lines, and the row that answers `matrix_row_for` as None.
6. `tests/test_property_coverage.py::test_scan_scope_is_the_entries_a_matrix_row_covers` stays honest with the
   decision: the scan scope rule is unchanged, and the pin no longer claims the nested child carries `parent`,
   because the parse no longer keeps it there.
7. `tests/test_parse_network.py::test_parse_virtual_wire_units` migrates to the rule: the parse carries no
   `parent` value for the `nested-block` entry, and the name states the parent part. The subinterface pin for a
   kind whose row declares `parent` is unchanged.
8. The entry-mark rule stays green, the report line shape, the console line shape, and the exit codes are
   unchanged, and the `nested-block` destination kind is unchanged.
9. The interfaces fixture run reports `PASS (0 FAIL, 0 WARN)`, and the entry line for `ethernet1/4.1` reads
   `captured: comment, mode, type`.
10. `ruff check .` is clean and `python3 -m pytest` passes. No golden is regenerated: the golden set pins `.tf`
    paths and bytes only, and no golden holds the interfaces fixture.
11. Tracking markdown after the commit: `backlog.md` loses the closed `nested-block` line and keeps the
    `bookkeeping` line, `to-do.md` closes this feature and names the next one (the `bookkeeping`
    `devices`/`templates` fields rule, the same shape in another kind), `agent-status.md` records the position
    and the pins changed, `PLAN.md` names the rule that now exists for `nested-block`. ASD-STE100, no test
    counts outside `agent-status.md`.
