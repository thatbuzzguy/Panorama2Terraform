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

Four rules the splitter reads from their owners, and one it states itself:

1. The file name is `naming.py` §5 applied to the device group name, so the splitter states no second naming
   rule and keeps no character of its own. Two names that read the same shape name one file, and that is a
   refusal: a numbering would depend on the order the entries appear in, which §6 says is not a rule a run may
   depend on.
2. The bytes are `write_path.py`'s: the splitter serializes the tree and hands the text to `write_file`, so
   `LF` and the final line come from the single writer. The splitter owns its own output path, because the split
   files are not the unit set or the codebase root set (§14).
3. The tables are `docs/ARCHITECTURE.md` §2.3 rows, keyed by the source line the read layer records (F4.2), so
   one entry is one row and a repeated name is not answered by one entry. The join answers in source line order,
   because §6 preserves the order the input states.
4. The shared merge is the pair (path, name) at the level the path names, and an entry keeps the path it sits at
   (docs/DEVICE_GROUP_SPLITTING.md).
5. The extraction answers through the row it was given, so it states no lookup of its own and can answer no
   absent value. The warning the old code stated for an absent answer is gone with the lookup, because the row
   names an entry the read layer saw.
6. The run prints the fact it read for the shape it read: the row count, the shape the tree holds instead, and the
   source line the read layer records for the entry that shows the shape. It states its own fact phrase and its own
   block header and calls `container_coverage.console_line`, so it builds no console shape of its own, and the row
   rule and the walk rule it already states are the only rules the printed line reads (`docs/INPUT_SHAPES.md` §4).

Usage:
    from split_device_groups import device_associations, parse_device_groups, split_file_names
    rows = parse_device_groups(parse_xml(path))
    names = split_file_names(rows)          # the collision decision, before anything is written
    join = device_associations(source)
    write_file(out / split_file_name(rows[0]['name']), serialize(extract_device_group_config(source, rows[0], join)))
"""

import argparse
import copy
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import container_coverage
import naming
from write_path import LF, write_file
from xml_input import (
    DEFAULT_MAX_INPUT_BYTES,
    ParsedSource,
    UnsafeInputError,
    add_max_input_argument,
    add_member_argument,
    parse_xml,
    read_text,
)


def _row(entry: ET.Element, source: ParsedSource, path: str) -> dict:
    """One row for one entry (§2.3): the source line the read layer records, the container path the entry sits
    at, the name, the entry as the read layer saw it, and the device names it lists.

    The line is the key, so two entries that state one name are two rows. An entry with no name is skipped, as
    §2.3 states, and a name is read through the one whitespace rule the read layer states.
    """
    return {
        "line": source.line_of(entry),
        "path": path,
        "name": read_text(entry.get("name")),
        "entry": entry,
        "devices": _device_names(entry),
    }


def parse_device_groups(source: ParsedSource) -> list:
    """The device group rows, in source line order (§6: the order the input states is preserved on purpose)."""
    table = device_associations(source)["device_groups"]
    return [table[line] for line in sorted(table)]


# The wording the block states for the fact it read, and the honest statement for the part the run cannot name.
# The shape itself is `container_coverage.console_line`, so the block calls it and holds no prefix.
BLOCK_HEADER = "Splitter row set"
NO_ENTRY_SHAPE = "no entry at any path"


def row_fact(count: int) -> str:
    """The fact part of the line: the row count the run read, and the shape the tree holds instead."""
    return f"{count} device-group/entry rows read, so the tree holds the shape named instead"


def tree_shape(source: ParsedSource) -> dict | None:
    """The row for the first entry the tree holds, read through the row rule and the walk rule this module states.

    The module's own tables answer nothing for the firewall export shape, so the fact the run can state is what the
    tree holds instead: the entry at the level the path names. The walk is the rule `merge_shared` states for that
    level, so this function adds no lookup rule of its own, and the row is the shape `_row` defines, which is the
    line the fact prints the parts from.
    """

    def walk(node: ET.Element, path: str) -> dict | None:
        for child in node:
            if child.tag == "entry":
                # The tables answer for a named entry only (§2.3), so an entry with no name shows no shape.
                if read_text(child.get("name")):
                    return _row(child, source, path)
                continue
            found = walk(child, f"{path}/{child.tag}" if path else child.tag)
            if found:
                return found
        return None

    return walk(source.root, "")


def console_lines(source: ParsedSource, rows: list) -> list:
    """The block for the shape the run read: the header, then one console line in the shape the owner states.

    Empty when the run read rows, so a run that reads its own table prints nothing new. The three parts the line
    names are the row count, the shape the tree holds instead, and the source line, and the run states the position
    through `container_coverage.position_part`, which is the honest statement for a finding with no line. The block
    has a fact, so the header carries the marker the owner states for a block that has findings.
    """
    if rows:
        return []
    shape = tree_shape(source)
    return [
        f"{container_coverage.CONSOLE_WARNING}  {BLOCK_HEADER}",
        container_coverage.console_line(
            "",
            container_coverage.position_part(shape["line"] if shape else 0),
            shape["path"] if shape else NO_ENTRY_SHAPE,
            row_fact(len(rows)),
        ),
    ]


def _device_names(entry: ET.Element) -> list:
    """Return the device names one entry lists.

    A Panorama export lists members two ways: the long form
    `<devices><entry name="fw-1.example.com">` and the short form
    `<devices><member>fw-1.example.com</member>`.
    """
    names = []
    listing = entry.find("devices")
    if listing is None:
        return names
    for node in list(listing):
        if node.tag == "entry":
            # Both shapes read the name through the one text rule (`xml_input.read_text`).
            name = read_text(node.get("name"))
        elif node.tag == "member":
            name = read_text(node.text)
        else:
            continue
        if name:
            names.append(name)
    return names


def _entries_by_device(source: ParsedSource, container_tags: tuple) -> dict:
    """The rows for one kind, keyed by the source line (§2.3: no method keeps a name-keyed dict).

    `container_tags` holds the spellings one kind appears under: a real export writes `<templates>`, and
    the split files this script writes are read back the same way, so both are accepted.
    """
    table = {}
    for tag in container_tags:
        for entry in source.root.findall(f".//{tag}/entry"):
            if read_text(entry.get("name")):
                table[source.line_of(entry)] = _row(entry, source, tag)
    return table


def device_associations(source: ParsedSource) -> dict:
    """Return the device membership the export declares (F3.6), as the §2.3 rows keyed by the source line.

    A Panorama export states the multi-device relationships in data:

        device-group/entry/<DG>/devices/entry/<device>
        templates/entry/<template>/devices/entry/<device>
        template-stack/entry/<stack>/devices/entry/<device>

    A device group and a template belong together when they list the same
    device. That join replaces the old `DG-` prefix convention and the
    substring test, both of which matched names rather than facts.

    Returns {'device_groups': table, 'templates': table,
    'template_stacks': table}; each table maps a source line to its row. An
    export that lists no device returns tables that associate nothing, which is
    the honest answer: no copy, and a printed note saying so.
    """
    return {
        "device_groups": _entries_by_device(source, ("device-group",)),
        "templates": _entries_by_device(source, ("templates", "template")),
        "template_stacks": _entries_by_device(source, ("template-stack", "template-stacks")),
    }


def _associated_rows(associations: dict, kind: str, devices: list) -> list:
    """The rows of one kind that list at least one of `devices`, in source line order (§6)."""
    if not devices:
        return []
    held = set(devices)
    table = associations[kind]
    return [table[line] for line in sorted(table) if set(table[line]["devices"]) & held]


def merge_shared(source: ParsedSource) -> ET.Element:
    """Merge the `shared` sections the export states into one section, deduped by the pair (path, name).

    Panorama configs can have MULTIPLE `<shared>` sections. The first occurrence of a path is the container the
    merged section states, and the content that path states comes from that occurrence. Entries from a later
    occurrence are appended at their own path, and the dedupe reads the pair at the level the path names, not a
    name at any depth, so one name at two depths is two entries. An entry inside an entry travels with the copy
    that holds it, because the walk does not enter an entry: the level the path names is the level the dedupe
    reads, which is the same rule `_list_values` states for a `member` list (§2.3).

    Copies, not append: `ElementTree.append` keeps no parent bookkeeping, so appending an entry that already has
    a parent makes one element a child of two trees, and the export would grow an entry per device group.
    """
    merged = ET.Element("shared")
    containers = {"": merged}
    seen = {"": []}

    def merge_level(node: ET.Element, path: str) -> None:
        # A path is a container, an entry is content, so the walk enters the container and stops at the entry.
        for child in node:
            if child.tag == "entry":
                name = read_text(child.get("name"))
                if name and name not in seen[path]:
                    seen[path].append(name)
                    containers[path].append(copy.deepcopy(child))
                continue
            child_path = f"{path}/{child.tag}" if path else child.tag
            if child_path not in containers:
                containers[child_path] = ET.SubElement(containers[path], child.tag)
                seen[child_path] = []
            merge_level(child, child_path)

    for shared in source.root.findall(".//shared"):
        merge_level(shared, "")
    return merged


def split_file_name(name: str) -> str:
    """The file name one device group name reads to: the §5 shape of the name, plus `.xml`."""
    return f"{naming.variable_name(name)}.xml"


def split_file_names(rows: list) -> list:
    """The file names for the rows, in row order, with the collision decision.

    Two names that read the same §5 shape name one file. The numbering a run would have to pick depends on the
    order the entries appear in, which §6 says is not a rule a run may depend on, so the pair is a refusal
    instead. The message names both source names and the file name they read to, so the operator can tell which
    entry is the other one.
    """
    source_name = {}
    for row in rows:
        file_name = split_file_name(row["name"])
        if file_name in source_name:
            raise UnsafeInputError(
                f"two device group names read one file name {file_name}: '{source_name[file_name]}' and '{row['name']}'"
            )
        source_name[file_name] = row["name"]
    return [split_file_name(row["name"]) for row in rows]


def serialize(root: ET.Element) -> str:
    """The text the single writer receives for one tree, with the final line the single writer ends a text with."""
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True) + LF


def extract_device_group_config(source: ParsedSource, row: dict, join: dict) -> ET.Element:
    """Build the tree the run writes for one row: the entry, the merged shared section, and the rows the join
    answers for the devices this row lists.

    The row names an entry the read layer saw, so this function states no lookup of its own and can answer no
    absent value (§2.3). `join` is the association tables, taken as an argument, so the run that reads them
    states the copy notes and this function builds the tree from the same rows.

    The entry is written at the path its row states, which is the same rule the shared merge states: an entry
    keeps the path it sits at, so this function states no container name of its own.
    """
    config = ET.Element("config")
    config.set("version", source.root.get("version", "10.0.0"))

    devices = ET.SubElement(config, "devices")
    localhost = ET.SubElement(devices, "entry")
    localhost.set("name", "localhost.localdomain")

    group = ET.SubElement(localhost, row["path"])
    group.append(copy.deepcopy(row["entry"]))

    # A shared section is written only when the export states one, so a run writes no empty container.
    merged = merge_shared(source)
    if len(merged):
        config.append(merged)

    # The network config the export associates with this device group (F3.6): the rows the join answers for
    # this row's own devices. The relationship comes from the device lists, never from a name.
    containers = {}
    for kind in ("templates", "template_stacks"):
        for joined in _associated_rows(join, kind, row["devices"]):
            # The container is made once per path. `setdefault` would build a second element for a path the
            # container already holds, because it evaluates its default even on a hit.
            if joined["path"] not in containers:
                containers[joined["path"]] = ET.SubElement(localhost, joined["path"])
            containers[joined["path"]].append(copy.deepcopy(joined["entry"]))

    return config


def split_panorama_config(
    input_file: str,
    output_dir: str = None,
    max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
    member: str | None = None,
):
    """Split Panorama configuration by device group"""
    # F3.8: the same safe read as the converter - a capped input size and a
    # parser-level DTD refusal. Nothing is written before it succeeds. F4.2: the read
    # also records the source line, which is what the tables key by. The member declaration is read through the
    # producer, so this states no member rule of its own.
    try:
        source = parse_xml(input_file, max_input_bytes, member)
    except UnsafeInputError as e:
        print(f"Error: {e}")
        return False
    except ET.ParseError as e:
        print(f"Error: Failed to parse XML file: {e}")
        return False

    rows = parse_device_groups(source)

    block = console_lines(source, rows)
    if block:
        print("\n".join(block))
        return False

    # Every file name is read before anything is written, so a pair that names one file stops the run with no
    # output directory behind it.
    try:
        file_names = split_file_names(rows)
    except UnsafeInputError as e:
        print(f"Error: {e}")
        return False

    print(f"\nFound {len(rows)} device groups:")
    for row in rows:
        print(f"  - {row['name']}")

    output_dir = Path(input_file).parent / "split_configs" if output_dir is None else Path(output_dir)
    print(f"\nSplitting configurations into: {output_dir}")

    join = device_associations(source)
    labels = {"templates": "template", "template_stacks": "template stack"}

    # `split_file_names` answers one name per row, so the two sides are the same set: a row with no name
    # for its file would write nothing and report nothing.
    for row, file_name in zip(rows, file_names, strict=True):
        print(f"\nProcessing device group: {row['name']}")

        if not row["devices"]:
            print("  - device group lists no devices: no template or template-stack copied")

        tree = extract_device_group_config(source, row, join)
        copied = [
            f"{labels[kind]}: {joined['name']}"
            for kind in ("templates", "template_stacks")
            for joined in _associated_rows(join, kind, row["devices"])
        ]
        if row["devices"] and not copied:
            print("  - no template or template-stack targets this device group's devices: none copied")
        for note in copied:
            print(f"  - copied {note}")

        output_file = output_dir / file_name
        write_file(output_file, serialize(tree))
        print(f"  ✓ Saved to: {output_file}")

    print(f"\n✓ Successfully split {len(rows)} device groups")
    print("\nNext steps:")
    print(f"  1. cd {output_dir}")
    print("  2. Run src/panorama_to_terraform.py on each XML file:")
    print("     python3 src/panorama_to_terraform.py <device-group>.xml --output-dir <device-group>-tf")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Split Panorama configuration by device group",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Split Panorama export into separate device group configs
  python3 src/split_device_groups.py panorama_export.xml

  # Specify custom output directory
  python3 src/split_device_groups.py panorama_export.xml --output-dir ./device-groups

  # Then convert each device group separately
  python3 src/panorama_to_terraform.py device-groups/dg_internet.xml --output-dir internet-tf
  python3 src/panorama_to_terraform.py device-groups/dg_dmz.xml --output-dir dmz-tf
  python3 src/panorama_to_terraform.py device-groups/dg_guest.xml --output-dir guest-tf

Use Case:
  When you have a Panorama managing multiple HA pairs (each with its own
  device group), use this script to split the export so you can migrate
  each HA pair to a separate virtual router on your target firewall.
        """,
    )

    parser.add_argument("input_file", help="Panorama XML export file")
    parser.add_argument("--output-dir", "-o", help="Output directory for split configs")
    # F3.8: the same input limit on both entry points, and the same member declaration.
    add_max_input_argument(parser)
    add_member_argument(parser)

    args = parser.parse_args()

    if not Path(args.input_file).exists():
        print(f"Error: Input file not found: {args.input_file}")
        return 1

    success = split_panorama_config(args.input_file, args.output_dir, args.max_input_bytes, args.member)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
