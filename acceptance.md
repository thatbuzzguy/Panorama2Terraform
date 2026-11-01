# Acceptance criteria — F7.1: the protocol object as output

Feature record: `PLAN.md` Epic 7. The emitter is `TerraformGenerator.generate_virtual_routers`, the
parse methods are `parse_bgp` and `parse_ospf`, the shape table is `resource_mapping.PROTOCOL_SHAPE`,
and the gate rule is `sanity_checks.check_protocol_object`. The tests are
`tests/test_protocol_object.py`, with the pinned sets in `tests/test_container_coverage.py`,
`tests/test_property_coverage.py`, `tests/test_coverage_matrix.py`, `tests/test_reports.py` and
`tests/test_parse_network.py`.

Facts measured 2026-10-31 against provider 2.0.14 (`terraform providers schema -json`, saved at
`/tmp/opencode/panos_schema/schema.json`): `panos_virtual_router.protocol` is an object attribute with
`nesting_mode` single; `bgp` and `ospf` are single; `peer_group`, `peer`, `redist_rules`, `area`,
`range`, `interface`, `auth_profile`, `md5` are lists; `peer_group.type`, `area.type` and
`area.interface.link_type` are single one-of objects; `ospf.auth_profile.md5.key`,
`ospf.auth_profile.password` and `bgp.auth_profile.secret` are `sensitive`; `metric` is a number.
`ospf.area.type.normal` has no attributes, so a one-of key can state nothing. `terraform validate`
accepts `protocol = { ... }` and refuses `protocol { ... }`. The provider requires exactly one of
`advertise` or `suppress` on a `range` element.

## Decisions

### 1. The print shape: an object value, not a block

- `protocol` prints as one field of the `panos_virtual_router` block: `protocol = { ... }`. A block
  shape (`protocol { ... }`) is refused by the provider, so the gate rule reports a `protocol` the
  field reader cannot read as a field.
- One level of the object is one nesting level of the table row: a `single` level prints as an object,
  a `list` level prints as one object per element, a `one_of` level prints as the one chosen key.
- The entry name inside a list element prints as the `name` field, the same rule
  `entry_coverage.name_field` states for `panos_virtual_router`.
- Field order is the table order, and `hcl_value` is the only printer, so two runs on the same bytes
  write the same bytes.
- A value the parse captured with no value prints nothing. A field the table declares `number` prints
  as a number when the value is one.

### 2. One table states the shape of the protocol object

`resource_mapping.PROTOCOL_SHAPE` is the one table. One row states the provider path, the nesting mode
(`single`, `list`, `one_of`) or the leaf shape (`string`, `bool`, `number`), the fields the level
declares, the report value that selects a `one_of` key, and the `sensitive` flag. `SHAPE_WORDS` is the
word list the table uses, and `block` is one of the words: a `block` field is a `single` level that
declares no attributes, so the reader prints `{}` for it when the export states it and prints nothing
when the export does not. `WORD_TO_SCHEMA` is the one mapping from a table word to the schema word the
test pins. The emitter reads the table to print, the gate reads it to check, and
`tests/test_protocol_object.py` pins every row against the live provider schema the way
`DATA_SOURCE_SCHEMA` is pinned.

The table states the provider spelling. `PanoramaParser._protocol_xml_name` is the one rule that turns a
field into the XML element the export writes, and `PanoramaParser._protocol_field_name` is the one rule
that turns a provider path into the key the captured dict holds, so `parse_bgp`, `parse_ospf` and
`_protocol_interface` state a path and never spell a field name. Both are named in
`tests/test_protocol_object.py::test_the_table_is_the_only_shape_owner`.

The table covers the levels this converter prints, plus the `sensitive` decision rows the emitter uses
when a parse method reaches the field. A level the table does not state is not read by the parser and is
not checked by the gate. No second table names a shape: `sanity_checks.value_shape` stays the reader's own
inverse, and it gains the `number` shape.

### 3. The one-of `type` choice

- `peer_group.type`: `external` → `ebgp`, `internal` → `ibgp`, `external-confederation` →
  `ebgp_confed`, `internal-confederation` → `ibgp_confed`. A nexthop belongs to the chosen sub-shape,
  and `import_nexthop` and `remove_private_as` exist only under `ebgp`.
- `area.type`: `normal`, `nssa`, `stub`. The report value is the sub-shape key.
- `area.interface.link_type`: `point-to-point` → `p2p`, `broadcast`, `p2mp`.
- A value the mapping cannot state prints nothing for that field and the report names the entry, so the
  operator sees the choice the tool could not make. The emitter reads the captured field to look up the
  mapping, so the property scan still records the read.
- The report value is the export spelling, so `external` maps to `ebgp` and `point-to-point` maps to
  `p2p`; `area.type` and `area.interface.link_type` are the identity, because the export states the
  provider key. `tests/test_protocol_object.py::test_the_one_of_mapping_is_the_decision_the_report_prints`
  pins both, including the `VPN_ROUTING_CONFIG_EXAMPLES.md` example, which reads `<type>external</type>`.
- An OSPF `range` element must state exactly one of `advertise` or `suppress`, so the row declares both as
  `block` fields and an element that states neither is a report entry. The choice detail is built from the
  row's own choice fields, so no module spells the words.

### 4. A peer belongs to the peer group entry that holds it

- `parse_bgp` nests the peer inside the peer group entry it read it in, so the record states the
  membership as the parent, not as a `peer_group` text field. The peer prints inside the peer group
  element.
- A peer the export holds in `bgp.peer` with no peer group cannot be expressed: the provider has no
  peer outside a peer group. The parse marks it `report_only` with the reason, and the manual report
  names the whole entry, so the file holds no half of it. The same rule covers an out-of-area interface,
  an unmappable `one_of` value, and a `range` entry with no choice.
- `parse_bgp` and `parse_ospf` fill the `protocol` part of the router object that `_parse_router`
  marked, so one entry keeps one mark. `protocol` is a captured field of the router entry, so the
  matrix row declares it as a property the emitter reads.

### 5. An OSPF interface lives inside the area

The provider declares an interface only inside `area`, so an interface inside an area prints inside the
area element. An interface at the `protocol/ospf` level has no provider field, so its container row
stays `report` and the manual report prints it.

### 6. A sensitive field prints as the variable reference

- `VALUE_VARIABLES` is the one table that decides the shape of a printed field, so it gains the rows for
  the three provider `sensitive` facts: `secret`, `key` and `password`. The shape is `reference_only`: the
  block prints `var.<name>`, the run declares the variable with `sensitive = true` and no value, and no
  generated file states the value.
- The name is `naming.py` applied to the entry name, because a value cannot name itself. `naming.py`
  stays the one naming rule. `TerraformGenerator.printed_value` is the one print site that reads it.
- A reference-only name records no value, so `site_data.py` rule 2 writes no `.tfvars` line for it and the
  operator supplies the value in `terraform.tfvars`, which the tool never writes. A report row is only an
  entry the file cannot express, so a sensitive field writes no report line: the variable is the rule that
  carries it.
- The completeness test for `VALUE_VARIABLES` covers the leaf fields `PROTOCOL_SHAPE` states, so the
  table is complete for every field the emitter prints.

### 7. The container rows move, and the gate rule for an object attribute

- `container_coverage.CONTAINER_TABLE`: `protocol/bgp` and `protocol/ospf` move from `report` to
  `emitted` with the note `panos_virtual_router`. The sub-shape rows for the entries the emitter prints
  (`peer-group`, `peer`, `redist-rules`, `area`, `area/interface`) move to `emitted` with the same note,
  because the property scan reads an entry only through an `emitted` row. `protocol/ospf/range` becomes
  `nested-block` (the element prints inside the area), and `protocol/ospf/interface` stays `report` with
  the reason.
- The gate rule `protocol_object` reads the object through the one block reader and the one field
  reader. `import_blocks.py` gains two shapes of the same reader: the fields inside a container value
  and the elements of a list value. `CHECK_ORDER` names `protocol_object` after `actions`. Five findings,
  each a FAIL:
  1. A `protocol` the field reader can read as a name but not as a field, which is the block shape the
     provider refuses.
  2. A level the shape table states no row for, a field the row does not declare, or a value whose shape
     the reader reads differently from the shape the row states. `one_of` and `block` are read as
     `object`, because a one-of level is an object that states one key and a `block` field is an object
     that states nothing but its presence.
  3. A `one_of` level states no key, or more than one key, or a key the row's mapping does not state, or
     a field inside a sub-shape the row for that sub-shape does not state.
  4. A field the table marks `sensitive` states a literal value instead of a `var.` reference.
  5. An element inside a `list` level states no `name`.
- The gate still reads no data file: the rule reads the block text, `PROTOCOL_SHAPE`, and `naming.py`.

### 8. The report prints what the emitter cannot express

The manual setup report prints only the rows the ledger marks `report`, read through
`entry_coverage.protocol_report_rows`, so a router whose whole protocol is expressed writes no report
line and the section prints only when it has content, following the rule for the report files. A row
names the router, the level and the entry name, then the fields in the order the ledger's row declares,
then the Vsys line. Rows are sorted by line, container and name, so two runs print the same lines. The
pinned details are `no peer group names it`, `no advertise or suppress`, `no provider field for an
interface outside an area`, and a `link_type` value the shape table does not state.
`tests/test_reports.py` pins the line shape.

## Acceptance criteria

1. `tests/test_protocol_object.py` pins the print shape, the one-of mapping, the peer membership, the
   OSPF interface placement, the sensitive reference, and the gate rule, including
   `::test_the_shape_table_is_the_measured_provider_shape`, `::test_the_table_is_the_only_shape_owner`,
   `::test_a_peer_prints_inside_its_peer_group`, `::test_a_one_of_level_prints_one_key`,
   `::test_an_unmapped_one_of_value_prints_nothing_and_is_reported`,
   `::test_an_ospf_interface_at_the_router_level_is_reported`,
   `::test_a_sensitive_field_prints_as_the_variable_reference`, and one test per gate finding.
2. `PROTOCOL_SHAPE` is data the gate reads and the test pins against the live provider schema;
   `VALUE_VARIABLES` is the one shape table for a printed field; `naming.py` is the one naming rule;
   `import_blocks.py` is the one reader, with the container shapes added to it; `SHAPE_WORDS` is the one
   word list. No module defines a second one, and `tests/test_protocol_object.py::test_the_table_is_the_only_shape_owner`
   keeps the parse methods from spelling a field name.
3. The property scan measures the moved rows against `panos_virtual_router`, so the matrix row declares
   every field the emitter reads, and its `emitter` names the report writer for the fields only the
   report reads.
4. The manual report prints only the rows the ledger marks `report`, and `tests/test_reports.py` pins the
   line shape, the router name, the field order and the four detail strings.
5. `CHECK_ORDER` names `protocol_object` after `actions`, and the gate reports no finding on the
   committed goldens.
6. `tests/golden/kitchen_sink/virtual_routers.tf` gains the `protocol` object. Every other golden byte
   is unchanged. Report files are not goldens.
7. `docs/RESOURCE_MAPPING.md`, `README.md`, `docs/README.md`, `docs/USAGE_GUIDE.md`,
   `docs/MIGRATION_GUIDE.md`, `docs/ADVANCED-ROUTING-ENGINE-SUPPORT.md`,
   `docs/VPN_ROUTING_CONFIG_EXAMPLES.md`, `docs/ARCHITECTURE.md` §4.6 and §4.9, and
   `docs/CODEBASE_ASSEMBLY.md` §9 state the landed rules and name the module or the test that holds them.
   `REPORT_ONLY_TYPES` loses the six routing rows, and the BGP example in
   `VPN_ROUTING_CONFIG_EXAMPLES.md` reads `<type>external</type>`, because that is the value the mapping
   turns into the provider key.
8. Two runs on the same source write the same bytes, pinned by
   `tests/test_protocol_object.py::test_two_runs_write_the_same_bytes`.
9. `ruff check .` is clean, `pytest` is green, the gate reports no finding on the goldens, and the
   change is committed. The tracking markdown loses the F7.1 detail.
