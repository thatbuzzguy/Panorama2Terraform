"""Maintenance tool: assemble the fixture corpus into one merged tree and print it.

The tool is a generator, not a pin. `tests/fixtures/kitchen_sink.xml` is the record that the golden set and
the corpus pins read, and the record is curated by hand, so the tool writes no file: it prints the tree it
assembles.

PAN-OS XML expresses repetition with named <entry> elements or leaf <member> elements, so merging is
well-defined:
- <entry>: merge with an existing child of the same name, else append
- leaf elements (text content, e.g. <member>): always append
- other elements: merge with an existing child of the same tag, else append

The read rule is the F3.8 input rule (`docs/ARCHITECTURE.md` §3) read on committed bytes: a fixture that
declares a DTD, or that the parse cannot read, is hostile input. A hostile fixture exists to trip the
refusal, so it is not material for the corpus, and the tool skips it by rule, not by name. The tool names no
fixture in its source except its own record, and `tests/test_build_kitchen_sink.py` pins that the tool's
decision agrees with `xml_input` for every committed fixture. The record is the result, so it is not an
input.

Run it from the repository root and redirect the tree to a file:

    python3 tools/build_kitchen_sink.py > /tmp/merged.xml
"""
import sys
import xml.etree.ElementTree as ET
import xml.parsers.expat as expat
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent
FIXDIR = REPO_ROOT / "tests" / "fixtures"

# The record the golden set reads. It is the curated result, so the tool never reads it and never writes it.
RECORD = "kitchen_sink.xml"


class _DtdFound(Exception):
    """The prolog scan found a DOCTYPE declaration."""


class _PrologDone(Exception):
    """The prolog scan stopped at the root element start tag, where a DTD cannot legally appear."""


def refusal_reason(path: Path) -> Optional[str]:
    """Why the tool does not read one fixture, or None when its read rule accepts it.

    The two F3.8 checks, read on the committed bytes. The size check has nothing to protect on a committed
    fixture, so the tool states the DTD check and the parse. The DTD check asks the parser, so a `<!DOCTYPE`
    inside a comment is not a refusal, and the tool cannot import `xml_input` (`docs/ARCHITECTURE.md` §1.1).
    """
    data = path.read_bytes()
    parser = expat.ParserCreate()

    def on_doctype(doctype_name, *_rest):
        raise _DtdFound(f"the file declares a DTD for '{doctype_name}'")

    def on_start_element(*_args):
        raise _PrologDone

    parser.StartDoctypeDeclHandler = on_doctype
    parser.StartElementHandler = on_start_element
    try:
        # isfinal=False: a truncated prolog is not a fault here, because the parse reports the same fault
        # with its position.
        parser.Parse(data, False)
    except _PrologDone:
        pass
    except _DtdFound as found:
        return str(found)
    except expat.ExpatError:
        # The prolog is not well-formed XML. Say nothing here; the parse below reports the same fault.
        pass

    try:
        ET.fromstring(data)
    except ET.ParseError as error:
        return f"the parse cannot read it: {error}"
    return None


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


def assemble(fixdir: Path) -> tuple[ET.Element, list[tuple[str, str]]]:
    """The merged tree for the fixtures the read rule accepts, and the fixtures it skipped, in read order."""
    root = ET.Element("config", {"version": "10.0.0", "urldb": "paloaltonetworks"})
    skipped: list[tuple[str, str]] = []
    for path in sorted(fixdir.glob("*.xml")):
        if path.name == RECORD:
            continue  # the record is the result, so it is not an input
        reason = refusal_reason(path)
        if reason is not None:
            skipped.append((path.name, reason))
            continue
        source = ET.parse(path).getroot()
        for child in source:
            match = next((c for c in root if c.tag == child.tag), None)
            if match is None:
                root.append(ET.fromstring(ET.tostring(child)))
            else:
                merge_into(match, child)
    return root, skipped


def render(root: ET.Element) -> str:
    """The tree in the shape the corpus files hold: the declaration, two-space indent, one final newline."""
    ET.indent(root, space="  ")
    return "<?xml version=\"1.0\"?>\n" + ET.tostring(root, encoding="unicode", xml_declaration=False) + "\n"


def main() -> int:
    root, skipped = assemble(FIXDIR)
    for name, reason in skipped:
        print(f"skipped {name}: {reason}", file=sys.stderr)
    print(render(root), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
