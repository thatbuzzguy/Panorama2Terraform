# Decision — the `tools/build_kitchen_sink.py` rebuild finding — acceptance criteria

This slice decides what the fixture assembler is, and what pins it. `tools/README.md` says the tool
assembles `tests/fixtures/kitchen_sink.xml` from the committed files and that its output is checked in, so
the claim is that the committed fixture is the tool's output. The tool takes no command-line path: it reads
committed files, so the F3.8 decision stands (`docs/ARCHITECTURE.md` §1.1) and the tool keeps its direct
`ET.parse` call.

## Facts measured before the change (2026-11-04, offline)

1. The tool stops on the corpus today. Its read set is a name list, so the first fixture its parse cannot
   read ends the run with a traceback: `tests/fixtures/hostile_bad_control_char.xml` (not well-formed, line
   13 column 34). It reads 24 files before it stops, and writes no file.
2. The tool reads hostile input when its parse accepts it: `hostile_billion_laughs.xml` parses, so its
   expanded entity text (`lollol...`) enters the tool's output. That is input the F3.8 input rule refuses
   before the parse, so "the parse accepts it" is not the read rule.
3. Read through the F3.8 checks (the DTD check, then the parse), the corpus is 70 XML fixtures: 3 hostile,
   67 that a run accepts. The tool's read rule, stated as those two checks on the committed bytes, answers
   the same decision as `xml_input` for every committed fixture, so the tool can state the rule and name no
   fixture. The read set is the 67 accepted fixtures, less the record.
4. The committed fixture is not the tool's output for the committed set: 983 lines against 3125 lines, and
   106 entries against 356 entries.
5. The committed fixture is curated by hand, so byte equality is not reachable:
   - it holds 15 comments, and `ET.parse` builds no comment node, so no merge can answer them;
   - it holds 11 entry names no committed fixture carries (`ACL-Kitchen`, `Dual-Protocol`,
     `Vsys-Duplicate`, `Vsys-Service`, `Web-Wildcard`, `kitchen-rule`, `template-tag`, `template-vsys`,
     `vr-device-level`, `vsys-zone1`, `vsys-zone2`);
   - it holds no `ip-with-expand` entry, while the tool's output for the committed set carries the one from
     `tests/fixtures/external_lists.xml`.
6. The tool writes inside the corpus. If its output is not the record, running it destroys the record and the
   golden set with it, so a generator that is not a pin must not write the record.
7. Option 1 is rejected on the measurement: to answer the record the tool would have to restate the record's
   content (the comments, the 11 names, the curated subset), which is a list of content, not a rule. Option
   2 states what the tool does assemble, and pins that.

## Decision (option 2)

1. The tool is a generator, not a pin. It prints the tree it assembles, and it writes no file.
   `tests/fixtures/kitchen_sink.xml` stays the record that the golden set and the corpus pins read, and the
   record is curated by hand.
2. The tool's read rule is the F3.8 input rule read on committed files: a fixture that declares a DTD, or
   that the parse cannot read, is hostile input, so the tool skips it by rule and not by name. `tools/`
   imports no tool module, so the tool states the DTD check itself, and the pin asserts the tool's decision
   agrees with `xml_input` for every committed fixture.
3. The record is not an input. The name-list exclusion for `address_objects_dg_override.xml` is removed:
   the merge joins entries by name, and the tool no longer answers for the record, so the fixture that shows
   the duplicate-name case is material like any other fixture.
4. `docs/ARCHITECTURE.md` §1.1 is the owner document for the tool's place in the layout, and states the read
   rule and the generator rule once. `tools/README.md` is the index row that names them, and `backlog.md`
   closes the finding.
5. The pin is offline data, in `tests/test_build_kitchen_sink.py`.

## Acceptance criteria

1. Read rule: for every committed fixture, the tool's decision agrees with `xml_input.parse_xml`. A hostile
   fixture is skipped by the rule, so the tool names no fixture in its source except its own record. The rule
   is general: the tool skips a fixture a test writes in a temporary directory.
2. Read set: for the committed corpus the tool reads 66 files and skips the 3 hostile fixtures, and the record
   is not an input. The read set equals the set the corpus pins read, less the record.
3. The tool writes no file: its source states no write, and a run leaves `tests/fixtures/kitchen_sink.xml`
   byte-identical. The run prints one line per fixture it skipped, in the read order.
4. The tool is not a pin on the record: its output for the committed set is not the record's bytes, pinned as
   data, with the two facts that keep it so (the record holds comments the tool's rule drops, and 11 entry
   names no committed fixture carries).
5. Merge rule, pinned with three constructed cases: an entry merges with the entry of the same name, a leaf
   with text always appends, another element merges with the element of the same tag or appends.
6. Determinism: two runs on the committed set answer the same bytes.
7. `ruff check .` is clean and `python3 -m pytest` passes. No fixture changes, so no golden moves and no
   corpus pin moves.
8. Documents: `tools/README.md` and `docs/ARCHITECTURE.md` §1.1 state the generator rule and the read rule;
   `README.md` names the new test; `backlog.md` and `to-do.md` close the finding, and `agent-status.md`
   records the position. Only `agent-status.md` states a test count.
