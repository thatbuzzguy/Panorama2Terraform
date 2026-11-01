# Acceptance criteria — F7.2: the `ospfv3` level of the protocol object

Feature record: `PLAN.md` Epic 7. The piece taken from `to-do.md` is the parse method for a routing level
`PROTOCOL_SHAPE` does not state. The Epic 6 write path stays open: it needs the outputs rule for a name
another unit owns, which is a decision, not a module.

Scope: the `ospfv3` level and the area subtree under it. The parse method reads the levels the table states,
the table gains a row for each of them, and the emitter, the gate rule and the report read the same table,
so no second shape appears.

## Decisions

### 1. The table states the levels the parse reads

The `protocol` row gains the `ospfv3` field, and the new rows are the levels `parse_ospfv3` reads:
`protocol/ospfv3`, `protocol/ospfv3/area`, `protocol/ospfv3/area/type` with its three bodies,
`protocol/ospfv3/area/range`, `protocol/ospfv3/area/interface` with its three link bodies. Each row is the
shape the live provider schema declares for that level, measured 2026-11-01 against the pinned provider
2.0.14 and pinned by `tests/test_protocol_object.py::test_the_shape_table_is_the_measured_provider_shape`.

The table states a level only when a parse method reads it. The levels `ospfv3` declares but this feature
does not read — `timers`, `global_bfd`, `graceful_restart`, `export_rules`, `auth_profile`,
`area/virtual_link`, `area/interface/neighbor`, `area/type/default_route`, `area/type/nssa_ext_range` — stay
unprinted and stay in `backlog.md`.

### 2. The `ospfv3` area shape is the `ospf` area shape, field for field

The provider declares the same fields for both area subtrees: `name`, `type`, `range`, `interface`, the three
area type bodies, the range choice blocks, and the three link types. So the new rows state the same shape
words as the `ospf` rows, with the field order the print order. Two rows for two levels are not two tables:
`PROTOCOL_SHAPE` stays the one owner, and the pin test reads both against the schema.

### 3. Bug fix the feature forces: the choice body lives inside the chosen element

`_protocol_choice` takes the element the sub-shape's fields live in: the entry itself for a BGP peer group,
and the chosen element for an area type. `parse_ospf` passed the `type` element, so a field inside the chosen
body was read from the wrong place and printed nothing. Measured before the fix: an area with
`<type><nssa><accept-summary>yes</accept-summary></nssa></type>` printed `type = { nssa = {} }`. Fix: the
parse passes the chosen element for an area type in both levels. Pinned by
`tests/test_protocol_object.py::test_an_ospf_area_type_body_prints_the_fields_it_declares`.

### 4. Membership and the report cases

An interface prints inside the area element that holds it, the same rule as the `ospf` level. An interface the
export places at the `ospfv3` level has no provider field, so the container row for it is a report row and the
manual report names it. A `range` entry must state exactly one of `advertise` or `suppress`, so an entry that
states neither is a report row. An entry the file cannot hold is not put in the printed list.

### 5. The container rows

One row for the level and one row per container the method reads: `protocol/ospfv3`, `protocol/ospfv3/area`,
`protocol/ospfv3/range` (nested block), `protocol/ospfv3/area/interface`, and `protocol/ospfv3/interface`
(report). `test_every_row_path_is_read_by_its_method` pins the paths, and the property scan measures the
emitted rows against the router row.

### 6. Truth across the corpus

`tests/fixtures/ospfv3.xml` is the fixture that exercises the level. The container scan reports no finding on
it, the property scan reports no finding on it, the gate rule reports no finding on the block the run writes
for it, and two runs on it write the same bytes. The committed goldens are unchanged.

## Acceptance criteria

1. `resource_mapping.PROTOCOL_SHAPE` gains the `ospfv3` field on the `protocol` row and the rows for the
   levels the parse reads; no row states a shape the live schema does not declare, and no field is spelled
   outside the table.
2. `PanoramaParser.parse_ospfv3` builds the level through `_protocol_level` and `_protocol_choice`, marks
   every entry it reads, states each level as a table path, and writes no field name of its own; the fix in
   decision 3 lands in `parse_ospf` as one rule for both levels.
3. `_parse_router` builds the `ospfv3` level with the two existing levels, so the emitter prints it from the
   table with no per-level branch.
4. `container_coverage.CONTAINER_TABLE` gains the rows in decision 5.
5. `tests/test_protocol_object.py` pins the table against the schema for the new rows, names `parse_ospfv3`
   as a shape owner, states the mapping for the new choice levels, pins the printed shape for the fixture,
   pins the choice body fix, and pins one report case.
6. `tests/test_container_coverage.py` and `tests/test_property_coverage.py` stay green on the new fixture
   with no new finding, and `tests/test_entry_coverage.py` pins that the parse marks the fixture's entries.
7. `docs/ARCHITECTURE.md` §4.9, `README.md`, `backlog.md`, `PLAN.md`, `to-do.md` and `agent-status.md` state
   the landed rule and name the test that holds it; the completed piece leaves the tracking markdown.
8. `ruff check .` is clean, `pytest` is green, and the change is committed. The completed pieces leave
   `to-do.md`, and `PLAN.md` keeps the open Epic 7 list without `ospfv3`.

## Results

All criteria are met. Measured against the pinned provider 2.0.14 on 2026-11-01: the `ospfv3` level declares
`enable`, `router_id` and `area`, the area declares `name` (a string), `type`, `range` and `interface`, the area
type states `normal`, `nssa` and `stub`, the range states `advertise` and `suppress` as blocks with no
attributes, and the interface's link type states `p2p`, `broadcast` and `p2mp`. No field in the new rows is
marked `sensitive`.

`tests/fixtures/ospfv3.xml` prints the block the table states, the gate rule reports no finding on it, the
container scan and the property scan report no finding on it, and two runs write the same bytes. The fix in
decision 3 is measured: `tests/fixtures/ospf.xml` now prints `accept_summary = true` inside the `stub` body.
The committed goldens are unchanged. `ruff check .` is clean and `pytest` is green (1244).
