"""Unit tests for PanoramaParser network parse methods (zones, interfaces, routers, BGP, OSPF).

F7.1, F7.2: `parse_bgp`, `parse_ospf` and `parse_ospfv3` build one router's levels, so the protocol entries
are captured fields of the router record and the router keeps one mark. An entry the `.tf` cannot express is
marked for the report, and `entry_coverage.protocol_report_rows` is the one list of them.
"""

import entry_coverage


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
    assert sub["parent"] == "ae1.101"


def test_parse_ethernet_subinterface_units(make_parser):
    """F3.3: ethernet subinterface units are individual entries."""
    p = _parser(make_parser, "interfaces_ethernet.xml")
    ifaces = p.parse_interfaces()
    by_name = {i["name"]: i for i in ifaces}

    sub = by_name["ethernet1/1.10"]
    assert sub["type"] == "ethernet-subinterface"
    assert sub["parent"] == "ethernet1/1"
    assert sub["tag"] == "10"
    assert sub["ip_addresses"] == ["192.168.1.10/24"]
    # The physical entry keeps only its own address.
    assert by_name["ethernet1/1"]["ip_addresses"] == ["192.168.1.1/24"]
    # F3.3 criterion 3: every entry carries kind, mode, parent, vsys.
    assert all(i["parent"] is not None or i["type"] in ("ethernet", "vlan",
                                                         "loopback", "tunnel")
               for i in ifaces)


def test_parse_virtual_wire_units(make_parser):
    """F3.3: the virtual-wire container is parsed as individual entries."""
    p = _parser(make_parser, "interfaces_ethernet.xml")
    by_name = {i["name"]: i for i in p.parse_interfaces()}

    vw = by_name["ethernet1/4.1"]
    assert vw["type"] == "ethernet"
    assert vw["mode"] == "virtual-wire"
    assert vw["parent"] == "ethernet1/4"

    # An ethernet entry that is itself in virtual-wire or tap mode keeps
    # that mode; the provider has no separate resource type for them.
    assert by_name["ethernet1/3"]["mode"] == "virtual-wire"
    assert by_name["ethernet1/5"]["mode"] == "tap"


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
    # A router outside a template declares no template (F3.5); the emitter
    # decides the location, the parser does not guess one.
    assert dmz["template"] == ""
    assert dmz["vsys"] == "vsys1"
    assert dmz["vsys_device"] == "localhost.localdomain"
    assert dmz["interfaces"] == ["ethernet1/3"]
    assert dmz["static_routes"] == []


def test_parse_virtual_routers_device_level(make_parser):
    """A router under devices/entry/<device>/network is parsed (F3.5).

    A firewall's own config export declares network config at device level,
    which the old template-plus-vsys walk missed.
    """
    p = _parser(make_parser, "virtual_routers.xml")
    by_name = {v["name"]: v for v in p.parse_virtual_routers()}

    device = by_name["vr-device"]
    assert device["template"] == ""
    assert device["vsys"] == ""
    assert device["vsys_device"] == "fw-1.example.com"
    assert device["interfaces"] == ["ethernet1/4"]


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
    """`parse_bgp` builds the `protocol/bgp` level of one router (F7.1).

    The router entry is the object the emitter places, so the level is a captured field of that entry
    instead of a record of its own, and the router keeps one mark.
    """
    p = _parser(make_parser, "bgp.xml")
    routers = p.parse_virtual_routers()
    # The fixture puts the router under a device and names a second router with no BGP, so the
    # assertion names the one that has it. One path reads it once, so the report prints one block.
    assert len(routers) == 2, routers
    router = [entry for entry in routers if entry["name"] == "default"][0]
    assert router["vsys_device"] == "localhost.localdomain"
    assert router["vsys"] == "vsys1"
    assert router["template"] == ""

    bgp = router["protocol"]["bgp"]
    assert bgp["enable"] is True
    assert bgp["local_as"] == "65001"
    assert bgp["router_id"] == "10.0.0.1"

    assert len(bgp["peer_group"]) == 1
    group = bgp["peer_group"][0]
    assert group["name"] == "PG-Branch"
    # A `one_of` level holds the value the export states as the key, so the report prints what the
    # operator types in the GUI and the emitter maps it to the provider key.
    assert group["type"] == {"external": {"export_nexthop": "self", "import_nexthop": "self",
                                          "remove_private_as": ""}}
    # The four facts belong to the entry the ledger marks, so the choice body holds none of them.
    assert not set(group["type"]["external"]) & entry_coverage.NON_FIELD_KEYS, group["type"]

    # The peer the export puts inside the peer-group element is captured on that entry, so the
    # membership is the parent entry and `peer_group` is not a captured field (F7.1).
    assert len(group["peer"]) == 1
    peer = group["peer"][0]
    assert peer["name"] == "10.55.0.2"
    assert peer["peer_as"] == "65002"
    assert peer["local_address"] == {"interface": "", "ip": "10.55.0.1"}
    assert peer["peer_address"] == {"fqdn": "", "ip": "10.55.0.2"}
    assert peer["enable"] is True
    assert "peer_group" not in peer

    assert len(bgp["redist_rules"]) == 1
    redist = bgp["redist_rules"][0]
    assert redist["name"] == "redist-static"
    assert redist["enable"] is True
    assert redist["address_family_identifier"] == "ipv4-unicast"
    # The export states no metric, so a number field with no value is empty and prints nothing (F7.1).
    assert redist["metric"] == ""


def test_parse_bgp_keeps_a_peer_no_group_names_for_the_report(make_parser):
    """A peer at the `bgp` level that no peer group names is marked for the report (F7.1).

    `PROTOCOL_SHAPE` states no provider field for it, so the emitter cannot express it and the manual
    report prints it. `entry_coverage.protocol_report_rows` is the one list these entries come from.
    """
    p = _parser(make_parser, "bgp.xml")
    p.parse_virtual_routers()
    rows = entry_coverage.protocol_report_rows(p.ledger)
    assert [(row["router"], row["level"], row["name"]) for row in rows] == [
        ("default", "peer", "10.55.0.9")], rows
    # The captured object is the same object the parse marked, so the report and the scan read one record.
    assert rows[0]["captured"]["peer_as"] == "65003"


def test_parse_bgp_absent(make_parser):
    """A router with no BGP element has no `bgp` level, so nothing prints for it (F7.1)."""
    p = _parser(make_parser, "zones.xml")
    for router in p.parse_virtual_routers():
        assert router["protocol"]["bgp"] == {}, router


def test_parse_ospf(make_parser):
    """`parse_ospf` builds the `protocol/ospf` level of one router (F7.1).

    `ospf.xml` puts one interface inside an area and one at the OSPF level, which is the case the
    `.tf` cannot express.
    """
    p = _parser(make_parser, "ospf.xml")
    router = p.parse_virtual_routers()[0]
    assert router["name"] == "default"
    assert router["vsys_device"] == "localhost.localdomain"
    assert router["vsys"] == "vsys1"

    ospf = router["protocol"]["ospf"]
    assert ospf["enable"] is True
    assert ospf["router_id"] == "10.0.0.1"

    assert len(ospf["area"]) == 1
    area = ospf["area"][0]
    assert area["name"] == "0.0.0.0"
    # A `one_of` area type is the value itself: the provider key is `stub`, and the export states it. The
    # fields of the body live inside the chosen element, so the parse reads them there (F7.2).
    assert area["type"] == {"stub": {"accept_summary": True}}
    # A range entry prints inside the area, with the choice block the provider requires. The entry that
    # states neither has no `.tf` shape, so it is not in the printed list (F7.1).
    assert len(area["range"]) == 1, area["range"]
    assert area["range"][0]["name"] == "10.0.0.0/8"
    assert str(area["range"][0]["advertise"]) == "{}"
    # An interface inside an area is captured inside that area, because the provider field is there.
    assert len(area["interface"]) == 1
    inner = area["interface"][0]
    assert inner["name"] == "ethernet1/2"
    assert inner["link_type"] == {"broadcast": {}}
    assert inner["metric"] == 10
    assert inner["passive"] is False

    # The three entries the `.tf` cannot express: the range entry with no choice, the interface whose
    # link-type value the mapping cannot state, and the interface the export places outside an area.
    # The rows come from the ledger in report order.
    rows = entry_coverage.protocol_report_rows(p.ledger)
    assert [(row["router"], row["level"], row["name"]) for row in rows] == [
        ("default", "range", "10.60.0.0/16"),
        ("default", "interface", "ethernet1/3"),
        ("default", "interface", "ethernet1/1")], rows
    assert rows[1]["detail"] == ('link_type multicast is not a value PROTOCOL_SHAPE states')
    assert rows[2]["captured"]["link_type"] == {"point-to-point": {}}


def test_parse_ospfv3(make_parser):
    """`parse_ospfv3` builds the `protocol/ospfv3` level of one router (F7.2).

    `ospfv3.xml` puts one interface inside an area and one at the level, which is the case the `.tf` cannot
    express. The area subtree is read by the same reader as `parse_ospf`, so the same facts hold.
    """
    p = _parser(make_parser, "ospfv3.xml")
    router = p.parse_virtual_routers()[0]
    ospfv3 = router["protocol"]["ospfv3"]
    assert ospfv3["enable"] is True
    assert ospfv3["router_id"] == "10.0.0.1"

    assert len(ospfv3["area"]) == 1
    area = ospfv3["area"][0]
    assert area["name"] == "0.0.0.0"
    # The fields of the chosen body live inside the chosen element, the same rule as the `ospf` level.
    assert area["type"] == {"nssa": {"accept_summary": True}}
    assert len(area["range"]) == 1, area["range"]
    assert area["range"][0]["name"] == "10.0.0.0/8"
    assert str(area["range"][0]["suppress"]) == "{}"
    inner = area["interface"][0]
    assert inner["name"] == "ethernet1/2"
    # The captured dict is keyed by the value the export states; the emitter prints the key the mapping
    # selects, which is `p2p` here.
    assert inner["link_type"] == {"point-to-point": {}}
    assert inner["passive"] is False

    # The interface the export places at the level has no provider field, so the row note is the reason.
    rows = entry_coverage.protocol_report_rows(p.ledger)
    assert [(row["router"], row["level"], row["name"]) for row in rows] == [
        ("default", "interface", "ethernet1/1")], rows
    assert rows[0]["detail"] == 'no provider field for an interface outside an area', rows[0]


def test_parse_ospfv3_absent(make_parser):
    """A router with no OSPFv3 element has no `ospfv3` level, so nothing prints for it (F7.2)."""
    p = _parser(make_parser, "zones.xml")
    for router in p.parse_virtual_routers():
        assert router["protocol"]["ospfv3"] == {}, router


def test_parse_ospf_absent(make_parser):
    """A router with no OSPF element has no `ospf` level, so nothing prints for it (F7.1)."""
    p = _parser(make_parser, "zones.xml")
    for router in p.parse_virtual_routers():
        assert router["protocol"]["ospf"] == {}, router
