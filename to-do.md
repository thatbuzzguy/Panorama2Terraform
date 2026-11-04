# To Do

The current feature is the shadow parent index key, which `backlog.md` recorded and this feature promotes. The
shadow scan (`F5.4`, `src/shadow_coverage.py`) keys the parent index by (matrix row, entry name), so two parent
entries that carry the same name under the same row give one key and the first parent row wins in report order.
Identity is (device group, vsys, type, name) (`docs/ARCHITECTURE.md` §2.1), so a key that also named the parent
scope would say which parent entry the child repeats.

Pieces:

- [ ] Measure the case through a run. `tests/fixtures/ownership_parent.xml` holds two `Printer-Pool` entries under
      the `panos_address` row in two device groups (measured 2026-11-04), so `parent_index` gives one key and the
      first parent row in report order wins. The shadow pins read `tests/fixtures/scope_parent.xml` as the parent
      source, so the case needs an entry there too.
- [ ] Add the parent scope to the key in `shadow_coverage.parent_index`, so one key names the parent entry the
      child repeats. The scope is the identity fact `docs/ARCHITECTURE.md` §2.1 states, not a name the scan
      guesses.
- [ ] Pin the rule in `tests/test_shadow_coverage.py`: the two parent entries, the child entry, the key, and the
      finding the scan reports. State the rule in `docs/ARCHITECTURE.md` §3.2, the owner document for the scan.
- [ ] A key that names the parent scope can pick a different parent entry, and the shadow line prints the parent
      line, so the report and console pins move with it. The printed set pins in `tests/test_shadow_coverage.py`
      and `tests/test_container_coverage.py` change in the same commit, from a real run.

The rule this feature rests on is in `docs/ARCHITECTURE.md` §2.1 and §3.2. The scan scope rule is
`docs/ARCHITECTURE.md` §3.2 and `docs/COVERAGE_MATRIX.md` §1: only an entry a matrix row covers is a finding.

## Rules the layout keeps

- `docs/ARCHITECTURE.md` §1.1 is the owner document for the layout. `AGENTS.md` names the tracking markdown
  set, and each index names every document under it, so a file outside an index is a finding.
- Import rule: `src/` is one flat namespace, so a module may import any `src/` module without a cycle. The
  one test that checks the rule reads only `src/`. A test may import `src` modules and `tests/conftest.py`
  through `importlib`; nothing under `tests/` may import another test module. `src/` may not import from
  `tests/`.
- The corpus is the directory the scan runs over. A hostile fixture in it changes the set the tool prints for
  other fixtures, so pins that state the printed set name the fixture count.
