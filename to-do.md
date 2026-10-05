# To-Do — F4.1: Post-Run Sanity Gate (current task)

Goal 4: the conversion is fully traceable and verified. F4.1 makes the
output side true: every run verifies the `.tf` files it wrote, instead of
leaving verification to the test suite alone.

F2.9 (real resources or explicit reports) landed 2026-10-04, worked
before F4.1 per direction; its detail is in `agent-status.md`.

Acceptance criteria for the current task go in `acceptance.md` before
code.

## Task

- [ ] **F4.1 Post-run sanity gate**
  - [ ] `--validate` CLI flag: after generation, run `terraform init -backend=false -input=false` then `terraform validate` in the output directory. Flag set but binary missing: clear error, non-zero exit (an explicit request is never silently skipped).
  - [ ] Static check module (pure Python, runs at the end of every conversion):
    - no dangling references: every `panos_<type>.<local>` reference in the output resolves to a declared resource address,
    - every resource block carries a `location` block (v2 hard requirement),
    - every emitted resource type is in `EMITTED_TYPES` (`resource_mapping.py`),
    - every variable declared in `variables.tf` is consumed (the F2.10 check),
    - no raw C0 control characters or DEL in any `.tf` file,
    - expected placeholders (VPN pre-shared keys) are WARN with a pointer to `VPN_MIGRATION_REPORT.txt`; unexpected placeholder tokens are FAIL.
  - [ ] `SANITY_REPORT.txt` with PASS / WARN / FAIL sections, written even on failure; console summary; non-zero exit on any FAIL (after all output files and the report are written).
  - [ ] Tests: kitchen-sink output passes all checks (VPN placeholder WARNs); negative fixtures are caught — dangling reference, missing `location`, undeclared type, dead variable — each with the offending file and line in the report; determinism (two runs byte-identical) pinned as a test-side invariant.
  - [ ] Docs: README documents the flag and the report; `agent-status.md` updated; commit.

## Deferred (tracked in PLAN.md)

- **Epic 2:** F2.10 (one-time dead-variable cleanup; its permanent check lands in F4.1), F2.11 (verified claims).
- **Epic 3:** F3.1 (keyed data model) first, then F3.2–F3.10.
- **Epic 4:** F4.2 (container table + line tracking; may land during Epic 3), F4.3 (per-entry `CONVERSION_REPORT.txt`; after F3.1), F4.4 (property-level matrix extending the landed F2.8 type-level matrix; after F3.1, last in Epic 4).

## Notes

- **F2.9 (real resources or explicit reports) landed 2026-10-04** —
  decryption, PBF, and PBF path monitoring profiles now emit as real v2
  resources; app override, QoS, IPsec tunnel monitor, schedules, log
  forwarding, and zone protection go to `MANUAL_SETUP_REPORT.txt` with
  their data and the reason. All comment-only `.tf` generators are gone.
- **F2.8 (type-level coverage matrix) landed 2026-07-13** — finished
  per direction to continue the previously active task: `COVERAGE_MATRIX`
  in `resource_mapping.py`, `tests/test_coverage_matrix.py` (61 tests:
  row set, element grounding, per-row pipeline), `docs/COVERAGE_MATRIX.md`
  (matrix, row schema, testing methodology). It exposed and fixed the
  VPN emission gate (standalone crypto profiles were silently dropped)
  and added the third `terraform validate` case.
- The static no-dangling-reference rule already exists as a test in
  `tests/test_dependency_wiring.py`; F4.1 shares that rule with the
  runtime check instead of copying it.
- The coverage report (F4.3/F4.4) keys on logical entries
  (`<entry name>` plus its properties), not physical lines; the reported
  line number is the entry's opening tag. Decision recorded in
  `backlog.md`.
