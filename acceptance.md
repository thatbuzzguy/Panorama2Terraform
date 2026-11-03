# Acceptance — F7.6, the BGP `policy` level of the `protocol` object

Scope: the `policy` level the pinned provider declares on `protocol.bgp`, the rows `PROTOCOL_SHAPE` states for
the levels `parse_bgp` reads, the shape word a member list needs, the parse read, the emitter print, the gate
rule, the container table and matrix row the scan reads, the fixture that reaches the level, the pins, and the
tracking markdown.

Baseline: `development` at `25e0a39` (F7.5), provider 2.0.14, Terraform 1.16.2, `ruff check .` clean, 1330 tests.

## Measurement

Measured 2026-11-02 against the pinned provider 2.0.14 (`terraform providers schema -json`): `protocol.bgp`
declares `policy` as a `single` level with four children (`aggregation`, `conditional_advertisement`, `export`,
`import`), and the subtree holds 77 levels below it. So `policy` is a table row, not the report decision F2.9
states for a level the provider does not declare. Every row this slice states is a level the provider declares;
`test_the_shape_table_is_the_measured_provider_shape` holds each row against the live schema.

The measurement also states three facts the existing table cannot express:

1. Five field names are `['list', 'string']` (`from_peer`, `nexthop`, `append`, `overwrite`, `used_by`), which is
   a list whose members are values, not entries, and 27 fields use them. `string_list` is the word for a `[`
   value, so it covers both. The table needs the specialization word `member_list` to say which one a field is,
   the same way `one_of` and `block` are specializations of `object`.
2. Nineteen levels declare no attribute (`action/deny`, `as_path/none`, `as_path/remove`, `community/none`,
   `community/remove_all` and their extended-community twins), so they are `block` rows or `block` fields inside
   the row that holds them: the export states them by presence.
3. `terraform validate` (Terraform 1.16.2, provider 2.0.14) accepts a policy level that states one attribute and
   refuses one that states two, so the nine levels whose attributes are values (`aggregate_route_attributes`
   `as_path`, `community` and `extended_community`, and the same three inside `export` and `import` rule
   `update`) are `one_of` rows with the identity mapping, and the levels that hold them state those fields as
   `one_of`. `update` and `match` accept more than one attribute, so they stay `object` rows. The import `update`
   `as_path` level declares only `none` and `remove`, so its mapping states only those two keys.

## Criteria

1. **`SHAPE_WORDS` gains `member_list`**, the `[` value whose members are values. `sanity_checks` states which
   word the field reader reads each specialization as (`one_of` and `block` as `object`, `member_list` as
   `string_list`), because the reader reads a shape family and cannot tell a specialization from the bytes.
   `test_value_shape_is_the_reader_inverse_for_every_shape_word` covers the new word, and the word is read from
   the table, not from a name list.

2. **`PROTOCOL_SHAPE` gains `policy` as a field of the `protocol/bgp` row** and one row per level of the policy
   subtree the reader walks: 78 rows. A `single` level with attributes is an `object` row, a `list` level is a
   `string_list` row, a level with no attribute is a `block` row, `action` is a `one_of` row with the identity
   mapping (`allow` → `allow`, `deny` → `deny`), the nine value-choice levels are `one_of` rows with the identity
   mapping, and a `['list', 'string']` field is a `member_list` field. No
   policy level declares a field the provider marks sensitive, so every new row states an empty `sensitive` set
   and no new `VALUE_VARIABLES` row is needed.

3. **A row states only the fields the reader reads.** For the policy subtree `parse_bgp` reads every field the
   provider declares for every level, so each row states all of them. Field order is the schema order.

4. **`parse_bgp` states a path and never spells a field name.** It reads the `policy` level through
   `_protocol_level`, and fills the four levels that hold entries through `_protocol_entries` with the path as
   the key. The walk from the level dict uses the path's segments, which are the table's field names. The
   levels inside an entry are read by the generic rule, so the code states no path for them and the container
   table states no row for them.

5. **`_protocol_body` fills the shapes a level dict cannot hold**, extended for the policy subtree: the `one_of`
   choice, the entries of a `string_list` level, and the entry lists inside an `object` level. A
   `member_list` field is read by `_protocol_level`, because its value is the members the element holds.

6. **The print reads the table.** A `member_list` field prints as its list of values, with no level row to walk.
   A `block` field prints `{}`, a `one_of` level prints the one key `selects` states, and an entry prints in the
   field order its row states. `test_an_ospfv3_level_prints_the_shape_the_table_states` style pin: the whole
   block a run writes for the new fixture.

7. **The gate reads the same table.** A `member_list` field is refused when the value is not a `[` value, and its
   members are not read as entries, so rule 4 (an element that states no `name`) does not reach a member list.
   The rule still refuses a level the table states no row for, a field the row does not declare, and a `one_of`
   level that states more than one key.

8. **The container table gains the four entry levels the scan measures**: `protocol/bgp/policy/aggregation/address`,
   `protocol/bgp/policy/conditional_advertisement/policy`, `protocol/bgp/policy/export/rules`,
   `protocol/bgp/policy/import/rules`, each `emitted` with `panos_virtual_router` and `level='sub-shape'`. Every
   other policy level holds no entry, or holds an entry inside an entry, so it has no row and stays grounded by
   the table.

9. **`COVERAGE_MATRIX` row `panos_virtual_router` gains the properties a run reads from those entries**:
   `action`, `advertise_filters`, `aggregate_route_attributes`, `as_set`, `match`, `non_exist_filters`, `prefix`,
   `summary`, `suppress_filters`, `used_by`. `enable` is already in the row.

10. **An entry the `.tf` cannot express is marked for the report and not put in the printed list**, the same rule
    as F7.1 and F7.5. For the policy subtree the case is an `action` element that states none of the keys the
    row selects.

11. **`tests/fixtures/bgp_policy.xml`** is the new device-level fixture: it states every field the new rows
    declare for each of the four entry levels, plus one export rule the report names. No golden fixture states a
    BGP policy, so no golden set moves.

12. **The pins**: the new rows against the live schema (the existing generic pin), the shape decision for
    `member_list` and `action`, the four container rows, the parse read, the print, the gate, and the scan scope.
    `test_the_table_is_the_only_shape_owner` reads the new rules as owners. `parse_bgp` is already in the two
    helpers that call a parse method for every router, so no helper changes.

13. `ruff check .` is clean and `python3 -m pytest` passes. `terraform validate` accepts the block the run
    writes for `tests/fixtures/bgp_policy.xml` (measured against Terraform 1.16.2, provider 2.0.14).

14. **The markdown tracks the slice**: `docs/ARCHITECTURE.md` §4.9 names the policy levels and the member-list
    word; `PLAN.md` records F7.6; `to-do.md` moves to F7.7; `backlog.md` keeps the auth profile body line for
    F7.7; `agent-status.md` records the position, the test count and the pins that changed.
