# To-Do — Complete Epic 2 (current goal)

Direction: finish the lowest-numbered unfinished epic. Epic 2 keeps
F2.10 and F2.11. Work F2.10 first, then F2.11; after both land, mark
Epic 2 COMPLETE in `PLAN.md`.

Acceptance criteria for the current task go in `acceptance.md` before
code.

## Tasks

- [ ] **F2.10 Clean generated config**
  - [ ] Wire the three credential variables into the `provider "panos"`
        block (`hostname`, `username`, `password`; verified against the
        v2.0.14 provider schema)
  - [ ] Remove the dead `device_group` variable (v2 `location` is derived
        per resource from the source XML; nothing consumes it)
  - [ ] Drop `sensitive = true` from the hostname and username; keep it
        on the password only
  - [ ] Test: every variable declared in `variables.tf` is consumed as
        `var.<name>` in the generated output; the provider block consumes
        the three credential variables
  - [ ] Regenerate goldens (sample + kitchen sink); README and generated
        README tfvars examples drop `device_group`
  - [ ] Gate: ruff clean, pytest green, terraform validate green
- [ ] **F2.11 Verified claims**
  - [ ] README coverage and validity claims reference the test evidence
        (F1.4 schema conformance, F1.5 validate gate, F2.8 coverage
        matrix tests)
  - [ ] Remove the remaining unverified claims
        (`docs/VERSION_4.0_COMPLETE_COVERAGE.md`: "100% success rate",
        "95%+ coverage", "133,000-line production-tested" and similar)
  - [ ] Gate: ruff clean, pytest green

## Deferred (tracked in PLAN.md)

- **Epic 3:** F3.1 (keyed data model) first, then F3.2–F3.10.
- **Epic 4:** F4.1 (post-run sanity gate; its dead-variable check
  reuses the F2.10 test), F4.2 (container table + line tracking; may
  land during Epic 3), F4.3 (per-entry `CONVERSION_REPORT.txt`; after
  F3.1), F4.4 (property-level matrix extending the landed F2.8
  type-level matrix; after F3.1, last in Epic 4).

## Notes

- **F2.9 (real resources or explicit reports) landed 2026-10-04** —
  decryption, PBF, and PBF path monitoring profiles now emit as real v2
  resources; app override, QoS, IPsec tunnel monitor, schedules, log
  forwarding, and zone protection go to `MANUAL_SETUP_REPORT.txt` with
  their data and the reason. All comment-only `.tf` generators are gone.
- **F2.8 (type-level coverage matrix) landed 2026-07-13** —
  `COVERAGE_MATRIX` in `resource_mapping.py`,
  `tests/test_coverage_matrix.py` (61 tests: row set, element
  grounding, per-row pipeline), `docs/COVERAGE_MATRIX.md`. It exposed
  and fixed the VPN emission gate (standalone crypto profiles were
  silently dropped) and added the third `terraform validate` case.
- The static no-dangling-reference rule already exists as a test in
  `tests/test_dependency_wiring.py`; F4.1 shares that rule with the
  runtime check instead of copying it.
- The coverage report (F4.3/F4.4) keys on logical entries
  (`<entry name>` plus its properties), not physical lines; the reported
  line number is the entry's opening tag. Decision recorded in
  `backlog.md`.
