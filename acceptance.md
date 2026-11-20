# Piece 22 acceptance criteria — which output reports a `number` text the reading rule cannot read

Closes the last open part of the 2026-11-12 audit's parse set, in `backlog.md`: `_protocol_field` keeps no
value for a `number` text the signed-integer rule cannot read, so the field prints nothing and nothing is
reported.

Closed conditions:

1. One output reports the unread `number` text, stated in the document that owns the fact.
2. The rule has an owner, named in that document, and a pin that names it.
3. The pin measures content, not a count, and runs through the pipeline.
4. `ruff check` and `ruff format --check` pass, `tools/check_documents.py` reports no finding, and the full
   test set passes.

Criteria for the decision:

1. The decision names which output reports the unread text, or which rule refuses it.
2. The rule that owns the decision cannot reach the fact: the input layer reads no shape table, so it cannot
   know which element is a `number` field. A rule that cannot reach its fact cannot be the decision maker.
3. `is_refusal` names exactly two kinds, and the closed set is pinned, so a new refusal kind is a change of
   the input layer's rule, not a decision inside the read.
4. A refusal moves the exit code to 1 and writes no file, so it answers one field by stopping the run. The
   report path answers one field by naming it and keeping the rest of the run.
5. F2.9's mechanism for a value the reader cannot read is a `# NOTE:` line inside an entry or rule block. The
   protocol, filter and certificate print paths return one dict of field values and `hcl_value` prints dict
   keys, so a note cannot be a key there. The property scan cannot name the field either, because the field is
   stored as no value and `captured_fields` drops a field stored empty. So the entry line is the output that
   reports an unread `number`.
6. The fact is recorded on the object the ledger marks for the entry, under the fact key
   `entry_coverage.NUMBER_TEXT_NOT_READ`, which is in `NON_FIELD_KEYS` because a fact is not a field. The reading
   rule states only its answer for the field: the integer for text it reads, `''` for an element that is absent or
   holds no text, and `''` plus the fact for text the shape word cannot read. The fact is stated only when the
   caller holds the fact set for the entry, so the rule cannot report a fact by itself, and the entry level owns
   the set and shares it down the levels inside it.
7. What the entry line prints: the entry, the field, and the text the rule could not read. A fact read for an
   entry inside a config-object entry prints on the row that counts that entry, with the name it is counted under,
   because such an entry has no line of its own. The block prints nothing for the field, so the gate sees no field
   to check and the exit code stays 0, and the read that prints the fact is through `RecordingDict.value()`, so
   printing it records no property use.

Measurement before the change: 66 accepted fixtures, 144 `number` field reads through `_protocol_field`,
79 read as integers, 65 elements absent, 0 texts present that the rule cannot read. So no committed fixture
trips the rule, no golden moves, and the pin plants its material read through `xml_input.parse_xml` and stays
out of the corpus, the way Piece 17's key pin does. The pin cannot measure the rule on the corpus, and that is
stated here. The pins are
`tests/test_parse_helpers.py::test_the_number_rule_answers_for_the_text_it_can_read_and_the_text_it_cannot` and
`tests/test_entry_coverage.py::test_the_entry_line_prints_the_fact_the_number_rule_cannot_read`, and the content
they share is in `tests/conftest.py` because no test module may import another.

Gate measurement, as it landed (2026-11-20, on the final tree, single-threaded): `ruff check .` clean at
`py310`, `ruff format --check .` clean on the 103 Python files, `python3 tools/check_documents.py` reports no
finding, and `python3 -m pytest` passes 1,717 pins with the same 4 skip for the missing `tflint` binary — 1,721
pins in 53 test modules against 1,719 before the piece, in 5m40s (5m25s on the run before the pin line was
shortened for the line-length rule). `tests/test_parse_helpers.py` reads 7 pins against 6, and
`tests/test_entry_coverage.py` reads 33 pins against 32. The planted run answers no property finding and no gate
finding, so the exit code stays 0, and no golden file and no report golden moved.
