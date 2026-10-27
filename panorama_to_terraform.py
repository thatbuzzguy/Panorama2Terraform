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
Commercial terms are in LICENSE-COMMERCIAL.

This script reads a Panorama XML export and writes Terraform configuration for
the provider `PaloAltoNetworks/panos` v2. An object the provider cannot model is
reported, not dropped. The type list is in docs/RESOURCE_MAPPING.md; this docstring
does not restate it.

Usage:
    python3 panorama_to_terraform.py <input_file.xml> [--output-dir <dir>] [--validate]

See docs/USAGE_GUIDE.md for the flags, the report files, and the post-run gate.
"""

import argparse
import hashlib
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

import container_coverage
import entry_coverage
import sanity_checks
from resource_mapping import INTERFACE_RESOURCE_TYPES, LOCATION_SCHEMA
from xml_input import (
    DEFAULT_MAX_INPUT_BYTES,
    UnsafeInputError,
    add_max_input_argument,
    parse_xml,
)


class PanoramaParser:
    """Parse Palo Alto Panorama XML configuration"""

    # Address entry elements that the v2.0.14 panos_address schema models as a
    # value attribute (XML element -> parser type). Verified against the live
    # schema. The provider stores IPv6 values in ip_netmask.
    ADDRESS_VALUE_ELEMENTS = {
        'ip-netmask': 'ip-netmask',
        'ip-range': 'ip-range',
        'ip-wildcard': 'ip-wildcard',
        'fqdn': 'fqdn',
        'ipv6': 'ipv6',
        'ipv6-range': 'ipv6-range',
    }

    # External dynamic list type sub-shapes (XML element -> v2 attribute).
    # Verified against the v2.0.14 schema for panos_external_dynamic_list.
    EDL_TYPE_ELEMENTS = {
        'domain': 'domain',
        'imei': 'imei',
        'imsi': 'imsi',
        'ip': 'ip',
        'predefined-ip': 'predefined_ip',
        'predefined-url': 'predefined_url',
        'url': 'url',
    }

    # Recurring schedule keys inside an EDL sub-shape (XML element -> v2 name).
    EDL_RECURRING_ELEMENTS = {
        'daily': 'daily',
        'five-minute': 'five_minute',
        'hourly': 'hourly',
        'monthly': 'monthly',
        'weekly': 'weekly',
    }

    # Fields inside an EDL sub-shape that the v2 schema models. The auth block
    # is deliberately absent: it carries credential material and the converter
    # does not write secrets into generated HCL.
    EDL_FIELD_ELEMENTS = {
        'url': 'url',
        'description': 'description',
        'expand-domain': 'expand_domain',
        'certificate-profile': 'certificate_profile',
    }

    def __init__(self, xml_file: str, max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
                 ledger: Optional[entry_coverage.EntryLedger] = None):
        self.xml_file = xml_file
        # F3.8: one safe read for both entry points. It caps the input size
        # and refuses a DTD at parser level (a DTD is the only way an entity
        # expansion or an external entity reaches the parser), so nothing here
        # expands an entity and nothing here reads an unbounded file.
        # F4.2: the same parse records the source line of every element, so a
        # report can name the line an entry came from.
        self.source = parse_xml(xml_file, max_input_bytes)
        self.root = self.source.root
        # ElementTree has no parent pointers; build a child -> parent map so
        # parse methods can find the enclosing device group of an entry (F2.3)
        # and so the coverage scan can tell a section from a property level
        # (F4.2).
        self.parent_map = container_coverage.parent_map(self.root)
        # F4.3: the per-entry record. A parse method marks the entries it reads,
        # and the report is built from the ledger after the parse.
        self.ledger = ledger if ledger is not None else entry_coverage.EntryLedger(
            self.source, self.parent_map)

    def line_of(self, elem: ET.Element) -> Optional[int]:
        """Source line of an element's opening tag (F4.2)."""
        return self.source.line_of(elem)

    def mark(self, entry: ET.Element, captured: dict, detail: str = '',
             destination: Optional[str] = None) -> dict:
        """Record what this method took from an entry, and return the object.

        F4.3 AC-1: a parse method that reads entries marks them. The ledger stores the
        object as a `RecordingDict` and returns it, so a field a method adds after the
        mark is still in the report, and the object also records which keys an output
        reads from it (F4.4).
        """
        return self.ledger.mark(entry, captured, detail, destination)

    def mark_skipped(self, entry: ET.Element, reason: str) -> None:
        """Record an entry this method visited and did not model (F4.3 AC-1.3)."""
        self.ledger.mark_skipped(entry, reason)

    def parse_device_groups(self) -> list[dict]:
        """Parse device groups from Panorama config"""
        device_groups = []

        # Find device-group elements
        for dg in self.root.findall(".//device-group/entry"):
            name = dg.get('name')
            if name:
                device_groups.append(self.mark(dg, {
                    'name': name,
                    'description': self._get_text(dg, 'description')
                }))

        return device_groups

    def device_group_of(self, elem: ET.Element) -> str:
        """Return the name of the device group that defines elem (F2.3).

        An entry under a <device-group><entry> belongs to that group. An
        entry under <shared> or at the top level belongs to the shared
        device group, which PAN-OS names "Shared".
        """
        node = elem
        while node is not None:
            parent = self.parent_map.get(node)
            if parent is not None and parent.tag == 'device-group' and node.tag == 'entry':
                return node.get('name') or 'Shared'
            if node.tag == 'shared':
                return 'Shared'
            node = parent
        return 'Shared'

    def vsys_of(self, elem: ET.Element) -> str:
        """Return the vsys that owns elem, or '' when the export declares none.

        Walks up to the nearest <vsys><entry name="..."> ancestor (F3.1
        identity key, F3.5 honest scope). The value is the declared name and
        never a default: an entry under <shared>, a device group, or a
        template network section has no vsys, and the emitter must be able
        to tell that case from an entry the export places in vsys1. A
        <vsys><entry> with no name attribute is the default vsys, which
        PAN-OS names vsys1.
        """
        node = elem
        while node is not None:
            parent = self.parent_map.get(node)
            if parent is not None and parent.tag == 'vsys' and node.tag == 'entry':
                return node.get('name') or 'vsys1'
            node = parent
        return ''

    def template_of(self, elem: ET.Element) -> str:
        """Return the template that owns elem, or '' when the export names none.

        Walks up to the nearest <templates><entry name="..."> ancestor
        (F3.1 identity key). Panorama nests a template's own device config
        under <templates><entry><devices><entry>, so a template-defined
        object reports its template here and its placeholder device name
        from device_of.
        """
        node = elem
        while node is not None:
            parent = self.parent_map.get(node)
            if parent is not None and parent.tag == 'templates' and node.tag == 'entry':
                return node.get('name') or ''
            node = parent
        return ''

    def device_of(self, elem: ET.Element) -> str:
        """Return the device that owns elem, or '' when the export names none.

        Walks up to the nearest <devices><entry name="..."> ancestor. A
        vsys-scoped object lives under a device entry, and the v2 location
        needs that name as `ngfw_device` to place the object in the right
        virtual system of the right firewall. A template's device entry and
        a firewall's own config use the placeholder name
        'localhost.localdomain', which means "this device"; the emitter
        treats it as no device name (F3.5).
        """
        node = elem
        while node is not None:
            parent = self.parent_map.get(node)
            if parent is not None and parent.tag == 'devices' and node.tag == 'entry':
                return node.get('name') or ''
            node = parent
        return ''

    def identity_of(self, elem: ET.Element) -> dict:
        """Return the four source scope facts of an entry (F3.5).

        Every parse method records these on every object, so the emitter can
        place a resource without looking at the XML again:

            device_group  - the defining device group, 'Shared' for the
                            shared section (F2.3)
            vsys          - the declared virtual system, '' when the export
                            declares none
            template      - the declared template, '' when the export
                            declares none
            vsys_device   - the device that owns a vsys-scoped entry, used
                            as the location `ngfw_device`
        """
        return {
            'device_group': self.device_group_of(elem),
            'vsys': self.vsys_of(elem),
            'template': self.template_of(elem),
            'vsys_device': self.device_of(elem),
        }

    @staticmethod
    def _list_names(container: ET.Element, child_tag: str) -> list:
        """Return the names a container lists, in document order.

        A Panorama export lists members two ways: the long form
        `<devices><entry name="fw-1.example.com">` and the short form
        `<templates><member>T1</member>`. Both mean the same thing.
        """
        names = []
        listing = container.find(child_tag)
        if listing is None:
            return names
        for node in list(listing):
            if node.tag == 'entry':
                name = node.get('name')
            elif node.tag == 'member':
                name = (node.text or '').strip()
            else:
                continue
            if name:
                names.append(name)
        return names

    def parse_associations(self) -> dict:
        """Return the device membership the export declares (F3.6).

        A Panorama export states the multi-device relationships in data, so
        the converter never infers one from a name:

            device-group/entry/<DG>/devices/entry/<device>
                the devices the device group contains
            templates/entry/<T>/devices/entry/<device>
                the devices the template targets
            template-stack/entry/<S>/devices/entry/<device>
                the devices the stack targets
            template-stack/entry/<S>/templates/member/<T>
                the templates the stack applies

        Returns four name-keyed tables (device_groups, templates,
        template_stacks, stack_templates), each value sorted so the result
        does not depend on document order. An export that lists no device
        returns empty tables: no association is better than a guessed one.
        """
        cached = getattr(self, '_associations', None)
        if cached is not None:
            return cached

        tables = {'device_groups': {}, 'templates': {}, 'template_stacks': {},
                  'stack_templates': {}}
        for entry in self.root.findall('.//device-group/entry'):
            name = entry.get('name')
            if name:
                # F4.3: the membership an association entry states is the whole
                # fact the parser takes, so the mark records it.
                devices = self._list_names(entry, 'devices')
                self.mark(entry, {'devices': devices})
                for device in devices:
                    tables['device_groups'].setdefault(device, []).append(name)
        for entry in self.root.findall('.//templates/entry'):
            name = entry.get('name')
            if name:
                devices = self._list_names(entry, 'devices')
                self.mark(entry, {'devices': devices})
                for device in devices:
                    tables['templates'].setdefault(device, []).append(name)
        for entry in self.root.findall('.//template-stack/entry'):
            name = entry.get('name')
            if not name:
                self.mark_skipped(entry, "entry has no name attribute")
                continue
            devices = self._list_names(entry, 'devices')
            templates = self._list_names(entry, 'templates')
            self.mark(entry, {'devices': devices, 'templates': templates})
            for device in devices:
                tables['template_stacks'].setdefault(device, []).append(name)
            for template in templates:
                tables['stack_templates'].setdefault(name, []).append(template)
        for table in tables.values():
            for names in table.values():
                names.sort()

        self._associations = tables
        return tables

    def templates_for_device(self, device: str) -> list:
        """Return the templates that apply to a device (F3.6).

        A device takes a template directly or through a template stack, so
        the effective set is the union. Sorted and de-duplicated; an empty
        or unknown device name returns [].
        """
        if not device:
            return []
        tables = self.parse_associations()
        names = list(tables['templates'].get(device, []))
        for stack in tables['template_stacks'].get(device, []):
            names.extend(tables['stack_templates'].get(stack, []))
        return sorted(set(names))

    def parse_tags(self) -> list[dict]:
        """Parse tags (administrative tags).

        F3.1: one object per XML entry, keyed by
        (device group, vsys, type, name). The broad path visits each entry
        exactly once, so no name dedup is needed.
        """
        tags = []

        for tag in self.root.findall(".//tag/entry"):
            name = tag.get('name')
            if not name:
                self.mark_skipped(tag, "entry has no name attribute")
                continue

            tags.append(self.mark(tag, {
                'name': name,
                **self.identity_of(tag),
                'color': self._get_text(tag, 'color'),
                'comments': self._get_text(tag, 'comments')
            }))

        return tags

    def parse_regions(self) -> list[dict]:
        """Parse regions (geographic locations).

        F3.1: one object per XML entry, keyed by
        (device group, vsys, type, name); no name dedup.
        """
        regions = []

        for region in self.root.findall(".//region/entry"):
            name = region.get('name')
            if not name:
                self.mark_skipped(region, "entry has no name attribute")
                continue

            addresses = []
            for addr in region.findall('.//address/member'):
                if addr.text:
                    addresses.append(addr.text)

            regions.append(self.mark(region, {
                'name': name,
                **self.identity_of(region),
                'addresses': addresses
            }))

        return regions

    def parse_custom_url_categories(self) -> list[dict]:
        """Parse custom URL categories.

        F3.1: one object per XML entry, keyed by
        (device group, vsys, type, name); no name dedup.
        """
        categories = []

        for cat in self.root.findall(".//custom-url-category/entry"):
            name = cat.get('name')
            if not name:
                self.mark_skipped(cat, "entry has no name attribute")
                continue

            url_list = []
            for url in cat.findall('.//list/member'):
                if url.text:
                    url_list.append(url.text)

            categories.append(self.mark(cat, {
                'name': name,
                **self.identity_of(cat),
                'type': self._get_text(cat, 'type'),
                'list': url_list,
                'description': self._get_text(cat, 'description')
            }))

        return categories

    def parse_application_groups(self) -> list[dict]:
        """Parse application groups.

        F3.1: one object per XML entry, keyed by
        (device group, vsys, type, name); no name dedup.
        """
        app_groups = []

        for ag in self.root.findall(".//application-group/entry"):
            name = ag.get('name')
            if not name:
                self.mark_skipped(ag, "entry has no name attribute")
                continue

            members = []
            for member in ag.findall('.//members/member'):
                if member.text:
                    members.append(member.text)

            app_groups.append(self.mark(ag, {
                'name': name,
                **self.identity_of(ag),
                'members': members
            }))

        return app_groups

    def parse_application_filters(self) -> list[dict]:
        """Parse application filters.

        F3.1: one object per XML entry, keyed by
        (device group, vsys, type, name); no name dedup.
        """
        app_filters = []

        for af in self.root.findall(".//application-filter/entry"):
            name = af.get('name')
            if not name:
                self.mark_skipped(af, "entry has no name attribute")
                continue

            app_filters.append(self.mark(af, {
                'name': name,
                **self.identity_of(af),
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
            }))

        return app_filters

    def parse_external_lists(self) -> list[dict]:
        """Parse external dynamic lists.

        F3.1: one object per XML entry, keyed by
        (device group, vsys, type, name); no name dedup.

        F3.4: the full v2.0.14 sub-shape set (domain, imei, imsi, ip,
        predefined_ip, predefined_url, url) and every field the schema
        models inside the sub-shape. The auth block is not captured: it
        carries credential material, and the converter does not write
        secrets into generated HCL (recorded in backlog.md).
        """
        ext_lists = []

        for ext_list in self.root.findall(".//external-list/entry"):
            name = ext_list.get('name')
            if not name:
                self.mark_skipped(ext_list, "entry has no name attribute")
                continue

            entry = self.mark(ext_list, {
                'name': name,
                **self.identity_of(ext_list),
                'type': '',
                # Fields captured inside the type sub-shape, keyed by the v2
                # attribute name (url, description, exception_list, recurring,
                # expand_domain, certificate_profile)
                'fields': {},
            })

            type_elem = ext_list.find('type')
            if type_elem is not None:
                for sub in type_elem:
                    if sub.tag not in self.EDL_TYPE_ELEMENTS:
                        continue
                    entry['type'] = self.EDL_TYPE_ELEMENTS[sub.tag]
                    for field in sub:
                        if field.tag == 'exception-list':
                            values = [m.text.strip() for m in field.findall('member')
                                      if m.text and m.text.strip()]
                            if values:
                                entry['fields']['exception_list'] = values
                        elif field.tag == 'recurring':
                            for sched in field:
                                if sched.tag not in self.EDL_RECURRING_ELEMENTS:
                                    continue
                                # A recurring key may be a bare flag (hourly,
                                # five-minute) or carry values (at, day_of_week)
                                block = {}
                                for value in sched:
                                    if value.text and value.text.strip():
                                        block[value.tag.replace('-', '_')] = value.text.strip()
                                entry['fields']['recurring'] = {
                                    self.EDL_RECURRING_ELEMENTS[sched.tag]: block
                                }
                        elif field.tag in self.EDL_FIELD_ELEMENTS:
                            text = (field.text or '').strip()
                            if text:
                                key = self.EDL_FIELD_ELEMENTS[field.tag]
                                if key == 'expand_domain':
                                    # v2 models expand_domain as a bool
                                    entry['fields'][key] = text.lower() == 'yes'
                                else:
                                    entry['fields'][key] = text

            # The entry-level description is the fallback for the sub-shape
            # description attribute (the schema exposes only the sub-shape one).
            if 'description' not in entry['fields']:
                desc = self._get_text(ext_list, 'description')
                if desc:
                    entry['fields']['description'] = desc.strip()

            ext_lists.append(entry)

        return ext_lists

    def parse_address_objects(self) -> list[dict]:
        """Parse address objects.

        F3.1: one object per XML entry, keyed by
        (device group, vsys, type, name). The broad path visits each entry
        exactly once in document order, so no name dedup is needed.

        An entry that carries only <id> is a reference pointer to a shared
        definition and has no content of its own, so it is skipped.

        F3.4: every value element the v2 schema models is read, including
        ip-wildcard. An entry with content but no modeled value element (a
        location-type address: country/region/continent/container) cannot be
        emitted as a valid panos_address, so its fields are captured
        generically and the entry is marked report_only.
        """
        addresses = []

        for addr in self.root.findall(".//address/entry"):
            name = addr.get('name')
            if not name:
                self.mark_skipped(addr, "entry has no name attribute")
                continue

            # A reference pointer has no content: skip it.
            if self._is_reference_pointer(addr):
                # F4.3: the entry is visited and skipped, so the report says why.
                self.mark_skipped(addr, 'reference pointer (id only)')
                continue

            addr_obj = self.mark(addr, {
                'name': name,
                **self.identity_of(addr),
                # PAN-OS records the object type as an entry attribute
                'declared_type': addr.get('type') or '',
                'other': {},
            })

            for child in addr:
                tag = child.tag
                if tag in self.ADDRESS_VALUE_ELEMENTS:
                    # PAN-OS stores exactly one value element per entry; the
                    # first one wins so the result is order-stable.
                    if 'type' not in addr_obj:
                        addr_obj['type'] = self.ADDRESS_VALUE_ELEMENTS[tag]
                        addr_obj['value'] = (child.text or '').strip()
                elif tag == 'description':
                    addr_obj['description'] = (child.text or '').strip()
                elif tag == 'disable-override':
                    addr_obj['disable_override'] = (child.text or '').strip()
                elif tag == 'tag':
                    addr_obj['tags'] = [m.text.strip() for m in child.findall('member')
                                        if m.text and m.text.strip()]
                else:
                    # Not modeled by panos_address (location-type fields).
                    # Keep the value so the report can show it.
                    if child.text and child.text.strip():
                        addr_obj['other'][tag] = child.text.strip()

            addr_obj.setdefault('tags', [])
            # No v2 attribute exists for this entry's content: it cannot be
            # emitted as a valid resource, so it is reported instead.
            if 'type' not in addr_obj and addr_obj['other']:
                addr_obj['report_only'] = True

            addresses.append(addr_obj)

        return addresses

    def _is_reference_pointer(self, elem: ET.Element) -> bool:
        """True if elem is an entry that only carries an <id> pointer.

        Panorama emits such entries to reference a shared definition; they
        have no content of their own (F3.1 keeps them out of the model).
        """
        if elem.find('id') is None:
            return False
        return all(child.tag == 'id' for child in elem)

    def parse_address_groups(self) -> list[dict]:
        """Parse address groups.

        F3.1: one object per XML entry, keyed by
        (device group, vsys, type, name). The broad path visits each entry
        exactly once, so no name dedup is needed. Entries that carry only
        <id> are reference pointers and are skipped.
        """
        groups = []

        for grp in self.root.findall(".//address-group/entry"):
            name = grp.get('name')
            if not name:
                self.mark_skipped(grp, "entry has no name attribute")
                continue

            if self._is_reference_pointer(grp):
                # F4.3: the entry is visited and skipped, so the report says why.
                self.mark_skipped(grp, 'reference pointer (id only)')
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

            groups.append(self.mark(grp, {
                'name': name,
                **self.identity_of(grp),
                'static_members': members,
                'dynamic_filter': filter_expr,
                'description': self._get_text(grp, 'description')
            }))

        return groups

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
        """Parse service objects.

        F3.1: one object per XML entry, keyed by (device group, vsys, type,
        name); no name dedup. Entries that carry only <id> are reference
        pointers and are skipped.

        F3.4: both protocol sub-blocks are captured, so a dual-protocol
        object keeps tcp AND udp. Multi-port values ("80,443") stay one
        string, which is the v2 destination_port shape. source-port, the
        override timeouts, and tag members are captured (the F1.2 gaps).
        """
        services = []

        for svc in self.root.findall(".//service/entry"):
            name = svc.get('name')
            if not name:
                self.mark_skipped(svc, "entry has no name attribute")
                continue

            if self._is_reference_pointer(svc):
                # F4.3: the entry is visited and skipped, so the report says why.
                self.mark_skipped(svc, 'reference pointer (id only)')
                continue

            service_obj = self.mark(svc, {
                'name': name,
                **self.identity_of(svc),
                # Protocol sub-blocks, keyed by 'tcp' / 'udp'. The parse model
                # keeps both legs; the emitter can only write one (v2 limit).
                # Each leg holds destination_port, source_port, and override.
                'protocols': {},
                'tags': [],
            })

            protocol = svc.find('protocol')
            if protocol is not None:
                for sub in protocol:
                    if sub.tag not in ('tcp', 'udp'):
                        # v2 models only tcp and udp; keep the rest visible
                        service_obj.setdefault('other_protocol', {})[sub.tag] = \
                            (sub.text or '').strip()
                        continue
                    block = {}
                    for field in sub:
                        text = (field.text or '').strip()
                        if field.tag in ('port', 'source-port'):
                            if text:
                                block['destination_port' if field.tag == 'port'
                                       else 'source_port'] = text
                        elif field.tag == 'override':
                            # Export shape: override/yes/<timeout>. The bare
                            # override/<timeout> shape is accepted as well.
                            body = field.find('yes')
                            nums = {}
                            for t in (body if body is not None else field):
                                value = (t.text or '').strip()
                                if value:
                                    nums[t.tag.replace('-', '_')] = int(value) if value.isdigit() else value
                            if nums:
                                block['override'] = nums
                    if block:
                        service_obj['protocols'][sub.tag] = block

            for tag_elem in svc.findall('.//tag/member'):
                if tag_elem.text and tag_elem.text.strip():
                    service_obj['tags'].append(tag_elem.text.strip())

            service_obj['description'] = (self._get_text(svc, 'description') or '').strip()
            services.append(service_obj)

        return services

    def parse_service_groups(self) -> list[dict]:
        """Parse service groups.

        F3.1: one object per XML entry, keyed by
        (device group, vsys, type, name); no name dedup. Entries that
        carry only <id> are reference pointers and are skipped.
        """
        groups = []

        for grp in self.root.findall(".//service-group/entry"):
            name = grp.get('name')
            if not name:
                self.mark_skipped(grp, "entry has no name attribute")
                continue

            if self._is_reference_pointer(grp):
                # F4.3: the entry is visited and skipped, so the report says why.
                self.mark_skipped(grp, 'reference pointer (id only)')
                continue

            members = []
            for member in grp.findall('.//members/member'):
                if member.text:
                    members.append(member.text)

            groups.append(self.mark(grp, {
                'name': name,
                **self.identity_of(grp),
                'members': members,
                'description': self._get_text(grp, 'description')
            }))

        return groups

    def parse_security_rules(self) -> list[dict]:
        """Parse security policy rules.

        F3.1: one rule per XML entry, keyed by
        (device group, vsys, type, name). The broad path visits each entry
        exactly once in document order, so no name dedup is needed.
        """
        rules = []

        for rule in self.root.findall(".//security/rules/entry"):
            name = rule.get('name')
            if not name:
                self.mark_skipped(rule, "entry has no name attribute")
                continue

            rule_obj = self.mark(rule, {
                'name': name,
                **self.identity_of(rule),
                'source_zones': self._get_members(rule, 'from'),
                'source_addresses': self._get_members(rule, 'source'),
                'destination_zones': self._get_members(rule, 'to'),
                'destination_addresses': self._get_members(rule, 'destination'),
                'applications': self._get_members(rule, 'application'),
                'services': self._get_members(rule, 'service'),
                'action': self._get_text(rule, 'action'),
                'description': self._get_text(rule, 'description')
            })

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
        """Parse NAT policy rules.

        F3.1: one rule per XML entry, keyed by
        (device group, vsys, type, name); single pass, no name dedup.
        """
        rules = []

        for rule in self.root.findall(".//nat/rules/entry"):
            name = rule.get('name')
            if not name:
                self.mark_skipped(rule, "entry has no name attribute")
                continue

            rule_obj = self.mark(rule, {
                'name': name,
                **self.identity_of(rule),
                'source_zones': self._get_members(rule, 'from'),
                'destination_zone': self._get_text(rule, 'to-interface'),
                'source_addresses': self._get_members(rule, 'source'),
                'destination_addresses': self._get_members(rule, 'destination'),
                'service': self._get_text(rule, 'service'),
                'description': self._get_text(rule, 'description')
            })

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
        """Parse schedules.

        F3.1: one object per XML entry, keyed by
        (device group, vsys, type, name); single pass, no name dedup.
        """
        schedules = []

        for sched in self.root.findall(".//schedule/entry"):
            name = sched.get('name')
            if not name:
                self.mark_skipped(sched, "entry has no name attribute")
                continue

            sched_obj = self.mark(sched, {
                'name': name,
                **self.identity_of(sched),
                'schedule_type': None,
                'recurring': []
            })

            # Check for recurring schedule
            recurring = sched.find('schedule-type/recurring')
            if recurring is not None:
                sched_obj['schedule_type'] = 'recurring'
                for entry in recurring.findall('entry'):
                    rec_name = entry.get('name')
                    rec_obj = self.mark(entry, {'name': rec_name})
                    sched_obj['recurring'].append(rec_obj)

            # Check for non-recurring schedule
            non_recurring = sched.find('schedule-type/non-recurring')
            if non_recurring is not None:
                sched_obj['schedule_type'] = 'non-recurring'

            schedules.append(sched_obj)

        return schedules

    def parse_decryption_rules(self) -> list[dict]:
        """Parse decryption policy rules.

        F3.1: one rule per XML entry, keyed by
        (device group, vsys, type, name); single pass, no name dedup.
        """
        rules = []

        for rule in self.root.findall(".//decryption/rules/entry"):
            name = rule.get('name')
            if not name:
                self.mark_skipped(rule, "entry has no name attribute")
                continue

            rule_obj = self.mark(rule, {
                'name': name,
                'uuid': rule.get('uuid'),
                # F2.9: the device group scopes the v2 resource and its
                # rule chain (location + position pivot semantics, F2.5)
                **self.identity_of(rule),
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
            })

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
        """Parse Policy-Based Forwarding rules.

        F3.1: one rule per XML entry, keyed by
        (device group, vsys, type, name); single pass, no name dedup.
        """
        rules = []

        for rule in self.root.findall(".//pbf/rules/entry"):
            name = rule.get('name')
            if not name:
                self.mark_skipped(rule, "entry has no name attribute")
                continue

            rule_obj = self.mark(rule, {
                'name': name,
                'uuid': rule.get('uuid'),
                # F2.9: the device group scopes the v2 resource and its
                # rule chain (location + position pivot semantics, F2.5)
                **self.identity_of(rule),
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
            })

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
        """Parse Application Override rules.

        F3.1: one rule per XML entry, keyed by
        (device group, vsys, type, name); single pass, no name dedup.
        """
        rules = []

        for rule in self.root.findall(".//application-override/rules/entry"):
            name = rule.get('name')
            if not name:
                self.mark_skipped(rule, "entry has no name attribute")
                continue

            rule_obj = self.mark(rule, {
                'name': name,
                **self.identity_of(rule),
                'description': self._get_text(rule, 'description'),
                'disabled': self._get_text(rule, 'disabled') == 'yes',
                'source_zones': self._get_members(rule, 'from'),
                'destination_zones': self._get_members(rule, 'to'),
                'source_addresses': self._get_members(rule, 'source'),
                'destination_addresses': self._get_members(rule, 'destination'),
                'port': self._get_text(rule, 'port'),
                'protocol': self._get_text(rule, 'protocol'),
                'application': self._get_text(rule, 'application')
            })

            rules.append(rule_obj)

        return rules

    def parse_zones(self) -> list[dict]:
        """Parse zone configurations.

        F3.1: one zone per XML entry, keyed by
        (device group, vsys, type, name); single pass, no name dedup.
        F3.5: identity_of records the declaring template and the owning
        device, which is what the v2 location needs.
        """
        zones = []

        for zone in self.root.findall(".//zone/entry"):
            name = zone.get('name')
            if not name:
                self.mark_skipped(zone, "entry has no name attribute")
                continue

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

            zones.append(self.mark(zone, {
                'name': name,
                **self.identity_of(zone),
                'type': zone_type,
                'interfaces': interfaces,
                'zone_protection_profile': zone_profile.text if zone_profile is not None else None
            }))

        return zones

    def parse_interfaces(self) -> list[dict]:
        """Parse interface configurations"""
        interfaces = []
        # Ethernet interfaces
        for iface in self.root.findall(".//network/interface/ethernet/entry"):
            name = iface.get('name')
            if not name:
                self.mark_skipped(iface, "entry has no name attribute")
                continue

            iface_obj = self.mark(iface, {
                'name': name,
                'type': 'ethernet',
                **self.identity_of(iface),
                'mode': None,
                'ip_addresses': [],
                'ipv6_addresses': [],
                'zone': None,
                'virtual_router': None,
                'management_profile': None,
                'comment': self._get_text(iface, 'comment'),
                'parent': None
            })

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

            # F3.3: subinterface units are individual entries. The parent is
            # the physical entry name; the unit name is the tag.
            for unit in iface.findall('units/entry'):
                unit_name = unit.get('name')
                if not unit_name:
                    self.mark_skipped(unit, 'unit entry has no name')
                    continue
                sub = self.mark(unit, {
                    'name': f'{name}.{unit_name}',
                    'type': 'ethernet-subinterface',
                    **self.identity_of(unit),
                    'mode': 'layer3',
                    'ip_addresses': [ip.get('name') for ip in unit.findall('.//ip/entry')
                                     if ip.get('name')],
                    'ipv6_addresses': [ip.get('name') for ip in unit.findall('.//ipv6/address/entry')
                                       if ip.get('name')],
                    'zone': None,
                    'virtual_router': None,
                    'management_profile': None,
                    'comment': self._get_text(unit, 'comment'),
                    'tag': unit_name,
                    'parent': name,
                })
                interfaces.append(sub)

        # Virtual-wire interface units. PAN-OS keeps them in a separate
        # container; the provider models them as panos_ethernet_interface
        # with a virtual_wire block (there is no virtual-wire resource type).
        for iface in self.root.findall(".//network/interface/virtual-wire/units/entry"):
            name = iface.get('name')
            if not name:
                self.mark_skipped(iface, "entry has no name attribute")
                continue
            iface_obj = self.mark(iface, {
                'name': name,
                'type': 'ethernet',
                **self.identity_of(iface),
                'mode': 'virtual-wire',
                'ip_addresses': [],
                'ipv6_addresses': [],
                'zone': None,
                'virtual_router': None,
                'management_profile': None,
                'comment': self._get_text(iface, 'comment'),
                'parent': name.split('.')[0] if '.' in name else None,
            })
            interfaces.append(iface_obj)

        # VLAN interfaces
        for iface in self.root.findall(".//network/interface/vlan/units/entry"):
            name = iface.get('name')
            # Dedupe on the namespaced name so a vlan unit number does
            # not collide with a loopback/tunnel unit of the same number.
            full_name = f'vlan.{name}'
            if not name:
                self.mark_skipped(iface, "entry has no name attribute")
                continue

            iface_obj = self.mark(iface, {
                'name': full_name,
                'type': 'vlan',
                **self.identity_of(iface),
                'mode': 'layer3',
                'ip_addresses': [],
                'ipv6_addresses': [],
                'zone': None,
                'virtual_router': None,
                'management_profile': None,
                'comment': self._get_text(iface, 'comment'),
                'tag': self._get_text(iface, 'tag'),
                'parent': None
            })

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
        for iface in self.root.findall(".//network/interface/loopback/units/entry"):
            name = iface.get('name')
            # Dedupe on the namespaced name so a loopback unit number
            # does not collide with a vlan/tunnel unit of the same number.
            full_name = f'loopback.{name}'
            if not name:
                self.mark_skipped(iface, "entry has no name attribute")
                continue

            iface_obj = self.mark(iface, {
                'name': full_name,
                'type': 'loopback',
                **self.identity_of(iface),
                'mode': 'layer3',
                'ip_addresses': [],
                'ipv6_addresses': [],
                'zone': None,
                'virtual_router': None,
                'management_profile': None,
                'comment': self._get_text(iface, 'comment'),
                'parent': None
            })

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
        for iface in self.root.findall(".//network/interface/tunnel/units/entry"):
            name = iface.get('name')
            # Dedupe on the namespaced name so a tunnel unit number
            # does not collide with a vlan/loopback unit of the same number.
            full_name = f'tunnel.{name}'
            if not name:
                self.mark_skipped(iface, "entry has no name attribute")
                continue

            iface_obj = self.mark(iface, {
                'name': full_name,
                'type': 'tunnel',
                **self.identity_of(iface),
                'mode': 'layer3',
                'ip_addresses': [],
                'ipv6_addresses': [],
                'zone': None,
                'virtual_router': None,
                'management_profile': None,
                'comment': self._get_text(iface, 'comment'),
                'parent': None
            })

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
        for iface in self.root.findall(".//network/interface/aggregate-ethernet/entry"):
            name = iface.get('name')
            if not name:
                self.mark_skipped(iface, "entry has no name attribute")
                continue

            iface_obj = self.mark(iface, {
                'name': name,
                'type': 'aggregate',
                **self.identity_of(iface),
                'mode': None,
                'ip_addresses': [],
                'ipv6_addresses': [],
                'zone': None,
                'virtual_router': None,
                'management_profile': None,
                'comment': self._get_text(iface, 'comment'),
                # An aggregate entry name can already be a subinterface
                # (ae1.101); the parent is the aggregate group name and the
                # unit number is the tag.
                'parent': name.split('.')[0] if '.' in name else None,
                'tag': name.split('.')[1] if '.' in name else None
            })
            units = []

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
                    if unit_name:

                        unit_obj = self.mark(unit, {
                            'name': unit_name,
                            'type': 'aggregate-subinterface',
                            **self.identity_of(unit),
                            'mode': 'layer3',
                            'ip_addresses': [],
                            'ipv6_addresses': [],
                            'zone': None,
                            'virtual_router': None,
                            'management_profile': None,
                            'comment': self._get_text(unit, 'comment'),
                            'tag': self._get_text(unit, 'tag'),
                            'parent': name
                        })

                        # Get IP addresses
                        for ip in unit.findall('.//ip/entry'):
                            ip_name = ip.get('name')
                            if ip_name:
                                unit_obj['ip_addresses'].append(ip_name)

                        # Management profile
                        unit_mgmt = unit.find('interface-management-profile')
                        if unit_mgmt is not None:
                            unit_obj['management_profile'] = unit_mgmt.text

                        units.append(unit_obj)

            elif iface.find('layer2') is not None:
                iface_obj['mode'] = 'layer2'

            # Append the parent entry before its units so the unit's parent
            # reference resolves to a declared resource (F2.6 rule).
            interfaces.append(iface_obj)
            interfaces.extend(units)

        return interfaces

    def _parse_router(self, router: ET.Element, next_hop_tag: str) -> dict:
        """Parse one <virtual-router> or <logical-router> entry.

        `next_hop_tag` names the static-route next-hop element, which
        differs by router kind: next-vr for a virtual router, next-lr for
        a logical router.
        """
        interfaces = [m.text for m in router.findall('./interface/member') if m.text]
        static_routes = []
        for route in router.findall('.//routing-table/ip/static-route/entry'):
            route_name = route.get('name')
            if not route_name:
                continue
            static_routes.append(self.mark(route, {
                'name': route_name,
                'destination': self._get_text(route, 'destination'),
                'nexthop_ip': self._get_text(route, 'nexthop/ip-address'),
                'nexthop_interface': self._get_text(route, f'nexthop/{next_hop_tag}'),
                'metric': self._get_text(route, 'metric'),
            }))
        return {
            'name': router.get('name'),
            **self.identity_of(router),
            'interfaces': interfaces,
            'static_routes': static_routes,
        }

    def _parse_routers(self, container_tag: str, next_hop_tag: str,
                       router_type: Optional[str] = None) -> list[dict]:
        """Parse every router of one kind, whatever scope it lives in.

        F3.5: one path, `.//network/<kind>/entry`, covers every place a
        PAN-OS export puts a router, and each entry's identity comes from
        its own ancestors:

            templates/entry/<T>/network/...                       -> template <T>
            templates/entry/<T>/devices/entry/<D>/network/...     -> template <T>, device <D>
            devices/entry/<D>/network/...                         -> device <D>
            devices/entry/<D>/vsys/entry/<V>/network/...          -> device <D>, vsys <V>

        The old code walked <templates> first and then only the vsys-nested
        device shape, so it dropped a router under
        devices/entry/<D>/network, the shape a firewall's own config export
        and a template's device config use. Each entry is visited once, so
        no name-based dedup is needed and same-name routers in different
        scopes all survive (F3.1).
        """
        routers = []
        for elem in self.root.findall(f'.//network/{container_tag}/entry'):
            if not elem.get('name'):
                continue
            obj = self.mark(elem, self._parse_router(elem, next_hop_tag))
            if router_type:
                obj['router_type'] = router_type
            routers.append(obj)
        return routers

    def parse_virtual_routers(self) -> list[dict]:
        """Parse virtual router configurations (see _parse_routers for paths)."""
        return self._parse_routers('virtual-router', 'next-vr')

    def parse_logical_routers(self) -> list[dict]:
        """Parse logical routers (PAN-OS 10.2+ Advanced Routing Engine).

        Logical routers replace virtual routers on the advanced routing
        engine; the export nests them at network/logical-router. They are
        marked router_type 'logical' so the emitter can label the resource
        (see _parse_routers for the source paths).
        """
        return self._parse_routers('logical-router', 'next-lr', router_type='logical')


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

        # Antivirus profiles
        for prof in self.root.findall(".//profiles/virus/entry"):
            name = prof.get('name')
            if not name:
                self.mark_skipped(prof, "entry has no name attribute")
                continue

            profiles['antivirus'].append(self.mark(prof, {
                'name': name,
                **self.identity_of(prof),
                'description': self._get_text(prof, 'description')
            }))

        # Vulnerability profiles
        for prof in self.root.findall(".//profiles/vulnerability/entry"):
            name = prof.get('name')
            if not name:
                self.mark_skipped(prof, "entry has no name attribute")
                continue

            profiles['vulnerability'].append(self.mark(prof, {
                'name': name,
                **self.identity_of(prof),
                'description': self._get_text(prof, 'description')
            }))

        # Anti-spyware profiles
        for prof in self.root.findall(".//profiles/spyware/entry"):
            name = prof.get('name')
            if not name:
                self.mark_skipped(prof, "entry has no name attribute")
                continue

            profiles['anti_spyware'].append(self.mark(prof, {
                'name': name,
                **self.identity_of(prof),
                'description': self._get_text(prof, 'description')
            }))

        # URL filtering profiles
        for prof in self.root.findall(".//profiles/url-filtering/entry"):
            name = prof.get('name')
            if not name:
                self.mark_skipped(prof, "entry has no name attribute")
                continue

            profiles['url_filtering'].append(self.mark(prof, {
                'name': name,
                **self.identity_of(prof),
                'description': self._get_text(prof, 'description')
            }))

        # File blocking profiles
        for prof in self.root.findall(".//profiles/file-blocking/entry"):
            name = prof.get('name')
            if not name:
                self.mark_skipped(prof, "entry has no name attribute")
                continue

            profiles['file_blocking'].append(self.mark(prof, {
                'name': name,
                **self.identity_of(prof),
                'description': self._get_text(prof, 'description')
            }))

        # WildFire analysis profiles
        for prof in self.root.findall(".//profiles/wildfire-analysis/entry"):
            name = prof.get('name')
            if not name:
                self.mark_skipped(prof, "entry has no name attribute")
                continue

            profiles['wildfire_analysis'].append(self.mark(prof, {
                'name': name,
                **self.identity_of(prof),
                'description': self._get_text(prof, 'description')
            }))

        return profiles

    def parse_security_profile_groups(self) -> list[dict]:
        """Parse security profile groups.

        F3.1: one object per XML entry, keyed by
        (device group, vsys, type, name); single pass, no name dedup.
        """
        groups = []

        for grp in self.root.findall(".//profile-group/entry"):
            name = grp.get('name')
            if not name:
                self.mark_skipped(grp, "entry has no name attribute")
                continue

            groups.append(self.mark(grp, {
                'name': name,
                **self.identity_of(grp),
                'virus': self._get_members(grp, 'virus'),
                'spyware': self._get_members(grp, 'spyware'),
                'vulnerability': self._get_members(grp, 'vulnerability'),
                'url_filtering': self._get_members(grp, 'url-filtering'),
                'file_blocking': self._get_members(grp, 'file-blocking'),
                'wildfire_analysis': self._get_members(grp, 'wildfire-analysis')
            }))

        return groups

    def parse_zone_protection_profiles(self) -> list[dict]:
        """Parse zone protection profiles.

        F3.1: one object per XML entry, keyed by
        (device group, vsys, type, name); single pass, no name dedup.
        """
        profiles = []

        for prof in self.root.findall(".//zone-protection-profile/entry"):
            name = prof.get('name')
            if not name:
                self.mark_skipped(prof, "entry has no name attribute")
                continue

            profiles.append(self.mark(prof, {
                'name': name,
                **self.identity_of(prof),
                'description': self._get_text(prof, 'description')
            }))

        return profiles

    def parse_log_settings(self) -> list[dict]:
        """Parse log forwarding profiles.

        F3.1: one object per XML entry, keyed by
        (device group, vsys, type, name); single pass, no name dedup.
        """
        profiles = []

        for prof in self.root.findall(".//log-settings/profiles/entry"):
            name = prof.get('name')
            if not name:
                self.mark_skipped(prof, "entry has no name attribute")
                continue

            profiles.append(self.mark(prof, {
                'name': name,
                **self.identity_of(prof),
                'description': self._get_text(prof, 'description')
            }))

        return profiles

    def parse_qos_profiles(self) -> list[dict]:
        """Parse QoS profiles.

        F3.1: one object per XML entry, keyed by
        (device group, vsys, type, name); single pass, no name dedup.
        """
        profiles = []

        for prof in self.root.findall(".//qos/profile/entry"):
            name = prof.get('name')
            if not name:
                self.mark_skipped(prof, "entry has no name attribute")
                continue

            prof_obj = self.mark(prof, {
                'name': name,
                **self.identity_of(prof),
                'class_bandwidth_type': {}
            })

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
        """Parse tunnel monitor profiles.

        F3.1: one object per XML entry, keyed by
        (device group, vsys, type, name). The two paths are disjoint XML
        locations (GlobalProtect gateway vs plain tunnel-monitor), so both
        are kept and each entry is visited exactly once.
        """
        profiles = []

        paths = [
            ".//network/tunnel/global-protect-gateway/Default/tunnel-monitor/monitor-profile/entry",
            ".//network/tunnel-monitor/monitor-profile/entry"
        ]

        for path in paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name:
                    continue

                profiles.append(self.mark(prof, {
                    'name': name,
                    **self.identity_of(prof),
                    'interval': self._get_text(prof, 'interval'),
                    'threshold': self._get_text(prof, 'threshold'),
                    'action': self._get_text(prof, 'action')
                }))

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

        F3.1: one object per XML entry, keyed by
        (device group, vsys, type, name); single pass, no name dedup.
        """
        profiles = []

        for prof in self.root.findall(".//network/profiles/monitor-profile/entry"):
            name = prof.get('name')
            if not name:
                self.mark_skipped(prof, "entry has no name attribute")
                continue

            profiles.append(self.mark(prof, {
                'name': name,
                **self.identity_of(prof),
                # v2 action is an enum: wait-recover | fail-over
                'action': self._get_text(prof, 'action'),
                'interval': self._get_text(prof, 'interval'),
                'threshold': self._get_text(prof, 'threshold')
            }))

        return profiles

    def parse_bgp(self) -> list[dict]:
        """Parse BGP configuration: one record per virtual router that has BGP enabled.

        F4.4 keeps one path. `.//` already reaches a router under a device, so the
        second path this method used read every device router twice. The record is
        the router, and it carries the four scope facts, so the report can name the
        scope the export places the router in (F3.9) instead of a single flat block.

        A router row belongs to `panos_virtual_router`, which `parse_virtual_routers`
        marks. The entries under the router are property level, so the marks here are
        the property entries the report counts on the router row.
        """
        routers = []

        for router in self.root.findall('.//network/virtual-router/entry'):
            bgp = router.find('protocol/bgp')
            if bgp is None or self._get_text(bgp, 'enable') != 'yes':
                continue

            record = {
                'name': router.get('name'),
                **self.identity_of(router),
                'router_id': self._get_text(bgp, 'router-id'),
                'as_number': self._get_text(bgp, 'local-as'),
                'peer_groups': [],
                'peers': [],
                'redistribution_rules': [],
            }

            # Peer Groups
            for pg in bgp.findall('.//peer-group/entry'):
                pg_name = pg.get('name')
                if pg_name:
                    record['peer_groups'].append(self.mark(pg, {
                        'name': pg_name,
                        'type': self._get_text(pg, 'type'),
                        'export_nexthop': self._get_text(pg, 'export-nexthop'),
                        'import_nexthop': self._get_text(pg, 'import-nexthop')
                    }))

            # BGP Peers
            for peer in bgp.findall('.//peer/entry'):
                peer_name = peer.get('name')
                if peer_name:
                    record['peers'].append(self.mark(peer, {
                        'name': peer_name,
                        'peer_as': self._get_text(peer, 'peer-as'),
                        'local_address_interface': self._get_text(peer, 'local-address/interface'),
                        'local_address_ip': self._get_text(peer, 'local-address/ip'),
                        'peer_address_ip': self._get_text(peer, 'peer-address/ip'),
                        'enable': self._get_text(peer, 'enable') == 'yes',
                        'peer_group': self._get_text(peer, 'peer-group')
                    }))

            # Redistribution rules
            for redist in bgp.findall('.//redist-rules/entry'):
                rule_name = redist.get('name')
                if rule_name:
                    record['redistribution_rules'].append(self.mark(redist, {
                        'name': rule_name,
                        'enable': self._get_text(redist, 'enable') == 'yes',
                        'address_family': self._get_text(redist, 'address-family-identifier')
                    }))

            routers.append(record)

        return routers

    def parse_ospf(self) -> list[dict]:
        """Parse OSPF configuration: one record per virtual router that has OSPF enabled.

        F4.4 keeps one path, the same rule as `parse_bgp`. The record is the router,
        with the four scope facts, so the report names the scope and the router.
        """
        routers = []

        for router in self.root.findall('.//network/virtual-router/entry'):
            ospf = router.find('protocol/ospf')
            if ospf is None or self._get_text(ospf, 'enable') != 'yes':
                continue

            record = {
                'name': router.get('name'),
                **self.identity_of(router),
                'router_id': self._get_text(ospf, 'router-id'),
                'areas': [],
                'interfaces': [],
            }

            # OSPF Areas
            for area in ospf.findall('.//area/entry'):
                area_id = area.get('name')
                if area_id:
                    area_config = self.mark(area, {
                        'area_id': area_id,
                        'type': 'normal'
                    })

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
                            # F4.3: the range entry is a name reference, so the
                            # parent row records it through the field it fills.
                            self.mark(range_entry, {'name': range_name},
                                      'name reference in field ranges')
                            ranges.append(range_name)
                    area_config['ranges'] = ranges

                    record['areas'].append(area_config)

            # OSPF Interfaces
            for iface in ospf.findall('.//interface/entry'):
                iface_name = iface.get('name')
                if iface_name:
                    record['interfaces'].append(self.mark(iface, {
                        'interface': iface_name,
                        'enable': self._get_text(iface, 'enable') == 'yes',
                        'passive': self._get_text(iface, 'passive') == 'yes',
                        'link_type': self._get_text(iface, 'link-type'),
                        'metric': self._get_text(iface, 'metric')
                    }))

            routers.append(record)

        return routers

    def parse_ipsec_tunnels(self) -> list[dict]:
        """Parse IPsec VPN tunnel configurations"""
        tunnels = []

        for tunnel in self.root.findall(".//network/tunnel/ipsec/entry"):
            name = tunnel.get('name')
            if not name:
                self.mark_skipped(tunnel, "entry has no name attribute")
                continue

            tunnel_config = self.mark(tunnel, {
                'name': name,
                **self.identity_of(tunnel),
                'tunnel_interface': self._get_text(tunnel, 'tunnel-interface'),
                'type': 'auto-key',  # Default
                'peer_address': None,
                'local_address': None,
                'auth_type': None,
                'preshared_key': None,
                'ike_gateway': None,
                'ipsec_crypto_profile': None
            })

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
                        proxy_config = self.mark(proxy, {
                            'name': proxy_name,
                            'local': self._get_text(proxy, 'local'),
                            'remote': self._get_text(proxy, 'remote'),
                            'protocol': self._get_text(proxy, 'protocol/number')
                        })
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

        for gw in self.root.findall(".//network/ike/gateway/entry"):
            name = gw.get('name')
            if not name:
                self.mark_skipped(gw, "entry has no name attribute")
                continue

            gateway_config = self.mark(gw, {
                'name': name,
                **self.identity_of(gw),
                'version': 'ikev1',  # Default
                'peer_address': None,
                'local_address': None,
                'pre_shared_key': '***CHANGE_ME***',  # Generic placeholder
                'auth_type': 'pre-shared-key',
                'ike_crypto_profile': None,
                'local_id': None,
                'peer_id': None
            })

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

        for profile in self.root.findall(".//network/ike/crypto-profiles/ike-crypto-profiles/entry"):
            name = profile.get('name')
            if not name:
                self.mark_skipped(profile, "entry has no name attribute")
                continue

            profile_config = self.mark(profile, {
                'name': name,
                **self.identity_of(profile),
                'dh_groups': self._get_members(profile, 'dh-group'),
                'authentications': self._get_members(profile, 'authentication'),
                'encryptions': self._get_members(profile, 'encryption'),
                'lifetime_hours': self._get_text(profile, 'lifetime/hours')
            })

            profiles.append(profile_config)

        return profiles

    def parse_ipsec_crypto_profiles(self) -> list[dict]:
        """Parse IPsec crypto profiles"""
        profiles = []

        for profile in self.root.findall(".//network/ike/crypto-profiles/ipsec-crypto-profiles/entry"):
            name = profile.get('name')
            if not name:
                self.mark_skipped(profile, "entry has no name attribute")
                continue

            profile_config = self.mark(profile, {
                'name': name,
                **self.identity_of(profile),
                'protocol': 'esp',  # Default
                'encryptions': self._get_members(profile, 'esp/encryption'),
                'authentications': self._get_members(profile, 'esp/authentication'),
                'dh_group': self._get_text(profile, 'dh-group'),
                'lifetime_hours': self._get_text(profile, 'lifetime/hours'),
                'lifetime_kb': self._get_text(profile, 'lifetime/kilobytes')
            })

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
# F3.3: a subinterface parent can be a physical interface, an aggregate
# group, or an aggregate layer-3 subinterface (ae1.101.20 has parent
# ae1.101), so parent resolution covers every interface scope.
IFACE_SCOPES = (
    'panos_ethernet_interface',
    'panos_ethernet_layer3_subinterface',
    'panos_aggregate_interface',
    'panos_aggregate_layer3_subinterface',
)
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

    def __init__(self, output_dir: str, associations: Optional[dict] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Collision handling for resource names. Two different PAN-OS names
        # can sanitize to the same Terraform name (for example 'a-b' and
        # 'a_b'). The registry maps (scope, context, input) -> assigned name
        # so a reference site that recomputes the same identity gets the same
        # name (F3.1 keyed identity). The flat (scope, input) index keeps
        # contextless reference sites resolving to the first declaration.
        self._name_registry: dict[tuple[str, str, str], str] = {}
        self._flat_registry: dict[tuple[str, str], str] = {}
        self._taken_names: dict[str, set[str]] = {}
        # F3.5: declarations that name a target device, keyed
        # (scope, device, name). An interface belongs to one device, and two
        # devices can declare the same interface name, so a reference from a
        # device-scoped referrer resolves against this index instead of the
        # flat (scope, name) index.
        self._device_registry: dict[tuple[str, str, str], str] = {}
        # F3.6: (scope, name) -> the devices that declared it. A name two
        # devices declare cannot be resolved by a referrer that names no
        # device, so name_ref keeps it a plain string.
        self._device_index: dict[tuple[str, str], set] = {}
        # F3.5: (kind, line) pairs for a source scope the emitted location
        # cannot carry ('scope') and for a vsys location with no target
        # device name ('device'). generate_manual_setup_report writes them.
        self._location_reports: list[tuple[str, str]] = []
        # F3.6: the device membership the export declares
        # (PanoramaParser.parse_associations). A template-scoped entry the
        # export leaves unplaced is reported with the templates its device
        # takes, so the operator sets the real name.
        self._associations: dict = associations or {}

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

    def declare_resource_name(self, name: str, scope: str, context: str = '',
                              vsys: str = '', device: str = '') -> str:
        """Assign a collision-free Terraform name for a new resource declaration.

        The local name is the sanitized PAN-OS name plus a short hash of the
        object's source identity (F2.7, F3.2): the path of the entry in the
        export, made of the resource type (scope), the device group or
        template that defines it (context), the virtual system (vsys), and
        the raw PAN-OS name. The raw name is in the hash, not the sanitized
        one: names that sanitize to the same base ('a-b' and 'a_b') still get
        different digests. The hash makes the name deterministic. The same
        object always gets the same local name. The name does not depend on
        emission order or run count. Same-named objects in different device
        groups, virtual systems, devices, or templates stay distinct.

        If the address is already taken in the scope (a duplicate declaration
        or a digest collision), a numeric suffix follows, so the output is
        always valid HCL.

        F3.1: `context` is the defining device group ('Shared' for shared
        objects) or template. F3.2: `vsys` completes the identity key
        (device group, vsys, type, name) recorded by the parser, so
        same-named objects in different vsys get different digests and both
        survive without the taken-name counter.

        F3.5: `device` (the target device an entry names) is not part of the
        digest. It indexes a declaration so a reference from one device
        cannot resolve to another device's resource of the same name.

        F3.6: a template-scoped object passes its template, else the device
        the export placed it under (TerraformGenerator.scope_context), so
        the same interface name on two firewalls stays two resources instead
        of one resource plus a taken-name counter.
        """
        base = self.sanitize_name(name) or 'unnamed'
        digest = hashlib.sha256(f'{scope}|{context}|{vsys}|{name}'.encode()).hexdigest()[:8]
        candidate = f'{base}_{digest}'
        taken = self._taken_names.setdefault(scope, set())
        n = 2
        while candidate in taken:
            candidate = f'{base}_{digest}_{n}'
            n += 1
        taken.add(candidate)
        # Reference sites resolve by (scope, context, vsys, name); the first
        # declaration of the same identity wins.
        self._name_registry.setdefault((scope, context, vsys, name), candidate)
        # Contextless reference sites resolve by (scope, name); the first
        # declaration wins regardless of context (F2.6 robustness).
        self._flat_registry.setdefault((scope, name), candidate)
        if device:
            self._device_registry.setdefault((scope, device, name), candidate)
            self._device_index.setdefault((scope, name), set()).add(device)
        return candidate

    def name_ref(self, name: str, scopes, key: Optional[str] = None,
                 context: Optional[str] = None, vsys: Optional[str] = None,
                 device: Optional[str] = None):
        """Resolve a PAN-OS name to a Terraform reference (F2.6, F3.1).

        Returns an HclRef of '<scope>.<local>.name' when the object is
        declared in this run, else the plain name. Names that point at
        objects outside the export (built-ins, other tenants) stay plain
        brown-field strings, so this never creates a reference to an
        undeclared resource. `scopes` is tried in order so an object wins
        over a group when both carry the same name. `key` is the registry
        key when it differs from the PAN-OS name (VPN composite keys such
        as 'ike_gw_<name>').

        F3.1: when `context` is given (the referrer's device group),
        resolution tries the referrer's own context first, then the shared
        context, then contextless declarations (template-scoped objects),
        and only then falls back to the flat (scope, name) first-declaration
        index. This makes same-named objects in different device groups
        resolvable to their own resources instead of one name shadowing the
        other.

        F3.2: `vsys` completes the key. PAN-OS resolution is per-vsys: a
        rule sees its own vsys's objects and the shared objects of the same
        vsys, never the other vsys's copies. Each stop of the context chain
        is therefore paired with the referrer's vsys.

        F3.5: `device` is the target device the referrer names. A name that
        a device declared (an interface, which is device-level config) then
        resolves only inside that device, so a zone on one firewall never
        points at another firewall's interface resource. When the referrer
        names no device, such a name resolves only when exactly one device
        declares it (F3.6). A name no device declared (a template-supplied
        interface) still resolves through the normal chain.
        """
        lookup = key if key is not None else name
        vs = vsys or ''
        # A device-declared name (an interface) resolves inside a device or
        # not at all: check this before the context chain, which is
        # device-blind (F3.5).
        declared_by_a_device = any((scope, lookup) in self._device_index
                                   for scope in scopes)
        if declared_by_a_device:
            if device:
                for scope in scopes:
                    local = self._device_registry.get((scope, device, lookup))
                    if local is not None:
                        return HclRef(f'{scope}.{local}.name')
                return name
            # The referrer names no device of its own, so it reached here
            # through a template that targets one device or several (F3.6).
            # One device declaring the name is a fact; two is a guess, so the
            # reference stays a plain name.
            devices: set = set()
            for scope in scopes:
                devices |= self._device_index.get((scope, lookup), set())
            if len(devices) > 1:
                return name
        # Context chain for the referrer: its own context first (a rule in a
        # device group references that group's objects), then the shared
        # objects the group inherits, then contextless declarations (zones,
        # interfaces, virtual routers, VPN objects). Every stop is paired
        # with the referrer's vsys (F3.2).
        chain: list[tuple[str, str]] = []
        for ctx in ([context] if context else []) + ['Shared', '']:
            pair = (ctx, vs)
            if pair not in chain:
                chain.append(pair)
        for scope in scopes:
            for ctx, vs_key in chain:
                local = self._name_registry.get((scope, ctx, vs_key, lookup))
                if local is not None:
                    return HclRef(f'{scope}.{local}.name')
        # Flat fallback for contextless call sites: the first declaration of
        # the (scope, name) pair wins (F2.6 robustness).
        for scope in scopes:
            local = self._flat_registry.get((scope, lookup))
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

    # Provider v2 requires a location block on every resource. A type is
    # template-scoped when its schema location declares no device_group
    # sub-block (F3.5: derived from LOCATION_SCHEMA, not a hand-kept list).
    _TEMPLATE_SCOPED_TYPES = frozenset(
        t for t, scopes in LOCATION_SCHEMA.items() if 'device_group' not in scopes)

    # Template-scoped resource the export places in no template and on no
    # named device (F3.6). The name is a guess, so location_block reports
    # every resource that uses it, with the templates the entry's device
    # does take.
    _TEMPLATE_PLACEHOLDER = 'Shared'

    # PAN-OS writes this device entry name for "this device" (Panorama
    # itself, or a firewall's own config export). It names no firewall, so
    # it cannot go into `ngfw_device` (F3.5).
    _LOCAL_DEVICE_PLACEHOLDER = 'localhost.localdomain'

    def _report_location(self, kind: str, line: str) -> None:
        """Record a location the emitted resource cannot carry (F3.5, F3.6).

        Three kinds: 'scope' (a declared virtual system, template, or device
        group the resource type cannot place the object in), 'device' (a
        vsys location with no usable target device name), and 'placeholder'
        (a template-scoped entry the export leaves unplaced, so the emitted
        template name is a placeholder). All land in
        MANUAL_SETUP_REPORT.txt.
        """
        self._location_reports.append((kind, line))

    @staticmethod
    def _location_source_text(obj: dict) -> str:
        """Describe where the export defined an object, for the report."""
        parts = [f"dg: {obj.get('device_group') or 'Shared'}"]
        if obj.get('vsys'):
            parts.append(f"vsys: {obj['vsys']}")
        if obj.get('template'):
            parts.append(f"template: {obj['template']}")
        if obj.get('vsys_device'):
            parts.append(f"device: {obj['vsys_device']}")
        return ', '.join(parts)

    def _template_device(self, template: str) -> str:
        """Return the one device a template targets, or '' when ambiguous (F3.6).

        Reads the association tables backwards: `templates/entry/<T>/devices`
        says which devices a template targets, and a device can take a
        template through a template stack. A template that targets two
        firewalls names no single device.
        """
        if not template:
            return ''
        devices = {device for device, names
                   in self._associations.get('templates', {}).items()
                   if template in names}
        for device, stacks in self._associations.get('template_stacks', {}).items():
            for stack in stacks:
                if template in self._associations.get('stack_templates', {}).get(stack, []):
                    devices.add(device)
        return sorted(devices)[0] if len(devices) == 1 else ''

    def reference_device(self, obj: dict) -> str:
        """Return the device a reference from `obj` resolves inside (F3.6).

        A device-scoped name (an interface) belongs to one firewall. When the
        referrer names its own device, that device decides. When it names only
        a template, the export still decides when that template targets
        exactly one device; a template that targets two firewalls is
        ambiguous, so the reference stays a plain name instead of guessing.
        """
        device = (obj.get('vsys_device') or '').strip()
        if device:
            return device
        return self._template_device((obj.get('template') or '').strip())

    @staticmethod
    def scope_context(obj: dict) -> str:
        """Return the naming context of a template-scoped object (F3.6).

        The digest context separates same-named objects that live in
        different scopes. A template-scoped object names its template when
        the export declares one; otherwise the export placed the entry under
        devices/entry/<device>, so the device is the scope. Without it, two
        firewalls that both declare ethernet1/1 collapse to one digest and
        the second resource only differs by the taken-name counter.
        """
        return (obj.get('template') or obj.get('vsys_device') or '').strip()

    # --- Report grouping (F3.9) ------------------------------------------
    # Both operator-facing reports group by the same rule: device group first,
    # then the scope the export declares (template, then device), then the
    # object kind inside the section. One implementation, so the two reports
    # cannot disagree.

    def _report_scope_path(self, obj: dict) -> tuple[tuple[int, str, str], ...]:
        """Return the scope path an entry belongs to, outermost first (F3.9).

        Levels, in the order the reports print them: the device group the
        export declares (0), then the template (1), then the device (2). An
        entry the export places nowhere is the shared section (3). Only what
        the export declares is printed: `Shared` in `device_group` is the
        parser fallback for an entry it cannot place, so it is not a device
        group when the entry's scope is a template or a device.

        The level number is part of the tuple so sections sort by level order,
        not by the label text.
        """
        path = []
        device_group = (obj.get('device_group') or '').strip()
        template = (obj.get('template') or '').strip()
        device = (obj.get('vsys_device') or '').strip()
        if device_group and device_group != 'Shared':
            path.append((0, 'DEVICE GROUP', device_group))
        if template:
            path.append((1, 'TEMPLATE', template))
        if device:
            # localhost.localdomain is the PAN-OS placeholder for "this device"
            # (F3.5), so it names no firewall; the report says what it is.
            label = ('DEVICE (this device placeholder)'
                     if device == self._LOCAL_DEVICE_PLACEHOLDER else 'DEVICE')
            path.append((2, label, device))
        if not path:
            path.append((3, 'SHARED SECTION', ''))
        return tuple(path)

    def _group_by_scope(self, entries: list[dict]) -> list[tuple[tuple, list[dict]]]:
        """Group parsed entries by scope path, sections in a stable order (F3.9)."""
        groups: dict[tuple, list[dict]] = {}
        for entry in entries:
            groups.setdefault(self._report_scope_path(entry), []).append(entry)
        return sorted(groups.items())

    @staticmethod
    def _report_section_header(path: tuple[tuple[int, str, str], ...]) -> str:
        """Return the section title for a scope path (F3.9)."""
        return ' / '.join(label if not value else f'{label}: {value}'
                          for _level, label, value in path)

    @staticmethod
    def _report_vsys_line(obj: dict) -> str:
        """Return the vsys line for an entry, or '' when the export declares none (F3.9).

        The parser records '' for an undeclared vsys (F3.5), so the report
        never prints an invented vsys1.
        """
        return f'  Vsys: {obj["vsys"]}\n' if obj.get('vsys') else ''

    def _device_template_text(self, device: str) -> str:
        """Describe the templates the export associates with a device (F3.6).

        Reads the tables PanoramaParser.parse_associations built from
        `templates/entry/*/devices/entry` and
        `template-stack/entry/*/{devices,templates}`. The placeholder report
        uses it, so the operator learns which template name to write.
        """
        if not device:
            return 'the export names no device for this entry'
        if device == self._LOCAL_DEVICE_PLACEHOLDER:
            return ('the entry sits on the PAN-OS "this device" placeholder, '
                    'so the export names no firewall that takes a template')
        names = list(self._associations.get('templates', {}).get(device, []))
        for stack in self._associations.get('template_stacks', {}).get(device, []):
            names.extend(self._associations.get('stack_templates', {}).get(stack, []))
        names = sorted(set(names))
        if names:
            return f'device {device} takes template(s): {", ".join(names)}'
        return f'the export associates no template with device {device}'

    def location_block(self, resource_type: str, obj: dict) -> str:
        """Required location object for a generated resource (F2.3, F3.5).

        Provider v2 requires `location` on every resource, and the sub-blocks
        one type accepts differ from the next, so the choice comes from
        LOCATION_SCHEMA (the verified v2.0.14 shapes) and the source identity
        the parser recorded:

        1. A declared vsys, with no declared template, on a type that accepts
           `vsys` -> `vsys { name, ngfw_device }`, so the object lands in the
           virtual system the export put it in.
        2. A declared template, on a type that accepts `template` ->
           `template { name }`, plus `vsys` when that type's `template`
           declares the field, plus `ngfw_device` when the export nests the
           entry under a device inside the template (F3.6).
        3. Otherwise, a device the export names, on a type that accepts
           `ngfw` -> `ngfw { ngfw_device }`: config the export puts under
           devices/entry/<device> belongs to that firewall, not to a
           template (F3.6).
        4. Otherwise the defining device group, the shared section, or the
           `template { name = "Shared" }` placeholder for a template-scoped
           type with no declared template, reported with the templates the
           entry's device does take (F3.6).

        A declared scope the type cannot carry goes to
        MANUAL_SETUP_REPORT.txt instead of being dropped silently, and no
        sub-block or field is emitted that the schema does not declare:
        `terraform validate` accepts an unknown `location` sub-block and
        drops it, so a wrong sub-block fails at apply, not at validate.
        """
        scopes = LOCATION_SCHEMA[resource_type]
        vsys = (obj.get('vsys') or '').strip()
        template = (obj.get('template') or '').strip()
        device = (obj.get('vsys_device') or '').strip()
        group = (obj.get('device_group') or '').strip()
        where = self._location_source_text(obj)

        def render(scope: str, fields: dict) -> str:
            """Emit one location sub-block with only the fields it declares."""
            kept = [(k, v) for k, v in fields.items() if k in scopes[scope]]
            if not kept:
                # An empty sub-block is the `shared = {}` shape.
                return f'  location = {{\n    {scope} = {{}}\n  }}\n'
            body = ''.join(f'      {k} = {self.escape_string(v)}\n' for k, v in kept)
            return f'  location = {{\n    {scope} = {{\n{body}    }}\n  }}\n'

        # 1. Virtual-system placement (F3.5).
        if vsys and not template and 'vsys' in scopes:
            fields = {'name': vsys}
            if device and device != self._LOCAL_DEVICE_PLACEHOLDER:
                fields['ngfw_device'] = device
            else:
                self._report_location(
                    'device',
                    f'  {resource_type} "{obj.get("name")}" ({where}): '
                    f'location.vsys.ngfw_device is empty because the export '
                    f'names no target device')
            return render('vsys', fields)

        # 2. Template placement. An entry the export nests under
        #    templates/entry/<T>/devices/entry/<D> is that device's own
        #    config inside the template; the schema carries it as
        #    template.ngfw_device (F3.6).
        if template and 'template' in scopes:
            fields = {'name': template}
            if device and device != self._LOCAL_DEVICE_PLACEHOLDER:
                fields['ngfw_device'] = device
            if vsys:
                if 'vsys' in scopes['template']:
                    fields['vsys'] = vsys
                else:
                    self._report_location(
                        'scope',
                        f'  {resource_type} "{obj.get("name")}" ({where}): vsys '
                        f'dropped because {resource_type} location.template '
                        f'declares no vsys field')
            return render('template', fields)

        # 3. Device-specific placement (F3.6). The export put the entry under
        #    devices/entry/<device>/network, so it is that firewall's own
        #    config and not a template's. Provider v2 places it with
        #    location.ngfw ("Located in a specific NGFW device"). Only the
        #    template-scoped types declare it: objects live in a virtual
        #    system and take branch 1.
        if device and device != self._LOCAL_DEVICE_PLACEHOLDER and 'ngfw' in scopes:
            return render('ngfw', {'ngfw_device': device})

        # 4. Report every declared scope the type cannot carry, then fall
        #    back to the location the type does accept.
        if vsys and 'vsys' not in scopes:
            self._report_location(
                'scope',
                f'  {resource_type} "{obj.get("name")}" ({where}): vsys dropped '
                f'because {resource_type} has no location.vsys sub-block; place '
                f'the object in the virtual system by hand')
        if template and 'template' not in scopes:
            self._report_location(
                'scope',
                f'  {resource_type} "{obj.get("name")}" ({where}): template '
                f'dropped because {resource_type} has no location.template '
                f'sub-block; place the object in the template by hand')
        if group and group != 'Shared' and 'device_group' not in scopes:
            self._report_location(
                'scope',
                f'  {resource_type} "{obj.get("name")}" ({where}): device group '
                f'dropped because {resource_type} has no location.device_group '
                f'sub-block; place the object in the device group by hand')

        if 'device_group' in scopes:
            if group and group != 'Shared':
                return render('device_group', {'name': group})
            if 'shared' in scopes:
                # The export defines the entry under <shared>. The schema
                # calls that location `shared`; a device group named
                # "Shared" is a different object that does not exist
                # (F3.5).
                return render('shared', {})
        if 'template' not in scopes:
            # Defensive: every emitted type declares `device_group`,
            # `shared`, or `template`, so no branch above returned. Emit no
            # location (the resource then fails `terraform validate` loudly)
            # and say why, rather than emitting a sub-block the type lacks.
            self._report_location(
                'scope',
                f'  {resource_type} "{obj.get("name")}" ({where}): no location '
                f'emitted because {resource_type} declares no sub-block this '
                f'entry can use; place the object by hand')
            return ''
        # Nothing in the export places this entry and the type only lives in
        # a template. Emit the placeholder and report it with the templates
        # the entry's device does take, so the operator replaces the guess
        # rather than applying it (F3.6).
        self._report_location(
            'placeholder',
            f'  {resource_type} "{obj.get("name")}" ({where}): '
            f'location.template.name is the "{self._TEMPLATE_PLACEHOLDER}" '
            f'placeholder because the export places this entry in no '
            f'template; {self._device_template_text(device)}')
        return render('template', {'name': self._TEMPLATE_PLACEHOLDER})

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
            # Nested lists put each element on its own line at indent + 2.
            parts = [f'{indent}  {self.hcl_value(item, indent + "  ")}' for item in value]
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
  # Credentials come from variables.tf. Set the values in
  # terraform.tfvars (do not commit it) or via the TF_VAR_*
  # environment variables.
  hostname = var.panos_hostname
  username = var.panos_username
  password = var.panos_password
}
'''

        with open(self.output_dir / 'provider.tf', 'w') as f:
            f.write(content)

    def generate_variables(self):
        """Generate variables.tf file"""
        # F2.10: every emitted variable is consumed. The three credential
        # variables are consumed by the provider block in provider.tf.
        # The old dead `device_group` variable is gone: v2 location is
        # derived per resource from the source XML.
        content = '''# Variables for Palo Alto Configuration
# Set the values in terraform.tfvars (do not commit it) or via the
# TF_VAR_panos_hostname / TF_VAR_panos_username / TF_VAR_panos_password
# environment variables.
variable "panos_hostname" {
  description = "Hostname or IP of the Palo Alto firewall or Panorama"
  type        = string
}

variable "panos_username" {
  description = "Username for authentication"
  type        = string
}

variable "panos_password" {
  description = "Password for authentication"
  type        = string
  sensitive   = true
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
            if addr.get('report_only'):
                # No v2 attribute exists for this entry type; the entry is
                # reported instead of emitted as an empty resource (F3.4).
                continue

            resource_name = self.declare_resource_name(
                addr['name'], 'panos_address',
                context=addr.get('device_group') or '', vsys=addr.get('vsys') or ''
            )

            content += f'resource "panos_address" "{resource_name}" {{\n'
            content += self.location_block('panos_address', addr)
            content += f'  name = {self.escape_string(addr["name"])}\n'

            if addr.get('description'):
                content += f'  description = {self.escape_string(addr["description"])}\n'

            disable = (addr.get('disable_override') or '').strip().lower()
            if disable in ('yes', 'no'):
                # v2 takes the "yes"/"no" string, not a bool (verified 2.0.14)
                content += f'  disable_override = "{disable}"\n'

            value = (addr.get('value') or '').strip()
            if value:
                attr = self._address_type_attribute(addr.get('type', 'ip-netmask'))
                content += f'  {attr} = {self.escape_string(value)}\n'

            if addr.get('tags'):
                # F2.6: tags declared in this run become references;
                # F3.2: resolve in the referrer's (device group, vsys) key
                ctx = addr.get('device_group')
                vs = addr.get('vsys') or ''
                tags_str = ', '.join([
                    self.hcl_value(self.name_ref(t, TAG_SCOPES, context=ctx, vsys=vs), '')
                    for t in addr['tags']
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
                grp['name'], 'panos_address_group',
                context=grp.get('device_group') or '', vsys=grp.get('vsys') or ''
            )

            content += f'resource "panos_address_group" "{resource_name}" {{\n'
            content += self.location_block('panos_address_group', grp)
            content += f'  name = {self.escape_string(grp["name"])}\n'

            if grp.get('description'):
                content += f'  description = {self.escape_string(grp["description"])}\n'

            if static_members:
                # F2.6: members declared in this run become references;
                # F3.2: resolve in the referrer's (device group, vsys) key
                ctx = grp.get('device_group')
                vs = grp.get('vsys') or ''
                members_str = ', '.join([
                    self.hcl_value(self.name_ref(m, ADDR_SCOPES, context=ctx, vsys=vs), '')
                    for m in static_members
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

        The v2 schema nests the port inside a protocol object, but accepts
        only ONE protocol leg per resource: a config that sets both tcp and
        udp fails `terraform validate` with "Invalid Attribute Combination"
        (verified against 2.0.14). A dual-protocol Panorama object therefore
        emits its tcp leg (udp when tcp is absent) and the dropped leg is
        reported in MANUAL_SETUP_REPORT.txt instead of being lost (F3.4).

        A multi-port value stays one string, which is the destination_port
        shape the provider takes.
        """
        if not services:
            return

        content = '# Service Objects\n\n'

        for svc in services:
            resource_name = self.declare_resource_name(
                svc['name'], 'panos_service',
                context=svc.get('device_group') or '', vsys=svc.get('vsys') or ''
            )

            content += f'resource "panos_service" "{resource_name}" {{\n'
            content += self.location_block('panos_service', svc)
            content += f'  name = {self.escape_string(svc["name"])}\n'

            if svc.get('description'):
                content += f'  description = {self.escape_string(svc["description"])}\n'

            # v2 protocol is a nested object: protocol = { tcp = { ... } }
            protocols = svc.get('protocols') or {}
            emitted = self.primary_service_protocol(protocols)
            if emitted:
                content += f'  protocol = {self.hcl_value({emitted: protocols[emitted]})}\n'

            for proto in self.dropped_service_protocols(protocols):
                summary = self.protocol_summary(protocols[proto])
                content += f'  # NOTE: {proto} leg not emitted, v2 takes one protocol only: '
                content += f'{summary}\n'

            other = svc.get('other_protocol') or {}
            if other:
                # v2 models only tcp and udp; keep the rest visible for review
                names = ', '.join(sorted(other))
                content += f'  # NOTE: protocol {names} is not modeled by the v2 schema; review manually\n'

            if svc.get('tags'):
                # F2.6: tags declared in this run become references;
                # F3.2: resolve in the referrer's (device group, vsys) key
                ctx = svc.get('device_group')
                vs = svc.get('vsys') or ''
                tags_str = ', '.join([
                    self.hcl_value(self.name_ref(t, TAG_SCOPES, context=ctx, vsys=vs), '')
                    for t in svc['tags']
                ])
                content += f'  tags = [{tags_str}]\n'

            content += '}\n\n'

        with open(self.output_dir / 'service_objects.tf', 'w') as f:
            f.write(content)

    # v2.0.14 panos_service accepts exactly one protocol leg (verified with
    # terraform validate). tcp is emitted first so the choice is stable.
    SERVICE_PROTOCOL_ORDER = ('tcp', 'udp')

    @classmethod
    def primary_service_protocol(cls, protocols: dict) -> Optional[str]:
        """The one protocol leg a service can emit: tcp wins, then udp."""
        for proto in cls.SERVICE_PROTOCOL_ORDER:
            if proto in protocols:
                return proto
        # An unmodeled leg (kept in other_protocol) never reaches here.
        return sorted(protocols)[0] if protocols else None

    @classmethod
    def dropped_service_protocols(cls, protocols: dict) -> list[str]:
        """Protocol legs the v2 schema forces the converter to leave out."""
        primary = cls.primary_service_protocol(protocols)
        return [p for p in sorted(protocols) if p != primary]

    @staticmethod
    def protocol_summary(block: dict) -> str:
        """One-line description of a protocol leg for reports and comments."""
        parts = [f'{key}={block[key]}' for key in ('destination_port', 'source_port')
                 if block.get(key)]
        parts += [f'{key}={value}' for key, value in sorted((block.get('override') or {}).items())]
        return ', '.join(parts) or 'no ports captured'

    def generate_service_groups(self, groups: list[dict]):
        """Generate service group Terraform configuration (v2: panos_service_group)

        Note: the v2 panos_service_group schema has no description attribute.
        """
        if not groups:
            return

        content = '# Service Groups\n\n'

        for grp in groups:
            resource_name = self.declare_resource_name(
                grp['name'], 'panos_service_group',
                context=grp.get('device_group') or '', vsys=grp.get('vsys') or ''
            )

            content += f'resource "panos_service_group" "{resource_name}" {{\n'
            content += self.location_block('panos_service_group', grp)
            content += f'  name = {self.escape_string(grp["name"])}\n'

            if grp.get('members'):
                # F2.6: members declared in this run become references;
                # F3.2: resolve in the referrer's (device group, vsys) key
                ctx = grp.get('device_group')
                vs = grp.get('vsys') or ''
                members_str = ', '.join([
                    self.hcl_value(self.name_ref(m, SERVICE_SCOPES, context=ctx, vsys=vs), '')
                    for m in grp['members']
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
                tag['name'], 'panos_administrative_tag',
                context=tag.get('device_group') or '', vsys=tag.get('vsys') or ''
            )

            content += f'resource "panos_administrative_tag" "{resource_name}" {{\n'
            content += self.location_block('panos_administrative_tag', tag)
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
                cat['name'], 'panos_custom_url_category',
                context=cat.get('device_group') or '', vsys=cat.get('vsys') or ''
            )

            content += f'resource "panos_custom_url_category" "{resource_name}" {{\n'
            content += self.location_block('panos_custom_url_category', cat)
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
                ag['name'], 'panos_application_group',
                context=ag.get('device_group') or '', vsys=ag.get('vsys') or ''
            )

            content += f'resource "panos_application_group" "{resource_name}" {{\n'
            content += self.location_block('panos_application_group', ag)
            content += f'  name = {self.escape_string(ag["name"])}\n'

            if ag.get('members'):
                members_str = ', '.join([self.escape_string(m) for m in ag['members']])
                content += f'  members = [{members_str}]\n'

            content += '}\n\n'

        with open(self.output_dir / 'application_groups.tf', 'w') as f:
            f.write(content)

    # NOTE: application filters have no v2 resource (see resource_mapping.py).
    # Their parsed data goes to MANUAL_SETUP_REPORT.txt instead.

    # Fields the v2.0.14 panos_external_dynamic_list models inside each type
    # sub-shape, verified against the live schema. The predefined_* sub-shapes
    # mirror vendor-supplied lists and model fewer fields; expand_domain is a
    # domain-only field. auth is never listed: it carries credentials, and the
    # converter does not write secrets into generated HCL.
    EDL_EXTENDED_FIELDS = ('url', 'description', 'exception_list',
                           'certificate_profile', 'recurring')
    EDL_SUBSHAPE_FIELDS = {
        'domain': ('url', 'description', 'exception_list', 'expand_domain',
                   'certificate_profile', 'recurring'),
        'imei': EDL_EXTENDED_FIELDS,
        'imsi': EDL_EXTENDED_FIELDS,
        'ip': EDL_EXTENDED_FIELDS,
        'url': EDL_EXTENDED_FIELDS,
        'predefined_ip': ('url', 'description', 'exception_list'),
        'predefined_url': ('url', 'description', 'exception_list'),
    }

    def generate_external_lists(self, ext_lists: list[dict]):
        """Generate external dynamic list Terraform configuration

        v2: panos_external_dynamic_list. The v2 schema nests the fetch details
        inside a type object keyed by the list type (ip, domain, url, ...).
        Only the fields the chosen sub-shape models are emitted; anything else
        is left as a NOTE comment for manual review (F3.4).
        """
        if not ext_lists:
            return

        content = '# External Dynamic Lists\n\n'

        # List types the v2 schema models inside the type block
        v2_types = ('domain', 'imei', 'imsi', 'ip', 'predefined_ip', 'predefined_url', 'url')

        for ext_list in ext_lists:
            resource_name = self.declare_resource_name(
                ext_list['name'], 'panos_external_dynamic_list',
                context=ext_list.get('device_group') or '', vsys=ext_list.get('vsys') or ''
            )

            content += f'resource "panos_external_dynamic_list" "{resource_name}" {{\n'
            content += self.location_block('panos_external_dynamic_list', ext_list)
            content += f'  name = {self.escape_string(ext_list["name"])}\n'

            # v2 type is a nested object keyed by list type
            lt = ext_list.get('type') or 'ip'
            fields = ext_list.get('fields') or {}
            if lt in v2_types:
                allowed = self.EDL_SUBSHAPE_FIELDS[lt]
                emit = {k: v for k, v in fields.items() if k in allowed}
                content += f'  type = {self.hcl_value({lt: emit})}\n'
                for key in (k for k in fields if k not in allowed):
                    content += f'  # NOTE: {key} is not modeled by the v2 {lt} '
                    content += 'sub-shape; review manually\n'
            else:
                # Unknown list type: keep the data visible for manual review
                content += f'  # NOTE: list type {lt} is not modeled by the v2 schema; review manually\n'
                if fields.get('url'):
                    content += f'  # url = {fields["url"]}\n'

            content += '}\n\n'

        with open(self.output_dir / 'external_lists.tf', 'w') as f:
            f.write(content)

    def _policy_rule_chains(self, rules: list[dict]) -> list[list[dict]]:
        """Group policy rules into per-(device group, vsys) chains (F2.5, F3.2).

        The provider places each rule relative to a pivot rule, so rules
        must emit as independent chains per (device group, vsys): a pivot
        only exists inside its own rulebase, so one vsys's rules must
        never chain on another vsys's rule. XML document order is
        preserved within a chain; chains appear in first-seen order.
        """
        chains: dict[tuple[str, str], list[dict]] = {}
        for rule in rules:
            key = (rule.get('device_group') or 'Shared', rule.get('vsys') or 'vsys1')
            chains.setdefault(key, []).append(rule)
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
                    rule['name'], 'panos_security_policy_rules',
                    context=rule.get('device_group') or '', vsys=rule.get('vsys') or ''
                )

                content += f'resource "panos_security_policy_rules" "{resource_name}" {{\n'
                content += self.location_block('panos_security_policy_rules', rule)
                content += self._policy_position_block(
                    'panos_security_policy_rules', prev_rule_name, prev_resource_name
                )

                # v2 rules is a list of objects
                rule_obj: dict = {'name': rule['name']}
                if rule.get('description'):
                    rule_obj['description'] = rule['description']
                # F2.6: zones, addresses and services declared in this run
                # become references; the rest stay brown-field strings
                # F3.2: resolve in the referrer's (device group, vsys) key
                ctx = rule.get('device_group')
                vs = rule.get('vsys') or ''
                if rule.get('source_zones'):
                    rule_obj['source_zones'] = [
                        self.name_ref(z, ZONE_SCOPES, context=ctx, vsys=vs) for z in rule['source_zones']]
                if rule.get('source_addresses'):
                    rule_obj['source_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES, context=ctx, vsys=vs) for a in rule['source_addresses']]
                if rule.get('destination_zones'):
                    rule_obj['destination_zones'] = [
                        self.name_ref(z, ZONE_SCOPES, context=ctx, vsys=vs) for z in rule['destination_zones']]
                if rule.get('destination_addresses'):
                    rule_obj['destination_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES, context=ctx, vsys=vs) for a in rule['destination_addresses']]
                if rule.get('applications'):
                    # Built-in PAN-OS app names: no managed scope, never wired
                    rule_obj['applications'] = list(rule['applications'])
                if rule.get('services'):
                    rule_obj['services'] = [
                        self.name_ref(s, SERVICE_SCOPES, context=ctx, vsys=vs) for s in rule['services']]
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
                    rule['name'], 'panos_nat_policy_rules',
                    context=rule.get('device_group') or '', vsys=rule.get('vsys') or ''
                )

                content += f'resource "panos_nat_policy_rules" "{resource_name}" {{\n'
                content += self.location_block('panos_nat_policy_rules', rule)
                content += self._policy_position_block(
                    'panos_nat_policy_rules', prev_rule_name, prev_resource_name
                )

                # v2 rules is a list of objects
                rule_obj: dict = {'name': rule['name']}
                if rule.get('description'):
                    rule_obj['description'] = rule['description']
                # F2.6: zones, addresses and services declared in this run
                # become references; the rest stay brown-field strings
                # F3.2: resolve in the referrer's (device group, vsys) key
                ctx = rule.get('device_group')
                vs = rule.get('vsys') or ''
                if rule.get('source_zones'):
                    rule_obj['source_zones'] = [
                        self.name_ref(z, ZONE_SCOPES, context=ctx, vsys=vs) for z in rule['source_zones']]
                # v2 destination_zone is a list
                if rule.get('destination_zone'):
                    rule_obj['destination_zone'] = [
                        self.name_ref(rule['destination_zone'], ZONE_SCOPES, context=ctx, vsys=vs)]
                if rule.get('source_addresses'):
                    rule_obj['source_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES, context=ctx, vsys=vs) for a in rule['source_addresses']]
                if rule.get('destination_addresses'):
                    rule_obj['destination_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES, context=ctx, vsys=vs) for a in rule['destination_addresses']]
                if rule.get('service'):
                    rule_obj['service'] = self.name_ref(
                        rule['service'], SERVICE_SCOPES, context=ctx, vsys=vs)
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
                        # (F2.6: reference when declared in this run;
                        # F3.2: resolve in the rule's vsys key)
                        rule_obj['source_translation'] = {
                            st_type: {'interface_address': {
                                'interface': self.name_ref(
                                    st_addr[0], INTERFACE_SCOPES,
                                    context=ctx, vsys=vs)}}}
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
                    rule['name'], 'panos_decryption_policy_rules',
                    context=device_group, vsys=rule.get('vsys') or ''
                )

                content += f'resource "panos_decryption_policy_rules" "{resource_name}" {{\n'
                content += self.location_block('panos_decryption_policy_rules', rule)
                content += self._policy_position_block(
                    'panos_decryption_policy_rules', prev_rule_name, prev_resource_name
                )

                rule_obj: dict = {'name': rule['name']}
                if rule.get('description'):
                    rule_obj['description'] = rule['description']
                # F2.6: zones, addresses and services declared in this run
                # become references; the rest stay brown-field strings
                # F3.2: resolve in the referrer's (device group, vsys) key
                ctx = rule.get('device_group')
                vs = rule.get('vsys') or ''
                if rule.get('source_zones'):
                    rule_obj['source_zones'] = [
                        self.name_ref(z, ZONE_SCOPES, context=ctx, vsys=vs) for z in rule['source_zones']]
                if rule.get('destination_zones'):
                    rule_obj['destination_zones'] = [
                        self.name_ref(z, ZONE_SCOPES, context=ctx, vsys=vs) for z in rule['destination_zones']]
                if rule.get('source_addresses'):
                    rule_obj['source_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES, context=ctx, vsys=vs) for a in rule['source_addresses']]
                if rule.get('destination_addresses'):
                    rule_obj['destination_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES, context=ctx, vsys=vs) for a in rule['destination_addresses']]
                if rule.get('source_users'):
                    rule_obj['source_user'] = list(rule['source_users'])
                if rule.get('categories'):
                    rule_obj['category'] = list(rule['categories'])
                if rule.get('services'):
                    rule_obj['services'] = [
                        self.name_ref(s, SERVICE_SCOPES, context=ctx, vsys=vs) for s in rule['services']]
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
                    rule['name'], 'panos_pbf_policy_rules',
                    context=device_group, vsys=rule.get('vsys') or ''
                )

                content += f'resource "panos_pbf_policy_rules" "{resource_name}" {{\n'
                content += self.location_block('panos_pbf_policy_rules', rule)
                content += self._policy_position_block(
                    'panos_pbf_policy_rules', prev_rule_name, prev_resource_name
                )

                rule_obj: dict = {'name': rule['name']}
                if rule.get('description'):
                    rule_obj['description'] = rule['description']
                # v2 models the PBF source as from { zone = [...] }
                # F3.2: resolve in the referrer's (device group, vsys) key
                ctx = rule.get('device_group')
                vs = rule.get('vsys') or ''
                if rule.get('source_zones'):
                    rule_obj['from'] = {
                        'zone': [
                            self.name_ref(z, ZONE_SCOPES, context=ctx, vsys=vs)
                            for z in rule['source_zones']]}
                if rule.get('source_addresses'):
                    rule_obj['source_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES, context=ctx, vsys=vs) for a in rule['source_addresses']]
                if rule.get('source_users'):
                    rule_obj['source_users'] = list(rule['source_users'])
                if rule.get('destination_addresses'):
                    rule_obj['destination_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES, context=ctx, vsys=vs) for a in rule['destination_addresses']]
                if rule.get('applications'):
                    rule_obj['applications'] = list(rule['applications'])
                if rule.get('services'):
                    rule_obj['services'] = [
                        self.name_ref(s, SERVICE_SCOPES, context=ctx, vsys=vs) for s in rule['services']]
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
            # F3.6: a monitor profile lives in a template or in one device's
            # own config, so the naming context is the declared template, else
            # the declared device (scope_context).
            resource_name = self.declare_resource_name(
                prof['name'], 'panos_monitor_profile',
                context=self.scope_context(prof), vsys=prof.get('vsys') or ''
            )
            content += f'resource "panos_monitor_profile" "{resource_name}" {{\n'
            content += self.location_block('panos_monitor_profile', prof)
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
            resource_name = self.declare_resource_name(
                zone['name'], 'panos_zone',
                context=self.scope_context(zone), vsys=zone.get('vsys') or ''
            )

            content += f'resource "panos_zone" "{resource_name}" {{\n'
            content += self.location_block('panos_zone', zone)
            content += f'  name = {self.escape_string(zone["name"])}\n'

            # v2 network object: membership list is keyed by layer type
            ztype = zone.get('type') or 'layer3'
            key = 'layer2' if ztype == 'layer2' else 'layer3'
            network: dict = {}
            if zone.get('interfaces'):
                # F2.6: interfaces declared in this run become references;
                # F3.2: resolve in the zone's vsys key
                network[key] = [
                    self.name_ref(i, INTERFACE_SCOPES, vsys=zone.get('vsys') or '',
                                  device=self.reference_device(zone))
                    for i in zone['interfaces']]
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
                router['name'], 'panos_virtual_router',
                context=self.scope_context(router), vsys=router.get('vsys') or ''
            )

            # Add comment showing source and type. A router the export does
            # not place in a template is device-specific (F3.5 records the
            # template as '' there).
            template = router.get('template') or 'device-specific'
            content += f'# Source: {template}\n'
            router_type = router.get('router_type', 'virtual')
            if router_type == 'logical':
                rtype = 'Logical Router (Advanced Routing Engine)'
            else:
                rtype = 'Virtual Router (Legacy)'
            content += f'# Type: {rtype}\n'

            content += f'resource "panos_virtual_router" "{resource_name}" {{\n'
            content += self.location_block('panos_virtual_router', router)
            content += f'  name = {self.escape_string(router["name"])}\n'

            # v2 interfaces is a flat string list
            if router.get('interfaces'):
                # F2.6: interfaces declared in this run become references;
                # F3.2: resolve in the router's vsys key
                ifaces_str = ', '.join([
                    self.hcl_value(self.name_ref(
                        i, INTERFACE_SCOPES, vsys=router.get('vsys') or '',
                        device=self.reference_device(router)), '')
                    for i in router['interfaces']
                ])
                content += f'  interfaces = [{ifaces_str}]\n'

            content += '}\n\n'

            # Generate static routes (v2: panos_virtual_router_static_route_ipv4)
            if router.get('static_routes'):
                for route in router['static_routes']:
                    route_key = f"{resource_name}_{route['name']}"
                    route_resource = self.declare_resource_name(
                        route_key, 'panos_virtual_router_static_route_ipv4',
                        context=self.scope_context(router), vsys=router.get('vsys') or ''
                    )

                    content += f'resource "panos_virtual_router_static_route_ipv4" "{route_resource}" {{\n'
                    # The route carries the owning router's source
                    # identity; only the report name is the route's own
                    content += self.location_block(
                        'panos_virtual_router_static_route_ipv4',
                        {**router, 'name': route['name']})
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

    def generate_interfaces(self, interfaces: list[dict]):
        """Generate interface Terraform configuration (v2, one resource per kind).

        The v2 panos_ethernet_interface has no ipv4 attribute: IPv4
        addresses on a physical L3 interface are modeled on its .0 layer-3
        subinterface via panos_ethernet_layer3_subinterface.
        """
        if not interfaces:
            return

        content = '# Interface Configurations\n'
        content += '# Note: These are reference configurations. Adjust for your hardware platform.\n\n'

        for iface in interfaces:
            kind = iface['type']
            if kind == 'ethernet':
                content += self._emit_ethernet_interface(iface)
                continue
            scope = INTERFACE_RESOURCE_TYPES.get(kind)
            if scope:
                content += self._emit_interface_resource(iface, scope)

        with open(self.output_dir / 'interfaces.tf', 'w') as f:
            f.write(content)

    def _emit_ethernet_interface(self, iface: dict) -> str:
        """Emit one ethernet entry: the physical interface, or a tagged subinterface."""
        name = iface['name']
        mode = iface.get('mode')
        context = self.scope_context(iface)
        vsys = iface.get('vsys') or ''
        device = iface.get('vsys_device') or ''
        scope_sub = 'panos_ethernet_layer3_subinterface'
        parent, dot, tag_str = name.partition('.')

        # Tagged L3 subinterface (ethernet1/2.10): v2 subinterface resource
        if dot and mode == 'layer3':
            scope = scope_sub
            resource_name = self.declare_resource_name(
                name, scope, context=context, vsys=vsys, device=device)
            out = f'resource "{scope}" "{resource_name}" {{\n'
            out += self.location_block(scope, iface)
            out += f'  name = {self.escape_string(name)}\n'
            # F2.6: the parent is an interface declared in this run
            # (or a brown-field interface outside the export);
            # F3.2: resolve in the subinterface's vsys key
            parent_ref = self.name_ref(parent, IFACE_SCOPES, context=context,
                                       vsys=vsys, device=device)
            out += f"  parent = {self.hcl_value(parent_ref, '')}\n"
            if tag_str.isdigit():
                out += f'  tag = {int(tag_str)}\n'
            if iface.get('management_profile'):
                out += f'  interface_management_profile = {self.escape_string(iface["management_profile"])}\n'
            out += self._ip_list_line(iface)
            out += '}\n\n'
            return out

        # Physical interface
        scope = 'panos_ethernet_interface'
        resource_name = self.declare_resource_name(
            name, scope, context=context, vsys=vsys, device=device)
        out = f'resource "{scope}" "{resource_name}" {{\n'
        out += self.location_block(scope, iface)
        out += f'  name = {self.escape_string(name)}\n'

        if iface.get('comment'):
            out += f'  comment = {self.escape_string(iface["comment"])}\n'

        # The v2 mode object signals the interface mode. F3.3: virtual-wire
        # and tap are nested blocks on panos_ethernet_interface; the provider
        # has no separate resource type for them.
        if mode == 'layer3':
            l3: dict = {}
            if iface.get('management_profile'):
                l3['interface_management_profile'] = iface['management_profile']
            out += f'  layer3 = {self.hcl_value(l3)}\n'
        elif mode == 'layer2':
            out += '  layer2 = {}\n'
        elif mode in ('virtual-wire', 'tap'):
            out += f'  {mode.replace("-", "_")} = {{}}\n'
        elif mode:
            # ha, aggregate-group: note for manual review
            out += f'  # NOTE: mode {mode} requires manual review (v2 block shape not modeled)\n'

        if iface.get('ipv6_addresses'):
            v6_str = ', '.join(iface['ipv6_addresses'])
            out += f'  # NOTE: IPv6 addresses ({v6_str}) require manual configuration on the .0 subinterface\n'

        out += '}\n\n'

        # v2 has no ipv4 attribute on the interface: IPv4 lives on the .0 subinterface
        if mode == 'layer3' and iface.get('ip_addresses'):
            sub_name = f'{name}.0'
            sub_resource = self.declare_resource_name(
                sub_name, scope_sub, context=context, vsys=vsys, device=device)
            out += f'resource "{scope_sub}" "{sub_resource}" {{\n'
            # The subinterface is its own object, so reports name it by its
            # own name (the location itself comes from the same source entry).
            out += self.location_block(scope_sub, {**iface, 'name': sub_name})
            out += f'  name = {self.escape_string(sub_name)}\n'
            # F2.6: the parent is the physical interface declared above;
            # F3.2: resolve in the subinterface's vsys key
            parent_ref = self.name_ref(name, IFACE_SCOPES, context=context,
                                       vsys=vsys, device=device)
            out += f"  parent = {self.hcl_value(parent_ref, '')}\n"
            out += '  tag = 0\n'
            out += self._ip_list_line(iface)
            out += '}\n\n'

        return out

    def _emit_interface_resource(self, iface: dict, scope: str) -> str:
        """Emit one interface resource for a non-ethernet kind (v2 nested shapes)."""
        name = iface['name']
        context = self.scope_context(iface)
        vsys = iface.get('vsys') or ''
        device = iface.get('vsys_device') or ''
        # An aggregate entry whose name already carries a unit (ae1.101) is a
        # layer-3 subinterface of the aggregate group; the group entry itself
        # has no ip, parent, or tag in the schema.
        if iface['type'] == 'aggregate' and '.' in name:
            scope = 'panos_aggregate_layer3_subinterface'
        resource_name = self.declare_resource_name(
            name, scope, context=context, vsys=vsys, device=device)
        out = f'resource "{scope}" "{resource_name}" {{\n'
        out += self.location_block(scope, iface)
        out += f'  name = {self.escape_string(name)}\n'
        if iface.get('comment'):
            out += f'  comment = {self.escape_string(iface["comment"])}\n'
        if scope == 'panos_aggregate_interface':
            mode = iface.get('mode')
            if mode:
                out += f'  {mode} = {{}}\n'
            out += '}\n\n'
            return out
        parent = iface.get('parent')
        if parent:
            parent_ref = self.name_ref(parent, IFACE_SCOPES, context=context,
                                       vsys=vsys, device=device)
            out += f"  parent = {self.hcl_value(parent_ref, '')}\n"
        # Only the layer-3 subinterface types carry a tag in the schema.
        tag = iface.get('tag')
        if tag and str(tag).isdigit() and scope.endswith('subinterface'):
            out += f'  tag = {int(tag)}\n'
        out += self._ip_list_line(iface)
        # The schema shape for these kinds: ip is a list of objects, ipv6 is
        # a single nested block with an address list.
        if iface.get('ipv6_addresses'):
            out += f'  ipv6 = {{ address = {self.hcl_value(iface["ipv6_addresses"])} }}\n'
        if iface.get('management_profile'):
            out += f'  interface_management_profile = {self.escape_string(iface["management_profile"])}\n'
        out += '}\n\n'
        return out

    def _ip_list_line(self, iface: dict) -> str:
        """The ip attribute line for an interface resource (v2: list of objects)."""
        ips = iface.get('ip_addresses') or []
        if not ips:
            return ''
        return f'  ip = {self.hcl_value([{"name": ip} for ip in ips])}\n'

    def generate_interface_report(self, interfaces: list[dict]):
        """Generate a text report of interfaces and their IP addresses.

        F3.9: one section per scope the export declares, so a reader can tell
        two same-named interfaces on two device groups apart. The migration
        checklist and the platform notes are one shared footer, not repeated
        per section.
        """
        if not interfaces:
            return

        content = '=' * 80 + '\n'
        content += 'INTERFACE AND IP ADDRESS MIGRATION REPORT\n'
        content += 'Generated for Firewall Migration Planning\n'
        content += '=' * 80 + '\n\n'

        content += 'This report lists all interfaces and their assigned IP addresses from the\n'
        content += 'source configuration. Use this to plan interface mapping for the new platform.\n\n'

        content += 'Interfaces are grouped by the scope the export declares: device group first,\n'
        content += 'then the template or the device the entry sits in, then the interface type.\n'
        content += 'A section names only the scope the export states, so the same interface name\n'
        content += 'on two device groups appears once under each.\n'

        for path, iface_list in self._group_by_scope(interfaces):
            content += '\n' + '=' * 80 + '\n'
            content += self._report_section_header(path) + '\n'
            content += '=' * 80 + '\n'

            # Kind grouping inside a section, as before F3.9.
            by_type: dict[str, list[dict]] = {}
            for iface in iface_list:
                by_type.setdefault(iface['type'], []).append(iface)

            for iface_type, type_list in sorted(by_type.items()):
                content += f'\n{iface_type.upper()} INTERFACES ({len(type_list)})\n'
                content += '-' * 80 + '\n'

                for iface in sorted(type_list, key=lambda x: x['name']):
                    content += f'\nInterface: {iface["name"]}\n'
                    content += f'  Type: {iface["type"]}\n'
                    content += f'  Mode: {iface["mode"]}\n'
                    content += self._report_vsys_line(iface)

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
                    prof['name'], 'panos_antivirus_security_profile',
                    # F3.1: contextless. This stub emits no location, so
                    # the device group and template stay out of its name;
                    # F3.2: vsys is part of the identity key
                    context='', vsys=prof.get('vsys') or '')
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_antivirus_security_profile.{resource_name}\n\n'

        # Vulnerability profiles
        if profiles.get('vulnerability'):
            content += '# Vulnerability Protection Profiles\n'
            for prof in profiles['vulnerability']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_vulnerability_security_profile',
                    # F3.1: contextless. This stub emits no location, so
                    # the device group and template stay out of its name;
                    # F3.2: vsys is part of the identity key
                    context='', vsys=prof.get('vsys') or '')
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_vulnerability_security_profile.{resource_name}\n\n'

        # Anti-spyware profiles
        if profiles.get('anti_spyware'):
            content += '# Anti-Spyware Profiles\n'
            for prof in profiles['anti_spyware']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_anti_spyware_security_profile',
                    # F3.1: contextless. This stub emits no location, so
                    # the device group and template stay out of its name;
                    # F3.2: vsys is part of the identity key
                    context='', vsys=prof.get('vsys') or '')
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_anti_spyware_security_profile.{resource_name}\n\n'

        # URL filtering profiles
        if profiles.get('url_filtering'):
            content += '# URL Filtering Profiles\n'
            for prof in profiles['url_filtering']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_url_filtering_security_profile',
                    # F3.1: contextless. This stub emits no location, so
                    # the device group and template stay out of its name;
                    # F3.2: vsys is part of the identity key
                    context='', vsys=prof.get('vsys') or '')
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_url_filtering_security_profile.{resource_name}\n\n'

        # File blocking profiles
        if profiles.get('file_blocking'):
            content += '# File Blocking Profiles\n'
            for prof in profiles['file_blocking']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_file_blocking_security_profile',
                    # F3.1: contextless. This stub emits no location, so
                    # the device group and template stay out of its name;
                    # F3.2: vsys is part of the identity key
                    context='', vsys=prof.get('vsys') or '')
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_file_blocking_security_profile.{resource_name}\n\n'

        # WildFire profiles
        if profiles.get('wildfire_analysis'):
            content += '# WildFire Analysis Profiles\n'
            for prof in profiles['wildfire_analysis']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_wildfire_analysis_security_profile',
                    # F3.1: contextless. This stub emits no location, so
                    # the device group and template stay out of its name;
                    # F3.2: vsys is part of the identity key
                    context='', vsys=prof.get('vsys') or '')
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
                grp['name'], 'panos_security_profile_group',
                context=grp.get('device_group') or '', vsys=grp.get('vsys') or ''
            )

            content += f'resource "panos_security_profile_group" "{resource_name}" {{\n'
            content += self.location_block('panos_security_profile_group', grp)
            content += f'  name = {self.escape_string(grp["name"])}\n'

            for category in categories:
                members = grp.get(category)
                if members:
                    members_str = ', '.join([self.escape_string(m) for m in members])
                    content += f'  {category} = [{members_str}]\n'

            content += '}\n\n'

        with open(self.output_dir / 'security_profile_groups.tf', 'w') as f:
            f.write(content)


    def generate_manual_setup_report(self, bgp_routers: list[dict],
                                     ospf_routers: list[dict],
                                     application_filters: list[dict],
                                     manual_key_tunnels: list[dict],
                                     application_override_rules: Optional[list[dict]] = None,
                                     qos_profiles: Optional[list[dict]] = None,
                                     tunnel_monitor_profiles: Optional[list[dict]] = None,
                                     schedules: Optional[list[dict]] = None,
                                     log_settings: Optional[list[dict]] = None,
                                     zone_protection_profiles: Optional[list[dict]] = None,
                                     report_only_addresses: Optional[list[dict]] = None,
                                     dual_protocol_services: Optional[list[dict]] = None,
                                     entry_coverage: str = ''):
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
        if not (bgp_routers or ospf_routers or application_filters or manual_key_tunnels
                or application_override_rules or qos_profiles
                or tunnel_monitor_profiles or schedules or log_settings
                or zone_protection_profiles or report_only_addresses
                or dual_protocol_services or entry_coverage or self._location_reports):
            return

        lines = ['MANUAL SETUP REPORT', '=' * 60, '']
        lines.append('The items below have no panos provider v2 resource, or the')
        lines.append('converter intentionally does not emit them (the reason is stated')
        lines.append('per section). Configure them manually (GUI or CLI) and verify')
        lines.append('against this report.')
        lines.append('')

        # BGP and OSPF name the scope (F3.9), because a router is an object the export
        # places: the parse returns one record per router with the four scope facts, so
        # the shared grouping rule applies to it like it applies to any other object.
        if bgp_routers:
            lines.append('--- BGP (no v2 resource: panos_bgp, panos_bgp_peer_group, panos_bgp_peer) ---')
            for path, routers in self._group_by_scope(bgp_routers):
                lines.append(self._report_section_header(path))
                for router in routers:
                    lines.append(f"  router: {router['name']} "
                                 f"(router_id: {router.get('router_id')}, "
                                 f"as_number: {router.get('as_number')})")
                    for pg in router['peer_groups']:
                        lines.append(f"    peer_group: {pg['name']} (type: {pg.get('type')}, "
                                     f"export-nexthop: {pg.get('export_nexthop')}, "
                                     f"import-nexthop: {pg.get('import_nexthop')})")
                    for peer in router['peers']:
                        lines.append(f"    peer: {peer['name']} (peer_as: {peer.get('peer_as')}, "
                                     f"local: {peer.get('local_address_ip') or peer.get('local_address_interface')}, "
                                     f"remote: {peer.get('peer_address_ip')}, "
                                     f"group: {peer.get('peer_group')}, enable: {peer.get('enable')})")
                    # The capture decision is now the print decision: a redist rule the
                    # parse keeps is printed here, so it is not a silent drop.
                    for rule in router['redistribution_rules']:
                        lines.append(f"    redist_rule: {rule['name']} "
                                     f"(family: {rule.get('address_family')}, "
                                     f"enable: {rule.get('enable')})")
                    vsys_line = self._report_vsys_line(router).rstrip()
                    if vsys_line:
                        lines.append(vsys_line)
            lines.append('')

        if ospf_routers:
            lines.append('--- OSPF (no v2 resource: panos_ospf, panos_ospf_area, panos_ospf_area_interface) ---')
            for path, routers in self._group_by_scope(ospf_routers):
                lines.append(self._report_section_header(path))
                for router in routers:
                    lines.append(f"  router: {router['name']} (router_id: {router.get('router_id')})")
                    for area in router['areas']:
                        ranges = f", ranges: {', '.join(area['ranges'])}" if area['ranges'] else ''
                        lines.append(f"    area: {area['area_id']} (type: {area.get('type')}{ranges})")
                    for iface in router['interfaces']:
                        lines.append(f"    interface: {iface['interface']} "
                                     f"(enable: {iface.get('enable')}, passive: {iface.get('passive')}, "
                                     f"link type: {iface.get('link_type')}, metric: {iface.get('metric')})")
                    vsys_line = self._report_vsys_line(router).rstrip()
                    if vsys_line:
                        lines.append(vsys_line)
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

        if report_only_addresses:
            lines.append('--- Address Objects With No v2 Attribute (v2 resource exists, not emitted) ---')
            for addr in report_only_addresses:
                fields = ', '.join(
                    f"{key}={value}"
                    for key, value in sorted((addr.get('other') or {}).items())) or 'no fields captured'
                lines.append(
                    f"  {addr.get('name')} (dg: {addr.get('device_group')}, "
                    f"vsys: {addr.get('vsys')}, type: {addr.get('declared_type') or 'unknown'}): "
                    f"{fields}")
            lines.append('  v2 resource: panos_address')
            lines.append('  Reason: panos_address models one attribute per address')
            lines.append('  type (ip_netmask, ip_range, ip_wildcard, fqdn). A')
            lines.append('  location-type entry (country/region/continent/container)')
            lines.append('  has no attribute, so it cannot be emitted. Configure the')
            lines.append('  object manually (GUI or CLI).')
            lines.append('')

        if dual_protocol_services:
            lines.append('--- Dual-Protocol Service Objects (v2 resource exists, one leg emitted) ---')
            for svc in dual_protocol_services:
                protocols = svc.get('protocols') or {}
                primary = TerraformGenerator.primary_service_protocol(protocols)
                for proto in TerraformGenerator.dropped_service_protocols(protocols):
                    lines.append(
                        f"  {svc.get('name')} (dg: {svc.get('device_group')}, "
                        f"vsys: {svc.get('vsys')}): {proto} leg dropped, "
                        f"{primary} emitted -> "
                        f"{TerraformGenerator.protocol_summary(protocols[proto])}")
            lines.append('  v2 resource: panos_service')
            lines.append('  Reason: panos_service accepts one protocol leg only; a')
            lines.append('  config with both tcp and udp fails terraform validate')
            lines.append('  (verified against 2.0.14). Add the dropped leg manually')
            lines.append('  (GUI or CLI), or define a second service object.')
            lines.append('')

        scope_reports = [line for kind, line in self._location_reports if kind == 'scope']
        if scope_reports:
            lines.append('--- Locations The Provider Cannot Carry (location emitted without the source scope) ---')
            lines.extend(scope_reports)
            lines.append('  v2 resource: as listed per line')
            lines.append('  Reason: the export defines the entry in a virtual')
            lines.append('  system, template, or device group that this resource')
            lines.append('  type has no location sub-block for, so the emitted')
            lines.append('  location cannot name it. terraform validate accepts an')
            lines.append('  unknown location sub-block and drops it silently, so')
            lines.append('  the converter omits it instead. Place the object in the')
            lines.append('  source scope manually (GUI or CLI) and verify against')
            lines.append('  this report.')
            lines.append('')

        device_reports = [line for kind, line in self._location_reports if kind == 'device']
        if device_reports:
            lines.append('--- Virtual System Locations Without A Target Device ---')
            lines.extend(device_reports)
            lines.append('  v2 resource: as listed per line')
            lines.append('  Reason: the export names the owning device')
            lines.append('  "localhost.localdomain", the PAN-OS placeholder for')
            lines.append('  "this device", so location.vsys.ngfw_device stays')
            lines.append('  empty. Set ngfw_device to the firewall that owns the')
            lines.append('  virtual system, or point the provider at that firewall.')
            lines.append('')

        placeholder_reports = [
            line for kind, line in self._location_reports if kind == 'placeholder']
        if placeholder_reports:
            lines.append('--- Template Locations The Export Does Not Name '
                         '(placeholder template emitted) ---')
            lines.extend(placeholder_reports)
            lines.append('  v2 resource: as listed per line')
            lines.append('  Reason: this resource type only lives in a template,')
            lines.append('  and the export places the entry in no template and on')
            lines.append('  no named device, so the converter cannot name the')
            lines.append('  template. It emits the placeholder name "Shared",')
            lines.append('  which is not a real template. Replace it with the')
            lines.append('  template that targets the firewall, or import the')
            lines.append('  entry from that firewall with location.ngfw.')
            lines.append('')

        # F4.2: entry coverage. A section the parse side does not read is
        # stated here so the operator sees what the conversion cannot cover.
        if entry_coverage:
            lines.append(entry_coverage)
            lines.append('')

        lines.append('End of report.')

        with open(self.output_dir / 'MANUAL_SETUP_REPORT.txt', 'w') as f:
            f.write('\n'.join(lines) + '\n')

    def generate_conversion_report(self, ledger) -> str:
        """Generate CONVERSION_REPORT.txt for the entries the parse read (F4.3).

        One line per report row, grouped by the F3.9 scope rule so a reader can
        tell two same-named entries on two device groups apart. The report names
        the input file name only, never the path (F4.2 rule 6).

        Returns '' when the input has no report rows, and writes no file in that
        case (F4.3 AC-9): a run that read no entry has nothing to report.
        """
        rows = ledger.rows()
        if not rows:
            return ''

        lines = ['=' * 80, entry_coverage.REPORT_HEADING, '=' * 80, '',
                 f'Input file: {ledger.source.name}', '', entry_coverage.RULE_PARAGRAPH, '']
        lines.extend(entry_coverage.summary_lines(ledger))

        gaps = ledger.gaps()
        if gaps:
            lines.extend(['', f'--- {entry_coverage.GAP_HEADING} ---', entry_coverage.GAP_RULE])
            for path, group in self._group_by_scope(gaps):
                lines.append(self._report_section_header(path))
                for row in group:
                    lines.append(entry_coverage.entry_line(row))

        # F4.4: the property scan. A captured property no output read is a gap. A
        # finding is an operator action, not a broken output, so it does not change the
        # exit code (the F4.1 gate does).
        findings = ledger.property_findings()
        if findings:
            lines.extend(['', f'--- {entry_coverage.PROPERTY_HEADING} ---', entry_coverage.PROPERTY_RULE])
            for path, group in self._group_by_scope(findings):
                lines.append(self._report_section_header(path))
                for row in group:
                    lines.append(entry_coverage.property_line(row))

        lines.extend(['', 'Entry lines are grouped by the scope the export declares (F3.9).',
                      '  line <source line>  <object type>/<entry name>  <destination>  '
                      '<detail>  captured: <fields>', ''])
        for path, group in self._group_by_scope(rows):
            lines.append('=' * 80)
            lines.append(self._report_section_header(path))
            lines.append('=' * 80)
            for row in group:
                lines.append(entry_coverage.entry_line(row))

        content = '\n'.join(lines) + '\n'
        with open(self.output_dir / entry_coverage.REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        return content

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
                    f"ike_profile_{profile['name']}", 'panos_ike_crypto_profile',
                    context=self.scope_context(profile), vsys=profile.get('vsys') or ''
                )
                content += f'resource "panos_ike_crypto_profile" "{resource_name}" {{\n'
                content += self.location_block('panos_ike_crypto_profile', profile)
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
                    profile_key, 'panos_ipsec_crypto_profile',
                    context=self.scope_context(profile), vsys=profile.get('vsys') or ''
                )
                content += f'resource "panos_ipsec_crypto_profile" "{resource_name}" {{\n'
                content += self.location_block('panos_ipsec_crypto_profile', profile)
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
                    f"ike_gw_{gw['name']}", 'panos_ike_gateway',
                    context=self.scope_context(gw), vsys=gw.get('vsys') or ''
                )
                content += f'resource "panos_ike_gateway" "{resource_name}" {{\n'
                content += self.location_block('panos_ike_gateway', gw)
                content += f'  name = {self.escape_string(gw["name"])}\n'

                # v2 protocol object: version + ikev1/ikev2 sub-object
                version = gw.get('version', 'ikev1')
                if version in ('ikev1', 'ikev2'):
                    proto_obj: dict = {'version': version}
                    ver_obj: dict = {}
                    if gw.get('ike_crypto_profile'):
                        ike_key = f"ike_profile_{gw['ike_crypto_profile']}"
                        # F2.6: reference when declared in this run, else
                        # plain name; F3.2: resolve in the gateway's vsys key
                        ver_obj['ike_crypto_profile'] = self.name_ref(
                            gw['ike_crypto_profile'], IKE_CRYPTO_SCOPES,
                            key=ike_key, vsys=gw.get('vsys') or '')
                    if ver_obj:
                        proto_obj[version] = ver_obj
                    content += f'  protocol = {self.hcl_value(proto_obj)}\n'

                if gw.get('peer_address'):
                    # v2 peer_address object keyed by fqdn or ip
                    key = 'fqdn' if gw.get('peer_address_type') == 'fqdn' else 'ip'
                    content += f'  peer_address = {self.hcl_value({key: gw["peer_address"]})}\n'

                if gw.get('local_address_interface'):
                    # F2.6: reference when the interface is in this run;
                    # F3.2: resolve in the gateway's vsys key
                    iface_ref = self.name_ref(
                        gw['local_address_interface'], INTERFACE_SCOPES,
                        vsys=gw.get('vsys') or '',
                        device=self.reference_device(gw))
                    content += f'  local_address = {self.hcl_value({"interface": iface_ref})}\n'
                elif gw.get('local_address'):
                    # Heuristic: dotted-quad values are IPs, otherwise
                    # interfaces; F3.2: resolve in the gateway's vsys key
                    local = gw['local_address']
                    key = 'ip' if self._looks_like_ip(local) else 'interface'
                    value = (self.name_ref(local, INTERFACE_SCOPES,
                                           vsys=gw.get('vsys') or '',
                                           device=self.reference_device(gw))
                             if key == 'interface' else local)
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
                    f"tunnel_{tunnel['name']}", 'panos_ipsec_tunnel',
                    context=self.scope_context(tunnel), vsys=tunnel.get('vsys') or ''
                )
                content += f'resource "panos_ipsec_tunnel" "{resource_name}" {{\n'
                content += self.location_block('panos_ipsec_tunnel', tunnel)
                content += f'  name = {self.escape_string(tunnel["name"])}\n'

                if tunnel.get('tunnel_interface'):
                    content += f'  tunnel_interface = {self.escape_string(tunnel["tunnel_interface"])}\n'

                # v2 auto_key object; ike_gateway and proxy_id are lists of objects
                auto_key: dict = {}
                if tunnel.get('ike_gateway'):
                    # F2.6: reference when the gateway is in this run,
                    # else a plain brown-field name (never a phantom
                    # resource); F3.2: resolve in the tunnel's vsys key
                    auto_key['ike_gateway'] = [{'name': self.name_ref(
                        tunnel['ike_gateway'], IKE_GATEWAY_SCOPES,
                        key=f"ike_gw_{tunnel['ike_gateway']}",
                        vsys=tunnel.get('vsys') or '')}]
                if tunnel.get('ipsec_crypto_profile'):
                    ipsec_key = f"ipsec_profile_{tunnel['ipsec_crypto_profile']}"
                    # F2.6: reference when declared in this run, else
                    # plain name; F3.2: resolve in the tunnel's vsys key
                    auto_key['ipsec_crypto_profile'] = self.name_ref(
                        tunnel['ipsec_crypto_profile'], IPSEC_CRYPTO_SCOPES,
                        key=ipsec_key, vsys=tunnel.get('vsys') or '')

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
        """Generate VPN migration report with key management instructions.

        F3.9: one section per scope the export declares, the same grouping rule
        as the interface report. The pre-shared-key warning stays at the top of
        the file, before the first section; the key management practices, the
        checklist and the security notes are one shared footer.
        """
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

        content += 'Gateways and tunnels are grouped by the scope the export declares: device\n'
        content += 'group first, then the template or the device the entry sits in. A section\n'
        content += 'names only the scope the export states, so the same object name on two\n'
        content += 'device groups appears once under each.\n'

        # One section per scope, then the object kind inside it (F3.9).
        sections: dict[tuple, dict[str, list[dict]]] = {}
        for entry in ike_gateways:
            sections.setdefault(self._report_scope_path(entry), {'gateways': [], 'tunnels': []})[
                'gateways'].append(entry)
        for entry in ipsec_tunnels:
            sections.setdefault(self._report_scope_path(entry), {'gateways': [], 'tunnels': []})[
                'tunnels'].append(entry)

        for path, kinds in sorted(sections.items()):
            content += '\n' + '=' * 80 + '\n'
            content += self._report_section_header(path) + '\n'
            content += '=' * 80 + '\n'

            for kind_title, entries in (('IKE GATEWAYS', kinds['gateways']),
                                        ('IPSEC TUNNELS', kinds['tunnels'])):
                if not entries:
                    continue
                content += f'\n{kind_title} ({len(entries)})\n'
                content += '-' * 80 + '\n'

                for entry in sorted(entries, key=lambda x: x['name']):
                    if kind_title == 'IKE GATEWAYS':
                        content += f'\nGateway: {entry["name"]}\n'
                        content += self._report_vsys_line(entry)
                        content += f'  Version: {entry.get("version", "ikev1")}\n'
                        content += f'  Peer Address: {entry.get("peer_address", "N/A")}\n'
                        content += (f'  Local Address: '
                                    f'{entry.get("local_address") or entry.get("local_address_interface", "N/A")}\n')
                        content += f'  Auth Type: {entry.get("auth_type", "pre-shared-key")}\n'

                        if entry.get('auth_type') == 'pre-shared-key':
                            content += '  ⚠️  Pre-Shared Key: ***MUST BE UPDATED***\n'
                            content += '     Current placeholder: ***CHANGE_ME***\n'
                            content += '     Action: Replace with actual key in vpn.tf\n'

                        content += f'  IKE Crypto Profile: {entry.get("ike_crypto_profile", "N/A")}\n'
                    else:
                        content += f'\nTunnel: {entry["name"]}\n'
                        content += self._report_vsys_line(entry)
                        content += f'  Type: {entry.get("type", "auto-key")}\n'
                        content += f'  Tunnel Interface: {entry.get("tunnel_interface", "N/A")}\n'
                        content += f'  IKE Gateway: {entry.get("ike_gateway", "N/A")}\n'
                        content += f'  IPsec Crypto Profile: {entry.get("ipsec_crypto_profile", "N/A")}\n'

                        if entry.get('proxy_ids'):
                            content += '  Proxy IDs:\n'
                            for proxy in entry['proxy_ids']:
                                content += (f'    - {proxy["name"]}: '
                                            f'{proxy.get("local", "any")} <-> {proxy.get("remote", "any")}\n')

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

1. Set up the credential variables in `terraform.tfvars` (do not
   commit the file):

```hcl
panos_hostname = "your-panorama-hostname-or-ip"
panos_username = "admin"
panos_password = "your-password"
```

Or use Terraform environment variables:
```bash
export TF_VAR_panos_hostname="your-panorama-hostname-or-ip"
export TF_VAR_panos_username="admin"
export TF_VAR_panos_password="your-password"
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

The generator writes a file only when it has content, so a run produces the
subset below that matches the input.

Terraform configuration:

- `provider.tf` - Provider configuration
- `variables.tf` - Variable definitions
- `address_objects.tf`, `address_groups.tf` - Address objects and groups
- `service_objects.tf`, `service_groups.tf` - Service objects and groups
- `tags.tf` - Administrative tags
- `custom_url_categories.tf` - Custom URL categories
- `application_groups.tf` - Application groups
- `external_lists.tf` - External dynamic lists
- `security_rules.tf`, `nat_rules.tf`, `decryption_rules.tf`, `pbf_rules.tf` -
  Policy rules, one resource per rule
- `monitor_profiles.tf` - PBF path monitoring profiles
- `zones.tf`, `virtual_routers.tf`, `interfaces.tf` - Network objects
- `security_profiles.tf` - Profile names and descriptions as comments, because the
  parse does not capture the profile body
- `security_profile_groups.tf` - Security profile groups
- `vpn.tf` - IKE and IPsec crypto profiles, IKE gateways, IPsec tunnels

Reports:

- `CONVERSION_REPORT.txt` - one line per entry the parse read, with its destination
- `MANUAL_SETUP_REPORT.txt` - objects the provider cannot model, and the reasons
- `INTERFACE_MIGRATION_REPORT.txt` - interfaces and IP addresses to set on the target
- `VPN_MIGRATION_REPORT.txt` - VPN objects and pre-shared key actions
- `SANITY_REPORT.txt` - the post-run gate result

## Important Notes

- Review all configurations before applying
- Test in a non-production environment first
- Back up your existing configuration
- Adjust rule ordering as needed
- Run `terraform validate` on this directory, or pass `--validate` to the
  converter, so the gate reports findings instead of printing only success
- Some features are reported, not generated: see the reports

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
    # F3.8: the same input limit on both entry points.
    add_max_input_argument(parser)
    # F4.1: the static gate runs on every conversion. --validate adds the
    # terraform init + validate check, which needs the terraform binary.
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Run terraform init and terraform validate on the output',
    )

    args = parser.parse_args()

    # Check if input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        return 1

    try:
        print(f"Parsing Panorama configuration from {args.input_file}...")
        panorama = PanoramaParser(args.input_file, args.max_input_bytes)

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

        # Dynamic routing (one record per router, F4.4)
        bgp_routers = panorama.parse_bgp()
        ospf_routers = panorama.parse_ospf()

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
        if bgp_routers:
            print(f"  - BGP enabled on {len(bgp_routers)} router(s)")
            for router in bgp_routers:
                print(f"    {router['name']}: AS {router.get('as_number')}, "
                      f"{len(router['peers'])} peers, {len(router['peer_groups'])} peer groups, "
                      f"{len(router['redistribution_rules'])} redistribution rules")
        if ospf_routers:
            print(f"  - OSPF enabled on {len(ospf_routers)} router(s)")
            for router in ospf_routers:
                print(f"    {router['name']}: {len(router['areas'])} areas, "
                      f"{len(router['interfaces'])} interfaces")

        # VPN
        print(f"  - {len(ike_gateways)} IKE gateways")
        print(f"  - {len(ipsec_tunnels)} IPsec tunnels")

        print(f"\nGenerating Terraform configuration in {args.output_dir}...")
        tf_gen = TerraformGenerator(args.output_dir, panorama.parse_associations())

        # F4.4: the property scan measures which keys an output reads from a captured
        # object, so the record starts here and not during the parse.
        panorama.ledger.start_recording()

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
        tf_gen.generate_interfaces(interfaces)
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
        # F4.2: scan the parsed input for a section container the container
        # table does not cover. A finding is an operator action, not a broken
        # output, so it does not change the exit code (the F4.1 gate does).
        coverage_findings = container_coverage.scan(panorama.source, panorama.parent_map)
        tf_gen.generate_manual_setup_report(
            bgp_routers, ospf_routers, application_filters, manual_key_tunnels,
            application_override_rules=app_override_rules,
            qos_profiles=qos_profiles,
            tunnel_monitor_profiles=tunnel_monitor_profiles,
            schedules=schedules,
            log_settings=log_settings,
            zone_protection_profiles=zone_protection_profiles,
            report_only_addresses=[a for a in addresses if a.get('report_only')],
            dual_protocol_services=[
                s for s in services
                if len(TerraformGenerator.dropped_service_protocols(s.get('protocols') or {})) > 0
            ],
            entry_coverage=container_coverage.render_section(coverage_findings, panorama.source.name),
        )

        # Reports
        tf_gen.generate_interface_report(interfaces)
        tf_gen.generate_readme()

        # F4.3: one line per entry the parse pipeline read. A gap is an operator
        # action, not a broken output, so it does not change the exit code (the
        # F4.1 gate does).
        tf_gen.generate_conversion_report(panorama.ledger)

        print("\n✓ Successfully generated Terraform configuration!")
        print("\n📄 Generated Migration Reports:")
        print("  - INTERFACE_MIGRATION_REPORT.txt (Interface and IP inventory)")
        if panorama.ledger.rows():
            print("  - CONVERSION_REPORT.txt (one line per entry the parser read)")
        if ike_gateways or ipsec_tunnels:
            print("  - VPN_MIGRATION_REPORT.txt ⚠️  (VPN config with key management instructions)")

        # F4.2: one console line per uncovered section, so a run that read an
        # entry it cannot model is visible without opening the report.
        if coverage_findings:
            print(f"\n⚠️  Entry Coverage: {len(coverage_findings)} container(s) the parser does not read")
            for finding in coverage_findings:
                print(container_coverage.console_line(finding))

        # F4.3: entry totals, then one console line per gap entry. A gap is an
        # operator action, not a broken output, so it does not change the exit
        # code (the F4.1 gate does). No console line when the run has no gap.
        gap_console = entry_coverage.console_lines(panorama.ledger, tf_gen._report_scope_path)
        if gap_console:
            print()
            for line in entry_coverage.summary_lines(panorama.ledger):
                print(line)
            for line in gap_console:
                print(line)
            print(f"Per-entry report file: {Path(args.output_dir) / entry_coverage.REPORT_FILE}")

        # F4.1: the gate reads the files that were written, so it reports what
        # the operator receives. A WARN does not fail the gate; a FAIL does.
        report = sanity_checks.run_checks(args.output_dir, run_terraform=args.validate)
        report_path = Path(args.output_dir) / 'SANITY_REPORT.txt'
        report_path.write_text(report.render(), encoding='utf-8')
        print()
        print(report.console_summary())
        print(f"Sanity report: {report_path}")

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

        # F4.1: a FAIL finding is a broken output, so the conversion reports it
        # with a non-zero exit code instead of writing files and exiting 0.
        return 1 if report.failed else 0

    except ET.ParseError as e:
        print(f"Error: Failed to parse XML file: {e}")
        return 1
    except UnsafeInputError as e:
        # F3.8: an input size or DTD refusal. The message already names the
        # file, the limit and the measured value, so print it unchanged.
        print(f"Error: {e}")
        return 1
    except ValueError as e:
        print(f"Error: rejected '{args.input_file}': {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
