"""The fixture assembler (`tools/build_kitchen_sink.py`): what it reads, how it merges, and the rule that the
committed fixture is the record it does not write (`docs/ARCHITECTURE.md` §1.1).

Four groups:

1. The read rule: the tool reads a fixture when the F3.8 input rule accepts it, so a hostile fixture is
   skipped by rule and not by name. The tool's decision agrees with `xml_input` for every committed fixture,
   the tool names no fixture in its source except its own record, and the rule answers for a fixture the test
   writes.
2. The generator, not a pin: the tool writes no file, the record is not an input, and the tool's output for
   the committed set is not the record, because the record is curated by hand.
3. The merge rule: an entry merges with the entry of the same name, a leaf with text always appends, and
   another element merges with the element of the same tag or appends.
4. The run: two runs on the committed set answer the same bytes, and the run prints one line per fixture it
   skipped, in the read order.

`tools/` is not on the test path, because the developer scripts are not tool modules (§1.1), so this test
reads the tool's functions through `importlib` on the path `tests/conftest.py` builds once.
"""

import ast
import contextlib
import importlib.util
import io
import xml.etree.ElementTree as ET

import xml_input
from conftest import FIXTURES_DIR, TOOLS_DIR

TOOL_PATH = TOOLS_DIR / "build_kitchen_sink.py"
_spec = importlib.util.spec_from_file_location("build_kitchen_sink", TOOL_PATH)
tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def _assemble_two(tmp_path, first: str, second: str) -> ET.Element:
    """The tree the tool builds from two committed-like fixture files."""
    (tmp_path / "a.xml").write_text(first, encoding="utf-8")
    (tmp_path / "b.xml").write_text(second, encoding="utf-8")
    root, skipped = tool.assemble(tmp_path)
    assert skipped == [], skipped
    return root


# --- 1. The read rule ----------------------------------------------------------

def test_the_read_rule_is_the_input_rule_read_on_committed_files():
    """For every committed fixture the tool's read decision agrees with the door, so the tool states the same
    rule the tool's entry points use (`docs/ARCHITECTURE.md` §3) and not a name list."""
    for path in sorted(FIXTURES_DIR.glob("*.xml")):
        try:
            xml_input.parse_xml(path)
            accepted = True
        except (xml_input.UnsafeInputError, ET.ParseError):
            accepted = False
        assert (tool.refusal_reason(path) is None) == accepted, (path.name, tool.refusal_reason(path))


def test_the_tool_names_no_fixture_in_its_source():
    """The only fixture name the tool states is its own record, so the hostile skip cannot be a list of names.
    The corpus pattern (`*.xml`) is the directory the tool reads, not a fixture name.
    """
    literals = {node.value for node in ast.walk(ast.parse(TOOL_PATH.read_text(encoding="utf-8")))
                if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    named = sorted(name for name in literals if name.endswith(".xml") and "*" not in name)
    assert named == [tool.RECORD], named


def test_the_read_rule_answers_for_a_fixture_the_tool_has_never_seen(tmp_path):
    """A fixture a test writes is refused by the same rule: a DTD, or a parse the parser cannot read."""
    dtd = tmp_path / "new_dtd.xml"
    dtd.write_text('<?xml version="1.0"?>\n<!DOCTYPE config [<!ENTITY x SYSTEM "file:///tmp/none">]>\n'
                   '<config><shared><tag><entry name="a"/></tag></shared></config>\n', encoding="utf-8")
    bad = tmp_path / "new_bad.xml"
    bad.write_bytes(b'<?xml version="1.0"?>\n<config><shared><tag>\x01</tag></shared></config>')
    good = tmp_path / "new_good.xml"
    good.write_text('<?xml version="1.0"?>\n<config><shared><tag><entry name="a"/></tag></shared></config>\n',
                    encoding="utf-8")
    comment = tmp_path / "comment_doctype.xml"
    comment.write_text('<?xml version="1.0"?>\n<!-- <!DOCTYPE config > -->\n'
                       '<config><shared><tag><entry name="a"/></tag></shared></config>\n', encoding="utf-8")

    assert "DTD" in tool.refusal_reason(dtd), tool.refusal_reason(dtd)
    assert "cannot read" in tool.refusal_reason(bad), tool.refusal_reason(bad)
    assert tool.refusal_reason(good) is None
    assert tool.refusal_reason(comment) is None, "a DOCTYPE inside a comment is legal input"


def test_the_read_set_is_the_set_the_corpus_pins_read_less_the_record():
    """The corpus pins read the fixtures that are not hostile, so the tool reads the same set, less its own
    record. Measured 2026-11-05 on the committed corpus: 68 accepted, 67 read, 3 skipped."""
    accepted = [path.name for path in sorted(FIXTURES_DIR.glob("*.xml")) if tool.refusal_reason(path) is None]
    skipped = [path.name for path in sorted(FIXTURES_DIR.glob("*.xml")) if tool.refusal_reason(path) is not None]
    read = [name for name in accepted if name != tool.RECORD]

    assert len(accepted) == 68, accepted
    assert len(skipped) == 3, skipped
    assert len(read) == 67, read
    assert tool.RECORD in accepted, "the record is not hostile, so the rule keeps it out for another reason"


# --- 2. The generator, not a pin ----------------------------------------------

def test_the_tool_writes_no_file_so_the_record_stays_the_record():
    """The tool prints the tree it assembles, so a run cannot change the record the goldens read."""
    source = TOOL_PATH.read_text(encoding="utf-8")
    assert not [line for line in source.splitlines()
                if "write_text" in line or "write_bytes" in line or "open(" in line], source

    before = (FIXTURES_DIR / tool.RECORD).read_bytes()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        tool.main()
    assert (FIXTURES_DIR / tool.RECORD).read_bytes() == before, "a run must not change the record"


def test_the_tool_is_not_a_pin_on_the_record():
    """The record is curated by hand, so the tool's output for the committed set is not the record. The two
    facts that keep it so are pinned as data: the record holds comments, which the tool's read rule drops, and
    entry names no committed fixture carries."""
    root, _skipped = tool.assemble(FIXTURES_DIR)
    output = tool.render(root)
    record = (FIXTURES_DIR / tool.RECORD).read_text(encoding="utf-8")
    assert output != record, "the tool is a generator, so its output is not the record"

    assert record.count("<!--") == 17, "ET.parse builds no comment node, so no merge can answer a comment"
    assert "<!--" not in output

    names = {entry.get("name") for entry in ET.fromstring(record).iter("entry")}
    carried = set()
    for path in sorted(FIXTURES_DIR.glob("*.xml")):
        if path.name == tool.RECORD or tool.refusal_reason(path) is not None:
            continue
        carried |= {entry.get("name") for entry in ET.parse(path).getroot().iter("entry")}
    assert len(names - carried) == 13, sorted(names - carried)


# --- 3. The merge rule ---------------------------------------------------------

def test_an_entry_merges_with_the_entry_of_the_same_name(tmp_path):
    root = _assemble_two(
        tmp_path,
        '<?xml version="1.0"?>\n<config><shared><address><entry name="A">'
        "<ip-netmask>10.0.0.1/32</ip-netmask></entry></address></shared></config>\n",
        '<?xml version="1.0"?>\n<config><shared><address><entry name="A">'
        "<tag>web</tag></entry></address></shared></config>\n",
    )
    entries = root.findall(".//entry")
    assert len(entries) == 1, entries
    assert entries[0].find("ip-netmask").text == "10.0.0.1/32"
    assert entries[0].find("tag").text == "web"


def test_a_leaf_with_text_always_appends(tmp_path):
    root = _assemble_two(
        tmp_path,
        '<?xml version="1.0"?>\n<config><shared><address-group><entry name="G"><static>'
        "<member>m1</member></static></entry></address-group></shared></config>\n",
        '<?xml version="1.0"?>\n<config><shared><address-group><entry name="G"><static>'
        "<member>m2</member><member>m3</member></static></entry></address-group></shared></config>\n",
    )
    assert [member.text for member in root.findall(".//member")] == ["m1", "m2", "m3"]


def test_another_element_merges_with_the_element_of_the_same_tag_or_appends(tmp_path):
    root = _assemble_two(
        tmp_path,
        '<?xml version="1.0"?>\n<config><shared><address><entry name="A">'
        "<ip-netmask>10.0.0.1/32</ip-netmask></entry></address></shared></config>\n",
        '<?xml version="1.0"?>\n<config><shared><address><entry name="B">'
        "<ip-netmask>10.0.0.2/32</ip-netmask></entry></address>"
        "<tag><entry name=\"prod\"/></tag></shared></config>\n",
    )
    shared = root.find("shared")
    assert [child.tag for child in shared] == ["address", "tag"], [child.tag for child in shared]
    assert len(shared.find("address").findall("entry")) == 2


# --- 4. The run ---------------------------------------------------------------

def test_two_runs_on_the_committed_set_answer_the_same_bytes():
    first = tool.render(tool.assemble(FIXTURES_DIR)[0])
    second = tool.render(tool.assemble(FIXTURES_DIR)[0])
    assert first == second, "the assembly is deterministic"


def test_the_run_prints_one_line_per_fixture_it_skipped():
    """The run states what its read rule decided, in the read order, and prints the tree on stdout."""
    with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
        tool.main()
    _root, skipped = tool.assemble(FIXTURES_DIR)
    assert err.getvalue().splitlines() == [f"skipped {name}: {reason}" for name, reason in skipped], \
        err.getvalue()
    assert out.getvalue().startswith("<?xml version=\"1.0\"?>\n<config"), out.getvalue()[:60]
