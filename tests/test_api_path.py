"""F8.5 the run over many sources (`docs/API_CONVERSION_PATH.md` §2.4): one response is one source.

Eight groups:

1. One response keeps its own line map and its own parent walk, so the run builds no tree from many
   responses. A report position can only name a line inside the response that holds the entry.
2. The section-to-response join: `api_requests.response_for_section` answers the response that holds the
   container a section names, through the place the section names first and the entry the run read. The
   join states no second path rule, and it refuses a section the run read no response for.
3. Each parse method runs over the response that holds its container, so the marks and the rows it
   produces name entries inside that response.
4. The report position and the source name for a path 2 run: the report row names the response that holds
   the entry, with the line inside it, and the place a section names is stated once, so the same content
   agrees with path 1 except for the source.
5. The predefined read: no container table row names a built-in container, so the run runs no parse method
   over a predefined response and the entry report names no row for a built-in entry.
6. No test calls a network: every response is handed by an injected producer, as `tests/test_source_fetch.py`
   does, and the committed response set is read through it.
7. The unit join (`docs/API_CONVERSION_PATH.md` §3): the run's unit set is read through `unit_manifest.units`,
   and the fact path 2 adds is the scope the run read for a unit. A unit the join answers no entry for, and an
   index entry the run read no rows for, are findings the join reports as data rows.
8. The entry point and the run view (`docs/API_CONVERSION_PATH.md` §6): the entry point decides the run order
   and the cross-response join, and the run view answers the entry protocol through the ledger that holds the
   entry. Both entry points call the same run sequence.

Every response is read through `source_fetch.fetch` with an injected producer, so the wrapper decision, the
origin, and the line map are the ones the run holds. No pin reads a response as a file, because the wrapper
decision belongs to the request that produced it.
"""

import argparse
import ast
import inspect
import re

import pytest

import api_requests
import api_to_terraform
import container_coverage
import entry_coverage
import ownership
import panorama_to_terraform
import provenance
import sanity_checks
import source_fetch
import unit_manifest
from conftest import REPO_ROOT, RESPONSES_DIR, SRC_DIR, TESTS_DIR

HOST = 'panorama.test'

# The two scope places the run read, in the per-scope shape F5.4 states: `result` holds the one element the
# path names. Each response holds one membership list, so the index reads its set from these responses, and
# one address entry inside a scope entry, so a report row is read inside a response rather than in a tree
# built from two responses. The same address name in both responses, at two different lines, is what the pin
# that names the source reads. `data-entry` is a container no table row covers, so the scan has a position to
# name, and `Unassigned-DG` lists no name, so the index makes no entry for it.
DEVICE_GROUP = (
    '<entry name="Office-FW">\n'
    '<devices><entry name="fw-1.example.com" /></devices>\n'
    '<address>\n'
    '<entry name="Web-Server-1"><ip-netmask>10.0.0.7</ip-netmask></entry>\n'
    '</address>\n'
    '<data-entry>\n'
    '<entry name="asset-owner"><field><member>owner</member></field></entry>\n'
    '</data-entry>\n'
    '</entry>\n'
    '<entry name="Unassigned-DG" />\n'
)
TEMPLATES = (
    '<entry name="HQ-Networks">\n'
    '<description>the stack applies this template</description>\n'
    '<devices><entry name="fw-1.example.com" /></devices>\n'
    '<address>\n'
    '<entry name="Web-Server-1"><ip-netmask>10.0.0.9</ip-netmask></entry>\n'
    '</address>\n'
    '</entry>\n'
)

# The same scope entries as responses for the entries themselves, which the run reads as its own sources.
ENTRY_OFFICE_FW = (
    '<entry name="Office-FW">\n'
    '<devices><entry name="fw-1.example.com" /></devices>\n'
    '<address>\n'
    '<entry name="Web-Server-1"><ip-netmask>10.0.0.7</ip-netmask></entry>\n'
    '</address>\n'
    '</entry>\n'
)
ENTRY_HQ_NETWORKS = (
    '<entry name="HQ-Networks">\n'
    '<devices><entry name="fw-1.example.com" /></devices>\n'
    '<address>\n'
    '<entry name="Web-Server-1"><ip-netmask>10.0.0.9</ip-netmask></entry>\n'
    '</address>\n'
    '</entry>\n'
)

PLACES = {'device-group': DEVICE_GROUP, 'templates': TEMPLATES}
ENTRIES = {'device-group/entry/Office-FW': ENTRY_OFFICE_FW, 'templates/entry/HQ-Networks': ENTRY_HQ_NETWORKS}
READ = ('device-group/entry/devices', 'templates/entry/devices')

# The same content as a whole-config export, so path 1 and path 2 read the same entries and the two reports
# can only disagree on the source they name (`docs/API_CONVERSION_PATH.md` §5).
SAME_CONTENT_EXPORT = (
    '<?xml version="1.0"?>\n<response type="success" code="0">\n<result>\n<config>\n<panorama>\n'
    + '<device-group>\n' + DEVICE_GROUP + '</device-group>\n</panorama>\n</config>\n</result>\n</response>\n'
).encode()

# A predefined read in each shape the one definition validates: the place, and one built-in entry inside it.
PREDEFINED_PLACE = ('<predefined>\n<url-list>\n'
                    '<entry name="url-list"><description>built-in</description></entry>\n'
                    '</url-list>\n</predefined>\n')
PREDEFINED_ENTRY = '<entry name="url-list"><description>built-in</description></entry>\n'


def _shape(request, body: str) -> bytes:
    """A per-scope response in the shape the request states: `result` holds the element the path names."""
    segments = request.segments()
    held = body if len(segments) == 3 else f'<{segments[0]}>\n{body}</{segments[0]}>\n'
    return ('<?xml version="1.0"?>\n<response type="success" code="0">\n<result>\n'
            + held + '</result>\n</response>\n').encode()


def _read(request, body: str, cache_dir):
    """One response, read through the injected producer. No test calls a network."""
    return source_fetch.fetch(request, cache_dir, producer=lambda r, b=body: _shape(r, b))


def _run(request, body: str, cache_dir):
    """The run for one response: the source the door parsed, and the parser built on that source."""
    source = _read(request, body, cache_dir)
    return source, panorama_to_terraform.PanoramaParser(source)


def _membership(cache_dir) -> dict:
    """The tables as the run holds them, read from the responses the run read.

    `api_requests.py` states no merge rule, so the join across responses is the run order's work, stated in
    `api_to_terraform.py` and `docs/API_CONVERSION_PATH.md` §6. Here the tables are only data for the join, so
    the pins read the join against the same responses they parse.
    """
    tables = {}
    for container in sorted(PLACES):
        _, parser = _run(source_fetch.ApiRequest(host=HOST, path=container), PLACES[container], cache_dir)
        for table, values in parser.parse_associations().items():
            for owner, names in values.items():
                tables.setdefault(table, {}).setdefault(owner, []).extend(names)
    return tables


def _index(cache_dir) -> tuple:
    return api_requests.scope_index(HOST, _membership(cache_dir), READ)


def _entry(source, name: str):
    """One entry by name, inside the tree the door parsed."""
    return next(element for element in source.root.iter() if element.get('name') == name)


def _row(ledger, name: str) -> dict:
    """One report row by entry name."""
    return next(row for row in ledger.rows() if row['name'] == name)


# --- 1. one response is one source --------------------------------------------

def test_each_response_keeps_its_own_line_map(tmp_path):
    """AC-1.1: the door records one line map per response, so a report position can only name a line inside
    the response that holds the entry. An element of one response has no line in another's map, so the run
    would need a tree across responses to name one, and the rule is that it builds none.
    """
    source_a, source_b = (
        _read(source_fetch.ApiRequest(host=HOST, path=container), PLACES[container], tmp_path / container)
        for container in sorted(PLACES)
    )
    assert source_a.lines is not source_b.lines, 'two maps, not one map for two responses'
    assert source_a.name != source_b.name, 'two sources, each named by the request that made it'

    entry_a, entry_b = _entry(source_a, 'Web-Server-1'), _entry(source_b, 'Web-Server-1')
    assert entry_a is not entry_b, 'the two responses hold two entries with the same name'
    assert source_a.line_of(entry_a) == 8, source_a.lines
    assert source_b.line_of(entry_b) == 9, source_b.lines
    assert source_b.line_of(entry_a) is None and source_a.line_of(entry_b) is None, \
        'no line in another response map, so a merged tree cannot name one'


def test_the_parent_walk_answers_within_one_response(tmp_path):
    """AC-1.2: the parent walk, the entry ledger, and the scope walk are keyed on one tree, so each response
    gets its own. A walk built for one response holds no element of another.
    """
    source_a, parser_a = _run(source_fetch.ApiRequest(host=HOST, path='device-group'), DEVICE_GROUP, tmp_path / 'a')
    source_b, parser_b = _run(source_fetch.ApiRequest(host=HOST, path='templates'), TEMPLATES, tmp_path / 'b')

    assert parser_a.parent_map is not parser_b.parent_map
    assert parser_a.parent_map.get(source_a.root) is None, 'the root of one tree has no parent'
    entry_a, entry_b = _entry(source_a, 'Web-Server-1'), _entry(source_b, 'Web-Server-1')
    assert parser_a.parent_map[entry_a].tag == 'address'
    assert parser_b.parent_map[entry_b].tag == 'address'
    assert entry_a not in parser_b.parent_map and entry_b not in parser_a.parent_map, \
        'no element of another response'
    assert parser_a.ledger.source is source_a and parser_b.ledger.source is source_b, 'one ledger per response'
    assert all(row['source'] == source_a.name for row in parser_a.ledger.rows()), parser_a.ledger.rows()
    assert all(row['source'] == source_b.name for row in parser_b.ledger.rows()), parser_b.ledger.rows()


def test_the_join_answers_one_response_per_section(tmp_path):
    """AC-1.3 and AC-2.1: the join answers one index entry per section, so no section needs a tree built
    across responses, and `api_requests.py` keeps no parser of its own.
    """
    index = _index(tmp_path)
    assert len({entry.path for entry in index}) == len(index), 'one entry per scope, so one answer per section'

    for row in container_coverage.CONTAINER_TABLE:
        place = api_requests.list_container(row.path)
        if place not in PLACES:
            continue
        answered = api_requests.response_for_section(row.path, index)
        assert answered.container == place and answered.level == api_requests.CONTAINER_LEVEL, (row.path, answered)

    # The same section inside the entry the run read joins to that entry, so a row has one answer: the
    # response the run read for the scope that holds its container.
    answered = api_requests.response_for_section('device-group/entry/address', index, name='Office-FW')
    assert answered.path == 'device-group/entry/Office-FW' and answered.level == api_requests.ENTRY_LEVEL, answered
    for name in ('parse', 'parse_bytes', 'element_from_line', 'merge', 'merge_membership', 'join_tables'):
        assert not hasattr(api_requests, name), 'the join keeps no parser and states no merge rule'


# --- 2. the section-to-response join ------------------------------------------

def test_a_section_that_names_no_scope_is_refused(tmp_path):
    """AC-2.3: a table row that names only a container names no scope, so the run reads it inside the
    response for the scope that holds it, and the join has no scope to answer.
    """
    index = _index(tmp_path)
    row = entry_coverage.covering_row('address')
    assert row is not None and row.path == 'address', 'the general row names no scope segment'
    with pytest.raises(ValueError) as excinfo:
        api_requests.response_for_section(row.path, index)
    message = str(excinfo.value)
    assert 'does not name a place' in message and 'address' in message, message


def test_the_join_refuses_a_section_inside_an_entry_the_run_read_no_response_for(tmp_path):
    """AC-2.3: the index reads its set from the membership responses, so an entry that lists no name gains no
    entry and the run read no response for it. The join refuses the section inside it rather than guessing a
    response, and answers the same section through the place the run did read.
    """
    index = _index(tmp_path)
    assert not any(entry.name == 'Unassigned-DG' for entry in index), 'the entry lists no name'
    with pytest.raises(ValueError) as excinfo:
        api_requests.response_for_section('device-group/entry/data-entry', index, name='Unassigned-DG')
    message = str(excinfo.value)
    assert 'no entry for' in message and 'device-group/entry/Unassigned-DG' in message, message

    answered = api_requests.response_for_section('device-group/entry/data-entry', index)
    assert answered.path == 'device-group' and answered.level == api_requests.CONTAINER_LEVEL, answered


def test_the_join_names_the_response_the_parse_method_runs_over(tmp_path):
    """AC-2.1, AC-2.2 and AC-2.4: the join answers the response for the scope that holds the container a row
    names, so the method named by that row runs over that response, and the report row names the same
    response. `name` is the entry the run read for the row's scope, which the run order states.
    """
    index = _index(tmp_path)

    for container, body in sorted(PLACES.items()):
        request = source_fetch.ApiRequest(host=HOST, path=container)
        source, parser = _run(request, body, tmp_path / 'place')
        rows = [row for row in container_coverage.CONTAINER_TABLE
                if api_requests.list_container(row.path) == container and row.read_via == 'pattern']
        assert rows, 'the run needs rows to run a method for'
        for row in rows:
            getattr(parser, row.method)()            # the parse method named by the row, over this response
        for report_row in parser.ledger.rows():
            answered = api_requests.response_for_section(report_row['container'], index)
            assert answered.request.cache_name() == report_row['source'], (report_row, answered)
            assert report_row['container'].split('/')[0] == answered.container, report_row

    # The run read the entry as its own source, so the join answers that source for a section inside it.
    for path, body in sorted(ENTRIES.items()):
        entry = [item for item in index if item.path == path][0]
        source, parser = _run(source_fetch.ApiRequest(host=HOST, path=path), body, tmp_path / 'entry')
        assert source.root[0].get('name') == entry.name, 'the response holds the entry its request names'
        parser.parse_address_objects()
        for report_row in parser.ledger.rows():
            section = report_row['container']
            if section in (path.split('/')[0], path):
                continue
            answered = api_requests.response_for_section(section, index, name=entry.name)
            assert answered is entry, (section, answered)
            assert answered.request.cache_name() == report_row['source'], report_row
            row_entry = next(e for e in source.root.iter() if e.get('name') == report_row['name'])
            assert report_row['line'] == source.line_of(row_entry), \
                'the position is the line inside the response that holds the entry the row names'


# --- 3. the parse method runs over one response -------------------------------

def test_a_parse_method_marks_only_the_entries_in_its_own_response(tmp_path):
    """AC-2.4: a method run over one response marks only the entries inside it, because the mark key is the
    element of the tree that was parsed, so a row from another response cannot be read through this ledger.
    """
    source_a, parser_a = _run(source_fetch.ApiRequest(host=HOST, path='device-group'), DEVICE_GROUP, tmp_path / 'a')
    source_b, parser_b = _run(source_fetch.ApiRequest(host=HOST, path='templates'), TEMPLATES, tmp_path / 'b')
    entry_a, entry_b = _entry(source_a, 'Web-Server-1'), _entry(source_b, 'Web-Server-1')

    parser_a.parse_address_objects()
    parser_b.parse_address_objects()
    assert parser_a.ledger.marked(entry_a) and parser_b.ledger.marked(entry_b), 'each response read its own entries'
    assert not parser_a.ledger.marked(entry_b) and not parser_b.ledger.marked(entry_a), 'no mark crosses a response'

    row_a, row_b = _row(parser_a.ledger, 'Web-Server-1'), _row(parser_b.ledger, 'Web-Server-1')
    assert row_a['source'] == source_a.name and row_b['source'] == source_b.name
    assert row_a['line'] == source_a.line_of(entry_a) and row_b['line'] == source_b.line_of(entry_b)
    assert row_a['fields'] == row_b['fields'], (row_a['fields'], row_b['fields'])
    assert row_a['fields'], 'the same method read the same fields in both responses'
    assert row_a['container'] == 'device-group/entry/address' and row_b['container'] == 'templates/entry/address', \
        (row_a['container'], row_b['container'], 'the same container inside each response')


def test_the_same_name_in_two_responses_gives_two_rows_naming_two_sources(tmp_path):
    """AC-3.3: one name in two responses is two entries, so the run holds two rows, each naming the response
    that holds it with the line inside it. A merged tree would name one source and one line for both.
    """
    source_a, parser_a = _run(source_fetch.ApiRequest(host=HOST, path='device-group'), DEVICE_GROUP, tmp_path / 'a')
    source_b, parser_b = _run(source_fetch.ApiRequest(host=HOST, path='templates'), TEMPLATES, tmp_path / 'b')
    parser_a.parse_address_objects()
    parser_b.parse_address_objects()

    rows = [row for row in parser_a.ledger.rows() + parser_b.ledger.rows() if row['name'] == 'Web-Server-1']
    assert len(rows) == 2, rows
    assert {row['source'] for row in rows} == {source_a.name, source_b.name}, rows
    assert len({row['line'] for row in rows}) == 2, 'two lines, read from two maps'

    index = _index(tmp_path)
    for row in rows:
        scope = row['device_group'] or row['template']
        assert scope in ('Office-FW', 'HQ-Networks'), 'the row names the scope entry it sits in'
        place = row['container'].split('/')[0]
        assert place in PLACES, row
        # The run read the place for both rows, so `name` is the place read and the join answers the place.
        # The row from the run that read the entry names the entry response, which the join pin reads.
        answered = api_requests.response_for_section(row['container'], index)
        assert answered.path == place and answered.level == api_requests.CONTAINER_LEVEL, (row, answered)
        assert answered.request.cache_name() == row['source'], 'the join answers the row source'
        assert row['line'] > 3, 'the position is a line inside the response, not the wrapper line'


def test_the_report_position_is_the_line_inside_the_response(tmp_path):
    """AC-3.2: the position a report line names is the line inside the response that holds the entry, read
    through that response's own map, in the shape `container_coverage.position_part` states.
    """
    source, parser = _run(source_fetch.ApiRequest(host=HOST, path='device-group'), DEVICE_GROUP, tmp_path / 'run')
    findings = container_coverage.scan(source, parser.parent_map)
    assert len(findings) == 1, (findings, 'the scan reads one response, so it names one position')
    finding = findings[0]
    container = next(element for element in source.root.iter() if element.tag == 'data-entry')
    assert finding.path == 'device-group/entry/data-entry', finding
    assert finding.line == source.line_of(container) == 10, source.lines
    assert container_coverage.position_phrase(finding) == 'line 10', finding

    entry = _entry(source, 'asset-owner')
    assert _row(parser.ledger, 'asset-owner')['line'] == source.line_of(entry) == 11, source.lines

    section = container_coverage.render_section(findings, source.name)
    assert section.splitlines()[1] == f'{container_coverage.SOURCE_LABEL} {source.name}', section
    assert str(source.origin.path) not in section, 'the report names the source by its name, not its path'
    assert 'line 10' in section, section


# --- 4. the report row names its source ---------------------------------------

def test_a_path_2_report_row_names_the_response_by_name_only(tmp_path):
    """AC-3.1: the row's source is the response name, which is the key-free request identity, and it holds no
    path. The printed entry line names the position and the identity, so the source stays row data and the
    report value, which `tests/test_entry_coverage.py::test_every_row_names_the_source_that_holds_the_entry`
    already pins.
    """
    index = _index(tmp_path)
    for container, body in sorted(PLACES.items()):
        request = source_fetch.ApiRequest(host=HOST, path=container)
        source, parser = _run(request, body, tmp_path / 'row')
        rows = parser.ledger.rows()
        assert rows, 'the rule needs rows to read'
        for row in rows:
            assert row['source'] == source.name == request.cache_name(), row
            assert '/' not in row['source'], 'the report value, not a path'
            assert api_requests.response_for_section(row['container'], index).request.cache_name() \
                == row['source'], 'the row names the response the join answers'
            assert row['source'] not in entry_coverage.entry_line(row), row
            assert f'line {row["line"]:>4}' in entry_coverage.entry_line(row), row


def test_the_same_content_agrees_with_path_1_except_for_the_source(tmp_path):
    """AC-3.4: the report names the place a section names once, so the same content read as a per-scope place
    response and as a whole-config export names the same container path. The two reports disagree only on the
    source they name, which is the rule `docs/API_CONVERSION_PATH.md` §5 states.
    """
    export = source_fetch.fetch(source_fetch.ApiRequest(host=HOST), tmp_path / 'path1',
                                producer=lambda r: SAME_CONTENT_EXPORT)
    per_scope, parser = _run(source_fetch.ApiRequest(host=HOST, path='device-group'), DEVICE_GROUP, tmp_path / 'path2')
    export_parser = panorama_to_terraform.PanoramaParser(export)
    for one in (export_parser, parser):
        one.parse_device_groups()
        one.parse_associations()

    fields = ('container', 'name', 'destination', 'detail', 'fields', 'device_group')
    path1 = {tuple(row[field] for field in fields) for row in export_parser.ledger.rows()}
    path2 = {tuple(row[field] for field in fields) for row in parser.ledger.rows()}
    assert path1 == path2, (sorted(path1), sorted(path2))
    assert 'device-group/entry/address' in {row['container'] for row in parser.ledger.rows()}, \
        'the place is stated once, not twice'
    assert {row['source'] for row in export_parser.ledger.rows()} == {export.name}
    assert {row['source'] for row in parser.ledger.rows()} == {per_scope.name}
    assert export.name != per_scope.name, 'the only disagreement is the source the report names'
    assert parser.source.is_per_scope and not export.is_per_scope, 'one is a scope read, one is not'


# --- 5. the predefined read ---------------------------------------------------

def test_no_table_row_names_a_builtin_container(tmp_path):
    """AC-4.1: no container table row names a built-in container, so the run runs no parse method over a
    predefined response, and the entry report names no row for a built-in entry.
    """
    assert not [row for row in container_coverage.CONTAINER_TABLE
                if api_requests.list_container(row.path) == 'predefined'], 'no row to run a method for'
    assert 'predefined' in container_coverage.SCOPE_PATH_ROOTS
    assert 'predefined' not in container_coverage.SCOPE_CONTAINERS, 'a built-in section is a place, not a scope'

    _, parser = _run(source_fetch.ApiRequest(host=HOST, path='predefined'), PREDEFINED_PLACE, tmp_path / 'place')
    assert parser.ledger.rows() == [], 'the report names no row for a built-in entry'
    assert parser.ledger.predefined_total() == 1, 'the ledger still counts the built-in entry'
    assert container_coverage.scan(parser.source, parser.parent_map) == [], \
        'the response holds the predefined element, so the built-in rule reaches it'


def test_the_join_answers_no_response_for_a_builtin_place(tmp_path):
    """AC-4.3: the index reads its set from the membership responses, and no membership row reads
    `predefined`, so the join answers no response for a built-in place. The run can read a predefined scope as
    its declared scope, and the fact the built-in name table needs stays a live fact
    (`docs/API_CONVERSION_PATH.md` §4, `backlog.md`).
    """
    index = _index(tmp_path)
    assert not any(entry.container == 'predefined' for entry in index), 'the index read no built-in scope'
    assert container_coverage.is_scope_path('predefined'), 'the shape rule still validates it as a place'
    with pytest.raises(ValueError) as excinfo:
        api_requests.response_for_section('predefined', index)
    message = str(excinfo.value)
    assert 'no entry for' in message and 'predefined' in message, message


def test_a_predefined_entry_read_reports_the_place_as_a_finding(tmp_path):
    """AC-4.2: for an entry read inside the place, the entry sits at the place level, so the parent walk
    reaches no element tagged `predefined` and the scan reports the place. This piece adds no rule that a
    predefined source is definitions, so `backlog.md` keeps the finding. The rule that a built-in entry is not
    a finding holds for a file source and for the place read.
    """
    source, parser = _run(source_fetch.ApiRequest(host=HOST, path='predefined/entry/url-list'),
                          PREDEFINED_ENTRY, tmp_path / 'entry')
    findings = container_coverage.scan(source, parser.parent_map)
    assert len(findings) == 1, (findings, 'the scan reads one response, so it names one position')
    assert findings[0].path == 'predefined', findings
    assert findings[0].line == source.line_of(source.root), \
        'the position is the line of the place element inside this response'
    row = parser.ledger.rows()[0]
    assert row['container'] == 'predefined' and row['destination'] == 'unaccounted', row
    assert parser.ledger.predefined_total() == 0, 'the walk never reaches the built-in element here'
    assert 'the scan has no rule that a predefined source is definitions' in \
        (REPO_ROOT / 'backlog.md').read_text(encoding='utf-8'), 'the finding stays recorded, not decided here'


# --- 6. the committed set, read one response at a time ------------------------

def test_the_committed_response_is_one_source_and_names_itself_in_the_report(tmp_path):
    """AC-5.2: the committed per-scope response is one source, read through the injected producer, and the
    report rows for it name that response with the line inside it. The response name is the key-free request
    identity the file is named by, so the report names no path and no credential.
    """
    request = source_fetch.ApiRequest(host=HOST, path='device-group')
    committed = (RESPONSES_DIR / request.cache_name()).read_bytes()
    assert 'device-group' in committed.decode('utf-8'), 'the committed response is the device-group read'

    source = source_fetch.fetch(request, tmp_path, producer=lambda r: committed)
    parser = panorama_to_terraform.PanoramaParser(source)
    index = api_requests.scope_index(HOST, parser.parse_associations(), ('device-group/entry/devices',))
    rows = parser.ledger.rows()
    assert rows, 'the rule needs rows to read'
    for row in rows:
        assert row['source'] == source.name == request.cache_name(), row
        assert '/' not in row['source'], 'the report value, not a path'
        assert api_requests.response_for_section(row['container'], index).request.cache_name() == row['source']
        assert row['line'] and row['line'] > 3, 'the position is a line inside the response, not the wrapper'

    # The line the report names is the line inside the committed bytes, which a reader can reopen.
    entry = _entry(source, 'Office-FW')
    lines = committed.decode('utf-8').splitlines()
    assert source.line_of(entry) == lines.index('  <entry name="Office-FW">') + 1, source.lines
    assert api_requests.response_for_section('device-group', index).request.cache_name() == source.name
    assert (RESPONSES_DIR / source.name).is_file(), 'the origin names the committed response'


def test_no_test_in_this_file_calls_a_network_producer(tmp_path, monkeypatch):
    """AC-5.1: every response in this file is handed by an injected producer, so Goal 1 holds for the run over
    many sources.
    """
    monkeypatch.setattr(source_fetch, 'network_producer',
                        lambda *args, **kwargs: (_ for _ in ()).throw(
                            AssertionError('the run called the network')))
    for container, body in sorted(PLACES.items()):
        source = _read(source_fetch.ApiRequest(host=HOST, path=container), body, tmp_path / container)
        assert source.origin.kind == 'api', (container, 'the door named a fetched source')
    for path, body in sorted(ENTRIES.items()):
        source = _read(source_fetch.ApiRequest(host=HOST, path=path), body, tmp_path / 'entry reads')
        assert source.origin.kind == 'api', (path, 'the door named a fetched source')
    committed = source_fetch.fetch(source_fetch.ApiRequest(host=HOST, path='device-group'), tmp_path / 'committed',
                                   producer=lambda r: (RESPONSES_DIR / r.cache_name()).read_bytes())
    assert committed.origin.kind == 'api'
    assert (RESPONSES_DIR / committed.origin.name).is_file(), 'the origin names the committed response'


# --- 7. the unit join -----------------------------------------------------------

def _rows_for(parser, methods: tuple) -> list:
    """Run the parse methods named by the run, over the response that holds its container, and return the rows.

    The join reads the row set through one ledger, because the join is per response (F8.5), so a pin reads the
    join against one run's ledger.
    """
    for method in methods:
        getattr(parser, method)()
    return parser.ledger.rows()


def test_the_unit_join_answers_the_scope_the_run_read_for_a_unit(tmp_path):
    """AC-1.3, AC-2.1, AC-2.2 and AC-2.3: the join reads the unit set through `unit_manifest.units` and
    answers, for each unit, the index entry whose request made the response that unit's rows name. The same
    content read as a place and as an entry gives two answers for the same unit, because the fact path 2 adds
    is the scope the run read, not the scope the unit sits in.
    """
    index = _index(tmp_path)
    place_source, place_parser = _run(source_fetch.ApiRequest(host=HOST, path='device-group'),
                                      DEVICE_GROUP, tmp_path / 'place read')
    place_rows = _rows_for(place_parser, ('parse_device_groups', 'parse_associations'))
    assert place_rows, 'the join needs rows to read'
    assert {row[ownership.SOURCE_FIELD] for row in place_rows} == {place_source.name}, \
        'each row names the response the run read'
    place_pairs = api_requests.join_units(index, place_parser.ledger)
    assert [facts for facts, _entry in place_pairs] == unit_manifest.units(place_parser.ledger), \
        'the join reads the unit set through the one rule'

    entry_source, entry_parser = _run(source_fetch.ApiRequest(host=HOST, path='device-group/entry/Office-FW'),
                                      ENTRY_OFFICE_FW, tmp_path / 'entry read')
    entry_rows = _rows_for(entry_parser, ('parse_device_groups', 'parse_address_objects'))
    assert entry_rows, 'the join needs rows to read'
    assert {row[ownership.SOURCE_FIELD] for row in entry_rows} == {entry_source.name}, \
        'the same content, named by a different request'
    entry_pairs = api_requests.join_units(index, entry_parser.ledger)
    assert [facts for facts, _entry in entry_pairs] == unit_manifest.units(entry_parser.ledger), entry_pairs

    # The two runs read the same content, so the units they share are the same units, and the join answers a
    # shared unit with the response the run read: the place response for one run, the entry response for the
    # other. That answer is the fact path 1 cannot state.
    shared = sorted(set(unit_manifest.units(place_parser.ledger)) & set(unit_manifest.units(entry_parser.ledger)))
    assert shared, 'the two runs share a unit'
    for facts in shared:
        assert [entry.path for row_facts, entry in place_pairs if row_facts == facts] == ['device-group'], \
            (facts, place_pairs)
        assert [entry.path for row_facts, entry in entry_pairs if row_facts == facts] == \
            ['device-group/entry/Office-FW'], (facts, entry_pairs)

    # The join reads the row's source field and the name rule in `source_fetch`, so the answer is the response
    # name the row carries, not a name the join states.
    for facts, answered in place_pairs:
        names = {row[ownership.SOURCE_FIELD] for row in place_rows if unit_manifest.facts_of(row) == facts}
        assert names == {answered.request.cache_name()}, (facts, names, answered)
    for facts, answered in entry_pairs:
        names = {row[ownership.SOURCE_FIELD] for row in entry_rows if unit_manifest.facts_of(row) == facts}
        assert names == {answered.request.cache_name()}, (facts, names, answered)


def test_a_unit_the_index_made_no_request_for_is_a_finding(tmp_path):
    """AC-3.1, the first direction: a unit the join answers no entry for, because the response its rows name
    is one the index made no request for. A whole-config response holds no scope entry, and a built-in place
    gains no entry, so the run read the unit through a response the index has no entry for.
    """
    index = _index(tmp_path)

    export_source = source_fetch.fetch(source_fetch.ApiRequest(host=HOST), tmp_path / 'export read',
                                       producer=lambda r: SAME_CONTENT_EXPORT)
    export_parser = panorama_to_terraform.PanoramaParser(export_source)
    export_rows = _rows_for(export_parser, ('parse_device_groups', 'parse_associations'))
    assert export_rows, 'the join needs rows to read'
    assert not export_source.is_per_scope, 'the whole-config shape holds no scope entry'

    # The response the rows name is not one the index made a request for, so the join answers no pair and every
    # unit it shows is a finding.
    assert not api_requests.join_units(index, export_parser.ledger), 'the join answers nothing here'
    unit_findings = [row for row in api_requests.unit_findings(index, export_parser.ledger) if row[1] is None]
    assert [facts for facts, _entry in unit_findings] == unit_manifest.units(export_parser.ledger), unit_findings

    # The same content read as a per-scope place is answered, so the direction is about the request the run
    # read, not about the content.
    _, place_parser = _run(source_fetch.ApiRequest(host=HOST, path='device-group'), DEVICE_GROUP,
                           tmp_path / 'place read')
    _rows_for(place_parser, ('parse_device_groups', 'parse_associations'))
    assert api_requests.join_units(index, place_parser.ledger), 'the join answers this unit'
    assert [row for row in api_requests.unit_findings(index, place_parser.ledger) if row[1] is None] == []

    # A built-in read is the same direction: no membership row reads `predefined`, so the index has no entry
    # for it. The join reports the unit and states no rule that a predefined source is definitions.
    _, predefined_parser = _run(source_fetch.ApiRequest(host=HOST, path='predefined/entry/url-list'),
                                PREDEFINED_ENTRY, tmp_path / 'entry read')
    _rows_for(predefined_parser, ('parse_address_objects',))
    assert predefined_parser.ledger.rows(), 'the ledger holds the built-in row'
    assert not api_requests.join_units(index, predefined_parser.ledger), 'the join answers nothing here'
    built_in_findings = [row for row in api_requests.unit_findings(index, predefined_parser.ledger) if row[1] is None]
    assert [facts for facts, _entry in built_in_findings] == unit_manifest.units(predefined_parser.ledger), \
        built_in_findings
    assert not any(entry.container == 'predefined' for entry in index), 'the index read no built-in scope'


def test_an_index_entry_the_run_read_no_rows_for_is_a_finding(tmp_path):
    """AC-3.2, the second direction: an index entry the run read no rows for, so no unit answers it. The set
    is read from the membership responses, so an entry the index names can exist while the run read no row for
    it.
    """
    index = _index(tmp_path)
    source, parser = _run(source_fetch.ApiRequest(host=HOST, path='device-group'), DEVICE_GROUP,
                          tmp_path / 'one response')
    rows = _rows_for(parser, ('parse_device_groups', 'parse_associations'))
    assert rows, 'the join needs rows to read'

    pairs = api_requests.join_units(index, parser.ledger)
    assert all(entry.path == 'device-group' for _facts, entry in pairs), pairs

    findings = api_requests.unit_findings(index, parser.ledger)
    assert all(facts is None for facts, _entry in findings), 'the run read rows for every unit it shows'
    answered = {entry.path for _facts, entry in pairs}
    assert [entry.path for _facts, entry in findings] == [entry.path for entry in index
                                                           if entry.path not in answered], findings

    # The join reads the name rule for each entry, so a finding names the entry whose response name the run
    # read no row for. The row set is this run's rows, because the join is per response (F8.5).
    read = {row[ownership.SOURCE_FIELD] for row in rows}
    assert all(entry.request.cache_name() not in read for _facts, entry in findings), findings
    assert read == {entry.request.cache_name() for entry in index if entry.path == 'device-group'}, \
        'the run read one response, and that response names one index entry'


def test_the_join_reports_the_findings_as_data_through_the_owners_names():
    """AC-1.2 and AC-3.3: the join names no field of its own and reports no shape of its own. It reads the
    fact order through `unit_manifest` and the field name for the row's source through `ownership`, and it
    builds no row, so the declared row shape and the declared record shape are unchanged by the join.
    """
    source = (SRC_DIR / 'api_requests.py').read_text(encoding='utf-8')
    assert 'unit_manifest.units(' in source and 'unit_manifest.facts_of(' in source, \
        'the join reads the unit rule through its owner'
    assert 'ownership.SOURCE_FIELD' in source, 'the field name for the row source is read through its owner'
    assert f"'{ownership.SOURCE_FIELD}'" not in source, 'the join states no field name of its own'
    for field in unit_manifest.FIELD_ORDER:
        assert f"'{field}'" not in source, (field, 'the join adds no field to the declared row shape')
    assert 'dict.fromkeys' not in source, 'the join builds no row shape of its own'

    # The join reports data rows only: no console line, no writer, no report section, and no unit rule.
    for name in ('finding_line', 'console_line', 'render', 'write_file', 'report_section', 'check',
                 'units', 'unit_name', 'named_fact', 'identity_digest', 'directory_name'):
        assert not hasattr(api_requests, name), (name, 'the join states no rule of this kind')
    for word in ('print(', 'CONSOLE_PREFIX', 'REPORT', 'MANUAL_SETUP'):
        assert word not in source, (word, 'the join prints nothing and writes nothing')


# --- 8. the entry point and the run view (F8.9, `docs/API_CONVERSION_PATH.md` §6) ---

def _read_order() -> tuple:
    """The order a run reads these responses: the membership lists in the order `api_requests` names them, read
    as the container that holds each list. Only the places this file holds a response for.
    """
    order = []
    for name in api_requests.membership_lists():
        container = api_requests.list_container(name)
        if container in PLACES and container not in order:
            order.append(container)
    return tuple(order)


def _parts(cache_dir, order: tuple = None) -> list:
    """The responses one run read, as the run holds them: the source the door returned, the request that read
    it, and the parser built on that source. Every response is read through the injected producer, so no test
    calls a network.
    """
    parts = []
    for path in (order or _read_order()):
        request = source_fetch.ApiRequest(host=HOST, path=path)
        source = _read(request, PLACES[path], cache_dir)
        parts.append(entry_coverage.RunPart(source, request, panorama_to_terraform.PanoramaParser(source)))
    return parts


def _concat_join(values):
    """The join as an argument, stated here so the pin measures what the view delegates to its owners. The
    merge rule is the entry point's decision and `api_requests.py` keeps none, so it is pinned by
    `test_the_entry_point_joins_the_tables_across_the_responses_it_read`.
    """
    if all(isinstance(value, list) for value in values):
        return [item for value in values for item in value]
    return values[-1]


def _producer(bodies: dict = None):
    """A producer that answers the responses this file holds, so a path 2 run can read more than the committed
    set. A request this file holds no response for answers None, the way `conftest.api_producer` does.
    """
    shapes = dict(PLACES, **(ENTRIES if bodies is None else bodies))
    return lambda request: _shape(request, shapes[request.path]) if request.path in shapes else None


def _run_args(tmp_path) -> tuple:
    """The arguments one path 2 run reads, through the entry point's own parser, and the directory it writes to."""
    argv = ['--host', HOST, '--cache-dir', str(tmp_path / 'cache'), '--output-dir', str(tmp_path / 'out')]
    parser = api_to_terraform.build_parser()
    return parser.parse_args(argv), argv


def _view(parts) -> entry_coverage.RunView:
    """The run view the entry point builds, with the join the entry point supplies."""
    return entry_coverage.RunView(parts, panorama_to_terraform.join_results)


def test_the_run_order_is_the_membership_lists_then_the_index_entries(tmp_path):
    """Criterion 1: the entry point is the only place that states the run order, and the record file the run
    wrote is that order's own statement. `api_requests.py` states no read order and `provenance.py` rule 6 says
    the read order for a path 2 run is the run order's decision, so this pin reads the order through the names
    the owners state and never through a list this file states.
    """
    args, argv = _run_args(tmp_path)
    parts, index = api_to_terraform.run_order(args, _producer())
    read = tuple(part.request.path for part in parts)

    # The order, read through the owners' names: the container each membership list names, in the order the
    # lists name them, then the entries the index names in index order. Two lists can name one container, and one
    # response is read once, so a container named by two lists enters the order at the first place a list names
    # it, and the entry part holds only the entries the run had not already read.
    named = []
    for name in api_requests.membership_lists():
        path = api_requests.scope_path(api_requests.list_container(name))
        if path in read and path not in named:
            named.append(path)
    membership = tuple(named)
    containers = tuple(entry.path for entry in index
                       if entry.level == api_requests.CONTAINER_LEVEL and entry.path in read)
    entries = tuple(entry.path for entry in index
                    if entry.level == api_requests.ENTRY_LEVEL and entry.path in read)
    assert membership and entries, 'the run read a membership response and an entry of its own'
    assert len({api_requests.list_container(name) for name in api_requests.membership_lists()}) < \
        len(api_requests.membership_lists()), 'two lists name one container, so one response is read once'
    assert containers == membership, 'the first part of the order is the membership order'
    assert read == membership + entries, (read, 'the membership responses first, then the entries')
    assert len(set(read)) == len(read), 'one response is read once'

    # The record the run wrote is the order's own statement, read back as data.
    assert api_to_terraform.run(argv, _producer()) == 0
    record = (tmp_path / 'out' / provenance.PROVENANCE_FILE).read_text(encoding='utf-8')
    assert [row.cache_entry for row in provenance.parse_records(record)] == \
        [part.request.cache_name() for part in parts], 'the record names the responses in the order it read them'

    # The order is stated once. The entry point reads it through the owners' names, so it states no path rule,
    # no sort, and no list of paths of its own, and no other module states it.
    entry_source = (SRC_DIR / 'api_to_terraform.py').read_text(encoding='utf-8')
    assert 'def run_order' in entry_source, 'the order is stated in the entry point'
    for name in ('membership_lists', 'scope_index', 'list_container', 'scope_path'):
        assert f'api_requests.{name}(' in entry_source, (name, 'the order is read through the owner')
    assert 'sorted(' not in entry_source, 'the entry point states no sort rule'
    for path in PLACES:
        assert path not in entry_source, (path, 'no path of its own')
    for module in ('api_requests.py', 'provenance.py', 'entry_coverage.py'):
        text = (SRC_DIR / module).read_text(encoding='utf-8')
        assert 'run order' in text, (module, 'names the order as the entry point\'s decision')
        assert 'def run_order' not in text, (module, 'states no read order of its own')


def test_the_entry_point_joins_the_tables_across_the_responses_it_read(tmp_path):
    """Criterion 2: `api_requests.py` keeps no merge rule, so the tables `parse_associations` answers stay per
    response and the entry point is what joins them, in the order it read them. The join names the response each
    fact came from, which path 1 cannot state: the same content read as one whole-config export names one source
    for its facts, and read as per-scope responses names one source per response. One response answers itself
    through the same join, so path 1 is unchanged.
    """
    args, _ = _run_args(tmp_path)
    parts, index = api_to_terraform.run_order(args, _producer())
    view = _view(parts)
    tables = view.parse('parse_associations')

    # Each table answer stays the response's own, in the order the run read them: the join adds no fact a
    # response did not read, and the index reads its set from the joined tables.
    for part in parts:
        for table, owners in part.parser.parse_associations().items():
            for owner, names in owners.items():
                assert tables[table][owner] == names, (part.request.path, table, owner)
    assert api_requests.scope_index(HOST, tables, api_to_terraform.lists_read(parts)) == index, \
        'the joined tables are the set the index reads'
    assert api_to_terraform.lists_read(parts) == tuple(
        name for name in api_requests.membership_lists()
        if api_requests.scope_path(api_requests.list_container(name)) in [part.request.path for part in parts]), \
        'the read set is what the entry point decided, not a list the join states'

    # A fact names the response it came from. The same entry name in two responses is two facts, each naming its
    # own response; read as one export the same content names one source for the same name. A whole-config
    # request names no path, so it is read through the door's own producer, not through the path shape.
    export = source_fetch.fetch(source_fetch.ApiRequest(host=HOST), tmp_path / 'export',
                                producer=lambda r: SAME_CONTENT_EXPORT)
    export_parser = panorama_to_terraform.PanoramaParser(export)
    export_parser.parse_address_objects()
    rows = [row for row in view.rows() if row['name'] == 'Web-Server-1']
    assert len(rows) == len(parts), (rows, 'one fact per response the run read')
    assert [row['source'] for row in rows] == [part.source.name for part in parts], \
        'the facts name the responses in run order'
    assert len({row['source'] for row in export_parser.ledger.rows()}) == 1, 'one export names one source'
    for name in ('merge', 'merge_membership', 'join_tables', 'join_value'):
        assert not hasattr(api_requests, name), (name, 'the join keeps no merge rule')

    # One response answers itself, so a path 1 run is unchanged.
    single = _view(parts[:1])
    assert single.parse('parse_associations') == parts[0].parser.parse_associations()
    assert single.rows() == parts[0].ledger().rows()


def test_the_run_sequence_is_stated_once_and_both_entry_points_call_it():
    """Criterion 3: the parse order and the emission order cannot be derived from data, so they live in one
    function that both entry points call. Neither entry point states a parse order or a block builder of its own,
    and the pins that read the sequence read the run function, not `main()`.
    """
    entry_source = (SRC_DIR / 'api_to_terraform.py').read_text(encoding='utf-8')
    path1 = inspect.getsource(panorama_to_terraform.main)
    assert 'generate_run(' in entry_source and 'generate_run(' in path1, \
        'both entry points call the sequence the run function states'

    # Neither entry point states a parse order or a block builder: the run function is the only place that names
    # them. The entry point reads the parser through one method, `parse_associations`, because the index needs the
    # tables the run read, and it holds no order of its own.
    methods = sorted({method for _, method in panorama_to_terraform.PARSE_ORDER})

    def called(text: str) -> list:
        """The parse methods and block builders an entry point calls, read as code so prose does not count."""
        out = set()
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Call):
                name = getattr(node.func, 'attr', None) or getattr(node.func, 'id', None)
                if name in methods or str(name).startswith('generate_'):
                    out.add(name)
        return sorted(out)
    assert called(entry_source) == ['generate_run', 'parse_associations'], \
        (called(entry_source), 'the entry point calls the run sequence and the one read the index needs')
    assert called(path1) == ['generate_run'], (called(path1), "path 1's entry point builds no block")
    assert not [name for name in methods if f'{name}(' in entry_source and name != 'parse_associations'], \
        (entry_source, 'the entry point states no parse order of its own')
    assert not [name for name in methods if f'{name}(' in path1], (path1, 'path 1 calls no parse method')
    assert not hasattr(api_to_terraform, 'PARSE_ORDER'), 'the entry point holds no parse order'

    # The three pins that read the run sequence read the run function, because the sequence moved there.
    for name in ('test_scope_objects.py', 'test_commit_actions.py', 'test_site_data.py'):
        text = (TESTS_DIR / name).read_text(encoding='utf-8')
        assert 'inspect.getsource(converter_module.generate_run)' in text, (name, 'reads the run function')
    # No pin reads the sequence from `main()`, because the sequence is the run function's. The needle is built in
    # two parts so this pin cannot match itself: it reads `main()` only to check that main calls the run function.
    needle = 'getsource(converter_module' + '.main)'
    reading_main = [path.name for path in sorted(TESTS_DIR.glob('test_*.py'))
                    if needle in path.read_text(encoding='utf-8')]
    assert reading_main == [], (reading_main, 'no pin reads the sequence from `main()`')


def test_the_run_view_answers_the_entry_protocol_through_the_ledger_that_holds_the_entry(tmp_path):
    """Criterion 4: the view holds the responses in run order and answers the protocol through the ledger that
    holds the entry, so an entry belongs to one response and no answer is built from a tree across responses. A
    run that read one response is answered the same as that response's own ledger.
    """
    parts = _parts(tmp_path)
    assert len({part.source.name for part in parts}) == len(parts), \
        'two responses, each named by the request that read it'
    view = entry_coverage.RunView(parts, _concat_join)

    assert view.parts() == parts, 'the view holds the parts in the order the run read them'
    assert view.entries() == [entry for part in parts for entry in part.ledger().entries()], \
        'the entry set is the parts in run order'
    assert view.rows() == [row for part in parts for row in part.ledger().rows()], \
        'the row set is the parts in run order'
    assert view.sources() == [part.source for part in parts], 'one source per response the run read'

    # Every protocol answer is the answer of the ledger that holds the entry, and the parent facts are the
    # merged per-response maps, so no entry has a parent in another response.
    for part in parts:
        for entry in part.ledger().entries():
            holder = part.ledger()
            assert view.ledger_for(entry) is holder, 'the answer goes to the ledger that holds the entry'
            assert view.row_for(entry) == holder.row_for(entry)
            assert view.mark_for(entry) is holder.mark_for(entry)
            assert view.destination(entry) == holder.destination(entry)
            assert view.is_report_entry(entry) == holder.is_report_entry(entry)
            assert view.scope(entry) == holder.scope(entry)
            assert view.line_of(entry) == holder.line_of(entry)
            assert view.source_of(entry) is holder.source
            assert view.parents[entry] is holder.parents[entry]
            assert all(entry not in other.ledger().parents for other in parts if other is not part), \
                'no parent crosses a response'

    single = entry_coverage.RunView(parts[:1], _concat_join)
    ledger = parts[0].ledger()
    for name in ('entries', 'rows', 'gaps', 'counts', 'property_findings',
                 'property_entry_total', 'predefined_total', 'gap_count'):
        assert getattr(single, name)() == getattr(ledger, name)(), name

    view.start_recording()
    assert all(part.ledger().recording for part in parts), 'the read record is turned on for every response'


def _class_node(module: str, name: str) -> ast.ClassDef:
    """One class body, so a pin reads what the class states and not the module that holds it."""
    tree = ast.parse((SRC_DIR / module).read_text(encoding='utf-8'))
    return next(node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == name)


def test_the_run_view_states_no_row_shape_and_no_field_name_of_its_own():
    """Criterion 4: the view answers, it does not decide. It states no row shape, no field name, no naming
    rule, no sort rule, no writer, no console line, and no environment name, and it takes the join as an
    argument, because the cross-response merge is the entry point's decision.
    """
    node = _class_node('entry_coverage.py', 'RunView')
    body = ast.unparse(node)
    fields = set(unit_manifest.FIELD_ORDER) | {'line', 'source', 'container', 'destination', 'detail',
                                               'fields', 'captured', 'property_entries'}
    for field in sorted(fields):
        assert f"'{field}'" not in body, (field, 'the view adds no field to the row shape its owner states')
    assert 'sorted(' not in body, 'the view states no sort rule: the row order is the run order'
    for name in ('print(', 'write_file', 'write_text', 'render', 'console_line', 'sanitize', 'name_ref'):
        assert name not in body, (name, 'the view states no rule of this kind')

    init = next(stmt for stmt in node.body if isinstance(stmt, ast.FunctionDef) and stmt.name == '__init__')
    assert 'join' in [arg.arg for arg in init.args.args], 'the join is an argument, so the view states no merge rule'


def _entry_code() -> ast.Module:
    """The entry point as code, so a pin reads what it states and not the document around it."""
    return ast.parse((SRC_DIR / 'api_to_terraform.py').read_text(encoding='utf-8'))


def test_the_entry_point_accepts_the_arguments_of_one_run_and_refuses_the_ones_that_name_one_source(tmp_path):
    """Criterion 5: the arguments are `shared_arguments`, stated once for both entry points, so the entry point
    adds none of its own. The request set is the scope set, so an argument that names one source is refused, and
    an argument error exits 2. The limit is read through the door's own argument rule.
    """
    entry = api_to_terraform.build_parser()
    shared = argparse.ArgumentParser()
    panorama_to_terraform.shared_arguments(shared)
    accepted = vars(entry.parse_args(['--host', HOST, '--output-dir', str(tmp_path / 'out')]))
    shared_accepted = vars(shared.parse_args(['--host', HOST, '--output-dir', str(tmp_path / 'out')]))
    assert sorted(accepted) == sorted(shared_accepted), 'the entry point adds no argument of its own'
    for name in ('host', 'cache_dir', 'offline', 'insecure', 'output_dir', 'max_input_bytes', 'validate',
                 'data_blocks', 'import_blocks', 'state', 'workspace', 'prune_cache'):
        assert name in accepted, (name, 'the argument one run reads')

    # The words that name one source are refused: the request set is the scope set, and the parent walk stays
    # inside one response (F8.5), so no argument names one source.
    for word in ('input_file', '--source', '--path', '--parent'):
        with pytest.raises(SystemExit) as raised:
            entry.parse_args([word, '--host', HOST, '--output-dir', str(tmp_path / 'out')])
        assert raised.value.code == 2, (word, 'an argument error exits 2')

    # The argument checks are `shared_checks`, so the entry point states none of its own beyond the words. An
    # argument error exits 2, and it exits before the run reads anything.
    entry_source = (SRC_DIR / 'api_to_terraform.py').read_text(encoding='utf-8')
    assert 'add_argument(' not in entry_source, 'the entry point adds no argument'
    assert 'shared_arguments(' in entry_source and 'shared_checks(' in entry_source, 'the checks are the owners'
    for case in (['--host', HOST, '--insecure', '--offline', '--output-dir', str(tmp_path / 'out')],
                 ['--host', HOST, '--workspace', 'ws', '--output-dir', str(tmp_path / 'out')]):
        with pytest.raises(SystemExit) as raised:
            api_to_terraform.run(case, _producer())
        assert raised.value.code == 2, (case, 'an argument error exits 2')
        assert not (tmp_path / 'out').exists(), 'an argument error writes no file'

    # The input limit is the door's rule, read through `source_fetch`, so the entry point states no limit.
    assert accepted['max_input_bytes'] == source_fetch.DEFAULT_MAX_INPUT_BYTES, 'the limit is the door default'
    assert 'source_fetch.add_max_input_argument' in \
        (SRC_DIR / 'panorama_to_terraform.py').read_text(encoding='utf-8'), 'the door owns the argument rule'
    assert 'max_input_bytes=args.max_input_bytes' in entry_source, 'the limit is passed to the owners'


def test_the_entry_point_passes_the_index_it_built_to_the_gate_and_keeps_the_gate_code(tmp_path):
    """Criterion 6: `run_checks` reports `request_set` as NOT RUN when it has no index, so the entry point passes
    the index and the run view it built. Path 1 still passes no index, because it read no request. The join
    findings print through the gate, so the entry point prints no join block of its own, and the exit code stays
    the gate's decision.
    """
    args, argv = _run_args(tmp_path)
    parts, index = api_to_terraform.run_order(args, _producer())
    view = _view(parts)
    out = tmp_path / 'out'
    assert api_to_terraform.run(argv, _producer()) == 0, 'the gate decided 0 for a run that wrote no finding'

    # The gate reads the index the entry point built. Without it the join reports as NOT RUN, so the run's own
    # gate call is the only place the join can run. A join finding prints through the gate: an index that holds
    # only one of the responses the run read finds rows that name a response the index does not hold.
    assert sanity_checks.run_checks(out).result_of('request_set') == sanity_checks.NOT_RUN
    with_index = sanity_checks.run_checks(out, ledger=view, index=index)
    assert with_index.result_of('request_set') != sanity_checks.NOT_RUN, 'the gate ran the join for this run'
    read_one = parts[:1]
    smaller = api_requests.scope_index(HOST, read_one[0].parser.parse_associations(),
                                       api_to_terraform.lists_read(read_one))
    assert sanity_checks.run_checks(out, ledger=view, index=smaller).findings('request_set'), \
        'the join findings print through the gate'

    entry_source = (SRC_DIR / 'api_to_terraform.py').read_text(encoding='utf-8')
    path1 = inspect.getsource(panorama_to_terraform.main)
    assert 'index=index' in entry_source, 'the entry point passes the index it built'
    assert 'run_checks' not in entry_source, 'the gate call is the run sequence, stated once'
    assert 'index=' not in path1, "path 1 passes no index: it read no request"

    # The findings print through the gate, so the entry point states no join block and no report of its own.
    for node in ast.walk(_entry_code()):
        if isinstance(node, ast.Call) and getattr(node.func, 'id', '') == 'print':
            assert any(getattr(inner.func, 'attr', '') in ('read_line', 'state_line')
                       for inner in ast.walk(node) if isinstance(inner, ast.Call)), \
                'the entry point prints only the lines the owners state'

    # The exit code is the gate's decision: a file the gate fails on exits 1, and a refused input exits 1 and
    # writes no file.
    (out / 'planted.tf').write_text(
        'resource "panos_address" "planted_00000000" {\n  name = "Planted"\n'
        '  value = panos_zone.ghost.name\n}\n', encoding='utf-8')
    assert sanity_checks.run_checks(out).result_of('references') == 'FAIL'
    assert api_to_terraform.run(argv, _producer()) == 1, 'the gate FAIL is the run exit code'

    refused_args, refused_argv = _run_args(tmp_path / 'refused run')
    def refusing(request):
        raise source_fetch.SourceFetchError('the response is refused by the door')
    assert api_to_terraform.run(refused_argv, refusing) == 1, 'a refused input exits 1'
    assert not [p for p in (tmp_path / 'refused run' / 'out').rglob('*') if p.is_file()], \
        'a refused input writes no file'


def test_the_entry_point_states_no_rule_an_owner_states():
    """Criterion 7: the entry point decides the run order and the arguments, and states nothing else. Every other
    rule has one owner, so the entry point reads each one through the module that owns it, and holds no rule
    name of its own.
    """
    tree = _entry_code()
    text = (SRC_DIR / 'api_to_terraform.py').read_text(encoding='utf-8')

    # What the entry point holds is the entry point name as data, and the functions that state the order, the
    # arguments, one read, and the run.
    held = sorted({t.id for node in tree.body if isinstance(node, ast.Assign) for t in node.targets})
    stated = sorted(node.name for node in tree.body if isinstance(node, ast.FunctionDef))
    assert held == ['ENTRY_POINT'], held
    assert stated == ['build_parser', 'lists_read', 'main', 'read_part', 'run', 'run_order'], stated
    # The name is the one fact the entry point can state, so it is data and not a rule.
    assert api_to_terraform.ENTRY_POINT == 'api_to_terraform.py', api_to_terraform.ENTRY_POINT
    assert not re.search(r'\d', api_to_terraform.ENTRY_POINT), 'the path name the label states is digit-free'

    # No rule an owner states. Each name below is stated by its owner, so the entry point cannot hold it, and it
    # reads what it needs through the module that owns it.
    owners = {
        'naming.py': ('sanitize', 'variable_name', 'variable_text'),
        'write_path.py': ('write_file', 'root_path'),
        'container_coverage.py': ('CONSOLE_PREFIX', 'CONTAINER_TABLE', 'console_line', 'position_part',
                                  'SECTION_TITLE'),
        'entry_coverage.py': ('REPORT_HEADING', 'GAP_HEADING', 'entry_line', 'console_lines'),
        'api_requests.py': ('scope_index', 'membership_lists', 'list_container', 'scope_path',
                            'CONTAINER_LEVEL', 'ENTRY_LEVEL'),
        'sanity_checks.py': ('run_checks', 'Finding', 'NOT_RUN'),
        'unit_manifest.py': ('FIELD_ORDER', 'identity_digest', 'directory_name', 'unit_name'),
        'source_fetch.py': ('API_KEY_ENV', 'add_max_input_argument', 'fetch', 'ApiRequest'),
    }
    for module, names in owners.items():
        for name in names:
            assert name in (SRC_DIR / module).read_text(encoding='utf-8'), (module, name, 'the owner states it')
            assert not hasattr(api_to_terraform, name), (name, 'the entry point states no rule of this kind')

    # Every module the entry point reads is an owner, so every name it uses is the owner's.
    read = sorted({node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)} |
                  {node.module.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)})
    assert read == sorted(['api_requests', 'argparse', 'entry_coverage', 'panorama_to_terraform', 'source_fetch',
                           'state_input', 'sys']), read
    used = sorted({f'{node.value.id}.{node.attr}' for node in ast.walk(tree)
                   if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                   and node.value.id in read})
    assert all(part.split('.')[0] in read for part in used), used

    # The entry point states no join rule, no block builder, no writer, no sort rule, and no file rule of its own,
    # read as the names its code holds, not as the prose around them.
    held_names = {getattr(node, 'attr', None) or getattr(node, 'id', None)
                  for node in ast.walk(tree) if isinstance(node, (ast.Name, ast.Attribute))}
    for name in ('join_value', 'merge', 'sorted', 'open', 'write_text', 'write_bytes', 'linesep'):
        assert name not in held_names, (name, 'the entry point states no rule of this kind')
    assert not any(str(name).startswith('generate_') and str(name) != 'generate_run'
                   for name in held_names), 'no block builder'

    # The environment name is the door's, stated once, so the entry point names no second one: the name it holds
    # is the value `source_fetch.API_KEY_ENV`, never the word itself.
    assert source_fetch.API_KEY_ENV not in text, 'no second environment name'
    assert not hasattr(api_to_terraform, 'API_KEY_ENV'), 'the entry point holds no environment name'
    assert not any(isinstance(node, ast.Attribute) and node.attr == 'environ' for node in ast.walk(tree)), \
        'the entry point reads no environment of its own'
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, 'id', '') == 'print':
            assert any(getattr(inner.func, 'attr', '') in ('read_line', 'state_line')
                       for inner in ast.walk(node) if isinstance(inner, ast.Call)), \
                'the entry point prints through the owners'


def test_the_report_names_each_response_the_run_read_in_run_order(tmp_path):
    """Criterion 8: the report names each source the run read, in the order it read them. One response names
    itself, so a path 1 report is byte-identical. The parts that need a full ledger are answered per response and
    concatenated in run order; the parts that read the row set read the merged set.
    """
    args, argv = _run_args(tmp_path)
    parts, _ = api_to_terraform.run_order(args, _producer())
    assert api_to_terraform.run(argv, _producer()) == 0
    report = (tmp_path / 'out' / entry_coverage.REPORT_FILE).read_text(encoding='utf-8').splitlines()
    named = [line for line in report if line.startswith(container_coverage.SOURCE_LABEL)]
    assert named == [f'{container_coverage.SOURCE_LABEL} {part.source.name}' for part in parts], \
        'one source line per response, in run order'
    assert len(named) == len({part.source.name for part in parts}), 'the run read four responses'

    # A run that read one response names that response only, which is the shape a path 1 report keeps.
    single = _view(parts[:1])
    assert single.sources() == [parts[0].source], 'one response, one source line'
    export = source_fetch.fetch(source_fetch.ApiRequest(host=HOST), tmp_path / 'export',
                                producer=lambda r: SAME_CONTENT_EXPORT)
    export_parser = panorama_to_terraform.PanoramaParser(export)
    export_parser.parse_address_objects()
    assert export_parser.ledger.sources() == [export], 'path 1 answers its own single source'

    # The parts that need a full ledger are the parts' own answers, in run order. The parts that read the row set
    # read the merged set, so a count is the merged count and not the largest part's.
    for name in ('rows', 'gaps', 'property_findings'):
        answer = getattr(_view(parts), name)()
        assert answer == [item for part in parts for item in getattr(part.ledger(), name)()], \
            (name, 'answered per response and concatenated in run order')
    merged = _view(parts).counts()
    for key in {key for part in parts for key in part.ledger().counts()}:
        assert merged[key] == sum(part.ledger().counts()[key] for part in parts if key in part.ledger().counts()), \
            (key, 'the merged set is what the report reads')
    for name in ('property_entry_total', 'predefined_total'):
        assert getattr(_view(parts), name)() == sum(getattr(part.ledger(), name)() for part in parts), name

    # The report holds no path and no credential, so the source lines name the cache entries only, and the same
    # report the run wrote is the gate's input through the owners.
    assert HOST not in report, 'the report names no host, and no path'
    assert all(len(line.split()) == 2 for line in named), 'a source line names the source and nothing else'
