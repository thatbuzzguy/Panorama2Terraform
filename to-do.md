# To Do

The round-trip cross-check landed: `sanity_checks.check_round_trip`, its `CHECK_ORDER` position, the ledger
argument on `run_checks`, and the pins in `tests/test_round_trip.py`. `docs/ARCHITECTURE.md` §4.6 becomes the
owner document for the rule when the document agent writes it.

The three decisions, as the rule now states them:

- What the rule reads: the `.tf` block set through `sanity_checks.blocks` with `kinds = ('resource',)`, and the
  entry set through the run's `entry_coverage.EntryLedger`. The rule writes no reader and reads no report and
  no data file, so `run_checks` takes the ledger as an argument and a call with no ledger reports the check as
  NOT RUN.
- The finding: one finding per unit and per `COVERAGE_MATRIX` row where the two counts do not agree, at the
  position the reader read (line 0, the file as a whole, when the reader read no block). The finding is a
  coverage fact, so it is a WARN and does not change the exit code, the decision
  `entry_coverage.PROPERTY_RULE` already states for a gap. `CHECK_ORDER` puts `round_trip` after `data_files`
  and before `control_chars`, so the cross-check is the only rule that reads two sets and sits after every rule
  that reads one set.
- Which types the rule can compare: the property-scan scope read through `entry_coverage.matrix_row_for`, so
  only an `emitted` row enters the count, and the destination per entry through `EntryLedger.destination`. The
  rule states no kind list and no type list. The three populations the rule cannot join, and the `report_only`
  timing, are in `backlog.md`.

## Next pieces

- [ ] Documents: `docs/ARCHITECTURE.md` §4.6 states the rule, its position and its severity, and §1 gains the
      ledger boundary so the sentence that the gate reads the written files names this rule as its one
      exception; `docs/COVERAGE_MATRIX.md` §1 names `matrix_row_for` as the scope both scans read; `README.md`
      names the check in the gate table and the test file in the Testing list; `docs/README.md` names the owner.
      The `backlog.md` sentence that the gate cannot see an entry that produced no file already names the
      cross-check as the rule that reads the ledger.

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
