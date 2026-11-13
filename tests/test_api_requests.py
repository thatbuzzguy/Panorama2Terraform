"""F8.2: the scope index (`docs/API_CONVERSION_PATH.md` §2.2 and §8).

Five groups, one per rule in `src/api_requests.py`:

1. The four membership lists. They are the `parse_associations` rows in the container table, so
   the module states no second list, and it reads no membership of its own. The four lists name
   three of the five scope facts, so `vsys` and `devices` name no entry.
2. The set is read, not guessed. The names come from the membership responses the run read, through
   the four lists, and only when the run read the response for the container that defines the entry
   a name belongs to. A partial read gains no request, an entry that lists no name gains no entry,
   and a table key names no entry.
3. Two levels, no more: one entry per scope container, then one entry per scope entry those
   containers name.
4. Order: the set is read in sorted order, one entry per scope.
5. The rules the module reads through their owners: the one scope path definition, the request
   shape, and the module table.
6. The response-to-request join (F8.3): each response is read against the index entry whose request made
   it, so the element it holds is the element that request names, and the entry name inside it agrees with
   the index. The shape rule is read through `source_fetch.py`, so this file states no shape rule of its own.
7. The offline harness (F8.4): one committed response per accepted request shape, each named by the request
   identity that produced it, read through the injected producer, and read as data by the record. The
   response set is not corpus material, so the scan and the fixture assembler never read it.

No test calls the network: every response is handed by an injected producer, as
`tests/test_source_fetch.py` does. Group 6 holds the join pins, and group 7 holds the harness pins.
"""

import ast
import hashlib

import pytest

import api_requests
import container_coverage
import panorama_to_terraform
import provenance
import source_fetch
from conftest import FIXTURES_DIR, REPO_ROOT, RESPONSES_DIR, SRC_DIR, TESTS_DIR

HOST = 'panorama.test'

# One membership response per membership container, in the per-scope shape F5.4 states: `result`
# holds the element the path names. A name inside a membership list is what the index reads. The
# names are deliberately unrelated, so a test cannot pass by matching one kind against another.
DEVICE_GROUP = (
    '<entry name="Office-FW"><devices><entry name="fw-1.example.com" /></devices></entry>\n'
    '<entry name="Datacenter-FW"><devices><entry name="fw-2.example.com" /></devices></entry>\n'
    # A container entry that lists no name reads no name, so it gains no entry.
    '<entry name="Unassigned-DG" />'
)
TEMPLATES = (
    '<entry name="HQ-Networks"><devices><entry name="fw-1.example.com" /></devices></entry>\n'
    '<entry name="DC-Networks"><devices><entry name="fw-2.example.com" /></devices></entry>'
)
STACK = (
    '<entry name="Branch-Stack"><devices><entry name="fw-3.example.com" /></devices>'
    '<templates><member>HQ-Networks</member></templates></entry>'
)
RESPONSES = {
    'device-group': DEVICE_GROUP,
    'templates': TEMPLATES,
    'template-stack': STACK,
}

# The same names in another document order, which the sorted rule must answer the same way.
DEVICE_GROUP_REORDERED = (
    '<entry name="Datacenter-FW"><devices><entry name="fw-2.example.com" /></devices></entry>\n'
    '<entry name="Office-FW"><devices><entry name="fw-1.example.com" /></devices></entry>\n'
    '<entry name="Unassigned-DG" />'
)

# The set the three membership responses name, in the order the index prints it.
INDEX_PATHS = [
    'device-group', 'template-stack', 'templates',
    'device-group/entry/Datacenter-FW', 'device-group/entry/Office-FW',
    'template-stack/entry/Branch-Stack',
    'templates/entry/DC-Networks', 'templates/entry/HQ-Networks',
]


def _response(container: str, body: str) -> bytes:
    """A per-scope membership response: `result` holds the container the path names."""
    return (f'<?xml version="1.0"?>\n<response type="success" code="0">\n<result>\n'
            f'<{container}>\n{body}\n</{container}>\n</result>\n</response>\n').encode()


def _read(read, cache_dir, bodies=None):
    """Read one response per membership container through the injected producer.

    Returns the four tables as the run holds them: what `parse_associations` read for the responses
    the run read, merged across the responses. `bodies` lets a pin hand the same names in another
    document order. No test calls a network.
    """
    bodies = bodies or RESPONSES
    membership = {}
    for list_path in read:
        container = api_requests.list_container(list_path)
        request = source_fetch.ApiRequest(host=HOST, path=container)
        source = source_fetch.fetch(request, cache_dir,
                                    producer=lambda r, c=container, b=bodies: _response(c, b[c]))
        tables = panorama_to_terraform.PanoramaParser(source).parse_associations()
        for table, values in tables.items():
            for owner, names in values.items():
                membership.setdefault(table, {}).setdefault(owner, []).extend(names)
    return membership


def _index(read, cache_dir, bodies=None):
    return api_requests.scope_index(HOST, _read(read, cache_dir, bodies), read)


# --- 1. the four membership lists ---------------------------------------------

def test_the_four_membership_lists_are_the_container_table_rows():
    """The module states no second list: the four lists are the `parse_associations` rows, and the
    join names those four paths and nothing else.
    """
    lists = api_requests.membership_lists()
    rows = sorted(row.path for row in container_coverage.CONTAINER_TABLE
                  if row.method == api_requests.MEMBERSHIP_METHOD)
    assert lists == tuple(rows), lists
    assert sorted(api_requests.LIST_JOIN) == list(lists), 'the join covers the four lists and no other path'
    for path, (table, defines) in api_requests.LIST_JOIN.items():
        # Each list belongs to the response for the container its own row names first.
        assert path.split('/')[0] == api_requests.list_container(path), path
        assert table and defines in container_coverage.SCOPE_CONTAINERS, (path, table, defines)
    # The fourth list names the templates a stack applies, which are entries inside `templates`.
    assert api_requests.LIST_JOIN['template-stack/entry/templates'] == ('stack_templates', 'templates')
    # The four lists name three of the five scope facts, so `vsys` and `devices` name no entry: the
    # index makes no request for a scope no membership row reads.
    assert sorted({defines for _, defines in api_requests.LIST_JOIN.values()}) == \
        ['device-group', 'template-stack', 'templates'], 'the three containers the lists name'


# --- 2. the set is read, not guessed ------------------------------------------

def test_the_scope_set_comes_from_the_membership_responses_the_run_read(tmp_path):
    """The index names the same set the four lists read for the same responses: no name is guessed."""
    lists = api_requests.membership_lists()
    membership = _read(lists, tmp_path)
    index = api_requests.scope_index(HOST, membership, lists)

    # Read through the tables the run holds, so the pin compares the index with what membership read.
    names = sorted({name for table in membership.values() for value in table.values() for name in value})
    entries = [entry for entry in index if entry.level == api_requests.ENTRY_LEVEL]
    assert sorted(entry.name for entry in entries) == names, names
    assert sorted(entry.container for entry in entries) == \
        ['device-group', 'device-group', 'template-stack', 'templates', 'templates'], \
        'each entry names the container that defines it'
    assert sorted(entry.path for entry in entries) == INDEX_PATHS[3:]
    # The join names the tables the parse method returns, so the join reads what the parse read.
    assert sorted(membership) == sorted(table for table, _ in api_requests.LIST_JOIN.values()), membership


def test_no_request_is_made_for_a_scope_the_run_did_not_read(tmp_path):
    """A partial read gains no request. A name read through the stack list belongs to an entry inside
    the `templates` container, so the run must have read that response to make a request for it.
    """
    read = ('template-stack/entry/devices', 'template-stack/entry/templates')
    index = _index(read, tmp_path)
    assert [entry.path for entry in index] == ['template-stack', 'template-stack/entry/Branch-Stack']
    assert not any(entry.name == 'HQ-Networks' for entry in index), \
        'the templates response was not read, so the name the stack list holds enters no entry'

    # A read set the container table does not name is refused, because the module states no list.
    with pytest.raises(ValueError) as excinfo:
        api_requests.scope_index(HOST, {}, ('vsys',))
    assert 'not membership lists' in str(excinfo.value), str(excinfo.value)


def test_a_container_that_lists_no_name_gains_no_entry(tmp_path):
    """An entry that lists nothing reads no name through a membership list, so the index makes no
    request for it: no association is better than a guessed one.
    """
    index = _index(api_requests.membership_lists(), tmp_path)
    assert not any(entry.name == 'Unassigned-DG' for entry in index), index


def test_a_device_key_names_no_entry_in_the_index(tmp_path):
    """`parse_associations` keys its tables on the entry that owns the list, and the index reads the
    names the lists hold, so a key never becomes an index entry. Three tables key on a device; the
    fourth keys on the stack that owns its list, and the stack entry it names is read through the
    devices list, not through the key.
    """
    lists = api_requests.membership_lists()
    membership = _read(lists, tmp_path)
    devices = {key for table, values in membership.items()
               if table in ('device_groups', 'templates', 'template_stacks') for key in values}
    assert devices == {'fw-1.example.com', 'fw-2.example.com', 'fw-3.example.com'}, devices
    index = api_requests.scope_index(HOST, membership, lists)
    assert not any(entry.name in devices for entry in index), index
    # Branch-Stack is an entry because the devices list named it, not because it is a table key.
    assert [entry.name for entry in index if entry.name == 'Branch-Stack'] == ['Branch-Stack']


# --- 3. two levels, no more ---------------------------------------------------

def test_the_index_makes_one_request_per_scope_container_then_one_per_entry(tmp_path):
    """Two levels, no more: one entry per membership container the run read, then one entry per scope
    entry those containers name. No entry is a third level.
    """
    index = _index(api_requests.membership_lists(), tmp_path)
    assert {entry.level for entry in index} == {api_requests.CONTAINER_LEVEL, api_requests.ENTRY_LEVEL}

    containers = [entry for entry in index if entry.level == api_requests.CONTAINER_LEVEL]
    assert [entry.path for entry in containers] == ['device-group', 'template-stack', 'templates']
    assert all(entry.name == '' for entry in containers), 'a container entry names no entry'

    entries = [entry for entry in index if entry.level == api_requests.ENTRY_LEVEL]
    assert all(entry.path == f'{entry.container}/entry/{entry.name}' for entry in entries), entries
    assert not any('devices' in entry.path for entry in index), 'the index has no third level'


# --- 4. sorted order, one entry per scope -------------------------------------

def test_the_index_is_read_in_sorted_order_and_names_one_entry_per_scope(tmp_path):
    """The set is read in sorted order: the containers first, then the entries in path order. A name
    two lists read gives one entry, and the same names in another document order give the same set.
    """
    lists = api_requests.membership_lists()
    index = _index(lists, tmp_path)
    assert [entry.path for entry in index] == INDEX_PATHS

    # HQ-Networks is read through the templates list and through the stack list: one entry.
    assert len([entry for entry in index if entry.name == 'HQ-Networks']) == 1

    reordered = _index(lists, tmp_path / 'other', {'device-group': DEVICE_GROUP_REORDERED,
                                                   'templates': TEMPLATES, 'template-stack': STACK})
    assert [entry.path for entry in reordered] == INDEX_PATHS, \
        'sorted order, so the document order does not move the set'


# --- 5. the rules the module reads through their owners ------------------------

def test_every_index_path_is_a_path_the_one_scope_path_definition_validates(tmp_path):
    """The module builds a path through `ENTRY_SEGMENT` and validates it through the one definition,
    so it states no second path rule. A name that builds a shape the definition does not validate is
    refused.
    """
    for entry in _index(api_requests.membership_lists(), tmp_path):
        assert container_coverage.is_scope_path(entry.path), entry.path

    with pytest.raises(ValueError) as excinfo:
        api_requests.scope_path('device-group', 'Odd/Name')
    assert 'does not validate' in str(excinfo.value), str(excinfo.value)

    source = (SRC_DIR / 'api_requests.py').read_text(encoding='utf-8')
    assert 'container_coverage.is_scope_path(' in source and 'ENTRY_SEGMENT' in source, \
        'the path is built through the definitions the owners state'


def test_each_entry_names_the_request_the_fetch_layer_reads(tmp_path):
    """Each entry names the request that reads its response, so the join (F8.3) reads the entry name
    and the request against the response. The request is the per-scope shape, and the module states no
    request shape, no cache rule, and no identity rule of its own.
    """
    lists = api_requests.membership_lists()
    index = _index(lists, tmp_path)
    assert all(entry.request.is_per_scope() and not entry.request.is_device_fact() for entry in index)
    assert {entry.request.request_shape() for entry in index} == {source_fetch.CONFIG_TYPE}
    assert len({entry.request.cache_name() for entry in index}) == len(index), \
        'the identity rule lives in source_fetch, so each entry finds its own cache entry'


def test_the_module_reads_the_layout_rules_through_their_owners():
    """The module owns the join between a name and a request, so it defines no naming rule, builds no
    console line, writes no file, states no environment name, and reads no source or membership of its
    own. The pins that scan the `src/` set read it with the other modules. F8.7: the unit join reads the fact
    order through `unit_manifest` and the field name for the row's source through `ownership`, so it names no
    field of its own.
    """
    assert not any(hasattr(api_requests, name) for name in
                   ('sanitize', 'sanitize_name', 'name_ref', 'console_line', 'check',
                    'merge', 'merge_membership', 'join_tables'))
    # The join is data, and the module owns no reader: the tables arrive as an argument.
    source = (SRC_DIR / 'api_requests.py').read_text(encoding='utf-8')
    assert 'def names_read(membership: dict' in source, 'the tables are taken as data'
    for rule in ('hashlib', 'sha256', 'SHAPE_PARAMS', 'API_KEY_ENV', 'PANOS_API_KEY',
                 'CONSOLE_PREFIX', 'def console_line', 'def sanitize', 'def name_ref',
                 'write_path', 'urllib', 'parse_bytes', 'findall'):
        assert rule not in source, (rule, 'the index states no second rule of this kind')
    assert [line.split()[1] for line in source.splitlines()
           if line.startswith(('import ', 'from '))] == \
        ['dataclasses', 'container_coverage', 'ownership', 'source_fetch', 'unit_manifest', 'xml_input'], \
        'the import rule, so the join reads the fact order and the row source name through their owners'


def test_the_module_is_named_in_the_architecture_module_table():
    """`docs/ARCHITECTURE.md` §1 names the module, and `docs/README.md` names it as the owner of the
    index rule.
    """
    doc = (REPO_ROOT / 'docs' / 'ARCHITECTURE.md').read_text(encoding='utf-8')
    assert '| `api_requests.py` |' in doc, 'the module is in the §1 table'
    index = (REPO_ROOT / 'docs' / 'README.md').read_text(encoding='utf-8')
    assert 'api_requests.py' in index, 'the index names it'


# --- 6. the response-to-request join ------------------------------------------

# The element each index entry's own request names, as its response holds it: the entry element for an
# entry, and the container body the membership read for a place. These are the same names the fixtures
# above hold. Group 7 reads the committed response for the per-scope shape through the injected producer, so
# the join is read against the index with committed bytes, and these bodies keep the pins that check a
# response against another entry's request.
ENTRY_BODIES = {
    'device-group/entry/Datacenter-FW':
        '<entry name="Datacenter-FW"><devices><entry name="fw-2.example.com" /></devices></entry>',
    'device-group/entry/Office-FW':
        '<entry name="Office-FW"><devices><entry name="fw-1.example.com" /></devices></entry>',
    'template-stack/entry/Branch-Stack':
        '<entry name="Branch-Stack"><devices><entry name="fw-3.example.com" /></devices>'
        '<templates><member>HQ-Networks</member></templates></entry>',
    'templates/entry/DC-Networks':
        '<entry name="DC-Networks"><devices><entry name="fw-2.example.com" /></devices></entry>',
    'templates/entry/HQ-Networks':
        '<entry name="HQ-Networks"><devices><entry name="fw-1.example.com" /></devices></entry>',
}

# A device fact, and a whole-config response: neither is a response the index made a request for, because
# a command names no scope path and the whole-config shape holds no scope entry.
FACT_BYTES = (b'<?xml version="1.0"?>\n<response type="success" code="0">\n<result>\n'
              b'<system><info name="Panorama"/></system>\n</result>\n</response>\n')
WHOLE_CONFIG = (b'<?xml version="1.0"?>\n<response type="success" code="0">\n<result>\n<config>\n'
                b'<device-group><entry name="Edge"/></device-group>\n</config>\n</result>\n</response>\n')


def _body_for(entry) -> str:
    """The body the response holds for one index entry: the entry element for an entry, and the container
    body the membership read for a place.
    """
    return ENTRY_BODIES.get(entry.path, RESPONSES[entry.container])


def _join_response(request, body: str) -> bytes:
    """A per-scope response in the shape the request states: `result` holds the element the path names,
    which is the entry itself for an entry path and the container for a place. The shape is read through
    the request's own segments, so this file states no shape rule either.
    """
    segments = request.segments()
    held = body if len(segments) == 3 else f'<{segments[0]}>\n{body}\n</{segments[0]}>'
    return ('<?xml version="1.0"?>\n<response type="success" code="0">\n<result>\n'
            + held + '\n</result>\n</response>\n').encode()


def _read_by_join(entry, body: str, cache_dir):
    """One response, read through the injected producer for the entry's own request."""
    return source_fetch.fetch(entry.request, cache_dir, producer=lambda r, b=body: _join_response(r, b))


def _place(index, container: str):
    """The container-level index entry for one scope container."""
    return [entry for entry in index if entry.level == api_requests.CONTAINER_LEVEL
            and entry.container == container][0]


def test_the_join_accepts_only_the_response_for_the_request_that_made_it(tmp_path):
    """AC-1.1 and AC-2.1: the response the injected producer hands for an entry's own request is accepted,
    and the entry names inside it agree with the index.
    """
    lists = api_requests.membership_lists()
    index = _index(lists, tmp_path)
    assert len(index) == 8, 'three places and five entries'

    for entry in index:
        source = _read_by_join(entry, _body_for(entry), tmp_path / 'join')
        inside = api_requests.join_response(source, entry, index)

        if entry.level == api_requests.ENTRY_LEVEL:
            assert inside == (entry.name,), (entry.path, inside)
        else:
            agreed = api_requests.names_in_index(index, entry.container)
            assert all(name in inside for name in agreed), (entry.path, inside, agreed)
            assert inside == tuple(sorted(inside)), (entry.path, inside)


def test_the_entry_name_inside_a_response_agrees_with_the_index(tmp_path):
    """AC-2.1, AC-2.2 and AC-2.3: the join reads the index, so a response that holds the names the index
    read for another container is refused even when the shape rule passes: the shape rule reads the path,
    and only the join reads the index.
    """
    index = _index(api_requests.membership_lists(), tmp_path)

    # The same names read through the templates list, so the templates response is accepted for it.
    templates = _place(index, 'templates')
    inside = api_requests.join_response(_read_by_join(templates, TEMPLATES, tmp_path / 'templates'),
                                        templates, index)
    assert inside == api_requests.names_in_index(index, 'templates'), inside

    # The same body handed to the device-group entry's request: `result` holds `<device-group>`, so the
    # shape rule passes, and the join refuses because the names inside are the ones for another container.
    device_group = _place(index, 'device-group')
    source = _read_by_join(device_group, TEMPLATES, tmp_path / 'other container')
    assert source.root[0].tag == 'device-group', 'the shape rule reads the path, not the names inside'
    with pytest.raises(ValueError) as excinfo:
        api_requests.join_response(source, device_group, index)
    message = str(excinfo.value)
    assert 'do not agree with the index' in message and device_group.path in message, message
    for name in api_requests.names_in_index(index, 'device-group'):
        assert name in message, 'the refusal names the names the index read and the response does not hold'


def test_the_join_refuses_a_response_whose_element_is_not_the_element_its_request_names(tmp_path):
    """AC-1.2 and AC-1.3: the join runs the fetch layer's wrapper decision, so bytes that came from another
    entry's request are refused through the same rule and the same error type, and the refusal names the
    path the entry states.
    """
    index = _index(api_requests.membership_lists(), tmp_path)
    entry = [e for e in index if e.level == api_requests.ENTRY_LEVEL and e.container == 'templates'][0]
    other = [e for e in index if e.level == api_requests.ENTRY_LEVEL and e.container == 'device-group'][0]
    data = _join_response(entry.request, ENTRY_BODIES[entry.path])

    with pytest.raises(source_fetch.SourceFetchError) as excinfo:
        source_fetch.fetch(other.request, tmp_path / 'wrong entry', producer=lambda r: data)
    message = str(excinfo.value)
    assert 'does not match the path' in message and other.path in message, message
    assert not (tmp_path / 'wrong entry' / other.request.cache_name()).exists(), \
        'no cache entry for a response the join cannot read'

    # Read through the join, the refusal is the fetch layer's words, because the join states no rule of its
    # own for which element a request names.
    accepted = source_fetch.fetch(entry.request, tmp_path / 'right entry', producer=lambda r: data)
    with pytest.raises(source_fetch.SourceFetchError) as excinfo:
        api_requests.join_response(accepted, other, index)
    assert 'does not match the path' in str(excinfo.value) and other.path in str(excinfo.value), \
        str(excinfo.value)


def test_the_join_refuses_a_response_the_index_made_no_request_for(tmp_path):
    """AC-1.4: the index makes only per-scope requests, so the join has no index entry to read a device
    fact against, and a whole-config response holds no scope entry.
    """
    index = _index(api_requests.membership_lists(), tmp_path)
    assert not any(entry.request.is_device_fact() for entry in index), 'the index makes no device fact request'

    fact = api_requests.ScopeIndexEntry(api_requests.CONTAINER_LEVEL, 'system', '', '',
                                        source_fetch.ApiRequest(host=HOST, command='show system info'))
    source = source_fetch.fetch(fact.request, tmp_path / 'fact', producer=lambda r: FACT_BYTES)
    assert source.root[0].tag == 'system', 'the shape rule passed, so only the join can refuse it'
    with pytest.raises(ValueError) as excinfo:
        api_requests.join_response(source, fact, index)
    assert 'names no scope path' in str(excinfo.value), str(excinfo.value)

    export = api_requests.ScopeIndexEntry(api_requests.CONTAINER_LEVEL, '', '', '',
                                          source_fetch.ApiRequest(host=HOST))
    source = source_fetch.fetch(export.request, tmp_path / 'whole', producer=lambda r: WHOLE_CONFIG)
    assert source.root.tag == 'config', 'the whole-config shape holds no scope entry'
    with pytest.raises(ValueError) as excinfo:
        api_requests.join_response(source, export, index)
    assert 'names no scope path' in str(excinfo.value), str(excinfo.value)


def test_an_entry_that_lists_no_name_names_no_entry_for_the_join(tmp_path):
    """AC-2.4: an entry that lists no name gains no entry in the index, so the join compares no name for it
    and accepts the response. No association is better than a guessed one, and the join states no rule of
    its own for that case.
    """
    index = _index(api_requests.membership_lists(), tmp_path)
    place = _place(index, 'device-group')
    inside = api_requests.join_response(_read_by_join(place, DEVICE_GROUP, tmp_path), place, index)
    assert 'Unassigned-DG' in inside, 'the response holds it'
    agreed = api_requests.names_in_index(index, 'device-group')
    assert 'Unassigned-DG' not in agreed, 'the index read no name for it'
    assert all(name in inside for name in agreed), 'the join compares only what the index read'


def test_an_entry_inside_a_response_with_no_name_is_refused(tmp_path):
    """AC-2.5: an entry inside a response that carries no name gives the join nothing to compare with the
    index, so it is refused rather than guessed.
    """
    index = _index(api_requests.membership_lists(), tmp_path)
    place = _place(index, 'device-group')
    body = '<entry name="Office-FW"><devices><entry name="fw-1.example.com" /></devices></entry>\n<entry />'
    source = _read_by_join(place, body, tmp_path / 'no name')
    with pytest.raises(ValueError) as excinfo:
        api_requests.join_response(source, place, index)
    assert 'carries no name' in str(excinfo.value), str(excinfo.value)


def test_the_join_returns_the_entry_names_inside_the_response_in_sorted_order(tmp_path):
    """AC-3.2: the names the run (F8.5) keys its parse on, in the same order for another document order.
    """
    index = _index(api_requests.membership_lists(), tmp_path)
    place = _place(index, 'device-group')
    ordered = api_requests.join_response(_read_by_join(place, DEVICE_GROUP, tmp_path / 'ordered'), place, index)
    reordered = api_requests.join_response(_read_by_join(place, DEVICE_GROUP_REORDERED, tmp_path / 'reordered'),
                                           place, index)
    assert ordered == tuple(sorted(ordered)), ordered
    assert ordered == reordered, 'sorted order, so the document order does not move the names'
    assert set(ordered) == {'Datacenter-FW', 'Office-FW', 'Unassigned-DG'}, ordered


def test_the_join_reads_the_same_response_the_door_parsed(tmp_path):
    """AC-1.5: the join builds no second tree and calls no producer, so the origin and the line map are the
    ones the door recorded, and a cached response reads through the join the same way.
    """
    index = _index(api_requests.membership_lists(), tmp_path)
    place = _place(index, 'device-group')
    calls = []

    def producer(request):
        calls.append(request)
        return _join_response(request, RESPONSES[place.container])

    cache = tmp_path / 'join'
    source = source_fetch.fetch(place.request, cache, producer=producer)
    inside = api_requests.join_response(source, place, index)
    assert len(calls) == 1, 'the join calls no producer'

    # The join reads the tree the door parsed, so a report line still names the line the response carries:
    # prolog 1, response 2, result 3, the container element 4.
    accepted = source_fetch.unwrap_config_root(source, place.request)
    assert accepted.origin is source.origin and accepted.lines is source.lines, 'the same origin and line map'
    assert accepted.line_of(accepted.root[0]) == 4, accepted.lines

    cached = source_fetch.fetch(place.request, cache)      # a hit: no producer, the same bytes
    assert cached.origin.path == source.origin.path, 'the origin names the cache entry the door read'
    assert api_requests.join_response(cached, place, index) == inside


def test_the_join_states_no_second_shape_rule_or_wrapper_rule():
    """AC-1.2, AC-1.4 and AC-1.5: the join reads the shape through `source_fetch.py`, states no
    command-to-element table, reads the entry rule through `xml_input.py`, and owns only the index
    agreement.
    """
    source = (SRC_DIR / 'api_requests.py').read_text(encoding='utf-8')
    assert 'source_fetch.unwrap_config_root(' in source, 'the join runs the one wrapper decision'
    assert 'names_element' in source, 'the join names the rule it reads through its owner'
    assert 'ENTRY_SEGMENT' in source, 'the entry rule is read through its owner'

    tree = ast.parse(source)
    shapes = {node.value for node in ast.walk(tree)
              if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    for shape in ('response', 'result', 'config', 'success', 'export'):
        assert shape not in shapes, (shape, 'the join states no shape rule of its own')
    # No command-to-element table: no dict in the module maps a command (words with spaces) to a name.
    tables = [node for node in ast.walk(tree) if isinstance(node, ast.Dict)
              and any(isinstance(key, ast.Constant) and isinstance(key.value, str)
                      and ' ' in key.value for key in node.keys)]
    assert not tables, 'the join states no command-to-element table'
    assert not any(hasattr(api_requests, name) for name in ('parse', 'parse_bytes', 'element_from_line')), \
        'the join keeps no parser, so it builds no second tree'


# --- 7. the offline harness (F8.4) --------------------------------------------

# One committed response per accepted request shape, in the set the layout rule names for responses
# (`tests/responses/`, `docs/ARCHITECTURE.md` §1.1). Each file is named by the key-free request identity that
# produced it, which is the cache entry the record reads as `cache_entry`, and each file states the same
# identity in its prolog comment. The identity is the words the request's shape states plus the part the
# request declares, so the three requests below find three different entries.
HARNESS = (
    ('whole-config export', source_fetch.ApiRequest(host=HOST),
     'panorama.test?category=configuration&type=export'),
    ('per-scope read', source_fetch.ApiRequest(host=HOST, path='device-group'),
     'panorama.test?action=get&path=device-group&type=config'),
    ('device fact', source_fetch.ApiRequest(host=HOST, command='show system info'),
     'panorama.test?cmd=show system info&type=op'),
)


def _committed(request) -> bytes:
    """The committed response for one request, read through the path `tests/conftest.py` builds once (§1.1)."""
    return (RESPONSES_DIR / request.cache_name()).read_bytes()


def _read_committed(request, cache_dir):
    """One committed response, read through the injected producer. No test calls a network."""
    data = _committed(request)
    return source_fetch.fetch(request, cache_dir, producer=lambda r, d=data: d)


def test_one_committed_response_per_request_shape_names_the_request_identity_that_produced_it():
    """AC-2.1 to AC-2.3: the response set holds one file per accepted shape, and each file is named by the
    identity that produced it, in the shape the record reads as `cache_entry`. The identity is key-free, so no
    file name can carry a credential.

    The shape set is read through `source_fetch.SHAPE_PARAMS`, the table that states it, so no pin here measures
    this file's own harness list: the harness holds one entry per accepted shape the table states, and the params
    the table states for a shape are inside the identity that names that shape's committed response.
    """
    assert len(HARNESS) == len(source_fetch.SHAPE_PARAMS), 'one entry per accepted shape the table states'
    files = sorted(p.name for p in RESPONSES_DIR.glob('*.xml'))
    assert files == sorted(request.cache_name() for _label, request, _identity in HARNESS), files

    # The shape comes from what each request declares, so a file is read by the request whose shape named it.
    shapes = sorted(request.request_shape() for _label, request, _identity in HARNESS)
    assert shapes == sorted(source_fetch.SHAPE_PARAMS), shapes

    for label, request, identity in HARNESS:
        shape = request.request_shape()
        text = (RESPONSES_DIR / request.cache_name()).read_text(encoding='utf-8')
        assert request.canonical() == identity, (label, request.canonical())
        assert identity in text, (label, 'the fixture names the request identity that produced it')
        assert 'key=' not in identity and 'key=' not in text, (label, 'the identity is the key-free shape')
        assert 'F8.4 offline harness' in text, (label, 'the fixture names itself as harness bytes')
        # Each param the table states for this shape is inside the identity, so the identity is the shape the
        # table states plus the part the request declares.
        for key, value in source_fetch.SHAPE_PARAMS[shape]:
            assert f'{key}={value}' in identity, (label, key, value, identity)


def test_a_committed_response_reads_through_the_injected_producer_and_the_record_names_the_same_bytes(
        tmp_path, monkeypatch):
    """AC-3.1 to AC-3.3: `fetch()` reads a committed response through the door with an injected producer, so
    no test calls a network, and the record names the same bytes the fixture holds."""
    monkeypatch.setattr(source_fetch, 'network_producer',
                        lambda *args, **kwargs: (_ for _ in ()).throw(
                            AssertionError('the harness called the network')))

    for shape, request, identity in HARNESS:
        data = _committed(request)
        cache = tmp_path / shape.replace(' ', '-')
        source = _read_committed(request, cache)

        # The cache entry the run wrote is the committed bytes, and the origin names the entry the fixture is
        # named by: the harness reads through the fetch layer, never through the file producer.
        entry = cache / request.cache_name()
        assert entry.read_bytes() == data, (shape, 'the cache holds the bytes as they arrived')
        assert source.origin.kind == 'api', (shape, 'the door named a fetched source')
        assert source.origin.name == request.cache_name() and source.origin.path == entry, \
            (shape, 'the origin names the committed response as the cache entry')

        record = provenance.record_for(source, request=request)
        assert record.cache_entry == request.cache_name(), (shape, 'the record names the same entry')
        assert record.request == identity, (shape, record.request)
        assert record.size == len(data), (shape, record.size)
        assert record.sha256 == hashlib.sha256(data).hexdigest(), (shape, record.sha256)

        # The wrapper decision read each committed response against the shape its own request states.
        if request.request_shape() == source_fetch.EXPORT_TYPE:
            assert source.root.tag == 'config', (shape, 'the whole-config shape reads the config element')
            assert record.scope == 'whole-config', (shape, 'a whole-config source names no scope path')
        elif request.request_shape() == source_fetch.CONFIG_TYPE:
            assert source.root.tag == 'result' and source_fetch.names_element(source.root[0], request), \
                (shape, 'the per-scope shape reads the element the path names')
            assert record.scope == request.path, (shape, 'the record names the path the request declared')
        else:
            assert source.root.tag == 'result' and len(list(source.root)) == 1, \
                (shape, 'the device fact shape reads the one element under result')
            assert record.scope == 'whole-config', (shape, 'a command names no scope, so the door keeps its default')


def test_the_committed_responses_are_not_corpus_material():
    """AC-1.1 to AC-1.3 (`docs/ARCHITECTURE.md` §1.1): a response is not a Panorama export, so the response
    set sits beside the corpus. The scan runs over the corpus, and the fixture assembler reads the corpus, so a
    committed response changes neither the printed fixture set nor the merge set."""
    assert RESPONSES_DIR == TESTS_DIR / 'responses', 'the path is built once, in `tests/conftest.py`'
    assert RESPONSES_DIR != FIXTURES_DIR, 'the response set is a set, not part of the corpus'

    harness = sorted(p.name for p in RESPONSES_DIR.glob('*.xml'))
    corpus = sorted(p.name for p in FIXTURES_DIR.glob('*.xml'))
    assert len(harness) == len(source_fetch.SHAPE_PARAMS), \
        (harness, 'one committed response per accepted shape the table states')
    assert not (set(harness) & set(corpus)), 'no response file is in the set the scan runs over'
    assert all(p.is_file() for p in FIXTURES_DIR.iterdir()), \
        'the corpus is one flat directory, so a response cannot enter the set the pins state'

    # The committed response fixtures the corpus pins already read stay in the corpus, so the pins that state
    # the printed fixture set read the same set as before this piece.
    for name in ('api_response.xml', 'scope_child.xml', 'scope_parent.xml'):
        assert name in corpus, (name, 'the corpus pins read it, so it is not moved')


def test_the_join_reads_the_committed_per_scope_response_through_the_injected_producer(tmp_path):
    """AC-4.1: the committed per-scope response is the membership read the index is built from, so the index
    and the join read the same committed bytes, and the join accepts the response for the entry whose request
    made it. The join pins above are unchanged, so this reads the harness without weakening them."""
    request = HARNESS[1][1]
    source = _read_committed(request, tmp_path / 'harness join')
    tables = panorama_to_terraform.PanoramaParser(source).parse_associations()
    membership = {table: {owner: list(names) for owner, names in value.items()}
                  for table, value in tables.items()}
    index = api_requests.scope_index(HOST, membership, ('device-group/entry/devices',))
    place = _place(index, 'device-group')
    inside = api_requests.join_response(source, place, index)

    assert [entry.path for entry in index] == ['device-group', 'device-group/entry/Office-FW'], index
    assert inside == ('Office-FW', 'Unassigned-DG'), inside
    assert api_requests.names_in_index(index, 'device-group') == ('Office-FW',), \
        'the entry that lists no name is inside the response but gains no index entry'
    assert inside == tuple(sorted(inside)), 'the names the run (F8.5) keys its parse on'
    assert source.origin.name == request.cache_name(), 'the join reads the response the door parsed'


def test_the_committed_op_response_shows_one_shape_and_names_no_live_fact(tmp_path):
    """AC-4.2: the committed device fact response shows the shape one command gives, and names no fact the
    tool can read offline. The fetch layer states no command-to-element table, so the shape stays an
    illustration and `docs/API_CONVERSION_PATH.md` §4 stays blocked."""
    request = HARNESS[2][1]
    source = _read_committed(request, tmp_path / 'harness fact')
    held = source.root[0]
    assert held.tag == 'show', 'the shape the fixture shows: `result` holds one element'
    assert not source_fetch.names_element(held, request), 'the one rule names no element for a command'
    assert not request.segments(), 'a command names no path, so the join has no index entry to read it against'

    text = _committed(request).decode('utf-8')
    assert 'illustration' in text, 'the fixture states that it shows a shape and is not a measurement'
    for fact in ('serial', 'rulebase', 'pre-rulebase', 'post-rulebase'):
        assert fact not in text, (fact, 'the fixture states no live fact')
    for name in ('source_fetch.py', 'api_requests.py'):
        tree = ast.parse((SRC_DIR / name).read_text(encoding='utf-8'))
        tables = [node for node in ast.walk(tree) if isinstance(node, ast.Dict)
                  and any(isinstance(key, ast.Constant) and isinstance(key.value, str)
                          and ' ' in key.value for key in node.keys)]
        assert not tables, (name, 'no command-to-element table, so the shape the fixture shows cannot become a rule')
    assert '§4' in (REPO_ROOT / 'docs' / 'API_CONVERSION_PATH.md').read_text(encoding='utf-8'), \
        'the live facts stay blocked in the design record'
