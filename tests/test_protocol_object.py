"""F7.1: the `protocol` object as output on `panos_virtual_router`.

`resource_mapping.PROTOCOL_SHAPE` is the one table that states the shape of the protocol object. The
emitter (`TerraformGenerator.generate_virtual_routers`), the gate rule
(`sanity_checks.check_protocol_object`) and these tests read the same table, and
`sanity_checks.value_shape` stays that reader's own inverse, so no second table names a shape.

Pins:

- the table against the live provider schema: one row per level the converter prints, the field names the
  provider declares, the shape word for each field, the `selects` keys, and the `sensitive` flags;
  F7.3 adds the four `ospfv3` levels outside `area` and the one spelling exception table, and F7.9 adds the
  four `ospf` levels outside `area`;
- the print shape: `protocol = { ... }` is one field of the block, and `protocol { ... }` is the shape the
  provider refuses, so the rule reports it (`tests/test_terraform_validate.py` runs the same check on a
  real run);
- the one-of mapping, the peer membership, the interface inside an area, and the value the mapping cannot
  state;
- the `rip` levels as the rows that state them, the choice an entry states inside itself, and the block a
  real run writes for them (F7.5);
- the `policy` levels as the rows that state them, the `member_list` word for a field whose members are values,
  and the block a real run writes for the four entry levels (F7.6);
- a sensitive field as the variable reference, and `VALUE_VARIABLES` as the one shape owner for a printed
  value;
- one negative test per gate finding, the gate reporting no finding on a run, and two runs writing the
  same bytes.
"""

import ast
import inspect
import textwrap
from pathlib import Path

import container_coverage
import entry_coverage
import import_blocks
import naming
import resource_mapping
import sanity_checks
import site_data
import unit_manifest
from conftest import FIXTURES_DIR, GOLDEN_DIR, file_text, run_script, tf_files

CONVERTER = 'panorama_to_terraform.py'


def _run(fixture: str, out_dir) -> dict:
    """Run the converter on one fixture and return the output files as text."""
    result = run_script(CONVERTER, str(FIXTURES_DIR / fixture), '--output-dir', str(out_dir))
    assert result.returncode == 0, result.stdout + result.stderr
    # F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): the `.tf` set is read as the gate reads it, so a `.tf`
    # entry holds the parts the run wrote for every unit, in path order. A report is a codebase root-set
    # file, so it stays at the root and is keyed by its name.
    tf = tf_files(out_dir)
    files = {Path(key).name: file_text(tf, Path(key).name) for key in tf}
    for path in sorted(Path(out_dir).iterdir()):
        if path.is_file() and path.name not in files:
            files[path.name] = path.read_text(encoding='utf-8')
    return files


def _block(protocol: str) -> dict:
    """One `panos_virtual_router` block written by hand, in the shape the emitter writes it.

    The rule reads the file text, so the tests that pin a finding state the block the gate reads: the
    field at the block's own level and the closing brace at column 0.
    """
    return {'vr.tf': 'resource "panos_virtual_router" "default_00000000" {\n'
                     '  name = "default"\n' + protocol + '}\n'}


def _findings(protocol: str) -> list:
    return sanity_checks.check_protocol_object(_block(protocol))


def _schema_node(provider_schema: dict, path: str) -> dict:
    """The provider schema attribute the table path names, walked from `protocol`."""
    node = provider_schema[resource_mapping.PROTOCOL_TYPE]['block']['attributes'][resource_mapping.PROTOCOL_FIELD]
    for part in path.split('/')[1:]:
        node = node['nested_type']['attributes'][part]
    return node


def _schema_level(node: dict) -> str:
    """What the schema states for one attribute: a leaf type, or a nesting mode.

    The schema has no word for a choice, so `one_of` is read as `single`: a choice level is a single level
    whose attributes are the alternatives, and the test checks the mapping's keys against the schema instead
    of guessing a word for it.
    """
    nested = node.get('nested_type')
    if nested is None:
        declared = node.get('type')
        return 'list' if isinstance(declared, list) else declared
    return nested['nesting_mode']


# A `SHAPE_WORDS` word as the schema states it, read through the one definition `resource_mapping` owns.
WORD_TO_SCHEMA = resource_mapping.SHAPE_TO_SCHEMA


# --- 1. the table against the live provider schema ---------------------------

def test_the_shape_table_is_the_measured_provider_shape(provider_schema):
    """Every row, field, shape word, `selects` key, and `sensitive` flag is a fact the provider declares.

    The table states the levels this converter prints, so it is a subset of the schema: `protocol` also
    declares the two redist profile lists, which the converter does not print and the gate does not check. A
    row states only the fields the parse method that reaches the level reads. F7.4 added the four area
    sub-levels, which `_protocol_areas` reads, F7.5 added the `rip` levels, which `parse_rip` reads, F7.6
    added the 78 `policy` levels, which `parse_bgp` reads, the `member_list` word for the fields the schema
    declares as `['list', 'string']`, F7.7 added the `ospfv3` auth profile levels, which `parse_ospfv3`
    reads, and F7.9 added the four `ospf` levels outside `area`, which `parse_ospf` reads: every row in the
    table is now a level a parse method reads.
    """
    for path, row in sorted(resource_mapping.PROTOCOL_SHAPE.items()):
        node = _schema_node(provider_schema, path)
        word = WORD_TO_SCHEMA.get(row['shape'], row['shape'])
        assert _schema_level(node) == word, (path, row['shape'], _schema_level(node))
        attributes = node['nested_type'].get('attributes', {})
        assert set(row['fields']) <= set(attributes), (path, row['fields'])
        for field, shape_word in row['fields'].items():
            assert _schema_level(attributes[field]) == WORD_TO_SCHEMA.get(shape_word, shape_word), (path, field)
        # A field the table states as `block` is a level the export states by presence: the schema gives it
        # no attribute, so the provider reads the empty object, which is what the reader reads back.
        for field, shape_word in row['fields'].items():
            if shape_word == 'block':
                assert _schema_level(attributes[field]) == 'single', (path, field)
                assert not attributes[field]['nested_type'].get('attributes'), (path, field)
        # F7.1 rule: the fields the row declares as sensitive are the ones the provider marks sensitive.
        sensitive = {field for field, attribute in attributes.items() if attribute.get('sensitive')}
        assert row['sensitive'] == frozenset(sensitive & set(row['fields'])), (path, row['sensitive'])
        # A `one_of` row's alternatives are the schema's attributes. Each one is the field the row states, or the
        # row the table states for it when the alternative names a level (F7.6).
        if row['selects']:
            assert set(row['selects'].values()) == set(attributes), (path, row['selects'])
            for key in row['selects'].values():
                assert key in row['fields'] or f'{path}/{key}' in resource_mapping.PROTOCOL_SHAPE, (path, key)


def test_the_sensitive_rows_are_the_reference_only_names():
    """`VALUE_VARIABLES` holds one row per field the provider marks `sensitive` (F7.1 rule).

    A sensitive value cannot reach a generated file as a literal, so the table says the block prints the
    reference, and the run declares the variable with no value for it.
    """
    declared = {field for row in resource_mapping.PROTOCOL_SHAPE.values() for field in row['sensitive']}
    reference_only = {field for field, row in resource_mapping.VALUE_VARIABLES.items()
                      if row == resource_mapping.REFERENCE_ONLY}
    assert declared == reference_only, (declared, reference_only)
    assert declared == {'secret', 'key', 'password'}, declared


def test_the_table_is_the_only_shape_owner(converter_module):
    """No parse method, emitter, or gate branch names a protocol field or a shape of its own (F7.1, F7.5).

    The table states the names and the shapes, and the reader and the rule read the table, so a field name
    written as a string constant in a parse method, the emitter, or the rule is a second owner. The parse
    methods state a level as a table path, so the key they write is the field the path names. `_parse_router`
    builds the `protocol` dict from the fields the `protocol` row states, so the levels are the table's names
    there too. `name` is the field the rule reads for the entry name, and `protocol` is the table's own
    `PROTOCOL_FIELD`: those two are the names the rule has to state.
    """
    # Both shape tables are shape owners, so a field name written as a string constant in a reader, an emitter
    # or a gate branch is a second owner for either table (F7.8).
    fields = {field for table in (resource_mapping.PROTOCOL_TABLE, resource_mapping.FILTER_TABLE)
              for row in table.rows.values() for field in row['fields']}
    # The static-route emitter is not a protocol owner: `metric` is the route's own field there, and the row
    # `COVERAGE_MATRIX` states for it names that shape. `name` is the field the rule reads for the entry
    # name, and `protocol` is the table's own `PROTOCOL_FIELD`. `interfaces` is the router's own field there,
    # the flat list of interface names the matrix row for `panos_virtual_router` declares, which is a
    # different shape from the `protocol/rip` field the table states (F7.5).
    static_route = [row for row in resource_mapping.COVERAGE_MATRIX
                    if row['resource'] == 'panos_virtual_router_static_route_ipv4'][0]
    # `entry` is the element the reader walks for an entry list, and it is also a schema attribute name for a
    # nested entry list (F7.8), so the reader has to state it.
    allowed = (set(resource_mapping.SHAPE_WORDS) | {'name', 'entry', resource_mapping.PROTOCOL_FIELD}
               | set(static_route['properties']) | {'interfaces'})
    owners = [getattr(sanity_checks, name, None) for name in
              ('check_protocol_object', 'check_filter_blocks', '_shape_level_findings',
               '_shape_field_findings', 'value_shape')]
    generator = converter_module.TerraformGenerator
    parser = converter_module.PanoramaParser
    owners += [getattr(generator, name) for name in ('generate_virtual_routers', '_protocol_fields', 'printed_value')]
    owners += [getattr(parser, name) for name in
               ('_parse_router', 'parse_bgp', 'parse_ospf', 'parse_ospfv3', 'parse_rip', '_protocol_areas',
                '_protocol_level', '_protocol_field', '_protocol_choice', '_protocol_interface',
                '_protocol_field_name', '_protocol_xml_name', '_protocol_entries', '_protocol_body',
                '_protocol_branch', '_protocol_presence_choice', '_protocol_presence_fields')]
    offenders = {}
    for owner in owners:
        for node in ast.walk(ast.parse(textwrap.dedent(inspect.getsource(owner)))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                    and node.value in fields and node.value not in allowed:
                offenders.setdefault(owner.__name__, set()).add(node.value)
    assert offenders == {}, offenders
    # The two spelling rules are one function each: the field name to element name rule, and the field name a
    # table path names, which is the key the captured dict holds.
    assert parser._protocol_xml_name('address_family_identifier') == 'address-family-identifier'
    assert parser._protocol_xml_name('spf_calculation_delay') == 'spf-calculation-delay'
    assert parser._protocol_field_name('protocol/ospfv3/export_rules') == 'export_rules'
    # F7.9: the same rule for the `ospf` level, which the row now states as an entry level.
    assert parser._protocol_field_name('protocol/ospf/export_rules') == 'export_rules'
    assert parser._protocol_field_name('protocol/ospf/area/interface/link_type') == 'link_type'
    # F7.3: the provider spells one field name from an element name the `-` rule cannot produce, because it
    # splits the initialism, so `XML_NAME_EXCEPTIONS` is the one place that states it.
    assert resource_mapping.XML_NAME_EXCEPTIONS == {'strict_l_s_a_checking': 'strict-lsa-checking'}
    assert parser._protocol_xml_name('strict_l_s_a_checking') == 'strict-lsa-checking'


def test_the_ospf_scalar_levels_are_rows_the_parse_reads():
    """The `protocol/ospf` levels outside `area` are table rows, and the level that holds entries is the one
    the property scan measures (F7.9).

    `test_the_shape_table_is_the_measured_provider_shape` pins every row against the schema, so this test pins
    the shape decision and the measurement scope: the three `bool` fields are leaf values, not blocks, a
    single-object level holds no entry so the scan measures nothing for it and the container table names no row
    for it, and an export rule is an entry. Field order is the print order, so the row's order is pinned as the
    dict's order: the two fields the row already stated keep their order, the `bool` fields follow in the order
    the schema names them, then the single-object levels and the entry levels in the order the `ospfv3` row
    states them. `disable_transit_traffic` is the field the provider declares for `ospfv3` and not for `ospf`,
    so this row states no field for it.
    """
    level = resource_mapping.protocol_row('protocol/ospf')
    assert list(level['fields']) == [
        'enable', 'router_id', 'allow_redist_default_route', 'reject_default_route', 'rfc1583',
        'timers', 'global_bfd', 'graceful_restart', 'area', 'export_rules', 'auth_profile'], level['fields']
    assert level['fields'] == {
        'enable': 'bool', 'router_id': 'string', 'allow_redist_default_route': 'bool',
        'reject_default_route': 'bool', 'rfc1583': 'bool', 'timers': 'object', 'global_bfd': 'object',
        'graceful_restart': 'object', 'area': 'string_list', 'export_rules': 'string_list',
        'auth_profile': 'string_list'}, level['fields']
    for path, shape in (('protocol/ospf/timers', 'object'),
                        ('protocol/ospf/global_bfd', 'object'),
                        ('protocol/ospf/graceful_restart', 'object'),
                        ('protocol/ospf/export_rules', 'string_list')):
        assert resource_mapping.protocol_row(path)['shape'] == shape, path
        # None of these levels carries a field the provider marks sensitive, so no `VALUE_VARIABLES` row.
        assert resource_mapping.protocol_row(path)['sensitive'] == frozenset(), path
    rows = [row.path for row in container_coverage.CONTAINER_TABLE
            if row.path.startswith('protocol/ospf/')]
    assert sorted(rows) == ['protocol/ospf/area', 'protocol/ospf/area/interface',
                             'protocol/ospf/area/interface/neighbor', 'protocol/ospf/area/virtual-link',
                             'protocol/ospf/auth-profile', 'protocol/ospf/export-rules',
                             'protocol/ospf/interface', 'protocol/ospf/range'], rows


def test_the_ospfv3_scalar_levels_are_rows_the_parse_reads():
    """The four `ospfv3` levels outside `area` are table rows, and the level that holds entries is the one
    the property scan measures (F7.3).

    `test_the_shape_table_is_the_measured_provider_shape` pins every row against the schema, so this test pins
    the shape decision and the measurement scope: a single-object level holds no entry, so the scan measures
    nothing for it and the container table names no row for it, while an export rule is an entry.
    F7.4 names the two entry levels the area rule reads: a neighbor entry, and a virtual link.
    """
    level = resource_mapping.protocol_row('protocol/ospfv3')
    assert [field for field in level['fields'] if field not in ('enable', 'router_id', 'area')] == [
        'timers', 'global_bfd', 'graceful_restart', 'export_rules', 'auth_profile'], level['fields']
    for path, shape in (('protocol/ospfv3/timers', 'object'),
                        ('protocol/ospfv3/global_bfd', 'object'),
                        ('protocol/ospfv3/graceful_restart', 'object'),
                        ('protocol/ospfv3/export_rules', 'string_list')):
        assert resource_mapping.protocol_row(path)['shape'] == shape, path
        # None of these levels carries a field the provider marks sensitive, so no `VALUE_VARIABLES` row.
        assert resource_mapping.protocol_row(path)['sensitive'] == frozenset(), path
    rows = [row.path for row in container_coverage.CONTAINER_TABLE
            if row.path.startswith('protocol/ospfv3/')]
    assert sorted(rows) == ['protocol/ospfv3/area', 'protocol/ospfv3/area/interface',
                             'protocol/ospfv3/area/interface/neighbor',
                             'protocol/ospfv3/area/virtual-link', 'protocol/ospfv3/auth-profile',
                             'protocol/ospfv3/export-rules', 'protocol/ospfv3/interface',
                             'protocol/ospfv3/range'], rows


def test_the_rip_levels_are_rows_the_parse_reads():
    """The `protocol/rip` levels are table rows, and the two that hold entries are the ones the scan
    measures (F7.5).

    `test_the_shape_table_is_the_measured_provider_shape` pins every row against the schema, so this test pins
    the shape decision and the measurement scope: `rip` declares no `router_id`, no `area` and no `neighbor`,
    so the level states no field for them, and `mode` is a string, so the row states no `selects` for it. A
    single-object level holds no entry, so the scan measures nothing for it and the container table names no
    row for it, while an interface entry and an export rule entry are entries. No row names
    `protocol/rip/interfaces/bfd`, because the parse reaches that level through the field the interfaces row
    states, and no row names `protocol/rip/auth-profile/md5` for the same reason: an entry inside an entry is
    not in the scan scope.
    """
    level = resource_mapping.protocol_row('protocol/rip')
    assert level['fields'] == {
        'enable': 'bool', 'allow_redist_default_route': 'bool', 'reject_default_route': 'bool',
        'timers': 'object', 'global_bfd': 'object', 'interfaces': 'string_list',
        'export_rules': 'string_list', 'auth_profile': 'string_list'}, level['fields']
    for path, shape in (('protocol/rip/timers', 'object'),
                        ('protocol/rip/global_bfd', 'object'),
                        ('protocol/rip/interfaces', 'string_list'),
                        ('protocol/rip/interfaces/bfd', 'object'),
                        ('protocol/rip/interfaces/default_route', 'one_of'),
                        ('protocol/rip/interfaces/default_route/advertise', 'object'),
                        ('protocol/rip/interfaces/default_route/disable', 'block'),
                        ('protocol/rip/export_rules', 'string_list')):
        row = resource_mapping.protocol_row(path)
        assert row['shape'] == shape, path
        # None of the levels `parse_rip` reads carries a field the provider marks sensitive, so no
        # `VALUE_VARIABLES` row for them.
        assert row['sensitive'] == frozenset(), path
    # F7.7: `parse_rip` reads the profile level, so the run prints the reference for `password`, and `key` is
    # the field the reader reads inside the `md5` entry.
    assert resource_mapping.protocol_row('protocol/rip/auth_profile')['sensitive'] == frozenset({'password'})
    assert resource_mapping.protocol_row('protocol/rip/auth_profile/md5')['sensitive'] == frozenset({'key'})
    # `selects` is the one place that maps the value the export states to the key the print states, the same
    # mapping the two OSPF levels use for a default route.
    assert resource_mapping.protocol_row('protocol/rip/interfaces/default_route')['selects'] == {
        'advertise': 'advertise', 'no': 'disable'}
    rows = [row.path for row in container_coverage.CONTAINER_TABLE if row.path.startswith('protocol/rip/')]
    assert sorted(rows) == ['protocol/rip/auth-profile', 'protocol/rip/export-rules',
                            'protocol/rip/interfaces'], rows


def test_the_auth_profile_rows_are_the_levels_the_four_methods_read():
    """F7.7: the four `auth_profile` levels are table rows the four parse methods read, and the entry inside a
    profile entry is not one of the rows the property scan reads.

    `test_the_shape_table_is_the_measured_provider_shape` pins every row against the schema, so this test pins
    the shape decision: a `list` level is a `string_list` row, a `single` level whose attributes are the
    alternatives is a `one_of` row with the identity mapping, a `single` level with attributes is an `object`
    row, and the alternative that declares no attribute is the `block` field of the row that holds it. The four
    container rows are the four levels, because the scan measures an entry only through an emitted row that
    names the provider type. No row names the `md5` level, because the parse reaches it through the field the
    profile row states, and a section path that holds an extra `entry` segment cannot match a row path.
    The provider accepts `ah` or `esp` for one entry, and the table has no word for that, so the fixture states
    the two choice levels in two entries.
    """
    for level in ('bgp', 'ospf', 'rip', 'ospfv3'):
        row = resource_mapping.protocol_row(f'protocol/{level}/auth_profile')
        assert row['shape'] == 'string_list', level
        # The entry name is the field the row reads for the entry, so it is never a property.
        assert 'name' in row['fields'], level
        for field in row['sensitive']:
            assert resource_mapping.VALUE_VARIABLES[field] == resource_mapping.REFERENCE_ONLY, (level, field)
    assert resource_mapping.protocol_row('protocol/bgp/auth_profile')['fields'] == {
        'name': 'string', 'secret': 'string'}, resource_mapping.protocol_row('protocol/bgp/auth_profile')['fields']
    assert resource_mapping.protocol_row('protocol/bgp/auth_profile')['sensitive'] == frozenset({'secret'})
    for level in ('ospf', 'rip'):
        row = resource_mapping.protocol_row(f'protocol/{level}/auth_profile')
        assert row['fields'] == {'name': 'string', 'password': 'string', 'md5': 'string_list'}, level
        assert row['sensitive'] == frozenset({'password'}), level
        assert resource_mapping.protocol_row(f'protocol/{level}/auth_profile/md5')['fields'] == {
            'name': 'string', 'key': 'string', 'preferred': 'bool'}, level
    # The `ospfv3` profile is the level the run reads through the table: `ah` and `esp/authentication` are
    # choice levels, and `none` is the alternative that declares no attribute, so it is the `block` field.
    assert resource_mapping.protocol_row('protocol/ospfv3/auth_profile')['fields'] == {
        'name': 'string', 'spi': 'string', 'ah': 'one_of', 'esp': 'object'}
    assert resource_mapping.protocol_row('protocol/ospfv3/auth_profile/ah')['selects'] == {
        'md5': 'md5', 'sha1': 'sha1', 'sha256': 'sha256', 'sha384': 'sha384', 'sha512': 'sha512'}
    authentication = resource_mapping.protocol_row('protocol/ospfv3/auth_profile/esp/authentication')
    assert authentication['fields'] == {'none': 'block'}, authentication['fields']
    assert authentication['selects'] == {
        'md5': 'md5', 'none': 'none', 'sha1': 'sha1', 'sha256': 'sha256', 'sha384': 'sha384',
        'sha512': 'sha512'}, authentication['selects']
    for path in (f'protocol/ospfv3/auth_profile/ah/{key}' for key in authentication['selects'].values()
                 if key != 'none'):
        row = resource_mapping.protocol_row(path)
        assert row['shape'] == 'object', path
        assert row['sensitive'] == frozenset({'key'}), path
    assert resource_mapping.protocol_row('protocol/ospfv3/auth_profile/esp/encryption')['fields'] == {
        'algorithm': 'string', 'key': 'string'}
    assert resource_mapping.protocol_row('protocol/ospfv3/auth_profile/esp/encryption')['sensitive'] == \
        frozenset({'key'})
    # The four rows the scan reads are the four levels, in the input's spelling.
    rows = sorted(row.path for row in container_coverage.CONTAINER_TABLE
                  if row.path.endswith('/auth-profile'))
    assert rows == ['protocol/bgp/auth-profile', 'protocol/ospf/auth-profile',
                    'protocol/ospfv3/auth-profile', 'protocol/rip/auth-profile'], rows
    assert not [row for row in container_coverage.CONTAINER_TABLE if '/md5' in row.path], \
        [row.path for row in container_coverage.CONTAINER_TABLE]


def test_value_shape_is_the_reader_inverse_for_every_shape_word():
    """`value_shape` reads back each shape word the table states, including `number` and `block` (F6.7, F7.1).

    A specialization reads back as the family word the reader reads, which `sanity_checks.SHAPE_READS_AS` states
    in one place: `one_of` and `block` are object values, and a `member_list` is a `[` value whose members are
    values and not entries.
    """
    samples = {'string': '"host"', 'bool': 'true', 'number': '10', 'object': '{}',
               'string_list': '["a"]', 'member_list': '["a"]', 'one_of': '{ebgp = {}}', 'block': '{}'}
    for word, text in samples.items():
        expected = sanity_checks.SHAPE_READS_AS.get(word, word)
        assert sanity_checks.value_shape(text) == expected, (word, text)
    assert set(samples) == set(resource_mapping.SHAPE_WORDS), resource_mapping.SHAPE_WORDS


# --- 2. the one-of mapping ---------------------------------------------------

def test_the_one_of_mapping_is_the_decision_the_report_prints():
    """The mapping states the value the export holds and the key the provider reads.

    The area type and the interface link type are the identity, because the export states the provider key;
    the BGP peer group type is the one level where the two spellings differ.
    """
    assert resource_mapping.protocol_row('protocol/bgp/peer_group/type')['selects'] == {
        'external': 'ebgp', 'internal': 'ibgp',
        'external-confederation': 'ebgp_confed', 'internal-confederation': 'ibgp_confed'}
    assert resource_mapping.protocol_row('protocol/ospf/area/type')['selects'] == {
        'normal': 'normal', 'nssa': 'nssa', 'stub': 'stub'}
    assert resource_mapping.protocol_row('protocol/ospf/area/interface/link_type')['selects'] == {
        'point-to-point': 'p2p', 'broadcast': 'broadcast', 'p2mp': 'p2mp'}
    # F7.2: the `ospfv3` choice levels state the same values, because the export spells the provider key there
    # too. The two rows are the same shape read by two parse methods, so one value maps to one key in both.
    assert resource_mapping.protocol_row('protocol/ospfv3/area/type')['selects'] == {
        'normal': 'normal', 'nssa': 'nssa', 'stub': 'stub'}
    assert resource_mapping.protocol_row('protocol/ospfv3/area/interface/link_type')['selects'] == {
        'point-to-point': 'p2p', 'broadcast': 'broadcast', 'p2mp': 'p2mp'}
    # F7.6: the policy choice levels are the levels `terraform validate` refuses to hold 2 attributes (provider
    # 2.0.14, Terraform 1.16.2, measured 2026-11-02), so each states `one_of` with the identity mapping, where
    # the key is the spelling the export states and the value is the provider name. `action` is the only one
    # whose alternatives name levels, so its mapping is the identity over the two rows for them.
    for path in ('protocol/bgp/policy/aggregation/address/aggregate_route_attributes/as_path',
                 'protocol/bgp/policy/aggregation/address/aggregate_route_attributes/community',
                 'protocol/bgp/policy/aggregation/address/aggregate_route_attributes/extended_community'):
        row = resource_mapping.protocol_row(path)
        assert row['shape'] == 'one_of', path
        assert row['selects'] == {key.replace('_', '-'): key for key in row['fields']}, path
    for side in ('export', 'import'):
        action = f'protocol/bgp/policy/{side}/rules/action'
        assert resource_mapping.protocol_row(action)['selects'] == {'allow': 'allow', 'deny': 'deny'}, side
        assert resource_mapping.protocol_row(f'{action}/deny')['shape'] == 'block', side
        for level in ('as_path', 'community', 'extended_community'):
            row = resource_mapping.protocol_row(f'{action}/allow/update/{level}')
            assert row['shape'] == 'one_of', (side, level)
            assert row['selects'] == {key.replace('_', '-'): key for key in row['fields']}, (side, level)
    # A nexthop belongs to the chosen sub-shape, and two of them exist only under `ebgp`.
    assert resource_mapping.protocol_row('protocol/bgp/peer_group/type/ebgp')['fields'] == {
        'export_nexthop': 'string', 'import_nexthop': 'string', 'remove_private_as': 'bool'}
    for key in ('ebgp_confed', 'ibgp', 'ibgp_confed'):
        assert 'import_nexthop' not in resource_mapping.protocol_row(
            f'protocol/bgp/peer_group/type/{key}')['fields'], key


def test_a_one_of_level_prints_one_key():
    """The rule accepts the one key the mapping states and refuses any other shape of that level."""
    good = ('  protocol = {\n    bgp = {\n      peer_group = [\n        {\n'
            '          name = "PG"\n          type = {\n            ebgp = {\n'
            '              export_nexthop = "self"\n            }\n          }\n        }\n      ]\n    }\n  }\n')
    assert _findings(good) == []
    findings = _findings(good.replace('            ebgp = {\n              export_nexthop = "self"\n            }',
                                      '            ebgp = {}\n            ibgp = {}'))
    assert len(findings) == 1 and 'states 2 keys' in findings[0].detail, findings
    findings = _findings(good.replace('ebgp = {\n              export_nexthop = "self"\n            }',
                                      'made_up = {}'))
    assert len(findings) == 1 and 'is not a key PROTOCOL_SHAPE selects' in findings[0].detail, findings
    # F7.6: a choice level whose alternatives are values is read by the same rule. The level states one key, and
    # the field rule reads the value the row states for that key, so the walk never enters a value.
    value_choice = ('  protocol = {\n    bgp = {\n      policy = {\n        aggregation = {\n          address = [\n'
                    '            {\n              name = "a1"\n              aggregate_route_attributes = {\n'
                    '                community = {\n                  append = [ "1:10" ]\n                }\n'
                    '              }\n            }\n          ]\n        }\n      }\n    }\n  }\n')
    assert _findings(value_choice) == [], value_choice
    base = ('protocol panos_virtual_router.default_00000000 '
            'protocol/bgp/policy/aggregation/address/aggregate_route_attributes/community ')
    one_key = '                  append = [ "1:10" ]\n'
    findings = _findings(value_choice.replace(
        one_key, one_key + '                  remove_all = {}\n'))
    assert [f.detail for f in findings] == [base + 'states 2 keys, which a one_of level cannot'], findings
    findings = _findings(value_choice.replace('append = [ "1:10" ]', 'made_up = { x = "1" }'))
    assert [f.detail for f in findings] == [base + 'key made_up is not a key PROTOCOL_SHAPE selects'], findings
    # The run prints one key, so a run reports nothing.
    files = {str(p.relative_to(GOLDEN_DIR / 'kitchen_sink')): p.read_text(encoding='utf-8')
              for p in sorted((GOLDEN_DIR / 'kitchen_sink').rglob('*.tf'))}
    assert sanity_checks.check_protocol_object(files) == [], sanity_checks.check_protocol_object(files)


# --- 3. the print shape ------------------------------------------------------

def test_protocol_prints_as_an_object_field_not_a_block(tmp_path):
    """The generated file states `protocol = { ... }`, which the provider reads, and the rule reports the
    block shape it does not.
    """
    files = _run('kitchen_sink.xml', tmp_path)
    block = files['virtual_routers.tf']
    assert '  protocol = {' in block, block
    assert '  protocol {' not in block, block
    findings = _findings('  protocol {\n    bgp {\n      enable = true\n    }\n  }\n')
    assert len(findings) == 1, findings
    assert findings[0].detail == (
        'protocol panos_virtual_router.default_00000000 is a block, not the field PROTOCOL_SHAPE states')
    # A `range` element states the choice the provider requires, and `block` is the shape the export states
    # by presence, so the reader reads the empty object as an object value.
    good = ('  protocol = {\n    ospf = {\n      area = [\n        {\n          name = "0.0.0.0"\n'
            '          range = [\n            {\n              name = "10.0.0.0/8"\n'
            '              advertise = {}\n            }\n          ]\n        }\n      ]\n    }\n  }\n')
    assert _findings(good) == [], _findings(good)
    findings = _findings(good.replace('advertise = {}', 'advertise = true'))
    assert len(findings) == 1 and 'advertise is not a block value' in findings[0].detail, findings
    # `import_blocks.fields_at` reads a level, so a `protocol` written as a block is not a field there.
    assert 'protocol' not in import_blocks.fields_at(
        '\n  name = "default"\n  protocol {\n    bgp {\n      enable = true\n    }\n  }')


# --- 4. the peer membership and the interface placement ----------------------

def test_a_peer_prints_inside_its_peer_group(tmp_path):
    """The membership is the parent entry, so the peer prints inside the peer group element (F7.1).

    `tests/fixtures/bgp.xml` holds the peer at the `bgp` level with the name reference, which is the case
    the parse resolves to the peer group entry. A peer no group names has no provider field, so the report
    names it and the file prints no half of it.
    """
    files = _run('bgp.xml', tmp_path)
    block = files['virtual_routers.tf']
    peer_section = block[block.index('peer_group = ['):block.index('redist_rules')]
    assert 'name = "PG-Branch"' in peer_section and 'name = "10.55.0.2"' in peer_section, peer_section
    # `peer_group` is no longer a field the block prints: the entry it names is the parent.
    assert 'peer_group = "PG-Branch"' not in block, block
    # The peer the file cannot hold is named by the report, once.
    report = files['MANUAL_SETUP_REPORT.txt']
    assert 'router default: peer 10.55.0.9 (panos_virtual_router - no peer group names it)' in report, report
    assert '10.55.0.2' not in report, report


def test_an_ospf_interface_inside_an_area_prints_inside_the_area(tmp_path):
    """The provider field for an interface is inside `area`, so the file nests it there (F7.1)."""
    files = _run('ospf.xml', tmp_path)
    block = files['virtual_routers.tf']
    area_section = block[block.index('area = ['):block.index('\n        }\n      ]')]
    assert 'interface = [' in area_section and 'name = "ethernet1/2"' in area_section, area_section
    # The entries the file cannot express are named by the report and are not printed.
    report = files['MANUAL_SETUP_REPORT.txt']
    assert 'router default: interface ethernet1/3 (link_type multicast is not a value PROTOCOL_SHAPE states)' in report
    assert 'router default: range 10.60.0.0/16 (no advertise or suppress)' in report
    assert 'ethernet1/3' not in block and '10.60.0.0/16' not in block, block


def test_an_ospfv3_area_prints_the_shape_the_table_states(tmp_path):
    """The `ospfv3` subtree prints as the rows `PROTOCOL_SHAPE` states for it (F7.2, F7.4).

    Field order is the table order, a `one_of` level states the one key its mapping selects, and a `block`
    field prints `{}` because the export states it by presence. F7.4: the choice inside a body prints as the
    key the row selects, so the export spelling `no` prints as `disable`.
    """
    expected = ('  protocol = {\n    ospfv3 = {\n      enable = true\n      router_id = "10.0.0.1"\n'
                '      area = [\n        {\n          name = "0.0.0.0"\n          type = {\n'
                '            nssa = {\n              accept_summary = true\n              default_route = {\n'
                '                disable = {}\n              }\n              nssa_ext_range = [\n'
                '                {\n                  name = "10.20.0.0/16"\n                  advertise = {}\n'
                '                }\n              ]\n            }\n          }\n'
                '          range = [\n            {\n              name = "10.0.0.0/8"\n'
                '              suppress = {}\n            }\n          ]\n          interface = [\n'
                '            {\n              name = "ethernet1/2"\n              enable = true\n'
                '              passive = false\n              metric = 10\n              link_type = {\n'
                '                p2p = {}\n              }\n              neighbor = [\n'
                '                {\n                  name = "10.0.0.2"\n                }\n              ]\n'
                '            }\n          ]\n          virtual_link = [\n'
                '            {\n              name = "10.0.0.2"\n              instance_id = 1\n'
                '              neighbor_id = "10.0.0.3"\n            }\n          ]\n        }\n      ]\n'
                '    }\n  }\n')
    block = _run('ospfv3.xml', tmp_path)['virtual_routers.tf']
    assert expected in block, block
    # The gate reads the same table, so the block the run wrote reports no finding.
    findings = _findings(expected)
    assert findings == [], findings


def test_an_ospf_level_prints_the_shape_the_table_states(tmp_path):
    """A `protocol/ospf` level prints as the rows `PROTOCOL_SHAPE` states for it (F7.9).

    Field order is the table order, so the pin is the whole `protocol` field the run wrote: `enable`,
    `router_id`, the three `bool` fields in the order the row states them, the three single-object levels as
    one object each, then the two entry levels. `export_rules` is a `string_list`, so it prints one object per
    entry. The fixture states every field the four new rows declare, so the run prints every one of them, and
    the gate reads the same table, so the block the run wrote reports no finding.
    """
    expected = ('  protocol = {\n    ospf = {\n      enable = true\n      router_id = "10.0.0.1"\n'
                '      allow_redist_default_route = true\n      reject_default_route = false\n'
                '      rfc1583 = true\n      timers = {\n        lsa_interval = 120\n'
                '        spf_calculation_delay = 20\n      }\n      global_bfd = {\n'
                '        profile = "BFD-OSPF"\n      }\n      graceful_restart = {\n'
                '        enable = true\n        grace_period = 120\n        helper_enable = true\n'
                '        max_neighbor_restart_time = 200\n        strict_l_s_a_checking = true\n      }\n'
                '      area = [\n        {\n          name = "0.0.0.0"\n          type = {\n'
                '            stub = {\n              accept_summary = true\n              default_route = {\n'
                '                advertise = {\n                  metric = 10\n                }\n'
                '              }\n            }\n          }\n          range = [\n            {\n'
                '              name = "10.0.0.0/8"\n              advertise = {}\n            }\n          ]\n'
                '          interface = [\n            {\n              name = "ethernet1/2"\n'
                '              enable = true\n              passive = false\n              metric = 10\n'
                '              link_type = {\n                broadcast = {}\n              }\n'
                '              neighbor = [\n                {\n                  name = "10.0.0.2"\n'
                '                }\n              ]\n            }\n          ]\n          virtual_link = [\n'
                '            {\n              name = "10.0.0.2"\n              hello_interval = 10\n'
                '              neighbor_id = "10.0.0.3"\n              transit_area_id = "0.0.0.1"\n'
                '            }\n          ]\n        },\n        {\n          name = "0.0.1.0"\n'
                '          type = {\n            nssa = {\n              default_route = {\n'
                '                disable = {}\n              }\n              nssa_ext_range = [\n'
                '                {\n                  name = "10.20.0.0/16"\n                  suppress = {}\n'
                '                }\n              ]\n            }\n          }\n        }\n      ]\n'
                '      export_rules = [\n        {\n          name = "export-static"\n          metric = 10\n'
                '          new_path_type = "internal"\n          new_tag = "0"\n        }\n      ]\n'
                '    }\n  }\n')
    files = _run('ospf.xml', tmp_path)
    block = files['virtual_routers.tf']
    assert expected in block, block
    # The gate reads the same table, so the block the run wrote reports no finding.
    findings = sanity_checks.check_protocol_object(files)
    assert findings == [], findings


def test_an_ospfv3_scalar_level_prints_the_shape_the_table_states(tmp_path):
    """A `protocol/ospfv3` level outside `area` prints as its row states it (F7.3).

    Field order is the table order, a `single` level prints as one object, and a `string_list` level prints one
    object per element. `tests/fixtures/ospfv3.xml` states every field the four rows declare, so the pin is the
    whole block the run wrote for that router.
    """
    expected = ('  protocol = {\n    ospfv3 = {\n      enable = true\n      timers = {\n'
                '        lsa_interval = 120\n        spf_calculation_delay = 20\n      }\n'
                '      global_bfd = {\n        profile = "BFD-OSP"\n      }\n'
                '      graceful_restart = {\n        enable = true\n        grace_period = 120\n'
                '        helper_enable = true\n        max_neighbor_restart_time = 200\n'
                '        strict_l_s_a_checking = true\n      }\n      export_rules = [\n        {\n'
                '          name = "static-af"\n          metric = 10\n          new_path_type = "internal"\n'
                '          new_tag = "0"\n        }\n      ]\n    }\n  }\n')
    files = _run('ospfv3.xml', tmp_path)
    parts = files['virtual_routers.tf'].split('resource "panos_virtual_router" ')
    assert len(parts) == 3, parts
    assert expected in parts[2], parts[2]
    # The area router states none of these levels, so it prints no field for them.
    for field in ('timers', 'global_bfd', 'graceful_restart', 'export_rules'):
        assert field not in parts[1], parts[1]
    # The gate reads the same table, so the block the run wrote reports no finding.
    findings = sanity_checks.check_protocol_object(files)
    assert findings == [], findings


def test_an_rip_level_prints_the_shape_the_table_states(tmp_path):
    """A `protocol/rip` level prints as the rows `PROTOCOL_SHAPE` states for it (F7.5).

    Field order is the table order, a `single` level prints as one object, a `string_list` level prints one
    object per element, and a `one_of` level states the one key its mapping selects, so the export spelling
    `no` prints as `disable`. A field the export does not state prints nothing, and the entry whose choice
    element states no alternative is not printed, so the file holds no half of it and the report names it once.
    """
    expected = ('  protocol = {\n    rip = {\n      enable = true\n'
                '      allow_redist_default_route = true\n      reject_default_route = false\n'
                '      timers = {\n        interval_seconds = 30\n        update_intervals = 180\n'
                '        expire_intervals = 210\n        delete_intervals = 120\n      }\n'
                '      global_bfd = {\n        profile = "BFD-RIP"\n      }\n      interfaces = [\n'
                '        {\n          name = "ethernet1/2"\n          enable = true\n          mode = "v2"\n'
                '          authentication = "md5"\n          bfd = {\n            profile = "BFD-RIP"\n          }\n'
                '          default_route = {\n            advertise = {\n              metric = 10\n'
                '            }\n          }\n        },\n        {\n          name = "ethernet1/3"\n'
                '          enable = false\n          mode = "v1"\n          default_route = {\n'
                '            disable = {}\n          }\n        }\n      ]\n'
                '      export_rules = [\n        {\n          name = "static-af"\n          metric = 10\n'
                '        }\n      ]\n    }\n  }\n')
    files = _run('rip.xml', tmp_path)
    block = files['virtual_routers.tf']
    assert expected in block, block
    # The entry the file cannot hold is named by the report, and the file holds no half of it.
    report = files['MANUAL_SETUP_REPORT.txt']
    assert ('router default: interfaces ethernet1/4 '
            '(panos_virtual_router - default_route states no key PROTOCOL_SHAPE selects)') in report, report
    assert 'ethernet1/4' not in block, block
    # The gate reads the same table, so the block the run wrote reports no finding.
    findings = sanity_checks.check_protocol_object(files)
    assert findings == [], findings


def test_a_policy_block_prints_the_shape_the_table_states(tmp_path):
    """F7.6: the whole `protocol` field a run writes for `tests/fixtures/bgp_policy.xml`.

    Field order is the table order. A `member_list` field prints as its values, because a member is a value and
    not an entry, so no level row stands under it. A `block` field prints `{}`, because the export states the
    level by presence, and the `one_of` level prints the one key its mapping selects, so `deny` prints as the
    empty block. The export rule whose choice element states no alternative is not printed, so the file holds no
    half of it and the report names it once.
    """
    expected = (
        '  protocol = {\n' + '    bgp = {\n' + '      enable = true\n'
        '      local_as = "65001"\n' + '      policy = {\n' + '        aggregation = {\n'
        '          address = [\n' + '            {\n' + '              advertise_filters = [\n'
        '                {\n' + '                  enable = true\n'
        '                  match = {\n' + '                    address_prefix = [\n'
        '                      {\n' + '                        exact = true\n'
        '                        name = "agg-prefix"\n' + '                      }\n'
        '                    ]\n' + '                    as_path = {\n'
        '                      regex = "65001.*"\n' + '                    }\n'
        '                    community = {\n' + '                      regex = "1:1"\n'
        '                    }\n' + '                    extended_community = {\n'
        '                      regex = "1:2"\n' + '                    }\n'
        '                    from_peer = [ "192.0.2.1", "192.0.2.2" ]\n'
        '                    med = 150\n' + '                    nexthop = [ "198.51.100.7" ]\n'
        '                    route_table = "unicast"\n' + '                  }\n'
        '                  name = "agg-advertises"\n' + '                }\n' + '              ]\n'
        '              aggregate_route_attributes = {\n' + '                as_path = {\n'
        '                  prepend = 5\n' + '                }\n'
        '                as_path_limit = 5\n' + '                community = {\n'
        '                  append = [ "1:10" ]\n' + '                }\n'
        '                extended_community = {\n' + '                  remove_regex = "2:.*"\n'
        '                }\n' + '                local_preference = 200\n'
        '                med = 300\n' + '                nexthop = "198.51.100.9"\n'
        '                origin = "igp"\n' + '                weight = 100\n' + '              }\n'
        '              as_set = true\n' + '              enable = true\n'
        '              name = "agg-10.0.0.0-8"\n' + '              prefix = "10.0.0.0/8"\n'
        '              summary = true\n' + '              suppress_filters = [\n'
        '                {\n' + '                  enable = true\n'
        '                  match = {\n' + '                    address_prefix = [\n'
        '                      {\n' + '                        exact = false\n'
        '                        name = "agg-suppressed-prefix"\n' + '                      }\n'
        '                    ]\n' + '                  }\n'
        '                  name = "agg-suppresses"\n' + '                }\n' + '              ]\n'
        '            }\n' + '          ]\n' + '        }\n'
        '        conditional_advertisement = {\n' + '          policy = [\n' + '            {\n'
        '              advertise_filters = [\n' + '                {\n'
        '                  enable = true\n' + '                  match = {\n'
        '                    address_prefix = [\n' + '                      {\n'
        '                        name = "cond-prefix"\n' + '                      }\n'
        '                    ]\n' + '                  }\n'
        '                  name = "cond-advertises"\n' + '                }\n' + '              ]\n'
        '              enable = true\n' + '              name = "cond-10.0.0.0-16"\n'
        '              non_exist_filters = [\n' + '                {\n'
        '                  enable = true\n' + '                  match = {\n'
        '                    address_prefix = [\n' + '                      {\n'
        '                        name = "cond-absent-prefix"\n' + '                      }\n'
        '                    ]\n' + '                  }\n'
        '                  name = "cond-non-exist"\n' + '                }\n' + '              ]\n'
        '              used_by = [ "agg-10.0.0.0-8" ]\n' + '            }\n' + '          ]\n'
        '        }\n' + '        export = {\n' + '          rules = [\n' + '            {\n'
        '              action = {\n' + '                allow = {\n'
        '                  update = {\n' + '                    as_path = {\n'
        '                      remove = {}\n' + '                    }\n'
        '                    community = {\n' + '                      append = [ "4:1" ]\n'
        '                    }\n' + '                    local_preference = 150\n'
        '                    med = 80\n' + '                    nexthop = "198.51.100.11"\n'
        '                    origin = "egp"\n' + '                  }\n' + '                }\n'
        '              }\n' + '              enable = true\n' + '              match = {\n'
        '                address_prefix = [\n' + '                  {\n'
        '                    exact = true\n' + '                    name = "export-prefix"\n'
        '                  }\n' + '                ]\n'
        '                from_peer = [ "192.0.2.1" ]\n' + '              }\n'
        '              name = "export-allow"\n' + '              used_by = [ "cond-10.0.0.0-16" ]\n'
        '            }\n' + '          ]\n' + '        }\n' + '        import = {\n'
        '          rules = [\n' + '            {\n' + '              action = {\n'
        '                deny = {}\n' + '              }\n' + '              enable = true\n'
        '              match = {\n' + '                address_prefix = [\n'
        '                  {\n' + '                    exact = true\n'
        '                    name = "import-prefix"\n' + '                  }\n'
        '                ]\n' + '                nexthop = [ "198.51.100.12" ]\n'
        '              }\n' + '              name = "import-deny"\n'
        '              used_by = [ "agg-10.0.0.0-8" ]\n' + '            }\n' + '          ]\n'
        '        }\n' + '      }\n' + '    }\n' + '  }\n'
    )
    files = _run('bgp_policy.xml', tmp_path)
    block = files['virtual_routers.tf']
    assert expected in block, block
    # The entry the file cannot hold is named by the report, and the file holds no half of it.
    report = files['MANUAL_SETUP_REPORT.txt']
    assert ('router policy-vr: rules export-no-action '
            '(panos_virtual_router - action states no key PROTOCOL_SHAPE selects)') in report, report
    # F7.6: the policy `address` level is not an address-object section, so the report names no address object
    # for the entry the address rule would otherwise read.
    assert 'Address Objects With No v2 Attribute' not in report, report
    assert 'export-no-action' not in block, block
    # The gate reads the same table, so the block the run wrote reports no finding.
    findings = sanity_checks.check_protocol_object(files)
    assert findings == [], findings


def test_member_list_is_the_word_for_a_field_whose_members_are_values():
    """F7.6: `member_list` is the `string_list` shape with values as members, and one place states the reading.

    `SHAPE_READS_AS` is the only place that states which word the field reader reads each specialization as, so
    the gate compares a value against the family word the reader can read while the table still states the
    specialization. `SHAPE_LEVELS` is the set of words that name a level the walk enters, and a member list names
    no level, so rule 4 cannot ask a member for a `name`.
    """
    fields = {field for row in resource_mapping.PROTOCOL_SHAPE.values()
              for field, word in row['fields'].items() if word == 'member_list'}
    assert fields == {'append', 'from_peer', 'nexthop', 'overwrite', 'used_by'}, fields
    assert sanity_checks.SHAPE_READS_AS['member_list'] == 'string_list', sanity_checks.SHAPE_READS_AS
    assert sanity_checks.SHAPE_LEVELS == ('object', 'one_of', 'string_list'), sanity_checks.SHAPE_LEVELS
    # `nexthop` is a string at the aggregate level and a member list at the match level, so the word is the
    # field's shape at the row that states it, not the field name.
    assert resource_mapping.protocol_row('protocol/bgp/policy/aggregation/address/aggregate_route_attributes')[
        'fields']['nexthop'] == 'string'
    assert resource_mapping.protocol_row('protocol/bgp/policy/export/rules/match')['fields']['nexthop'] == (
        'member_list')


def test_the_gate_reads_a_member_list_as_values_and_not_as_entries(tmp_path):
    """F7.6: the walk reads a `[` value whose members are values against the row that states the field.

    The rule refuses a member list printed as a string, and it does not walk a member list, so a member is never
    asked for a `name`. The choice inside the same entry is read by the same rule as any other `one_of` level:
    the entry states one key, and that key is one the row selects.
    """
    good = ('  protocol = {\n    bgp = {\n      policy = {\n        export = {\n          rules = [\n'
            '            {\n              name = "r1"\n              used_by = [ "a", "b" ]\n'
            '              action = {\n                allow = {}\n              }\n            }\n'
            '          ]\n        }\n      }\n    }\n  }\n')
    assert _findings(good) == [], good
    findings = _findings(good.replace('used_by = [ "a", "b" ]', 'used_by = "a"'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/bgp/policy/export/rules '
        'used_by is not a member_list value'], findings
    findings = _findings(good.replace('action = {\n                allow = {}\n              }',
                                      'action = {\n                allow = {}\n'
                                      '                deny = {}\n              }'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/bgp/policy/export/rules/action '
        'states 2 keys, which a one_of level cannot'], findings
    findings = _findings(good.replace('allow = {}', 'approve = {}'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/bgp/policy/export/rules/action '
        'key approve is not a key PROTOCOL_SHAPE selects'], findings
    # The block the run wrote for the new fixture is the positive half: the rule reads the whole subtree and
    # reports nothing, including the two levels the export states by presence.
    files = _run('bgp_policy.xml', tmp_path)
    assert sanity_checks.check_protocol_object(files) == [], files['virtual_routers.tf']


def test_the_gate_reads_a_scalar_level_against_the_row_it_states():
    """One finding per violation type for a level `PROTOCOL_SHAPE` states (F7.3).

    The rule reads the printed value against the row, so a level printed in a shape the row does not state, a
    field printed in a shape the row does not state, a field the row does not declare, and an element with no
    name are four findings.
    """
    good = ('  protocol = {\n    ospfv3 = {\n      timers = {\n        lsa_interval = 120\n      }\n'
            '      export_rules = [\n        {\n          name = "static-af"\n          new_tag = "0"\n        }\n'
            '      ]\n    }\n  }\n')
    assert _findings(good) == [], good
    findings = _findings(good.replace('timers = {\n        lsa_interval = 120\n      }', 'timers = 120'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/ospfv3 timers is not a object value'], findings
    findings = _findings(good.replace('export_rules = [\n        {\n          name = "static-af"\n'
                                      '          new_tag = "0"\n        }\n      ]',
                                      'export_rules = {\n        name = "static-af"\n      }'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/ospfv3 export_rules '
        'is not a string_list value'], findings
    findings = _findings(good.replace('new_tag = "0"', 'new_tag = 0'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/ospfv3/export_rules '
        'new_tag is not a string value'], findings
    # An element inside a `[` container is an entry, so the entry name is the field the row reads for it.
    findings = _findings(good.replace('{\n          name = "static-af"\n          new_tag = "0"',
                                      '{\n          new_tag = "0"'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/ospfv3/export_rules '
        'element states no name'], findings
    findings = _findings(good.replace('lsa_interval = 120', 'lsa_period = 120'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/ospfv3/timers '
        'lsa_period is not a field PROTOCOL_SHAPE declares'], findings


def test_the_gate_reads_an_ospf_level_against_the_row_it_states():
    """F7.9: the walk reads the seven `protocol/ospf` fields the row now states, and still refuses a field the
    row does not declare.

    The seven fields are the measured provider shape, so a hand-written block that states them is not a
    finding: three `bool` values, three single-object levels, and one entry list. `disable_transit_traffic` is
    the field the provider declares for `ospfv3` and not for `ospf`, so the refusal the row restates is the same
    finding the field rule reports for any name the row does not declare. The positive half read from a real
    run is `test_an_ospf_level_prints_the_shape_the_table_states`.
    """
    good = ('  protocol = {\n    ospf = {\n      enable = true\n      router_id = "10.0.0.1"\n'
            '      allow_redist_default_route = true\n      reject_default_route = false\n'
            '      rfc1583 = true\n      timers = {\n        lsa_interval = 120\n      }\n'
            '      global_bfd = {\n        profile = "BFD-OSPF"\n      }\n      graceful_restart = {\n'
            '        enable = true\n        grace_period = 120\n        helper_enable = true\n'
            '        max_neighbor_restart_time = 200\n        strict_l_s_a_checking = true\n      }\n'
            '      export_rules = [\n        {\n          name = "export-static"\n          metric = 10\n'
            '          new_path_type = "internal"\n          new_tag = "0"\n        }\n      ]\n    }\n  }\n')
    assert _findings(good) == [], good
    findings = _findings(good.replace('rfc1583 = true', 'rfc1583 = "yes"'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/ospf rfc1583 is not a bool value'], findings
    findings = _findings(good.replace('reject_default_route = false', 'disable_transit_traffic = true'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/ospf '
        'disable_transit_traffic is not a field PROTOCOL_SHAPE declares'], findings
    findings = _findings(good.replace('timers = {\n        lsa_interval = 120\n      }', 'timers = 120'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/ospf timers is not a object value'], findings
    # An entry inside the entry list is an entry, so the entry name is the field the row reads for it.
    findings = _findings(good.replace('{\n          name = "export-static"\n          metric = 10',
                                      '{\n          metric = 10'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/ospf/export_rules '
        'element states no name'], findings


def test_a_choice_body_prints_the_fields_it_declares(tmp_path):
    """The fields of a `one_of` body live inside the chosen element, so the parse reads them there (F7.2, F7.4).

    The export puts the flag's fields inside the chosen element, not inside `type`. The rule is one rule for
    both routing levels, so the same test pins the `ospf` area and the `ospfv3` area. F7.4: the export states
    the choice inside the body by presence, and the print states the key the row selects for it, which is
    `disable` for the value `no`.
    """
    ospf_body = ('type = {\n            stub = {\n              accept_summary = true\n'
                 '              default_route = {\n                advertise = {\n                  metric = 10\n'
                 '                }\n              }\n            }\n          }')
    ospfv3_body = ('type = {\n            nssa = {\n              accept_summary = true\n'
                   '              default_route = {\n                disable = {}\n              }\n'
                   '              nssa_ext_range = [\n                {\n'
                   '                  name = "10.20.0.0/16"\n                  advertise = {}\n'
                   '                }\n              ]\n            }\n          }')
    ospf = _run('ospf.xml', tmp_path / 'ospf')['virtual_routers.tf']
    ospfv3 = _run('ospfv3.xml', tmp_path / 'ospfv3')['virtual_routers.tf']
    assert ospf_body in ospf, ospf
    assert ospfv3_body in ospfv3, ospfv3
    # F7.4: a neighbor entry prints as the entry name, which is the whole shape the row states.
    pin = 'neighbor = [\n                {\n                  name = "10.0.0.2"\n                }\n              ]'
    assert pin in ospfv3, ospfv3


def test_the_gate_reads_a_choice_inside_a_body():
    """F7.4: the walk reads a `one_of` level inside a chosen body against the row that states it.

    The rule is one rule for every level, so `default_route` is checked the same way `type` is: the level
    states one key, and that key is one the row's mapping selects. The value the export states (`no`) is not
    the key the print states (`disable`), so a block that writes the export spelling is a finding.
    """
    good = ('  protocol = {\n    ospfv3 = {\n      area = [\n        {\n          name = "0.0.0.0"\n'
            '          type = {\n            nssa = {\n              default_route = {\n'
            '                disable = {}\n              }\n            }\n          }\n        }\n      ]\n'
            '    }\n  }\n')
    assert _findings(good) == [], good
    findings = _findings(good.replace('disable = {}', 'no = {}'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/ospfv3/area/type/nssa/default_route '
        'key no is not a key PROTOCOL_SHAPE selects'], findings
    findings = _findings(good.replace('default_route = {\n                disable = {}\n              }',
                                      'default_route = {}'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/ospfv3/area/type/nssa/default_route '
        'states 0 keys, which a one_of level cannot'], findings
    # The entries inside a `string_list` level hold the entry name, which is the field the row reads.
    findings = _findings(good.replace(
        'default_route = {\n                disable = {}\n              }',
        'default_route = {\n                disable = {}\n              }\n'
        '              nssa_ext_range = [\n                {\n                  advertise = {}\n                }\n'
        '              ]'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/ospfv3/area/type/nssa/nssa_ext_range '
        'element states no name'], findings


def test_the_gate_reads_a_choice_inside_an_entry_level():
    """F7.5: the walk reads a `one_of` field inside an entry against the row that states it.

    A choice inside a chosen body and a choice inside an entry are the same rule, so `default_route` inside a
    `rip` interface entry is checked the same way `type` inside an area body is: the level states one key, and
    that key is one the row's mapping selects. The entry name is the field the row reads for an element inside
    a `string_list` level, and the fields of a chosen alternative are checked against the row for that
    alternative.
    """
    good = ('  protocol = {\n    rip = {\n      interfaces = [\n        {\n'
            '          name = "ethernet1/2"\n          default_route = {\n            advertise = {\n'
            '              metric = 10\n            }\n          }\n        }\n      ]\n    }\n  }\n')
    assert _findings(good) == [], good
    findings = _findings(good.replace('advertise = {\n              metric = 10\n            }',
                                      'advertise = {}\n            disable = {}'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/rip/interfaces/default_route '
        'states 2 keys, which a one_of level cannot'], findings
    findings = _findings(good.replace('            advertise = {\n              metric = 10\n            }',
                                      '            no = {}'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/rip/interfaces/default_route '
        'key no is not a key PROTOCOL_SHAPE selects'], findings
    findings = _findings(good.replace('metric = 10', 'made_up = 10'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/rip/interfaces/default_route/advertise '
        'made_up is not a field PROTOCOL_SHAPE declares'], findings
    # `mode` is a string, so the row states no `selects` for it: the value is the string the export states.
    findings = _findings(good.replace('          name = "ethernet1/2"\n',
                                      '          name = "ethernet1/2"\n          mode = {\n'
                                      '            v2 = {}\n          }\n'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/rip/interfaces '
        'mode is not a string value'], findings
    # An element inside a `[` container is an entry, so the entry name is the field the row reads for it.
    findings = _findings(good.replace('{\n          name = "ethernet1/2"\n', '{\n          mode = "v2"\n'))
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/rip/interfaces '
        'element states no name'], findings


def test_an_unmapped_one_of_value_prints_nothing_and_is_reported(make_parser):
    """The mapping is the one lookup, and the entry it cannot state is the entry the report names.

    `_protocol_choice` states both the printed value and the reason it cannot be printed, so the parse
    marks the entry for the report with that reason and does not put it in the printed list.
    """
    parser = make_parser('ospf.xml')
    parser.parse_virtual_routers()
    rows = entry_coverage.protocol_report_rows(parser.ledger)
    unmapped = [row for row in rows if row['name'] == 'ethernet1/3']
    assert len(unmapped) == 1, rows
    assert unmapped[0]['detail'] == (
        'link_type multicast is not a value PROTOCOL_SHAPE states'), unmapped[0]
    assert unmapped[0]['captured']['link_type'] == {'multicast': {}}, unmapped[0]
    # The parse prints nothing for a value the mapping cannot state, so the file has no empty field.
    assert sanity_checks.value_shape('') == ''


def test_an_ospf_interface_at_the_router_level_is_reported(make_parser):
    """`PROTOCOL_SHAPE` states no interface outside an area, so the row's note is the reason (F7.1)."""
    parser = make_parser('ospf.xml')
    parser.parse_virtual_routers()
    rows = entry_coverage.protocol_report_rows(parser.ledger)
    outside = [row for row in rows if row['name'] == 'ethernet1/1']
    assert len(outside) == 1, rows
    # The mark states no detail, because the container row's note is the reason.
    assert outside[0]['detail'] == 'no provider field for an interface outside an area', outside[0]
    assert outside[0]['level'] == 'interface', outside[0]


def test_an_ospfv3_interface_at_the_level_is_reported(make_parser):
    """The same rule serves both routing levels: the container row's note is the reason (F7.2)."""
    parser = make_parser('ospfv3.xml')
    parser.parse_virtual_routers()
    rows = entry_coverage.protocol_report_rows(parser.ledger)
    outside = [row for row in rows if row['name'] == 'ethernet1/1']
    assert len(outside) == 1, rows
    assert outside[0]['detail'] == 'no provider field for an interface outside an area', outside[0]
    assert outside[0]['level'] == 'interface', outside[0]


# --- 5. a sensitive field prints as the variable reference -------------------

def test_a_sensitive_field_prints_as_the_variable_reference(converter_module, tmp_path):
    """The rule refuses a secret written as a literal, and the emitter prints the reference the table says.

    `protocol/bgp/auth_profile` is a level the parse reads, so a run prints the reference for the value it read
    (`test_an_auth_profile_prints_the_reference_the_entry_names`); the block here is written by hand, so the pin
    is the rule alone: the table row is what both the emitter and the rule read.
    """
    findings = _findings('  protocol = {\n    bgp = {\n      auth_profile = [\n        {\n'
                         '          name = "AP-1"\n          secret = "hunter2"\n        }\n      ]\n    }\n  }\n')
    assert len(findings) == 1, findings
    assert 'prints a sensitive value as a literal' in findings[0].detail, findings[0]
    assert _findings('  protocol = {\n    bgp = {\n      auth_profile = [\n        {\n'
                     '          name = "AP-1"\n          secret = var.ap_1\n        }\n      ]\n    }\n  }\n') == []

    # The print site is `printed_value`, and a reference-only name records no value for the `.tfvars`, so
    # the run declares nothing and writes no line for it: the operator supplies the value.
    # F6.10.4: the print site takes the unit's facts, so the record is keyed by the unit the block reads.
    generator = converter_module.TerraformGenerator(str(tmp_path))
    entry = {'name': 'AP-1'}
    facts = unit_manifest.facts_of(entry)
    assert generator.printed_value('secret', 'AP-1', facts) == naming.variable_text('AP-1')
    assert generator.value_variables() == {facts: {}}, generator.value_variables()
    printed = generator._protocol_fields('protocol/bgp/auth_profile',
                                         {'name': 'AP-1', 'secret': 'hunter2'}, entry)
    # A reference prints unquoted, so the value is the HCL expression the reader reads as an object, not a
    # quoted string.
    assert printed['secret'].expr == naming.variable_text('AP-1'), printed
    assert 'name' in printed, printed
    rendered = generator.hcl_value(printed)
    assert 'secret = var.ap_1' in rendered and '"hunter2"' not in rendered, rendered


def test_a_rip_auth_profile_field_prints_the_reference_only():
    """F7.5: the two `protocol/rip` rows that state the `sensitive` decision are read by the rule.

    No parse method reads an auth profile body, so the block is written by hand, the same way the `bgp` row is
    read above. The schema marks `password` on the profile level and `key` inside `md5`, so the rule refuses a
    literal for each and accepts the variable reference.
    """
    literal = ('  protocol = {\n    rip = {\n      auth_profile = [\n        {\n'
               '          name = "AP-RIP"\n          password = "hunter2"\n          md5 = [\n'
               '            {\n              name = "MD5-1"\n              key = "hunter2"\n            }\n'
               '          ]\n        }\n      ]\n    }\n  }\n')
    assert [f.detail for f in _findings(literal)] == [
        'protocol panos_virtual_router.default_00000000 protocol/rip/auth_profile '
        'password prints a sensitive value as a literal',
        'protocol panos_virtual_router.default_00000000 protocol/rip/auth_profile/md5 '
        'key prints a sensitive value as a literal'], _findings(literal)
    reference = literal.replace('password = "hunter2"', 'password = var.ap_rip').replace(
        'key = "hunter2"', 'key = var.md5_1')
    assert _findings(reference) == [], reference


def test_an_auth_profile_prints_the_reference_the_entry_names(tmp_path):
    """F7.7: a run that reads an auth profile prints the reference the entry names, never the value.

    The entry that holds a `sensitive` field names the variable: the profile entry for `secret` and `password`,
    the `md5` entry for the `key` inside it, and the profile entry for the `key` inside a choice level, because
    a level inside an entry is not an entry and names nothing. Field order is the table order, `none` prints as
    `{}` because it is the `block` field of the row that states it, and the gate reads the same table, so the
    block the run wrote reports no finding. The fixture states the two `ospfv3` choice levels in two entries,
    because the provider accepts one or the other for an entry, which `terraform validate` confirms.
    """
    expected = ('  protocol = {\n    bgp = {\n      enable = true\n      auth_profile = [\n'
                '        {\n          name = "profile-bgp"\n          secret = var.profile_bgp\n'
                '        }\n      ]\n    }\n    ospf = {\n      enable = true\n'
                '      auth_profile = [\n        {\n          name = "profile-ospf"\n'
                '          password = var.profile_ospf\n          md5 = [\n            {\n'
                '              name = "profile-ospf-md5"\n              key = var.profile_ospf_md5\n'
                '              preferred = true\n            }\n          ]\n        }\n      ]'
                '\n    }\n    ospfv3 = {\n      enable = true\n      auth_profile = [\n        {'
                '\n          name = "profile-ospfv3-ah"\n          spi = "2000"\n          ah = {\n'
                '            sha1 = {\n              key = var.profile_ospfv3_ah\n            }\n'
                '          }\n        },\n        {\n          name = "profile-ospfv3-esp"\n'
                '          esp = {\n            authentication = {\n              none = {}\n'
                '            }\n            encryption = {\n              algorithm = "aes256"\n'
                '              key = var.profile_ospfv3_esp\n            }\n          }\n        }'
                '\n      ]\n    }\n    rip = {\n      enable = true\n      auth_profile = [\n'
                '        {\n          name = "profile-rip"\n          password = var.profile_rip\n'
                '          md5 = [\n            {\n              name = "profile-rip-md5"\n'
                '              key = var.profile_rip_md5\n            }\n          ]\n        }\n'
                '      ]\n    }\n  }\n}')
    files = _run('auth_profile.xml', tmp_path)
    block = files['virtual_routers.tf']
    assert expected in block, block
    assert sanity_checks.check_protocol_object(files) == [], sanity_checks.check_protocol_object(files)


def test_the_gate_reads_a_choice_level_inside_an_auth_profile():
    """F7.7: the gate reads the choice levels inside the `ospfv3` profile entry against the same rows.

    `ah` and `esp/authentication` are `one_of` levels whose alternatives are their own rows, so the rule reads
    the chosen alternative as a level and refuses a literal for the field the provider marks `sensitive` there.
    `none` is the `block` field the row states, so an object value for it is the shape the reader reads back.
    The provider accepts `ah` or `esp` for one entry, so the example states them in two entries, the way the
    fixture does.
    """
    literal = ('  protocol = {\n    ospfv3 = {\n      auth_profile = [\n        {\n'
               '          name = "AP-3"\n          ah = {\n            sha1 = {\n'
               '              key = "hunter2"\n            }\n          }\n        },\n        {\n'
               '          name = "AP-4"\n          esp = {\n            authentication = {\n'
               '              md5 = {\n                key = "hunter2"\n              }\n            }\n          }\n'
               '        }\n      ]\n    }\n  }\n')
    assert [f.detail for f in _findings(literal)] == [
        'protocol panos_virtual_router.default_00000000 protocol/ospfv3/auth_profile/ah/sha1 '
        'key prints a sensitive value as a literal',
        'protocol panos_virtual_router.default_00000000 protocol/ospfv3/auth_profile/esp/authentication/md5 '
        'key prints a sensitive value as a literal'], _findings(literal)
    # Each entry names its own variable, so a reference for each is the shape the gate accepts.
    reference = ('  protocol = {\n    ospfv3 = {\n      auth_profile = [\n        {\n'
                 '          name = "AP-3"\n          ah = {\n            sha1 = {\n'
                 '              key = var.ap_3\n            }\n          }\n        },\n        {\n'
                 '          name = "AP-4"\n          esp = {\n            authentication = {\n'
                 '              md5 = {\n                key = var.ap_4\n              }\n            }\n          }\n'
                 '        }\n      ]\n    }\n  }\n')
    assert _findings(reference) == [], reference
    # A `block` alternative is the empty object the export stated by presence, so it is the shape the reader
    # reads back.
    assert _findings('  protocol = {\n    ospfv3 = {\n      auth_profile = [\n        {\n'
                     '          name = "AP-3"\n          esp = {\n            authentication = {\n'
                     '              none = {}\n            }\n          }\n        }\n      ]\n    }\n  }\n') == []
    # A value the row does not state as an alternative is the same finding the one-of rule reports.
    findings = _findings('  protocol = {\n    ospfv3 = {\n      auth_profile = [\n        {\n'
                         '          name = "AP-3"\n          ah = {\n            unknown = {}\n'
                         '          }\n        }\n      ]\n    }\n  }\n')
    assert [f.detail for f in findings] == [
        'protocol panos_virtual_router.default_00000000 protocol/ospfv3/auth_profile/ah key unknown '
        'is not a key PROTOCOL_SHAPE selects'], findings


def test_a_sensitive_field_is_never_written_as_a_value(tmp_path):
    """No generated file states a protocol secret, because the run holds no value for a reference-only name.

    `site_data.py` rule 2 writes a row for a site that names a value, so a name the run cannot value has no
    `.tfvars` line and no site data row. F7.7: the same rule for a value the run did read is pinned by
    `tests/test_robustness.py::test_a_parsed_secret_never_reaches_a_generated_file`.
    """
    files = _run('kitchen_sink.xml', tmp_path)
    assert not any('hunter2' in text for text in files.values()), sorted(files)
    tfvars = files.get(site_data.TFVARS_FILE, '')
    assert 'secret' not in tfvars and 'key' not in tfvars, tfvars


# --- 6. the gate findings and determinism ------------------------------------

def test_the_rule_reports_an_undeclared_field_and_a_wrong_shape():
    """Finding 1: a field the row does not declare, and a value the reader reads as another shape."""
    findings = _findings('  protocol = {\n    bgp = {\n      made_up = "y"\n    }\n  }\n')
    assert len(findings) == 1 and 'made_up is not a field' in findings[0].detail, findings
    findings = _findings('  protocol = {\n    bgp = {\n      enable = "yes"\n    }\n  }\n')
    assert len(findings) == 1 and 'enable is not a bool value' in findings[0].detail, findings
    # A `list` level that states an object value is the same finding.
    findings = _findings('  protocol = {\n    bgp = {\n      peer_group = {\n'
                         '        name = "PG"\n      }\n    }\n  }\n')
    assert len(findings) == 1 and 'peer_group is not a string_list value' in findings[0].detail, findings
    # A level the table states no row for is the same finding: `protocol` declares the two redist profile
    # lists in the provider, but the table states only the levels this converter prints, so the rule refuses a
    # level outside it. `rip` is a row now (F7.5), so the rule reads it against its row instead, which
    # `test_the_gate_reads_a_choice_inside_an_entry_level` pins.
    findings = _findings('  protocol = {\n    redist_profile = {\n      name = "R1"\n    }\n  }\n')
    assert len(findings) == 1 and 'redist_profile is not a field' in findings[0].detail, findings


def test_the_rule_reports_a_list_element_with_no_name():
    """Finding 4: the entry name is the field the row reads for an element inside a container."""
    findings = _findings('  protocol = {\n    bgp = {\n      peer_group = [\n        {\n'
                         '          enable = true\n        }\n      ]\n    }\n  }\n')
    assert len(findings) == 1, findings
    assert 'element states no name' in findings[0].detail, findings[0]
    assert findings[0].check == 'protocol_object', findings[0]
    assert findings[0].severity == sanity_checks.FAIL, findings[0]
    assert findings[0].file == 'vr.tf' and findings[0].line == 1, findings[0]


def test_the_rule_runs_after_actions_in_the_gate_order():
    """`CHECK_ORDER` names `protocol_object` after `actions`, and the runner records it."""
    assert sanity_checks.CHECK_ORDER[sanity_checks.CHECK_ORDER.index('actions') + 1] == 'protocol_object'
    assert 'protocol_object' in sanity_checks.CHECK_ORDER


def test_two_runs_write_the_same_bytes(tmp_path):
    """The print order is the table order and `hcl_value` is the only printer, so the bytes repeat."""
    first = _run('kitchen_sink.xml', tmp_path / 'first')
    second = _run('kitchen_sink.xml', tmp_path / 'second')
    assert first['virtual_routers.tf'] == second['virtual_routers.tf']
    assert first['MANUAL_SETUP_REPORT.txt'] == second['MANUAL_SETUP_REPORT.txt']
