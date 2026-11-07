"""F8.2: the scope index (`docs/API_CONVERSION_PATH.md` §2.2 and §7).

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

No test calls the network: every response is handed by an injected producer, as
`tests/test_source_fetch.py` does. No response is committed here: the committed harness is F8.4, and
the response-to-request join is F8.3.
"""

import pytest

import api_requests
import container_coverage
import panorama_to_terraform
import source_fetch
from conftest import REPO_ROOT, SRC_DIR

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
    own. The pins that scan the `src/` set read it with the other modules.
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
        ['dataclasses', 'container_coverage', 'source_fetch', 'xml_input'], 'the import rule'


def test_the_module_is_named_in_the_architecture_module_table():
    """`docs/ARCHITECTURE.md` §1 names the module, and `docs/README.md` names it as the owner of the
    index rule.
    """
    doc = (REPO_ROOT / 'docs' / 'ARCHITECTURE.md').read_text(encoding='utf-8')
    assert '| `api_requests.py` |' in doc, 'the module is in the §1 table'
    index = (REPO_ROOT / 'docs' / 'README.md').read_text(encoding='utf-8')
    assert 'api_requests.py' in index, 'the index names it'
