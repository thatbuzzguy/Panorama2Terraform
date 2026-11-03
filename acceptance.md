# Acceptance — F7.7, the auth profile body of the `protocol` object

Scope: the rows `PROTOCOL_SHAPE` states for the auth profile levels of the four routing levels, the parse read
for an auth profile entry, the emitter print for a reference-only field, the gate rule, the container table rows
the property scan reads, the matrix row the scan measures, the fixtures that reach the levels, the pins, and the
tracking markdown.

Baseline: `development` at `206e493` (markdown) / `14826ca` (code), provider 2.0.14, Terraform 1.16.2,
`ruff check .` clean, 1336 tests.

## Measurement

Measured 2026-11-03 against the pinned provider 2.0.14 (`terraform providers schema -json`), for
`panos_virtual_router.protocol`:

1. `protocol.bgp.auth_profile` is a `list` with two attributes: `name` (string) and `secret` (string, marked
   `sensitive`).
2. `protocol.ospf.auth_profile` and `protocol.rip.auth_profile` are the same shape: `name`, `password`
   (`sensitive`), and `md5`, which is a `list` holding `name`, `key` (`sensitive`) and `preferred` (bool).
3. `protocol.ospfv3.auth_profile` is a `list` with `name`, `spi` (string), `ah` and `esp`. `ah` declares five
   alternatives (`md5`, `sha1`, `sha256`, `sha384`, `sha512`), each a `single` level holding `key`
   (`sensitive`). `esp` is a `single` level with two: `authentication`, which declares the same five plus
   `none` with no attribute, and `encryption`, a `single` level holding `algorithm` and `key` (`sensitive`).
4. `protocol.ospfv3` does not declare `auth_profile` as a field today, so the row gains it.
5. The provider accepts `ah` or `esp` for one `ospfv3` auth profile entry, not both, and `terraform validate`
   reports the combination as an invalid attribute combination. The table states no word for that, so the
   fixture states the two choice levels in two entries.

The existing rows for the `bgp`, `ospf` and `rip` auth profiles state the fields the provider declares, so they
stay. The `md5` rows gain `preferred`, because the reader now reads the level and a row states only the fields
the reader reads. The `ospfv3` auth-profile subtree has no rows, so this slice states 14 rows for it. No
auth-profile level declares a field outside the three `reference_only` names, so `VALUE_VARIABLES` gains no row
and the sensitive set stays `secret`, `key`, `password`.

## Criteria

1. **`PROTOCOL_SHAPE` states the auth profile levels as the provider declares them.** A `list` level is a
   `string_list` row, a `single` level whose attributes are the alternatives is a `one_of` row with the identity
   mapping, a `single` level with attributes is an `object` row, and a level with no attribute (`none`) is a
   `block`. Every new row is pinned against the live schema by
   `test_the_shape_table_is_the_measured_provider_shape`, so the docstring that exempted the three
   `auth_profile` rows as "rows with no reader" is removed.

2. **The parse read states a path and never spells a field name.** Each of `parse_bgp`, `parse_ospf`,
   `parse_ospfv3` and `parse_rip` fills its auth profile level through `_protocol_branch`, which walks the
   path's segments and calls `_protocol_entries`. The levels inside the entry (`md5`, `ah`, `esp`,
   `esp/authentication`, `esp/encryption`) are filled by `_protocol_body`, which reaches them through the table,
   so the code states no path for them.

3. **The parse stores the value for a reference-only field.** `_protocol_level` reads it with no special case, so
   the captured object holds it and the property scan counts the read. The print site records the §5 name of the
   entry that holds the field, with no value for it, so the value cannot reach a generated file: no `.tfvars`
   line, no site row, and the declaration states `sensitive = true`. The description of the declaration says the
   reference prints and no file states the value, because the run now reads a value it never writes.

4. **The print is the reference.** A field the table marks `sensitive` prints as `var.<the §5 name of the entry
   that holds it>`, through `VALUE_VARIABLES`, with no per-level branch in the emitter.

5. **The gate reads the same table.** A sensitive field inside the subtree is refused as a literal and accepted
   as a reference; a `one_of` level that states more than one alternative is refused; a field the row does not
   declare is refused.

6. **The container table gains four `emitted` `sub-shape` rows**, one per routing level, in the input spelling
   (`protocol/<level>/auth-profile`), because the property scan measures an entry only through an emitted row that
   names the provider type. No row names `protocol/ospf/auth_profile/md5`, because the parse reaches that level
   through the field the auth profile row states and the code states no path for it.

7. **`COVERAGE_MATRIX` row `panos_virtual_router` gains the properties a run reads from those entries.** The
   measured set gains `ah`, `esp`, `md5`, `password`, `secret` and `spi`. `key` stays grounded by the table,
   because an entry inside an entry is not in the scan scope. A reference-only name is a property only for the
   row that covers the entry the run read it in, so
   `tests/test_site_data.py::test_the_table_holds_no_property` reads the names through `PROTOCOL_SHAPE` instead
   of excluding them.

8. **An entry the `.tf` cannot express is marked for the report and not put in the printed list**, the same rule
   as F7.1 and F7.5: a presence choice that states none of the alternatives the provider requires.

9. **The fixtures.** One new fixture, `tests/fixtures/auth_profile.xml`, states one router with an auth profile
   entry at each of the four levels, and each entry states every field its row declares: one `md5` entry
   inside a profile entry, and the `ah` and `esp` choices in two `ospfv3` entries. The four level fixtures stay
   unchanged, so the whole-block print pins that read them stay intact. No golden fixture states an auth profile,
   so no golden set moves. Each value is distinct, so the pin that no generated file holds a parsed value can
   name each one.

10. **The pins.** The rows against the live schema (the existing generic pin); the shape decision and the
    `selects` mapping for `ah` and `esp/authentication`; the four container rows; the parse read for each level;
    the print for a real run; the gate for a literal and for a reference; the scan scope for an auth profile
    entry and not for an entry inside it; the declaration set and the `sensitive` marking for the names the run
    records; and the pin that no generated file holds the parsed value. `test_entry_coverage.py::_parse_every`
    and `tests/test_multi_vsys_location.py` already call the four level methods for every router, so they are
    the registration and the corpus pins read the new marks. The declaration pins read the names the run records
     through the table and the naming rule, so they state no name list.

11. `ruff check .` is clean and `python3 -m pytest` passes. `terraform validate` accepts the block the run
    writes for `tests/fixtures/auth_profile.xml` (Terraform 1.16.2, provider 2.0.14), which is the check that one
    entry states `ah` or `esp`, not both.

12. **The markdown tracks the slice**: `docs/ARCHITECTURE.md` §4.9 names the auth profile levels and the print
    rule for a reference-only field; `PLAN.md` records F7.7; `to-do.md` moves to F7.8; `backlog.md` keeps the
    levels this slice does not read; `agent-status.md` records the position, the test count and the pins that
    changed.
