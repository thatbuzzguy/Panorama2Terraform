# To-Do — Epic 2: Complete Support of the Latest Provider (Goal 2)

Goal 2: `terraform validate` passes on all fixture configs. Resource coverage is tracked by test.

Epic 1 is complete; its xfail tests (13 missing v2 types, missing `location`,
validate failures) flip green as this epic lands.

## Tasks

- [ ] **F2.1 Provider baseline** — Generate a `provider.tf` pinned to the v2 range. Record the supported range.
- [ ] **F2.2 Resource mapping** — One table maps old emitted names to real v2 resources: `panos_address`, `panos_service`, `panos_security_policy_rule`, `panos_nat_policy_rule`, `panos_bgp_*_routing_profile`, `panos_ospf_*_routing_profile`, `panos_virtual_router_static_route_ipv4`, `panos_ethernet_layer3_subinterface`.
- [ ] **F2.3 `location` on every resource** — Derive the block from the XML source: `shared`, `device_group`, or `vsys`.
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
- F3.1 (keyed data model) is the agreed dependency for F2.3 and F2.5.
