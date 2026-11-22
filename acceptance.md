# Acceptance — review record for Piece 11B.1 (2026-11-22)

Piece 11B.1 (the merge rule in `src/codebase_state.py`) is reviewed at `4a5b871` (the module and the pins)
and `0ee48a8` (the tracking markdown), both not pushed. Every committed criterion is met by the tree, and
the review changed nothing, so nothing was committed. The measurements were re-run independently through the
record modules themselves, single-threaded.

1. Each committed criterion, read against the tree, is met. This document is the review record.
2. `JOIN_KEYS` and `merge_rows` hold no file name, no path rule, no reader, no row shape, no second key, no
   naming rule, no writer, no console line, and no environment name: the module-shape pin
   `tests/test_codebase_state.py::test_the_module_states_no_rule_an_owner_states_and_writes_no_file` reads the
   module clean, and the four `src/` scans read it with the other 23 modules. `merge_rows` replaces only the
   rows the run named and adds no field
   (`tests/test_codebase_state.py::test_the_merge_adds_no_field_so_a_merged_row_reads_back_as_itself`); the
   merge is keyed by row identity, so no record states which run wrote a row. No committed golden moved:
   `4a5b871` changed `README.md`, `docs/ARCHITECTURE.md`, `docs/LICENSING.md`, the module, and the two test
   modules, nothing else.
3. Join keys re-measured on the accepted corpus — 67 fixtures, each run and read back through the record
   module's own `parse_rows`: the key is unique per row for every record on every fixture, and
   `ownership.row_key`'s `source` part separates no pair the join key does not already separate, because the
   join key plus `source` equals `row_key` on every row of every fixture.
4. The order of a merged set is read through each record's own rule: `unit_manifest.FACT_KEYS`,
   `ownership.row_key`, `reference_edges.FIELD_ORDER`. `site_data.py` states no order rule, and the site file
   order is the join-key order on all 7 fixtures that hold site rows. The manifest fact order differs from the
   join-key order on 26 of the 67 accepted fixtures, which is the count the order pin holds, so the manifest
   order stays the fact order. The site-order condition and the ownership-collapse condition are recorded only
   as conditions in `backlog.md`.
5. Pins: 9 in `tests/test_codebase_state.py`, and 1 new pin in `tests/test_data_file_gate.py` (the module
   holds 28). Every pin passes on its own, and every pin reads the committed runs through `parse_rows` and
   `tests/conftest.py`; no pin builds a row by hand. The measured counts reproduce: manifest 11 against 1
   gives 11, ownership 61 against 5 gives 62, edges 9, site 3. `codebase_state.py` is named in `README.md`
   §Testing and in the `docs/ARCHITECTURE.md` §1 module table, and `docs/LICENSING.md` states 24 modules,
   which matches `src/`.
6. Import rule: no test module imports another test module, and no `src/` module imports anything from
   `tests/`. The index pin `tests/test_layout.py::test_the_indexes_name_every_document_under_them` passes. The
   writer scan, the environment-name scan, the console-line scan, and the second-naming-rule scans all read the
   24-module set clean with `codebase_state.py` in it.
7. Tracking markdown: `to-do.md` shows 11B.2 as the open piece and holds no completed-piece narrative. No
   document states a test count outside `agent-status.md` and this record. Every test named in the tracking
   markdown exists, read through `tools/check_documents.py` (no finding) and by direct lookup. The wording is
   plain and no emoji appears in the tracking markdown.
8. Gate measured single-threaded on the tree at `0ee48a8`: `ruff check .` is clean at `py310`,
   `ruff format --check .` is clean on the 108 files it reads (81 Python files, 27 markdown files),
   `python3 tools/check_documents.py` reports no finding, and `python3 -m pytest` passes 1,767 pins with the
   same 4 `tflint` skips — 1,771 pins in 54 test modules, in 256.60 s. These agree with the counts recorded
   when the piece landed; only the wall time differs from the 246.53 s recorded there.
