# Acceptance criteria — F7.3 (the `ospfv3` scalar levels)

This is the first slice of Epic 7 (`PLAN.md`). It puts the four `ospfv3` levels the provider declares and
`parse_ospfv3` can read into `resource_mapping.PROTOCOL_SHAPE`, reads them, prints them, and keeps the gate
rule reading the same table. `ruff check .` and `python3 -m pytest` must pass at the end.

## 1. The measured levels (decided from the live provider schema)

The pinned provider is 2.0.14. `terraform providers schema -json` declares all four levels under
`panos_virtual_router.protocol.ospfv3`, so all four become table rows. None is a report refusal, and none
carries a field the provider marks `sensitive`, so `VALUE_VARIABLES` gains no row.

| Table path | Shape word | Fields the row states |
|---|---|---|
| `protocol/ospfv3/timers` | `object` | `lsa_interval` number, `spf_calculation_delay` number |
| `protocol/ospfv3/global_bfd` | `object` | `profile` string |
| `protocol/ospfv3/graceful_restart` | `object` | `enable` bool, `grace_period` number, `helper_enable` bool, `max_neighbor_restart_time` number, `strict_l_s_a_checking` bool |
| `protocol/ospfv3/export_rules` | `string_list` | `name` string, `metric` number, `new_path_type` string, `new_tag` string |

Criteria:

1. `PROTOCOL_SHAPE` is the one table. The emitter, the gate rule `protocol_object`, and the property scan read
   it, so a shape stated twice is a failure.
2. Every new row is pinned against the live provider schema by
   `tests/test_protocol_object.py::test_the_shape_table_is_the_measured_provider_shape`, through
   `WORD_TO_SCHEMA`. A row that states a field the provider does not declare is a failure.
3. `test_the_sensitive_rows_are_the_reference_only_names` keeps its pins: no new sensitive field, so the
   declared set stays `{'secret', 'key', 'password'}`.
4. The `protocol/ospfv3` row gains the four as fields, so the emitter prints them. Field print order stays
   the table order, and the `ospfv3` area pin in `tests/test_protocol_object.py` stays intact because the
   fixture's area router states none of the new levels.

## 2. The spelling exception (decided)

`_protocol_xml_name` is the one rule that turns a table field name into the element name the export states.
It cannot produce `strict-lsa-checking` from `strict_l_s_a_checking`, because the provider splits the
initialism. The provider spelling is the table's, so the exception is one place in `resource_mapping`:
`XML_NAME_EXCEPTIONS`, read by `_protocol_xml_name`. No parse method spells an element name of its own.

Criteria:

1. `XML_NAME_EXCEPTIONS` holds one entry: `strict_l_s_a_checking` → `strict-lsa-checking`. It is the only
   place a spelling is stated besides the rule.
2. `tests/test_protocol_object.py::test_the_table_is_the_only_shape_owner` keeps its pins and names the
   exception as the one case the rule cannot produce.
3. `docs/ARCHITECTURE.md` §4.9 rule 3 states the exception in one sentence and names the table that holds it.

## 3. Parse, print, and the gate

Criteria:

1. The three `object` levels are read by `_protocol_level`, so `parse_ospfv3` gains no field-name literal;
   `export_rules` is a `string_list`, so `parse_ospfv3` reads its entries with one path constant. The method
   states a path and never spells a field name.
2. `container_coverage.CONTAINER_TABLE` gains one sub-shape row for `protocol/ospfv3/export-rules`, so the
   property scan measures its entries. A level that holds no entries needs no row.
3. The emitter prints the four levels, and the gate rule reports no finding on a run that prints them. A
   hand-written block that states a level in a shape the row does not state is one finding.
4. `COVERAGE_MATRIX` row `panos_virtual_router` gains `new_path_type` and `new_tag`, because the property
   scan measures an export-rule entry against that row. A field read through a level dict is grounded by the
   table, not by the measurement, so the three `object` levels add nothing to the row.
5. No test helper needs a new method name: `parse_ospfv3` is already registered in
   `tests/test_entry_coverage.py::_parse_every` and `tests/test_multi_vsys_location.py`.

## 4. Fixture and pins

Criteria:

1. `tests/fixtures/ospfv3.xml` gains one router entry that states all four levels. The existing area entry is
   unchanged, so the existing pins hold. The fixture is not a golden case, so no golden is regenerated.
2. New pins in `tests/test_protocol_object.py`: the four rows against the schema (already generic), the
   spelling exception, the parse reading the levels, the emitter printing them, and one gate finding per
   violation type for a new level.
3. Golden sets are the bytes of a real run and are not edited by hand. No golden fixture states one of the
   four levels, so the goldens must not move; a run must show that.
4. `ruff check .` is clean and `python3 -m pytest` is green.

## 5. Tracking markdown

1. `to-do.md`: this slice's pieces are tracked while the work runs, and removed when it is committed.
2. `backlog.md`: the resolved `ospfv3` scalar levels are removed; `strict_l_s_a_checking` and the levels this
   slice does not read stay.
3. `agent-status.md`: the position, the test count, and the pins that changed.
4. `PLAN.md`: the Epic 7 paragraph names the levels this slice landed.
5. No document restates a rule another document owns, and no document states a test count.

## 6. Commit

One commit whose message starts with `F7.3:`, states the measured levels, the spelling exception and the
property scan change in ASD-STE100. The tracking markdown is updated after the commit.
