# F7.12 — acceptance criteria

F7.12 decides how `PROTOCOL_SHAPE` states a level the provider reads as an exactly-one choice between two of
its attributes, so the gate rule `protocol_object` refuses a hand-written block that states both alternatives
and still prints one alternative for a run that states one.

The two levels are the two F7.11 recorded:

- `protocol/ospfv3/auth_profile`: an entry states `ah` or `esp`; the row states them as fields and no choice.
- `protocol/bgp/peer_group/peer/peer_address`: a level states `ip` or `fqdn`; the row states them as fields and
  no choice.

Measure source: the pinned provider (2.0.14) through `conftest.py::provider_schemas` for the schema facts, and
`terraform validate` (Terraform 1.16.2) for what the provider reads. Both levels are measured before the
decision, so the decision comes from the measurement and not from one case.

## The measurement, both cases

Measured 2026-11-03 against provider 2.0.14 (Terraform 1.16.2):

| Level | What the schema declares | What `terraform validate` reads |
|---|---|---|
| `protocol/ospfv3/auth_profile` entry | `name` (required), `spi`, `ah` (`single`), `esp` (`single`); every one optional | `ah` and `esp` together: "2 attributes specified when one (and only one) of [...auth_profile[0].ah.&lt;.&gt;] is required". Neither: "No attribute specified when one (and only one) of [...] is required". |
| `protocol/bgp/peer_group/peer/peer_address` | `fqdn` (string, optional), `ip` (string, optional) | `ip` and `fqdn` together: "2 attributes specified when one (and only one) of [...peer_address.ip.&lt;.&gt;] is required". Neither: the same message. |

The schema states no word for the choice: every alternative is an optional attribute of a `single` level, so the
reader reads both levels as an object value and `SHAPE_TO_SCHEMA` reads both as `single`. The choice is what the
provider enforces at validate time.

## The decision

**No new shape word. `selects` is the one place the table states the choice, and the gate's choice rule reads
`selects` at every level or entry the walk enters.**

1. A word cannot carry this. `SHAPE_WORDS` is the set of shapes the field reader reads back
   (`sanity_checks.value_shape` is the reader's own inverse), and `SHAPE_TO_SCHEMA` pins each word to one fact the
   provider declares. Measured, the fact for both levels is `single` with optional attributes, which is the fact
   `object` and `one_of` already state. A word for the choice would name no schema fact, so it would be a second
   owner for the same fact.
2. One rule covers both cases. A row that states `selects` names the attributes that form the choice, and the
   level or the entry states exactly one of them. The two cases are the same rule: the choice is the whole value
   for `peer_address`, where `selects` names every attribute the provider declares for the level, and the choice
   is part of the value for `auth_profile`, where the entry also states `name` and `spi`. The walk already reads
   both shapes, so the rule is stated once and called at the level and at each entry.
3. `one_of` keeps its meaning: the word for a row whose whole value is the choice, which is the row that states
   the choice and no other fields. A row that states other fields keeps the word the measurement gives it
   (`object` for `peer_address`, `string_list` for the profile entry) and states the choice in `selects`. The
   choice rule reads `selects`, not the word, so no word changes: `SHAPE_WORDS`, `SHAPE_TO_SCHEMA`,
   `SHAPE_READS_AS` and `SHAPE_LEVELS` stay as they are, so no new word needs reading at the print site, by the
   gate, or by the pin.
4. The rows state the choice as the identity, because the export spells the provider key there: the entry names
   the alternative by presence, and the value it states is the key the block prints. So no mapping value differs
   from its key, and `selects` gains the two rows with no new spelling rule.

## The gate finding

Rule 2 is the choice rule, with one wording for the count and the existing wording for a key the row does not
select:

- `protocol {address} {path} states {n} keys, which is not the one key PROTOCOL_SHAPE selects` — `n` is the
  number of selected keys the level or entry states, so the same wording covers 0 and 2 for both shapes. This
  replaces `which a one_of level cannot`.
- `protocol {address} {path} key {key} is not a key PROTOCOL_SHAPE selects` — stays for a `one_of` level, where
  every key the value states is a key the row selects. For a level that states the choice among its other
  fields, an extra key is read by the field rule against the row, so the choice rule counts only the keys it
  selects.

The choice rule is read at the level the walk enters and at each entry inside a `string_list` row, so the entry
of `auth_profile` is read against its own row.

## The print path

The emitter is unchanged and pinned. It prints one alternative when the export states one, because
`_protocol_fields` prints the fields the value holds, and the parse reads one field for the two levels:
`tests/fixtures/auth_profile.xml` states `ah` in one entry and `esp` in another, and `tests/fixtures/bgp.xml`
states one attribute for `peer_address`, so both runs print one key and report nothing. The gate reads the same
blocks with no finding.

## Criteria

1. **One choice owner.** `selects` is the only place a row states a choice, and the two rows gained it:
   `protocol/ospfv3/auth_profile` (`ah`, `esp`) and `protocol/bgp/peer_group/peer/peer_address` (`ip`, `fqdn`).
   No shape word, no name list and no gate branch states a choice, so
   `test_the_table_is_the_only_shape_owner` still passes with the new gate helper registered.
2. **The pin reads the choice as the measurement states it.** For every row that states `selects`, each selected
   key is an attribute the provider declares for that level, and each is the field the row states or the row the
   table states for it. The pin no longer asserts that `selects` names every attribute, because `name` and `spi`
   are attributes of the profile entry that are not alternatives. The two rows are pinned by name as the choice
   the provider reads, and the row for `peer_address` is the case where the choice covers every attribute the
   provider declares for it.
3. **The gate refuses both alternatives.** A hand-written block that states `ip` and `fqdn` for `peer_address`,
   and an entry that states `ah` and `esp` for `auth_profile`, is one FAIL finding each. A level or entry that
   states none of the alternatives is the same finding, because the provider requires one. A level or entry that
   states one alternative is not a finding. The pin that recorded the limit
   (`test_the_gate_reads_a_peer_against_the_rows_it_states`) moves to a violation pin.
4. **The print path still prints one alternative.** The run on `tests/fixtures/bgp.xml` and
   `tests/fixtures/auth_profile.xml` prints the one key the export states, and the gate reads the blocks it wrote
   with no finding. A corpus run reports `PASS (0 FAIL, 0 WARN)`.
5. **Goldens move only from a real run.** No golden is expected to move, because no fixture states both
   alternatives.
6. **The pins.** `ruff check .` and `python3 -m pytest` pass. `docs/ARCHITECTURE.md` §4.9 rule 7 records the
   choice rule, and the tracking markdown records the decision.
