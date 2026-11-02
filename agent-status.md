# Agent Status

## Current position

F6.10.2 (the print site per unit) is complete and committed: `name_ref` resolves a name inside the
referrer's own unit, so a name the flat chain resolved across scopes is now the plain name. No
directory is written in that slice, so `tests/test_write_path.py::test_no_unit_directory_is_written_yet`
stays green and the directory write stays with F6.10.3.

The rule, in `docs/ARCHITECTURE.md` §4.3, first match wins:

1. A name the referrer's own unit declares is `HclRef('<scope>.<local>.name')`, where `local` is the
   name the naming rule (§5) gave for that unit.
2. A name another unit in the run declares is the plain name. The device case (F3.5, F3.6) is one case
   of this rule, so the device rule and the helper that read it are gone.
3. A name no unit in the run declares is a read-through `data block` when the run opted the scope in,
   for the unit the site belongs to (§4.7).
4. Otherwise the plain name.

The shape the code carries:

- `self._declaration_index` is `(scope, name)` -> the declaring unit's facts -> the local name. It
  replaces `_block_registry`, `_flat_registry`, `_device_registry` and `_device_index`. A `data` block
  enters no declaration index.
- `declare_block_name` takes the object, because the rule reads the unit through `unit_manifest.facts_of`
  at both ends. The digest input is unchanged for a resource (`context|vsys`), so a single-unit run writes
  the same bytes; for a `data` block the identity is `identity_digest(facts)`, and no golden pins a
  read-through local name.
- `name_ref` takes no `context`, `vsys` or `device`: the referrer states them. `key` stays for a VPN
  composite key. The recording rule is unchanged.
- `_data_blocks` is keyed by `(scope, unit, name)`, and the writer sorts by `(type, local)` so the file
  stays byte-identical between runs.

The pin lists changed by this slice: `tests/test_reference_edges.py::CORPUS_EDGES` is 20 rows over five
fixtures (`dependency_wiring.xml` 3, `kitchen_sink.xml` 8, `multi_device_templates.xml` 4,
`reference_cycle.xml` 2, `policy_order.xml` 3), measured from a real run. `GROUPING_REFERENCES` in
`tests/test_unit_manifest.py` is unchanged, because the grouping fixture names one unit. The kitchen
goldens for `security_rules.tf`, `virtual_routers.tf` and `zones.tf` regenerated from a real run; the
sample goldens are byte-identical. The suite is 1258 tests.

The pins that name the per-unit rule are `::test_name_ref_resolves_inside_the_referrers_own_unit`,
`::test_a_name_another_unit_declares_stays_a_plain_name`, `::test_name_ref_resolves_inside_the_referrers_own_vsys`,
and `::test_the_record_names_the_referrers_unit_not_the_declaring_unit`, plus the read-through pins in
`tests/test_data_blocks.py` and `tests/test_multi_device_template.py` that `docs/ARCHITECTURE.md` §4.3
names.

The next slice is F6.10.3 (the directory write). `acceptance.md` holds F6.10.2's criteria and must be
overwritten for it. F6.10.3 writes one directory per unit the manifest names, holds the unit set §14
states, applies the LF rule, and regenerates both goldens with the per-unit layout, so the golden pin reads
the `.tf` set as paths from the case directory and a gate finding names the path. It also changes
`test_no_unit_directory_is_written_yet`.

## Rules to keep when writing documents

- One owner document per rule; every other document links to it.
- Machine-readable tables are code. A document explains a table and never restates it
  row by row, so a regenerated table cannot drift.
- No test counts in a document. A document names the test that pins a rule; the
  count lives in `agent-status.md` and the git history.
- A claim about what the tool does must name the module or the test that holds it. A
  feature id is written only when a module or a test uses it as a name.
- ASD-STE100 Simplified Technical English, no marketing voice, no emoji.
- A historical record is not kept in the markdown. The git history is the record, and the
  markdown states the current state.
- A record is data, so a document describes its fields and never restates a record. The
  example in `docs/USAGE_GUIDE.md` is an illustration with a shortened hash, not a pin.
- Completed epic, phase, feature and task detail is removed from the tracking markdown after
  the work is committed; `AGENTS.md` states the rule.

## Watch for Epic 6 and Epic 7

- The codebase modules name the unit, the owner, the pair, the order, the block, the scope
  object and the site, and write no directory. The write path is the step that turns a
  `directory` field into a real directory, and `scope.tf`, `imports.tf` and `site.auto.tfvars`
  are one file for the run until it lands. The print-site rule it applies is decided
  (`docs/CODEBASE_ASSEMBLY.md` §5 rule 5), and the file shape is decided (§14), so the step has
  no open decision.
- A rule that pins an absence by scanning module sources cannot read a source that names the words it
  forbids, so a scan reads the tool's own modules, and the test name and the module docstring carry no
  forbidden word. The pin for the outputs rule is group 7 of `tests/test_reference_edges.py`; the pins for
  the file shape are `tests/test_write_path.py`.
- The block reader in `sanity_checks.py` serves every kind, and the same field reader serves the
  fields inside a container value and the elements of a list value, so a new block shape uses them
  rather than writing a second reader.
- The gate reads the `.tf` files for the block rules and the four data files for the data rule, so the two
  file sets are distinct: a block rule reads a `.tf` file, and the data rule reads a record through the
  module that owns its row shape. `scope.tf`, `imports.tf` and `actions.tf` are `.tf` files, so the block
  rules read them. `site.auto.tfvars` is the printed form of the site record, so the data rule compares it
  and does not count it as a data file, and `SOURCE.txt` is read by no rule. A new file shape must name
  which of the two sets it belongs to, and the report counts, the console line and the tests that pin the
  file set change with it. No data rule reads a `.tf` file, and no block rule reads a data file.
- A field reader must read at the block's own level and stop at the closing quote, or a
  sub-block field or an escaped quote answers for the block's field. Both are pinned in
  `tests/test_import_blocks.py`, and the scope rule reads at the block's own level through the
  same reader, which takes the sub-block it reads as an argument (the action rule reads inside
  `config`). The same reader also tells a quoted value from a `var.` reference, so no second
  rule decides the shape of a field.
- `PROTOCOL_SHAPE` is the one table for the protocol object, and a level it does not state is not read.
  A new routing level needs a table row before an emitter, a gate rule or a report can read it, and
  `WORD_TO_SCHEMA` is the pin between a table word and the schema word. A parse method states a path and
  never spells a field name: `_protocol_xml_name` and `_protocol_field_name` are the two rules.
  `_protocol_areas` is the area rule the two OSPF levels share, and `_protocol_choice` takes the element that
  holds the chosen body: the flag element for an area type, the entry's own level for a BGP peer group.
- The parse method that takes the router element is named in the test helpers that call it for each router:
  `tests/test_entry_coverage.py::_parse_every` and `tests/test_multi_vsys_location.py`. A new level method
  must be added there, or the corpus checks run no method for it.
- A container row that moves from `report` to `emitted` changes the property scan scope, the per-entry
  report, and the `.tf` goldens together, so it cannot be a print-only change. A moved row must be
  `emitted` with the provider type in its note, because the matrix row and the report both read the note.
- `SCOPE_PLACEMENT` and the location sub-block are one fact: a new scope type needs both the
  placement key and the `SCOPE_ANSWER` entry, and the emitter reads the placement key as the
  location, so a new row cannot place itself in a scope it does not name.
- The entry name is never a property. A row whose provider type declares no `name` reaches the
  block through `entry_coverage.name_field`; no emitter, gate rule, or test should state the
  field again.
- One place decides the shape of a value: `resource_mapping.VALUE_VARIABLES`, read at the print
  site. A new field a table row maps must be read by the emitter, the gate and the `.tfvars`
  writer through the same table, and the table must cover every field `LOCATION_SCHEMA` declares.
- The §5 naming rule lives in `naming.py`. No module may define a second one;
  `TerraformGenerator.sanitize_name` is a delegate and the data modules take the rule as an
  argument.
- One place decides the shape of a reference field: `TerraformGenerator.name_ref`, read at the print site.
  The mechanism for a name it cannot resolve is the plain name it returns, so a write path that runs the
  rule per unit changes the corpus pin lists, not the rule.
- The import position for the four `*_policy_rules` types must be the position the live config
  holds, and the F3.5 rulebase decision gates it. No block is written for a rule entry until both
  land.
- The generated `README.md` does not name `imports.tf`, `SITE_DATA.json` or `site.auto.tfvars`;
  the F5.5 label precedent says an opt-in shape labels itself.
- Actions need Terraform 1.14 or later; the committed goldens now declare it, so a change to the
  minimum is a golden change.
- The credential rule needs one statement that covers both the fetch layer and the generated
  provider block.
- The prune action still needs the record directory decided. A state record references nothing,
  so it prunes nothing, and the prune rule reads a record file, not one record.
- A coverage fact that comes from a run must be read from the run's ledger, so the scan tests run
  the pipeline in process.
- A cycle test needs two units that each declare a name the other one uses, because the rule resolves a
  name only inside the unit that declared it (`tests/fixtures/reference_cycle.xml`).
- The LF rule is a byte rule, so the goldens and the no-change tests change with the write path.
