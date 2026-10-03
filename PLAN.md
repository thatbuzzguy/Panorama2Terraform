# PLAN — Panorama to Terraform Converter

This file tracks epics and top-level features. Detailed design documents live in `docs/`.

## Current State

The adversarial audit (`ADVERSARIAL_AUDIT_REPORT.md`) found three blocking problems:

1. **Invalid Terraform output.** The generator pins provider v2 but emits a v1-style schema. `terraform validate` reports 24 errors on the repository sample.
2. **Silent data loss.** Name-keyed parsing drops per-device-group rules, policy order, VLANs, IPv6, and multi-port services.
3. **No test gate.** CI runs only `py_compile` and `--help`. Nothing verifies the generated Terraform.

Epic 1 is complete. Epic 2 is in progress: F2.1–F2.4 have landed (provider pinned to `~> 2.0.14`, resource mapping table, `location` on every resource, emitters rewritten to the v2 attribute shapes). Both committed goldens now pass `terraform validate` against v2.0.14. Remaining Epic 2 work is order preservation, dependency wiring, naming, coverage matrix, report finalization, and cleanup. Audit problem 2 (silent data loss) remains for Epic 3; the test gate (problem 3) landed in Epic 1.

## Goals

| Goal | Description | Definition of Done |
|------|-------------|-------------------|
| 1 | Adequate testing and linting for iterative development, independent of Panorama or PAN-OS device access | CI passes offline. Every emitted resource type and argument is verified against the provider schema. |
| 2 | Complete support of the latest Terraform provider features for PAN-OS configuration | `terraform validate` passes on all fixture configs. Resource coverage is tracked by test. |
| 3 | Architectural support for complex, multi-device, real-life brown-field device configs | Multi-device-group and multi-vsys fixtures generate output with no silent drops and preserved policy order. |

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
- [ ] **F2.5 Order-preserving policy** — Emit rules in XML order per (device group, rulebase). Replace the blanket `position { where = "last" }` with order-preserving `position` values.
- [ ] **F2.6 Dependency wiring** — Add `depends_on` or `.name` references where the provider supports them.
- [ ] **F2.7 Collision-safe naming** — Build the resource name from the sanitized name plus a short hash of the source path. Handle empty and colliding names.
- [ ] **F2.8 Coverage matrix** — Maintain a provider-resource ↔ Panorama-XML-element matrix. Give each supported row a fixture test.
- [ ] **F2.9 Real resources or explicit reports** — Replace comment-only generators (decryption, PBF, app-override, QoS, log-settings) with real v2 resources or an explicit "manual setup" checklist.
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

## Out of Scope (tracked in backlog.md)

- Live Panorama API integration
- PAN-OS version matrix testing
- `.gitignore` consistency (committed sample XML vs the `*.xml` ignore rule)
- Dual-license legal review

## Sequencing

1. **Epic 1 first.** It is the gate. No feature lands without tests.
2. **F3.1 refines F2.3 and F2.5.** F2.3 landed with the defining device group per object (the keyed model's per-DG instances and vsys sub-blocks land with F3.1). Policy order (F2.5) still needs the keyed model.
3. **Epic 2 and Epic 3 overlap.** They share the data model and the fixture corpus.
4. **F2.8 (coverage matrix) lands last in Epic 2.** It measures the final state.

Rationale: Epic 1 makes Epics 2 and 3 safe to iterate on. The fixture corpus (F1.6) is the shared test asset for all three epics.
