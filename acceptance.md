# Acceptance criteria — F6.5 Scope objects as output

F6.5 (Epic 6, Goal 6) emits the six scope objects the pinned provider schema has for
the scopes a codebase needs: `panos_device_group`, `panos_device_group_parent`,
`panos_template`, `panos_template_stack`, `panos_template_variable`, `panos_vsys`.
The design record is `docs/CODEBASE_ASSEMBLY.md` §8; the order rule is §6.

## Decisions

### 1. Emission is default, not opt-in

F6.5 changes the default output. It is not a flag. Three facts force this:

1. `test_resource_mapping.py::test_emitted_types_match_goldens` pins that `EMITTED_TYPES`
   equals the types the committed goldens emit. A type a run only emits when a flag is on
   cannot be in `EMITTED_TYPES` without a golden that has it.
2. The property scan (F4.4) measures what an output reads, and the destination of a report
   row comes from the container table for every run. If a scope container becomes an
   `emitted` row, a run that writes no scope block states a destination it did not write,
   and the scan reports every captured scope field as unread. The report, the scan, and the
   bytes must agree, so the emitter runs in every run.
3. `docs/CODEBASE_ASSEMBLY.md` §6 states the order rule: the scope object comes before the
   config inside it. A unit that has config inside it needs the scope object first, so the
   scope object cannot be an optional extra.

Consequence for the goldens: each golden case gains one file, `scope.tf`. Every existing
golden `.tf` byte stays identical, because no existing emitter changes. The new file is the
behaviour change, and it is reviewed as such. `tests/golden/sample/scope.tf` and
`tests/golden/kitchen_sink/scope.tf` are the pinned output.

`kitchen_sink.xml` gains four scope entries (a device-group `parent`, a template stack, a
template variable, and a vsys entry inside the template) so the golden set carries all six
types. No existing entry in the fixture changes.

### 2. One file for the run, written first

`scope.tf` is one file per codebase, following the `imports.tf` (F6.4) and `read_through.tf`
(F5.5) precedent: the scope object belongs to the unit, and the per-unit write path (§14) is
still open, so a per-type or per-unit file would sit outside the shape it names. `main()`
writes it after `provider.tf` and `variables.tf` and before the object files, so the reader
sees the unit before the config inside it. Inside the file, blocks print in the level order
the F3.9 rule states: device group, then the parent record, then template, then template
stack, then template variable, then virtual system. Within a type, entries print in parse
order (document order), so the file is byte-identical between runs.

### 3. `panos_template_variable` emits as literals

F6.5 emits the template variable with the values the export states. F6.6 (the site data
layer) replaces the literal with a `var.` reference, because the value-to-variable mapping
is not data yet (§9). F6.5 therefore parses only what an emitter can print as a literal:
the entry name, the description, and the `type` object. It writes no `var.` value, so it does
not half-implement F6.6.

### 4. The entry name is the identity, not a property

The entry name and the four scope facts stay the row identity (`entry_coverage.NON_FIELD_KEYS`),
so the parent row declares only the properties its emitter reads. For
`panos_device_group_parent` the provider declares no `name` attribute, so the coverage matrix
test reads the entry name through the field that carries it: `device_group`. Which field carries
it is not a second naming rule: `DATA_SOURCE_SCHEMA` says whether the type declares `name`
(`test_data_source_schema.py`), and `entry_coverage.REPORT_SCOPE_KEYS` is the one place that maps
a scope container to the field its entry name reaches the output through, so the pipeline test
reads `device_group` from those two tables.

One entry can feed two blocks — the scope object and the parent record — so the property scan
measures an entry against the matrix row that covers its container, and that row is
`panos_device_group`. The parent row therefore has no read of its own to measure, and
`panos_vsys` has none either, because its block carries the entry name and the location only and
the emitter reads no property from it. Both rows are grounded by the emitter source test, so
`test_property_coverage.py` pins the unmeasured set as `panos_aggregate_layer3_subinterface`,
`panos_device_group_parent`, and `panos_vsys`, and `test_coverage_matrix.py` states that a row
whose block carries the entry name and the location only declares no property.

### 5. The device member rule

`localhost.localdomain` is the PAN-OS "this device" placeholder (F3.5). It names no firewall,
so it never enters a `devices` list in a scope block, and it is never written as a device
member. A device group whose export lists only the placeholder writes no `devices` list,
because the provider field is optional and the codebase states no device fact it cannot name
(`backlog.md`). The placeholder stays one definition in `container_coverage.py`.

### 6. A scope object is emitted only when the export places it

The provider places each scope object in one kind of scope:

| Type | Placement the schema declares |
|---|---|
| `panos_device_group`, `panos_device_group_parent`, `panos_template`, `panos_template_stack` | `location.panorama` |
| `panos_template_variable` | `location.template` or `location.template_stack` |
| `panos_vsys` | `location.template` or `location.template_stack` |

A virtual system entry that the export places outside a template or a template stack has no
place the provider can put it, so the parse records the entry as `skipped` with the reason,
and the run writes no block for it. The converter does not guess a template for it, the way
it does not guess a template for an object (F3.6). `panorama_device` is not emitted: the codebase
states no device fact in a location today (`backlog.md`), so `location` prints the empty
`panorama = {}` sub-block, the shape `shared = {}` already uses.

### 7. Gate rule: a scope block names a scope this run declares

The gate needs one new rule, because a scope block places itself inside another scope by
name, and the reference rule does not reach a name inside `location`:

`sanity_checks.check_scope_blocks` — for a `resource` block of one of the six scope types,
every name inside its `location` must match the `name` of a block this run declares for that
scope. A `data` block cannot answer. `panorama_device` is not a scope name, so it is not
checked, and an empty `location` sub-block states no name to resolve. The rule reads blocks
with the one block reader (`ARCHITECTURE.md` §4.6), so no second reader appears. Every
violation type the rule states is pinned by a test, and the corpus produces no finding.

The existing checks (`emitted_types`, `location_present`) already cover the new blocks, so no
other gate rule changes. `CHECK_ORDER` gains `scope_blocks` after `import_blocks`, and the check
table in `sanity_checks.py` gains its row, because the report order is pinned by the tests that
compare the report's check names with `CHECK_ORDER`. Reports are not in the golden set, so this
does not change a golden byte.

### 8. The template membership, and one mark per entry

`panos_template` declares no device field, so a template entry's device members are not a
property the emitter can print. `parse_templates` captures only the fields the block prints, and
`parse_associations` reads the membership for its tables. F4.3 rule 1 says a parse method marks
the entries it reads, so the membership entries inside a scope entry are marked by `_list_names`,
the method that reads them, and the scope entry keeps the one mark its scope method gave it. The
membership containers keep their `bookkeeping` rows, so no matrix row covers them and the property
scan does not report them. The test that pins the mark rule
(`tests/test_entry_coverage.py::test_every_parse_method_that_reads_entries_marks_them`) follows
`self.` calls, so it reads through `_list_names` and needs no change.

The scope types are not template-scoped objects: they are the scopes. `_TEMPLATE_SCOPED_TYPES` is
derived from `LOCATION_SCHEMA`, so it excludes the six scope rows; otherwise the pinned `ngfw`
test in `tests/test_multi_vsys_location.py` reads a scope as an object.

### 9. The destination for a scope entry

F4.3 rule 3 says the container table row gives the destination. F6.5 makes a scope container
an `emitted` row, so a scope entry is an object, and the `is_scope_entry` exception in
`EntryLedger.destination` is no longer needed: the table row alone decides. The `devices`
entry stays `bookkeeping`, because no provider resource exists for a device. `parse_associations`
keeps its `bookkeeping` rows for the membership it reads through the scope parse methods, so
one entry has one mark.

The ownership record (F6.2) gains the rows for the scope entries, because an entry that writes
an object can own a name. F6.2 rule 4's gap closes: the parse now captures the device-group
`parent`, so a repeated name between a parent group and a child group has a stated ancestor,
and `ownership.py` reads the parent relation instead of calling it `ambiguous`. `NO_RELATION`
stays for a group the export does not place under another group.

### 10. The emitter prints the properties its row declares

The emitter is one method, `generate_scope_objects`, because one file is one write and the six
types share the block shape. It prints the entry name field, then the properties its matrix row
declares, in the row order, so the read record the property scan measures is the same list the
row states. The property names appear in the method as literals, which is what
`test_coverage_matrix.py::test_declared_property_is_a_key_the_emitter_reads` grounds a row
against. `main()` calls it for every run, because decision 1 states emission is default.

### 11. The value shape is the provider shape

A printed value is not a style choice: the provider takes a list of objects for `devices` on
`panos_device_group` and `panos_template_stack`, a list of strings for `templates`, and an object for
the template variable `type`, and `terraform validate` refuses a string where it takes an object. So
the shape is a table, `resource_mapping.SCOPE_SHAPE`, and the emitter prints through it
(`TerraformGenerator._scope_property`), with no per-type branch in the emitter.

- Each entry names the shape the provider declares, and the test reads it against the live provider
  schema through the `provider_schemas` fixture.
- Every property a scope row declares at the block's own level has a shape entry, so a row cannot add
  a property the emitter prints without stating its shape. The placement keys are the `location`
  fields, not the block's own, so they are not shape entries, and `parent` is not one for
  `panos_device_group`, because the provider has no `parent` attribute for that type and the value
  reaches the output through the parent record the same entry feeds.
- A device object carries the field the provider requires (`name`). The vsys list a device can carry
  is not a fact the membership entry states, so the block states no vsys, and the shape entry is the
  object with one field rather than the two the provider allows.

Pinned by `tests/test_scope_objects.py::test_scope_shape_is_the_provider_shape` and
`::test_scope_shape_covers_the_properties_the_rows_declare`.

### 12. Quality gates

- `ruff check .` is clean, and `pytest` is green. Every test runs offline.
- The provider shape tests use the `provider_schemas` fixture and skip without the terraform
  binary, the same way `DATA_SOURCE_SCHEMA` and `LOCATION_SCHEMA` are checked today. Each new
  `LOCATION_SCHEMA` row equals its `DATA_SOURCE_SCHEMA` row exactly
  (`test_data_source_schema.py::test_location_schema_stays_inside_the_data_shape`).
- Every existing golden `.tf` file is byte-identical. The two golden sets gain `scope.tf`, as
  decision 1 states.
- Exit codes are unchanged: 0 for a run, 1 for an input refusal, 2 for an argument error. A
  gate FAIL exits 1; a WARN exits 0. No new flag, so no new argument error path.
- Report, manifest, ownership, edge, and provenance files stay byte-identical between two runs
  on the same bytes, and no data file names a path or a timestamp.
- `main()` writes `scope.tf` only when it has content, following the rule for the other files.

## Acceptance criteria

1. **Rows.** `COVERAGE_MATRIX` has one row per emitted type, so the six scope types gain rows,
   and `EMITTED_TYPES` gains them. Each row names its emitter and the properties that emitter
   reads. `tests/test_coverage_matrix.py` passes for the new rows, including the pipeline test
   that reads the emitted name through `DATA_SOURCE_SCHEMA` for `panos_device_group_parent`.
2. **Container table.** `parse_device_groups` gains the `parent` fact, and the parse methods for
   the template, template stack, template variable, and virtual system entries exist, each with
   a row. The scope rows read `emitted`; the `devices` row stays `bookkeeping`. One entry, one
   mark: `parse_associations` builds its tables from the objects the scope methods return.
3. **Output.** Running the converter on a fixture that declares a scope writes one `resource`
   block per scope entry, in `scope.tf`, in the level order decision 2 states, with the location
   the provider declares. The device member rule (decision 5) holds: no block names the
   placeholder device.
4. **Placement.** A vsys entry outside a template or template stack writes no block and is
   reported as `skipped` with the reason.
5. **Gate.** `check_scope_blocks` detects a scope block that names a scope no block in the same
   run declares, reads blocks with the one block reader, and reports no finding on the corpus.
6. **Report.** A scope entry in an emitted container prints as `emitted`, and the report bytes
   stay identical between two runs.
7. **Ownership.** A device group and a child device group that repeat a name have a stated
   ancestor from the captured `parent`, and the test that pins it uses a fixture with a parent
   relation.
8. **Shape.** Each printed value matches the shape the provider declares, and every property a row
   prints at the block's own level has a `SCOPE_SHAPE` entry. A membership the provider takes as a
   list of objects prints as a list of objects, so `terraform validate` accepts the file.
9. **Determinism.** `scope.tf` is byte-identical between two runs on the same bytes, and the
   goldens pin it.
10. **Docs.** `docs/CODEBASE_ASSEMBLY.md` §8 names the module and the test for each rule, §6 names
   the file order, `docs/ARCHITECTURE.md` §4.1, §4.2, §4.6, and §3.2 state the changed rules, and
   `docs/COVERAGE_MATRIX.md` counts the rows. `README.md` and `docs/USAGE_GUIDE.md` name
   `scope.tf`.