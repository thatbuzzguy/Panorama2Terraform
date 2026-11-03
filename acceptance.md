# F7.9 — acceptance criteria

F7.9 states the shape rows for the `protocol/ospf` fields `PROTOCOL_SHAPE` does not declare, makes
`parse_ospf` read them through the table, and pins the rows, the parse read, the emitter print, the gate
rule, the container row and the scan scope.

Measure source: `terraform providers schema -json` for the pinned provider (2.0.14), read through the door
`tests/test_data_source_schema.py` uses (`conftest.py::provider_schemas`). The decision is from the
measurement, not from memory. The measured shape is recorded in `resource_mapping.py::PROTOCOL_SHAPE`.

## The measurement, field by field

Measured 2026-11-03 against provider 2.0.14 (Terraform 1.16.2). Every one of the seven fields the row
does not state is declared by the provider, so every one becomes a row field. None is refused.

| Field | Measured provider shape | Row field |
|---|---|---|
| `timers` | `single`, 2 attributes | `object` |
| `global_bfd` | `single`, 1 attribute | `object` |
| `graceful_restart` | `single`, 5 attributes | `object` |
| `export_rules` | `list`, entry level | `string_list` |
| `rfc1583` | `bool` | `bool` |
| `allow_redist_default_route` | `bool` | `bool` |
| `reject_default_route` | `bool` | `bool` |

The three `bool` fields are values, not blocks: the provider declares each as a leaf of type `bool`, so the
row states `bool` and the field reader reads `yes` or `no` the way it already reads `enable`. No `ospf`
field is `sensitive` in the schema, so the row states an empty `sensitive` set and no `VALUE_VARIABLES` row
is needed. `strict_l_s_a_checking` is the one spelling the `-` rule cannot produce, and
`XML_NAME_EXCEPTIONS` already states it.

## The print order

Field order is the table order, so the row's order is the print order. The `ospf` row states:
`enable`, `router_id`, the three `bool` fields in the order the schema names them, the three single-object
levels in the order the `ospfv3` row states them, then the two entry levels in the same order. The fields
the row already stated keep their relative order, so a run that states no value for a new field prints the
same bytes as before.

## Criteria

1. **One shape owner.** `PROTOCOL_SHAPE` stays the only table that states the `protocol` object. The row
   gains the seven measured fields, and four new rows stand under it for the levels. The emitter, the gate
   rule and the property scan read the same names, so no field name is stated twice.
2. **No parse method names a field.** `parse_ospf` reads the three `object` levels through
   `_protocol_level`, so it states no path for them. `export_rules` is a `string_list` level, so the method
   states its path and `_protocol_branch` fills it. The parse stays registered in
   `tests/test_entry_coverage.py::_parse_every` and `tests/test_multi_vsys_location.py`, which already call
   it for each router.
3. **The scan scope.** `CONTAINER_TABLE` gains the sub-shape row for `protocol/ospf/export-rules`, because
   an export rule is an entry and only an `emitted` row has a matrix row. The three single-object levels
   hold no entry, so they gain no row and stay grounded by the table. The properties the row for
   `panos_virtual_router` declares are measured through a fixture, so they move only if the run reads a new
   name.
4. **The gate accepts the new fields.** A hand-written block that states them is not a finding, and the gate
   still refuses a field the row does not declare. The pin that refused these fields because the row did not
   state them is restated.
5. **The fixture.** `tests/fixtures/ospf.xml` states the three `bool` fields and each of the four new
   levels, with one entry stating every field its row declares, so the property scan has no unused
   property for it. A real run on it reports `PASS (0 FAIL, 0 WARN)` and `terraform validate` accepts the
   block.
6. **Goldens move only from a real run.** A golden case moves only when the run writes different bytes for
   it.
7. **The pins.** The rows are pinned against the live schema, the print order against a real run, the parse
   read, the gate findings, the container row and the scan scope. `ruff check .` and `python3 -m pytest`
   pass.

## Out of scope for this slice

Fields the provider declares for a routing level that the row does not state stay in `backlog.md`: the two
redistribution profile lists, the `bgp` fields outside the levels the table states, and the `ospfv3` bool
fields. A field the provider does not declare cannot become a row.
