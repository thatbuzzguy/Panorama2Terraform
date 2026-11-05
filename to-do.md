# To Do

The round-trip cross-check design decisions are committed. The criteria the implementing agent measures
against are in `acceptance.md`. `docs/ARCHITECTURE.md` §4.6 becomes the owner document for the rule when the
rule lands.

The three decisions:

- What the rule reads: the `.tf` block set through `sanity_checks.blocks` with `kinds = ('resource',)`, and the
  entry set through the run's `entry_coverage.EntryLedger`. The rule writes no reader and reads no report and
  no data file, so `run_checks` takes the ledger as an argument and a call with no ledger reports the check as
  NOT RUN.
- The finding: one FAIL finding per unit and per `COVERAGE_MATRIX` row where the two counts do not agree, at the
  position the reader read (line 0, the file as a whole, when the reader read no block). `CHECK_ORDER` puts
  `round_trip` after `data_files` and before `control_chars`, so the cross-check is the only rule that reads two
  sets and sits after every rule that reads one set.
- Which types the rule can compare: the property-scan scope read through `entry_coverage.matrix_row_for`, so
  only an `emitted` row enters the count, and the destination per entry through `EntryLedger.destination`. The
  rule states no kind list and no type list.

## Implementation pieces

- [ ] `sanity_checks.check_round_trip`: read the block set through `blocks` and the entry set through the
      ledger, join them through `matrix_row_for` and `unit_manifest`, and state no reader, no count, no scope,
      no kind, no type, no field name and no file name of its own.
- [ ] `run_checks` takes the ledger as an argument, and `main()` passes the run's ledger, so a call with no
      ledger reports NOT RUN.
- [ ] `CHECK_ORDER` gains `round_trip` between `data_files` and `control_chars`, and the order pin in
      `tests/test_data_file_gate.py` gains the name.
- [ ] `tests/test_round_trip.py`: one test per finding, the reader-reuse pin, the ledger-and-scope-rule pin, the
      unit-rule pin, the no-ledger pin, the second-source pin, the order pin, the determinism pin, the
      file-and-line pin, the no-false-positive pin across the corpus, the console-shape pin, and the pins for
      each destination kind the count excludes.
- [ ] Documents: `docs/ARCHITECTURE.md` §4.6 states the rule and its position, and §1 gains the ledger boundary
      so the sentence that the gate reads the written files names this rule as its one exception;
      `docs/COVERAGE_MATRIX.md` §1 names `matrix_row_for` as the scope both scans read; `README.md` names the
      check in the gate table and the test file in the Testing list; `docs/README.md` names the owner;
      `sanity_checks.py` states the check in its own table. The `backlog.md` sentence that the gate cannot see
      an entry that produced no file moves to §4.6, because the cross-check reads the ledger.

Feature-sized items that stay blocked on a fact the tool cannot read offline are in `backlog.md`: the four
`*_policy_rules` types wait for the F3.5 rulebase decision and a live target, a config entry inside a stack
needs a provider location shape, the EDL `certificate_profile` field needs a rule that makes the EDL site
resolve names, and the per-entry report `profile_name` column needs a value the provider does not declare.

## Rules the layout keeps

- `docs/ARCHITECTURE.md` §1.1 is the owner document for the layout. `AGENTS.md` names the tracking markdown set,
  and each index names every document under it, so a file outside an index is a finding.
- Import rule: `src/` is one flat namespace, so a module may import any `src/` module without a cycle. The
  one test that checks the rule reads only `src/`. A test may import `src` modules and `tests/conftest.py`
  through `importlib`; nothing under `tests/` may import another test module. `src/` may not import from
  `tests/`. `tools/` is not on the test path, so `tests/test_build_kitchen_sink.py` reads the fixture assembler
  through `importlib` on the path `tests/conftest.py` builds once.
- The corpus is the directory the scan runs over. A hostile fixture in it changes the set the scan reports for
  the other fixtures, so pins that state the printed set name the fixture count. The fixture assembler reads the
  same set by rule: a fixture the F3.8 input rule refuses is skipped, and the record is not an input
  (`tests/test_build_kitchen_sink.py`).
