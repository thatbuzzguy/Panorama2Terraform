"""Edge-case fixture tests (F1.6 corpus).

Pins parser behavior for edge cases:

- duplicate names across device groups or vsys: F3.1 keys objects by
  (device group, vsys, type, name), so all definitions survive.
- IPv6 address objects: parsed from the <ipv6> element (F2.4).
- multi-port / dual-protocol services: current behavior pinned; the udp
  drop is recorded in backlog.md.
- F3.2 emit-side vsys identity: same-named objects in two vsys emit as
  distinct digest-named resources, the identity-to-name assignment is
  stable under entry-order flips, references resolve in the referrer's
  own vsys, and rule chains never cross a vsys boundary.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from conftest import FIXTURES_DIR, run_script


def _fixture(name: str):
    """Parse a fixture file and return its root element."""
    return ET.parse(str(FIXTURES_DIR / name)).getroot()


# --- 1. Quoted device-group names (splitter) --------------------------------

def test_splitter_finds_dg_with_single_quote_in_name(splitter_module):
    """A DG name with a single quote must resolve (no f-string XPath)."""
    root = _fixture("edge_quoted_dg_names.xml")
    extracted = splitter_module.extract_device_group_config(root, "DG-It's Here")
    assert extracted is not None


def test_splitter_finds_dg_with_double_quote_in_name(splitter_module):
    """A DG name with double quotes must resolve too."""
    root = _fixture("edge_quoted_dg_names.xml")
    extracted = splitter_module.extract_device_group_config(root, 'DG-"East" Prod')
    assert extracted is not None


def test_quoted_dg_objects_parse(make_parser):
    """Objects under quoted-named DGs parse regardless of name quoting."""
    parser = make_parser("edge_quoted_dg_names.xml")
    names = sorted(a["name"] for a in parser.parse_address_objects())
    assert names == ["dg-double-quote-host", "dg-single-quote-host"]


# --- 2. Duplicate names across device groups --------------------------------

def test_dup_names_across_dgs_both_survive(make_parser):
    """Same-named objects in different DGs both survive (F3.1 keyed identity).

    Each object carries its identity fields: the defining device group and
    the vsys. The key is (device group, vsys, type, name).
    """
    parser = make_parser("edge_dup_names_across_dgs.xml")
    objects = parser.parse_address_objects()
    assert len(objects) == 2
    by_group = {a["device_group"]: a for a in objects}
    assert set(by_group) == {"DG-A", "DG-B"}
    assert by_group["DG-A"]["value"] == "10.0.0.1/32"
    assert by_group["DG-B"]["value"] == "10.0.0.2/32"
    assert all(a["vsys"] == "vsys1" for a in objects)
    assert all(a["name"] == "web" for a in objects)


def test_dup_names_across_vsys_both_survive(make_parser):
    """Same-named objects in different vsys both survive (F3.1 keyed identity)."""
    parser = make_parser("edge_dup_names_across_vsys.xml")
    objects = parser.parse_address_objects()
    assert len(objects) == 2
    by_vsys = {a["vsys"]: a for a in objects}
    assert set(by_vsys) == {"vsys1", "vsys2"}
    assert by_vsys["vsys1"]["value"] == "10.1.0.1/32"
    assert by_vsys["vsys2"]["value"] == "10.2.0.1/32"


# --- 3. Multi-vsys -----------------------------------------------------------

def test_multi_vsys_objects_both_parse(make_parser):
    """Objects under different vsys must all be parsed, tagged with their vsys."""
    parser = make_parser("edge_multi_vsys.xml")
    objects = {a["name"]: a for a in parser.parse_address_objects()}
    assert objects["host-vs1"]["value"] == "10.9.1.10/32"
    assert objects["host-vs2"]["value"] == "10.9.2.10/32"
    assert objects["host-vs1"]["vsys"] == "vsys1"
    assert objects["host-vs2"]["vsys"] == "vsys2"


# --- 4. Mixed virtual and logical routers ------------------------------------

def test_mixed_vr_lr_both_routers_parse(make_parser):
    """A template VR and a vsys LR must both be parsed."""
    parser = make_parser("edge_mixed_vr_lr.xml")
    names = sorted(r["name"] for r in parser.parse_virtual_routers() + parser.parse_logical_routers())
    assert names == ["LR-EDGE", "VR-MAIN"]


def test_mixed_vr_lr_routes_attributed(make_parser):
    """Routes keep their nexthop kind (next-vip vs next-vr) per router."""
    parser = make_parser("edge_mixed_vr_lr.xml")
    routers = {r["name"]: r for r in parser.parse_virtual_routers() + parser.parse_logical_routers()}

    vr_routes = {r["name"]: r for r in routers["VR-MAIN"]["static_routes"]}
    assert len(vr_routes) == 2
    assert vr_routes["to-lr"]["nexthop_interface"] == "LR-EDGE"
    assert vr_routes["default-gw"]["nexthop_ip"] == "192.168.1.254"

    lr_routes = {r["name"]: r for r in routers["LR-EDGE"]["static_routes"]}
    assert len(lr_routes) == 1
    assert lr_routes["to-internet"]["nexthop_ip"] == "10.0.0.254"


# --- 5. IPv6 ------------------------------------------------------------------

def test_ipv4_object_still_parses(make_parser):
    """The IPv4 object in the same config must parse normally."""
    parser = make_parser("edge_ipv6.xml")
    objects = {a["name"]: a for a in parser.parse_address_objects()}
    assert objects["v4-host"]["value"] == "192.168.1.10/32"


def test_ipv6_object_keeps_value(make_parser):
    """Desired behavior: IPv6 objects keep their address value."""
    parser = make_parser("edge_ipv6.xml")
    objects = {a["name"]: a for a in parser.parse_address_objects()}
    assert objects["v6-host"].get("value") == "2001:db8::10/128"
    assert objects["v6-range"].get("value") == "2001:db8::/48"


# --- 6. Multi-port and dual-protocol services ---------------------------------

def test_multi_port_service_port_list_passes_through(make_parser):
    """Current behavior: a tcp port list is kept as-is."""
    parser = make_parser("edge_multi_port_services.xml")
    services = {s["name"]: s for s in parser.parse_service_objects()}
    assert services["svc-multi-port"]["port"] == "80,443"


def test_dual_protocol_service_keeps_tcp(make_parser):
    """Current behavior: tcp wins; the udp definition is dropped (backlog)."""
    parser = make_parser("edge_multi_port_services.xml")
    services = {s["name"]: s for s in parser.parse_service_objects()}
    assert services["svc-dual"]["protocol"] == "tcp"
    assert services["svc-dual"]["port"] == "8080"


# --- 7. F3.2: vsys identity on the emit side --------------------------------

# The generated format is fixed, so small structural regexes are enough.
# A resource block ends at the first newline followed by a column-0 brace.

RESOURCE_BLOCK_RE = re.compile(
    r'resource "([a-z0-9_]+)" "([^"]+)" \{(.*?)\n\}', re.S)


def _resource_blocks(text: str, resource_type: str) -> list[dict]:
    """Parse generated resources into {local, body} dicts in file order."""
    return [{'local': m.group(2), 'body': m.group(3)}
            for m in RESOURCE_BLOCK_RE.finditer(text)
            if m.group(1) == resource_type]


def _generate(fixture_name: str, out_dir: Path) -> dict[str, str]:
    """Run the converter CLI on a fixture. Return {filename: text}."""
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / fixture_name),
                      '--output-dir', str(out_dir))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return {f.name: f.read_text(encoding='utf-8') for f in out_dir.glob('*.tf')}


@pytest.fixture(scope='module')
def emitted_vsys(tmp_path_factory) -> dict[str, dict[str, str]]:
    """Generate both vsys fixtures once for the whole module."""
    out = tmp_path_factory.mktemp('vsys_emit')
    return {
        'vsys1_first': _generate('edge_dup_names_across_vsys.xml', out / 'a'),
        'vsys2_first': _generate('edge_dup_names_across_vsys_swapped.xml', out / 'b'),
    }


def _addr_assignment(text: str) -> dict[str, str]:
    """{ip_netmask value: local name} for address resources."""
    out = {}
    for b in _resource_blocks(text, 'panos_address'):
        m = re.search(r'ip_netmask = "([^"]+)"', b['body'])
        out[m.group(1)] = b['local']
    return out


def _rule_assignment(text: str) -> dict[str, str]:
    """{PAN-OS rule name: local name} for security rule resources."""
    out = {}
    for b in _resource_blocks(text, 'panos_security_policy_rules'):
        # The rules list holds one object per rule; the rule name is the
        # only name = line inside it (the location block is outside).
        rules_body = re.search(r'rules = \[(.*?)\n  \]', b['body'], re.S).group(1)
        out[re.search(r'name = "([^"]+)"', rules_body).group(1)] = b['local']
    return out


def test_dup_names_across_vsys_emit_distinct_digests(emitted_vsys):
    """F3.2: both web objects emit as distinct digest-named resources.

    The taken-name counter must not decide which object gets the name:
    every local name is the sanitized base plus the 8-hex identity digest,
    with no _2 suffix.
    """
    blocks = _resource_blocks(emitted_vsys['vsys1_first']['address_objects.tf'],
                              'panos_address')
    assert len(blocks) == 2
    for b in blocks:
        assert re.fullmatch(r'web_[0-9a-f]{8}', b['local']), b['local']
    assert blocks[0]['local'] != blocks[1]['local']
    assert '_2' not in emitted_vsys['vsys1_first']['address_objects.tf']


def test_identity_to_name_assignment_survives_entry_order_flip(emitted_vsys):
    """F3.2: flipping the XML entry order does not change the assignment.

    The digest is computed from the object identity, so the same object
    keeps the same local name in both fixture orderings.
    """
    assert _addr_assignment(emitted_vsys['vsys1_first']['address_objects.tf']) == \
        _addr_assignment(emitted_vsys['vsys2_first']['address_objects.tf'])
    assert _rule_assignment(emitted_vsys['vsys1_first']['security_rules.tf']) == \
        _rule_assignment(emitted_vsys['vsys2_first']['security_rules.tf'])


def test_rule_resolves_name_in_its_own_vsys(emitted_vsys):
    """F3.2: a rule wires to the same-vsys object, not the other vsys's copy."""
    text = emitted_vsys['vsys1_first']['security_rules.tf']
    addr = _addr_assignment(emitted_vsys['vsys1_first']['address_objects.tf'])
    vs1_local = addr['10.1.0.1/32']   # the vsys1 web object
    vs2_local = addr['10.2.0.1/32']   # the vsys2 web object
    blocks = _resource_blocks(text, 'panos_security_policy_rules')
    assert len(blocks) == 4
    wired = {}
    for b in blocks:
        rules_body = re.search(r'rules = \[(.*?)\n  \]', b['body'], re.S).group(1)
        rule_name = re.search(r'name = "([^"]+)"', rules_body).group(1)
        ref = re.search(r'panos_address\.([a-z0-9_]+)\.name', b['body']).group(1)
        wired[rule_name] = ref
    assert wired['rule-vs1-a'] == vs1_local
    assert wired['rule-vs1-b'] == vs1_local
    assert wired['rule-vs2-a'] == vs2_local
    assert wired['rule-vs2-b'] == vs2_local


def test_rule_chains_do_not_cross_vsys(emitted_vsys):
    """F3.2: each vsys keeps its own rule chain.

    Each chain anchors at where = "last" (the chain restarts at the vsys
    boundary), and each later rule pivots on and depends on the previous
    rule of its own vsys only.
    """
    text = emitted_vsys['vsys1_first']['security_rules.tf']
    blocks = _resource_blocks(text, 'panos_security_policy_rules')
    by_name = {}
    for b in blocks:
        rules_body = re.search(r'rules = \[(.*?)\n  \]', b['body'], re.S).group(1)
        rule_name = re.search(r'name = "([^"]+)"', rules_body).group(1)
        where = re.search(r'where = "([^"]+)"', b['body'])
        pivot = re.search(r'pivot = "([^"]+)"', b['body'])
        dep = re.search(r'depends_on = \[([^\]]*)\]', b['body'])
        by_name[rule_name] = {
            'local': b['local'],
            'where': where.group(1) if where else None,
            'pivot': pivot.group(1) if pivot else None,
            'depends_on': dep.group(1).strip() if dep else None,
        }
    # Chain 1 (vsys1): anchor, then after-previous.
    assert by_name['rule-vs1-a']['where'] == 'last'
    assert by_name['rule-vs1-a']['pivot'] is None
    assert by_name['rule-vs1-a']['depends_on'] is None
    assert by_name['rule-vs1-b']['where'] == 'after'
    assert by_name['rule-vs1-b']['pivot'] == 'rule-vs1-a'
    assert by_name['rule-vs1-b']['depends_on'] == (
        f"panos_security_policy_rules.{by_name['rule-vs1-a']['local']}")
    # Chain 2 (vsys2): the boundary restarts the chain at the anchor.
    assert by_name['rule-vs2-a']['where'] == 'last'
    assert by_name['rule-vs2-a']['pivot'] is None
    assert by_name['rule-vs2-a']['depends_on'] is None
    assert by_name['rule-vs2-b']['where'] == 'after'
    assert by_name['rule-vs2-b']['pivot'] == 'rule-vs2-a'
    assert by_name['rule-vs2-b']['depends_on'] == (
        f"panos_security_policy_rules.{by_name['rule-vs2-a']['local']}")
