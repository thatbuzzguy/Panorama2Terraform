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

The gate keeps one boundary rule, stated in `docs/ARCHITECTURE.md` §4.6: it reads only data it can read offline, so a
value the provider constrains in its code, not in the schema JSON, stays outside the static rules and the `terraform`
check reports it on `--validate`. A plan reads the directory it runs on, so the validate pins run the plan once per
unit directory the manifest record names, and Goal 2 holds for every fixture because the pin reads the files the run
wrote.

The cross-check rule (`sanity_checks.check_round_trip`, `tests/test_round_trip.py`) is the one exception to that
boundary, because its fact compares two sets: the `.tf` block set it read, and the entry set the run's ledger read,
per unit and per coverage matrix row. A disagreeing count names no broken output, so the finding is a WARN and the
exit code stays with the rules that read the files (`docs/ARCHITECTURE.md` §4.6).

The cross-check counts the entry side through one destination rule. `entry_coverage.EntryLedger.destination` is
the one place that answers a destination, in the order the per-entry fact on the recorded object, then the
destination `mark` recorded, then the container table row, and `mark` records a destination only when the caller
states it. So an entry the run reports enters no count, even when the row that covers its container is an
`emitted` row. The rule is in `docs/ARCHITECTURE.md` §3.2, `docs/README.md` names `entry_coverage.py` as its
owner, and `tests/test_round_trip.py::test_an_entry_the_run_reports_is_not_counted` holds it.

The three shape tables each have one owner and one gate rule that reads them: `PROTOCOL_SHAPE` and
`protocol_object`, `FILTER_SHAPE` and `filter_blocks`, `CERTIFICATE_SHAPE` and `certificate_blocks` (F7.14). Each
rule reads the block through the same block reader and the same field reader, so a printed block and a
hand-written block are read the same way.

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

A brown-field config is an existing production config: mixed shared objects,
per-device-group overrides, template stacks, and multiple virtual systems.

## Epic 6 — Codebase assembly (Goal 6) — closed

A codebase is a set of directories, one per declared scope, that a platform plans and
applies. The design record is `docs/CODEBASE_ASSEMBLY.md`, and every rule it states names the module
and the test that holds it. The unit rule, the owner rule, the edge rule, the order rule, the import
block rule, the scope object rule, the site rule, and the action rule are all landed, and the write
path writes one directory per unit the manifest names.

## Epic 8 — the API-only conversion path (Goal 7) — open

Path 2 reads only API responses, one per scope, and writes the same codebase. The design record is
`docs/API_CONVERSION_PATH.md`, and every rule it states names the module and the test that holds it.

Phase 8A — the read boundary. The accepted request shapes (the whole-config export, the per-scope
read, and the device fact shape), the scope index read from the membership responses, and the join
between a response and the request that made it. The offline harness is part of this phase, so no
piece in it needs a server.

Phase 8B — the run over many sources. The parse methods run per response, the report position names
the line inside the response that held the entry, the record holds one record per request, and the
unit join reads the scope the run read for each unit.

Phase 8C — the gate and the entry point. Every existing gate rule reads the same files, so path 2
adds one rule: the request set must agree with the scope the run read. The entry point states the
arguments, the run order, the exit codes, and the generated `README.md` label that names which path
wrote the codebase.

Phase 8D — the facts only a live target states: the rulebase per rule, the rule position, the device
serial, the per-device template variable override, and the built-in name table. Each fact is gated on
its own condition, recorded in `backlog.md`, and none of it is a piece until a committed response
shows its shape.

Definition of done for the epic: CI runs path 2 with no server, its output passes the gate, the
record names every request the run read, and for a fixture with no live-only fact the `.tf` bytes
agree with path 1.

## Sequencing

The rule that keeps a container outside the scan scope honest is in `docs/COVERAGE_MATRIX.md` §1: the output that
reaches the entry must read the field it names, because a container with no matrix row cannot produce a finding.
Four shapes state it, one per kind. A `report` container's section reads the field it prints through the captured
object; a `count-only` row has no section, so the per-entry report line prints the value of each field it names,
read through the captured object; a `nested-block` line names only the fields the print reads, because a nested
block prints only what its type declares; a `bookkeeping` line names no field, because the fact its row records is
the relation between an entry and the membership container that lists it, and the entry carries no value for that
relation. Measured 2026-11-04 the four rules hold for every container in the corpus, so the work that used them is
closed.

The credential rule single statement is complete, and `docs/CODEBASE_ASSEMBLY.md` §11 is the owner document for it.
The certificate container row, its emitters and its gate rule are complete (`docs/ARCHITECTURE.md` §4.11). The
round-trip cross-check is complete, and `docs/ARCHITECTURE.md` §4.6 is the owner document for it: the rule reads
the generated HCL back through the one gate reader and compares the block count with the run's entry ledger, per
unit and per coverage matrix row. The `report_only` timing fact that rule measured is landed and closed here,
through the destination rule in Current State. The certificate `REFERENCE_ONLY` rows for `private_key` and
`passphrase` are landed in `resource_mapping.VALUE_VARIABLES`, read by the emitter, the gate and the `.tfvars`
writer through the same table, so that feature is closed. The next actionable slice is `ruff format` as a gate,
which `backlog.md` records as its own task. The gated
pieces that stay held in `backlog.md` are the four `*_policy_rules` types, which wait for the F3.5 rulebase
decision and a live target, and a config entry inside a stack, which needs a provider location shape before the
emitter can write a block for it. The rows that state fewer fields than the pinned provider declares for their
level are the choice levels, which state their alternatives as `selects` keys.

## Out of Scope (tracked in backlog.md)

- PAN-OS version matrix testing
- Lawyer review of the licensing rule
