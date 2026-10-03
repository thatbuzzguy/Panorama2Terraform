"""Resource mapping (Epic 2).

Single source of truth for what the converter produces against the
panos provider v2:

    EMITTED_TYPES     - the provider v2 resource types the generator emits.
    REPORT_ONLY_TYPES - PAN-OS config types with no v2 resource; the
                        captured data goes to MANUAL_SETUP_REPORT.txt
                        (and the VPN/interface migration reports) instead.

The generator emits the v2 types directly; the old v1 names
(panos_address_object, panos_security_rule_group, ...) no longer exist
anywhere in the code base. The v1 -> v2 rename rationale is preserved in
docs/RESOURCE_MAPPING.md.

Verified against provider v2.0.14 (128 resource types) with
`terraform providers schema -json`.
"""

# Provider v2 resource types emitted by the generator.
EMITTED_TYPES = frozenset({
    # Objects (device-group scoped)
    'panos_address',
    'panos_address_group',
    'panos_administrative_tag',
    'panos_application_group',
    'panos_custom_url_category',
    'panos_external_dynamic_list',
    'panos_service',
    'panos_service_group',
    # Policy containers (one resource per device group; ordered rules list)
    'panos_security_policy_rules',
    'panos_nat_policy_rules',
    # Profiles (device-group scoped)
    'panos_security_profile_group',
    # Network (template scoped)
    'panos_ethernet_interface',
    'panos_ethernet_layer3_subinterface',
    'panos_virtual_router',
    'panos_virtual_router_static_route_ipv4',
    'panos_zone',
    # VPN (template scoped)
    'panos_ike_crypto_profile',
    'panos_ike_gateway',
    'panos_ipsec_crypto_profile',
    'panos_ipsec_tunnel',
})

# PAN-OS config types with no v2 provider resource. The converter keeps
# the data visible in the manual setup report instead of emitting it.
REPORT_ONLY_TYPES = frozenset({
    # v2 panos_application is a single static application object; an
    # application filter (category/subcategory/technology/risk lists) is
    # a different concept with no v2 resource.
    'panos_application_filter',
    # v2 exposes only six specialized BGP routing profiles (timer, auth,
    # dampening, filtering, redistribution, address family). None accepts
    # AS number, router ID, or peer data, so the captured BGP data has
    # nowhere to go.
    'panos_bgp',
    'panos_bgp_peer',
    'panos_bgp_peer_group',
    # Same shape as BGP: v2 has only auth/interface-timer/SPF-timer/
    # redistribution profiles for OSPF. No area or router-ID resource.
    'panos_ospf',
    'panos_ospf_area',
    'panos_ospf_area_interface',
})
