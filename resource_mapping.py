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
    ACTION_SCHEMA      - one row per provider action type (F6.7): the fields
                         it declares, each field's value shape, and the fields
                         the row requires. Enforced by
                         tests/test_commit_actions.py against the live schema,
                         and read by the gate rule for an `action` block.
    ACTION_FILTERS     - the one mapping from an action field to the scope
                         fact it names (F6.7). The emitter reads it and the
                         gate reads it, so no branch names the fields again.
    PROTOCOL_SHAPE     - one row per level of the `protocol` object attribute on
                         `panos_virtual_router` (F7.1): the nesting mode or the
                         leaf value shape, the fields the level declares, the
                         report value that selects a `one_of` key, and the fields
                         the provider marks `sensitive`. The emitter prints from it,
                         the gate rule `protocol_object` reads it, and
                         tests/test_protocol_object.py pins it against the live schema.

The generator emits the v2 types directly; the old v1 names
(panos_address_object, panos_security_rule_group, ...) no longer exist
anywhere in the code base. The v1 -> v2 rename rationale is preserved in
docs/RESOURCE_MAPPING.md.

Verified against provider v2.0.14 (128 resource types) with
`terraform providers schema -json`.
"""

from typing import Optional

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

# F7.8: the six filter containers place in a template or a template stack, the shape the pinned
# data source declares for each one.

    'panos_filters_access_list_routing_profile': {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    },

    'panos_filters_as_path_access_list_routing_profile': {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    },

    'panos_filters_bgp_route_map_routing_profile': {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    },

    'panos_filters_community_list_routing_profile': {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    },

    'panos_filters_prefix_list_routing_profile': {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
    },

    'panos_filters_route_maps_redistribution_routing_profile': {
        'ngfw': ('ngfw_device',),
        'template': ('name', 'ngfw_device', 'panorama_device'),
        'template_stack': ('name', 'ngfw_device', 'panorama_device'),
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

# F7.8: the six routing-profile filter containers, one resource per entry (`filters.tf`).
    'panos_filters_access_list_routing_profile',
    'panos_filters_as_path_access_list_routing_profile',
    'panos_filters_bgp_route_map_routing_profile',
    'panos_filters_community_list_routing_profile',
    'panos_filters_prefix_list_routing_profile',
    'panos_filters_route_maps_redistribution_routing_profile',
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
# tries it. Both keys are scope facts (F6.10.5), so the placement key is the fact the emitter reads
# to choose the sub-block, and the property scan counts no property for either.
SCOPE_PLACEMENT = {
    'panos_device_group': (),
    'panos_device_group_parent': (),
    'panos_template': (),
    'panos_template_stack': (),
    'panos_template_variable': ('template', 'template_stack'),
    'panos_vsys': ('template',),
}

# The block that answers a name written inside a scope block's `location`, or inside an `action`
# block (F6.7): the type that defines that scope. A name inside a location or a filter list is not
# a `.name` reference, so the reference rule cannot reach it; `sanity_checks.check_scope_blocks` and
# `sanity_checks.check_actions` read this table (F6.5, F6.7). The `device_group` row is read by the
# action rule: the scope rule never sees it, because the six scope types place themselves and print
# no device-group name inside a location.
SCOPE_ANSWER = {
    'device_group': 'panos_device_group',
    'template': 'panos_template',
    'template_stack': 'panos_template_stack',
}

# F6.7: the one mapping from an `action` field to the scope fact it names. The emitter reads it
# (fact to field) and the gate reads it (field to fact), so no branch names the fields again. The
# `name` field of a push shape names the fact its `type` states, so its row states the field that
# carries the fact key rather than a fact. A fact the provider cannot name in a commit filter
# (`vsys`, `vsys_device`) has no row, so no field can state it, and a unit whose selected fact is one
# of those writes no action. `commit_actions.field_fact` and `commit_actions.filter_field` are the
# two readers of this table; neither adds a fact.
ACTION_FILTERS = {
    'device_groups': 'device_group',
    'templates': 'template',
    'template_stacks': 'template_stack',
    'name': 'type',
}

# F6.7: the two action types the pinned schema declares (2.0.14), written from
# `terraform providers schema -json` and pinned against the live schema by
# `tests/test_commit_actions.py`. One row: the fields the action declares with their value shapes,
# and the fields the row requires. An action declares no `location`, so the `location_present` rule
# does not read it, and an action names no entry, so no coverage matrix row covers an `action`
# block (the decision F5.5 made for a `data` block).
ACTION_SCHEMA = {
    'panos_commit': ((), {
        'admins': 'string_list',
        'description': 'string',
        'device_groups': 'string_list',
        'exclude_device_and_network': 'bool',
        'exclude_policy_and_objects': 'bool',
        'exclude_shared_objects': 'bool',
        'force': 'bool',
        'log_collector_groups': 'string_list',
        'log_collectors': 'string_list',
        'push_configuration': 'object',
        'template_stacks': 'string_list',
        'templates': 'string_list',
        'wildfire_appliances': 'string_list',
        'wildfire_clusters': 'string_list',
    }),
    'panos_push_to_devices': (('name', 'type'), {
        'description': 'string',
        'devices': 'string_list',
        'force_template_values': 'bool',
        'include_template': 'bool',
        'name': 'string',
        'type': 'string',
    }),
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

# F6.6: the value-to-variable mapping (`docs/CODEBASE_ASSEMBLY.md` §9). One row per field the emitter
# prints — the fields `LOCATION_SCHEMA` declares, and the leaf fields `PROTOCOL_SHAPE` states — and what
# the block prints for it. The mapping is a table, so the emitter reads it and the gate reads it, and no
# emitter branch decides the shape for one type. A property is the entry's content, not a site value, so
# the table holds no property row except the `sensitive` rows: a field the provider marks sensitive
# cannot reach a generated file as a literal, so the block prints the reference for it even when the
# value is the entry's content. F7.7: such a name is a property only for the matrix row that covers the entry
# the run read it in. `panos_template_variable` prints its value as a literal (F6.5 decision 3,
# recorded in `backlog.md`). `variable` names the value through the §5 rule in `naming.py`.
VARIABLE = 'variable'
LITERAL = 'literal'
# A field the provider marks `sensitive`: the block prints the reference, and no generated file states the
# value. The name is `naming.py` applied to the entry that holds the field, because a value cannot name itself
# (`backlog.md`, the value the parse cannot carry). F7.7: the run can read the value for such a field inside an
# entry, and it holds it only to decide the name, so no `.tfvars` line and no site row is written for it.
REFERENCE_ONLY = 'reference_only'
# F6.10.4: the shape for a site fact the tool cannot name. The run names the variable, holds no value for it,
# and the operator supplies the value in `terraform.tfvars` (§11). The export states a device as a hostname,
# so a serial is a fact the tool cannot read, and the tool names the name and not the value. This is the
# `reference_only` shape without the `sensitive` marking, because a serial is not a secret: the marking stays
# the `reference_only` row's rule alone.
OPERATOR_SUPPLIED = 'operator_supplied'
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
    # The three provider `sensitive` facts in the protocol object (F7.1, F7.7): the run reads them, the block
    # prints the reference, the run declares the variable, and no generated file states the value.
    'secret': REFERENCE_ONLY,
    'key': REFERENCE_ONLY,
    'password': REFERENCE_ONLY,
    # F6.10.4: the one row for a field the emitter prints outside a location, so the table covers the fields
    # it prints a value shape for: the location fields, the `sensitive` names, and this provider argument.
    # The corpus states no serial (the device entry names are hostnames), so no value can be named for it.
    'target': OPERATOR_SUPPLIED,
}

# F7.1, F7.2: the shape of the `protocol` object attribute on `panos_virtual_router`, written from the live
# provider schema measured 2026-10-31, and the `ospfv3` levels measured 2026-11-01
# (`tests/test_protocol_object.py` pins every row against it). One
# row per level the converter prints, plus the `sensitive` decision rows the emitter uses when a parse
# method reaches the field. The emitter prints from this table, the gate rule `protocol_object` reads
# this table, and no second table states a shape: `sanity_checks.value_shape` is the reader's own inverse
# for the leaf words.
#
# `shape` is one of `SHAPE_WORDS`. `fields` states the field name -> the shape word, in the print order.
# `selects` is the mapping from the report value to the key a `one_of` level prints; an empty `selects`
# means the level is not a one-of choice. `sensitive` names the fields the provider marks sensitive.
SHAPE_WORDS = ('string', 'bool', 'number', 'object', 'string_list', 'member_list', 'one_of', 'block')

# Each shape word as the provider schema states it: a level word is a nesting mode, and a leaf word is a
# type. `one_of`, `block` and `object` are all the `single` mode, and a `member_list` is a `list` whose
# members are values, so the two list words read the same way. The two shape-table pins read this one
# mapping instead of each stating its own (F7.1, F7.8).
SHAPE_TO_SCHEMA = {'string_list': 'list', 'member_list': 'list', 'object': 'single', 'one_of': 'single',
                   'block': 'single', 'string': 'string', 'bool': 'bool', 'number': 'number'}

# The reader states a `[` container as `string_list`, so that word covers a list of objects as well as a
# list of strings; `one_of` is the `object` shape with the extra rule that it states exactly one key.
# `block` is the `object` shape for a provider block that has no attributes of its own: the export states
# it by presence, so the value is the empty object and the block prints it (`value_shape` reads `{}` as an
# object, which is why the gate treats `block` as `object`). A field the export does not state has no value,
# so presence is the whole shape rule.
# `member_list` is the `string_list` shape with the extra rule that its members are values, which is what the
# provider declares for a field whose type is `['list', 'string']` (F7.6). A shape word is what the table
# states, so the reader's own inverse keeps reading the family word: `sanity_checks.SHAPE_READS_AS` is the one
# place that states which word a specialization reads back as.
PROTOCOL_TYPE = 'panos_virtual_router'
PROTOCOL_FIELD = 'protocol'

# The one exception to the field name to element name rule (`PanoramaParser._protocol_xml_name`), which
# turns `_` into `-`. The provider spells `strict_l_s_a_checking` for the element a PAN-OS export names
# `strict-lsa-checking`, because it splits the initialism, so the rule cannot produce it (F7.3).
XML_NAME_EXCEPTIONS = {'strict_l_s_a_checking': 'strict-lsa-checking'}

PROTOCOL_SHAPE: dict[str, dict] = {
    'protocol': {
        'shape': 'object',
        'fields': {'bgp': 'object', 'ospf': 'object', 'ospfv3': 'object', 'rip': 'object'},
        'selects': {},
        'sensitive': frozenset(),
    },
    # F7.6: `policy` is the fifth level the provider declares for `bgp`, so the row states it and the reader
    # fills it. F7.7 put the `auth_profile` level into the table, so the reader fills it too.
    'protocol/bgp': {
        'shape': 'object',
        'fields': {'enable': 'bool', 'local_as': 'string', 'router_id': 'string',
                   'peer_group': 'string_list', 'redist_rules': 'string_list',
                   'auth_profile': 'string_list', 'policy': 'object'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/peer_group': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'enable': 'bool', 'type': 'one_of', 'peer': 'string_list'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/peer_group/type': {
        'shape': 'one_of',
        'fields': {},
        'selects': {'external': 'ebgp', 'internal': 'ibgp',
                    'external-confederation': 'ebgp_confed',
                    'internal-confederation': 'ibgp_confed'},
        'sensitive': frozenset(),
    },
    'protocol/bgp/peer_group/type/ebgp': {
        'shape': 'object',
        'fields': {'export_nexthop': 'string', 'import_nexthop': 'string',
                   'remove_private_as': 'bool'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/peer_group/type/ebgp_confed': {
        'shape': 'object',
        'fields': {'export_nexthop': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/peer_group/type/ibgp': {
        'shape': 'object',
        'fields': {'export_nexthop': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/peer_group/type/ibgp_confed': {
        'shape': 'object',
        'fields': {'export_nexthop': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/peer_group/peer': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'enable': 'bool', 'peer_as': 'string',
                   'local_address': 'object', 'peer_address': 'object'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/peer_group/peer/local_address': {
        'shape': 'object',
        'fields': {'interface': 'string', 'ip': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/peer_group/peer/peer_address': {
        'shape': 'object',
        'fields': {'fqdn': 'string', 'ip': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/redist_rules': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'enable': 'bool',
                   'address_family_identifier': 'string', 'metric': 'number'},
        'selects': {},
        'sensitive': frozenset(),
    },
    # F7.7: the four auth profile levels are the levels the four parse methods read. A field the provider marks
    # `sensitive` is printed as the variable reference, so each row states its `sensitive` set.
    'protocol/bgp/auth_profile': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'secret': 'string'},
        'selects': {},
        'sensitive': frozenset({'secret'}),
    },
    # F7.9: the seven fields measured 2026-11-03 are the fields `parse_ospf` reads, so the row states them.
    # Field order is the print order: the two fields the row already stated keep their order, the three
    # `bool` fields follow in the order the schema names them, then the single-object levels in the order
    # the `ospfv3` row states them, then the two entry levels in the same order. None of these fields is
    # `sensitive`, so no `VALUE_VARIABLES` row is needed for them.
    'protocol/ospf': {
        'shape': 'object',
        'fields': {'enable': 'bool', 'router_id': 'string',
                   'allow_redist_default_route': 'bool', 'reject_default_route': 'bool',
                   'rfc1583': 'bool', 'timers': 'object', 'global_bfd': 'object',
                   'graceful_restart': 'object', 'area': 'string_list',
                   'export_rules': 'string_list', 'auth_profile': 'string_list'},
        'selects': {},
        'sensitive': frozenset(),
    },
    # A single-object level holds no entry, so the parse reads it as one object and the container table
    # names no row for it. `export_rules` is an entry level, so `parse_ospf` fills it and the property scan
    # measures its entries against the router row.
    'protocol/ospf/timers': {
        'shape': 'object',
        'fields': {'lsa_interval': 'number', 'spf_calculation_delay': 'number'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospf/global_bfd': {
        'shape': 'object',
        'fields': {'profile': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    # `strict_l_s_a_checking` is the provider spelling, and `XML_NAME_EXCEPTIONS` is the one place that
    # states the element name the export holds for it.
    'protocol/ospf/graceful_restart': {
        'shape': 'object',
        'fields': {'enable': 'bool', 'grace_period': 'number', 'helper_enable': 'bool',
                   'max_neighbor_restart_time': 'number', 'strict_l_s_a_checking': 'bool'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospf/export_rules': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'metric': 'number', 'new_path_type': 'string', 'new_tag': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    # F7.4: the four area sub-levels the provider declares, measured 2026-11-02. `default_route` is not a
    # child of `type`: the provider declares it inside the `nssa` and the `stub` bodies, and
    # `nssa_ext_range` only inside `nssa`, so the rows are the bodies' fields. The two routing levels stay
    # separate rows, because the provider declares `instance_id` for `ospfv3` and not for `ospf`.
    'protocol/ospf/area': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'type': 'one_of', 'range': 'string_list',
                   'interface': 'string_list', 'virtual_link': 'string_list'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospf/area/virtual_link': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'authentication': 'string', 'bfd': 'object',
                   'dead_counts': 'number', 'enable': 'bool', 'hello_interval': 'number',
                   'neighbor_id': 'string', 'retransmit_interval': 'number',
                   'transit_area_id': 'string', 'transit_delay': 'number'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospf/area/virtual_link/bfd': {
        'shape': 'object',
        'fields': {'profile': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospf/area/type': {
        'shape': 'one_of',
        'fields': {},
        'selects': {'normal': 'normal', 'nssa': 'nssa', 'stub': 'stub'},
        'sensitive': frozenset(),
    },
    'protocol/ospf/area/type/normal': {
        'shape': 'object',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    # A `default_route` element is the one choice the provider requires: `terraform validate` refuses one that
    # states neither `advertise` or `no`, so the row states the choice as `selects`. The export spells the
    # second alternative `no`, which is the value the mapping reads, and the key the provider prints is
    # `disable`. `nssa_ext_range` is an entry level with the same presence choice as a `range` entry.
    'protocol/ospf/area/type/nssa': {
        'shape': 'object',
        'fields': {'accept_summary': 'bool', 'default_route': 'one_of',
                   'nssa_ext_range': 'string_list'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospf/area/type/nssa/default_route': {
        'shape': 'one_of',
        'fields': {},
        'selects': {'advertise': 'advertise', 'no': 'disable'},
        'sensitive': frozenset(),
    },
    'protocol/ospf/area/type/nssa/default_route/advertise': {
        'shape': 'object',
        'fields': {'metric': 'number', 'type': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospf/area/type/nssa/default_route/disable': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospf/area/type/nssa/nssa_ext_range': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'advertise': 'block', 'suppress': 'block'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospf/area/type/stub': {
        'shape': 'object',
        'fields': {'accept_summary': 'bool', 'default_route': 'one_of'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospf/area/type/stub/default_route': {
        'shape': 'one_of',
        'fields': {},
        'selects': {'advertise': 'advertise', 'no': 'disable'},
        'sensitive': frozenset(),
    },
    # The `stub` body declares no metric type for the advertised default route, so this row states one field.
    'protocol/ospf/area/type/stub/default_route/advertise': {
        'shape': 'object',
        'fields': {'metric': 'number'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospf/area/type/stub/default_route/disable': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    # A range entry is the entry name plus the choice the provider requires: `terraform validate` refuses a
    # range element with no `advertise` or `suppress`, so the shape table states both as `block` fields and
    # the export's presence is the value (F7.1).
    'protocol/ospf/area/range': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'advertise': 'block', 'suppress': 'block'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospf/area/interface': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'enable': 'bool', 'passive': 'bool',
                   'metric': 'number', 'link_type': 'one_of', 'neighbor': 'string_list'},
        'selects': {},
        'sensitive': frozenset(),
    },
    # A neighbor entry is the entry name, which is the whole shape the provider declares for it.
    'protocol/ospf/area/interface/neighbor': {
        'shape': 'string_list',
        'fields': {'name': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospf/area/interface/link_type': {
        'shape': 'one_of',
        'fields': {},
        'selects': {'point-to-point': 'p2p', 'broadcast': 'broadcast', 'p2mp': 'p2mp'},
        'sensitive': frozenset(),
    },
    'protocol/ospf/area/interface/link_type/p2p': {
        'shape': 'object',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospf/area/interface/link_type/broadcast': {
        'shape': 'object',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospf/area/interface/link_type/p2mp': {
        'shape': 'object',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    # F7.7: `md5` is an entry level inside the profile entry, so the reader fills it through `_protocol_body`,
    # which reaches it through the field the profile row states. The container table states no row for it,
    # because an entry inside an entry is not in the scan scope.
    'protocol/ospf/auth_profile': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'password': 'string', 'md5': 'string_list'},
        'selects': {},
        'sensitive': frozenset({'password'}),
    },
    'protocol/ospf/auth_profile/md5': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'key': 'string', 'preferred': 'bool'},
        'selects': {},
        'sensitive': frozenset({'key'}),
    },
    # F7.2: the `ospfv3` levels `parse_ospfv3` reads, measured 2026-11-01 against the pinned provider. The
    # area subtree states the same shape the `ospf` rows state, field for field, because the provider
    # declares the same fields for both levels; the rows stay separate because the levels are separate. The
    # two are not identical: `ospfv3` declares `instance_id` on `area/interface` and on `area/virtual_link`,
    # and `ospf` does not. A level the parse does not read has no row, so the gate refuses it.
    # F7.3: the four levels measured 2026-11-02 are the scalar levels the provider declares for this level
    # and `parse_ospfv3` reads. F7.7 added `auth_profile`, the level the same method reads through
    # `_protocol_branch`.
    'protocol/ospfv3': {
        'shape': 'object',
        'fields': {'enable': 'bool', 'router_id': 'string', 'timers': 'object',
                   'global_bfd': 'object', 'graceful_restart': 'object', 'area': 'string_list',
                   'export_rules': 'string_list', 'auth_profile': 'string_list'},
        'selects': {},
        'sensitive': frozenset(),
    },
    # A scalar level holds no entries, so the parse reads it as one object and the container table names no
    # row for it. None of these levels declares a field the provider marks sensitive, so no
    # `VALUE_VARIABLES` row is needed for them.
    'protocol/ospfv3/timers': {
        'shape': 'object',
        'fields': {'lsa_interval': 'number', 'spf_calculation_delay': 'number'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/global_bfd': {
        'shape': 'object',
        'fields': {'profile': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    # `strict_l_s_a_checking` is the provider spelling, and `XML_NAME_EXCEPTIONS` is the one place that
    # states the element name the export holds for it.
    'protocol/ospfv3/graceful_restart': {
        'shape': 'object',
        'fields': {'enable': 'bool', 'grace_period': 'number', 'helper_enable': 'bool',
                   'max_neighbor_restart_time': 'number', 'strict_l_s_a_checking': 'bool'},
        'selects': {},
        'sensitive': frozenset(),
    },
    # An export rule is an entry, so the parse method fills this list and the property scan measures the
    # entries against the router row.
    'protocol/ospfv3/export_rules': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'metric': 'number', 'new_path_type': 'string', 'new_tag': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    # F7.7: the `ospfv3` auth profile, measured 2026-11-03 against the pinned provider. `ah` and
    # `esp/authentication` are choice levels: the export states the alternative by presence under the level, so
    # the row states the alternatives as `selects` keys, and each alternative that declares an attribute is its
    # own row. `none` declares no attribute, so it is the `block` field inside the row that holds it. Every
    # alternative holds only `key`, which the provider marks `sensitive`.
    'protocol/ospfv3/auth_profile': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'spi': 'string', 'ah': 'one_of', 'esp': 'object'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/auth_profile/ah': {
        'shape': 'one_of',
        'fields': {},
        'selects': {'md5': 'md5', 'sha1': 'sha1', 'sha256': 'sha256', 'sha384': 'sha384', 'sha512': 'sha512'},
        'sensitive': frozenset(),
    },
    # The five alternatives of `ah`, and the five of `esp/authentication`, are the same shape, so the rows are
    # the same row content read under two paths.
    'protocol/ospfv3/auth_profile/ah/md5': {
        'shape': 'object',
        'fields': {'key': 'string'},
        'selects': {},
        'sensitive': frozenset({'key'}),
    },
    'protocol/ospfv3/auth_profile/ah/sha1': {
        'shape': 'object',
        'fields': {'key': 'string'},
        'selects': {},
        'sensitive': frozenset({'key'}),
    },
    'protocol/ospfv3/auth_profile/ah/sha256': {
        'shape': 'object',
        'fields': {'key': 'string'},
        'selects': {},
        'sensitive': frozenset({'key'}),
    },
    'protocol/ospfv3/auth_profile/ah/sha384': {
        'shape': 'object',
        'fields': {'key': 'string'},
        'selects': {},
        'sensitive': frozenset({'key'}),
    },
    'protocol/ospfv3/auth_profile/ah/sha512': {
        'shape': 'object',
        'fields': {'key': 'string'},
        'selects': {},
        'sensitive': frozenset({'key'}),
    },
    'protocol/ospfv3/auth_profile/esp': {
        'shape': 'object',
        'fields': {'authentication': 'one_of', 'encryption': 'object'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/auth_profile/esp/authentication': {
        'shape': 'one_of',
        'fields': {'none': 'block'},
        'selects': {'md5': 'md5', 'none': 'none', 'sha1': 'sha1', 'sha256': 'sha256',
                     'sha384': 'sha384', 'sha512': 'sha512'},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/auth_profile/esp/authentication/md5': {
        'shape': 'object',
        'fields': {'key': 'string'},
        'selects': {},
        'sensitive': frozenset({'key'}),
    },
    'protocol/ospfv3/auth_profile/esp/authentication/sha1': {
        'shape': 'object',
        'fields': {'key': 'string'},
        'selects': {},
        'sensitive': frozenset({'key'}),
    },
    'protocol/ospfv3/auth_profile/esp/authentication/sha256': {
        'shape': 'object',
        'fields': {'key': 'string'},
        'selects': {},
        'sensitive': frozenset({'key'}),
    },
    'protocol/ospfv3/auth_profile/esp/authentication/sha384': {
        'shape': 'object',
        'fields': {'key': 'string'},
        'selects': {},
        'sensitive': frozenset({'key'}),
    },
    'protocol/ospfv3/auth_profile/esp/authentication/sha512': {
        'shape': 'object',
        'fields': {'key': 'string'},
        'selects': {},
        'sensitive': frozenset({'key'}),
    },
    'protocol/ospfv3/auth_profile/esp/encryption': {
        'shape': 'object',
        'fields': {'algorithm': 'string', 'key': 'string'},
        'selects': {},
        'sensitive': frozenset({'key'}),
    },
    'protocol/ospfv3/area': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'type': 'one_of', 'range': 'string_list',
                   'interface': 'string_list', 'virtual_link': 'string_list'},
        'selects': {},
        'sensitive': frozenset(),
    },
    # F7.4: the same shape the `ospf` row states, plus the `instance_id` the provider declares for this
    # level only.
    'protocol/ospfv3/area/virtual_link': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'authentication': 'string', 'bfd': 'object',
                   'dead_counts': 'number', 'enable': 'bool', 'hello_interval': 'number',
                   'instance_id': 'number', 'neighbor_id': 'string',
                   'retransmit_interval': 'number', 'transit_area_id': 'string',
                   'transit_delay': 'number'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/virtual_link/bfd': {
        'shape': 'object',
        'fields': {'profile': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/type': {
        'shape': 'one_of',
        'fields': {},
        'selects': {'normal': 'normal', 'nssa': 'nssa', 'stub': 'stub'},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/type/normal': {
        'shape': 'object',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/type/nssa': {
        'shape': 'object',
        'fields': {'accept_summary': 'bool', 'default_route': 'one_of',
                   'nssa_ext_range': 'string_list'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/type/nssa/default_route': {
        'shape': 'one_of',
        'fields': {},
        'selects': {'advertise': 'advertise', 'no': 'disable'},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/type/nssa/default_route/advertise': {
        'shape': 'object',
        'fields': {'metric': 'number', 'type': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/type/nssa/default_route/disable': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/type/nssa/nssa_ext_range': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'advertise': 'block', 'suppress': 'block'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/type/stub': {
        'shape': 'object',
        'fields': {'accept_summary': 'bool', 'default_route': 'one_of'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/type/stub/default_route': {
        'shape': 'one_of',
        'fields': {},
        'selects': {'advertise': 'advertise', 'no': 'disable'},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/type/stub/default_route/advertise': {
        'shape': 'object',
        'fields': {'metric': 'number'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/type/stub/default_route/disable': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/range': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'advertise': 'block', 'suppress': 'block'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/interface': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'enable': 'bool', 'passive': 'bool',
                   'metric': 'number', 'link_type': 'one_of', 'neighbor': 'string_list'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/interface/neighbor': {
        'shape': 'string_list',
        'fields': {'name': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/interface/link_type': {
        'shape': 'one_of',
        'fields': {},
        'selects': {'point-to-point': 'p2p', 'broadcast': 'broadcast', 'p2mp': 'p2mp'},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/interface/link_type/p2p': {
        'shape': 'object',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/interface/link_type/broadcast': {
        'shape': 'object',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/ospfv3/area/interface/link_type/p2mp': {
        'shape': 'object',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    # F7.5: the `rip` levels, measured 2026-11-02. `rip` declares no `router_id`, no `area` and no
    # `neighbor`, so it has no area row and no choice row outside `default_route`. The two `auth_profile`
    # rows state the `sensitive` decision only, because no parse method reads an auth profile body
    # (`backlog.md`, F7.7).
    'protocol/rip': {
        'shape': 'object',
        'fields': {'enable': 'bool', 'allow_redist_default_route': 'bool',
                   'reject_default_route': 'bool', 'timers': 'object', 'global_bfd': 'object',
                   'interfaces': 'string_list', 'export_rules': 'string_list',
                   'auth_profile': 'string_list'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/rip/timers': {
        'shape': 'object',
        'fields': {'interval_seconds': 'number', 'update_intervals': 'number',
                   'expire_intervals': 'number', 'delete_intervals': 'number'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/rip/global_bfd': {
        'shape': 'object',
        'fields': {'profile': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/rip/interfaces': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'enable': 'bool', 'mode': 'string', 'authentication': 'string',
                   'bfd': 'object', 'default_route': 'one_of'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/rip/interfaces/bfd': {
        'shape': 'object',
        'fields': {'profile': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    # `mode` is the string the export states, not a choice, so the row states no `selects` for it. Only the
    # `one_of` level states a choice, and `terraform validate` requires exactly one of its keys.
    'protocol/rip/interfaces/default_route': {
        'shape': 'one_of',
        'fields': {},
        'selects': {'advertise': 'advertise', 'no': 'disable'},
        'sensitive': frozenset(),
    },
    'protocol/rip/interfaces/default_route/advertise': {
        'shape': 'object',
        'fields': {'metric': 'number'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/rip/interfaces/default_route/disable': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/rip/export_rules': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'metric': 'number'},
        'selects': {},
        'sensitive': frozenset(),
    },
    # F7.7: the same two shapes as the `ospf` rows, read by `parse_rip`.
    'protocol/rip/auth_profile': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'password': 'string', 'md5': 'string_list'},
        'selects': {},
        'sensitive': frozenset({'password'}),
    },
    'protocol/rip/auth_profile/md5': {
        'shape': 'string_list',
        'fields': {'name': 'string', 'key': 'string', 'preferred': 'bool'},
        'selects': {},
        'sensitive': frozenset({'key'}),
    },
    # F7.6: the `policy` levels `parse_bgp` reads, measured 2026-11-02 against the pinned provider 2.0.14.
    'protocol/bgp/policy': {
        'shape': 'object',
        'fields': {
            'aggregation': 'object', 'conditional_advertisement': 'object', 'export': 'object',
            'import': 'object',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation': {
        'shape': 'object',
        'fields': {'address': 'string_list'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address': {
        'shape': 'string_list',
        'fields': {
            'advertise_filters': 'string_list', 'aggregate_route_attributes': 'object',
            'as_set': 'bool', 'enable': 'bool', 'name': 'string', 'prefix': 'string',
            'summary': 'bool', 'suppress_filters': 'string_list',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/advertise_filters': {
        'shape': 'string_list',
        'fields': {
            'enable': 'bool', 'match': 'object', 'name': 'string',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/advertise_filters/match': {
        'shape': 'object',
        'fields': {
            'address_prefix': 'string_list', 'as_path': 'object', 'community': 'object',
            'extended_community': 'object', 'from_peer': 'member_list', 'med': 'number',
            'nexthop': 'member_list', 'route_table': 'string',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/advertise_filters/match/address_prefix': {
        'shape': 'string_list',
        'fields': {'exact': 'bool', 'name': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/advertise_filters/match/as_path': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/advertise_filters/match/community': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/advertise_filters/match/extended_community': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/aggregate_route_attributes': {
        'shape': 'object',
        'fields': {
            'as_path': 'one_of', 'as_path_limit': 'number', 'community': 'one_of',
            'extended_community': 'one_of', 'local_preference': 'number', 'med': 'number',
            'nexthop': 'string', 'origin': 'string', 'weight': 'number',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/aggregate_route_attributes/as_path': {
        'shape': 'one_of',
        'fields': {'none': 'block', 'prepend': 'number'},
        'selects': {'none': 'none', 'prepend': 'prepend'},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/aggregate_route_attributes/as_path/none': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/aggregate_route_attributes/community': {
        'shape': 'one_of',
        'fields': {
            'append': 'member_list', 'none': 'block', 'overwrite': 'member_list',
            'remove_all': 'block', 'remove_regex': 'string',
        },
        'selects': { 'append': 'append', 'none': 'none', 'overwrite': 'overwrite',
                  'remove-all': 'remove_all',
                  'remove-regex': 'remove_regex'},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/aggregate_route_attributes/community/none': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/aggregate_route_attributes/community/remove_all': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/aggregate_route_attributes/extended_community': {
        'shape': 'one_of',
        'fields': {
            'append': 'member_list', 'none': 'block', 'overwrite': 'member_list',
            'remove_all': 'block', 'remove_regex': 'string',
        },
        'selects': { 'append': 'append', 'none': 'none', 'overwrite': 'overwrite',
                  'remove-all': 'remove_all',
                  'remove-regex': 'remove_regex'},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/aggregate_route_attributes/extended_community/none': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/aggregate_route_attributes/extended_community/remove_all': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/suppress_filters': {
        'shape': 'string_list',
        'fields': {
            'enable': 'bool', 'match': 'object', 'name': 'string',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/suppress_filters/match': {
        'shape': 'object',
        'fields': {
            'address_prefix': 'string_list', 'as_path': 'object', 'community': 'object',
            'extended_community': 'object', 'from_peer': 'member_list', 'med': 'number',
            'nexthop': 'member_list', 'route_table': 'string',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/suppress_filters/match/address_prefix': {
        'shape': 'string_list',
        'fields': {'exact': 'bool', 'name': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/suppress_filters/match/as_path': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/suppress_filters/match/community': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/aggregation/address/suppress_filters/match/extended_community': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/conditional_advertisement': {
        'shape': 'object',
        'fields': {'policy': 'string_list'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/conditional_advertisement/policy': {
        'shape': 'string_list',
        'fields': {
            'advertise_filters': 'string_list', 'enable': 'bool', 'name': 'string',
            'non_exist_filters': 'string_list', 'used_by': 'member_list',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/conditional_advertisement/policy/advertise_filters': {
        'shape': 'string_list',
        'fields': {
            'enable': 'bool', 'match': 'object', 'name': 'string',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/conditional_advertisement/policy/advertise_filters/match': {
        'shape': 'object',
        'fields': {
            'address_prefix': 'string_list', 'as_path': 'object', 'community': 'object',
            'extended_community': 'object', 'from_peer': 'member_list', 'med': 'number',
            'nexthop': 'member_list', 'route_table': 'string',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/conditional_advertisement/policy/advertise_filters/match/address_prefix': {
        'shape': 'string_list',
        'fields': {'name': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/conditional_advertisement/policy/advertise_filters/match/as_path': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/conditional_advertisement/policy/advertise_filters/match/community': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/conditional_advertisement/policy/advertise_filters/match/extended_community': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/conditional_advertisement/policy/non_exist_filters': {
        'shape': 'string_list',
        'fields': {
            'enable': 'bool', 'match': 'object', 'name': 'string',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/conditional_advertisement/policy/non_exist_filters/match': {
        'shape': 'object',
        'fields': {
            'address_prefix': 'string_list', 'as_path': 'object', 'community': 'object',
            'extended_community': 'object', 'from_peer': 'member_list', 'med': 'number',
            'nexthop': 'member_list', 'route_table': 'string',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/conditional_advertisement/policy/non_exist_filters/match/address_prefix': {
        'shape': 'string_list',
        'fields': {'name': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/conditional_advertisement/policy/non_exist_filters/match/as_path': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/conditional_advertisement/policy/non_exist_filters/match/community': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/conditional_advertisement/policy/non_exist_filters/match/extended_community': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export': {
        'shape': 'object',
        'fields': {'rules': 'string_list'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules': {
        'shape': 'string_list',
        'fields': {
            'action': 'one_of', 'enable': 'bool', 'match': 'object', 'name': 'string',
            'used_by': 'member_list',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/action': {
        'shape': 'one_of',
        'fields': {},
        'selects': {'allow': 'allow', 'deny': 'deny'},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/action/allow': {
        'shape': 'object',
        'fields': {'update': 'object'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/action/allow/update': {
        'shape': 'object',
        'fields': {
            'as_path': 'one_of', 'as_path_limit': 'number', 'community': 'one_of',
            'extended_community': 'one_of', 'local_preference': 'number', 'med': 'number',
            'nexthop': 'string', 'origin': 'string',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/action/allow/update/as_path': {
        'shape': 'one_of',
        'fields': {
            'none': 'block', 'prepend': 'number', 'remove': 'block',
            'remove_and_prepend': 'number',
        },
        'selects': { 'none': 'none', 'prepend': 'prepend', 'remove': 'remove',
                  'remove-and-prepend': 'remove_and_prepend'},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/action/allow/update/as_path/none': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/action/allow/update/as_path/remove': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/action/allow/update/community': {
        'shape': 'one_of',
        'fields': {
            'append': 'member_list', 'none': 'block', 'overwrite': 'member_list',
            'remove_all': 'block', 'remove_regex': 'string',
        },
        'selects': { 'append': 'append', 'none': 'none', 'overwrite': 'overwrite',
                  'remove-all': 'remove_all',
                  'remove-regex': 'remove_regex'},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/action/allow/update/community/none': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/action/allow/update/community/remove_all': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/action/allow/update/extended_community': {
        'shape': 'one_of',
        'fields': {
            'append': 'member_list', 'none': 'block', 'overwrite': 'member_list',
            'remove_all': 'block', 'remove_regex': 'string',
        },
        'selects': { 'append': 'append', 'none': 'none', 'overwrite': 'overwrite',
                  'remove-all': 'remove_all',
                  'remove-regex': 'remove_regex'},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/action/allow/update/extended_community/none': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/action/allow/update/extended_community/remove_all': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/action/deny': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/match': {
        'shape': 'object',
        'fields': {
            'address_prefix': 'string_list', 'as_path': 'object', 'community': 'object',
            'extended_community': 'object', 'from_peer': 'member_list', 'med': 'number',
            'nexthop': 'member_list', 'route_table': 'string',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/match/address_prefix': {
        'shape': 'string_list',
        'fields': {'exact': 'bool', 'name': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/match/as_path': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/match/community': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/export/rules/match/extended_community': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import': {
        'shape': 'object',
        'fields': {'rules': 'string_list'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules': {
        'shape': 'string_list',
        'fields': {
            'action': 'one_of', 'enable': 'bool', 'match': 'object', 'name': 'string',
            'used_by': 'member_list',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/action': {
        'shape': 'one_of',
        'fields': {},
        'selects': {'allow': 'allow', 'deny': 'deny'},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/action/allow': {
        'shape': 'object',
        'fields': {'dampening': 'string', 'update': 'object'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/action/allow/update': {
        'shape': 'object',
        'fields': {
            'as_path': 'one_of', 'as_path_limit': 'number', 'community': 'one_of',
            'extended_community': 'one_of', 'local_preference': 'number', 'med': 'number',
            'nexthop': 'string', 'origin': 'string', 'weight': 'number',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/action/allow/update/as_path': {
        'shape': 'one_of',
        'fields': {'none': 'block', 'remove': 'block'},
        'selects': { 'none': 'none', 'remove': 'remove'},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/action/allow/update/as_path/none': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/action/allow/update/as_path/remove': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/action/allow/update/community': {
        'shape': 'one_of',
        'fields': {
            'append': 'member_list', 'none': 'block', 'overwrite': 'member_list',
            'remove_all': 'block', 'remove_regex': 'string',
        },
        'selects': { 'append': 'append', 'none': 'none', 'overwrite': 'overwrite',
                  'remove-all': 'remove_all',
                  'remove-regex': 'remove_regex'},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/action/allow/update/community/none': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/action/allow/update/community/remove_all': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/action/allow/update/extended_community': {
        'shape': 'one_of',
        'fields': {
            'append': 'member_list', 'none': 'block', 'overwrite': 'member_list',
            'remove_all': 'block', 'remove_regex': 'string',
        },
        'selects': { 'append': 'append', 'none': 'none', 'overwrite': 'overwrite',
                  'remove-all': 'remove_all',
                  'remove-regex': 'remove_regex'},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/action/allow/update/extended_community/none': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/action/allow/update/extended_community/remove_all': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/action/deny': {
        'shape': 'block',
        'fields': {},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/match': {
        'shape': 'object',
        'fields': {
            'address_prefix': 'string_list', 'as_path': 'object', 'community': 'object',
            'extended_community': 'object', 'from_peer': 'member_list', 'med': 'number',
            'nexthop': 'member_list', 'route_table': 'string',
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/match/address_prefix': {
        'shape': 'string_list',
        'fields': {'exact': 'bool', 'name': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/match/as_path': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/match/community': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
    'protocol/bgp/policy/import/rules/match/extended_community': {
        'shape': 'object',
        'fields': {'regex': 'string'},
        'selects': {},
        'sensitive': frozenset(),
    },
}

# F7.8: the six filter containers sit outside the `protocol` object, so their shape is its own table.
# One row per level, and each row is the shape the pinned provider (2.0.14) declares for it, read through
# `terraform providers schema -json` and pinned by tests/test_filter_containers.py.
#
# The container row is the level the resource block prints, so its `fields` are the properties the
# `COVERAGE_MATRIX` row declares for that resource. `selects` is empty for every row: the provider declares
# each choice level as optional fields, not as required-exactly-one, so `one_of` is not the word for it.
# `sensitive` is empty: no filter field is marked sensitive in the schema, so `VALUE_VARIABLES` gains no row.
#
# The redistribution route-map entry is mirrored to the `match` and `set` levels, and those rows state leaf
# fields only: the levels inside them (`match.ipv4.address`, `match.next_hop`, `match.route_source`,
# `set.metric`, `set.ipv4`, `set.ipv6`) are not read or printed, and they are recorded in backlog.md.
FILTER_SHAPE: dict[str, dict] = {
    # network/routing-profile/filters/access-list (panos_filters_access_list_routing_profile)
    'network/routing-profile/filters/access-list': {
        'shape': 'object',
        'fields': {
        'description': 'string', 'name': 'string', 'type': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/access-list/type': {
        'shape': 'object',
        'fields': {
        'ipv4': 'object', 'ipv6': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/access-list/type/ipv4': {
        'shape': 'object',
        'fields': {
        'ipv4_entries': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/access-list/type/ipv4/ipv4_entries': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'destination_address': 'object', 'name': 'string', 'source_address': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/access-list/type/ipv4/ipv4_entries/destination_address': {
        'shape': 'object',
        'fields': {
        'address': 'string', 'entry': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/access-list/type/ipv4/ipv4_entries/destination_address/entry': {
        'shape': 'object',
        'fields': {
        'address': 'string', 'wildcard': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/access-list/type/ipv4/ipv4_entries/source_address': {
        'shape': 'object',
        'fields': {
        'address': 'string', 'entry': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/access-list/type/ipv4/ipv4_entries/source_address/entry': {
        'shape': 'object',
        'fields': {
        'address': 'string', 'wildcard': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/access-list/type/ipv6': {
        'shape': 'object',
        'fields': {
        'ipv6_entries': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/access-list/type/ipv6/ipv6_entries': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'name': 'string', 'source_address': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/access-list/type/ipv6/ipv6_entries/source_address': {
        'shape': 'object',
        'fields': {
        'address': 'string', 'entry': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/access-list/type/ipv6/ipv6_entries/source_address/entry': {
        'shape': 'object',
        'fields': {
        'address': 'string', 'exact_match': 'bool'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    # network/routing-profile/filters/as-path-access-list (panos_filters_as_path_access_list_routing_profile)
    'network/routing-profile/filters/as-path-access-list': {
        'shape': 'object',
        'fields': {
        'aspath_entries': 'string_list', 'description': 'string', 'name': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/as-path-access-list/aspath_entries': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'aspath_regex': 'string', 'name': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    # network/routing-profile/filters/prefix-list (panos_filters_prefix_list_routing_profile)
    'network/routing-profile/filters/prefix-list': {
        'shape': 'object',
        'fields': {
        'description': 'string', 'name': 'string', 'type': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/prefix-list/type': {
        'shape': 'object',
        'fields': {
        'ipv4': 'object', 'ipv6': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/prefix-list/type/ipv4': {
        'shape': 'object',
        'fields': {
        'ipv4_entries': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/prefix-list/type/ipv4/ipv4_entries': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'name': 'string', 'prefix': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/prefix-list/type/ipv4/ipv4_entries/prefix': {
        'shape': 'object',
        'fields': {
        'entry': 'object', 'network': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/prefix-list/type/ipv4/ipv4_entries/prefix/entry': {
        'shape': 'object',
        'fields': {
        'greater_than_or_equal': 'number', 'less_than_or_equal': 'number', 'network': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/prefix-list/type/ipv6': {
        'shape': 'object',
        'fields': {
        'ipv6_entries': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/prefix-list/type/ipv6/ipv6_entries': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'name': 'string', 'prefix': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/prefix-list/type/ipv6/ipv6_entries/prefix': {
        'shape': 'object',
        'fields': {
        'entry': 'object', 'network': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/prefix-list/type/ipv6/ipv6_entries/prefix/entry': {
        'shape': 'object',
        'fields': {
        'greater_than_or_equal': 'number', 'less_than_or_equal': 'number', 'network': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    # network/routing-profile/filters/community-list (panos_filters_community_list_routing_profile)
    'network/routing-profile/filters/community-list': {
        'shape': 'object',
        'fields': {
        'description': 'string', 'name': 'string', 'type': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/community-list/type': {
        'shape': 'object',
        'fields': {
        'extended': 'object', 'large': 'object', 'regular': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/community-list/type/extended': {
        'shape': 'object',
        'fields': {
        'extended_entries': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/community-list/type/extended/extended_entries': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'extended_community_regexes': 'member_list', 'name': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/community-list/type/large': {
        'shape': 'object',
        'fields': {
        'large_entries': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/community-list/type/large/large_entries': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'large_community_regexes': 'member_list', 'name': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/community-list/type/regular': {
        'shape': 'object',
        'fields': {
        'regular_entries': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/community-list/type/regular/regular_entries': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'communities': 'member_list', 'name': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    # network/routing-profile/filters/route-maps/bgp/bgp-entry (panos_filters_bgp_route_map_routing_profile)
    'network/routing-profile/filters/route-maps/bgp/bgp-entry': {
        'shape': 'object',
        'fields': {
        'description': 'string', 'name': 'string', 'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/bgp/bgp-entry/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/bgp/bgp-entry/route_map/match': {
        'shape': 'object',
        'fields': {
        'as_path_access_list': 'string', 'extended_community': 'string', 'interface': 'string', 'ipv4': 'object',
        'ipv6': 'object', 'large_community': 'string', 'local_preference': 'number', 'metric': 'number',
        'origin': 'string', 'peer': 'string', 'regular_community': 'string', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/bgp/bgp-entry/route_map/match/ipv4': {
        'shape': 'object',
        'fields': {
        'address': 'object', 'next_hop': 'object', 'route_source': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/bgp/bgp-entry/route_map/match/ipv4/address': {
        'shape': 'object',
        'fields': {
        'access_list': 'string', 'prefix_list': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/bgp/bgp-entry/route_map/match/ipv4/next_hop': {
        'shape': 'object',
        'fields': {
        'access_list': 'string', 'prefix_list': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/bgp/bgp-entry/route_map/match/ipv4/route_source': {
        'shape': 'object',
        'fields': {
        'access_list': 'string', 'prefix_list': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/bgp/bgp-entry/route_map/match/ipv6': {
        'shape': 'object',
        'fields': {
        'address': 'object', 'next_hop': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/bgp/bgp-entry/route_map/match/ipv6/address': {
        'shape': 'object',
        'fields': {
        'access_list': 'string', 'prefix_list': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/bgp/bgp-entry/route_map/match/ipv6/next_hop': {
        'shape': 'object',
        'fields': {
        'access_list': 'string', 'prefix_list': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/bgp/bgp-entry/route_map/set': {
        'shape': 'object',
        'fields': {
        'aggregator': 'object', 'aspath_exclude': 'member_list', 'aspath_prepend': 'member_list',
        'atomic_aggregate': 'bool', 'extended_community': 'member_list', 'ipv4': 'object', 'ipv6': 'object',
        'ipv6_nexthop_prefer_global': 'bool', 'large_community': 'member_list', 'local_preference': 'number',
        'metric': 'object', 'origin': 'string', 'originator_id': 'string', 'overwrite_large_community': 'bool',
        'overwrite_regular_community': 'bool', 'regular_community': 'member_list', 'remove_large_community': 'string',
        'remove_regular_community': 'string', 'tag': 'number', 'weight': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/bgp/bgp-entry/route_map/set/aggregator': {
        'shape': 'object',
        'fields': {
        'as': 'number', 'router_id': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/bgp/bgp-entry/route_map/set/ipv4': {
        'shape': 'object',
        'fields': {
        'next_hop': 'string', 'source_address': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/bgp/bgp-entry/route_map/set/ipv6': {
        'shape': 'object',
        'fields': {
        'next_hop': 'string', 'source_address': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/bgp/bgp-entry/route_map/set/metric': {
        'shape': 'object',
        'fields': {
        'action': 'string', 'value': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    # network/routing-profile/filters/route-maps/redistribution/redist-entry
    # (panos_filters_route_maps_redistribution_routing_profile)
    'network/routing-profile/filters/route-maps/redistribution/redist-entry': {
        'shape': 'object',
        'fields': {
        'bgp': 'object', 'connected_static': 'object', 'description': 'string', 'name': 'string', 'ospf': 'object',
        'ospfv3': 'object', 'rip': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp': {
        'shape': 'object',
        'fields': {
        'ospf': 'object', 'ospfv3': 'object', 'rib': 'object', 'rip': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp/ospf': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp/ospf/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp/ospf/route_map/match': {
        'shape': 'object',
        'fields': {
        'as_path_access_list': 'string', 'extended_communities': 'string', 'interface': 'string',
        'large_communities': 'string', 'local_preference': 'number', 'metric': 'number', 'origin': 'string',
        'peer': 'string', 'regular_communities': 'string', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp/ospf/route_map/set': {
        'shape': 'object',
        'fields': {
        'metric_type': 'string', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp/ospfv3': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp/ospfv3/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp/ospfv3/route_map/match': {
        'shape': 'object',
        'fields': {
        'as_path_access_list': 'string', 'extended_communities': 'string', 'interface': 'string',
        'large_communities': 'string', 'local_preference': 'number', 'metric': 'number', 'origin': 'string',
        'peer': 'string', 'regular_communities': 'string', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp/ospfv3/route_map/set': {
        'shape': 'object',
        'fields': {
        'metric_type': 'string', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp/rib': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp/rib/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp/rib/route_map/match': {
        'shape': 'object',
        'fields': {
        'as_path_access_list': 'string', 'extended_communities': 'string', 'interface': 'string',
        'large_communities': 'string', 'local_preference': 'number', 'metric': 'number', 'origin': 'string',
        'peer': 'string', 'regular_communities': 'string', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp/rib/route_map/set': {
        'shape': 'object',
        'fields': {
        'source_address': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp/rip': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp/rip/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp/rip/route_map/match': {
        'shape': 'object',
        'fields': {
        'as_path_access_list': 'string', 'extended_communities': 'string', 'interface': 'string',
        'large_communities': 'string', 'local_preference': 'number', 'metric': 'number', 'origin': 'string',
        'peer': 'string', 'regular_communities': 'string', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp/rip/route_map/set': {
        'shape': 'object',
        'fields': {
        'next_hop': 'string', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static': {
        'shape': 'object',
        'fields': {
        'bgp': 'object', 'ospf': 'object', 'ospfv3': 'object', 'rib': 'object', 'rip': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/bgp': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/bgp/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/bgp/route_map/match': {
        'shape': 'object',
        'fields': {
        'interface': 'string', 'metric': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/bgp/route_map/set': {
        'shape': 'object',
        'fields': {
        'aspath_prepends': 'member_list', 'atomic_aggregate': 'bool', 'extended_communities': 'member_list',
        'large_communities': 'member_list', 'local_preference': 'number', 'origin': 'string',
        'originator_id': 'string', 'regular_communities': 'member_list', 'tag': 'number', 'weight': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/ospf': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/ospf/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/ospf/route_map/match': {
        'shape': 'object',
        'fields': {
        'interface': 'string', 'metric': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/ospf/route_map/set': {
        'shape': 'object',
        'fields': {
        'metric_type': 'string', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/ospfv3': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/ospfv3/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/ospfv3/route_map/match': {
        'shape': 'object',
        'fields': {
        'interface': 'string', 'metric': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/ospfv3/route_map/set': {
        'shape': 'object',
        'fields': {
        'metric_type': 'string', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/rib': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/rib/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/rib/route_map/match': {
        'shape': 'object',
        'fields': {
        'interface': 'string', 'metric': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/rib/route_map/set': {
        'shape': 'object',
        'fields': {
        'source_address': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/rip': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/rip/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/rip/route_map/match': {
        'shape': 'object',
        'fields': {
        'interface': 'string', 'metric': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static/rip/route_map/set': {
        'shape': 'object',
        'fields': {
        'next_hop': 'string', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospf': {
        'shape': 'object',
        'fields': {
        'bgp': 'object', 'rib': 'object', 'rip': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospf/bgp': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospf/bgp/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospf/bgp/route_map/match': {
        'shape': 'object',
        'fields': {
        'interface': 'string', 'metric': 'number', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospf/bgp/route_map/set': {
        'shape': 'object',
        'fields': {
        'aspath_prepends': 'member_list', 'atomic_aggregate': 'bool', 'extended_communities': 'member_list',
        'large_communities': 'member_list', 'local_preference': 'number', 'origin': 'string',
        'originator_id': 'string', 'regular_communities': 'member_list', 'tag': 'number', 'weight': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospf/rib': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospf/rib/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospf/rib/route_map/match': {
        'shape': 'object',
        'fields': {
        'interface': 'string', 'metric': 'number', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospf/rib/route_map/set': {
        'shape': 'object',
        'fields': {
        'source_address': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospf/rip': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospf/rip/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospf/rip/route_map/match': {
        'shape': 'object',
        'fields': {
        'interface': 'string', 'metric': 'number', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospf/rip/route_map/set': {
        'shape': 'object',
        'fields': {
        'next_hop': 'string', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospfv3': {
        'shape': 'object',
        'fields': {
        'bgp': 'object', 'rib': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospfv3/bgp': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospfv3/bgp/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospfv3/bgp/route_map/match': {
        'shape': 'object',
        'fields': {
        'interface': 'string', 'metric': 'number', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospfv3/bgp/route_map/set': {
        'shape': 'object',
        'fields': {
        'aspath_prepends': 'member_list', 'atomic_aggregate': 'bool', 'extended_communities': 'member_list',
        'large_communities': 'member_list', 'local_preference': 'number', 'origin': 'string',
        'originator_id': 'string', 'regular_communities': 'member_list', 'tag': 'number', 'weight': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospfv3/rib': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospfv3/rib/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospfv3/rib/route_map/match': {
        'shape': 'object',
        'fields': {
        'interface': 'string', 'metric': 'number', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospfv3/rib/route_map/set': {
        'shape': 'object',
        'fields': {
        'source_address': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/rip': {
        'shape': 'object',
        'fields': {
        'bgp': 'object', 'ospf': 'object', 'rib': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/rip/bgp': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/rip/bgp/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/rip/bgp/route_map/match': {
        'shape': 'object',
        'fields': {
        'interface': 'string', 'metric': 'number', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/rip/bgp/route_map/set': {
        'shape': 'object',
        'fields': {
        'aspath_prepends': 'member_list', 'atomic_aggregate': 'bool', 'extended_communities': 'member_list',
        'large_communities': 'member_list', 'local_preference': 'number', 'origin': 'string',
        'originator_id': 'string', 'regular_communities': 'member_list', 'tag': 'number', 'weight': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/rip/ospf': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/rip/ospf/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/rip/ospf/route_map/match': {
        'shape': 'object',
        'fields': {
        'interface': 'string', 'metric': 'number', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/rip/ospf/route_map/set': {
        'shape': 'object',
        'fields': {
        'metric_type': 'string', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/rip/rib': {
        'shape': 'object',
        'fields': {
        'route_map': 'string_list'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/rip/rib/route_map': {
        'shape': 'string_list',
        'fields': {
        'action': 'string', 'description': 'string', 'match': 'object', 'name': 'string', 'set': 'object'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/rip/rib/route_map/match': {
        'shape': 'object',
        'fields': {
        'interface': 'string', 'metric': 'number', 'tag': 'number'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/rip/rib/route_map/set': {
        'shape': 'object',
        'fields': {
        'source_address': 'string'
        },
        'selects': {},
        'sensitive': frozenset(),
    },
}

# The provider type each filter container row names, which the emitter and the gate both need. It is the
# same fact `CONTAINER_TABLE` states in the row note, so tests/test_filter_containers.py pins the two
# against each other instead of letting this be a second decision.
FILTER_TYPES = {
    'network/routing-profile/filters/access-list': 'panos_filters_access_list_routing_profile',
    'network/routing-profile/filters/as-path-access-list': 'panos_filters_as_path_access_list_routing_profile',
    'network/routing-profile/filters/prefix-list': 'panos_filters_prefix_list_routing_profile',
    'network/routing-profile/filters/community-list': 'panos_filters_community_list_routing_profile',
    'network/routing-profile/filters/route-maps/bgp/bgp-entry': 'panos_filters_bgp_route_map_routing_profile',
    'network/routing-profile/filters/route-maps/redistribution/redist-entry':
        'panos_filters_route_maps_redistribution_routing_profile',
}

# The six filter containers: the entry rows of `FILTER_SHAPE`, which are the keys of `FILTER_TYPES` and the
# paths `CONTAINER_TABLE` names.
FILTER_PATHS = tuple(sorted(FILTER_TYPES))


def filter_row(path: str) -> Optional[dict]:
    """The shape row for one filter level. None when the table states no shape for the level."""
    return FILTER_SHAPE.get(path)


def filter_path(resource: str) -> Optional[str]:
    """The container path a filter resource type belongs to (`FILTER_TYPES`, read the other way)."""
    for path, name in FILTER_TYPES.items():
        if name == resource:
            return path
    return None


# The input spellings `ShapeTable.xml_name` cannot produce, keyed by the container path, because one
# provider field name spells two ways in the input: `extended_communities` is `ec-regex` inside a
# community-list entry and `extended-community` inside a route-map match. An entry-list field is the
# singular container element that holds the entries, so those fields are here too.
FILTER_XML_NAME_EXCEPTIONS = {
    'network/routing-profile/filters/access-list': {'ipv4_entries': 'ipv4-entry', 'ipv6_entries': 'ipv6-entry'},
    'network/routing-profile/filters/as-path-access-list': {'aspath_entries': 'aspath-entry'},
    'network/routing-profile/filters/prefix-list': {'ipv4_entries': 'ipv4-entry', 'ipv6_entries': 'ipv6-entry'},
    'network/routing-profile/filters/community-list': {
        'extended_entries': 'extended-entry', 'large_entries': 'large-entry',
        'regular_entries': 'regular-entry', 'communities': 'community',
        'extended_community_regexes': 'ec-regex', 'large_community_regexes': 'lc-regex'},
    'network/routing-profile/filters/route-maps/redistribution/redist-entry': {
        'extended_communities': 'extended-community', 'large_communities': 'large-community',
        'regular_communities': 'regular-community', 'aspath_prepends': 'aspath-prepend'},
}


class ShapeTable:
    """One shape table: its rows, and the input spellings the field-name rule cannot produce.

    The reader, the printer and the gate rule walk a level through this object, so no method writes a
    field name of its own (F7.1 rule): the table is the only shape owner. `exceptions` is the spelling map
    for this table, keyed by the container path, because one provider field name can spell two ways in the
    input (F7.8). `xml_name` is the one rule that turns a table name into the tag the input spells.
    """

    def __init__(self, name: str, rows: dict, exceptions: Optional[dict] = None,
                 word: str = 'shape', rule: str = 'shape_blocks'):
        self.name = name
        self.rows = rows
        self.exceptions = exceptions or {}
        # `word` is the word a finding uses for the table's levels, and `rule` is the gate rule that reports
        # them, so the one reader can serve both tables without naming either one.
        self.word = word
        self.rule = rule

    def row(self, path: str) -> Optional[dict]:
        return self.rows.get(path)

    @staticmethod
    def field_name(path: str) -> str:
        """The field the path names, which is the last part of the path (F7.1)."""
        return path.rsplit('/', 1)[-1]

    def xml_name(self, field: str, path: str = '') -> str:
        """The element name for a field name: `_` becomes `-`, with this table's exceptions."""
        for container, words in self.exceptions.items():
            if path == container or path.startswith(container + '/'):
                word = words.get(field)
                if word:
                    return word
        return XML_NAME_EXCEPTIONS.get(field, field.replace('_', '-'))


# The two shape tables as the reader, the printer and the gate rule see them.
PROTOCOL_TABLE = ShapeTable('PROTOCOL_SHAPE', PROTOCOL_SHAPE, word='protocol', rule='protocol_object')
FILTER_TABLE = ShapeTable('FILTER_SHAPE', FILTER_SHAPE, FILTER_XML_NAME_EXCEPTIONS, 'filter', 'filter_blocks')


def protocol_row(path: str) -> Optional[dict]:
    """The shape row for one protocol path. None when the table states no shape for the level."""
    return PROTOCOL_SHAPE.get(path)

# PAN-OS config types with no v2 provider resource. The converter keeps
# the data visible in the manual setup report instead of emitting it.
REPORT_ONLY_TYPES = frozenset({
    # v2 panos_application is a single static application object; an
    # application filter (category/subcategory/technology/risk lists) is
    # a different concept with no v2 resource.
    'panos_application_filter',
    # F7.1: BGP and OSPF data is printed as the `protocol` object attribute on `panos_virtual_router`, so
    # these six types no longer have a report row. The provider has no separate resource for a peer group,
    # a peer, an area, or an area interface, and an OSPF interface outside an area has no field, so F4.3
    # rule 3 keeps a name reference on its parent row and the manual report names what no field can
    # express.
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
#                  entry name and the five scope facts are the row identity,
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
        # F7.1: the emitter reads the protocol fields through `PROTOCOL_SHAPE`, so the measured set is the
        # fields the table declares for the levels this row covers plus the reads `generate_virtual_routers`
        # states on its own. A level dict the parse builds is not a recorded object, so a field the table
        # declares for the `bgp` and `ospf` levels is grounded by the table, not by the measurement: the
        # emitter test in tests/test_coverage_matrix.py covers those, and the limit is in backlog.md.
        # F7.3: an export rule is an entry, so the scan measures its fields, and `new_path_type` and `new_tag`
        # join the measured set through `tests/fixtures/ospfv3.xml`. The three single-object levels hold no
        # entry, so they stay grounded by the table.
        # F7.4: `virtual_link` is a field of the area entry, which this row covers, so the scan measures it.
        # The levels inside an entry are not in the scan scope, so `neighbor` and the fields of a
        # `nssa_ext_range` entry stay grounded by the table.
        # F7.5: `authentication`, `bfd`, `default_route` and `mode` join the measured set through a `rip`
        # interface entry, which this row covers. `bfd` is measured as the field of the entry, not as the
        # level inside it, because the level dict the parse builds is not a recorded object.
        # F7.6: the four policy entry levels this row covers join the measured set. A policy level inside an
        # entry is not in the scan scope, so its fields stay grounded by the table, and a member list is read
        # as the field of the entry that holds it.
        # F7.7: an auth profile entry is in the scan scope, so its fields join the measured set. The levels
        # inside it (`md5`, `ah`, `esp`) are read as the fields of the entry that holds them, and an `md5` entry
        # inside a profile entry is not in the scan scope, so `key` stays grounded by the table.
        'properties': ('action', 'address_family_identifier', 'advertise_filters',
                       'aggregate_route_attributes', 'ah', 'as_set', 'authentication', 'bfd',
                       'default_route', 'enable', 'esp', 'interface', 'interfaces',
                       'local_address', 'match', 'md5', 'metric', 'mode', 'new_path_type', 'new_tag',
                       'non_exist_filters', 'password', 'peer', 'peer_address', 'peer_as', 'prefix', 'protocol',
                       'range', 'router_type', 'secret', 'spi', 'static_routes', 'summary',
                       'suppress_filters', 'type', 'used_by', 'virtual_link',),
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
        # `template_stack` is a scope fact (F6.10.5), so the row lists no property for it: the
        # emitter reads it to choose the location sub-block, and the fact is part of the row identity
        # (`entry_coverage.NON_FIELD_KEYS`). The value prints as a literal, because the block is the
        # PAN-OS variable and the tool cannot know which values a module takes as parameters
        # (§9 rule 2).
        'resource': 'panos_template_variable',
        'xml_element': 'variable/entry',
        'xml_name': 'edge-tag',
        'emitted_name': 'edge-tag',
        'fixture': 'scope_objects.xml',
        'output_file': 'scope.tf',
        'emitter': ('generate_scope_objects',),
        'properties': ('description', 'type'),
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
    },

    {
        'resource': 'panos_filters_access_list_routing_profile',
        'xml_element': 'network/routing-profile/filters/access-list/entry',
        'xml_name': 'ACL-Filter',
        'emitted_name': 'ACL-Filter',
        'fixture': 'filter_containers.xml',
        'output_file': 'filters.tf',
        'emitter': ('generate_filter_containers',),
        # F7.8: the emitter prints the fields the entry row states, so the properties are the
        # entry row's fields without the entry name, and the scan measures them through the fixture.
        'properties': ('description', 'type'),
    },
    {
        'resource': 'panos_filters_as_path_access_list_routing_profile',
        'xml_element': 'network/routing-profile/filters/as-path-access-list/entry',
        'xml_name': 'ASPath-Filter',
        'emitted_name': 'ASPath-Filter',
        'fixture': 'filter_containers.xml',
        'output_file': 'filters.tf',
        'emitter': ('generate_filter_containers',),
        # F7.8: the emitter prints the fields the entry row states, so the properties are the
        # entry row's fields without the entry name, and the scan measures them through the fixture.
        'properties': ('aspath_entries', 'description'),
    },
    {
        'resource': 'panos_filters_prefix_list_routing_profile',
        'xml_element': 'network/routing-profile/filters/prefix-list/entry',
        'xml_name': 'Prefix-Filter',
        'emitted_name': 'Prefix-Filter',
        'fixture': 'filter_containers.xml',
        'output_file': 'filters.tf',
        'emitter': ('generate_filter_containers',),
        # F7.8: the emitter prints the fields the entry row states, so the properties are the
        # entry row's fields without the entry name, and the scan measures them through the fixture.
        'properties': ('description', 'type'),
    },
    {
        'resource': 'panos_filters_community_list_routing_profile',
        'xml_element': 'network/routing-profile/filters/community-list/entry',
        'xml_name': 'Community-Filter',
        'emitted_name': 'Community-Filter',
        'fixture': 'filter_containers.xml',
        'output_file': 'filters.tf',
        'emitter': ('generate_filter_containers',),
        # F7.8: the emitter prints the fields the entry row states, so the properties are the
        # entry row's fields without the entry name, and the scan measures them through the fixture.
        'properties': ('description', 'type'),
    },
    {
        'resource': 'panos_filters_bgp_route_map_routing_profile',
        'xml_element': 'network/routing-profile/filters/route-maps/bgp/bgp-entry/entry',
        'xml_name': 'RouteMap-Filter',
        'emitted_name': 'RouteMap-Filter',
        'fixture': 'filter_containers.xml',
        'output_file': 'filters.tf',
        'emitter': ('generate_filter_containers',),
        # F7.8: the emitter prints the fields the entry row states, so the properties are the
        # entry row's fields without the entry name, and the scan measures them through the fixture.
        'properties': ('description', 'route_map'),
    },
    {
        'resource': 'panos_filters_route_maps_redistribution_routing_profile',
        'xml_element': 'network/routing-profile/filters/route-maps/redistribution/redist-entry/entry',
        'xml_name': 'Redist-Filter',
        'emitted_name': 'Redist-Filter',
        'fixture': 'filter_containers.xml',
        'output_file': 'filters.tf',
        'emitter': ('generate_filter_containers',),
        # F7.8: the emitter prints the fields the entry row states, so the properties are the
        # entry row's fields without the entry name, and the scan measures them through the fixture.
        'properties': ('bgp', 'connected_static', 'description', 'ospf', 'ospfv3', 'rip'),
    },
)

