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

One feature is open: the upstream source layer (Epic 5). The open gaps and decided
limits are in `backlog.md`.

## Goals

| Goal | Description | Definition of Done |
|---|---|---|
| 1 | Adequate testing and linting for iterative development, independent of Panorama or PAN-OS device access | CI passes offline. Every emitted resource type and argument is verified against the provider schema. |
| 2 | Complete support of the latest Terraform provider features for PAN-OS configuration | `terraform validate` passes on all fixture configs. Resource coverage is tracked by test. |
| 3 | Architectural support for complex, multi-device, real-life brown-field device configs | Multi-device-group and multi-vsys fixtures generate output with no silent drops and preserved policy order. |
| 4 | Full traceability and verification of the conversion | Every input entry is classified converted, report-only, or unaccounted in a per-entry report with line numbers. Every output passes the sanity gate. No silent drops, no unverified output. |
| 5 | Input comes from a declared source, and the run records which source it used | The parse boundary returns the same contract for every source. The F3.8 size and DTD checks apply to the bytes a source returns. A run with no network passes CI. The provenance record names the source, the scope, and the cache entry it read. |

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

## Epic 5 — Upstream Data Sources (Goal 5)

The tool reads two kinds of source now: a file, and a cached Panorama API response
through `source_fetch.py` (`docs/ARCHITECTURE.md` §3). Epic 5 makes the source a declared
thing, so a run can read the same config from a file, from the API export, or from
Terraform state, and so an entry can name which source it came from.

- [x] **F5.1 Source read boundary** (refactor, no behaviour change) —
  `parse_bytes(data, origin)` holds the F3.8 size and DTD checks, and `parse_xml(path)`
  is the file producer. `ParsedSource` carries the source origin. The report label stays
  as it is, because the label change belongs with the provenance record, so F5.1 writes
  the same report bytes as before. Every other piece in this epic depends on this one.
- [x] **F5.2 Cached API export** — `source_fetch.py`, a standard-library byte producer for
  the door. The response wrapper is normalised to the `config` element, so the container
  table needs no wrapper row and the line map survives. The cache entry is what gets parsed,
  and its name is the request identity without the credential. `--offline` reads the cache
  only, so a run with no network passes CI. https only, no scheme-changing redirect, key from
  the environment. The rules are in `docs/ARCHITECTURE.md` §3.
- [x] **F5.3 Provenance record** — `SOURCE.txt`, one record per completed run, as
  `field: value` data: the source kind, the name, the path, the scope, the request
  identity, the cache entry, and the size and SHA-256 hex of the bytes the door parsed.
  Written outside the report bodies, so the report byte rule holds. It carries the report
  label change to `Source:`. The rules are in `docs/ARCHITECTURE.md` §3.3.
- [ ] **F5.4 Cross-source shadow report** — uses the property scan (F4.4). A
  per-device-group run cannot see its parent, so an inherited name stays a plain string
  and a shadowed object is invisible. With the parent as a second source, the ledger
  names the source of each entry, and a child name that repeats a parent name is
  reported as a shadow.
- [ ] **F5.5 Read-through data blocks** (opt-in) — plain strings stay the default
  for a name outside the run. A declared upstream scope may emit `data` blocks
  instead, where the value has to be verified. Needs `DATA_SOURCE_SCHEMA` in
  `resource_mapping.py`, verified against the provider `data_source_schemas`, and
  one new gate rule. The provider facts are in `backlog.md`.
- [ ] **F5.6 Terraform state as a source** — report-only ownership and drift: which
  entries another workspace already owns. Offline, because a state file is a JSON
  document. Uses the property scan (F4.4), because ownership and drift are
  property-level facts.

## Sequencing

1. Epic 4 is complete, so the open work is Epic 5. F5.1, F5.2 and F5.3 landed, so F5.4 is
   next: it reads a declared scope, and the record `scope` field is the hook F5.3 left for it
   (`whole-config` is the only value a source writes today).
2. F5.4 and F5.6 use the property scan F4.4 landed, because a shadow and a drift are
   property-level facts.
3. The two report defects found while refreshing the documentation landed with F4.4:
   the overlapping BGP and OSPF paths, and the manual report sections that did not name
   their scope.

## Out of Scope (tracked in backlog.md)

- PAN-OS version matrix testing
- Dual-license legal review
