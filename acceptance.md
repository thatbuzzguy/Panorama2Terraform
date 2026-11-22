# Acceptance — review record for Piece 11B.2 (2026-11-22)

Piece 11B.2 (the run's unit set against the codebase's unit set, and the rule that the run writes no
directory for a unit it read only through the record) is reviewed at `c079d02` (the three modules and the five
pins) and `e28c5d7` (the tracking markdown), both not pushed. Seven checks, each read against the tree. Every
committed criterion is met by the tree; two markdown lines needed correction and no code and no pin changed.
The measurements were re-run independently through the record modules themselves, on committed material,
single-threaded. `acceptance.md` is this record.

1. **Each committed criterion, read against the tree, is met.** This document is the review record.
2. **The measurement reproduces** when re-run through the record modules on committed material: the
   kitchen-sink run as the codebase answers 11 units, the `address_objects.xml` run answers 1 unit
   (`shared_45ca31c3`), the merged set answers the same 11, the run set is inside the merged set, and the 10
   units only the merged set names are the units the second run read only through the record, with the names the
   record lists (`Branch-Stack`, `fw-2.example.com`, `Shared` (`shared_a6577c11`), `FW-Template`,
   `template-vsys`, `vsys1` twice, `vsys2`, `Dev-DG`, `Production-DG`). A run that read nothing from the record
   answers its own set, so the single-run case is unchanged and no committed golden moved.
3. **The write fact reproduces** on a real run that wrote into a copy of the kitchen-sink output: it added no
   directory, wrote no file inside the 10 directories the record names, and every byte inside them (60 files) is
   the byte the first run wrote; it wrote one unit file, `shared_45ca31c3/address_objects.tf`, inside the one
   directory its own set names, plus the 6 root files. The single-run `.tf` bytes agree with the committed
   goldens (61 files for the kitchen sink, 14 for the sample), and the second run through the gate exits 1,
   which is Piece 11B.4's open behaviour, not this piece.
4. **The rules are as the piece states them.** `unit_manifest.units` reads either row set and answers the empty
   set for a reader with no rows, so `rows = source.rows() if hasattr(source, "rows") else list(source)` is the
   one read path. `write_path.py` defines only `LF`, `unit_path`, `root_path` and `write_file`, so it keeps the
   byte rule, the two builders and the one writer, and states the no-directory fact as its rule 4.
   `codebase_state.py` names no unit set of its own. `unit_manifest.units` is the only unit rule in `src/`: every
   other module that names units reads it, or reads a row through `facts_of`. `src/` still holds 24 tracked
   modules.
5. **The five pins** exist, pass on their own, sit in the module that owns the fact, read through
   `parse_rows` and `tests/conftest.py`, and are grounded on committed runs rather than on hand-built rows: 2 in
   `tests/test_unit_manifest.py` (which collects 41), 2 in `tests/test_write_path.py` (23), 1 in
   `tests/test_codebase_state.py` (10).
6. **The index rule and the import rule hold.** The index pin
   `tests/test_layout.py::test_the_indexes_name_every_document_under_them` passes, no test module imports another
   test module (48 test modules read `from conftest import`, none imports a test module), no `src/` module
   imports anything from `tests/`, and the pins that scan the `src/` set — the writer scan, the environment-name
   scan, the console-line scan and the second-naming-rule scan — read the modules unchanged.
7. **Tracking markdown agrees with the tree.** `to-do.md` holds Phase 11B with the open 11B.3 and 11B.4 items
   and no completed-piece narrative; `PLAN.md` states the open Phase 11B items without the landed unit-set piece;
   `agent-status.md` records the piece and the gate; `docs/MULTI_RUN_CODEBASE.md` §2 rule 5 states one rule over
   two row sets and names its three pins, §3 rule 2 names its pin, and §6 rule 2 names `write_path.py` rule 4 as
   the place the no-directory fact is stated and names its two pins; `docs/ARCHITECTURE.md` §1 names the unit
   rule read over either row set and the write path rule; `docs/CODEBASE_ASSEMBLY.md` §14 keeps the shape rule;
   `README.md` §Testing names each entry once. No document states a test count outside `agent-status.md` and this
   record, every named test exists, and the wording is plain with no emoji in document prose.

## Findings and the two corrections

1. `docs/LICENSING.md` stated "The other 19 modules carry no notice" while `src/` holds 24 tracked modules and 4
   carry a notice, so the set without a notice is 20. The count was stale from the commit that added the 24th
   module (`4a5b871`), and `tools/check_documents.py` reads only the "N of the M modules carry a notice" pair, so
   the sentence is not a gate finding. Corrected in this record's commit.
2. `README.md` §Testing listed the facts `tests/test_write_path.py` holds but did not name the run set rule, so
   the entry did not agree with the piece's record. The entry now names the rule that the run writes no directory
   for a unit it read only through the record. Corrected in this record's commit.

Two scan findings are not document errors, so nothing was changed for them:
`docs/ARCHITECTURE.md:698` `::test_one_label_for_both_sources` belongs to `tests/test_provenance.py`, which the
line before it names, and `docs/CODEBASE_ASSEMBLY.md:247`
`::test_the_record_is_one_row_per_edge_the_data_can_name` belongs to `tests/test_reference_edges.py`, which the
line two above names; both tests exist, so the line-level attribution was a false positive. The `✓` in
`docs/DEVICE_GROUP_SPLITTING.md` is inside a fenced block that reproduces the console output
`src/split_device_groups.py` prints, so it is not document prose.

## Gate, measured single-threaded

Measured single-threaded on the tree that holds this record: `ruff check .` is clean at `py310`,
`ruff format --check .` is clean on the 108 files it reads (81 Python files, 27 markdown files),
`python3 tools/check_documents.py` reports no finding, and `python3 -m pytest` passes 1,772 pins with the same 4
`tflint` skips — 1,776 pins in 54 test modules, 5 more than the 1,767 pins Piece 11B.1 measured. The counts are
read from the run's progress output, and the wall time `time` measured for that run is 282.0 s; the same counts
were measured on this review's run before the two corrections, in 231.68 s. Read through the per-module
collection counts: `tests/test_unit_manifest.py` collects 41, `tests/test_write_path.py` collects 23, and
`tests/test_codebase_state.py` collects 10, so the 5 pins are 2, 2 and 1. `terraform` is present, so the pins
that read the live provider schema ran, and the 4 skips are the `tflint` pins in `tests/test_sanity_gate.py`.
