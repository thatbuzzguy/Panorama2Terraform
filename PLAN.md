# PLAN — Panorama to Terraform Converter

This file tracks epics and top-level features. Detailed design documents live in
`docs/`. Completed epic and feature detail is removed here; the git history holds it.

## Current State

The tool converts a Panorama XML export to provider v2 Terraform, reports what the
provider cannot model, and runs a post-run gate on the output it wrote. Every test
runs offline against fixtures and the live provider schema. CI runs `ruff check .`
and `pytest`, plus a job that runs `terraform init` and `terraform validate`.

The three problems the adversarial audit found are closed: the output validates
against the pinned provider, no parse method keys by name alone, and the test gate
covers the generated Terraform. `ADVERSARIAL_AUDIT_REPORT.md` is the audit record;
its status table states the current state.

One feature is open, in Epic 4: the property-level coverage matrix (F4.4). The open
gaps and decided limits are in `backlog.md`.

## Goals

| Goal | Description | Definition of Done |
|---|---|---|
| 1 | Adequate testing and linting for iterative development, independent of Panorama or PAN-OS device access | CI passes offline. Every emitted resource type and argument is verified against the provider schema. |
| 2 | Complete support of the latest Terraform provider features for PAN-OS configuration | `terraform validate` passes on all fixture configs. Resource coverage is tracked by test. |
| 3 | Architectural support for complex, multi-device, real-life brown-field device configs | Multi-device-group and multi-vsys fixtures generate output with no silent drops and preserved policy order. |
| 4 | Full traceability and verification of the conversion | Every input entry is classified converted, report-only, or unaccounted in a per-entry report with line numbers. Every output passes the sanity gate. No silent drops, no unverified output. |

A brown-field config is an existing production config: mixed shared objects,
per-device-group overrides, template stacks, and multiple virtual systems.

## Epic 4 — Full Traceability and Verification (Goal 4)

F4.1 (sanity gate), F4.2 (container table and line tracking) and F4.3 (per-entry
report) landed. Their rules are in `docs/ARCHITECTURE.md` §3.1, §3.2 and §4.6.

- [ ] **F4.4 Property-level coverage** — the matrix is type level today. Extend it so
  each row names the properties an emitter reads, so a property the parse captured
  but no output used is reported as a gap. Foundation: `COVERAGE_MATRIX` in
  `resource_mapping.py`. A property level is a container inside a config-object
  entry, so `container_coverage` reports only the section level and the per-entry
  report counts property entries on the parent row. Keep the entry-mark rule and the
  section rule unchanged; add the property scan and its report section.

## Sequencing

1. F4.4 is the only open feature. It builds on the F4.2 container table and the F4.3
   ledger, so it does not need a new naming or grouping rule.
2. Fix the two open defects found while refreshing the documentation in the same
   pass as F4.4, because both change report output: the overlapping BGP and OSPF
   paths (`backlog.md`), and the manual report sections that do not name their scope.

## Out of Scope (tracked in backlog.md)

- Live Panorama API integration
- PAN-OS version matrix testing
- Dual-license legal review
