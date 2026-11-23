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
   prolog scan cannot read them, and the parse answers "not well-formed (invalid token)". The
   splitter's firewall message is therefore only reached when the bytes already are XML: a
   bundle member read after extraction, or a per-device export.
2. The splitter answers through `device_associations`, so the fact it can state is the row set
   it read: zero `device-group/entry` rows, and the shape the tree holds instead. The current
   line "This may be a single firewall export, not a Panorama export." states a guess, not the
   fact, and does not fit the four parts of the console-line rule
   (`container_coverage.console_line`, `docs/ARCHITECTURE.md` §3.2).
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

## 3. The shape table (pending)

One table: byte shape → accepted entry point → the refusal or report line the run prints. The
machine-readable table is code, so the table needs one owner module in `src/` before a pin can
read it, and the documents link to it instead of restating rows. Each accepted shape gets a
committed fixture read through the fixture assembler, and the pins that state the printed fixture
set name the fixture count, so a fixture and the pins move in the same commit
(`to-do.md` §Rules the layout keeps).

## 4. The diagnostic rule

The splitter prints the fact the run reads: the number of `device-group/entry` rows, the shape
the tree holds instead, and the source line of the entry that shows it. The finding must fit the
four parts of the console-line rule — one position, one identity, one fact — or print in the
report only, because a fact that compares the read row set against the expected row set
compares two sets. The exit code does not change: the exit code stays with the rules that read
the files (`docs/ARCHITECTURE.md` §4.6).

## 5. Facts only a live target states

Recorded in `backlog.md`, under Design Decisions (input sources): the file form the UI download
writes, whether a backup XML declares a DOCTYPE, whether a bundle can hold more than one XML
member, and the unfinished 10.2 documentation comparison leg. No document states these as facts.
