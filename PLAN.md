# PLAN — Panorama to Terraform Converter

This file tracks epics and top-level features. Detailed design documents live in
`docs/`. Completed epic and feature detail is removed here; the git history holds it.

## Current State

The tool converts a Panorama XML export to provider v2 Terraform, reports what the
provider cannot model, and runs a post-run gate on the output it wrote. Every test
runs offline against fixtures and the live provider schema. CI runs `ruff check .`,
`ruff format --check .` and `pytest`, plus a job that runs `terraform init` and `terraform validate`.

The output is a codebase, not one directory: the run writes one directory per unit the manifest names,
and the codebase records name the unit, the owner, the reference edge, the order, the import block,
the scope objects, the site values, and the commit and push action per unit. The rules are in
`docs/CODEBASE_ASSEMBLY.md` §3 to §14, and `docs/ARCHITECTURE.md` §3.4 to §3.7, §4.1, §4.2, §4.5,
§4.6, §4.8, and §5.

The template and stack unit is recorded in `docs/TEMPLATE_STACK_DEPLOYMENT.md` §2 to §4: which membership name
enters the edge set, the scope a template or a stack entry is declared inside, and what the tool states for a
template entry the export declares and no device names. The facts only a live target states — the device the
operator adds, and the device serial a push target names — are in `backlog.md`.

Routing is reachable through an object attribute, so the BGP, OSPF and OSPFv3 levels are an emitter shape
and not a provider gap, and the tool prints the levels the shape table states (`docs/ARCHITECTURE.md` §4.9).
A value the parse cannot carry has one shape: the block prints the variable reference, never the value
(`backlog.md`, the value the parse cannot carry). A choice the provider reads as exactly one is stated as a
`selects` key, the one place a row states it (`docs/ARCHITECTURE.md` §4.9 and §4.10).

The three shape tables each have one owner and one gate rule that reads them: `PROTOCOL_SHAPE` and
`protocol_object`, `FILTER_SHAPE` and `filter_blocks`, `CERTIFICATE_SHAPE` and `certificate_blocks`. Each
rule reads the block through the same block reader and the same field reader, so a printed block and a
hand-written block are read the same way.

Rules as data: the row shape `rule_data.RULE_ROW_FIELDS`, the three forms of one row set, the iterated
block that reads the printed map, and the key order as the apply order are in `docs/ARCHITECTURE.md` §4.4
and §4.6, and `docs/CODEBASE_ASSEMBLY.md` §14. The conditions held on the rule types are in `backlog.md`.

The gate keeps one boundary rule, stated in `docs/ARCHITECTURE.md` §4.6: the gate that runs on every conversion
reads only data it can read offline, so a value the provider constrains in its code, not in the schema JSON, stays
outside the static rules, and the two checks that run an external command are gated by a flag (`--validate` and
`--tflint`) and report NOT RUN when the call did not ask for one. A plan reads the directory it runs on, so the
validate pins run the plan once per unit directory the manifest record names, and the rule-set check reads one
directory the same way, and Goal 2 holds for every fixture because the pin reads the files the run wrote.

The cross-check rule (`sanity_checks.check_round_trip`, `tests/test_round_trip.py`) is the one exception to that
boundary, because its fact compares two sets: the `.tf` block set it read, and the entry set the run's ledger read,
per unit and per coverage matrix row. A disagreeing count names no broken output, so the finding is a WARN and the
exit code stays with the rules that read the files (`docs/ARCHITECTURE.md` §4.6). The cross-check counts the entry
side through one destination rule, `entry_coverage.EntryLedger.destination`, stated in `docs/ARCHITECTURE.md` §3.2.

The second conversion path reads only API responses, one per scope, and writes the same codebase. Its rules are
in `docs/API_CONVERSION_PATH.md`.

The repository layout is a rule with one owner document, `docs/ARCHITECTURE.md` §1.1: `src/` is one flat
namespace, `tests/` is flat with `tests/conftest.py` as the one shared helper file, each index names every file
under it, and a directory with no index of its own is named by the root index. `AGENTS.md` names the tracking
markdown set.

## Goals

| Goal | Description | Definition of Done |
|---|---|---|
| 1 | Adequate testing and linting for iterative development, independent of Panorama or PAN-OS device access | CI passes offline. Every emitted resource type and argument is verified against the provider schema. |
| 2 | Complete support of the latest Terraform provider features for PAN-OS configuration | `terraform validate` passes on all fixture configs. Resource coverage is tracked by test. |
| 3 | Architectural support for complex, multi-device, real-life brown-field device configs | Multi-device-group and multi-vsys fixtures generate output with no silent drops and preserved policy order. |
| 4 | Full traceability and verification of the conversion | Every input entry is classified converted, report-only, or unaccounted in a per-entry report with line numbers. Every output passes the sanity gate. No silent drops, no unverified output. |
| 5 | Input comes from a declared source, and the run records which source it used | The parse boundary returns the same contract for every source. The F3.8 size and DTD checks apply to the bytes a source returns. A run with no network passes CI. The provenance record names the source, the scope, and the cache entry it read. |
| 6 | The output is a codebase, not one directory: one unit per declared scope, one owner per entry, and the path that binds each entry to the live config | A codebase run writes one directory per declared scope, a manifest that names each unit and the entries it owns, one scope object per declared scope, an import block per entry, the reference edges between units, and the site values as data with the `.tfvars` written from them. The gate reads the `.tf` files for the block rules and the four data files for the data rule. Every rule stays offline and deterministic. |
| 7 | A second conversion path that reads only Panorama and PAN-OS API responses | Path 2 reads no file. Its scope set comes from the membership responses it read, and every response is checked against the request that made it. CI runs it offline on committed responses with no server. It reads the same tables, naming rule, write path, and gate as path 1, and for content with no live-only fact it writes the same `.tf` bytes as path 1. |
| 8 | The codebase is assembled by more than one run, and each run names what it covers | A targeted run reads one scope plus the membership facts its unit identity needs, and writes the same unit bytes as a full run writes for that unit, for content that names no read-through name. A run that writes into an existing codebase merges its rows through the shape rule each record module owns and keeps the rows for the units it did not build. The run names the units it built and the codebase units it did not read in the report. Every rule stays offline and deterministic, and a run that builds a whole codebase writes the committed golden bytes. |

## Open epic — Epic 11, the codebase several runs write into (feature id `F11.x`)

The design record is `docs/MULTI_RUN_CODEBASE.md`. Phase 11A, the run's read set, is complete, so its detail is
removed here. The open phases:

- **11B, the records as codebase state**: the cross-run ownership, edge and order facts, and the gate for a
  partial run.
- **11C, the update run**: the existing records as a reference source, the write boundary, the run's report
  section, and the move fact.

The three levels the output sits in are the codebase root, the unit, and the unit's files. The unit level and
the file level are unchanged, because a unit directory is already one plan against one state and already holds
its own declarations. What Epic 11 adds is the root level read as state, and the layer that names which scopes a
run read and which units it built.

A brown-field config is an existing production config: mixed shared objects,
per-device-group overrides, template stacks, and multiple virtual systems.

## Planning — the API documentation as a source for the response set

The planning record is `docs/API_DOCUMENTATION_AND_MOCKS.md`. It is not an epic yet: the decision it puts in
front is whether documented response shapes can stand as committed response fixtures for the shape half of
the Epic 8 §4 facts, with the value half still gated on a live target. The recommended shape is a
documentation-derived response builder under `tools/`, read through the injected-producer seam, so Goal 1
and the standard-library rule are unchanged. Promoted to an epic on decision.

## Out of Scope (tracked in backlog.md)

- PAN-OS version matrix testing
- Lawyer review of the licensing rule
