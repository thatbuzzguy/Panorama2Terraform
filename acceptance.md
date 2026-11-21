# Piece E10.3 acceptance review — a new site instantiated from an existing template

Review record for commits `1977366` (the fixture and the pins) and `73764c2` (the decision and the
measurement). The piece was not redone here: every criterion below is met, and only what the review
found wrong was changed. The two commits are not pushed.

## Criterion 1 — the decision is grounded in the tool's own read on the fixture (met)

Re-read 2026-11-21 through `entry_coverage`/`unit_manifest`, `site_data`, `reference_edges`,
`commit_actions`, the scope block emitter and the gate on `tests/fixtures/template_no_device.xml`.
Every value `docs/TEMPLATE_STACK_DEPLOYMENT.md` §4 states agrees:

- `identity_of` answers `Shared` for `device_group`, empty for `vsys`, `vsys_device` and
  `template_stack`, `Remote-Networks` for `template`. `facts_of` answers
  `('', '', 'Remote-Networks', '', '')`, so `Shared` is the parse fallback and not a fact value.
- The digest is `93488ed8` and the directory is `remote_networks_93488ed8`. The device group unit is
  `newsite_fw_9f79c4e2`. Both rows are written.
- `parse_associations` answers four empty tables (`device_groups`, `templates`, `template_stacks`,
  `stack_templates`). `reference_edges.build_rows` answers no row. `order` answers `after` empty on
  both rows, with rank 1 for the template unit and rank 2 for the device group unit — the identity
  order, read through `reference_edges.order`, which starts the walk from the identity-smallest ready
  unit. `container_coverage.CONTAINER_TABLE` names no row for `device-group/entry/templates`, and
  `api_requests.LIST_JOIN` has no key for it.
- `site_data.build_rows` answers no row and `value_variables` answers no name for either unit, so the
  run writes no `SITE_DATA.json` and no `site.auto.tfvars`; `provider.tf` prints
  `hostname = var.hostname` with no `target`, and `variables.tf` declares no `target`.
- `commit_actions.build_rows` answers four rows: `panos_commit` and `panos_push_to_devices` on the
  template fact for the template unit, and the same two on the device group fact for the device group
  unit. The push block states no `devices`.
- The scope file prints the template block with the empty `panorama` sub-block, `name`,
  `default_vsys = "vsys1"`, `description`, and no device; the device group block prints
  `templates = [ "Remote-Networks" ]` and no device members.
- The gate reports no finding on the run and writes no `MANUAL_SETUP_REPORT.txt`; the per-entry report
  reads 2 `emitted` entries, one per entry the ledger names.

## Criterion 2 — a fact only a live target states is not asserted (met)

`backlog.md` holds only the device the operator adds and the serial a push target names, and no pin
asserts either.

## Criterion 3 — one owner document per rule (met)

`docs/TEMPLATE_STACK_DEPLOYMENT.md` §4 is the single statement of the decision. `docs/CODEBASE_ASSEMBLY.md`
§3 rule 2, §5 rule 7, §8 rule 6, §9 rule 8, §10 rule 2 and §12 each state their own rule and link to §4.
`docs/README.md` names §4 in the index row and in the rule-ownership table, and names the other rule
owners (`unit_manifest.facts_of`, `site_data.py`, `reference_edges.py`, `commit_actions.py`, the scope
block emitter). No module changed, so no module states a second rule. The import rule is read
independently: no test module imports another test module, and no `src/` module imports anything from
`tests/`. The index rule is pinned by `tests/test_layout.py::test_the_indexes_name_every_document_under_them`,
which passes.

## Criterion 4 — pins, one per fact, in the module that owns the rule (met)

Each pin exists, passes on its own, and states only the fact §4 reads through that module:

| Fact | Pin | Module that owns the rule |
|---|---|---|
| The empty device fact, the identity, the digest, the directory | `tests/test_unit_manifest.py::test_a_template_entry_no_device_names_keeps_the_device_fact_empty` | `unit_manifest.py` |
| No site row, no `.tfvars` line, no `target` | `tests/test_site_data.py::test_a_unit_that_names_no_device_writes_no_site_row_and_no_tfvars_line` | `site_data.py` |
| No edge row for the device group's template list, `after` empty, ranks in the identity order | `tests/test_reference_edges.py::test_a_device_group_that_lists_a_template_records_no_row` | `reference_edges.py` |
| The printed blocks | `tests/test_scope_objects.py::test_a_template_entry_with_no_device_prints_its_names_and_no_device` | the scope block emitter |
| The commit and push blocks name the fact `named_fact` selects | `tests/test_commit_actions.py::test_a_unit_with_no_device_fact_names_the_fact_the_export_declares` | `commit_actions.py` |

No pin holds a set the tool can read by rule: the edge pin reads `CONTAINER_TABLE`, `LIST_JOIN` and
`membership_lists()` rather than restating them.

## Criterion 5 — the pins that state the printed fixture set read the measured value (met)

Measured independently over `tests/fixtures/`: 70 `.xml` files, 67 accepted, 3 refused
(`hostile_bad_control_char.xml`, `hostile_billion_laughs.xml`, `hostile_xxe.xml`), and 66 read, because
the record is not an input. `tests/test_build_kitchen_sink.py` (67 accepted, 66 read, 3 skipped),
`tests/test_api_requests.py` (5 response files, 67 accepted, 3 refused) and `tests/test_policy_order.py`
(67 accepted fixtures) state the measured value, and all three pass. The corpus edge, gap, property,
ownership and site-row sets did not move, and the `.tf` goldens are unchanged.

## Criterion 6 — the gate, single-threaded, with measured counts (met)

Measured 2026-11-21 on the reviewed tree: `ruff check .` clean at `py310`, `ruff format --check .` clean
on the 104 Python files, `python3 tools/check_documents.py` reports no finding, and
and reports no finding, and
`python3 -m pytest` passes 1,732 pins with 4 skips for the missing `tflint` binary — 1,736 pins in 53
test modules, in 246.55 s. `terraform` is present on this machine, so the pins that read the live
provider schema ran rather than skipped; the 4 skips are the `tflint` pins in
`tests/test_sanity_gate.py`.

## Criterion 7 — no test count in a document, every named test exists, plain wording (met)

`tools/check_documents.py` reads the documents for a test count and for a test name that does not exist
and reports no finding. The counts the pins state are measurements inside test docstrings, which is where
the fixture-set count rule puts them. No emoji in any markdown; the wording is the project's literal
vocabulary.

## Criterion 8 — the tracking markdown carries the current state (met, with the corrections below)

`PLAN.md` names the design record as the place the three decisions are read and holds no Epic 10 piece
detail; `to-do.md` states no open piece; `backlog.md` holds the two live-only facts.

## Findings and corrections

1. `docs/CODEBASE_ASSEMBLY.md` still named Piece E10.2 and Piece E10.3 as open work in three places —
   the top of the document, the end of §2, and the end of §14 — which contradicts the landed state in
   `PLAN.md` and `docs/README.md`. The three sentences are removed; the zero-change plan half of §7 is
   the only part of the document that stays open.
2. The pin-delta baseline was wrong. Read through the per-module collection counts: 1,726 pins in 53
   modules at `4351ca0`, 1,730 in 53 modules at `4adecbd` (Piece E10.2), 1,736 in 53 modules on the
   reviewed tree. The piece adds six pins, so the six is the delta from Piece E10.2, not from `4351ca0`
   (the delta from `4351ca0` is ten). Of the six, five are the pins named in §4 and the sixth is the new
   fixture's instance in the corpus-parametrized gate pin `tests/test_sanity_gate.py` (its count moves
   113 to 114), because the pin reads `corpus_fixtures()` and the fixture is accepted.
3. `acceptance.md` as written named `entry_coverage.identity_of`; `identity_of` is
   `panorama_to_terraform.PanoramaParser.identity_of`. The decision itself names the right owner, so this
   is a review record correction only, not a code change.

The corrections are documentation only, so no pin moved: the counts above are the same set before and
after them.

## Criterion 9 — the commit style (met)

The two piece commits follow the conventional-commits style and are not pushed. The review's
corrections are one `docs(tracking)` commit.
