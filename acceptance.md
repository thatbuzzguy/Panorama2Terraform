# Acceptance — the rule row shape (Epic 9, Piece 17, Phase 9A)

Criteria set 2026-11-18 for Piece 17: `rule_data.py` declares the rule row shape `RULE_ROW_FIELDS` and
the two forms of the same rows, the consumed JSON and the printed CSV. This piece declares the shape and
reads the rules through the rules that already own the facts; it wires no file, changes no run output,
and changes no golden. The write path is Piece 18, the iterated block is Piece 19, the gate is Piece 20.

Owners this piece reads and does not restate: §2.1 identity through `state_coverage.ownership_key`; the
8-hex digest through `unit_manifest.identity_digest` and `unit_manifest.DIGEST_HEX`; the §5 naming rule
through `naming.py`, taken as an argument like `unit_manifest.py` and `site_data.py` take it; the field
set through `entry_coverage.MATRIX_BY_RESOURCE`, the matrix row that covers the rule container; the no-value
rule through `entry_coverage.EMPTY_FIELD_VALUES`; the unit join through `unit_manifest.facts_of` and
`unit_manifest.directory_name`. The piece states two rules of its own: the row shape, and the chain grouping
(F2.5, F3.2), which moves from `TerraformGenerator._policy_rule_chains` to `rule_data.chains` so the group
is stated once; the generator reads it here, as `TerraformGenerator.sanitize_name` reads the §5 rule.

## The rules this piece states

1. **The row shape.** `RULE_ROW_FIELDS = ("directory", "resource", "entry", "key", "pivot", "properties")`.
   `directory` is the join to the manifest. `resource` names the coverage matrix row. `entry` is the entry
   name. `key` is the `for_each` key: the chain ordinal, zero-padded to four digits, joined to the identity
   digest. `pivot` names the pivot rule, or is empty for the first rule of a chain. `properties` is the field
   set the matrix row names, sorted, read through the recorded object. `rulebase` is not declared: the parse
   records no rulebase fact, so no column can name a field the parse cannot capture (F3.5); the column enters
   the shape when the live fact lands, not before. The earlier wording in `to-do.md` ("the rulebase column
   prints nothing") means exactly this: a declared column with no captured fact behind it is a finding under
   `COVERAGE_MATRIX.md` §1, so the shape declares nothing for it today. Phase 9A as planned named the five scope
   facts as columns of the row; the shape that landed holds one column for the unit, `directory`, because the unit
   fact belongs to §3.4 and enters the row through `unit_manifest.facts_of`, so the row states no second unit rule.
2. **Every properties column reads the field it names through the recorded object**, through the recording
   read, so the data file is an output and the honesty rule holds for every column. A field the recorded
   object holds with no value prints no column, the way the per-entry report reads `EMPTY_FIELD_VALUES`.
3. **The key cannot be the name alone.** The digest half is `unit_manifest.identity_digest` read through
   `state_coverage.ownership_key`, so the key is the §2.1 identity in the order that rule states. A name in
   two device groups, or in two virtual systems, gives two rows and two keys.
4. **The chain grouping is the F2.5 and F3.2 rule, stated once here**: chains per (rule type, device group,
   vsys), document order within a chain, first-seen order across chains, `Shared` for a device group the
   export cannot place and `vsys1` for a virtual system the export declares none for. The ordinal is the
   position in the chain, so the sorted key order is the XML order inside the chain, which is the rule the
   single object of Piece 19 reads for apply order. `TerraformGenerator._policy_rule_chains` delegates to
   `rule_data.chains`; the position facts already pinned by `tests/test_policy_order.py` are unchanged, so
   no golden byte changes in this piece.
5. **Two forms, one row set.** `render` prints the rows as JSON, which is the form the Terraform object
   reads. `render_csv` is the printed form of the same rows: the header in field order, one line per row in
   row order, every value as its JSON text, the same escape set `import_blocks.unescape` reads back. A
   printed form is not a reader input, so `parse_rows` reads the data and refuses the printed form.
6. **No second rule and no writer.** The module states no naming rule, no unit rule, no identity key, no
   path, no console line, no environment name, and writes no file; the writer is `write_path.py` and the
   path builders are Piece 18's. Standard library and house modules only.

## Pins, in `tests/test_rule_data.py`

The eight pins, in the order the rules above state them. `tests/conftest.py` holds no fixture of its own, so the
pins build the parse through `xml_input.parse_xml`, the same input door the corpus pins read, and read the record
the way `tests/test_property_coverage.py` reads it.

- AC-1: `test_the_row_shape_is_the_declared_field_set` — the tuple, in order; `rulebase` is not in it; each of the
  four rule fixtures gives rows in the declared shape; `render` prints exactly the declared fields in field order,
  which is why a writer cannot write a field the shape does not declare.
- AC-2: `test_parse_rows_refuses_a_shape_it_does_not_declare` — an extra field, a missing field, a key that is not
  the declared shape in the three ways it can fail (short ordinal, no digest half, a digest half that is not the
  row's own unit digest), a property value that is not something the recorded object can hold (a number, or no
  value), a field the row does not name, properties that is not a mapping, and the printed CSV read as data. The
  PBF rule's mapping value is refused neither way: the shape declares it and reads it back.
- AC-3: `test_build_rows_names_only_captured_fields_and_reads_through_the_recorded_object` — for the four rule
  fixtures, the recorded object lists the row's fields as keys the output read, every printed value equals the
  value read through the recorded object, and the pin measures both a column with a value and a field held with no
  value, which prints no column.
- AC-4: `test_the_key_is_the_ordinal_and_the_digest_read_through_the_one_identity_rule` — the ordinal is the
  position inside the chain and the digest half is `unit_manifest.identity_digest` applied to the facts tail of
  `state_coverage.ownership_key`, so the pin recomputes each key through the two owners rather than restating a
  key rule, and the key half names the same unit as the directory half. No committed fixture holds one rule name in
  two device groups, so this pin plants its material and says so; the planted file goes through the input door and
  stays out of the corpus.
- AC-5: `test_the_chain_grouping_and_order_are_the_f2_5_rule_read_through_rule_data` — measured on
  `tests/fixtures/policy_order.xml`, the fixture the F2.5 pins read: three device groups, so three chains of 3, 2
  and 1 in first-seen order, document order inside a chain, the first rule of a chain names no pivot and each later
  rule names the rule before it, the sorted key order equals the chain order, and a rule the export places in no
  device group is grouped as `Shared`.
- AC-6: `test_the_generator_reads_the_chain_grouping_through_rule_data` — the delegate, read through the import
  rule, and no other module defines the grouping.
- AC-7: `test_the_printed_csv_states_the_same_rows_as_the_data` — the header in field order, one line per row in
  row order, every value as its JSON text, and the escape set read back by `import_blocks.unescape`, so no second
  escape rule appears.
- AC-8: `test_the_rule_data_layer_states_no_second_rule_and_writes_no_file` — no naming rule, no identity key, no
  unit rule, no path, no console line, no environment name, no writer; the imports are the standard library and the
  house modules it reads its rules through.

## Indexes and measurement the piece moves

- The §1 module table names `rule_data.py` and its rule column names `RULE_ROW_FIELDS`, held by
  `tests/test_layout.py::test_the_indexes_name_every_document_under_them` and by
  `tools/check_documents.py` check 4, which needs the new entry in its `SHAPES` set.
- The root index names `tests/test_rule_data.py` once, held by the same pin and by
  `tools/check_documents.py` check 6.
- `tests/test_write_path.py::test_a_record_module_renders_rows_and_writes_no_file` names `rule_data` in the module
  tuple it reads, and `docs/LICENSING.md` measures the `src/` module count from the working tree, so a 23rd module
  moves the count it states. `rule_data.py` carries no notice, so the pair becomes 4 of 23 and the other 19 carry
  none. The document states its counts as the working tree, which is what check 3 reads, so the re-statement is in
  the same commit as the module, `e4ffe7b`.
- `docs/ARCHITECTURE.md` §1 and `docs/COVERAGE_MATRIX.md` §1 do not state any new rule beyond the row shape, so no
  golden, fixture, response, or tflint file changes and the pins that name the printed sets and the golden bytes are
  unchanged.

## Gate

`ruff check .`, `ruff format --check .`, `python3 -m pytest`, `python3 tools/check_documents.py`, in that
order, conservative threads. Before, measured 2026-11-18 on the committed tree at `623dea2`: `ruff check .`
clean at `py310`, `ruff format --check .` clean on the 100 Python files, 1,697 pins in 52 test modules, all pass,
no skips when the `tflint` binary is present, and the same 4 pins skip for the missing binary on this machine,
258.53 s, `python3 tools/check_documents.py` reports no finding.
After, measured on the final tree at the commit that holds the module, the test module and the indexes: `ruff
check .` clean, `ruff format --check .` clean on the 102 Python files, 1,705 pins in 53 test modules — 1,701 pass
and the same 4 skip for the missing `tflint` binary — 346.42 s, and `python3 tools/check_documents.py` reports no
finding.