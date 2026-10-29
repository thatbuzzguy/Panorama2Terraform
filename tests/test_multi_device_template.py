"""F3.6: multi-device, template-aware parsing.

A Panorama export states the multi-device relationships in data:

    device-group/entry/<DG>/devices/entry/<device>
    templates/entry/<template>/devices/entry/<device>
    template-stack/entry/<stack>/devices/entry/<device>
    template-stack/entry/<stack>/templates/member/<template>

Four contracts:

1. The parser reads those lists and nothing else: no `DG-` prefix
   convention, no substring match, no name that "looks like" a template.
2. Config a firewall owns (an entry under `devices/entry/<device>`) is
   placed with `location.ngfw`, not with a guessed template name.
3. The naming context of a template-scoped object is its template, else its
   device, so the same name on two firewalls or in two templates stays two
   resources.
4. The splitter joins a device group and a template on a shared device name.
"""

import xml.etree.ElementTree as ET

import pytest

import naming
from conftest import FIXTURES_DIR
from panorama_to_terraform import TerraformGenerator

# The association tables PanoramaParser.parse_associations builds for
# tests/fixtures/multi_device_templates.xml, written out so an emitter test
# can name a scope without re-reading the XML.
ASSOCIATIONS = {
    'device_groups': {'fw-1.example.com': ['Office-FW'],
                      'fw-2.example.com': ['Datacenter-FW']},
    'templates': {'fw-1.example.com': ['HQ-Networks'],
                  'fw-2.example.com': ['DC-Networks']},
    'template_stacks': {'fw-3.example.com': ['Branch-Stack']},
    'stack_templates': {'Branch-Stack': ['HQ-Networks']},
}

FW1 = 'fw-1.example.com'
FW2 = 'fw-2.example.com'


def _fixture_root(name: str) -> ET.Element:
    return ET.parse(str(FIXTURES_DIR / name)).getroot()


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


def _location(text: str) -> dict:
    """Return the emitted location as {scope: {field: value}}."""
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


@pytest.fixture
def gen(tmp_path):
    """A generator that knows the fixture's device associations."""
    return TerraformGenerator(str(tmp_path), ASSOCIATIONS)


@pytest.fixture
def bare_gen(tmp_path):
    """A generator with no association tables (a single-firewall export)."""
    return TerraformGenerator(str(tmp_path))


# --- parser: the association the export declares ---------------------------

def test_parser_reads_the_declared_membership(make_parser):
    """Device groups, templates and stacks are joined to devices by name."""
    tables = make_parser('multi_device_templates.xml').parse_associations()
    assert tables['device_groups'] == {FW1: ['Office-FW'], FW2: ['Datacenter-FW']}
    assert tables['templates'] == {FW1: ['HQ-Networks'], FW2: ['DC-Networks']}
    assert tables['template_stacks'] == {'fw-3.example.com': ['Branch-Stack']}
    assert tables['stack_templates'] == {'Branch-Stack': ['HQ-Networks']}


def test_templates_for_device_follows_the_stack(make_parser):
    """A device takes a template directly or through a template stack."""
    parser = make_parser('multi_device_templates.xml')
    assert parser.templates_for_device(FW1) == ['HQ-Networks']
    assert parser.templates_for_device(FW2) == ['DC-Networks']
    # fw-3 is named only by the stack, and the stack names the template.
    assert parser.templates_for_device('fw-3.example.com') == ['HQ-Networks']
    assert parser.templates_for_device('fw-9.example.com') == []
    assert parser.templates_for_device('') == []


def test_association_is_empty_when_the_export_lists_no_devices(make_parser):
    """No device list means no association, never a guessed one.

    A firewall's own export has no device-group or template membership at
    all; inventing one would place resources in a template that does not
    exist.
    """
    parser = make_parser('virtual_routers.xml')
    tables = parser.parse_associations()
    assert tables == {'device_groups': {}, 'templates': {},
                      'template_stacks': {}, 'stack_templates': {}}
    assert parser.templates_for_device(FW1) == []


def test_association_names_are_sorted(make_parser):
    """The tables do not depend on document order."""
    tables = make_parser('multi_device_templates.xml').parse_associations()
    for table in tables.values():
        for names in table.values():
            assert names == sorted(names)


# --- emitter: device-specific placement ------------------------------------

def test_device_specific_config_uses_ngfw(bare_gen):
    """An entry under devices/entry/<device> is that device's own config.

    The old emitter had no ngfw branch, so it wrote the "Shared" template
    placeholder, which names a template no Panorama has. The device name prints
    as `VALUE_VARIABLES` says, so the block states the variable name (F6.6).
    """
    text = bare_gen.location_block('panos_virtual_router',
                                   {'name': 'vr', 'vsys_device': FW1})
    assert _location(text) == {'ngfw': {'ngfw_device': naming.variable_text(FW1)}}


def test_object_types_never_emit_ngfw(bare_gen):
    """An object lives in a virtual system or a device group, never ngfw.

    panos_address declares no location.ngfw (v2.0.14), so an address the
    export places on a device with no vsys falls back to its real location
    instead of a sub-block the provider would reject at apply.
    """
    text = bare_gen.location_block('panos_address',
                                   {'name': 'a', 'device_group': 'Shared',
                                    'vsys_device': FW1})
    assert 'ngfw' not in text
    assert _location(text) == {'shared': {}}


def test_placeholder_device_never_becomes_ngfw(bare_gen):
    """localhost.localdomain names no firewall, so it is never ngfw_device.

    F6.6: a value that reaches no location names no variable, so the placeholder cannot enter the
    value-to-variable mapping.
    """
    text = bare_gen.location_block('panos_ethernet_interface',
                                   {'name': 'ethernet1/1',
                                    'vsys_device': 'localhost.localdomain'})
    assert 'localhost' not in text
    assert 'var.' not in text, 'the placeholder names no device, so it names no variable'
    assert _location(text) == {'template': {'name': 'Shared'}}


def test_template_override_inside_a_template_names_the_device(bare_gen):
    """A device entry inside a template is that device's config (F3.6).

    location.template declares ngfw_device next to name, which is how the
    provider spells a per-device override of a template.
    """
    text = bare_gen.location_block('panos_zone',
                                   {'name': 'trust', 'template': 'HQ-Networks',
                                    'vsys_device': FW1})
    assert _location(text) == {'template': {'name': 'HQ-Networks',
                                            'ngfw_device': naming.variable_text(FW1)}}


def test_zone_with_a_device_and_no_vsys_is_reported(gen):
    """A zone on a device with no template is reported with the real name.

    panos_zone has no location.ngfw (a zone always lives in a virtual
    system), so the converter cannot place it and says which template the
    device takes instead of staying silent.
    """
    text = gen.location_block('panos_zone', {'name': 'trust',
                                             'vsys_device': FW2})
    assert _location(text) == {'template': {'name': 'Shared'}}
    gen.generate_manual_setup_report({}, [], [], [])
    report = (gen.output_dir / 'MANUAL_SETUP_REPORT.txt').read_text()
    assert 'Template Locations The Export Does Not Name' in report
    line = next(line for line in report.split('\n') if 'panos_zone "trust"' in line)
    assert 'DC-Networks' in line


def test_placeholder_report_without_a_device(bare_gen):
    """The report still explains a placeholder with no device to name."""
    bare_gen.location_block('panos_monitor_profile', {'name': 'PM'})
    bare_gen.generate_manual_setup_report({}, [], [], [])
    report = (bare_gen.output_dir / 'MANUAL_SETUP_REPORT.txt').read_text()
    line = next(line for line in report.split('\n')
                if 'panos_monitor_profile "PM"' in line)
    assert 'the export names no device for this entry' in line


def test_placeholder_report_names_the_localhost_placeholder(bare_gen):
    """A placeholder on `localhost.localdomain` says no firewall is named.

    A firewall's own export puts its config under `localhost.localdomain`,
    which names no device (F3.5), so the report must not read as if a device
    existed and took no template.
    """
    bare_gen.location_block('panos_monitor_profile',
                            {'name': 'PM', 'vsys_device': 'localhost.localdomain'})
    bare_gen.generate_manual_setup_report({}, [], [], [])
    report = (bare_gen.output_dir / 'MANUAL_SETUP_REPORT.txt').read_text()
    line = next(line for line in report.split('\n')
                if 'panos_monitor_profile "PM"' in line)
    assert 'the PAN-OS "this device" placeholder' in line


# --- emitter: two devices, two resources -----------------------------------

def test_same_interface_name_on_two_devices(tmp_path):
    """Two firewalls declaring ethernet1/1 get two digests and two locations.

    Before F3.6 the digest context was empty for a device-specific object,
    so the second resource differed from the first only by the taken-name
    counter and both carried the same location.
    """
    gen = TerraformGenerator(str(tmp_path), ASSOCIATIONS)
    gen.generate_interfaces([
        {'name': 'ethernet1/1', 'type': 'ethernet', 'mode': 'layer3',
         'device_group': 'Shared', 'vsys': '', 'template': '',
         'vsys_device': FW1},
        {'name': 'ethernet1/1', 'type': 'ethernet', 'mode': 'layer3',
         'device_group': 'Shared', 'vsys': '', 'template': '',
         'vsys_device': FW2},
    ])
    blocks = _resources((tmp_path / 'interfaces.tf').read_text())
    assert len(blocks) == 2
    locals_ = [header.split('"')[3] for header in blocks]
    assert len(set(locals_)) == 2, locals_
    locations = [_location(block) for block in blocks.values()]
    assert {'ngfw': {'ngfw_device': naming.variable_text(FW1)}} in locations
    assert {'ngfw': {'ngfw_device': naming.variable_text(FW2)}} in locations


def test_reference_resolves_inside_the_template_target_device(tmp_path):
    """A template that targets one device resolves its interface names there.

    The virtual router is template config and names no device, but the
    export says which device the template targets, so the interface name has
    exactly one referent.
    """
    gen = TerraformGenerator(str(tmp_path), ASSOCIATIONS)
    gen.generate_interfaces([
        {'name': 'ethernet1/1', 'type': 'ethernet', 'mode': 'layer3',
         'device_group': 'Shared', 'vsys': '', 'template': '',
         'vsys_device': FW2},
    ])
    gen.generate_virtual_routers([
        {'name': 'vr-hq', 'type': 'virtual-router', 'vsys': '',
         'template': 'DC-Networks', 'vsys_device': '',
         'interfaces': ['ethernet1/1']},
    ])
    routers = (tmp_path / 'virtual_routers.tf').read_text()
    assert 'panos_ethernet_interface.ethernet1_1_' in routers


def test_ambiguous_template_keeps_a_plain_interface_name(tmp_path):
    """A name two devices declare is not resolved by a deviceless referrer.

    The export cannot say which firewall the referrer means, so guessing the
    first declaration would point a resource at another firewall's interface.
    """
    gen = TerraformGenerator(str(tmp_path))
    gen.generate_interfaces([
        {'name': 'ethernet1/1', 'type': 'ethernet', 'mode': 'layer3',
         'device_group': 'Shared', 'vsys': '', 'template': '',
         'vsys_device': FW1},
        {'name': 'ethernet1/1', 'type': 'ethernet', 'mode': 'layer3',
         'device_group': 'Shared', 'vsys': '', 'template': '',
         'vsys_device': FW2},
    ])
    gen.generate_virtual_routers([
        {'name': 'vr-shared', 'type': 'virtual-router', 'vsys': '',
         'template': '', 'vsys_device': '', 'interfaces': ['ethernet1/1']},
    ])
    routers = (tmp_path / 'virtual_routers.tf').read_text()
    assert 'panos_ethernet_interface.' not in routers
    assert '"ethernet1/1"' in routers


def test_single_device_declaration_still_resolves_without_a_device(tmp_path):
    """One device declaring the name is a fact, so the reference resolves."""
    gen = TerraformGenerator(str(tmp_path))
    gen.generate_interfaces([
        {'name': 'ethernet1/1', 'type': 'ethernet', 'mode': 'layer3',
         'device_group': 'Shared', 'vsys': '', 'template': '',
         'vsys_device': FW1},
    ])
    gen.generate_virtual_routers([
        {'name': 'vr-any', 'type': 'virtual-router', 'vsys': '',
         'template': '', 'vsys_device': '', 'interfaces': ['ethernet1/1']},
    ])
    routers = (tmp_path / 'virtual_routers.tf').read_text()
    assert 'panos_ethernet_interface.ethernet1_1_' in routers


# --- the fixture as a whole ------------------------------------------------

def test_multi_device_fixture_places_everything_it_can(tmp_path, make_parser):
    """The two-device fixture emits no placeholder and reports nothing."""
    parser = make_parser('multi_device_templates.xml')
    out = tmp_path / 'out'
    gen = TerraformGenerator(str(out), parser.parse_associations())
    gen.generate_interfaces(parser.parse_interfaces())
    gen.generate_virtual_routers(parser.parse_virtual_routers())
    assert not (out / 'MANUAL_SETUP_REPORT.txt').exists()
    routers = (out / 'virtual_routers.tf').read_text()
    assert 'name = "HQ-Networks"' in routers
    assert 'name = "DC-Networks"' in routers
    interfaces = (out / 'interfaces.tf').read_text()
    assert f'ngfw_device = {naming.variable_text(FW1)}' in interfaces
    assert f'ngfw_device = {naming.variable_text(FW2)}' in interfaces


# --- splitter: the association replaces the name convention ----------------

def test_splitter_joins_template_and_device_group_by_device(splitter_module):
    """Unrelated names still associate, because the join is the device.

    Office-FW and HQ-Networks share only the device fw-1.example.com. The
    old code stripped a 'DG-' prefix and then tested whether the device group
    name appeared inside the template name, so it copied nothing here.
    """
    root = _fixture_root('multi_device_templates.xml')
    extracted = splitter_module.extract_device_group_config(root, 'Office-FW')
    templates = extracted.findall('.//templates/entry')
    assert [t.get('name') for t in templates] == ['HQ-Networks']


def test_splitter_copies_the_template_stack_by_device(splitter_module):
    """A stack belongs to the device group that holds one of its devices."""
    root = _fixture_root('multi_device_templates.xml')
    extracted = splitter_module.extract_device_group_config(root, 'Office-FW')
    assert extracted.findall('.//template-stack/entry') == []

    root = _fixture_root('multi_device_templates.xml')
    tables = splitter_module.device_associations(root)
    assert tables['template_stacks']['Branch-Stack']['devices'] == \
        {'fw-3.example.com'}


def test_splitter_copies_no_template_without_a_shared_device(splitter_module):
    """A device group whose devices no template targets copies none."""
    root = _fixture_root('multi_device_templates.xml')
    extracted = splitter_module.extract_device_group_config(root, 'Datacenter-FW')
    # DC-Networks does target fw-2, so it is copied; Unassigned-DG is not.
    assert [t.get('name') for t in extracted.findall('.//templates/entry')] == \
        ['DC-Networks']

    root = _fixture_root('multi_device_templates.xml')
    extracted = splitter_module.extract_device_group_config(root, 'Unassigned-DG')
    assert extracted.findall('.//templates/entry') == []
    assert extracted.findall('.//template-stack/entry') == []


def _entry_shapes(root: ET.Element) -> list:
    """Return a sorted (tag, name) list of every entry under `root`."""
    return sorted((e.tag, e.get('name') or '') for e in root.iter('entry'))


def test_splitter_leaves_the_source_tree_intact(splitter_module):
    """Extracting a device group must not change the export it read.

    ElementTree keeps no parent bookkeeping, so `append` makes one element
    object a child of two trees, and the shared-section merge adds entries.
    Both mutate what the next extraction reads, so the splitter copies with
    `copy.deepcopy` and the export keeps its own entries.
    """
    root = _fixture_root('multi_device_templates.xml')
    before = _entry_shapes(root)
    splitter_module.extract_device_group_config(root, 'Office-FW')
    splitter_module.extract_device_group_config(root, 'Datacenter-FW')
    assert _entry_shapes(root) == before


def test_splitter_merges_shared_sections_without_touching_the_source(splitter_module):
    """Two shared sections merge into every split file, source unchanged.

    The merge appends the second section's entries into the first section's
    element. Without a copy that append lands in the source tree, so the
    export grows an entry per device group.
    """
    root = ET.fromstring(
        '<config>'
        '<devices><entry name="localhost.localdomain"><device-group>'
        '<entry name="DG-A"/><entry name="DG-B"/>'
        '</device-group></entry></devices>'
        '<shared><address><entry name="a1"/></address></shared>'
        '<shared><address><entry name="a2"/></address></shared>'
        '</config>'
    )
    for device_group in ('DG-A', 'DG-B'):
        extracted = splitter_module.extract_device_group_config(root, device_group)
        names = [e.get('name') for e in extracted.findall('.//shared//entry')]
        assert names == ['a1', 'a2'], device_group
    assert [e.get('name') for e in root.findall('.//shared//entry')] == ['a1', 'a2']
