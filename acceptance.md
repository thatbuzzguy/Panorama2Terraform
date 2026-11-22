# Acceptance — review record for Piece 11B.3 (2026-11-22)

Piece 11B.3 (ownership, edges and the plan order read over the merged record set, so an edge row and an `after`
fact can name a unit another run wrote) is reviewed at `baa6e2b` (the pins and the one `src/` change) and
`c11ffcb` (the tracking markdown), both not pushed. Every committed criterion is met by the tree. The review
corrected three counts, one comment, one wording claim and one over-long line, listed under Findings, and
committed them as one commit
for the `tests/conftest.py` comment and one for this record with the `backlog.md` counts and the `agent-status.md`
update. The measurements were re-run independently through the record modules themselves, single-threaded.

## Criteria, read against the tree

1. Each committed criterion, read against the tree, is met. This document is the review record.
2. The measurement, re-run through each record's `parse_rows` and `codebase_state.merge_rows` on the committed
   fixtures:
   - `tests/fixtures/address_groups.xml` as the codebase and `tests/fixtures/security_rules.xml` as the second run:
     the manifest 1 against 2 give 3 units, read through `unit_manifest.units`, and ownership 2 against 3 give 5
     rows. Neither run's own edge set names a pair; the merged rows name one row,
     `('production_dg_6ce3cc69', 'shared_45ca31c3', 'panos_address_group', 'Web-Servers')`, the referrer being the
     unit the second run built and the target the unit the first run built. Over the second run's own rows its two
     units rank 1 and 2 with an empty `after`; over the merged rows `shared_45ca31c3` ranks 1, `shared_a6577c11`
     ranks 2 with `after` naming it, and `production_dg_6ce3cc69` ranks 3 with `after` naming it, and that entry
     comes from the edge basis: the level basis alone names no dependency for that pair.
   - `tests/fixtures/reference_cycle.xml` as the codebase and `tests/fixtures/address_objects.xml` as the second
     run: manifest 2 against 1 give 3, ownership 4 against 5 give 9, edges 2 against 0 give 2. The second run's own
     rows answer no cycle; the merged rows answer the cycle the codebase wrote, grouped through the merged manifest
     row of `fw_a_example_com_4febb524`, a unit the second run did not build; both cycle units keep `NO_RANK`, and
     the second run's own unit `shared_45ca31c3` ranks 1.
   - `tests/fixtures/address_objects.xml` as the codebase and `tests/fixtures/address_objects_dg_override.xml` as
     the second run: 5 against 2 give 7 rows, and `('panos_address', 'Web-Server-1')` is the one group the merged set
     can hold from both runs. Each run's own group answers `declared`; over the merged group the rule answers
     `definition` for the row the codebase wrote and `override` for the row the second run built, naming the
     codebase's unit `shared_45ca31c3` through the shared-unit case, which the five scope facts state on their own.
   - corpus pair scan: the read rule accepts 67 fixtures, 59 of which state ownership rows, so the scan reads 4,422
     ordered pairs. 178 key counts are stated by both runs — 89 keys across 62 unordered pairs, read in both
     directions — and no merged ownership row names a unit only the other run built as the rows were written. 0 pair
     reads give a cycle whose two halves come from two runs, 0 give a membership row whose two sides come from two
     runs, and 337 give an edge the second run's own rows cannot name: 297 where both fixtures state ownership rows,
     and 40 where the second fixture states no ownership row at all, so its own edge set is empty. The two pairs
     that hold a cycle read across two runs, `interfaces_ethernet.xml` with `kitchen_sink.xml` and
     `report_grouping.xml` with `kitchen_sink.xml`, hold it inside one run's own unit set: each cycle names a unit
     that is in both fixtures, so neither half comes from the other run.
3. Single-owner claims. `baa6e2b` changed five files: `src/reference_edges.py`, `tests/conftest.py`,
   `tests/test_codebase_state.py`, `tests/test_ownership.py`, `tests/test_reference_edges.py`. The only `src/`
   change is the wording of `reference_edges.py` rule 1; rule 7, the unit order, is unchanged in the tree, so the
   commit message's "rule 1 and rule 7" is corrected here. `codebase_state.py` and `unit_manifest.py` are unchanged.
   `JOIN_KEYS`, `join_key` and `merge_rows` appear only in `codebase_state.py`, `units` only in
   `unit_manifest.py`, `LEVEL_KEYS` only in `reference_edges.py`, and `state_coverage.ownership_key` is still the one
   identity key rule; `LEVEL_KEYS` and the membership basis gained no second basis; the acyclic rule and its report
   section stay single; `ownership.py`'s decision, its seven emitters and the `disable_override` rule do not change.
   The single-owner scan pin reads the 24-module set clean, and no committed golden moved.
4. The three conditions in `backlog.md` are stated only as conditions, and no pin asserts them: the cross-run
   membership row, because the corpus holds 3 membership facts, each inside one fixture (`kitchen_sink.xml`
   Branch-Stack to FW-Template, `multi_device_templates.xml` Branch-Stack to HQ-Networks, `scope_objects.xml`
   Edge-Stack to Edge-Networks) and every fixture declares the membership name inside itself; the cross-run
   half-cycle, 0 pair reads; and the ownership findings and ancestor half, which reads `chain`, `from_parent`,
   `reason`, `line` and `container`, none of which `parse_rows` reads back. The counts reproduce, as stated in
   criterion 2, and the pins that mention a cross-run pair read the merged set itself rather than one of the three
   conditions.
5. The six pins exist, pass on their own, and sit in the module that owns the rule: 4 in
   `tests/test_reference_edges.py` (the module collects 43), 2 in `tests/test_ownership.py` (the module collects
   42). Each runs a committed fixture through `tests/conftest.py`'s `run_records` and reads every row through the
   record's own `parse_rows`, and none builds a row by hand. The read-back is stated once in `tests/conftest.py`
   (`record_rows`, `run_records` and `JOIN_RECORDS`), read through `sanity_checks.DATA_FILES` and
   `codebase_state.JOIN_KEYS`; `tests/test_codebase_state.py` reads it from there, and its pin assertions are the
   same as before the move — only the names changed. No test module imports another test module.
6. Index rule and import rule: `tests/test_layout.py::test_the_indexes_name_every_document_under_them` passes, no
   test module imports another test module (the only line in `tests/` that names another test module is a comment in
   `tests/test_schema_conformance.py`), no `src/` module imports anything from `tests/`, and the `src/` scan pins read
   the 24-module set unchanged.
7. Tracking markdown: `to-do.md` shows Piece 11B.4 open with no completed-piece narrative and no Phase 11A detail;
   `agent-status.md` carries the position and the measurement; `PLAN.md` agrees; `docs/MULTI_RUN_CODEBASE.md` §4
   rules 2 to 5 name the module and the tests that hold; `README.md` §Testing names the 54 test modules, each once,
   and every module it names exists. No document states a test count outside `agent-status.md` and this record;
   `python3 tools/check_documents.py` reports no finding. The wording is plain and no emoji appears in the tracking
   markdown.
8. Gate measured single-threaded on the tree after the corrections, the tree this record describes: `ruff check .`
   is clean at `py310`, `ruff format --check .` is clean on the 108 files it reads (81 Python files, 27 markdown
   files), `python3 tools/check_documents.py` reports no finding, and `python3 -m pytest` passes 1,778 pins with the
   same 4 `tflint` skips — 1,782 pins in 54 test modules, counted from the per-module collection totals — in 252.64 s.
   `terraform` is present, so the pins that read the live provider schema ran, and the 4 skips are the `tflint` pins
   in `tests/test_sanity_gate.py` at lines 712, 806, 904 and 973. These agree with the counts recorded when the
   piece landed, which measured the same 1,778 passed and 4 skipped in 352.23 s; only the wall time differs. The
   six pins, the index pin, the single-owner scan pins and the ownership key pin were also run on their own and pass.

## Findings, and how they were corrected

1. The pair-scan count. The committed record says the scan ran over "59 accepted-fixture pairs". The read rule
   accepts 67 fixtures, 59 of which state ownership rows, so 59 is a fixture count and not a pair count; the scan
   reads 4,422 ordered pairs, and 178 is the key count read in both directions (89 keys across 62 unordered pairs).
   Corrected in `backlog.md`, `agent-status.md` and this record.
2. The committed record also states "59 pairs where the merged ownership set names an edge the second run's own
   rows cannot". Measured: 337 ordered pair reads give such an edge, 297 of them among the pairs of the 59 fixtures
   that state ownership rows. Corrected in this record.
3. `tests/conftest.py` named five test modules as readers of `JOIN_RECORDS`. Three read it
   (`tests/test_codebase_state.py`, `tests/test_reference_edges.py`, `tests/test_ownership.py`);
   `tests/test_data_file_gate.py` and `tests/test_unit_manifest.py` read the table through its owner,
   `codebase_state.JOIN_KEYS`, so the table is still stated once. The comment is corrected in `tests/conftest.py`.
4. `baa6e2b` names `reference_edges.py` rule 1 and rule 7 as the two wording changes; the tree changed rule 1 only.
   Recorded here; the commit is not amended.
5. One line in the `backlog.md` cycle condition ran to 151 characters, past the 120 the tracking markdown keeps. It is
   wrapped here.
