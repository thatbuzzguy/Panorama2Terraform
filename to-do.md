# To Do

The round-trip cross-check feature is complete and committed. The rule, its `CHECK_ORDER` position, the ledger
argument on `run_checks`, the pins in `tests/test_round_trip.py`, and the documents that name it
(`README.md`, `docs/ARCHITECTURE.md` §1 and §4.6, `docs/COVERAGE_MATRIX.md` §1, and `docs/README.md`) are all
landed. No piece of this feature stays open.

## Next pieces

- [ ] The destination a report-only entry answers (`acceptance.md`). The rule, the pins and the Result are
      landed: `mark` records what the parse method took and only the destination the caller states, and
      `EntryLedger.destination` is the one place that answers a destination, in the order the per-entry fact
      read from the recorded object, then the mark-stated destination, then the container table row. Piece left
      open:
  - [ ] Write the documents that name the rule: `docs/ARCHITECTURE.md` §1.1, §3.2, §4.6,
        `docs/COVERAGE_MATRIX.md` §1, `docs/README.md`, `README.md` gate table (`acceptance.md` §5), and
        `backlog.md`, where the 'entry side counts more' entry reads 3 findings with the surviving instances
        named.
- [ ] The certificate `REFERENCE_ONLY` rows for `private_key` and `passphrase`, which the table has no row for,
      so the certificate emitter cannot print the reference yet (`backlog.md`).

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
