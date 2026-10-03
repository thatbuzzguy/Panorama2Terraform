"""Resource mapping: emitted panos resource type -> real provider v2 type (F2.2).

This is the single source of truth for the Epic 2 rewrite. The generator
(F2.4) emits the target column; tests (tests/test_resource_mapping.py)
verify the table against the live provider schema.

Verified against provider v2.0.14 (128 resource types) with
`terraform providers schema -json`. The registry's latest 2.x release.

Value semantics:
    str  -> the v2 resource type to emit (a rename when it differs).
    None -> v2 has no equivalent resource; the data goes to the
            migration report instead (F2.9 "real resources or explicit reports").

The 13 types that already exist in v2 map to themselves. They still need
the required `location` attribute (F2.3) and v2 attribute shapes (F2.4).
"""

from typing import Optional

# Old emitted type -> v2 resource type (or None when v2 has no equivalent).
RESOURCE_MAPPING: dict[str, Optional[str]] = {
    # --- already exist in v2 (identity; F2.3/F2.4 fix attributes) ---
    'panos_address_group': 'panos_address_group',
    'panos_administrative_tag': 'panos_administrative_tag',
    'panos_application_group': 'panos_application_group',
    'panos_custom_url_category': 'panos_custom_url_category',
    'panos_ethernet_interface': 'panos_ethernet_interface',
    'panos_ike_crypto_profile': 'panos_ike_crypto_profile',
    'panos_ike_gateway': 'panos_ike_gateway',
    'panos_ipsec_crypto_profile': 'panos_ipsec_crypto_profile',
    'panos_ipsec_tunnel': 'panos_ipsec_tunnel',
    'panos_security_profile_group': 'panos_security_profile_group',
    'panos_service_group': 'panos_service_group',
    'panos_virtual_router': 'panos_virtual_router',
    'panos_zone': 'panos_zone',
    # --- renames to real v2 types ---
    # v2 uses the short names for single objects.
    'panos_address_object': 'panos_address',
    'panos_service_object': 'panos_service',
    # v2 static routes belong to the virtual router.
    'panos_static_route_ipv4': 'panos_virtual_router_static_route_ipv4',
    # v2 policy containers: one resource per location holding an ordered
    # `rules` list plus a `position` block (F2.5 order preservation).
    'panos_security_rule_group': 'panos_security_policy_rules',
    'panos_nat_rule_group': 'panos_nat_policy_rules',
    # v2 name for the dynamic list of external addresses. url/recurring/
    # description have no v2 home; F2.9 reports them.
    'panos_external_list': 'panos_external_dynamic_list',
    # PAN-OS VLAN subinterfaces (e.g. ethernet1/1.5) are exposed in v2 as
    # layer-3 subinterfaces; F2.4 derives parent/tag from the .unit name.
    'panos_layer2_subinterface': 'panos_ethernet_layer3_subinterface',
    # --- merged into another v2 resource ---
    # v2 has no standalone proxy-id resource. proxy-ids are a list inside
    # panos_ipsec_tunnel: auto_key { proxy_id = [...] }. F2.4 merges them.
    'panos_ipsec_tunnel_proxy_id_ipv4': 'panos_ipsec_tunnel',
    # --- no v2 equivalent: report only (F2.9) ---
    # v2 panos_application is a single static application object; an
    # application filter (category/subcategory/technology/risk lists) is a
    # different concept and has no v2 resource.
    'panos_application_filter': None,
    # v2 exposes only six specialized BGP routing profiles (timer, auth,
    # dampening, filtering, redistribution, address family). None of them
    # accepts AS number, router ID, or peer data, so the captured BGP data
    # has nowhere to go.
    'panos_bgp': None,
    'panos_bgp_peer': None,
    'panos_bgp_peer_group': None,
    # Same shape as BGP: v2 has only auth/interface-timer/SPF-timer/
    # redistribution profiles for OSPF. No area or router-ID resource.
    'panos_ospf': None,
    'panos_ospf_area': None,
    'panos_ospf_area_interface': None,
}

# Types that map to themselves (already real v2 resource types).
IDENTITY_TYPES = frozenset(k for k, v in RESOURCE_MAPPING.items() if v == k)

# Types with no v2 equivalent (their data goes to the migration report).
REPORT_ONLY_TYPES = frozenset(k for k, v in RESOURCE_MAPPING.items() if v is None)

# Types renamed or merged into another v2 resource.
MAPPED_TYPES = frozenset(RESOURCE_MAPPING) - IDENTITY_TYPES - REPORT_ONLY_TYPES
