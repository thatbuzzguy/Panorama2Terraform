# PLAN — Panorama to Terraform Converter

This file tracks epics and top-level features. Detailed design documents live in `docs/`.

## Current State

The adversarial audit (`ADVERSARIAL_AUDIT_REPORT.md`) found three blocking problems:

1. **Invalid Terraform output.** The generator pins provider v2 but emits a v1-style schema. `terraform validate` reports 24 errors on the repository sample.
2. **Silent data loss.** Name-keyed parsing drops per-device-group rules, policy order, VLANs, IPv6, and multi-port services.
3. **No test gate.** CI runs only `py_compile` and `--help`. Nothing verifies the generated Terraform.

Epic 1, Epic 2 and Epic 3 are complete. Problem 1 (invalid output) and problem 3 (no test gate) are closed. Problem 2 (silent data loss) is open: Epic 3 removed the name-keyed parsing and states the model and the rules in `docs/ARCHITECTURE.md`, and the Epic 4 per-entry report (F4.3) will classify every input entry as converted, report-only or unaccounted. F2.8 (coverage matrix) moved to Epic 4 as F4.4: it is now a live coverage structure, not an end-of-Epic-2 measurement; the type-level F2.8 matrix (row per emitted type + fixture row tests, `COVERAGE_MATRIX` in `resource_mapping.py`) landed 2026-07-13 and F4.4 extends it to property level.

## Goals

| Goal | Description | Definition of Done |
|------|-------------|-------------------|
| 1 | Adequate testing and linting for iterative development, independent of Panorama or PAN-OS device access | CI passes offline. Every emitted resource type and argument is verified against the provider schema. |
| 2 | Complete support of the latest Terraform provider features for PAN-OS configuration | `terraform validate` passes on all fixture configs. Resource coverage is tracked by test. |
| 3 | Architectural support for complex, multi-device, real-life brown-field device configs | Multi-device-group and multi-vsys fixtures generate output with no silent drops and preserved policy order. |
| 4 | Full traceability and verification of the conversion | Every input entry is classified converted, report-only, or unaccounted in a per-entry report with line numbers. Every output passes the sanity gate (terraform validate plus static invariants). No silent drops, no unverified output. |

A brown-field config is an existing production config: mixed shared objects, per-device-group overrides, template stacks, and multiple virtual systems.

## Epic 1 — Testing and Linting Foundation (Goal 1) — COMPLETE

Test against static artifacts (XML fixtures, provider schema JSON), not live devices. Delivered: tooling gate (pytest + ruff in CI and pre-commit), 42 parser unit tests (5 parser bugs found and fixed), golden-file tests for sample and kitchen-sink output, provider schema conformance (15 of 28 emitted types missing from v2 — xfailed until Epic 2), a `terraform init`/`validate` CI gate, an edge-case fixture corpus (splitter quote bug fixed), and security/robustness tests (DTD rejection, control-character escaping, collision-safe resource names). Suite: 106 passed, 46 xfailed, 13 xpassed. Detail is in the git history.

## Epic 2 — Complete Support of the Latest Provider (Goal 2) — COMPLETE

Strategy: the provider schema is the single source of truth. No resource names or attributes from memory. Target: `PaloAltoNetworks/panos` provider v2 (pinned `~> 2.0.14`; the registry's latest 2.x release).

Delivered: provider baseline pinned to `~> 2.0.14`; the resource mapping table (`resource_mapping.py` + `docs/RESOURCE_MAPPING.md`, every emitted type verified against the v2.0.14 schema); `location` on every resource derived from the XML source; all emitters rewritten to the v2.0.14 nested attribute shapes (proxy-ids merged into `panos_ipsec_tunnel.auto_key`); order-preserving per-device-group policy chains; dependency wiring (`.name` references only for names declared in the same run, never phantoms); deterministic collision-safe naming (sanitized name + 8-hex digest of the source identity); real v2 resources or explicit `MANUAL_SETUP_REPORT.txt` entries for every converted area (no comment-only output); a clean generated config (the three credential variables are declared and all consumed by the provider block; the dead `device_group` variable is gone; `tests/test_variables.py` pins it); and verified user-facing claims (the README references the test evidence; stale v1-era docs and unverified marketing claims are removed or corrected to the real v2 output). Both committed goldens pass `terraform validate` against v2.0.14. Detail is in the git history.

## Epic 3 — Architecture for Multi-Device Brown-Field Configs (Goal 3) — COMPLETE

Strategy: model the Panorama hierarchy before generation. Key objects by (device group, vsys, type, name). No name-only deduplication.

Delivered: the keyed data model (every parse method visits each entry once and records the four scope facts `identity_of` returns); device-group and vsys identity at emit, so the naming digest and the registry key cover (scope, context, vsys, name) and same-named objects in different scopes stay distinct without an order-dependent counter; all seven interface kinds plus virtual-wire and TAP blocks, with subinterface `parent` resolved to the declared parent; full object types (every address value element the schema models, all seven EDL sub-shapes, dual-protocol services reported because the provider accepts one leg); `location` chosen from the verified `LOCATION_SCHEMA` with no invented scope and every unusable scope reported; the multi-device association read from the export, not inferred from a name; one safe input read for both entry points (size cap checked before the read, DTD refused by the parser); per-device-group report sections through one shared grouping rule; and `docs/ARCHITECTURE.md`, the one document that states the data model, the parse pipeline, the emit pipeline and the naming rules, with each rule pinned by a test. Detail is in the git history.

## Epic 4 — Full Traceability and Verification (Goal 4)

Strategy: the conversion proves what it did. Input side: a report classifies every config entry, so nothing is silently dropped. Output side: a gate verifies every emitted file, so nothing is silently broken (F4.1 landed). Both halves reuse one shared structure: the coverage matrix (F4.4, former F2.8).

- [x] **F4.1 Post-run sanity gate** — Landed 2026-10-19. A `--validate` CLI flag
  runs `terraform init` + `terraform validate` on the output. A static check
  module (`sanity_checks.py`, pure Python) runs on every conversion and enforces:
  no dangling references, `location` on every resource, only `EMITTED_TYPES`,
  every variable consumed (absorbs the F2.10 check), no raw control characters,
  expected placeholders (VPN pre-shared keys) as WARN not FAIL. Writes
  `SANITY_REPORT.txt` plus a console summary; non-zero exit on FAIL. Determinism
  (two runs byte-identical) is pinned by test, not paid in the CLI. Each rule is
  stated once in the module, so the tests call it instead of copying it.
- [x] **F4.2 Entry coverage — container table and line tracking** — Landed 2026-10-20. `xml_input.ParsedSource` records the opening line of every element during the single read; `container_coverage.CONTAINER_TABLE` is the container table in code (seed of the F4.4 matrix); a section no row covers is reported in `MANUAL_SETUP_REPORT.txt` and on the console. Line tracking moved from `TreeBuilder` to expat handlers, because `TreeBuilder` has no line number.
- [x] **F4.3 Per-entry conversion report** — Landed 2026-10-20. Every parse method marks the entries it reads; `entry_coverage.py` holds the ledger, the row rules and the report text, and `TerraformGenerator.generate_conversion_report` writes `CONVERSION_REPORT.txt`: one line per entry (line, object type, entry name, destination, detail, captured fields), grouped by the F3.9 scope rule. A test asserts that every parse method that reads entries marks them, so the report cannot drift into lying.
- [ ] **F4.4 Property-level coverage (extends F2.8)** — The per-type property matrix is the single source of truth for which properties each emitter reads; the report classifies properties, not just entries. Each supported row has a fixture test. Permanent duty: every emitter change keeps the matrix honest. Foundation: the F2.8 type-level matrix landed 2026-07-13 (`COVERAGE_MATRIX`). Lands after F3.1, last in Epic 4.

## Out of Scope (tracked in backlog.md)

- Live Panorama API integration
- PAN-OS version matrix testing
- `.gitignore` consistency (committed sample XML vs the `*.xml` ignore rule)
- Dual-license legal review

## Sequencing

1. **Epic 1 first.** It is the gate. No feature lands without tests.
2. **Epic 3 is next.** It builds on the Epic 2 emitters and the shared fixture corpus. F3.1 (keyed data model), F3.2 (device-group + vsys identity at emit), F3.3 (full interface types), F3.4 (full object types), F3.5 (multi-vsys), F3.6 (multi-device, template-aware parsing), F3.7 (splitter rewrite), F3.8 (safe XML input) and F3.9 (per-device-group reports) landed; the next task is F3.10 (architecture document).
3. **Epic 4 interleaves.** F4.1 (sanity gate) is independent of the parser and its dead-variable check reuses the F2.10 test, so it can land anytime after Epic 2; it landed 2026-10-19. F4.2 (container table, line tracking) may land during Epic 3. F4.3 and F4.4 land after F3.1, so the consumed marks and the property matrix key on the keyed data model.

Rationale: Epic 1 makes Epics 2 and 3 safe to iterate on. The fixture corpus (F1.6) is the shared test asset for all three epics.
