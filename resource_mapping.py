"""Resource mapping (Epic 2).

Single source of truth for what the converter produces against the
panos provider v2:

    EMITTED_TYPES      - the provider v2 resource types the generator emits.
    REPORT_ONLY_TYPES  - PAN-OS config types with no v2 resource; the
                         captured data goes to MANUAL_SETUP_REPORT.txt
                         (and the VPN/interface migration reports) instead.
    NOT_EMITTED_TYPES  - v2 resource types that exist but the converter
                         intentionally does not emit (the configuration
                         body is not parsed); the captured data goes to
                         MANUAL_SETUP_REPORT.txt with the reason (F2.9).
    COVERAGE_MATRIX    - one row per emitted type: the Panorama XML
                         element that feeds the resource, the fixture
                         that exercises it, and the expected emitted
                         name. Enforced by tests/test_coverage_matrix.py.

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
    # Policy containers (one resource per rule; per-device-group chains in
    # XML order, F2.5)
    'panos_security_policy_rules',
    'panos_nat_policy_rules',
    # F2.9: decryption and PBF rules emit as real v2 resources, one resource
    # per rule, chained per device group (F2.5 position semantics)
    'panos_decryption_policy_rules',
    'panos_pbf_policy_rules',
    # Profiles (device-group scoped)
    'panos_security_profile_group',
    # Network (template scoped)
    # F2.9: PBF path monitoring profiles (network/profiles/monitor-profile);
    # template-scoped in v2. NOT the IPsec tunnel monitor profile.
    'panos_monitor_profile',
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
    # F2.9: no v2 resource for application override rules or QoS profiles;
    # the captured rule/profile data goes to MANUAL_SETUP_REPORT.txt.
    'panos_application_override',
    'panos_qos_profile',
    # F2.9: no v2 resource for IPsec tunnel monitor profiles
    # (network/tunnel-monitor/monitor-profile). panos_monitor_profile is a
    # different PAN-OS object (PBF path monitoring), verified against the
    # provider source (pango: network/profiles/monitor-profile).
    'panos_tunnel_monitor_profile',
})

# v2 resource types that exist but the converter intentionally does not emit
# (F2.9). The parser captures only the name and description of these objects;
# the bodies that make them functional (match lists, SIP/UDP/TCP/ICMP/DNS
# options) are not parsed. Emitting an empty profile would silently create a
# misconfigured object, so the data goes to MANUAL_SETUP_REPORT.txt with the
# reason instead. Each entry MUST exist in the v2 schema (guarded by
# tests/test_resource_mapping.py) - the inverse of the report-only absence
# test.
NOT_EMITTED_TYPES = {
    'panos_log_forwarding_profile': (
        'only name/description are parsed; the match_list body is not '
        'captured, and an empty profile would be a misconfigured object'
    ),
    'panos_zone_protection_profile': (
        'only name/description are parsed; the SIP/UDP/TCP/ICMP/DNS options '
        'body is not captured; real emission needs profile parsing (Epic 3)'
    ),
    'panos_schedule': (
        'only the entry names are parsed; the day/time ranges are not '
        'captured, and v2.0.14 has no monthly schedule support'
    ),
}

# Coverage matrix (F2.8): provider resource <-> Panorama XML element.
#
# One row per EMITTED_TYPES type. Fields:
#   resource     - the provider v2 resource type the generator emits.
#   xml_element  - the tag path of the Panorama XML element whose <entry>
#                  feeds the resource (scope prefixes such as shared/,
#                  device-group/entry/, vsys/entry/, templates/entry/ vary
#                  per export and are not part of the element identity).
#   xml_name     - the <entry name=...> in the fixture that feeds it.
#   emitted_name - the `name` attribute the emitted resource must carry.
#                  Derived names (for example the .0 subinterface) differ
#                  from xml_name on purpose.
#   fixture      - the XML fixture under tests/fixtures/ for the row test.
#   output_file  - the .tf file (relative to the output directory) that
#                  must contain the resource block.
#
# Maintenance duty: an emitter change that adds, renames, or drops a
# resource type must update this matrix in the same change.
# tests/test_coverage_matrix.py fails when the matrix and the converter
# disagree (row set, fixture content, or emitted output).
COVERAGE_MATRIX = (
    {
        'resource': 'panos_address',
        'xml_element': 'address/entry',
        'xml_name': 'Web-Server-1',
        'emitted_name': 'Web-Server-1',
        'fixture': 'address_objects.xml',
        'output_file': 'address_objects.tf',
    }, {
        'resource': 'panos_address_group',
        'xml_element': 'address-group/entry',
        'xml_name': 'Web-Servers',
        'emitted_name': 'Web-Servers',
        'fixture': 'address_groups.xml',
        'output_file': 'address_groups.tf',
    }, {
        'resource': 'panos_administrative_tag',
        'xml_element': 'tag/entry',
        'xml_name': 'env-prod',
        'emitted_name': 'env-prod',
        'fixture': 'tags.xml',
        'output_file': 'tags.tf',
    }, {
        'resource': 'panos_application_group',
        'xml_element': 'application-group/entry',
        'xml_name': 'web-apps',
        'emitted_name': 'web-apps',
        'fixture': 'application_groups.xml',
        'output_file': 'application_groups.tf',
    }, {
        'resource': 'panos_custom_url_category',
        'xml_element': 'custom-url-category/entry',
        'xml_name': 'blocked-sites',
        'emitted_name': 'blocked-sites',
        'fixture': 'custom_url_categories.xml',
        'output_file': 'custom_url_categories.tf',
    }, {
        'resource': 'panos_external_dynamic_list',
        'xml_element': 'external-list/entry',
        'xml_name': 'threat-ips',
        'emitted_name': 'threat-ips',
        'fixture': 'external_lists.xml',
        'output_file': 'external_lists.tf',
    }, {
        'resource': 'panos_service',
        'xml_element': 'service/entry',
        'xml_name': 'TCP-8080',
        'emitted_name': 'TCP-8080',
        'fixture': 'service_objects.xml',
        'output_file': 'service_objects.tf',
    }, {
        'resource': 'panos_service_group',
        'xml_element': 'service-group/entry',
        'xml_name': 'Web-Services',
        'emitted_name': 'Web-Services',
        'fixture': 'service_groups.xml',
        'output_file': 'service_groups.tf',
    }, {
        'resource': 'panos_security_policy_rules',
        'xml_element': 'security/rules/entry',
        'xml_name': 'Allow-Web-Traffic',
        'emitted_name': 'Allow-Web-Traffic',
        'fixture': 'security_rules.xml',
        'output_file': 'security_rules.tf',
    }, {
        'resource': 'panos_nat_policy_rules',
        'xml_element': 'nat/rules/entry',
        'xml_name': 'Outbound-NAT',
        'emitted_name': 'Outbound-NAT',
        'fixture': 'nat_rules.xml',
        'output_file': 'nat_rules.tf',
    }, {
        # F2.9: decryption rules emit as real v2 resources (one per rule)
        'resource': 'panos_decryption_policy_rules',
        'xml_element': 'decryption/rules/entry',
        'xml_name': 'Decrypt-HTTPS',
        'emitted_name': 'Decrypt-HTTPS',
        'fixture': 'decryption_rules.xml',
        'output_file': 'decryption_rules.tf',
    }, {
        # F2.9: PBF rules emit as real v2 resources (one per rule)
        'resource': 'panos_pbf_policy_rules',
        'xml_element': 'pbf/rules/entry',
        'xml_name': 'PBF-Forward',
        'emitted_name': 'PBF-Forward',
        'fixture': 'pbf_rules.xml',
        'output_file': 'pbf_rules.tf',
    }, {
        'resource': 'panos_security_profile_group',
        'xml_element': 'profile-group/entry',
        'xml_name': 'Strict-Profile',
        'emitted_name': 'Strict-Profile',
        'fixture': 'security_profile_groups.xml',
        'output_file': 'security_profile_groups.tf',
    }, {
        # F2.9: PBF path monitoring profiles are template-scoped in v2;
        # a different PAN-OS object from the IPsec tunnel monitor profile
        'resource': 'panos_monitor_profile',
        'xml_element': 'profiles/monitor-profile/entry',
        'xml_name': 'PM-Branch',
        'emitted_name': 'PM-Branch',
        'fixture': 'pbf_monitor_profiles.xml',
        'output_file': 'monitor_profiles.tf',
    }, {
        'resource': 'panos_ethernet_interface',
        'xml_element': 'ethernet/entry',
        'xml_name': 'ethernet1/1',
        'emitted_name': 'ethernet1/1',
        'fixture': 'interfaces_ethernet.xml',
        'output_file': 'interfaces.tf',
    }, {
        'resource': 'panos_ethernet_layer3_subinterface',
    # The physical L3 interface feeds its derived .0 subinterface:
    # the entry name is ethernet1/1, the subinterface is ethernet1/1.0.
        'xml_element': 'ethernet/entry',
        'xml_name': 'ethernet1/1',
        'emitted_name': 'ethernet1/1.0',
        'fixture': 'interfaces_ethernet.xml',
        'output_file': 'interfaces.tf',
    }, {
        'resource': 'panos_virtual_router',
        'xml_element': 'virtual-router/entry',
        'xml_name': 'default',
        'emitted_name': 'default',
        'fixture': 'virtual_routers.xml',
        'output_file': 'virtual_routers.tf',
    }, {
        'resource': 'panos_virtual_router_static_route_ipv4',
        'xml_element': 'static-route/entry',
        'xml_name': 'default-gw',
        'emitted_name': 'default-gw',
        'fixture': 'virtual_routers.xml',
        'output_file': 'virtual_routers.tf',
    }, {
        'resource': 'panos_zone',
        'xml_element': 'zone/entry',
        'xml_name': 'trust',
        'emitted_name': 'trust',
        'fixture': 'zones.xml',
        'output_file': 'zones.tf',
    }, {
        'resource': 'panos_ike_crypto_profile',
        'xml_element': 'crypto-profiles/ike-crypto-profiles/entry',
        'xml_name': 'IKE-DEFAULT',
        'emitted_name': 'IKE-DEFAULT',
        'fixture': 'ike_crypto_profiles.xml',
        'output_file': 'vpn.tf',
    }, {
        'resource': 'panos_ike_gateway',
        'xml_element': 'ike/gateway/entry',
        'xml_name': 'IKE-GW-Branch',
        'emitted_name': 'IKE-GW-Branch',
        'fixture': 'ike_gateways.xml',
        'output_file': 'vpn.tf',
    }, {
        'resource': 'panos_ipsec_crypto_profile',
        'xml_element': 'crypto-profiles/ipsec-crypto-profiles/entry',
        'xml_name': 'IPSEC-DEFAULT',
        'emitted_name': 'IPSEC-DEFAULT',
        'fixture': 'ipsec_crypto_profiles.xml',
        'output_file': 'vpn.tf',
    }, {
        'resource': 'panos_ipsec_tunnel',
        'xml_element': 'tunnel/ipsec/entry',
        'xml_name': 'TUN-Branch',
        'emitted_name': 'TUN-Branch',
        'fixture': 'ipsec_tunnels.xml',
        'output_file': 'vpn.tf',
    }
)

