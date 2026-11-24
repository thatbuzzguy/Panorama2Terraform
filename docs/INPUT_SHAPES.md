# Input Shapes

Design record for Epic 13, open. This document is the owner of the rules about what bytes an
input can be, which entry point accepts each shape, and what the run states when a shape is
refused or read. The document index is in [README.md](README.md). The read rule it extends is
[ARCHITECTURE.md](ARCHITECTURE.md) §3.1, and the console-line shape a new finding must fit is
[ARCHITECTURE.md](ARCHITECTURE.md) §3.2. The pieces are in `to-do.md`, the criteria are in
`acceptance.md`, and the facts that need a live target are in `backlog.md`.

## 1. Facts measured offline

1. No producer decompresses anything. `src/xml_input.py` states no archive rule, and
   `read_input` hands raw bytes to the door, so archive magic bytes reach `reject_dtd`, the
   prolog scan cannot read them, and the parse answers the line the shape table states for the
   magic-bytes row (`src/input_shapes.py`). The splitter's line for the shape it read is therefore only
   reached when the bytes already are XML: a bundle member read after extraction, or a per-device
   export.
2. The splitter answers through `device_associations`, so the fact it can state is the row set
   it read: zero `device-group/entry` rows, and the shape the tree holds instead, which is the path the entry sits
   at. Piece 13A.2 wrote the line for that fact, so the run prints the fact through
   `container_coverage.console_line` and names no file, because the run wrote none. The line that guessed where the
   export came from is gone with the piece.
3. The two config shapes are already read and pinned by tests: the Panorama export holds
   `device-group` entries plus `templates` and `template_stacks`, and a firewall's own export
   holds `devices/entry/<serial>` — or `localhost.localdomain` — with no device-group row. Both
   are converter inputs; only the splitter refuses the second
   (`docs/DEVICE_GROUP_SPLITTING.md` §Troubleshooting).
4. Measured 2026-11-23 against the published PAN-OS API documentation, page "XML and XPath":
   the four node types — root, element, attribute, text — and the entry shape `<entry name=...>`
   are stated the same on the 9.1 (EoL) page and the 11.1 & Later page. The read layer keys
   entries by the `name` attribute, so it agrees with the documented shape on both pages. The
   10.2 page redirects to the current landing page, so the version-by-version comparison is not
   complete, and any version difference that would change the read stays a measurement.

## 2. The archive producer (decision, 2026-11-23)

A gzip or tar.gz input is read through a producer behind the F5.1 door, so the F5.1 rule holds
unchanged: adding a source means adding a producer, not a check. Rules pending, each needing an
owner before the first piece lands:

1. `check_bytes` stays the one definition of the two checks, and the door runs them on the
   bytes it parses — for an archive, the decompressed bytes.
2. The size cap must be applied during decompression, not after. Without this the size check
   answers for the compressed file only, and a bundle that expands past the cap reaches the
   parse. No second size definition may appear.
3. The shape is read from the magic bytes, not from the file extension, following the DTD
   rule's shape: the check asks the parser, not a text search.
4. Accepted shapes pending decision: single-member gzip, and a tar.gz whose single XML member
   is read. The member selection for a bundle with more than one XML member is open: the run
   refuses, or the run names one member by a rule. A selection that depends on member order
   conflicts with `docs/ARCHITECTURE.md` §6, so the refusal is the starting shape.
5. The provenance facts for an archive read are an open decision: what `SourceOrigin.kind`
   states, whether the record names the archive bytes or the decompressed bytes for `size` and
   `sha256` (F5.3 says the record names the bytes the door checked), and how the cache rule —
   the cache holds exactly the bytes the boundary parsed — reads for an archive. The member
   name enters the record as a field the file case does not have.

## 3. The shape table (rules, Piece 13A.1, 2026-11-24)

The table is one machine-readable table, held as data in `src/input_shapes.py`, which is its only
owner. Each row states the byte shape, the content that shows it, the entry point that accepts it,
the line the run prints for it, the status, the decision a pending row waits for, and the owner
function the pins read the row through, as `SHAPE_ROW_FIELDS`. The document names the owner and
states the rules around the table; it holds no row, and the row wording appears in no document,
which `tools/check_documents.py` reports. Every document that describes a shape links here.

1. **The module states no rule an owner states**, so each line is the measured wording of the module that builds
   it: the size line from `xml_input.check_bytes` and `xml_input.read_input`, the DTD line from
   `xml_input.check_bytes`, the parse line from `xml_input.parse_bytes`, the state line from
   `state_input.parse_state`, and the console line from `container_coverage.console_line` with the fact phrase and the
   block header of the entry point that read the fact. A row names its owner in `measured_through`, and
   `tests/test_input_shapes.py` measures the row by running the row's content through that owner and comparing the
   printed line with the row. A pending row names no owner, because the rule it waits for has no owner yet. A console
   line row holds no prefix, because the prefix is the part `container_coverage` states, so the pin reads the prefix
   through that owner and holds that the table holds no copy of the shape.
2. **The parts of a line the pins measure are the origin and the byte counts**, held as `{origin}`, `{size}` and
   `{limit}`. Every other part of a line is the row's own wording, so the pin compares the whole line. A part the
   row's own content shows — the DTD name, a parse answer, the position and the identity a console line names — is
   wording measured by running the content through the owner, so no row states a number the pins cannot read from it.
3. **The status vocabulary is two words.** `held` is a row the pins measure today; `pending` is a row whose line does
   not exist yet, and a pending row states no line, names no entry point as accepting its shape, and names the
   decision in §2 it waits for. A decision that lands, or a line that is written for a held shape, moves the row in
   the same commit.
4. **The shape is read from the bytes**, so no row names a file name, an extension, or a committed fixture, and the
   pins decide acceptance from the row's content under different names. The committed fixture pair is Piece 13A.3,
   which adds no row here, so the fixture-count pins do not move.
5. **Every entry point prints the same line for the same bytes**, which the pins measure by running both entry points
   on one row's content. A row that names `none` as its accepted entry point is a refusal row: the entry point prints
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
member, and the unfinished 10.2 documentation comparison leg. No document states these as facts.
