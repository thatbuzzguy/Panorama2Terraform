# PLAN — Panorama to Terraform Converter

This file tracks epics and top-level features. Detailed design documents live in
`docs/`. Completed epic and feature detail is removed here; the git history holds it.

## Current State

The tool converts a Panorama XML export to provider v2 Terraform, reports what the
provider cannot model, and runs a post-run gate on the output it wrote. Every test
runs offline against fixtures and the live provider schema. CI runs `ruff check .`
and `pytest`, plus a job that runs `terraform init` and `terraform validate`.

The work before Epic 6 is complete: the output validates against the pinned
provider, no parse method keys by name alone, the test gate covers the generated
Terraform, the input comes from a declared source with a provenance record, and the
per-entry report accounts for every entry. The rules that came from that work are in
`docs/ARCHITECTURE.md` §2 to §5 and `docs/COVERAGE_MATRIX.md`.

Epic 6 (codebase assembly) is open. F6.1 to F6.6 landed: the unit boundary as data,
ownership as data, the reference edge and the unit order, the import block, the scope
objects, and the site data layer. Their rules are in `docs/ARCHITECTURE.md` §3.4 to
§3.7, §4.1, §4.2, §4.5, §4.6, §4.8, and §5, and in `docs/CODEBASE_ASSEMBLY.md` §3 to
§9. The open decisions are in `backlog.md`; the open pieces are in `to-do.md`.

## Goals

| Goal | Description | Definition of Done |
|---|---|---|
| 1 | Adequate testing and linting for iterative development, independent of Panorama or PAN-OS device access | CI passes offline. Every emitted resource type and argument is verified against the provider schema. |
| 2 | Complete support of the latest Terraform provider features for PAN-OS configuration | `terraform validate` passes on all fixture configs. Resource coverage is tracked by test. |
| 3 | Architectural support for complex, multi-device, real-life brown-field device configs | Multi-device-group and multi-vsys fixtures generate output with no silent drops and preserved policy order. |
| 4 | Full traceability and verification of the conversion | Every input entry is classified converted, report-only, or unaccounted in a per-entry report with line numbers. Every output passes the sanity gate. No silent drops, no unverified output. |
| 5 | Input comes from a declared source, and the run records which source it used | The parse boundary returns the same contract for every source. The F3.8 size and DTD checks apply to the bytes a source returns. A run with no network passes CI. The provenance record names the source, the scope, and the cache entry it read. |
| 6 | The output is a codebase, not one directory: one unit per declared scope, one owner per entry, and the path that binds each entry to the live config | A codebase run writes one directory per declared scope, a manifest that names each unit and the entries it owns, one scope object per declared scope, an import block per entry, the reference edges between units, and the site values as data with the `.tfvars` written from them. The gate reads the manifest, the import blocks, the scope blocks, and the action blocks. Every rule stays offline and deterministic. |

A brown-field config is an existing production config: mixed shared objects,
per-device-group overrides, template stacks, and multiple virtual systems.

## Epic 6 — Codebase assembly (Goal 6) — open

A codebase is a set of directories, one per declared scope, that a platform plans and
applies. The design record is `docs/CODEBASE_ASSEMBLY.md`. Every feature in the record
is a rule to decide, then a module to write. F6.1 to F6.6 are implemented, so their
rules name the module and the test that holds them. Each landed feature names its unit
and writes no directory, so the write path (§14) and the gate rule that reads a data
file are the shared open steps.

- [ ] **F6.7 Commit and push per unit** — one `panos_commit` action block per unit, the rule
  that no action names a scope another unit owns, and the gate rule that reads an `action`
  block. Needs the Terraform minimum decision (actions need 1.14 or later).

## Sequencing

F6.7 needs the write path that `docs/CODEBASE_ASSEMBLY.md` §14 step 7 and step 8 share,
because the site feature names the unit and writes no directory. The order of the open
pieces is in §14, and the pieces held until the next feature takes them are in `to-do.md`.

## Out of Scope (tracked in backlog.md)

- PAN-OS version matrix testing
- Dual-license legal review
