"""Coverage matrix tests (F2.8).

COVERAGE_MATRIX (resource_mapping.py) is the provider-resource <->
Panorama-XML-element matrix. These tests enforce it in three directions:

- row set: exactly one row per EMITTED_TYPES type. A type that is
  report-only can never gain a row without first leaving
  REPORT_ONLY_TYPES, and an emitter change must add or remove its row
  in the same change.
- element grounding: every row's fixture actually contains the row's
  Panorama XML element with the named entry.
- pipeline: running the converter on the row's fixture emits the
  provider resource with the expected name in the expected file.

The per-fixture pipeline runs are cached per test session (module-level
dict), so a fixture shared by two rows (interfaces_ethernet.xml feeds
both ethernet resource types) converts only once.
"""

import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from conftest import FIXTURES_DIR, run_script
from resource_mapping import COVERAGE_MATRIX, EMITTED_TYPES

# Every `resource "panos_x" "y" {` line in a Terraform file.
RESOURCE_RE = re.compile(r'resource\s+"([a-z0-9_]+)"\s+"([^"]+)"\s*\{')

# fixture name -> {filename: text} of the converter's .tf output.
_OUTPUTS: dict[str, dict[str, str]] = {}


# pytest calls the ids function once per parameter value.
def _row_id(row: dict) -> str:
    return row['resource']


ROWS = list(COVERAGE_MATRIX)


def _generate(fixture_name: str) -> dict[str, str]:
    """Run the converter CLI on one fixture. Cache the .tf output per session."""
    if fixture_name not in _OUTPUTS:
        out_dir = Path(tempfile.mkdtemp(prefix='coverage_matrix_'))
        result = run_script(
            'panorama_to_terraform.py', str(FIXTURES_DIR / fixture_name),
            '--output-dir', str(out_dir))
        assert result.returncode == 0, (
            f'converter failed on {fixture_name}: {result.stderr}\n{result.stdout}')
        _OUTPUTS[fixture_name] = {
            f.name: f.read_text() for f in sorted(out_dir.glob('*.tf'))
        }
    return _OUTPUTS[fixture_name]


def _resource_blocks(text: str, rtype: str) -> list[str]:
    """The resource blocks of one type in a .tf file.

    A block runs from its `resource "..." "..." {` line to the first
    line that is exactly `}` (column 0); nested object values close on
    indented lines, so the first unindented brace is the block end.
    """
    blocks = []
    for m in RESOURCE_RE.finditer(text):
        if m.group(1) != rtype:
            continue
        end = text.find('\n}', m.end())
        assert end != -1, f'unclosed resource block for {rtype}'
        blocks.append(text[m.start():end + 2])
    return blocks


def test_matrix_covers_exactly_the_emitted_types():
    """One row per emitted type; no row for any other type.

    This is the drift guard: an emitter that adds or drops a resource
    type must update the matrix in the same change.
    """
    row_types = [row['resource'] for row in ROWS]
    assert sorted(row_types) == sorted(EMITTED_TYPES), (
        f'matrix rows and EMITTED_TYPES disagree: '
        f'missing={sorted(EMITTED_TYPES - set(row_types))} '
        f'extra={sorted(set(row_types) - EMITTED_TYPES)}')
    assert len(row_types) == len(set(row_types)), (
        f'duplicate rows: {sorted(t for t in row_types if row_types.count(t) > 1)}')


@pytest.mark.parametrize('row', ROWS, ids=_row_id)
def test_row_fixture_exists(row):
    assert (FIXTURES_DIR / row['fixture']).is_file(), (
        f"row for {row['resource']}: fixture {row['fixture']!r} not found in tests/fixtures/")


@pytest.mark.parametrize('row', ROWS, ids=_row_id)
def test_fixture_contains_the_row_element(row):
    """The element column must name a real Panorama element in the fixture.

    The row's fixture must contain the row's XML element (tag path, any
    scope prefix) with an entry named xml_name.
    """
    root = ET.parse(FIXTURES_DIR / row['fixture']).getroot()
    entries = root.findall('.//' + row['xml_element'])
    assert entries, (
        f"row for {row['resource']}: fixture {row['fixture']!r} contains no "
        f"<{row['xml_element'].split('/')[0]}...> element")
    names = [e.get('name') for e in entries]
    assert row['xml_name'] in names, (
        f"row for {row['resource']}: fixture {row['fixture']!r} has element "
        f"<{row['xml_element']}> but no entry named {row['xml_name']!r} "
        f'(found: {names})')


@pytest.mark.parametrize('row', ROWS, ids=_row_id)
def test_row_emits_the_provider_resource(row):
    """The full pipeline maps the row's element to the provider resource.

    Converting the row's fixture must emit a `resource "<type>"` block in
    the row's output file whose body carries name = "<emitted_name>".
    """
    outputs = _generate(row['fixture'])
    assert row['output_file'] in outputs, (
        f"row for {row['resource']}: converter wrote no {row['output_file']!r} "
        f'(files: {sorted(outputs)})')
    text = outputs[row['output_file']]
    blocks = _resource_blocks(text, row['resource'])
    assert blocks, (
        f"row for {row['resource']}: no resource block of this type in "
        f"{row['output_file']!r}")
    expected = f'name = "{row["emitted_name"]}"'
    assert any(expected in block for block in blocks), (
        f"row for {row['resource']}: no block in {row['output_file']!r} carries "
        f'{expected!r}')
