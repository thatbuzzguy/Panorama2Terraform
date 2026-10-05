# PLAN — Panorama to Terraform Converter

This file tracks epics and top-level features. Detailed design documents live in `docs/`.

## Current State

The adversarial audit (`ADVERSARIAL_AUDIT_REPORT.md`) found three blocking problems:

1. **Invalid Terraform output.** The generator pins provider v2 but emits a v1-style schema. `terraform validate` reports 24 errors on the repository sample.
2. **Silent data loss.** Name-keyed parsing drops per-device-group rules, policy order, VLANs, IPv6, and multi-port services.
3. **No test gate.** CI runs only `py_compile` and `--help`. Nothing verifies the generated Terraform.

Epic 1 is complete. Epic 2 is in progress: F2.1–F2.7 and F2.9 have landed (provider pinned to `~> 2.0.14`, resource mapping table, `location` on every resource, emitters rewritten to the v2 attribute shapes, order-preserving policy chains, dependency wiring, deterministic collision-safe naming, and real resources or explicit reports for every converted area — no comment-only output remains). Both committed goldens now pass `terraform validate` against v2.0.14. Remaining Epic 2 work is cleanup (F2.10, F2.11). F2.8 (coverage matrix) moved to Epic 4 as F4.4: it is now a live coverage structure, not an end-of-Epic-2 measurement. Update 2026-07-13: the type-level F2.8 matrix (row per emitted type + fixture row tests, `COVERAGE_MATRIX` in `resource_mapping.py`) landed; F4.4 extends it to property level. Audit problem 2 (silent data loss) remains for Epic 3; the Epic 4 coverage report will surface each gap as it is confirmed. The test gate (problem 3) landed in Epic 1.

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

## Epic 2 — Complete Support of the Latest Provider (Goal 2)

Strategy: the provider schema is the single source of truth. No resource names or attributes from memory.

Target: `PaloAltoNetworks/panos` provider v2 (2.0.14+ per the audit). Track upstream releases.

- [x] **F2.1 Provider baseline** — Generate a `provider.tf` pinned to the v2 range. Record the supported range. (Pinned `~> 2.0.14`.)
- [x] **F2.2 Resource mapping** — One table maps old emitted names to real v2 resources. (`resource_mapping.py`; verified against the v2.0.14 schema.)
- [x] **F2.3 `location` on every resource** — Derive the block from the XML source: `shared`, `device_group`, or `vsys`. (Landed as the defining device group per object, or the default template for network/VPN resources. Per-DG instances and vsys sub-blocks land with F3.1/F3.5.)
- [x] **F2.4 Rewrite emitters to v2 schemas** — Use the real nested blocks (`protocol{}`, `layer3{}`, `auto_key{}`, `position{}`). Put proxy-id inside `panos_ipsec_tunnel`. Remove hardcoded assumptions (for example `panos_virtual_router.default`, the hardcoded OSPF area). (Landed: every emitted resource uses the v2.0.14 nested attribute shapes; proxy-ids merged into `panos_ipsec_tunnel.auto_key`; report-only types go to `MANUAL_SETUP_REPORT.txt`; sample and kitchen-sink outputs pass `terraform validate`.)
- [x] **F2.5 Order-preserving policy** — Emit rules in XML order per (device group, rulebase). Replace the blanket `position { where = "last" }` with order-preserving `position` values. (Landed: per-device-group chains in XML order; first rule anchors at the end of the rulebase, each later rule uses `where = "after"` with `directly = true`, the previous rule as pivot, and a `depends_on` on the previous rule so the apply order is the XML order. Pinned by `tests/test_policy_order.py` plus golden assertions. Same-named rules across device groups still deduplicate by name — F3.1.)
- [x] **F2.6 Dependency wiring** — Add `depends_on` or `.name` references where the provider supports them. (Landed: `name_ref` resolves a PAN-OS name to a `.name` reference only when the target is declared in the same run — group members, rule zones/addresses/services, NAT translation interfaces, zone and virtual-router interface lists, subinterface parents, and the VPN profile/gateway chain. Undeclared names stay plain brown-field strings and are never declared as phantoms. Interfaces emit before zones and virtual routers so the lists resolve. Pinned by `tests/test_dependency_wiring.py` with a no-dangling-reference invariant and a terraform validate gate; goldens regenerated.)
- [x] **F2.7 Collision-safe naming** — Build the resource name from the sanitized name plus a short hash of the source path. Handle empty and colliding names. (Landed: `declare_resource_name` assigns the sanitized name plus an 8-hex sha256 digest of the object's source identity (type, defining device group or template, raw name); the name is deterministic, empty and colliding names stay distinct, and a taken-address counter keeps the output valid HCL.)
- F2.8 (coverage matrix) moved to Epic 4 as **F4.4**. The matrix is now a live coverage structure with a permanent maintenance duty, and it lands after F3.1 so its keys match the keyed data model. The type-level matrix itself landed 2026-07-13 (`COVERAGE_MATRIX` + `tests/test_coverage_matrix.py` + `docs/COVERAGE_MATRIX.md`); F4.4 builds the property level on it.
- [x] **F2.9 Real resources or explicit reports** — Decryption, PBF, and PBF path monitoring profiles emit as real v2 resources with the full parsed body (per-rule chains like F2.5). App override, QoS, IPsec tunnel monitor, log forwarding, zone protection, and schedules go to `MANUAL_SETUP_REPORT.txt` with their captured data and the reason (no v2 resource, or v2 resource exists but the body is not parsed). Every comment-only `.tf` generator is removed; `NOT_EMITTED_TYPES` records the deliberate non-emissions with an existence guard. (Landed 2026-10-04; legacy PAN-OS 9 decryption actions normalize to the v2 action enum plus `type` block.)
- [ ] **F2.10 Clean generated config** — Remove dead variables. Every emitted variable is consumed.
- [ ] **F2.11 Verified claims** — README coverage claims reference F1.4 and F1.5 test evidence. Remove unverified "success rate" claims.

## Epic 3 — Architecture for Multi-Device Brown-Field Configs (Goal 3)

Strategy: model the Panorama hierarchy before generation. Key objects by (device group, vsys, type, name). No name-only deduplication.

- [ ] **F3.1 Keyed data model** — Replace name-keyed dictionaries. Key objects by (device group, vsys, type, name). Remove first-wins and last-wins deduplication.
- [ ] **F3.2 Preserve device-group association** — Carry the source device group from parse to emit. Same-named objects in different device groups both survive.
- [ ] **F3.3 Full interface types** — VLAN, loopback, subinterfaces, virtual-wire, TAP, and aggregate. Not only physical ethernet.
- [ ] **F3.4 Full object types** — IPv6, ip-wildcard, external, and location addresses. Multi-port services. Combined tcp+udp services.
- [ ] **F3.5 Multi-vsys** — Represent vsys in the data model and in `location`.
- [ ] **F3.6 Multi-device, template-aware parsing** — Use explicit device-group → template association. Replace substring matching.
- [ ] **F3.7 Rewrite `split_device_groups.py`** — Iterate entries and compare `get('name')`. No f-string XPath. Safe shared-section merge. Covered by F1.2 tests.
- [ ] **F3.8 Safe XML input** — Reject DTDs or use `defusedxml`. (DTD rejection already landed in F1.7; remainder is an input size limit or `defusedxml`.)
- [ ] **F3.9 Per-device-group reports** — Key the interface migration report and the VPN report by device group. Keep the pre-shared-key placeholder warning in the VPN report.
- [ ] **F3.10 Architecture document** — Write `docs/ARCHITECTURE.md`: data model, parse pipeline, emit pipeline, and naming rules.

## Epic 4 — Full Traceability and Verification (Goal 4)

Strategy: the conversion proves what it did. Input side: a report classifies every config entry, so nothing is silently dropped. Output side: a gate verifies every emitted file, so nothing is silently broken. Both halves reuse one shared structure: the coverage matrix (F4.4, former F2.8).

- [ ] **F4.1 Post-run sanity gate** — A `--validate` CLI flag runs `terraform init` + `terraform validate` on the output. A static check module (pure Python, runs on every conversion) enforces: no dangling references, `location` on every resource, only `EMITTED_TYPES`, every variable consumed (absorbs the F2.10 check), no raw control characters, expected placeholders (VPN pre-shared keys) as WARN not FAIL. Writes `SANITY_REPORT.txt` plus a console summary; non-zero exit on FAIL. Determinism (two runs byte-identical) is pinned by test, not paid in the CLI.
- [ ] **F4.2 Entry coverage — container table and line tracking** — A line-tracking `TreeBuilder` in the parser (ElementTree does not record lines today). A static table maps known containers to their parse methods (seed of the F4.4 matrix). Every unknown container is reported. May land during Epic 3.
- [ ] **F4.3 Per-entry conversion report** — Parse methods mark the entries they consume; `CONVERSION_REPORT.txt` classifies every `<entry>` as converted / report-only / unaccounted with line number and XPath. A test asserts that every element a parse method reads is marked, so the report cannot drift into lying. Lands after F3.1 so the marks key on the keyed model.
- [ ] **F4.4 Property-level coverage (extends F2.8)** — The per-type property matrix is the single source of truth for which properties each emitter reads; the report classifies properties, not just entries. Each supported row has a fixture test. Permanent duty: every emitter change keeps the matrix honest. Foundation: the F2.8 type-level matrix landed 2026-07-13 (`COVERAGE_MATRIX`). Lands after F3.1, last in Epic 4.

## Out of Scope (tracked in backlog.md)

- Live Panorama API integration
- PAN-OS version matrix testing
- `.gitignore` consistency (committed sample XML vs the `*.xml` ignore rule)
- Dual-license legal review

## Sequencing

1. **Epic 1 first.** It is the gate. No feature lands without tests.
2. **F3.1 refines F2.3 and F2.5.** F2.3 landed with the defining device group per object (the keyed model's per-DG instances and vsys sub-blocks land with F3.1). F2.5 landed per-device-group chains on the name-keyed model; F3.1 removes the name dedup so same-named rules in different device groups both survive inside their chains.
3. **Epic 2 and Epic 3 overlap.** They share the data model and the fixture corpus.
4. **Epic 4 interleaves.** F4.1 (sanity gate) is the next task: it is independent of the parser, and its dead-variable check absorbs the F2.10 verification. F4.2 (container table, line tracking) may land during Epic 3. F4.3 and F4.4 land after F3.1, so the consumed marks and the property matrix key on the keyed data model.

Rationale: Epic 1 makes Epics 2 and 3 safe to iterate on. The fixture corpus (F1.6) is the shared test asset for all three epics.
