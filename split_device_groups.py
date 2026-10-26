#!/usr/bin/env python3
"""
Panorama Device Group Splitter

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

Splits a Panorama export into one XML file per device group. Each file holds the
device group entry, the shared section, and the templates and template stacks that
target a device the group lists. This step is optional: the converter reads a full
export on its own. See docs/DEVICE_GROUP_SPLITTING.md for the join rule and the
usage.
"""

import argparse
import copy
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from xml_input import (
    DEFAULT_MAX_INPUT_BYTES,
    UnsafeInputError,
    add_max_input_argument,
    parse_xml,
)


def parse_device_groups(root: ET.Element) -> list:
    """Get list of device groups from Panorama config"""
    device_groups = []
    seen = set()

    for dg in root.findall(".//device-group/entry"):
        name = dg.get('name')
        if name and name not in seen:
            device_groups.append(name)
            seen.add(name)

    return device_groups


def _device_names(entry: ET.Element) -> list:
    """Return the device names one entry lists.

    A Panorama export lists members two ways: the long form
    `<devices><entry name="fw-1.example.com">` and the short form
    `<devices><member>fw-1.example.com</member>`.
    """
    names = []
    listing = entry.find('devices')
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


def _entries_by_device(root: ET.Element, container_tags: tuple) -> dict:
    """Map entry name to its elements and the device names it lists.

    `container_tags` holds the spellings one kind appears under: a real
    export writes `<templates>`, and the split files this script writes are
    read back the same way, so both are accepted.
    """
    table = {}
    for tag in container_tags:
        for entry in root.findall(f'.//{tag}/entry'):
            name = entry.get('name')
            if not name:
                continue
            row = table.setdefault(name, {'devices': set(), 'elements': []})
            row['devices'].update(_device_names(entry))
            row['elements'].append(entry)
    return table


def device_associations(root: ET.Element) -> dict:
    """Return the device membership the export declares (F3.6).

    A Panorama export states the multi-device relationships in data:

        device-group/entry/<DG>/devices/entry/<device>
        templates/entry/<template>/devices/entry/<device>
        template-stack/entry/<stack>/devices/entry/<device>

    A device group and a template belong together when they list the same
    device. That join replaces the old `DG-` prefix convention and the
    substring test, both of which matched names rather than facts.

    Returns {'device_groups': table, 'templates': table,
    'template_stacks': table}; each table maps a name to
    {'devices': set, 'elements': [entry, ...]}. An export that lists no
    device returns tables that associate nothing, which is the honest
    answer: no copy, and a printed note saying so.
    """
    return {
        'device_groups': _entries_by_device(root, ('device-group',)),
        'templates': _entries_by_device(root, ('templates', 'template')),
        'template_stacks': _entries_by_device(
            root, ('template-stack', 'template-stacks')),
    }


def _associated_names(associations: dict, kind: str, devices: set) -> list:
    """Return the entries of one kind that list at least one of `devices`."""
    if not devices:
        return []
    return sorted(name for name, row in associations[kind].items()
                  if row['devices'] & devices)


def extract_device_group_config(root: ET.Element, device_group_name: str,
                                associations: dict = None) -> ET.Element:
    """Extract configuration for a specific device group"""
    # Create new root config element
    new_config = ET.Element('config')
    new_config.set('version', root.get('version', '10.0.0'))

    # Create devices structure
    devices = ET.SubElement(new_config, 'devices')
    localhost = ET.SubElement(devices, 'entry')
    localhost.set('name', 'localhost.localdomain')

    # Find the specific device group. Match the name attribute in Python
    # rather than interpolating it into an XPath string: names may contain
    # quote characters, which would break (or silently mismatch) the XPath.
    source_dg = None
    for dg in root.findall(".//device-group/entry"):
        if dg.get("name") == device_group_name:
            source_dg = dg
            break

    if source_dg is None:
        return None

    # Copy device-group. deepcopy, not append: ElementTree keeps no parent
    # bookkeeping, so append makes the same element object a child of two
    # trees. The split file and the source tree then alias one object, and a
    # later step that mutates either changes the other. A copy keeps each
    # split file independent of the source and of the other split files.
    device_group_container = ET.SubElement(localhost, 'device-group')
    device_group_container.append(copy.deepcopy(source_dg))

    # Copy shared objects (they're referenced by device groups)
    # Note: Panorama configs can have MULTIPLE <shared> sections
    # We need to merge them all to capture all objects
    shared_sections = root.findall('.//shared')
    if shared_sections:
        # Create a merged shared section
        merged_shared = ET.Element('shared')

        # Track what we've added to avoid duplicates
        seen_children = {}

        for shared in shared_sections:
            for child in shared:
                child_tag = child.tag

                # If we haven't seen this tag yet, add a copy of it
                if child_tag not in seen_children:
                    merged_shared.append(copy.deepcopy(child))
                    seen_children[child_tag] = merged_shared[-1]
                else:
                    # If the tag exists, merge in copies of the new entries
                    existing = seen_children[child_tag]
                    existing_names = [e.get('name') for e in existing.findall('.//entry')]
                    for entry in child.findall('.//entry'):
                        entry_name = entry.get('name')
                        # Only add if not already present
                        if entry_name and entry_name not in existing_names:
                            existing.append(copy.deepcopy(entry))
                            existing_names.append(entry_name)

        new_config.append(merged_shared)

    # Copy the network config the export associates with this device group
    # (F3.6): the templates and template stacks that target one of the
    # device group's own devices. The relationship comes from the device
    # lists, never from a name.
    assoc = associations if associations is not None else device_associations(root)
    dg_devices = assoc['device_groups'].get(device_group_name, {}).get('devices', set())
    labels = {'templates': 'template', 'template_stacks': 'template stack'}

    if not dg_devices:
        print("  - device group lists no devices: no template or "
              "template-stack copied")

    copied = []
    for kind, container_tag in (('templates', 'templates'),
                                ('template_stacks', 'template-stack')):
        names = _associated_names(assoc, kind, dg_devices)
        if not names:
            continue
        container = ET.SubElement(localhost, container_tag)
        for name in names:
            for element in assoc[kind][name]['elements']:
                container.append(copy.deepcopy(element))
            copied.append(f"{labels[kind]}: {name}")

    if dg_devices and not copied:
        print("  - no template or template-stack targets this device group's "
              "devices: none copied")
    for note in copied:
        print(f"  - copied {note}")

    return new_config

def split_panorama_config(input_file: str, output_dir: str = None,
                          max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES):
    """Split Panorama configuration by device group"""
    # F3.8: the same safe read as the converter — a capped input size and a
    # parser-level DTD refusal. Nothing is written before it succeeds.
    try:
        # F4.2: parse_xml returns the tree plus the source line of each element.
        # The splitter writes XML only, so it uses the tree and no line.
        root = parse_xml(input_file, max_input_bytes).root
    except UnsafeInputError as e:
        print(f"Error: {e}")
        return False
    except ET.ParseError as e:
        print(f"Error: Failed to parse XML file: {e}")
        return False

    # Get list of device groups
    device_groups = parse_device_groups(root)

    if not device_groups:
        print("No device groups found in Panorama configuration.")
        print("This may be a single firewall export, not a Panorama export.")
        return False

    print(f"\nFound {len(device_groups)} device groups:")
    for dg in device_groups:
        print(f"  - {dg}")

    # Create output directory
    output_dir = Path(input_file).parent / "split_configs" if output_dir is None else Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nSplitting configurations into: {output_dir}")

    # Extract and save each device group
    for dg_name in device_groups:
        print(f"\nProcessing device group: {dg_name}")

        dg_config = extract_device_group_config(root, dg_name)

        if dg_config is None:
            print(f"  ⚠ Warning: Could not extract config for {dg_name}")
            continue

        # Sanitize filename
        safe_name = dg_name.replace('/', '_').replace(' ', '_')
        output_file = output_dir / f"{safe_name}.xml"

        # Write to file
        tree = ET.ElementTree(dg_config)
        ET.indent(tree, space="  ")
        tree.write(output_file, encoding='utf-8', xml_declaration=True)

        print(f"  ✓ Saved to: {output_file}")

    print(f"\n✓ Successfully split {len(device_groups)} device groups")
    print("\nNext steps:")
    print(f"  1. cd {output_dir}")
    print("  2. Run panorama_to_terraform.py on each XML file:")
    print("     python3 panorama_to_terraform.py <device-group>.xml --output-dir <device-group>-tf")

    return True

def main():
    parser = argparse.ArgumentParser(
        description='Split Panorama configuration by device group',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Split Panorama export into separate device group configs
  python3 split_device_groups.py panorama_export.xml

  # Specify custom output directory
  python3 split_device_groups.py panorama_export.xml --output-dir ./device-groups

  # Then convert each device group separately
  python3 panorama_to_terraform.py device-groups/DG-Internet.xml --output-dir internet-tf
  python3 panorama_to_terraform.py device-groups/DG-DMZ.xml --output-dir dmz-tf
  python3 panorama_to_terraform.py device-groups/DG-Guest.xml --output-dir guest-tf

Use Case:
  When you have a Panorama managing multiple HA pairs (each with its own
  device group), use this script to split the export so you can migrate
  each HA pair to a separate virtual router on your target firewall.
        '''
    )

    parser.add_argument('input_file', help='Panorama XML export file')
    parser.add_argument('--output-dir', '-o', help='Output directory for split configs')
    # F3.8: the same input limit on both entry points.
    add_max_input_argument(parser)

    args = parser.parse_args()

    if not Path(args.input_file).exists():
        print(f"Error: Input file not found: {args.input_file}")
        return 1

    success = split_panorama_config(args.input_file, args.output_dir, args.max_input_bytes)

    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
