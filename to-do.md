# To Do

The certificate feature is complete and committed: the two `CONTAINER_TABLE` rows, the two `COVERAGE_MATRIX`
rows, `CERTIFICATE_SHAPE` and `CERTIFICATE_TABLE`, the two parse methods, the two emitters, the two
`VALUE_VARIABLES` rows, the fixture, the goldens from one real run, and the gate rule
`sanity_checks.check_certificate_blocks` that reads a printed certificate block against `CERTIFICATE_SHAPE`
(`docs/ARCHITECTURE.md` §4.6 and §4.11). `tests/test_certificate_blocks.py` holds its pins.

The next feature is the round-trip cross-check, in `backlog.md` (Deeper post-run checks): parse the generated
HCL and compare the object counts against the input, through the coverage data. It is the gate work that is
actionable offline. Pieces:

- [ ] Decide what the round-trip check reads: the `.tf` block set and the entry ledger, so no second count rule
      appears and the rule stays a rule about a read.
- [ ] Decide the finding: a count that does not agree, stated per unit, at the position the reader read, and the
      `CHECK_ORDER` position the new rule takes.
- [ ] Decide which types the check can compare: a `nested-block` row writes lines inside a parent block, so its
      count is not one block, and an entry the run reports writes no block.

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
