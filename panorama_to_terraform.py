#!/usr/bin/env python3
"""
Palo Alto Panorama to Terraform Converter

Copyright (c) 2025 GSW Systems

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

COMMERCIAL LICENSE AVAILABLE
For use in proprietary applications without AGPL v3 obligations,
contact sales@gswsystems.com for commercial licensing options.
See LICENSE-COMMERCIAL for details.

═══════════════════════════════════════════════════════════════════════

This script parses Palo Alto Panorama server output (XML format) and converts it
into Terraform configuration files that can be used to configure replacement devices.

Supports:
- Device Groups
- Security Policies
- NAT Policies
- Address Objects
- Address Groups
- Service Objects
- Service Groups
- Zones
- Interfaces
- Virtual Routers
- And many more (36 object types total)

Usage:
    python panorama_to_terraform.py <input_file.xml> [--output-dir <dir>]
"""

import argparse
import hashlib
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional


class PanoramaParser:
    """Parse Palo Alto Panorama XML configuration"""

    def __init__(self, xml_file: str):
        self.xml_file = xml_file
        # Panorama exports never contain a DTD. Reject one before parsing:
        # ElementTree resolves internal entities, so a deep entity chain
        # ("billion laughs") is a memory DoS, and external entities are an
        # XXE vector. A DTD is the only way either reaches the parser.
        raw = Path(xml_file).read_text(encoding='utf-8', errors='replace')
        if re.search(r'<!DOCTYPE', raw, re.IGNORECASE):
            raise ValueError('input contains a DTD, which Panorama exports never include')
        self.tree = ET.parse(xml_file)
        self.root = self.tree.getroot()
        # ElementTree has no parent pointers; build a child -> parent map so
        # parse methods can find the enclosing device group of an entry (F2.3).
        self._parent_map = {child: parent for parent in self.root.iter() for child in parent}

    def parse_device_groups(self) -> list[dict]:
        """Parse device groups from Panorama config"""
        device_groups = []

        # Find device-group elements
        for dg in self.root.findall(".//device-group/entry"):
            name = dg.get('name')
            if name:
                device_groups.append({
                    'name': name,
                    'description': self._get_text(dg, 'description')
                })

        return device_groups

    def device_group_of(self, elem: ET.Element) -> str:
        """Return the name of the device group that defines elem (F2.3).

        An entry under a <device-group><entry> belongs to that group. An
        entry under <shared> or at the top level belongs to the shared
        device group, which PAN-OS names "Shared".
        """
        node = elem
        while node is not None:
            parent = self._parent_map.get(node)
            if parent is not None and parent.tag == 'device-group' and node.tag == 'entry':
                return node.get('name') or 'Shared'
            if node.tag == 'shared':
                return 'Shared'
            node = parent
        return 'Shared'

    def parse_tags(self) -> list[dict]:
        """Parse tags"""
        tags = []
        seen_names = set()

        paths = [
            ".//tag/entry",
            ".//device-group/entry/tag/entry"
        ]

        for path in paths:
            for tag in self.root.findall(path):
                name = tag.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                tag_obj = {
                    'name': name,
                    'device_group': self.device_group_of(tag),
                    'color': self._get_text(tag, 'color'),
                    'comments': self._get_text(tag, 'comments')
                }

                tags.append(tag_obj)

        return tags

    def parse_regions(self) -> list[dict]:
        """Parse regions (geographic locations)"""
        regions = []
        seen_names = set()

        paths = [
            ".//region/entry",
            ".//device-group/entry/region/entry"
        ]

        for path in paths:
            for region in self.root.findall(path):
                name = region.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                addresses = []
                for addr in region.findall('.//address/member'):
                    if addr.text:
                        addresses.append(addr.text)

                region_obj = {
                    'name': name,
                    'addresses': addresses
                }

                regions.append(region_obj)

        return regions

    def parse_custom_url_categories(self) -> list[dict]:
        """Parse custom URL categories"""
        categories = []
        seen_names = set()

        paths = [
            ".//custom-url-category/entry",
            ".//device-group/entry/custom-url-category/entry"
        ]

        for path in paths:
            for cat in self.root.findall(path):
                name = cat.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                url_list = []
                for url in cat.findall('.//list/member'):
                    if url.text:
                        url_list.append(url.text)

                cat_obj = {
                    'name': name,
                    'device_group': self.device_group_of(cat),
                    'type': self._get_text(cat, 'type'),
                    'list': url_list,
                    'description': self._get_text(cat, 'description')
                }

                categories.append(cat_obj)

        return categories

    def parse_application_groups(self) -> list[dict]:
        """Parse application groups"""
        app_groups = []
        seen_names = set()

        paths = [
            ".//application-group/entry",
            ".//device-group/entry/application-group/entry"
        ]

        for path in paths:
            for ag in self.root.findall(path):
                name = ag.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                members = []
                for member in ag.findall('.//members/member'):
                    if member.text:
                        members.append(member.text)

                ag_obj = {
                    'name': name,
                    'device_group': self.device_group_of(ag),
                    'members': members
                }

                app_groups.append(ag_obj)

        return app_groups

    def parse_application_filters(self) -> list[dict]:
        """Parse application filters"""
        app_filters = []
        seen_names = set()

        paths = [
            ".//application-filter/entry",
            ".//device-group/entry/application-filter/entry"
        ]

        for path in paths:
            for af in self.root.findall(path):
                name = af.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                af_obj = {
                    'name': name,
                    'device_group': self.device_group_of(af),
                    'category': self._get_members(af, 'category'),
                    'subcategory': self._get_members(af, 'subcategory'),
                    'technology': self._get_members(af, 'technology'),
                    'risk': self._get_members(af, 'risk'),
                    'evasive': self._get_text(af, 'evasive'),
                    'excessive_bandwidth_use': self._get_text(af, 'excessive-bandwidth-use'),
                    'prone_to_misuse': self._get_text(af, 'prone-to-misuse'),
                    'is_saas': self._get_text(af, 'is-saas'),
                    'transfers_files': self._get_text(af, 'transfers-files'),
                    'tunnels_other_apps': self._get_text(af, 'tunnels-other-apps'),
                    'used_by_malware': self._get_text(af, 'used-by-malware'),
                }

                app_filters.append(af_obj)

        return app_filters

    def parse_external_lists(self) -> list[dict]:
        """Parse external dynamic lists"""
        ext_lists = []
        seen_names = set()

        paths = [
            ".//external-list/entry",
            ".//device-group/entry/external-list/entry"
        ]

        for path in paths:
            for ext_list in self.root.findall(path):
                name = ext_list.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                # Determine type
                list_type = None
                url = None
                recurring = None

                type_elem = ext_list.find('type')
                if type_elem is not None:
                    if type_elem.find('ip') is not None:
                        list_type = 'ip'
                        url = self._get_text(type_elem, 'ip/url')
                        # Check for recurring schedule
                        if type_elem.find('.//recurring/hourly') is not None:
                            recurring = 'hourly'
                        elif type_elem.find('.//recurring/five-minute') is not None:
                            recurring = 'five-minute'
                        elif type_elem.find('.//recurring/daily') is not None:
                            recurring = 'daily'
                    elif type_elem.find('domain') is not None:
                        list_type = 'domain'
                        url = self._get_text(type_elem, 'domain/url')
                        if type_elem.find('.//recurring/hourly') is not None:
                            recurring = 'hourly'
                        elif type_elem.find('.//recurring/five-minute') is not None:
                            recurring = 'five-minute'
                        elif type_elem.find('.//recurring/daily') is not None:
                            recurring = 'daily'
                    elif type_elem.find('url') is not None:
                        list_type = 'url'
                        url = self._get_text(type_elem, 'url/url')
                        if type_elem.find('.//recurring/hourly') is not None:
                            recurring = 'hourly'
                        elif type_elem.find('.//recurring/five-minute') is not None:
                            recurring = 'five-minute'
                        elif type_elem.find('.//recurring/daily') is not None:
                            recurring = 'daily'

                ext_list_obj = {
                    'name': name,
                    'device_group': self.device_group_of(ext_list),
                    'type': list_type,
                    'url': url,
                    'recurring': recurring,
                    'description': self._get_text(ext_list, 'description')
                }

                ext_lists.append(ext_list_obj)

        return ext_lists

    def parse_address_objects(self) -> list[dict]:
        """Parse address objects"""
        # Use dictionary to track objects by name, allowing overrides
        addresses_dict = {}

        # Parse in order: device groups first, then shared
        # This allows device-group definitions to override shared references
        paths = [
            ".//device-group/entry/address/entry",
            ".//shared/address/entry",
            ".//address/entry"
        ]

        for path in paths:
            for addr in self.root.findall(path):
                name = addr.get('name')
                if not name:
                    continue

                # Check if this is just a reference (only has <id> tag, no actual content)
                has_id_only = (addr.find('id') is not None and
                              addr.find('ip-netmask') is None and
                              addr.find('ip-range') is None and
                              addr.find('fqdn') is None and
                              addr.find('description') is None)

                if has_id_only:
                    # Skip reference-only entries
                    continue

                addr_obj = {'name': name, 'device_group': self.device_group_of(addr)}

                # Check for IP netmask
                ip_netmask = addr.find('ip-netmask')
                if ip_netmask is not None:
                    addr_obj['type'] = 'ip-netmask'
                    addr_obj['value'] = ip_netmask.text

                # Check for IP range
                ip_range = addr.find('ip-range')
                if ip_range is not None:
                    addr_obj['type'] = 'ip-range'
                    addr_obj['value'] = ip_range.text

                # IPv6 objects carry their prefix in a dedicated element
                # (the v2 provider stores any prefix in ip_netmask)
                ipv6 = addr.find('ipv6')
                if ipv6 is not None:
                    addr_obj['type'] = 'ipv6'
                    addr_obj['value'] = ipv6.text

                ipv6_range = addr.find('ipv6-range')
                if ipv6_range is not None:
                    addr_obj['type'] = 'ipv6-range'
                    addr_obj['value'] = ipv6_range.text

                # Check for FQDN
                fqdn = addr.find('fqdn')
                if fqdn is not None:
                    addr_obj['type'] = 'fqdn'
                    addr_obj['value'] = fqdn.text

                # Description
                desc = addr.find('description')
                if desc is not None:
                    addr_obj['description'] = desc.text

                # Tags
                tags = []
                tag_member = addr.findall('.//tag/member')
                for tag in tag_member:
                    if tag.text:
                        tags.append(tag.text)
                addr_obj['tags'] = tags

                # Only add/override if this entry has content (value defined)
                # OR if we haven't seen this name yet
                if ('value' in addr_obj or name not in addresses_dict):
                    addresses_dict[name] = addr_obj

        return list(addresses_dict.values())

    def parse_address_groups(self) -> list[dict]:
        """Parse address groups"""
        # Use dictionary to track groups by name, allowing overrides
        groups_dict = {}

        # Parse in order: device groups first, then shared
        # This allows device-group definitions to override shared references
        paths = [
            ".//device-group/entry/address-group/entry",
            ".//shared/address-group/entry",
            ".//address-group/entry"
        ]

        for path in paths:
            for grp in self.root.findall(path):
                name = grp.get('name')
                if not name:
                    continue

                # Check if this is just a reference (only has <id> tag, no actual content)
                # References are used in Panorama to inherit shared objects
                has_id_only = (grp.find('id') is not None and
                              grp.find('.//static') is None and
                              grp.find('.//dynamic') is None and
                              grp.find('description') is None)

                if has_id_only:
                    # Skip reference-only entries (they're just pointers to shared objects)
                    continue

                # Parse members
                members = []
                static_members = grp.findall('.//static/member')
                for member in static_members:
                    if member.text:
                        members.append(member.text)

                # v2 models the tag-based filter as a single expression string
                dynamic_filter = grp.find('.//dynamic/filter')
                filter_expr = self._dynamic_filter_expr(dynamic_filter) if dynamic_filter is not None else None

                group_obj = {
                    'name': name,
                    'device_group': self.device_group_of(grp),
                    'static_members': members,
                    'dynamic_filter': filter_expr,
                    'description': self._get_text(grp, 'description')
                }

                # Only add/override if this entry has content (members or dynamic filter)
                # OR if we haven't seen this name yet
                if (members or filter_expr or name not in groups_dict):
                    groups_dict[name] = group_obj

        return list(groups_dict.values())

    def _dynamic_filter_expr(self, filter_elem) -> str:
        """Serialize a PAN-OS dynamic address filter element to an expression.

        The export format nests the attribute and value elements:
            <filter><address><tag>web</tag></address></filter>
        The v2 provider takes a single tag-based filter string, so each
        attribute/value pair becomes 'attr == "value"' joined by 'and'.
        """
        parts = []
        for attr in filter_elem:
            for value_elem in attr:
                val = (value_elem.text or '').strip()
                if val:
                    parts.append(f'{value_elem.tag} == "{val}"')
        return ' and '.join(parts)

    def parse_service_objects(self) -> list[dict]:
        """Parse service objects"""
        # Use dictionary to track objects by name, allowing overrides
        services_dict = {}

        # Parse in order: device groups first, then shared
        paths = [
            ".//device-group/entry/service/entry",
            ".//shared/service/entry",
            ".//service/entry"
        ]

        for path in paths:
            for svc in self.root.findall(path):
                name = svc.get('name')
                if not name:
                    continue

                # Check if this is just a reference (only has <id> tag, no actual content)
                has_id_only = (svc.find('id') is not None and
                              svc.find('protocol') is None and
                              svc.find('description') is None)

                if has_id_only:
                    # Skip reference-only entries
                    continue

                service_obj = {'name': name, 'device_group': self.device_group_of(svc)}

                # Protocol and port
                protocol = svc.find('protocol')
                if protocol is not None:
                    tcp = protocol.find('tcp')
                    udp = protocol.find('udp')

                    if tcp is not None:
                        service_obj['protocol'] = 'tcp'
                        port = tcp.find('port')
                        if port is not None:
                            service_obj['port'] = port.text
                    elif udp is not None:
                        service_obj['protocol'] = 'udp'
                        port = udp.find('port')
                        if port is not None:
                            service_obj['port'] = port.text

                service_obj['description'] = self._get_text(svc, 'description')

                # Only add/override if this entry has content (protocol defined)
                # OR if we haven't seen this name yet
                if ('protocol' in service_obj or name not in services_dict):
                    services_dict[name] = service_obj

        return list(services_dict.values())

    def parse_service_groups(self) -> list[dict]:
        """Parse service groups"""
        # Use dictionary to track groups by name, allowing overrides
        groups_dict = {}

        # Parse in order: device groups first, then shared
        paths = [
            ".//device-group/entry/service-group/entry",
            ".//shared/service-group/entry",
            ".//service-group/entry"
        ]

        for path in paths:
            for grp in self.root.findall(path):
                name = grp.get('name')
                if not name:
                    continue

                # Check if this is just a reference (only has <id> tag, no actual content)
                has_id_only = (grp.find('id') is not None and
                              grp.find('.//members') is None and
                              grp.find('description') is None)

                if has_id_only:
                    # Skip reference-only entries
                    continue

                members = []
                for member in grp.findall('.//members/member'):
                    if member.text:
                        members.append(member.text)

                group_obj = {
                    'name': name,
                    'device_group': self.device_group_of(grp),
                    'members': members,
                    'description': self._get_text(grp, 'description')
                }

                # Only add/override if this entry has content (members defined)
                # OR if we haven't seen this name yet
                if (members or name not in groups_dict):
                    groups_dict[name] = group_obj

        return list(groups_dict.values())

    def parse_security_rules(self) -> list[dict]:
        """Parse security policy rules"""
        rules = []
        seen_names = set()

        paths = [
            ".//security/rules/entry",
            ".//device-group/entry/pre-rulebase/security/rules/entry",
            ".//device-group/entry/post-rulebase/security/rules/entry"
        ]

        for path in paths:
            for rule in self.root.findall(path):
                name = rule.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)
                rule_obj = {
                    'name': name,
                    'device_group': self.device_group_of(rule),
                    'source_zones': self._get_members(rule, 'from'),
                    'source_addresses': self._get_members(rule, 'source'),
                    'destination_zones': self._get_members(rule, 'to'),
                    'destination_addresses': self._get_members(rule, 'destination'),
                    'applications': self._get_members(rule, 'application'),
                    'services': self._get_members(rule, 'service'),
                    'action': self._get_text(rule, 'action'),
                    'description': self._get_text(rule, 'description')
                }

                # Log settings
                log_start = rule.find('log-start')
                log_end = rule.find('log-end')
                rule_obj['log_start'] = log_start.text == 'yes' if log_start is not None else False
                rule_obj['log_end'] = log_end.text == 'yes' if log_end is not None else False

                # Disabled status
                disabled = rule.find('disabled')
                rule_obj['disabled'] = disabled.text == 'yes' if disabled is not None else False

                rules.append(rule_obj)

        return rules

    def parse_nat_rules(self) -> list[dict]:
        """Parse NAT policy rules"""
        rules = []
        seen_names = set()

        paths = [
            ".//nat/rules/entry",
            ".//device-group/entry/pre-rulebase/nat/rules/entry",
            ".//device-group/entry/post-rulebase/nat/rules/entry"
        ]

        for path in paths:
            for rule in self.root.findall(path):
                name = rule.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)
                rule_obj = {
                    'name': name,
                    'device_group': self.device_group_of(rule),
                    'source_zones': self._get_members(rule, 'from'),
                    'destination_zone': self._get_text(rule, 'to-interface'),
                    'source_addresses': self._get_members(rule, 'source'),
                    'destination_addresses': self._get_members(rule, 'destination'),
                    'service': self._get_text(rule, 'service'),
                    'description': self._get_text(rule, 'description')
                }

                # Source translation
                source_translation = rule.find('.//source-translation')
                if source_translation is not None:
                    dynamic_ip_and_port = source_translation.find('dynamic-ip-and-port')
                    if dynamic_ip_and_port is not None:
                        translated_address = dynamic_ip_and_port.find('.//translated-address')
                        if translated_address is not None:
                            members = []
                            for member in translated_address.findall('member'):
                                if member.text:
                                    members.append(member.text)
                            rule_obj['source_translation_type'] = 'dynamic-ip-and-port'
                            rule_obj['source_translation_address'] = members

                # Destination translation
                destination_translation = rule.find('.//destination-translation')
                if destination_translation is not None:
                    translated_address = destination_translation.find('translated-address')
                    translated_port = destination_translation.find('translated-port')

                    if translated_address is not None:
                        rule_obj['destination_translation_address'] = translated_address.text
                    if translated_port is not None:
                        rule_obj['destination_translation_port'] = translated_port.text

                # Disabled status
                disabled = rule.find('disabled')
                rule_obj['disabled'] = disabled.text == 'yes' if disabled is not None else False

                rules.append(rule_obj)

        return rules

    def parse_schedules(self) -> list[dict]:
        """Parse schedules"""
        schedules = []
        seen_names = set()

        paths = [
            ".//schedule/entry",
            ".//device-group/entry/schedule/entry"
        ]

        for path in paths:
            for sched in self.root.findall(path):
                name = sched.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                sched_obj = {
                    'name': name,
                    'schedule_type': None,
                    'recurring': []
                }

                # Check for recurring schedule
                recurring = sched.find('schedule-type/recurring')
                if recurring is not None:
                    sched_obj['schedule_type'] = 'recurring'
                    for entry in recurring.findall('entry'):
                        rec_name = entry.get('name')
                        rec_obj = {
                            'name': rec_name
                        }
                        sched_obj['recurring'].append(rec_obj)

                # Check for non-recurring schedule
                non_recurring = sched.find('schedule-type/non-recurring')
                if non_recurring is not None:
                    sched_obj['schedule_type'] = 'non-recurring'

                schedules.append(sched_obj)

        return schedules

    def parse_decryption_rules(self) -> list[dict]:
        """Parse decryption policy rules"""
        rules = []
        seen_names = set()

        paths = [
            ".//decryption/rules/entry",
            ".//device-group/entry/pre-rulebase/decryption/rules/entry",
            ".//device-group/entry/post-rulebase/decryption/rules/entry"
        ]

        for path in paths:
            for rule in self.root.findall(path):
                name = rule.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                rule_obj = {
                    'name': name,
                    'uuid': rule.get('uuid'),
                    # F2.9: the device group scopes the v2 resource and its
                    # rule chain (location + position pivot semantics, F2.5)
                    'device_group': self.device_group_of(rule),
                    'source_zones': self._get_members(rule, 'from'),
                    'destination_zones': self._get_members(rule, 'to'),
                    'source_addresses': self._get_members(rule, 'source'),
                    'destination_addresses': self._get_members(rule, 'destination'),
                    'source_users': self._get_members(rule, 'source-user'),
                    'categories': self._get_members(rule, 'category'),
                    'services': self._get_members(rule, 'service'),
                    'action': self._get_text(rule, 'action'),
                    'type': None,
                    'profile': self._get_text(rule, 'profile'),
                    'description': self._get_text(rule, 'description'),
                    'disabled': self._get_text(rule, 'disabled') == 'yes',
                    'log_setting': self._get_text(rule, 'log-setting'),
                    # F2.9: log-start/log-end map to the v2 log_success and
                    # log_fail attributes
                    'log_start': self._get_text(rule, 'log-start') == 'yes',
                    'log_end': self._get_text(rule, 'log-end') == 'yes',
                }

                # Determine type
                type_elem = rule.find('type')
                if type_elem is not None:
                    if type_elem.find('ssl-forward-proxy') is not None:
                        rule_obj['type'] = 'ssl-forward-proxy'
                    elif type_elem.find('ssl-inbound-inspection') is not None:
                        rule_obj['type'] = 'ssl-inbound-inspection'
                    elif type_elem.find('ssh-proxy') is not None:
                        rule_obj['type'] = 'ssh-proxy'

                rules.append(rule_obj)

        return rules

    def parse_pbf_rules(self) -> list[dict]:
        """Parse Policy-Based Forwarding rules"""
        rules = []
        seen_names = set()

        paths = [
            ".//pbf/rules/entry",
            ".//device-group/entry/pre-rulebase/pbf/rules/entry",
            ".//device-group/entry/post-rulebase/pbf/rules/entry"
        ]

        for path in paths:
            for rule in self.root.findall(path):
                name = rule.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                rule_obj = {
                    'name': name,
                    'uuid': rule.get('uuid'),
                    # F2.9: the device group scopes the v2 resource and its
                    # rule chain (location + position pivot semantics, F2.5)
                    'device_group': self.device_group_of(rule),
                    'description': self._get_text(rule, 'description'),
                    'disabled': self._get_text(rule, 'disabled') == 'yes',
                    'source_zones': [],
                    'source_addresses': self._get_members(rule, 'source'),
                    'source_users': self._get_members(rule, 'source-user'),
                    'destination_addresses': self._get_members(rule, 'destination'),
                    'applications': self._get_members(rule, 'application'),
                    'services': self._get_members(rule, 'service'),
                    # F2.9: optional rule schedule name
                    'schedule': self._get_text(rule, 'schedule'),
                    'action': None
                }

                # Get source zones
                from_elem = rule.find('from')
                if from_elem is not None:
                    for zone in from_elem.findall('.//zone/member'):
                        if zone.text:
                            rule_obj['source_zones'].append(zone.text)

                # Get action
                action_elem = rule.find('action')
                if action_elem is not None:
                    forward = action_elem.find('forward')
                    if forward is not None:
                        nexthop_ip = self._get_text(forward, 'nexthop/ip-address')
                        egress_iface = self._get_text(forward, 'egress-interface')
                        action_obj = {
                            'type': 'forward',
                            'nexthop_ip': nexthop_ip,
                            'egress_interface': egress_iface
                        }
                        # F2.9: optional path monitoring on the forward action.
                        # The profile name references a panos_monitor_profile
                        # (network/profiles/monitor-profile), a different
                        # object from the IPsec tunnel monitor profile.
                        monitor = forward.find('monitor')
                        if monitor is not None:
                            action_obj['monitor'] = {
                                'ip_address': self._get_text(monitor, 'ip-address'),
                                'profile': self._get_text(monitor, 'profile'),
                                'disable_if_unreachable':
                                    self._get_text(monitor, 'disable-if-unreachable') == 'yes'
                            }
                        rule_obj['action'] = action_obj

                    discard = action_elem.find('discard')
                    if discard is not None:
                        rule_obj['action'] = {
                            'type': 'discard'
                        }

                    no_pbf = action_elem.find('no-pbf')
                    if no_pbf is not None:
                        rule_obj['action'] = {
                            'type': 'no-pbf'
                        }

                    # F2.9: forward-to-vsys is a plain vsys name in both the
                    # export and the v2 schema
                    fwd_vsys = action_elem.find('forward-to-vsys')
                    if fwd_vsys is not None and fwd_vsys.text:
                        rule_obj['action'] = {
                            'type': 'forward_to_vsys',
                            'vsys': fwd_vsys.text
                        }

                # Enforce symmetric return
                enforce_sym = rule.find('.//enforce-symmetric-return/enabled')
                if enforce_sym is not None:
                    rule_obj['enforce_symmetric_return'] = enforce_sym.text == 'yes'

                rules.append(rule_obj)

        return rules

    def parse_application_override_rules(self) -> list[dict]:
        """Parse Application Override rules"""
        rules = []
        seen_names = set()

        paths = [
            ".//application-override/rules/entry",
            ".//device-group/entry/pre-rulebase/application-override/rules/entry",
            ".//device-group/entry/post-rulebase/application-override/rules/entry"
        ]

        for path in paths:
            for rule in self.root.findall(path):
                name = rule.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                rule_obj = {
                    'name': name,
                    'description': self._get_text(rule, 'description'),
                    'disabled': self._get_text(rule, 'disabled') == 'yes',
                    'source_zones': self._get_members(rule, 'from'),
                    'destination_zones': self._get_members(rule, 'to'),
                    'source_addresses': self._get_members(rule, 'source'),
                    'destination_addresses': self._get_members(rule, 'destination'),
                    'port': self._get_text(rule, 'port'),
                    'protocol': self._get_text(rule, 'protocol'),
                    'application': self._get_text(rule, 'application')
                }

                rules.append(rule_obj)

        return rules

    def parse_zones(self) -> list[dict]:
        """Parse zone configurations"""
        zones = []
        seen_names = set()

        paths = [
            ".//zone/entry",
            ".//vsys/entry/zone/entry",
            ".//devices/entry/vsys/entry/zone/entry"
        ]

        for path in paths:
            for zone in self.root.findall(path):
                name = zone.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                # Determine zone type
                zone_type = 'layer3'
                if zone.find('network/layer2') is not None:
                    zone_type = 'layer2'
                elif zone.find('network/tap') is not None:
                    zone_type = 'tap'
                elif zone.find('network/virtual-wire') is not None:
                    zone_type = 'virtual-wire'
                elif zone.find('network/tunnel') is not None:
                    zone_type = 'tunnel'

                # Get interfaces
                interfaces = []
                for iface in zone.findall('.//network/*/member'):
                    if iface.text:
                        interfaces.append(iface.text)

                # Get zone protection profile
                zone_profile = zone.find('.//zone-protection-profile')

                zone_obj = {
                    'name': name,
                    'type': zone_type,
                    'interfaces': interfaces,
                    'zone_protection_profile': zone_profile.text if zone_profile is not None else None
                }

                zones.append(zone_obj)

        return zones

    def parse_interfaces(self) -> list[dict]:
        """Parse interface configurations"""
        interfaces = []
        seen_names = set()

        # Ethernet interfaces
        eth_paths = [
            ".//network/interface/ethernet/entry",
            ".//devices/entry/network/interface/ethernet/entry"
        ]

        for path in eth_paths:
            for iface in self.root.findall(path):
                name = iface.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                iface_obj = {
                    'name': name,
                    'type': 'ethernet',
                    'mode': None,
                    'ip_addresses': [],
                    'ipv6_addresses': [],
                    'zone': None,
                    'virtual_router': None,
                    'management_profile': None,
                    'comment': self._get_text(iface, 'comment')
                }

                # Determine mode (layer3, layer2, virtual-wire, tap, ha, aggregate-group)
                if iface.find('layer3') is not None:
                    iface_obj['mode'] = 'layer3'
                    l3 = iface.find('layer3')

                    # Get IP addresses
                    for ip in l3.findall('.//ip/entry'):
                        ip_name = ip.get('name')
                        if ip_name:
                            iface_obj['ip_addresses'].append(ip_name)

                    # Get IPv6 addresses
                    for ip in l3.findall('.//ipv6/address/entry'):
                        ip_name = ip.get('name')
                        if ip_name:
                            iface_obj['ipv6_addresses'].append(ip_name)

                    # Management profile
                    mgmt_profile = l3.find('interface-management-profile')
                    if mgmt_profile is not None:
                        iface_obj['management_profile'] = mgmt_profile.text

                elif iface.find('layer2') is not None:
                    iface_obj['mode'] = 'layer2'
                elif iface.find('virtual-wire') is not None:
                    iface_obj['mode'] = 'virtual-wire'
                elif iface.find('tap') is not None:
                    iface_obj['mode'] = 'tap'
                elif iface.find('ha') is not None:
                    iface_obj['mode'] = 'ha'
                elif iface.find('aggregate-group') is not None:
                    iface_obj['mode'] = 'aggregate-group'

                interfaces.append(iface_obj)

        # VLAN interfaces
        vlan_paths = [
            ".//network/interface/vlan/units/entry",
            ".//devices/entry/network/interface/vlan/units/entry"
        ]

        for path in vlan_paths:
            for iface in self.root.findall(path):
                name = iface.get('name')
                # Dedupe on the namespaced name so a vlan unit number does
                # not collide with a loopback/tunnel unit of the same number.
                full_name = f'vlan.{name}'
                if not name or full_name in seen_names:
                    continue

                seen_names.add(full_name)

                iface_obj = {
                    'name': full_name,
                    'type': 'vlan',
                    'mode': 'layer3',
                    'ip_addresses': [],
                    'ipv6_addresses': [],
                    'zone': None,
                    'virtual_router': None,
                    'management_profile': None,
                    'comment': self._get_text(iface, 'comment'),
                    'tag': self._get_text(iface, 'tag')
                }

                # Get IP addresses
                for ip in iface.findall('.//ip/entry'):
                    ip_name = ip.get('name')
                    if ip_name:
                        iface_obj['ip_addresses'].append(ip_name)

                # Get IPv6 addresses
                for ip in iface.findall('.//ipv6/address/entry'):
                    ip_name = ip.get('name')
                    if ip_name:
                        iface_obj['ipv6_addresses'].append(ip_name)

                # Management profile
                mgmt_profile = iface.find('interface-management-profile')
                if mgmt_profile is not None:
                    iface_obj['management_profile'] = mgmt_profile.text

                interfaces.append(iface_obj)

        # Loopback interfaces
        loopback_paths = [
            ".//network/interface/loopback/units/entry",
            ".//devices/entry/network/interface/loopback/units/entry"
        ]

        for path in loopback_paths:
            for iface in self.root.findall(path):
                name = iface.get('name')
                # Dedupe on the namespaced name so a loopback unit number
                # does not collide with a vlan/tunnel unit of the same number.
                full_name = f'loopback.{name}'
                if not name or full_name in seen_names:
                    continue

                seen_names.add(full_name)

                iface_obj = {
                    'name': full_name,
                    'type': 'loopback',
                    'mode': 'layer3',
                    'ip_addresses': [],
                    'ipv6_addresses': [],
                    'zone': None,
                    'virtual_router': None,
                    'management_profile': None,
                    'comment': self._get_text(iface, 'comment')
                }

                # Get IP addresses
                for ip in iface.findall('.//ip/entry'):
                    ip_name = ip.get('name')
                    if ip_name:
                        iface_obj['ip_addresses'].append(ip_name)

                # Get IPv6 addresses
                for ip in iface.findall('.//ipv6/address/entry'):
                    ip_name = ip.get('name')
                    if ip_name:
                        iface_obj['ipv6_addresses'].append(ip_name)

                interfaces.append(iface_obj)

        # Tunnel interfaces
        tunnel_paths = [
            ".//network/interface/tunnel/units/entry",
            ".//devices/entry/network/interface/tunnel/units/entry"
        ]

        for path in tunnel_paths:
            for iface in self.root.findall(path):
                name = iface.get('name')
                # Dedupe on the namespaced name so a tunnel unit number
                # does not collide with a vlan/loopback unit of the same number.
                full_name = f'tunnel.{name}'
                if not name or full_name in seen_names:
                    continue

                seen_names.add(full_name)

                iface_obj = {
                    'name': full_name,
                    'type': 'tunnel',
                    'mode': 'layer3',
                    'ip_addresses': [],
                    'ipv6_addresses': [],
                    'zone': None,
                    'virtual_router': None,
                    'management_profile': None,
                    'comment': self._get_text(iface, 'comment')
                }

                # Get IP addresses
                for ip in iface.findall('.//ip/entry'):
                    ip_name = ip.get('name')
                    if ip_name:
                        iface_obj['ip_addresses'].append(ip_name)

                # Get IPv6 addresses
                for ip in iface.findall('.//ipv6/address/entry'):
                    ip_name = ip.get('name')
                    if ip_name:
                        iface_obj['ipv6_addresses'].append(ip_name)

                # Management profile
                mgmt_profile = iface.find('interface-management-profile')
                if mgmt_profile is not None:
                    iface_obj['management_profile'] = mgmt_profile.text

                interfaces.append(iface_obj)

        # Aggregate interfaces (ae)
        aggregate_paths = [
            ".//network/interface/aggregate-ethernet/entry",
            ".//devices/entry/network/interface/aggregate-ethernet/entry"
        ]

        for path in aggregate_paths:
            for iface in self.root.findall(path):
                name = iface.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                iface_obj = {
                    'name': name,
                    'type': 'aggregate',
                    'mode': None,
                    'ip_addresses': [],
                    'ipv6_addresses': [],
                    'zone': None,
                    'virtual_router': None,
                    'management_profile': None,
                    'comment': self._get_text(iface, 'comment')
                }

                # Determine mode
                if iface.find('layer3') is not None:
                    iface_obj['mode'] = 'layer3'
                    l3 = iface.find('layer3')

                    # Get IP addresses from the main interface only. Use a
                    # direct-child lookup so subinterface IPs (nested under
                    # <units>) do not leak into the parent's address list.
                    for ip in l3.findall('ip/entry'):
                        ip_name = ip.get('name')
                        if ip_name:
                            iface_obj['ip_addresses'].append(ip_name)

                    # Management profile
                    mgmt_profile = l3.find('interface-management-profile')
                    if mgmt_profile is not None:
                        iface_obj['management_profile'] = mgmt_profile.text

                    # Get subinterfaces (units)
                    for unit in l3.findall('.//units/entry'):
                        unit_name = unit.get('name')
                        if unit_name and unit_name not in seen_names:
                            seen_names.add(unit_name)

                            unit_obj = {
                                'name': unit_name,
                                'type': 'aggregate-subinterface',
                                'mode': 'layer3',
                                'ip_addresses': [],
                                'ipv6_addresses': [],
                                'zone': None,
                                'virtual_router': None,
                                'management_profile': None,
                                'comment': self._get_text(unit, 'comment'),
                                'tag': self._get_text(unit, 'tag')
                            }

                            # Get IP addresses
                            for ip in unit.findall('.//ip/entry'):
                                ip_name = ip.get('name')
                                if ip_name:
                                    unit_obj['ip_addresses'].append(ip_name)

                            # Management profile
                            unit_mgmt = unit.find('interface-management-profile')
                            if unit_mgmt is not None:
                                unit_obj['management_profile'] = unit_mgmt.text

                            interfaces.append(unit_obj)

                elif iface.find('layer2') is not None:
                    iface_obj['mode'] = 'layer2'

                interfaces.append(iface_obj)

        return interfaces

    def parse_virtual_routers(self) -> list[dict]:
        """Parse virtual router configurations"""
        vrouters_dict = {}

        # Parse from templates first (most authoritative source).
        # Panorama exports use a top-level <templates> element containing
        # <entry> children (not <template>), so match that exact structure.
        for template in self.root.findall('.//templates/entry'):
            template_name = template.get('name')

            for vr in template.findall('.//network/virtual-router/entry'):
                name = vr.get('name')
                if not name:
                    continue

                # Get interfaces
                interfaces = []
                for iface in vr.findall('.//interface/member'):
                    if iface.text:
                        interfaces.append(iface.text)

                # Get static routes
                static_routes = []
                for route in vr.findall('.//routing-table/ip/static-route/entry'):
                    route_name = route.get('name')
                    destination = self._get_text(route, 'destination')
                    nexthop_ip = self._get_text(route, 'nexthop/ip-address')
                    nexthop_iface = self._get_text(route, 'nexthop/next-vr')
                    metric = self._get_text(route, 'metric')

                    if route_name:
                        static_routes.append({
                            'name': route_name,
                            'destination': destination,
                            'nexthop_ip': nexthop_ip,
                            'nexthop_interface': nexthop_iface,
                            'metric': metric
                        })

                vr_obj = {
                    'name': name,
                    'template': template_name,
                    'interfaces': interfaces,
                    'static_routes': static_routes
                }

                # Create a unique key based on name + interface signature
                # This handles cases where multiple templates have VRs with same name
                interface_signature = ','.join(sorted(interfaces[:5]))  # First 5 interfaces as signature
                unique_key = f"{name}_{interface_signature}"

                # Only add if we haven't seen this exact configuration
                # Or if this has more interfaces (more complete definition)
                if unique_key not in vrouters_dict or len(interfaces) > len(vrouters_dict[unique_key]['interfaces']):
                    vrouters_dict[unique_key] = vr_obj

        # Also check per-vsys device-level VRs (real exports nest the network
        # config under devices/entry/vsys/entry, not directly under devices/entry)
        for vr in self.root.findall('.//devices/entry/vsys/entry/network/virtual-router/entry'):
            name = vr.get('name')
            if not name:
                continue

            interfaces = []
            for iface in vr.findall('.//interface/member'):
                if iface.text:
                    interfaces.append(iface.text)

            static_routes = []
            for route in vr.findall('.//routing-table/ip/static-route/entry'):
                route_name = route.get('name')
                destination = self._get_text(route, 'destination')
                nexthop_ip = self._get_text(route, 'nexthop/ip-address')
                nexthop_iface = self._get_text(route, 'nexthop/next-vr')
                metric = self._get_text(route, 'metric')

                if route_name:
                    static_routes.append({
                        'name': route_name,
                        'destination': destination,
                        'nexthop_ip': nexthop_ip,
                        'nexthop_interface': nexthop_iface,
                        'metric': metric
                    })

            vr_obj = {
                'name': name,
                'template': 'device-specific',
                'interfaces': interfaces,
                'static_routes': static_routes
            }

            interface_signature = ','.join(sorted(interfaces[:5]))
            unique_key = f"{name}_{interface_signature}"

            if unique_key not in vrouters_dict or len(interfaces) > len(vrouters_dict[unique_key]['interfaces']):
                vrouters_dict[unique_key] = vr_obj

        return list(vrouters_dict.values())

    def parse_logical_routers(self) -> list[dict]:
        """Parse logical router configurations (Advanced Routing Engine)

        Logical routers are part of PAN-OS 10.2+ Advanced Routing Engine.
        They replace virtual routers with industry-standard configuration.
        """
        lrouters_dict = {}

        # Parse from templates first (most authoritative source).
        # Panorama exports use <templates><entry>, not <template><entry>.
        for template in self.root.findall('.//templates/entry'):
            template_name = template.get('name')

            for lr in template.findall('.//network/logical-router/entry'):
                name = lr.get('name')
                if not name:
                    continue

                # Get interfaces
                interfaces = []
                for iface in lr.findall('.//interface/member'):
                    if iface.text:
                        interfaces.append(iface.text)

                # Get static routes
                static_routes = []
                for route in lr.findall('.//routing-table/ip/static-route/entry'):
                    route_name = route.get('name')
                    destination = self._get_text(route, 'destination')
                    nexthop_ip = self._get_text(route, 'nexthop/ip-address')
                    nexthop_iface = self._get_text(route, 'nexthop/next-lr')  # next-lr for logical routers
                    metric = self._get_text(route, 'metric')

                    if route_name:
                        static_routes.append({
                            'name': route_name,
                            'destination': destination,
                            'nexthop_ip': nexthop_ip,
                            'nexthop_interface': nexthop_iface,
                            'metric': metric
                        })

                lr_obj = {
                    'name': name,
                    'template': template_name,
                    'router_type': 'logical',  # Mark as logical router
                    'interfaces': interfaces,
                    'static_routes': static_routes
                }

                # Create a unique key based on name + interface signature
                interface_signature = ','.join(sorted(interfaces[:5]))
                unique_key = f"{name}_{interface_signature}"

                if unique_key not in lrouters_dict or len(interfaces) > len(lrouters_dict[unique_key]['interfaces']):
                    lrouters_dict[unique_key] = lr_obj

        # Also check per-vsys device-level logical routers (network config is
        # nested under devices/entry/vsys/entry in real exports)
        for lr in self.root.findall('.//devices/entry/vsys/entry/network/logical-router/entry'):
            name = lr.get('name')
            if not name:
                continue

            interfaces = []
            for iface in lr.findall('.//interface/member'):
                if iface.text:
                    interfaces.append(iface.text)

            static_routes = []
            for route in lr.findall('.//routing-table/ip/static-route/entry'):
                route_name = route.get('name')
                destination = self._get_text(route, 'destination')
                nexthop_ip = self._get_text(route, 'nexthop/ip-address')
                nexthop_iface = self._get_text(route, 'nexthop/next-lr')
                metric = self._get_text(route, 'metric')

                if route_name:
                    static_routes.append({
                        'name': route_name,
                        'destination': destination,
                        'nexthop_ip': nexthop_ip,
                        'nexthop_interface': nexthop_iface,
                        'metric': metric
                    })

            lr_obj = {
                'name': name,
                'template': 'device-specific',
                'router_type': 'logical',
                'interfaces': interfaces,
                'static_routes': static_routes
            }

            interface_signature = ','.join(sorted(interfaces[:5]))
            unique_key = f"{name}_{interface_signature}"

            if unique_key not in lrouters_dict or len(interfaces) > len(lrouters_dict[unique_key]['interfaces']):
                lrouters_dict[unique_key] = lr_obj

        return list(lrouters_dict.values())

    def parse_security_profiles(self) -> dict[str, list[dict]]:
        """Parse security profiles (antivirus, vulnerability, spyware, url-filtering, file-blocking, wildfire)"""
        profiles = {
            'antivirus': [],
            'vulnerability': [],
            'anti_spyware': [],
            'url_filtering': [],
            'file_blocking': [],
            'wildfire_analysis': []
        }

        seen_names = {key: set() for key in profiles}

        # Antivirus profiles
        av_paths = [
            ".//profiles/virus/entry",
            ".//device-group/entry/profiles/virus/entry",
            ".//shared/profiles/virus/entry"
        ]

        for path in av_paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names['antivirus']:
                    continue

                seen_names['antivirus'].add(name)
                profiles['antivirus'].append({
                    'name': name,
                    'description': self._get_text(prof, 'description')
                })

        # Vulnerability profiles
        vuln_paths = [
            ".//profiles/vulnerability/entry",
            ".//device-group/entry/profiles/vulnerability/entry",
            ".//shared/profiles/vulnerability/entry"
        ]

        for path in vuln_paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names['vulnerability']:
                    continue

                seen_names['vulnerability'].add(name)
                profiles['vulnerability'].append({
                    'name': name,
                    'description': self._get_text(prof, 'description')
                })

        # Anti-spyware profiles
        spy_paths = [
            ".//profiles/spyware/entry",
            ".//device-group/entry/profiles/spyware/entry",
            ".//shared/profiles/spyware/entry"
        ]

        for path in spy_paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names['anti_spyware']:
                    continue

                seen_names['anti_spyware'].add(name)
                profiles['anti_spyware'].append({
                    'name': name,
                    'description': self._get_text(prof, 'description')
                })

        # URL filtering profiles
        url_paths = [
            ".//profiles/url-filtering/entry",
            ".//device-group/entry/profiles/url-filtering/entry",
            ".//shared/profiles/url-filtering/entry"
        ]

        for path in url_paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names['url_filtering']:
                    continue

                seen_names['url_filtering'].add(name)
                profiles['url_filtering'].append({
                    'name': name,
                    'description': self._get_text(prof, 'description')
                })

        # File blocking profiles
        fb_paths = [
            ".//profiles/file-blocking/entry",
            ".//device-group/entry/profiles/file-blocking/entry",
            ".//shared/profiles/file-blocking/entry"
        ]

        for path in fb_paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names['file_blocking']:
                    continue

                seen_names['file_blocking'].add(name)
                profiles['file_blocking'].append({
                    'name': name,
                    'description': self._get_text(prof, 'description')
                })

        # WildFire analysis profiles
        wf_paths = [
            ".//profiles/wildfire-analysis/entry",
            ".//device-group/entry/profiles/wildfire-analysis/entry",
            ".//shared/profiles/wildfire-analysis/entry"
        ]

        for path in wf_paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names['wildfire_analysis']:
                    continue

                seen_names['wildfire_analysis'].add(name)
                profiles['wildfire_analysis'].append({
                    'name': name,
                    'description': self._get_text(prof, 'description')
                })

        return profiles

    def parse_security_profile_groups(self) -> list[dict]:
        """Parse security profile groups"""
        groups = []
        seen_names = set()

        paths = [
            ".//profile-group/entry",
            ".//device-group/entry/profile-group/entry",
            ".//shared/profile-group/entry"
        ]

        for path in paths:
            for grp in self.root.findall(path):
                name = grp.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                group_obj = {
                    'name': name,
                    'device_group': self.device_group_of(grp),
                    'virus': self._get_members(grp, 'virus'),
                    'spyware': self._get_members(grp, 'spyware'),
                    'vulnerability': self._get_members(grp, 'vulnerability'),
                    'url_filtering': self._get_members(grp, 'url-filtering'),
                    'file_blocking': self._get_members(grp, 'file-blocking'),
                    'wildfire_analysis': self._get_members(grp, 'wildfire-analysis')
                }

                groups.append(group_obj)

        return groups

    def parse_zone_protection_profiles(self) -> list[dict]:
        """Parse zone protection profiles"""
        profiles = []
        seen_names = set()

        paths = [
            ".//zone-protection-profile/entry",
            ".//device-group/entry/zone-protection-profile/entry",
            ".//network/profiles/zone-protection-profile/entry"
        ]

        for path in paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                prof_obj = {
                    'name': name,
                    'description': self._get_text(prof, 'description')
                }

                profiles.append(prof_obj)

        return profiles

    def parse_log_settings(self) -> list[dict]:
        """Parse log forwarding profiles"""
        profiles = []
        seen_names = set()

        paths = [
            ".//log-settings/profiles/entry",
            ".//device-group/entry/log-settings/profiles/entry",
            ".//shared/log-settings/profiles/entry"
        ]

        for path in paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                prof_obj = {
                    'name': name,
                    'description': self._get_text(prof, 'description')
                }

                profiles.append(prof_obj)

        return profiles

    def parse_qos_profiles(self) -> list[dict]:
        """Parse QoS profiles"""
        profiles = []
        seen_names = set()

        paths = [
            ".//qos/profile/entry",
            ".//device-group/entry/qos/profile/entry",
            ".//network/qos/profile/entry"
        ]

        for path in paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                prof_obj = {
                    'name': name,
                    'class_bandwidth_type': {}
                }

                # Parse class bandwidth settings
                for cls in prof.findall('.//class/entry'):
                    cls_name = cls.get('name')
                    if cls_name:
                        prof_obj['class_bandwidth_type'][cls_name] = {
                            'priority': self._get_text(cls, 'priority')
                        }

                profiles.append(prof_obj)

        return profiles

    def parse_tunnel_monitor_profiles(self) -> list[dict]:
        """Parse tunnel monitor profiles"""
        profiles = []
        seen_names = set()

        paths = [
            ".//network/tunnel/global-protect-gateway/Default/tunnel-monitor/monitor-profile/entry",
            ".//network/tunnel-monitor/monitor-profile/entry",
            ".//devices/entry/network/tunnel-monitor/monitor-profile/entry"
        ]

        for path in paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                prof_obj = {
                    'name': name,
                    'interval': self._get_text(prof, 'interval'),
                    'threshold': self._get_text(prof, 'threshold'),
                    'action': self._get_text(prof, 'action')
                }

                profiles.append(prof_obj)

        return profiles

    def parse_pbf_monitor_profiles(self) -> list[dict]:
        """Parse PBF path monitoring profiles (F2.9)

        These live at network/profiles/monitor-profile and are referenced by
        PBF rule path monitoring. The provider manages them as
        panos_monitor_profile resources (v2.0.14).

        Note: this is NOT the IPsec tunnel monitor profile
        (network/tunnel-monitor/monitor-profile). That object has no v2
        resource and goes to the manual setup report instead. The v2 schema
        has no description attribute, so none is captured.
        """
        profiles = []
        seen_names = set()

        paths = [
            ".//network/profiles/monitor-profile/entry",
            ".//device-group/entry/network/profiles/monitor-profile/entry"
        ]

        for path in paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                profiles.append({
                    'name': name,
                    # v2 action is an enum: wait-recover | fail-over
                    'action': self._get_text(prof, 'action'),
                    'interval': self._get_text(prof, 'interval'),
                    'threshold': self._get_text(prof, 'threshold')
                })

        return profiles

    def parse_bgp(self) -> dict[str, Any]:
        """Parse BGP configuration"""
        bgp_config = {
            'enabled': False,
            'router_id': None,
            'as_number': None,
            'peer_groups': [],
            'peers': [],
            'redistribution_rules': []
        }

        paths = [
            ".//network/virtual-router/entry/protocol/bgp",
            ".//devices/entry/network/virtual-router/entry/protocol/bgp"
        ]

        for path in paths:
            for bgp in self.root.findall(path):
                if bgp.find('enable') is not None and bgp.find('enable').text == 'yes':
                    bgp_config['enabled'] = True

                    # Router ID
                    router_id = bgp.find('router-id')
                    if router_id is not None:
                        bgp_config['router_id'] = router_id.text

                    # AS Number
                    local_as = bgp.find('local-as')
                    if local_as is not None:
                        bgp_config['as_number'] = local_as.text

                    # Peer Groups
                    for pg in bgp.findall('.//peer-group/entry'):
                        pg_name = pg.get('name')
                        if pg_name:
                            peer_group = {
                                'name': pg_name,
                                'type': self._get_text(pg, 'type'),
                                'export_nexthop': self._get_text(pg, 'export-nexthop'),
                                'import_nexthop': self._get_text(pg, 'import-nexthop')
                            }
                            bgp_config['peer_groups'].append(peer_group)

                    # BGP Peers
                    for peer in bgp.findall('.//peer/entry'):
                        peer_name = peer.get('name')
                        if peer_name:
                            peer_config = {
                                'name': peer_name,
                                'peer_as': self._get_text(peer, 'peer-as'),
                                'local_address_interface': self._get_text(peer, 'local-address/interface'),
                                'local_address_ip': self._get_text(peer, 'local-address/ip'),
                                'peer_address_ip': self._get_text(peer, 'peer-address/ip'),
                                'enable': self._get_text(peer, 'enable') == 'yes',
                                'peer_group': self._get_text(peer, 'peer-group')
                            }
                            bgp_config['peers'].append(peer_config)

                    # Redistribution rules
                    for redist in bgp.findall('.//redist-rules/entry'):
                        rule_name = redist.get('name')
                        if rule_name:
                            redist_rule = {
                                'name': rule_name,
                                'enable': self._get_text(redist, 'enable') == 'yes',
                                'address_family': self._get_text(redist, 'address-family-identifier')
                            }
                            bgp_config['redistribution_rules'].append(redist_rule)

        return bgp_config if bgp_config['enabled'] else None

    def parse_ospf(self) -> dict[str, Any]:
        """Parse OSPF configuration"""
        ospf_config = {
            'enabled': False,
            'router_id': None,
            'areas': [],
            'interfaces': []
        }

        paths = [
            ".//network/virtual-router/entry/protocol/ospf",
            ".//devices/entry/network/virtual-router/entry/protocol/ospf"
        ]

        for path in paths:
            for ospf in self.root.findall(path):
                if ospf.find('enable') is not None and ospf.find('enable').text == 'yes':
                    ospf_config['enabled'] = True

                    # Router ID
                    router_id = ospf.find('router-id')
                    if router_id is not None:
                        ospf_config['router_id'] = router_id.text

                    # OSPF Areas
                    for area in ospf.findall('.//area/entry'):
                        area_id = area.get('name')
                        if area_id:
                            area_config = {
                                'area_id': area_id,
                                'type': 'normal'
                            }

                            # Check for stub/nssa
                            if area.find('type/stub') is not None:
                                area_config['type'] = 'stub'
                            elif area.find('type/nssa') is not None:
                                area_config['type'] = 'nssa'

                            # Area ranges
                            ranges = []
                            for range_entry in area.findall('.//range/entry'):
                                range_name = range_entry.get('name')
                                if range_name:
                                    ranges.append(range_name)
                            area_config['ranges'] = ranges

                            ospf_config['areas'].append(area_config)

                    # OSPF Interfaces
                    for iface in ospf.findall('.//interface/entry'):
                        iface_name = iface.get('name')
                        if iface_name:
                            iface_config = {
                                'interface': iface_name,
                                'enable': self._get_text(iface, 'enable') == 'yes',
                                'passive': self._get_text(iface, 'passive') == 'yes',
                                'link_type': self._get_text(iface, 'link-type'),
                                'metric': self._get_text(iface, 'metric')
                            }
                            ospf_config['interfaces'].append(iface_config)

        return ospf_config if ospf_config['enabled'] else None

    def parse_ipsec_tunnels(self) -> list[dict]:
        """Parse IPsec VPN tunnel configurations"""
        tunnels = []
        seen_names = set()

        paths = [
            ".//network/tunnel/ipsec/entry",
            ".//devices/entry/network/tunnel/ipsec/entry"
        ]

        for path in paths:
            for tunnel in self.root.findall(path):
                name = tunnel.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                tunnel_config = {
                    'name': name,
                    'tunnel_interface': self._get_text(tunnel, 'tunnel-interface'),
                    'type': 'auto-key',  # Default
                    'peer_address': None,
                    'local_address': None,
                    'auth_type': None,
                    'preshared_key': None,
                    'ike_gateway': None,
                    'ipsec_crypto_profile': None
                }

                # Check for auto-key (most common)
                auto_key = tunnel.find('auto-key')
                if auto_key is not None:
                    tunnel_config['type'] = 'auto-key'

                    # IKE Gateway. Real Panorama exports use <gateway><entry
                    # name="..."/> under <auto-key>; accept the alternate
                    # <ike-gateway> tag some tools emit as well.
                    ike_gw = auto_key.find('gateway/entry')
                    if ike_gw is None:
                        ike_gw = auto_key.find('ike-gateway/entry')
                    if ike_gw is not None:
                        tunnel_config['ike_gateway'] = ike_gw.get('name')

                    # IPsec Crypto Profile
                    ipsec_profile = auto_key.find('ipsec-crypto-profile')
                    if ipsec_profile is not None:
                        tunnel_config['ipsec_crypto_profile'] = ipsec_profile.text

                    # Proxy IDs
                    proxy_ids = []
                    for proxy in auto_key.findall('.//proxy-id/entry'):
                        proxy_name = proxy.get('name')
                        if proxy_name:
                            proxy_config = {
                                'name': proxy_name,
                                'local': self._get_text(proxy, 'local'),
                                'remote': self._get_text(proxy, 'remote'),
                                'protocol': self._get_text(proxy, 'protocol/number')
                            }
                            proxy_ids.append(proxy_config)
                    tunnel_config['proxy_ids'] = proxy_ids

                # Check for manual key
                manual_key = tunnel.find('manual-key')
                if manual_key is not None:
                    tunnel_config['type'] = 'manual-key'

                tunnels.append(tunnel_config)

        return tunnels

    def parse_ike_gateways(self) -> list[dict]:
        """Parse IKE gateway configurations"""
        gateways = []
        seen_names = set()

        paths = [
            ".//network/ike/gateway/entry",
            ".//devices/entry/network/ike/gateway/entry"
        ]

        for path in paths:
            for gw in self.root.findall(path):
                name = gw.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                gateway_config = {
                    'name': name,
                    'version': 'ikev1',  # Default
                    'peer_address': None,
                    'local_address': None,
                    'pre_shared_key': '***CHANGE_ME***',  # Generic placeholder
                    'auth_type': 'pre-shared-key',
                    'ike_crypto_profile': None,
                    'local_id': None,
                    'peer_id': None
                }

                # Version
                protocol = gw.find('protocol')
                if protocol is not None:
                    if protocol.find('ikev1') is not None:
                        gateway_config['version'] = 'ikev1'
                    elif protocol.find('ikev2') is not None:
                        gateway_config['version'] = 'ikev2'

                    # IKE Crypto Profile
                    version_node = protocol.find(gateway_config['version'])
                    if version_node is not None:
                        ike_profile = version_node.find('ike-crypto-profile')
                        if ike_profile is not None:
                            gateway_config['ike_crypto_profile'] = ike_profile.text

                # Peer address
                peer_addr = gw.find('.//peer-address/ip')
                if peer_addr is not None:
                    gateway_config['peer_address'] = peer_addr.text

                peer_fqdn = gw.find('.//peer-address/fqdn')
                if peer_fqdn is not None:
                    gateway_config['peer_address'] = peer_fqdn.text
                    gateway_config['peer_address_type'] = 'fqdn'

                # Local address
                local_addr = gw.find('.//local-address/ip')
                if local_addr is not None:
                    gateway_config['local_address'] = local_addr.text

                local_iface = gw.find('.//local-address/interface')
                if local_iface is not None:
                    gateway_config['local_address_interface'] = local_iface.text

                # Authentication
                auth = gw.find('authentication')
                if auth is not None:
                    # Check for pre-shared key (won't have actual value in export for security)
                    if auth.find('pre-shared-key') is not None:
                        gateway_config['auth_type'] = 'pre-shared-key'
                        # Note: Actual key not in export for security reasons
                        gateway_config['pre_shared_key'] = '***CHANGE_ME***'
                    elif auth.find('certificate') is not None:
                        gateway_config['auth_type'] = 'certificate'
                        cert = auth.find('certificate')
                        if cert is not None:
                            gateway_config['certificate_profile'] = self._get_text(cert, 'profile')

                # Local/Peer IDs
                gateway_config['local_id'] = self._get_text(gw, 'local-id/id')
                gateway_config['peer_id'] = self._get_text(gw, 'peer-id/id')

                gateways.append(gateway_config)

        return gateways

    def parse_ike_crypto_profiles(self) -> list[dict]:
        """Parse IKE crypto profiles"""
        profiles = []
        seen_names = set()

        paths = [
            ".//network/ike/crypto-profiles/ike-crypto-profiles/entry",
            ".//devices/entry/network/ike/crypto-profiles/ike-crypto-profiles/entry"
        ]

        for path in paths:
            for profile in self.root.findall(path):
                name = profile.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                profile_config = {
                    'name': name,
                    'dh_groups': self._get_members(profile, 'dh-group'),
                    'authentications': self._get_members(profile, 'authentication'),
                    'encryptions': self._get_members(profile, 'encryption'),
                    'lifetime_hours': self._get_text(profile, 'lifetime/hours')
                }

                profiles.append(profile_config)

        return profiles

    def parse_ipsec_crypto_profiles(self) -> list[dict]:
        """Parse IPsec crypto profiles"""
        profiles = []
        seen_names = set()

        paths = [
            ".//network/ike/crypto-profiles/ipsec-crypto-profiles/entry",
            ".//devices/entry/network/ike/crypto-profiles/ipsec-crypto-profiles/entry"
        ]

        for path in paths:
            for profile in self.root.findall(path):
                name = profile.get('name')
                if not name or name in seen_names:
                    continue

                seen_names.add(name)

                profile_config = {
                    'name': name,
                    'protocol': 'esp',  # Default
                    'encryptions': self._get_members(profile, 'esp/encryption'),
                    'authentications': self._get_members(profile, 'esp/authentication'),
                    'dh_group': self._get_text(profile, 'dh-group'),
                    'lifetime_hours': self._get_text(profile, 'lifetime/hours'),
                    'lifetime_kb': self._get_text(profile, 'lifetime/kilobytes')
                }

                # Check if AH is used instead of ESP
                if profile.find('ah') is not None:
                    profile_config['protocol'] = 'ah'
                    profile_config['authentications'] = self._get_members(profile, 'ah/authentication')

                profiles.append(profile_config)

        return profiles

    def _get_text(self, element: ET.Element, path: str) -> Optional[str]:
        """Safely get text from an XML element"""
        elem = element.find(path)
        return elem.text if elem is not None else None

    def _get_members(self, element: ET.Element, path: str) -> list[str]:
        """Get list of members from an XML element"""
        members = []
        for member in element.findall(f'.//{path}/member'):
            if member.text:
                members.append(member.text)
        return members


class HclRef:
    """A raw HCL expression (e.g. a resource reference) emitted verbatim.

    Terraform resource references such as panos_virtual_router.x.name must
    not be quoted, so they are wrapped in HclRef when passed to hcl_value().
    """
    __slots__ = ('expr',)

    def __init__(self, expr: str):
        self.expr = expr

    def __str__(self) -> str:
        # A reference leaked into an f-string still renders as valid HCL.
        return self.expr


# F2.6: resource types a .name reference may target, in lookup order.
# Object scopes come before group scopes so a name shared by both
# resolves to the object (PAN-OS policy-reference semantics).
ADDR_SCOPES = ('panos_address', 'panos_address_group')
SERVICE_SCOPES = ('panos_service', 'panos_service_group')
ZONE_SCOPES = ('panos_zone',)
INTERFACE_SCOPES = ('panos_ethernet_interface', 'panos_ethernet_layer3_subinterface')
ETH_IFACE_SCOPES = ('panos_ethernet_interface',)
TAG_SCOPES = ('panos_administrative_tag',)
IKE_CRYPTO_SCOPES = ('panos_ike_crypto_profile',)
IPSEC_CRYPTO_SCOPES = ('panos_ipsec_crypto_profile',)
IKE_GATEWAY_SCOPES = ('panos_ike_gateway',)


class TerraformGenerator:
    """Generate Terraform configuration files from Panorama data"""

    # F2.9: the v2 panos_decryption_policy_rules action is an enum, and the
    # inspection mode is a separate type block. Legacy PAN-OS 9 exports put
    # the mode in <action> instead of <type>; both shapes map to the same
    # v2 output.
    _V2_DECRYPTION_ACTIONS = ('no-decrypt', 'decrypt', 'decrypt-and-forward')
    _DECRYPTION_TYPE_KEYS = {
        'ssl-forward-proxy': 'ssl_forward_proxy',
        'ssl-inbound-inspection': 'ssl_inbound_inspection',
        'ssh-proxy': 'ssh_proxy',
    }

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Collision handling for resource names. Two different PAN-OS names
        # can sanitize to the same Terraform name (for example 'a-b' and
        # 'a_b'). The registry maps (scope, input) -> assigned name so a
        # reference site that recomputes the same input gets the same name.
        self._name_registry: dict[tuple[str, str], str] = {}
        self._taken_names: dict[str, set[str]] = {}

    def sanitize_name(self, name: str) -> str:
        """Sanitize names for Terraform resource names"""
        # Replace spaces and special characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = f'_{sanitized}'
        return sanitized.lower()

    def declare_resource_name(self, name: str, scope: str, context: str = '') -> str:
        """Assign a collision-free Terraform name for a new resource declaration.

        The local name is the sanitized PAN-OS name plus a short hash of the
        object's source identity (F2.7): the path of the entry in the export,
        made of the resource type (scope), the device group or template that
        defines it (context), and the raw PAN-OS name. The raw name is in the
        hash, not the sanitized one: names that sanitize to the same base
        ('a-b' and 'a_b') still get different digests. The hash makes the
        name deterministic. The same object always gets the same local name.
        The name does not depend on emission order or run count. Same-named
        objects in different device groups or templates stay distinct.

        If the address is already taken in the scope (a duplicate declaration
        or a digest collision), a numeric suffix follows, so the output is
        always valid HCL.
        """
        base = self.sanitize_name(name) or 'unnamed'
        digest = hashlib.sha256(f'{scope}|{context}|{name}'.encode()).hexdigest()[:8]
        candidate = f'{base}_{digest}'
        taken = self._taken_names.setdefault(scope, set())
        n = 2
        while candidate in taken:
            candidate = f'{base}_{digest}_{n}'
            n += 1
        taken.add(candidate)
        # Reference sites resolve by (scope, name); the first declaration wins
        self._name_registry.setdefault((scope, name), candidate)
        return candidate

    def name_ref(self, name: str, scopes, key: Optional[str] = None):
        """Resolve a PAN-OS name to a Terraform reference (F2.6).

        Returns an HclRef of '<scope>.<local>.name' when the object is
        declared in this run, else the plain name. Names that point at
        objects outside the export (built-ins, other tenants) stay plain
        brown-field strings, so this never creates a reference to an
        undeclared resource. `scopes` is tried in order so an object wins
        over a group when both carry the same name. `key` is the registry
        key when it differs from the PAN-OS name (VPN composite keys such
        as 'ike_gw_<name>').
        """
        lookup = key if key is not None else name
        for scope in scopes:
            local = self._name_registry.get((scope, lookup))
            if local is not None:
                return HclRef(f'{scope}.{local}.name')
        return name

    def escape_string(self, value: str) -> str:
        """Escape strings for Terraform"""
        if value is None:
            return '""'
        # Escape special characters. HCL quoted strings support the escape
        # sequences below and no other raw control characters.
        value = value.replace('\\', '\\\\')
        value = value.replace('"', '\\"')
        value = value.replace('\t', '\\t')
        value = value.replace('\r', '\\r')
        value = value.replace('\n', '\\n')
        # Strip any remaining C0 control characters and DEL.
        value = ''.join(ch for ch in value if ch >= ' ' and ch != '\x7f')
        return f'"{value}"'

    # Provider v2 requires a location block on every resource. Network and
    # VPN resources are template-scoped; objects and rules are device-group
    # scoped (verified against the v2.0.14 schema, F2.2/F2.3).
    _TEMPLATE_SCOPED_TYPES = {
        'panos_zone',
        'panos_virtual_router',
        'panos_virtual_router_static_route_ipv4',
        'panos_ethernet_interface',
        'panos_ethernet_layer3_subinterface',
        'panos_ike_crypto_profile',
        'panos_ipsec_crypto_profile',
        'panos_ike_gateway',
        'panos_ipsec_tunnel',
        # F2.9: tunnel monitor profiles are template-scoped in v2
        'panos_monitor_profile',
    }

    def location_block(self, resource_type: str, device_group: Optional[str] = None,
                       template: Optional[str] = None) -> str:
        """Required location object for a generated resource (F2.3/F2.4).

        Provider v2 requires `location` on every resource. Objects and
        rules are scoped to the device group that defined them (default
        "Shared"). Network and VPN resources are template-scoped; the
        tracked template name is used when known, otherwise the default
        "Shared" template.
        """
        if resource_type in self._TEMPLATE_SCOPED_TYPES:
            return (
                '  location = {\n'
                '    template = {\n'
                f'      name = {self.escape_string(template or "Shared")}\n'
                '    }\n'
                '  }\n'
            )
        return (
            '  location = {\n'
            '    device_group = {\n'
            f'      name = {self.escape_string(device_group or "Shared")}\n'
            '    }\n'
            '  }\n'
        )

    def hcl_value(self, value: Any, indent: str = '  ') -> str:
        """Render a Python value as an HCL expression.

        Provider v2 models nested structures as object/list arguments rather
        than blocks, so multi-line object and list syntax is required:
            key = {
              inner = "value"
            }
        Use HclRef for raw expressions (resource references) that must be
        emitted without quoting.
        """
        if isinstance(value, HclRef):
            return value.expr
        if value is True:
            return 'true'
        if value is False:
            return 'false'
        if isinstance(value, int):
            return str(value)
        if isinstance(value, str):
            return self.escape_string(value)
        if isinstance(value, dict):
            if not value:
                return '{}'
            parts = [f'{indent}  {k} = ' + self.hcl_value(v, indent + '  ')
                     for k, v in value.items()]
            return '{\n' + '\n'.join(parts) + f'\n{indent}}}'
        if isinstance(value, (list, tuple)):
            if not value:
                return '[]'
            if all(not isinstance(item, (dict, list)) for item in value):
                # Primitive lists stay inline
                return '[ ' + ', '.join(self.hcl_value(item, '') for item in value) + ' ]'
            parts = [self.hcl_value(item, indent + '  ') for item in value]
            return '[\n' + ',\n'.join(parts) + f'\n{indent}]'
        raise TypeError(f'Cannot render {type(value)} as HCL')

    def generate_provider_config(self):
        """Generate provider.tf file"""
        content = '''# Palo Alto Networks PAN-OS Provider Configuration
# Supported provider range: v2 series, baseline 2.0.14 (the latest 2.x
# release and the version the conformance and validate gates verify).
terraform {
  required_providers {
    panos = {
      source  = "PaloAltoNetworks/panos"
      version = "~> 2.0.14"
    }
  }
}

provider "panos" {
  # Configure these variables or use environment variables:
  # PANOS_HOSTNAME, PANOS_USERNAME, PANOS_PASSWORD
  # hostname = var.panos_hostname
  # username = var.panos_username
  # password = var.panos_password
}
'''

        with open(self.output_dir / 'provider.tf', 'w') as f:
            f.write(content)

    def generate_variables(self):
        """Generate variables.tf file"""
        content = '''# Variables for Palo Alto Configuration
variable "panos_hostname" {
  description = "Hostname or IP of the Palo Alto firewall/Panorama"
  type        = string
  sensitive   = true
}

variable "panos_username" {
  description = "Username for authentication"
  type        = string
  sensitive   = true
}

variable "panos_password" {
  description = "Password for authentication"
  type        = string
  sensitive   = true
}

variable "device_group" {
  description = "Device group name for Panorama"
  type        = string
  default     = "shared"
}
'''

        with open(self.output_dir / 'variables.tf', 'w') as f:
            f.write(content)

    def generate_address_objects(self, addresses: list[dict]):
        """Generate address object Terraform configuration (v2: panos_address)

        The v2 schema exposes one attribute per address type (ip_netmask,
        ip_range, fqdn, ip_wildcard) instead of a generic value attribute.
        """
        if not addresses:
            return

        content = '# Address Objects\n\n'

        for addr in addresses:
            resource_name = self.declare_resource_name(
                addr['name'], 'panos_address', context=addr.get('device_group') or ''
            )

            content += f'resource "panos_address" "{resource_name}" {{\n'
            content += self.location_block('panos_address', addr.get('device_group'))
            content += f'  name = {self.escape_string(addr["name"])}\n'

            if addr.get('description'):
                content += f'  description = {self.escape_string(addr["description"])}\n'

            value = (addr.get('value') or '').strip()
            if value:
                attr = self._address_type_attribute(addr.get('type', 'ip-netmask'))
                content += f'  {attr} = {self.escape_string(value)}\n'

            if addr.get('tags'):
                # F2.6: tags declared in this run become references
                tags_str = ', '.join([
                    self.hcl_value(self.name_ref(t, TAG_SCOPES), '') for t in addr['tags']
                ])
                content += f'  tags = [{tags_str}]\n'

            content += '}\n\n'

        with open(self.output_dir / 'address_objects.tf', 'w') as f:
            f.write(content)

    @staticmethod
    def _address_type_attribute(addr_type: str) -> str:
        """Map the parser address type to the v2 panos_address attribute."""
        mapping = {
            'ip-netmask': 'ip_netmask',
            'ip-range': 'ip_range',
            'ip-wildcard': 'ip_wildcard',
            'fqdn': 'fqdn',
        }
        return mapping.get(addr_type, 'ip_netmask')

    def generate_address_groups(self, groups: list[dict]):
        """Generate address group Terraform configuration (v2: panos_address_group)"""
        if not groups:
            return

        content = '# Address Groups\n\n'

        for grp in groups:
            static_members = grp.get('static_members') or []
            dynamic_filter = (grp.get('dynamic_filter') or '').strip()

            # The v2 provider requires exactly one of the static member list
            # or the dynamic filter; an empty group would be invalid, so it is
            # kept visible as a comment instead of a resource.
            if not static_members and not dynamic_filter:
                content += f'# NOTE: address group {grp["name"]} has no members or filter; configure manually\n\n'
                continue

            resource_name = self.declare_resource_name(
                grp['name'], 'panos_address_group', context=grp.get('device_group') or ''
            )

            content += f'resource "panos_address_group" "{resource_name}" {{\n'
            content += self.location_block('panos_address_group', grp.get('device_group'))
            content += f'  name = {self.escape_string(grp["name"])}\n'

            if grp.get('description'):
                content += f'  description = {self.escape_string(grp["description"])}\n'

            if static_members:
                # F2.6: members declared in this run become references
                members_str = ', '.join([
                    self.hcl_value(self.name_ref(m, ADDR_SCOPES), '') for m in static_members
                ])
                content += f'  static = [{members_str}]\n'

            # v2 dynamic groups: the filter expression lives in dynamic.dynamic
            if dynamic_filter:
                content += f'  dynamic = {self.hcl_value({"dynamic": {"filter": dynamic_filter}})}\n'

            content += '}\n\n'

        with open(self.output_dir / 'address_groups.tf', 'w') as f:
            f.write(content)

    def generate_service_objects(self, services: list[dict]):
        """Generate service object Terraform configuration (v2: panos_service)

        The v2 schema nests the port inside a protocol block:
        protocol { tcp { destination_port = "..." } }
        """
        if not services:
            return

        content = '# Service Objects\n\n'

        for svc in services:
            resource_name = self.declare_resource_name(
                svc['name'], 'panos_service', context=svc.get('device_group') or ''
            )

            content += f'resource "panos_service" "{resource_name}" {{\n'
            content += self.location_block('panos_service', svc.get('device_group'))
            content += f'  name = {self.escape_string(svc["name"])}\n'

            if svc.get('description'):
                content += f'  description = {self.escape_string(svc["description"])}\n'

            # v2 protocol is a nested object: protocol = { tcp = { destination_port = "..." } }
            protocol = svc.get('protocol', 'tcp')
            if protocol in ('tcp', 'udp'):
                inner: dict = {}
                if svc.get('port'):
                    inner['destination_port'] = str(svc['port'])
                content += f'  protocol = {self.hcl_value({protocol: inner})}\n'
            else:
                # v2 only models tcp/udp; note the protocol for manual review
                content += f'  # NOTE: protocol {protocol} is not modeled by the v2 schema; review manually\n'

            content += '}\n\n'

        with open(self.output_dir / 'service_objects.tf', 'w') as f:
            f.write(content)

    def generate_service_groups(self, groups: list[dict]):
        """Generate service group Terraform configuration (v2: panos_service_group)

        Note: the v2 panos_service_group schema has no description attribute.
        """
        if not groups:
            return

        content = '# Service Groups\n\n'

        for grp in groups:
            resource_name = self.declare_resource_name(
                grp['name'], 'panos_service_group', context=grp.get('device_group') or ''
            )

            content += f'resource "panos_service_group" "{resource_name}" {{\n'
            content += self.location_block('panos_service_group', grp.get('device_group'))
            content += f'  name = {self.escape_string(grp["name"])}\n'

            if grp.get('members'):
                # F2.6: members declared in this run become references
                members_str = ', '.join([
                    self.hcl_value(self.name_ref(m, SERVICE_SCOPES), '') for m in grp['members']
                ])
                content += f'  members = [{members_str}]\n'

            content += '}\n\n'

        with open(self.output_dir / 'service_groups.tf', 'w') as f:
            f.write(content)

    def generate_tags(self, tags: list[dict]):
        """Generate tag Terraform configuration (v2: panos_administrative_tag)

        The v2 schema uses comments (not comment/description) for the tag text.
        """
        if not tags:
            return

        content = '# Tags\n\n'

        for tag in tags:
            resource_name = self.declare_resource_name(
                tag['name'], 'panos_administrative_tag', context=tag.get('device_group') or ''
            )

            content += f'resource "panos_administrative_tag" "{resource_name}" {{\n'
            content += self.location_block('panos_administrative_tag', tag.get('device_group'))
            content += f'  name = {self.escape_string(tag["name"])}\n'

            # v2 uses numeric color names (color1..colorN); PAN-OS exports use
            # the color words in the GUI order (red, orange, yellow, green, ...)
            color_map = {
                'red': 'color1', 'orange': 'color2', 'yellow': 'color3',
                'green': 'color4', 'blue': 'color5', 'purple': 'color6',
                'gray': 'color7',
            }
            tag_color = (tag.get('color') or '').lower()
            if tag_color in color_map:
                content += f'  color = {self.escape_string(color_map[tag_color])}\n'

            # Parser stores the tag text in comments (or description)
            tag_text = tag.get('comments') or tag.get('description')
            if tag_text:
                content += f'  comments = {self.escape_string(tag_text)}\n'

            content += '}\n\n'

        with open(self.output_dir / 'tags.tf', 'w') as f:
            f.write(content)

    def generate_custom_url_categories(self, categories: list[dict]):
        """Generate custom URL category Terraform configuration (v2: panos_custom_url_category)"""
        if not categories:
            return

        content = '# Custom URL Categories\n\n'

        for cat in categories:
            resource_name = self.declare_resource_name(
                cat['name'], 'panos_custom_url_category', context=cat.get('device_group') or ''
            )

            content += f'resource "panos_custom_url_category" "{resource_name}" {{\n'
            content += self.location_block('panos_custom_url_category', cat.get('device_group'))
            content += f'  name = {self.escape_string(cat["name"])}\n'

            if cat.get('type'):
                content += f'  type = {self.escape_string(cat["type"])}\n'

            if cat.get('description'):
                content += f'  description = {self.escape_string(cat["description"])}\n'

            if cat.get('list'):
                sites_str = ', '.join([self.escape_string(url) for url in cat['list']])
                content += f'  list = [{sites_str}]\n'

            content += '}\n\n'

        with open(self.output_dir / 'custom_url_categories.tf', 'w') as f:
            f.write(content)

    def generate_application_groups(self, app_groups: list[dict]):
        """Generate application group Terraform configuration (v2: panos_application_group)"""
        if not app_groups:
            return

        content = '# Application Groups\n\n'

        for ag in app_groups:
            resource_name = self.declare_resource_name(
                ag['name'], 'panos_application_group', context=ag.get('device_group') or ''
            )

            content += f'resource "panos_application_group" "{resource_name}" {{\n'
            content += self.location_block('panos_application_group', ag.get('device_group'))
            content += f'  name = {self.escape_string(ag["name"])}\n'

            if ag.get('members'):
                members_str = ', '.join([self.escape_string(m) for m in ag['members']])
                content += f'  members = [{members_str}]\n'

            content += '}\n\n'

        with open(self.output_dir / 'application_groups.tf', 'w') as f:
            f.write(content)

    # NOTE: application filters have no v2 resource (see resource_mapping.py).
    # Their parsed data goes to MANUAL_SETUP_REPORT.txt instead.

    def generate_external_lists(self, ext_lists: list[dict]):
        """Generate external dynamic list Terraform configuration

        v2: panos_external_dynamic_list. The v2 schema nests the fetch details
        inside a type block keyed by the list type (ip, domain, url, ...).
        """
        if not ext_lists:
            return

        content = '# External Dynamic Lists\n\n'

        # List types the v2 schema models inside the type block
        v2_types = ('domain', 'imei', 'imsi', 'ip', 'predefined_ip', 'predefined_url', 'url')
        recurring_keys = ('daily', 'five_minute', 'hourly', 'monthly', 'weekly')

        for ext_list in ext_lists:
            resource_name = self.declare_resource_name(
                ext_list['name'], 'panos_external_dynamic_list', context=ext_list.get('device_group') or ''
            )

            content += f'resource "panos_external_dynamic_list" "{resource_name}" {{\n'
            content += self.location_block('panos_external_dynamic_list', ext_list.get('device_group'))
            content += f'  name = {self.escape_string(ext_list["name"])}\n'

            # v2 type is a nested object keyed by list type
            lt = ext_list.get('type') or 'ip'
            if lt in v2_types:
                type_obj: dict = {}
                if ext_list.get('url'):
                    type_obj['url'] = ext_list['url']
                recurring = ext_list.get('recurring')
                if recurring in recurring_keys:
                    type_obj['recurring'] = {recurring: {}}
                if ext_list.get('description'):
                    type_obj['description'] = ext_list['description']
                content += f'  type = {self.hcl_value({lt: type_obj})}\n'
            else:
                # Unknown list type: keep the data visible for manual review
                content += f'  # NOTE: list type {lt} is not modeled by the v2 schema; review manually\n'
                if ext_list.get('url'):
                    content += f'  # url = {ext_list["url"]}\n'

            content += '}\n\n'

        with open(self.output_dir / 'external_lists.tf', 'w') as f:
            f.write(content)

    def _policy_rule_chains(self, rules: list[dict]) -> list[list[dict]]:
        """Group policy rules into per-device-group chains (F2.5).

        The provider places each rule relative to a pivot rule, so rules
        must emit as independent chains per device group. XML document
        order is preserved within a chain; chains appear in first-seen
        order.
        """
        chains: dict[str, list[dict]] = {}
        for rule in rules:
            chains.setdefault(rule.get('device_group') or 'Shared', []).append(rule)
        return list(chains.values())

    def _policy_position_block(self, resource_type: str,
                              prev_rule_name: Optional[str],
                              prev_resource_name: Optional[str]) -> str:
        """Render position (and depends_on) for one rule in a chain (F2.5).

        The first rule of a chain anchors the managed block at the end of
        the rulebase, the least disruptive choice for a brown-field
        rulebase. Each later rule is placed directly after the previous
        rule (the provider requires pivot and directly together when
        where = "after"). The provider fails when the pivot is missing,
        so the rule also declares depends_on on the previous rule's
        resource to fix the apply order to the XML order.
        """
        if prev_rule_name is None:
            return f'  position = {self.hcl_value({"where": "last"})}\n\n'
        position = {'where': 'after', 'directly': True, 'pivot': prev_rule_name}
        return (
            f'  position = {self.hcl_value(position)}\n'
            f'  depends_on = [ {resource_type}.{prev_resource_name} ]\n\n'
        )

    def generate_security_rules(self, rules: list[dict]):
        """Generate security policy rules Terraform configuration (F2.5).

        v2: panos_security_policy_rules. One resource per rule, chained
        per device group in XML order with order-preserving position
        values (first rule at the end of the rulebase, each later rule
        directly after the previous one).
        """
        if not rules:
            return

        content = '# Security Policy Rules\n\n'

        for chain in self._policy_rule_chains(rules):
            prev_rule_name: Optional[str] = None
            prev_resource_name: Optional[str] = None
            for rule in chain:
                resource_name = self.declare_resource_name(
                    rule['name'], 'panos_security_policy_rules', context=rule.get('device_group') or ''
                )

                content += f'resource "panos_security_policy_rules" "{resource_name}" {{\n'
                content += self.location_block('panos_security_policy_rules', rule.get('device_group'))
                content += self._policy_position_block(
                    'panos_security_policy_rules', prev_rule_name, prev_resource_name
                )

                # v2 rules is a list of objects
                rule_obj: dict = {'name': rule['name']}
                if rule.get('description'):
                    rule_obj['description'] = rule['description']
                # F2.6: zones, addresses and services declared in this run
                # become references; the rest stay brown-field strings
                if rule.get('source_zones'):
                    rule_obj['source_zones'] = [self.name_ref(z, ZONE_SCOPES) for z in rule['source_zones']]
                if rule.get('source_addresses'):
                    rule_obj['source_addresses'] = [self.name_ref(a, ADDR_SCOPES) for a in rule['source_addresses']]
                if rule.get('destination_zones'):
                    rule_obj['destination_zones'] = [self.name_ref(z, ZONE_SCOPES) for z in rule['destination_zones']]
                if rule.get('destination_addresses'):
                    rule_obj['destination_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES) for a in rule['destination_addresses']]
                if rule.get('applications'):
                    # Built-in PAN-OS app names: no managed scope, never wired
                    rule_obj['applications'] = list(rule['applications'])
                if rule.get('services'):
                    rule_obj['services'] = [self.name_ref(s, SERVICE_SCOPES) for s in rule['services']]
                rule_obj['action'] = rule.get('action', 'allow')
                if rule.get('log_start'):
                    rule_obj['log_start'] = True
                if rule.get('log_end'):
                    rule_obj['log_end'] = True
                if rule.get('disabled'):
                    rule_obj['disabled'] = True

                content += f'  rules = {self.hcl_value([rule_obj])}\n'
                content += '}\n\n'

                prev_rule_name = rule['name']
                prev_resource_name = resource_name

        with open(self.output_dir / 'security_rules.tf', 'w') as f:
            f.write(content)

    def generate_nat_rules(self, rules: list[dict]):
        """Generate NAT policy rules Terraform configuration (F2.5).

        v2: panos_nat_policy_rules. One resource per rule, chained per
        device group in XML order with the same order-preserving position
        semantics as security rules. Translation is modeled as a
        source_translation block with one of dynamic_ip_and_port, dynamic_ip,
        or static_ip sub-blocks (v2 names use underscores).
        """
        if not rules:
            return

        content = '# NAT Policy Rules\n\n'

        for chain in self._policy_rule_chains(rules):
            prev_rule_name: Optional[str] = None
            prev_resource_name: Optional[str] = None
            for rule in chain:
                resource_name = self.declare_resource_name(
                    rule['name'], 'panos_nat_policy_rules', context=rule.get('device_group') or ''
                )

                content += f'resource "panos_nat_policy_rules" "{resource_name}" {{\n'
                content += self.location_block('panos_nat_policy_rules', rule.get('device_group'))
                content += self._policy_position_block(
                    'panos_nat_policy_rules', prev_rule_name, prev_resource_name
                )

                # v2 rules is a list of objects
                rule_obj: dict = {'name': rule['name']}
                if rule.get('description'):
                    rule_obj['description'] = rule['description']
                # F2.6: zones, addresses and services declared in this run
                # become references; the rest stay brown-field strings
                if rule.get('source_zones'):
                    rule_obj['source_zones'] = [self.name_ref(z, ZONE_SCOPES) for z in rule['source_zones']]
                # v2 destination_zone is a list
                if rule.get('destination_zone'):
                    rule_obj['destination_zone'] = [self.name_ref(rule['destination_zone'], ZONE_SCOPES)]
                if rule.get('source_addresses'):
                    rule_obj['source_addresses'] = [self.name_ref(a, ADDR_SCOPES) for a in rule['source_addresses']]
                if rule.get('destination_addresses'):
                    rule_obj['destination_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES) for a in rule['destination_addresses']]
                if rule.get('service'):
                    rule_obj['service'] = self.name_ref(rule['service'], SERVICE_SCOPES)
                if rule.get('disabled'):
                    rule_obj['disabled'] = True

                # Source translation (v2 sub-object names use underscores)
                st_type = (rule.get('source_translation_type') or '').replace('-', '_')
                st_addr = rule.get('source_translation_address') or []
                if st_type in ('dynamic_ip_and_port', 'dynamic_ip', 'static_ip'):
                    # v2 nat_type is the NAT family (ipv4/nat64/nptv6), not the
                    # translation direction; IPv4 is the Panorama default family
                    rule_obj['nat_type'] = 'ipv4'
                    if st_type == 'dynamic_ip_and_port' and st_addr:
                        # The translation address is the egress interface
                        # (F2.6: reference when declared in this run)
                        rule_obj['source_translation'] = {
                            st_type: {'interface_address': {
                                'interface': self.name_ref(st_addr[0], INTERFACE_SCOPES)}}}
                    elif st_type == 'dynamic_ip' and st_addr:
                        rule_obj['source_translation'] = {
                            st_type: {'translated_address': list(st_addr)}}
                    elif st_type == 'static_ip' and st_addr:
                        # static_ip takes a single translated address
                        rule_obj['source_translation'] = {
                            st_type: {'translated_address': st_addr[0]}}

                # Destination translation (the direction is implied by which
                # translation object is present, not by nat_type)
                if rule.get('destination_translation_address'):
                    dst: dict = {'translated_address': rule['destination_translation_address']}
                    if rule.get('destination_translation_port'):
                        dst['translated_port'] = int(rule['destination_translation_port'])
                    rule_obj['destination_translation'] = dst

                content += f'  rules = {self.hcl_value([rule_obj])}\n'
                content += '}\n\n'

                prev_rule_name = rule['name']
                prev_resource_name = resource_name

        with open(self.output_dir / 'nat_rules.tf', 'w') as f:
            f.write(content)

    def generate_decryption_rules(self, rules: list[dict]):
        """Generate decryption policy rules (F2.9: real v2 resources).

        v2.0.14 has no decryption rule container: each rule is its own
        `panos_decryption_policy_rules` resource with a position argument.
        Rules chain per device group exactly like security and NAT rules
        (F2.5): the first rule anchors at the end of the rulebase and each
        later rule is placed directly after the previous one with a
        depends_on on it, so Terraform applies the chain in XML order.
        The parser captures the full rule, so real emission is safe.
        """
        if not rules:
            return

        content = '# Decryption Policy Rules (F2.9: real v2 resources)\n'
        content += '# One panos_decryption_policy_rules resource per rule; per-device-group\n'
        content += '# chains preserve XML order (F2.5).\n\n'

        for chain in self._policy_rule_chains(rules):
            prev_rule_name: Optional[str] = None
            prev_resource_name: Optional[str] = None
            for rule in chain:
                device_group = rule.get('device_group') or 'Shared'
                resource_name = self.declare_resource_name(
                    rule['name'], 'panos_decryption_policy_rules', context=device_group
                )

                content += f'resource "panos_decryption_policy_rules" "{resource_name}" {{\n'
                content += self.location_block('panos_decryption_policy_rules', device_group)
                content += self._policy_position_block(
                    'panos_decryption_policy_rules', prev_rule_name, prev_resource_name
                )

                rule_obj: dict = {'name': rule['name']}
                if rule.get('description'):
                    rule_obj['description'] = rule['description']
                # F2.6: zones, addresses and services declared in this run
                # become references; the rest stay brown-field strings
                if rule.get('source_zones'):
                    rule_obj['source_zones'] = [
                        self.name_ref(z, ZONE_SCOPES) for z in rule['source_zones']]
                if rule.get('destination_zones'):
                    rule_obj['destination_zones'] = [
                        self.name_ref(z, ZONE_SCOPES) for z in rule['destination_zones']]
                if rule.get('source_addresses'):
                    rule_obj['source_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES) for a in rule['source_addresses']]
                if rule.get('destination_addresses'):
                    rule_obj['destination_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES) for a in rule['destination_addresses']]
                if rule.get('source_users'):
                    rule_obj['source_user'] = list(rule['source_users'])
                if rule.get('categories'):
                    rule_obj['category'] = list(rule['categories'])
                if rule.get('services'):
                    rule_obj['services'] = [
                        self.name_ref(s, SERVICE_SCOPES) for s in rule['services']]
                # F2.9: the v2 action is an enum (no-decrypt | decrypt |
                # decrypt-and-forward) and the inspection mode is a separate
                # type block. Modern PAN-OS exports carry both; legacy PAN-OS
                # 9 exports put the mode in <action> instead, so map it.
                # Unknown actions pass through and fail terraform validate
                # explicitly rather than being silently reinterpreted.
                action = rule.get('action')
                type_key = self._DECRYPTION_TYPE_KEYS.get(rule.get('type'))
                if action in self._V2_DECRYPTION_ACTIONS:
                    rule_obj['action'] = action
                elif action in self._DECRYPTION_TYPE_KEYS:
                    rule_obj['action'] = 'decrypt'
                    type_key = type_key or self._DECRYPTION_TYPE_KEYS[action]
                elif action:
                    rule_obj['action'] = action
                if type_key:
                    rule_obj['type'] = {type_key: {}}
                if rule.get('profile'):
                    rule_obj['profile'] = rule['profile']
                if rule.get('log_setting'):
                    rule_obj['log_setting'] = rule['log_setting']
                if rule.get('log_start'):
                    rule_obj['log_success'] = True
                if rule.get('log_end'):
                    rule_obj['log_fail'] = True
                if rule.get('disabled'):
                    rule_obj['disabled'] = True

                content += f'  rules = {self.hcl_value([rule_obj])}\n'
                content += '}\n\n'

                prev_rule_name = rule['name']
                prev_resource_name = resource_name

        with open(self.output_dir / 'decryption_rules.tf', 'w') as f:
            f.write(content)

    def generate_pbf_rules(self, rules: list[dict]):
        """Generate Policy-Based Forwarding rules (F2.9: real v2 resources).

        v2.0.14 has no PBF rule container: each rule is its own
        `panos_pbf_policy_rules` resource. The chain semantics match the
        other policy rulebases (F2.5). The action is a single-choice
        object: forward, discard, no_pbf, or forward_to_vsys.
        """
        if not rules:
            return

        content = '# Policy-Based Forwarding Rules (F2.9: real v2 resources)\n'
        content += '# One panos_pbf_policy_rules resource per rule; per-device-group\n'
        content += '# chains preserve XML order (F2.5).\n\n'

        for chain in self._policy_rule_chains(rules):
            prev_rule_name: Optional[str] = None
            prev_resource_name: Optional[str] = None
            for rule in chain:
                device_group = rule.get('device_group') or 'Shared'
                resource_name = self.declare_resource_name(
                    rule['name'], 'panos_pbf_policy_rules', context=device_group
                )

                content += f'resource "panos_pbf_policy_rules" "{resource_name}" {{\n'
                content += self.location_block('panos_pbf_policy_rules', device_group)
                content += self._policy_position_block(
                    'panos_pbf_policy_rules', prev_rule_name, prev_resource_name
                )

                rule_obj: dict = {'name': rule['name']}
                if rule.get('description'):
                    rule_obj['description'] = rule['description']
                # v2 models the PBF source as from { zone = [...] }
                if rule.get('source_zones'):
                    rule_obj['from'] = {
                        'zone': [self.name_ref(z, ZONE_SCOPES) for z in rule['source_zones']]}
                if rule.get('source_addresses'):
                    rule_obj['source_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES) for a in rule['source_addresses']]
                if rule.get('source_users'):
                    rule_obj['source_users'] = list(rule['source_users'])
                if rule.get('destination_addresses'):
                    rule_obj['destination_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES) for a in rule['destination_addresses']]
                if rule.get('applications'):
                    rule_obj['applications'] = list(rule['applications'])
                if rule.get('services'):
                    rule_obj['services'] = [
                        self.name_ref(s, SERVICE_SCOPES) for s in rule['services']]
                # Single-choice action object (v2 names use underscores)
                action = rule.get('action')
                if action:
                    kind = action.get('type')
                    if kind == 'forward':
                        forward: dict = {}
                        if action.get('nexthop_ip'):
                            forward['nexthop'] = {'ip_address': action['nexthop_ip']}
                        if action.get('egress_interface'):
                            forward['egress_interface'] = action['egress_interface']
                        # F2.9: optional path monitoring; the profile name
                        # references a panos_monitor_profile resource
                        monitor = action.get('monitor')
                        if monitor:
                            monitor_out: dict = {}
                            if monitor.get('ip_address'):
                                monitor_out['ip_address'] = monitor['ip_address']
                            if monitor.get('profile'):
                                monitor_out['profile'] = monitor['profile']
                            if monitor.get('disable_if_unreachable'):
                                monitor_out['disable_if_unreachable'] = True
                            if monitor_out:
                                forward['monitor'] = monitor_out
                        rule_obj['action'] = {'forward': forward}
                    elif kind == 'discard':
                        rule_obj['action'] = {'discard': {}}
                    elif kind == 'no-pbf':
                        rule_obj['action'] = {'no_pbf': {}}
                    elif kind == 'forward_to_vsys' and action.get('vsys'):
                        rule_obj['action'] = {'forward_to_vsys': action['vsys']}
                if rule.get('enforce_symmetric_return'):
                    rule_obj['enforce_symmetric_return'] = {'enabled': True}
                if rule.get('schedule'):
                    rule_obj['schedule'] = rule['schedule']
                if rule.get('disabled'):
                    rule_obj['disabled'] = True

                content += f'  rules = {self.hcl_value([rule_obj])}\n'
                content += '}\n\n'

                prev_rule_name = rule['name']
                prev_resource_name = resource_name

        with open(self.output_dir / 'pbf_rules.tf', 'w') as f:
            f.write(content)

    def generate_pbf_monitor_profiles(self, profiles: list[dict]):
        """Generate PBF path monitoring profiles (F2.9: real v2 resources).

        v2.0.14 exposes these as `panos_monitor_profile`, template-scoped.
        The parser captures the complete profile (action, interval,
        threshold), so real emission is safe. The v2 schema has no
        description attribute, so none is emitted. The v2 action is an enum
        (wait-recover | fail-over); values outside the enum will fail
        `terraform validate`, which is the intended behavior for a
        malformed source export.
        """
        if not profiles:
            return

        content = '# PBF Path Monitoring Profiles (F2.9: real v2 resources)\n\n'

        for prof in profiles:
            resource_name = self.declare_resource_name(
                prof['name'], 'panos_monitor_profile'
            )
            content += f'resource "panos_monitor_profile" "{resource_name}" {{\n'
            # Template-scoped; the tracked template name is unknown at
            # parse time, so the default "Shared" template is used (same
            # convention as the other template-scoped types, F2.3/F2.4)
            content += self.location_block('panos_monitor_profile')
            content += f'  name = {self.escape_string(prof["name"])}\n'
            for attr in ('interval', 'threshold'):
                raw = prof.get(attr)
                # The v2 schema takes numbers; skip values that are not
                # plain integers so the output always validates
                if raw is not None and str(raw).isdigit():
                    content += f'  {attr} = {int(raw)}\n'
            if prof.get('action'):
                content += f'  action = {self.escape_string(prof["action"])}\n'
            content += '}\n\n'

        with open(self.output_dir / 'monitor_profiles.tf', 'w') as f:
            f.write(content)


    def generate_zones(self, zones: list[dict]):
        """Generate zone Terraform configuration (v2: panos_zone)

        The v2 schema nests membership in a network block:
        network { layer3 = [...] } or network { layer2 = [...] }
        """
        if not zones:
            return

        content = '# Zone Configurations\n\n'

        for zone in zones:
            resource_name = self.declare_resource_name(zone['name'], 'panos_zone', context=zone.get('template') or '')

            content += f'resource "panos_zone" "{resource_name}" {{\n'
            content += self.location_block('panos_zone', template=zone.get('template'))
            content += f'  name = {self.escape_string(zone["name"])}\n'

            # v2 network object: membership list is keyed by layer type
            ztype = zone.get('type') or 'layer3'
            key = 'layer2' if ztype == 'layer2' else 'layer3'
            network: dict = {}
            if zone.get('interfaces'):
                # F2.6: interfaces declared in this run become references
                network[key] = [self.name_ref(i, INTERFACE_SCOPES) for i in zone['interfaces']]
            if zone.get('zone_protection_profile'):
                network['zone_protection_profile'] = zone['zone_protection_profile']
            if network:
                content += f'  network = {self.hcl_value(network)}\n'

            content += '}\n\n'

        with open(self.output_dir / 'zones.tf', 'w') as f:
            f.write(content)

    def generate_virtual_routers(self, vrouters: list[dict]):
        """Generate virtual router Terraform configuration (v2: panos_virtual_router)

        Logical routers (Advanced Routing Engine) emit the same v2 resource.
        Static routes use the v2 panos_virtual_router_static_route_ipv4
        resource and reference the owning virtual router resource.
        """
        if not vrouters:
            return

        content = '# Router Configurations\n'
        content += '# Supports both Virtual Routers (legacy) and Logical Routers (Advanced Routing Engine)\n\n'

        for router in vrouters:
            resource_name = self.declare_resource_name(
                router['name'], 'panos_virtual_router', context=router.get('template') or ''
            )

            # Add comment showing source and type
            template = router.get('template', 'unknown')
            content += f'# Source: {template}\n'
            router_type = router.get('router_type', 'virtual')
            if router_type == 'logical':
                rtype = 'Logical Router (Advanced Routing Engine)'
            else:
                rtype = 'Virtual Router (Legacy)'
            content += f'# Type: {rtype}\n'

            content += f'resource "panos_virtual_router" "{resource_name}" {{\n'
            content += self.location_block('panos_virtual_router', template=router.get('template'))
            content += f'  name = {self.escape_string(router["name"])}\n'

            # v2 interfaces is a flat string list
            if router.get('interfaces'):
                # F2.6: interfaces declared in this run become references
                ifaces_str = ', '.join([
                    self.hcl_value(self.name_ref(i, INTERFACE_SCOPES), '') for i in router['interfaces']
                ])
                content += f'  interfaces = [{ifaces_str}]\n'

            content += '}\n\n'

            # Generate static routes (v2: panos_virtual_router_static_route_ipv4)
            if router.get('static_routes'):
                for route in router['static_routes']:
                    route_key = f"{resource_name}_{route['name']}"
                    route_resource = self.declare_resource_name(
                        route_key, 'panos_virtual_router_static_route_ipv4', context=router.get('template') or ''
                    )

                    content += f'resource "panos_virtual_router_static_route_ipv4" "{route_resource}" {{\n'
                    content += self.location_block(
                        'panos_virtual_router_static_route_ipv4',
                        template=router.get('template'))
                    content += f'  name = {self.escape_string(route["name"])}\n'
                    # Reference the owning virtual router resource
                    content += f'  virtual_router = panos_virtual_router.{resource_name}.name\n'

                    if route.get('destination'):
                        # PAN-OS exports the default route destination as "default"
                        destination = route['destination']
                        if destination == 'default':
                            destination = '0.0.0.0/0'
                        content += f'  destination = {self.escape_string(destination)}\n'

                    if route.get('nexthop_ip'):
                        # v2 nexthop is a nested object
                        content += f'  nexthop = {self.hcl_value({"ip_address": route["nexthop_ip"]})}\n'
                    elif route.get('nexthop_interface'):
                        content += f'  interface = {self.escape_string(route["nexthop_interface"])}\n'

                    metric = route.get('metric')
                    if metric is not None:
                        try:
                            metric = int(metric)
                        except (TypeError, ValueError):
                            metric = None
                    if metric is not None:
                        content += f'  metric = {metric}\n'

                    content += '}\n\n'

        with open(self.output_dir / 'virtual_routers.tf', 'w') as f:
            f.write(content)

    def generate_ethernet_interfaces(self, interfaces: list[dict]):
        """Generate ethernet interface Terraform configuration (v2: panos_ethernet_interface)

        The v2 panos_ethernet_interface has no ipv4 attribute: IPv4
        addresses on a physical L3 interface are modeled on its .0 layer-3
        subinterface via panos_ethernet_layer3_subinterface.
        """
        if not interfaces:
            return

        content = '# Ethernet Interface Configurations\n'
        content += '# Note: These are reference configurations. Adjust for your hardware platform.\n\n'

        for iface in interfaces:
            if iface['type'] != 'ethernet':
                continue

            name = iface['name']
            mode = iface.get('mode')
            parent, dot, tag_str = name.partition('.')

            # Tagged L3 subinterface (ethernet1/2.10): v2 subinterface resource
            if dot and mode == 'layer3':
                resource_name = self.declare_resource_name(
                    name, 'panos_ethernet_layer3_subinterface', context=iface.get('template') or ''
                )
                content += f'resource "panos_ethernet_layer3_subinterface" "{resource_name}" {{\n'
                content += self.location_block('panos_ethernet_layer3_subinterface', template=iface.get('template'))
                content += f'  name = {self.escape_string(name)}\n'
                # F2.6: the parent is an interface declared in this run
                # (or a brown-field interface outside the export)
                content += f"  parent = {self.hcl_value(self.name_ref(parent, ETH_IFACE_SCOPES), '')}\n"
                if tag_str.isdigit():
                    content += f'  tag = {int(tag_str)}\n'
                if iface.get('management_profile'):
                    content += f'  interface_management_profile = {self.escape_string(iface["management_profile"])}\n'
                self._emit_subinterface_ip(content, iface)
                content += '}\n\n'
                continue

            # Physical interface
            resource_name = self.declare_resource_name(
                name, 'panos_ethernet_interface', context=iface.get('template') or ''
            )
            content += f'resource "panos_ethernet_interface" "{resource_name}" {{\n'
            content += self.location_block('panos_ethernet_interface', template=iface.get('template'))
            content += f'  name = {self.escape_string(name)}\n'

            if iface.get('comment'):
                content += f'  comment = {self.escape_string(iface["comment"])}\n'

            # The v2 layer3/layer2 object signals the interface mode
            if mode == 'layer3':
                l3: dict = {}
                if iface.get('management_profile'):
                    l3['interface_management_profile'] = iface['management_profile']
                content += f'  layer3 = {self.hcl_value(l3)}\n'
            elif mode == 'layer2':
                content += '  layer2 = {}\n'
            elif mode:
                # tap, virtual-wire, ha, aggregate-group: note for manual review
                content += f'  # NOTE: mode {mode} requires manual review (v2 block shape not modeled)\n'

            if iface.get('ipv6_addresses'):
                v6_str = ', '.join(iface['ipv6_addresses'])
                content += f'  # NOTE: IPv6 addresses ({v6_str}) require manual configuration on the .0 subinterface\n'

            content += '}\n\n'

            # v2 has no ipv4 attribute on the interface: IPv4 lives on the .0 subinterface
            if mode == 'layer3' and iface.get('ip_addresses'):
                sub_name = f'{name}.0'
                sub_resource = self.declare_resource_name(
                    sub_name, 'panos_ethernet_layer3_subinterface', context=iface.get('template') or ''
                )
                content += f'resource "panos_ethernet_layer3_subinterface" "{sub_resource}" {{\n'
                content += self.location_block('panos_ethernet_layer3_subinterface', template=iface.get('template'))
                content += f'  name = {self.escape_string(sub_name)}\n'
                # F2.6: the parent is the physical interface declared above
                content += f"  parent = {self.hcl_value(self.name_ref(name, ETH_IFACE_SCOPES), '')}\n"
                content += '  tag = 0\n'
                self._emit_subinterface_ip(content, iface)
                content += '}\n\n'

        with open(self.output_dir / 'interfaces.tf', 'w') as f:
            f.write(content)

    def _emit_subinterface_ip(self, content: str, iface: dict) -> None:
        """Emit the ip list object for a subinterface resource (v2: list of objects)."""
        ips = iface.get('ip_addresses') or []
        if ips:
            content += f'  ip = {self.hcl_value([{"name": ip} for ip in ips])}\n'

    def generate_interface_report(self, interfaces: list[dict]):
        """Generate a text report of interfaces and their IP addresses"""
        if not interfaces:
            return

        content = '=' * 80 + '\n'
        content += 'INTERFACE AND IP ADDRESS MIGRATION REPORT\n'
        content += 'Generated for Firewall Migration Planning\n'
        content += '=' * 80 + '\n\n'

        content += 'This report lists all interfaces and their assigned IP addresses from the\n'
        content += 'source configuration. Use this to plan interface mapping for the new platform.\n\n'

        content += '=' * 80 + '\n'
        content += 'INTERFACE SUMMARY\n'
        content += '=' * 80 + '\n\n'

        # Group by type
        by_type = {}
        for iface in interfaces:
            iface_type = iface['type']
            if iface_type not in by_type:
                by_type[iface_type] = []
            by_type[iface_type].append(iface)

        for iface_type, iface_list in sorted(by_type.items()):
            content += f'\n{iface_type.upper()} INTERFACES ({len(iface_list)})\n'
            content += '-' * 80 + '\n'

            for iface in sorted(iface_list, key=lambda x: x['name']):
                content += f'\nInterface: {iface["name"]}\n'
                content += f'  Type: {iface["type"]}\n'
                content += f'  Mode: {iface["mode"]}\n'

                if iface.get('comment'):
                    content += f'  Comment: {iface["comment"]}\n'

                if iface.get('ip_addresses'):
                    content += '  IPv4 Addresses:\n'
                    for ip in iface['ip_addresses']:
                        content += f'    - {ip}\n'

                if iface.get('ipv6_addresses'):
                    content += '  IPv6 Addresses:\n'
                    for ip in iface['ipv6_addresses']:
                        content += f'    - {ip}\n'

                if iface.get('management_profile'):
                    content += f'  Management Profile: {iface["management_profile"]}\n'

                if iface.get('tag'):
                    content += f'  VLAN Tag: {iface["tag"]}\n'

        content += '\n' + '=' * 80 + '\n'
        content += 'MIGRATION CHECKLIST\n'
        content += '=' * 80 + '\n\n'

        content += '1. Review interface naming differences between platforms\n'
        content += '2. Map source interfaces to target platform interfaces\n'
        content += '3. Verify IP addressing scheme is compatible\n'
        content += '4. Check for interface-specific features that may not translate\n'
        content += '5. Update zone and virtual router configurations accordingly\n'
        content += '6. Test connectivity after migration\n\n'

        content += '=' * 80 + '\n'
        content += 'PLATFORM MIGRATION NOTES\n'
        content += '=' * 80 + '\n\n'

        content += 'Common Interface Naming Patterns:\n\n'
        content += '  PA-200/500 Series:    ethernet1/1 - ethernet1/8\n'
        content += '  PA-800 Series:        ethernet1/1 - ethernet1/8\n'
        content += '  PA-3000 Series:       ethernet1/1 - ethernet1/20+\n'
        content += '  PA-5000 Series:       ethernet1/1 - ethernet1/24+\n'
        content += '  PA-7000 Series:       ethernet1/1 - ethernet1/48+ (per slot)\n'
        content += '  VM-Series:            ethernet1/1 - ethernet1/X (configurable)\n\n'

        content += 'Remember:\n'
        content += '  - Management interface naming varies by platform\n'
        content += '  - Some platforms support additional interface types (QSFP, SFP+, etc.)\n'
        content += '  - Aggregate interfaces may have different limitations\n'
        content += '  - Verify transceiver compatibility for the new platform\n\n'

        with open(self.output_dir / 'INTERFACE_MIGRATION_REPORT.txt', 'w') as f:
            f.write(content)

    def generate_security_profiles(self, profiles: dict[str, list[dict]]):
        """Generate security profile Terraform configuration"""
        if not any(profiles.values()):
            return

        content = '# Security Profiles\n'
        content += '# Note: These are simplified profile references.\n'
        content += '# Detailed profile rules must be configured manually or imported.\n\n'

        # Note: Full profile configuration with all rules is complex
        # This generates basic profile declarations that can be enhanced

        # Antivirus profiles
        if profiles.get('antivirus'):
            content += '# Antivirus Profiles\n'
            for prof in profiles['antivirus']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_antivirus_security_profile', context=prof.get('device_group') or ''
                )
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_antivirus_security_profile.{resource_name}\n\n'

        # Vulnerability profiles
        if profiles.get('vulnerability'):
            content += '# Vulnerability Protection Profiles\n'
            for prof in profiles['vulnerability']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_vulnerability_security_profile', context=prof.get('device_group') or ''
                )
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_vulnerability_security_profile.{resource_name}\n\n'

        # Anti-spyware profiles
        if profiles.get('anti_spyware'):
            content += '# Anti-Spyware Profiles\n'
            for prof in profiles['anti_spyware']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_anti_spyware_security_profile', context=prof.get('device_group') or ''
                )
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_anti_spyware_security_profile.{resource_name}\n\n'

        # URL filtering profiles
        if profiles.get('url_filtering'):
            content += '# URL Filtering Profiles\n'
            for prof in profiles['url_filtering']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_url_filtering_security_profile', context=prof.get('device_group') or ''
                )
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_url_filtering_security_profile.{resource_name}\n\n'

        # File blocking profiles
        if profiles.get('file_blocking'):
            content += '# File Blocking Profiles\n'
            for prof in profiles['file_blocking']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_file_blocking_security_profile', context=prof.get('device_group') or ''
                )
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_file_blocking_security_profile.{resource_name}\n\n'

        # WildFire profiles
        if profiles.get('wildfire_analysis'):
            content += '# WildFire Analysis Profiles\n'
            for prof in profiles['wildfire_analysis']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_wildfire_analysis_security_profile', context=prof.get('device_group') or ''
                )
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_wildfire_analysis_security_profile.{resource_name}\n\n'

        with open(self.output_dir / 'security_profiles.tf', 'w') as f:
            f.write(content)

    def generate_security_profile_groups(self, groups: list[dict]):
        """Generate security profile group Terraform configuration (v2: panos_security_profile_group)

        The v2 schema models each profile category as a string list.
        """
        if not groups:
            return

        content = '# Security Profile Groups\n\n'

        # Profile categories the v2 schema models as lists
        categories = ('virus', 'spyware', 'vulnerability', 'url_filtering',
                      'file_blocking', 'wildfire_analysis', 'gtp', 'sctp', 'data_filtering')

        for grp in groups:
            resource_name = self.declare_resource_name(
                grp['name'], 'panos_security_profile_group', context=grp.get('device_group') or ''
            )

            content += f'resource "panos_security_profile_group" "{resource_name}" {{\n'
            content += self.location_block('panos_security_profile_group', grp.get('device_group'))
            content += f'  name = {self.escape_string(grp["name"])}\n'

            for category in categories:
                members = grp.get(category)
                if members:
                    members_str = ', '.join([self.escape_string(m) for m in members])
                    content += f'  {category} = [{members_str}]\n'

            content += '}\n\n'

        with open(self.output_dir / 'security_profile_groups.tf', 'w') as f:
            f.write(content)


    def generate_manual_setup_report(self, bgp_config: dict[str, Any],
                                     ospf_config: dict[str, Any],
                                     application_filters: list[dict],
                                     manual_key_tunnels: list[dict],
                                     application_override_rules: Optional[list[dict]] = None,
                                     qos_profiles: Optional[list[dict]] = None,
                                     tunnel_monitor_profiles: Optional[list[dict]] = None,
                                     schedules: Optional[list[dict]] = None,
                                     log_settings: Optional[list[dict]] = None,
                                     zone_protection_profiles: Optional[list[dict]] = None):
        """Write MANUAL_SETUP_REPORT.txt for items that are not emitted (F2.9)

        Two buckets, one report:
        - no v2 resource exists (BGP, OSPF, application filters, manual-key
          IPsec tunnels, application override rules, QoS profiles);
        - a v2 resource exists but the converter intentionally does not emit
          it, because only the name and description were parsed and an empty
          object would be a misconfiguration (log forwarding and zone
          protection profiles).

        The parsed data is preserved here instead of being emitted as .tf
        resources, so nothing is silently dropped (see resource_mapping.py).
        """
        if not (bgp_config or ospf_config or application_filters or manual_key_tunnels
                or application_override_rules or qos_profiles
                or tunnel_monitor_profiles or schedules or log_settings
                or zone_protection_profiles):
            return

        lines = ['MANUAL SETUP REPORT', '=' * 60, '']
        lines.append('The items below have no panos provider v2 resource, or the')
        lines.append('converter intentionally does not emit them (the reason is stated')
        lines.append('per section). Configure them manually (GUI or CLI) and verify')
        lines.append('against this report.')
        lines.append('')

        if bgp_config:
            lines.append('--- BGP (no v2 resource: panos_bgp, panos_bgp_peer_group, panos_bgp_peer) ---')
            lines.append(f"  router_id: {bgp_config.get('router_id')}")
            lines.append(f"  as_number: {bgp_config.get('as_number')}")
            for pg in bgp_config.get('peer_groups', []):
                lines.append(f"  peer_group: {pg.get('name')} (type: {pg.get('type')})")
            for peer in bgp_config.get('peers', []):
                lines.append(f"  peer: {peer.get('name')} "
                             f"(peer_as: {peer.get('peer_as')}, "
                             f"local: {peer.get('local_address_ip') or peer.get('local_address_interface')}, "
                             f"remote: {peer.get('peer_address_ip')}, "
                             f"group: {peer.get('peer_group')}, enable: {peer.get('enable')})")
            lines.append('')

        if ospf_config:
            lines.append('--- OSPF (no v2 resource: panos_ospf, panos_ospf_area, panos_ospf_area_interface) ---')
            lines.append(f"  router_id: {ospf_config.get('router_id')}")
            for area in ospf_config.get('areas', []):
                lines.append(f"  area: {area.get('area_id')} (type: {area.get('type')})")
            for iface in ospf_config.get('interfaces', []):
                lines.append(f"  interface: {iface.get('interface')} "
                             f"(enable: {iface.get('enable')}, passive: {iface.get('passive')}, "
                             f"metric: {iface.get('metric')})")
            lines.append('')

        if application_filters:
            lines.append('--- Application Filters (no v2 resource: panos_application_filter) ---')
            for af in application_filters:
                lines.append(f"  {af.get('name')} (dg: {af.get('device_group')}): "
                             f"category={af.get('category')}, risk={af.get('risk')}, "
                             f"evasive={af.get('evasive')}")
            lines.append('')

        if manual_key_tunnels:
            lines.append('--- Manual-key IPsec tunnels (manual_key block requires key material) ---')
            for tunnel in manual_key_tunnels:
                lines.append(f"  {tunnel.get('name')}: peer={tunnel.get('peer_address')}, "
                             f"local={tunnel.get('local_address')}, "
                             f"interface={tunnel.get('tunnel_interface')}")
            lines.append('  See VPN_MIGRATION_REPORT.txt for key management instructions.')
            lines.append('')

        if application_override_rules:
            lines.append('--- Application Override Rules (no v2 resource) ---')
            for rule in application_override_rules:
                lines.append(
                    f"  {rule.get('name')}: from={rule.get('source_zones')} "
                    f"to={rule.get('destination_zones')} "
                    f"source={rule.get('source_addresses')} "
                    f"port={rule.get('port') or 'any'} "
                    f"protocol={rule.get('protocol') or 'any'} "
                    f"application={rule.get('application')} "
                    f"disabled={rule.get('disabled')}")
            lines.append('  Configure via the Panorama GUI or CLI.')
            lines.append('')

        if qos_profiles:
            lines.append('--- QoS Profiles (no v2 resource) ---')
            for prof in qos_profiles:
                classes = prof.get('class_bandwidth_type') or {}
                class_list = ', '.join(
                    f"{name}({cfg.get('priority')})" if cfg.get('priority') else name
                    for name, cfg in classes.items()) or 'none'
                lines.append(
                    f"  {prof.get('name')}: classes=[{class_list}]"
                    + (f" ({prof['description']})" if prof.get('description') else ''))
            lines.append('  Configure via the Panorama GUI or CLI.')
            lines.append('')

        if tunnel_monitor_profiles:
            lines.append('--- IPsec Tunnel Monitor Profiles (no v2 resource) ---')
            for prof in tunnel_monitor_profiles:
                lines.append(
                    f"  {prof.get('name')}: interval={prof.get('interval')}, "
                    f"threshold={prof.get('threshold')}, action={prof.get('action')}")
            lines.append('  No v2 resource exists for IPsec tunnel monitor profiles.')
            lines.append('  panos_monitor_profile manages PBF path monitoring')
            lines.append('  profiles, a different PAN-OS object')
            lines.append('  (network/profiles/monitor-profile). Configure via the')
            lines.append('  Panorama GUI or CLI.')
            lines.append('')

        if schedules:
            lines.append('--- Schedules (v2 resource exists, not emitted) ---')
            for sched in schedules:
                entries = ','.join(e['name'] for e in sched.get('recurring', [])) or '-'
                lines.append(
                    f"  {sched['name']}: type={sched.get('schedule_type')}, "
                    f"entries={entries}")
            lines.append('  The v2 resource panos_schedule exists, but only the')
            lines.append('  entry names are parsed (day and time ranges are not')
            lines.append('  captured), and v2.0.14 does not model monthly')
            lines.append('  schedules. Configure via the Panorama GUI or CLI.')
            lines.append('')

        if log_settings:
            lines.append('--- Log Forwarding Profiles (v2 resource exists, not emitted) ---')
            for prof in log_settings:
                lines.append(
                    f"  {prof.get('name')}"
                    + (f" ({prof['description']})" if prof.get('description') else ''))
            lines.append('  v2 resource: panos_log_forwarding_profile')
            lines.append('  Reason: only the name and description are parsed. The')
            lines.append('  match_list body is not captured, and an empty profile')
            lines.append('  would be a misconfigured object. Configure the profile')
            lines.append('  manually (GUI or CLI).')
            lines.append('')

        if zone_protection_profiles:
            lines.append('--- Zone Protection Profiles (v2 resource exists, not emitted) ---')
            for prof in zone_protection_profiles:
                lines.append(
                    f"  {prof.get('name')}"
                    + (f" ({prof['description']})" if prof.get('description') else ''))
            lines.append('  v2 resource: panos_zone_protection_profile')
            lines.append('  Reason: only the name and description are parsed. The')
            lines.append('  SIP/UDP/TCP/ICMP/DNS options body is not captured, and an')
            lines.append('  empty profile would be a misconfigured object. Real')
            lines.append('  emission needs profile parsing (Epic 3). Configure the')
            lines.append('  profile manually (GUI or CLI).')
            lines.append('')

        lines.append('End of report.')

        with open(self.output_dir / 'MANUAL_SETUP_REPORT.txt', 'w') as f:
            f.write('\n'.join(lines) + '\n')

    def generate_vpn_config(self, ike_gateways: list[dict], ipsec_tunnels: list[dict],
                           ike_profiles: list[dict], ipsec_profiles: list[dict]):
        """Generate VPN Terraform configuration (v2 resource shapes)

        v2 changes applied here:
        - panos_ike_crypto_profile: encryption/hash/dh_group lists, lifetime block
        - panos_ipsec_crypto_profile: esp block, dh_group string, lifetime/lifesize blocks
        - panos_ike_gateway: protocol + peer_address + authentication blocks
        - panos_ipsec_tunnel: proxy_id list entries inside auto_key (no separate
          panos_ipsec_tunnel_proxy_id_ipv4 resource in v2)

        Emission gate (F2.8): every v2 VPN resource type is independently
        valid, so any non-empty VPN section emits vpn.tf. The legacy gate
        required a gateway or tunnel, which silently dropped standalone
        crypto profiles.
        """
        if not (ike_gateways or ipsec_tunnels or ike_profiles or ipsec_profiles):
            return

        content = '# IPsec VPN Configuration\n'
        content += '# IMPORTANT: Pre-shared keys are set to generic placeholders.\n'
        content += '# You MUST update all pre-shared keys before applying!\n'
        content += '# Search for "***CHANGE_ME***" and replace with actual keys.\n\n'

        # IKE Crypto Profiles (v2: encryption/hash/dh_group lists + lifetime block)
        if ike_profiles:
            content += '# IKE Crypto Profiles\n\n'
            for profile in ike_profiles:
                resource_name = self.declare_resource_name(
                    f"ike_profile_{profile['name']}", 'panos_ike_crypto_profile', context=profile.get('template') or ''
                )
                content += f'resource "panos_ike_crypto_profile" "{resource_name}" {{\n'
                content += self.location_block('panos_ike_crypto_profile', template=profile.get('template'))
                content += f'  name = {self.escape_string(profile["name"])}\n'

                if profile.get('encryptions'):
                    enc_str = ', '.join([self.escape_string(e) for e in profile['encryptions']])
                    content += f'  encryption = [{enc_str}]\n'

                # v2 calls the hash algorithms hash (not authentication)
                if profile.get('authentications'):
                    auth_str = ', '.join([self.escape_string(a) for a in profile['authentications']])
                    content += f'  hash = [{auth_str}]\n'

                if profile.get('dh_groups'):
                    dh_str = ', '.join([self.escape_string(dh) for dh in profile['dh_groups']])
                    content += f'  dh_group = [{dh_str}]\n'

                if profile.get('lifetime_hours'):
                    try:
                        hours = int(profile['lifetime_hours'])
                    except (TypeError, ValueError):
                        hours = None
                    if hours is not None:
                        content += f'  lifetime = {self.hcl_value({"hours": hours})}\n'

                content += '}\n\n'

        # IPsec Crypto Profiles (v2: esp object + dh_group string + lifetime/lifesize)
        if ipsec_profiles:
            content += '# IPsec Crypto Profiles\n\n'
            for profile in ipsec_profiles:
                profile_key = f"ipsec_profile_{profile['name']}"
                resource_name = self.declare_resource_name(
                    profile_key, 'panos_ipsec_crypto_profile', context=profile.get('template') or ''
                )
                content += f'resource "panos_ipsec_crypto_profile" "{resource_name}" {{\n'
                content += self.location_block('panos_ipsec_crypto_profile', template=profile.get('template'))
                content += f'  name = {self.escape_string(profile["name"])}\n'

                # v2 dh_group is a single string (not a list)
                if profile.get('dh_group'):
                    content += f'  dh_group = {self.escape_string(profile["dh_group"])}\n'

                # v2 esp object holds the encryption/authentication algorithms
                esp: dict = {}
                if profile.get('encryptions'):
                    esp['encryption'] = list(profile['encryptions'])
                if profile.get('authentications'):
                    esp['authentication'] = list(profile['authentications'])
                if esp:
                    content += f'  esp = {self.hcl_value(esp)}\n'

                if profile.get('lifetime_hours'):
                    try:
                        hours = int(profile['lifetime_hours'])
                    except (TypeError, ValueError):
                        hours = None
                    if hours is not None:
                        content += f'  lifetime = {self.hcl_value({"hours": hours})}\n'

                if profile.get('lifetime_kb'):
                    try:
                        kb = int(profile['lifetime_kb'])
                    except (TypeError, ValueError):
                        kb = None
                    if kb is not None:
                        content += f'  lifesize = {self.hcl_value({"kb": kb})}\n'

                content += '}\n\n'

        # IKE Gateways (v2: protocol/peer_address/authentication blocks)
        if ike_gateways:
            content += '# IKE Gateways\n'
            content += '# WARNING: Pre-shared keys use placeholder "***CHANGE_ME***"\n'
            content += '# Update these with actual keys from your key management system!\n\n'

            for gw in ike_gateways:
                resource_name = self.declare_resource_name(
                    f"ike_gw_{gw['name']}", 'panos_ike_gateway', context=gw.get('template') or ''
                )
                content += f'resource "panos_ike_gateway" "{resource_name}" {{\n'
                content += self.location_block('panos_ike_gateway', template=gw.get('template'))
                content += f'  name = {self.escape_string(gw["name"])}\n'

                # v2 protocol object: version + ikev1/ikev2 sub-object
                version = gw.get('version', 'ikev1')
                if version in ('ikev1', 'ikev2'):
                    proto_obj: dict = {'version': version}
                    ver_obj: dict = {}
                    if gw.get('ike_crypto_profile'):
                        ike_key = f"ike_profile_{gw['ike_crypto_profile']}"
                        # F2.6: reference when declared in this run, else plain name
                        ver_obj['ike_crypto_profile'] = self.name_ref(
                            gw['ike_crypto_profile'], IKE_CRYPTO_SCOPES, key=ike_key)
                    if ver_obj:
                        proto_obj[version] = ver_obj
                    content += f'  protocol = {self.hcl_value(proto_obj)}\n'

                if gw.get('peer_address'):
                    # v2 peer_address object keyed by fqdn or ip
                    key = 'fqdn' if gw.get('peer_address_type') == 'fqdn' else 'ip'
                    content += f'  peer_address = {self.hcl_value({key: gw["peer_address"]})}\n'

                if gw.get('local_address_interface'):
                    # F2.6: reference when the interface is in this run
                    iface_ref = self.name_ref(gw['local_address_interface'], INTERFACE_SCOPES)
                    content += f'  local_address = {self.hcl_value({"interface": iface_ref})}\n'
                elif gw.get('local_address'):
                    # Heuristic: dotted-quad values are IPs, otherwise interfaces
                    local = gw['local_address']
                    key = 'ip' if self._looks_like_ip(local) else 'interface'
                    value = self.name_ref(local, INTERFACE_SCOPES) if key == 'interface' else local
                    content += f'  local_address = {self.hcl_value({key: value})}\n'

                # v2 authentication object; pre-shared key only (cert auth is manual)
                auth_type = gw.get('auth_type', 'pre-shared-key')
                if auth_type == 'pre-shared-key' and gw.get('pre_shared_key'):
                    key_obj = self.hcl_value({'pre_shared_key': {'key': gw['pre_shared_key']}})
                    content += f'  authentication = {key_obj}  # *** CHANGE THIS KEY ***\n'

                if gw.get('local_id'):
                    content += f'  local_id = {self.hcl_value({"id": gw["local_id"]})}\n'

                if gw.get('peer_id'):
                    content += f'  peer_id = {self.hcl_value({"id": gw["peer_id"]})}\n'

                content += '}\n\n'

        # IPsec Tunnels (v2: auto_key block with nested proxy_id entries)
        if ipsec_tunnels:
            content += '# IPsec Tunnels\n\n'
            for tunnel in ipsec_tunnels:
                if tunnel.get('type') != 'auto-key':
                    # Manual-key tunnels need key material: manual-setup report only
                    continue

                resource_name = self.declare_resource_name(
                    f"tunnel_{tunnel['name']}", 'panos_ipsec_tunnel', context=tunnel.get('template') or ''
                )
                content += f'resource "panos_ipsec_tunnel" "{resource_name}" {{\n'
                content += self.location_block('panos_ipsec_tunnel', template=tunnel.get('template'))
                content += f'  name = {self.escape_string(tunnel["name"])}\n'

                if tunnel.get('tunnel_interface'):
                    content += f'  tunnel_interface = {self.escape_string(tunnel["tunnel_interface"])}\n'

                # v2 auto_key object; ike_gateway and proxy_id are lists of objects
                auto_key: dict = {}
                if tunnel.get('ike_gateway'):
                    # F2.6: reference when the gateway is in this run,
                    # else a plain brown-field name (never a phantom resource)
                    auto_key['ike_gateway'] = [{'name': self.name_ref(
                        tunnel['ike_gateway'], IKE_GATEWAY_SCOPES,
                        key=f"ike_gw_{tunnel['ike_gateway']}")}]
                if tunnel.get('ipsec_crypto_profile'):
                    ipsec_key = f"ipsec_profile_{tunnel['ipsec_crypto_profile']}"
                    # F2.6: reference when declared in this run, else plain name
                    auto_key['ipsec_crypto_profile'] = self.name_ref(
                        tunnel['ipsec_crypto_profile'], IPSEC_CRYPTO_SCOPES, key=ipsec_key)

                # v2 merges proxy IDs into the tunnel as auto_key proxy_id entries
                proxy_list = []
                for proxy in tunnel.get('proxy_ids', []):
                    proxy_obj: dict = {'name': proxy['name']}
                    if proxy.get('local'):
                        proxy_obj['local'] = proxy['local']
                    if proxy.get('remote'):
                        proxy_obj['remote'] = proxy['remote']
                    if proxy.get('protocol') is not None:
                        try:
                            protocol_number = int(proxy['protocol'])
                        except (TypeError, ValueError):
                            protocol_number = None
                        if protocol_number is not None:
                            proxy_obj['protocol'] = {'number': protocol_number}
                    proxy_list.append(proxy_obj)
                if proxy_list:
                    auto_key['proxy_id'] = proxy_list

                if auto_key:
                    content += f'  auto_key = {self.hcl_value(auto_key)}\n'

                content += '}\n\n'

        with open(self.output_dir / 'vpn.tf', 'w') as f:
            f.write(content)

    @staticmethod
    def _looks_like_ip(value: str) -> bool:
        """Return True if the value looks like an IPv4 address (best effort)."""
        parts = (value or '').split('.')
        return len(parts) == 4 and all(p.isdigit() for p in parts)

    def generate_vpn_report(self, ike_gateways: list[dict], ipsec_tunnels: list[dict]):
        """Generate VPN migration report with key management instructions"""
        if not (ike_gateways or ipsec_tunnels):
            return

        content = '=' * 80 + '\n'
        content += 'VPN CONFIGURATION MIGRATION REPORT\n'
        content += '=' * 80 + '\n\n'

        content += '⚠️  CRITICAL: PRE-SHARED KEY MANAGEMENT\n\n'
        content += 'Pre-shared keys are NOT included in Panorama exports for security reasons.\n'
        content += 'All VPN configurations use placeholder keys: ***CHANGE_ME***\n\n'
        content += 'REQUIRED ACTIONS:\n'
        content += '1. Retrieve actual pre-shared keys from your secure key management system\n'
        content += '2. Update vpn.tf file with real keys before applying\n'
        content += '3. Consider using Terraform variables or secrets management\n'
        content += '4. Never commit actual keys to version control\n\n'

        content += '=' * 80 + '\n'
        content += 'IKE GATEWAYS\n'
        content += '=' * 80 + '\n\n'

        for gw in ike_gateways:
            content += f'Gateway: {gw["name"]}\n'
            content += f'  Version: {gw.get("version", "ikev1")}\n'
            content += f'  Peer Address: {gw.get("peer_address", "N/A")}\n'
            content += f'  Local Address: {gw.get("local_address") or gw.get("local_address_interface", "N/A")}\n'
            content += f'  Auth Type: {gw.get("auth_type", "pre-shared-key")}\n'

            if gw.get('auth_type') == 'pre-shared-key':
                content += '  ⚠️  Pre-Shared Key: ***MUST BE UPDATED***\n'
                content += '     Current placeholder: ***CHANGE_ME***\n'
                content += '     Action: Replace with actual key in vpn.tf\n'

            content += f'  IKE Crypto Profile: {gw.get("ike_crypto_profile", "N/A")}\n'
            content += '\n'

        content += '=' * 80 + '\n'
        content += 'IPSEC TUNNELS\n'
        content += '=' * 80 + '\n\n'

        for tunnel in ipsec_tunnels:
            content += f'Tunnel: {tunnel["name"]}\n'
            content += f'  Type: {tunnel.get("type", "auto-key")}\n'
            content += f'  Tunnel Interface: {tunnel.get("tunnel_interface", "N/A")}\n'
            content += f'  IKE Gateway: {tunnel.get("ike_gateway", "N/A")}\n'
            content += f'  IPsec Crypto Profile: {tunnel.get("ipsec_crypto_profile", "N/A")}\n'

            if tunnel.get('proxy_ids'):
                content += '  Proxy IDs:\n'
                for proxy in tunnel['proxy_ids']:
                    content += f'    - {proxy["name"]}: {proxy.get("local", "any")} <-> {proxy.get("remote", "any")}\n'

            content += '\n'

        content += '=' * 80 + '\n'
        content += 'KEY MANAGEMENT BEST PRACTICES\n'
        content += '=' * 80 + '\n\n'

        content += 'Option 1: Terraform Variables (Recommended)\n'
        content += '-' * 40 + '\n'
        content += 'Create terraform.tfvars (DO NOT COMMIT):\n'
        content += '  vpn_psk_gateway1 = "actual-pre-shared-key-here"\n'
        content += '  vpn_psk_gateway2 = "actual-pre-shared-key-here"\n\n'

        content += 'Update vpn.tf:\n'
        content += '  pre_shared_key = var.vpn_psk_gateway1\n\n'

        content += 'Option 2: Environment Variables\n'
        content += '-' * 40 + '\n'
        content += 'Set environment variables:\n'
        content += '  export TF_VAR_vpn_psk_gateway1="actual-key"\n\n'

        content += 'Option 3: Secrets Management\n'
        content += '-' * 40 + '\n'
        content += 'Use HashiCorp Vault, AWS Secrets Manager, or similar:\n'
        content += '  data "vault_generic_secret" "vpn_keys" {\n'
        content += '    path = "secret/vpn-keys"\n'
        content += '  }\n\n'

        content += 'Option 4: Manual Entry (Least Secure)\n'
        content += '-' * 40 + '\n'
        content += 'Directly in vpn.tf (NOT RECOMMENDED):\n'
        content += '  pre_shared_key = "actual-key"  # DO NOT COMMIT TO GIT\n\n'

        content += '=' * 80 + '\n'
        content += 'MIGRATION CHECKLIST\n'
        content += '=' * 80 + '\n\n'

        content += '[ ] Retrieve all VPN pre-shared keys from secure storage\n'
        content += '[ ] Update vpn.tf with actual keys (use variables/secrets)\n'
        content += '[ ] Verify IKE gateway peer addresses\n'
        content += '[ ] Confirm tunnel interface assignments\n'
        content += '[ ] Check proxy ID configurations\n'
        content += '[ ] Validate crypto profile settings\n'
        content += '[ ] Test VPN connectivity in lab\n'
        content += '[ ] Verify routing through tunnels\n'
        content += '[ ] Monitor Phase 1 and Phase 2 negotiations\n'
        content += '[ ] Ensure .gitignore includes terraform.tfvars\n\n'

        content += '=' * 80 + '\n'
        content += 'IMPORTANT SECURITY NOTES\n'
        content += '=' * 80 + '\n\n'

        content += '1. Never commit pre-shared keys to version control\n'
        content += '2. Use .gitignore to exclude terraform.tfvars and *.auto.tfvars\n'
        content += '3. Rotate keys regularly according to security policy\n'
        content += '4. Use strong, unique keys for each VPN tunnel\n'
        content += '5. Consider using certificate-based authentication\n'
        content += '6. Implement proper key escrow and recovery procedures\n'
        content += '7. Audit key access and usage\n\n'

        with open(self.output_dir / 'VPN_MIGRATION_REPORT.txt', 'w') as f:
            f.write(content)

    def generate_readme(self):
        """Generate README with usage instructions"""
        content = '''# Palo Alto Terraform Configuration

This directory contains Terraform configuration files generated from Palo Alto Panorama export.

## Prerequisites

1. Install Terraform (>= 1.0)
2. Install the Palo Alto Networks PAN-OS provider

## Configuration

1. Set up authentication variables in `terraform.tfvars`:

```hcl
panos_hostname = "your-panorama-hostname-or-ip"
panos_username = "admin"
panos_password = "your-password"
device_group   = "your-device-group"
```

Or use environment variables:
```bash
export PANOS_HOSTNAME="your-panorama-hostname-or-ip"
export PANOS_USERNAME="admin"
export PANOS_PASSWORD="your-password"
```

2. Initialize Terraform:
```bash
terraform init
```

3. Review the plan:
```bash
terraform plan
```

4. Apply the configuration:
```bash
terraform apply
```

## File Structure

- `provider.tf` - Provider configuration
- `variables.tf` - Variable definitions
- `address_objects.tf` - Address object configurations
- `address_groups.tf` - Address group configurations
- `service_objects.tf` - Service object configurations
- `service_groups.tf` - Service group configurations
- `security_rules.tf` - Security policy rules
- `nat_rules.tf` - NAT policy rules

## Important Notes

- Review all configurations before applying
- Test in a non-production environment first
- Back up your existing configuration
- Adjust rule ordering as needed
- Some features may require manual adjustment

## Provider Documentation

For more information on the PAN-OS Terraform provider:
https://registry.terraform.io/providers/PaloAltoNetworks/panos/latest/docs
'''

        with open(self.output_dir / 'README.md', 'w') as f:
            f.write(content)


def main():
    parser = argparse.ArgumentParser(
        description='Convert Palo Alto Panorama XML output to Terraform configuration'
    )
    parser.add_argument(
        'input_file',
        help='Input XML file from Panorama'
    )
    parser.add_argument(
        '--output-dir',
        default='terraform_output',
        help='Output directory for Terraform files (default: terraform_output)'
    )

    args = parser.parse_args()

    # Check if input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        return 1

    try:
        print(f"Parsing Panorama configuration from {args.input_file}...")
        panorama = PanoramaParser(args.input_file)

        print("Extracting configuration elements...")
        device_groups = panorama.parse_device_groups()

        # New: Tags and Regions
        tags = panorama.parse_tags()
        regions = panorama.parse_regions()

        # New: URL and Application objects
        custom_url_categories = panorama.parse_custom_url_categories()
        application_groups = panorama.parse_application_groups()
        application_filters = panorama.parse_application_filters()
        external_lists = panorama.parse_external_lists()
        schedules = panorama.parse_schedules()

        # Address and Service objects
        addresses = panorama.parse_address_objects()
        address_groups = panorama.parse_address_groups()
        services = panorama.parse_service_objects()
        service_groups = panorama.parse_service_groups()

        # Rules
        security_rules = panorama.parse_security_rules()
        nat_rules = panorama.parse_nat_rules()
        decryption_rules = panorama.parse_decryption_rules()
        pbf_rules = panorama.parse_pbf_rules()
        app_override_rules = panorama.parse_application_override_rules()

        # Network
        zones = panorama.parse_zones()
        interfaces = panorama.parse_interfaces()
        virtual_routers = panorama.parse_virtual_routers()
        logical_routers = panorama.parse_logical_routers()  # Advanced Routing Engine

        # Combine virtual and logical routers for unified handling
        all_routers = virtual_routers + logical_routers

        # Security Profiles
        security_profiles = panorama.parse_security_profiles()
        security_profile_groups = panorama.parse_security_profile_groups()
        zone_protection_profiles = panorama.parse_zone_protection_profiles()
        log_settings = panorama.parse_log_settings()
        qos_profiles = panorama.parse_qos_profiles()
        tunnel_monitor_profiles = panorama.parse_tunnel_monitor_profiles()
        # F2.9: PBF path monitoring profiles (a different PAN-OS object; the
        # provider manages them as panos_monitor_profile)
        pbf_monitor_profiles = panorama.parse_pbf_monitor_profiles()

        # Dynamic routing
        bgp_config = panorama.parse_bgp()
        ospf_config = panorama.parse_ospf()

        # VPN configurations
        ike_gateways = panorama.parse_ike_gateways()
        ipsec_tunnels = panorama.parse_ipsec_tunnels()
        ike_crypto_profiles = panorama.parse_ike_crypto_profiles()
        ipsec_crypto_profiles = panorama.parse_ipsec_crypto_profiles()

        print("\nFound:")
        print(f"  - {len(device_groups)} device groups")
        print(f"  - {len(tags)} tags")
        print(f"  - {len(regions)} regions")
        print(f"  - {len(custom_url_categories)} custom URL categories")
        print(f"  - {len(application_groups)} application groups")
        print(f"  - {len(application_filters)} application filters")
        print(f"  - {len(external_lists)} external lists")
        print(f"  - {len(schedules)} schedules")
        print(f"  - {len(addresses)} address objects")
        print(f"  - {len(address_groups)} address groups")
        print(f"  - {len(services)} service objects")
        print(f"  - {len(service_groups)} service groups")
        print(f"  - {len(security_rules)} security rules")
        print(f"  - {len(nat_rules)} NAT rules")
        print(f"  - {len(decryption_rules)} decryption rules")
        print(f"  - {len(pbf_rules)} policy-based forwarding rules")
        print(f"  - {len(app_override_rules)} application override rules")
        print(f"  - {len(zones)} zones")
        print(f"  - {len(interfaces)} interfaces")
        if logical_routers:
            print(f"  - {len(virtual_routers)} virtual routers (legacy)")
            print(f"  - {len(logical_routers)} logical routers (advanced routing)")
            print(f"  - {len(all_routers)} total routers")
        else:
            print(f"  - {len(virtual_routers)} virtual routers")

        # Count profiles
        profile_count = sum(len(profs) for profs in security_profiles.values())
        print(f"  - {profile_count} security profiles")
        print(f"  - {len(security_profile_groups)} security profile groups")
        print(f"  - {len(zone_protection_profiles)} zone protection profiles")
        print(f"  - {len(log_settings)} log forwarding profiles")
        print(f"  - {len(qos_profiles)} QoS profiles")
        print(f"  - {len(tunnel_monitor_profiles)} IPsec tunnel monitor profiles")
        print(f"  - {len(pbf_monitor_profiles)} PBF path monitoring profiles")

        # Dynamic routing
        if bgp_config:
            peer_count = len(bgp_config.get('peers', []))
            print(f"  - BGP enabled with {peer_count} peers")
        if ospf_config:
            area_count = len(ospf_config.get('areas', []))
            print(f"  - OSPF enabled with {area_count} areas")

        # VPN
        print(f"  - {len(ike_gateways)} IKE gateways")
        print(f"  - {len(ipsec_tunnels)} IPsec tunnels")

        print(f"\nGenerating Terraform configuration in {args.output_dir}...")
        tf_gen = TerraformGenerator(args.output_dir)

        # Core configuration
        tf_gen.generate_provider_config()
        tf_gen.generate_variables()

        # New: Tags and URL/App objects
        tf_gen.generate_tags(tags)
        tf_gen.generate_custom_url_categories(custom_url_categories)
        tf_gen.generate_application_groups(application_groups)
        # Application filters have no v2 resource: they go to the manual setup report
        tf_gen.generate_external_lists(external_lists)
        # F2.9: schedules go to the manual setup report (v2 resource
        # exists, but only entry names are parsed and v2.0.14 has no
        # monthly schedule support)

        # Address and Service objects
        tf_gen.generate_address_objects(addresses)
        tf_gen.generate_address_groups(address_groups)
        tf_gen.generate_service_objects(services)
        tf_gen.generate_service_groups(service_groups)

        # Network
        # F2.6: interfaces emit first so zone/VR/interface .name lookups
        # resolve to declared resources
        tf_gen.generate_ethernet_interfaces(interfaces)
        tf_gen.generate_zones(zones)
        tf_gen.generate_virtual_routers(all_routers)  # Handles both virtual & logical routers

        # Security Profiles
        # F2.9: zone protection, log forwarding, and IPsec tunnel monitor
        # profiles go to the manual setup report (no v2 resource, or the
        # v2 resource exists but the profile body is not parsed)
        tf_gen.generate_security_profiles(security_profiles)
        tf_gen.generate_security_profile_groups(security_profile_groups)
        # F2.9: PBF path monitoring profiles emit as real v2 resources
        tf_gen.generate_pbf_monitor_profiles(pbf_monitor_profiles)

        # Rules
        # F2.9: application override rules go to the manual setup report
        # (no v2 resource)
        tf_gen.generate_security_rules(security_rules)
        tf_gen.generate_nat_rules(nat_rules)
        tf_gen.generate_decryption_rules(decryption_rules)
        tf_gen.generate_pbf_rules(pbf_rules)

        # VPN: any non-empty section emits vpn.tf (F2.8); the key
        # management report still needs a gateway or tunnel to mention.
        tf_gen.generate_vpn_config(ike_gateways, ipsec_tunnels,
                                  ike_crypto_profiles, ipsec_crypto_profiles)
        if ike_gateways or ipsec_tunnels:
            tf_gen.generate_vpn_report(ike_gateways, ipsec_tunnels)

        # Items that are not emitted (F2.9): BGP, OSPF, app filters, manual-key
        # tunnels, app override, QoS, IPsec tunnel monitor (no v2 resource),
        # and log forwarding + zone protection + schedules (v2 resource
        # exists, profile body not parsed). See resource_mapping.py.
        manual_key_tunnels = [t for t in ipsec_tunnels if t.get('type') != 'auto-key']
        tf_gen.generate_manual_setup_report(
            bgp_config, ospf_config, application_filters, manual_key_tunnels,
            application_override_rules=app_override_rules,
            qos_profiles=qos_profiles,
            tunnel_monitor_profiles=tunnel_monitor_profiles,
            schedules=schedules,
            log_settings=log_settings,
            zone_protection_profiles=zone_protection_profiles,
        )

        # Reports
        tf_gen.generate_interface_report(interfaces)
        tf_gen.generate_readme()

        print("\n✓ Successfully generated Terraform configuration!")
        print("\n📄 Generated Migration Reports:")
        print("  - INTERFACE_MIGRATION_REPORT.txt (Interface and IP inventory)")
        if ike_gateways or ipsec_tunnels:
            print("  - VPN_MIGRATION_REPORT.txt ⚠️  (VPN config with key management instructions)")
        print("\nNext steps:")
        print(f"  1. cd {args.output_dir}")
        print("  2. Review INTERFACE_MIGRATION_REPORT.txt for interface mapping")
        if ike_gateways or ipsec_tunnels:
            print("  3. ⚠️  Review VPN_MIGRATION_REPORT.txt and update pre-shared keys!")
        print("  4. Review the generated .tf files")
        print("  5. Create terraform.tfvars with your credentials")
        if ike_gateways or ipsec_tunnels:
            print("  6. ⚠️  Add VPN pre-shared keys to terraform.tfvars (DO NOT COMMIT)")
        print("  7. Run: terraform init")
        print("  8. Run: terraform plan")
        print("  9. Run: terraform apply")

        return 0

    except ET.ParseError as e:
        print(f"Error: Failed to parse XML file: {e}")
        return 1
    except ValueError as e:
        # DTD rejection in PanoramaParser raises ValueError.
        print(f"Error: rejected '{args.input_file}': {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
