"""F3.5: multi-vsys identity and `location` sub-block choice.

Provider v2 places a resource with the `location` argument, and the
sub-blocks one type accepts differ from the next. `terraform validate`
accepts an unknown `location` sub-block and drops it silently, so these
tests check the emitted text against the verified v2.0.14 schema
(`LOCATION_SCHEMA` in resource_mapping.py) instead of relying on validate.

Three contracts:

1. The parser records the source scope an export declares, with no
   defaults: `vsys`, `template`, `vsys_device`, and the device group.
2. The emitter picks the sub-block the type accepts and the source identity
   allows, and reports a scope it cannot carry.
3. A name that repeats in two virtual systems produces two resources with
   two digests.
"""

import pytest

from panorama_to_terraform import TerraformGenerator
from resource_mapping import EMITTED_TYPES, LOCATION_SCHEMA


@pytest.fixture
def gen(tmp_path):
    """Return a generator writing into a temporary output directory."""
    return TerraformGenerator(str(tmp_path))


def _location(text: str) -> dict:
    """Return the emitted location as {scope: {field: value}}.

    The emitter writes `location` in a fixed shape (one sub-block, flat
    string fields), so a small line scanner is enough and keeps the
    assertions readable.
    """
    lines = text.split('\n')
    start = next(i for i, line in enumerate(lines)
                 if line.startswith('  location = {'))
    scopes, current = {}, None
    for line in lines[start + 1:]:
        stripped = line.strip()
        if stripped.endswith('= {}'):
            scopes[stripped.split(' = ')[0]] = {}
            current = None
        elif stripped.endswith('= {'):
            current = stripped.split(' = ')[0]
            scopes[current] = {}
        elif stripped == '}':
            if current is None:
                break
            current = None
        elif ' = ' in stripped and current is not None:
            key, value = stripped.split(' = ', 1)
            scopes[current][key] = value.strip('"')
    return scopes


def _resources(text: str) -> dict:
    """Return {resource header: full block} for every resource in a file."""
    blocks, current = {}, None
    for line in text.split('\n'):
        if line.startswith('resource "'):
            current = line
            blocks[current] = line + '\n'
        elif current is not None:
            blocks[current] += line + '\n'
    return blocks


# --- LOCATION_SCHEMA (the verified provider contract) ----------------------

def test_schema_table_matches_provider_shape():
    """Every emitted type declares its location sub-blocks and their fields.

    The field lists are the v2.0.14 `terraform providers schema -json`
    output; a wrong entry emits a location that validate accepts and apply
    rejects.
    """
    # Objects and rules take device_group, shared, or vsys.
    assert LOCATION_SCHEMA['panos_address'] == {
        'device_group': ('name', 'panorama_device'),
        'shared': (),
        'vsys': ('name', 'ngfw_device')}
    # A security profile group has no vsys sub-block.
    assert LOCATION_SCHEMA['panos_security_profile_group'] == {
        'device_group': ('name', 'panorama_device'), 'shared': ()}
    # Zones and virtual routers are template or vsys scoped, never device
    # group or shared.
    assert LOCATION_SCHEMA['panos_zone'] == {
        'template': ('name', 'ngfw_device', 'panorama_device', 'vsys'),
        'vsys': ('name', 'ngfw_device')}
    # A VLAN interface template block declares no vsys field.
    assert LOCATION_SCHEMA['panos_vlan_interface'] == {
        'ngfw': ('ngfw_device',),
        'shared': (), 'template': ('name', 'ngfw_device', 'panorama_device')}


def test_only_template_scoped_types_declare_ngfw():
    """`ngfw` belongs to the template-scoped types, and to every one of them.

    Config a firewall owns is a template-scoped object placed on one device
    (F3.6). Objects and rules live in a virtual system or a device group, so
    they have no ngfw sub-block to emit.
    """
    ngfw_types = {t for t, scopes in LOCATION_SCHEMA.items() if 'ngfw' in scopes}
    assert ngfw_types == TerraformGenerator._TEMPLATE_SCOPED_TYPES - {'panos_zone'}
    assert 'panos_address' not in ngfw_types
    assert 'panos_security_policy_rules' not in ngfw_types


def test_schema_table_exists_in_the_provider_schema(provider_schema):
    """Every sub-block and field the table lists really exists.

    The table is a subset by design: the provider also declares
    `template_stack`, `template_stack_vsys` and `template_vsys` for some
    types, and the converter never needs them (a template stack holds device
    and template members, never config). A table entry the provider does not
    declare is an invalid location.
    """
    for resource_type, scopes in LOCATION_SCHEMA.items():
        assert resource_type in provider_schema, resource_type
        location = provider_schema[resource_type]['block']['attributes']
        assert 'location' in location, resource_type
        sub_blocks = location['location']['nested_type']['attributes']
        for sub_block, fields in scopes.items():
            assert sub_block in sub_blocks, f'{resource_type}.{sub_block}'
            declared = sub_blocks[sub_block]['nested_type'].get('attributes', {})
            for field in fields:
                assert field in declared, f'{resource_type}.{sub_block}.{field}'


def test_schema_table_covers_every_emitted_type():
    """No emitted resource type is missing from the schema table."""
    assert not EMITTED_TYPES - set(LOCATION_SCHEMA), sorted(
        EMITTED_TYPES - set(LOCATION_SCHEMA))


def test_template_scoped_types_derive_from_schema():
    """A type is template-scoped when its location has no device_group."""
    assert {'panos_zone', 'panos_virtual_router', 'panos_monitor_profile'} <= \
        TerraformGenerator._TEMPLATE_SCOPED_TYPES
    assert 'panos_address' not in TerraformGenerator._TEMPLATE_SCOPED_TYPES
    assert 'panos_security_policy_rules' not in \
        TerraformGenerator._TEMPLATE_SCOPED_TYPES


# --- parser identity (the honest source scope) -----------------------------

def test_parser_records_declared_scope(make_parser):
    """A declared vsys, template, and device all reach the parsed object."""
    parser = make_parser('kitchen_sink.xml')
    zones = {z['name']: z for z in parser.parse_zones()}
    assert (zones['vsys-zone2']['vsys'], zones['vsys-zone2']['vsys_device']) == \
        ('vsys2', 'fw-2.example.com')
    assert zones['vsys-zone1']['vsys'] == 'vsys1'

    routers = {r['name']: r for r in parser.parse_virtual_routers()}
    assert routers['default']['template'] == 'FW-Template'
    assert routers['default']['vsys'] == ''


def test_parser_records_no_invented_scope(make_parser):
    """An undeclared vsys or template stays empty (F3.5).

    The old parser wrote vsys1 for every object and 'device-specific' for
    every router outside a template, so the emitter could not tell a shared
    object from one the export placed in vsys1.
    """
    parser = make_parser('kitchen_sink.xml')
    shared = {a['name']: a for a in parser.parse_address_objects()
              if a['device_group'] == 'Shared' and not a['vsys']}
    # The <shared> section declares no virtual system and no device.
    assert shared['Web-Server-1']['vsys'] == ''
    assert shared['Web-Server-1']['template'] == ''
    assert shared['Web-Server-1']['vsys_device'] == ''

    routers = {r['name']: r for r in parser.parse_virtual_routers()}
    # A device-level router names its device and no virtual system.
    assert routers['vr-device-level']['vsys_device'] == 'fw-2.example.com'
    assert routers['vr-device-level']['vsys'] == ''
    assert routers['vr-device-level']['template'] == ''


def test_every_parse_method_records_the_four_scope_facts(make_parser):
    """Every parse method records the four scope facts on every object (F3.10).

    The emitter places a resource from these four facts alone, so an object
    without them cannot be placed. The rule holds for every parse method that
    returns objects. parse_device_groups is the one exception: it returns the
    device groups themselves, which are the scope, not an object inside a
    scope. Tables (associations) and settings (BGP, OSPF) are not objects.
    """
    parser = make_parser('kitchen_sink.xml')
    facts = {'device_group', 'vsys', 'template', 'vsys_device'}
    checked = 0
    for name in sorted(dir(parser)):
        if not name.startswith('parse_') or name == 'parse_device_groups':
            continue
        result = getattr(parser, name)()
        if isinstance(result, dict) and all(isinstance(v, list) for v in result.values()):
            items = [item for values in result.values() for item in values]
        elif isinstance(result, list):
            items = result
        else:
            continue
        for item in items:
            assert facts <= set(item), f'{name} returned an object without the four facts: {item}'
            checked += 1
    assert checked > 40, f'only {checked} objects checked: the fixture does not exercise the rule'


def test_parser_finds_device_level_routers(make_parser):
    """A router under devices/entry/<device>/network is parsed (F3.5).

    The old code walked <templates> and only the vsys-nested device shape,
    so it dropped every router a firewall's own config export declares at
    device level.
    """
    parser = make_parser('virtual_routers.xml')
    routers = {r['name']: r for r in parser.parse_virtual_routers()}
    assert {'default', 'vr-dmz', 'vr-device', 'vr-vsys2'} <= set(routers)
    assert (routers['vr-device']['vsys'], routers['vr-device']['vsys_device'],
            routers['vr-device']['template']) == ('', 'fw-1.example.com', '')
    assert (routers['vr-vsys2']['vsys'], routers['vr-vsys2']['vsys_device']) == \
        ('vsys2', 'fw-1.example.com')


# --- emitter: location choice ---------------------------------------------

@pytest.mark.parametrize('resource_type,obj,expected', [
    # A declared vsys with a real device name.
    ('panos_address', {'name': 'a', 'device_group': 'Shared', 'vsys': 'vsys2',
                       'vsys_device': 'fw-2.example.com'},
     {'vsys': {'name': 'vsys2', 'ngfw_device': 'fw-2.example.com'}}),
    # The shared section is `shared = {}`, not a device group named Shared.
    ('panos_address', {'name': 'a', 'device_group': 'Shared'}, {'shared': {}}),
    # A device group is a device group.
    ('panos_address', {'name': 'a', 'device_group': 'Production-DG'},
     {'device_group': {'name': 'Production-DG'}}),
    # A declared template wins over the device group.
    ('panos_zone', {'name': 'z', 'device_group': 'Shared',
                    'template': 'FW-Template'},
     {'template': {'name': 'FW-Template'}}),
    # A template and a vsys both reach the template block when it declares
    # the vsys field.
    ('panos_zone', {'name': 'z', 'template': 'FW-Template', 'vsys': 'vsys3'},
     {'template': {'name': 'FW-Template', 'vsys': 'vsys3'}}),
    # A template-scoped type with no declared scope keeps the placeholder.
    ('panos_virtual_router', {'name': 'vr', 'device_group': 'Shared'},
     {'template': {'name': 'Shared'}}),
    # An object with no declared vsys falls back to its device group.
    ('panos_service', {'name': 's', 'device_group': 'Dev-DG'},
     {'device_group': {'name': 'Dev-DG'}}),
    # A rule follows the same rule as an object.
    ('panos_security_policy_rules', {'name': 'r', 'device_group': 'Dev-DG'},
     {'device_group': {'name': 'Dev-DG'}}),
])
def test_location_choice(gen, resource_type, obj, expected):
    """The emitted location sub-block matches the source identity."""
    assert _location(gen.location_block(resource_type, obj)) == expected


def test_shared_is_not_a_device_group(gen):
    """A shared object never emits `device_group = { name = "Shared" }`."""
    text = gen.location_block('panos_address',
                              {'name': 'a', 'device_group': 'Shared'})
    assert 'device_group' not in text
    assert 'shared = {}' in text


def test_no_sub_block_outside_the_schema(gen):
    """No emitted location names a sub-block or field the schema lacks."""
    cases = [
        # A vsys on a type with no vsys sub-block must not appear.
        ('panos_security_profile_group',
         {'name': 'g', 'device_group': 'Shared', 'vsys': 'vsys2',
          'vsys_device': 'fw-1.example.com'}),
        # A template on a type with no template sub-block must not appear.
        ('panos_address', {'name': 'a', 'template': 'FW-Template'}),
        # A vsys field the type's template block does not declare.
        ('panos_vlan_interface', {'name': 'vlan.10', 'template': 'FW-Template',
                                  'vsys': 'vsys2'}),
    ]
    for resource_type, obj in cases:
        scopes = _location(gen.location_block(resource_type, obj))
        assert set(scopes) <= set(LOCATION_SCHEMA[resource_type]), scopes
        for scope, fields in scopes.items():
            assert set(fields) <= set(LOCATION_SCHEMA[resource_type][scope]), \
                scopes


def test_placeholder_template_for_unscoped_template_type(gen):
    """A template-scoped resource with no declared template keeps the marker.

    'Shared' is a placeholder name, not a template the export named. F3.6
    resolves the template where the export states one (a declared template,
    else location.ngfw for a named device); what is left over is reported,
    because the placeholder is not a template an operator can apply to.
    """
    text = gen.location_block('panos_monitor_profile',
                              {'name': 'PM', 'device_group': 'Shared'})
    assert _location(text) == {'template': {'name': 'Shared'}}


# --- emitter: reports -----------------------------------------------------

def _report(gen) -> str:
    """Write the manual setup report and return its text."""
    gen.generate_manual_setup_report({}, [], [], [])
    return (gen.output_dir / 'MANUAL_SETUP_REPORT.txt').read_text()


def test_report_lists_a_dropped_vsys(gen):
    """A vsys the type cannot carry is reported, not dropped silently."""
    gen.location_block('panos_security_profile_group',
                       {'name': 'Strict', 'device_group': 'Shared',
                        'vsys': 'vsys2', 'vsys_device': 'fw-1.example.com'})
    report = _report(gen)
    assert 'Locations The Provider Cannot Carry' in report
    line = next(line for line in report.split('\n')
                if 'panos_security_profile_group' in line)
    assert 'vsys2' in line and 'fw-1.example.com' in line
    assert 'no location.vsys sub-block' in line


def test_report_lists_a_dropped_template(gen):
    """A template on a device-group-only type is reported."""
    gen.location_block('panos_address', {'name': 'a', 'template': 'FW-Template'})
    line = next(line for line in _report(gen).split('\n')
                if 'panos_address "a"' in line)
    assert 'FW-Template' in line
    assert 'no location.template sub-block' in line


def test_report_lists_a_missing_target_device(gen):
    """A vsys location with no usable device name is reported.

    A firewall's own export names its device 'localhost.localdomain', the
    PAN-OS placeholder for "this device", which is not a value an operator
    can put in ngfw_device.
    """
    text = gen.location_block('panos_zone', {'name': 'trust', 'vsys': 'vsys1',
                                             'vsys_device': 'localhost.localdomain'})
    assert 'ngfw_device' not in text
    report = _report(gen)
    assert 'Virtual System Locations Without A Target Device' in report
    assert 'panos_zone "trust"' in report
    assert 'localhost.localdomain' in report


def test_report_is_absent_when_every_location_is_placeable(gen):
    """No report file appears when every location carries its source scope."""
    gen.location_block('panos_address', {'name': 'a', 'device_group': 'Shared'})
    gen.location_block('panos_zone', {'name': 'z', 'vsys': 'vsys1',
                                      'vsys_device': 'fw-1.example.com'})
    gen.generate_manual_setup_report({}, [], [], [])
    assert not (gen.output_dir / 'MANUAL_SETUP_REPORT.txt').exists()


# --- emitter: two virtual systems, two resources ---------------------------

def test_interface_reference_stays_inside_its_device(tmp_path):
    """A zone never references another device's interface resource (F3.5).

    Interfaces are device-level config and two firewalls declare the same
    interface names. A zone whose export names a device resolves inside that
    device, and stays a plain interface name when that device declares no
    such interface.
    """
    gen = TerraformGenerator(str(tmp_path))
    gen.generate_interfaces([
        {'name': 'ethernet1/1', 'type': 'ethernet', 'mode': 'layer3',
         'device_group': 'Shared', 'vsys': '', 'template': '',
         'vsys_device': 'fw-1.example.com'},
    ])
    gen.generate_zones([
        {'name': 'home', 'device_group': 'Shared', 'vsys': 'vsys1',
         'vsys_device': 'fw-1.example.com', 'type': 'layer3',
         'interfaces': ['ethernet1/1']},
        {'name': 'other', 'device_group': 'Shared', 'vsys': 'vsys1',
         'vsys_device': 'fw-2.example.com', 'type': 'layer3',
         'interfaces': ['ethernet1/1']},
    ])
    zones = _resources((tmp_path / 'zones.tf').read_text())
    blocks = {name: next(b for b in zones.values() if f'name = "{name}"' in b)
              for name in ('home', 'other')}
    assert 'panos_ethernet_interface.' in blocks['home']
    assert 'panos_ethernet_interface.' not in blocks['other']
    assert '"ethernet1/1"' in blocks['other']


def test_virtual_router_reference_stays_inside_its_device(tmp_path):
    """A contextless referrer on another device borrows no interface (F3.5).

    A virtual router resolves with no context and no vsys, so the context
    chain alone lands on whichever device declared the name first. The
    device rule is checked first, so a router on the second firewall keeps a
    plain interface name.
    """
    gen = TerraformGenerator(str(tmp_path))
    gen.generate_interfaces([
        {'name': 'ethernet1/1', 'type': 'ethernet', 'mode': 'layer3',
         'device_group': 'Shared', 'vsys': '', 'template': '',
         'vsys_device': 'fw-1.example.com'},
    ])
    gen.generate_virtual_routers([
        {'name': 'vr-home', 'type': 'virtual-router', 'vsys': '', 'template': '',
         'vsys_device': 'fw-1.example.com', 'interfaces': ['ethernet1/1']},
        {'name': 'vr-other', 'type': 'virtual-router', 'vsys': '', 'template': '',
         'vsys_device': 'fw-2.example.com', 'interfaces': ['ethernet1/1']},
    ])
    routers = _resources((tmp_path / 'virtual_routers.tf').read_text())
    blocks = {name: next(b for b in routers.values() if f'name = "{name}"' in b)
              for name in ('vr-home', 'vr-other')}
    assert 'panos_ethernet_interface.' in blocks['vr-home']
    assert 'panos_ethernet_interface.' not in blocks['vr-other']
    assert '"ethernet1/1"' in blocks['vr-other']

def test_same_name_in_two_vsys_emits_two_resources(tmp_path):
    """A name that repeats in two vsys produces two resources and two digests."""
    gen = TerraformGenerator(str(tmp_path))
    gen.generate_address_objects([
        {'name': 'Web', 'value': '10.0.0.1/32', 'device_group': 'Shared',
         'vsys': 'vsys1', 'vsys_device': 'fw-2.example.com'},
        {'name': 'Web', 'value': '10.0.0.2/32', 'device_group': 'Shared',
         'vsys': 'vsys2', 'vsys_device': 'fw-2.example.com'},
    ])
    blocks = _resources((tmp_path / 'address_objects.tf').read_text())
    assert len(blocks) == 2
    names = [header.split('"')[3] for header in blocks]
    assert len(set(names)) == 2, names
    locations = [_location(block) for block in blocks.values()]
    assert {'vsys': {'name': 'vsys1', 'ngfw_device': 'fw-2.example.com'}} in locations
    assert {'vsys': {'name': 'vsys2', 'ngfw_device': 'fw-2.example.com'}} in locations


def test_same_name_in_two_vsys_references_resolve_per_vsys(tmp_path):
    """A group in vsys2 references the vsys2 member, not the vsys1 one."""
    gen = TerraformGenerator(str(tmp_path))
    gen.generate_address_objects([
        {'name': 'Web', 'value': '10.0.0.1/32', 'device_group': 'Shared',
         'vsys': 'vsys1', 'vsys_device': 'fw-2.example.com'},
        {'name': 'Web', 'value': '10.0.0.2/32', 'device_group': 'Shared',
         'vsys': 'vsys2', 'vsys_device': 'fw-2.example.com'},
    ])
    blocks = _resources((tmp_path / 'address_objects.tf').read_text())
    # Read each copy's local name back from its own location block, so the
    # assertion follows the emitted output instead of re-deriving digests.
    local_by_vsys = {}
    for header, block in blocks.items():
        local_by_vsys[_location(block)['vsys']['name']] = header.split('"')[3]
    assert local_by_vsys['vsys1'] != local_by_vsys['vsys2']

    gen.generate_address_groups([
        {'name': 'Group', 'static_members': ['Web'], 'device_group': 'Shared',
         'vsys': 'vsys2', 'vsys_device': 'fw-2.example.com'},
    ])
    groups = (tmp_path / 'address_groups.tf').read_text()
    assert f"panos_address.{local_by_vsys['vsys2']}.name" in groups
    assert local_by_vsys['vsys1'] not in groups
