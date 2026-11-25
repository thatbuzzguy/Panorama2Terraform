# Input Shapes

Design record for Epic 13, landed. This document is the owner of the rules about what bytes an
input can be, which entry point accepts each shape, and what the run states when a shape is
refused or read. The document index is in [README.md](README.md). The read rule it extends is
[ARCHITECTURE.md](ARCHITECTURE.md) §3.1, and the console-line shape a new finding must fit is
[ARCHITECTURE.md](ARCHITECTURE.md) §3.2. The pieces are in `to-do.md`, the criteria are in
`acceptance.md`, and the facts that need a live target are in `backlog.md`.

## 1. Facts measured, not pinned

1. `src/xml_input.py` holds the archive producer, `parse_archive`, which reads the shape from the bytes and
   expands one accepted member: the single-member gzip, and a gzip stream that holds a tar archive with exactly one
   member. The producer runs no check, so `check_bytes` stays the one definition of the two checks and the door runs
   them on the bytes the producer hands it, which for an accepted shape are the expanded bytes. The read cap is
   applied while the bytes expand, at the count the read step already states, `max_input_bytes + 1`, so a bundle that
   expands past the cap answers the size rule before the parse builds a tree. Bytes that are not an accepted shape
   reach the door unchanged, so the parse answers the line the shape table states for the magic-bytes row, and the
   producer writes no refusal wording of its own. A bundle with more than one XML member is read only through the
   declaration the operator names, so a run that names none is answered by rule 4's owner, and the row for that shape
   is measured through the rule itself. Pinned by
   `tests/test_safe_input.py::test_the_archive_producer_runs_the_checks_on_the_bytes_it_expands`,
   `tests/test_safe_input.py::test_the_cap_stops_the_expansion_before_a_tree_is_built`, and
   `tests/test_safe_input.py::test_the_archive_producer_opens_no_file`, `tests/test_safe_input.py::test_the_checks_answer_on_the_bytes_a_declared_member_expands`, and `tests/test_safe_input.py::test_the_member_rule_states_no_check_and_no_size_rule_of_its_own`. The splitter's line for the shape it read is
   reached when the bytes the splitter sees are XML, which now includes a bundle the producer expanded, and a
   per-device export.
2. The splitter answers through `device_associations`, so the fact it can state is the row set
   it read: zero `device-group/entry` rows, and the shape the tree holds instead, which is the path the entry sits
   at. Piece 13A.2 wrote the line for that fact, so the run prints the fact through
   `container_coverage.console_line` and names no file, because the run wrote none. The line that guessed where the
   export came from is gone with the piece.
3. The two config shapes are already read and pinned by tests: the Panorama export holds
   `device-group` entries plus `templates` and `template_stacks`, and a firewall's own export
   holds `devices/entry/<serial>` — or `localhost.localdomain` — with no device-group row. Both
   are converter inputs; only the splitter refuses the second
   (`docs/DEVICE_GROUP_SPLITTING.md` §Troubleshooting). Which export an operator should take, and how to
   get one, has one owner, [USAGE_GUIDE.md](USAGE_GUIDE.md) §Which export a run needs, so this fact names
   the shapes it measures and links to that section.
4. Measured against the published PAN-OS API documentation, page "XML and XPath", on three version
   legs: the 9.1 (EoL) leg and the 11.1 & Later leg, read 2026-11-23, and the 10.2 leg, read
   2026-11-24. Each leg states the four node types — root, element, attribute, text — and the entry
   shape `<entry name=...>`, where the entry name is an attribute node, the name/value pair. The read
   layer reads the entry name from the `name` attribute, through `xml_input.ENTRY_SEGMENT`, so it
   agrees with the documented shape on all three legs, and the committed corpus states its entries in
   that shape. The comparison is complete, and no leg states a version difference. The 10.2 leg was
   read through the stored capture of its page address (capture `20250602181153`, the page the site
   stated on 2024-03-20), because the live address for that leg answers a redirect; the redirect, the
   date, and the address that answered are the finding in `backlog.md`.
5. **The record row is read through the record build rule its owner names**, `provenance.record_for`, so the fact
   the pins measure is the record a run builds and not a line the table states. For an archive read the record names
   the archive through `xml_input.ARCHIVE_KIND`, the member through `SourceOrigin.member`, and the byte facts name
   the decompressed bytes the door checked, because the byte facts come from the door and the producer hands the
   expanded bytes to it. The record reads back as itself through `provenance.parse_record`, which is what makes the
   row held, because a row is measured only when a pin can call its owner. No committed golden holds a record, so
   the pins build the record they read from a row's content. Pinned by
   `tests/test_input_shapes.py::test_the_record_row_is_measured_through_the_record_build_rule` and
   `tests/test_provenance.py::test_an_archive_record_names_the_archive_the_member_and_the_decompressed_bytes`.
6. **The cache rule reads through its existing owner** (`docs/ARCHITECTURE.md` §3.3), and the condition that
   differs is a measurement rather than a rule: `source_fetch.fetch()` runs the checks through `parse_bytes` and
   never through the archive producer, so no archive read reaches a cache entry today, and a record built for an
   archive read states `-` for the cache field and references nothing, the same way a state record does. Pinned by
   `tests/test_provenance.py::test_an_archive_record_references_no_cache_entry`.

## 2. The archive producer (decision, 2026-11-23; rules 4 and 5 taken 2026-11-24)

A gzip or tar.gz input is read through a producer behind the F5.1 door, so the F5.1 rule holds
unchanged: adding a source means adding a producer, not a check. Rule 1 to rule 3 are the rules
that needed an owner before the first piece landed; the producer `xml_input.parse_archive` is that
owner, landed by Piece 13B.2 on 2026-11-24. Rule 4 and rule 5 are the two decisions, taken
2026-11-24.

1. `check_bytes` stays the one definition of the two checks, and the door runs them on the
   bytes it parses — for an archive, the decompressed bytes. The producer states no check, so
   the door runs the two checks on what the producer hands it. Pinned by
   `tests/test_safe_input.py::test_the_archive_producer_runs_the_checks_on_the_bytes_it_expands`, which records what
   the door is handed, and `tests/test_safe_input.py::test_file_producer_runs_the_checks_through_the_boundary`,
   which reads the file producer for one shape of each kind.
2. The size cap must be applied during decompression, not after. Without this the size check
   answers for the compressed file only, and a bundle that expands past the cap reaches the
   parse. No second size definition may appear. The producer stops at the count the read step already states,
   `max_input_bytes + 1`, and hands the bytes it expanded to the door, so the size rule stays `check_bytes` and
   answers with the line the table holds for a size refusal, naming the origin. Landed by Piece 13B.2, pinned by
   `tests/test_safe_input.py::test_the_cap_stops_the_expansion_before_a_tree_is_built` and
   `tests/test_input_shapes.py::test_the_decompression_row_is_measured_against_the_expansion_and_not_the_compressed_size`.
3. The shape is read from the magic bytes, not from the file extension, following the DTD
   rule's shape: the check asks the parser, not a text search. The producer reads the shape through
   `xml_input.GZIP_MAGIC` and `xml_input.TAR_MAGIC`, so the pins read it through the producer's own definitions and
   hold no shape rule of their own. Pinned by
   `tests/test_input_shapes.py::test_the_shape_is_decided_from_the_bytes_and_not_from_a_file_name`.
4. **Taken 2026-11-24, the member rule.** One member is accepted: a single-member gzip, and a
   tar.gz that holds exactly one XML member. When the archive holds more than one XML member, the
   run reads one only when the operator declares which member to read, as an argument; with no
   declaration the run refuses. A selection that reads the member order stays refused by the
   determinism rule (`docs/ARCHITECTURE.md` §6), so no member can be chosen by order. The
   declaration is held by the CLI, not by a rule owner, so no module states a member rule the CLI
   holds instead. The shape is still read from the bytes, so this decision changes no rule about
   a name.
   Landed by Piece 13B.4 on 2026-11-25. The owner is `xml_input.read_member`, which
   `xml_input.parse_archive` calls, so the producer adds no check and states no refusal wording of
   its own, and the rule answers before the door is handed any bytes. The refusal is the wording
   the table mirrors as data, and the line names no member count, because a count is a fact a pin
   reads from the row's own content. The declaration is read through
   `xml_input.add_member_argument` and `panorama_to_terraform.shared_arguments`, so both entry
   points read one set, and the argument states no path rule and no naming rule of its own, and a
   run that declares nothing is refused nothing by it. Pinned by
   `tests/test_input_shapes.py::test_the_member_rule_line_holds_only_the_origin_as_a_measured_part`,
   `tests/test_input_shapes.py::test_the_table_mirrors_the_member_rule_and_holds_no_wording_of_its_own`,
   `tests/test_input_shapes.py::test_the_declaration_is_row_data_and_no_pin_holds_a_member_of_its_own`,
   `tests/test_input_shapes.py::test_both_entry_points_print_the_same_line_for_the_same_bytes`, and
   `tests/test_safe_input.py::test_the_member_argument_states_no_rule_an_owner_states`.
5. **Taken 2026-11-24, landed with Piece 13B.3, the provenance bytes.** For an archive read the record names the
   decompressed bytes, because F5.3 states that the record names the bytes the door checked and rule 1 states that
   the door checks the decompressed bytes. `SourceOrigin.kind` names the archive, through `xml_input.ARCHIVE_KIND`
   as the producer's own kind constant, and the member name enters the record as a field the file case does not
   have, read through `SourceOrigin.member`, so the record module states no shape rule of its own and reads both
   facts through the origin the producer states. The cache rule is read through the owner that states it,
   `source_fetch.py` (`docs/ARCHITECTURE.md` §3.3): an archive record comes through the file producer, so it states
   `-` for the cache field, and the condition that differs is the measurement in §1 fact 6. Pinned by
   `tests/test_provenance.py::test_an_archive_record_names_the_archive_the_member_and_the_decompressed_bytes` and
   `tests/test_provenance.py::test_an_archive_record_references_no_cache_entry`.

## 3. The shape table (rules, Piece 13A.1, 2026-11-24)

The table is one machine-readable table, held as data in `src/input_shapes.py`, which is its only
owner. Each row states the byte shape, the content that shows it, the entry point that accepts it,
the line the run prints for it, the status, the decision a pending row waits for, and the owner
function the pins read the row through, and the member the row is read through when the operator declares one, as `SHAPE_ROW_FIELDS`. The document names the owner and
states the rules around the table; it holds no row, and the row wording appears in no document,
which `tools/check_documents.py` reports. Every document that describes a shape links here.

1. **The module states no rule an owner states**, so each line is the measured wording of the module that builds
   it: the size line from `xml_input.check_bytes` and `xml_input.read_input`, the DTD line from
   `xml_input.check_bytes`, the parse line from `xml_input.parse_bytes`, the state line from
   `state_input.parse_state`, and the console line from `container_coverage.console_line` with the fact phrase and the
   block header of the entry point that read the fact. A row names its owner in `measured_through`, and
   `tests/test_input_shapes.py` measures the row by running the row's content through that owner and comparing the
   The pins read every row through `tests/conftest.py::shape_row` and fill the line through
   `tests/conftest.py::shape_line` with the parts they measure, so no test module holds a row, a
   row line, or a declaration of its own, and the table module builds no wording.
   printed line with the row. The record row's owner is the record build rule, `provenance.record_for`, so that row
   is measured by building the record the run would write for its content and reading the record back through the
   same module, because a record row states no printed line of its own. A pending row names no owner, because the
   rule it waits for has no owner yet. A console line row holds no prefix, because the prefix is the part
   `container_coverage` states, so the pin reads the prefix through that owner and holds that the table holds no copy
   of the shape.
2. **The parts of a line the pins measure are the origin and the byte counts**, held as `{origin}`, `{size}` and
   `{limit}`. Every other part of a line is the row's own wording, so the pin compares the whole line. A part the
   row's own content shows — the DTD name, a parse answer, the position and the identity a console line names — is
   wording measured by running the content through the owner, so no row states a number the pins cannot read from it.
   The member rule's line holds only `{origin}`, because the number of members a bundle holds is a
   fact a pin reads from the row's content, so the line names no count.
3. **The status vocabulary is two words.** `held` is a row the pins measure today; `pending` is a row whose line does
   not exist yet, and a pending row states no line, names no entry point as accepting its shape, and names the
   decision in §2 it waits for, or the piece that will give its rule an owner once the decision is taken. Both §2
   decisions are taken, and the rule that needed an owner was the member rule, so no row is pending today and the pins read the pending set as an absence: every row names a function its owner defines. A decision that lands, or a line that is written for a
   Pinned by
   `tests/test_input_shapes.py::test_no_row_is_pending_so_the_pins_measure_every_row_through_an_owner_they_call`.
   held shape, moves the row in the same commit. A pending row cannot be held by a decision alone, because the pins
   read a held row only through an owner function they call, and the table module states no rule an owner states.
4. **The shape is read from the bytes**, so no row names a file name, an extension, or a committed fixture, and the
   pins decide acceptance from the row's content under different names, read with the declaration the row states. The committed fixture pair (Piece 13A.3)
   shows the two shapes as two files and adds no row here, so the pins read its shape from its bytes and not from
   its name, and the pins that state the printed fixture set read the measured value, so they move with the pair.
5. **Every entry point prints the same line for the same bytes**, which the pins measure by running both entry points
   on one row's content, read with the declaration the row states, so the pins pass no member name of their own. A row that names `none` as its accepted entry point is a refusal row: the entry point prints
   the refusal, and the line is that refusal. A row that names an entry point is a shape that entry point accepts, so
   the line is the fact it read, and the pins read that row through the block the entry point states rather than
   through a refusal.

## 4. The diagnostic rule (rules, Piece 13A.2, 2026-11-24)

The splitter prints the fact the run reads: the number of `device-group/entry` rows, the shape the tree holds
instead, and the source line of the entry that shows it. The fact names one position, one identity and one fact, so it
prints through `container_coverage.console_line`; the report branch is for a fact that compares two sets, and this fact
compares a count with one shape, and the splitter writes no report. The run states its own fact phrase and its own
block header and calls the shape, so it holds no shape of its own, and the row rule and the walk rule it already
states are the only rules the line reads. A part the run cannot name is the honest statement, and a block prints only
when it has a finding. The exit code does not change: the exit code stays with the rules that read the files
(`docs/ARCHITECTURE.md` §4.6). Pinned by
`tests/test_split_device_groups.py::test_the_splitter_prints_the_fact_it_read_for_a_file_with_no_device_group_row`,
`tests/test_split_device_groups.py::test_the_line_names_the_honest_statement_when_the_tree_holds_no_entry`,
`tests/test_split_device_groups.py::test_the_run_prints_nothing_new_when_its_table_answers`, and
`tests/test_input_shapes.py::test_a_held_console_row_prints_the_fact_through_the_block_its_owner_states`.

## 5. Facts only a live target states

Recorded in `backlog.md`, under Design Decisions (input sources): the file form the UI download
writes, whether a backup XML declares a DOCTYPE, whether a bundle can hold more than one XML
member, and the condition that the 10.2 leg can only be read from a stored capture, because its live
page address answers a redirect. No document states these as facts: §1 fact 4 states the measurement
the piece made, and `backlog.md` states the redirect finding with the address that answered.
