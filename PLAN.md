# PLAN — Panorama to Terraform Converter

This file tracks epics and top-level features. Detailed design documents live in `docs/`.

## Current State

The adversarial audit (`ADVERSARIAL_AUDIT_REPORT.md`) found three blocking problems:

1. **Invalid Terraform output.** The generator pins provider v2 but emits a v1-style schema. `terraform validate` reports 24 errors on the repository sample.
2. **Silent data loss.** Name-keyed parsing drops per-device-group rules, policy order, VLANs, IPv6, and multi-port services.
3. **No test gate.** CI runs only `py_compile` and `--help`. Nothing verifies the generated Terraform.

Epic 1 and Epic 2 are complete. Epic 2 delivered full provider-v2 support: provider pinned to `~> 2.0.14`, resource mapping table, `location` on every resource, emitters rewritten to the v2 attribute shapes, order-preserving policy chains, dependency wiring, deterministic collision-safe naming, real resources or explicit reports for every converted area (no comment-only output), a clean generated config (every emitted variable consumed), and user-facing claims verified against the real output and the test evidence. Both committed goldens pass `terraform validate` against v2.0.14. F2.8 (coverage matrix) moved to Epic 4 as F4.4: it is now a live coverage structure, not an end-of-Epic-2 measurement; the type-level F2.8 matrix (row per emitted type + fixture row tests, `COVERAGE_MATRIX` in `resource_mapping.py`) landed 2026-07-13 and F4.4 extends it to property level. Audit problem 2 (silent data loss) remains for Epic 3; the Epic 4 coverage report will surface each gap as it is confirmed. The test gate (problem 3) landed in Epic 1.

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

## Epic 3 — Architecture for Multi-Device Brown-Field Configs (Goal 3)

Strategy: model the Panorama hierarchy before generation. Key objects by (device group, vsys, type, name). No name-only deduplication.

F3.1 (keyed data model) landed: every parse method visits each entry once and records `device_group` + `vsys` on every object; the generator resolves references by the referrer's context (referrer DG, then Shared, then contextless, then a flat first-declaration fallback); same-named objects across device groups or vsys both survive with stable names; goldens byte-identical.

F3.2 (device-group + vsys identity at emit) landed: the naming digest and the registry key cover (scope, context, vsys, name), so same-named objects in different device groups or virtual systems get distinct names without the order-dependent `_2` counter; `name_ref` resolves in the referrer's (context, vsys) pair; policy chains key on (device group, vsys), so a rule never pivots on a rule in another vsys. Both goldens regenerated (digest-only diff).

- [x] **F3.2 Preserve device-group association** — COMPLETE. Carry the source device group from parse to emit. Same-named objects in different device groups both survive.
F3.3 (full interface types) landed: every interface kind the parser finds now emits its schema-verified v2 resource (`panos_vlan_interface`, `panos_loopback_interface`, `panos_tunnel_interface`, `panos_aggregate_interface`, `panos_aggregate_layer3_subinterface`); ethernet subinterface units and virtual-wire units parse as individual entries; virtual-wire and TAP emit as nested blocks on `panos_ethernet_interface` (the provider has no resource type for them); subinterface `parent` resolves to the declared parent resource; the `ip` list bug in the subinterface emitter is fixed.

- [x] **F3.3 Full interface types** — COMPLETE. VLAN, loopback, subinterfaces, virtual-wire, TAP, and aggregate. Not only physical ethernet.
- [x] **F3.4 Full object types** — COMPLETE. IPv6, ip-wildcard, multi-port and dual-protocol services.
F3.4 (full object types) landed: the address parser reads every value element the v2.0.14 schema models (`ip-netmask`, `ip-range`, `ip-wildcard`, `fqdn`, `ipv6`, `ipv6-range`) plus `tag`, `description` and `disable-override`; an entry with no v2 attribute (location type, external type) is captured generically and reported instead of emitted as an empty resource. The EDL parser and emitter cover all seven v2 sub-shapes and the fields each one models (`exception_list`, `expand_domain` on domain only, `certificate_profile`, the five recurring keys), and never capture `auth` credentials. Services keep both protocol legs in the parse model with `source_port`, the `override` timeouts and tags; `panos_service` accepts one protocol leg (verified with `terraform validate`), so the tcp leg emits and the dropped leg is a NOTE plus a report entry.
- [x] **F3.5 Multi-vsys** — COMPLETE. Represent vsys in the data model and in `location`.
F3.5 (multi-vsys) landed: the parser records the scope an export declares and invents nothing — `vsys` is `''` outside a `<vsys><entry>` (no more default `vsys1`), `template` is `''` outside a template, and `vsys_device` names the enclosing `devices/entry`; one `identity_of(elem)` helper returns all four facts and every parse method uses it. `LOCATION_SCHEMA` in `resource_mapping.py` holds the `location` sub-blocks and fields the v2.0.14 schema declares per emitted type, and `location_block` chooses from it: `vsys { name, ngfw_device }` for a declared vsys, `template { name }` plus `vsys` where that sub-block declares it, otherwise the device group, `shared = {}` for the shared section (not a device group named "Shared"), or the `Shared` template placeholder F3.6 replaces. `localhost.localdomain` is the PAN-OS placeholder for "this device", so it is never emitted as `ngfw_device`. Every scope the type cannot carry, and every vsys location with no target device, is listed in `MANUAL_SETUP_REPORT.txt`. Router parsing now finds routers under `devices/entry/<device>/network` (device-level routers were missed before), and a name a device declared resolves inside that device only, so a firewall never references another firewall's interface resource.
- [x] **F3.6 Multi-device, template-aware parsing** — COMPLETE. Use explicit device-group → template association. Replace substring matching.
F3.6 (multi-device) landed: `parse_associations()` reads the four membership lists the export declares (`device-group/entry/*/devices/entry`, `templates/entry/*/devices/entry`, `template-stack/entry/*/devices/entry`, `template-stack/entry/*/templates/member`, `<devices><member>` too) into device → device group / template / stack and stack → template tables, and `templates_for_device()` resolves a device's direct templates plus its stacks' templates; an export that lists no device yields empty tables, never a guessed association. Config an export places under `devices/entry/<device>/` is that firewall's own config, so `location_block` emits `ngfw = { ngfw_device = "<device>" }` for it (the 14 template-scoped types that declare `location.ngfw`, added to `LOCATION_SCHEMA`; `panos_zone` is template-scoped and declares none, so it is reported instead), and an entry nested under a device inside a template adds `ngfw_device` to its `template` block. The naming context of a template-scoped object is its template, else its device, so two firewalls that both declare `ethernet1/1` are two resources with two locations instead of one plus a `_2` counter; a deviceless reference to a name two devices declare stays a plain string rather than pointing at one firewall. The `Shared` template placeholder survives only where nothing in the export places the entry, and every use is listed in `MANUAL_SETUP_REPORT.txt` with the templates that device does take. The splitter joins a device group, a template and a template stack on the devices they list, so the `DG-` prefix convention and the substring test are gone, and it copies with `copy.deepcopy` because ElementTree `append` aliases one element in two trees.
- [x] **F3.7 Rewrite `split_device_groups.py`** — COMPLETE (landed inside F3.6). Entry iteration with `get('name')` comparison, no f-string XPath, a shared-section merge that copies, and splitter tests that pin the association and the untouched source tree.
- [x] **F3.8 Safe XML input** — COMPLETE. One safe read for both entry points: a capped input size plus a DTD refusal the parser makes, not a text search.
F3.8 (safe input) landed: `xml_input.py` is the single implementation both entry points import (`parse_xml`, `UnsafeInputError`, `--max-input-bytes`). The read is capped at 64 MiB and the size is checked before the file is allocated; `--max-input-bytes N` raises it on both CLIs. The DTD check moved from a UTF-8 text search to the parser itself (an expat prolog scan that stops at the root element), which closed a real bypass: a UTF-16 export hid `<!DOCTYPE` from the text search while expat parsed and expanded the DTD (reproduced), and the same search refused a `<!DOCTYPE` that only appeared in a prolog comment. Verified that a DTD is the only entity door — with no DTD expat expands nothing (`&a;` is a parse error) and fetches nothing (no `ExternalEntityRefHandler`) — so no `defusedxml` dependency was added, and `defusedxml` would not have covered the size risk. A refusal names the file, the limit and the measured size, exits non-zero, and writes no output; the tree is parsed from the bytes that passed the checks, so the input is read once.
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
2. **Epic 3 is next.** It builds on the Epic 2 emitters and the shared fixture corpus. F3.1 (keyed data model), F3.2 (device-group + vsys identity at emit), F3.3 (full interface types), F3.4 (full object types), F3.5 (multi-vsys), F3.6 (multi-device, template-aware parsing), F3.7 (splitter rewrite) and F3.8 (safe XML input) landed; the next task is F3.9 (per-device-group reports).
3. **Epic 4 interleaves.** F4.1 (sanity gate) is independent of the parser and its dead-variable check reuses the F2.10 test, so it can land anytime after Epic 2. F4.2 (container table, line tracking) may land during Epic 3. F4.3 and F4.4 land after F3.1, so the consumed marks and the property matrix key on the keyed data model.

Rationale: Epic 1 makes Epics 2 and 3 safe to iterate on. The fixture corpus (F1.6) is the shared test asset for all three epics.
