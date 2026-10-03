# To-Do — Epic 2: Complete Support of the Latest Provider (Goal 2)

Goal 2: `terraform validate` passes on all fixture configs. Resource coverage is tracked by test.

Epic 1 is complete; its xfail tests (15 missing v2 types, validate
failures) flip green as this epic lands. The missing-`location` cases
already xpass from F2.3.

## Tasks

- [x] **F2.1 Provider baseline** — Generate a `provider.tf` pinned to the v2 range. Record the supported range. (COMPLETED — pin raised to `~> 2.0.14`, the latest 2.x release and the version the gates verify; goldens regenerated, only `provider.tf` changed; README support line updated)
- [x] **F2.2 Resource mapping** — One table maps old emitted names to real v2 resources. (COMPLETED — `resource_mapping.py` is the single source of truth; verified against v2.0.14: 13 identity, 7 renames, 1 merge into `panos_ipsec_tunnel`, 7 report-only; `docs/RESOURCE_MAPPING.md` records the rationale; the earlier "13 missing" count corrected to 15)
- [x] **F2.3 `location` on every resource** — Derive the block from the XML source: `shared`, `device_group`, or `vsys`. (COMPLETED — parser tracks the defining device group; every emitted block carries `location { device_group { ... } }` or `location { template { ... } }` per the v2.0.14 schema; goldens regenerated; conformance test 2 xpasses for all 13 existing types. vsys-scoped location sub-blocks stay with F3.1)
- [ ] **F2.4 Rewrite emitters to v2 schemas** — Use the real nested blocks (`protocol{}`, `layer3{}`, `auto_key{}`, `position{}`). Put proxy-id inside `panos_ipsec_tunnel`. Remove hardcoded assumptions (for example `panos_virtual_router.default`, the hardcoded OSPF area).
- [ ] **F2.5 Order-preserving policy** — Emit rules in XML order per (device group, rulebase). Remove the blanket `position = "bottom"`.
- [ ] **F2.6 Dependency wiring** — Add `depends_on` or `.name` references where the provider supports them.
- [ ] **F2.7 Collision-safe naming** — Build the resource name from the sanitized name plus a short hash of the source path. Handle empty and colliding names. (Foundation exists: `unique_resource_name` registry from F1.7.)
- [ ] **F2.8 Coverage matrix** — Maintain a provider-resource ↔ Panorama-XML-element matrix. Give each supported row a fixture test.
- [ ] **F2.9 Real resources or explicit reports** — Replace comment-only generators (decryption, PBF, app-override, QoS, log-settings) with real v2 resources or an explicit "manual setup" checklist.
- [ ] **F2.10 Clean generated config** — Remove dead variables. Every emitted variable is consumed.
- [ ] **F2.11 Verified claims** — README coverage claims reference F1.4 and F1.5 test evidence. Remove unverified "success rate" claims.

## Notes

- The provider schema JSON (`terraform providers schema -json`) is the single
  source of truth for resource names and attributes.
- F2.8 lands last in Epic 2; it measures the final state.
- F3.1 (keyed data model) refines F2.3 (per-DG instances, vsys sub-blocks)
  and is the dependency for F2.5 (policy order per device group).
