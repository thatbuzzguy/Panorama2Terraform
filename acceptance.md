# Acceptance criteria

This file carries the record for the current task. The Piece 13B.4 record is complete and is in the git history at
`14e764cd`, so it is not restated here. The other epic records are pointers: Epic 13's rules are in
`docs/INPUT_SHAPES.md`, and Epic 14's criteria are not restated here because that epic still has open pieces in
`to-do.md` and its decisions are in `docs/IMPORT_BINDING.md` §2.

## Piece 13C.1, the documents on how to get the correct export (main, the current task)

Piece 13C.1 of Epic 13, the shapes an input can be. The piece writes documents only. It states which export a run
needs, so an operator can tell the two shapes apart before running either script, and it keeps that rule in one
document with the others linking to it.

### Criteria

1. `docs/USAGE_GUIDE.md` is the owner of the operator rule for which export a run needs, because it is the document
   that tells the operator how to run each script. It states that the export taken from Panorama is the one a run
   needs for device groups and the export taken from one managed device is the one a run needs for that device's own
   config, and it names the fact that tells them apart: the first holds the device-group rows, the second holds the
   device's entries and none. The two shapes are rows of `src/input_shapes.py`, so the section names them, holds no
   row wording, and links to the table and to `docs/INPUT_SHAPES.md` §1 fact 3, which is the measurement that reads
   them from committed bytes.
2. One place states the rule. `docs/DEVICE_GROUP_SPLITTING.md` already states the fact, so the piece keeps the fact
   with the owner and turns the other into a link. `docs/DEVICE_GROUP_SPLITTING.md` keeps its own rules, the join
   between a device group and a template and what a split file holds, keeps the splitter's answer for a device
   export, and links to the owner for the export choice.
3. The root `README.md` section "Exporting from Panorama" stays an index: it keeps no wording the owner states and
   links to it, and keeps the archive rule with its owner, `docs/INPUT_SHAPES.md` §2.
4. The troubleshooting rows in `docs/USAGE_GUIDE.md` and in `docs/DEVICE_GROUP_SPLITTING.md` keep naming the shape
   and linking to the table, and hold no row wording, which `tools/check_documents.py` check 7 reads as four words
   inside a quotation or a code span and six words anywhere.
5. Every claim about what the tool does names the module or the test that holds it, and every test a document names
   exists, which check 1 reads. The pins that hold the two shapes are `tests/test_input_shapes.py`, which reads each
   row through the owner its row names, and
   `tests/test_build_kitchen_sink.py::test_the_committed_shape_pair_is_read_by_rule_and_not_by_name`, which reads
   each half of the committed pair from its bytes and not from its name. The splitter's answer for a device export is
   held by `tests/test_split_device_groups.py::test_the_splitter_prints_the_fact_it_read_for_a_file_with_no_device_group_row`.
6. `docs/README.md` names the owner, so the index gains the row for which export a run needs.
7. No document states a test count. Nothing in `src/` or in `tests/` changes, so no pin, no fixture, no golden, no
   index name and no `docs/LICENSING.md` count moves. The measurements this piece takes are the ones that can move:
   the files `ruff format --check .` reads, the time `tools/check_documents.py` takes, and the pytest answer, which
   must agree with the Piece 13B.4 baseline of 1,857 passed and 4 `tflint` skips.
8. The tracking markdown is updated: `agent-status.md` Current position for this piece, `to-do.md` for the complete
   Phase 13C, `backlog.md` for any finding this piece opens, and this file for the measurements. The gate is measured
   single-threaded, and the piece is committed.

### Out of scope

- This piece writes no code, no new test module and no fixture, because a wording check is a document review and not
  a pin: `tools/check_documents.py` holds it and the test set does not read it. A pin cannot read the wording of a
  document, so nothing in the test set moves for this piece.
- The facts only a live target states stay in `backlog.md`: which file form the UI download writes for a
  configuration download, and which export a bundle holds. No document states them as facts.
- The archive rules stay with `docs/INPUT_SHAPES.md`, so this piece states no rule for a compressed input and names
  no member rule, and the `--member` argument is not part of the export statement.
- Epic 14's decisions in `docs/IMPORT_BINDING.md` §2 are untaken, so no Epic 14 piece moves and nothing here is
  written from a decision.
- `tools/check_documents.py` is not part of the gate; it is a developer script run by hand.

### Definition of done

The two documents do not state one rule twice, the root index links, the troubleshooting rows keep their shape name
and their link to the table, the docs index names the owner, and the gate answers with no finding: `ruff check .`
clean, `ruff format --check .` clean, `python3 tools/check_documents.py` reports no finding, and `python3 -m pytest`
in one process with no parallel plugin exits 0. Every count that moves is recorded here, the tracking markdown is
updated, and the piece is committed in the conventional-commits style with the completion history in the body.
Nothing is pushed.

### Measured result, 2026-11-25

Gate, single-threaded on the tree that holds this work: `ruff check .` clean at `py310` with the 120-character line
length. `ruff format --check .` clean on 112 files. `python3 tools/check_documents.py` reports no finding, in
12.28 s. The fast path answered 43 passed in 1.02 s for `tests/test_layout.py` and `tests/test_input_shapes.py`, and
the full run answered 1,857 passed and 4 skipped in 470.76 s, which agrees with the Piece 13B.4 baseline: 1,861 pins
in 55 test modules, the 4 skips being the `tflint` pins in `tests/test_sanity_gate.py`. No count moved, because
nothing in `src/` or in `tests/` changed.

Document review, criterion by criterion: criterion 1, `docs/USAGE_GUIDE.md` §Which export a run needs states the two
exports and names the pins that read the shapes, with no row wording. Criterion 2, `docs/DEVICE_GROUP_SPLITTING.md`
now links for the export choice and keeps only the join rule, the split file's content and the splitter's answer for a
device export, so the rule is stated in one document. Criterion 3, root `README.md` §Exporting from Panorama is now a
link to the owner and keeps the archive rule with `docs/INPUT_SHAPES.md` §2. Criterion 4, the two troubleshooting rows
name the shape and link to the table and hold no row wording; check 7 answers no finding for them. Criterion 5, the
three tests this piece names exist:
`tests/test_build_kitchen_sink.py::test_the_committed_shape_pair_is_read_by_rule_and_not_by_name`,
`tests/test_input_shapes.py`, and
`tests/test_input_shapes.py`, and
`tests/test_split_device_groups.py::test_the_splitter_prints_the_fact_it_read_for_a_file_with_no_device_group_row`.
Criterion 6, `docs/README.md` gained the owner row for the rule. Criterion 7, no document states a test count.
Criterion 8, the tracking markdown is updated and this record holds the measurements.

No decision was taken by this piece, and no decision could be taken from measurement here, because the piece states
which export a run needs as an operator rule and reads no new fact. One finding this piece opened is recorded in
`backlog.md`: check 7 reads only a row's `printed_line`, and the two config shape rows state none, so the guard for a
document that copies a shape name or its description is a document review and not a check.

Epic 13's pieces are complete, so the piece list is removed from `to-do.md` and the epic section is removed from
`PLAN.md`; the design record `docs/INPUT_SHAPES.md` and `docs/README.md` now read `landed`, and the open facts stay in
`backlog.md`. No Epic 14 piece moved, because `docs/IMPORT_BINDING.md` §2 decisions are untaken. Nothing is pushed.
