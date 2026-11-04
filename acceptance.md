# F7.11 — acceptance criteria

F7.11 closes the six `PROTOCOL_SHAPE` rows that state fewer fields than provider 2.0.14 declares:
`protocol/bgp/peer_group` (2), `protocol/bgp/peer_group/peer` (9), `protocol/bgp/redist_rules` (7),
`protocol/ospf/area/interface` (8), `protocol/ospfv3/area` (1), and `protocol/ospfv3/area/interface` (9).
It decides each missing field, extends the rows, makes the parse read them through the table, prints them,
and pins the rows, the parse read, the emitter print, the gate rule, and the scan scope.

Measure source: `terraform providers schema -json` for the pinned provider (2.0.14), read through the door
`tests/test_data_source_schema.py` uses (`conftest.py::provider_schemas`). The decision is from the
measurement, not from memory. The measured shape is recorded in `resource_mapping.py::PROTOCOL_SHAPE`.

## The decision

Every one of the 36 fields is read and printed. None is a report gap, for three reasons the measurement
supports:

1. None is marked `sensitive`, so no field needs the variable reference and no `VALUE_VARIABLES` row.
2. None of the new fields is refused by `terraform validate`: a `single` level that holds its attributes
   as optional fields is an `object` row, the same decision F7.10 made for `redist_profile/action`.
   Measured on the pinned provider (Terraform 1.16.2, 2026-11-03): a peer that states 2 attributes inside
   `connection_options` validates, and a peer that states both `multicast` and `unicast` inside
   `subsequent_address_family_identifier` validates, so neither level is a choice between two levels and
   F7.12 is not reached. One level inside the peer entry is a choice the provider enforces at validate
   time: `peer_address` refuses 2 attributes when one is required (`ip` or `fqdn`), so the fixture states
   one attribute for it, and the gate cannot refuse a hand-written block that states both. That gap is the
   F7.12 word and is recorded in `backlog.md`.
3. The parse and the emitter are table-driven (`_protocol_level` and `_protocol_fields` read the row), so a
   field the row states is read and printed with no new rule.

The rows that state a `single` level inside an entry need a row for that level, because `_protocol_level`
walks a field the row states as `object`: `peer/bfd`, `peer/connection_options`,
`peer/connection_options/incoming_bgp_connection`, `peer/connection_options/outgoing_bgp_connection`,
`peer/subsequent_address_family_identifier`, `ospf/area/interface/bfd`, and `ospfv3/area/interface/bfd`.
None of these holds an entry, so none gains a `CONTAINER_TABLE` row: they are grounded by the table, the same
rule F7.10 recorded for the levels inside a redist profile entry.

## The measurement, field by field

Measured 2026-11-03 against provider 2.0.14 (Terraform 1.16.2). Every field below is declared by the
provider, so every one becomes a row field. The `sensitive` set of every row stays empty.

| Row | New row fields |
|---|---|
| `protocol/bgp/peer_group` | `aggregated_confed_as_path`, `soft_reset_with_stored_info` (`bool`) |
| `protocol/bgp/peer_group/peer` | `address_family_identifier`, `max_prefixes`, `peering_type`, `reflector_client` (`string`); `enable_mp_bgp`, `enable_sender_side_loop_detection` (`bool`); `bfd`, `connection_options`, `subsequent_address_family_identifier` (`single` → `object`) |
| `protocol/bgp/peer_group/peer/bfd` | `profile` (`string`) |
| `protocol/bgp/peer_group/peer/connection_options` | `authentication`, `hold_time`, `keep_alive_interval` (`string`); `idle_hold_time`, `min_route_adv_interval`, `multihop`, `open_delay_time` (`number`); `incoming_bgp_connection`, `outgoing_bgp_connection` (`single` → `object`) |
| `protocol/bgp/peer_group/peer/connection_options/incoming_bgp_connection` | `allow` (`bool`), `remote_port` (`number`) |
| `protocol/bgp/peer_group/peer/connection_options/outgoing_bgp_connection` | `allow` (`bool`), `local_port` (`number`) |
| `protocol/bgp/peer_group/peer/subsequent_address_family_identifier` | `multicast`, `unicast` (`bool`) |
| `protocol/bgp/redist_rules` | `route_table`, `set_origin` (`string`); `set_as_path_limit`, `set_local_preference`, `set_med` (`number`); `set_community`, `set_extended_community` (`['list', 'string']` → `member_list`) |
| `protocol/ospf/area/interface` | `authentication` (`string`); `dead_counts`, `gr_delay`, `hello_interval`, `priority`, `retransmit_interval`, `transit_delay` (`number`); `bfd` (`single` → `object`) |
| `protocol/ospf/area/interface/bfd` | `profile` (`string`) |
| `protocol/ospfv3/area` | `authentication` (`string`) |
| `protocol/ospfv3/area/interface` | the 8 fields the `ospf` row gains, plus `instance_id` (`number`), which the provider declares for this level only |

No new field needs a spelling exception: each one is the field name with `_` as `-`
(`set_community` → `set-community`, `subsequent_address_family_identifier` →
`subsequent-address-family-identifier`), so `XML_NAME_EXCEPTIONS` stays as the one entry F7.3 recorded.

## The print order

Field order is the table order, so the row's order is the print order. The fields a row already stated keep
their order; the fields a row gains are appended in the order the schema names them. A `single` level inside an
entry prints as one object, a `member_list` prints the members as values, and a field with no value prints
nothing.

## The scan scope

`CONTAINER_TABLE` needs no new row: the six levels already have one. The property scan measures the entries at
`peer_group`, `peer`, `redist_rules`, and `ospfv3/area`, so the properties the row for `panos_virtual_router`
declares gain only what a fixture entry states at those levels. An interface entry sits inside an area entry, so
its section path holds an `entry` segment no row path can match: the `ospf` and `ospfv3` interface fields stay
grounded by the table, and no property is added for them.

## Criteria

1. **One shape owner.** The six rows state every field the provider declares for their level, so no row that
   holds an entry is a subset of the measurement. The seven new levels are rows. No parse method, emitter, or
   gate branch names a field, and `test_the_table_is_the_only_shape_owner` still passes.
2. **No parse method names a field.** `parse_bgp` and `_protocol_areas` read the new fields through the row
   fields, so they state no new path. The new owners stay registered in
   `tests/test_entry_coverage.py::_parse_every` and `tests/test_multi_vsys_location.py`.
3. **The fixtures.** `tests/fixtures/bgp.xml`, `tests/fixtures/ospf.xml`, and `tests/fixtures/ospfv3.xml` state
   every field the rows declare for the entries the pins run on, and `tests/fixtures/kitchen_sink.xml` states
   them for its peer group, peer, and redist rule. Each entry states every field its row declares, so the run
   reports no unused property for it, and `peer_address` states one attribute because the provider requires one
   of `ip` or `fqdn`. A real run on each fixture reports `PASS (0 FAIL, 0 WARN)` and `terraform validate`
   accepts the blocks it writes.
4. **The gate accepts the new fields.** A hand-written block that states them is not a finding, and the gate
   still refuses a field the row does not state. The block a real run writes reports no finding. The gate cannot
   refuse a `peer_address` that states both `ip` and `fqdn`, so the fixture states one attribute and the gap is
   recorded in `backlog.md`.
5. **Goldens move only from a real run.** A golden case moves only when the run writes different bytes for it.
6. **The pins.** The rows are pinned against the live schema, the print order against a real run, the parse
   read, the gate findings, the scan scope, and the properties the matrix row declares.
   `ruff check .` and `python3 -m pytest` pass.

## Out of scope for this slice

F7.12 (the gate has no word for a choice between two levels, `ah` or `esp`) is not reached here: no row F7.11
adds states a choice between two levels. The `peer_address` choice the provider enforces at validate time is the
same gap, and both are recorded in `backlog.md`. The rows that are still a subset of the measurement are the
choice levels, which state their alternatives as `selects` keys.
