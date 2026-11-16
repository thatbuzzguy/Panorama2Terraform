# Acceptance — Piece 7, the indexes and the documents agree with measurement

Criteria set 2026-11-16 for `to-do.md` Piece 7, the findings the 2026-11-11 audit recorded in `backlog.md`
against the indexes, the documents, and the pins that read markdown. Each item states the rule, the owner
document, the decision, and the measurement that closes it.

Rules this piece works under, from `agent-status.md` §Rules to keep when writing documents:

- One owner document per rule; every other document links to it.
- No test counts in a document. A document names the test that pins a rule.
- A claim about what the tool does names the module or the test that holds it, and a test name a document
  states must be a test the test set defines.
- A document explains a table and never restates it row by row, so a count a document states must either
  agree with the measurement or be stated as derived from the table.

Gate before commit: `ruff check .` clean, and the full `python3 -m pytest` with every pin passing and no
skips. Baseline before this piece: 1,687 pins in 51 test modules, all pass, no skips, exit 0, measured
2026-11-15 (`/tmp/opencode/piece7_collect_baseline.txt`, counts by module). No pin may be weakened; a pin
that fails on content is a finding recorded in `backlog.md`.

## The two decisions this piece sets

**1. The test set does not read document wording.** A wording edit is a document review, not a code
failure, so a pin cannot hold it: a pin that asserts a phrase in a document fails when the phrase is
reworded correctly. The test set keeps one pin for the index rule — that a name is present — in one place,
`tests/test_layout.py`. The wording checks move to `tools/check_documents.py`, a developer script named by
`tools/README.md`. The tool prints what disagrees and exits non-zero; it is not part of the gate, and the
test set does not read it (`docs/ARCHITECTURE.md` §1.1: `tools/` is not on the test path). A pin that
reads a markdown file reads an index, not its wording.

**2. The test set is named by the root index.** `tests/` gets no index of its own, because the root index
already names every test module, so completing the list was a matter of adding `tests/conftest.py` and the three
files in `tests/responses/`. That keeps the index set `AGENTS.md` states. `docs/ARCHITECTURE.md` §1.1 states the
rule, the pin measures it, and the root index is the owner of the test-set naming.

The pin excludes `.github/`: the two template files sit outside every index, which `backlog.md` records as
its own finding, so a pin cannot read them as a violation. `tests/fixtures/` and `tests/golden/` are sets the
documents describe by rule, not file by file, so the pin reads the test modules and the response set only.

## Criteria, by item

### 1. The §1 module table names every `src/` module

`docs/ARCHITECTURE.md` §1 must name all 22 modules in `src/`. Measured: 21 named, `commit_actions.py`
missing. The row is added with its role and its rule. Measured 2026-11-16: 22 rows for the 22 modules.

### 2. The test set is named by one index

The root index must name every test module (51 before this piece, 52 with `tests/test_layout.py`),
`tests/conftest.py`, and the three files in `tests/responses/`. Measured before: the root index already named all
51 test modules, so the change is the harness and the response set. Measurement after: every test module named,
`tests/conftest.py` named, and the three response files named.

### 3. A document that names a test names a test that exists

Measured 2026-11-16 with a scan of every markdown file (141 claims, `tests/<module>.py::<name>`), and the tool
now checks every claim at each run. Four claims named a test that did not exist; each takes the real name:

- `backlog.md` §Parser extraction gaps named `test_report_declares_the_profile_name_column`. No pin holds
  that rule, because the pinned provider declares no profile-name attribute, so the claim becomes "no pin
  holds it", not a name.
- `docs/ARCHITECTURE.md` §4.9 named `test_parse_rip`; the pin is
  `tests/test_parse_network.py::test_parse_rip_reads_the_levels_the_table_states` (line 555).
- `docs/API_CONVERSION_PATH.md` §1 named `test_the_module_defines_no_second_naming_rule`; the pin is
  `tests/test_site_data.py::test_site_data_defines_no_second_naming_rule` (line 770).
- `to-do.md` Piece 4 and `backlog.md` §Parse set named `test_a_number_field_prints_the_signed_integer_the_shape_states`;
  the pin is `tests/test_protocol_object.py::test_value_shape_is_the_reader_inverse_for_every_shape_word`
  (line 564), which asserts `value_shape('-1')` as `number`.

A claim that names a helper or a module constant (`_reference_names`, `_parse_every`, `_name_guards`,
`PRINTED_BY_ANOTHER_BLOCK`) is not a pin claim; the tool reads it as a name the module defines. The document
record of a pin that this piece removed names the pin without a claim, so the tool does not read it as one.

### 4. The counts a document states agree with measurement

- `docs/COVERAGE_MATRIX.md` states 40 rows and shows 40. `resource_mapping.COVERAGE_MATRIX` holds 42: the
  `panos_certificate_import` and `panos_certificate_profile` rows are missing from the document table. Fix:
  add the two rows, and state the count as derived from the table instead of as a stored number.
- `README.md` states 34 rows for the same table. Fix: the root index links to the owner document and states
  no count.
- `docs/LICENSING.md` §The split, measured and §The inherited set are stale. Re-measured with `git blame` at
  commit `ac7609e` (2026-11-16), by author: whole tree 2,064 upstream (`devnullNZ`, 3.3%) against 60,242 ours
  (`Ryan Brown`); `src/`, `tests/` and `tools/` 503 (3.2%) against 52,690; commits 9 against 195. The inherited
  set is 18 files with 2,064 upstream lines, and the total is stated as the sum of the rows. The document names
  the commit it was measured at, so `tools/check_documents.py` re-measures at that commit and a later edit does
  not move the count. `docs/LICENSING.md` is the owner of the split, so `README.md` keeps no counts and links
  to it.
- The notice table calls `src/panorama_to_terraform.py` and `src/split_device_groups.py` "the upstream,
  unchanged". Measured at `ac7609e`: 408 upstream lines in a 7,407-line file, and 68 in a 383-line file.
  Neither is unchanged, so the table states the notice as the header text and the split as the measured share.
  The table is also incomplete: 4 of the 22 `src/` modules carry the notice, so it names `src/xml_input.py`
  and `src/naming.py` as well.
- The fixture set measures 71 (68 accepted, 3 refused by the F3.8 rule), which `agent-status.md` states and
  `tests/test_build_kitchen_sink.py` measures. No document states a fixture count, so nothing to correct;
  the pins that state the printed set as a fixed number are the separate audit finding that stays in
  `backlog.md` (out of this piece).

### 5. The index rule has one pin, and the wording checks sit outside the test set

`tests/test_layout.py` holds one pin, `test_the_indexes_name_every_document_under_them`, that measures the rule:
each index names every document under it, and the root index names every test module, `tests/conftest.py` and
the three response files. It reads only the four index scopes, so `.github/` is outside the rule and stays an
open finding in `backlog.md`. The pin cannot read wording.

The two pins that read `backlog.md` keep their facts as data in the test and stop reading the markdown. The five
pins that read `docs/` prose move to `tools/check_documents.py`, which is not part of the test set: it reads the
matrix through `ast` and the split through `git blame` at the commit the document names, and the test set does
not read it. Decision 1 in §Decision record records this as a departure from the audit's "everything through
asserts", with the reason: a pin that reads document wording fails when the wording is rephrased.

The root index names every test module and the response set, so no `tests/` index is needed, and §1.1 states the
rule that the pin measures.

### 6. Each row shape has one name

`ROW_FIELDS` is four different row shapes in one flat namespace, so a pin that reads one table can read the wrong
shape. Each table takes the name of its own rule: `SITE_ROW_FIELDS` (`src/site_data.py`), `ACTION_ROW_FIELDS`
(`src/commit_actions.py`), `IMPORT_ROW_FIELDS` (`src/import_blocks.py`), `MATRIX_ROW_FIELDS`
(`tests/test_coverage_matrix.py`, the test that reads the matrix row shape). There is no `ROW_FIELDS` left, and no
record shape to rename: `src/record_data.py` and `src/rules.py` do not exist, and no module defines
`RECORD_FIELD_SHAPE` or `RECORD_RULE_SHAPE`.

Each shape is named in the rule column of its §1 table row, `MATRIX_ROW_FIELDS` on the `resource_mapping.py` row
because the shape belongs to the matrix the module defines. The pins that read the shapes read them through the
names, and `docs/ARCHITECTURE.md` §1.1 keeps only the rule, with the shape names living in the table rows.

## Pins that change

- `tests/test_layout.py::test_the_indexes_name_every_document_under_them` (new, the one index-rule pin): reads the
  four indexes and the tree, and asserts the naming rule. It cannot read wording, and it does not read
  `backlog.md`.
- The pin in `tests/test_api_requests.py` named `test_the_module_is_named_in_the_architecture_module_table`:
  removed. Both halves are the index rule, and the new pin measures them for all 22 modules, not for one.
- `tests/test_api_requests.py::test_the_committed_op_response_shows_one_shape_and_names_no_live_fact`:
  loses its `docs/API_CONVERSION_PATH.md` wording assert, which moves to the tool. The code half stays.
- The pins in `tests/test_container_coverage.py` named `test_the_architecture_document_states_the_console_line_shape_once`
  and `test_architecture_points_at_the_table_instead_of_restating_it`: removed, and the checks move to the tool.
  The module keeps the code half of the console-line rule (no second console line).
- `tests/test_api_path.py::test_a_predefined_entry_read_reports_the_place_as_a_finding`: loses the
  `backlog.md` assert. The fact it asserted is the scan's own rule, which the pin already measures: the scan
  answers no destination for a built-in place.
- `tests/test_sanity_gate.py::test_the_run_wide_findings_print_through_the_join`: loses the `backlog.md`
  assert. The fact it asserted is data in the pin: the join reports one response, so the run-wide direction
  prints with no file, which the pin measures. The pin also gained the row-count assert that the tool's
  table check needs.
- `tests/test_site_data.py::test_the_fields_print_in_the_declared_order` and the pins that read the row shape
  in `tests/test_coverage_matrix.py`: the name changes, the asserted content does not.

Pin count: 1,687 before, 1,685 after (3 pins removed with the wording checks, 1 index pin added), 51 modules before
and 52 after, because `tests/test_layout.py` is new.

## Measurement

Gate, measured 2026-11-16:

- `ruff check .`: clean.
- `python3 -m pytest`: 1,685 pins pass in 52 test modules, no skips, 4 min 24 s (6 min 25 s on the run before the
  markdown was finished, the same set).
- `python3 tools/check_documents.py`: no finding, on the claims in the markdown set, the matrix table, the
  licensing split at commit `ac7609e`, the wording checks, and the test counts.

Counts by module that changed: `tests/test_layout.py` is new at 1 pin, `tests/test_api_requests.py` 25 to 24,
`tests/test_container_coverage.py` 29 to 27. The other 49 modules are unchanged. Before the piece: 1,687 pins in
51 modules (`/tmp/opencode/piece7_collect_baseline.txt`). No pin was weakened: the three pins removed measured
document wording, and no pin that measures content was removed.

The two findings that stay open in `backlog.md`: the two `.github/` template files sit outside every index, and the
pins that state the fixture set as a fixed number.
