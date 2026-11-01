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

Epic 6 (codebase assembly) is open. F6.1 to F6.7 landed: the unit boundary as data,
ownership as data, the reference edge and the unit order, the import block, the scope
objects, the site data layer, and the commit action per unit. Their rules are in
`docs/ARCHITECTURE.md` §3.4 to §3.7, §4.1, §4.2, §4.5, §4.6, §4.8, and §5, and in
`docs/CODEBASE_ASSEMBLY.md` §3 to §10. Each landed feature names its unit and writes no
directory, so the write path that splits the output per unit directory and the gate rule
that reads a data file are the shared open steps, in `to-do.md` and `backlog.md`.

Two facts from the 2026-10-31 re-measurement of the pinned provider hold. Routing is reachable through an
object attribute, so the BGP and OSPF levels are an emitter shape and not a provider gap, and the tool
prints them (`docs/ARCHITECTURE.md` §4.9). And a value the parse cannot carry has one shape: the block
prints the variable reference, never the value. Both rules are in `backlog.md`.

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
is a rule to decide, then a module to write. F6.1 to F6.7 are implemented, so their
rules name the module and the test that holds them. Each landed feature names its unit
and writes no directory, so the write path (§14) and the gate rule that reads a data
file are the shared open steps, and they are the open pieces of Epic 6.

## Epic 7 — Routing output through the protocol object (Goal 2) — open

The pinned provider (2.0.14) has no standalone BGP or OSPF resource, but `panos_virtual_router` declares
`protocol` as an object attribute that carries `bgp`, `ospf`, `ospfv3`, `rip`, and the two redistribution
profile lists. F7.1 landed: `resource_mapping.PROTOCOL_SHAPE` states the levels the tool prints, the emitter
prints them inside the router block, the gate rule `protocol_object` reads a printed object against the
table, and `MANUAL_SETUP_REPORT.txt` names the entries the object cannot express. The rules are in
`docs/ARCHITECTURE.md` §4.9.

Open for Epic 7: the levels `PROTOCOL_SHAPE` does not state, which no parse method reads — `ospfv3`, `rip`,
the BGP `policy`, the timer levels, the auth profile bodies, and the filter containers (route maps, prefix
lists, community lists, access lists). They are in `backlog.md`.

## Sequencing

The open Epic 6 pieces are the write path that splits the output per unit directory and the gate rule that
reads a data file. Their order is in `docs/CODEBASE_ASSEMBLY.md` §14, and the pieces held until the next
feature takes them are in `to-do.md`. The open Epic 7 piece is a parse method for a routing level the shape
table does not state: it needs a table row before an emitter or a gate rule can read it.

## Out of Scope (tracked in backlog.md)

- PAN-OS version matrix testing
- Dual-license legal review
