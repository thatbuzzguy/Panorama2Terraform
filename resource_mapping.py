"""Resource mapping.

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
                         that exercises it, the expected emitted name, the
                         emitter method, and the properties that emitter
                         reads. Enforced by tests/test_coverage_matrix.py
                         and tests/test_property_coverage.py.
    DATA_SOURCE_SCHEMA - one row per provider data source type: whether it
                         declares `name`, and the `location` sub-blocks it
                         declares with their fields. Enforced by
                         tests/test_data_source_schema.py against the live
                         schema, and read by the gate rule for a `data`
                         block (tests/test_data_blocks.py).

The generator emits the v2 types directly; the old v1 names
(panos_address_object, panos_security_rule_group, ...) no longer exist
anywhere in the code base. The v1 -> v2 rename rationale is preserved in
docs/RESOURCE_MAPPING.md.

Verified against provider v2.0.14 (128 resource types) with
`terraform providers schema -json`.
"""

# F3.3: parsed interface kind -> provider resource type. The generator uses
# this table to pick the resource type for each interface entry.
INTERFACE_RESOURCE_TYPES = {
    'ethernet': 'panos_ethernet_interface',
    'ethernet-subinterface': 'panos_ethernet_layer3_subinterface',
    'vlan': 'panos_vlan_interface',
    'loopback': 'panos_loopback_interface',
    'tunnel': 'panos_tunnel_interface',
    'aggregate': 'panos_aggregate_interface',
    'aggregate-subinterface': 'panos_aggregate_layer3_subinterface',
}

# F3.5: the `location` sub-blocks the v2.0.14 schema declares for each
# emitted type, with the fields of every sub-block. The generator picks the
# sub-block from this table; it never emits a sub-block or a field the table
# omits.
#
# Per type the table lists only the sub-blocks the converter can use
# (device_group, shared, vsys, template). The schema declares more for some
# types — `ngfw`, `template_stack`, `template_stack_vsys`, `template_vsys`
# — for direct-firewall and template-stack placement; the converter targets
# Panorama device groups and templates, so it never uses them and the table
# is a deliberate subset. tests/test_multi_vsys_location.py checks every
# listed sub-block and field against the live provider schema. That check
# matters because `terraform validate` accepts an unknown `location`
# sub-block and drops it silently, so a wrong sub-block fails at apply,
# not at validate.
#
# Verified against provider v2.0.14 with `terraform providers schema -json`.
LOCATION_SCHEMA = {
    'panos_address': {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    },
    'panos_address_group': {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    },
    'panos_administrative_tag': {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    },
    'panos_aggregate_interface': {
        'ngfw': ('ngfw_device',),
        'shared': (),
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
    },
    'panos_aggregate_layer3_subinterface': {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
    },
    'panos_application_group': {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    },
    'panos_custom_url_category': {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    },
    'panos_decryption_policy_rules': {
        'device_group': ('name', 'panorama_device', 'rulebase'),
        'shared': ('rulebase',),
        'vsys': ('name', 'ngfw_device'),
    },
    # F6.5: the six scope objects, one row each. A scope block places itself inside the scope
    # the export names, so the four Panorama scopes take `panorama` and the two that sit inside
    # a template take `template` or `template_stack`. The generator writes no `panorama_device`
    # field, because the codebase states no device fact for a scope (backlog.md), but the row
    # states the verified shape so it stays equal to `DATA_SOURCE_SCHEMA`.
    'panos_device_group': {
        'panorama': ('panorama_device',),
    },
    'panos_device_group_parent': {
        'panorama': ('panorama_device',),
    },
    'panos_ethernet_interface': {
        'ngfw': ('ngfw_device',),
        'shared': (),
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
    },
    'panos_ethernet_layer3_subinterface': {
        'ngfw': ('ngfw_device',),
        'shared': (),
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
    },
    'panos_external_dynamic_list': {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    },
    'panos_ike_crypto_profile': {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
    },
    'panos_ike_gateway': {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
    },
    'panos_ipsec_crypto_profile': {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
    },
    'panos_ipsec_tunnel': {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
    },
    'panos_loopback_interface': {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
    },
    'panos_monitor_profile': {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
    },
    'panos_nat_policy_rules': {
        'device_group': ('name', 'panorama_device', 'rulebase'),
        'shared': ('rulebase',),
        'vsys': ('name', 'ngfw_device'),
    },
    'panos_pbf_policy_rules': {
        'device_group': ('name', 'panorama_device', 'rulebase'),
        'shared': ('rulebase',),
        'vsys': ('name', 'ngfw_device'),
    },
    'panos_security_policy_rules': {
        'device_group': ('name', 'panorama_device', 'rulebase'),
        'shared': ('rulebase',),
        'vsys': ('name', 'ngfw_device'),
    },
    'panos_security_profile_group': {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
    },
    'panos_service': {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    },
    'panos_service_group': {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    },
    'panos_template': {
        'panorama': ('panorama_device',),
    },
    'panos_template_stack': {
        'panorama': ('panorama_device',),
    },
    # A template variable sits inside a template or inside a template stack, so the two
    # sub-blocks are the two the emitter can choose between (F6.5).
    'panos_template_variable': {
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
    },
    'panos_tunnel_interface': {
        'ngfw': ('ngfw_device',),
        'shared': (),
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
    },
    'panos_virtual_router': {
        'ngfw': ('ngfw_device',),
        'vsys': ('name', 'ngfw_device'),
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
    },
    'panos_virtual_router_static_route_ipv4': {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
    },
    'panos_vlan_interface': {
        'ngfw': ('ngfw_device',),
        'shared': (),
        'template': ('name', 'ngfw_device', 'panorama_device'),
    },
    # A virtual system is the scope itself, and the export can only place it inside a template
    # or a template stack, so this row has no `vsys` sub-block (F6.5).
    'panos_vsys': {
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    },
    'panos_zone': {
        'vsys': ('name', 'ngfw_device'),
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
    },
}

# F5.5: the shape of every provider data source type, written from
# `terraform providers schema -json` against the provider version the golden
# provider.tf declares (v2.0.14), and pinned against the live schema by
# tests/test_data_source_schema.py.
#
# Row shape: type -> (declares `name`, {sub-block: fields}). The two facts are
# the two the gate rule for a `data` block needs
# (`sanity_checks.check_data_blocks`).
#
# Unlike LOCATION_SCHEMA this table is not a generator subset: it lists every
# sub-block the provider declares, because the gate must refuse a sub-block or
# field a type does not declare. `terraform validate` accepts an unknown
# `location` sub-block and drops it silently, so a wrong sub-block fails at
# apply, not at validate.
#
# Verified against provider v2.0.14 with `terraform providers schema -json`:
# 128 data sources, 106 that declare `name` and 22 that do not (the settings,
# policy, and collection shapes), `location` required for all 128, and `name`
# required for every data source that declares it.
DATA_SOURCE_SCHEMA = {
    'panos_address': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_address_group': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_addresses': (False, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_admin_role': (True, {
        'template': ('name', 'panorama_device'),
    }),
    'panos_administrative_tag': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_administrator': (True, {
        'ngfw': (),
        'panorama': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
    }),
    'panos_aggregate_interface': (True, {
        'ngfw': ('ngfw_device',),
        'shared': (),
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_aggregate_layer3_subinterface': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_anti_spyware_security_profile': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_antivirus_security_profile': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_application': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_application_group': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_authentication_policy': (False, {
        'device_group': ('name', 'panorama_device', 'rulebase'),
        'shared': ('rulebase',),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_authentication_policy_rules': (False, {
        'device_group': ('name', 'panorama_device', 'rulebase'),
        'shared': ('rulebase',),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_authentication_profile': (True, {
        'panorama': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_bfd_network_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_bfd_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_bgp_address_family_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_bgp_auth_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_bgp_dampening_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_bgp_filtering_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_bgp_redistribution_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_bgp_timer_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_certificate': (True, {
        'panorama': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_certificate_profile': (True, {
        'panorama': (),
        'shared': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
    }),
    'panos_config_log_settings': (True, {
        'panorama': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
    }),
    'panos_correlation_log_settings': (True, {
        'panorama': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
    }),
    'panos_custom_data_object': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_custom_spyware': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_custom_url_category': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_custom_vulnerability': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_data_filtering_profile': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
    }),
    'panos_decryption_policy': (False, {
        'device_group': ('name', 'panorama_device', 'rulebase'),
        'shared': ('rulebase',),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_decryption_policy_rules': (False, {
        'device_group': ('name', 'panorama_device', 'rulebase'),
        'shared': ('rulebase',),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_decryption_profile': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_default_security_policy': (False, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
    }),
    'panos_device_group': (True, {
        'panorama': ('panorama_device',),
    }),
    'panos_device_group_parent': (False, {
        'panorama': ('panorama_device',),
    }),
    'panos_dhcp': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_dns_proxy': (True, {
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_dns_settings': (False, {
        'system': ('device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_dos_protection_profile': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
    }),
    'panos_dynamic_updates': (False, {
        'system': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_dynamic_user_group': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_email_server_profile': (True, {
        'panorama': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_ethernet_interface': (True, {
        'ngfw': ('ngfw_device',),
        'shared': (),
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_ethernet_layer3_subinterface': (True, {
        'ngfw': ('ngfw_device',),
        'shared': (),
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_external_dynamic_list': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_file_blocking_security_profile': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_filters_access_list_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_filters_as_path_access_list_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_filters_bgp_route_map_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_filters_community_list_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_filters_prefix_list_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_filters_route_maps_redistribution_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_general_settings': (False, {
        'system': ('device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_globalprotect_gateway': (True, {
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_globalprotect_log_settings': (True, {
        'panorama': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
    }),
    'panos_globalprotect_portal': (True, {
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_gre_tunnel': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_hipmatch_log_settings': (True, {
        'panorama': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
    }),
    'panos_ike_crypto_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_ike_gateway': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_interface_management_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_ip_tag': (False, {
        'panorama': (),
        'target_device': ('serial', 'vsys'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_ipsec_crypto_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_ipsec_tunnel': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_iptag_log_settings': (True, {
        'panorama': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
    }),
    'panos_ldap_profile': (True, {
        'panorama': (),
        'shared': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_lldp_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_local_user': (True, {
        'shared': (),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_log_export_schedule': (True, {
        'system': ('device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_log_forwarding_profile': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
    }),
    'panos_logical_router': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_loopback_interface': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_mfa_server_profile': (True, {
        'shared': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_monitor_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_multicast_pim_interface_timer_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_nat_policy': (False, {
        'device_group': ('name', 'panorama_device', 'rulebase'),
        'shared': ('rulebase',),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_nat_policy_rules': (False, {
        'device_group': ('name', 'panorama_device', 'rulebase'),
        'shared': ('rulebase',),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_ntp_settings': (False, {
        'system': ('device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_ospf_auth_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_ospf_interface_timer_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_ospf_redistribution_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_ospf_spf_timer_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_ospfv3_auth_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_ospfv3_if_timer_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_ospfv3_redistribution_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_ospfv3_spf_timer_routing_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_password_profile': (True, {
        'ngfw': (),
        'panorama': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
    }),
    'panos_pbf_policy': (False, {
        'device_group': ('name', 'panorama_device', 'rulebase'),
        'shared': ('rulebase',),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_pbf_policy_rules': (False, {
        'device_group': ('name', 'panorama_device', 'rulebase'),
        'shared': ('rulebase',),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_predefined_dlp_file_type': (True, {
        'predefined': (),
    }),
    'panos_proxy_settings': (False, {
        'system': ('device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_radius_profile': (True, {
        'panorama': (),
        'shared': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_saml_idp_profile': (True, {
        'panorama': (),
        'shared': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_schedule': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_security_policy': (False, {
        'device_group': ('name', 'panorama_device', 'rulebase'),
        'shared': ('rulebase',),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_security_policy_rules': (False, {
        'device_group': ('name', 'panorama_device', 'rulebase'),
        'shared': ('rulebase',),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_security_profile_group': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
    }),
    'panos_service': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_service_group': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_snmptrap_profile': (True, {
        'panorama': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_ssl_decrypt': (False, {
        'panorama': (),
        'shared': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
    }),
    'panos_ssl_tls_service_profile': (True, {
        'panorama': (),
        'shared': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
    }),
    'panos_syslog_profile': (True, {
        'panorama': (),
        'shared': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_system_log_settings': (True, {
        'panorama': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
    }),
    'panos_tacacs_plus_profile': (True, {
        'panorama': (),
        'shared': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_template': (True, {
        'panorama': ('panorama_device',),
    }),
    'panos_template_stack': (True, {
        'panorama': ('panorama_device',),
    }),
    'panos_template_variable': (True, {
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
    }),
    'panos_tunnel_interface': (True, {
        'ngfw': ('ngfw_device',),
        'shared': (),
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_url_filtering_security_profile': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
    }),
    'panos_userid_log_settings': (True, {
        'panorama': (),
        'template': ('name', 'panorama_device'),
        'template_stack': ('name', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
    }),
    'panos_virtual_router': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack_vsys': ('ngfw_device', 'panorama_device', 'template_stack', 'vsys'),
        'template_vsys': ('ngfw_device', 'panorama_device', 'template', 'vsys'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_virtual_router_static_route_ipv4': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_virtual_router_static_route_ipv6': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_virtual_router_static_routes_ipv4': (False, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_virtual_router_static_routes_ipv6': (False, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_virtual_wire': (True, {
        'ngfw': ('ngfw_device',),
        'shared': (),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_vlan': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_vlan_entry': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_vlan_interface': (True, {
        'ngfw': ('ngfw_device',),
        'shared': (),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_vsys': (True, {
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
    'panos_vulnerability_security_profile': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
    }),
    'panos_wildfire_analysis_security_profile': (True, {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
    }),
    'panos_zone': (True, {
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
        'vsys': ('name', 'ngfw_device'),
    }),
    'panos_zone_protection_profile': (True, {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    }),
}

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
    # F3.3: the other interface kinds. The provider has no virtual-wire or
    # tap resource type; those are nested blocks on panos_ethernet_interface.
    'panos_vlan_interface',
    'panos_loopback_interface',
    'panos_tunnel_interface',
    'panos_aggregate_interface',
    'panos_aggregate_layer3_subinterface',
    'panos_virtual_router',
    'panos_virtual_router_static_route_ipv4',
    'panos_zone',
    # VPN (template scoped)
    'panos_ike_crypto_profile',
    'panos_ike_gateway',
    'panos_ipsec_crypto_profile',
    'panos_ipsec_tunnel',
    # F6.5: the scope objects. One resource per scope entry, in `scope.tf`, before the config
    # inside the scope (`docs/CODEBASE_ASSEMBLY.md` §6).
    'panos_device_group',
    'panos_device_group_parent',
    'panos_template',
    'panos_template_stack',
    'panos_template_variable',
    'panos_vsys',
})

# F6.5: the six scope object types, and the parsed key that names the scope each one places
# itself inside. The key is the location sub-block name, so the block and the key agree. An empty
# value is a scope that places itself at the top of its own chain (`panorama`), so `location`
# prints the empty sub-block, the shape `shared = {}` already uses. A variable and a virtual
# system can only be placed inside a template or a template stack, so a scope entry the export
# places nowhere writes no block: the converter does not guess a place.
SCOPE_TYPES = frozenset({
    'panos_device_group',
    'panos_device_group_parent',
    'panos_template',
    'panos_template_stack',
    'panos_template_variable',
    'panos_vsys',
})

# The order the scope file prints its blocks in: the F3.9 level order (device group, then
# template), with the parent record read as part of the device group level, because it names the
# relation between two device groups and not an object. `generate_scope_objects` prints in this
# order, and within a type the entries print in document order.
SCOPE_LEVEL_ORDER = (
    'panos_device_group',
    'panos_device_group_parent',
    'panos_template',
    'panos_template_stack',
    'panos_template_variable',
    'panos_vsys',
)

# The key the parse method records for the scope a scope entry sits in, in the order the emitter
# tries it. `template` is one of the four scope facts; `template_stack` is the property the
# template variable row declares, because the emitter reads it to choose the sub-block.
SCOPE_PLACEMENT = {
    'panos_device_group': (),
    'panos_device_group_parent': (),
    'panos_template': (),
    'panos_template_stack': (),
    'panos_template_variable': ('template', 'template_stack'),
    'panos_vsys': ('template',),
}

# The block that answers a name written inside a scope block's `location`: the type that defines
# that scope. A name inside a location is not a `.name` reference, so the reference rule cannot
# reach it; `sanity_checks.check_scope_blocks` reads this table (F6.5).
SCOPE_ANSWER = {
    'template': 'panos_template',
    'template_stack': 'panos_template_stack',
}

# The value shape the provider takes for each property a scope block prints at its own level,
# written from the provider 2.0.14 schema for the six scope types and pinned against the live schema
# by `tests/test_scope_objects.py`. A membership the provider takes as a list of objects is not a
# list of strings: `terraform validate` refuses a string there, so the shape is a fact and not a
# style choice. The entry name field and the location fields are not here, because the name field is
# `entry_coverage.name_field` and the location shape is `DATA_SOURCE_SCHEMA`.
SCOPE_SHAPE = {
    'panos_device_group': {
        'description': 'string',
        'devices': 'object_list',
        'templates': 'string_list',
    },
    'panos_device_group_parent': {
        'parent': 'string',
    },
    'panos_template': {
        'default_vsys': 'string',
        'description': 'string',
    },
    'panos_template_stack': {
        'default_vsys': 'string',
        'description': 'string',
        'devices': 'object_list',
        'templates': 'string_list',
    },
    'panos_template_variable': {
        'description': 'string',
        'type': 'object',
    },
    'panos_vsys': {},
}

# F6.6: the value-to-variable mapping (`docs/CODEBASE_ASSEMBLY.md` §9). One row per location field the
# emitter prints — the fields `LOCATION_SCHEMA` declares — and what `TerraformGenerator.location_block`
# prints for it. The mapping is a table, so the emitter reads it and the gate reads it, and no emitter
# branch decides the shape for one type. A property at the block's own level is the entry's content, not a
# site value, so it is not in this table: `panos_template_variable` prints its value as a literal (F6.5
# decision 3, recorded in `backlog.md`). `variable` names the value through the §5 rule in `naming.py`.
VARIABLE = 'variable'
LITERAL = 'literal'
VALUE_VARIABLES = {
    # The device the site names. Hardware replacement changes the serial, and a literal prints in every
    # resource inside the template, so this is the value a codebase changes per site (§9 rule 1).
    'ngfw_device': VARIABLE,
    # The entry name is the row identity (F6.5 rule 3), not a site value.
    'name': LITERAL,
    # A virtual system is a scope name, not a site value.
    'vsys': LITERAL,
    # The codebase states no device fact in a location (§8 rule 6), and the Panorama host is the credential
    # gap (§11), so this row states the decision for a field the tool never prints.
    'panorama_device': LITERAL,
    # The parse records no rulebase (F3.5), so no value reaches the block.
    'rulebase': LITERAL,
}

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
#   emitter      - the TerraformGenerator method names that read this row's
#                  properties. Two names when a report writer reads properties
#                  the .tf emitter does not.
#   properties   - the keys of the parsed object those emitters read. The
#                  entry name and the four scope facts are the row identity,
#                  not properties, so they are not listed here.
#
# Maintenance duty: an emitter change that adds, renames, or drops a
# resource type must update this matrix in the same change, and an emitter
# that reads or stops reading a property must update that row's
# `properties` in the same change.
# tests/test_coverage_matrix.py fails when the matrix and the converter
# disagree (row set, fixture content, emitted output, row shape, or a
# declared property the emitter does not read). The measured read sets are
# pinned by tests/test_property_coverage.py.
COVERAGE_MATRIX = (
    {
        'resource': 'panos_address',
        'xml_element': 'address/entry',
        'xml_name': 'Web-Server-1',
        'emitted_name': 'Web-Server-1',
        'fixture': 'address_objects.xml',
        'output_file': 'address_objects.tf',
        'emitter': ('generate_address_objects', 'generate_manual_setup_report',),
        'properties': (
            'declared_type',
            'description',
            'disable_override',
            'other',
            'report_only',
            'tags',
            'type',
            'value',
        ),
    }, {
        'resource': 'panos_address_group',
        'xml_element': 'address-group/entry',
        'xml_name': 'Web-Servers',
        'emitted_name': 'Web-Servers',
        'fixture': 'address_groups.xml',
        'output_file': 'address_groups.tf',
        'emitter': ('generate_address_groups',),
        'properties': ('description', 'dynamic_filter', 'static_members',),
    }, {
        'resource': 'panos_administrative_tag',
        'xml_element': 'tag/entry',
        'xml_name': 'env-prod',
        'emitted_name': 'env-prod',
        'fixture': 'tags.xml',
        'output_file': 'tags.tf',
        'emitter': ('generate_tags',),
        'properties': ('color', 'comments', 'description',),
    }, {
        'resource': 'panos_application_group',
        'xml_element': 'application-group/entry',
        'xml_name': 'web-apps',
        'emitted_name': 'web-apps',
        'fixture': 'application_groups.xml',
        'output_file': 'application_groups.tf',
        'emitter': ('generate_application_groups',),
        'properties': ('members',),
    }, {
        'resource': 'panos_custom_url_category',
        'xml_element': 'custom-url-category/entry',
        'xml_name': 'blocked-sites',
        'emitted_name': 'blocked-sites',
        'fixture': 'custom_url_categories.xml',
        'output_file': 'custom_url_categories.tf',
        'emitter': ('generate_custom_url_categories',),
        'properties': ('description', 'list', 'type',),
    }, {
        'resource': 'panos_external_dynamic_list',
        'xml_element': 'external-list/entry',
        'xml_name': 'threat-ips',
        'emitted_name': 'threat-ips',
        'fixture': 'external_lists.xml',
        'output_file': 'external_lists.tf',
        'emitter': ('generate_external_lists',),
        'properties': ('fields', 'type',),
    }, {
        'resource': 'panos_service',
        'xml_element': 'service/entry',
        'xml_name': 'TCP-8080',
        'emitted_name': 'TCP-8080',
        'fixture': 'service_objects.xml',
        'output_file': 'service_objects.tf',
        'emitter': ('generate_service_objects',),
        'properties': ('description', 'disable_override', 'other_protocol', 'protocols', 'tags',),
    }, {
        'resource': 'panos_service_group',
        'xml_element': 'service-group/entry',
        'xml_name': 'Web-Services',
        'emitted_name': 'Web-Services',
        'fixture': 'service_groups.xml',
        'output_file': 'service_groups.tf',
        'emitter': ('generate_service_groups',),
        'properties': ('members',),
    }, {
        'resource': 'panos_security_policy_rules',
        'xml_element': 'security/rules/entry',
        'xml_name': 'Allow-Web-Traffic',
        'emitted_name': 'Allow-Web-Traffic',
        'fixture': 'security_rules.xml',
        'output_file': 'security_rules.tf',
        'emitter': ('generate_security_rules',),
        'properties': (
            'action',
            'applications',
            'description',
            'destination_addresses',
            'destination_zones',
            'disabled',
            'log_end',
            'log_start',
            'services',
            'source_addresses',
            'source_zones',
        ),
    }, {
        'resource': 'panos_nat_policy_rules',
        'xml_element': 'nat/rules/entry',
        'xml_name': 'Outbound-NAT',
        'emitted_name': 'Outbound-NAT',
        'fixture': 'nat_rules.xml',
        'output_file': 'nat_rules.tf',
        'emitter': ('generate_nat_rules',),
        'properties': (
            'description',
            'destination_addresses',
            'destination_translation_address',
            'destination_translation_port',
            'destination_zone',
            'disabled',
            'service',
            'source_addresses',
            'source_translation_address',
            'source_translation_type',
            'source_zones',
        ),
    }, {
        # F2.9: decryption rules emit as real v2 resources (one per rule)
        'resource': 'panos_decryption_policy_rules',
        'xml_element': 'decryption/rules/entry',
        'xml_name': 'Decrypt-HTTPS',
        'emitted_name': 'Decrypt-HTTPS',
        'fixture': 'decryption_rules.xml',
        'output_file': 'decryption_rules.tf',
        'emitter': ('generate_decryption_rules',),
        'properties': (
            'action',
            'categories',
            'description',
            'destination_addresses',
            'destination_zones',
            'disabled',
            'log_end',
            'log_setting',
            'log_start',
            'profile',
            'services',
            'source_addresses',
            'source_users',
            'source_zones',
            'type',
        ),
    }, {
        # F2.9: PBF rules emit as real v2 resources (one per rule)
        'resource': 'panos_pbf_policy_rules',
        'xml_element': 'pbf/rules/entry',
        'xml_name': 'PBF-Forward',
        'emitted_name': 'PBF-Forward',
        'fixture': 'pbf_rules.xml',
        'output_file': 'pbf_rules.tf',
        'emitter': ('generate_pbf_rules',),
        'properties': (
            'action',
            'applications',
            'description',
            'destination_addresses',
            'disabled',
            'enforce_symmetric_return',
            'schedule',
            'services',
            'source_addresses',
            'source_users',
            'source_zones',
        ),
    }, {
        'resource': 'panos_security_profile_group',
        'xml_element': 'profile-group/entry',
        'xml_name': 'Strict-Profile',
        'emitted_name': 'Strict-Profile',
        'fixture': 'security_profile_groups.xml',
        'output_file': 'security_profile_groups.tf',
        'emitter': ('generate_security_profile_groups',),
        'properties': (
            'data_filtering',
            'file_blocking',
            'gtp',
            'sctp',
            'spyware',
            'url_filtering',
            'virus',
            'vulnerability',
            'wildfire_analysis',
        ),
    }, {
        # F2.9: PBF path monitoring profiles are template-scoped in v2;
        # a different PAN-OS object from the IPsec tunnel monitor profile
        'resource': 'panos_monitor_profile',
        'xml_element': 'profiles/monitor-profile/entry',
        'xml_name': 'PM-Branch',
        'emitted_name': 'PM-Branch',
        'fixture': 'pbf_monitor_profiles.xml',
        'output_file': 'monitor_profiles.tf',
        'emitter': ('generate_pbf_monitor_profiles',),
        'properties': ('action', 'interval', 'threshold',),
    }, {
        'resource': 'panos_ethernet_interface',
        'xml_element': 'ethernet/entry',
        'xml_name': 'ethernet1/1',
        'emitted_name': 'ethernet1/1',
        'fixture': 'interfaces_ethernet.xml',
        'output_file': 'interfaces.tf',
        'emitter': ('generate_interfaces',),
        'properties': ('comment', 'ip_addresses', 'ipv6_addresses', 'management_profile', 'mode', 'tag', 'type',),
    }, {
        'resource': 'panos_ethernet_layer3_subinterface',
    # The physical L3 interface feeds its derived .0 subinterface:
    # the entry name is ethernet1/1, the subinterface is ethernet1/1.0.
        'xml_element': 'ethernet/entry',
        'xml_name': 'ethernet1/1',
        'emitted_name': 'ethernet1/1.0',
        'fixture': 'interfaces_ethernet.xml',
        'output_file': 'interfaces.tf',
        'emitter': ('generate_interfaces',),
        'properties': (
            'comment',
            'ip_addresses',
            'ipv6_addresses',
            'management_profile',
            'mode',
            'parent',
            'tag',
            'type',
        ),
    }, {
        'resource': 'panos_vlan_interface',
        'xml_element': 'vlan/units/entry',
        'xml_name': '10',
        'emitted_name': 'vlan.10',
        'fixture': 'interfaces_other.xml',
        'output_file': 'interfaces.tf',
        'emitter': ('generate_interfaces',),
        'properties': (
            'comment',
            'ip_addresses',
            'ipv6_addresses',
            'management_profile',
            'mode',
            'parent',
            'tag',
            'type',
        ),
    }, {
        'resource': 'panos_loopback_interface',
        'xml_element': 'loopback/units/entry',
        'xml_name': '1',
        'emitted_name': 'loopback.1',
        'fixture': 'interfaces_other.xml',
        'output_file': 'interfaces.tf',
        'emitter': ('generate_interfaces',),
        'properties': (
            'comment',
            'ip_addresses',
            'ipv6_addresses',
            'management_profile',
            'mode',
            'parent',
            'tag',
            'type',
        ),
    }, {
        'resource': 'panos_tunnel_interface',
        'xml_element': 'tunnel/units/entry',
        'xml_name': '1',
        'emitted_name': 'tunnel.1',
        'fixture': 'interfaces_other.xml',
        'output_file': 'interfaces.tf',
        'emitter': ('generate_interfaces',),
        'properties': (
            'comment',
            'ip_addresses',
            'ipv6_addresses',
            'management_profile',
            'mode',
            'parent',
            'tag',
            'type',
        ),
    }, {
        'resource': 'panos_aggregate_interface',
        'xml_element': 'aggregate-ethernet/entry',
        'xml_name': 'ae1',
        'emitted_name': 'ae1',
        'fixture': 'interfaces_other.xml',
        'output_file': 'interfaces.tf',
        'emitter': ('generate_interfaces',),
        'properties': (
            'comment',
            'ip_addresses',
            'ipv6_addresses',
            'management_profile',
            'mode',
            'parent',
            'tag',
            'type',
        ),
    }, {
        'resource': 'panos_aggregate_layer3_subinterface',
        'xml_element': 'aggregate-ethernet/entry',
        'xml_name': 'ae1.101',
        'emitted_name': 'ae1.101',
        'fixture': 'interfaces_other.xml',
        'output_file': 'interfaces.tf',
        'emitter': ('generate_interfaces',),
        'properties': (
            'comment',
            'ip_addresses',
            'ipv6_addresses',
            'management_profile',
            'mode',
            'parent',
            'tag',
            'type',
        ),
    }, {
        'resource': 'panos_virtual_router',
        'xml_element': 'virtual-router/entry',
        'xml_name': 'default',
        'emitted_name': 'default',
        'fixture': 'virtual_routers.xml',
        'output_file': 'virtual_routers.tf',
        'emitter': ('generate_virtual_routers',),
        'properties': ('interfaces', 'router_type', 'static_routes',),
    }, {
        'resource': 'panos_virtual_router_static_route_ipv4',
        'xml_element': 'static-route/entry',
        'xml_name': 'default-gw',
        'emitted_name': 'default-gw',
        'fixture': 'virtual_routers.xml',
        'output_file': 'virtual_routers.tf',
        'emitter': ('generate_virtual_routers',),
        'properties': ('destination', 'metric', 'nexthop_interface', 'nexthop_ip',),
    }, {
        'resource': 'panos_zone',
        'xml_element': 'zone/entry',
        'xml_name': 'trust',
        'emitted_name': 'trust',
        'fixture': 'zones.xml',
        'output_file': 'zones.tf',
        'emitter': ('generate_zones',),
        'properties': ('interfaces', 'type', 'zone_protection_profile',),
    }, {
        'resource': 'panos_ike_crypto_profile',
        'xml_element': 'crypto-profiles/ike-crypto-profiles/entry',
        'xml_name': 'IKE-DEFAULT',
        'emitted_name': 'IKE-DEFAULT',
        'fixture': 'ike_crypto_profiles.xml',
        'output_file': 'vpn.tf',
        'emitter': ('generate_vpn_config',),
        'properties': ('authentications', 'dh_groups', 'encryptions', 'lifetime_hours',),
    }, {
        'resource': 'panos_ike_gateway',
        'xml_element': 'ike/gateway/entry',
        'xml_name': 'IKE-GW-Branch',
        'emitted_name': 'IKE-GW-Branch',
        'fixture': 'ike_gateways.xml',
        'output_file': 'vpn.tf',
        'emitter': ('generate_vpn_config',),
        'properties': (
            'auth_type',
            'ike_crypto_profile',
            'local_address',
            'local_address_interface',
            'local_id',
            'peer_address',
            'peer_address_type',
            'peer_id',
            'pre_shared_key',
            'version',
        ),
    }, {
        'resource': 'panos_ipsec_crypto_profile',
        'xml_element': 'crypto-profiles/ipsec-crypto-profiles/entry',
        'xml_name': 'IPSEC-DEFAULT',
        'emitted_name': 'IPSEC-DEFAULT',
        'fixture': 'ipsec_crypto_profiles.xml',
        'output_file': 'vpn.tf',
        'emitter': ('generate_vpn_config',),
        'properties': ('authentications', 'dh_group', 'encryptions', 'lifetime_hours', 'lifetime_kb',),
    }, {
        'resource': 'panos_ipsec_tunnel',
        'xml_element': 'tunnel/ipsec/entry',
        'xml_name': 'TUN-Branch',
        'emitted_name': 'TUN-Branch',
        'fixture': 'ipsec_tunnels.xml',
        'output_file': 'vpn.tf',
        'emitter': ('generate_vpn_config',),
        'properties': (
            'ike_gateway',
            'ipsec_crypto_profile',
            'local',
            'protocol',
            'proxy_ids',
            'remote',
            'tunnel_interface',
            'type',
        ),
    }, {
        # F6.5: the scope objects. One file for the run (`scope.tf`), written before the config
        # inside the scope. The entry name is the row identity, so it is not a property.
        # `parent` is on this row because the emitter reads it for the parent record below, and the
        # property scan measures one entry against the row that covers its container. The device group
        # block itself prints no parent: the provider declares no `parent` attribute for this type.
        'resource': 'panos_device_group',
        'xml_element': 'device-group/entry',
        'xml_name': 'Edge-FW',
        'emitted_name': 'Edge-FW',
        'fixture': 'scope_objects.xml',
        'output_file': 'scope.tf',
        'emitter': ('generate_scope_objects',),
        'properties': ('description', 'devices', 'parent', 'templates'),
    }, {
        # The provider declares no `name` for this type, so the entry name reaches the block
        # through `device_group` (`DATA_SOURCE_SCHEMA`). One device-group entry can feed two
        # blocks: the scope object above and this record.
        'resource': 'panos_device_group_parent',
        'xml_element': 'device-group/entry',
        'xml_name': 'Edge-FW',
        'emitted_name': 'Edge-FW',
        'fixture': 'scope_objects.xml',
        'output_file': 'scope.tf',
        'emitter': ('generate_scope_objects',),
        'properties': ('parent',),
    }, {
        'resource': 'panos_template',
        'xml_element': 'templates/entry',
        'xml_name': 'Edge-Networks',
        'emitted_name': 'Edge-Networks',
        'fixture': 'scope_objects.xml',
        'output_file': 'scope.tf',
        'emitter': ('generate_scope_objects',),
        'properties': ('default_vsys', 'description'),
    }, {
        'resource': 'panos_template_stack',
        'xml_element': 'template-stack/entry',
        'xml_name': 'Edge-Stack',
        'emitted_name': 'Edge-Stack',
        'fixture': 'scope_objects.xml',
        'output_file': 'scope.tf',
        'emitter': ('generate_scope_objects',),
        'properties': ('default_vsys', 'description', 'devices', 'templates'),
    }, {
        # `template_stack` is the placement fact the emitter reads to choose the location
        # sub-block. The value prints as a literal until F6.6 makes it a `var.` reference.
        'resource': 'panos_template_variable',
        'xml_element': 'variable/entry',
        'xml_name': 'edge-tag',
        'emitted_name': 'edge-tag',
        'fixture': 'scope_objects.xml',
        'output_file': 'scope.tf',
        'emitter': ('generate_scope_objects',),
        'properties': ('description', 'template_stack', 'type'),
    }, {
        # A virtual system block carries the entry name and the location only, so this row
        # declares no property.
        'resource': 'panos_vsys',
        'xml_element': 'vsys/entry',
        'xml_name': 'edge-vsys',
        'emitted_name': 'edge-vsys',
        'fixture': 'scope_objects.xml',
        'output_file': 'scope.tf',
        'emitter': ('generate_scope_objects',),
        'properties': (),
    }
)

