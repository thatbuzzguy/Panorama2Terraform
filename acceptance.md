# Acceptance criteria — F4.1 Post-run sanity gate (Epic 4)

F4.1 makes the static invariants run when a conversion runs, not only when
the suite runs. It is the first feature of Epic 4.

## Audit before writing (2026-10-19)

The invariants exist today only as tests. They do not run during a
conversion, so a conversion that breaks an invariant still writes files and
exits 0.

| Invariant | Pinned today by | Runs during a conversion today |
|---|---|---|
| No dangling `.name` reference | `tests/test_dependency_wiring.py::test_every_emitted_reference_resolves_to_a_declared_resource` | No |
| `location` on every resource | `tests/test_schema_conformance.py::test_every_block_has_location` (against the committed goldens, not a live run) | No |
| Only `EMITTED_TYPES` emitted | `tests/test_resource_mapping.py`, `tests/test_coverage_matrix.py` | No |
| Every declared variable consumed | `tests/test_variables.py::test_every_declared_variable_is_consumed` | No |
| No raw control character in `.tf` | `tests/test_robustness.py::test_tab_cr_names_produce_valid_tf` (one fixture, one file) | No |
| Expected VPN placeholder | `tests/test_reports.py::test_per_gateway_placeholder_line_survives` (report text only) | No |

Two facts shape the design:

- The checks must read what the operator receives (the written `.tf` files),
  not the generator's internal state, so a check cannot be satisfied by a
  bookkeeping value that never reached the file.
- Each rule must exist in one place. The module is the rule; the tests call
  it. A copied rule can drift and then disagree with the gate.

## Criteria

1. **Module.** `sanity_checks.py`, pure Python, standard library plus
   `resource_mapping`. No dependency on the converter, so the tests and the
   CLI import the same module.
2. **Checks.** One function per rule, each returning findings:
   - `emitted_types` — every resource type is in `EMITTED_TYPES` (FAIL)
   - `location_present` — every resource block has a `location` block (FAIL)
   - `references` — every `.name` reference resolves to a resource declared
     in the same run (FAIL)
   - `variables` — every declared variable has a `var.` consumer (FAIL)
   - `control_chars` — no raw control character or DEL in a `.tf` file (FAIL)
   - `placeholders` — an expected placeholder, such as the VPN pre-shared key
     `***CHANGE_ME***`, is reported as WARN, never FAIL
   - `terraform` — `terraform init` + `terraform validate`, only with
     `--validate` (FAIL on failure, SKIPPED when the binary is absent)
3. **Reads the output, not memory.** A finding names the file and the line the
   operator sees. A resource block ends at the first column-0 brace, as the
   existing tests read it.
4. **Runs on every conversion.** The converter runs the static checks after it
   writes the output. The splitter writes XML only, so it has no `.tf` to
   check; that is stated, not assumed.
5. **Report plus console.** `SANITY_REPORT.txt` in the output directory, and a
   console summary. The report names each check result, then the findings.
6. **Exit code.** 0 when no finding is FAIL, including a WARN-only run.
   1 when a finding is FAIL. A SKIPPED check never changes the exit code, so
   the suite stays offline-capable (Goal 1).
7. **Determinism.** The report is byte-identical between two runs on the same
   input: no timestamp, no absolute path, findings sorted by check order then
   file then line. Determinism stays pinned by test, not paid in the CLI.
8. **Shared rules.** `tests/test_dependency_wiring.py` and
   `tests/test_variables.py` call the module instead of restating their
   invariant; the behavior tests in those files stay.
9. **No false positives and no lying.** The gate reports no FAIL finding on
   every fixture in `tests/fixtures/` and on the committed sample. Each check
   has a negative test that proves it detects its violation.
10. **Documentation.** `docs/ARCHITECTURE.md` §7 no longer says F4.1 is not
    implemented; the module is added to the module table, and the gate is
    stated in the emit pipeline with the tests that pin it. README states the
    flag and the report.
11. **Gates:** ruff clean, pytest green, `terraform validate` green on the
    sample and kitchen-sink outputs. Both golden sets stay byte-identical:
    the gate writes a report, not `.tf`, so no golden moves.

## Result (2026-10-19)

- `sanity_checks.py` added: seven checks, one function per rule, findings with
  file and line, deterministic report render, console summary.
- The gate runs on every conversion (`main()` writes `SANITY_REPORT.txt` and
  prints the summary) and exits 1 when a finding is FAIL. A WARN-only run exits
  0. The `terraform` check is SKIPPED when the binary is absent, so the exit code
  still comes from the static checks.
- `--validate` added to the converter CLI: `terraform init` + `terraform
  validate`, with the output read plain (ANSI codes stripped).
- Rules shared, not copied: `tests/test_dependency_wiring.py`,
  `tests/test_variables.py`, `tests/test_schema_conformance.py` and
  `tests/test_robustness.py` now call the module for the reference, variable,
  location and control-character rules. The behavior tests in those files stay.
- `tests/test_sanity_gate.py` (70 tests): the gate runs on a conversion, the
  report is byte-identical between two runs, no timestamp and no absolute path,
  one negative test per rule, no FAIL finding on all 53 output fixtures, WARN for
  the VPN placeholder with exit 0, exit 1 for a planted broken file, `--validate`
  green, the SKIPPED path, and the splitter output (no `.tf`, so nothing to check).
- Gates: ruff clean, pytest 509 passed, `terraform validate` green on the sample
  and kitchen-sink outputs. Both golden sets byte-identical: the gate writes a
  report, not a `.tf`.
- Docs updated: `docs/ARCHITECTURE.md` §1 (module row), new §4.6, §6
  (report determinism), §7 (F4.1 no longer listed as not implemented); README and
  `docs/USAGE_GUIDE.md` state the flag, the checks and `SANITY_REPORT.txt`.
- One limit recorded: the gate checks that `location` is present. The sub-block
  and field shape stays pinned by `tests/test_multi_vsys_location.py`, because
  `terraform validate` accepts an unknown sub-block and drops it silently.
