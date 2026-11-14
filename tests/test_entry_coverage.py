"""F4.3 per-entry coverage: the ledger, the report rows, and the report file.

Five groups of checks:

1. The mark mechanism. `mark` records the entry and returns the object it built,
   which is the recorded object the parse method works through, and `mark_skipped`
   records an entry a parse method visited and did not model.
2. The read-but-not-marked rule. A parse method that reads config-object entries
   marks them, and a method that reads entries without marking them fails. A
   negative control pins that the check really fails. The corpus check runs the
   parse methods, so it checks the marks the parse actually made. The entry-name
   guard is part of this rule: a guard that skips a nameless entry must record it,
   and a nameless entry reaches the report line or the parent row count.
3. The row rules. Object type is the F4.2 `section_path`, destination is answered in
   one place, in the order: the per-entry fact on the recorded object, the destination
   `mark` recorded, the container table row. A scope entry takes the destination its
   table row states (F6.5), a property entry is counted on the parent row, a
   `predefined` entry is not a row, and an entry at a level the table states no row
   for still holds a record.
4. Captured fields. The names a report line prints, without the identity and scope
   facts.
5. The report. One line per row, the gap section, file name only, byte-identical
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
from pathlib import Path

import container_coverage
import entry_coverage
import xml_input
from conftest import FIXTURES_DIR, SAMPLE_CONFIG, corpus_fixtures, run_pipeline, run_script, written_bytes

GAP_FIXTURE = 'entry_gaps.xml'
UNKNOWN_FIXTURE = 'unknown_containers.xml'
GROUPING_FIXTURE = 'report_grouping.xml'


def _ledger(fixture_name: str, folder: Path = FIXTURES_DIR) -> entry_coverage.EntryLedger:
    """Parse one fixture and build an empty ledger, for the rule tests."""
    source = xml_input.parse_xml(folder / fixture_name)
    return entry_coverage.EntryLedger(source, container_coverage.parent_map(source.root))


def _parse_every(parser) -> None:
    """Run every parse method, so the ledger holds the marks the parse made.

    `parse_bgp`, `parse_ospf`, `parse_ospfv3` and `parse_rip` take the router element (F7.1, F7.2, F7.5), so
    they are called for each router the fixture names; every other parse method takes no argument. F7.10 added
    the two methods the `protocol` row names for the redistribution profile lists, which take the router element
    for the same reason.
    """
    for name in [n for n in dir(parser) if n.startswith('parse_')]:
        method = getattr(parser, name)
        if name in ('parse_bgp', 'parse_ospf', 'parse_ospfv3', 'parse_rip',
                    'parse_redist_profile', 'parse_redist_profile_ipv6'):
            for router in parser.root.findall('.//virtual-router/entry'):
                method(router)
        else:
            method()


def _parsed_ledger(converter_module, fixture_name: str) -> entry_coverage.EntryLedger:
    """Run every parse method, so the ledger holds the marks the parse made."""
    parser = converter_module.PanoramaParser(xml_input.parse_xml(FIXTURES_DIR / fixture_name))
    _parse_every(parser)
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
    parser = converter_module.PanoramaParser(xml_input.parse_xml(FIXTURES_DIR / GAP_FIXTURE))
    entry = next(e for e in parser.root.iter() if e.tag == 'entry' and e.get('name') == 'Named-Host')
    obj = {'name': entry.get('name'), 'type': 'ip-netmask', 'value': '10.0.0.1/32'}
    returned = parser.mark(entry, obj)
    mark = parser.ledger.mark_for(entry)
    assert mark is not None
    assert mark['captured'] is returned
    assert returned == obj  # the recorded object carries the content the parse captured


def test_fields_added_through_the_recorded_object_are_recorded(converter_module):
    """A field a parse method adds after the mark is still in the report."""
    parser = converter_module.PanoramaParser(xml_input.parse_xml(FIXTURES_DIR / GAP_FIXTURE))
    entry = next(e for e in parser.root.iter() if e.tag == 'entry' and e.get('name') == 'Named-Host')
    obj = {'name': entry.get('name'), 'type': 'ip-netmask', 'value': '10.0.0.1/32'}
    recorded = parser.mark(entry, obj)
    recorded['description'] = 'added after the mark'
    assert entry_coverage.entry_line(parser.ledger.row_for(entry)).endswith(
        'captured: description, type, value')


def test_mark_skipped_records_the_reason(converter_module):
    """An entry a parse method visited and did not model is reported as skipped."""
    parser = converter_module.PanoramaParser(xml_input.parse_xml(FIXTURES_DIR / GAP_FIXTURE))
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


def _name_guards(cls) -> list:
    """Every entry-name guard as (method name, guard form, the branch that skips the entry).

    A guard is an `if` whose test is the truthiness of the entry name: the name read through
    `.get('name')`, or through a variable the method assigns from that call. The branch that skips the
    entry is the body of the negative form (`if not name`) and the `else` of the positive form
    (`if name`), so the pin reads the branch the skip happens in.
    """
    guards = []
    for method_name in sorted(n for n in dir(cls) if n.startswith('parse_') or n.startswith('_')):
        try:
            source = inspect.getsource(getattr(cls, method_name))
        except (TypeError, AttributeError):
            continue
        tree = ast.parse(textwrap.dedent(source))
        # The variables a method assigns from `.get('name')`, so a guard that tests one of them tests the
        # same entry name.
        name_vars = {node.targets[0].id for node in ast.walk(tree)
                     if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                     and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == 'get'
                     and node.value.args and isinstance(node.value.args[0], ast.Constant)
                     and node.value.args[0].value == 'name'
                     and isinstance(node.targets[0], ast.Name)}

        # `name_vars` is bound as a default so the nested function reads this method's set, not the last
        # one the loop leaves behind.
        def tests_name(node, bound=name_vars) -> bool:
            if isinstance(node, ast.Name):
                return node.id in bound
            return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'get' and node.args
                    and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'name')

        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            if isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not) \
                    and tests_name(node.test.operand):
                guards.append((method_name, 'negative', node.body, node.lineno))
            elif tests_name(node.test):
                guards.append((method_name, 'positive', node.orelse, node.lineno))
    return guards


def _records_in_branch(statements) -> bool:
    """True when the branch calls `mark_skipped`, the call that gives a skipped entry a record."""
    return any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
               and node.func.attr == 'mark_skipped'
               for statement in statements for node in ast.walk(statement))


def test_every_name_guard_records_the_entry_it_reads(converter_module):
    """Every entry-name guard records the entry it skips (F4.3 rule 1, `GAP_RULE`).

    Measured 2026-11-13: 69 guards, 68 of them call `mark_skipped` in the branch that skips. `_list_names`
    is the one the rule does not reach: its name can come from a `member` child, which is not an entry, and
    it marks every `entry` child before the guard, so a nameless entry there still has a record. Before the
    change the same definition measured 77 guards and 47 records, 11 negative-form guards and 19
    positive-form guards with no record.
    """
    cls = converter_module.PanoramaParser
    guards = _name_guards(cls)
    assert len(guards) == 69, len(guards)
    unrecorded = [(g[0], g[1]) for g in guards if not _records_in_branch(g[2])]
    assert unrecorded == [('_list_names', 'positive')], unrecorded
    # The exception is honest: the mark is before the guard, so the guard is not the record for that entry.
    guard = next(g for g in guards if g[0] == '_list_names')
    tree = ast.parse(textwrap.dedent(inspect.getsource(cls._list_names)))
    loop = next(n for n in ast.walk(tree) if isinstance(n, ast.For))
    marked = [c.lineno for c in ast.walk(loop) if isinstance(c, ast.Call)
              and isinstance(c.func, ast.Attribute) and c.func.attr == 'mark']
    assert marked and min(marked) < guard[3], (marked, guard[3])


def test_a_nameless_entry_reaches_the_record_and_the_report(converter_module, tmp_path):
    """A nameless entry has a record, and the report prints its line when its container is a section.

    The content holds one nameless entry at the `tag` section level and one nameless entry inside an address
    entry. The first is a report entry, so its row prints a line. The second is a property level (§3.2), so
    `is_report_entry` answers False, no line prints for it, and the parent row counts it as a property entry.
    Both have a record with the reason, and the run writes its `.tf` file for the entries it models. Before
    the change neither entry had a record.
    """
    content = tmp_path / 'nameless_entry.xml'
    content.write_text(
        '<?xml version="1.0"?>\n<config version="10.0.0">\n  <shared>\n'
        '    <tag>\n      <entry name="Named-Tag"><color>red</color></entry>\n'
        '      <entry><comments>Nameless at the section level</comments></entry>\n'
        '    </tag>\n    <address>\n      <entry name="Parent-Address">\n'
        '        <type>ip-netmask</type>\n        <value>10.0.0.1/32</value>\n'
        '        <tag><entry><color>Nameless inside the entry</color></entry></tag>\n'
        '      </entry>\n    </address>\n  </shared>\n</config>\n', encoding='utf-8')
    # `run_pipeline` builds the report, so the content path is the source the report names. An absolute path
    # passes through `FIXTURES_DIR /` unchanged.
    out = tmp_path / 'out'
    parser = run_pipeline(converter_module, str(content), out)
    assert parser is not None, 'the run refused the input'
    ledger = parser.ledger
    nameless = [e for e in ledger.entries() if e.get('name') is None]
    assert len(nameless) == 2, nameless
    for entry in nameless:
        mark = ledger.mark_for(entry)
        assert mark is not None, entry
        assert mark['destination'] == 'skipped', mark['destination']
        assert mark['detail'] == 'entry has no name attribute', mark['detail']

    # The section-level entry is a report entry, so the report prints its line.
    section_entry = next(e for e in nameless if ledger.is_report_entry(e))
    assert ledger.row_for(section_entry)['property_entries'] == 0, ledger.row_for(section_entry)
    report = written_bytes(out)[entry_coverage.REPORT_FILE].decode(encoding='utf-8')
    line = next(line for line in report.splitlines() if 'tag/' in line)
    assert line == entry_coverage.entry_line(ledger.row_for(section_entry)), line
    assert 'skipped' in line and 'captured: name only' in line, line
    assert str(content) not in report

    # The entry inside the address entry prints no line of its own: the record is its report, and the parent
    # row counts it. `rows()` holds only report entries, so the child is not in it.
    child = next(e for e in nameless if not ledger.is_report_entry(e))
    child_row = ledger.row_for(child)
    assert child_row['name'] == '(no name)' and child_row['destination'] == 'skipped', child_row
    parent = next(e for e in ledger.entries() if e.get('name') == 'Parent-Address')
    parent_row = ledger.row_for(parent)
    assert parent_row['name'] == 'Parent-Address' and parent_row['property_entries'] == 1, parent_row
    assert parent_row in ledger.rows(), ledger.rows()
    # The two tag rows are the report rows, so the child has no row of its own.
    assert [r['name'] for r in ledger.rows()] == ['Named-Tag', '(no name)', 'Parent-Address'], ledger.rows()
    # No line prints for the child, so its value text appears nowhere in the report.
    assert 'Nameless inside the entry' not in report, report

    # The `.tf` set holds the two entries the parse modelled and nothing for the nameless ones.
    tf = '\n'.join(text.decode(encoding='utf-8') for text in written_bytes(out).values())
    # The named entries the parse modelled: the tag block, and no block for the nameless entry.
    assert 'name = "Named-Tag"' in tf and 'name = "Parent-Address"' not in tf, tf
    assert tf.count('resource "panos_administrative_tag"') == 1, tf


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
    # The read rule's accepted set, so the parse cannot fail here.
    for path in [FIXTURES_DIR / name for name in corpus_fixtures()] + [SAMPLE_CONFIG]:
        parser = converter_module.PanoramaParser(xml_input.parse_xml(path))
        _parse_every(parser)
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


def test_every_row_names_the_source_that_holds_the_entry():
    """F5.4: `source` is row data for the cross-source scan, and it is the report value of
    the source (F5.1), so a file row names the file name only."""
    ledger = _ledger(GAP_FIXTURE)
    assert ledger.rows(), 'the rule needs rows to read'
    assert all(row['source'] == ledger.source.name for row in ledger.rows()), ledger.rows()
    assert all(row['source'] == GAP_FIXTURE for row in ledger.rows()), ledger.rows()
    assert all('/' not in row['source'] for row in ledger.rows()), 'the report value, not a path'


def test_the_entry_line_prints_no_source():
    """F5.4: `source` is row data, not a printed field, so a row and the same row without
    it write the same bytes: the entry-line bytes are unchanged for a one-source run."""
    ledger = _ledger(GAP_FIXTURE)
    for row in ledger.rows():
        without = {key: value for key, value in row.items() if key != 'source'}
        assert entry_coverage.entry_line(row) == entry_coverage.entry_line(without), row
        assert row['source'] not in entry_coverage.entry_line(row), row


def test_longest_matching_row_wins_for_a_sub_shape():
    """A sub-shape row describes an entry more exactly than the general row."""
    general = entry_coverage.covering_row('protocol/bgp')
    sub_shape = entry_coverage.covering_row('protocol/bgp/peer-group')
    assert general is not None and sub_shape is not None
    assert len(sub_shape.path.split('/')) > len(general.path.split('/'))
    assert entry_coverage.covering_row('protocol/bgp/peer-group') is sub_shape


def test_report_only_entry_destination_is_report():
    """1.1: the per-entry fact on the recorded object answers `report`, ahead of the destination the mark
    recorded. `mark` states no destination of its own, so the destination it records is the one the caller
    states, and here that is the table row's.

    The read order is the one the rule states: the fact on the recorded object, then the destination the mark
    recorded, then the container table row.
    """
    ledger = _ledger('kitchen_sink.xml')
    entry = next(e for e in ledger.entries() if e.get('name') == 'Country-US')
    row_destination = entry_coverage.covering_row('address').destination
    assert row_destination == 'emitted'
    # Mark first, with the table row's destination, so the mark answer is visible before the fact.
    recorded = ledger.mark(entry, {'name': entry.get('name')}, destination=row_destination)
    assert ledger.destination(entry) == 'emitted', 'no fact on the object, so the mark answers'
    # Then the fact is added through the recorded object, as the parse method does.
    recorded['report_only'] = 'no v2 resource'
    row = ledger.row_for(entry)
    assert row['destination'] == 'report', row
    # A `report` destination writes the manual report, so it is not a gap row.
    assert row not in ledger.gaps()


def test_the_destination_is_read_from_the_recorded_object_after_the_mark():
    """1.2: the fact is read at read time, so the order of `mark` and the field cannot change the answer.

    The pin reads in the order the parse method works: mark, then the field through the recorded object, then
    the destination. `::test_fields_added_through_the_recorded_object_are_recorded` holds the decision this
    depends on, that a field added after the mark is still the recorded fact, and
    `::test_skipped_entry_destination_beats_the_table_row` holds the second step, because `mark_skipped`
    records no object so the mark answers for a skipped entry.
    """
    ledger = _ledger('kitchen_sink.xml')
    entry = next(e for e in ledger.entries() if e.get('name') == 'Country-US')
    recorded = ledger.mark(entry, {'name': entry.get('name')})
    recorded['report_only'] = 'no v2 resource'
    assert ledger.destination(entry) == 'report', ledger.destination(entry)
    # The same entry read in the other order answers the same, because the answer is the recorded fact.
    other = _ledger('kitchen_sink.xml')
    other_entry = next(e for e in other.entries() if e.get('name') == 'Country-US')
    fact_first = {'name': other_entry.get('name'), 'report_only': 'no v2 resource'}
    other.mark(other_entry, fact_first)
    assert other.destination(other_entry) == ledger.destination(entry), 'the call order states nothing'
    # 1.3: the fact is read through `RecordingDict.value()`, so the decision records no property use.
    ledger.start_recording()
    recorded.get('name')
    assert ledger.destination(entry) == 'report', ledger.destination(entry)
    assert recorded.used_keys() == ('name',), recorded.used_keys()
    # The same key read through `get()` is an output read, so the two reads are different.
    recorded.get('report_only')
    assert recorded.used_keys() == ('name', 'report_only'), recorded.used_keys()


def test_skipped_entry_destination_beats_the_table_row():
    """A skipped entry is `skipped` even inside a container the table emits."""
    ledger = _ledger(GAP_FIXTURE)
    entry = next(e for e in ledger.entries() if e.get('name') is None)
    ledger.mark_skipped(entry, 'entry has no name attribute')
    assert entry_coverage.covering_row('address').destination == 'emitted'
    assert ledger.destination(entry) == 'skipped'


def test_scope_entry_destination_comes_from_the_table_row():
    """F6.5: a scope entry is an object, so its destination is the table row's.

    F4.3 rule 3 says the container table row gives the destination. F6.5 makes the scope
    containers `emitted` rows, so `EntryLedger.destination` has no scope exception left and the row
    alone decides. `is_scope_entry` stays, because the report row still names the scope an entry
    reaches the output through.
    """
    ledger = _ledger(GAP_FIXTURE)
    scope_entry = next(e for e in ledger.entries() if e.get('name') == 'Edge')
    assert container_coverage.is_scope_entry(scope_entry, ledger.parents)
    assert ledger.destination(scope_entry) == 'emitted'
    assert entry_coverage.covering_row('device-group').destination == 'emitted'


def test_parse_device_groups_row_is_emitted():
    """A device group name reaches the output as a resource, and not only through location."""
    row = entry_coverage.covering_row('device-group')
    assert row.destination == 'emitted', row
    ledger = _ledger('multi_device_templates.xml')
    dg_rows = [r for r in ledger.rows() if r['container'] == 'device-group']
    assert dg_rows and all(r['destination'] == 'emitted' for r in dg_rows)


def test_property_entries_are_counted_on_the_parent_row():
    """An entry inside a config-object entry is a property level (F4.2 AC-3.2)."""
    ledger = _ledger('kitchen_sink.xml')
    names = {row['name'] for row in ledger.rows()}
    parent = next(row for row in ledger.rows() if row['name'] == 'threat-ips')
    assert parent['property_entries'] == 1, parent
    # The entry inside it is a property level, so it is not a row of its own.
    assert 'hourly' not in names
    assert ledger.property_entry_total() > 0


def test_an_entry_at_a_level_the_table_states_no_row_is_recorded(converter_module, tmp_path):
    """A level the container table states no row for still holds a record for the entry it reads.

    `protocol/static-routes` is such a level: the provider declares `panos_virtual_router.protocol` without
    `static_routes`, so `PROTOCOL_SHAPE` states no row for it and no method reads it. `_parse_router` records
    each entry the export states there as skipped, naming the level. The entry is inside the router entry, so
    it is a property level and prints no line of its own: the record is its report and the parent row counts it.
    Before the change the entry had no record and the parent row counted nothing.
    """
    content = tmp_path / 'static_routes_level.xml'
    content.write_text(
        '<?xml version="1.0"?>\n<config version="10.0.0">\n  <shared>\n'
        '    <network>\n      <virtual-router>\n        <entry name="VR-Static">\n'
        '          <protocol>\n            <static-routes>\n'
        '              <entry name="via-peer"><prefix>10.0.0.0/8</prefix></entry>\n'
        '            </static-routes>\n            <bgp><enabled>yes</enabled></bgp>\n'
        '          </protocol>\n        </entry>\n      </virtual-router>\n    </network>\n  </shared>\n</config>\n',
        encoding='utf-8')
    out = tmp_path / 'out'
    parser = run_pipeline(converter_module, str(content), out)
    assert parser is not None, 'the run refused the input'
    ledger = parser.ledger
    route = next(e for e in ledger.entries() if e.get('name') == 'via-peer')
    mark = ledger.mark_for(route)
    assert mark is not None, 'the entry the parse read has no record'
    assert mark['destination'] == 'skipped', mark['destination']
    assert mark['detail'] == 'no row states the protocol/static-routes level', mark['detail']
    assert ledger.captured_fields(mark) == (), ledger.captured_fields(mark)

    # The level the reason names is a level the table states no row for, so the entry is not a row of its own.
    assert entry_coverage.covering_row('protocol/static-routes') is None
    assert entry_coverage.matrix_row_for('protocol/static-routes') is None
    router = next(e for e in ledger.entries() if e.get('name') == 'VR-Static')
    parent_row = ledger.row_for(router)
    assert parent_row['name'] == 'VR-Static' and parent_row['property_entries'] == 1, parent_row
    # The entry is not a report entry, so the report prints one line: the parent row, with the count.
    report = written_bytes(out)[entry_coverage.REPORT_FILE].decode(encoding='utf-8')
    assert entry_coverage.entry_line(parent_row) in report, report
    assert [r['name'] for r in ledger.rows()] == ['VR-Static'], ledger.rows()

    # The `.tf` bytes hold no block for the entry, because no resource prints a level no row states.
    tf = '\n'.join(text.decode(encoding='utf-8') for text in written_bytes(out).values())
    assert 'panos_virtual_router_static_route' not in tf, tf
    assert 'via-peer' not in tf, tf
    assert 'name = "VR-Static"' in tf, tf


def test_predefined_entries_are_not_rows():
    """`predefined` entries are PAN-OS definitions, so the header counts them."""
    ledger = _ledger(UNKNOWN_FIXTURE)
    entry = next(e for e in ledger.entries() if e.get('name') == 'ssl')
    assert not ledger.is_report_entry(entry)
    assert ledger.predefined_total() == 1
    assert 'ssl' not in {row['name'] for row in ledger.rows()}


# --- 4. Captured fields ----------------------------------------------------

def test_captured_fields_exclude_name_and_scope_facts():
    """The row identity and the five scope facts are not captured fields."""
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


def test_report_names_the_source_not_the_path(tmp_path):
    """The report body names the source name, never the path (F4.2 rule 6)."""
    report = _convert(GAP_FIXTURE, tmp_path)['report']
    file_line = [line for line in report.splitlines() if line.startswith(container_coverage.SOURCE_LABEL)]
    assert file_line == [f'Source: {GAP_FIXTURE}'], file_line
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
    parser = converter_module.PanoramaParser(xml_input.parse_xml(FIXTURES_DIR / GROUPING_FIXTURE))
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
