# Acceptance Criteria — F4.1: Post-Run Sanity Gate

## Goal
Every conversion run verifies the Terraform it writes. Today the
strongest checks (`terraform init`/`validate`, no dangling references,
`location` on every resource) exist only as pytest gates; the CLI flow
writes files and exits 0 even if the output is broken or inconsistent.
F4.1 moves verification into the product: a `--validate` flag for the
terraform gate, a static check module that runs on every conversion, and
a `SANITY_REPORT.txt` the user can read.

## Design

- **CLI:** `--validate` flag. When set, run `terraform init -backend=false
  -input=false` then `terraform validate` in the output directory after
  generation. Flag set but binary absent: clear error, non-zero exit —
  an explicit request is never silently skipped.
- **Static checks** (pure Python, always run at the end of `main()`, no
  terraform required):
  1. No dangling references: every `panos_<type>.<local>` reference in
     any `.tf` resolves to a declared resource address.
  2. `location` present: every resource block carries a `location` block
     (a v2 hard requirement).
  3. Known types only: every emitted resource type is in
     `EMITTED_TYPES` (`resource_mapping.py`).
  4. Variables consumed: every variable declared in `variables.tf` is
     referenced somewhere in the output (the F2.10 check).
  5. Clean strings: no raw C0 control characters or DEL in any `.tf`
     (defense in depth over `escape_string`).
  6. Placeholders: expected placeholders (VPN pre-shared keys) are WARN
     with a pointer to `VPN_MIGRATION_REPORT.txt`; unexpected
     placeholder tokens are FAIL.
- **Report:** `SANITY_REPORT.txt` with a PASS / WARN / FAIL section per
  check, written even on failure; a console summary; non-zero exit on
  any FAIL (after all output files and the report are written).
- **Determinism** (two runs, byte-identical output) is a test-side
  invariant, not a CLI cost.

## Definition of Done

1. `python3 panorama_to_terraform.py tests/fixtures/kitchen_sink.xml
   --output-dir X --validate` exits 0 and its `SANITY_REPORT.txt` shows
   every check PASS (the VPN pre-shared-key placeholder WARNs).
2. Negative cases are caught, each with a test: a dangling reference, a
   resource without `location`, an undeclared type, a dead variable.
   Each produces a non-zero exit and a FAIL line in the report naming
   the offending file and line.
3. `--validate` without a terraform binary: clear error, non-zero exit.
   Without the flag: the converter works unchanged and never requires
   terraform.
4. The existing gates still pass (`test_terraform_validate.py`,
   `test_schema_conformance.py`, the no-dangling-reference invariant in
   `test_dependency_wiring.py`); the new static module reuses the same
   rules, not copies of them.
5. Docs: README documents the flag and the report; `agent-status.md`
   updated; commit.

## Gate

- `ruff check .` clean
- `pytest` green (terraform gates run when the binary exists)
- `terraform validate` green on the sample and kitchen-sink outputs
