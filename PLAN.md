# PLAN — Panorama to Terraform Converter

This file tracks epics and top-level features. Detailed design documents live in `docs/`.

## Current State

The adversarial audit (`ADVERSARIAL_AUDIT_REPORT.md`) found three blocking problems:

1. **Invalid Terraform output.** The generator pins provider v2 but emits a v1-style schema. `terraform validate` reports 24 errors on the repository sample.
2. **Silent data loss.** Name-keyed parsing drops per-device-group rules, policy order, VLANs, IPv6, and multi-port services.
3. **No test gate.** CI runs only `py_compile` and `--help`. Nothing verifies the generated Terraform.

## Goals

| Goal | Description | Definition of Done |
|------|-------------|-------------------|
| 1 | Adequate testing and linting for iterative development, independent of Panorama or PAN-OS device access | CI passes offline. Every emitted resource type and argument is verified against the provider schema. |
| 2 | Complete support of the latest Terraform provider features for PAN-OS configuration | `terraform validate` passes on all fixture configs. Resource coverage is tracked by test. |
| 3 | Architectural support for complex, multi-device, real-life brown-field device configs | Multi-device-group and multi-vsys fixtures generate output with no silent drops and preserved policy order. |

A brown-field config is an existing production config: mixed shared objects, per-device-group overrides, template stacks, and multiple virtual systems.

## Epic 1 — Testing and Linting Foundation (Goal 1)

Strategy: test against static artifacts, not live devices. The static artifacts are XML fixture configs and the provider schema JSON. Both download without Panorama access.

- [ ] **F1.1 Tooling baseline** — Add pytest and ruff to `requirements.txt`. Run lint and tests in pre-commit and CI.
- [ ] **F1.2 Parser unit tests** — One test per parse method. Fixtures are isolated XML snippets.
- [ ] **F1.3 Generator golden-file tests** — Generate from a fixture, diff the result against committed expected output.
- [ ] **F1.4 Provider schema conformance test** — Load `terraform providers schema -json`. Assert that every emitted resource type exists. Assert that required arguments (for example `location`) are present.
- [ ] **F1.5 CI Terraform gate** — Run `terraform init -backend=false` and `terraform validate` on generated sample output.
- [ ] **F1.6 Fixture corpus** — Build synthetic configs that cover edge cases: quoted device-group names, duplicate names across device groups, multi-vsys, mixed virtual and logical routers, IPv6, multi-port services.
- [ ] **F1.7 Security and robustness tests** — Hostile XML (entity expansion), DTD rejection, control-character escaping, empty and colliding names.
- [ ] **F1.8 Lint both scripts** — Put `panorama_to_terraform.py` and `split_device_groups.py` under the same gate.

## Epic 2 — Complete Support of the Latest Provider (Goal 2)

Strategy: the provider schema is the single source of truth. No resource names or attributes from memory.

Target: `PaloAltoNetworks/panos` provider v2 (2.0.14+ per the audit). Track upstream releases.

- [ ] **F2.1 Provider baseline** — Generate a `provider.tf` pinned to the v2 range. Record the supported range.
- [ ] **F2.2 Resource mapping** — One table maps old emitted names to real v2 resources: `panos_address`, `panos_service`, `panos_security_policy_rule`, `panos_nat_policy_rule`, `panos_bgp_*_routing_profile`, `panos_ospf_*_routing_profile`, `panos_virtual_router_static_route_ipv4`, `panos_ethernet_layer3_subinterface`.
- [ ] **F2.3 `location` on every resource** — Derive the block from the XML source: `shared`, `device_group`, or `vsys`.
- [ ] **F2.4 Rewrite emitters to v2 schemas** — Use the real nested blocks (`protocol{}`, `layer3{}`, `auto_key{}`, `position{}`). Put proxy-id inside `panos_ipsec_tunnel`. Remove hardcoded assumptions (for example `panos_virtual_router.default`, the hardcoded OSPF area).
- [ ] **F2.5 Order-preserving policy** — Emit rules in XML order per (device group, rulebase). Remove the blanket `position = "bottom"`.
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
- [ ] **F3.8 Safe XML input** — Reject DTDs or use `defusedxml`.
- [ ] **F3.9 Per-device-group reports** — Key the interface migration report and the VPN report by device group. Keep the pre-shared-key placeholder warning in the VPN report.
- [ ] **F3.10 Architecture document** — Write `docs/ARCHITECTURE.md`: data model, parse pipeline, emit pipeline, and naming rules.

## Out of Scope (tracked in backlog.md)

- Live Panorama API integration
- PAN-OS version matrix testing
- `.gitignore` consistency (committed sample XML vs the `*.xml` ignore rule)
- Dual-license legal review

## Sequencing

1. **Epic 1 first.** It is the gate. No feature lands without tests.
2. **F3.1 before F2.3 and F2.5.** The `location` block and policy order both depend on the keyed data model.
3. **Epic 2 and Epic 3 overlap.** They share the data model and the fixture corpus.
4. **F2.8 (coverage matrix) lands last in Epic 2.** It measures the final state.

Rationale: Epic 1 makes Epics 2 and 3 safe to iterate on. The fixture corpus (F1.6) is the shared test asset for all three epics.
