# To Do

The current feature is the certificate container row and its emitter, which `backlog.md` names. The credential rule
single statement is complete: `docs/CODEBASE_ASSEMBLY.md` §11 is the owner document, and the run declares no
credential variable, so the shape the certificate emitter needs is already decided — the value the export holds
prints as a value, and a field the provider marks `sensitive` prints as the reference to the §5 name of the entry
that holds it. The gate rule for a value the provider constrains in its code, not in the schema, is also complete
(`docs/ARCHITECTURE.md` §4.6): such a value stays outside the static rules and the `terraform` check reports it, so
the certificate piece below names only what a gate rule reads from a block, and the plan pins read the unit
directories the run wrote.

Pieces:

- [x] Measure `panos_certificate_import` and `panos_certificate_profile` against the pinned provider schema
      (2.0.14) through `tests/conftest.py::provider_schemas`: the attributes each declares, which are required, and
      which are `sensitive`. `panos_certificate` is a data source only, so the container cannot become an `emitted`
      row through a data source. Measured 2026-11-05; the sets are in `acceptance.md`, and the corrected facts are
      in `backlog.md`.
- [x] Decide the `certificate` container row in `resource_mapping.COVERAGE_MATRIX`: `emitted` with the provider
      type in its note, so the property scan and the per-entry report read the same row. Measured 2026-11-05: no
      certificate type declares a `device_group` sub-block, so the fixture entry sits in a scope the row's type
      can place (a virtual system for the record entry, a template and a virtual system in
      `tests/fixtures/certificates.xml`), and `tests/test_container_coverage.py::EXPECTED_FINDINGS` lost the
      `unaccounted` finding for `device-group/entry/certificate`.
- [x] Decide the profile row: `emitted`, with a `LOCATION_SCHEMA` row that states `template` only, because
      `location_data` reaches `shared` only inside the device-group branch and the row declares no device group,
      so a `shared` row would be a fact the tool cannot use. The whole entry is readable, so the
      `NOT_EMITTED_TYPES` reason (a partial object) does not hold for this type. The container row is the input's
      spelling `certificate-profile`, and the profile's `certificate` objects are a `nested-block` row under it.
- [x] Write the emitter: it prints `local.pem.certificate` as the value the export states and the two `sensitive`
      fields as the variable reference the entry names, so no generated file states the value, and the field order
      is the order `CERTIFICATE_SHAPE` states. Two files, one per emitter: `certificates.tf` and
      `certificate_profiles.tf`.
- [ ] Say what the gate reads for a certificate block. A certificate entry has no name a reference resolves, so the
      F5.5 read-through rule cannot serve it, and the gate rule must read the block the run wrote instead.
- [x] Check the gate and the goldens together: the two rows moved to `emitted`, so the scan scope, the per-entry
      report and the `.tf` goldens changed in the same commit, and the goldens are the bytes one real run wrote.
      The pins that moved are listed in `acceptance.md` §Result. `tests/test_edge_cases.py` and the EDL golden did
      not move, because the EDL site resolves no names.

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
