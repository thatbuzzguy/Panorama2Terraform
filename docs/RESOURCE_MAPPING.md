# Resource Mapping: Emitted Type -> Provider v2 Type

F2.2 deliverable. The machine-readable table lives in
[`resource_mapping.py`](../resource_mapping.py); this document records the
rationale for each decision.

Verified against **provider v2.0.14** (128 resource types) via
`terraform providers schema -json` (the registry's latest 2.x release).
The F1.4 conformance test and the F1.5 validate gate run against this
version.

## Status summary

| Bucket | Count | Types |
|---|---|---|
| Identity (already a real v2 type) | 13 | see table |
| Renamed to a real v2 type | 7 | see table |
| Merged into another v2 resource | 1 | `panos_ipsec_tunnel_proxy_id_ipv4` |
| No v2 equivalent (report only) | 7 | see table |

Of the 28 emitted types, **15 have no matching v2 resource type under the
name the generator emits today** (13 exist, 15 missing). Note: the
adversarial audit report lists 13; it omitted
`panos_application_filter` and `panos_external_list`.

## Mapping table

### Identity — the name is already correct in v2

These resources exist in v2.0.14. They still fail validation today for two
reasons: every v2 resource requires `location` (F2.3 adds it), and several
attribute shapes changed (F2.4 rewrites them).

| Emitted type | v2 type | v2 attribute notes (verified in schema) |
|---|---|---|
| `panos_address_group` | `panos_address_group` | required: `location`, `name` |
| `panos_administrative_tag` | `panos_administrative_tag` | required: `location`, `name` |
| `panos_application_group` | `panos_application_group` | required: `location`, `name` |
| `panos_custom_url_category` | `panos_custom_url_category` | required: `location`, `name` |
| `panos_ethernet_interface` | `panos_ethernet_interface` | `static_ips`/`management_profile` do not exist; v2 nests `layer3 { ipv4 = { ip_address = [...] } }` |
| `panos_ike_crypto_profile` | `panos_ike_crypto_profile` | flat lists become single values: `dh_group`, `hash`, `encryption`, `lifetime {}` |
| `panos_ike_gateway` | `panos_ike_gateway` | flat attributes become `peer_address {}`, `authentication {}`, `protocol {}` |
| `panos_ipsec_crypto_profile` | `panos_ipsec_crypto_profile` | v2 shape per schema |
| `panos_ipsec_tunnel` | `panos_ipsec_tunnel` | `type = "auto-key"` becomes `auto_key { ... }`; `ak_ike_gateway` becomes `auto_key.ike_gateway` |
| `panos_security_profile_group` | `panos_security_profile_group` | required: `location`, `name` |
| `panos_service_group` | `panos_service_group` | required: `location`, `name` |
| `panos_virtual_router` | `panos_virtual_router` | required: `location`, `name` |
| `panos_zone` | `panos_zone` | required: `location`, `name` |

### Renames — the v2 type has a different name

| Emitted type | v2 type | Rationale |
|---|---|---|
| `panos_address_object` | `panos_address` | v2 uses the short name. Attributes: `value`+`type` become `ip_netmask` / `ip_range` / `fqdn` / `ip_wildcard` |
| `panos_service_object` | `panos_service` | v2 uses the short name. Flat `protocol`+`destination_port` becomes `protocol = { tcp = { destination_port = "80" } }` |
| `panos_static_route_ipv4` | `panos_virtual_router_static_route_ipv4` | v2 static routes belong to the virtual router |
| `panos_security_rule_group` | `panos_security_policy_rules` | v2 container: ordered `rules = [...]` list plus a `position { where, pivot, directly }` block. F2.5 order preservation builds on `position` |
| `panos_nat_rule_group` | `panos_nat_policy_rules` | same container pattern as security rules |
| `panos_external_list` | `panos_external_dynamic_list` | v2 name for the dynamic external address list. `url`/`recurring`/`description` have no v2 home and go to the report (F2.9) |
| `panos_layer2_subinterface` | `panos_ethernet_layer3_subinterface` | PAN-OS VLAN subinterfaces (`ethernet1/1.5`) are v2 layer-3 subinterfaces. F2.4 derives `parent`/`tag` from the `.unit` name |

### Merged — the data moves inside another v2 resource

| Emitted type | v2 home | Rationale |
|---|---|---|
| `panos_ipsec_tunnel_proxy_id_ipv4` | `panos_ipsec_tunnel` → `auto_key { proxy_id = [...] }` | v2 has no standalone proxy-id resource. `proxy_id` is a list inside `auto_key` with `name`, `local`, `remote`, `protocol { number/tcp/udp/any }`. F2.4 merges each proxy-id into its tunnel |

### Report only — v2 has no equivalent resource

| Emitted type | Why there is no v2 target |
|---|---|
| `panos_application_filter` | v2 `panos_application` is a single static application object (category, risk, signature, ...). An application filter (category/subcategory/technology/risk *lists*) is a different concept |
| `panos_bgp` | v2 exposes only six specialized BGP routing profiles (timer, auth, dampening, filtering, redistribution, address family). None accepts AS number, router ID, or peer data |
| `panos_bgp_peer` | no v2 peer resource |
| `panos_bgp_peer_group` | no v2 peer-group resource |
| `panos_ospf` | v2 exposes only four specialized OSPF routing profiles (auth, interface timer, SPF timer, redistribution). No router-ID resource |
| `panos_ospf_area` | no v2 area resource |
| `panos_ospf_area_interface` | no v2 area-interface resource |

The report-only types are covered by F2.9 ("real resources or explicit
reports"): the generator keeps the data visible in a migration report so
nothing is silently dropped.

## Verification

`tests/test_resource_mapping.py` asserts, against the live v2.0.14 schema:

1. the mapping keys are exactly the types the generator emits today
   (parsed from the committed goldens);
2. every non-`None` target exists in the provider schema;
3. every `None` entry is genuinely absent from the schema (guards against
   a report-only decision masking a real resource).
