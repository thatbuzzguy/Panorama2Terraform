"""F7.1: the `protocol` object as output on `panos_virtual_router`.

`resource_mapping.PROTOCOL_SHAPE` is the one table that states the shape of the protocol object. The
emitter (`TerraformGenerator.generate_virtual_routers`), the gate rule
(`sanity_checks.check_protocol_object`) and these tests read the same table, and
`sanity_checks.value_shape` stays that reader's own inverse, so no second table names a shape.

Pins:

- the table against the live provider schema: one row per level the converter prints, the field names the
  provider declares, the shape word for each field, the `selects` keys, and the `sensitive` flags;
- the print shape: `protocol = { ... }` is one field of the block, and `protocol { ... }` is the shape the
  provider refuses, so the rule reports it (`tests/test_terraform_validate.py` runs the same check on a
  real run);
- the one-of mapping, the peer membership, the interface inside an area, and the value the mapping cannot
  state;
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


# A `SHAPE_WORDS` word as the schema states it. A level word is a nesting mode, and a leaf word is a type.
WORD_TO_SCHEMA = {'string_list': 'list', 'object': 'single', 'one_of': 'single', 'block': 'single'}


# --- 1. the table against the live provider schema ---------------------------

def test_the_shape_table_is_the_measured_provider_shape(provider_schema):
    """Every row, field, shape word, `selects` key, and `sensitive` flag is a fact the provider declares.

    The table states the levels this converter prints, so it is a subset of the schema: `protocol` also
    declares `rip` and the two redist profile lists, which the converter does not print and the gate does not
    check. A row states only the fields the parse method that reaches the level reads, so the `ospfv3`
    `auth_profile` level, `area/virtual_link`, `area/interface/neighbor`, and `area/type/default_route` are
    outside the table (`backlog.md`).
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
        # A `one_of` row's alternatives are the schema's attributes, and each one is a row in the table.
        if row['selects']:
            assert set(row['selects'].values()) == set(attributes), (path, row['selects'])
            for key in row['selects'].values():
                assert f'{path}/{key}' in resource_mapping.PROTOCOL_SHAPE, (path, key)


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
    """No parse method, emitter, or gate branch names a protocol field or a shape of its own (F7.1).

    The table states the names and the shapes, and the reader and the rule read the table, so a field name
    written as a string constant in a parse method, the emitter, or the rule is a second owner. The parse
    methods state a level as a table path, so the key they write is the field the path names. `name` is the
    field the rule reads for the entry name, and `protocol` is the table's own `PROTOCOL_FIELD`: those two are
    the names the rule has to state.
    """
    fields = {field for row in resource_mapping.PROTOCOL_SHAPE.values() for field in row['fields']}
    # The static-route emitter is not a protocol owner: `metric` is the route's own field there, and the row
    # `COVERAGE_MATRIX` states for it names that shape. `name` is the field the rule reads for the entry
    # name, and `protocol` is the table's own `PROTOCOL_FIELD`.
    static_route = [row for row in resource_mapping.COVERAGE_MATRIX
                    if row['resource'] == 'panos_virtual_router_static_route_ipv4'][0]
    allowed = (set(resource_mapping.SHAPE_WORDS) | {'name', resource_mapping.PROTOCOL_FIELD}
               | set(static_route['properties']))
    owners = [getattr(sanity_checks, name, None) for name in
              ('check_protocol_object', '_protocol_level_findings', '_protocol_field_findings', 'value_shape')]
    generator = converter_module.TerraformGenerator
    parser = converter_module.PanoramaParser
    owners += [getattr(generator, name) for name in ('generate_virtual_routers', '_protocol_fields', 'printed_value')]
    owners += [getattr(parser, name) for name in
               ('parse_bgp', 'parse_ospf', 'parse_ospfv3', '_protocol_areas', '_protocol_level',
                '_protocol_field', '_protocol_choice', '_protocol_interface', '_protocol_field_name',
                '_protocol_xml_name')]
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
    assert parser._protocol_field_name('protocol/ospf/area/interface/link_type') == 'link_type'
    # F7.3: the provider spells one field name from an element name the `-` rule cannot produce, because it
    # splits the initialism, so `XML_NAME_EXCEPTIONS` is the one place that states it.
    assert resource_mapping.XML_NAME_EXCEPTIONS == {'strict_l_s_a_checking': 'strict-lsa-checking'}
    assert parser._protocol_xml_name('strict_l_s_a_checking') == 'strict-lsa-checking'


def test_the_ospfv3_scalar_levels_are_rows_the_parse_reads():
    """The four `ospfv3` levels outside `area` are table rows, and the level that holds entries is the one
    the property scan measures (F7.3).

    `test_the_shape_table_is_the_measured_provider_shape` pins every row against the schema, so this test pins
    the shape decision and the measurement scope: a single-object level holds no entry, so the scan measures
    nothing for it and the container table names no row for it, while an export rule is an entry.
    """
    level = resource_mapping.protocol_row('protocol/ospfv3')
    assert [field for field in level['fields'] if field not in ('enable', 'router_id', 'area')] == [
        'timers', 'global_bfd', 'graceful_restart', 'export_rules'], level['fields']
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
                             'protocol/ospfv3/export-rules', 'protocol/ospfv3/interface',
                             'protocol/ospfv3/range'], rows


def test_value_shape_is_the_reader_inverse_for_every_shape_word():
    """`value_shape` reads back each shape word the table states, including `number` and `block` (F6.7, F7.1)."""
    samples = {'string': '"host"', 'bool': 'true', 'number': '10', 'object': '{}',
               'string_list': '["a"]', 'one_of': '{ebgp = {}}', 'block': '{}'}
    for word, text in samples.items():
        expected = 'object' if word in ('one_of', 'block') else word
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
    """The `ospfv3` subtree prints as the rows `PROTOCOL_SHAPE` states for it (F7.2).

    Field order is the table order, a `one_of` level states the one key its mapping selects, and a `block`
    field prints `{}` because the export states it by presence.
    """
    expected = ('  protocol = {\n    ospfv3 = {\n      enable = true\n      router_id = "10.0.0.1"\n'
                '      area = [\n        {\n          name = "0.0.0.0"\n          type = {\n'
                '            nssa = {\n              accept_summary = true\n            }\n          }\n'
                '          range = [\n            {\n              name = "10.0.0.0/8"\n'
                '              suppress = {}\n            }\n          ]\n          interface = [\n'
                '            {\n              name = "ethernet1/2"\n              enable = true\n'
                '              passive = false\n              metric = 10\n              link_type = {\n'
                '                p2p = {}\n              }\n            }\n          ]\n        }\n      ]\n'
                '    }\n  }\n')
    block = _run('ospfv3.xml', tmp_path)['virtual_routers.tf']
    assert expected in block, block
    # The gate reads the same table, so the block the run wrote reports no finding.
    findings = _findings(expected)
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


def test_a_choice_body_prints_the_fields_it_declares(tmp_path):
    """The fields of a `one_of` body live inside the chosen element, so the parse reads them there (F7.2).

    The export puts the flag's fields inside the chosen element, not inside `type`. The rule is one rule for
    both routing levels, so the same test pins the `ospf` area and the `ospfv3` area.
    """
    body = 'type = {\n            stub = {\n              accept_summary = true\n            }\n          }'
    ospf = _run('ospf.xml', tmp_path / 'ospf')['virtual_routers.tf']
    ospfv3 = _run('ospfv3.xml', tmp_path / 'ospfv3')['virtual_routers.tf']
    assert body in ospf, ospf
    assert body.replace('stub', 'nssa') in ospfv3, ospfv3


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

    No parse method reads an auth profile, so the block is written by hand: the table row for
    `protocol/bgp/auth_profile` is what both the emitter and the rule read.
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


def test_a_sensitive_field_is_never_written_as_a_value(tmp_path):
    """No generated file states a protocol secret, because the run holds no value for a reference-only name.

    `site_data.py` rule 2 writes a row for a site that names a value, so a name the run cannot value has no
    `.tfvars` line and no site data row.
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
    # A level the table states no row for is the same finding: `protocol` declares `rip` in the provider,
    # but the table states only the levels this converter prints, so the rule refuses a level outside it.
    findings = _findings('  protocol = {\n    rip = {\n      enable = true\n    }\n  }\n')
    assert len(findings) == 1 and 'rip is not a field' in findings[0].detail, findings


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
