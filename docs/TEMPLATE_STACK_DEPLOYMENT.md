# Template and stack deployment (Epic 10)

Design record for Epic 10. Each rule here names the module that holds it and the test that pins it. Epic 6 landed
the unit, the ownership row, the reference edge record and the unit order (`docs/CODEBASE_ASSEMBLY.md` §5 and §6),
so this document adds only what a template or a stack unit needs before the codebase can be applied to a device.

## 1. What a template or a stack needs

A template unit and a stack unit each write one `scope.tf` block (`ARCHITECTURE.md` §4, F6.5). Applying that block
to a device needs two facts the codebase does not state today:

1. **The order the platform applies the objects in.** Panorama applies a template to a device through the stack
   that lists it, and a stack cannot apply a template entry that does not exist yet. So the plan order must put
   the template units before the stack unit that lists them. This is the order rule, so it is data on the manifest
   row and not a rule about templates.
2. **The site the block applies to.** A template unit writes the object for the template the export named, not for
   a new template the operator creates on a device that the export does not name. The tool can state the name, the
   place, and the membership, but not the device the operator adds later.

Each piece is landed and recorded in its own section: piece 1 in §2, piece 2 in §3, piece 3 in §4.

## 2. Piece 1: the membership names as recorded uses (landed)

The order rule ranks a unit after the units it names, so the order rule needs a pair for the stack and each
template its membership lists. The membership fact already states that pair as data: the four lists
`parse_associations` reads are rows in `container_coverage.CONTAINER_TABLE` with the `bookkeeping` destination, and
each row joins to the table the method returned and to the container that defines the entries its names belong to
through `api_requests.LIST_JOIN`.

**The entry rule.** A membership name enters the edge set when the container that names it cannot place that name
inside itself, so the name must already exist when the container names it. Measured on the four rows: the three
lists that name devices join to their own container, so the name is placed inside the container that read it, and
the level basis of the order rule already states that order. The list a stack keeps for its member templates joins
to `templates`, outside the stack that names it, so that name enters the edge set. A membership name that is a
scope fact — `vsys_device`, F3.5 — names no entry, because `resource_mapping.SCOPE_ANSWER` answers no device fact,
so the join finds no row for it.

**The join, and the direction.** The row is the F6.2 join, unchanged: `type` is the row that answers the fact the
join container fills, `entry` is the membership name, `target` is the unit that owns the ownership row for that
pair, and `referrer` is the unit that owns the row for the entry that names the membership, because a membership
entry writes no ownership row of its own. A membership name the run declares no entry for writes no row. The
direction is the order rule's existing direction: `after` reads the target unit before the referrer unit, so the
stack unit is planned after the template units it names. No module states a second order basis for membership.

**The level basis reads the same pair one way.** `resource_mapping.SCOPE_PLACEMENT` states no location sub-block
for `panos_template_stack`, so no entry is read inside a stack and the level basis states nothing for the pair the
membership rule names. The edge basis is what ranks the stack after the template it names. A row that does declare
the sub-block — `panos_template_variable`, `panos_vsys` — keeps its level dependency, so a unit read inside the
stack still comes after the stack unit. `LEVEL_KEYS` needs no change for this: measured across the corpus, no
manifest row carries both the `template` and the `template_stack` fact, so the level chain reads the same prefixes
in either order, and no pair is stated by both bases.

**No second rule.** `reference_edges.py` defines no reader of the four membership tables and no fact order of its
own. It takes the tables as an argument, the way it takes `sanitize_name`, and reads the join, the fact each
container fills, and the row that answers a fact through `api_requests`, `entry_coverage`, and
`resource_mapping`. `join_results` is the cross-response join, so the entry point states no list of its own.

Pinned by `tests/test_reference_edges.py`, including
`::test_a_stack_that_names_a_template_records_one_row`,
`::test_the_lists_that_name_devices_record_no_row`,
`::test_a_membership_name_the_run_declares_no_entry_for_writes_no_row`,
`::test_the_stack_unit_is_planned_after_the_template_units_it_names`,
`::test_the_level_basis_states_no_dependency_for_the_pair_the_membership_rule_names`, and the import-set pin
`::test_the_module_resolves_no_name_and_records_no_name`. `CORPUS_EDGES` in the same module reads 23 rows over six
fixtures, so the three membership rows are part of the measured set, and the level pin
`::test_the_shallower_scope_comes_before_the_deeper_scope_inside_it` reads the stack's `after` through the
membership fact.

This piece writes no `.tf` byte, so the golden set is unchanged. The membership entry keeps its `bookkeeping` line
in the per-entry report, and the cross-check counts only the entries `entry_coverage.EntryLedger.destination`
answers as `emitted`, so membership enters no count.

### Measurement

Read on 2026-11-20 on `tests/fixtures/multi_device_templates.xml`. Before the change the stack row
`branch_stack_5c39384d` had `rank` 1 and `after` empty, and the template units ranked after the device units inside
them, so the codebase put the stack first and the templates after it — the order Panorama cannot apply. After the
change the same run records one membership edge, `branch_stack_5c39384d` → `hq_networks_8ada44b7` on
(`panos_template`, `HQ-Networks`), and the stack row reads `after` = that template unit. The rank walk stays
acyclic on every fixture, so `tests/test_reference_edges.py::test_no_corpus_fixture_produces_a_cycle_finding` is
unchanged. The three fixtures that carry a stack listing a declared template are `kitchen_sink.xml`,
`multi_device_templates.xml` and `scope_objects.xml`; each produces one row.

## 3. Piece 2: the scope a template or a stack entry is declared inside (landed)

`resource_mapping.SCOPE_PLACEMENT` states the key the parse records for the scope a scope entry sits in, and a key
can only name a location sub-block that declares `name`, because a placement is a scope name written inside
another block. `resource_mapping.LOCATION_SCHEMA` declares only `panorama` for `panos_template` and for
`panos_template_stack`, and `panorama` declares no `name` field, so those two rows state no key: the location has
no field that could hold a container name. A device group names its base through the parent entry it declares,
which the parent record reads.

**The decision.** A template entry and a stack entry are not declared inside another scope, so the read answers no
containing scope. The empty set on those two rows is that answer, not an omission: the location block prints the
empty sub-block, and the naming context the emitter reads from the same table is empty, which is the F3.1 rule for
an entry that defines its own scope. Measured on `tests/fixtures/scope_objects.xml`, which holds `<templates>` and
`<template-stack>` as siblings of `<device-group>` under `<panorama>`: the scope walk names no entry above either
entry, so `identity_of` records `Shared` for `device_group` — the parse fallback, not a fact value — and each
entry's own level key names the entry. The relation the export states between a device group and a template, and
between a stack and a template, is a membership list of names, so §2's entry rule is the only place that relation
is stated.

**The manifest row needs no field.** The row states placement through the five fact keys it already reads: the key
for the entry's own level names the entry and the container keys read empty, so "no containing scope" is an absent
fact, the same way the tool states no place it cannot name (the F3.6 rule). A field for it would state the fact a
second time, and no entry could fill it. Measured on the same fixture run: the template unit `Edge-Networks` reads
`device_group` empty and `template` as its own name, and the stack unit `Edge-Stack` reads `device_group` empty,
`template` empty, and `template_stack` as its own name. Because a row can carry at most one of the `template` and
`template_stack` facts, the level order resolves one container fact per row, so `unit_manifest.NAME_LEVELS` and
`reference_edges.LEVEL_KEYS` are unchanged.

Pinned by `tests/test_scope_objects.py::test_a_placement_key_names_a_sub_block_that_can_hold_a_scope_name` and
`::test_a_template_entry_and_a_stack_entry_record_no_container_fact`, and by
`tests/test_unit_manifest.py::test_the_row_states_placement_through_the_fact_keys_it_already_reads` and
`::test_no_row_carries_two_container_facts`. `::test_the_four_panorama_scopes_print_the_empty_sub_block` is the
existing pin for the printed sub-block, and `tests/test_data_source_schema.py` pins `LOCATION_SCHEMA` against the
live provider schema.

The change this piece makes is the wording it corrects: `src/resource_mapping.py` and `src/unit_manifest.py` state
the decision, `docs/CODEBASE_ASSEMBLY.md` §3 rule 2 and `docs/ARCHITECTURE.md` §2.2 no longer state that a template
can sit inside a stack, and no `.tf` byte is written, so the golden set is unchanged. The case a config entry
inside a stack reaches is a provider location shape the pinned schema does not state, so it stays in `backlog.md`.

## 4. Piece 3: a new site instantiated from an existing template (landed)

No corpus fixture showed a template entry that no device names, so the piece added
`tests/fixtures/template_no_device.xml`: a device group that lists one template as a member and names no device, and
one template entry with no `devices` element inside it. Every fact below is read through the module that owns it on
that run.

**The decision.** For the unit a template entry names with no device inside it, the tool states the names the export
declares and states nothing for a device it does not name. The device fact, `vsys_device`, is the empty fact, the
same way the tool states no place it cannot name (F3.6), so no output names a device for that unit and no rule has
to decide what to state for a fact the export cannot carry. The unit is still a unit the manifest names, and each
codebase part that reads a device value answers for the empty fact as it already does.

**The identity, the row, and the directory.** `PanoramaParser.identity_of` records `Shared` for `device_group`, the
parse fallback for an entry the parse cannot place (`docs/ARCHITECTURE.md` §2.2), and `unit_manifest.facts_of`
excludes it, so the identity is the four facts the export names plus the empty device fact. The row states placement
through the five fact keys it already reads (§3), so no field is needed for a device the export cannot name, and the
digest and the directory name come from the facts alone. Pinned by
`tests/test_unit_manifest.py::test_a_template_entry_no_device_names_keeps_the_device_fact_empty`.

**The site data.** A site row is a value the run read, so a unit with no device fact holds no row: the record has no
row for the unit, `site.auto.tfvars` has no line for it, `provider.tf` names no `target`, and `variables.tf`
declares no `target`. The `target` fact is `docs/CODEBASE_ASSEMBLY.md` §9 rule 8 read on this shape, and the pin
there reads a fixture that names a device, so this piece pins the same rule on the fixture that shows no device:
`tests/test_site_data.py::test_a_unit_that_names_no_device_writes_no_site_row_and_no_tfvars_line`.

**The reference edges and the order.** The device group's template list is a field of the entry that owns the
container, so `container_coverage.CONTAINER_TABLE` names no `bookkeeping` row for `device-group/entry/templates` and
`api_requests.LIST_JOIN` states no join for a row the table names no row for. That is rule 8's condition for writing
no row: the name is printed inside the block the container writes. So the pair the membership rule would record for
the device group unit and the template unit does not exist, the edge record holds no row for the run, and the order
rule has no dependency for the pair — the ranks the two rows carry are the identity order, not an answer for the
pair. The relation reaches the output only as the names the device group block prints. Pinned by
`tests/test_reference_edges.py::test_a_device_group_that_lists_a_template_records_no_row`, which reads the same
tables §2's pins read.

**The printed blocks.** The template block prints the empty `panorama` sub-block, because the placement rule answers
no containing scope for a template entry (§3), the entry name, and the two properties its row declares, and it prints
no device because the export names none. The device group block prints the template name as data through the field
its own row declares and prints no device members. Pinned by
`tests/test_scope_objects.py::test_a_template_entry_with_no_device_prints_its_names_and_no_device`, with
`::test_the_four_panorama_scopes_print_the_empty_sub_block` the existing pin for the printed sub-block.

**The commit and push action.** The action rule selects the fact through `unit_manifest.named_fact`, so for a unit
whose device fact is empty both blocks name the template fact. The push block states no `devices`, because the tool
names no serial (`docs/CODEBASE_ASSEMBLY.md` §10 rule 6), so the two blocks name the fact the row can name and no
device value. Pinned by
`tests/test_commit_actions.py::test_a_unit_with_no_device_fact_names_the_fact_the_export_declares`; the pins there
that read a unit naming a device read `kitchen_sink.xml`, so this pin reads the new fixture.

**No new rule.** The piece adds no naming rule, no reader, no writer, no console line, no environment name, and no
field on the manifest row or on an edge row, and it changes no `src/` module: every part of the decision is an
existing rule answering for a fixture that shows the shape. The piece's rule content is this section and the pins.
The `.tf` goldens are unchanged, because the piece writes no `.tf` byte on them. The fixture is read by the corpus
pins through `corpus_fixtures()`, so the pins that state the printed fixture set read the measured value, and the
corpus edge, gap, property, ownership and site-row sets did not move: the fixture writes no row for them.

**What stays in `backlog.md`.** The device the operator adds to the device group for a new site, and the serial a
push target names, are facts only a live target states, so they stay in `backlog.md` and no pin asserts them.

### Measurement

Read 2026-11-21 through the tool's own modules on `tests/fixtures/template_no_device.xml`:

- `identity_of` answers `Shared` for `device_group` and empty for `vsys`, `vsys_device` and `template_stack`, with
  `template` as `Remote-Networks`. `facts_of` answers `('', '', 'Remote-Networks', '', '')`, the digest `93488ed8`,
  and the directory `remote_networks_93488ed8`.
- The run writes a manifest row for that unit and one for the device group unit `newsite_fw_9f79c4e2`.
  `reference_edges.build_rows` answers no row, `order` answers `after` empty on both rows, and the ranks are 1 and 2
  in the identity order. `parse_associations` answers four empty tables for the run.
- `site_data.build_rows` answers no row and `value_variables` answers no name, so the run writes no `SITE_DATA.json`
  and no `.tfvars`, and `provider.tf` prints `hostname = var.hostname` and no `target`.
- The scope file prints the template block with the empty `panorama` sub-block, `name`, `default_vsys` and
  `description`, and the device group block with `templates = [ "Remote-Networks" ]` and no device members. The
  action file prints the commit and push blocks for the template unit on the template fact and for the device group
  unit on the device group fact.
- The gate reports no finding on the run and writes no `MANUAL_SETUP_REPORT.txt`; the per-entry report reads 2
  `emitted` entries, one for the device group entry and one for the template entry.
