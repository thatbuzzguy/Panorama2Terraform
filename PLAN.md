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

Epic 6 (codebase assembly) is closed. The run writes one directory per unit the manifest names,
and the codebase records name the unit, the owner, the reference edge, the order, the import block,
the scope objects, the site values, and the commit and push action per unit. F6.10.5 closed the two
rules the write path could decide after it landed: `template_stack` is the fifth scope fact, so a
stack entry names its own unit, and the tool decides no module parameter. The rules are in
`docs/ARCHITECTURE.md` §3.4 to §3.7, §4.1, §4.2, §4.5, §4.6, §4.8, and §5, and in
`docs/CODEBASE_ASSEMBLY.md` §3 to §14.

Two facts from the 2026-10-31 re-measurement of the pinned provider hold. Routing is reachable through an
object attribute, so the BGP, OSPF and OSPFv3 levels are an emitter shape and not a provider gap, and the tool
prints the levels the shape table states (`docs/ARCHITECTURE.md` §4.9). And a value the parse cannot carry has one shape: the block
prints the variable reference, never the value. Both rules are in `backlog.md`.

The repository layout is a rule with one owner document, `docs/ARCHITECTURE.md` §1.1: `src/` is one flat
namespace, `tests/` is flat with `tests/conftest.py` as the one shared helper file, and each index names every
file under it. `AGENTS.md` names the tracking markdown set.

Epic 7 (routing output through the protocol object) is closed. `resource_mapping.PROTOCOL_SHAPE` states the
levels the tool prints, `FILTER_SHAPE` states the six filter containers outside it, the routing methods read them
through the table, the emitter prints them in the row's field order, and the gate rules `protocol_object` and
`filter_blocks` read a printed object against the same rows. F7.12 decided how the table states a choice the
provider reads as exactly one: `selects` is the one place the table states it, because the schema states no fact
for a choice, and the gate reads the rule at the level the walk enters and at each entry of a `string_list` row.
F7.13 applied the same rule and the same wording to `FILTER_SHAPE`, which states the choice for the 14 rows the
measurement names, and the gate reads a filter choice at the block's own level as well. The rules are in
`docs/ARCHITECTURE.md` §4.9 and §4.10, and the coverage is in `docs/COVERAGE_MATRIX.md`.

## Goals

| Goal | Description | Definition of Done |
|---|---|---|
| 1 | Adequate testing and linting for iterative development, independent of Panorama or PAN-OS device access | CI passes offline. Every emitted resource type and argument is verified against the provider schema. |
| 2 | Complete support of the latest Terraform provider features for PAN-OS configuration | `terraform validate` passes on all fixture configs. Resource coverage is tracked by test. |
| 3 | Architectural support for complex, multi-device, real-life brown-field device configs | Multi-device-group and multi-vsys fixtures generate output with no silent drops and preserved policy order. |
| 4 | Full traceability and verification of the conversion | Every input entry is classified converted, report-only, or unaccounted in a per-entry report with line numbers. Every output passes the sanity gate. No silent drops, no unverified output. |
| 5 | Input comes from a declared source, and the run records which source it used | The parse boundary returns the same contract for every source. The F3.8 size and DTD checks apply to the bytes a source returns. A run with no network passes CI. The provenance record names the source, the scope, and the cache entry it read. |
| 6 | The output is a codebase, not one directory: one unit per declared scope, one owner per entry, and the path that binds each entry to the live config | A codebase run writes one directory per declared scope, a manifest that names each unit and the entries it owns, one scope object per declared scope, an import block per entry, the reference edges between units, and the site values as data with the `.tfvars` written from them. The gate reads the `.tf` files for the block rules and the four data files for the data rule. Every rule stays offline and deterministic. |

A brown-field config is an existing production config: mixed shared objects,
per-device-group overrides, template stacks, and multiple virtual systems.

## Epic 6 — Codebase assembly (Goal 6) — closed

A codebase is a set of directories, one per declared scope, that a platform plans and
applies. The design record is `docs/CODEBASE_ASSEMBLY.md`, and every rule it states names the module
and the test that holds it. The unit rule, the owner rule, the edge rule, the order rule, the import
block rule, the scope object rule, the site rule, and the action rule are all landed, and the write
path writes one directory per unit the manifest names.

## Sequencing

The next feature is the parse extraction gaps that `backlog.md` names: confirm each gap in a fixture through the
report that names it, then read the field in the parse method and name it in the matrix row in the same change,
so the property scan measures the row through a corpus entry. The `disable-override` gap is closed: nine matrix
rows name the property, one helper states the print shape for them, and `OWNERSHIP.json` states the flag as the
parse read it for their entries. The coverage row for the aggregate subinterface container is landed, so the scan
measures `panos_aggregate_layer3_subinterface` through a fixture entry and the parity test names one row with no
read of its own. The gated pieces that stay held are also in `backlog.md`: the four `*_policy_rules` types wait
for the F3.5 rulebase decision, and a config entry inside a stack needs a provider location shape before the
emitter can write a block for it. The rows that state fewer fields than the pinned provider declares for their
level are the choice levels, which state their alternatives as `selects` keys.

## Out of Scope (tracked in backlog.md)

- PAN-OS version matrix testing
- Dual-license legal review
