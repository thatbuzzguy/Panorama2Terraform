# To Do

The current feature is the credential rule single statement, which `backlog.md` names and
`docs/CODEBASE_ASSEMBLY.md` §11 states as a decision. Two statements cover the same idea today: the fetch rule
(`docs/ARCHITECTURE.md` §3) says the key comes from the environment only and never reaches a generated file, and
`generate_variables` declares `panos_hostname`, `panos_username` and `panos_password`, which
`generate_provider_config` uses. One statement must cover both the fetch layer and the generated provider block.

Pieces:

- [ ] Decide the one statement and the document that owns it. Say what the generated provider block reads: the key
      from the environment, or the declared variables. The fetch layer must read the same statement, so no module
      states a second rule.
- [ ] Decide what the block holds for a unit: the host as the variable the codebase already declares, and no
      credential literal in a generated file. `site_data.py` states the operator's own file for the credentials, so
      the statement must agree with it, and `resource_mapping.VALUE_VARIABLES` stays the single shape owner.
- [ ] Decide the pins. The fetch layer reads the key through the one statement, and the generated `provider.tf`
      writes what the statement says. `tests/test_variables.py` pins the declaration set and
      `tests/conftest.py::declared_provider` reads the provider block from the golden, so the new pin reads through
      those rules and restates neither.
- [ ] Check the gate and the goldens together: a change to the generated provider block moves the goldens, which
      are regenerated only from a real run.

The rules this feature rests on are `docs/CODEBASE_ASSEMBLY.md` §11 for the gap, `docs/ARCHITECTURE.md` §3 for the
fetch rule, and `docs/CODEBASE_ASSEMBLY.md` §6 for the file the run writes.

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
