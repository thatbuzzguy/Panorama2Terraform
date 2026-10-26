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

Two features are open: the property-level coverage matrix (F4.4, Epic 4), and the
upstream source layer (Epic 5). The open gaps and decided limits are in `backlog.md`.

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

## Epic 5 — Upstream Data Sources (Goal 5)

The tool reads one kind of source today: a file, through `xml_input.parse_xml`
(`docs/ARCHITECTURE.md` §1). Epic 5 makes the source a declared thing, so a run can
read the same config from a file, from a cached Panorama API export, or from
Terraform state, and so an entry can name which source it came from.

- [x] **F5.1 Source read boundary** (refactor, no behaviour change) —
  `parse_bytes(data, origin)` holds the F3.8 size and DTD checks, and `parse_xml(path)`
  is the file producer. `ParsedSource` carries the source origin. The report label stays
  as it is, because the label change belongs with the provenance record, so F5.1 writes
  the same report bytes as before. Every other piece in this epic depends on this one.
- [ ] **F5.2 Cached API export** — `source_fetch.py`. The SDK is a byte producer
  only: the parse layer keeps the ElementTree tree, because the container table,
  the entry ledger and the line map are keyed on the tree. The response is cached
  and the cache is what gets parsed, so a report line still names bytes a reader
  can reopen. `--offline` reads the cache only. CI uses a fixture-backed producer,
  so no test calls the network.
- [ ] **F5.3 Provenance record** — `SOURCE.txt` names the source, the scope and the
  cache entry. It is written outside the report bodies, so the report byte rule
  still holds. This feature also carries the report label change to `Source:`.
- [ ] **F5.4 Cross-source shadow report** — needs F4.4. A per-device-group run
  cannot see its parent, so an inherited name stays a plain string and a shadowed
  object is invisible. With the parent as a second source, the ledger names the
  source of each entry, and a child name that repeats a parent name is reported as
  a shadow.
- [ ] **F5.5 Read-through data blocks** (opt-in) — plain strings stay the default
  for a name outside the run. A declared upstream scope may emit `data` blocks
  instead, where the value has to be verified. Needs `DATA_SOURCE_SCHEMA` in
  `resource_mapping.py`, verified against the provider `data_source_schemas`, and
  one new gate rule. The provider facts are in `backlog.md`.
- [ ] **F5.6 Terraform state as a source** — report-only ownership and drift: which
  entries another workspace already owns. Offline, because a state file is a JSON
  document. Needs F4.4, because ownership and drift are property-level facts.

## Sequencing

1. F5.1 is a refactor that changes no behaviour, so it can land before F4.4. F4.4
   builds on the F4.2 container table and the F4.3 ledger, so it does not need a new
   naming or grouping rule.
2. F4.4 comes before F5.4 and F5.6, because a shadow and a drift are property-level
   facts and the property scan is the only thing that can state them.
3. Fix the two open defects found while refreshing the documentation in the same
   pass as F4.4, because both change report output: the overlapping BGP and OSPF
   paths (`backlog.md`), and the manual report sections that do not name their scope.

## Out of Scope (tracked in backlog.md)

- PAN-OS version matrix testing
- Dual-license legal review
