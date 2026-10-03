# Acceptance Criteria — F2.4: Rewrite emitters to the v2 schemas

## Scope
Apply `resource_mapping.py` to the generator and rewrite every emitter to
the v2.0.14 attribute shapes (verified from `terraform providers schema`).
Move the seven report-only types (BGP, OSPF x3, application filter) out of
the .tf output into a manual-setup report so `terraform validate` can pass.

## Type renames (from RESOURCE_MAPPING)
- `panos_address_object` → `panos_address`
- `panos_service_object` → `panos_service`
- `panos_security_rule_group` → `panos_security_policy_rules`
- `panos_nat_rule_group` → `panos_nat_policy_rules`
- `panos_external_list` → `panos_external_dynamic_list`
- `panos_static_route_ipv4` → `panos_virtual_router_static_route_ipv4`
- `panos_layer2_subinterface` → `panos_ethernet_layer3_subinterface`
- `panos_ipsec_tunnel_proxy_id_ipv4` → merged into `panos_ipsec_tunnel.auto_key.proxy_id`
- No legacy type name appears in any generated .tf file.

## Attribute shapes (v2.0.14)
- `panos_address`: `ip_netmask` | `ip_range` | `fqdn` | `ip_wildcard` (from parser `type`/`value`), `description`, `tags`.
- `panos_service`: `protocol { tcp|udp { destination_port = "..." } }`, `description`, `tags`.
- `panos_address_group`: `static = [...]`, `description`.
- `panos_service_group`: `members = [...]` (v2 has no description; drop it).
- `panos_administrative_tag`: `color`, `comments` (from parser `description`).
- `panos_custom_url_category`: `type`, `list = [...]`, `description`.
- `panos_application_group`: `members = [...]`.
- `panos_security_profile_group`: non-empty profile lists (`virus`, `spyware`, ...).
- `panos_security_policy_rules`: `position { where = "bottom" }` (F2.5 refines order) + `rules { ... }` with v2 names (`source_zones`, `applications`, `services`, `action`, `log_start`, `log_end`, ...).
- `panos_nat_policy_rules`: `position { where = "bottom" }` + `rules { ... }` with `nat_type` and `source_translation { dynamic_ip_and_port | dynamic_ip | static_ip { ... } }`.
- `panos_external_dynamic_list`: `type { ip|domain|url|... { url = "...", recurring { hourly|... {} } } }`.
- `panos_zone`: `network { layer3 = [...] | layer2 = [...], zone_protection_profile = "..." }`.
- `panos_virtual_router`: `interfaces = [...]` (flat list, v2 shape).
- `panos_virtual_router_static_route_ipv4`: `destination`, `nexthop { ip_address }` or `interface`, `virtual_router = "<actual VR name>"` (no `panos_virtual_router.default`), `metric`.
- `panos_ethernet_interface`: `comment`, `layer3 { interface_management_profile = "..." }` where applicable. v2 has no ipv4 attribute: IPv4 addresses emit as a `panos_ethernet_layer3_subinterface` with `parent`, `tag = 0`, `ip { name = "addr/prefix" }`.
- `panos_ethernet_layer3_subinterface`: `parent`, `tag` (number), `ip { name = "addr/prefix" }`.
- `panos_ike_crypto_profile`: `encryption = [...]`, `hash = [...]`, `dh_group = [...]`, `lifetime { hours = N }`.
- `panos_ipsec_crypto_profile`: `dh_group = "..."`, `esp { encryption = [...], authentication = [...] }`, `lifetime { ... }`, `lifesize { ... }`.
- `panos_ike_gateway`: `protocol { version = "ikev2|ikev1", ikev2 { ike_crypto_profile = "..." } }`, `peer_address { fqdn = "..." | ip = "..." }`, `authentication { pre_shared_key { key = "..." } }`, `local_id`, `peer_id`.
- `panos_ipsec_tunnel`: `tunnel_interface`, `auto_key { ike_gateway, ipsec_crypto_profile, proxy_id { name, local, remote, protocol } }`. No separate proxy-id resource. Manual-key tunnels go to the manual-setup report.

## Report-only types
- `panos_bgp*`, `panos_ospf*`, `panos_application_filter` are NOT emitted as .tf resources.
- Their parsed data goes to `MANUAL_SETUP_REPORT.txt` (name + key fields + "configure manually" note). No parsed data is silently dropped.

## Tests
- `test_resource_mapping.py` restructured: mapping keys are the frozen legacy set; mapping targets exist in the schema; report-only entries are absent from the schema; generated goldens contain only mapped v2 types.
- `test_schema_conformance.py`: both parameterized tests now pass for all emitted types → xfail markers removed.
- `test_terraform_validate.py`: `terraform validate` passes on both generated corpora → xfail removed.
- `test_robustness.py` collision tests updated to the new type names.
- Goldens regenerated (sample + kitchen sink).

## Gate
- ruff clean; full pytest suite green with no conformance/validate xfails remaining (remaining xfails: Epic 3 per-DG dedup cases only).
- `terraform validate` passes locally on both corpora.
- README coverage section updated to the v2 type names.
- Committed with a detailed ASD-STE100 message.
