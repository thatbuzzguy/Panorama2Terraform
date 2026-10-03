# Acceptance — F1.5: CI Terraform gate

## Purpose
Make `terraform init -backend=false` + `terraform validate` on generated
output a permanent gate. The gate runs in CI as a dedicated job and as a
pytest test so it is visible in the same suite as the rest of Epic 1.

## Design
- `tests/test_terraform_validate.py`:
  - Generate the sample-config output with the converter CLI.
  - `terraform init -backend=false` must succeed (green today).
  - `terraform validate` must succeed — the current v1-style output fails
    against the v2 provider, so this check is `xfail` with Epic 2
    references (F2.2 resource mapping, F2.3 location, F2.4 arguments).
    It goes green when Epic 2 lands.
  - Skip (not fail) when the `terraform` binary is absent, so the
    Python matrix jobs stay unaffected.
- CI workflow gains a `terraform-gate` job: installs terraform
  (hashicorp/setup-terraform, pinned) and runs the validate test.

## Non-goals
- No generator changes in this task.
- No `terraform plan`/`apply` (needs live credentials; out of scope).

## Done when
- Locally: `pytest tests/test_terraform_validate.py` shows init green,
  validate xfailed with Epic 2 references (or green if terraform is
  absent: skip).
- CI workflow contains the terraform-gate job.
- `ruff check .` clean; full suite still green.
- Committed with an ASD-STE100 message.
