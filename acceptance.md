# Acceptance — Piece 6, the splitter reads the owners' rules, and the error rule names its kinds

Criteria set 2026-11-15 for `to-do.md` Piece 6, the six findings the 2026-11-12 audit recorded in
`backlog.md` (`src/split_device_groups.py` and the error rule). Each item states the rule, the module that
owns it, the decision, and the test that pins it. A pin measures content: it reads the table a module
returns, the split XML file a run wrote, or the `.tf` bytes a run wrote, and no pin reads the tracking
markdown. A pin that fails on content is a finding recorded in `backlog.md`, not a pin to relax.

Gate before commit: `ruff check .` clean, and the full `python3 -m pytest` with every pin passing and no
skips. Baseline before this piece: 1,673 pins in 50 test modules, all pass, no skips, exit 0
(`/tmp/opencode/baseline_piece6_pytest.txt`), measured 2026-11-15. Counts by module are in
`/tmp/opencode/collect_before_piece6.txt`. No pin may be weakened; a pin may change what it asserts when the
rule changes, and each such change is recorded in the next section.

Two items keep a source scan, and each states why content cannot show its rule. Item 1's rule is "no module
writes a file outside the single writer": an element writer can produce the same bytes as the single writer for
the same tree, so a run shows only the trailing LF, not which writer wrote the file, and the scan is what holds
the rule for a module that could add a writer later. Item 5's rule is "the extraction states no lookup of its
own": a branch that cannot fire cannot be shown by a run at all. Each of those two items keeps a content pin as
well, and each item has at least one pin that fails on the code before the change.

What the splitter writes is not the codebase the gate reads: the split XML files are not the unit set or the
codebase root set, so the gate pins (`tests/test_sanity_gate.py::test_splitter_output_has_no_tf_for_the_gate`)
hold only that the splitter writes no data file. The pins for the splitter's own output read the split files as
the bytes the run wrote.

## Pins that changed

A pin changes when the rule it measures changes. Each change is recorded here, with what the pin asserted
before. A pin that cannot fail before the change says so.

- `tests/test_write_path.py::test_one_function_writes_bytes_and_no_other_module_writes_a_file`: the writer scan
  now reads the element writer shape (`ET.ElementTree(`) as well as `write_text`, `write_bytes`, `os.linesep` and
  `open(...'w')`. Before: the scan read only the four words, so a module that built an element tree and wrote it
  was not in the set. Fails before the change, on the splitter.
- `tests/test_multi_device_template.py` (four splitter pins: `test_splitter_joins_template_and_device_group_by_device`,
  `test_splitter_copies_the_template_stack_by_device`, `test_splitter_copies_no_template_without_a_shared_device`,
  `test_splitter_leaves_the_source_tree_intact`,
  `test_splitter_merges_shared_sections_without_touching_the_source`): the helper now parses through the door
  (`xml_input.parse_xml`) instead of `ET.parse`, so the pin hands a `ParsedSource` and the extraction takes the
  table row instead of a name. Before: the helper returned the root element with no line map, and the extraction
  looked the name up in the tree. Fails before the change at the read of the contract, because the pre-change
  functions take a root. The asserted content is unchanged for the three pins that read the copied entries, and
  the stack pin reads the row through the table key.
- `tests/test_edge_cases.py` (two quote pins: `test_splitter_finds_dg_with_single_quote_in_name`,
  `test_splitter_finds_dg_with_double_quote_in_name`): the pin reads a row from `parse_device_groups` and hands
  the row, so it states no lookup of its own. Before: the pin named the device group and read the returned tree.
  Fails before the change, at the read of the contract.
- `tests/test_variables.py::test_the_record_refuses_two_entries_that_name_one_variable`: adds the assertion that
  the run prints the shape an unexpected error takes (the error line and the traceback), because a `ValueError`
  raised inside the tool is no longer a refusal. Before: the pin asserted exit 1 and the message, and the run
  printed the refusal line with no traceback. Fails before the change. The message half and the no-record half
  are unchanged.
- `tests/test_safe_input.py::test_a_copied_element_has_no_line`: the docstring claim changes, the assertion does
  not. The splitter records the line of the source entries it reads, and still gets no line for a copy. Before:
  the claim said the splitter never asks for a line. It cannot fail before the change, because the copy answers
  None on both sides; it is recorded here because the claim it states moves.
- `tests/test_parse_helpers.py::test_the_value_helpers_read_the_text_the_read_layer_states`: unchanged.
  `_device_names` keeps the entry as its argument, because the join reads devices as a set and the line is the
  row key, not the device order. It cannot fail before the change.

## 1. The split files go through the single writer

Rule: `docs/ARCHITECTURE.md` §6 — one function writes a file (`write_path.py` `write_file`), and no module of the
tool writes a file outside it. `LF` is the only line ending a run writes.

Decision: the splitter serializes the tree to text (`ET.tostring(..., encoding='unicode', xml_declaration=True)`)
and hands that text to `write_file`, so the byte rule is enforced at the print site and not in an operator note.
The splitter owns its own output path: the split files are not the unit set or the codebase root set, so the
splitter names no builder from `write_path.py` and keeps its own output directory rule
(`docs/DEVICE_GROUP_SPLITTING.md`). The text ends with `LF`, because the single writer writes text with `LF` and
the element writer wrote no final line.

Measured before the change: a split file ended with the closing `>` byte and no `LF` (`od -c`), and the writer
scan named no writer for the splitter (`src/split_device_groups.py` line 281, `tree.write(output_file, ...)`).

Owner: `src/write_path.py` (the byte rule and the one writer), `src/split_device_groups.py` (the print site).

Pins:

- `tests/test_write_path.py::test_the_splitter_writes_through_the_single_writer` — source scan, for the reason
  stated above: the splitter reads `write_file` and states no writer of its own. Fails before the change.
- `tests/test_write_path.py::test_one_function_writes_bytes_and_no_other_module_writes_a_file` — the scan pin
  changed as recorded above. Fails before the change.
- `tests/test_split_device_groups.py::test_a_split_file_is_the_text_the_single_writer_writes` — content: the bytes
  a run wrote for one device group hold no CR, end with `LF`, and read back through the door as the tree the run
  built for that group. Fails before the change (no trailing `LF`).

## 2. The file name is the naming rule, with a collision decision

Rule: `src/naming.py` §5 — a name is the §5 shape of the name, stated once there, and no module defines a second
one. A name that sanitizes to nothing is `UNNAMED`.

Decision: the file name is `naming.sanitize(name) or UNNAMED` plus `.xml`, so the splitter states no second
naming rule and keeps no character of its own. The collision decision is **refuse**, not number. Two names that
read the same §5 shape name one file, and the numbering a run would pick depends on the order the entries appear
in, which §6 says is not a rule a run may depend on. The refusal is an input-layer refusal
(`xml_input.UnsafeInputError`), so it prints the refusal line and exits 1, and no file is written: every name is
resolved and refused before the output directory is made. The message names both source names and the file name
they read to, so the operator can tell which entry is the other one.

Measured before the change: the file name was the name with `/` and a space replaced, so a name that stated any
other character kept it (`DG-Internet.xml`, and a device group named `.` wrote `..xml`), and the two names `DG/A`
and `DG A` wrote one file, `DG_A.xml`, where the second write replaced the first.

Owner: `src/naming.py` (the rule), `src/split_device_groups.py` (the print site and the decision),
`docs/DEVICE_GROUP_SPLITTING.md` (the decision as documented).

Pins:

- `tests/test_split_device_groups.py::test_the_split_file_name_is_the_naming_rule_applied_to_the_name` —
  content: a run writes `dg_internet.xml` for `DG-Internet` and `unnamed.xml` for a name that sanitizes to
  nothing, read through `naming`. Fails before the change.
- `tests/test_split_device_groups.py::test_two_names_that_read_one_file_name_are_refused_and_no_file_is_written`
  — content: `DG/A` and `DG A` are refused with exit 1, the message names both source names, and the output
  directory holds no file and was never made. Fails before the change.

## 3. The splitter tables are keyed by the source line

Rule: `docs/ARCHITECTURE.md` §2.3 — one entry produces one object, no parse method deduplicates by name, and no
method keeps a name-keyed dict. The source line is the identity the read layer records for an entry (F4.2), so it
is the key.

Decision: `parse_device_groups` returns one row per device-group entry, and each table row holds the name, the
source line, the path, and the entry element. The join answers the devices of the entry it read, so one entry
does not answer for two. The join's rows are in source line order, because the order the input states is
preserved on purpose (§6); the name sort is gone, so it is not a second order rule. The splitter reads the
`ParsedSource`, not a root, so the line is the same line the reports read, and the copy rule holds: a copy has no
line, so the pins that read a split file read the source row for its line.

Measured before the change: two device-group entries named `DG-Dup` answered one row, wrote one file, and the
file held the first entry while the join copied the templates of both entries (the device sets were merged by
name); the join order was the name sort (`T-a` before `T-b`) when the source stated `T-b` first.

Owner: `src/split_device_groups.py`, `docs/ARCHITECTURE.md` §2.3 and §6, `src/xml_input.py` (the line map).

Pins:

- `tests/test_split_device_groups.py::test_the_splitter_tables_are_keyed_by_the_source_line` — content: the keys
  of the three association tables are the source lines `line_of` answers for the entries the run read, and each
  row names its own entry. Fails before the change.
- `tests/test_split_device_groups.py::test_a_repeated_device_group_name_writes_one_file_per_entry` — content: two
  entries with one name write two files, each holding its own entry, read back through the door. Fails before the
  change.
- `tests/test_split_device_groups.py::test_two_entries_with_one_name_are_two_rows_that_answer_their_own_devices` —
  content: for each of two same-named entries the row holds only that entry's devices, and the tree the run built
  for a row copies only the template that targets that row's device. Fails before the change.
- `tests/test_split_device_groups.py::test_the_join_answers_the_rows_in_source_line_order` — content: two template
  entries that list one shared device, stated in the content in an order an alphabetical name sort would change.
  Fails before the change.

## 4. The shared merge merges by path and name and keeps the path

Rule: `docs/DEVICE_GROUP_SPLITTING.md` (this item's owner document) — several `shared` sections merge into one,
and the dedupe is the pair (path, name): an entry belongs to the level the container names, so a name at two
depths is two entries, and each entry keeps the path it sits at. This is the same level rule the parse set states
for `member` lists (`docs/ARCHITECTURE.md` §2.3, and `_list_values` reads only direct children).

Decision: the first occurrence of a path is the container in the merged section, the content that path states
comes from that first occurrence, and entries are appended at their own path, deduped by (path, name) at that
level. An entry inside an entry travels with the entry copy that holds it, because the level the field names is
the level the dedupe reads.

Measured before the change: the dedupe read `findall('.//entry')`, so a name matched at any depth — content with
`address/entry[x]` in one section and `address/group/entry[x]` in another dropped the second `x`, and the `group`
path was gone; an unmatched entry from a later section was appended directly under the container, so content with
`interface/virtual-wire/units/entry[y]` in a second section wrote `y` as `interface/entry`.

Owner: `src/split_device_groups.py`, `docs/DEVICE_GROUP_SPLITTING.md`.

Pins:

- `tests/test_split_device_groups.py::test_the_merge_keeps_an_entry_at_the_path_it_sits_at` — content: a nested
  entry stated in a second `shared` section is read back at its own path in the split file. Fails before the
  change.
- `tests/test_split_device_groups.py::test_the_merge_dedupes_the_pair_path_and_name_at_its_own_level` — content:
  one name at two depths keeps both entries, and a second entry with the same name at the same path is merged
  once. Fails before the change.
- `tests/test_split_device_groups.py::test_the_run_writes_one_container_per_path` — content: the tree the run built
  for a row holds one container per path, and an entry is read back under the path its row states. Fails before
  the change, because the pre-change code named the container per kind (`templates` for a row at `template`) and
  built an empty container for a second entry at a path.
- `tests/test_split_device_groups.py::test_an_empty_shared_section_writes_no_container` — content: a `shared`
  section that states no entry writes no container. Fails before the change, because the pre-change code wrote a
  container for every `shared` section the export had, empty or not.
- `tests/test_multi_device_template.py::test_splitter_merges_shared_sections_without_touching_the_source` — the
  unchanged half of the rule: the merge copies, so the source keeps its own entries. Changed signature only; it
  fails before the change at the read of the contract, as recorded above.

## 5. The extraction answers through the row it was given

Rule: `src/split_device_groups.py` — the extraction takes the table row, so the lookup the dead branch guarded
against cannot exist: every row names an entry the run read, and the answer is never the absent answer.

Decision: remove the branch, because the row is the entry. `extract_device_group_config` takes the row, states no
lookup, and cannot answer None, so the warning print and the troubleshooting row in
`docs/DEVICE_GROUP_SPLITTING.md` are gone with it. Making the extraction able to fail would need a rule that the
table already read an entry the run did not read, which is not a state the tool can reach.

Measured before the change: the branch could not fire — `parse_device_groups` named only entries that were in the
tree, so a run never printed `Could not extract config for {name}`. A branch that cannot fire is why this item
keeps a source scan.

Owner: `src/split_device_groups.py`, `docs/DEVICE_GROUP_SPLITTING.md` (troubleshooting table).

Pins:

- `tests/test_split_device_groups.py::test_the_extraction_states_no_lookup_and_no_warning` — source scan, for the
  reason stated above: the method takes the row, states no `findall` lookup of its own, answers no absent value,
  and prints no warning. Fails before the change.
- `tests/test_split_device_groups.py::test_the_extraction_answers_through_the_row_it_was_given` — content: for each
  row the tree the run built holds that row's own entry, so the row and the tree name the same entry. Fails
  before the change, at the read of the contract.

## 6. `is_refusal` names only the input-layer exceptions

Rule: `src/panorama_to_terraform.py::is_refusal` (criterion 5) — a refusal is the run's own decision to stop
before it writes, and anything else is an unexpected error and keeps its traceback. The input layer states its
refusals as two exceptions: `xml_input.UnsafeInputError` (with `source_fetch.SourceFetchError` as a subclass) and
`xml.etree.ElementTree.ParseError`.

Decision: the refusal kinds are the two input-layer exceptions, and a plain `ValueError` raised inside the tool is
an unexpected error, so it keeps the shape `failed()` states: the error line, the traceback, exit 1. The rule that
refuses a pair with two sources (`site_data.record_pair`, §9 rule 4) raises a plain `ValueError`, so the run shows
it as a failure and not as an input refusal. The pins that call a data-module function directly
(`pytest.raises(ValueError)`) read the rule, not the entry point, so they are unchanged, and the fetch pin that
reads a `SourceFetchError` reads a subclass of the input-layer kind, so it is unchanged.

Measured before the change: content with two certificate entries named `AP-1` and `AP_1` printed
`Error: rejected '...': name ap_1 states two values: 'AP-1' and 'AP_1'` with exit 1 and no traceback.

Owner: `src/panorama_to_terraform.py::is_refusal`, read by both entry points; `src/xml_input.py` (the kinds).

Pins:

- `tests/test_safe_input.py::test_the_refusal_kinds_name_only_the_input_layer_exceptions` — content: the rule
  answers True for `UnsafeInputError` and `ET.ParseError` and False for a plain `ValueError`, read through the
  function itself. Fails before the change.
- `tests/test_variables.py::test_the_record_refuses_two_entries_that_name_one_variable` — content, as recorded in
  the pin-change section: the entry point prints the traceback shape for this content and exits 1, and the message
  still names both source names. Fails before the change.
- `tests/test_robustness.py` and `tests/test_safe_input.py` clean-failure pins (hostile input, over-limit input,
  a directory as input): unchanged, and they cannot fail before the change, because every material they read is
  refused through an input-layer exception on both sides of the change.

## Measurement

Gate, measured 2026-11-15 against the committed tree: `ruff check .` clean, and the full
`python3 -m pytest` = 1,687 pins in 51 test modules, all pass, no skips, exit 0, 355.14 s (257.51 s on the working
tree before the documents were committed). Counts by module: `/tmp/opencode/piece6_after_collect.txt`. The run
output is `/tmp/opencode/piece6_committed_pytest.txt`, and the failing set is `/tmp/opencode/piece6/before_failing.txt`.

Baseline before the change: 1,673 pins in 50 modules, all pass, no skips (`/tmp/opencode/baseline_piece6_pytest.txt`,
counts in `/tmp/opencode/collect_before_piece6.txt`). The change adds 12 pins in
`tests/test_split_device_groups.py` (50 modules → 51), 1 in `tests/test_write_path.py` (19 → 20), and 1 in
`tests/test_safe_input.py` (36 → 37).

Failing set before the change, measured in a scratch tree of the committed `src/` with the pins as they now read
(`/tmp/opencode/piece6/before`): 23 pins fail, and the same 23 pass in the working tree.

- `tests/test_split_device_groups.py`: all 12.
- `tests/test_edge_cases.py`: the two quote pins.
- `tests/test_multi_device_template.py`: all 5 splitter pins.
- `tests/test_variables.py`: `test_the_record_refuses_two_entries_that_name_one_variable`.
- `tests/test_write_path.py`: both pins.
- `tests/test_safe_input.py`: `test_the_refusal_kinds_name_only_the_input_layer_exceptions`.

Two pins record a claim that moves without a measurement change, so they pass before the change:
`tests/test_safe_input.py::test_a_copied_element_has_no_line` (docstring claim) and
`tests/test_parse_helpers.py::test_the_value_helpers_read_the_text_the_read_layer_states` (unchanged).

Before-change content, recorded in `/tmp/opencode/piece6/`: the collision pair writing one file
(`p_collision.xml`, `out_collision/DG_A.xml` holding the second entry), a split file with no final line
(`od -c` of `c.xml`), `DG-Internet.xml` and `..xml` for the name `.` (`p_unnamed.xml`), one row for two
same-named entries (`p_repeat.xml`), the join order after the name sort (`p_join_order.xml`), the merge depth
(`p_depth.xml`), a nested entry merged at the container level (`p_nested.xml`, `p_nested_second.xml`), and the
plain `ValueError` printed as a refusal with no traceback (`p_plain_value_error.xml`).

Finding, left to Piece 7: `docs/LICENSING.md` states 130 lines for `src/split_device_groups.py` and calls it
"the upstream, unchanged". It is now 383 lines and no longer upstream code, so the count and that row need
Piece 7's pass over the licensing document.

