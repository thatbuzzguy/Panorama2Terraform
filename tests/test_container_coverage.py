"""F4.2 entry coverage: the container table, the scan, and the report.

Three groups of checks:

1. Table <-> code. Every parse method on `PanoramaParser` has a row in
   `container_coverage.CONTAINER_TABLE`, every row names a method that exists,
   and every row path is a path the method actually reads. This is what keeps
   `docs/ARCHITECTURE.md` §3.1 honest: the document points at the table, and
   these tests keep the table and the code in step.
2. The section rule. A container is a section when no config-object entry lies
   between it and a config root. A container inside a config-object entry is a
   property level, so this module does not report it (the property-level scan, F4.4,
   covers it).
3. The report. A section the table does not cover produces one finding, sorted
   by tag chain then line, naming the file name only. An absent container is not
   a finding. A finding does not change the exit code.

Path matching is by segment presence: a method may reach a container through a
helper, so a row path matches when the method, or a method it calls, names each
segment. It is a presence check, not a full path comparison.
"""

import ast
import inspect
import re
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

import container_coverage
import xml_input
from conftest import FIXTURES_DIR, REPO_ROOT, run_script

# A path-like string constant in a parse method: a tag name or a tag chain.
PATH_STRING_RE = re.compile(r'^[A-Za-z0-9_.\-/]+$')

# The fixture that holds sections no parse method reads.
UNKNOWN_FIXTURE = 'unknown_containers.xml'

# Findings the fixture produces, in report order. Pinned so the report bytes and
# the console lines can be compared with these values.
EXPECTED_FINDINGS = [
    ('data-entry', 23, 1),
    ('device-group/entry/certificate', 46, 1),
    ('devices/entry/vsys/entry/import', 64, 1),
    ('document', 14, 2),
]


def _segments_of_method(cls, method_name: str) -> set[str]:
    """Tag segments the method names, including the ones it hands to a helper."""
    segments: set[str] = set()
    pending = [method_name]
    seen: set[str] = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        tree = ast.parse(textwrap.dedent(inspect.getsource(getattr(cls, name))))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if PATH_STRING_RE.match(node.value):
                    segments.update(node.value.split('/'))
            elif isinstance(node, ast.JoinedStr):
                for part in node.values:
                    if isinstance(part, ast.Constant) and PATH_STRING_RE.match(part.value):
                        segments.update(part.value.split('/'))
                    elif isinstance(part, ast.FormattedValue):
                        segments.add('entry')  # the entry placeholder
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                  and isinstance(node.func.value, ast.Name) and node.func.value.id == 'self'):
                pending.append(node.func.attr)
    return segments


def _scan(fixture_name: str):
    """Parse one fixture and run the scan the way the converter does."""
    source = xml_input.parse_xml(FIXTURES_DIR / fixture_name)
    parents = container_coverage.parent_map(source.root)
    return source, parents, container_coverage.scan(source, parents)


# --- 1. Table <-> code -------------------------------------------------------

def test_every_parse_method_has_a_table_row(converter_module):
    """A parse method without a row is an entry the report cannot describe."""
    methods = {name for name in dir(converter_module.PanoramaParser) if name.startswith('parse_')}
    missing = sorted(methods - set(container_coverage.parse_methods()))
    assert not missing, f'parse methods with no container row: {missing}'


def test_every_row_names_a_method_that_exists(converter_module):
    """The table cannot name a method the code does not have."""
    for row in container_coverage.CONTAINER_TABLE:
        assert hasattr(converter_module.PanoramaParser, row.method), row


def test_every_row_path_is_read_by_its_method(converter_module):
    """Every row path is a path the named method reads."""
    for row in container_coverage.CONTAINER_TABLE:
        if row.read_via != 'pattern':
            continue
        segments = _segments_of_method(converter_module.PanoramaParser, row.method)
        missing = [s for s in row.path.split('/') if s not in segments]
        assert not missing, f'{row.method} does not read {row.path} (missing {missing})'


def test_destination_kinds_are_the_documented_set():
    """A row uses one of the eight destinations and one of the two read vias."""
    for row in container_coverage.CONTAINER_TABLE:
        assert row.destination in container_coverage.DESTINATION_KINDS, row
        assert row.read_via in container_coverage.READ_VIAS, row


def test_emitted_rows_name_a_provider_resource():
    """A row that writes output names a resource type the mapping can emit."""
    from resource_mapping import EMITTED_TYPES
    for row in container_coverage.CONTAINER_TABLE:
        if row.destination not in ('emitted', 'nested-block'):
            continue
        named = re.findall(r'panos_[a-z0-9_]+', row.note)
        if row.destination == 'emitted':
            assert named and any(word in EMITTED_TYPES for word in named), row
        else:
            # A nested block has no resource type of its own; it names the
            # parent type or the table that picks the parent type.
            assert (named and any(word in EMITTED_TYPES for word in named)) or \
                   'INTERFACE_RESOURCE_TYPES' in row.note, row


def test_scope_walk_rows_are_the_scope_containers(converter_module):
    """The read-by-walk rows are the four scope facts over the scope containers."""
    facts = {'device_group_of', 'vsys_of', 'template_of', 'device_of'}
    for row in container_coverage.CONTAINER_TABLE:
        if row.read_via != 'scope walk':
            continue
        assert row.method in facts, row
        assert row.path in container_coverage.SCOPE_CONTAINERS, row


# --- 2. The section rule -----------------------------------------------------

def _tree(text: str):
    """A parsed fixture-like tree plus its parent map."""
    root = ET.fromstring(text)
    return root, container_coverage.parent_map(root)


def test_container_inside_a_config_object_entry_is_a_property_level():
    """`schedule/entry/schedule-type/recurring` is a property level, not a section."""
    root, parents = _tree(
        '<config><shared><schedule><entry name="weekly">'
        '<schedule-type><recurring><name>monday</name></recurring></schedule-type>'
        '</entry></schedule></shared></config>'
    )
    section = root.find('.//schedule')
    property_level = root.find('.//recurring')
    assert container_coverage.is_section(section, parents)
    assert not container_coverage.is_section(property_level, parents)
    assert container_coverage.section_path(property_level, parents) == 'schedule/entry/schedule-type/recurring'


def test_container_under_a_scope_entry_is_a_section():
    """A container under a device-group entry is still a section."""
    root, parents = _tree(
        '<config><panorama><device-group><entry name="Edge"><tag>'
        '<entry name="prod"/></tag></entry></device-group></panorama></config>'
    )
    container = root.find('.//tag')
    assert container_coverage.is_section(container, parents)
    assert container_coverage.section_path(container, parents) == 'device-group/entry/tag'
    assert container_coverage.is_known(container_coverage.section_path(container, parents))


def test_scope_entry_itself_is_not_a_config_object_entry():
    """The four scope containers define a scope, so they do not break the rule."""
    root, parents = _tree('<config><shared><devices><entry name="fw-1"/></devices></shared></config>')
    entry = root.find('.//devices/entry')
    assert container_coverage.is_scope_entry(entry, parents)


# --- 3. Findings --------------------------------------------------------------

def test_unknown_section_is_reported():
    """A section no row covers produces one finding with its line and entry count."""
    source, parents, findings = _scan(UNKNOWN_FIXTURE)
    got = [(f.path, f.line, f.entries) for f in findings]
    assert got == EXPECTED_FINDINGS, got
    for finding in findings:
        assert finding.path, finding
        assert finding.line, f'{finding.path} carries no line'
        assert finding.entries > 0, finding


def test_findings_are_sorted_by_path_then_line():
    """The same input always produces the same order."""
    _, _, findings = _scan(UNKNOWN_FIXTURE)
    assert findings == sorted(findings, key=lambda f: (f.path, f.line or 0))


def test_predefined_entries_are_not_findings():
    """A PAN-OS built-in definition is not an operator object."""
    _, _, findings = _scan(UNKNOWN_FIXTURE)
    assert not any('predefined' in f.path for f in findings)


def test_property_level_entries_are_not_findings():
    """A config-object entry is a property level, so F4.2 does not report it."""
    _, _, findings = _scan('kitchen_sink.xml')
    assert findings == [], findings


def test_absent_container_is_not_a_finding():
    """An export does not have to contain every container the converter knows."""
    _, _, findings = _scan('kitchen_sink.xml')
    assert not any('region' in f.path for f in findings)


def test_empty_known_container_is_not_a_finding(tmp_path):
    """A known container with no entries is not a coverage gap."""
    source_file = tmp_path / 'empty.xml'
    source_file.write_text('<config><shared><tag></tag></shared></config>', encoding='utf-8')
    source = xml_input.parse_xml(source_file)
    assert container_coverage.scan(source, container_coverage.parent_map(source.root)) == []


def test_committed_corpus_has_no_findings():
    """Every committed fixture is covered at the section level.

    The coverage fixture is the exception: it is the input that demonstrates the
    report, so it is the one fixture that produces findings.
    """
    for path in sorted(FIXTURES_DIR.glob('*.xml')):
        if path.name == UNKNOWN_FIXTURE:
            continue
        try:
            source, parents, findings = _scan(path.name)
        except (ET.ParseError, xml_input.UnsafeInputError):
            continue  # the hostile fixtures are refused before the parse
        assert findings == [], (path.name, findings)


def test_report_line_wording_counts_the_entries():
    """The wording is one place: a single entry is not called 'entries'."""
    _, _, findings = _scan(UNKNOWN_FIXTURE)
    phrases = [container_coverage.entry_phrase(f.entries) for f in findings]
    assert phrases == ['1 entry', '1 entry', '1 entry', '2 entries'], phrases
    single = container_coverage.Finding(path='document', line=14, entries=1)
    assert container_coverage.report_line(single).endswith('1 entry - no parse method reads this container')
    unknown = container_coverage.Finding(path='document', line=None, entries=2)
    assert container_coverage.position_phrase(unknown) == 'position unknown'


# --- 4. Report and console --------------------------------------------------

def _convert(fixture_name: str, out_dir: Path) -> dict:
    """Run the converter on one fixture and return its outputs."""
    proc = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / fixture_name),
                      '--output-dir', str(out_dir))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = out_dir / 'MANUAL_SETUP_REPORT.txt'
    return {'proc': proc, 'report': report.read_text(encoding='utf-8') if report.is_file() else ''}


def test_report_names_the_source_not_the_path(tmp_path):
    """The report section names the source name, never the path (F4.2 rule 6).

    The path is in the provenance record (F5.3), which is not a report body.
    """
    result = _convert(UNKNOWN_FIXTURE, tmp_path)
    lines = result['report'].splitlines()
    section = [line for line in lines if 'Entry Coverage' in line]
    assert section, result['report']
    file_line = [line for line in lines if line.startswith(container_coverage.SOURCE_LABEL)]
    assert file_line == [f'Source: {UNKNOWN_FIXTURE}'], file_line
    assert str(FIXTURES_DIR) not in result['report']


def test_report_lists_every_finding_with_its_line(tmp_path):
    """One report line per finding, in the scan order."""
    _, _, findings = _scan(UNKNOWN_FIXTURE)
    report = _convert(UNKNOWN_FIXTURE, tmp_path)['report']
    lines = [line for line in report.splitlines() if 'no parse method reads' in line]
    assert lines == [container_coverage.report_line(f) for f in findings], lines


def test_report_bytes_are_identical_between_runs(tmp_path):
    """The same input produces the same report bytes."""
    first = _convert(UNKNOWN_FIXTURE, tmp_path / 'a')
    second = _convert(UNKNOWN_FIXTURE, tmp_path / 'b')
    assert first['report'] == second['report']


def test_console_lists_the_findings(tmp_path):
    """A run with findings says so on the console."""
    _, _, findings = _scan(UNKNOWN_FIXTURE)
    stdout = _convert(UNKNOWN_FIXTURE, tmp_path)['proc'].stdout
    assert f'Entry Coverage: {len(findings)} container(s) the parser does not read' in stdout
    for finding in findings:
        assert container_coverage.console_line(finding) in stdout, finding


def test_no_coverage_output_when_there_is_nothing_to_report(tmp_path):
    """A covered input writes no coverage section and prints no coverage line."""
    result = _convert('kitchen_sink.xml', tmp_path)
    assert 'Entry Coverage' not in result['report']
    assert 'Entry Coverage' not in result['proc'].stdout


def test_a_finding_does_not_change_the_exit_code(tmp_path):
    """A coverage gap is an operator action, not a broken output."""
    result = _convert(UNKNOWN_FIXTURE, tmp_path)
    assert result['proc'].returncode == 0
    sanity = (tmp_path / 'SANITY_REPORT.txt').read_text(encoding='utf-8')
    assert 'Result: PASS' in sanity, sanity


def test_architecture_points_at_the_table_instead_of_restating_it():
    """docs/ARCHITECTURE.md §3.1 names the code table as the source of truth."""
    doc = (REPO_ROOT / 'docs' / 'ARCHITECTURE.md').read_text(encoding='utf-8')
    assert 'container_coverage.CONTAINER_TABLE' in doc, 'section 3.1 must point at the table'
    assert 'F4.2' in doc
