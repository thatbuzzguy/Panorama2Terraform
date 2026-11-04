# F7.10 — acceptance criteria

F7.10 states the shape rows for the fields `PROTOCOL_SHAPE` does not declare on the `protocol` row (the two
redistribution profile lists), on `protocol/bgp` (seven fields plus the `routing_options` level), and on
`protocol/ospfv3` (three fields). It makes the parse read them through the table, prints them, and pins the
rows, the parse read, the emitter print, the gate rule, the container rows and the scan scope.

Measure source: `terraform providers schema -json` for the pinned provider (2.0.14), read through the door
`tests/test_data_source_schema.py` uses (`conftest.py::provider_schemas`). The decision is from the
measurement, not from memory. The measured shape is recorded in `resource_mapping.py::PROTOCOL_SHAPE`.

## The measurement, field by field

Measured 2026-11-03 against provider 2.0.14 (Terraform 1.16.2). Every field below is declared by the
provider, so every one becomes a row field. None is refused, and none is marked `sensitive`, so no
`VALUE_VARIABLES` row is needed and the `sensitive` set of every new row is empty.

| Row | Measured provider shape | New row fields |
|---|---|---|
| `protocol` | `single` | `redist_profile` (`list`, entry level), `redist_profile_ipv6` (`list`, entry level) |
| `protocol/bgp` | `single` | `allow_redist_default_route`, `ecmp_multi_as`, `enforce_first_as`, `install_route`, `reject_default_route` (`bool`); `global_bfd` (`single`, 1 attribute), `routing_options` (`single`, 7 attributes); `dampening_profile` (`list`, entry level) |
| `protocol/ospfv3` | `single` | `allow_redist_default_route`, `disable_transit_traffic`, `reject_default_route` (`bool`) |
| `protocol/redist_profile` | `list`, entry level | `action` (`single`), `filter` (`single`), `name` (`string`, required), `priority` (`number`) |
| `protocol/redist_profile_ipv6` | `list`, entry level | same, with `ospfv3` in place of `ospf` inside `filter` |
| `protocol/redist_profile/action` | `single` | `no_redist`, `redist` (`block`: no attribute, so the export states them by presence) |
| `protocol/redist_profile/filter` | `single` | `bgp` (`single`), `destination`, `interface`, `nexthop`, `type` (`['list', 'string']` → `member_list`) |
| `protocol/redist_profile/filter/bgp` | `single` | `community`, `extended_community` (`member_list`) |
| `protocol/redist_profile/filter/ospf` | `single` | `area`, `path_type`, `tag` (`member_list`) |
| `protocol/bgp/dampening_profile` | `list`, entry level | `cutoff`, `decay_half_life_reachable`, `decay_half_life_unreachable`, `max_hold_time`, `reuse` (`number`), `enable` (`bool`), `name` (`string`, required) |
| `protocol/bgp/global_bfd` | `single` | `profile` (`string`) |
| `protocol/bgp/routing_options` | `single` | `aggregate`, `graceful_restart`, `med` (`single`); `as_format`, `confederation_member_as`, `reflector_cluster_id` (`string`); `default_local_preference` (`number`) |
| `protocol/bgp/routing_options/aggregate` | `single` | `aggregate_med` (`bool`) |
| `protocol/bgp/routing_options/graceful_restart` | `single` | `enable` (`bool`), `local_restart_time`, `max_peer_restart_time`, `stale_route_time` (`number`) |
| `protocol/bgp/routing_options/med` | `single` | `always_compare_med`, `deterministic_med_comparison` (`bool`) |

The two `action` alternatives are `block` fields, not a `one_of` choice: the provider declares both as
optional attributes, so the row states no `selects` and the gate reads the level as an object. The same holds
for `filter/bgp` and `filter/ospf`, which state no choice. No new field needs a spelling exception, so
`XML_NAME_EXCEPTIONS` stays as the one entry F7.3 recorded.

A `list` level whose attributes hold a required `name` is an entry level, so the three entry levels
(`redist_profile`, `redist_profile_ipv6`, `dampening_profile`) gain a `CONTAINER_TABLE` row: an entry the
parse reads must be marked, and only an `emitted` row has a matrix row for the property scan. The single-object
levels hold no entry, so they gain no row and stay grounded by the table.

## The print order

Field order is the table order, so the row's order is the print order. The fields a row already stated keep
their order. The fields a row gains are appended in the order the schema names them, and a new row states
`name` first, because the entry name is the first field the block prints. A run that states no value for a new
field prints the same bytes as before, so no golden moves unless a fixture states a new field.

## Criteria

1. **One shape owner.** `PROTOCOL_SHAPE` stays the only table that states the `protocol` object. Three rows
   gain fields, sixteen rows are new, and the emitter, the gate rule and the property scan read the same
   names, so no field name is stated twice.
2. **No parse method names a field.** `parse_bgp` reads the five `bool` fields, `global_bfd` and
   `routing_options` through the row fields, so it states one new path: `protocol/bgp/dampening_profile`.
   `_parse_router` calls a parse method for each field the `protocol` row states, so the two entry levels need
   `parse_redist_profile` and `parse_redist_profile_ipv6`, and both read through `_protocol_entries` with the
   path as the only name. The two methods are registered in `tests/test_entry_coverage.py::_parse_every` and
   `tests/test_multi_vsys_location.py`.
3. **The scan scope.** `CONTAINER_TABLE` gains the three entry-level rows. The properties the row for
   `panos_virtual_router` declares move only for the fields the scan measures through an entry: `action` and
   `priority` are already read, `filter` and the six `dampening_profile` fields join the measured set. A single
   level inside an entry (`action`, `filter`, `filter/bgp`) is not in the scan scope, so its fields stay
   grounded by the table.
4. **The gate accepts the new fields.** A hand-written block that states them is not a finding, and the gate
   still refuses a field the row does not declare. The pin that refused `redist_profile` because the row did
   not state it is restated: the level is now a row, so the refusal moves to a field the row does not state.
5. **The fixtures.** `tests/fixtures/virtual_routers.xml` states the two redist profile entries,
   `tests/fixtures/bgp.xml` states the eight `bgp` fields and the dampening entry, and
   `tests/fixtures/ospfv3.xml` states the three new fields. Each entry states every field its row declares, so
   the property scan reports no unused property for them. A real run on each reports `PASS (0 FAIL, 0 WARN)`
   and `terraform validate` accepts the blocks it writes.
6. **Goldens move only from a real run.** A golden case moves only when the run writes different bytes for it.
7. **The pins.** The rows are pinned against the live schema, the print order against a real run, the parse
   read, the gate findings, the container rows, the scan scope and the new owners in
   `test_the_table_is_the_only_shape_owner`. `ruff check .` and `python3 -m pytest` pass.

## Out of scope for this slice

A row that states fewer fields than the provider declares for its level is a report decision, and the list of
those gaps stays in `backlog.md`: `peer_group`, `peer`, `redist_rules`, `area`, `area/interface`, and the auth
profile choice levels. The gate gap F7.7 recorded (no word for a choice between two levels, `ah` or `esp`) is
not reached here, because no new row states a choice between two levels.
