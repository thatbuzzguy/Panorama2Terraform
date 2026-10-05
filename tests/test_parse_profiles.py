"""Unit tests for PanoramaParser profile parse methods."""


def _parser(make_parser, fixture_name):
    return make_parser(fixture_name)


def test_parse_security_profiles(make_parser):
    p = _parser(make_parser, "security_profiles.xml")
    profiles = p.parse_security_profiles()

    # All six profile kinds are present as empty lists.
    assert set(profiles) == {
        "antivirus",
        "vulnerability",
        "anti_spyware",
        "url_filtering",
        "file_blocking",
        "wildfire_analysis",
    }

    assert [a["name"] for a in profiles["antivirus"]] == ["AV-Default"]
    assert profiles["antivirus"][0]["description"] == "Default antivirus"
    assert [v["name"] for v in profiles["vulnerability"]] == ["VULN-Default"]
    assert [s["name"] for s in profiles["anti_spyware"]] == ["SPY-Default"]
    assert [u["name"] for u in profiles["url_filtering"]] == ["URL-Default"]
    assert [f["name"] for f in profiles["file_blocking"]] == ["FB-Default"]
    assert [w["name"] for w in profiles["wildfire_analysis"]] == ["WF-Default"]


def test_parse_security_profile_groups(make_parser):
    p = _parser(make_parser, "security_profile_groups.xml")
    groups = p.parse_security_profile_groups()
    assert len(groups) == 1
    group = groups[0]
    assert group["name"] == "Strict-Profile"
    assert group["virus"] == ["AV-Default"]
    assert group["spyware"] == ["SPY-Default"]
    assert group["vulnerability"] == ["VULN-Default"]
    assert group["url_filtering"] == ["URL-Default"]
    assert group["file_blocking"] == []
    assert group["wildfire_analysis"] == []


def test_parse_zone_protection_profiles(make_parser):
    p = _parser(make_parser, "zone_protection_profiles.xml")
    profiles = p.parse_zone_protection_profiles()
    assert len(profiles) == 1
    assert profiles[0]["name"] == "ZPP-Default"
    assert profiles[0]["description"] == "Default zone protection"


def test_parse_log_settings(make_parser):
    p = _parser(make_parser, "log_settings.xml")
    profiles = p.parse_log_settings()
    assert len(profiles) == 1
    assert profiles[0]["name"] == "Log-To-SIEM"
    assert profiles[0]["description"] == "Forward logs to SIEM"


def test_parse_qos_profiles(make_parser):
    p = _parser(make_parser, "qos_profiles.xml")
    profiles = p.parse_qos_profiles()
    assert len(profiles) == 1
    assert profiles[0]["name"] == "QOS-Default"
    assert profiles[0]["class_bandwidth_type"] == {
        "Class-1": {"priority": "high"},
        "Class-2": {"priority": "low"},
    }


def test_parse_tunnel_monitor_profiles(make_parser):
    p = _parser(make_parser, "tunnel_monitor_profiles.xml")
    profiles = p.parse_tunnel_monitor_profiles()
    assert len(profiles) == 1
    assert profiles[0]["name"] == "TM-Default"
    assert profiles[0]["interval"] == "30"
    assert profiles[0]["threshold"] == "3"
    assert profiles[0]["action"] == "reset"


def test_parse_pbf_monitor_profiles(make_parser):
    """PBF path monitoring profiles (F2.9): the panos_monitor_profile source.

    A different PAN-OS object from the IPsec tunnel monitor profile; the v2
    action is an enum (wait-recover | fail-over).
    """
    p = _parser(make_parser, "pbf_monitor_profiles.xml")
    profiles = p.parse_pbf_monitor_profiles()
    by_name = {prof["name"]: prof for prof in profiles}
    assert list(by_name) == ["PM-Branch", "PM-HQ"]

    branch = by_name["PM-Branch"]
    assert branch["action"] == "wait-recover"
    assert branch["interval"] == "10"
    assert branch["threshold"] == "5"

    hq = by_name["PM-HQ"]
    assert hq["action"] == "fail-over"
    assert hq["interval"] == "30"
    assert hq["threshold"] == "3"
