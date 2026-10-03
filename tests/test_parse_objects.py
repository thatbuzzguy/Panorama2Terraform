"""Unit tests for PanoramaParser object-level parse methods.

Each test uses an isolated XML fixture that mirrors the real Panorama
config structure. These tests pin down the parser data contract that the
Terraform generator depends on.
"""

def _parser(make_parser, fixture_name):
    return make_parser(fixture_name)


def test_parse_device_groups(make_parser):
    p = _parser(make_parser, "device_groups.xml")
    dgs = p.parse_device_groups()
    assert [d["name"] for d in dgs] == ["Production-DG", "Dev-DG"]
    assert dgs[0]["description"] == "Production device group"
    assert dgs[1]["description"] is None


def test_parse_tags(make_parser):
    p = _parser(make_parser, "tags.xml")
    tags = p.parse_tags()
    by_name = {t["name"]: t for t in tags}
    assert by_name["env-prod"]["color"] == "green"
    assert by_name["env-prod"]["comments"] == "Production environment"
    assert by_name["web"]["color"] == "blue"
    assert by_name["web"]["comments"] is None


def test_parse_regions(make_parser):
    p = _parser(make_parser, "regions.xml")
    regions = p.parse_regions()
    assert len(regions) == 1
    assert regions[0]["name"] == "North-America"
    assert regions[0]["addresses"] == ["US", "CA", "MX"]


def test_parse_custom_url_categories(make_parser):
    p = _parser(make_parser, "custom_url_categories.xml")
    cats = p.parse_custom_url_categories()
    assert len(cats) == 1
    assert cats[0]["name"] == "blocked-sites"
    assert cats[0]["type"] == "block"
    assert cats[0]["list"] == ["example.com", "bad.example.org"]
    assert cats[0]["description"] == "Blocked websites"


def test_parse_application_groups(make_parser):
    p = _parser(make_parser, "application_groups.xml")
    groups = p.parse_application_groups()
    assert len(groups) == 1
    assert groups[0]["name"] == "web-apps"
    assert groups[0]["members"] == ["http", "https"]


def test_parse_application_filters(make_parser):
    p = _parser(make_parser, "application_filters.xml")
    filters = p.parse_application_filters()
    assert len(filters) == 1
    assert filters[0]["name"] == "high-risk-web"
    assert filters[0]["category"] == ["web-proxy", "file-transfer"]
    assert filters[0]["risk"] == ["high"]
    assert filters[0]["evasive"] == "yes"


def test_parse_external_lists(make_parser):
    p = _parser(make_parser, "external_lists.xml")
    lists = p.parse_external_lists()
    assert len(lists) == 1
    assert lists[0]["name"] == "threat-ips"
    assert lists[0]["type"] == "ip"
    assert lists[0]["url"] == "https://threat.example.com/list.txt"
    assert lists[0]["recurring"] == "hourly"
    assert lists[0]["description"] == "Threat IP list"


def test_parse_address_objects(make_parser):
    p = _parser(make_parser, "address_objects.xml")
    addrs = p.parse_address_objects()
    by_name = {a["name"]: a for a in addrs}

    # Reference-only entries (id only, no address content) are skipped.
    assert "Reference-Only" not in by_name
    assert len(addrs) == 3

    web = by_name["Web-Server-1"]
    assert web["type"] == "ip-netmask"
    assert web["value"] == "10.1.1.10/32"
    assert web["description"] == "Web server"
    assert web["tags"] == ["Production", "Web"]

    assert by_name["Web-Range"]["type"] == "ip-range"
    assert by_name["Web-Range"]["value"] == "10.1.2.0-10.1.2.255"

    assert by_name["External-API"]["type"] == "fqdn"
    assert by_name["External-API"]["value"] == "api.example.com"


def test_parse_address_objects_device_group_override(make_parser):
    """A device-group definition must win over a shared reference-only entry.

    Regression test for the v4.0.1 bug where device-group-specific
    definitions were silently replaced by shared reference-only entries.
    """
    p = _parser(make_parser, "address_objects_dg_override.xml")
    addrs = p.parse_address_objects()
    assert len(addrs) == 1
    web = addrs[0]
    assert web["name"] == "Web-Server-1"
    assert web["value"] == "192.168.1.10/32"
    assert web["description"] == "DG-specific web server"


def test_parse_address_groups(make_parser):
    p = _parser(make_parser, "address_groups.xml")
    groups = p.parse_address_groups()
    by_name = {g["name"]: g for g in groups}

    # Reference-only entries are skipped.
    assert "Reference-Only" not in by_name
    assert len(groups) == 2

    static = by_name["Web-Servers"]
    assert static["static_members"] == ["Web-Server-1", "Web-Server-2"]
    assert static["description"] == "All web servers"

    # A dynamic group has no static members but is marked as dynamic.
    dynamic = by_name["Dynamic-Web"]
    assert dynamic["static_members"] == []
    assert dynamic["dynamic_filter"] is not None


def test_parse_service_objects(make_parser):
    p = _parser(make_parser, "service_objects.xml")
    services = p.parse_service_objects()
    by_name = {s["name"]: s for s in services}

    assert by_name["TCP-8080"]["protocol"] == "tcp"
    assert by_name["TCP-8080"]["port"] == "8080"
    assert by_name["TCP-8080"]["description"] == "Custom HTTP port"

    assert by_name["UDP-514"]["protocol"] == "udp"
    assert by_name["UDP-514"]["port"] == "514"


def test_parse_service_groups(make_parser):
    p = _parser(make_parser, "service_groups.xml")
    groups = p.parse_service_groups()
    assert len(groups) == 1
    assert groups[0]["name"] == "Web-Services"
    assert groups[0]["members"] == ["service-http", "TCP-8080"]
    assert groups[0]["description"] == "Web services"
