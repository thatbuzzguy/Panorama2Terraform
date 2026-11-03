"""F7.8: the six routing-profile filter containers as output.

`resource_mapping.FILTER_SHAPE` is the one table that states the shape of a filter container, because a filter
container sits outside the `protocol` object. The parse method (`PanoramaParser.parse_filter_containers`), the
emitter (`TerraformGenerator.generate_filter_containers`), the gate rule (`sanity_checks.check_filter_blocks`)
and these tests all read the same table through `resource_mapping.FILTER_TABLE`, so no second table names a
shape. `tests/test_protocol_object.py` is where the one-shape-owner rule is pinned for both tables.

Pins:

- the table against the live provider schema: one row per level the converter prints, the field names the
  provider declares, and the shape word for each field. `selects` is empty for every row, because the provider
  declares each filter choice as optional fields, and `sensitive` is empty, because no filter field is marked
  sensitive, so `VALUE_VARIABLES` gains no row for a filter field;
- the row scope: the redistribution entry is mirrored to the `match` and `set` levels, and those rows state
  leaf fields only, so the walk stops at them;
- the six `CONTAINER_TABLE` rows, the six `COVERAGE_MATRIX` rows, the six `EMITTED_TYPES` entries and the six
  `LOCATION_SCHEMA` rows, with `FILTER_TYPES` pinned against the `CONTAINER_TABLE` row notes so the decision
  has one owner;
- the parse read, the emitter print, the gate rule, and the path-keyed input spellings measured from pango;
- the three choice levels the provider enforces as exactly-one, which the table states as optional fields and
  the fixture answers with one element, so `terraform validate` accepts the run;
- one negative test per gate rule, and the gate reporting no finding on a real run.
"""

import ast
import inspect
import re
import textwrap
from pathlib import Path

import container_coverage
import entry_coverage
import import_blocks
import resource_mapping
import sanity_checks
import xml_input
from conftest import FIXTURES_DIR, GOLDEN_DIR, run_script, tf_files

CONVERTER = 'panorama_to_terraform.py'
FIXTURE = 'filter_containers.xml'

# The six containers, and the entry the fixture holds for each one.
ENTRIES = {
    'network/routing-profile/filters/access-list': 'ACL-Filter',
    'network/routing-profile/filters/as-path-access-list': 'ASPath-Filter',
    'network/routing-profile/filters/prefix-list': 'Prefix-Filter',
    'network/routing-profile/filters/community-list': 'Community-Filter',
    'network/routing-profile/filters/route-maps/bgp/bgp-entry': 'RouteMap-Filter',
    'network/routing-profile/filters/route-maps/redistribution/redist-entry': 'Redist-Filter',
}


def _container_of(path: str) -> str:
    """The container path a level path belongs to."""
    return next(c for c in resource_mapping.FILTER_PATHS if path == c or path.startswith(c + '/'))


def _row(path: str) -> dict:
    """One row of the shape table, read through the table object the reader uses."""
    row = resource_mapping.FILTER_TABLE.row(path)
    assert row is not None, path
    return row


def _fixture_entries() -> dict:
    """The fixture entry for each container, as the parse sees it."""
    source = xml_input.parse_xml(FIXTURES_DIR / FIXTURE)
    return {path: source.root.findall(f'.//{path}/entry')[0] for path in resource_mapping.FILTER_PATHS}


def _stated(path: str, entry) -> list:
    """The entry row's fields this entry states in the input, without the entry name.

    `xml_name` is the one rule that turns a table word into the element the input spells, so the fixture
    states a field when it holds the element that rule names for it.
    """
    table = resource_mapping.FILTER_TABLE
    return sorted(field for field in _row(path)['fields']
                  if field != 'name' and entry.find(table.xml_name(field, path)) is not None)


def _run(fixture: str, out_dir) -> dict:
    """Run the converter on one fixture and return the output files as text.

    The `.tf` set is read as the gate reads it, so a `.tf` entry holds the parts the run wrote for every unit,
    in path order, and a report is a codebase root-set file keyed by its name.
    """
    result = run_script(CONVERTER, str(FIXTURES_DIR / fixture), '--output-dir', str(out_dir))
    assert result.returncode == 0, result.stdout + result.stderr
    tf = tf_files(out_dir)
    files = {}
    for name in sorted({Path(key).name for key in tf}):
        files[name] = ''.join(tf[key] for key in sorted(tf) if Path(key).name == name)
    for path in sorted(Path(out_dir).iterdir()):
        if path.is_file():
            files[path.name] = path.read_text(encoding='utf-8')
    return files


def _printed_level(block, path: str) -> dict:
    """The keys the run printed for one level, read the way the gate rule reads them."""
    fields = import_blocks.fields_at(block.body)
    level = _container_of(path)
    for part in path[len(level):].split('/'):
        if not part:
            continue
        shape = resource_mapping.FILTER_TABLE.row(level)['fields'][part]
        value = fields[part]
        if shape == 'string_list':
            fields = import_blocks.fields_at(
                import_blocks.container_body(import_blocks.elements_of(value)[0]))
        else:
            fields = import_blocks.fields_at(import_blocks.container_body(value))
        level = f'{level}/{part}'
    return fields


def _findings(path: str, body: str) -> list:
    """One filter block written by hand, read by the gate rule.

    The rule reads the file text, so a test that pins a finding states the block the gate reads: the field at
    the block's own level, and the closing brace at column 0.
    """
    return sanity_checks.check_filter_blocks({
        'filters.tf': f'resource "{resource_mapping.FILTER_TYPES[path]}" "filter_00000000" {{\n{body}}}\n'})


def _detail(path: str, text: str) -> str:
    """A finding as the rule states it: the block address, then the level, then the field."""
    return f'filter {resource_mapping.FILTER_TYPES[_container_of(path)]}.filter_00000000 {path} {text}'


# --- 1. the table against the live provider schema ---------------------------

def _schema_level(node: dict) -> str:
    """What the schema states for one attribute: a leaf type, or a nesting mode.

    The provider declares a level with no `nesting_mode` as a single-nested block, which is the same word the
    table states for a level the converter prints as one object.
    """
    nested = node.get('nested_type')
    if nested is None:
        declared = node.get('type')
        return 'list' if isinstance(declared, list) else declared
    return nested.get('nesting_mode', 'single')


def _schema_node(provider_schema: dict, path: str) -> dict:
    """The provider schema attribute the table path names, walked from the container's own block.

    The entry row is the resource block, so it is read as a level through the same rule: the block is the
    `nested_type` of the level the entry row names, and every deeper row is an attribute of the level above it.
    """
    node = {'nested_type': provider_schema[resource_mapping.FILTER_TYPES[_container_of(path)]]['block']}
    for part in path[len(_container_of(path)):].split('/'):
        if part:
            node = node['nested_type']['attributes'][part]
    return node


def test_the_filter_table_is_the_measured_provider_shape(provider_schema):
    """Every filter row, field and shape word is a fact the provider declares for the pinned provider.

    `selects` is empty for every row, because the provider declares each filter choice as optional fields and
    not as required-exactly-one, and `sensitive` is empty for every row, because no filter field is marked
    sensitive: so `VALUE_VARIABLES` gains no row for a filter field.
    """
    for path, row in sorted(resource_mapping.FILTER_SHAPE.items()):
        node = _schema_node(provider_schema, path)
        word = resource_mapping.SHAPE_TO_SCHEMA.get(row['shape'], row['shape'])
        assert _schema_level(node) == word, (path, row['shape'], _schema_level(node))
        attributes = node['nested_type'].get('attributes', {})
        assert set(row['fields']) <= set(attributes), (path, row['fields'])
        for field, shape_word in row['fields'].items():
            assert _schema_level(attributes[field]) == resource_mapping.SHAPE_TO_SCHEMA.get(
                shape_word, shape_word), (path, field, shape_word)
        assert row['selects'] == {}, (path, row['selects'])
        assert row['sensitive'] == frozenset(), (path, row['sensitive'])


def test_the_row_scope_is_the_decision_acceptance_states():
    """The six entry rows are the six containers, and the redistribution `match` and `set` rows stop the walk.

    The four simple containers and the two route-map entries mirror every level the provider declares, so every
    row is a level the parse reaches through the table: 121 rows and 397 fields. The redistribution entry is
    the one table that stops early, because its `match` and `set` rows state leaf fields only, so no row stands
    under them and the levels inside them (`match.ipv4.address`, `match.next_hop`, `match.route_source`,
    `set.metric`, `set.ipv4`, `set.ipv6`) are recorded in backlog.md.
    """
    for path in resource_mapping.FILTER_PATHS:
        row = _row(path)
        # The entry is the object one block prints, and the entry name is the field the row reads for it.
        assert row['shape'] == 'object', path
        assert row['fields'].get('name') == 'string', path

    redist = 'network/routing-profile/filters/route-maps/redistribution/redist-entry'
    levels = [path for path in resource_mapping.FILTER_SHAPE if path.startswith(redist + '/')]
    assert len(levels) == 73, len(levels)
    assert sum(1 for path in levels if _row(path)['shape'] == 'string_list') == 17, levels
    mirrored = [path for path in levels if path.rsplit('/', 1)[-1] in ('match', 'set')]
    assert len(mirrored) == 34, len(mirrored)
    for path in mirrored:
        for field, shape_word in _row(path)['fields'].items():
            assert shape_word in ('string', 'bool', 'number', 'member_list'), (path, field, shape_word)
        # A row that states leaf fields only has no row under it, so the walk stops there.
        assert not [child for child in resource_mapping.FILTER_SHAPE if child.startswith(path + '/')], path

    # The three levels the provider enforces as exactly-one are rows that state their alternatives as fields,
    # so `selects` states nothing for them: the choice is the provider's, not the table's. The fixture answers
    # each with one element, which is why `terraform validate` accepts the run.
    choices = {
        'network/routing-profile/filters/access-list/type/ipv4/ipv4_entries/source_address': 'address',
        'network/routing-profile/filters/prefix-list/type/ipv4/ipv4_entries/prefix': 'entry',
        redist + '/bgp': 'ospf',
    }
    for path, chosen in choices.items():
        row = _row(path)
        assert row['shape'] == 'object' and row['selects'] == {}, (path, row)
        assert len(row['fields']) > 1, (path, row['fields'])
        assert chosen in row['fields'], (path, row['fields'])


# --- 2. the tables that name the six containers -----------------------------

def test_the_six_container_rows_name_the_provider_types():
    """`CONTAINER_TABLE` holds one emitted row per container, and the row note names the provider type.

    `FILTER_TYPES` is the same fact the row note states, so it is a lookup the emitter and the gate read and
    not a second decision: the pin compares the two.
    """
    rows = [row for row in container_coverage.CONTAINER_TABLE if row.method == 'parse_filter_containers']
    assert sorted(row.path for row in rows) == sorted(resource_mapping.FILTER_PATHS), [row.path for row in rows]
    for row in rows:
        assert row.destination == 'emitted', row
        assert row.read_via == 'pattern', row
        assert re.findall(r'panos_[a-z0-9_]+', row.note) == [resource_mapping.FILTER_TYPES[row.path]], row
        # The row path is the entry row of the shape table, read through `FILTER_TYPES` the other way.
        assert resource_mapping.filter_path(resource_mapping.FILTER_TYPES[row.path]) == row.path, row.path


def test_the_matrix_rows_are_the_entry_rows():
    """The six matrix rows read the same six containers, and their properties are the entry row's fields.

    The emitter prints the fields the entry row declares, so the properties the scan measures are that row's
    fields without the entry name (F4.4 scan scope). The file the row names is the one file the emitter writes
    for the run, and the placement is the shape the pinned data source declares for a filter type.
    """
    rows = [row for row in resource_mapping.COVERAGE_MATRIX
            if row['resource'] in resource_mapping.FILTER_TYPES.values()]
    assert len(rows) == 6, len(rows)
    for row in rows:
        path = resource_mapping.filter_path(row['resource'])
        assert row['xml_element'] == f"{path}/entry", (row['resource'], row['xml_element'])
        assert row['fixture'] == FIXTURE, row
        assert row['output_file'] == 'filters.tf', row
        assert row['emitter'] == ('generate_filter_containers',), row
        assert sorted(row['properties']) == sorted(
            field for field in _row(path)['fields'] if field != 'name'), (path, row['properties'])
        assert row['resource'] in resource_mapping.EMITTED_TYPES, row
        # A filter entry sits inside a template or a template stack, which is the shape the data source
        # declares for it.
        assert sorted(resource_mapping.LOCATION_SCHEMA[row['resource']]) == [
            'ngfw', 'template', 'template_stack'], row['resource']


# --- 3. the parse read ------------------------------------------------------

def test_the_parse_method_states_the_six_paths_and_no_field_name(converter_module):
    """The parse method states the six container paths and no field name of its own (F7.1 rule).

    Each level is read through `FILTER_TABLE`, so a table word written as a string constant inside the method
    would be a second shape owner. `name` is the one word the method states, because the entry name is the
    attribute the mark is read from, not a field of a row.
    """
    method = converter_module.PanoramaParser.parse_filter_containers
    constants = {node.value for node in ast.walk(ast.parse(textwrap.dedent(inspect.getsource(method))))
                 if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    stated = {value for value in constants if value.startswith('network/routing-profile/filters/')}
    assert stated == set(resource_mapping.FILTER_PATHS), stated
    words = {value for value in constants if '/' not in value and ' ' not in value and '\n' not in value}
    assert words == {'name'}, constants
    # Every row is reachable from one of the six paths, through the field the path names.
    for path in sorted(resource_mapping.FILTER_SHAPE):
        assert _container_of(path) in stated, (path, _container_of(path))
        assert resource_mapping.FILTER_TABLE.field_name(path) == path.rsplit('/', 1)[-1], path


def test_the_parse_marks_every_entry_it_reads(converter_module, xml_input_module):
    """One mark per entry, each carrying the five scope facts and its entry row's properties (F4.3 rule 1).

    The entry sits inside a template, so the mark holds the scope facts the emitter reads to choose the
    sub-block, and the captured fields are the entry row's fields without the entry name, which is what the
    property scan measures for the covering matrix row.
    """
    source = xml_input_module.parse_xml(FIXTURES_DIR / FIXTURE)
    parser = converter_module.PanoramaParser(source)
    parser.parse_filter_containers()
    for path, name in sorted(ENTRIES.items()):
        entry = next(e for e in parser.ledger.entries() if e.get('name') == name)
        mark = parser.ledger.mark_for(entry)
        assert mark is not None, name
        row = entry_coverage.matrix_row_for(container_coverage.section_path(
            parser.ledger.parents[entry], parser.ledger.parents, source))
        assert row is not None and row['resource'] == resource_mapping.FILTER_TYPES[path], name
        assert entry_coverage.covering_row(container_coverage.section_path(
            parser.ledger.parents[entry], parser.ledger.parents, source)).destination == 'emitted', name
        assert set(container_coverage.SCOPE_FACT_KEYS) <= set(mark['captured']), name
        assert parser.ledger.captured_fields(mark) == tuple(sorted(
            field for field in _row(path)['fields'] if field != 'name')), name
        # The fixture states every property the row declares, so the scan measures the whole row.
        assert set(_stated(path, entry)) <= set(parser.ledger.captured_fields(mark)), name


# --- 4. the emitter print ---------------------------------------------------

def test_the_emitter_prints_the_fields_the_entry_row_declares(tmp_path):
    """One block per entry, in the entry row's field order, in the one file the run writes.

    A level the row states as `object` prints as one object, a `string_list` level prints one object per
    element, and the block prints the entry name first and then the fields the input states, in sorted order.
    """
    files = _run(FIXTURE, tmp_path)
    text = files['filters.tf']
    entries = _fixture_entries()
    for path in resource_mapping.FILTER_PATHS:
        resource = resource_mapping.FILTER_TYPES[path]
        blocks = [block for block in sanity_checks.blocks({'filters.tf': text}, ('resource',))
                  if block.rtype == resource]
        assert len(blocks) == 1, (resource, len(blocks))
        # `location` is the placement sub-block, which the shape rule leaves to `location_present`.
        printed = {key: value for key, value in import_blocks.fields_at(blocks[0].body).items()
                   if key != 'location'}
        assert set(printed) == {'name'} | set(_stated(path, entries[path])), (path, sorted(printed))
        assert list(printed) == sorted(printed, key=lambda key: (key != 'name', key)), (path, list(printed))
        for field, shape_word in _row(path)['fields'].items():
            if field in printed:
                reads_as = sanity_checks.SHAPE_READS_AS.get(shape_word, shape_word)
                assert sanity_checks.value_shape(printed[field]) == reads_as, (path, field, shape_word)
    # The per-entry report is the same mark the parse wrote, so it names the entry and its properties.
    report = files['CONVERSION_REPORT.txt']
    for path, name in sorted(ENTRIES.items()):
        line = next(line for line in report.split('\n') if name in line)
        assert f'{path}/{name}' in line and resource_mapping.FILTER_TYPES[path] in line, line
        captured = line.split('captured: ')[1].split('  property entries:')[0].split(', ')
        assert captured == sorted(field for field in _row(path)['fields'] if field != 'name'), (path, captured)


def test_the_choice_levels_state_one_key_in_the_run(tmp_path):
    """The three choice levels the provider enforces as exactly-one print one key each.

    `selects` states nothing for them, because the pinned schema declares each alternative as an optional
    field, so the choice is the provider's rule and not the table's. The fixture answers each with one element,
    and `terraform validate` accepts the run for that reason.
    """
    text = _run(FIXTURE, tmp_path)['filters.tf']
    blocks = {block.rtype: block for block in sanity_checks.blocks({'filters.tf': text}, ('resource',))}
    redist = 'network/routing-profile/filters/route-maps/redistribution/redist-entry'
    choices = {
        'network/routing-profile/filters/access-list/type/ipv4/ipv4_entries/source_address': 'address',
        'network/routing-profile/filters/prefix-list/type/ipv4/ipv4_entries/prefix': 'entry',
        redist + '/bgp': 'ospf',
    }
    for path, chosen in choices.items():
        row = _row(path)
        assert len(row['fields']) > 1 and row['selects'] == {}, (path, row)
        block = blocks[resource_mapping.FILTER_TYPES[_container_of(path)]]
        assert list(_printed_level(block, path)) == [chosen], (path, _printed_level(block, path))


def test_the_gate_reads_the_run_and_reports_nothing(tmp_path):
    """The blocks the run wrote for the six containers report no finding, and the report states the check."""
    files = _run(FIXTURE, tmp_path)
    assert sanity_checks.check_filter_blocks(tf_files(tmp_path)) == [], tf_files(tmp_path)
    line = next(line for line in files['SANITY_REPORT.txt'].split('\n') if line.startswith('filter_blocks'))
    assert 'PASS' in line, files['SANITY_REPORT.txt']
    assert sanity_checks.CHECK_ORDER.index('filter_blocks') == (
        sanity_checks.CHECK_ORDER.index('protocol_object') + 1), sanity_checks.CHECK_ORDER


# --- 5. one finding per gate rule -------------------------------------------

def test_the_gate_refuses_a_field_the_row_does_not_declare():
    """Rule 1, first half: a field the entry row does not declare."""
    path = 'network/routing-profile/filters/prefix-list'
    good = '  name = "Prefix-Filter"\n  description = "the lab ranges"\n'
    assert _findings(path, good) == [], good
    findings = _findings(path, good + '  made_up = "x"\n')
    assert [f.detail for f in findings] == [_detail(path, 'made_up is not a field FILTER_SHAPE declares')], (
        findings)
    assert [f.check for f in findings] == ['filter_blocks'], findings


def test_the_gate_refuses_a_value_read_as_another_shape():
    """Rule 1, second half: a value the reader reads differently from the shape the row states."""
    path = 'network/routing-profile/filters/prefix-list'
    good = ('  name = "Prefix-Filter"\n  type = {\n    ipv4 = {\n      ipv4_entries = [\n'
            '        {\n          name = "rule-1"\n          action = "deny"\n        }\n      ]\n    }\n  }\n')
    assert _findings(path, good) == [], good
    findings = _findings(path, good.replace('type = {', 'type = "ipv4"'))
    assert [f.detail for f in findings] == [_detail(path, 'type is not a object value')], findings


def test_the_gate_reads_a_match_level_as_leaf_fields_only():
    """The row scope: the `match` and `set` rows state leaf fields, so a level inside one is a finding.

    No row stands under `match`, so the walk stops at it: a field the row does not declare is refused, and a
    value read as a leaf is the shape the row states.
    """
    path = 'network/routing-profile/filters/route-maps/redistribution/redist-entry'
    level = f"{path}/bgp/ospf/route_map/match"
    good = ('  name = "Redist-Filter"\n  bgp = {\n    ospf = {\n      route_map = [\n        {\n'
            '          name = "1"\n          action = "permit"\n          match = {\n'
            '            interface = "ethernet1/1"\n          }\n          set = {\n            tag = 100\n'
            '          }\n        }\n      ]\n    }\n  }\n')
    assert _findings(path, good) == [], good
    findings = _findings(path, good.replace(
        'match = {\n            interface = "ethernet1/1"\n          }',
        'match = {\n            ipv4 = {\n              address = "1"\n            }\n          }'))
    assert [f.detail for f in findings] == [_detail(level, 'ipv4 is not a field FILTER_SHAPE declares')], (
        findings)
    # A field the row states as a leaf is the walk's end, so the rule reads the value as a leaf too.
    findings = _findings(path, good.replace(
        'match = {\n            interface = "ethernet1/1"\n          }', 'match = "ethernet1/1"'))
    assert [f.detail for f in findings] == [_detail(
        f"{path}/bgp/ospf/route_map", 'match is not a object value')], findings


def test_the_gate_refuses_an_element_that_states_no_name():
    """Rule 4: an element inside a `[` container is an entry, so it carries the name the row reads for it."""
    path = 'network/routing-profile/filters/prefix-list'
    good = ('  name = "Prefix-Filter"\n  type = {\n    ipv4 = {\n      ipv4_entries = [\n'
            '        {\n          name = "rule-1"\n          action = "deny"\n        }\n      ]\n    }\n  }\n')
    assert _findings(path, good) == [], good
    findings = _findings(path, good.replace('name = "rule-1"\n', ''))
    assert [f.detail for f in findings] == [_detail(
        f'{path}/type/ipv4/ipv4_entries', 'element states no name')], findings


def test_the_gate_does_not_read_the_location_sub_block():
    """The placement is the `location_present` rule, so the shape rule reads the block's own fields only."""
    path = 'network/routing-profile/filters/access-list'
    block = ('resource "panos_filters_access_list_routing_profile" "filter_00000000" {\n'
             '  location = {\n    template = {\n      name = "FW-Template"\n    }\n  }\n'
             '  name = "ACL-Filter"\n  description = "deny the test host"\n}\n')
    body = block[block.index('{\n') + 1:block.rindex('}\n')]
    assert 'location' in import_blocks.fields_at(body), body
    assert 'location' not in _row(path)['fields'], _row(path)['fields']
    assert sanity_checks.check_filter_blocks({'filters.tf': block}) == [], block


# --- 6. the input spellings -------------------------------------------------

def test_the_path_keyed_exceptions_are_the_spellings_the_input_uses():
    """`FILTER_XML_NAME_EXCEPTIONS` is the one place that states a spelling the `-` rule cannot produce.

    A field that spells two ways in the input is keyed by its container path: `extended_communities` is
    `ec-regex` inside a community-list entry and `extended-community` inside a route-map match. An entry-list
    field is the singular container element that holds the entries, so those fields are in the map too. The map
    holds 15 pairs, and `ipv4_entries` and `ipv6_entries` spell the same way in two containers, so 13 distinct
    spellings, and every one of them is a spelling the `-` rule cannot produce. Five of them are in the fixture,
    because the provider requires exactly one alternative per choice, so one entry states one entry-list spelling
    only; the other ten are the spellings the pango source measures. `XML_NAME_EXCEPTIONS` stays the protocol
    table's own map.
    """
    pairs = sorted((container, field, word) for container, words in
                   resource_mapping.FILTER_XML_NAME_EXCEPTIONS.items() for field, word in words.items())
    assert len(pairs) == 15, pairs
    assert len({(field, word) for _container, field, word in pairs}) == 13, pairs
    for container, field, word in pairs:
        assert word != field.replace('_', '-'), (container, field, word)
        assert resource_mapping.FILTER_TABLE.xml_name(field, container) == word, (container, field, word)
    community = 'network/routing-profile/filters/community-list'
    redist = 'network/routing-profile/filters/route-maps/redistribution/redist-entry'
    assert resource_mapping.FILTER_TABLE.xml_name('extended_community_regexes', community) == 'ec-regex'
    assert resource_mapping.FILTER_TABLE.xml_name('extended_communities', redist) == 'extended-community'
    # A field with no exception follows the `-` rule.
    assert resource_mapping.FILTER_TABLE.xml_name('as_path_access_list', redist) == 'as-path-access-list'
    assert resource_mapping.XML_NAME_EXCEPTIONS == {'strict_l_s_a_checking': 'strict-lsa-checking'}
    fixture = (FIXTURES_DIR / FIXTURE).read_text(encoding='utf-8')
    grounded = [pair for pair in pairs if f'<{pair[2]}>' in fixture]
    assert grounded == [
        ('network/routing-profile/filters/access-list', 'ipv4_entries', 'ipv4-entry'),
        ('network/routing-profile/filters/as-path-access-list', 'aspath_entries', 'aspath-entry'),
        ('network/routing-profile/filters/community-list', 'communities', 'community'),
        ('network/routing-profile/filters/community-list', 'regular_entries', 'regular-entry'),
        ('network/routing-profile/filters/prefix-list', 'ipv4_entries', 'ipv4-entry')], grounded


def test_the_golden_case_holds_a_real_run_for_the_six_containers():
    """The corpus case for this fixture is a real run, so a table change moves the goldens with it.

    The kitchen-sink case carries one filter entry, so the property scan scope, the per-entry report and the
    `.tf` goldens move together for the same table.
    """
    golden = sorted((GOLDEN_DIR / 'filter_containers').rglob('*.tf'))
    assert golden, 'no golden .tf for the filter case'
    text = '\n'.join(path.read_text(encoding='utf-8') for path in golden)
    for resource in sorted(resource_mapping.FILTER_TYPES.values()):
        assert f'resource "{resource}"' in text, resource
    kitchen = '\n'.join(path.read_text(encoding='utf-8')
                        for path in sorted((GOLDEN_DIR / 'kitchen_sink').rglob('*.tf')))
    assert 'ACL-Kitchen' in kitchen, kitchen
