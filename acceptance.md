# Acceptance Criteria: F2.3 Add `location` to every resource

## Background

Provider v2 requires a `location` block on every resource, and the allowed
sub-blocks differ by resource type (verified in the v2.0.14 schema):

- **device_group-scoped** (objects, rules, groups):
  `panos_address`, `panos_service`, `panos_address_group`,
  `panos_service_group`, `panos_administrative_tag`,
  `panos_custom_url_category`, `panos_application_group`,
  `panos_security_profile_group`, `panos_security_policy_rules`,
  `panos_nat_policy_rules`, `panos_external_dynamic_list`.
- **template-scoped** (network/VPN settings): `panos_zone`,
  `panos_virtual_router`, `panos_virtual_router_static_route_ipv4`,
  `panos_ethernet_interface`, `panos_ethernet_layer3_subinterface`,
  `panos_ike_crypto_profile`, `panos_ike_gateway`,
  `panos_ipsec_crypto_profile`, `panos_ipsec_tunnel`. BGP/OSPF (report
  only in v2) are also template-scoped in PAN-OS semantics.

The current parser drops the defining device group (objects are merged
into name-keyed dicts), so the generator cannot name a device group yet.

## Changes

1. **Parser** (`panorama_to_terraform.py`):
   - Build a child->parent map in `PanoramaParser.__init__`
     (ElementTree has no parent pointers).
   - `device_group_of(elem)`: walk up to the enclosing
     `device-group/entry` and return its name; entries under `shared` or
     at the top level return `Shared` (PAN-OS's shared device group name).
   - Record `device_group` in every parsed object dict that feeds a
     device_group-scoped resource: address objects, address groups,
     service objects, service groups, tags, custom URL categories,
     application groups, application filters, external lists, security
     rules, NAT rules, security profile groups.
2. **Generator** (`panorama_to_terraform.py`):
   - `location_block(resource_type, device_group)`: emits the required
     `location { ... }` block. Device_group-scoped types use the object's
     defining DG (default `Shared`); template-scoped types use
     `template { name = "Shared" }` (the default template; F2.4 tracks
     the exact template name).
   - Insert the block as the first attribute of every emitted resource
     block (26 emission points).
3. **Goldens**: regenerate sample + kitchen-sink. Every .tf file with
   resource blocks gains `location` blocks.
4. **Tests**:
   - New green test: every emitted resource block in the goldens carries
     a `location` block.
   - F1.4 conformance test 2 (required attributes) flips to xpass for
     the 13 types that exist in v2.

## Gate

- `uvx --with ruff==0.16.10 ruff check .` clean.
- `uvx --with pytest==9.1.1 pytest` green: previous 106 passed plus new
  tests; no new failures (xfail/xpass split may shift as designed).
- Parser unit tests (42) still pass: `device_group` is an added field,
  not a behavior change.

## Non-goals (later features)

- Exact template-name tracking for network/VPN resources (F2.4).
- Per-device-group resource instances (Epic 3, F3.1).
- vsys-scoped location sub-blocks (Epic 3, F3.1 keyed model).
- Making `terraform validate` fully pass (F2.4/F2.10; the 15 missing
  types and changed attribute shapes still fail).
