# To Do

The current feature is the certificate container row and its emitter, which `backlog.md` names. The credential rule
single statement is complete: `docs/CODEBASE_ASSEMBLY.md` §11 is the owner document, and the run declares no
credential variable, so the shape the certificate emitter needs is already decided — the value the export holds
prints as a value, and a field the provider marks `sensitive` prints as the reference to the §5 name of the entry
that holds it.

Pieces:

- [ ] Measure `panos_certificate_import` and `panos_certificate_profile` against the pinned provider schema
      (2.0.14) through `tests/conftest.py::provider_schemas`: the attributes each declares, which are required, and
      which are `sensitive`. `panos_certificate` is a data source only, so the container cannot become an `emitted`
      row through a data source.
- [ ] Decide the `certificate` container row in `resource_mapping.COVERAGE_MATRIX`: the row must be `emitted` with
      the provider type in its note, so the property scan and the per-entry report read the same row, and
      `tests/test_container_coverage.py::EXPECTED_FINDINGS` loses the `unaccounted` finding for
      `device-group/entry/certificate`.
- [ ] Decide the profile row: `panos_certificate_profile` is in `LOCATION_SCHEMA` but in neither `EMITTED_TYPES` nor
      `NOT_EMITTED_TYPES`. Emit it, or state it in `NOT_EMITTED_TYPES` with the reason.
- [ ] Write the emitter: it prints `local.pem.certificate` as the value the export states and the key as the
      reference the §11 rule gives it, so no key value reaches a generated file, and the field order is the order the
      row states.
- [ ] Say what the gate reads for a certificate block. A certificate entry has no name a reference resolves, so the
      F5.5 read-through rule cannot serve it, and the gate rule must read the block the run wrote instead.
- [ ] Check the gate and the goldens together: a container row that moves to `emitted` changes the scan scope, the
      per-entry report and the `.tf` goldens in the same commit, and the goldens are regenerated only from a real
      run.

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
