# To Do

No implementation piece is open for a landed feature. The completed pieces that this file carried are closed in
the git history and the owner documents, including the certificate `REFERENCE_ONLY` fact: `resource_mapping.
VALUE_VARIABLES` holds the `private_key` and `passphrase` rows, the emitter reads them at the print site, and
the pins are `tests/test_variables.py` and
`tests/test_robustness.py::test_a_parsed_secret_never_reaches_a_generated_file`.

## Next pieces

- [ ] `ruff format` as a gate, its own task per `backlog.md` (Nice-to-Haves). The one-time format pass of the
      legacy scripts comes first, so the diff stays reviewable. `tflint` integration is the following item.

Feature-sized items that stay blocked on a fact the tool cannot read offline are recorded in `backlog.md` and
are not pieces here: the four `*_policy_rules` types wait for the F3.5 rulebase decision and a live target, a
config entry inside a stack needs a provider location shape, the EDL `certificate_profile` field needs a rule
that makes the EDL site resolve names, the per-entry report `profile_name` column needs a value the provider
does not declare, and the two `.github/` template files outside the indexes are findings.

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
