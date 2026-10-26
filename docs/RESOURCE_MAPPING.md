# Resource Mapping: Converter Output -> Provider v2 Types

The machine-readable table lives in
[`resource_mapping.py`](../resource_mapping.py). This document records the
rationale for each decision. The companion coverage matrix — which
Panorama XML element feeds each emitted type, and the fixture that
proves it — is in [`COVERAGE_MATRIX.md`](./COVERAGE_MATRIX.md). The document
index is in [README.md](README.md).

Verified against **provider v2.0.14** (128 resource types) via
`terraform providers schema -json` (the registry's latest 2.x release).
The conformance test and the `terraform validate` gate run against this
version.

## Status summary

| Bucket | Count |
|---|---|
| Emitted as real v2 resources (`EMITTED_TYPES`) | 28 |
| No v2 equivalent, report only (`REPORT_ONLY_TYPES`) | 10 |
| v2 resource exists, intentionally not emitted (`NOT_EMITTED_TYPES`) | 3 |

The old v1 names (`panos_address_object`, `panos_security_rule_group`,
...) no longer exist in the code base. The v1 -> v2 rename rationale is
preserved in the "Renamed from" column of the emitted-type table below.

## Emitted types

Every v2 resource requires `location` and `name`. The notes below list
the v2 attribute shapes that differ from the v1 output.

### Objects (device-group scoped)

| v2 type | Renamed from | v2 attribute notes (verified in schema) |
|---|---|---|
| `panos_address` | `panos_address_object` | `value`+`type` become one attribute per type: `ip_netmask` / `ip_range` / `fqdn` / `ip_wildcard` |
| `panos_address_group` | identity | `static` is a list; dynamic groups use `dynamic = { dynamic = { filter = "..." } }` |
| `panos_administrative_tag` | identity | colors are numeric: `color1`..`colorN` (PAN-OS color words map in GUI order: red, orange, yellow, green, blue, purple, gray) |
| `panos_application_group` | identity | `static` member list |
| `panos_custom_url_category` | identity | `static` member list |
| `panos_external_dynamic_list` | `panos_external_list` | `type = { <type> = { url, exception_list, certificate_profile, recurring = { <freq> = { ... } }, description } }`; `expand_domain` exists on the `domain` sub-shape only, and the `predefined_*` sub-shapes take `url`/`exception_list`/`description` only |
| `panos_service` | `panos_service_object` | flat `protocol`+`destination_port` becomes `protocol = { tcp = { destination_port, source_port, override = { ... } } }`; the provider accepts **one** protocol leg, so a tcp+udp object emits tcp and reports udp |
| `panos_service_group` | identity | `static` member list |

### Policy rules (one resource per rule, chained per device group)

| v2 type | Renamed from | v2 attribute notes |
|---|---|---|
| `panos_security_policy_rules` | `panos_security_rule_group` | `position { where, pivot, directly }` places one rule per resource; chains preserve XML order |
| `panos_nat_policy_rules` | `panos_nat_rule_group` | same per-rule chain model; `nat_type` is the protocol family (`ipv4`/`nat64`/`nptv6`), not the translation direction |
| `panos_decryption_policy_rules` | identity (no v1 equivalent) | same per-rule chain model. The `action` is an enum (`no-decrypt`/`decrypt`/`decrypt-and-forward`); the inspection mode is a separate `type { <key> = {} }` block. Legacy PAN-OS 9 exports put the mode in the `action` field; the converter maps that to `action = "decrypt"` plus the matching `type` block |
| `panos_pbf_policy_rules` | identity (no v1 equivalent) | same per-rule chain model. Single-choice action: `forward` (with optional `monitor { ip_address, profile, disable_if_unreachable }`), `forward_to_vsys`, `discard`, `no_pbf` |

The rulebase is part of the `location.device_group` and `location.shared`
sub-blocks in the schema, but the converter does not emit it: the parser does
not record which rulebase an entry came from. See
[`../backlog.md`](../backlog.md).

### Profiles (device-group scoped)

| v2 type | Renamed from | v2 attribute notes |
|---|---|---|
| `panos_security_profile_group` | identity | profile members are name lists (`virus`, `spyware`, `vulnerability`, ...). This is the emitted type with no `vsys` sub-block in `LOCATION_SCHEMA` |

### Network (template scoped)

| v2 type | Renamed from | v2 attribute notes |
|---|---|---|
| `panos_ethernet_interface` | identity | `layer3` / `layer2` are mode blocks (`layer3 { interface_management_profile, ... }`); no `static_ips`/`management_profile`. The untagged interface's IPv4 address goes on the `.0` subinterface's `ip` list. Virtual-wire and TAP are blocks inside this resource, not resource types |
| `panos_ethernet_layer3_subinterface` | `panos_layer2_subinterface` | PAN-OS VLAN subinterfaces (`ethernet1/1.5`) are v2 layer-3 subinterfaces; `parent`/`tag` derive from the `.unit` name |
| `panos_aggregate_interface` | identity | physical aggregate (LAG) |
| `panos_aggregate_layer3_subinterface` | identity | layer-3 subinterface of an aggregate |
| `panos_vlan_interface` | identity | `layer3` block; the entry name is the VLAN id, and the emitted name is `vlan.<id>` |
| `panos_loopback_interface` | identity | emitted name is `loopback.<unit>` |
| `panos_tunnel_interface` | identity | emitted name is `tunnel.<unit>`. These are the interface layers, not the IPsec tunnel resource |
| `panos_virtual_router` | identity | required: `location`, `name`. Logical routers (Advanced Routing Engine) emit as this type; see [ADVANCED-ROUTING-ENGINE-SUPPORT.md](ADVANCED-ROUTING-ENGINE-SUPPORT.md) |
| `panos_virtual_router_static_route_ipv4` | `panos_static_route_ipv4` | static routes belong to the virtual router; `nexthop = { ip_address = "..." }`. A next-VR route has no v2 attribute, so it is configured on the target |
| `panos_zone` | identity | `network = { layer3 = [...] }` |
| `panos_monitor_profile` | identity (no v1 equivalent) | PBF path monitoring profiles (`network/profiles/monitor-profile`), referenced by PBF rule path monitoring. `action` is an enum (`wait-recover`/`fail-over`); no `description` attribute |

`INTERFACE_RESOURCE_TYPES` in `resource_mapping.py` maps each parsed
interface kind to the type above. Virtual-wire and TAP write lines inside a
parent resource block, so they have no resource type of their own.

### VPN (template scoped)

| v2 type | Renamed from | v2 attribute notes |
|---|---|---|
| `panos_ike_crypto_profile` | identity | attribute names differ from the v1 output: `encryption`, `hash`, `dh_group` stay lists; `lifetime` becomes the nested block `lifetime { hours }` |
| `panos_ike_gateway` | identity | flat attributes become `peer_address {}`, `local_address {}`, `authentication {}`, `protocol {}` |
| `panos_ipsec_crypto_profile` | identity | `esp` is a nested block holding the `encryption` and `authentication` lists; `dh_group` is one string; `lifetime { hours }` and `lifesize { kb }` are nested blocks |
| `panos_ipsec_tunnel` | identity + `panos_ipsec_tunnel_proxy_id_ipv4` | `type = "auto-key"` becomes `auto_key { ike_gateway = [...], proxy_id = [...] }`; v2 has no standalone proxy-id resource, so each proxy-id merges into its tunnel |

## Report-only types (no v2 resource)

The captured data goes to `MANUAL_SETUP_REPORT.txt` (or the VPN/interface
migration reports) so nothing is silently dropped.

| Type | Why there is no v2 target |
|---|---|
| `panos_application_filter` | v2 `panos_application` is a single static application object (category, risk, signature, ...). An application filter (category/subcategory/technology/risk *lists*) is a different concept |
| `panos_bgp` | v2 exposes only six specialized BGP routing profiles (timer, auth, dampening, filtering, redistribution, address family). None accepts AS number, router ID, or peer data |
| `panos_bgp_peer` | no v2 peer resource |
| `panos_bgp_peer_group` | no v2 peer-group resource |
| `panos_ospf` | v2 exposes only four specialized OSPF routing profiles (auth, interface timer, SPF timer, redistribution). No router-ID resource |
| `panos_ospf_area` | no v2 area resource |
| `panos_ospf_area_interface` | no v2 area-interface resource |
| `panos_application_override` | no v2 resource for application override rules |
| `panos_qos_profile` | no v2 resource for QoS profiles |
| `panos_tunnel_monitor_profile` | no v2 resource for IPsec tunnel monitor profiles. `panos_monitor_profile` is a different PAN-OS object (PBF path monitoring) — verified in the provider/pango source |

BGP redistribution rules are captured by the parser but the report prints
only the router, peer groups and peers. That gap is recorded in
[`../backlog.md`](../backlog.md).

## Types that exist in v2 but are not emitted

The parser captures only the name and description for these objects. An
empty profile resource would be a misconfigured object, so the captured data
stays in `MANUAL_SETUP_REPORT.txt` with the reason:

| Type | Reason |
|---|---|
| `panos_log_forwarding_profile` | the `match_list` body is not captured |
| `panos_zone_protection_profile` | the SIP/UDP/TCP/ICMP/DNS options body is not captured |
| `panos_schedule` | only the entry names are parsed; v2.0.14 has no monthly schedule support |

Security profile bodies (antivirus, anti-spyware, vulnerability, URL
filtering, file blocking, WildFire, zone protection) follow the same
policy: the parser captures only name and description, and the v2
resources (for example `panos_antivirus_security_profile`) require the
detailed configuration that is not captured.

## Other limits the converter states in the report

- An address entry whose type has no `panos_address` attribute (country,
  region, continent, container, external) is reported. Every other address
  type emits, including `ip-wildcard` and IPv6.
- A service that defines both tcp and udp emits the tcp leg (the udp leg when
  tcp is absent). The provider accepts one leg, and a config with both fails
  `terraform validate` with "Invalid Attribute Combination" (verified against
  2.0.14). The dropped leg is listed with its ports.
- An EDL that authenticates to its fetch URL needs credentials. The converter
  never writes credential material into generated HCL.
- A declared scope the resource type cannot carry is reported, never dropped
  silently. The rule is in [ARCHITECTURE.md](ARCHITECTURE.md) §4.2.

## Verification

`tests/test_resource_mapping.py` asserts, against the live v2.0.14
schema:

1. the emitted-type set is exactly the types the committed goldens emit;
2. every emitted type exists in the provider schema;
3. every report-only type is genuinely absent from the schema (guards
   against a report-only decision masking a real resource);
4. every not-emitted type genuinely exists in the schema (the inverse
   guard, so a future rename cannot silently move a type between buckets).

`tests/test_coverage_matrix.py` keeps `COVERAGE_MATRIX` in step with the
emitters, and `tests/test_container_coverage.py` keeps the container table in
step with the parse methods.
