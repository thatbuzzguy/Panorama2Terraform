"""Unit tests for PanoramaParser network parse methods (zones, interfaces, routers, BGP, OSPF)."""


def _parser(make_parser, fixture_name):
    return make_parser(fixture_name)


def test_parse_zones(make_parser):
    p = _parser(make_parser, "zones.xml")
    zones = p.parse_zones()
    by_name = {z["name"]: z for z in zones}

    trust = by_name["trust"]
    assert trust["type"] == "layer3"
    assert trust["interfaces"] == ["ethernet1/1", "ethernet1/2"]
    assert trust["zone_protection_profile"] == "ZPP-Default"

    lan2 = by_name["lan2"]
    assert lan2["type"] == "layer2"
    assert lan2["interfaces"] == ["ethernet1/3"]
    assert lan2["zone_protection_profile"] is None


def test_parse_interfaces_ethernet(make_parser):
    p = _parser(make_parser, "interfaces_ethernet.xml")
    ifaces = p.parse_interfaces()
    by_name = {i["name"]: i for i in ifaces}

    l3 = by_name["ethernet1/1"]
    assert l3["type"] == "ethernet"
    assert l3["mode"] == "layer3"
    assert l3["ip_addresses"] == ["192.168.1.1/24"]
    assert l3["management_profile"] == "Management1"
    assert l3["comment"] == "Trust uplink"

    l2 = by_name["ethernet1/2"]
    assert l2["mode"] == "layer2"
    assert l2["ip_addresses"] == []


def test_parse_interfaces_other_types(make_parser):
    p = _parser(make_parser, "interfaces_other.xml")
    ifaces = p.parse_interfaces()
    by_name = {i["name"]: i for i in ifaces}

    vlan = by_name["vlan.10"]
    assert vlan["type"] == "vlan"
    assert vlan["mode"] == "layer3"
    assert vlan["ip_addresses"] == ["10.10.10.1/24"]
    assert vlan["tag"] == "10"

    loop = by_name["loopback.1"]
    assert loop["type"] == "loopback"
    assert loop["ip_addresses"] == ["169.254.0.1/32"]

    tunnel = by_name["tunnel.1"]
    assert tunnel["type"] == "tunnel"
    assert tunnel["ip_addresses"] == ["10.255.0.1/32"]

    # The parent aggregate must only carry its own IP, not the subinterface IP.
    agg = by_name["ae1.101"]
    assert agg["type"] == "aggregate"
    assert agg["mode"] == "layer3"
    assert agg["ip_addresses"] == ["172.16.1.1/24"]

    sub = by_name["ae1.101.20"]
    assert sub["type"] == "aggregate-subinterface"
    assert sub["ip_addresses"] == ["172.16.20.1/24"]
    assert sub["tag"] == "20"


def test_parse_virtual_routers_from_template(make_parser):
    """Virtual routers from the templates section must be parsed.

    Regression test: the parser searched for `.//template/entry` (singular)
    but Panorama exports use `<templates><entry>`, so template VRs were
    silently dropped.
    """
    p = _parser(make_parser, "virtual_routers.xml")
    vrouters = p.parse_virtual_routers()
    by_name = {v["name"]: v for v in vrouters}

    default = by_name["default"]
    assert default["template"] == "FW-Template"
    assert default["interfaces"] == ["ethernet1/1", "ethernet1/2"]
    routes = {r["name"]: r for r in default["static_routes"]}
    assert routes["default-gw"]["destination"] == "default"
    assert routes["default-gw"]["nexthop_ip"] == "192.168.1.254"
    assert routes["default-gw"]["metric"] == "10"
    assert routes["dmz-route"]["destination"] == "172.16.0.0/16"
    assert routes["dmz-route"]["metric"] is None


def test_parse_virtual_routers_from_vsys(make_parser):
    """Virtual routers from the per-vsys network section must be parsed."""
    p = _parser(make_parser, "virtual_routers.xml")
    vrouters = p.parse_virtual_routers()
    by_name = {v["name"]: v for v in vrouters}

    dmz = by_name["vr-dmz"]
    assert dmz["template"] == "device-specific"
    assert dmz["interfaces"] == ["ethernet1/3"]
    assert dmz["static_routes"] == []


def test_parse_logical_routers(make_parser):
    p = _parser(make_parser, "logical_routers.xml")
    lrouters = p.parse_logical_routers()
    assert len(lrouters) == 1
    lr = lrouters[0]
    assert lr["name"] == "lr-main"
    assert lr["router_type"] == "logical"
    assert lr["template"] == "FW-Template"
    assert lr["interfaces"] == ["ethernet1/1"]
    assert len(lr["static_routes"]) == 1
    route = lr["static_routes"][0]
    assert route["name"] == "lr-default"
    assert route["nexthop_interface"] == "lr-peer"


def test_parse_bgp_enabled(make_parser):
    p = _parser(make_parser, "bgp.xml")
    bgp = p.parse_bgp()
    assert bgp is not None
    assert bgp["enabled"] is True
    assert bgp["router_id"] == "10.0.0.1"
    assert bgp["as_number"] == "65001"

    assert len(bgp["peer_groups"]) == 1
    pg = bgp["peer_groups"][0]
    assert pg["name"] == "PG-Branch"
    assert pg["type"] == "external"

    assert len(bgp["peers"]) == 1
    peer = bgp["peers"][0]
    assert peer["name"] == "10.55.0.2"
    assert peer["peer_as"] == "65002"
    assert peer["local_address_ip"] == "10.55.0.1"
    assert peer["peer_address_ip"] == "10.55.0.2"
    assert peer["enable"] is True
    assert peer["peer_group"] == "PG-Branch"

    assert len(bgp["redistribution_rules"]) == 1
    redist = bgp["redistribution_rules"][0]
    assert redist["name"] == "redist-static"
    assert redist["enable"] is True
    assert redist["address_family"] == "ipv4-unicast"


def test_parse_bgp_absent(make_parser):
    """BGP returns None when no virtual router has BGP enabled."""
    p = _parser(make_parser, "zones.xml")
    assert p.parse_bgp() is None


def test_parse_ospf(make_parser):
    p = _parser(make_parser, "ospf.xml")
    ospf = p.parse_ospf()
    assert ospf is not None
    assert ospf["enabled"] is True
    assert ospf["router_id"] == "10.0.0.1"

    assert len(ospf["areas"]) == 1
    area = ospf["areas"][0]
    assert area["area_id"] == "0.0.0.0"
    assert area["type"] == "stub"
    assert area["ranges"] == ["10.0.0.0/8"]

    assert len(ospf["interfaces"]) == 1
    iface = ospf["interfaces"][0]
    assert iface["interface"] == "ethernet1/1"
    assert iface["enable"] is True
    assert iface["passive"] is True
    assert iface["link_type"] == "point-to-point"
    assert iface["metric"] == "10"


def test_parse_ospf_absent(make_parser):
    """OSPF returns None when no virtual router has OSPF enabled."""
    p = _parser(make_parser, "zones.xml")
    assert p.parse_ospf() is None
