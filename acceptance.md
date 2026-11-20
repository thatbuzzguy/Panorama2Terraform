# Piece E10.1 acceptance criteria — the membership names that enter the edge set (Epic 10, piece 1)

Epic 10 (template and stack deployment, `PLAN.md`) opens with the decision `docs/TEMPLATE_STACK_DEPLOYMENT.md` §2
states: the order rule ranks a stack unit before the template units inside it, but a `panos_template_stack` block
cannot apply before its member template entries exist, because Panorama states membership as names that must already
exist. This piece decides which membership names enter the edge set, what order fact they state, and how the level
basis reads the pair so the two bases do not disagree.

Closed conditions:

1. The decision is measured, not assumed: the current order data is read from a run on the stack fixtures before the
   change, so the piece records what the level rule states today (`branch_stack_5c39384d` with `after` empty on
   `tests/fixtures/multi_device_templates.xml`, measured 2026-11-20).
2. The piece is an edge-record and order piece. It writes no `.tf` byte, so the golden `.tf` set is unchanged, and
   the report bodies are unchanged: the membership entry keeps its `bookkeeping` line, and the cross-check counts
   only the entries `entry_coverage.EntryLedger.destination` answers as `emitted`, so membership enters no count.
3. The gate, single-threaded: `ruff check .`, `ruff format --check .`, `python3 tools/check_documents.py` reporting
   no finding, and the full `python3 -m pytest`. Pin count moves only by the pins this piece writes.

Criteria for the rule:

1. **Which membership names enter the edge set.** The four lists are the `parse_associations` rows in the container
   table, read through `api_requests.membership_lists()`, which reads `container_coverage.CONTAINER_TABLE`, and each
   joins to the table it returned and to the container that defines the entries its names belong to through
   `api_requests.LIST_JOIN`. A name enters as an edge when the join container that defines its entries is not the
   container that names it: a name that joins inside the container that names it is placed inside that container, so
   the level basis already states that order, and a name that joins outside it cannot be placed inside, so it must
   already exist when the container names it. Measured on the four rows: the three lists that name devices join
   inside their own container, and `template-stack/entry/templates` joins to `templates`, outside the stack that
   names it. A membership name that is a device fact (`vsys_device`, F3.5) names no entry, because
   `resource_mapping.SCOPE_ANSWER` answers no device fact, so it writes no row.
2. **The join is the F6.2 rule, unchanged.** The row joins to `OWNERSHIP.json` on (`type`, `entry`), where `type` is
   the row that covers the entry the membership name names — measured `panos_template` for
   `template-stack/entry/templates`, read through `entry_coverage.matrix_row_for` and `resource_mapping.SCOPE_ANSWER`
   through `entry_coverage.REPORT_SCOPE_KEYS` — and the referrer is the unit that owns the entry that names the
   membership. The membership entry keeps its `bookkeeping` row and writes no ownership row of its own; the edge
   joins to the entry's own row. A membership name the run declares no entry for writes no row (rule 1 of
   `reference_edges.py`).
3. **The direction is the existing edge rule, not a second rule.** `after` reads the target unit before the referrer
   unit, so the stack unit is planned after the template units it names. No module states a second order basis for
   membership.
4. **The level basis states no dependency for a pair the placement fact cannot state.** The level basis reads the
   placement fact through `resource_mapping.SCOPE_PLACEMENT`: `panos_template_stack` declares no location sub-block,
   so no entry is read inside a stack and the level basis states nothing for the pair the membership rule names,
   while the edge basis states the order. For a row that declares the sub-block (`panos_template_variable`,
   `panos_vsys`) the level basis keeps its dependency, so the unit read inside the stack still comes after the stack
   unit. `LEVEL_KEYS` does not move: measured across the corpus, no manifest row carries both the `template` and the
   `template_stack` fact, so the level chain reads the same prefixes in either order and no pair is stated by both
   bases.
5. **`reference_edges.py` states no membership reader.** The module takes the tables `parse_associations` returned
   as an argument, the way it takes `sanitize_name`; the join, the fact each container fills, and the row that
   answers a fact are read through `api_requests`, `entry_coverage`, and `resource_mapping`, and the fact order and
   the naming rule through `unit_manifest`, so the import-set pin `test_the_module_resolves_no_name_and_records_no_name`
   gains those names with a stated reason for each, and the module defines no reader of the four tables itself.
6. **Pins.** New pins in `tests/test_reference_edges.py`:
   - `::test_a_stack_that_names_a_template_records_one_row` — referrer the stack unit, target the template unit,
     `type` the `panos_template` row, `entry` the template name, and no matrix row covers the membership entry;
   - `::test_the_lists_that_name_devices_record_no_row` — the entry rule measured on the four lists, and no row for a
     device fact;
   - `::test_a_membership_name_the_run_declares_no_entry_for_writes_no_row` — pinned on its own input, because no
     fixture has a member name with no entry;
   - `::test_the_stack_unit_is_planned_after_the_template_units_it_names` — read as data through
     `reference_edges.order` on `tests/fixtures/multi_device_templates.xml`;
   - `::test_the_level_basis_states_no_dependency_for_the_pair_the_membership_rule_names` — the order read with the
     level basis alone, and the device inside the stack keeping its level dependency.
   Moved pins: `CORPUS_EDGES` gains the rows the rule produces on the fixtures that carry a stack listing a declared
   template (`kitchen_sink.xml`, `multi_device_templates.xml`, `scope_objects.xml`), the measured count moves from 20
   to 23, `test_the_shallower_scope_comes_before_the_deeper_scope_inside_it` reads the stack's `after` through the new
   fact with the level-chain half unchanged, and the import-set pin gains the three names criterion 5 states. The
   three call sites that build the rows (`_sets`, and the two pins that call `build_rows` with their own input) pass
   the tables.
7. **Unchanged facts the piece must not move:** the manifest `references` field is the names `name_ref` recorded, so
   membership names enter no manifest field; membership enters no membership table read by a report, so no report
   field changes; the round-trip cross-check counts stay; `data_files` reads the record through the same shape rule
   and the same order rule, so the corpus reports no new finding; no report names the record (F4.5); determinism pins
   hold; the exit codes are unchanged; `docs/CODEBASE_ASSEMBLY.md` §5 rule 1, §5 rule 7 and §6 rule 2 name the
   membership rule and the placement guard, and `tools/check_documents.py` reports no finding for the pin claims the
   new document names.

Measurements, as they landed:

- Run on `tests/fixtures/multi_device_templates.xml` before and after: `after` on the stack row moves from `[]` to
  `hq_networks_8ada44b7`, and its `rank` moves 1 to 6. The rank walk stays acyclic on every fixture, so
  `test_no_corpus_fixture_produces_a_cycle_finding` passes with no change.
- `CORPUS_EDGES` after the change reads 23 rows over six fixtures: one row on each of the three fixtures that carry a
  stack listing a declared template.
- The level basis read on its own, with no edge and no ownership rows, states no dependency for the stack pair on
  `tests/fixtures/multi_device_templates.xml` and keeps `fw_3_example_com_a1c0f1a0` after `branch_stack_5c39384d`.
- The gate, read on the final tree single-threaded 2026-11-20: `ruff check .` clean at `py310`,
  `ruff format --check .` clean on the 103 Python files, `python3 tools/check_documents.py` reports no finding, and
  `python3 -m pytest` passes 1,722 pins with the same 4 skip for the missing `tflint` binary — 1,726 pins in 53
  modules, against 1,721 before the piece, in 453.62 s, single-threaded. `tests/test_reference_edges.py` reads 38
  pins against the 33 it read before the piece. No golden, fixture, response or tflint file changes.
