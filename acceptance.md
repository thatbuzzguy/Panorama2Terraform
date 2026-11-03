# F7.8 — acceptance criteria

F7.8 decides, for the six filter containers in Epic 7, whether `CONTAINER_TABLE` names a provider
type or a `report` row, then implements the read, the print, the gate rule and the pins.

Measure source: `terraform providers schema -json` for the pinned provider (2.0.14), read through
the door `tests/test_data_source_schema.py` uses (`conftest.py::provider_schemas`). The decision is
from the measurement, not from memory. The measured shape is recorded in
`resource_mapping.py::FILTER_SHAPE`.

## The decision, container by container

The pinned provider declares a resource for all six containers, so all six are `emitted` and the
container row's note names the provider type. No container is a `report` row.

| Container | Measured provider resource | Row |
|---|---|---|
| `network/routing-profile/filters/access-list` | `panos_filters_access_list_routing_profile` | `emitted` |
| `network/routing-profile/filters/as-path-access-list` | `panos_filters_as_path_access_list_routing_profile` | `emitted` |
| `network/routing-profile/filters/prefix-list` | `panos_filters_prefix_list_routing_profile` | `emitted` |
| `network/routing-profile/filters/community-list` | `panos_filters_community_list_routing_profile` | `emitted` |
| `network/routing-profile/filters/route-maps/bgp/bgp-entry` | `panos_filters_bgp_route_map_routing_profile` | `emitted` |
| `network/routing-profile/filters/route-maps/redistribution/redist-entry` | `panos_filters_route_maps_redistribution_routing_profile` | `emitted` |

## Criteria

1. **One shape owner.** A filter container sits outside the `protocol` object, so its shape is in
   `FILTER_SHAPE`, not `PROTOCOL_SHAPE`. Each row states `shape`, `fields`, `selects`, `sensitive`,
   the same row shape an existing config container uses, so the existing pins read both tables the
   same way. A row whose shape word is `object` or `string_list` is the provider word measured from
   the schema; `selects` is empty because the provider declares every choice as optional fields, not
   as one-of; `sensitive` is empty because no filter field is `sensitive` in the schema.
2. **The row scope is a subset choice, stated here.** For the four simple containers and the BGP
   route-map entry, `FILTER_SHAPE` mirrors every level the provider declares. For the redistribution
   route-map entry, the table states the entry level, the protocol levels, the protocol/pair levels,
   the route-map entry level, and the `match` and `set` levels; the levels inside them
   (`match.ipv4.address`, `match.next_hop`, `match.route_source`, `set.metric`, `set.ipv4`, `set.ipv6`)
   are not in the table and are recorded in `backlog.md`.
3. **No parse method names a field.** `parse_filter_containers` states the six container paths and
   reads each level through `FILTER_SHAPE`. The entry-name rule and the field-shape rule of F7.1 apply
   to a filter block the way they apply to `protocol`.
4. **The input spelling is measured from pango.** `XML_NAME_EXCEPTIONS` gains the fields whose element
   or attribute name differs from `to_xml_name`, and the pin `test_the_table_is_the_only_shape_owner`
   reads every word of every `FILTER_SHAPE` row against the schema and pango. A field that spells two
   ways in the input is pinned by its path (`ec-regex` for `extended_communities` in a community-list
   entry, `extended-community` in a route-map match).
5. **Every entry the method reads is marked**, and the property scan measures a filter entry against
   its container row: the properties `COVERAGE_MATRIX` declares are the entry-level fields `FILTER_SHAPE`
   states, minus the entry name.
6. **The emitter prints what the row declares.** `generate_filter_containers` reads every property the
   matrix row declares, and the gate rule `filter_blocks` refuses a filter block whose field reads as a
   shape the row does not state, an entry inside a list element with no `name`, or a field the row does
   not declare.
7. **The fixture.** `tests/fixtures/filter_containers.xml` has one entry per container, each stating
   every field its entry row declares, inside a template so a location block prints. The gate reports
   `PASS (0 FAIL, 0 WARN)` on it, and `terraform validate` accepts the emitted block.
8. **Goldens move together.** The corpus case `tests/fixtures/kitchen_sink.xml` gains one filter entry,
   so a row change moves the property scan scope, the per-entry report and the `.tf` goldens together.
   Goldens are regenerated only from a real run.
9. **The pins.** Rows are pinned against the live schema; the parse read, the emitter print, the gate
   rule, the scan scope and the input spellings are pinned; `ruff check .` and `python3 -m pytest` pass.
