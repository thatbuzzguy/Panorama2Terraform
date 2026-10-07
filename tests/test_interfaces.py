"""F3.3: every interface kind emits its schema-verified resource type.

The provider has no virtual-wire resource type: virtual-wire and tap entries
are nested blocks on panos_ethernet_interface. Subinterface resources carry a
parent reference to the physical interface or aggregate group declared in the
same run.
"""

import re

from conftest import FIXTURES_DIR, RESOURCE_RE, run_script


def _generate(fixture: str, tmp_path) -> str:
    proc = run_script('panorama_to_terraform.py',
                      str(FIXTURES_DIR / fixture), '--output-dir', str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    return (tmp_path / 'interfaces.tf').read_text()


def _blocks(text: str) -> dict[str, str]:
    """Resource bodies keyed by the resource `name` attribute."""
    out = {}
    for block in re.findall(r'resource "[a-z0-9_]+" "[^"]+" \{\n(.*?)\n\}', text, re.S):
        # The resource name attribute sits at two-space indent; the location
        # block also contains an indented `name`, so anchor on the indent.
        m = re.search(r'^  name = "([^"]+)"', block, re.M)
        if m:
            out[m.group(1)] = block
    return out


def test_every_kind_emits_its_resource_type(tmp_path):
    """Each parsed kind emits the provider resource type for that kind."""
    text = _generate('interfaces_other.xml', tmp_path)
    types = {m.group(1) for m in RESOURCE_RE.finditer(text)}
    assert types == {
        'panos_vlan_interface',
        'panos_loopback_interface',
        'panos_tunnel_interface',
        'panos_aggregate_interface',
        'panos_aggregate_layer3_subinterface',
    }


def test_ethernet_subinterface_unit_emits_with_parent_reference(tmp_path):
    """A units/entry becomes its own resource with a reference to the parent."""
    text = _generate('interfaces_ethernet.xml', tmp_path)
    blocks = _blocks(text)

    parent_block = blocks['ethernet1/1']
    parent_local = re.search(r'resource "panos_ethernet_interface" "([^"]+)"', text).group(1)
    sub = blocks['ethernet1/1.10']
    assert f'parent = panos_ethernet_interface.{parent_local}.name' in sub
    assert 'tag = 10' in sub
    assert 'name = "ethernet1/1.10"' in sub
    assert parent_block  # the physical entry is still emitted


def test_subinterface_parents_resolve_to_declared_resources(tmp_path):
    """No subinterface keeps a plain string parent when the parent is in the run."""
    text = _generate('interfaces_other.xml', tmp_path)
    blocks = _blocks(text)

    ae_group_local = re.search(r'resource "panos_aggregate_interface" "([^"]+)"', text).group(1)
    ae_sub_local = re.search(
        r'resource "panos_aggregate_layer3_subinterface" "([^"]+)"', text).group(1)
    assert f'parent = panos_aggregate_interface.{ae_group_local}.name' in blocks['ae1.101']
    assert f'parent = panos_aggregate_layer3_subinterface.{ae_sub_local}.name' in blocks['ae1.101.20']


def test_aggregate_group_has_no_parent_or_tag(tmp_path):
    """The aggregate group resource has neither parent nor tag in the schema."""
    blocks = _blocks(_generate('interfaces_other.xml', tmp_path))
    group = blocks['ae1']
    assert 'parent' not in group
    assert 'tag' not in group
    assert 'layer2 = {}' in group


def test_virtual_wire_and_tap_emit_as_blocks(tmp_path):
    """Virtual-wire and tap are nested blocks, not separate resource types."""
    text = _generate('interfaces_ethernet.xml', tmp_path)
    blocks = _blocks(text)
    assert 'virtual_wire = {}' in blocks['ethernet1/3']
    assert 'virtual_wire = {}' in blocks['ethernet1/4.1']
    assert 'tap = {}' in blocks['ethernet1/5']
    # F3.3 criterion 4: no manual-review note for a modeled mode.
    assert 'requires manual review' not in text


def test_ip_list_is_emitted_for_every_kind(tmp_path):
    """Regression: the ip attribute was dropped because the helper mutated a str."""
    blocks = _blocks(_generate('interfaces_other.xml', tmp_path))
    for name in ('vlan.10', 'loopback.1', 'tunnel.1', 'ae1.101', 'ae1.101.20'):
        assert 'ip = [' in blocks[name], name


def test_interfaces_are_template_scoped(tmp_path):
    """The provider scopes interface resources to a template, not a device group."""
    text = _generate('interfaces_other.xml', tmp_path)
    assert 'device_group' not in text
    assert 'template = {' in text
