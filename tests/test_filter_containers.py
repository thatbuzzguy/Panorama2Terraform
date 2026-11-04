"""F7.8: the six routing-profile filter containers as output.

`resource_mapping.FILTER_SHAPE` is the one table that states the shape of a filter container, because a filter
container sits outside the `protocol` object. The parse method (`PanoramaParser.parse_filter_containers`), the
emitter (`TerraformGenerator.generate_filter_containers`), the gate rule (`sanity_checks.check_filter_blocks`)
and these tests all read the same table through `resource_mapping.FILTER_TABLE`, so no second table names a
shape. `tests/test_protocol_object.py` is where the one-shape-owner rule is pinned for both tables.

Pins:

- the table against the live provider schema: one row per level the converter prints, the field names the
  provider declares, and the shape word for each field. `selects` states the choice for the 14 rows that
  `terraform validate` reads as exactly one attribute, and it is empty for the rest; `sensitive` is empty,
  because no filter field is marked sensitive, so `VALUE_VARIABLES` gains no row for a filter field;
- the row scope: the redistribution entry is mirrored to the `match` and `set` levels, and those rows state
  leaf fields only, so the walk stops at them;
- the six `CONTAINER_TABLE` rows, the six `COVERAGE_MATRIX` rows, the six `EMITTED_TYPES` entries and the six
  `LOCATION_SCHEMA` rows, with `FILTER_TYPES` pinned against the `CONTAINER_TABLE` row notes so the decision
  has one owner;
- the parse read, the emitter print, the gate rule, and the path-keyed input spellings measured from pango;
- the choice rows: the 14 levels `terraform validate` reads as exactly one, the gate refusing a choice level
  that states two of them or none, and the run printing the one key each choice level states;
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

# F7.13: the filter rows `terraform validate` (provider 2.0.14, Terraform 1.16.2, measured 2026-11-03) reads as
# exactly one attribute. Each row is written as `FILTER_SHAPE` names it, and the names are the fields the row
# states that form the choice. The schema states no word for a choice, because it declares every alternative as
# an optional attribute of a `single` level, so the choice is what `terraform validate` enforces.
CHOICE_ROWS = {
    'network/routing-profile/filters/access-list/type': ('ipv4', 'ipv6'),
    'network/routing-profile/filters/access-list/type/ipv4/ipv4_entries/destination_address': ('address', 'entry'),
    'network/routing-profile/filters/access-list/type/ipv4/ipv4_entries/source_address': ('address', 'entry'),
    'network/routing-profile/filters/access-list/type/ipv6/ipv6_entries/source_address': ('address', 'entry'),
    'network/routing-profile/filters/community-list/type': ('extended', 'large', 'regular'),
    'network/routing-profile/filters/prefix-list/type': ('ipv4', 'ipv6'),
    'network/routing-profile/filters/prefix-list/type/ipv4/ipv4_entries/prefix': ('entry', 'network'),
    'network/routing-profile/filters/prefix-list/type/ipv6/ipv6_entries/prefix': ('entry', 'network'),
    'network/routing-profile/filters/route-maps/redistribution/redist-entry': (
        'bgp', 'connected_static', 'ospf', 'ospfv3', 'rip'),
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp': ('ospf', 'ospfv3', 'rib', 'rip'),
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/connected_static': (
        'bgp', 'ospf', 'ospfv3', 'rib', 'rip'),
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospf': ('bgp', 'rib', 'rip'),
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/ospfv3': ('bgp', 'rib'),
    'network/routing-profile/filters/route-maps/redistribution/redist-entry/rip': ('bgp', 'ospf', 'rib'),
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
        'filters.tf': f'resource "{resource_mapping.FILTER_TYPES[_container_of(path)]}" '
        f'"filter_00000000" {{\n{body}}}\n'})


def _detail(path: str, text: str) -> str:
    """A finding as the rule states it: the block address, then the level, then the field."""
    return f'filter {resource_mapping.FILTER_TYPES[_container_of(path)]}.filter_00000000 {path} {text}'


def _field_value(level: str, field: str, indent: int) -> str:
    """One field value written as the shape its row states, so the choice finding is the only finding.

    A level the walk enters must state the one key its row selects, so an alternative that is a level is
    written with one key when that level is a choice row too, and an element inside a `[` container states the
    name rule 4 asks for.
    """
    row = _row(level)
    shape = row['fields'][field]
    pad = ' ' * (indent + 2)
    child = resource_mapping.FILTER_TABLE.row(f'{level}/{field}')
    if shape == 'object' and child is not None and child['selects']:
        key = sorted(child['selects'])[0]
        return ('{\n' + pad + f'{key} = ' + _field_value(f'{level}/{field}', key, indent + 2) + '\n'
                + ' ' * indent + '}')
    if shape == 'string':
        return '"v"'
    if shape == 'number':
        return '1'
    if shape == 'bool':
        return 'true'
    if shape == 'string_list':
        return (f'[\n{pad}{{\n{" " * (indent + 4)}name = "e1"\n{" " * (indent + 4)}}}\n{" " * indent}]')
    return '{}'


def _choice_block_body(path: str, keys: tuple) -> str:
    """A hand-written filter block body that states `keys` at the level `path` names (F7.13).

    Each level is written at its own indent, which is the one rule `fields_at` reads, so the block can trip the
    choice finding at `path` and nothing else.
    """
    container = _container_of(path)

    def write(level: str, parts: list, indent: int) -> str:
        pad = ' ' * indent
        if not parts:
            return ''.join(f'{pad}{key} = {_field_value(level, key, indent)}\n' for key in keys)
        part = parts[0]
        shape = _row(level)['fields'][part]
        body = write(f'{level}/{part}', parts[1:], indent + (4 if shape == 'string_list' else 2))
        if shape == 'string_list':
            return (f'{pad}{part} = [\n{" " * (indent + 2)}{{\n{" " * (indent + 4)}name = "e1"\n'
                    f'{body}{" " * (indent + 4)}}}\n{pad}]\n')
        return f'{pad}{part} = {{\n{body}{pad}}}\n'

    return write(container, [p for p in path[len(container):].split('/') if p], 2)


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

    A row that states `selects` states an exactly-one choice as data, and the schema states no word for it: it
    declares every alternative as an optional attribute of a `single` level, so the shape word for a filter
    choice row is `object` as it is for every other filter level, and the choice is a rule the gate reads from
    `selects` and not a shape word. Each key `selects` names is a field the row states, so the choice is the
    whole value or part of it. `sensitive` is empty for every row, because no filter field is marked
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
        for key in row['selects']:
            assert key in row['fields'], (path, key, row['fields'])
            assert attributes[key].get('optional'), (path, key)
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

    # The choice rows are pinned by `test_the_choice_rows_are_the_levels_the_provider_reads_as_exactly_one`, so
    # this pin keeps the row scope only.
    for path in sorted(CHOICE_ROWS):
        row = _row(path)
        assert row['shape'] == 'object', (path, row['shape'])
        assert len(row['fields']) > 1, (path, row['fields'])
        assert set(CHOICE_ROWS[path]) <= set(row['fields']), (path, row['fields'])


def test_the_choice_rows_are_the_levels_the_provider_reads_as_exactly_one(provider_schema):
    """F7.13: the filter rows that state `selects` are the 14 the measurement names, and no others.

    Measured 2026-11-03 with `terraform validate` (provider 2.0.14, Terraform 1.16.2): each of the 14 refuses
    more than one of its alternatives and also refuses none, so the provider reads the level as exactly one.
    `selects` is the one place either table states a choice, so a rule that read "a choice stated as fields"
    would need to say which fields form it, which is a second place that states it. Each mapping is the
    identity, because the export spells the provider key at a filter choice level, so
    `FILTER_XML_NAME_EXCEPTIONS` gained no row and no shape word changed.
    """
    measured = sorted(CHOICE_ROWS)
    assert sorted(p for p, row in resource_mapping.FILTER_SHAPE.items() if row['selects']) == measured
    for path, alternatives in sorted(CHOICE_ROWS.items()):
        row = _row(path)
        assert row['selects'] == {key: key for key in alternatives}, (path, row['selects'])
        # Every alternative is a field the row states, so the choice is the whole value or part of it.
        assert sorted(row['selects']) == sorted(alternatives), (path, row['selects'])
        attributes = _schema_node(provider_schema, path)['nested_type'].get('attributes', {})
        for key in row['selects']:
            assert key in row['fields'] and attributes[key].get('optional'), (path, key)
    # The choice is the whole value for 13 rows, and part of it for the redist entry, which also states the
    # entry name and the description.
    whole = [p for p, row in resource_mapping.FILTER_SHAPE.items()
            if row['selects'] and set(row['selects']) == set(row['fields'])]
    assert len(whole) == 13, whole
    redist = 'network/routing-profile/filters/route-maps/redistribution/redist-entry'
    assert set(_row(redist)['selects']) < set(_row(redist)['fields']), _row(redist)['fields']
    assert sorted(set(_row(redist)['fields']) - set(_row(redist)['selects'])) == ['description', 'name'], (
        _row(redist)['fields'])
    # No filter row is a `one_of` row, because the schema declares each alternative as an optional attribute of
    # a `single` level, so `one_of` keeps its meaning and `SHAPE_READS_AS` is unchanged.
    assert not [p for p, row in resource_mapping.FILTER_SHAPE.items() if row['shape'] == 'one_of']
    assert sanity_checks.SHAPE_READS_AS.get('one_of') == 'object', sanity_checks.SHAPE_READS_AS


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
    """The print path: each choice level the run reaches prints the one key `selects` names.

    The parse reads the fields the entry states, so the run can only print the one alternative the input
    states. The fixture answers each choice level it covers with one element, and the gate reads the blocks the
    run wrote with no finding, which `test_the_gate_reads_the_run_and_reports_nothing` pins for the whole run.
    """
    files = _run(FIXTURE, tmp_path)
    blocks = {block.rtype: block for block in sanity_checks.blocks(
        {'filters.tf': files['filters.tf']}, ('resource',))}
    source = xml_input.parse_xml(FIXTURES_DIR / FIXTURE)
    table = resource_mapping.FILTER_TABLE
    covered = []
    for path in sorted(CHOICE_ROWS):
        container = _container_of(path)
        node = source.root.findall(f'.//{container}/entry')[0]
        for part in path[len(container):].split('/'):
            if not part:
                continue
            children = node.findall(table.xml_name(part, container))
            if not children:
                break
            node = children[0]
        else:
            covered.append(path)
            alternatives = set(table.row(path)['selects'].values())
            stated = [child.tag for child in node if child.tag in alternatives]
            assert len(stated) == 1, (path, stated)
            printed = _printed_level(blocks[resource_mapping.FILTER_TYPES[container]], path)
            assert [key for key in printed if key in alternatives] == stated, (path, printed, stated)
    # The fixture covers 5 of the 14, so the other 9 are pinned through the table and the gate.
    assert covered == [
        'network/routing-profile/filters/access-list/type',
        'network/routing-profile/filters/community-list/type',
        'network/routing-profile/filters/prefix-list/type',
        'network/routing-profile/filters/route-maps/redistribution/redist-entry',
        'network/routing-profile/filters/route-maps/redistribution/redist-entry/bgp'], covered


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


def test_the_gate_reads_the_choice_at_the_level_the_walk_enters():
    """Rule 2 for the filter table: the choice a row states as `selects` is read at the level it states (F7.13).

    For a filter block the block's own level is the entry row the walk enters, so `check_filter_blocks` reads
    the choice there before the field rule, as `_shape_level_findings` does at every level below. One helper
    (`_shape_choice_findings`) serves both tables, so the finding wording is the one F7.12 states, read through
    the table object. Every one of the 14 measured rows is read for the number the provider refuses: more than
    one alternative, and none. A level that states one alternative is not a finding.
    """
    for path, alternatives in sorted(CHOICE_ROWS.items()):
        findings = _findings(path, _choice_block_body(path, alternatives))
        assert [f.detail for f in findings] == [
            _detail(path, f'states {len(alternatives)} keys, which is not the one key FILTER_SHAPE selects')], (
            path, findings)
        assert [f.check for f in findings] == ['filter_blocks'], (path, findings)
        findings = _findings(path, _choice_block_body(path, ()))
        assert [f.detail for f in findings] == [
            _detail(path, 'states 0 keys, which is not the one key FILTER_SHAPE selects')], (path, findings)
        for key in alternatives:
            assert _findings(path, _choice_block_body(path, (key,))) == [], (path, key)
    # The choice is part of the value for the redist entry row, so the choice rule reads only the alternatives
    # and the field rule reads `name` and `description`: the same key is not read twice.
    redist = 'network/routing-profile/filters/route-maps/redistribution/redist-entry'
    entry = '  name = "Redist-Filter"\n  description = "the lab redist"\n'
    assert _findings(redist, entry + _choice_block_body(redist, ('bgp',))) == []
    findings = _findings(redist, entry + _choice_block_body(redist, ('bgp', 'rip')))
    assert [f.detail for f in findings] == [
        _detail(redist, 'states 2 keys, which is not the one key FILTER_SHAPE selects')], findings
    # A choice level that states no alternative is the same finding, so the field rule does not read the level
    # twice: the choice finding is the one finding the block trips.
    findings = _findings(redist, entry + '  made_up = {}\n')
    assert [f.detail for f in findings] == [
        _detail(redist, 'states 0 keys, which is not the one key FILTER_SHAPE selects')], findings
    # With one alternative stated, the field rule still reads the fields the row declares.
    findings = _findings(redist, entry + _choice_block_body(redist, ('bgp',)) + '  made_up = {}\n')
    assert [f.detail for f in findings] == [
        _detail(redist, 'made_up is not a field FILTER_SHAPE declares')], findings


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
