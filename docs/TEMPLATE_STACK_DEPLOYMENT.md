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

Piece 1 decided fact 1. Pieces 2 and 3 are the open decisions, and each is recorded here when it is taken.

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

## 3. Piece 2: the scope a template or a stack entry is declared inside (open)

The parse records the scope a scope entry sits in through `resource_mapping.SCOPE_PLACEMENT`, which states the
location sub-block for the two types that can sit inside another scope (`panos_template_variable`, `panos_vsys`)
and an empty set for the six scope rows, because each of those places itself at the top of its own chain. A device
group names its base through the parent entry it declares, which the parent record reads. The decision this piece
takes is what the read answers for a template entry and a stack entry, and whether the manifest row needs a field
for it. It stays open until the entry rule in §2 has landed, because the read and the edge read the same container.

## 4. Piece 3: a new site from an existing template (open)

A new site needs a template unit whose entry the export did not name. The tool can write the name, the place and
the membership for a template the export declares, but the device the operator adds is a fact only a live target
states. What stays inside this piece, and what moves to `backlog.md`, is decided when the piece is opened.
