"""Unit tests for PanoramaParser rule parse methods (security, NAT, decryption, PBF, schedules, app-override)."""


def _parser(make_parser, fixture_name):
    return make_parser(fixture_name)


def test_parse_security_rules(make_parser):
    p = _parser(make_parser, "security_rules.xml")
    rules = p.parse_security_rules()
    by_name = {r["name"]: r for r in rules}
    assert list(by_name) == ["Allow-Web-Traffic", "Block-Risky-Apps"]

    allow = by_name["Allow-Web-Traffic"]
    assert allow["source_zones"] == ["Trust"]
    assert allow["destination_zones"] == ["DMZ"]
    assert allow["source_addresses"] == ["Internal-Network"]
    assert allow["destination_addresses"] == ["Web-Servers"]
    assert allow["applications"] == ["web-browsing", "ssl"]
    assert allow["services"] == ["application-default"]
    assert allow["action"] == "allow"
    assert allow["log_start"] is True
    assert allow["log_end"] is False
    assert allow["disabled"] is False
    assert allow["description"] == "Allow web traffic"

    block = by_name["Block-Risky-Apps"]
    assert block["action"] == "deny"
    assert block["disabled"] is True
    assert block["log_end"] is True
    assert block["log_start"] is False


def test_parse_nat_rules(make_parser):
    p = _parser(make_parser, "nat_rules.xml")
    rules = p.parse_nat_rules()
    by_name = {r["name"]: r for r in rules}
    assert list(by_name) == ["Outbound-NAT", "Inbound-Web-NAT"]

    outbound = by_name["Outbound-NAT"]
    assert outbound["source_translation_type"] == "dynamic-ip-and-port"
    assert outbound["source_zones"] == ["Trust"]
    assert outbound["destination_zone"] == "Untrust"
    assert outbound["source_addresses"] == ["Internal-Network"]
    assert outbound["service"] == "any"
    assert outbound["source_translation_address"] == ["Untrust-Interface"]
    assert "destination_translation_address" not in outbound
    assert outbound["description"] == "Outbound NAT"

    inbound = by_name["Inbound-Web-NAT"]
    assert "source_translation_type" not in inbound
    assert inbound["destination_translation_address"] == "10.1.1.10"
    assert inbound["destination_translation_port"] == "80"


def test_parse_schedules(make_parser):
    p = _parser(make_parser, "schedules.xml")
    schedules = p.parse_schedules()
    by_name = {s["name"]: s for s in schedules}

    biz = by_name["Business-Hours"]
    assert biz["schedule_type"] == "recurring"
    assert [e["name"] for e in biz["recurring"]] == ["Weekdays"]

    one = by_name["One-Time"]
    assert one["schedule_type"] == "non-recurring"
    assert one["recurring"] == []


def test_parse_decryption_rules(make_parser):
    p = _parser(make_parser, "decryption_rules.xml")
    rules = p.parse_decryption_rules()
    assert [r["name"] for r in rules] == ["Decrypt-HTTPS", "Decrypt-SSH"]

    https = rules[0]
    assert https["uuid"] == "abc-123"
    # F2.9: the device group scopes the v2 resource location and chain
    assert https["device_group"] == "Production-DG"
    assert https["source_zones"] == ["Trust"]
    assert https["destination_zones"] == ["Untrust"]
    assert https["source_addresses"] == ["Internal-Network"]
    assert https["services"] == ["service-https"]
    # Modern PAN-OS 10/11 shape: the v2 action enum plus the type block name
    assert https["action"] == "decrypt"
    assert https["type"] == "ssl-forward-proxy"
    assert https["profile"] == "ssl-decrypt-policy"
    assert https["log_setting"] == "default"
    assert https["disabled"] is False
    # F2.9: log-start/log-end map to the v2 log_success/log_fail attributes
    assert https["log_start"] is True
    assert https["log_end"] is False

    # Legacy PAN-OS 9 shape: the mode sits in the action field and there
    # is no type block; the generator maps it to the v2 shape
    ssh = rules[1]
    assert ssh["action"] == "ssh-proxy"
    assert ssh["type"] is None
    assert ssh["profile"] == "ssh-decrypt-profile"
    assert ssh["log_start"] is True
    assert ssh["log_end"] is True


def test_parse_pbf_rules(make_parser):
    p = _parser(make_parser, "pbf_rules.xml")
    rules = p.parse_pbf_rules()
    by_name = {r["name"]: r for r in rules}
    assert list(by_name) == ["PBF-Forward", "PBF-ForwardVsys", "PBF-Discard", "PBF-NoPBF"]

    # F2.9: the device group scopes the v2 resource location and chain
    assert by_name["PBF-Forward"]["device_group"] == "Production-DG"

    fwd = by_name["PBF-Forward"]
    assert fwd["source_zones"] == ["vsys1"]
    assert fwd["source_addresses"] == ["Internal-Network"]
    assert fwd["action"] == {
        "type": "forward",
        "nexthop_ip": "10.0.0.1",
        "egress_interface": "ethernet1/1",
        # F2.9: path monitoring on the forward action; the profile name
        # references a panos_monitor_profile resource
        "monitor": {
            "ip_address": "10.1.1.1",
            "profile": "PM-Branch",
            "disable_if_unreachable": True,
        },
    }
    assert fwd["enforce_symmetric_return"] is True
    # F2.9: optional schedule name
    assert fwd["schedule"] == "Business-Hours"

    # F2.9: forward-to-vsys is a plain vsys name
    fwd_vsys = by_name["PBF-ForwardVsys"]
    assert fwd_vsys["action"] == {"type": "forward_to_vsys", "vsys": "vsys2"}
    assert "schedule" not in fwd_vsys or fwd_vsys["schedule"] is None

    discard = by_name["PBF-Discard"]
    assert discard["action"] == {"type": "discard"}
    assert "enforce_symmetric_return" not in discard

    no_pbf = by_name["PBF-NoPBF"]
    assert no_pbf["action"] == {"type": "no-pbf"}


def test_parse_application_override_rules(make_parser):
    p = _parser(make_parser, "application_override_rules.xml")
    rules = p.parse_application_override_rules()
    assert len(rules) == 1
    rule = rules[0]
    assert rule["name"] == "Override-443"
    assert rule["source_zones"] == ["Trust"]
    assert rule["destination_zones"] == ["Untrust"]
    assert rule["source_addresses"] == ["Internal-Network"]
    assert rule["port"] == "8443"
    assert rule["protocol"] == "tcp"
    assert rule["application"] == "https"
    assert rule["disabled"] is False
