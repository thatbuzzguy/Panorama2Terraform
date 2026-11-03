# Acceptance — F7.5, the `rip` level of the `protocol` object

Scope: the `rip` level the pinned provider declares. One table row per level `parse_rip` reads, the parse
method that reads them through the table, the pins that hold the new rows against the live provider
schema, and the tracking markdown.

Baseline: `development`, provider 2.0.14, Terraform 1.16.2, `ruff check .` clean, 1322 tests.

## Criteria

1. **`PROTOCOL_SHAPE` gains the `rip` field on the `protocol` row**, and one row per level the provider
   declares for the `rip` subtree that this converter prints:

   | Path | Shape | Fields |
   |---|---|---|
   | `protocol/rip` | `object` | `enable` bool, `allow_redist_default_route` bool, `reject_default_route` bool, `timers` object, `global_bfd` object, `interfaces` string_list, `export_rules` string_list, `auth_profile` string_list |
   | `protocol/rip/timers` | `object` | `interval_seconds`, `update_intervals`, `expire_intervals`, `delete_intervals`, each `number` |
   | `protocol/rip/global_bfd` | `object` | `profile` string |
   | `protocol/rip/interfaces` | `string_list` | `name` string, `enable` bool, `mode` string, `authentication` string, `bfd` object, `default_route` one_of |
   | `protocol/rip/interfaces/bfd` | `object` | `profile` string |
   | `protocol/rip/interfaces/default_route` | `one_of` | no fields, `selects` = `advertise` → `advertise`, `no` → `disable` |
   | `protocol/rip/interfaces/default_route/advertise` | `object` | `metric` number |
   | `protocol/rip/interfaces/default_route/disable` | `block` | no fields |
   | `protocol/rip/export_rules` | `string_list` | `name` string, `metric` number |
   | `protocol/rip/auth_profile` | `string_list` | `name` string, `password` string (sensitive) |
   | `protocol/rip/auth_profile/md5` | `string_list` | `name` string, `key` string (sensitive) |

   Every row is the field name and shape the provider declares, measured 2026-11-02 against 2.0.14. The
   provider declares no `router_id`, no `area`, no `neighbor`, and no `type` for `rip`, so `rip` has no area
   row and no choice row outside `default_route`.

2. **The two `auth_profile` rows are the sensitive decision only.** `parse_rip` reads no value for them, the
   same rule as `protocol/bgp/auth_profile` and `protocol/ospf/auth_profile`. The `sensitive` facts they
   state (`password`, `key`) are pinned against the schema, and `VALUE_VARIABLES` keeps the same three
   reference-only names, so no new row is needed there. The parse method that reads an auth profile body is
   F7.7, which is also the slice that decides `ospfv3`.

3. **`parse_rip` states a path and never spells a field name.** It reads the level through `_protocol_level`,
   fills the two `string_list` levels with `_protocol_entries`, and fills the choice the export states inside
   an interface entry through `_protocol_body` and `_protocol_presence_choice`. A field name comes from
   `_protocol_field_name`, an element name from `_protocol_xml_name`. `test_the_table_is_the_only_shape_owner`
   reads `parse_rip` as an owner.

4. **`_protocol_entries` fills the choice an entry states inside itself.** An interface entry holds its
   `default_route` choice, so the reader fills a `one_of` field of the row from the element under the entry,
   the same rule `_protocol_body` already uses for a chosen body, and keeps the existing rule for the row's
   `block` fields. The choice level is not required, so an entry that states no choice element prints nothing
   for it. A choice element that states none of the alternatives `terraform validate` requires has no `.tf`
   shape, so the entry that holds it is marked for the report and not put in the printed list.

5. **The export states a name-keyed list as an entry**, so a `rip` interface and an export rule are entries the
   ledger records, the same rule as every other protocol level.

6. **The container table gains the rows the scan reads**: `protocol/rip`, `protocol/rip/interfaces`,
   `protocol/rip/export-rules`, each `emitted` with `panos_virtual_router`. A single-object level holds no
   entry, so it has no row. No row names `protocol/rip/interfaces/bfd`, because the parse reaches it through
   the field the interfaces row states.

7. **The property scan measures the two entry levels**, so `COVERAGE_MATRIX` row `panos_virtual_router` gains
   the properties a run reads from a `rip` entry: `authentication`, `bfd`, `default_route`, `mode`. `enable` and
   `metric` are already there. The single-object levels are plain dicts, so nothing is measured for them.

8. **The gate rule needs no new branch**: it reads the table. New pins: the rip rows against the schema, the
   block a run writes for `tests/fixtures/rip.xml`, one finding per violation type for a choice inside an
   entry, and the `password` and `key` fields printed as the variable reference.
   `test_the_rule_reports_an_undeclared_field_and_a_wrong_shape` no longer uses `rip` for a level outside the
   table; it uses `redist_profile`, which the table still does not state.

9. **The new parse method is registered in the two test helpers** that call a parse method for every router:
   `tests/test_entry_coverage.py::_parse_every` and `tests/test_multi_vsys_location.py`.

10. **`tests/fixtures/rip.xml`** states every field the new rows declare, plus one interface entry whose
    choice element states no alternative for the report. It is a device-level fixture, so the scope pins and
    the corpus scan read it with no finding. No golden fixture states `rip`, so no golden set moves.

11. **The markdown tracks the slice**: `docs/ARCHITECTURE.md` §4.9 names the new levels and the entry that
    holds its own choice; `backlog.md` closes the `rip` line and keeps the auth profile body line; `PLAN.md`
    records F7.5; `to-do.md` moves to F7.6; `agent-status.md` records the position, the test count and the
    pins that changed.

12. `ruff check .` is clean and `python3 -m pytest` passes. `terraform validate` accepts the block the run
    writes for `rip.xml` (measured 2026-11-02, Terraform 1.16.2, provider 2.0.14).
