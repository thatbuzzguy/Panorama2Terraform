"""Unit tests for PanoramaParser helper methods (_get_text, _get_members)."""

import xml.etree.ElementTree as ET


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
