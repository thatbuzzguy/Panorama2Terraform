# F7.13 — acceptance criteria

F7.13 closes the asymmetry F7.12 recorded: `FILTER_SHAPE` states no `selects`, so the choice rule reads no
choice for a filter block, even though the provider reads some filter levels as exactly one attribute. The work
takes the rule that covers both tables, so the gate refuses a hand-written filter block that states both
alternatives and still prints one alternative for a run that states one.

Measure source: `conftest.py::provider_schemas` for the attribute facts, and `terraform validate`
(Terraform 1.16.2, provider 2.0.14) for what the provider reads as exactly one. Measured 2026-11-03 for every
row of `FILTER_SHAPE`, so the decision comes from the measurement of the whole table and not from the three
rows F7.8 recorded.

## The measurement

The schema states no fact for a choice: it declares every alternative as an optional attribute of a `single`
level, so the choice is what `terraform validate` enforces. Measured 2026-11-03, the filter levels that refuse
more than one attribute and also refuse none are these 14 rows. Each row is written as the table names it, and
the alternatives are the fields the row states that form the choice.

| Row | What the provider reads as exactly one |
|---|---|
| `access-list/type` | `ipv4`, `ipv6` |
| `access-list/type/ipv4/ipv4_entries/destination_address` | `address`, `entry` |
| `access-list/type/ipv4/ipv4_entries/source_address` | `address`, `entry` |
| `access-list/type/ipv6/ipv6_entries/source_address` | `address`, `entry` |
| `community-list/type` | `extended`, `large`, `regular` |
| `prefix-list/type` | `ipv4`, `ipv6` |
| `prefix-list/type/ipv4/ipv4_entries/prefix` | `entry`, `network` |
| `prefix-list/type/ipv6/ipv6_entries/prefix` | `entry`, `network` |
| `route-maps/redistribution/redist-entry` | `bgp`, `connected_static`, `ospf`, `ospfv3`, `rip` |
| `route-maps/redistribution/redist-entry/bgp` | `ospf`, `ospfv3`, `rib`, `rip` |
| `route-maps/redistribution/redist-entry/connected_static` | `bgp`, `ospf`, `ospfv3`, `rib`, `rip` |
| `route-maps/redistribution/redist-entry/ospf` | `bgp`, `rib`, `rip` |
| `route-maps/redistribution/redist-entry/ospfv3` | `bgp`, `rib` |
| `route-maps/redistribution/redist-entry/rip` | `bgp`, `ospf`, `rib` |

The three rows F7.8 recorded are in that set, and the other 11 carry the same fact. The redist entry row is the
filter case where the choice is part of the value: the row also states `name` and `description`, which are not
alternatives. Every other choice row states only its alternatives, so the choice is the whole value there. No
other filter row is a choice level, and no filter field is marked `sensitive`.

## The decision

**One rule for both tables: `selects` is the one place either table states a choice, so the 14 filter rows the
measurement names state it there, and the gate reads it at the level or the entry the walk enters.**

1. A rule that reads "a choice stated as fields" cannot be stated, because the schema has no word for a choice:
   every alternative is an optional attribute of a `single` level. The rule would need to say which fields form
   the choice, which is a second place that states it. So the choice stays data in the row, and `selects` stays
   the one place that holds it. The three rows, and the 11 that carry the same fact, state it.
2. No shape word changes. `SHAPE_WORDS`, `SHAPE_TO_SCHEMA`, `SHAPE_READS_AS` and `SHAPE_LEVELS` stay as they
   are, so `value_shape` still reads each choice level as an object value, and `one_of` keeps its meaning: the
   word for a row whose whole value is the choice.
   A filter row keeps the word the measurement gives it (`object`) and states the choice in `selects`.
3. The choice is the identity, because the export spells the provider key at a filter choice level, so
   `selects` gains no new spelling rule and `FILTER_XML_NAME_EXCEPTIONS` is unchanged.
4. The gate reads the choice at every level the walk enters, and for a filter block the block's own level is the
   entry row the walk enters, so `check_filter_blocks` reads the choice at the block's own level, at each entry
   of a `string_list` row, and at each level below. One helper (`sanity_checks._shape_choice_findings`) serves
   both tables, so one wording covers both.

## The gate finding

The finding wording is the one F7.12 states for the count, read through the table object, so it names the filter
table for a filter block:

- `filter {address} {path} states {n} keys, which is not the one key FILTER_SHAPE selects` — `n` is the number
  of selected keys the level, the entry, or the block states, so the same wording covers 0 and more than one.

The wording for a key a row does not select stays for a `one_of` level, which no filter row is.

## The print path

The emitter is unchanged. It prints one alternative when the export states one, because the parse reads the
fields the entry states, and the fixture answers each choice level with one element. The corpus run
(`tests/fixtures/filter_containers.xml`) trips no finding, and reports `PASS (0 FAIL, 0 WARN)`. No golden moves.

## Criteria

1. **The rule, not a name list.** `selects` is the only place either table states a choice. The filter rows that
   state it are the 14 the measurement names, and no module, gate branch or document names one of the three by
   path as an exception.
2. **The pin reads the choice as the measurement states it.** For every filter row that states `selects`, each
   selected key is an optional attribute the provider declares for that level, and each is a field the row
   states, so the choice is the whole value or part of it. A row that states no choice states no `selects`, and
   `sensitive` stays empty for every row.
3. **The gate refuses both alternatives.** For each of the three levels F7.8 recorded, and for every filter row
   that states `selects`, a hand-written block that states two alternatives is one FAIL finding, and a level or
   entry that states none is the same finding. A block that states one alternative is not a finding.
4. **The print path still prints one alternative.** The run on `tests/fixtures/filter_containers.xml` prints the
   one key the export states at each choice level, and the gate reads the blocks it wrote with no finding. The
   corpus run reports `PASS (0 FAIL, 0 WARN)`.
5. **Goldens move only from a real run.** No golden is expected to move, because no fixture states both
   alternatives, so the fixture is not extended for this slice.
6. **The pins.** `ruff check .` and `python3 -m pytest` pass. `docs/ARCHITECTURE.md` §4.10 rule 1 records the
   rule for the filter table, `README.md` names the choice in the `filter_blocks` rule, and the tracking
   markdown records the decision.
