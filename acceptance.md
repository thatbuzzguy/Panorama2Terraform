# Acceptance criteria — F3.3 Full interface types (Epic 3)

F3.3 emits every interface kind the parser finds, not only physical
ethernet. Subinterface units and virtual-wire units become individual
entries.

## Criteria

1. **Parser — ethernet subinterface units.** `ethernet/entry/units/entry`
   is parsed as individual interface entries. Each entry records `parent`
   (the physical entry name) and `tag` (the unit number). The F1.6
   extraction gap in `backlog.md` closes.
2. **Parser — virtual-wire units.**
   `network/interface/virtual-wire/units/entry` is parsed as individual
   entries with mode `virtual-wire`.
3. **Entry shape.** Every interface entry carries: kind, mode, `parent`
   (when it is a subunit), device group, and vsys.
4. **Emitted types, verified against the live v2.0.14 schema** (no type
   from memory):
   - `panos_ethernet_interface`
   - `panos_ethernet_layer3_subinterface`
   - `panos_vlan_interface`
   - `panos_loopback_interface`
   - `panos_tunnel_interface`
   - `panos_aggregate_interface`
   - `panos_aggregate_layer3_subinterface`

   The schema has no `panos_virtual_wire_interface`: virtual-wire and tap
   are nested blocks on `panos_ethernet_interface`.
5. **Mode blocks.** `virtual_wire` and `tap` emit as nested blocks on the
   ethernet interface, replacing the "requires manual review" note. The
   `layer3` and `layer2` blocks keep the F2.4 shape.
6. **Address shapes.** `ip` emits as a nested list of objects with
   `name`; `ipv6` emits as a nested single block with `address` (the
   schema shapes for the non-ethernet kinds).
7. **Naming and references.** The F2.7/F3.2 contract holds: sanitized
   base plus the 8-hex digest of (scope, context, vsys, name); `parent`
   resolves through `name_ref` in the referrer's (context, vsys) pair.
   The `name` attribute keeps the documented convention: the PAN-OS
   display name (`vlan.10`, `ethernet1/1.0`), with `parent` as a separate
   attribute.
8. **Fixture and tests.** A fixture covers each kind plus a parsed
   ethernet subinterface unit and a virtual-wire unit. Tests assert: each
   kind emits the right resource type; the subinterface `parent` points
   at the physical interface resource; the virtual-wire and tap blocks
   emit; `COVERAGE_MATRIX` gains a row for each new emitted type.
9. **Goldens** regenerated for both sets with a reviewed diff.
10. **Gates:** ruff clean, pytest green, terraform validate green.
