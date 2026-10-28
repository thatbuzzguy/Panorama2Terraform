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

Epic 5 (the upstream source layer) is complete. Epic 6 (codebase assembly) is planned and not
started; its design record is `docs/CODEBASE_ASSEMBLY.md`. The open decisions are in `backlog.md`.

## Goals

| Goal | Description | Definition of Done |
|---|---|---|
| 1 | Adequate testing and linting for iterative development, independent of Panorama or PAN-OS device access | CI passes offline. Every emitted resource type and argument is verified against the provider schema. |
| 2 | Complete support of the latest Terraform provider features for PAN-OS configuration | `terraform validate` passes on all fixture configs. Resource coverage is tracked by test. |
| 3 | Architectural support for complex, multi-device, real-life brown-field device configs | Multi-device-group and multi-vsys fixtures generate output with no silent drops and preserved policy order. |
| 4 | Full traceability and verification of the conversion | Every input entry is classified converted, report-only, or unaccounted in a per-entry report with line numbers. Every output passes the sanity gate. No silent drops, no unverified output. |
| 5 | Input comes from a declared source, and the run records which source it used | The parse boundary returns the same contract for every source. The F3.8 size and DTD checks apply to the bytes a source returns. A run with no network passes CI. The provenance record names the source, the scope, and the cache entry it read. |
| 6 | The output is a codebase, not one directory: one unit per declared scope, one owner per entry, and the path that binds each entry to the live config | A codebase run writes one directory per declared scope, a manifest that names each unit and the entries it owns, an import block per entry, and the reference edges between units. The gate reads the manifest, the import blocks, and the action blocks. Every rule stays offline and deterministic. |

A brown-field config is an existing production config: mixed shared objects,
per-device-group overrides, template stacks, and multiple virtual systems.

## Epic 4 — Full Traceability and Verification (Goal 4) — complete

F4.1 (sanity gate), F4.2 (container table and line tracking), F4.3 (per-entry
report) and F4.4 (property-level coverage) landed. Their rules are in
`docs/ARCHITECTURE.md` §2.4, §3.1, §3.2 and §4.6, and in `docs/COVERAGE_MATRIX.md`.

F4.4 gave each matrix row the emitter method and the property list that emitter reads,
and the report prints a captured property no output read. Goal 4 is met: every input
entry is classified, every property a row declares is grounded in the emitter that reads
it, and the output passes the sanity gate.

## Epic 5 — Upstream Data Sources (Goal 5) — complete

The tool reads three kinds of source: a file, a cached Panorama API response through
`source_fetch.py`, and a Terraform state document as a reference source through
`state_input.py`. Epic 5 made the source a declared thing, so a run can read the same
config from a file, from the API export, or from Terraform state, and an entry can name
which source it came from. F5.1 (source read boundary), F5.2 (cached API export),
F5.3 (provenance record), F5.4 (cross-source shadow report), F5.5 (read-through data
blocks, landed 2026-10-28) and F5.6 (Terraform state as a source) are in the git history.
Their rules are in `docs/ARCHITECTURE.md` §3, §3.2, §3.3, §4.5, §4.6 and §4.7.

F5.5 made the read-through reference opt-in: a name a reference site cannot resolve stays
a plain string by default, and a run that declares read-through scopes writes one `data`
block per identity in `read_through.tf`, with the gate rule that reads it
(`DATA_SOURCE_SCHEMA`, written from the provider `data_source_schemas`). This is the first
half of the codebase reference rule, so Epic 6 F6.3 follows it.

## Epic 6 — Codebase assembly (Goal 6) — planned, not started

A codebase is a set of directories, one per declared scope, that a platform plans and
applies. The design record is `docs/CODEBASE_ASSEMBLY.md`. Every feature below is a rule
to decide, then a module to write. No rule in that document is implemented, so no test
pins one yet.

- [ ] **F6.1 Unit boundary as data** — the declared scopes, one directory name per scope,
  and the manifest row (the four scope facts, the directory, the entry count, and the
  names the unit references from outside itself). Built from the ledger
  `entry_coverage.py` already writes. Needs the directory naming rule and the data file
  shape decided.
- [ ] **F6.2 Ownership as data** — which unit owns each entry, so a name a parent defines
  is not owned by a child. Needs the override decision (`disable_override`, and the
  service leg the parse does not extract).
- [ ] **F6.3 Reference between units** — the plain-string names as an edge list, and the
  mechanism that resolves a name defined by another unit. The data block half is built
  (F5.5, `docs/ARCHITECTURE.md` §4.7); the edge list and the remote state half need the
  data file shape and the outputs rule decided.
- [ ] **F6.4 Import blocks** — one `import` block per entry, from the same identity data
  the resource block uses, plus the gate rule that an import block agrees with the
  resource block it names. The rule types need the rulebase decision, and the position
  must be the position the live config holds.
- [ ] **F6.5 Scope objects as output** — `panos_device_group`, `panos_device_group_parent`,
  `panos_template`, `panos_template_stack`, `panos_template_variable`, `panos_vsys`,
  written from the provider schema. Needs new `EMITTED_TYPES` entries and matrix rows for
  the scopes the container table marks as bookkeeping.
- [ ] **F6.6 Site data layer** — one JSON data file per site, the `.tfvars` the tool writes
  for it, and the device name as a variable instead of a literal. Needs the
  value-to-variable mapping as a pinned table.
- [ ] **F6.7 Commit and push per unit** — one `panos_commit` action block per unit, the rule
  that no action names a scope another unit owns, and the gate rule that reads an `action`
  block. Needs the Terraform minimum decision (actions need 1.14 or later).

## Sequencing

1. Epic 5 is complete: F5.1, F5.2, F5.3, F5.4, F5.5 and F5.6 landed. F5.5 decided the
   reference mechanism for a name outside the run, so F6.3 follows it.
2. A state source is a reference source, so it cannot move an output fact: it writes no `.tf` byte, it
   is not an output read for the property scan, and its record references no cache entry, so it prunes
   nothing.
3. Epic 6 is planned and not started. F6.1 is the unit, and F6.2, F6.3 and F6.4 all need the unit.
   F6.4 can land before F6.2 for one unit, because a single-unit run owns everything it read. The
   order is in `docs/CODEBASE_ASSEMBLY.md` §14.

## Out of Scope (tracked in backlog.md)

- PAN-OS version matrix testing
- Dual-license legal review
