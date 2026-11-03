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

## Epic 7 — Routing output through the protocol object (Goal 2) — open

The pinned provider (2.0.14) has no standalone BGP or OSPF resource, but `panos_virtual_router` declares
`protocol` as an object attribute that carries `bgp`, `ospf`, `ospfv3`, `rip`, and the two redistribution
profile lists. F7.1 landed: `resource_mapping.PROTOCOL_SHAPE` states the levels the tool prints, the emitter
prints them inside the router block, the gate rule `protocol_object` reads a printed object against the
table, and `MANUAL_SETUP_REPORT.txt` names the entries the object cannot express. The rules are in
`docs/ARCHITECTURE.md` §4.9.

F7.2 landed: `parse_ospfv3` reads the `ospfv3` area subtree through the same shape table, and `_protocol_areas`
is the area rule the two OSPF levels share, so the same reader, emitter and gate rule serve both.

F7.3 landed: `PROTOCOL_SHAPE` states the four `ospfv3` levels outside `area` that the pinned provider declares,
so the emitter prints them, the gate rule reads them, and the property scan measures the export-rule entries.
`resource_mapping.XML_NAME_EXCEPTIONS` is the one exception to the field name to element name rule.

F7.4 landed: `PROTOCOL_SHAPE` states the four area sub-levels for both routing levels, so `_protocol_areas`
reads the entries of `virtual_link`, `neighbor` and `nssa_ext_range`, and the `default_route` choice the export
states by presence. `selects` is the one place that maps the value the export states to the key the print
states, so the export spelling `no` prints as `disable`.

F7.5 landed: `PROTOCOL_SHAPE` states the `rip` levels the pinned provider declares, `parse_rip` reads them, and
`_parse_router` builds the `protocol` dict from the fields the `protocol` row states, so the level names are the
table's names. An interface entry fills the choice it states inside itself, so the same reader that fills a
chosen body also fills an entry.

F7.6 landed: `PROTOCOL_SHAPE` states the `policy` level the pinned provider declares on `protocol.bgp` and the
78 rows of its subtree, `parse_bgp` reads the four levels that hold entries, and a `member_list` field prints as
the values its element holds. Nine policy levels accept one attribute, so they are `one_of` rows.

Open for Epic 7: the levels `PROTOCOL_SHAPE` does not state, which no parse method reads — the auth profile
bodies, and the filter containers (route maps, prefix lists, community lists, access lists). They are in
`backlog.md`.

## Housekeeping — repository layout (open)

The layout is a rule, not a habit. The root holds `AGENTS.md`, the two readme indexes (`README.md`,
`docs/README.md`) and the tracking markdown; `docs/` holds every other document; `tests/` holds every test;
`src/` holds the tool's modules; `tools/` holds the developer scripts; `examples/` holds the sample input and
the sample output. Each index names every document under it.

`tests/` and `docs/` already hold what they should, and the canonical sample output is the golden set
`tests/golden/` pins byte for byte, so `terraform_output/` is only the default value of `--output-dir`. The
open work is the root: `conftest.py`, the flat module set, `quick_start.sh`, and `sample_panorama_config.xml`.
The item list, and the pins that read a path, are in `backlog.md`.

## Sequencing

Epic 6 is closed, so the next feature is the open Epic 7 work: the routing levels
`resource_mapping.PROTOCOL_SHAPE` does not state, each of which needs a row and a parse method before an
emitter, a gate rule, or the report can read it. The gated pieces that stay held are in `backlog.md`: the
four `*_policy_rules` types wait for the F3.5 rulebase decision, and a config entry inside a stack needs a
provider location shape before the emitter can write a block for it. The layout work waits for the open
feature work to be committed, because it renames the paths those tests read.

## Out of Scope (tracked in backlog.md)

- PAN-OS version matrix testing
- Dual-license legal review
