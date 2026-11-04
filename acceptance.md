# Decision — grounding the filter exception pairs — acceptance criteria

This slice closes the open item `backlog.md` names for `docs/ARCHITECTURE.md` §4.10 rule 3:
`FILTER_XML_NAME_EXCEPTIONS` holds 15 path-keyed pairs, and the fixture grounds five. A pair is grounded
when a fixture entry states the input spelling and the run prints the table spelling for it, so the pair is
a fact a real run read, not a spelling the pango source measures. This slice extends
`tests/fixtures/filter_containers.xml` so every pair is stated by an entry, and moves the pin from a text
search to the pair the run prints.

## Facts

- `FILTER_XML_NAME_EXCEPTIONS` is keyed by the container path, because one provider field name spells two
  ways in the input. It holds 15 pairs across 5 containers, and `ipv4_entries` and `ipv6_entries` spell the
  same way in two containers, so 13 distinct spellings. None is a spelling the `-` rule can produce.
- `resource_mapping.FILTER_SHAPE` is the one table that states a filter level's fields, and
  `ShapeTable.xml_name` is the one rule that turns a table name into the element the input spells, so the
  parse reads the element through the exception map (`_protocol_xml_name`) and the emitter prints the table
  name. A parse method states a path and never spells a field name (`docs/ARCHITECTURE.md` §4.9 rule 3).
  `XML_NAME_EXCEPTIONS` stays the protocol table's own map, and no new exception row is added here: the
  pairs are already in the map, so this slice grounds them and changes no mapping.
- The choice rule (F7.12, F7.13): a row that states `selects` is a level the provider reads as exactly one
  attribute, so one entry can state one alternative. The entry-list fields of a choice container are under
  the chosen alternative, so one entry states one entry-list spelling only. That is why a pair is grounded
  by an entry and not by one entry per container: the fixture needs one entry per pair, or one entry that
  states several spellings under one chosen alternative.
- `tests/fixtures/filter_containers.xml` is a golden case (`tests/test_golden_files.py` case
  `filter_containers`), so extending it moves the `.tf` goldens. A golden is the bytes of a real run and is
  never edited by hand.
- The pin machinery already in `tests/test_filter_containers.py` reads a run the way the gate reads it:
  `_run` runs the converter, `sanity_checks.blocks` and `import_blocks.fields_at` read the printed fields,
  and `_printed_level` walks a level inside a printed block. `sanity_checks.check_terraform` is the validate
  check the CLI runs on `--validate`, and `test_terraform_validate_filters_succeeds` calls it per unit
  directory. The grounding pin reads the pair through that machinery, so it cannot restate a table row by
  hand.

## Criteria

1. Every one of the 15 pairs is stated by an entry in `tests/fixtures/filter_containers.xml`. Each entry
   states the element the exception names, and the row that declares the field states the provider spelling.
   No exception row is added, removed, or reworded, and no mapping is restated.
2. One entry states one alternative per choice level, so the choice rule still holds for every entry the
   fixture adds: each choice level the entry reaches states exactly one key.
3. A real run on the extended fixture reports `PASS (0 FAIL, 0 WARN)`; `terraform validate` accepts every
   block the run wrote for the fixture, including the blocks written for the new entries.
4. The grounding pin is the pair the run prints, read from the run's output: for each pair, the fixture
   entry states the input spelling, and the block the run wrote for that entry prints the field name the row
   declares. The pin asserts all 15 pairs are grounded, and it runs `terraform validate` on the output the
   run wrote (skip when the terraform binary is absent, as the existing validate pins do). It states no
   hand-written list of pairs.
5. A pair that cannot be grounded — the provider refuses the combination in every entry shape — stays in
   `backlog.md` with the reason, and the pin states the grounded set as what the run read, so the count is
   the measurement, not an assumption.
6. The pins that already read the fixture stay honest with more than one entry per container: the parse mark
   pin, the emitter print pin, the choice pin, and the property grounding pin read the entries the fixture
   holds, not one entry per container. The scan scope, the row scope decision, and the writer scan are
   unchanged.
7. The goldens for the filter case are regenerated from a real run, and every other golden is unchanged.
8. `docs/ARCHITECTURE.md` §4.10 rule 3 states the grounding as the pin states it, and
   `docs/COVERAGE_MATRIX.md` keeps naming the entry each matrix row reads. `README.md` names the test that
   pins the map.
9. `ruff check .` is clean and `python3 -m pytest` passes. No test count appears in a document other than
   `agent-status.md`.
10. The commit message follows the `git log` style, uses ASD-STE100, and states which pairs are grounded and
   which are not. The tracking markdown is a second commit.

## Result

Met, and no pair is ungroundable. The fixture holds 11 entries, so all 15 pairs are stated by an entry:

- access-list: `ACL-Filter` states `ipv4-entry`, `ACL-Filter-v6` states `ipv6-entry`.
- as-path-access-list: `ASPath-Filter` states `aspath-entry`.
- prefix-list: `Prefix-Filter` states `ipv4-entry`, `Prefix-Filter-v6` states `ipv6-entry`.
- community-list: `Community-Filter` states `regular-entry` and `community`,
  `Community-Filter-Extended` states `extended-entry` and `ec-regex`,
  `Community-Filter-Large` states `large-entry` and `lc-regex`.
- redist-entry: `Redist-Filter-Set` states `aspath-prepend`, `extended-community`, `large-community` and
  `regular-community` in one `set`, which grounds the 4 redist pairs in one entry.

Criterion 2 holds for every entry the fixture adds: each choice level a new entry reaches states one key.
Criterion 3 holds: the run reports `Result: PASS (0 FAIL, 0 WARN)`, and `terraform validate` passes for the
3 unit directories the manifest names.

Pins: `tests/test_filter_containers.py`. The new pin
`test_the_run_prints_the_field_for_each_pair_the_fixture_states` reads the pairs through the map, the fixture
and the run, and validates the output the run wrote, so no pair is measured from the pango source alone; the
hand-written list of 5 grounded pairs is removed from
`test_the_path_keyed_exceptions_are_the_spellings_the_input_uses`. The map facts (15 pairs, 13 distinct
spellings, the `xml_name` results for the two containers that spell one idea two ways) are unchanged. The
scan scope, the row scope decision, the writer scan and the property grounding pins read the same rule with
more entries.

The goldens are regenerated from a real run, so `tests/golden/filter_containers/fw_template_00a08cdc/filters.tf`
is the only golden that changed. `ruff check .` is clean and `python3 -m pytest` passes 1462 tests.

Code commit: `244ddef`.
