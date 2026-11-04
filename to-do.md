# To Do

The current feature is the `bookkeeping` `devices` and `templates` fields rule, which `backlog.md` names:
`parse_associations` keeps `devices` and `templates`, and no output reads them, because a `bookkeeping` row has
no matrix row. The rule `docs/COVERAGE_MATRIX.md` §1 states for a container outside the scan scope is that the
output which reaches the entry must read the field it names. The `nested-block` rule decided what a read is:
`parent` is a fact of the parent entry, so the child carries no value for it and the entry line names only what
the print reads. This feature can now say whether an association table and a scope fact are fields an output
reads, or facts the run records without a captured object.

Pieces:

- [ ] Decide what a `bookkeeping` row names. A `captured_fields` set names the keys of the object the parse
      method built, so a fact the run records without a captured object cannot be a captured field. Say whether
      `devices` and `templates` are fields an output reads, or facts the report records as bookkeeping.
- [ ] Decide the pin, in the shape of the group 6 pins in `tests/test_property_coverage.py`: the fixture entry,
      the read the parse made, and the output that prints the field or states that no output can read it. A
      `bookkeeping` row has no matrix row, so the pin is the only thing that can keep the field honest.
- [ ] No fixture change until the rule states what a `bookkeeping` output reads, because the corpus pins are
      keyed by fixture name and the goldens read the bytes of a run on the fixture.
- [ ] Check the entry name and the five scope facts against the decision: they are the row identity
      (`entry_coverage.NON_FIELD_KEYS`), so a rule that calls an association table a field must say why it is
      not an identity fact.

The rules this feature rests on are `docs/COVERAGE_MATRIX.md` §1 for the scan scope and the output that reads a
field, and `docs/ARCHITECTURE.md` §2.2, §2.4 and §3.1 for the scope facts and the destination kinds.

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
