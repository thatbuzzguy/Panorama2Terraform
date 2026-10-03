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
    assert len(rules) == 1
    rule = rules[0]
    assert rule["name"] == "Decrypt-HTTPS"
    assert rule["uuid"] == "abc-123"
    assert rule["source_zones"] == ["Trust"]
    assert rule["destination_zones"] == ["Untrust"]
    assert rule["source_addresses"] == ["Internal-Network"]
    assert rule["services"] == ["service-https"]
    assert rule["action"] == "ssl-forward-proxy"
    assert rule["type"] == "ssl-forward-proxy"
    assert rule["profile"] == "ssl-decrypt-policy"
    assert rule["log_setting"] == "default"
    assert rule["disabled"] is False


def test_parse_pbf_rules(make_parser):
    p = _parser(make_parser, "pbf_rules.xml")
    rules = p.parse_pbf_rules()
    by_name = {r["name"]: r for r in rules}
    assert list(by_name) == ["PBF-Forward", "PBF-Discard"]

    fwd = by_name["PBF-Forward"]
    assert fwd["source_zones"] == ["vsys1"]
    assert fwd["source_addresses"] == ["Internal-Network"]
    assert fwd["action"] == {
        "type": "forward",
        "nexthop_ip": "10.0.0.1",
        "egress_interface": "ethernet1/1",
    }
    assert fwd["enforce_symmetric_return"] is True

    discard = by_name["PBF-Discard"]
    assert discard["action"] == {"type": "discard"}
    assert "enforce_symmetric_return" not in discard


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
