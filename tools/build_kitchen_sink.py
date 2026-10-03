"""Maintenance tool: rebuild tests/fixtures/kitchen_sink.xml from the per-method fixtures.

PAN-OS XML expresses repetition with named <entry> elements or leaf <member>
elements, so merging is well-defined:
- <entry>: merge with an existing child of the same name, else append
- leaf elements (text content, e.g. <member>): always append
- other elements: merge with an existing child of the same tag, else append
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
FIXDIR = REPO_ROOT / "tests" / "fixtures"
EXCLUDE = {"kitchen_sink.xml", "address_objects_dg_override.xml"}


def merge_into(target: ET.Element, source: ET.Element) -> None:
    for child in source:
        if child.tag == "entry":
            match = next(
                (c for c in target if c.tag == "entry" and c.get("name") == child.get("name")),
                None,
            )
            if match is None:
                target.append(ET.fromstring(ET.tostring(child)))
            else:
                merge_into(match, child)
        elif child.text and not list(child):
            # leaf with text (member, any, etc.): always append
            target.append(ET.fromstring(ET.tostring(child)))
        else:
            match = next((c for c in target if c.tag == child.tag), None)
            if match is None:
                target.append(ET.fromstring(ET.tostring(child)))
            else:
                merge_into(match, child)


def main() -> None:
    root = ET.Element("config", {"version": "10.0.0", "urldb": "paloaltonetworks"})
    for f in sorted(FIXDIR.glob("*.xml")):
        if f.name in EXCLUDE:
            continue
        src = ET.parse(f).getroot()
        for child in src:
            match = next((c for c in root if c.tag == child.tag), None)
            if match is None:
                root.append(ET.fromstring(ET.tostring(child)))
            else:
                merge_into(match, child)

    ET.indent(root, space="  ")
    raw = ET.tostring(root, encoding="unicode", xml_declaration=False)
    out = '<?xml version="1.0"?>\n' + raw + "\n"
    (FIXDIR / "kitchen_sink.xml").write_text(out)
    print(f"wrote {FIXDIR / 'kitchen_sink.xml'} ({len(out.splitlines())} lines)")


if __name__ == "__main__":
    sys.exit(main())
