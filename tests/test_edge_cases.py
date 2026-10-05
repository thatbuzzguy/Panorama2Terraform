"""Edge-case fixture tests (F1.6 corpus).

Pins current parser behavior for edge cases and marks the known gaps as
xfail with references to the epic that must change behavior:

- duplicate names across device groups: last-wins today; Epic 3 F3.1
  keys objects by (device group, vsys, type, name).
- IPv6 address objects: parsed from the <ipv6> element (F2.4).
- multi-port / dual-protocol services: current behavior pinned; the udp
  drop is recorded in backlog.md.
"""

import xml.etree.ElementTree as ET

import pytest

from conftest import FIXTURES_DIR


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

def test_dup_names_across_dgs_current_last_wins(make_parser):
    """Current behavior: one entry per name, last definition wins."""
    parser = make_parser("edge_dup_names_across_dgs.xml")
    objects = parser.parse_address_objects()
    assert len(objects) == 1
    assert objects[0]["name"] == "web"
    assert objects[0]["value"] == "10.0.0.2/32"


@pytest.mark.xfail(reason="same-named objects in different DGs must both survive; Epic 3 F3.1", strict=False)
def test_dup_names_across_dgs_both_survive(make_parser):
    """Desired behavior: per-DG objects are not merged away."""
    parser = make_parser("edge_dup_names_across_dgs.xml")
    values = sorted(a["value"] for a in parser.parse_address_objects())
    assert values == ["10.0.0.1/32", "10.0.0.2/32"]


# --- 3. Multi-vsys -----------------------------------------------------------

def test_multi_vsys_objects_both_parse(make_parser):
    """Objects under different vsys must all be parsed."""
    parser = make_parser("edge_multi_vsys.xml")
    objects = {a["name"]: a["value"] for a in parser.parse_address_objects()}
    assert objects == {"host-vs1": "10.9.1.10/32", "host-vs2": "10.9.2.10/32"}


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
