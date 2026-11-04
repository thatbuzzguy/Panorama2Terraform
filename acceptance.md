# Decision — the container row for an aggregate subinterface — acceptance criteria

This slice closes the open item `backlog.md` names for the property scan (F4.4):
`panos_aggregate_layer3_subinterface` is one of the two matrix rows with no read of its own. The cause is the
container table: `parse_interfaces` reads the aggregate subinterface container
(`network/interface/aggregate-ethernet/entry/layer3/units`) through the same relative pattern it uses for the
ethernet shape, and the table has no row for it, so the general `layer3/units` sub-shape row covers the entry
and the scan measures it against `panos_ethernet_layer3_subinterface`.

## Facts before the change

- `parse_interfaces` reaches the aggregate subinterface two ways: an entry under `aggregate-ethernet` whose
  name already carries a unit (`ae1.101`), and an entry under `layer3/units` inside an aggregate entry
  (`ae1.101.20`). Only the second is a container the table can name, because the first is a name fact the row
  shape cannot state.
- `entry_coverage.covering_row` takes the longest matching row, so a row for the aggregate subinterface
  container is the row that covers a nested aggregate entry, and the aggregate group row still covers the
  entries directly under `aggregate-ethernet`.
- The emitter prints both shapes as `panos_aggregate_layer3_subinterface` (`INTERFACE_RESOURCE_TYPES` for a
  `units` entry, the name rule for `ae1.101`), so no emitter change is needed: the table row is missing.
- `test_measured_reads_equal_the_declared_properties` compares the properties the row declares with the keys
  the run read from the entries that row covers. The aggregate group row declares 8 properties, and the
  `parent` read comes from `ae1.101`, which stays covered by that row, so the group row keeps its list.

## Decision

`CONTAINER_TABLE` covers the aggregate subinterface container with its own `emitted` sub-shape row that names
`panos_aggregate_layer3_subinterface`. The ethernet sub-shape rows keep the shape they state for the ethernet
container. The matrix row for `panos_aggregate_layer3_subinterface` names the fixture entry the scan measures
through that row: `ae1.101.20` in `tests/fixtures/interfaces_other.xml`.

## Acceptance criteria

1. `CONTAINER_TABLE` holds one row for `parse_interfaces` reading
   `network/interface/aggregate-ethernet/entry/layer3/units`, with destination `emitted`, the provider type in
   its note, and level `sub-shape`. `test_every_row_path_is_read_by_its_method` reads the path through the
   segments the method names.
2. `entry_coverage.covering_row` answers that row for `ae1.101.20`, so `matrix_row_for` answers the matrix row
   for `panos_aggregate_layer3_subinterface` for the entry. The pin states both.
3. The fixture entry is marked by `parse_interfaces`, and the run prints it as a
   `panos_aggregate_layer3_subinterface` block in `interfaces.tf` with `parent` and `tag`.
4. The matrix row names that entry: `xml_element` is the container path the parse reads plus `entry`,
   `xml_name` is `ae1.101.20`, and `emitted_name` is `ae1.101.20`, so `test_fixture_contains_the_row_element`
   reads the entry the property scan measures.
5. `test_measured_reads_equal_the_declared_properties` measures the aggregate subinterface row through the
   corpus, so the unmeasured set is `['panos_device_group_parent']`, and the docstring names one row instead
   of two.
6. No golden moves. The aggregate subinterface entry is a property level, so the entry report shows the count
   on the `ae1.101` row, the run writes the same `.tf` bytes, and the property scan reports no finding for the
   entry. A golden that does move must come from a real run and be stated in `agent-status.md`.
7. The run accepts the fixture: the sanity gate reports `PASS (0 FAIL, 0 WARN)` for
   `tests/fixtures/interfaces_other.xml`, and `terraform validate` passes for the block the run writes for the
   entry in the kitchen-sink case.
8. `ruff check .` is clean and `python3 -m pytest` passes.
9. `docs/COVERAGE_MATRIX.md` states the row as the pin states it, `backlog.md` loses the closed item, and
   `to-do.md` and `agent-status.md` carry the decision.
