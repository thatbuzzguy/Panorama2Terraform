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
    python3 src/panorama_to_terraform.py <input_file.xml> [--output-dir <dir>] [--validate]

See docs/USAGE_GUIDE.md for the flags, the report files, and the post-run gate.
"""

import argparse
import hashlib
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

import commit_actions
import container_coverage
import entry_coverage
import import_blocks
import naming
import ownership
import provenance
import reference_edges
import resource_mapping
import sanity_checks
import shadow_coverage
import site_data
import source_fetch
import state_coverage
import state_input
import unit_manifest
import write_path
from resource_mapping import (
    DATA_SOURCE_SCHEMA,
    INTERFACE_RESOURCE_TYPES,
    LOCATION_SCHEMA,
    SCOPE_LEVEL_ORDER,
    SCOPE_PLACEMENT,
    SCOPE_SHAPE,
    SCOPE_TYPES,
)
from xml_input import (
    DEFAULT_SCOPE,
    ParsedSource,
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

    def __init__(self, source: ParsedSource,
                 ledger: Optional[entry_coverage.EntryLedger] = None):
        # F5.2: the parser takes the ParsedSource the producer boundary returns,
        # the same contract for every source. The parser keeps no read of its
        # own: the size cap and the DTD refusal (F3.8) and the line map (F4.2)
        # belong to the door, so a source that bypasses the door cannot reach
        # this class.
        self.source = source
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
        """Parse the device group entries (F6.5: a scope entry is an object the output writes).

        The entry name is the scope, so the block writes it as `name`. The properties are the
        fields the scope block prints: the description, the parent group, the device members,
        and the template members. The parent is what `ownership.py` rule 4 needs to name an
        ancestor, so a repeated name between a parent group and a child group is no longer an
        operator decision.

        `parse_associations` reads the same membership for its tables and marks the membership
        entries, not this entry, so the entry keeps one mark (F4.3 rule 1).
        """
        device_groups = []
        for dg in self.root.findall(".//device-group/entry"):
            name = dg.get('name')
            if not name:
                self.mark_skipped(dg, 'entry has no name attribute')
                continue
            device_groups.append(self.mark(dg, {
                'name': name,
                'description': self._get_text(dg, 'description'),
                'parent': self._get_text(dg, 'parent'),
                'devices': self._list_names(dg, 'devices'),
                'templates': self._list_names(dg, 'templates'),
                **self.identity_of(dg),
            }))

        return device_groups

    def parse_templates(self) -> list[dict]:
        """Parse the template entries (F6.5).

        The properties are the fields the block prints. A template's device members are not a
        provider field for `panos_template`, so they are read by `parse_associations` for the
        association table and are not captured here.
        """
        templates = []
        for entry in self.root.findall('.//templates/entry'):
            name = entry.get('name')
            if not name:
                self.mark_skipped(entry, 'entry has no name attribute')
                continue
            templates.append(self.mark(entry, {
                'name': name,
                'description': self._get_text(entry, 'description'),
                'default_vsys': self._get_text(entry, 'default_vsys'),
                **self.identity_of(entry),
            }))

        return templates

    def parse_template_stacks(self) -> list[dict]:
        """Parse the template stack entries (F6.5).

        A stack is the only scope that lists members instead of holding config, so its device
        and template lists are fields the block prints.
        """
        stacks = []
        for entry in self.root.findall('.//template-stack/entry'):
            name = entry.get('name')
            if not name:
                self.mark_skipped(entry, 'entry has no name attribute')
                continue
            stacks.append(self.mark(entry, {
                'name': name,
                'description': self._get_text(entry, 'description'),
                'default_vsys': self._get_text(entry, 'default_vsys'),
                'devices': self._list_names(entry, 'devices'),
                'templates': self._list_names(entry, 'templates'),
                **self.identity_of(entry),
            }))

        return stacks

    def parse_template_variables(self) -> list[dict]:
        """Parse the template variable entries (F6.5).

        `template_stack` is the fifth scope fact (F6.10.5), so the walk names the scope the entry
        sits in and the emitter reads it to choose the location sub-block. The value stays a
        literal: the tool cannot know which values a module takes as parameters, so the block is the
        PAN-OS variable (`docs/CODEBASE_ASSEMBLY.md` §9 rule 2). An entry the export places in no
        template and no template stack has no place the provider can put it, so the run writes no
        block for it.
        """
        variables = []
        for entry in self.root.findall('.//variable/entry'):
            name = entry.get('name')
            if not name:
                self.mark_skipped(entry, 'entry has no name attribute')
                continue
            container = self._scope_container_of(entry, ('templates', 'template-stack'))
            if not container:
                self.mark_skipped(
                    entry,
                    'no template or template stack holds this variable, so the provider has no '
                    'location for it')
                continue
            variables.append(self.mark(entry, {
                'name': name,
                'description': self._get_text(entry, 'description'),
                'type': self._variable_type(entry),
                **self.identity_of(entry),
            }))

        return variables

    def parse_vsys(self) -> list[dict]:
        """Parse the virtual system entries (F6.5).

        A virtual system is a scope. The provider places it inside a template or a template
        stack, but the export holds a virtual system only inside a template: a template stack
        lists devices and templates and holds no virtual system. So an entry the export places on
        a device alone has no place the provider can put it, and the run writes no block and
        reports the entry as skipped. This row declares no property, so the block carries the
        entry name and the location only.
        """
        systems = []
        for entry in self.root.findall('.//vsys/entry'):
            name = entry.get('name')
            if not name:
                self.mark_skipped(entry, 'entry has no name attribute')
                continue
            if not self._scope_container_of(entry, ('templates',)):
                self.mark_skipped(
                    entry,
                    'no template holds this virtual system, so the provider has no location for '
                    'it: a template stack lists templates and devices and holds no virtual system')
                continue
            systems.append(self.mark(entry, {'name': name, **self.identity_of(entry)}))

        return systems

    def _scope_container_of(self, elem: ET.Element, containers: tuple) -> str:
        """The name of the scope entry whose container is one of `containers` (F6.5).

        Walks up through the parent map, so the scope is the one the export declares, never a
        guess. The container name comes from `container_coverage.container_tag`, the one place
        the per-scope shape is stated.
        """
        node = elem
        while node is not None:
            if node.tag == 'entry' and \
                    container_coverage.container_tag(node, self.parent_map, self.source) in containers:
                return node.get('name') or ''
            node = self.parent_map.get(node)
        return ''

    def _variable_type(self, entry: ET.Element) -> dict:
        """The variable's `type` shape as one dict: the kind the entry states and its value.

        A template variable entry writes the value inside `<type>`, in the field that names the
        kind (`ip-netmask`, `fqdn`, ...), and the provider takes the same shape as a nested
        block. A field name is the provider spelling, so the underscore is the provider's.
        """
        shape = entry.find('type')
        if shape is None:
            return {}
        for node in list(shape):
            return {node.tag.replace('-', '_'): (node.text or '').strip()}
        return {}

    def device_group_of(self, elem: ET.Element) -> str:
        """Return the name of the device group that defines elem (F2.3).

        An entry under a <device-group><entry> belongs to that group. An
        entry under <shared> or at the top level belongs to the shared
        device group, which PAN-OS names "Shared".

        F5.4: the container name comes from `container_coverage.container_tag`, so a
        per-scope source reads its root as the place its path names and the declared
        scope entry names the group, instead of falling back to Shared.
        """
        node = elem
        while node is not None:
            container = container_coverage.container_tag(node, self.parent_map, self.source)
            if container == 'device-group' and node.tag == 'entry':
                return node.get('name') or 'Shared'
            if node.tag == 'shared':
                return 'Shared'
            node = self.parent_map.get(node)
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

        The container name comes from `container_coverage.container_tag` (F5.4), so a
        per-scope source reads its root as the place its path names.
        """
        node = elem
        while node is not None:
            container = container_coverage.container_tag(node, self.parent_map, self.source)
            if node.tag == 'entry' and container == 'vsys':
                return node.get('name') or 'vsys1'
            node = self.parent_map.get(node)
        return ''

    def template_of(self, elem: ET.Element) -> str:
        """Return the template that owns elem, or '' when the export names none.

        Walks up to the nearest <templates><entry name="..."> ancestor
        (F3.1 identity key). Panorama nests a template's own device config
        under <templates><entry><devices><entry>, so a template-defined
        object reports its template here and its placeholder device name
        from device_of.

        The container name comes from `container_coverage.container_tag` (F5.4), so a
        per-scope source reads its root as the place its path names.
        """
        node = elem
        while node is not None:
            container = container_coverage.container_tag(node, self.parent_map, self.source)
            if node.tag == 'entry' and container == 'templates':
                return node.get('name') or ''
            node = self.parent_map.get(node)
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

        The container name comes from `container_coverage.container_tag` (F5.4), so a
        per-scope source reads its root as the place its path names.
        """
        node = elem
        while node is not None:
            container = container_coverage.container_tag(node, self.parent_map, self.source)
            if node.tag == 'entry' and container == 'devices':
                return node.get('name') or ''
            node = self.parent_map.get(node)
        return ''

    def template_stack_of(self, elem: ET.Element) -> str:
        """Return the template stack that owns elem, or '' when the export names none.

        Walks up to the nearest <template-stack><entry name="..."> ancestor (F6.10.5, the
        fifth scope fact). A stack entry is its own ancestor, so a stack names the stack. A
        stack lists members instead of holding config, so the entries it owns are the ones the
        export nests inside it, which is a variable.

        The container name comes from `container_coverage.container_tag` (F5.4), so a
        per-scope source reads its root as the place its path names.
        """
        node = elem
        while node is not None:
            container = container_coverage.container_tag(node, self.parent_map, self.source)
            if node.tag == 'entry' and container == 'template-stack':
                return node.get('name') or ''
            node = self.parent_map.get(node)
        return ''

    def identity_of(self, elem: ET.Element) -> dict:
        """Return the five source scope facts of an entry (F3.5, F6.10.5).

        Every parse method records these on every object, so the emitter can
        place a resource without looking at the XML again:

            device_group    - the defining device group, 'Shared' for the
                              shared section (F2.3)
            vsys            - the declared virtual system, '' when the export
                              declares none
            template        - the declared template, '' when the export
                              declares none
            vsys_device     - the device that owns a vsys-scoped entry, used
                              as the location `ngfw_device`
            template_stack  - the declared template stack, '' when the export
                              declares none (F6.10.5)
        """
        return {
            'device_group': self.device_group_of(elem),
            'vsys': self.vsys_of(elem),
            'template': self.template_of(elem),
            'vsys_device': self.device_of(elem),
            'template_stack': self.template_stack_of(elem),
        }

    def _list_names(self, container: ET.Element, child_tag: str) -> list:
        """Return the names a container lists, in document order, and mark the entries it holds.

        A Panorama export lists members two ways: the long form
        `<devices><entry name="fw-1.example.com">` and the short form
        `<templates><member>T1</member>`. Both mean the same thing.

        A member is not an entry, so it has nothing to mark. An entry inside a membership
        container is marked here, because this is the method that reads it (F4.3 rule 1): the
        scope entry itself is marked by the parse method that reads the scope, so one entry has
        one mark (F6.5).
        """
        names = []
        listing = container.find(child_tag)
        if listing is None:
            return names
        for node in list(listing):
            if node.tag == 'entry':
                name = node.get('name')
                self.mark(node, {})
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

        The tables are the fact this method records, and they are read as tables, so no captured field carries
        them (`docs/COVERAGE_MATRIX.md` §1). The membership entries this method marks hold no value: `_list_names`
        marks each with an empty object, so the entry line names no field and states the relation as the detail
        column. The value of the relation is the list on the entry that owns the container, and the block of that
        entry prints it through the row that covers it. The location rule reads these tables to place an entry, so
        the membership entry reaches the output only as the row identity.
        """
        cached = getattr(self, '_associations', None)
        if cached is not None:
            return cached

        tables = {'device_groups': {}, 'templates': {}, 'template_stacks': {},
                  'stack_templates': {}}
        # F6.5: the scope entry is marked by the parse method that reads it as an object, so
        # this method marks only the membership entries inside it (`_list_names`). One entry,
        # one mark.
        for entry in self.root.findall('.//device-group/entry'):
            name = entry.get('name')
            if name:
                for device in self._list_names(entry, 'devices'):
                    tables['device_groups'].setdefault(device, []).append(name)
        for entry in self.root.findall('.//templates/entry'):
            name = entry.get('name')
            if name:
                for device in self._list_names(entry, 'devices'):
                    tables['templates'].setdefault(device, []).append(name)
        for entry in self.root.findall('.//template-stack/entry'):
            name = entry.get('name')
            if not name:
                continue
            devices = self._list_names(entry, 'devices')
            templates = self._list_names(entry, 'templates')
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
                'comments': self._get_text(tag, 'comments'),
                # F4.4: the `panos_administrative_tag` row names the property, so the parse reads the
                # entry field here and the emitter reads the key
                'disable_override': self._get_text(tag, 'disable-override')
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
                'description': self._get_text(cat, 'description'),
                # F4.4: the row names the property, so the flag is read through the same helper as
                # the other fields of this entry
                'disable_override': self._get_text(cat, 'disable-override')
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
                'members': members,
                # F4.4: the row names the property, so the flag is read through the same helper as
                # the other fields of this entry
                'disable_override': self._get_text(ag, 'disable-override')
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
                # F4.4: the field is printed by the manual report, which is the output for a `report`
                # container, so the report line reads it through the captured object
                'description': self._get_text(af, 'description'),
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
                # F4.4: the flag is a field of the entry, not of the sub-shape, so the
                # provider takes it at the block's own level
                'disable_override': self._get_text(ext_list, 'disable-override'),
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
            # F7.6: the policy states an `address` level that holds entries, so the row that covers that container
            # is the policy row and not the address-object row. The table is the one place that states which method
            # reads a level, so the address rule reads only the level its own row states, and a policy address
            # entry is read by `parse_bgp`.
            row = entry_coverage.covering_row(
                container_coverage.section_path(self.parent_map.get(addr), self.parent_map, self.source))
            if row is not None and row.method != 'parse_address_objects':
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
                'description': self._get_text(grp, 'description'),
                # F4.4: the row names the property, so the flag is read through the same helper as
                # the other fields of this entry
                'disable_override': self._get_text(grp, 'disable-override')
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

        F6.2: `disable-override` is captured, so the ownership rule can read the flag for a
        service entry (`ownership.py` rule 4). The emitter reads it, so the coverage matrix row
        names it.
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
            # F6.2: the parse keeps the flag here, as the address parser does (F3.4), because the
            # ownership rule reads it (`ownership.py` rule 4). An entry with no value keeps the
            # cleared default, so no property finding appears for it.
            service_obj['disable_override'] = (self._get_text(svc, 'disable-override') or '').strip()
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
                'description': self._get_text(grp, 'description'),
                # F4.4: the row names the property, so the flag is read through the same helper as
                # the other fields of this entry
                'disable_override': self._get_text(grp, 'disable-override')
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
                # F4.4: the profile group reference reaches the provider as
                # `profile_setting.group`, so the parse keeps the members under the parsed-object
                # key the row names. No reference scope names a profile group, so the names stay
                # brown-field strings.
                'profile_group': self._get_members(rule, 'profile/group'),
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
                # F4.4: `panos_nat_policy_rules.rules.service` is a string, so the member form
                # reaches the field as one name; the helper is what reads both export forms
                'service': self._get_single_value(rule, 'service'),
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
                'recurring': [],
                # F4.4: `panos_schedule` declares no description, so the manual report is the
                # output that reads this field
                'description': self._get_text(sched, 'description')
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
                # F4.4: `parent` is not a field for a nested-block entry, so it stays empty here. The
                # pinned provider declares no `parent` attribute on `panos_ethernet_interface`, so no line of
                # this block can print a parent. The parent is a fact of the parent entry, and for a unit name
                # the child's own name states it (`ethernet1/4.1` is unit 1 of `ethernet1/4`), which the print
                # reads through the name: the name is the row identity. The entry line therefore names only the
                # fields the print reads: `mode` for the block key, `type` for the parent type, and `comment`
                # when the entry carries one (`docs/COVERAGE_MATRIX.md` §1).
                'parent': None,
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
        # F7.1, F7.2: `protocol` is a captured field of the router entry, so the entry keeps one mark and the
        # protocol levels are the properties of that one entry. Each level is built by the parse method the
        # `protocol` row names, in the table order, so this method states no field name of its own (F7.5).
        return {
            'name': router.get('name'),
            **self.identity_of(router),
            'interfaces': interfaces,
            'static_routes': static_routes,
            'protocol': {field: getattr(self, f'parse_{field}')(router)
                          for field in resource_mapping.protocol_row(resource_mapping.PROTOCOL_FIELD)['fields']},
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
                'wildfire_analysis': self._get_members(grp, 'wildfire-analysis'),
                # F4.4: the row names the property, so the flag is read through the same helper as
                # the other fields of this entry
                'disable_override': self._get_text(grp, 'disable-override')
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

    def parse_bgp(self, router: ET.Element) -> dict:
        """Build the `bgp` level of one router's protocol object (F7.1).

        The router entry is marked once by `_parse_router`, so this method fills the `protocol` field of
        that mark instead of keeping a record of its own. Every captured field is a field
        `PROTOCOL_SHAPE` declares for the level, so the emitter, the gate and the property scan read the
        same names. A field's element name is the field name with `_` as `-`, which is how a PAN-OS export
        spells it, and that rule lives here in the reader, not in a second table.

        A peer nests inside the peer-group entry that holds it, because the shape table states no peer
        outside a peer group: the membership is the parent entry, not a text field. A peer the export
        places at the `bgp` level that no peer group names cannot be expressed, so it is marked for the
        report and the manual report prints it. The same rule holds for every entry this method reads:
        an entry the `.tf` cannot express is marked for the report and is not put in the printed list, so
        the report names it and the file holds no half of it.

        F7.10: the five `bool` fields and the two single-object levels the row now states are read by
        `_protocol_level`, so this method states no path for them. `dampening_profile` is the entry level the
        row states, so this method states its path and `_protocol_branch` fills it.
        """
        bgp_path = 'protocol/bgp'
        bgp = router.find(bgp_path)
        if bgp is None:
            return {}
        level = self._protocol_level(bgp, bgp_path)
        groups = {}
        # The key a level dict holds is the field the table path names, so the parse methods state a path and
        # never spell a field name: `PROTOCOL_SHAPE` stays the one owner of the names.
        group_path, peer_path = 'protocol/bgp/peer_group', 'protocol/bgp/peer_group/peer'
        for group in bgp.findall('.//peer-group/entry'):
            name = group.get('name')
            if not name:
                continue
            captured = self._protocol_level(group, group_path)
            choice_path = 'protocol/bgp/peer_group/type'
            field = self._protocol_field_name(choice_path)
            choice, detail = self._protocol_choice(choice_path,
                                                   self._get_text(group, self._protocol_xml_name(field)),
                                                   group, group)
            captured[field] = choice
            entry = self.mark(group, captured, detail, destination='report' if detail else None)
            if detail:
                continue
            level[self._protocol_field_name(group_path)].append(entry)
            groups[name] = entry
            # A peer inside the peer-group element belongs to that entry, so the shape table states `peer`
            # as a field of the peer-group level.
            for peer in group.findall('./peer/entry'):
                if peer.get('name'):
                    entry[self._protocol_field_name(peer_path)].append(
                        self.mark(peer, self._protocol_level(peer, peer_path)))

        for peer in bgp.findall('./peer/entry'):
            name = peer.get('name')
            if not name:
                continue
            captured = self._protocol_level(peer, peer_path)
            group = self._get_text(peer, 'peer-group')
            if group in groups:
                # The name reference is recorded on the parent entry, which is the peer group that
                # holds it, so the entry keeps one mark (F4.3 rule 3).
                groups[group][self._protocol_field_name(peer_path)].append(self.mark(peer, captured))
            else:
                # The provider has no peer outside a peer group, so this one cannot be expressed.
                self.mark(peer, captured, 'no peer group names it', destination='report')
        redist_path = 'protocol/bgp/redist_rules'
        for rule in bgp.findall('.//redist-rules/entry'):
            if rule.get('name'):
                level[self._protocol_field_name(redist_path)].append(
                    self.mark(rule, self._protocol_level(rule, redist_path)))
        # F7.6: the `policy` level and its subtree are read through the table. The four levels inside it that
        # hold entries are the levels the container table names, so this method states their paths; a level
        # inside an entry is filled by `_protocol_body`, which reaches it through the table and so states no
        # path, and the container table states no row for it.
        policy_path = 'protocol/bgp/policy'
        policy = router.find(policy_path)
        if policy is not None:
            policy_level = self._protocol_level(policy, policy_path)
            for path in ('protocol/bgp/policy/aggregation/address',
                         'protocol/bgp/policy/conditional_advertisement/policy',
                         'protocol/bgp/policy/export/rules',
                         'protocol/bgp/policy/import/rules'):
                self._protocol_branch(policy_path, policy_level, policy, path)
            level[self._protocol_field_name(policy_path)] = policy_level
        # F7.7: `auth_profile` is an entry level the row states as a `string_list` field, so the same rule
        # fills it. The path is the only name this method states; `secret` is read as a field, and the print
        # site turns it into the variable reference.
        self._protocol_branch(bgp_path, level, bgp, 'protocol/bgp/auth_profile')
        # F7.10: `dampening_profile` is the other entry level this method fills through the table. The five
        # `bool` fields and the two single-object levels are row fields, so `_protocol_level` reads them with no
        # field name of its own, and the levels inside `routing_options` hold no entry.
        self._protocol_branch(bgp_path, level, bgp, 'protocol/bgp/dampening_profile')
        return level

    def parse_ospf(self, router: ET.Element) -> dict:
        """Build the `ospf` level of one router's protocol object (F7.1, F7.9).

        The area rule is `_protocol_areas`, the same reader `parse_ospfv3` uses. An interface at the
        `protocol/ospf` level has no provider field, so it is marked for the report and the manual report
        prints it.

        F7.9: the three `bool` fields and the three single-object levels are fields the row states, so
        `_protocol_level` reads them with no field name of its own. `export_rules` is a `string_list` level,
        so this method states its path and `_protocol_branch` fills it with the entries the export holds, the
        same rule `parse_ospfv3` uses.
        """
        ospf_path = 'protocol/ospf'
        ospf = router.find(ospf_path)
        if ospf is None:
            return {}
        level = self._protocol_areas(ospf, ospf_path)
        for iface in ospf.findall('./interface/entry'):
            if not iface.get('name'):
                continue
            # The provider declares an interface only inside an area, so an interface at the OSPF level
            # cannot be expressed and the manual report prints it. The row note is the reason, so the mark
            # states no detail of its own.
            captured, _ = self._protocol_interface(iface, ospf_path)
            self.mark(iface, captured, destination='report')
        # F7.7: `auth_profile` is an entry level the row states as a `string_list` field, so the same rule
        # fills it, and `md5` is the entry level inside the profile entry that `_protocol_body` fills through
        # the table. The path is the only name this method states.
        self._protocol_branch(ospf_path, level, ospf, 'protocol/ospf/auth_profile')
        # F7.9: `export_rules` is the other entry level this method fills through the table. The three
        # single-object levels hold no entry, so they are read by `_protocol_level` through the row fields,
        # and this method states no path for them.
        self._protocol_branch(ospf_path, level, ospf, 'protocol/ospf/export_rules')
        return level

    def parse_ospfv3(self, router: ET.Element) -> dict:
        """Build the `ospfv3` level of one router's protocol object (F7.2, F7.3).

        The same reader as `parse_ospf`, because the provider declares the same fields for the two area
        subtrees. An interface at the `protocol/ospfv3` level has no provider field, so the report names it.
        A level the shape table states no row for is read by no method, so the levels this feature does not
        read print nothing (`backlog.md`).

        F7.3: the three single-object levels are read by `_protocol_level`, because the row states them as
        fields of this level. `export_rules` is a `string_list`, so this method fills it with the entries the
        export holds, the same rule as `parse_bgp` for `redist_rules`.
        """
        ospfv3_path = 'protocol/ospfv3'
        ospfv3 = router.find(ospfv3_path)
        if ospfv3 is None:
            return {}
        level = self._protocol_areas(ospfv3, ospfv3_path)
        export_path = f'{ospfv3_path}/export_rules'
        for rule in ospfv3.findall('.//export-rules/entry'):
            if rule.get('name'):
                level[self._protocol_field_name(export_path)].append(
                    self.mark(rule, self._protocol_level(rule, export_path)))
        for iface in ospfv3.findall('./interface/entry'):
            if not iface.get('name'):
                continue
            # The provider declares an interface only inside an area, so an interface at the level cannot be
            # expressed and the manual report prints it, the same rule as `parse_ospf`.
            captured, _ = self._protocol_interface(iface, ospfv3_path)
            self.mark(iface, captured, destination='report')
        # F7.7: `auth_profile` is the entry level this method reads, and the choice levels inside the entry
        # (`ah`, `esp/authentication`) and the object level `esp/encryption` are filled by `_protocol_body`,
        # which reaches them through the table, so this method states no path for them.
        self._protocol_branch(ospfv3_path, level, ospfv3, 'protocol/ospfv3/auth_profile')
        return level

    def parse_rip(self, router: ET.Element) -> dict:
        """Build the `rip` level of one router's protocol object (F7.5).

        The same rule as the other routing levels: every captured field is a field `PROTOCOL_SHAPE` declares
        for the level, the method states a level as a table path, and `_protocol_field_name` and
        `_protocol_xml_name` name the key and the element. `rip` declares no router id, no area and no
        neighbor, so the level prints nothing for a field the row does not state.

        The level's two `string_list` fields are filled by `_protocol_entries`, because the export states a
        name-keyed list as an entry. An interface entry holds its `default_route` choice inside itself, so
        `_protocol_body` fills it, and an entry whose choice element states none of the alternatives the
        provider requires is marked for the report and not put in the printed list. The choice level itself is
        not required, so an entry that states no choice element prints no field for it. F7.7: `auth_profile` is
        the level this method reads through `_protocol_branch`, so the print site names the entry's variable
        for `key` and `password`.
        """
        rip_path = 'protocol/rip'
        rip = router.find(rip_path)
        if rip is None:
            return {}
        level = self._protocol_level(rip, rip_path)
        interface_path, rule_path = f'{rip_path}/interfaces', f'{rip_path}/export_rules'
        for path, entries in ((interface_path, rip.findall('./interfaces/entry')),
                              (rule_path, rip.findall('.//export-rules/entry'))):
            self._protocol_entries(path, level[self._protocol_field_name(path)], entries)
        # F7.7: `auth_profile` is the entry level the row states as a `string_list` field, so the same rule
        # fills it, and `md5` inside the profile entry is filled by `_protocol_body` through the table.
        self._protocol_branch(rip_path, level, rip, 'protocol/rip/auth_profile')
        return level

    def parse_redist_profile(self, router: ET.Element) -> list:
        """Build the entries of one router's `redist_profile` level (F7.10).

        The `protocol` row states this level as a `string_list` field, so `_parse_router` calls this method by
        the field's name. The path is the only name this method states: `_protocol_entry_level` reads each entry
        through the row, so the key an entry holds is the field the path names, and each entry is marked, which is
        what puts its fields in the property scan.
        """
        return self._protocol_entry_level(router, 'protocol/redist_profile')

    def parse_redist_profile_ipv6(self, router: ET.Element) -> list:
        """The same shape for the IPv6 list, read through the row the table states for it (F7.10).

        The two rows differ by one field: the provider names the routing level inside `filter` as `ospf` for the
        IPv4 list and `ospfv3` for the IPv6 list, so the reader states two paths and spells no field name.
        """
        return self._protocol_entry_level(router, 'protocol/redist_profile_ipv6')

    def _protocol_areas(self, container: ET.Element, base: str) -> dict:
        """One routing level and its area entries, read as `PROTOCOL_SHAPE` states them (F7.1, F7.2).

        `base` is the table path of the level, so the reader states a level as a path and never spells a
        field name: the key a level dict holds is the field the path names, the same rule as `parse_bgp`.

        A PAN-OS export states the area type as a flag element inside `type`, so the report value is the
        flag's tag and the mapping for this level is the identity. The fields of the chosen body live inside
        that body, so the chosen element is the holder `_protocol_choice` reads. F7.4 adds the two shapes the
        body holds: the `default_route` choice, and the entries of `nssa_ext_range`.

        An entry that prints inside the area is the entry this method reads: a `range` entry, a
        `virtual_link` entry, a `neighbor` entry, or an `nssa_ext_range` entry. The provider requires exactly
        one of the alternatives a presence choice states, so an entry that states none cannot be expressed.
        The same rule as `parse_bgp`: an entry the `.tf` cannot express is marked for the report and is not
        put in the printed list. A `default_route` is not an entry, so the report names the entry that holds
        it, which is the area entry.
        """
        level = self._protocol_level(container, base)
        area_path, range_path = f'{base}/area', f'{base}/area/range'
        type_path, interface_path = f'{area_path}/type', f'{area_path}/interface'
        link_path, neighbor_path = f'{area_path}/virtual_link', f'{interface_path}/neighbor'
        for area in container.findall('.//area/entry'):
            name = area.get('name')
            if not name:
                continue
            captured = self._protocol_level(area, area_path)
            field = self._protocol_field_name(type_path)
            type_element = area.find(self._protocol_xml_name(field))
            body = type_element[0] if type_element is not None and len(type_element) else None
            value = body.tag if body is not None else ''
            choice, detail = self._protocol_choice(type_path, value, type_element, body)
            captured[field] = choice
            key = resource_mapping.protocol_row(type_path)['selects'].get(value, '')
            if key:
                detail = detail or self._protocol_body(f'{type_path}/{key}', body, choice[value])
            entry = self.mark(area, captured, detail, destination='report' if detail else None)
            if detail:
                continue
            level[self._protocol_field_name(area_path)].append(entry)
            for path, entries in ((range_path, area.findall('.//range/entry')),
                                  (link_path, area.findall('.//virtual-link/entry'))):
                self._protocol_entries(path, entry[self._protocol_field_name(path)], entries)
            for iface in area.findall('./interface/entry'):
                if not iface.get('name'):
                    continue
                captured_iface, reason = self._protocol_interface(iface, base)
                marked = self.mark(iface, captured_iface, reason, destination='report' if reason else None)
                if not reason:
                    entry[self._protocol_field_name(interface_path)].append(marked)
                    self._protocol_entries(neighbor_path, marked[self._protocol_field_name(neighbor_path)],
                                           iface.findall('./neighbor/entry'))
        return level

    def _protocol_branch(self, base: str, level: dict, element: ET.Element, path: str) -> None:
        """Fill one entry level that lives inside a level dict (F7.6).

        `level` is the dict `_protocol_level` read for `base`, and `path` is the table path of the entry level.
        The segments between them are the field names the rows declare, so this rule states no field name of
        its own: it walks the dict through them, and walks the XML through the same segments to the element
        that holds the entries. `_protocol_entries` then marks each entry and puts it in the list the last
        segment names. A `member_list` field holds values and not entries, so it is read by `_protocol_level`
        and never reaches this rule.
        """
        segments = path[len(base) + 1:].split('/')
        holder, source = level, element
        for segment in segments[:-1]:
            holder = holder[self._protocol_field_name(segment)]
            source = source.find(self._protocol_xml_name(segment))
            if source is None:
                return
        entries = source.findall(f'./{self._protocol_xml_name(segments[-1])}/entry')
        self._protocol_entries(path, holder[self._protocol_field_name(path)], entries)

    def _protocol_entry_level(self, router: ET.Element, path: str) -> list:
        """The entries of one entry level that the `protocol` row states as a field (F7.10).

        `path` is the table path, so the caller states a path and no field name: the element it reads is the
        element the last segment names, and the entries go through `_protocol_entries`, the same rule the routing
        methods use. An entry level inside a level dict reaches this rule through `_protocol_branch`; a level the
        row states as an object is read by `_protocol_level`, because its entries live under the element the field
        names.
        """
        field = self._protocol_field_name(path)
        container = router.find(f'{resource_mapping.PROTOCOL_FIELD}/{self._protocol_xml_name(field)}')
        if container is None:
            return []
        entries: list = []
        self._protocol_entries(path, entries, container.findall('./entry'))
        return entries

    def _protocol_entries(self, path: str, holder: list, entries,
                         table: Optional[resource_mapping.ShapeTable] = None) -> None:
        """The entries of a `string_list` level, marked and put in the list that holds them (F7.4, F7.5).

        `holder` is the list the field the path names holds in the object that owns it, so the caller states
        the path once and this method never spells a field name. An entry fills the two shapes a level dict
        cannot hold: the choice it states inside itself, which is a `one_of` field the row declares, and its
        `block` fields. The provider requires exactly one alternative, so an entry that states none has no
        `.tf` shape: it is marked for the report and not put in the printed list, the same rule as
        `parse_bgp`.
        """
        table = table or resource_mapping.PROTOCOL_TABLE
        for entry in entries:
            if not entry.get('name'):
                continue
            captured = self._protocol_level(entry, path, True, table)
            reason = (self._protocol_body(path, entry, captured, table)
                      or self._protocol_presence_fields(path, captured, table))
            marked = self.mark(entry, captured, reason, destination='report' if reason else None)
            if not reason:
                holder.append(marked)

    def _protocol_body(self, path: str, body: ET.Element, fields: dict,
                         table: Optional[resource_mapping.ShapeTable] = None) -> str:
        """The shapes inside a level that a level dict cannot hold (F7.4, F7.5, F7.6).

        `_protocol_level` read the level's fields, so a `one_of` field is the choice it read from the element
        and a `string_list` field is the empty list it states. This fills the three: the choice the export
        states by presence under the level, the entries the export holds under it, and the entries under an
        `object` field, because a level dict is not an entry and the export holds its entries under the element
        the field names. `body` is the element that holds them, which is the chosen flag element for an area
        type and the entry itself for an interface entry. The provider requires exactly one of the alternatives,
        so a level that states none prints nothing, and the detail the mapping cannot state is captured here
        because the entry is the object the ledger marks. A `member_list` field and a `block` field hold no
        entries, so `_protocol_level` reads them and this rule states nothing for them.
        """
        table = table or resource_mapping.PROTOCOL_TABLE
        detail = ''
        for field, shape in table.row(path)['fields'].items():
            element = body.find(self._protocol_xml_name(field, path, table))
            if element is None:
                continue
            entry_path = f'{path}/{field}'
            if shape == 'one_of':
                fields[field], reason = self._protocol_presence_choice(entry_path, element)
                detail = detail or reason
            elif shape == 'string_list':
                # The entries a level holds are its own children, so an entry inside an entry belongs to the
                # level that names it and not to the one above it (F7.6).
                self._protocol_entries(entry_path, fields[field], element.findall('./entry'), table)
            elif shape == 'object':
                # F7.6: a level dict is not an entry, so the entries a `string_list` field holds live under the
                # element this field names. The same rule fills them, through the path the field names.
                self._protocol_body(entry_path, element, fields[field], table)
        return detail

    def _protocol_presence_choice(self, path: str, element: ET.Element,
                         table: Optional[resource_mapping.ShapeTable] = None) -> tuple:
        """The one key a `one_of` level states when the export states the level by presence (F7.4, F7.5).

        The export holds the choice as the element under the level, so the value is that element's tag and
        the holder is that element: `advertise` or `no` for a default route. `selects` is the one lookup, so
        the key the print uses is the key the row selects for the value, not the tag the export states. A
        level element with no child states none of the alternatives the provider requires, so the mapping
        cannot state a key for it and the caller marks the entry with that reason.
        """
        table = table or resource_mapping.PROTOCOL_TABLE
        child = element[0] if len(element) else None
        return self._protocol_choice(path, child.tag if child is not None else '', element, child)

    def _protocol_presence_fields(self, path: str, captured: dict,
                         table: Optional[resource_mapping.ShapeTable] = None) -> str:
        """The reason an entry that states a presence choice states none of its alternatives (F7.1, F7.4).

        The provider requires exactly one, so the alternatives are the `block` fields the row states: the
        rule reads the table, and a `range` entry and an `nssa_ext_range` entry are the same shape. A level
        the table states no `block` field for states no required choice, so it has no reason.
        """
        table = table or resource_mapping.PROTOCOL_TABLE
        alternatives = [f for f, shape in table.row(path)['fields'].items()
                        if shape == 'block']
        if not alternatives:
            return ''
        return '' if any(captured[f] for f in alternatives) else 'no ' + ' or '.join(alternatives)

    def _protocol_interface(self, iface: ET.Element, base: str,
                         table: Optional[resource_mapping.ShapeTable] = None) -> tuple:
        """One interface entry, read as the shape table names its fields (F7.1, F7.2).

        The provider declares an interface only inside an area, so the area-interface row is the only
        interface shape row for a routing level, and an interface the export places at the level itself is
        read through the same row and then reported. `detail` is the reason the entry cannot be printed,
        which is empty for a link type the mapping states.
        """
        table = table or resource_mapping.PROTOCOL_TABLE
        path = f'{base}/area/interface'
        field = self._protocol_field_name(f'{path}/link_type', table)
        captured = self._protocol_level(iface, path)
        choice, detail = self._protocol_choice(f'{path}/{field}',
                                               self._get_text(iface, self._protocol_xml_name(field, table)),
                                               iface, iface, table)
        captured[field] = choice
        return captured, detail

    @staticmethod
    def _protocol_field_name(path: str, table: Optional[resource_mapping.ShapeTable] = None) -> str:
        """The field name a `PROTOCOL_SHAPE` path names, which is the last part of the path (F7.1).

        The parse methods state a level as a path, so the key they write is the field the path names: the
        captured dict and the printed dict hold the table's names, not a spelling of their own.
        """
        return (table or resource_mapping.PROTOCOL_TABLE).field_name(path)

    def _protocol_choice(self, path: str, report_value: str, level: Optional[ET.Element],
                         holder: Optional[ET.Element],
                         table: Optional[resource_mapping.ShapeTable] = None) -> tuple:
        """The one key a `one_of` level states, as `({the report value: the alternative's value}, detail)` (F7.1).

        `level` is the element the choice lives under and `holder` is the element the alternative's fields live
        in, because the export puts them at the entry's own level for a BGP peer group and inside the chosen
        element for an area type. F7.6: the alternatives are the attributes the row states, so an alternative
        can be a value instead of a level. When the row states it as a field, the field reader reads it from
        `level`, and when the row states it as a level, the level reader reads it from `holder`. `detail` is the
        reason the mapping cannot state the value, which is empty for a value it can state: the caller marks
        the entry for the report with it, because a one-of level with no key prints nothing.
        """
        table = table or resource_mapping.PROTOCOL_TABLE
        row = table.row(path)
        chosen = row['selects'].get(report_value, '')
        if not chosen:
            name = self._protocol_field_name(path, table)
            return {report_value: {}}, (
                f'{name} {report_value} is not a value PROTOCOL_SHAPE states' if report_value
                else f'{name} states no key PROTOCOL_SHAPE selects')
        if chosen in row['fields']:
            field = self._protocol_field_name(f'{path}/{chosen}', table)
            return ({report_value: self._protocol_field(level, field, self._protocol_xml_name(field, table),
                                                        row['fields'][chosen])}, '')
        return ({report_value: self._protocol_level(holder, f'{path}/{chosen}', False, table)}, '')

    def _protocol_level(self, entry: Optional[ET.Element], path: str, facts: bool = True,
                         table: Optional[resource_mapping.ShapeTable] = None) -> dict:
        """Read one protocol level as `PROTOCOL_SHAPE` names its fields (F7.1).

        The shape table is the only thing that states a level's fields and shapes, so the emitter, the gate
        rule and the property scan read the same names. A `string_list` level is filled by the caller,
        because the entries it holds are decided there. A `one_of` field is read here when the row states its
        alternatives as fields; a row that states no field is left to the caller, because the alternative is a
        level the export states by presence and the caller reports the entry that states none.

        `facts` is the five scope facts. They belong to the object the ledger marks, which is the entry
        level, so a level read for a choice body or for a child element is read without them.
        """
        table = table or resource_mapping.PROTOCOL_TABLE
        row = table.row(path)
        if row['shape'] == 'block':
            # A `block` level states no field, so the value is the empty object the export stated by
            # presence, the same rule as a `block` field (F7.1).
            return HclRef('{}')
        level = {}
        for field, shape in row['fields'].items():
            if shape == 'string_list':
                level[field] = []
            elif shape == 'one_of':
                sub = resource_mapping.protocol_row(f'{path}/{field}')
                if sub['fields']:
                    # F7.6: the row states its alternatives as its own fields, so the level reads the one the
                    # element holds. A row that states no field leaves the choice to the caller, because the
                    # alternative there is a level the export states by presence.
                    element = entry.find(self._protocol_xml_name(field, path, table)) if entry is not None else None
                    level[field] = self._protocol_presence_choice(f'{path}/{field}', element, table)[0] \
                        if element is not None else {}
                else:
                    level[field] = {}
            elif shape == 'object':
                child = entry.find(self._protocol_xml_name(field, path, table)) if entry is not None else None
                level[field] = self._protocol_level(child, f'{path}/{field}', True, table)
            else:
                level[field] = self._protocol_field(entry, field, self._protocol_xml_name(field, path, table), shape)
        if facts and entry is not None and entry.tag == 'entry':
            # F3.10: a protocol entry is an object the ledger records, so it carries the five scope facts
            # of the router that holds it. A container level (`bgp`, `ospf`) is not an entry, and the
            # emitter places only the router, so that level holds no facts.
            level.update(self.identity_of(entry))
        return level

    @staticmethod
    def _protocol_xml_name(field: str, path: str = '',
                         table: Optional[resource_mapping.ShapeTable] = None) -> str:
        """The XML element name for a `PROTOCOL_SHAPE` field name (F7.1).

        A PAN-OS export spells a field with `-` where the provider schema spells it with `_`, so the shape
        table states the provider spelling and this is the one rule that turns it into the element name. The
        one exception is `resource_mapping.XML_NAME_EXCEPTIONS`, because the provider splits an initialism the
        export does not (F7.3).
        """
        return (table or resource_mapping.PROTOCOL_TABLE).xml_name(field, path)

    def _protocol_field(self, entry: ET.Element, field: str, xml_name: str, shape: str):
        """One protocol field, read as the shape table states it (F7.1)."""
        if entry is None:
            return ''
        if field == 'name':
            # The entry name inside a list element is the entry's own `name` (F7.1 rule 1).
            return entry.get('name') or ''
        node = entry.find(xml_name)
        text = (node.text or '') if node is not None else ''
        if shape == 'bool':
            if node is None:
                # The export states a flag by its presence, so an element that is not there is no value:
                # the field prints nothing, and the gate sees no field to check.
                return ''
            # A presence element with no text is the flag being set, which is the shape a PAN-OS export
            # uses for `accept-summary`.
            return text == 'yes' or not text
        if shape == 'number':
            return int(text) if text.isdigit() else ''
        if shape == 'block':
            # Presence is the value: the provider reads an empty block as the export having stated it, so
            # the field prints `{}` when the element is there and prints nothing when it is not (F7.1).
            return HclRef('{}') if node is not None else ''
        if shape == 'member_list':
            # The provider declares this field as `['list', 'string']`, so the value is the members the element
            # holds: there is no entry and no level row for a member (F7.6).
            return [(member.text or '').strip() for member in node.findall('member')] if node is not None else []
        return text

    def parse_filter_containers(self) -> dict:
        """Read the six routing-profile filter containers (F7.8).

        The six paths are the six `CONTAINER_TABLE` rows, which are the entry rows of `FILTER_SHAPE`. Each
        entry is the object one resource block prints, so it carries the five scope facts and is marked here
        (F4.3 rule 1). The levels inside an entry are read through the table, so this method states the paths
        and no field name (F7.1 rule).

        The return is `{container path: the entries it holds}`, in the order `FILTER_PATHS` states, so
        `tests/test_multi_vsys_location.py` sees every entry the method read.
        """
        table = resource_mapping.FILTER_TABLE
        containers = {}
        for path in ('network/routing-profile/filters/access-list',
                     'network/routing-profile/filters/as-path-access-list',
                     'network/routing-profile/filters/prefix-list',
                     'network/routing-profile/filters/community-list',
                     'network/routing-profile/filters/route-maps/bgp/bgp-entry',
                     'network/routing-profile/filters/route-maps/redistribution/redist-entry'):
            entries = []
            for container in self.root.findall(f'.//{path}'):
                for entry in container.findall('./entry'):
                    if not entry.get('name'):
                        self.mark_skipped(entry, 'entry has no name attribute')
                        continue
                    captured = self._protocol_level(entry, path, True, table)
                    self._protocol_body(path, entry, captured, table)
                    entries.append(self.mark(entry, captured))
            containers[path] = entries
        return containers

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

    def _get_single_value(self, element: ET.Element, path: str) -> str | list[str] | None:
        """Read a field the provider holds as one value, in either export form.

        The export states such a field as text or as a member list. `_get_text` answers the
        whitespace between the element and its members for the member form, so this helper takes
        the members when the element holds them. One member is the value the field can hold; more
        than one is the set it cannot hold, so the parse keeps the list and the emitter prints the
        `# NOTE:` line that names it (F2.9: never a silent drop).
        """
        elem = element.find(path)
        if elem is None:
            return None
        members = [member.text for member in elem.findall('member') if member.text]
        if not members:
            return elem.text
        return members[0] if len(members) == 1 else members


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

# F5.5: every scope a reference site resolves a name against. A read-through
# `data` block exists to answer a name a reference needs, so `--data-blocks`
# accepts a scope from this set only, and only a scope whose `DATA_SOURCE_SCHEMA`
# row declares `name`: a data source with no `name` attribute cannot hold the
# entry name a reference needs. tests/test_data_blocks.py pins both rules.
REFERENCE_SCOPES = tuple(sorted({
    *ADDR_SCOPES, *SERVICE_SCOPES, *ZONE_SCOPES, *INTERFACE_SCOPES, *IFACE_SCOPES,
    *TAG_SCOPES, *IKE_CRYPTO_SCOPES, *IPSEC_CRYPTO_SCOPES, *IKE_GATEWAY_SCOPES,
}))

# F4.4: the field order the manual report line states for an application override rule, which is the
# order the report already used for the fields it printed. The report is the only output for this
# container, so the line prints the fields it reads through the captured object, in this order, and a
# field the entry carries no value for prints nothing (F4.3 rule 3). `port` and `protocol` are the two
# fields whose empty value the report prints as `any`, because an export that states no value for them
# means any port or any protocol.
OVERRIDE_REPORT_FIELDS = (
    ('from', 'source_zones'),
    ('to', 'destination_zones'),
    ('source', 'source_addresses'),
    ('destination', 'destination_addresses'),
    ('port', 'port'),
    ('protocol', 'protocol'),
    ('application', 'application'),
    ('disabled', 'disabled'),
    ('description', 'description'),
)


class UnitText:
    """One `.tf` file's text, held per unit directory (F6.10.3, `docs/CODEBASE_ASSEMBLY.md` §14).

    A per-unit file names its unit only by its directory, so this class puts no unit inside a file: the
    unit is read through `unit_manifest.facts_of` at the site that built the block, and the path is the
    only place a file states the unit it belongs to. `header` is the text the file states once, so it is
    the start of each unit's text. `write` writes one file per unit that has content, through the one
    write path, in the order the run read that unit's blocks.
    """

    def __init__(self, generator: 'TerraformGenerator', name: str, header: str = ''):
        self.generator = generator
        self.name = name
        self.header = header
        self._text: dict[str, str] = {}

    def add(self, entry, text: str) -> None:
        """One piece of the text, for the unit `entry` belongs to, in the order the run read it.

        `entry` is the parsed entry, or the five scope facts of the unit when the text names no entry.
        """
        facts = entry if isinstance(entry, tuple) else unit_manifest.facts_of(entry)
        directory = self.generator.directory_of(facts)
        self._text[directory] = self._text.get(directory, self.header) + text

    def add_once(self, entry, text: str) -> None:
        """Text a file states once per unit, which is what a section header is (F6.10.3)."""
        facts = entry if isinstance(entry, tuple) else unit_manifest.facts_of(entry)
        directory = self.generator.directory_of(facts)
        if text not in self._text.setdefault(directory, self.header):
            self._text[directory] += text

    def write(self) -> None:
        """Write the file for every unit that has content, in the order the manifest rows print."""
        for directory in sorted(self._text):
            self.generator.write_unit_file(directory, self.name, self._text[directory])


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

    def __init__(self, output_dir: str, associations: Optional[dict] = None,
                 data_scopes: Optional[frozenset] = None, ledger=None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): the run's unit set is the ledger's rows, read
        # through `unit_manifest.units`, so the directories the run writes are the units rule 1 names.
        self._ledger = ledger
        # Collision handling for block names. Two different PAN-OS names
        # can sanitize to the same Terraform name (for example 'a-b' and
        # 'a_b'), so the counter keeps the output valid HCL.
        self._taken_names: dict[str, set[str]] = {}
        # F6.10.2: the declaration index, keyed by the identity the naming rule applied (scope, name).
        # Each entry maps the unit that declared the name, read through `unit_manifest.facts_of`, to the
        # local name, so the reference rule resolves a name inside the referrer's own unit and can tell a
        # name another unit declared from a name no unit declares (`docs/CODEBASE_ASSEMBLY.md` §5 rule 5).
        # A `data` block enters no index, because a reference site creates it and a plain reference must
        # not resolve to it (F5.5).
        self._declaration_index: dict[tuple, dict] = {}
        # F3.5: (kind, line) pairs for a source scope the emitted location
        # cannot carry ('scope') and for a vsys location with no target
        # device name ('device'). generate_manual_setup_report writes them.
        self._location_reports: list[tuple[str, str]] = []
        # F3.6: the device membership the export declares
        # (PanoramaParser.parse_associations). A template-scoped entry the
        # export leaves unplaced is reported with the templates its device
        # takes, so the operator sets the real name.
        self._associations: dict = associations or {}
        # F5.5: the read-through scopes the run declares (`--data-blocks`), and the blocks the reference
        # sites needed, keyed by the identity the reference site named: (scope, unit, name). So two sites
        # in one unit that name the same outside name share one block, and a site in another unit writes
        # its own (F6.10.2).
        self.data_scopes = frozenset(data_scopes or ())
        self._data_blocks: dict[tuple, dict] = {}
        # F6.1, F6.10.2: the names the reference rule could not resolve inside the referrer's own
        # unit, keyed by the referrer's five scope facts (`unit_manifest.facts_of`), so the manifest
        # row can state them. One name is stored once per unit.
        self._unit_references: dict[tuple, set] = {}
        # F6.4: one import row per entry a `resource` block declares, recorded at the site that applied the
        # naming rule (`import_blocks.row`). `render` prints them in the order a reader can reproduce.
        self.import_rows: list[dict] = []
        # F6.6: the site values the value-to-variable table mapped, keyed by the unit's five scope facts
        # (`unit_manifest.facts_of`) and recorded at the site that applied the table, so `site_data.py` states
        # them without resolving a name. One value is stored once per unit.
        self._value_variables: dict[tuple, dict] = {}
        # F6.10.4: the shape each recorded name came from, so the declaration file reads the marking through
        # the table and not through a name list. Recorded at the same site as the pair.
        self._value_shapes: dict[tuple, dict] = {}

    def sanitize_name(self, name: str) -> str:
        """Sanitize names for Terraform resource names.

        The rule is `naming.py` (F6.6), because the post-run gate reads it without the generator, so no
        module defines a second shape. Every caller takes this method as the argument the data modules use.
        """
        return naming.sanitize(name)

    # --- The write path (F6.10.3, `docs/CODEBASE_ASSEMBLY.md` §14) ------------
    # `write_path.py` is the one place that writes bytes, and its two builders name the two file sets:
    # the unit set inside the directory the manifest row names, the codebase root set at the root. The
    # generator names the unit only through `unit_manifest`, so it states no unit rule and no directory
    # rule, and a per-unit file names its unit only by its directory.

    def directory_of(self, facts: tuple) -> str:
        """The directory name `unit_manifest.directory_name` gives one unit identity (§5, F6.6)."""
        return unit_manifest.directory_name(facts, self.sanitize_name)

    def unit_directory(self, obj: dict) -> str:
        """The directory the manifest row names for the unit a parsed object belongs to."""
        return self.directory_of(unit_manifest.facts_of(obj))

    def units_of(self, entries: list[dict]) -> list[tuple]:
        """The units the entries belong to, in the identity order `unit_manifest` states."""
        return sorted({unit_manifest.facts_of(entry) for entry in entries})

    def unit_set(self) -> list[tuple]:
        """The run's unit set: the units `unit_manifest.units` names, in identity order.

        A unit exists when the ledger has a row in it, so a generator that reads no ledger names no unit.
        The unit-set files that state no block (`provider.tf` and `variables.tf`) are written for the units
        this rule names, which is why `main()` gives the generator the ledger the parse wrote.
        """
        return unit_manifest.units(self._ledger)

    def write_unit_file(self, directory: str, name: str, content: str) -> None:
        """Write one unit's file through the one write path, and only when it has content.

        A unit that has no block for this file gets no file, which is the rule the emitter already
        states (`if not content`), read per unit instead of per run.
        """
        if not content:
            return
        write_path.write_file(write_path.unit_path(self.output_dir, directory, name), content)

    def write_root_file(self, name: str, content: str) -> None:
        """Write one codebase root-set file through the one write path, and only when it has content."""
        if not content:
            return
        write_path.write_file(write_path.root_path(self.output_dir, name), content)

    def declare_resource_name(self, name: str, scope: str, obj: dict,
                              context: str = '', vsys: str = '') -> str:
        """Assign a collision-free name for a `resource` declaration (F2.7)."""
        return self.declare_block_name(name, scope, obj, context, vsys)

    def declare_block_name(self, name: str, scope: str, obj: dict,
                           context: str = '', vsys: str = '',
                           kind: str = 'resource') -> str:
        """Assign a collision-free Terraform name for a new block declaration.

        One name rule for both block kinds (F5.5): a read-through `data` block
        takes the name the object would have had as a `resource`, so a run that
        declares no read-through scope writes the same bytes as before.

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

        For a `data` block the entry is not in the export, so the source identity is the unit the
        reference site belongs to (F6.10.2), read through `unit_manifest.identity_digest`.

        If the address is already taken in the scope (a duplicate declaration
        or a digest collision), a numeric suffix follows, so the output is
        always valid HCL.

        F3.1: `context` is the defining device group ('Shared' for shared
        objects) or template. F3.2: `vsys` completes the identity key
        (device group, vsys, type, name) recorded by the parser, so
        same-named objects in different vsys get different digests and both
        survive without the taken-name counter.

        F3.6: a template-scoped object passes its template, else the device
        the export placed it under (TerraformGenerator.scope_context), so
        the same interface name on two firewalls stays two resources instead
        of one resource plus a taken-name counter.

        `obj` is the parsed object the declaration belongs to, so the declaring unit is recorded here, at
        the site that applied the naming rule, through `unit_manifest.facts_of` — the same read
        `record_import_row` makes. The reference rule reads the declaring unit from this record, so no
        second unit rule and no second naming key exists.
        """
        base = self.sanitize_name(name) or 'unnamed'
        unit = unit_manifest.facts_of(obj)
        identity = f'{context}|{vsys}' if kind == 'resource' else unit_manifest.identity_digest(unit)
        digest = hashlib.sha256(f'{scope}|{identity}|{name}'.encode()).hexdigest()[:8]
        candidate = f'{base}_{digest}'
        taken = self._taken_names.setdefault(scope, set())
        n = 2
        while candidate in taken:
            candidate = f'{base}_{digest}_{n}'
            n += 1
        taken.add(candidate)
        if kind == 'data':
            # A `data` block is created by a reference site, not by a parsed
            # entry, so it enters no declaration index: a plain reference must
            # not resolve to it, and a `data.` reference resolves only to the
            # block the same identity created (F5.5).
            return candidate
        # One local name per unit that declared the name, and the first declaration of one identity wins.
        # The reference rule reads the referrer's own unit here (F6.10.2).
        self._declaration_index.setdefault((scope, name), {}).setdefault(unit, candidate)
        return candidate

    def name_ref(self, name: str, scopes, referrer: dict, key: Optional[str] = None):
        """Apply the reference rule for one unit (F6.10.2) and record what it resolved outside it (F6.1).

        `referrer` is the parsed object the reference site belongs to, so the rule reads the unit through
        `unit_manifest.facts_of` and no second unit rule exists. A name the rule resolved outside the
        referrer's unit is recorded against the referrer's five scope facts, so the manifest row can state
        the names a unit references from outside itself (`unit_manifest.py`). The record is made here, at
        the site that applies the rule, so no second resolution rule exists. Every call site passes the
        object it belongs to, so a name is never recorded twice, and a call site names no context, no vsys
        and no device, because the referrer states them.
        """
        resolved = self._resolve_reference(name, scopes, referrer, key=key)
        if self._is_outside_reference(resolved):
            self._unit_references.setdefault(unit_manifest.facts_of(referrer), set()).add(name)
        return resolved

    @staticmethod
    def _is_outside_reference(resolved) -> bool:
        """True when the rule resolved the name to something outside the unit that asked for it: a plain
        string, or a read-through `data` block (F5.5). A name the referrer's own unit declares resolves to a
        `resource` block inside the unit, so it is not an outside name. The edge list (F6.3) is the feature
        that names the other unit, so this record keeps one fact: the name is outside the unit, which for one
        unit is outside the run.
        """
        if isinstance(resolved, str):
            return True
        return isinstance(resolved, HclRef) and resolved.expr.startswith('data.')

    def unit_references(self) -> dict:
        """The recorded reference names, keyed by the referrer's five scope facts, in sorted order."""
        return {facts: tuple(sorted(names)) for facts, names in self._unit_references.items()}

    def value_variables(self) -> dict:
        """The recorded site values, keyed by the unit's five scope facts, in name order (F6.6).

        Recorded at the site that applied the value-to-variable table, so `site_data.py` can state the row
        without resolving a name, and `generate_variables` declares exactly the values the run printed.
        """
        return {facts: {name: values[name] for name in sorted(values) if values[name] is not None}
                for facts, values in self._value_variables.items()}

    def value_shapes(self) -> dict:
        """The recorded shapes, keyed by the unit's five scope facts, in name order (F6.10.4).

        A name the run holds with no value is read through this record, so the declaration file and a test can
        tell a `reference_only` name from an `operator_supplied` one without naming the fields again.
        """
        return {facts: {name: shapes[name] for name in sorted(shapes)}
                for facts, shapes in self._value_shapes.items()}

    def record_import_row(self, resource_type: str, obj: dict, local_name: str, location: dict) -> None:
        """Record the import row for one entry, at the site that applied the naming rule (F6.4).

        The row states only facts the resource block already states: the type, the local name the naming rule
        gave, the entry name the block writes, and the location `location_data` built. The unit is the
        `unit_manifest` identity, read through `facts_of`, so no second identity key appears.
        """
        unit = unit_manifest.directory_name(unit_manifest.facts_of(obj), self.sanitize_name)
        self.import_rows.append(import_blocks.row(
            unit, resource_type, local_name, obj.get('name') or '', location))

    def _resolve_reference(self, name: str, scopes, referrer: dict,
                           key: Optional[str] = None):
        """Resolve a PAN-OS name inside one unit (F2.6, F6.10.2).

        Returns an HclRef of '<scope>.<local>.name' when the referrer's own unit declares the name, else
        the plain name. `scopes` is tried in order so an object wins over a group when both carry the same
        name. `key` is the registry key when it differs from the PAN-OS name (VPN composite keys such as
        'ike_gw_<name>').

        Order, first match wins:

        1. A name the referrer's own unit declares.
        2. A name another unit in the run declares: the plain name. One plan runs against one root and one
           state, so a reference cannot name an address another unit declares, and the value the provider
           reads is the name itself, which Panorama resolves through its own inheritance at commit time
           (`docs/CODEBASE_ASSEMBLY.md` §5 rule 5).
        3. A name no unit in the run declares, when the run declares one of the scopes with
           `--data-blocks`: one read-through `data` block, and the reference is `data.<scope>.<local>.name`
           (F5.5). The read-through branch answers a name outside the codebase, so it does not run for a
           name one unit declares and another unit uses. The block type is the first opted-in scope in this
           site's lookup order, which is the order PAN-OS resolves a name in, and the block is the one
           written for this site's identity (scope, unit, name), so a second site in one unit shares it and
           a site in another unit writes its own.
        4. Otherwise the plain name.

        A name a device declared is one case of this rule: an interface is declared inside the device unit,
        so a referrer outside that unit keeps the plain name (F3.5, F3.6). The rule reads the referrer's
        unit through `unit_manifest.facts_of` and the declaring unit through the record `declare_block_name`
        made, so no second unit rule and no second reference rule exists.
        """
        lookup = key if key is not None else name
        unit = unit_manifest.facts_of(referrer)
        for scope in scopes:
            local = self._declaration_index.get((scope, lookup), {}).get(unit)
            if local is not None:
                return HclRef(f'{scope}.{local}.name')
        # 2. The name is declared, but by another unit, so it is not reachable from this one.
        if any(self._declaration_index.get((scope, lookup)) for scope in scopes):
            return name
        # 3. the read-through branch.
        for scope in scopes:
            if scope not in self.data_scopes:
                continue
            block = self._data_blocks.get((scope, unit, lookup))
            if block is None:
                local = self.declare_block_name(name, scope, referrer, kind='data')
                block = self._data_blocks[(scope, unit, lookup)] = {
                    'type': scope,
                    'local': local,
                    'name': name,
                    # F6.10.3: the block is written in the unit it names, so the writer needs the facts.
                    'unit': unit,
                    # The location the referrer's unit names: one location rule (`location_block`), and the
                    # tool does not guess which scope holds a name outside the run (F5.5).
                    'location': self.location_block(scope, {**referrer, 'name': name}),
                }
            return HclRef(f'data.{scope}.{block["local"]}.name')
        # 4.
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

    # Provider v2 requires a location block on every resource. A type is template-scoped when its
    # schema location declares no device_group sub-block (F3.5: derived from LOCATION_SCHEMA, not a
    # hand-kept list). The six scope types are not scoped objects: they are the scopes, so they are
    # not template-scoped, and the `panorama` sub-block is their own place (F6.5).
    _TEMPLATE_SCOPED_TYPES = frozenset(
        t for t, scopes in LOCATION_SCHEMA.items()
        if 'device_group' not in scopes and t not in SCOPE_TYPES)

    # Template-scoped resource the export places in no template and on no
    # named device (F3.6). The name is a guess, so location_block reports
    # every resource that uses it, with the templates the entry's device
    # does take.
    _TEMPLATE_PLACEHOLDER = 'Shared'

    # PAN-OS writes this device entry name for "this device" (Panorama
    # itself, or a firewall's own config export). It names no firewall, so
    # it cannot go into `ngfw_device` (F3.5). The one definition is
    # `container_coverage.PLACEHOLDER_DEVICE`, which the state scan reads too (F5.6).
    _LOCAL_DEVICE_PLACEHOLDER = container_coverage.PLACEHOLDER_DEVICE

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

    def location_data(self, resource_type: str, obj: dict) -> dict:
        """The location as data: {sub-block: {field: value}}, in the order the block prints it (F6.4).

        One location rule. `location_block` renders from it, and `import_blocks.row` encodes from it, so the
        resource block and the import id cannot state two different locations. The field order is the order the
        block prints, so the goldens keep their bytes.
        """
        scopes = LOCATION_SCHEMA[resource_type]
        vsys = (obj.get('vsys') or '').strip()
        template = (obj.get('template') or '').strip()
        device = (obj.get('vsys_device') or '').strip()
        group = (obj.get('device_group') or '').strip()
        where = self._location_source_text(obj)

        def keep(scope: str, fields: dict) -> dict:
            """Keep only the fields the sub-block declares, in the order it was given."""
            return {k: v for k, v in fields.items() if k in scopes[scope]}

        # 0. Scope placement (F6.5): a scope object is placed in the scope the export puts it in,
        #    or at the top of its own chain. The four Panorama scopes place themselves, and the
        #    codebase states no device fact in a location, so the sub-block prints empty, the shape
        #    `shared = {}` already uses. A variable and a virtual system place inside a template or
        #    a template stack, and an entry the export places in neither is reported by the parse
        #    as skipped, so it reaches no block here. Branch 4 would report a device group as
        #    "device group dropped", which is wrong for the object that defines the group.
        if resource_type in SCOPE_TYPES:
            key = next((k for k in SCOPE_PLACEMENT[resource_type] if obj.get(k)), '')
            if not key:
                return {'panorama': {}}
            return {key: keep(key, {'name': obj.get(key)})}

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
            return {'vsys': keep('vsys', fields)}

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
            return {'template': keep('template', fields)}

        # 3. Device-specific placement (F3.6). The export put the entry under
        #    devices/entry/<device>/network, so it is that firewall's own
        #    config and not a template's. Provider v2 places it with
        #    location.ngfw ("Located in a specific NGFW device"). Only the
        #    template-scoped types declare it: objects live in a virtual
        #    system and take branch 1.
        if device and device != self._LOCAL_DEVICE_PLACEHOLDER and 'ngfw' in scopes:
            return {'ngfw': keep('ngfw', {'ngfw_device': device})}

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
                return {'device_group': {'name': group}}
            if 'shared' in scopes:
                # The export defines the entry under <shared>. The schema
                # calls that location `shared`; a device group named
                # "Shared" is a different object that does not exist
                # (F3.5).
                return {'shared': {}}
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
            return {}
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
        return {'template': {'name': self._TEMPLATE_PLACEHOLDER}}

    def printed_value(self, key: str, value: str, facts: tuple) -> str:
        """Print one field as `VALUE_VARIABLES` says, and record the pair (F6.6, F7.1, F6.10.4).

        `VALUE_VARIABLES` is the only place that decides the shape, so the emitter has no per-type branch.
        The pair is recorded at the site that applies the rule, the way `name_ref` records a reference
        name, so the site data states the values the run printed and the gate rule `variables` cannot see
        a declaration with no consumer. `localhost.localdomain` never reaches a location (F3.5), so it
        never reaches this method and names no variable.

        A field the table states as `reference_only` is a value the provider marks `sensitive`: no
        generated file may state it, so the run records the name with no value, and the `.tfvars` writer
        writes no line for it. The name is the §5 name of the entry, because a secret cannot name itself.

        A field the table states as `operator_supplied` is a fact the tool cannot read: `target` is that
        row, because the export states a device as a hostname and no serial reaches the parse (F6.10.4). The
        run records the name with no value, so no site row and no `.tfvars` line is written for it, and the
        operator supplies the value in `terraform.tfvars` (§11). The name is the §5 rule applied to the field,
        because there is no value to name it from.
        """
        shape = resource_mapping.VALUE_VARIABLES.get(key)
        if shape not in (resource_mapping.VARIABLE, resource_mapping.REFERENCE_ONLY,
                         resource_mapping.OPERATOR_SUPPLIED):
            return self.escape_string(value)
        # A name the run holds no value for is named by the entry (F7.1) or by the field (F6.10.4), because a
        # value cannot name itself and an unread fact has no value.
        name = naming.variable_name(key if shape == resource_mapping.OPERATOR_SUPPLIED else value)
        self._value_variables.setdefault(facts, {})[name] = value if shape == resource_mapping.VARIABLE else None
        self._value_shapes.setdefault(facts, {})[name] = shape
        return naming.variable_text(name)

    def location_field(self, key: str, value: str, obj: dict) -> str:
        """Print one location field as the value-to-variable table says, and record the pair (F6.6).

        The value stays the fact in `location_data`: the import id encodes it, because the provider parses
        the id and a variable name is not a device name.
        """
        return self.printed_value(key, value, unit_manifest.facts_of(obj))

    def location_block(self, resource_type: str, obj: dict, local_name: str = '') -> str:
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

        The block renders from `location_data` and records the import row at the site that applied the naming
        rule (F6.4), so the block and the block's id state one location and one name. Each field prints as the
        value-to-variable table says (F6.6), so the block prints a site value as a `var.` reference while the
        id states the value.
        """
        data = self.location_data(resource_type, obj)
        if local_name:
            self.record_import_row(resource_type, obj, local_name, data)
        if not data:
            return ''
        scope, fields = next(iter(data.items()))
        if not fields:
            # An empty sub-block is the `shared = {}` shape.
            return f'  location = {{\n    {scope} = {{}}\n  }}\n'
        body = ''.join(f'      {k} = {self.location_field(k, v, obj)}\n' for k, v in fields.items())
        return f'  location = {{\n    {scope} = {{\n{body}    }}\n  }}\n'

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

    def _protocol_fields(self, path: str, level: dict, router: dict, entry_name: str = '',
                         table: Optional[resource_mapping.ShapeTable] = None) -> dict:
        """One level of the protocol object, printed in the shape table's order (F7.1).

        `PROTOCOL_SHAPE` is the only thing that states a level's fields and shapes, so the emitter prints
        from it and the gate rule `protocol_object` checks against it. A field with no value prints
        nothing, a `list` level prints one object per element, and a `one_of` level prints the one key the
        mapping states. A field the table marks `sensitive` prints as the variable reference, because no
        generated file may state the value.

        `entry_name` is the name of the entry that holds the level (F7.7). The variable a `sensitive` field
        prints is the one the entry names, so the walk carries the name down: an entry names itself, and a
        level inside an entry has no name of its own, so it prints the reference the entry that holds it names.
        """
        table = table or resource_mapping.PROTOCOL_TABLE
        row = table.row(path)
        if row['shape'] == 'block':
            # A `block` level states no field, so the value the parse read for it is the whole print (F7.1).
            return level
        name = level.get('name') or entry_name or ''
        printed = {}
        for field, shape in row['fields'].items():
            value = level.get(field)
            if value in entry_coverage.EMPTY_FIELD_VALUES:
                continue
            if shape == 'member_list':
                # The value is the members themselves, so there is no element to print as an object and no
                # level row to walk (F7.6).
                out = value
            elif shape == 'string_list':
                out = [self._protocol_fields(f'{path}/{field}', element, router, name, table)
                        for element in value]
            elif shape == 'one_of':
                # The mapping lives on the one_of row for this field, not on the level that holds it.
                sub = resource_mapping.protocol_row(f'{path}/{field}')
                report_value = next(iter(value), '')
                key = sub['selects'].get(report_value, '')
                if not key:
                    out = {}
                elif key in sub['fields']:
                    # F7.6: the alternative is a value the row states, so the reader's value is the print.
                    out = {key: value[report_value]}
                else:
                    out = ({key: self._protocol_fields(f'{path}/{field}/{key}', value[report_value], router,
                                                       name, table)})
            elif shape == 'object':
                out = self._protocol_fields(f'{path}/{field}', value, router, name, table)
            elif resource_mapping.VALUE_VARIABLES.get(field) == resource_mapping.REFERENCE_ONLY:
                out = HclRef(self.printed_value(field, name, unit_manifest.facts_of(router)))
            else:
                out = value
            # A level that printed nothing prints nothing, so the block states no empty field.
            if out in entry_coverage.EMPTY_FIELD_VALUES:
                continue
            printed[field] = out
        return printed

    def generate_filter_containers(self, containers: dict) -> None:
        """Generate the six filter containers (F7.8): one `filters.tf` block per entry.

        `FILTER_SHAPE` states the fields and the shapes, so the block prints exactly what the entry row
        declares, in the table's order, and the gate rule `filter_blocks` checks the same names. The resource
        type is the one `CONTAINER_TABLE` names in the row note, reached through `FILTER_TYPES`.
        """
        out = UnitText(self, 'filters.tf', '# Routing-profile filter containers (F7.8)\n\n')
        wrote = False
        for path in resource_mapping.FILTER_PATHS:
            for entry in containers.get(path) or []:
                resource = resource_mapping.FILTER_TYPES[path]
                name = entry['name']
                block_name = self.declare_resource_name(name, resource, entry,
                                                        context=self.scope_context(entry),
                                                        vsys=entry.get('vsys') or '')
                out.add(entry, f'resource "{resource}" "{block_name}" {{\n')
                out.add(entry, self.location_block(resource, entry, block_name))
                printed = self._protocol_fields(path, entry, entry, entry['name'],
                                          resource_mapping.FILTER_TABLE)
                for field in sorted(printed, key=lambda key: (key != 'name', key)):
                    out.add(entry, f'  {field} = {self.hcl_value(printed[field])}\n')
                out.add(entry, '}\n\n')
                wrote = True
        if wrote:
            out.write()

    def generate_provider_config(self):
        """Generate `provider.tf` for every unit the run's unit set names (F6.10.3, §14).

        One plan reads one root, so the provider block is a unit-set file: the codebase root set holds no
        `.tf` file. The text states no unit, so the path is the only place the file names the unit.

        The credential rule (`docs/CODEBASE_ASSEMBLY.md` §11) decides what the block states. The block prints the
        host through the shape table, so the argument name is the §5 rule applied to the `hostname` row, and it
        states no credential argument: the provider reads the key from the environment named by
        `source_fetch.API_KEY_ENV`, so the run declares no credential variable and writes no credential value.
        Measured against the pinned provider,
        every provider-block argument is optional, so a block that states only the facts the run names is complete.

        F6.10.4: the block prints `target` for a unit whose manifest row names a device, because the provider
        reads the serial there (§12). The shape table decides the shape, so the block prints the reference to
        the name the run declares, and the operator supplies the value in `terraform.tfvars` (§11): the export
        states a device as a hostname, so no serial reaches the parse and the tool names no value for it. A unit
        that names no device prints no `target`, because a declaration with no consumer is a finding, and the
        placeholder device names no device (F3.5).
        """
        head = '''# Palo Alto Networks PAN-OS Provider Configuration
# Supported provider range: v2 series, baseline 2.0.14 (the latest 2.x
# release and the version the conformance and validate gates verify).
# Terraform 1.14 minimum: an `action` block is 1.14 syntax (F6.7).
terraform {
  required_version = ">= 1.14"
  required_providers {
    panos = {
      source  = "PaloAltoNetworks/panos"
      version = "~> 2.0.14"
    }
  }
}

provider "panos" {
'''
        for facts in self.unit_set():
            body = head
            # The host is the fact the run names and cannot read, so the block prints the reference to the name
            # the table's `operator_supplied` row gives it (F6.6, §11).
            body += ('  # The Panorama host this unit plans against. The run names the variable and holds no\n'
                     '  # value for it, so the operator supplies it in terraform.tfvars (do not commit that\n'
                     '  # file). The provider reads ' + source_fetch.API_KEY_ENV + ' from the environment, so the\n'
                     '  # block states no key.\n'
                     f'  hostname = {self.printed_value("hostname", "", facts)}\n')
            device = unit_manifest.fact(facts, 'vsys_device')
            if device and device != container_coverage.PLACEHOLDER_DEVICE:
                body += ('  # The NGFW serial for the device this unit plans against. The run names the\n'
                         '  # variable and holds no value for it, so the operator supplies the serial.\n'
                         f'  target = {self.printed_value("target", "", facts)}\n')
            self.write_unit_file(self.directory_of(facts), 'provider.tf', body + '}\n')

    def generate_variables(self):
        """Generate `variables.tf` for every unit the run's unit set names (F6.10.3, §14).

        F2.10: every emitted variable is consumed. The declaration set is what the run named: the site values the
        shape table mapped, the reference-only names, and the facts the tool cannot read (`hostname` and `target`),
        and each is consumed by the provider block in the same unit directory. The old dead `device_group`
        variable is gone: v2 location is derived per resource from the source XML.

        The credential rule (`docs/CODEBASE_ASSEMBLY.md` §11): a credential is never a declared variable, so the
        header states no name list and each description follows its shape word. The provider reads the key from the
        environment, so the run declares nothing for it.

        F6.6: `main()` calls this after the emitters, because the file cannot state a variable the run has not
        consumed. The type is the kind the site data row declares, so a declaration agrees with the value the
        `.tfvars` prints.
        """
        header = (f'# Variables for Palo Alto Configuration\n'
                  '# The run declares the names it names: the site values `site_data.py` maps, the reference-only\n'
                  '# names, and the facts the tool cannot read. Set the values in terraform.tfvars (do not commit\n'
                  '# it) or via the TF_VAR_* environment variables. The run declares no key, because the provider\n'
                  f'# reads {source_fetch.API_KEY_ENV} from the environment (docs/CODEBASE_ASSEMBLY.md §11).\n')
        for facts in self.unit_set():
            recorded = self._value_variables.get(facts) or {}
            # F7.1: a reference-only name is a declaration with no value held for it.
            values = {name: value for name, value in recorded.items() if value is not None}
            content = header
            if values:
                content += (f'# Site values (F6.6): one variable per value `resource_mapping.VALUE_VARIABLES` maps.\n'
                            f'# The values are in {site_data.TFVARS_FILE}, which Terraform loads automatically.\n\n')
                for name in sorted(values):
                    kind = 'list(string)' if isinstance(values[name], list) else 'string'
                    content += (f'variable "{name}" {{\n'
                                f'  description = "Site value (F6.6), read from {site_data.TFVARS_FILE}"\n'
                                f'  type        = {kind}\n'
                                '}\n\n')
            held = {name for name in recorded if recorded[name] is None}
            shapes = self._value_shapes.get(facts) or {}
            for name in sorted(held):
                # F7.1 marks a held name `sensitive` when its table row is `reference_only`; F6.10.4 names a
                # fact the tool cannot read, and neither is a secret, so the marking follows the row. The
                # description states the shape word, so no name list appears in a generated file.
                if shapes.get(name) == resource_mapping.REFERENCE_ONLY:
                    content += (f'variable "{name}" {{\n'
                                f'  description = "Sensitive protocol value (F7.1, F7.7): the reference prints, so no '
                                f'file states the value, and the operator supplies it"\n'
                                f'  type        = string\n'
                                f'  sensitive   = true\n'
                                '}\n\n')
                else:
                    content += (f'variable "{name}" {{\n'
                                f'  description = "A fact the tool cannot read (F6.10.4, docs/CODEBASE_ASSEMBLY.md '
                                f'§11): the run names the variable and the operator supplies the value"\n'
                                f'  type        = string\n'
                                '}\n\n')
            self.write_unit_file(self.directory_of(facts), 'variables.tf', content)

    # F6.5: the scope objects are the unit's file, the way `imports.tf` (F6.4) and
    # `read_through.tf` (F5.5) are unit-set files. Written only when the run has a block.
    SCOPE_FILE = 'scope.tf'

    def generate_scope_objects(self, device_groups: list[dict], templates: list[dict],
                               stacks: list[dict], variables: list[dict],
                               systems: list[dict]) -> None:
        """Write the scope objects, one `resource` block per scope entry (F6.5).

        The file is written before the config inside the scopes it names, which is the order rule
        `docs/CODEBASE_ASSEMBLY.md` §6 states. Blocks print in the F3.9 level order, and within a
        type in document order, so the file is byte-identical between runs.

        A block prints the field that carries the entry name, then the properties its matrix row
        declares, in the row order, so the read record the property scan measures is the list the
        row states. The entry name is the row identity, not a property, so it is not in the list.

        The device group block prints no `parent`: the provider has no `parent` attribute for
        `panos_device_group`, so the parent is the field of the parent record the same entry feeds.
        The row still declares `parent`, because the scan measures one entry against the row that
        covers its container, and this method reads it for the record. A record that would state no
        fact is not written, so a device group that states no parent writes no parent record.

        An entry the provider cannot place reaches no block here: the parse reported it as skipped,
        so the run writes no block for a virtual system no template holds, and for a variable no
        template or template stack holds.
        """
        # The type, the entries its blocks come from, the properties its matrix row declares, in the
        # order the block prints them, and the property the provider needs for the block to state a
        # fact. One device-group entry feeds two blocks: the scope object and the parent record. The
        # device group block prints no `parent`, because `DATA_SOURCE_SCHEMA` shows the provider has
        # no `parent` attribute for `panos_device_group`; the parent is the parent record's field, and
        # the row still declares it, because the property scan measures one entry against the row that
        # covers its container and this method reads it there.
        # The entry name is the row identity, so it is not a property.
        levels = (
            ('panos_device_group', device_groups, ('description', 'devices', 'templates'), ''),
            ('panos_device_group_parent', device_groups, ('parent',), 'parent'),
            ('panos_template', templates, ('default_vsys', 'description'), ''),
            ('panos_template_stack', stacks,
             ('default_vsys', 'description', 'devices', 'templates'), ''),
            ('panos_template_variable', variables,
             ('description', 'template_stack', 'type'), ''),
            ('panos_vsys', systems, (), ''),
        )
        out = UnitText(self, self.SCOPE_FILE)
        # The print order is `SCOPE_LEVEL_ORDER`, the F3.9 level order the file states, and not the
        # order this method lists the levels in.
        levels_in_order = sorted(levels, key=lambda level: SCOPE_LEVEL_ORDER.index(level[0]))
        for resource_type, entries, properties, needs in levels_in_order:
            for entry in entries:
                if needs and not entry.get(needs):
                    continue
                # The naming context is the placement key the emitter uses, so the name and the
                # location state the same scope. An entry that defines its own scope has no context
                # above it.
                placement = next((key for key in SCOPE_PLACEMENT[resource_type] if entry.get(key)), '')
                local = self.declare_resource_name(entry['name'], resource_type, entry, context=placement)
                out.add(entry, f'resource "{resource_type}" "{local}" {{\n')
                out.add(entry, self.location_block(resource_type, entry, local))
                out.add(entry, self._scope_name_field(resource_type, entry))
                for key in properties:
                    value = entry.get(key)
                    # A property that names the location sub-block is the location's field, not the
                    # block's own field (the same distinction `import_blocks.block_value` reads), so
                    # it prints inside `location` and not here. The read still counts, because the row
                    # declares it as a property this method reads.
                    if key in SCOPE_PLACEMENT[resource_type]:
                        continue
                    out.add(entry, self._scope_property(resource_type, key, value))
                out.add(entry, '}\n\n')
        out.write()

    def _scope_name_field(self, resource_type: str, entry: dict) -> str:
        """The field that carries the entry name, in the shape the provider declares it (F6.5).

        `entry_coverage.name_field` is the one rule for that field, so the emitter, the import
        agreement gate, and the coverage matrix test state the same thing.
        """
        return f'  {entry_coverage.name_field(resource_type)} = {self.escape_string(entry.get("name"))}\n'

    def _scope_property(self, resource_type: str, key: str, value) -> str:
        """One property line, in the shape the provider declares it as (F6.5).

        `SCOPE_SHAPE` states the shape for each property this method prints, and the shape is a
        provider fact: a membership the provider takes as a list of objects prints as a list of
        objects, because `terraform validate` refuses a string there. A membership the provider takes
        as a list of strings prints inline, the template variable `type` prints as the nested object
        the provider takes, and every other property is a string. A property with no value is not a
        field the export states, so the block writes no line for it.

        The device object carries the field the provider requires (`name`). The vsys list a device can
        carry is not a fact a device-group membership states, so the object states no vsys.

        The device member rule (F3.5): `localhost.localdomain` is the PAN-OS "this device"
        placeholder and names no firewall, so it never enters a printed membership list, and a list
        that held only the placeholder writes no line, because the provider field is optional.
        """
        shape = SCOPE_SHAPE[resource_type][key]
        if value in entry_coverage.EMPTY_FIELD_VALUES:
            return ''
        if isinstance(value, (list, tuple)):
            members = [item for item in value if item != container_coverage.PLACEHOLDER_DEVICE]
            if not members:
                return ''
            if shape == 'object_list':
                return f'  {key} = {self.hcl_value([{"name": item} for item in members])}\n'
            return f'  {key} = {self.hcl_value(members)}\n'
        return f'  {key} = {self.hcl_value(value)}\n'

    def generate_address_objects(self, addresses: list[dict]):
        """Generate address object Terraform configuration (v2: panos_address)

        The v2 schema exposes one attribute per address type (ip_netmask,
        ip_range, fqdn, ip_wildcard) instead of a generic value attribute.
        """
        if not addresses:
            return

        out = UnitText(self, 'address_objects.tf', '# Address Objects\n\n')

        for addr in addresses:
            if addr.get('report_only'):
                # No v2 attribute exists for this entry type; the entry is
                # reported instead of emitted as an empty resource (F3.4).
                continue

            resource_name = self.declare_resource_name(
                addr['name'], 'panos_address', addr,
                context=addr.get('device_group') or '', vsys=addr.get('vsys') or ''
            )

            out.add(addr, f'resource "panos_address" "{resource_name}" {{\n')
            out.add(addr, self.location_block('panos_address', addr, resource_name))
            out.add(addr, f'  name = {self.escape_string(addr["name"])}\n')

            if addr.get('description'):
                out.add(addr, f'  description = {self.escape_string(addr["description"])}\n')

            self.emit_disable_override(out, addr)

            value = (addr.get('value') or '').strip()
            if value:
                attr = self._address_type_attribute(addr.get('type', 'ip-netmask'))
                out.add(addr, f'  {attr} = {self.escape_string(value)}\n')

            if addr.get('tags'):
                # F2.6: tags declared in this run become references;
                # F3.2, F6.10.2: resolve inside the referrer's own unit
                addr.get('device_group')
                addr.get('vsys') or ''
                tags_str = ', '.join([
                    self.hcl_value(self.name_ref(t, TAG_SCOPES, referrer=addr), '')
                    for t in addr['tags']
                ])
                out.add(addr, f'  tags = [{tags_str}]\n')

            out.add(addr, '}\n\n')

        out.write()

    def emit_disable_override(self, out: 'UnitText', obj: dict) -> None:
        """Print the `disable_override` line for one entry: the one shape every row uses (F3.4, F6.2).

        The provider takes the string, not a bool (verified against 2.0.14). The line prints after the
        entry's descriptive field, or after `name` when the block prints no descriptive field, and only
        when the value is `yes` or `no`, so an entry that carries nothing prints nothing. Every matrix
        row that names the property reads the key through this one helper, which is what the property
        scan measures (F4.4).
        """
        disable = (obj.get('disable_override') or '').strip().lower()
        if disable in ('yes', 'no'):
            out.add(obj, f'  disable_override = "{disable}"\n')

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

        out = UnitText(self, 'address_groups.tf', '# Address Groups\n\n')

        for grp in groups:
            static_members = grp.get('static_members') or []
            dynamic_filter = (grp.get('dynamic_filter') or '').strip()

            # The v2 provider requires exactly one of the static member list
            # or the dynamic filter; an empty group would be invalid, so it is
            # kept visible as a comment instead of a resource.
            if not static_members and not dynamic_filter:
                out.add(grp, f'# NOTE: address group {grp["name"]} has no members or filter; configure manually\n\n')
                continue

            resource_name = self.declare_resource_name(
                grp['name'], 'panos_address_group', grp,
                context=grp.get('device_group') or '', vsys=grp.get('vsys') or ''
            )

            out.add(grp, f'resource "panos_address_group" "{resource_name}" {{\n')
            out.add(grp, self.location_block('panos_address_group', grp, resource_name))
            out.add(grp, f'  name = {self.escape_string(grp["name"])}\n')

            if grp.get('description'):
                out.add(grp, f'  description = {self.escape_string(grp["description"])}\n')

            self.emit_disable_override(out, grp)

            if static_members:
                # F2.6: members declared in this run become references;
                # F3.2, F6.10.2: resolve inside the referrer's own unit
                grp.get('device_group')
                grp.get('vsys') or ''
                members_str = ', '.join([
                    self.hcl_value(self.name_ref(m, ADDR_SCOPES, referrer=grp), '')
                    for m in static_members
                ])
                out.add(grp, f'  static = [{members_str}]\n')

            # v2 dynamic groups: the filter expression lives in dynamic.dynamic
            if dynamic_filter:
                out.add(grp, f'  dynamic = {self.hcl_value({"dynamic": {"filter": dynamic_filter}})}\n')

            out.add(grp, '}\n\n')

        out.write()

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

        out = UnitText(self, 'service_objects.tf', '# Service Objects\n\n')

        for svc in services:
            resource_name = self.declare_resource_name(
                svc['name'], 'panos_service', svc,
                context=svc.get('device_group') or '', vsys=svc.get('vsys') or ''
            )

            out.add(svc, f'resource "panos_service" "{resource_name}" {{\n')
            out.add(svc, self.location_block('panos_service', svc, resource_name))
            out.add(svc, f'  name = {self.escape_string(svc["name"])}\n')

            if svc.get('description'):
                out.add(svc, f'  description = {self.escape_string(svc["description"])}\n')

            self.emit_disable_override(out, svc)

            # v2 protocol is a nested object: protocol = { tcp = { ... } }
            protocols = svc.get('protocols') or {}
            emitted = self.primary_service_protocol(protocols)
            if emitted:
                out.add(svc, f'  protocol = {self.hcl_value({emitted: protocols[emitted]})}\n')

            for proto in self.dropped_service_protocols(protocols):
                summary = self.protocol_summary(protocols[proto])
                out.add(svc, f'  # NOTE: {proto} leg not emitted, v2 takes one protocol only: ')
                out.add(svc, f'{summary}\n')

            other = svc.get('other_protocol') or {}
            if other:
                # v2 models only tcp and udp; keep the rest visible for review
                names = ', '.join(sorted(other))
                out.add(svc, f'  # NOTE: protocol {names} is not modeled by the v2 schema; review manually\n')

            if svc.get('tags'):
                # F2.6: tags declared in this run become references;
                # F3.2, F6.10.2: resolve inside the referrer's own unit
                svc.get('device_group')
                svc.get('vsys') or ''
                tags_str = ', '.join([
                    self.hcl_value(self.name_ref(t, TAG_SCOPES, referrer=svc), '')
                    for t in svc['tags']
                ])
                out.add(svc, f'  tags = [{tags_str}]\n')

            out.add(svc, '}\n\n')

        out.write()

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

        out = UnitText(self, 'service_groups.tf', '# Service Groups\n\n')

        for grp in groups:
            resource_name = self.declare_resource_name(
                grp['name'], 'panos_service_group', grp,
                context=grp.get('device_group') or '', vsys=grp.get('vsys') or ''
            )

            out.add(grp, f'resource "panos_service_group" "{resource_name}" {{\n')
            out.add(grp, self.location_block('panos_service_group', grp, resource_name))
            out.add(grp, f'  name = {self.escape_string(grp["name"])}\n')

            # F4.4: the row names the property, and the block prints no descriptive field, so the
            # flag prints after the name
            self.emit_disable_override(out, grp)

            if grp.get('members'):
                # F2.6: members declared in this run become references;
                # F3.2, F6.10.2: resolve inside the referrer's own unit
                grp.get('device_group')
                grp.get('vsys') or ''
                members_str = ', '.join([
                    self.hcl_value(self.name_ref(m, SERVICE_SCOPES, referrer=grp), '')
                    for m in grp['members']
                ])
                out.add(grp, f'  members = [{members_str}]\n')

            out.add(grp, '}\n\n')

        out.write()

    def generate_tags(self, tags: list[dict]):
        """Generate tag Terraform configuration (v2: panos_administrative_tag)

        The v2 schema uses comments (not comment/description) for the tag text.
        """
        if not tags:
            return

        out = UnitText(self, 'tags.tf', '# Tags\n\n')

        for tag in tags:
            resource_name = self.declare_resource_name(
                tag['name'], 'panos_administrative_tag', tag,
                context=tag.get('device_group') or '', vsys=tag.get('vsys') or ''
            )

            out.add(tag, f'resource "panos_administrative_tag" "{resource_name}" {{\n')
            out.add(tag, self.location_block('panos_administrative_tag', tag, resource_name))
            out.add(tag, f'  name = {self.escape_string(tag["name"])}\n')

            # v2 uses numeric color names (color1..colorN); PAN-OS exports use
            # the color words in the GUI order (red, orange, yellow, green, ...)
            color_map = {
                'red': 'color1', 'orange': 'color2', 'yellow': 'color3',
                'green': 'color4', 'blue': 'color5', 'purple': 'color6',
                'gray': 'color7',
            }
            tag_color = (tag.get('color') or '').lower()
            if tag_color in color_map:
                out.add(tag, f'  color = {self.escape_string(color_map[tag_color])}\n')

            # Parser stores the tag text in comments (or description)
            tag_text = tag.get('comments') or tag.get('description')
            if tag_text:
                out.add(tag, f'  comments = {self.escape_string(tag_text)}\n')

            # F4.4: the row names the property, and the tag text is the entry's descriptive field,
            # so the flag prints after it
            self.emit_disable_override(out, tag)

            out.add(tag, '}\n\n')

        out.write()

    def generate_custom_url_categories(self, categories: list[dict]):
        """Generate custom URL category Terraform configuration (v2: panos_custom_url_category)"""
        if not categories:
            return

        out = UnitText(self, 'custom_url_categories.tf', '# Custom URL Categories\n\n')

        for cat in categories:
            resource_name = self.declare_resource_name(
                cat['name'], 'panos_custom_url_category', cat,
                context=cat.get('device_group') or '', vsys=cat.get('vsys') or ''
            )

            out.add(cat, f'resource "panos_custom_url_category" "{resource_name}" {{\n')
            out.add(cat, self.location_block('panos_custom_url_category', cat, resource_name))
            out.add(cat, f'  name = {self.escape_string(cat["name"])}\n')

            if cat.get('type'):
                out.add(cat, f'  type = {self.escape_string(cat["type"])}\n')

            if cat.get('description'):
                out.add(cat, f'  description = {self.escape_string(cat["description"])}\n')

            self.emit_disable_override(out, cat)

            if cat.get('list'):
                sites_str = ', '.join([self.escape_string(url) for url in cat['list']])
                out.add(cat, f'  list = [{sites_str}]\n')

            out.add(cat, '}\n\n')

        out.write()

    def generate_application_groups(self, app_groups: list[dict]):
        """Generate application group Terraform configuration (v2: panos_application_group)"""
        if not app_groups:
            return

        out = UnitText(self, 'application_groups.tf', '# Application Groups\n\n')

        for ag in app_groups:
            resource_name = self.declare_resource_name(
                ag['name'], 'panos_application_group', ag,
                context=ag.get('device_group') or '', vsys=ag.get('vsys') or ''
            )

            out.add(ag, f'resource "panos_application_group" "{resource_name}" {{\n')
            out.add(ag, self.location_block('panos_application_group', ag, resource_name))
            out.add(ag, f'  name = {self.escape_string(ag["name"])}\n')

            # F4.4: the row names the property, and the block prints no descriptive field, so the
            # flag prints after the name
            self.emit_disable_override(out, ag)

            if ag.get('members'):
                members_str = ', '.join([self.escape_string(m) for m in ag['members']])
                out.add(ag, f'  members = [{members_str}]\n')

            out.add(ag, '}\n\n')

        out.write()

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

        out = UnitText(self, 'external_lists.tf', '# External Dynamic Lists\n\n')

        # List types the v2 schema models inside the type block
        v2_types = ('domain', 'imei', 'imsi', 'ip', 'predefined_ip', 'predefined_url', 'url')

        for ext_list in ext_lists:
            resource_name = self.declare_resource_name(
                ext_list['name'], 'panos_external_dynamic_list', ext_list,
                context=ext_list.get('device_group') or '', vsys=ext_list.get('vsys') or ''
            )

            out.add(ext_list, f'resource "panos_external_dynamic_list" "{resource_name}" {{\n')
            out.add(ext_list, self.location_block('panos_external_dynamic_list', ext_list, resource_name))
            out.add(ext_list, f'  name = {self.escape_string(ext_list["name"])}\n')

            # F4.4: the row names the property, and the fields the sub-shape holds print inside the
            # type object, so the flag prints after the name, at the block's own level
            self.emit_disable_override(out, ext_list)

            # v2 type is a nested object keyed by list type
            lt = ext_list.get('type') or 'ip'
            fields = ext_list.get('fields') or {}
            if lt in v2_types:
                allowed = self.EDL_SUBSHAPE_FIELDS[lt]
                emit = {k: v for k, v in fields.items() if k in allowed}
                out.add(ext_list, f'  type = {self.hcl_value({lt: emit})}\n')
                for key in (k for k in fields if k not in allowed):
                    out.add(ext_list, f'  # NOTE: {key} is not modeled by the v2 {lt} ')
                    out.add(ext_list, 'sub-shape; review manually\n')
            else:
                # Unknown list type: keep the data visible for manual review
                out.add(ext_list, f'  # NOTE: list type {lt} is not modeled by the v2 schema; review manually\n')
                if fields.get('url'):
                    out.add(ext_list, f'  # url = {fields["url"]}\n')

            out.add(ext_list, '}\n\n')

        out.write()

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

        out = UnitText(self, 'security_rules.tf', '# Security Policy Rules\n\n')

        for chain in self._policy_rule_chains(rules):
            prev_rule_name: Optional[str] = None
            prev_resource_name: Optional[str] = None
            for rule in chain:
                resource_name = self.declare_resource_name(
                    rule['name'], 'panos_security_policy_rules', rule,
                    context=rule.get('device_group') or '', vsys=rule.get('vsys') or ''
                )

                out.add(rule, f'resource "panos_security_policy_rules" "{resource_name}" {{\n')
                out.add(rule, self.location_block('panos_security_policy_rules', rule, resource_name))
                out.add(rule, self._policy_position_block(
                    'panos_security_policy_rules', prev_rule_name, prev_resource_name
                ))

                # v2 rules is a list of objects
                rule_obj: dict = {'name': rule['name']}
                if rule.get('description'):
                    rule_obj['description'] = rule['description']
                # F2.6: zones, addresses and services declared in this run
                # become references; the rest stay brown-field strings
                # F3.2, F6.10.2: resolve inside the referrer's own unit
                rule.get('device_group')
                rule.get('vsys') or ''
                if rule.get('source_zones'):
                    rule_obj['source_zones'] = [
                        self.name_ref(z, ZONE_SCOPES, referrer=rule)
                        for z in rule['source_zones']]
                if rule.get('source_addresses'):
                    rule_obj['source_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES, referrer=rule)
                        for a in rule['source_addresses']]
                if rule.get('destination_zones'):
                    rule_obj['destination_zones'] = [
                        self.name_ref(z, ZONE_SCOPES, referrer=rule)
                        for z in rule['destination_zones']]
                if rule.get('destination_addresses'):
                    rule_obj['destination_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES, referrer=rule)
                        for a in rule['destination_addresses']]
                if rule.get('applications'):
                    # Built-in PAN-OS app names: no managed scope, never wired
                    rule_obj['applications'] = list(rule['applications'])
                if rule.get('services'):
                    rule_obj['services'] = [
                        self.name_ref(s, SERVICE_SCOPES, referrer=rule) for s in rule['services']]
                if rule.get('profile_group'):
                    # The provider holds the profile group reference inside the `profile_setting`
                    # object (v2.0.14 declares `profile_setting.group` as a list of strings). No
                    # reference scope names a profile group, so the names stay brown-field strings.
                    rule_obj['profile_setting'] = {'group': list(rule['profile_group'])}
                rule_obj['action'] = rule.get('action', 'allow')
                if rule.get('log_start'):
                    rule_obj['log_start'] = True
                if rule.get('log_end'):
                    rule_obj['log_end'] = True
                if rule.get('disabled'):
                    rule_obj['disabled'] = True

                out.add(rule, f'  rules = {self.hcl_value([rule_obj])}\n')
                out.add(rule, '}\n\n')

                prev_rule_name = rule['name']
                prev_resource_name = resource_name

        out.write()

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

        out = UnitText(self, 'nat_rules.tf', '# NAT Policy Rules\n\n')

        for chain in self._policy_rule_chains(rules):
            prev_rule_name: Optional[str] = None
            prev_resource_name: Optional[str] = None
            for rule in chain:
                resource_name = self.declare_resource_name(
                    rule['name'], 'panos_nat_policy_rules', rule,
                    context=rule.get('device_group') or '', vsys=rule.get('vsys') or ''
                )

                out.add(rule, f'resource "panos_nat_policy_rules" "{resource_name}" {{\n')
                out.add(rule, self.location_block('panos_nat_policy_rules', rule, resource_name))
                out.add(rule, self._policy_position_block(
                    'panos_nat_policy_rules', prev_rule_name, prev_resource_name
                ))

                # v2 rules is a list of objects
                rule_obj: dict = {'name': rule['name']}
                if rule.get('description'):
                    rule_obj['description'] = rule['description']
                # F2.6: zones, addresses and services declared in this run
                # become references; the rest stay brown-field strings
                # F3.2, F6.10.2: resolve inside the referrer's own unit
                rule.get('device_group')
                rule.get('vsys') or ''
                if rule.get('source_zones'):
                    rule_obj['source_zones'] = [
                        self.name_ref(z, ZONE_SCOPES, referrer=rule)
                        for z in rule['source_zones']]
                # v2 destination_zone is a list
                if rule.get('destination_zone'):
                    rule_obj['destination_zone'] = [
                        self.name_ref(rule['destination_zone'], ZONE_SCOPES, referrer=rule)]
                if rule.get('source_addresses'):
                    rule_obj['source_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES, referrer=rule)
                        for a in rule['source_addresses']]
                if rule.get('destination_addresses'):
                    rule_obj['destination_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES, referrer=rule)
                        for a in rule['destination_addresses']]
                service = rule.get('service')
                if service:
                    if isinstance(service, list):
                        # The provider field takes one string, so a member list cannot be
                        # printed as the field (v2.0.14 schema). The set is named in the block
                        # instead of being dropped (F2.9).
                        out.add(rule, '  # NOTE: service ' + ', '.join(service) +
                                 ' is a member list; the v2 field takes one name, '
                                 'so review manually\n')
                    else:
                        rule_obj['service'] = self.name_ref(service, SERVICE_SCOPES, referrer=rule)
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
                        # F3.2, F6.10.2: resolve inside the rule's unit)
                        rule_obj['source_translation'] = {
                            st_type: {'interface_address': {
                                'interface': self.name_ref(
                                    st_addr[0], INTERFACE_SCOPES,
                                    referrer=rule)}}}
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

                out.add(rule, f'  rules = {self.hcl_value([rule_obj])}\n')
                out.add(rule, '}\n\n')

                prev_rule_name = rule['name']
                prev_resource_name = resource_name

        out.write()

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

        out = UnitText(self, 'decryption_rules.tf', '# Decryption Policy Rules (F2.9: real v2 resources)\n')
        out.header += '# One panos_decryption_policy_rules resource per rule; per-device-group\n'
        out.header += '# chains preserve XML order (F2.5).\n\n'

        for chain in self._policy_rule_chains(rules):
            prev_rule_name: Optional[str] = None
            prev_resource_name: Optional[str] = None
            for rule in chain:
                device_group = rule.get('device_group') or 'Shared'
                resource_name = self.declare_resource_name(
                    rule['name'], 'panos_decryption_policy_rules', rule,
                    context=device_group, vsys=rule.get('vsys') or ''
                )

                out.add(rule, f'resource "panos_decryption_policy_rules" "{resource_name}" {{\n')
                out.add(rule, self.location_block('panos_decryption_policy_rules', rule, resource_name))
                out.add(rule, self._policy_position_block(
                    'panos_decryption_policy_rules', prev_rule_name, prev_resource_name
                ))

                rule_obj: dict = {'name': rule['name']}
                if rule.get('description'):
                    rule_obj['description'] = rule['description']
                # F2.6: zones, addresses and services declared in this run
                # become references; the rest stay brown-field strings
                # F3.2, F6.10.2: resolve inside the referrer's own unit
                rule.get('device_group')
                rule.get('vsys') or ''
                if rule.get('source_zones'):
                    rule_obj['source_zones'] = [
                        self.name_ref(z, ZONE_SCOPES, referrer=rule)
                        for z in rule['source_zones']]
                if rule.get('destination_zones'):
                    rule_obj['destination_zones'] = [
                        self.name_ref(z, ZONE_SCOPES, referrer=rule)
                        for z in rule['destination_zones']]
                if rule.get('source_addresses'):
                    rule_obj['source_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES, referrer=rule)
                        for a in rule['source_addresses']]
                if rule.get('destination_addresses'):
                    rule_obj['destination_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES, referrer=rule)
                        for a in rule['destination_addresses']]
                if rule.get('source_users'):
                    rule_obj['source_user'] = list(rule['source_users'])
                if rule.get('categories'):
                    rule_obj['category'] = list(rule['categories'])
                if rule.get('services'):
                    rule_obj['services'] = [
                        self.name_ref(s, SERVICE_SCOPES, referrer=rule) for s in rule['services']]
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

                out.add(rule, f'  rules = {self.hcl_value([rule_obj])}\n')
                out.add(rule, '}\n\n')

                prev_rule_name = rule['name']
                prev_resource_name = resource_name

        out.write()

    def generate_pbf_rules(self, rules: list[dict]):
        """Generate Policy-Based Forwarding rules (F2.9: real v2 resources).

        v2.0.14 has no PBF rule container: each rule is its own
        `panos_pbf_policy_rules` resource. The chain semantics match the
        other policy rulebases (F2.5). The action is a single-choice
        object: forward, discard, no_pbf, or forward_to_vsys.
        """
        if not rules:
            return

        out = UnitText(self, 'pbf_rules.tf', '# Policy-Based Forwarding Rules (F2.9: real v2 resources)\n')
        out.header += '# One panos_pbf_policy_rules resource per rule; per-device-group\n'
        out.header += '# chains preserve XML order (F2.5).\n\n'

        for chain in self._policy_rule_chains(rules):
            prev_rule_name: Optional[str] = None
            prev_resource_name: Optional[str] = None
            for rule in chain:
                device_group = rule.get('device_group') or 'Shared'
                resource_name = self.declare_resource_name(
                    rule['name'], 'panos_pbf_policy_rules', rule,
                    context=device_group, vsys=rule.get('vsys') or ''
                )

                out.add(rule, f'resource "panos_pbf_policy_rules" "{resource_name}" {{\n')
                out.add(rule, self.location_block('panos_pbf_policy_rules', rule, resource_name))
                out.add(rule, self._policy_position_block(
                    'panos_pbf_policy_rules', prev_rule_name, prev_resource_name
                ))

                rule_obj: dict = {'name': rule['name']}
                if rule.get('description'):
                    rule_obj['description'] = rule['description']
                # v2 models the PBF source as from { zone = [...] }
                # F3.2, F6.10.2: resolve inside the referrer's own unit
                rule.get('device_group')
                rule.get('vsys') or ''
                if rule.get('source_zones'):
                    rule_obj['from'] = {
                        'zone': [
                            self.name_ref(z, ZONE_SCOPES, referrer=rule)
                            for z in rule['source_zones']]}
                if rule.get('source_addresses'):
                    rule_obj['source_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES, referrer=rule)
                        for a in rule['source_addresses']]
                if rule.get('source_users'):
                    rule_obj['source_users'] = list(rule['source_users'])
                if rule.get('destination_addresses'):
                    rule_obj['destination_addresses'] = [
                        self.name_ref(a, ADDR_SCOPES, referrer=rule)
                        for a in rule['destination_addresses']]
                if rule.get('applications'):
                    rule_obj['applications'] = list(rule['applications'])
                if rule.get('services'):
                    rule_obj['services'] = [
                        self.name_ref(s, SERVICE_SCOPES, referrer=rule) for s in rule['services']]
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

                out.add(rule, f'  rules = {self.hcl_value([rule_obj])}\n')
                out.add(rule, '}\n\n')

                prev_rule_name = rule['name']
                prev_resource_name = resource_name

        out.write()

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

        out = UnitText(self, 'monitor_profiles.tf', '# PBF Path Monitoring Profiles (F2.9: real v2 resources)\n\n')

        for prof in profiles:
            # F3.6: a monitor profile lives in a template or in one device's
            # own config, so the naming context is the declared template, else
            # the declared device (scope_context).
            resource_name = self.declare_resource_name(
                prof['name'], 'panos_monitor_profile', prof,
                context=self.scope_context(prof), vsys=prof.get('vsys') or ''
            )
            out.add(prof, f'resource "panos_monitor_profile" "{resource_name}" {{\n')
            out.add(prof, self.location_block('panos_monitor_profile', prof, resource_name))
            out.add(prof, f'  name = {self.escape_string(prof["name"])}\n')
            for attr in ('interval', 'threshold'):
                raw = prof.get(attr)
                # The v2 schema takes numbers; skip values that are not
                # plain integers so the output always validates
                if raw is not None and str(raw).isdigit():
                    out.add(prof, f'  {attr} = {int(raw)}\n')
            if prof.get('action'):
                out.add(prof, f'  action = {self.escape_string(prof["action"])}\n')
            out.add(prof, '}\n\n')

        out.write()


    def generate_zones(self, zones: list[dict]):
        """Generate zone Terraform configuration (v2: panos_zone)

        The v2 schema nests membership in a network block:
        network { layer3 = [...] } or network { layer2 = [...] }
        """
        if not zones:
            return

        out = UnitText(self, 'zones.tf', '# Zone Configurations\n\n')

        for zone in zones:
            resource_name = self.declare_resource_name(
                zone['name'], 'panos_zone', zone,
                context=self.scope_context(zone), vsys=zone.get('vsys') or ''
            )

            out.add(zone, f'resource "panos_zone" "{resource_name}" {{\n')
            out.add(zone, self.location_block('panos_zone', zone, resource_name))
            out.add(zone, f'  name = {self.escape_string(zone["name"])}\n')

            # v2 network object: membership list is keyed by layer type
            ztype = zone.get('type') or 'layer3'
            key = 'layer2' if ztype == 'layer2' else 'layer3'
            network: dict = {}
            if zone.get('interfaces'):
                # F2.6: interfaces declared in this run become references;
                # F3.2, F6.10.2: resolve inside the zone's unit
                network[key] = [
                    self.name_ref(i, INTERFACE_SCOPES,
                                  referrer=zone)
                    for i in zone['interfaces']]
            if zone.get('zone_protection_profile'):
                network['zone_protection_profile'] = zone['zone_protection_profile']
            if network:
                out.add(zone, f'  network = {self.hcl_value(network)}\n')

            out.add(zone, '}\n\n')

        out.write()

    def generate_virtual_routers(self, vrouters: list[dict]):
        """Generate virtual router Terraform configuration (v2: panos_virtual_router)

        Logical routers (Advanced Routing Engine) emit the same v2 resource.
        Static routes use the v2 panos_virtual_router_static_route_ipv4
        resource and reference the owning virtual router resource.
        """
        if not vrouters:
            return

        out = UnitText(self, 'virtual_routers.tf', '# Router Configurations\n')
        out.header += '# Supports both Virtual Routers (legacy) and Logical Routers (Advanced Routing Engine)\n\n'

        for router in vrouters:
            resource_name = self.declare_resource_name(
                router['name'], 'panos_virtual_router', router,
                context=self.scope_context(router), vsys=router.get('vsys') or ''
            )

            # Add comment showing source and type. A router the export does
            # not place in a template is device-specific (F3.5 records the
            # template as '' there).
            template = router.get('template') or 'device-specific'
            out.add(router, f'# Source: {template}\n')
            router_type = router.get('router_type', 'virtual')
            if router_type == 'logical':
                rtype = 'Logical Router (Advanced Routing Engine)'
            else:
                rtype = 'Virtual Router (Legacy)'
            out.add(router, f'# Type: {rtype}\n')

            out.add(router, f'resource "panos_virtual_router" "{resource_name}" {{\n')
            out.add(router, self.location_block('panos_virtual_router', router, resource_name))
            out.add(router, f'  name = {self.escape_string(router["name"])}\n')

            # v2 interfaces is a flat string list
            if router.get('interfaces'):
                # F2.6: interfaces declared in this run become references;
                # F3.2, F6.10.2: resolve inside the router's unit
                ifaces_str = ', '.join([
                    self.hcl_value(self.name_ref(
                        i, INTERFACE_SCOPES,
                        referrer=router), '')
                    for i in router['interfaces']
                ])
                out.add(router, f'  interfaces = [{ifaces_str}]\n')

            # F7.1: the protocol object is one field of the block, printed from `PROTOCOL_SHAPE`. A block
            # shape (`protocol { ... }`) is refused by the provider, so the object value is the only shape
            # the gate rule accepts.
            protocol = self._protocol_fields(resource_mapping.PROTOCOL_FIELD, router.get('protocol') or {},
                                             router)
            if protocol:
                out.add(router, f'  protocol = {self.hcl_value(protocol, "  ")}\n')

            out.add(router, '}\n\n')

            # Generate static routes (v2: panos_virtual_router_static_route_ipv4)
            if router.get('static_routes'):
                for route in router['static_routes']:
                    route_key = f"{resource_name}_{route['name']}"
                    route_resource = self.declare_resource_name(
                        route_key, 'panos_virtual_router_static_route_ipv4', router,
                        context=self.scope_context(router), vsys=router.get('vsys') or ''
                    )

                    out.add(router, f'resource "panos_virtual_router_static_route_ipv4" "{route_resource}" {{\n')
                    # The route carries the owning router's source
                    # identity; only the report name is the route's own
                    out.add(router, self.location_block(
                        'panos_virtual_router_static_route_ipv4',
                        {**router, 'name': route['name']}, route_resource))
                    out.add(router, f'  name = {self.escape_string(route["name"])}\n')
                    # Reference the owning virtual router resource
                    out.add(router, f'  virtual_router = panos_virtual_router.{resource_name}.name\n')

                    if route.get('destination'):
                        # PAN-OS exports the default route destination as "default"
                        destination = route['destination']
                        if destination == 'default':
                            destination = '0.0.0.0/0'
                        out.add(router, f'  destination = {self.escape_string(destination)}\n')

                    if route.get('nexthop_ip'):
                        # v2 nexthop is a nested object
                        out.add(router, f'  nexthop = {self.hcl_value({"ip_address": route["nexthop_ip"]})}\n')
                    elif route.get('nexthop_interface'):
                        out.add(router, f'  interface = {self.escape_string(route["nexthop_interface"])}\n')

                    metric = route.get('metric')
                    if metric is not None:
                        try:
                            metric = int(metric)
                        except (TypeError, ValueError):
                            metric = None
                    if metric is not None:
                        out.add(router, f'  metric = {metric}\n')

                    out.add(router, '}\n\n')

        out.write()

    def generate_interfaces(self, interfaces: list[dict]):
        """Generate interface Terraform configuration (v2, one resource per kind).

        The v2 panos_ethernet_interface has no ipv4 attribute: IPv4
        addresses on a physical L3 interface are modeled on its .0 layer-3
        subinterface via panos_ethernet_layer3_subinterface.
        """
        if not interfaces:
            return

        out = UnitText(self, 'interfaces.tf', '# Interface Configurations\n')
        out.header += '# Note: These are reference configurations. Adjust for your hardware platform.\n\n'

        for iface in interfaces:
            kind = iface['type']
            if kind == 'ethernet':
                out.add(iface, self._emit_ethernet_interface(iface))
                continue
            scope = INTERFACE_RESOURCE_TYPES.get(kind)
            if scope:
                out.add(iface, self._emit_interface_resource(iface, scope))

        out.write()

    def _emit_ethernet_interface(self, iface: dict) -> str:
        """Emit one ethernet entry: the physical interface, or a tagged subinterface."""
        name = iface['name']
        mode = iface.get('mode')
        context = self.scope_context(iface)
        vsys = iface.get('vsys') or ''
        scope_sub = 'panos_ethernet_layer3_subinterface'
        parent, dot, tag_str = name.partition('.')

        # Tagged L3 subinterface (ethernet1/2.10): v2 subinterface resource
        if dot and mode == 'layer3':
            scope = scope_sub
            resource_name = self.declare_resource_name(
                name, scope, iface, context=context, vsys=vsys)
            out = f'resource "{scope}" "{resource_name}" {{\n'
            out += self.location_block(scope, iface, resource_name)
            out += f'  name = {self.escape_string(name)}\n'
            # F2.6: the parent is an interface declared in this run
            # (or a brown-field interface outside the export);
            # F3.2, F6.10.2: resolve inside the subinterface's unit
            parent_ref = self.name_ref(parent, IFACE_SCOPES,
                                       referrer=iface)
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
            name, scope, iface, context=context, vsys=vsys)
        out = f'resource "{scope}" "{resource_name}" {{\n'
        out += self.location_block(scope, iface, resource_name)
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
                sub_name, scope_sub, iface, context=context, vsys=vsys)
            out += f'resource "{scope_sub}" "{sub_resource}" {{\n'
            # The subinterface is its own object, so reports name it by its
            # own name (the location itself comes from the same source entry).
            out += self.location_block(scope_sub, {**iface, 'name': sub_name}, sub_resource)
            out += f'  name = {self.escape_string(sub_name)}\n'
            # F2.6: the parent is the physical interface declared above;
            # F3.2, F6.10.2: resolve inside the subinterface's unit
            parent_ref = self.name_ref(name, IFACE_SCOPES,
                                       referrer=iface)
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
        # An aggregate entry whose name already carries a unit (ae1.101) is a
        # layer-3 subinterface of the aggregate group; the group entry itself
        # has no ip, parent, or tag in the schema.
        if iface['type'] == 'aggregate' and '.' in name:
            scope = 'panos_aggregate_layer3_subinterface'
        resource_name = self.declare_resource_name(
            name, scope, iface, context=context, vsys=vsys)
        out = f'resource "{scope}" "{resource_name}" {{\n'
        out += self.location_block(scope, iface, resource_name)
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
            parent_ref = self.name_ref(parent, IFACE_SCOPES,
                                       referrer=iface)
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

        self.write_root_file('INTERFACE_MIGRATION_REPORT.txt', content)

    def generate_security_profiles(self, profiles: dict[str, list[dict]]):
        """Generate security profile Terraform configuration"""
        if not any(profiles.values()):
            return

        out = UnitText(self, 'security_profiles.tf',
                       '# Security Profiles\n'
                       '# Note: These are simplified profile references.\n'
                       '# Detailed profile rules must be configured manually or imported.\n\n')

        # Note: Full profile configuration with all rules is complex
        # This generates basic profile declarations that can be enhanced

        # Antivirus profiles
        if profiles.get('antivirus'):
            for facts in self.units_of(profiles['antivirus']):
                out.add_once(facts, '# Antivirus Profiles\n')
            for prof in profiles['antivirus']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_antivirus_security_profile', prof,
                    # F3.1: contextless. This stub emits no location, so
                    # the device group and template stay out of its name;
                    # F3.2: vsys is part of the identity key
                    context='', vsys=prof.get('vsys') or '')
                out.add(prof, f'# Profile: {prof["name"]}\n')
                if prof.get('description'):
                    out.add(prof, f'# Description: {prof["description"]}\n')
                out.add(prof, f'# Resource: panos_antivirus_security_profile.{resource_name}\n\n')

        # Vulnerability profiles
        if profiles.get('vulnerability'):
            for facts in self.units_of(profiles['vulnerability']):
                out.add_once(facts, '# Vulnerability Protection Profiles\n')
            for prof in profiles['vulnerability']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_vulnerability_security_profile', prof,
                    # F3.1: contextless. This stub emits no location, so
                    # the device group and template stay out of its name;
                    # F3.2: vsys is part of the identity key
                    context='', vsys=prof.get('vsys') or '')
                out.add(prof, f'# Profile: {prof["name"]}\n')
                if prof.get('description'):
                    out.add(prof, f'# Description: {prof["description"]}\n')
                out.add(prof, f'# Resource: panos_vulnerability_security_profile.{resource_name}\n\n')

        # Anti-spyware profiles
        if profiles.get('anti_spyware'):
            for facts in self.units_of(profiles['anti_spyware']):
                out.add_once(facts, '# Anti-Spyware Profiles\n')
            for prof in profiles['anti_spyware']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_anti_spyware_security_profile', prof,
                    # F3.1: contextless. This stub emits no location, so
                    # the device group and template stay out of its name;
                    # F3.2: vsys is part of the identity key
                    context='', vsys=prof.get('vsys') or '')
                out.add(prof, f'# Profile: {prof["name"]}\n')
                if prof.get('description'):
                    out.add(prof, f'# Description: {prof["description"]}\n')
                out.add(prof, f'# Resource: panos_anti_spyware_security_profile.{resource_name}\n\n')

        # URL filtering profiles
        if profiles.get('url_filtering'):
            for facts in self.units_of(profiles['url_filtering']):
                out.add_once(facts, '# URL Filtering Profiles\n')
            for prof in profiles['url_filtering']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_url_filtering_security_profile', prof,
                    # F3.1: contextless. This stub emits no location, so
                    # the device group and template stay out of its name;
                    # F3.2: vsys is part of the identity key
                    context='', vsys=prof.get('vsys') or '')
                out.add(prof, f'# Profile: {prof["name"]}\n')
                if prof.get('description'):
                    out.add(prof, f'# Description: {prof["description"]}\n')
                out.add(prof, f'# Resource: panos_url_filtering_security_profile.{resource_name}\n\n')

        # File blocking profiles
        if profiles.get('file_blocking'):
            for facts in self.units_of(profiles['file_blocking']):
                out.add_once(facts, '# File Blocking Profiles\n')
            for prof in profiles['file_blocking']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_file_blocking_security_profile', prof,
                    # F3.1: contextless. This stub emits no location, so
                    # the device group and template stay out of its name;
                    # F3.2: vsys is part of the identity key
                    context='', vsys=prof.get('vsys') or '')
                out.add(prof, f'# Profile: {prof["name"]}\n')
                if prof.get('description'):
                    out.add(prof, f'# Description: {prof["description"]}\n')
                out.add(prof, f'# Resource: panos_file_blocking_security_profile.{resource_name}\n\n')

        # WildFire profiles
        if profiles.get('wildfire_analysis'):
            for facts in self.units_of(profiles['wildfire_analysis']):
                out.add_once(facts, '# WildFire Analysis Profiles\n')
            for prof in profiles['wildfire_analysis']:
                resource_name = self.declare_resource_name(
                    prof['name'], 'panos_wildfire_analysis_security_profile', prof,
                    # F3.1: contextless. This stub emits no location, so
                    # the device group and template stay out of its name;
                    # F3.2: vsys is part of the identity key
                    context='', vsys=prof.get('vsys') or '')
                out.add(prof, f'# Profile: {prof["name"]}\n')
                if prof.get('description'):
                    out.add(prof, f'# Description: {prof["description"]}\n')
                out.add(prof, f'# Resource: panos_wildfire_analysis_security_profile.{resource_name}\n\n')

        out.write()

    def generate_security_profile_groups(self, groups: list[dict]):
        """Generate security profile group Terraform configuration (v2: panos_security_profile_group)

        The v2 schema models each profile category as a string list.
        """
        if not groups:
            return

        out = UnitText(self, 'security_profile_groups.tf', '# Security Profile Groups\n\n')

        # Profile categories the v2 schema models as lists
        categories = ('virus', 'spyware', 'vulnerability', 'url_filtering',
                      'file_blocking', 'wildfire_analysis', 'gtp', 'sctp', 'data_filtering')

        for grp in groups:
            resource_name = self.declare_resource_name(
                grp['name'], 'panos_security_profile_group', grp,
                context=grp.get('device_group') or '', vsys=grp.get('vsys') or ''
            )

            out.add(grp, f'resource "panos_security_profile_group" "{resource_name}" {{\n')
            out.add(grp, self.location_block('panos_security_profile_group', grp, resource_name))
            out.add(grp, f'  name = {self.escape_string(grp["name"])}\n')

            # F4.4: the row names the property, and the block prints no descriptive field, so the
            # flag prints after the name
            self.emit_disable_override(out, grp)

            for category in categories:
                members = grp.get(category)
                if members:
                    members_str = ', '.join([self.escape_string(m) for m in members])
                    out.add(grp, f'  {category} = [{members_str}]\n')

            out.add(grp, '}\n\n')

        out.write()


    @staticmethod
    def _protocol_report_value(value) -> str:
        """One captured protocol value as the report prints it (F7.1).

        The report prints the fields the `.tf` cannot hold, in the order `captured_fields` states them,
        which is the field list the ledger holds for the entry. A `one_of` value prints the value the export
        states, which is what the operator types in the GUI, not the provider key the `.tf` prints. A field
        with nothing in it prints nothing, the same rule the emitter follows.
        """
        if isinstance(value, dict):
            if len(value) == 1 and all(item in entry_coverage.EMPTY_FIELD_VALUES for item in value.values()):
                # The one key a `one_of` level states is the value itself when the choice has no field
                # with a value, which is what the operator types in the GUI.
                return next(iter(value))
            return ', '.join(f'{key}={TerraformGenerator._protocol_report_value(item)}'
                             for key, item in value.items()
                             if item not in entry_coverage.EMPTY_FIELD_VALUES)
        if isinstance(value, list):
            return ', '.join(TerraformGenerator._protocol_report_value(item) for item in value
                             if item not in entry_coverage.EMPTY_FIELD_VALUES)
        return '' if value in entry_coverage.EMPTY_FIELD_VALUES else str(value)

    def generate_manual_setup_report(self, protocol_report: list[dict],
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
                                     entry_report: str = ''):
        """Write MANUAL_SETUP_REPORT.txt for items that are not emitted (F2.9)

        Two buckets, one report:
        - the generated file cannot express them: the routing protocol entries no provider field
          reaches (F7.1), the application filter, the manual-key IPsec tunnel, the application
          override rule, the QoS profile;
        - a v2 resource exists but the converter intentionally does not emit
          it, because only the name and description were parsed and an empty
          object would be a misconfiguration (log forwarding and zone
          protection profiles).

        The parsed data is preserved here instead of being emitted as .tf
        resources, so nothing is silently dropped (see resource_mapping.py).

        `entry_report` is the section text the caller built, not the module, so the module name
        `entry_coverage` stays readable inside the method.
        """
        if not (protocol_report or application_filters or manual_key_tunnels
                or application_override_rules or qos_profiles
                or tunnel_monitor_profiles or schedules or log_settings
                or zone_protection_profiles or report_only_addresses
                or dual_protocol_services or entry_report or self._location_reports):
            return

        lines = ['MANUAL SETUP REPORT', '=' * 60, '']
        lines.append('The items below have no panos provider v2 resource, or the')
        lines.append('converter intentionally does not emit them (the reason is stated')
        lines.append('per section). Configure them manually (GUI or CLI) and verify')
        lines.append('against this report.')
        lines.append('')

        # F7.1: the emitter prints the protocol object, so this section names only what no provider field
        # can express: a peer no peer group names, and an interface the export places outside an area. The
        # fields come from the captured object, which the parse fills from `PROTOCOL_SHAPE`, so the report
        # cannot state a field the shape table does not declare. The entry is a property level, so the
        # coverage rows count it on the router row (F4.2 AC-3.2); the reason it is named here is the mark
        # detail, which is the same record the gate reads.
        if protocol_report:
            lines.append('--- Routing protocol entries the generated file cannot express (F7.1) ---')
            for path, rows in self._group_by_scope(protocol_report):
                lines.append(self._report_section_header(path))
                for row in rows:
                    lines.append(f"  router {row['router']}: {row['level']} {row['name']} "
                                 f"({row['detail']})")
                    # `row['fields']` is the field list the ledger states for the entry, so the report reads
                    # every field through the captured object: the read is the property the scan counts.
                    for field in row['fields']:
                        text = self._protocol_report_value(row['captured'].get(field))
                        if text:
                            lines.append(f'    {field}: {text}')
                    vsys_line = self._report_vsys_line(row).rstrip()
                    if vsys_line:
                        lines.append(vsys_line)
            lines.append('')

        if application_filters:
            lines.append('--- Application Filters (no v2 resource: panos_application_filter) ---')
            for af in application_filters:
                # The report is the output for this container, so it reads the field it prints
                # through the captured object (F4.4).
                lines.append(f"  {af.get('name')} (dg: {af.get('device_group')}): "
                             f"category={af.get('category')}, risk={af.get('risk')}, "
                             f"evasive={af.get('evasive')}"
                             + (f", description={af['description']}" if af.get('description') else ''))
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
                # The report is the only output for this container, so the line prints the fields it reads
                # through the captured object (F4.4, `docs/COVERAGE_MATRIX.md` §1). One rule states the
                # shape: `OVERRIDE_REPORT_FIELDS` is the field order, and a field the entry carries no
                # value for prints nothing (F4.3 rule 3). `port` and `protocol` state `any` for the empty
                # field, which is what the export means.
                parts = [f"  {rule.get('name')}:"]
                for label, key in OVERRIDE_REPORT_FIELDS:
                    value = rule.get(key)
                    if value not in entry_coverage.EMPTY_FIELD_VALUES:
                        parts.append(f'{label}={value}')
                    elif key in ('port', 'protocol'):
                        parts.append(f'{label}=any')
                lines.append(' '.join(parts))
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
                # The report is the output for this container, so it reads the field it prints
                # through the captured object (F4.4). `panos_schedule` declares no description.
                lines.append(
                    f"  {sched['name']}"
                    + (f" ({sched['description']})" if sched.get('description') else '')
                    + f": type={sched.get('schedule_type')}, entries={entries}")
            lines.append('  The v2 resource panos_schedule exists, but the parse')
            lines.append('  reads the entry name, the description and the schedule')
            lines.append('  type only (day and time ranges are not captured), and')
            lines.append('  v2.0.14 does not model monthly schedules. Configure via')
            lines.append('  the Panorama GUI or CLI.')
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
        if entry_report:
            lines.append(entry_report)
            lines.append('')

        lines.append('End of report.')

        self.write_root_file('MANUAL_SETUP_REPORT.txt', '\n'.join(lines) + '\n')

    def generate_conversion_report(self, ledger, shadows=None, state=None,
                                   ownership_findings=None, cycle_findings=None) -> str:
        """Generate CONVERSION_REPORT.txt for the entries the parse read (F4.3).

        One line per report row, grouped by the F3.9 scope rule so a reader can
        tell two same-named entries on two device groups apart. The report names
        the source name only, never the path (F4.2 rule 6); the path is in the
        provenance record (`provenance.py`, F5.3).

        `shadows` is the F5.4 cross-source scan result. `state` is the F5.6 state scan result.
        `ownership_findings` is the F6.2 ownership scan result. `cycle_findings` is the F6.3 edge scan
        result. Each prints in its own section, after the property section, only when it has a finding,
        and each is grouped by the same scope rule as the other sections. Section order is fixed: header,
        summary, gaps, property findings, shadows, repeated names, reference cycles, state ownership,
        drift.

        Returns '' when the input has no report rows, and writes no file in that
        case (F4.3 AC-9): a run that read no entry has nothing to report.
        """
        rows = ledger.rows()
        if not rows:
            return ''

        lines = ['=' * 80, entry_coverage.REPORT_HEADING, '=' * 80, '',
                 f'{container_coverage.SOURCE_LABEL} {ledger.source.name}', '',
                 entry_coverage.RULE_PARAGRAPH, '']
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

        # F5.4: the cross-source shadow scan. A child entry name that repeats a parent
        # entry name is an operator action, not a broken output, so it does not change
        # the exit code (the F4.1 gate does). The section prints only when there is a
        # finding, and the console prints one line per finding in the shape
        # `container_coverage.console_line` states.
        if shadows:
            lines.extend(['', f'--- {shadow_coverage.SHADOW_HEADING} ---', shadow_coverage.SHADOW_RULE])
            for path, group in self._group_by_scope(shadows):
                lines.append(self._report_section_header(path))
                for row in group:
                    lines.append(shadow_coverage.shadow_line(row, self._report_scope_path))

        # F6.2: the ownership scan. A repeated name the rule cannot decide is an operator action, not
        # a broken output, so it does not change the exit code (the F4.1 gate does). The section prints
        # only when it has a finding, and the console prints no ownership line.
        if ownership_findings:
            lines.extend(['', f'--- {ownership.FINDING_HEADING} ---', ownership.FINDING_RULE])
            for path, group in self._group_by_scope(ownership_findings):
                lines.append(self._report_section_header(path))
                for row in group:
                    lines.append(ownership.finding_line(row))

        # F6.3: the edge scan. Two units that reference each other cannot be put in a plan order, so a
        # cycle is an operator action, not a broken output, and it does not change the exit code (the F4.1
        # gate does). The section prints only when it has a finding, and the console prints no cycle line.
        if cycle_findings:
            lines.extend(['', f'--- {reference_edges.CYCLE_HEADING} ---', reference_edges.CYCLE_RULE])
            for path, group in self._group_by_scope(cycle_findings):
                lines.append(self._report_section_header(path))
                for row in group:
                    lines.append(reference_edges.cycle_line(row))

        # F5.6: the state scan. Ownership and drift are operator actions, not broken output, so
        # they do not change the exit code (the F4.1 gate does). Each section prints only when it
        # has a finding, and the console prints no state line.
        if state:
            lines.extend(['', f'--- {state_coverage.OWNERSHIP_HEADING} ---', state_coverage.OWNERSHIP_RULE])
            for path, group in self._group_by_scope(state):
                lines.append(self._report_section_header(path))
                for row in group:
                    lines.append(state_coverage.ownership_line(row))

            # A drift fact needs an ownership fact, so this section is a subset of the one above.
            drifting = [row for row in state if row['drift']]
            if drifting:
                lines.extend(['', f'--- {state_coverage.DRIFT_HEADING} ---', state_coverage.DRIFT_RULE])
                for path, group in self._group_by_scope(drifting):
                    lines.append(self._report_section_header(path))
                    for row in group:
                        lines.append(state_coverage.drift_line(row))


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
        self.write_root_file(entry_coverage.REPORT_FILE, content)
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

        out = UnitText(self, 'vpn.tf',
                       '# IPsec VPN Configuration\n'
                       '# IMPORTANT: Pre-shared keys are set to generic placeholders.\n'
                       '# You MUST update all pre-shared keys before applying!\n'
                       '# Search for "***CHANGE_ME***" and replace with actual keys.\n\n')

        # IKE Crypto Profiles (v2: encryption/hash/dh_group lists + lifetime block)
        if ike_profiles:
            for facts in self.units_of(ike_profiles):
                out.add_once(facts, '# IKE Crypto Profiles\n\n')
            for profile in ike_profiles:
                resource_name = self.declare_resource_name(
                    f"ike_profile_{profile['name']}", 'panos_ike_crypto_profile', profile,
                    context=self.scope_context(profile), vsys=profile.get('vsys') or ''
                )
                out.add(profile, f'resource "panos_ike_crypto_profile" "{resource_name}" {{\n')
                out.add(profile, self.location_block('panos_ike_crypto_profile', profile, resource_name))
                out.add(profile, f'  name = {self.escape_string(profile["name"])}\n')

                if profile.get('encryptions'):
                    enc_str = ', '.join([self.escape_string(e) for e in profile['encryptions']])
                    out.add(profile, f'  encryption = [{enc_str}]\n')

                # v2 calls the hash algorithms hash (not authentication)
                if profile.get('authentications'):
                    auth_str = ', '.join([self.escape_string(a) for a in profile['authentications']])
                    out.add(profile, f'  hash = [{auth_str}]\n')

                if profile.get('dh_groups'):
                    dh_str = ', '.join([self.escape_string(dh) for dh in profile['dh_groups']])
                    out.add(profile, f'  dh_group = [{dh_str}]\n')

                if profile.get('lifetime_hours'):
                    try:
                        hours = int(profile['lifetime_hours'])
                    except (TypeError, ValueError):
                        hours = None
                    if hours is not None:
                        out.add(profile, f'  lifetime = {self.hcl_value({"hours": hours})}\n')

                out.add(profile, '}\n\n')

        # IPsec Crypto Profiles (v2: esp object + dh_group string + lifetime/lifesize)
        if ipsec_profiles:
            for facts in self.units_of(ipsec_profiles):
                out.add_once(facts, '# IPsec Crypto Profiles\n\n')
            for profile in ipsec_profiles:
                profile_key = f"ipsec_profile_{profile['name']}"
                resource_name = self.declare_resource_name(
                    profile_key, 'panos_ipsec_crypto_profile', profile,
                    context=self.scope_context(profile), vsys=profile.get('vsys') or ''
                )
                out.add(profile, f'resource "panos_ipsec_crypto_profile" "{resource_name}" {{\n')
                out.add(profile, self.location_block('panos_ipsec_crypto_profile', profile, resource_name))
                out.add(profile, f'  name = {self.escape_string(profile["name"])}\n')

                # v2 dh_group is a single string (not a list)
                if profile.get('dh_group'):
                    out.add(profile, f'  dh_group = {self.escape_string(profile["dh_group"])}\n')

                # v2 esp object holds the encryption/authentication algorithms
                esp: dict = {}
                if profile.get('encryptions'):
                    esp['encryption'] = list(profile['encryptions'])
                if profile.get('authentications'):
                    esp['authentication'] = list(profile['authentications'])
                if esp:
                    out.add(profile, f'  esp = {self.hcl_value(esp)}\n')

                if profile.get('lifetime_hours'):
                    try:
                        hours = int(profile['lifetime_hours'])
                    except (TypeError, ValueError):
                        hours = None
                    if hours is not None:
                        out.add(profile, f'  lifetime = {self.hcl_value({"hours": hours})}\n')

                if profile.get('lifetime_kb'):
                    try:
                        kb = int(profile['lifetime_kb'])
                    except (TypeError, ValueError):
                        kb = None
                    if kb is not None:
                        out.add(profile, f'  lifesize = {self.hcl_value({"kb": kb})}\n')

                out.add(profile, '}\n\n')

        # IKE Gateways (v2: protocol/peer_address/authentication blocks)
        if ike_gateways:
            for facts in self.units_of(ike_gateways):
                out.add_once(facts, '# IKE Gateways\n')
                out.add_once(facts, '# WARNING: Pre-shared keys use placeholder "***CHANGE_ME***"\n')
                out.add_once(facts, '# Update these with actual keys from your key management system!\n\n')

            for gw in ike_gateways:
                resource_name = self.declare_resource_name(
                    f"ike_gw_{gw['name']}", 'panos_ike_gateway', gw,
                    context=self.scope_context(gw), vsys=gw.get('vsys') or ''
                )
                out.add(gw, f'resource "panos_ike_gateway" "{resource_name}" {{\n')
                out.add(gw, self.location_block('panos_ike_gateway', gw, resource_name))
                out.add(gw, f'  name = {self.escape_string(gw["name"])}\n')

                # v2 protocol object: version + ikev1/ikev2 sub-object
                version = gw.get('version', 'ikev1')
                if version in ('ikev1', 'ikev2'):
                    proto_obj: dict = {'version': version}
                    ver_obj: dict = {}
                    if gw.get('ike_crypto_profile'):
                        ike_key = f"ike_profile_{gw['ike_crypto_profile']}"
                        # F2.6: reference when declared in this run, else
                        # plain name; F3.2, F6.10.2: resolve inside the gateway's unit
                        ver_obj['ike_crypto_profile'] = self.name_ref(
                            gw['ike_crypto_profile'], IKE_CRYPTO_SCOPES,
                            key=ike_key, referrer=gw)
                    if ver_obj:
                        proto_obj[version] = ver_obj
                    out.add(gw, f'  protocol = {self.hcl_value(proto_obj)}\n')

                if gw.get('peer_address'):
                    # v2 peer_address object keyed by fqdn or ip
                    key = 'fqdn' if gw.get('peer_address_type') == 'fqdn' else 'ip'
                    out.add(gw, f'  peer_address = {self.hcl_value({key: gw["peer_address"]})}\n')

                if gw.get('local_address_interface'):
                    # F2.6: reference when the interface is in this run;
                    # F3.2, F6.10.2: resolve inside the gateway's unit
                    iface_ref = self.name_ref(
                        gw['local_address_interface'], INTERFACE_SCOPES,
                        referrer=gw)
                    out.add(gw, f'  local_address = {self.hcl_value({"interface": iface_ref})}\n')
                elif gw.get('local_address'):
                    # Heuristic: dotted-quad values are IPs, otherwise
                    # interfaces; F3.2, F6.10.2: resolve inside the gateway's unit
                    local = gw['local_address']
                    key = 'ip' if self._looks_like_ip(local) else 'interface'
                    value = (self.name_ref(local, INTERFACE_SCOPES,
                                           referrer=gw)
                             if key == 'interface' else local)
                    out.add(gw, f'  local_address = {self.hcl_value({key: value})}\n')

                # v2 authentication object; pre-shared key only (cert auth is manual)
                auth_type = gw.get('auth_type', 'pre-shared-key')
                if auth_type == 'pre-shared-key' and gw.get('pre_shared_key'):
                    key_obj = self.hcl_value({'pre_shared_key': {'key': gw['pre_shared_key']}})
                    out.add(gw, f'  authentication = {key_obj}  # *** CHANGE THIS KEY ***\n')

                if gw.get('local_id'):
                    out.add(gw, f'  local_id = {self.hcl_value({"id": gw["local_id"]})}\n')

                if gw.get('peer_id'):
                    out.add(gw, f'  peer_id = {self.hcl_value({"id": gw["peer_id"]})}\n')

                out.add(gw, '}\n\n')

        # IPsec Tunnels (v2: auto_key block with nested proxy_id entries)
        if ipsec_tunnels:
            for facts in self.units_of(ipsec_tunnels):
                out.add_once(facts, '# IPsec Tunnels\n\n')
            for tunnel in ipsec_tunnels:
                if tunnel.get('type') != 'auto-key':
                    # Manual-key tunnels need key material: manual-setup report only
                    continue

                resource_name = self.declare_resource_name(
                    f"tunnel_{tunnel['name']}", 'panos_ipsec_tunnel', tunnel,
                    context=self.scope_context(tunnel), vsys=tunnel.get('vsys') or ''
                )
                out.add(tunnel, f'resource "panos_ipsec_tunnel" "{resource_name}" {{\n')
                out.add(tunnel, self.location_block('panos_ipsec_tunnel', tunnel, resource_name))
                out.add(tunnel, f'  name = {self.escape_string(tunnel["name"])}\n')

                if tunnel.get('tunnel_interface'):
                    out.add(tunnel, f'  tunnel_interface = {self.escape_string(tunnel["tunnel_interface"])}\n')

                # v2 auto_key object; ike_gateway and proxy_id are lists of objects
                auto_key: dict = {}
                if tunnel.get('ike_gateway'):
                    # F2.6: reference when the gateway is in this run,
                    # else a plain brown-field name (never a phantom
                    # resource); F3.2, F6.10.2: resolve inside the tunnel's unit
                    auto_key['ike_gateway'] = [{'name': self.name_ref(
                        tunnel['ike_gateway'], IKE_GATEWAY_SCOPES,
                        key=f"ike_gw_{tunnel['ike_gateway']}",
                        referrer=tunnel)}]
                if tunnel.get('ipsec_crypto_profile'):
                    ipsec_key = f"ipsec_profile_{tunnel['ipsec_crypto_profile']}"
                    # F2.6: reference when declared in this run, else
                    # plain name; F3.2, F6.10.2: resolve inside the tunnel's unit
                    auto_key['ipsec_crypto_profile'] = self.name_ref(
                        tunnel['ipsec_crypto_profile'], IPSEC_CRYPTO_SCOPES,
                        key=ipsec_key, referrer=tunnel)

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
                    out.add(tunnel, f'  auto_key = {self.hcl_value(auto_key)}\n')

                out.add(tunnel, '}\n\n')

        out.write()

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

        self.write_root_file('VPN_MIGRATION_REPORT.txt', content)

    # F5.5: the read-through blocks go in the unit's file, so a reader can
    # separate what the run read from what the plan will read.
    READ_THROUGH_FILE = 'read_through.tf'

    def generate_read_through(self):
        """Write the read-through data blocks (F5.5).

        One block per name a reference site needed and this run did not read. The
        file is written only when the run has blocks, so a run that declares no
        read-through scope writes no file and the golden bytes stay unchanged.
        Blocks are in sorted (type, local name) order, so the file is
        byte-identical between two runs on the same bytes.

        F6.10.3: a block belongs to the unit its location names, so the file is one per unit and the
        order is the same sorted order the run read the blocks in.
        """
        if not self._data_blocks:
            return

        header = ('# Read-through data blocks\n\n'
                  '# Each block names an entry this run did not read. A `data` block resolves\n'
                  '# at plan time, so the plan reads the device and fails when the entry is\n'
                  '# not present in the location the block names.\n\n')
        out = UnitText(self, self.READ_THROUGH_FILE, header)
        for block in sorted(self._data_blocks.values(),
                            key=lambda block: (block['type'], block['local'])):
            out.add(block['unit'], f'data "{block["type"]}" "{block["local"]}" {{\n')
            out.add(block['unit'], f'  name = {self.escape_string(block["name"])}\n\n')
            out.add(block['unit'], block['location'])
            out.add(block['unit'], '}\n\n')

        out.write()

    def generate_readme(self):
        """Generate README with usage instructions.

        F5.5: a run that declares read-through scopes adds the label section, so a
        reader knows the plan will call the API. A run that declares no read-through
        scope writes the same README as before.

        F6.10.4: the README names the site record, its printed form, and `imports.tf`, because those are the
        files a reader cannot see from a `.tf` file alone. It names the files and states no row and no value,
        so the rule that no report names a field the site data states still holds for the site record itself.
        """
        # The environment name is stated once, in `source_fetch.API_KEY_ENV`, so the README cannot name a
        # second one (docs/CODEBASE_ASSEMBLY.md §11). The host name is read through the naming rule, so the
        # instruction names the name the table's `operator_supplied` row gives it.
        host = naming.variable_name('hostname')
        head = f'''# Palo Alto Terraform Configuration

This directory contains Terraform configuration files generated from Palo Alto Panorama export.

The run writes one directory per unit the unit manifest names, and each unit directory holds that unit's `.tf`
files and the printed form of its site row. A unit is one plan against one state, so run Terraform inside one
unit directory.

## Prerequisites

1. Install Terraform (>= 1.14, the minimum the `terraform` block declares,
   because an `action` block is 1.14 syntax)
2. Install the Palo Alto Networks PAN-OS provider

## Configuration

1. Set the API key in the environment the provider reads:

```bash
export {source_fetch.API_KEY_ENV}="your-api-key"
```

2. Set the host in `terraform.tfvars` (do not commit the file). The run declares the name and writes no value
   for it:

```hcl
{host} = "your-panorama-hostname-or-ip"
```

Or set it with the environment variable Terraform reads for a declared variable:
```bash
export TF_VAR_{host}="your-panorama-hostname-or-ip"
```

3. Initialize Terraform:
```bash
terraform init
```

4. Review the plan:
```bash
terraform plan
```

5. Apply the configuration:
```bash
terraform apply
```

## File Structure

The generator writes a file only when it has content, so a run produces the
subset below that matches the input.

Terraform configuration, one file per unit inside the unit directory the manifest names:

- `provider.tf` - Provider configuration. The block prints the host through the variable the run declares, and
  names the environment the provider reads for the key
- `variables.tf` - The names the run declares: the site values, the reference-only names, and the facts the tool
  cannot read
- `scope.tf` - The scope objects (device group, template, template stack, template variable,
  virtual system), one block per scope entry, written before the config inside them
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
- `imports.tf` - the import rows for a name this run references but did not read, written before
  the blocks that reference the name
- `actions.tf` - the commit and push actions, one block per action the provider schema declares for
  each unit the manifest names, written last
- `site.auto.tfvars` - the printed form of this unit's row in `SITE_DATA.json`

Reports, at the codebase root:

- `SOURCE.txt` - what this run read, as `field: value` data, one record per source read: the
  source kind, the source name, the path, the scope, the request identity, the cache entry, the
  size, and the SHA-256 hex of the bytes the input door parsed
- `CONVERSION_REPORT.txt` - one line per entry the parse read, with its destination, and the
  shadow section for a run that declares a parent source
- `MANUAL_SETUP_REPORT.txt` - objects the provider cannot model, and the reasons
- `INTERFACE_MIGRATION_REPORT.txt` - interfaces and IP addresses to set on the target
- `VPN_MIGRATION_REPORT.txt` - VPN objects and pre-shared key actions
- `SANITY_REPORT.txt` - the post-run gate result
'''

        # F5.5 label. Deterministic: the sorted scopes, then the block count. The
        # tool cannot know which scope holds a name outside the run, so the label
        # states what a reader must check.
        label = ''
        if self.data_scopes:
            label = (
                '\n## Read-through data blocks\n\n'
                f'This run declares read-through scopes '
                f'({", ".join(sorted(self.data_scopes))}) and writes '
                f'`{self.READ_THROUGH_FILE}` with {len(self._data_blocks)} data blocks for '
                'names this run did not read.\n\n'
                'A `data` block resolves at plan time, so `terraform plan` reads the device '
                'and fails when a name is not present in the location the block names. '
                '`terraform validate` cannot check it. Each block carries the location of '
                'the reference that needed the name, because no rule here names the scope '
                'that holds an entry outside the run, so check each block against the '
                'device before applying.\n'
            )

        # F6.10.4 label: the site half names files a reader cannot see from a `.tf` file alone, so the README
        # names them. The label states no row, no value and no mapping result, so the rule that no report names
        # a field the site data states still holds for the site record. Deterministic: fixed text, no count, no
        # path, no timestamp.
        site_label = (
            '\n## Site values\n\n'
            f'The run writes `{site_data.SITE_DATA_FILE}` at the codebase root, one row per unit it recorded a '
            f'site value for, and writes the printed form of that row as `{site_data.TFVARS_FILE}` inside the '
            'unit directory. Set the values there, or with `TF_VAR_<name>`.\n\n'
            'The tool names a variable for a site fact it cannot read, so it writes no row and no line for it: '
            '`target` for a unit that plans against a device, and '
            f'`{naming.variable_name("hostname")}` for every unit. The operator supplies both in '
            '`terraform.tfvars`. A value the provider marks `sensitive` follows the same rule: the run holds it '
            'to decide the name and never writes it.\n'
        )

        tail = '''
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

        self.write_root_file('README.md', head + site_label + label + tail)


def main():
    parser = argparse.ArgumentParser(
        description='Convert Palo Alto Panorama XML output to Terraform configuration'
    )
    # F5.2: the input is a declared source. The file source is the default and
    # behaves as before; the api source reads the cached API export.
    parser.add_argument(
        'input_file',
        nargs='?',
        help='Input XML file from Panorama (the source when --source file, the default)',
    )
    parser.add_argument(
        '--source',
        choices=('file', 'api'),
        default='file',
        help='where the input comes from: a file (default) or the Panorama API export (F5.2)',
    )
    parser.add_argument(
        '--host',
        help='Panorama host for --source api; https only, a bare host is read as https',
    )
    # F5.4: a per-scope run reads one scope instead of the whole config, and the declared
    # parent scope is the second source the shadow scan reads.
    parser.add_argument(
        '--path',
        help='scope path for --source api, as /<container> or /<container>/entry/<name>. '
             'The request reads that scope, not the whole config (F5.4)',
    )
    parser.add_argument(
        '--parent',
        help='parent scope path for --source api, read as the second source for the '
             'shadow scan (F5.4). Needs --path',
    )
    # F5.6: the state document is a reference source, so it applies to any source kind:
    # the run reads it for the ownership and drift facts and writes no output from it.
    parser.add_argument(
        '--state',
        help='Terraform state document to read as a reference source (F5.6). The ownership '
             'and drift sections report the entries it already owns',
    )
    parser.add_argument(
        '--workspace',
        help='the workspace the state document belongs to, so the record can name it. '
             'Needs --state (F5.6)',
    )
    # F5.5: the read-through opt-in. Off by default, so a run that declares no
    # scope writes the same bytes as before.
    parser.add_argument(
        '--data-blocks',
        action='append',
        metavar='SCOPE',
        help='a reference scope this run may read through, as a provider data source type. '
             'Repeatable, or a comma-separated list. A name that no scope in this run declares '
             f'becomes a data block in {TerraformGenerator.READ_THROUGH_FILE} (F5.5)',
    )
    # F6.4: the import blocks are an opt-in. Off by default, so a run that declares nothing
    # writes the same `.tf` bytes as before (`import_blocks.py` rule 1).
    parser.add_argument(
        '--import-blocks',
        action='store_true',
        help=f'write one import block per entry the run declares, in {import_blocks.IMPORT_FILE}. '
             'The id is base64 of the location object and the entry name (F6.4)',
    )
    parser.add_argument(
        '--cache-dir',
        default=source_fetch.DEFAULT_CACHE_DIR,
        help=f'cache directory for API responses (default: {source_fetch.DEFAULT_CACHE_DIR})',
    )
    # F5.3 rule 4: the prune action is an opt-in that gates a run step, following the `--data-blocks`
    # and `--import-blocks` precedent, so a run that declares nothing keeps its cache. The reference it
    # reads is the record file the run wrote, so it applies to the source kind that has a cache.
    parser.add_argument(
        '--prune-cache',
        action='store_true',
        help='remove the cache entries no record this run wrote references. Off by default, and '
             'applies to --source api, because a file record references no cache entry (F5.3 rule 4)',
    )
    parser.add_argument(
        '--offline',
        action='store_true',
        help='read the cache entry only; never call the network',
    )
    parser.add_argument(
        '--insecure',
        action='store_true',
        help='skip certificate verification for the API request. Verification is on by default',
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

    if args.source == 'file':
        if not args.input_file:
            parser.error('--source file needs an input file')
        if args.offline or args.insecure:
            parser.error('--offline and --insecure apply to --source api, and a file source reads no network')
        # F5.3 rule 4: the prune acts on a cache entry a record references, and a file record states `-`
        # for the cache field, so a file run has nothing to prune.
        if args.prune_cache:
            parser.error('--prune-cache applies to --source api, and a file record references no cache entry')
        # F5.4: a file is one source and holds its own scopes, so a declared scope path
        # has nothing to name.
        if args.path or args.parent:
            parser.error('--path and --parent apply to --source api, and a file source reads one scope: the file')
        # Check if input file exists
        if not os.path.exists(args.input_file):
            print(f"Error: Input file '{args.input_file}' not found")
            return 1
    else:
        if not args.host:
            parser.error('--source api needs --host')
        if args.input_file:
            parser.error('--source api does not take an input file; it reads the cached API export')
        if args.insecure and args.offline:
            parser.error('--insecure applies to the network producer, and --offline never calls one')
        # F5.4: the parent is the second source, so it needs a child scope to compare with.
        # A whole-config source holds its own parent, and the tool does not guess which
        # scope a run reads.
        if args.parent and not args.path:
            parser.error('--parent needs --path: a whole-config source holds its own parent, '
                         'and the converter does not guess which scope a run reads')
        for flag, declared in (('--path', args.path), ('--parent', args.parent)):
            if declared and not container_coverage.is_scope_path(declared):
                parser.error(
                    f'{flag} must name a scope path: /<container> or /<container>/entry/<name>, '
                    f'where <container> is a declared scope container '
                    f'({", ".join(sorted(container_coverage.SCOPE_PATH_ROOTS))})'
                )

    # F5.6: the state source is a reference source, so it applies to both source kinds.
    # The workspace names the state document, so it needs a state document to name.
    if args.workspace and not args.state:
        parser.error('--workspace needs --state: the workspace names the state document, and a '
                     'run that declares no --state reads no state document')

    # F5.5: the read-through scopes are checked before the run. A scope outside the
    # reference sets answers no reference, and a data source that declares no `name`
    # cannot hold the entry name a reference needs, so both are argument errors.
    data_scopes = sorted({scope.strip() for arg in (args.data_blocks or [])
                          for scope in arg.split(',') if scope.strip()})
    if args.data_blocks and not data_scopes:
        parser.error('--data-blocks needs at least one scope')
    for scope in data_scopes:
        if scope not in REFERENCE_SCOPES:
            parser.error(
                f'--data-blocks must name a scope a reference resolves against '
                f'({", ".join(REFERENCE_SCOPES)}); {scope} answers no reference'
            )
        if not DATA_SOURCE_SCHEMA[scope][0]:
            parser.error(
                f'--data-blocks scope {scope} declares no name in the provider schema, so a '
                f'data block for it cannot hold the entry name a reference needs'
            )

    # F5.3: the request the run read, so the provenance record can name the identity. A
    # file run has no request, so the two api fields stay `-`. F5.4 adds the parent
    # request, so the record holds one record per source the run read.
    request = None
    parent_request = None
    parent_source = None
    # F5.6: the state document is the third source the record can name. It has no request,
    # so its two api fields stay `-` and it references nothing.
    state_source = None

    try:
        if args.source == 'file':
            print(f"Parsing Panorama configuration from {args.input_file}...")
            source = parse_xml(args.input_file, args.max_input_bytes)
        else:
            # F5.2: the producer hands bytes to the door, and the cache entry is
            # what gets parsed, so the run names the entry it read.
            request = source_fetch.ApiRequest(host=args.host, path=container_coverage.record_path(args.path))
            print(f"Reading Panorama configuration from the API export of {request.https_host()} "
                  f"(cache entry {request.cache_name()})...")
            source = source_fetch.fetch(
                request, args.cache_dir,
                offline=args.offline, insecure=args.insecure,
                max_input_bytes=args.max_input_bytes)

            # F5.4: the declared parent is the second source, read through the same cached
            # producer, so --offline covers both requests and each request keeps its own
            # cache entry.
            if args.parent:
                parent_request = source_fetch.ApiRequest(host=args.host,
                                                         path=container_coverage.record_path(args.parent))
                print(f"Reading the parent scope '{parent_request.path}' from the same host "
                      f"(cache entry {parent_request.cache_name()})...")
                parent_source = source_fetch.fetch(
                    parent_request, args.cache_dir,
                    offline=args.offline, insecure=args.insecure,
                    max_input_bytes=args.max_input_bytes)

        # F5.6: the state document is the third source the run reads, and it is read as a
        # file. A state read is a file read, so --offline needs no new rule: no producer is
        # called for it. It is a reference source, so the run writes no output from it.
        if args.state:
            print(f"Reading the state document {args.state} as a reference source "
                  f"(workspace {args.workspace or DEFAULT_SCOPE})...")
            state_source = state_input.read_state(args.state, workspace=args.workspace,
                                                   max_input_bytes=args.max_input_bytes)

        panorama = PanoramaParser(source)

        print("Extracting configuration elements...")
        device_groups = panorama.parse_device_groups()

        # F6.5: the scopes are objects the output writes, so the other scope containers have a
        # parse method each, and the emitter writes them before the config inside them.
        templates = panorama.parse_templates()
        template_stacks = panorama.parse_template_stacks()
        template_variables = panorama.parse_template_variables()
        virtual_systems = panorama.parse_vsys()

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
        filter_containers = panorama.parse_filter_containers()  # F7.8
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

        # Dynamic routing (F7.1): the protocol levels belong to the router record, so no separate parse
        # call builds a routing record any more. `_parse_router` fills the `protocol` field, and the
        # entries inside a level are marked there.
        protocol_routers = [r for r in all_routers if any((r.get('protocol') or {}).values())]

        # VPN configurations
        ike_gateways = panorama.parse_ike_gateways()
        ipsec_tunnels = panorama.parse_ipsec_tunnels()
        ike_crypto_profiles = panorama.parse_ike_crypto_profiles()
        ipsec_crypto_profiles = panorama.parse_ipsec_crypto_profiles()

        print("\nFound:")
        print(f"  - {len(device_groups)} device groups")
        print(f"  - {len(templates)} templates")
        print(f"  - {len(template_stacks)} template stacks")
        print(f"  - {len(template_variables)} template variables")
        print(f"  - {len(virtual_systems)} virtual systems")
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

        # Dynamic routing (F7.1): the counts come from the protocol levels of the router record, so the
        # summary names the same entries the `.tf` file prints.
        if protocol_routers:
            print(f"  - {len(protocol_routers)} router(s) with a routing protocol")
            for router in protocol_routers:
                parts = []
                bgp = (router.get('protocol') or {}).get('bgp') or {}
                if bgp:
                    groups = bgp.get('peer_group') or []
                    parts.append(
                        f"bgp: AS {bgp.get('local_as')}, {len(groups)} peer groups, "
                        f"{sum(len(group.get('peer') or []) for group in groups)} peers, "
                        f"{len(bgp.get('redist_rules') or [])} redistribution rules")
                ospf = (router.get('protocol') or {}).get('ospf') or {}
                if ospf:
                    parts.append(f"ospf: {len(ospf.get('area') or [])} areas")
                print(f"    {router['name']}: " + ', '.join(parts))

        # VPN
        print(f"  - {len(ike_gateways)} IKE gateways")
        print(f"  - {len(ipsec_tunnels)} IPsec tunnels")

        print(f"\nGenerating Terraform configuration in {args.output_dir}...")
        tf_gen = TerraformGenerator(args.output_dir, panorama.parse_associations(),
                                    data_scopes=data_scopes, ledger=panorama.ledger)

        # F4.4: the property scan measures which keys an output reads from a captured
        # object, so the record starts here and not during the parse.
        panorama.ledger.start_recording()

        # Core configuration
        tf_gen.generate_provider_config()

        # F6.5: the scope objects come before the config inside them (`docs/CODEBASE_ASSEMBLY.md`
        # §6), so `scope.tf` is the first object file the run writes.
        tf_gen.generate_scope_objects(device_groups, templates, template_stacks,
                                      template_variables, virtual_systems)

        # New: Tags and URL/App objects
        tf_gen.generate_tags(tags)
        tf_gen.generate_custom_url_categories(custom_url_categories)
        tf_gen.generate_application_groups(application_groups)
        # Application filters have no v2 resource: they go to the manual setup report
        tf_gen.generate_external_lists(external_lists)
        # F2.9: schedules go to the manual setup report (v2 resource
        # exists, but the parse reads the name, the description and the
        # type only, and v2.0.14 has no monthly schedule support)

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
        tf_gen.generate_filter_containers(filter_containers)  # F7.8

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

        # Items that are not emitted (F2.9): the routing protocol entries no provider field reaches
        # (F7.1), app filters, manual-key tunnels, app override, QoS, IPsec tunnel monitor, and log
        # forwarding + zone protection + schedules (v2 resource exists, profile body not parsed). See
        # resource_mapping.py.
        manual_key_tunnels = [t for t in ipsec_tunnels if t.get('type') != 'auto-key']
        # F4.2: scan the parsed input for a section container the container
        # table does not cover. A finding is an operator action, not a broken
        # output, so it does not change the exit code (the F4.1 gate does).
        coverage_findings = container_coverage.scan(panorama.source, panorama.parent_map)
        tf_gen.generate_manual_setup_report(
            entry_coverage.protocol_report_rows(panorama.ledger), application_filters, manual_key_tunnels,
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
            entry_report=container_coverage.render_section(coverage_findings, panorama.source.name),
        )

        # F5.5: the read-through blocks, the unit's file, written before the
        # reports so the label can state the count and the gate can read the file.
        tf_gen.generate_read_through()

        # F6.6: `variables.tf` is written after the emitters, because the declaration set is the site
        # values the value-to-variable table mapped at the print sites (`generate_variables`). A file
        # written before the emitters could not state what the run consumed.
        tf_gen.generate_variables()

        # Reports
        tf_gen.generate_interface_report(interfaces)
        tf_gen.generate_readme()

        # F4.3: one line per entry the parse pipeline read. A gap is an operator
        # action, not a broken output, so it does not change the exit code (the
        # F4.1 gate does).
        # F5.4: the parent ledger is read with the same row rule, so the matrix row that
        # covers a parent entry is the row that covers the child entry. A run with no
        # declared parent has no shadow to report.
        parent_ledger = entry_coverage.EntryLedger(parent_source) if parent_source is not None else None
        shadows = shadow_coverage.shadow_findings(panorama.ledger, parent_ledger)
        # F6.2: ownership as data. Both sources are read with the same row rule, so the matrix row that
        # covers a run entry is the row that covers a parent entry. A finding is an operator action, so
        # it does not change the exit code (the F4.1 gate does), and the console prints no line for it.
        ownership_rows = ownership.build_rows(panorama.ledger, parent_ledger, tf_gen.sanitize_name)
        # F6.3: the reference between units as an edge list. The pair comes from the names `name_ref`
        # recorded at the sites that applied the rule, joined to the ownership rows on (`type`, `entry`),
        # so no second resolution rule and no second naming rule appears here. A cycle is an operator
        # action, so it does not change the exit code (the F4.1 gate does), and the console prints no line
        # for it.
        edge_rows = reference_edges.build_rows(ownership_rows, tf_gen.unit_references(),
                                               tf_gen.sanitize_name)
        # F6.1: the unit as data. One row per declared scope, from the ledger the parse already
        # writes and the names `name_ref` recorded at the sites that applied the rule. Written as
        # data, so an orchestrator reads it (docs/CODEBASE_ASSEMBLY.md §13), and written only when
        # it has content, following the rule for the report files. F6.1 names the directory a later
        # feature writes; it does not write one. F6.3 fills the two order fields, because the order
        # comes from the three rules `reference_edges.py` states. The rows are built before the
        # report, because a cycle finding reads its grouping facts through the manifest row.
        manifest_rows = reference_edges.order(
            unit_manifest.build_rows(panorama.ledger, tf_gen.unit_references(), tf_gen.sanitize_name),
            ownership_rows, edge_rows)
        # F5.6: the state scan reads the same row rule, so the matrix row that covers a run
        # entry is the row that covers the state resource. A run with no declared state source
        # has no state to read, so it reports neither fact.
        state_findings = state_coverage.state_findings(panorama.ledger, state_source)
        tf_gen.generate_conversion_report(panorama.ledger, shadows, state_findings,
                                          ownership.findings(ownership_rows),
                                          reference_edges.findings(edge_rows, manifest_rows))

        # F5.3: the provenance record. Written outside the report bodies, so the report
        # byte rule still holds: a report body names the source name, and the record is
        # the file that names the path. Written as data, so the cache reference a prune
        # action reads is the `cache_entry` field, not a printed line. F5.4: one record per
        # source the run read, in read order, so the shadow line names a source a reader
        # can check against the record.
        records = [provenance.record_for(panorama.source, request=request)]
        if parent_request is not None:
            records.append(provenance.record_for(parent_source, request=parent_request))
        # F5.6: the state source is read last, so its record is last. It has no request, so
        # the two api fields stay `-` and the record references nothing: it prunes nothing.
        if state_source is not None:
            records.append(provenance.record_for(state_source))
        # F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): a record describes the whole codebase, so it is a
        # codebase root-set file and goes through the one write path at the root.
        record_file = write_path.root_path(args.output_dir, provenance.PROVENANCE_FILE)
        write_path.write_file(record_file, provenance.render_records(records))

        # F6.1: the manifest is written as data, so an orchestrator reads it. The rows are built
        # above, before the report, because a cycle finding reads its grouping facts through them.
        if manifest_rows:
            write_path.write_file(write_path.root_path(args.output_dir, unit_manifest.MANIFEST_FILE),
                                unit_manifest.render(manifest_rows))

        # F6.2: the ownership record. One row per entry the coverage matrix covers, written as data,
        # and only when it has content, following the rule for the report files and the manifest. It
        # names the unit that declares each entry and the unit that owns its name, so a reader joins it
        # to the manifest row on `directory`.
        if ownership_rows:
            write_path.write_file(write_path.root_path(args.output_dir, ownership.OWNERSHIP_FILE),
                                ownership.render(ownership_rows))

        # F6.3: the edge record. One row per pair the data can name, written as data, and only when it has
        # content, following the rule for the report files and the two data files. A reader joins `referrer`
        # and `target` to the manifest row on `directory`, and (`type`, `entry`) to the ownership row.
        if edge_rows:
            write_path.write_file(write_path.root_path(args.output_dir, reference_edges.EDGE_FILE),
                                reference_edges.render(edge_rows))

        # F6.6: the site data. One row per site that names a value, written as data, and only when it has
        # content, following the rule for the report files and the other data files. A reader joins
        # `directory` to the manifest row. The `.tfvars` is written from the rows, not from the generator's
        # state. The gate rule `data_files` (F6.8) reads the record through `parse_rows` and compares the
        # printed form with `render_tfvars` (`ARCHITECTURE.md` §4.5), so the run writes both or neither.
        site_rows = site_data.build_rows(panorama.ledger, tf_gen.value_variables(), tf_gen.sanitize_name)
        if site_rows:
            write_path.write_file(write_path.root_path(args.output_dir, site_data.SITE_DATA_FILE),
                                    site_data.render(site_rows))
            # F6.10.3: the printed form is the unit's file, so the run writes one per unit that names a value,
            # each holding the printed form of that unit's row.
            for row in site_rows:
                write_path.write_file(write_path.unit_path(args.output_dir, row['directory'], site_data.TFVARS_FILE),
                                      site_data.render_tfvars([row]))

        # F6.4: the import blocks. A `.tf` file, because the gate rule that checks an import block reads the
        # files the operator receives (`ARCHITECTURE.md` §4.5), and written only when the run declares them and
        # has rows that state an id. A row that states a rule instead of an id writes no block.
        import_rows = [row for row in tf_gen.import_rows if row['import_id']]
        if args.import_blocks and import_rows:
            # F6.10.3: `imports.tf` is a `.tf` file, so it is the unit's file and the run writes one per
            # unit that has a block. `render` prints rows in unit order, so a unit's blocks print in the
            # same order the run read them.
            for facts in tf_gen.unit_set():
                directory = tf_gen.directory_of(facts)
                unit_rows = [row for row in import_rows if row['unit'] == directory]
                if unit_rows:
                    write_path.write_file(write_path.unit_path(args.output_dir, directory, import_blocks.IMPORT_FILE),
                                          import_blocks.render(unit_rows))

        # F6.7: the commit actions. One block per unit the manifest names, written as the last `.tf`
        # file so the gate rule reads the action against the completed unit, and only when it has
        # content, following the rule for the report files and the four data files. Emission is default:
        # the committed goldens pin what a default run emits, so a shape written only behind a flag could
        # not be pinned (the F6.5 rule 1 argument).
        action_rows = commit_actions.build_rows(manifest_rows, tf_gen.sanitize_name)
        if action_rows:
            # F6.10.3: `actions.tf` is the last `.tf` file of a unit, so the run writes one per unit the
            # manifest names, and each file holds that unit's block.
            for facts in tf_gen.unit_set():
                directory = tf_gen.directory_of(facts)
                unit_rows = [row for row in action_rows if row['directory'] == directory]
                if unit_rows:
                    write_path.write_file(write_path.unit_path(args.output_dir, directory, commit_actions.ACTIONS_FILE),
                                          commit_actions.render(unit_rows))

        print("\n✓ Successfully generated Terraform configuration!")
        print("\n📄 Generated Migration Reports:")
        print("  - INTERFACE_MIGRATION_REPORT.txt (Interface and IP inventory)")
        if panorama.ledger.rows():
            print("  - CONVERSION_REPORT.txt (one line per entry the parser read)")
        if ike_gateways or ipsec_tunnels:
            print("  - VPN_MIGRATION_REPORT.txt ⚠️  (VPN config with key management instructions)")
        print(f"Provenance record: {record_file}")

        # F4.2: one console line per uncovered section, so a run that read an
        # entry it cannot model is visible without opening the report. Every line here
        # is built by `container_coverage.console_line`, the one place the console line shape
        # is stated (`docs/ARCHITECTURE.md` §3.2), and each block prints only when it has a finding.
        coverage_console = container_coverage.console_lines(coverage_findings)
        if coverage_console:
            print()
            for line in coverage_console:
                print(line)

        # F4.3: entry totals, then one console line per gap entry. A gap is an
        # operator action, not a broken output, so it does not change the exit
        # code (the F4.1 gate does). No console line when the run has no gap.
        # F4.4 and F5.4: the property and shadow blocks print too, in the report section order. A console
        # line names the entry, its position, and its fact, and no matrix row, because a console line has
        # no room for the report's fixed-width column; the report keeps it. The shadow line names the
        # parent source by its name, the minimum actionable field: the path is in the provenance record.
        gap_console = entry_coverage.console_lines(panorama.ledger, tf_gen._report_scope_path)
        property_console = entry_coverage.property_console_lines(
            panorama.ledger.property_findings(), tf_gen._report_scope_path)
        shadow_console = shadow_coverage.console_lines(shadows, tf_gen._report_scope_path)
        if gap_console or property_console or shadow_console:
            print()
            for block in (entry_coverage.summary_lines(panorama.ledger),
                          gap_console, property_console, shadow_console):
                for line in block:
                    print(line)
            print(f"Per-entry report file: {Path(args.output_dir) / entry_coverage.REPORT_FILE}")

        # F4.1: the gate reads the files that were written, so it reports what
        # the operator receives. A WARN does not fail the gate; a FAIL does.
        # The four data files are written above, so the data rule (F6.8) reads the records the run wrote.
        report = sanity_checks.run_checks(args.output_dir, run_terraform=args.validate)
        report_path = write_path.root_path(args.output_dir, 'SANITY_REPORT.txt')
        write_path.write_file(report_path, report.render())
        print()
        print(report.console_summary())
        print(f"Sanity report: {report_path}")

        print("\nNext steps:")
        print(f"  1. cd {args.output_dir}")
        print("  2. Review INTERFACE_MIGRATION_REPORT.txt for interface mapping")
        if ike_gateways or ipsec_tunnels:
            print("  3. ⚠️  Review VPN_MIGRATION_REPORT.txt and update pre-shared keys!")
        print("  4. Review the generated .tf files")
        print("  5. Set the host in terraform.tfvars (do not commit the file), and set the key in the "
              f"environment ({source_fetch.API_KEY_ENV})")
        if ike_gateways or ipsec_tunnels:
            print("  6. ⚠️  Add VPN pre-shared keys to terraform.tfvars (DO NOT COMMIT)")
        # F6.10.3: a unit is one plan against one state, so the plan runs inside the unit directory the
        # manifest names.
        print("  7. Run: terraform init inside one unit directory the manifest names")
        print("  8. Run: terraform plan")
        print("  9. Run: terraform apply")

        # F4.1: a FAIL finding is a broken output, so the conversion reports it
        # with a non-zero exit code instead of writing files and exiting 0.
        code = 1 if report.failed else 0

        # F5.3 rule 4: the prune runs last, because the reference is the record file the run wrote,
        # and it is the file the gate does not read, so the code the gate decided does not move. The
        # action reads that file back through `parse_records`, so the reference stays data. A record the
        # action cannot read is a refusal, so the run exits 1, and the message names the record file, not
        # the input file. A prune that removes nothing prints nothing and changes nothing.
        if args.prune_cache:
            try:
                pruned = provenance.prune(record_file, args.cache_dir)
            except ValueError as e:
                print(f"Error: {e}")
                return 1
            if pruned:
                print()
                print(f"Cache prune: {len(pruned)} entries no written record referenced")
                for entry in pruned:
                    print(f"  - {entry.name}")

        return code

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
