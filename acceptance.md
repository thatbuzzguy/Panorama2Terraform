# Acceptance — Piece 4, the parse set reads what its rows state

Criteria set 2026-11-13 for `to-do.md` Piece 4, the parse-set findings `backlog.md` recorded on
2026-11-12. Each item states the rule, the module that owns it, the decision, and the test that pins it.
A pin measures content: it reads the parse object, the report, or the `.tf` bytes a run wrote, and no pin
reads the tracking markdown. A pin that fails on content is a finding recorded in `backlog.md`, not a pin
to relax.

Gate before commit: `ruff check .` clean, and the full `python3 -m pytest` with every pin passing and no
skips. Baseline before this piece: 1,651 pins, all pass, no skips, 334.6 s.

Every decision below was read against the code before it was written. Four decisions changed after measurement,
and each change is recorded where it happened: the four `member_list` corrections are dropped (item 5), the name
guard measurement covers both forms and the counts moved (item 2), the blind-side pin sits in
`tests/test_property_coverage.py` (item 1), and `static_routes` is grounded by the read record rather than by a
printed key (item 4).

## 1. `parse_interfaces` — the object holds the fields its row declares

Rule: `docs/COVERAGE_MATRIX.md` §1 — an interface row states the fields the output reads for an entry of
that kind, and the parse object holds those fields and the six identity facts, and nothing else.

Decision:

- `tag` is a declared field of every interface row, so the parse reads it for every entry kind: the entry's
  own `tag` element, or the `tag` inside the mode block for a virtual-wire or tap entry, because
  `_get_text` reads a direct child only. For an entry whose name already carries the unit (F3.3), the name
  is the tag the row states. One rule owns the field: `TerraformParser._interface_tag`.
- Both address shapes are the same field, so one rule reads both: a list field is the entry names under the
  element the field names, or the member texts under it. `parse_interfaces` read only the entry shape, so a
  member-form address was dropped. One rule owns the field: `TerraformParser._list_values`, the list form of
  `_get_single_value` (the value rule that already accepts both shapes). `_get_members` stays the member-only
  rule the other methods use, because migrating it would move the member-only containers the scan measures
  (`region/address`).
- `zone` and `virtual_router` are not interface fields and no output reads them: measured, the two keys are
  only ever assigned `None`, and nothing reads them. The provider models membership from the other side
  (`panos_zone.interfaces`, `panos_virtual_router.interfaces`), which `parse_zones` and `_parse_router` read,
  so the interface object carries no key for them: the two keys are removed.
- The scan's blind side is stated in `src/entry_coverage.py` §F4.4: `captured_fields` skips a field whose
  value is empty, so a declared field the parse stores empty is never a finding, and a field the parse never
  stored is not in the set at all. The pin measures both sides of that limit.

Measured, so two pins moved: the interface goldens hold only `.tf` files, and the emitter prints a `tag` line
only for a layer-3 subinterface type, so reading `tag` for every kind moves no golden. It moves the two pins
that read the report line's field list, because `tag` becomes a captured field for a physical entry and for a
nested-block entry: `tests/test_property_coverage.py::test_scan_scope_is_the_entries_a_matrix_row_covers` and
`test_the_nested_block_line_names_only_the_fields_the_emitter_reads` both now name `tag`. The nested-block pin
states the two sides: the emitter reads the field for every kind, so the record names it, and the block prints
it only for the kind whose type declares it. `CORPUS_FINDINGS` compares reads against the row's declared
properties, and every interface row already declares `tag`, so the read set cannot gain a property no row
states.

Removing the keys moves two pins that read them on the object:
`tests/test_parse_network.py::test_parse_ethernet_subinterface_units` reads `parent` for every entry the parse
returns, and `test_parse_virtual_wire_units` reads it for the nested-block entry. After the decision no key is
there for those kinds, so both now state the field set per kind: `parent` for a subinterface, no key for a
physical entry and for a nested-block entry.

Owner: `src/panorama_to_terraform.py::parse_interfaces`, `_interface_tag` and `_list_values`; the interface
rows of `src/resource_mapping.py::COVERAGE_MATRIX`; the blind-side statement in `src/entry_coverage.py` §F4.4.

Pins:

- `tests/test_interfaces.py::test_the_interface_object_holds_the_fields_its_row_declares` — for every
  interface row, content that states each field the row declares gives an object whose stored keys are
  exactly the row's properties plus `name` and the five scope facts. Fails before the change: `tag` is
  missing for a physical entry, `zone` and `virtual_router` are keys no row states.
- `tests/test_interfaces.py::test_a_list_field_is_read_in_both_export_shapes` — content that states the
  member form gives the addresses; the entry form still gives them. Fails before the change.
- `tests/test_property_coverage.py::test_the_scan_cannot_see_a_field_the_parse_stored_empty` — the blind side
  measured: a field stored empty gives no finding, and a field the parse never stored is not in the set. The
  module name `src/entry_coverage.py` §F4.4 states for the rule is this one, so the pin sits there; these
  criteria first named `tests/test_entry_coverage.py`, which is one of the three changes measurement made.

## 2. A name guard records the entry it reads

Rule: `src/entry_coverage.py` §F4.3 (`RULE_PARAGRAPH`) — one line per config entry the parse pipeline read,
and `GAP_RULE` — an entry with no name is recorded. A name guard that skips an entry without a record breaks
both.

Decision: every name guard in a parse method calls `mark_skipped` at the place it decides to skip, so the
entry has a record. Measured against the code through `ast`, the audit's 11 guards are the negative form
(`if not name: continue`); the same rule also covers the positive form (`if name:`, `if entry.get('name'):`),
where the missing-name branch is the `else`. The definition counts 69 guards in the parse set, 68 of them
recording, and it reads both forms, so the positive-form guards join this item. Before the change the same
definition measured 77 guards and 47 records: 30 unrecorded, 11 in the negative form and 19 in the positive
form. `_list_names` is the one exception: its name can come from a `member` child, which is not an entry, and
it marks every `entry` child before the guard, so a nameless entry there still has a record. The audit's
"47 of 58" is the negative-form subset: 58 negative-form guards, 11 of them without a record.

A nameless entry inside a config-object entry is a property level (§3.2), so the report prints no line of its
own: the record is its report, and the parent row counts it as a property entry. A nameless entry whose
container is a section does print a line. The pin measures both.

Owner: the parse methods that hold the guards.

Pins:

- `tests/test_entry_coverage.py::test_every_name_guard_records_the_entry_it_reads` — reads the parse methods
  through `ast` and asserts that each entry name guard calls `mark_skipped` on the branch that skips, with the
  one exception and the reason it is honest. Fails before the change for the 30 unrecorded guards.
- `tests/test_entry_coverage.py::test_a_nameless_entry_reaches_the_record_and_the_report` — content with one
  section-level nameless entry and one nameless entry inside a config-object entry: the first gives a report
  line, the second gives a record and is counted on the parent row, and the run writes its `.tf` file. Fails
  before the change.

## 3. `parse_schedules` skips a nameless recurring child through the record

Rule: the same §F4.3 rule; the writer rule `docs/ARCHITECTURE.md` §5 — the report joins the name it prints,
so a name the parse stored as `None` raises and leaves half-written output.

Decision: `parse_schedules` reads the recurring child name through the record, so a child with no name is
`mark_skipped` and never enters the set the report joins.

Measured, so the pin shape changed: a recurring child sits inside the schedule entry, so it is a property
level and the report prints no line for it. The pin measures the record, the parent row's property count, and
the file set, not a report line.

Owner: `src/panorama_to_terraform.py::parse_schedules`.

Pin: `tests/test_property_coverage.py::test_a_nameless_recurring_child_reaches_the_record_and_not_the_join` —
content with a nameless recurring child: the run completes, the record names the child as skipped with the
reason, the schedule row counts it as a property entry, and the report joins the names it kept. Fails before
the change with `TypeError`, exit 1, and only `provider.tf` written.

## 4. `_parse_router` states the shape limit and records what it cannot model

Rule: `docs/ARCHITECTURE.md` §4.9 — `PROTOCOL_SHAPE` states one row per level of `protocol`, and no method
reads a level the table does not state. The virtual-router row covers only the entry shape it names.

Decision: the parse keeps reading only the shape the row states (`routing-table/ip/static-route/entry`), so an
entry the export states under `protocol/static-routes` is not modeled. The parse records each such entry
through `mark_skipped`, naming the level the table states no row for, and the virtual-router row states the
limit in its comment.

Measured: the provider declares `panos_virtual_router.protocol` with `bgp`, `ospf`, `ospfv3`, `rip`,
`redist_profile` and `redist_profile_ipv6` only — no `static_routes` — so `protocol/static-routes` is
legitimately a level the table states no row for, and the `static_routes` in the virtual-router row is grounded
by the read record: `generate_virtual_routers` reads the key and prints one resource block per entry, so no
golden prints it as a field of the router block. A pin cannot read a comment, so the row's limit is measured
through the record: the reason names the level, and the table states no row for it. A nameless entry inside
the router entry is a property level, so it has no report line of its own; the record is its report.

Owner: `src/panorama_to_terraform.py::_parse_router`; the `panos_virtual_router` row of
`src/resource_mapping.py::COVERAGE_MATRIX` (the limit) and the static-route row.

Pins:

- `tests/test_protocol_object.py::test_the_shape_table_states_no_row_for_the_level_the_router_records` — the
  recorded level is a level `PROTOCOL_SHAPE` states no row for, and the two paths the router row owns are the
  row's own shape plus the key the emitter prints.
- `tests/test_entry_coverage.py::test_an_entry_at_a_level_the_table_states_no_row_is_recorded` — content with
  a `protocol/static-routes` entry: the record names the entry as skipped with the level the table does not
  state, the parent row counts it as a property entry, and the `.tf` bytes the run wrote hold no block for it.
  Fails before the change: no record and no property entry.

## 5. `_protocol_field` reads a number as the shape states it

Rule: `docs/ARCHITECTURE.md` §4.9 value rule — a shape reads the value the row states, and the reader's
inverse `src/sanity_checks.py::value_shape` reads each shape word back.

Decision:

- The `number` shape reads a signed integer, so `set-med -1` prints. `text.isdigit()` read an unsigned value
  only, so a negative number was dropped. `value_shape` reads a signed integer as `number`, because the gate
  compares the printed value against the shape word, and a printed `-1` read as `''` would report
  "is not a number value".
- The single-match limit is stated as the limit of the value rule: `find` answers one element, so a field the
  provider declares as `['list', 'string']` must be a `member_list` row. Measured against the live provider
  schema (Terraform 1.16.2, `PaloAltoNetworks/panos ~> 2.0.14`), the four rows the audit named
  (`peer_group/peer/local_address.interface`, `aggregation/address/aggregate_route_attributes.nexthop`,
  `export/rules/action/allow/update.nexthop`, `import/rules/action/allow/update.nexthop`) are all `string`,
  not `['list', 'string']`. **The four `member_list` corrections are dropped**: they contradict the
  measurement, and they would break
  `tests/test_protocol_object.py::test_the_shape_table_is_the_measured_provider_shape`, which already pins
  every row field against the schema. No new pin is added for the single-match limit, because that pin is the
  existing one; the limit is stated in the value rule.
- A `number` text the rule cannot read keeps no value, so the field prints nothing and the gate sees no field
  to check. F2.9's mechanism for an unreadable value is a `# NOTE:` line inside the block, but the protocol
  emitter prints dict keys, so a note cannot be a key, and the mark mechanism records detail per entry while
  `_protocol_field` returns only a value. This stays open in `backlog.md` with owner `_protocol_field`, and the
  pin measures only the signed-integer reading.

Owner: `src/panorama_to_terraform.py::_protocol_field`, the value rule's limit statement, and
`src/sanity_checks.py::value_shape`.

Pins:

- `tests/test_protocol_object.py::test_value_shape_is_the_reader_inverse_for_every_shape_word` — extended with
  the signed number sample, so the inverse reads `-1` back as `number`. Fails before the change.
- `tests/test_protocol_object.py::test_a_number_field_prints_the_signed_integer_the_shape_states` — content
  with `set-med -1` prints `set_med = -1` in the block the run wrote. Fails before the change: the field
  printed nothing.

## Measurement

Gate run 2026-11-13, after the changes: `ruff check .` clean, `python3 -m pytest` 1,659 pins passed, no skips,
270.21 s. Baseline before this piece: 1,651 pins, all pass, no skips, 334.6 s. Eight pins added, none removed,
none weakened.

Counts by module: `tests/test_interfaces.py` 8 → 10, `tests/test_entry_coverage.py` 29 → 32,
`tests/test_property_coverage.py` 31 → 33, `tests/test_protocol_object.py` 45 → 46. `tests/test_parse_network.py`
holds 24 pins before and after; two of them changed what they assert.

Item 1: the field-set pin measures, for each of the eight interface rows, an entry whose content states every
field the row declares, and the stored keys equal the row's properties plus `name` and the five scope facts — so
`tag` is present for a physical entry and `zone` and `virtual_router` are absent. The list pin measures an
aggregate-ethernet entry that states the member shape and gives both addresses, and the entry shape still gives
them; the pin reads `network/interface/aggregate-ethernet/entry/layer3/units`, the row the scan measures. The
blind-side pin measures `tests/fixtures/tags.xml` entry `web`: `color` kept with a value, `comments` and
`disable_override` stored empty, `description` never stored, `captured_fields` = `('color',)`, the read record
naming all four, and the finding set empty; the contrast entry `service_groups.xml` `Web-Services` keeps
`description` with a value no output read and is a finding. Gate: pass.

Item 2: the guard pin measures the parse set through `ast` — 69 guards, 68 record, `_list_names` the one
exception and the pin also measures why it is honest. Before the change the same definition measured 77 guards
and 47 records. The content pin measures a nameless entry at the `tag` section level and one inside an address
entry: the first prints `  line    6  tag/(no name) ... skipped      panos_administrative_tag - entry has no name
attribute captured: name only`, the second prints no line and is counted as `property entries: 1` on the parent
row, and the run writes one tag resource. Gate: pass. Before the change neither entry had a record.

Item 3: the pin measures the record (`skipped`, `entry has no name attribute`), the parent row count
(`property entries: 2`), the join (`entries=Monday`), and the file set (`.tf` holds `provider.tf` and
`variables.tf` only), with no finding and exit 0. Before the change the content raised `TypeError` and wrote
only `provider.tf`. Gate: pass.

Item 4: the schema pin measures `panos_virtual_router.protocol` as the six levels `PROTOCOL_SHAPE` states rows
for and no `static_routes`, `protocol_row('protocol/static-routes')` as None, and the read record on
`virtual_routers.xml` entry `default` naming `protocol` and `static_routes`, with no golden printing the key as
a field. The record half measures a `protocol/static-routes` entry as `skipped` with
`no row states the protocol/static-routes level`, `property entries: 1` on the router row, and no
`panos_virtual_router_static_route` block in the bytes the run wrote. Gate: pass.

Item 5: `value_shape('-1') == 'number'` and `value_shape('-') == ''`; content with `set-med -1` prints
`set_med = -1`, the gate reports no finding, exit 0. Before the change the block printed no `set_med` line.
Gate: pass.

Open after this piece: the unreadable number text, recorded in `backlog.md` with owner `_protocol_field`.

