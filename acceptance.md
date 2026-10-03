# Acceptance — F1.4: Provider schema conformance test

## Purpose
Make the provider schema the single source of truth for what the generator
may emit. The test loads `terraform providers schema -json` for the provider
version declared in the generated `provider.tf` and checks the committed
golden output against it:

1. Every emitted resource type must exist in the provider schema.
2. For every emitted resource that exists, each required attribute of that
   type (for example `location`) must be present in every generated block.

## Red→green design
The current v1-style generator output fails this test (13 of 28 emitted
types do not exist in provider v2; required attributes such as `location`
are missing). The failing checks are marked `xfail` with reasons that
point at the Epic 2 tasks that fix them (F2.2 resource mapping, F2.3
location). As Epic 2 lands, cases flip to xpass, then the markers come
off and the suite goes strict green.

## Scope
- Tests run against the committed golden .tf files (the golden tests already
  guarantee fresh generation equals the goldens).
- Provider version is read from `tests/golden/sample/provider.tf`, so the
  F2.1 version pin automatically retargets this test.
- Tests skip (not fail) when the `terraform` binary or registry access is
  unavailable; F1.5 makes terraform mandatory in CI.

## Non-goals
- No `terraform validate` (F1.5).
- No generator changes in this task.

## Done when
- `pytest` runs the conformance tests; expected xfails are reported with
  Epic 2 task references; CI stays green.
- `ruff check .` clean.
- Committed with an ASD-STE100 message.
