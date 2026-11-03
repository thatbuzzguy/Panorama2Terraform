# Acceptance criteria — F7.4 (the area sub-levels)

This slice of Epic 7 (`PLAN.md`) puts the four area sub-levels the pinned provider declares into
`resource_mapping.PROTOCOL_SHAPE` for both routing levels, extends the area rule that reads them, prints them,
and keeps the gate rule reading the same table. `ruff check .` and `python3 -m pytest` must pass at the end.

## 1. The measured levels (decided from the live provider schema)

The pinned provider is 2.0.14, measured with `terraform providers schema -json` on 2026-11-02. All four levels
are declared for `protocol.ospf` and for `protocol.ospfv3`, so all four become table rows. None is a report
refusal, and none carries a field the provider marks `sensitive`, so `VALUE_VARIABLES` gains no row.

Two of the four are not direct children of `area`. The provider declares `default_route` inside the `nssa` and
the `stub` bodies, so the rows are `.../area/type/nssa/default_route` and `.../area/type/stub/default_route`,
and `default_route` is a field of those two rows. `nssa_ext_range` is declared only inside `nssa`. The rows stay
separate per routing level, as F7.2 left them, and the two levels are not identical: `ospfv3` declares
`instance_id` on `area/interface` and on `area/virtual_link`, and `ospf` does not. A new row states the whole
field set the provider declares for its level, and an existing row gains only the new level field, so
`instance_id` prints for the `ospfv3` virtual link and the `ospfv3` interface row keeps the fields the parse
read before.

| Table path | Shape word | Fields the row states |
|---|---|---|
| `protocol/<level>/area` | `string_list` | gains `virtual_link` |
| `protocol/<level>/area/virtual_link` | `string_list` | `name` string, `authentication` string, `bfd` object, `dead_counts` number, `enable` bool, `hello_interval` number, `instance_id` number (`ospfv3` only), `neighbor_id` string, `retransmit_interval` number, `transit_area_id` string, `transit_delay` number |
| `protocol/<level>/area/virtual_link/bfd` | `object` | `profile` string |
| `protocol/<level>/area/interface` | `string_list` | gains `neighbor` |
| `protocol/<level>/area/interface/neighbor` | `string_list` | `name` string |
| `protocol/<level>/area/type/nssa` | `object` | gains `default_route` (`one_of`), `nssa_ext_range` (`string_list`) |
| `protocol/<level>/area/type/nssa/default_route` | `one_of` | selects `advertise` → `advertise`, `no` → `disable` |
| `protocol/<level>/area/type/nssa/default_route/advertise` | `object` | `metric` number, `type` string |
| `protocol/<level>/area/type/nssa/default_route/disable` | `block` | none |
| `protocol/<level>/area/type/nssa/nssa_ext_range` | `string_list` | `name` string, `advertise` block, `suppress` block |
| `protocol/<level>/area/type/stub` | `object` | gains `default_route` (`one_of`) |
| `protocol/<level>/area/type/stub/default_route` | `one_of` | selects `advertise` → `advertise`, `no` → `disable` |
| `protocol/<level>/area/type/stub/default_route/advertise` | `object` | `metric` number |
| `protocol/<level>/area/type/stub/default_route/disable` | `block` | none |

Criteria:

1. `PROTOCOL_SHAPE` is the one table. The emitter, the gate rule `protocol_object`, and the property scan read
   it, so a shape stated twice is a failure.
2. Every row is pinned against the live provider schema by
   `tests/test_protocol_object.py::test_the_shape_table_is_the_measured_provider_shape`, through
   `WORD_TO_SCHEMA`. A row that states a level or a field the provider does not declare is a failure, so the
   table states no `area/type/default_route` row.
3. The spelling rule keeps its pins: `selects` is the one place that maps the value the export states (`no`) to
   the key the provider reads (`disable`), so `XML_NAME_EXCEPTIONS` gains no row and no parse method spells a
   field name.
4. `test_the_sensitive_rows_are_the_reference_only_names` keeps its pins: no new sensitive field, so the
   declared set stays `{'secret', 'key', 'password'}`.
5. `COVERAGE_MATRIX` row `panos_virtual_router` gains `virtual_link`, because the property scan measures an area
   entry against that row. A level the scan does not measure stays grounded by the table.

## 2. The choice the export states by presence

`terraform validate` refuses a `nssa_ext_range` element that states neither `advertise` or `suppress`, and a
`default_route` element that states neither `advertise` or `no`. So the two are presence choices, the same rule
F7.1 rule 7 states for a `range` element: the entry that states no choice is marked for the report and prints
nothing. A `default_route` is not an entry, so the report names the entry that holds it — the area entry —
because the report names entries and the file holds no half of it.

Criteria:

1. One rule reads the choice: the fields of a `string_list` entry level that are `block`, and the `selects`
   mapping of a `one_of` level. `_protocol_choice` is the one lookup for both.
2. An export that states no `default-route` element states no choice, so nothing prints and nothing is
   reported: only a level the export states can be a finding.
3. A `one_of` level that states two keys, or a key the mapping does not state, is one gate finding for each.

## 3. Parse, print, and the gate

Criteria:

1. `_protocol_areas` is still the area rule the two routing levels share. It reads the entries of a
   `string_list` level and the one key of a `one_of` level, and it states a level as a table path: no new
   field-name literal appears in the parse methods, which
   `tests/test_protocol_object.py::test_the_table_is_the_only_shape_owner` pins.
2. `container_coverage.CONTAINER_TABLE` gains one `emitted` sub-shape row per routing level for each entry
   level the parse states as a path: `area/virtual-link` and `area/interface/neighbor`. `nssa-ext-range` needs
   no row, because the parse reaches it from the field the `nssa` body row names, so no path string states it
   and `test_every_row_path_is_read_by_its_method` could not read such a row.
3. The emitter prints the new levels in the table order, and the gate rule reports no finding on a run that
   prints them.
4. The parse registers no new method, so `tests/test_entry_coverage.py::_parse_every` and
   `tests/test_multi_vsys_location.py` keep their lists: the new levels are read through
   `_protocol_areas`, which `parse_ospf` and `parse_ospfv3` already call.

## 4. Pins

1. `tests/test_protocol_object.py`: `test_the_shape_table_is_the_measured_provider_shape` no longer names the
   four levels as outside the table; the new pins state the rows, the presence-choice mapping, the print for a
   choice inside a body, and the gate finding for a choice inside a nested level.
2. `tests/fixtures/ospf.xml` and `tests/fixtures/ospfv3.xml` gain entries that reach every new level for their
   routing level, and one entry that states no presence choice, which the report names.
3. `tests/test_parse_network.py` pins the parse read for both routing levels.
4. `tests/test_property_coverage.py` pins the scan scope: the area dict is measured, so `virtual_link` is a
   declared property of the router row, and a neighbor entry inside an interface entry is not measured, so
   `neighbor` is not.
5. The golden set is the bytes of a real run. The three golden fixtures state none of the new levels, so the
   goldens move only if a run moves them.
