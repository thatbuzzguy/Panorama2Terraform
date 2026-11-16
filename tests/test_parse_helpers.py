"""Unit tests for PanoramaParser helper methods (_get_text, _get_members).

The whitespace around text read from the tree is the export's formatting, not part of the value, so one rule
reads it: `xml_input.read_text` (`src/xml_input.py` rule 2). The six helpers the value readers use call it, so
no helper states a second whitespace rule: `_get_text`, `_get_members`, `_get_single_value`, `_protocol_field`,
`_list_names`, and `split_device_groups._device_names`.

Pins:

- the six helpers read the same content through the one rule, and an element that is not there still answers
  None, so the rule does not turn an absent field into an empty one;
- the run prints a value without the export's formatting, and the gate reads the same run clean.
"""

import xml.etree.ElementTree as ET

import resource_mapping
import sanity_checks
import split_device_groups
from conftest import file_text, run_script, tf_files

CONVERTER = "panorama_to_terraform.py"

# The content the pins read: one value that states the export's formatting around it.
SPACED = "  spaced  "


def _root():
    return ET.fromstring(
        """<root>
          <description>hello</description>
          <members>
            <member>a</member>
            <member>b</member>
          </members>
        </root>"""
    )


def _spaced_root():
    """The same three shapes, each stating the whitespace the export puts around the value."""
    return ET.fromstring(
        f"""<root>
          <description>{SPACED}</description>
          <members><member>{SPACED}</member></members>
          <more_members><member>{SPACED}</member><member>{SPACED}</member></more_members>
          <devices>
            <entry name="{SPACED}"/>
            <member>{SPACED}</member>
          </devices>
        </root>"""
    )


def _any_parser(make_parser):
    """Any parser instance will do: the helpers do not read the file."""
    return make_parser("tags.xml")


def test_get_text_present(make_parser):
    p = _any_parser(make_parser)
    assert p._get_text(_root(), "description") == "hello"


def test_get_text_missing(make_parser):
    p = _any_parser(make_parser)
    assert p._get_text(_root(), "missing") is None


def test_get_members(make_parser):
    p = _any_parser(make_parser)
    assert p._get_members(_root(), "members") == ["a", "b"]


def test_get_members_missing(make_parser):
    p = _any_parser(make_parser)
    assert p._get_members(_root(), "nothing") == []


def test_the_value_helpers_read_the_text_the_read_layer_states(make_parser):
    """Each of the six helpers answers the value without the whitespace the export states around it.

    The pin reads one content through all six, so a helper that states its own rule is the only way it can
    answer differently. The shape words and the element spellings passed to `_protocol_field` are read through
    the shape table, so the pin states no rule of its own.
    """
    p = _any_parser(make_parser)
    root = _spaced_root()
    assert p._get_text(root, "description") == "spaced"
    assert p._get_members(root, "members") == ["spaced"]
    # `_get_single_value` reads both shapes the export can state: the element text, one member, and many
    # members. A missing element answers None, so the rule cannot turn an absent field into an empty one.
    assert p._get_single_value(root, "description") == "spaced"
    assert p._get_single_value(root, "members") == "spaced"
    assert p._get_single_value(root, "more_members") == ["spaced", "spaced"]
    assert p._list_names(root, "devices") == ["spaced", "spaced"]
    # A membership entry names itself, so the name shape is read through the same rule as the member text. The
    # shape words and the element spellings are read through the table, so the pin states no rule of its own.
    path = "network/routing-profile/filters/access-list"
    table = resource_mapping.FILTER_TABLE
    row = table.row(path)
    entry = root.find("devices/entry")
    assert p._protocol_field(entry, "name", table.xml_name("name", path), row["fields"]["name"]) == "spaced"
    assert (
        p._protocol_field(root, "description", table.xml_name("description", path), row["fields"]["description"])
        == "spaced"
    )
    assert split_device_groups._device_names(root) == ["spaced", "spaced"]
    assert p._get_text(root, "missing") is None
    assert p._get_single_value(root, "missing") is None
    assert p._get_members(root, "missing") == []
    assert (
        p._protocol_field(
            root.find("missing"), "description", table.xml_name("description", path), row["fields"]["description"]
        )
        == ""
    )


def test_a_value_with_surrounding_whitespace_prints_without_it(tmp_path):
    """The `.tf` bytes the run wrote hold the value without the export's formatting.

    The corpus states no value with surrounding whitespace, because an export writes element text without
    padding, so the pin writes its own content. The gate reads the same run clean.
    """
    source = tmp_path / "whitespace_value.xml"
    source.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<config>\n  <device-group>\n'
        f'    <entry name="Edge-DG"><description>{SPACED}</description></entry>\n'
        "  </device-group>\n</config>\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    result = run_script(CONVERTER, str(source), "--output-dir", str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    # A scope entry is the unit's own block, so the run writes it in the unit's scope file (§14).
    text = file_text(tf_files(out), "scope.tf")
    assert 'description = "spaced"' in text, text
    assert not sanity_checks.run_checks(out).failed, "the value prints as the read layer read it"
