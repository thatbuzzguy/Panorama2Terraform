"""Unit tests for PanoramaParser network parse methods (zones, interfaces, routers, BGP, OSPF).

F7.1, F7.2, F7.5: `parse_bgp`, `parse_ospf`, `parse_ospfv3` and `parse_rip` build one router's levels, so the
protocol entries are captured fields of the router record and the router keeps one mark. An entry the `.tf`
cannot express is marked for the report, and `entry_coverage.protocol_report_rows` is the one list of them.
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
    # The five facts belong to the entry the ledger marks, so the choice body holds none of them.
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
    """`parse_ospf` builds the `protocol/ospf` level of one router (F7.1, F7.4).

    `ospf.xml` puts one interface inside an area and one at the OSPF level, which is the case the
    `.tf` cannot express, and one area of each type so the two body shapes print.
    """
    p = _parser(make_parser, "ospf.xml")
    router = p.parse_virtual_routers()[0]
    assert router["name"] == "default"
    assert router["vsys_device"] == "localhost.localdomain"
    assert router["vsys"] == "vsys1"

    ospf = router["protocol"]["ospf"]
    assert ospf["enable"] is True
    assert ospf["router_id"] == "10.0.0.1"

    assert len(ospf["area"]) == 2
    area = ospf["area"][0]
    assert area["name"] == "0.0.0.0"
    # A `one_of` area type is the value itself: the provider key is `stub`, and the export states it. The
    # fields of the body live inside the chosen element, so the parse reads them there (F7.2).
    # F7.4: `default_route` is the one choice the provider requires inside the body, so the export states
    # it by presence and the value read is the child element's tag.
    assert area["type"] == {"stub": {"accept_summary": True,
                                     "default_route": {"advertise": {"metric": 10}}}}
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
    # F7.4: a neighbor entry holds the entry name, which is the whole shape the provider declares.
    assert [entry["name"] for entry in inner["neighbor"]] == ["10.0.0.2"]
    # F7.4: the virtual link is read through the same area rule, and the `ospf` row states no `instance_id`
    # for it, so the captured dict holds no key for a field the provider does not declare here.
    link = area["virtual_link"][0]
    assert link["name"] == "10.0.0.2"
    assert link["hello_interval"] == 10
    assert link["transit_area_id"] == "0.0.0.1"
    assert "instance_id" not in link

    # F7.4: the `nssa` body holds the entry level `nssa_ext_range`, and the default-route choice the export
    # states as `no`. `str()` is the print, which is the empty object a `block` level states.
    nssa = ospf["area"][1]["type"]["nssa"]
    assert str(nssa["default_route"]["no"]) == "{}"
    assert [(entry["name"], str(entry["suppress"])) for entry in nssa["nssa_ext_range"]] == [
        ("10.20.0.0/16", "{}")]

    # The four entries the `.tf` cannot express: the range entry with no choice, the interface whose
    # link-type value the mapping cannot state, the `nssa_ext_range` entry with no choice, and the
    # interface the export places outside an area. The rows come from the ledger in report order.
    rows = entry_coverage.protocol_report_rows(p.ledger)
    assert [(row["router"], row["level"], row["name"]) for row in rows] == [
        ("default", "range", "10.60.0.0/16"),
        ("default", "interface", "ethernet1/3"),
        ("default", "nssa-ext-range", "10.30.0.0/16"),
        ("default", "interface", "ethernet1/1")], rows
    assert rows[1]["detail"] == ('link_type multicast is not a value PROTOCOL_SHAPE states')
    # The same reason as a `range` entry, because the row states the choice as `block` fields.
    assert rows[2]["detail"] == 'no advertise or suppress', rows[2]
    assert rows[3]["captured"]["link_type"] == {"point-to-point": {}}


def test_parse_ospfv3(make_parser):
    """`parse_ospfv3` builds the `protocol/ospfv3` level of one router (F7.2, F7.4).

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
    # F7.4: the second area states a `default-route` element with no child, so it is not in the printed
    # list and the report names it below.
    assert area["name"] == "0.0.0.0"
    # The fields of the chosen body live inside the chosen element, the same rule as the `ospf` level.
    # F7.4: the value read is the child element's tag `no`, and the key the print states is `disable`.
    nssa = area["type"]["nssa"]
    assert nssa["accept_summary"] is True
    assert str(nssa["default_route"]["no"]) == "{}"
    assert [(entry["name"], str(entry["advertise"])) for entry in nssa["nssa_ext_range"]] == [
        ("10.20.0.0/16", "{}")]
    assert len(area["range"]) == 1, area["range"]
    assert area["range"][0]["name"] == "10.0.0.0/8"
    assert str(area["range"][0]["suppress"]) == "{}"
    inner = area["interface"][0]
    assert inner["name"] == "ethernet1/2"
    # The captured dict is keyed by the value the export states; the emitter prints the key the mapping
    # selects, which is `p2p` here.
    assert inner["link_type"] == {"point-to-point": {}}
    assert inner["passive"] is False
    # F7.4: a neighbor entry holds the entry name, which is the whole shape the provider declares.
    assert [entry["name"] for entry in inner["neighbor"]] == ["10.0.0.2"]
    # F7.4: `instance_id` is the one field the provider declares for this level and not for the `ospf` one,
    # so the same reader reads it here.
    link = area["virtual_link"][0]
    assert link["name"] == "10.0.0.2"
    assert link["instance_id"] == 1

    # The two entries the `.tf` cannot express: the area whose `default-route` element states neither
    # choice, and the interface the export places at the level. A `default_route` is not an entry, so the
    # report names the area entry that holds it.
    rows = entry_coverage.protocol_report_rows(p.ledger)
    assert [(row["router"], row["level"], row["name"]) for row in rows] == [
        ("default", "area", "0.0.1.0"),
        ("default", "interface", "ethernet1/1")], rows
    assert rows[0]["detail"] == (
        'panos_virtual_router - default_route states no key PROTOCOL_SHAPE selects'), rows[0]
    assert rows[1]["detail"] == 'no provider field for an interface outside an area', rows[1]


def test_parse_ospfv3_reads_the_levels_the_table_states(make_parser):
    """`parse_ospfv3` reads the four `protocol/ospfv3` levels outside `area` as their rows state them (F7.3).

    A `single` level is one object, so `_protocol_level` reads it with no field name of its own, and
    `export_rules` is a `string_list`, so the method fills it with the entries the export holds. The entry is
    marked, so the property scan measures it against the router row.
    """
    p = _parser(make_parser, "ospfv3.xml")
    ospfv3 = {r["name"]: r for r in p.parse_virtual_routers()}["edge-af"]["protocol"]["ospfv3"]
    assert ospfv3["timers"] == {"lsa_interval": 120, "spf_calculation_delay": 20}, ospfv3["timers"]
    assert ospfv3["global_bfd"] == {"profile": "BFD-OSP"}, ospfv3["global_bfd"]
    assert ospfv3["graceful_restart"] == {
        "enable": True, "grace_period": 120, "helper_enable": True,
        "max_neighbor_restart_time": 200, "strict_l_s_a_checking": True}, ospfv3["graceful_restart"]
    # The element name for `strict_l_s_a_checking` is the one case the `-` rule cannot produce, so the export
    # states `strict-lsa-checking` and the table reads it through `XML_NAME_EXCEPTIONS`.
    rule = ospfv3["export_rules"][0]
    element = next(e for e in p.ledger.entries() if e.get("name") == "static-af")
    assert p.ledger.mark_for(element) is not None, 'an export rule is a marked entry'
    assert rule["name"] == "static-af"
    assert (rule["metric"], rule["new_path_type"], rule["new_tag"]) == (10, "internal", "0"), rule


def test_parse_rip_reads_the_levels_the_table_states(make_parser):
    """`parse_rip` reads the `protocol/rip` levels as their rows state them (F7.5).

    A `single` level is one object read by `_protocol_level` with no field name of its own, and the two
    `string_list` levels are filled with the entries the export holds. An interface entry fills the choice it
    states inside itself, so the entry whose choice element states no alternative is marked for the report and
    is not put in the printed list.
    """
    p = _parser(make_parser, "rip.xml")
    rip = p.parse_virtual_routers()[0]["protocol"]["rip"]
    assert (rip["enable"], rip["allow_redist_default_route"], rip["reject_default_route"]) == (
        True, True, False), rip
    assert rip["timers"] == {"interval_seconds": 30, "update_intervals": 180,
                             "expire_intervals": 210, "delete_intervals": 120}, rip["timers"]
    assert rip["global_bfd"] == {"profile": "BFD-RIP"}, rip["global_bfd"]
    # The two entries the print holds. The third states a choice with no alternative, so the report names it.
    assert [entry["name"] for entry in rip["interfaces"]] == ["ethernet1/2", "ethernet1/3"], rip["interfaces"]
    first = rip["interfaces"][0]
    # `mode` is a string, so the read is the value the export states: no mapping stands between them.
    assert (first["mode"], first["authentication"]) == ("v2", "md5"), first
    assert first["bfd"] == {"profile": "BFD-RIP"}, first
    # The choice the entry holds inside itself, the same rule as a choice inside a chosen area body.
    assert first["default_route"] == {"advertise": {"metric": 10}}, first
    # The export states this alternative as `no`, and the key the print states for it is `disable`.
    second = rip["interfaces"][1]
    assert str(second["default_route"]["no"]) == "{}", second
    rule = rip["export_rules"][0]
    assert (rule["name"], rule["metric"]) == ("static-af", 10), rule
    # An interface entry and an export rule entry are entries the container table covers, so they are marked.
    for name in ("ethernet1/2", "static-af"):
        element = next(e for e in p.ledger.entries() if e.get("name") == name)
        assert p.ledger.mark_for(element) is not None, name

    rows = entry_coverage.protocol_report_rows(p.ledger)
    assert [(row["router"], row["level"], row["name"]) for row in rows] == [
        ("default", "interfaces", "ethernet1/4")], rows
    assert rows[0]["detail"] == (
        'panos_virtual_router - default_route states no key PROTOCOL_SHAPE selects'), rows[0]
    # The entry is a property level of the router, so the row names the router that holds it and the level the
    # row path names.
    assert rows[0]["container"].endswith('protocol/rip/interfaces'), rows[0]["container"]


def test_parse_bgp_reads_the_policy_levels_the_table_states(make_parser):
    """`parse_bgp` reads the `policy` level and its four entry levels as their rows state them (F7.6).

    `policy` is a `single` level, so `_protocol_level` reads it with no field name of its own, and the four
    levels inside it that hold entries are filled through the path the row names. A level inside an entry is
    filled by `_protocol_body`, which reaches it through the table, so the code states no path for it. A
    `member_list` field is read by `_protocol_level`, because its value is the members the element holds and not
    entries. The export rule whose `action` element states no alternative is not put in the printed list, so the
    report names it.
    """
    p = _parser(make_parser, "bgp_policy.xml")
    policy = p.parse_virtual_routers()[0]["protocol"]["bgp"]["policy"]
    address = policy["aggregation"]["address"][0]
    assert (address["name"], address["prefix"], address["summary"], address["as_set"]) == (
        "agg-10.0.0.0-8", "10.0.0.0/8", True, True), address
    # A choice level is the one key the export states, and the value is what the field reader reads for the
    # alternative: a value alternative is the value, so the read holds no dict for it (F7.6). The key is the
    # spelling the export states, so the print applies the row's mapping to it.
    choice = address["aggregate_route_attributes"]
    assert tuple(list(choice[name]) for name in ("as_path", "community", "extended_community")) == (
        ["prepend"], ["append"], ["remove-regex"]), choice
    assert (choice["as_path"]["prepend"], choice["community"]["append"],
            choice["extended_community"]["remove-regex"]) == (5, ["1:10"], "2:.*"), choice
    filter_entry = address["advertise_filters"][0]
    # The members are values, so a member list is the list `_protocol_field` read, with no entry inside it.
    assert (filter_entry["match"]["from_peer"], filter_entry["match"]["nexthop"]) == (
        ["192.0.2.1", "192.0.2.2"], ["198.51.100.7"]), filter_entry
    # An entry inside an entry belongs to the level the field names, not to the level above it.
    assert [entry["name"] for entry in filter_entry["match"]["address_prefix"]] == ["agg-prefix"], filter_entry
    assert [entry["name"] for entry in address["suppress_filters"]] == ["agg-suppresses"], address
    cond = policy["conditional_advertisement"]["policy"][0]
    assert (cond["name"], cond["used_by"]) == ("cond-10.0.0.0-16", ["agg-10.0.0.0-8"]), cond
    export = policy["export"]["rules"][0]
    # `action` is the one choice level in the subtree, and its mapping is the identity, so the value the export
    # states is the key the print states.
    assert list(export["action"]) == ["allow"], export["action"]
    assert str(export["action"]["allow"]["update"]["as_path"]["remove"]) == "{}", export["action"]
    assert [entry["name"] for entry in policy["import"]["rules"]] == ["import-deny"], policy["import"]["rules"]
    assert str(policy["import"]["rules"][0]["action"]["deny"]) == "{}", policy["import"]["rules"][0]
    # The four entry levels the container table names are the levels the property scan measures, so the entries
    # at them are marked.
    for name in ("agg-10.0.0.0-8", "cond-10.0.0.0-16", "export-allow", "import-deny"):
        element = next(e for e in p.ledger.entries() if e.get("name") == name)
        assert p.ledger.mark_for(element) is not None, name

    rows = entry_coverage.protocol_report_rows(p.ledger)
    assert [(row["router"], row["level"], row["name"]) for row in rows] == [
        ("policy-vr", "rules", "export-no-action")], rows
    assert rows[0]["detail"] == (
        'panos_virtual_router - action states no key PROTOCOL_SHAPE selects'), rows[0]
    # The entry the file cannot hold is a property entry, so the report reads its captured fields.
    assert rows[0]["fields"] == ('action', 'enable', 'match'), rows[0]
    # The container table states no row for a level inside an entry, so the scan scope is the entry level.
    assert rows[0]["container"].endswith('protocol/bgp/policy/export/rules'), rows[0]["container"]


def test_parse_rip_absent(make_parser):
    """A router with no RIP element has no `rip` level, so nothing prints for it (F7.5)."""
    p = _parser(make_parser, "zones.xml")
    for router in p.parse_virtual_routers():
        assert router["protocol"]["rip"] == {}, router


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
