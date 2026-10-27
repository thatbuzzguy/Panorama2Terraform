"""F4.3 per-entry coverage: the ledger, the report rows, and the report file.

Four groups of checks:

1. The mark mechanism. `mark` records the entry and returns the object it built,
   which is the recorded object the parse method works through, and `mark_skipped`
   records an entry a parse method visited and did not model.
2. The read-but-not-marked rule. A parse method that reads config-object entries
   marks them, and a method that reads entries without marking them fails. A
   negative control pins that the check really fails. The corpus check runs the
   parse methods, so it checks the marks the parse actually made.
3. The row rules. Object type is the F4.2 `section_path`, destination is the
   longest matching table row, a per-entry mark wins for `report_only` and a
   skipped entry, a scope entry is bookkeeping, a property entry is counted on
   the parent row, and a `predefined` entry is not a row.
4. The report. One line per row, the gap section, file name only, byte-identical
   between runs, and no file when the input has no entries. A gap does not change
   the exit code.

`tests/fixtures/entry_gaps.xml` holds the two gap kinds a run can produce from a
covered container: a count-only entry and an unnamed entry.
`unknown_containers.xml` is the one fixture that produces an `unaccounted` row,
because its containers are the ones the table does not cover.
"""

import ast
import inspect
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

import container_coverage
import entry_coverage
import xml_input
from conftest import FIXTURES_DIR, REPO_ROOT, run_pipeline, run_script

GAP_FIXTURE = 'entry_gaps.xml'
UNKNOWN_FIXTURE = 'unknown_containers.xml'
GROUPING_FIXTURE = 'report_grouping.xml'


def _ledger(fixture_name: str, folder: Path = FIXTURES_DIR) -> entry_coverage.EntryLedger:
    """Parse one fixture and build an empty ledger, for the rule tests."""
    source = xml_input.parse_xml(folder / fixture_name)
    return entry_coverage.EntryLedger(source, container_coverage.parent_map(source.root))


def _parsed_ledger(converter_module, fixture_name: str) -> entry_coverage.EntryLedger:
    """Run every parse method, so the ledger holds the marks the parse made."""
    parser = converter_module.PanoramaParser(str(FIXTURES_DIR / fixture_name))
    for name in [n for n in dir(parser) if n.startswith('parse_')]:
        getattr(parser, name)()
    return parser.ledger


def _convert(fixture_name: str, out_dir: Path) -> dict:
    """Run the converter on one fixture and return its outputs."""
    proc = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / fixture_name),
                      '--output-dir', str(out_dir))
    report_file = out_dir / entry_coverage.REPORT_FILE
    return {
        'proc': proc,
        'report': report_file.read_text(encoding='utf-8') if report_file.is_file() else '',
        'report_file': report_file,
    }


# --- 1. The mark mechanism ---------------------------------------------------

def test_mark_records_the_entry_and_returns_the_recorded_object(converter_module):
    """A parse method marks at the point it builds the object, so `mark` returns it.

    F4.4: the stored object is the `RecordingDict` that carries the read record, so a
    parse method must work through the object `mark` returns. Identity that matters is
    the ledger's object and the returned object, not the dict the caller passed in.
    """
    parser = converter_module.PanoramaParser(str(FIXTURES_DIR / GAP_FIXTURE))
    entry = next(e for e in parser.root.iter() if e.tag == 'entry' and e.get('name') == 'Named-Host')
    obj = {'name': entry.get('name'), 'type': 'ip-netmask', 'value': '10.0.0.1/32'}
    returned = parser.mark(entry, obj)
    mark = parser.ledger.mark_for(entry)
    assert mark is not None
    assert mark['captured'] is returned
    assert returned == obj  # the recorded object carries the content the parse captured


def test_fields_added_through_the_recorded_object_are_recorded(converter_module):
    """A field a parse method adds after the mark is still in the report."""
    parser = converter_module.PanoramaParser(str(FIXTURES_DIR / GAP_FIXTURE))
    entry = next(e for e in parser.root.iter() if e.tag == 'entry' and e.get('name') == 'Named-Host')
    obj = {'name': entry.get('name'), 'type': 'ip-netmask', 'value': '10.0.0.1/32'}
    recorded = parser.mark(entry, obj)
    recorded['description'] = 'added after the mark'
    assert entry_coverage.entry_line(parser.ledger.row_for(entry)).endswith(
        'captured: description, type, value')


def test_mark_skipped_records_the_reason(converter_module):
    """An entry a parse method visited and did not model is reported as skipped."""
    parser = converter_module.PanoramaParser(str(FIXTURES_DIR / GAP_FIXTURE))
    entry = next(e for e in parser.root.iter() if e.tag == 'entry' and e.get('name') is None)
    parser.mark_skipped(entry, 'entry has no name attribute')
    row = parser.ledger.row_for(entry)
    assert row['destination'] == 'skipped'
    assert 'entry has no name attribute' in row['detail']
    assert row in parser.ledger.gaps()


# --- 2. Read but not marked fails -------------------------------------------

def _reads_entries(cls, method_name: str) -> bool:
    """True when this method, or a method it calls, reads entries."""
    pending = [method_name]
    seen = set()
    found = False
    while pending:
        name = pending.pop()
        if name in seen or not hasattr(cls, name):
            continue
        seen.add(name)
        tree = ast.parse(textwrap.dedent(inspect.getsource(getattr(cls, name))))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value.rstrip('/').endswith('entry'):
                    found = True
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and isinstance(node.func.value, ast.Name) and node.func.value.id == 'self':
                pending.append(node.func.attr)
    return found


def _marks_in(cls, method_name: str) -> bool:
    """True when this method, or a helper it calls, marks the entries it reads."""
    pending = [method_name]
    seen = set()
    while pending:
        name = pending.pop()
        if name in seen or not hasattr(cls, name):
            continue
        seen.add(name)
        tree = ast.parse(textwrap.dedent(inspect.getsource(getattr(cls, name))))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in ('mark', 'mark_skipped'):
                return True
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and isinstance(node.func.value, ast.Name) and node.func.value.id == 'self':
                pending.append(node.func.attr)
    return False


def test_every_parse_method_that_reads_entries_marks_them(converter_module):
    """Every parse method that reads config-object entries marks them (AC-1.5)."""
    cls = converter_module.PanoramaParser
    parse_methods = [name for name in dir(cls) if name.startswith('parse_')]
    assert parse_methods, 'no parse methods found'
    offenders = [name for name in parse_methods if _reads_entries(cls, name) and not _marks_in(cls, name)]
    assert offenders == [], offenders


def test_a_parse_method_that_reads_without_marking_fails(converter_module):
    """Negative control: the check is real, so a read with no mark is reported."""

    class Demo:
        def parse_demo(self):
            for entry in self.root.findall('.//address/entry'):
                yield entry.get('name')

    assert _reads_entries(Demo, 'parse_demo') and not _marks_in(Demo, 'parse_demo')

    class Marking:
        def parse_marked(self):
            for entry in self.root.findall('.//tag/entry'):
                self.mark(entry, {'name': entry.get('name')})

    assert _reads_entries(Marking, 'parse_marked') and _marks_in(Marking, 'parse_marked')


def test_corpus_entries_in_a_covered_container_are_all_marked(converter_module):
    """The corpus: every config-object entry in a covered container is marked.

    A scope entry is not a config-object entry, so the rule does not reach it: it
    defines a scope and the report shows it as bookkeeping. `unknown_containers.xml`
    is the other exception: its containers have no table row to report against.
    """
    for path in sorted(FIXTURES_DIR.glob('*.xml')) + [REPO_ROOT / 'sample_panorama_config.xml']:
        try:
            parser = converter_module.PanoramaParser(str(path))
        except (ET.ParseError, xml_input.UnsafeInputError):
            continue  # the hostile fixtures are refused before the parse
        for name in [n for n in dir(parser) if n.startswith('parse_')]:
            getattr(parser, name)()
        ledger = parser.ledger
        for entry in ledger.entries():
            container = ledger.parents.get(entry)
            if not ledger.is_report_entry(entry) or container is None:
                continue
            section = container_coverage.section_path(container, ledger.parents)
            if entry_coverage.covering_row(section) is None:
                continue  # an uncovered container is the F4.2 finding, not a mark gap
            if container_coverage.is_scope_entry(entry, ledger.parents):
                continue  # a scope entry defines a scope; it is not read as an object
            assert ledger.marked(entry), (path.name, parser.line_of(entry), section, entry.get('name'))


# --- 3. Row rules -----------------------------------------------------------

def test_destination_kinds_are_the_documented_eight():
    """F4.3 added `skipped` and `unaccounted` to the six F4.2 kinds."""
    assert entry_coverage.DESTINATION_KINDS == container_coverage.DESTINATION_KINDS
    assert set(entry_coverage.DESTINATION_KINDS) == {
        'emitted', 'report', 'inventory', 'count-only', 'bookkeeping',
        'nested-block', 'skipped', 'unaccounted',
    }
    assert entry_coverage.GAP_KINDS == ('count-only', 'skipped', 'unaccounted')


def test_object_type_is_the_f4_2_section_path():
    """The report names the object type with the same rule F4.2 pinned."""
    ledger = _ledger(GAP_FIXTURE)
    types = sorted({row['container'] for row in ledger.rows()})
    assert types == ['address', 'device-group', 'device-group/entry/address', 'region'], types
    entry = next(e for e in ledger.entries() if e.get('name') == 'Named-Host')
    assert container_coverage.section_path(ledger.parents[entry], ledger.parents) == \
        'device-group/entry/address'


def test_longest_matching_row_wins_for_a_sub_shape():
    """A sub-shape row describes an entry more exactly than the general row."""
    general = entry_coverage.covering_row('protocol/bgp')
    sub_shape = entry_coverage.covering_row('protocol/bgp/peer-group')
    assert general is not None and sub_shape is not None
    assert len(sub_shape.path.split('/')) > len(general.path.split('/'))
    assert entry_coverage.covering_row('protocol/bgp/peer-group') is sub_shape


def test_report_only_entry_destination_is_report():
    """A per-entry fact wins over the table row (AC-2.4).

    `address` is emitted, so the table row says `emitted`. The entry with
    `report_only` content writes nothing, so the mark reports it as `report`.
    """
    ledger = _ledger('kitchen_sink.xml')
    entry = next(e for e in ledger.entries() if e.get('name') == 'Country-US')
    assert entry_coverage.covering_row('address').destination == 'emitted'
    ledger.mark(entry, {'report_only': 'no v2 resource'})
    row = ledger.row_for(entry)
    assert row['destination'] == 'report', row
    # A `report` destination writes the manual report, so it is not a gap row.
    assert row not in ledger.gaps()


def test_skipped_entry_destination_beats_the_table_row():
    """A skipped entry is `skipped` even inside a container the table emits."""
    ledger = _ledger(GAP_FIXTURE)
    entry = next(e for e in ledger.entries() if e.get('name') is None)
    ledger.mark_skipped(entry, 'entry has no name attribute')
    assert entry_coverage.covering_row('address').destination == 'emitted'
    assert ledger.destination(entry) == 'skipped'


def test_scope_entry_is_bookkeeping():
    """An entry that defines a scope is not an object inside one (AC-2.7)."""
    ledger = _ledger(GAP_FIXTURE)
    scope_entry = next(e for e in ledger.entries() if e.get('name') == 'Edge')
    assert container_coverage.is_scope_entry(scope_entry, ledger.parents)
    assert ledger.destination(scope_entry) == 'bookkeeping'


def test_parse_device_groups_row_is_bookkeeping():
    """A device group name reaches the output through location, not as a resource."""
    row = entry_coverage.covering_row('device-group')
    assert row.destination == 'bookkeeping', row
    ledger = _ledger('multi_device_templates.xml')
    dg_rows = [r for r in ledger.rows() if r['container'] == 'device-group']
    assert dg_rows and all(r['destination'] == 'bookkeeping' for r in dg_rows)


def test_property_entries_are_counted_on_the_parent_row():
    """An entry inside a config-object entry is a property level (F4.2 AC-3.2)."""
    ledger = _ledger('kitchen_sink.xml')
    names = {row['name'] for row in ledger.rows()}
    parent = next(row for row in ledger.rows() if row['name'] == 'threat-ips')
    assert parent['property_entries'] == 1, parent
    # The entry inside it is a property level, so it is not a row of its own.
    assert 'hourly' not in names
    assert ledger.property_entry_total() > 0


def test_predefined_entries_are_not_rows():
    """`predefined` entries are PAN-OS definitions, so the header counts them."""
    ledger = _ledger(UNKNOWN_FIXTURE)
    entry = next(e for e in ledger.entries() if e.get('name') == 'ssl')
    assert not ledger.is_report_entry(entry)
    assert ledger.predefined_total() == 1
    assert 'ssl' not in {row['name'] for row in ledger.rows()}


# --- 4. Captured fields ----------------------------------------------------

def test_captured_fields_exclude_name_and_scope_facts():
    """The row identity and the four scope facts are not captured fields."""
    assert 'name' in entry_coverage.NON_FIELD_KEYS
    assert set(container_coverage.SCOPE_FACT_KEYS) <= entry_coverage.NON_FIELD_KEYS
    mark = {'captured': {'name': 'GW-Common', 'pre_named': True, 'vsys': 'vsys1',
                         'device_group': 'Office-FW', 'template': 'HQ-Networks',
                         'vsys_device': 'fw-1.example.com', 'description': 'gate'}}
    assert _ledger(GAP_FIXTURE).captured_fields(mark) == ('description', 'pre_named')


def test_captured_fields_skip_empty_values_and_sort():
    """The report shows what the parser actually took, in sorted order."""
    ledger = _ledger(GAP_FIXTURE)
    mark = {'captured': {'zz': 'last', 'description': '', 'ip-netmask': None,
                         'ab': 'first', 'members': [], 'name': 'x'}}
    assert ledger.captured_fields(mark) == ('ab', 'zz')
    assert ledger.captured_fields({'captured': {'name': 'only-name'}}) == ()
    line = entry_coverage.entry_line({'line': 1, 'container': 'region', 'name': 'x',
                                      'destination': 'count-only', 'detail': '',
                                      'fields': (), 'property_entries': 0, 'vsys': ''})
    assert line.endswith('captured: name only'), line


# --- 5. The report ---------------------------------------------------------

def test_report_line_fields_are_in_report_order(converter_module):
    """One line: line, object type, entry name, destination, detail, captured fields."""
    ledger = _parsed_ledger(converter_module, GAP_FIXTURE)
    row = next(r for r in ledger.rows() if r['destination'] == 'skipped')
    line = entry_coverage.entry_line(row)
    assert line.startswith('  line   25  address/(no name)'), line
    # Fields in report order: line, object type and name, destination, detail, captured.
    assert line.index('skipped') < line.index('panos_address') < line.index('captured:')
    assert 'captured: name only' in line


def test_report_names_the_file_not_the_path(tmp_path):
    report = _convert(GAP_FIXTURE, tmp_path)['report']
    file_line = [line for line in report.splitlines() if line.startswith('Input file:')]
    assert file_line == [f'Input file: {GAP_FIXTURE}'], file_line
    assert str(FIXTURES_DIR) not in report


def test_report_header_gives_the_totals_per_destination(tmp_path, converter_module):
    ledger = _parsed_ledger(converter_module, GAP_FIXTURE)
    report = _convert(GAP_FIXTURE, tmp_path)['report']
    counts = ledger.counts()
    assert f'Per-entry report: {sum(counts.values())} entries read' in report
    for kind in entry_coverage.DESTINATION_KINDS:
        marker = '  (writes nothing: gap)' if kind in entry_coverage.GAP_KINDS else ''
        assert f'  {kind:<14} {counts[kind]}{marker}' in report, kind


def test_gap_section_lists_the_rows_that_write_nothing(tmp_path, converter_module):
    ledger = _parsed_ledger(converter_module, GAP_FIXTURE)
    report = _convert(GAP_FIXTURE, tmp_path)['report']
    assert entry_coverage.GAP_HEADING in report
    gaps = ledger.gaps()
    expected = [entry_coverage.entry_line(row) for row in gaps]
    lines = report.splitlines()
    heading_line = next(i for i, line in enumerate(lines) if entry_coverage.GAP_HEADING in line)
    end_line = next(i for i, line in enumerate(lines) if line.startswith('Entry lines are grouped'))
    gap_block = lines[heading_line + 2:end_line]
    assert [line for line in gap_block if line.startswith('  line')] == expected, gap_block


def test_report_groups_rows_by_the_f3_9_scope_rule(tmp_path, converter_module):
    """The conversion report uses the grouping rule the other reports use."""
    ledger = _parsed_ledger(converter_module, GROUPING_FIXTURE)
    tf_gen = converter_module.TerraformGenerator(output_dir=str(tmp_path))
    report = tf_gen.generate_conversion_report(ledger)
    sections = [tf_gen._report_section_header(path)
                for path, _rows in tf_gen._group_by_scope(ledger.rows())]
    assert sections, sections
    for header in sections:
        assert header in report, header
    # The scope facts must come from the entry that defines each scope, so a row inside
    # a device group is not printed as the shared section (F3.9).
    assert {'DEVICE GROUP: Datacenter-FW', 'DEVICE GROUP: Office-FW'} <= set(sections)
    # The F3.9 point, pinned on the report itself: one name, two sections.
    same_name = sorted({tf_gen._report_section_header(path)
                        for path, rows in tf_gen._group_by_scope(ledger.rows())
                        for row in rows if row['name'] == 'ethernet1/1'})
    assert same_name == ['DEVICE GROUP: Datacenter-FW', 'DEVICE GROUP: Office-FW'], same_name
    # The interface report prints the same section titles for the same input.
    parser = converter_module.PanoramaParser(str(FIXTURES_DIR / GROUPING_FIXTURE))
    tf_gen.generate_interface_report(parser.parse_interfaces())
    interface_report = (tmp_path / 'INTERFACE_MIGRATION_REPORT.txt').read_text(encoding='utf-8')
    shared = [header for header in sections if header in interface_report]
    assert shared, (sections, interface_report)


def test_report_bytes_are_identical_between_runs(tmp_path):
    first = _convert(GAP_FIXTURE, tmp_path / 'a')
    second = _convert(GAP_FIXTURE, tmp_path / 'b')
    assert first['report'] == second['report']
    assert first['report']


def test_no_report_file_when_the_input_has_no_entries(tmp_path):
    """A run that read no entry has nothing to report."""
    empty = tmp_path / 'no_entries.xml'
    empty.write_text('<config><shared><tag></tag></shared></config>', encoding='utf-8')
    out = tmp_path / 'out'
    proc = run_script('panorama_to_terraform.py', str(empty), '--output-dir', str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not (out / entry_coverage.REPORT_FILE).is_file()
    assert 'Per-entry report' not in proc.stdout


def test_console_reports_the_gaps_and_prints_nothing_extra(tmp_path, converter_module):
    """The console prints the summary and the gap block for a run with gaps.

    The counts must come from the run the console prints, so the ledger here is a
    pipeline run: the property scan counts what the outputs read, and a parse-only
    ledger has no reads to count (F4.4).
    """
    parser = run_pipeline(converter_module, GAP_FIXTURE, tmp_path / 'run')
    assert parser is not None
    ledger = parser.ledger
    tf_gen = converter_module.TerraformGenerator(output_dir=str(tmp_path / 'gen'))
    stdout = _convert(GAP_FIXTURE, tmp_path)['proc'].stdout
    for line in entry_coverage.summary_lines(ledger) + entry_coverage.console_lines(
            ledger, tf_gen._report_scope_path):
        assert line in stdout, line
    clean = _convert('tags.xml', tmp_path / 'clean')
    assert 'Per-entry report' not in clean['proc'].stdout, clean['proc'].stdout


def test_a_gap_does_not_change_the_exit_code(tmp_path):
    """A coverage gap is an operator action, not a broken output."""
    result = _convert(GAP_FIXTURE, tmp_path)
    assert result['proc'].returncode == 0
    sanity = (tmp_path / 'SANITY_REPORT.txt').read_text(encoding='utf-8')
    assert 'Result: PASS' in sanity, sanity
