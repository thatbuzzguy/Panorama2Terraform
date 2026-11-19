# Acceptance — the iterated block (Epic 9, Piece 19, Phase 9C)

Criteria set 2026-11-19 for Piece 19: the four rule generators print one `for_each` resource block per rule type
per unit instead of one block per rule entry. This piece carries its own criteria for the F2.5 order rule, because
the order fact moves from `depends_on` to the key order (Epic 9 decision 4). The gate rule that reads the iterated
block is Piece 20; this piece states the shape Piece 20 reads and adds no gate rule of its own. Piece 21
re-measures the goldens as a whole; the goldens this piece moves are the ones that name the printed rule output.

Owners this piece reads and does not restate: the row shape through `rule_data.RULE_ROW_FIELDS`; the key, the
ordinal width and the chain grouping through `rule_data`; the one file-name stem through the coverage matrix row's
`output_file`, read through `rule_data` (`data_file`, `printed_file`, and the map name `locals_name`); the field
order through the matrix row's `properties` (table order); the name field through `entry_coverage.name_field`; the
location through `LOCATION_SCHEMA`; the value-to-variable shape through `resource_mapping.VALUE_VARIABLES`; the
naming rule through `naming.py`; the unit join through `unit_manifest`; the writer through `write_path.py`.

## The rules this piece states

1. **One block per rule type per unit.** The block is written in the file the matrix row names. The block's local
   name and the map name are the one stem the row names, so the block, the map, the `.json` form and the `.csv`
   form read one name and no second naming rule appears.
2. **The `locals` map is the printed form of the unit's rows.** One entry per rule row for that unit, keyed by the
   row `key`, printed in sorted key order, which is the XML order inside a chain. The entry states the name field
   first (`entry_coverage.name_field`) and then the fields the rule type prints, in the table order the row
   declares. A field the recorded object holds with no value prints `null`, because one field list serves every
   instance; the data record keeps the rule that such a field prints no column, so the printed form is compared
   against the data read through `parse_rows` field by field, and the fields it states as `null` are exactly the
   declared fields the recorded object holds with no value.
3. **The block prints the reference into the map, never a value.** `for_each` reads the map, and every row field
   in the block body prints as `each.value.<field>`, under the name the provider declares for that field. The map
   is the only place the file states a row value, so the rule that a block prints the variable reference, never the
   value, is not broken: the value sits in one place, the printed form of the rows, and the block reads it by
   reference, the way the `.tfvars` is the printed form of the site record. For a field `VALUE_VARIABLES` maps to a
   variable the map states `var.<name>`, so no `.tf` file states a value for it, and the block still prints the
   reference.
   - Measured 2026-11-19 against the pinned provider schema: `rules = [ each.value ]` is refused, because the
     provider marks `rules[0].name` required and cannot read it through a dynamically-typed `each.value`
     (`Value Conversion Error … Target Type: provider.SecurityPolicyRulesResourceRulesObject`). So the block body
     names the fields. Measured in the same harness: the enumerated body with `each.value.<field>`, a reference in
     the map entry, and a map entry that states `null` validates.
   - The two shape words the emitter states are not row values: the `position` anchor, and the NAT family word the
     export states no value for. `pivot` stays a row column the block does not read.
4. **Reference columns record whether a name resolved inside the unit, read through `name_ref`.** A reference
   column prints the name the naming rule answered: the reference for a name the referrer's own unit declares, the
   plain name otherwise. One iterated block prints one body for every instance, so the resolution is recorded in the
   map entry and not in the block body, and the provider reads the name either way. The emitter applies the one
   naming rule at the map site and states no second rule.
5. **`position` prints `where = "last"`, and `depends_on` drops.** Instances inside one block create in key order,
   and the key order is the XML order inside a chain, so the apply order comes from the key and not from a
   per-instance pivot. `pivot` stays a row column of the record; the block does not read it.
6. **The F2.5 rule, retargeted.** `tests/test_policy_order.py` pins that apply order equals XML order through the
   key order: one block per rule type per unit, the key ordinals run 1..N inside a chain in XML order, the sorted
   key order equals the XML order, and a chain never crosses a unit, because the chain group (device group, vsys) is
   two of the five unit facts and the row's `directory` is the join. These are the criteria own to this piece, and
   the shared rule-block parser and chain check in `tests/conftest.py` read the block shape.
7. **The pins that name the printed rule output move with the shape**, and each still measures content: the pins
   named in the Pins section below.
8. **No second reader, naming rule, writer, console line, or environment name.** The emitter reads the field order,
   the name field, the location and the variable shape through the tables that own them, prints through
   `hcl_value`, and writes through `write_path.py`. The module that owns the row shape gains one name read through
   the same stem rule (`locals_name`) and states no other rule.

## Field name and shape exceptions the entry states

The entry prints each field as the provider's `rules` object declares it, because `each.value.<field>` is
dynamically typed and `terraform validate` cannot type-check it, so a shape mismatch shows only at apply. So
`RULE_ENTRY_FIELDS` is one table of `row field -> (provider field name, shape word)`, read through the matrix row's
field order and through `SHAPE_WORDS` and `SHAPE_TO_SCHEMA`, and `RULE_ENTRY_READERS` names the reader for a field
whose provider object key is the value the row records. The shape word is the provider's declared type, measured from
the pinned provider schema on 2026-11-19: every reference column is a list, `disabled` and the two log flags are
booleans, `description`, `action`, `profile`, `log_setting` and `schedule` are one string, NAT `service` is one
string, and `profile_setting`, `source_translation`, `destination_translation`, decryption `type`, PBF `action` and
`enforce_symmetric_return` are objects or one_of. `destination_zone` is the one row field the parse records as one
value, through `xml_input._get_text`, while the provider declares `['list','string']`, so the entry prints the
one-member list. A `panos_nat_policy_rules` `service` member list is the one field the provider cannot take as the
row's value, so the entry states the field as `null` and the file states the members in the `# NOTE:` line: a value
is printed or reported, never dropped. The `# NOTE:` lines print inside the entry, before the field line they
explain, so the printer prints entry fields line by line rather than one `hcl_value` call per entry.

## What Piece 20 reads

The block rule Piece 20 states can be stated from this piece as a gate rule: for each rule type, the block's local
name and the `for_each` map name are `rule_data.locals_name`, the block's `location` equals the `LOCATION_SCHEMA`
row for the type, its field list is the name field plus the table order the matrix row declares, every field in the
block body is `each.value.<field>` with the provider name `RULE_ENTRY_FIELDS` states, one block per rule type per
unit, and the map entry keyed by the row `key` holds the values the row names when read through `parse_rows`, with
the entry field printed as the shape word the same table states. The `data_files` rule reads the rule rows through
`RULE_ROW_FIELDS` and joins on `directory`. The cross-check rule is Piece 19's own retarget, not Piece 20's: for the
four rule rows its block side is the entry keys the printed map holds for the unit, read through
`rule_data.printed_keys`, so the gate states no reader for the map and the rule-type set is read through
`import_blocks.rule_types()`.

## Pins

Retargeted, in the order the rules above state them:

- `tests/conftest.py`: the shared rule-block parser reads one block per rule type per unit — the block's local
  name, the unit it belongs to, the map entries in printed key order, and the `for_each` reference; the chain check
  reads the key order, the ordinals, and the no-crossing rule through the row join. `depends_on` and `pivot` are no
  longer part of what the parser answers.
- `tests/test_policy_order.py` (8 pins, retargeted): the block set, the key order inside each chain, the ordinals,
  the goldens read through the same parser.
- `tests/test_real_or_report.py` (5 pins): the block plus the map entries for the decryption and PBF bodies.
- `tests/test_edge_cases.py`: the rule chain pins read the shared parser; the assignment pin reads the key's digest
  half through `rule_data.identity_key`.
- `tests/test_dependency_wiring.py`: the rule reference pins read the map entry.
- `tests/test_coverage_matrix.py`: the name pin for the four rule rows reads the name through the map entry keyed by
  the row key, and the emitter grounding for the four rule rows reads the row's field set through `rule_data`.
- `tests/test_round_trip.py` (34 pins): the cross-check's block side for the four rule rows is the entry keys the
  printed map holds, read through `rule_data.printed_keys`, so the corpus table no longer names a rule row; the
  sample run's resource count moves to the measurement recorded below, and the count fact's second number is now the
  blocks read or the entries printed in the map, so `COUNTS_RE` stops at the number.
- Extended, in `tests/test_rule_data.py`: the map name is the same stem as the two file forms, and the printed map
  agrees with the rows the run wrote for that unit, read through `parse_rows`.

No test module imports another test module, and no test calls a network.

## Indexes and measurement the piece moves

- `README.md` §Testing names the modules above with the pins this piece retargets or adds.
- `docs/ARCHITECTURE.md` §1's row for `rule_data.py`: the rule column gains the map name read through the same stem.
- `docs/CODEBASE_ASSEMBLY.md` §14 names the map as the printed form of the unit's rows, compared and not counted.
- `docs/USAGE_GUIDE.md` names the rule output as one iterated block per rule type per unit.
- The goldens that name the printed rule output move, from a real run, in this piece's commit.

## Gate

`ruff check .`, `ruff format --check .`, `python3 tools/check_documents.py`, `python3 -m pytest`, in that
order, conservative threads, single process.

Before, measured 2026-11-19 on the committed tree at `eda2d1a`: `ruff check .` clean at `py310`,
`ruff format --check .` clean on the 102 Python files, 1,708 pins in 53 test modules — all pass, with the same
4 skip for the missing `tflint` binary — and `python3 tools/check_documents.py` reports no finding. Per module for
the modules this piece touches: `tests/test_rule_data.py` 10, `tests/test_policy_order.py` 8,
`tests/test_real_or_report.py` 5, `tests/test_round_trip.py` 34, `tests/test_coverage_matrix.py` 211,
`tests/test_property_coverage.py` 33, `tests/test_golden_files.py` 91, `tests/test_dependency_wiring.py` 11,
`tests/test_edge_cases.py` 19, `tests/test_import_blocks.py` 32, `tests/test_sanity_gate.py` 110.

After, measured 2026-11-19 on the final tree: `ruff check .` clean at `py310`, `ruff format --check .` clean on the
102 Python files, 1,709 pins in 53 test modules — 1,705 pass, with the same 4 skip for the missing `tflint` binary —
and `python3 tools/check_documents.py` reports no finding. The one added pin is
`tests/test_rule_data.py::test_the_printed_map_reads_back_as_the_same_row_keys`, which measures the third form
reading back as the rows it was built from; no pin was weakened, and every retargeted pin still measures content.

Per module for the modules this piece touched: `tests/test_rule_data.py` 11 (10 before), `tests/test_policy_order.py`
8, `tests/test_real_or_report.py` 5, `tests/test_round_trip.py` 34, `tests/test_coverage_matrix.py` 211,
`tests/test_property_coverage.py` 33, `tests/test_golden_files.py` 91, `tests/test_dependency_wiring.py` 11,
`tests/test_edge_cases.py` 19, `tests/test_import_blocks.py` 32, `tests/test_sanity_gate.py` 110,
`tests/test_data_file_gate.py` 21.

Measurement the retargeted pins state: the sample run's resource count is 17 (20 before), because each rule file
prints one block: the sample fixture's 2 nat entries and 3 security entries become 2 blocks, a drop of 3. The
kitchen-sink run prints 4 blocks, one per rule type, reading 7 map entries (2 nat, 2 security, 1 decryption,
2 pbf). The cross-check reports no finding for the four rule rows on any corpus fixture, so the corpus table in
`tests/test_round_trip.py` names no rule row and the corpus fact count stays 19 on 8 fixtures, 3 + 15 + 1 by
category.
