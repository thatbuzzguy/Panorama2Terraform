# To Do

The current feature is the `nested-block` `parent` read rule, which `backlog.md` names: `parse_interfaces` keeps
`parent` for a layer-3 subinterface inside its parent interface row, and the nested block prints the parent name
from the parent object, not through the child object, so no output reads the field on the child. The scan cannot
report it, because a `nested-block` container has no matrix row, and the pin that shows the rule against this gap
is `tests/test_property_coverage.py::test_scan_scope_is_the_entries_a_matrix_row_covers`.

Pieces:

- [ ] Decide what the rule names as the output that reads the field for a nested block. Two shapes are possible:
      the print reads `parent` through the child object, so the recorded read lands on the entry the report names;
      or the rule states that the field belongs to the parent entry, which its emitter already reads, and the key
      on the child is not the child's own field.
- [ ] Decide whether the child can carry the field at all. A nested block writes no resource of its own, so the
      print reads through the parent object. If the rule needs a read through the child object, the print changes,
      and the `.tf` goldens move with it in the same commit.
- [ ] Decide the pin before the code, in the shape of the group 6 pins in `tests/test_property_coverage.py`: the
      fixture entry, the read the parse made, and the output that prints the field. A nested-block row has no
      matrix row, so the pin is the only thing that can keep the field honest.
- [ ] No fixture change until the rule states what a nested-block output reads, because the corpus pins are keyed
      by fixture name and the goldens read the bytes of a run on the fixture.
- [ ] `bookkeeping` (`devices`, `templates`) is the same shape in another kind, so the rule must say whether a
      scope fact and an association table are fields an output reads or facts the run records without a captured
      object. Do not write that rule before the nested-block rule decides what a read is.

The rules this feature rests on are `docs/COVERAGE_MATRIX.md` §1 for the scan scope and the output that reads a
field, and `docs/ARCHITECTURE.md` §2.4 and §3.1 for the destination kinds.

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
