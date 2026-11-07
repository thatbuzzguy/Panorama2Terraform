"""F8.5 the run over many sources (`docs/API_CONVERSION_PATH.md` §2.4): one response is one source.

Six groups:

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

Every response is read through `source_fetch.fetch` with an injected producer, so the wrapper decision, the
origin, and the line map are the ones the run holds. No pin reads a response as a file, because the wrapper
decision belongs to the request that produced it.
"""

import pytest

import api_requests
import container_coverage
import entry_coverage
import panorama_to_terraform
import source_fetch
from conftest import REPO_ROOT, RESPONSES_DIR

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

    `api_requests.py` states no merge rule, so the merge across responses is the run order's work
    (`backlog.md`). Here the tables are only data for the join, so the pins read the join against the same
    responses they parse.
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
