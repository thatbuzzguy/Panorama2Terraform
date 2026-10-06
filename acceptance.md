# Acceptance criteria — F2.10: Clean generated config

No generated variable is dead. Every variable the converter writes is
consumed by the generated configuration, and no variable exists without
a consumer.

## Generated `provider.tf`

The `provider "panos"` block consumes the credential variables:

```hcl
provider "panos" {
  hostname = var.panos_hostname
  username = var.panos_username
  password = var.panos_password
}
```

Verified against the v2.0.14 provider schema: `hostname`, `username`,
and `password` are string attributes of the provider block (each also
available as a `PANOS_*` environment variable). The commented-out
references and the "configure these variables" comment are replaced by
the live references.

## Generated `variables.tf`

- Declares exactly the three credential variables: `panos_hostname`,
  `panos_username`, `panos_password`.
- The dead `device_group` variable is gone: v2 `location` is derived
  per resource from the source XML, so no global device-group variable
  has a consumer.
- `sensitive = true` stays on `panos_password` only. A hostname and a
  username are not secrets; only the password is.
- Descriptions stay.

## Test evidence

A test (both committed golden cases: sample and kitchen sink) asserts:

1. every `variable "<name>"` declared in the generated `variables.tf`
   appears as `var.<name>` in at least one generated `.tf` file other
   than `variables.tf` (no dead variables), and
2. the `provider "panos"` block consumes all three credential
   variables (the credentials are actually wired to the provider, not
   just declared).

## Bookkeeping

- Goldens regenerated: `provider.tf` and `variables.tf` in both golden
  sets; all other goldens byte-identical.
- The root README "Deploying with Terraform" tfvars example and the
  generated output README (`generate_readme`) drop `device_group` and
  keep the three credential variables.
- `test_smoke.py` still sees `variables.tf` (the file is still
  emitted); no other test changes.
- Gate: ruff clean; pytest green; `terraform init` + `terraform
  validate` green on the sample and kitchen-sink output.
