# To Do

The tracking markdown for the completed Epic 8 phases is removed here; the git history and the owner
documents hold it. Epic 8 is complete. The open pieces are the actionable findings the 2026-11-11 and
2026-11-12 audits recorded in `backlog.md`. Each piece below names the rule it holds, the module that
states it, and the test that pins it. One piece is finished before the next is started.

## Current series

### Piece 1 — the test set reads one shared definition

Owner: `tests/conftest.py`. The findings are the import rule violation, the second definitions, and the
path builder, from `backlog.md` (measured 2026-11-11).

- [ ] Move the two helpers `test_real_or_report.py` imports from `test_policy_order` into
      `tests/conftest.py`, the one shared helper file (§1.1).
- [ ] State `RESOURCE_RE` once in `tests/conftest.py` with one capture group, and read it through that
      file from the four test modules that define their own copy.
- [ ] State `TERRAFORM` once in `tests/conftest.py` and read it through that file from the four test
      modules that define their own copy.
- [ ] Build the golden set path in `tests/conftest.py` (the one place the path to each set is built),
      and correct the regeneration note in `tests/test_golden_files.py` header, which names the case
      root as where the goldens live.

### Piece 2 — pins that measure nothing

Owner: `tests/conftest.py` and the pins named in `backlog.md` (measured 2026-11-11).

- [ ] Read the golden `.tf` set through `rglob`, keyed by the path from the case directory, in the four
      pins that compare an empty set with an empty set: `tests/test_data_blocks.py`,
      `tests/test_ownership.py`, `tests/test_reference_edges.py`, `tests/test_unit_manifest.py`.
- [ ] `tests/test_commit_actions.py`: assert the file exists, so a fixture that writes nothing is not a
      pass.
- [ ] `tests/test_api_requests.py`: pin a rule the module states, not the length of the test's own
      harness list.
- [ ] Read the hostile-fixture exclusion through the tool's read rule (`tool.refusal_reason` or
      `xml_input.check_bytes`) in every corpus pin, so the name rule is gone.

### Piece 3 — the parse set reads what its rows state

Owner: the parse methods named in `backlog.md` (measured 2026-11-12), and the coverage matrix rows.

- [ ] `parse_interfaces`: read `zone`, `virtual_router` and `tag` for every entry kind, and read both
      address shapes (`ip/entry` and `ip/member`); or state the fields as report-only on the interface
      row. Decide which, and make the property scan able to see the difference (the `captured_fields`
      rule that skips an empty value).
- [ ] Call `mark_skipped` in the 11 name guards that `continue` without a record, so the per-entry
      report keeps its one-line-per-entry rule.
- [ ] `parse_schedules`: skip a nameless recurring child through the record, so the report writer does
      not raise and the run does not leave half-written output.
- [ ] `_parse_router`: read the entry shape under `protocol/static-routes`, or state that shape on the
      virtual-router row.
- [ ] `_protocol_field`: use the shape rule for a number instead of `text.isdigit()`, and state the
      single-match limit.

### Piece 4 — naming and printing state one rule

Owner: `src/naming.py`, `src/panorama_to_terraform.py`, `src/sanity_checks.py`, `src/xml_input.py`, as
`backlog.md` (measured 2026-11-12) names them.

- [ ] Build the static-route block name from the route's own name, so the declaration index holds the
      name a reference can resolve (§5, one digest per name).
- [ ] Read `naming.UNNAMED` instead of hardcoding the fallback word in `declare_block_name`.
- [ ] Decide the collision rule for `printed_value`: refuse a name collision inside a unit, or key the
      record by the entry.
- [ ] State the order rule for nested keys once, so an object does not print in two orders at two
      levels, and make the two emitters read the table order their docstrings claim.
- [ ] State which layer owns the control-character rule, or make the gate read the value before the
      escape.
- [ ] State one whitespace rule for the value helpers (`_get_text`, `_get_members`,
      `_get_single_value`, `_protocol_field`, `_list_names`, and the splitter's `_device_names`).
- [ ] `UnitText.add_once`: keep a per-file once record, so header prose cannot stop a section.
- [ ] `generate_vpn_config`: print the `VALUE_VARIABLES` `key` as the reference the table states, or
      state the exception in the table.

### Piece 5 — the splitter reads the owners' rules, and the error rule names its kinds

Owner: `src/split_device_groups.py`, `src/naming.py`, `src/write_path.py`, `src/xml_input.py`,
`docs/DEVICE_GROUP_SPLITTING.md`, `docs/ARCHITECTURE.md` §2.3.

- [ ] Write the split files through `write_path.py`, so the single writer and the LF rule cover them.
- [ ] Build the file name through `naming.sanitize`, and add the collision decision for two names that
      sanitize to the same value.
- [ ] Key the splitter's tables by the source line, as §2.3 states, so a repeated device-group name is
      not answered by one entry.
- [ ] Merge the shared section by path and name, and keep each entry's path.
- [ ] Remove the dead branch, or make the extraction able to fail.
- [ ] `is_refusal`: state the refusal kinds as the input-layer exceptions, so a `ValueError` raised
      inside the tool keeps its traceback.

### Piece 6 — the indexes and the documents agree with measurement

Owner: the tracking markdown, `docs/ARCHITECTURE.md` §1 and §1.1, and the pins `backlog.md` names.

- [ ] Name `commit_actions.py` in the `docs/ARCHITECTURE.md` §1 module table. `api_to_terraform.py` is named
      there since F8.9, so this item covers the one module the table still does not name.
- [ ] Give `tests/` an index, or state in §1.1 that the test set is named by the root index, and name
      the three files in `tests/responses/`.
- [ ] Correct the three document pin claims that name a test that does not exist.
- [ ] Re-measure the counts the documents state (matrix rows against `COVERAGE_MATRIX`, the licensing
      split, the fixture set) and correct them, or state them as derived from the table.
- [ ] Keep the document-wording checks outside the test set, and pin the index rule in one place;
      migrate the pins that read `backlog.md` so a housekeeping commit does not fail them.

## Feature-sized items that stay blocked

Feature-sized items that stay blocked on a fact the tool cannot read offline are recorded in
`backlog.md` and are not pieces here: the four `*_policy_rules` types wait for the F3.5 rulebase
decision and a live target, a config entry inside a stack needs a provider location shape, the EDL
`certificate_profile` field needs a rule that makes the EDL site resolve names, the per-entry report
`profile_name` column needs a value the provider does not declare, and the path 2 live facts in
`docs/API_CONVERSION_PATH.md` §4 need a live target: the committed response set shows one shape per
accepted request shape and names no fact.

`ruff format` as a gate stays the next actionable slice outside this series (`backlog.md`,
Nice-to-Haves), with `tflint` integration after it.

## Rules the layout keeps

- `docs/ARCHITECTURE.md` §1.1 is the owner document for the layout. `AGENTS.md` names the tracking
  markdown set, and each index names every document under it, so a file outside an index is a finding.
- Import rule: `src/` is one flat namespace, so a module may import any `src/` module without a cycle.
  The one test that checks the rule reads only `src/`. A test may import `src` modules and
  `tests/conftest.py` through `importlib`; nothing under `tests/` may import another test module. `src/`
  may not import from `tests/`. `tools/` is not on the test path, so `tests/test_build_kitchen_sink.py`
  reads the fixture assembler through `importlib` on the path `tests/conftest.py` builds once.
- Path 2 adds two modules, `api_requests.py` and `api_to_terraform.py`, and both must be named in the
  `docs/ARCHITECTURE.md` §1 table. Both state no second naming rule, no second writer, no second
  console line, and no environment name, so the pins that scan the `src/` set read them with the other
  modules.
- The corpus is the directory the scan runs over. A hostile fixture in it changes the set the scan
  reports for the other fixtures, so pins that state the printed set name the fixture count. The fixture
  assembler reads the same set by rule: a fixture the F3.8 input rule refuses is skipped, and the record
  is not an input (`tests/test_build_kitchen_sink.py`). A committed API response is not corpus material, so
  it sits in its own set (`tests/responses/`), and the pins that state the printed fixture set are not
  changed by it (`docs/ARCHITECTURE.md` §1.1).
