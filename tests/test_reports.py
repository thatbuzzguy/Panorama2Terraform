"""F3.9: the two operator-facing migration reports name the scope each entry came from.

Both reports group by one rule, shared through `TerraformGenerator`: device
group first, then the template or the device the export places the entry in,
then the object kind inside the section. A section prints only the scope the
export declares, so the parser's `Shared` fallback is never printed as a device
group for an entry whose scope is a template or a device.

The fixture (tests/fixtures/report_grouping.xml) puts the same names in two
device groups, which is the case a flat report cannot tell apart.
"""

import re

from conftest import FIXTURES_DIR, run_script

FIXTURE = 'report_grouping.xml'

# A report section: an 80-character rule, the title, the rule, the body.
SECTION_RE = re.compile(r'={80}\n(?P<title>[^\n]+)\n={80}\n(?P<body>.*?)(?=(?:={80}\n|\Z))', re.S)

# Section titles the grouping rule can produce.
SCOPE_TITLES = ('DEVICE GROUP:', 'TEMPLATE:', 'DEVICE:', 'SHARED SECTION')


def _generate(tmp_path, fixture=FIXTURE):
    """Run the converter and return the two reports as text."""
    result = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / fixture),
                        '--output-dir', str(tmp_path))
    assert result.returncode == 0, result.stderr
    return {f.name: f.read_text() for f in tmp_path.iterdir()}


def _sections(text: str) -> dict[str, str]:
    """Return {scope section title: body} for a grouped report."""
    return {title: body for title, body in SECTION_RE.findall(text)
            if title.startswith(SCOPE_TITLES)}


def _reports(tmp_path) -> tuple[str, str]:
    files = _generate(tmp_path)
    return files['INTERFACE_MIGRATION_REPORT.txt'], files['VPN_MIGRATION_REPORT.txt']


# --- interface report ------------------------------------------------------

def test_interface_report_has_one_section_per_scope(tmp_path):
    iface, _vpn = _reports(tmp_path)
    assert set(_sections(iface)) == {
        'DEVICE GROUP: Datacenter-FW',
        'DEVICE GROUP: Office-FW',
        'SHARED SECTION',
        'TEMPLATE: HQ-Networks',
        'TEMPLATE: DC-Networks / DEVICE (this device placeholder): localhost.localdomain',
        'DEVICE: fw-2.example.com',
    }


def test_each_interface_section_lists_only_its_own_entries(tmp_path):
    iface, _vpn = _reports(tmp_path)
    sections = _sections(iface)
    own = {
        'DEVICE GROUP: Office-FW': 'HQ uplink',
        'DEVICE GROUP: Datacenter-FW': 'Datacenter uplink',
        'SHARED SECTION': 'Shared management',
        'DEVICE: fw-2.example.com': 'Own config',
    }
    for title, marker in own.items():
        assert marker in sections[title]
        # The same entry must not appear under another section.
        for other, body in sections.items():
            if other != title:
                assert marker not in body


def test_same_named_interface_appears_under_each_device_group(tmp_path):
    """The F3.9 point: two ethernet1/1 entries, one per device group."""
    iface, _vpn = _reports(tmp_path)
    sections = _sections(iface)
    occurrences = [title for title, body in sections.items() if 'Interface: ethernet1/1' in body]
    assert sorted(occurrences) == ['DEVICE GROUP: Datacenter-FW', 'DEVICE GROUP: Office-FW']


def test_template_and_device_scopes_are_not_printed_as_a_device_group(tmp_path):
    iface, vpn = _reports(tmp_path)
    for report in (iface, vpn):
        for title, body in _sections(report).items():
            if title.startswith(('TEMPLATE:', 'DEVICE:')):
                assert 'DEVICE GROUP' not in title
                assert 'DEVICE GROUP' not in body


def test_shared_section_is_named_shared(tmp_path):
    iface, vpn = _reports(tmp_path)
    assert 'Interface: ethernet1/9' in _sections(iface)['SHARED SECTION']
    assert 'Gateway: GW-Shared' in _sections(vpn)['SHARED SECTION']
    # The shared section is the PAN-OS shared section, not a device group.
    assert 'DEVICE GROUP' not in _sections(iface)['SHARED SECTION']


def test_placeholder_device_is_not_named_as_a_firewall(tmp_path):
    iface, _vpn = _reports(tmp_path)
    title = next(t for t in _sections(iface) if 'localhost.localdomain' in t)
    assert 'this device placeholder' in title


def test_interface_counts_are_per_section(tmp_path):
    iface, _vpn = _reports(tmp_path)
    assert 'ETHERNET INTERFACES (2)' in _sections(iface)['DEVICE GROUP: Datacenter-FW']
    assert 'ETHERNET INTERFACES (1)' in _sections(iface)['DEVICE GROUP: Office-FW']


def test_vsys_is_printed_only_when_the_export_declares_one(tmp_path):
    iface, vpn = _reports(tmp_path)
    # One declared vsys in the fixture, so one vsys line per report, and it
    # lands in the section that owns it.
    assert iface.count('Vsys:') == 1
    assert vpn.count('Vsys:') == 1
    assert 'Vsys: vsys2' in _sections(iface)['DEVICE GROUP: Datacenter-FW']
    assert 'Vsys: vsys2' in _sections(vpn)['DEVICE GROUP: Datacenter-FW']


def test_interface_footer_is_one_shared_block(tmp_path):
    iface, _vpn = _reports(tmp_path)
    for footer in ('MIGRATION CHECKLIST', 'PLATFORM MIGRATION NOTES'):
        assert iface.count(footer) == 1
    titles = [title for title, _body in SECTION_RE.findall(iface)]
    # The footer is one shared block after every scope section.
    assert titles[-2:] == ['MIGRATION CHECKLIST', 'PLATFORM MIGRATION NOTES']
    assert any(title.startswith(SCOPE_TITLES) for title in titles[:-2])


# --- VPN report ------------------------------------------------------------

def test_vpn_report_has_one_section_per_scope(tmp_path):
    _iface, vpn = _reports(tmp_path)
    assert set(_sections(vpn)) == {
        'DEVICE GROUP: Datacenter-FW',
        'DEVICE GROUP: Office-FW',
        'SHARED SECTION',
    }


def test_each_vpn_section_lists_only_its_own_entries(tmp_path):
    _iface, vpn = _reports(tmp_path)
    sections = _sections(vpn)
    own = {
        'DEVICE GROUP: Office-FW': '203.0.1.10',
        'DEVICE GROUP: Datacenter-FW': '203.0.1.11',
        'SHARED SECTION': '203.0.1.12',
    }
    for title, marker in own.items():
        assert marker in sections[title]
        for other, body in sections.items():
            if other != title:
                assert marker not in body


def test_same_named_gateway_appears_under_each_device_group(tmp_path):
    _iface, vpn = _reports(tmp_path)
    sections = _sections(vpn)
    occurrences = [title for title, body in sections.items() if '\nGateway: GW-Common' in body]
    assert sorted(occurrences) == ['DEVICE GROUP: Datacenter-FW', 'DEVICE GROUP: Office-FW']


def test_pre_shared_key_warning_survives_at_the_top(tmp_path):
    _iface, vpn = _reports(tmp_path)
    warning = vpn.index('CRITICAL: PRE-SHARED KEY MANAGEMENT')
    first_section = min(vpn.index(title) for title in _sections(vpn))
    assert warning < first_section
    # The warning is shared, so it is printed once, not per section.
    assert vpn.count('CRITICAL: PRE-SHARED KEY MANAGEMENT') == 1


def test_per_gateway_placeholder_line_survives(tmp_path):
    _iface, vpn = _reports(tmp_path)
    # One line per pre-shared-key gateway, inside its own section.
    assert vpn.count('***MUST BE UPDATED***') == 4
    for _title, body in _sections(vpn).items():
        # 'Gateway: ' at the entry line, not the tunnel's IKE Gateway reference.
        assert body.count('***MUST BE UPDATED***') == body.count('\nGateway: ')
        assert '***CHANGE_ME***' in body


def test_vpn_footer_is_one_shared_block(tmp_path):
    _iface, vpn = _reports(tmp_path)
    for footer in ('KEY MANAGEMENT BEST PRACTICES', 'MIGRATION CHECKLIST',
                   'IMPORTANT SECURITY NOTES'):
        assert vpn.count(footer) == 1
    titles = [title for title, _body in SECTION_RE.findall(vpn)]
    assert titles[-3:] == ['KEY MANAGEMENT BEST PRACTICES', 'MIGRATION CHECKLIST',
                           'IMPORTANT SECURITY NOTES']
    assert any(title.startswith(SCOPE_TITLES) for title in titles[:-3])


# --- shared rule and determinism -------------------------------------------

def test_both_reports_use_the_same_grouping_rule(converter_module, make_parser, tmp_path):
    """The section titles come from one helper, so the reports cannot drift."""
    parser = make_parser(FIXTURE)
    gen = converter_module.TerraformGenerator(str(tmp_path))
    header = converter_module.TerraformGenerator._report_section_header

    iface_report, vpn_report = _reports(tmp_path)
    iface_titles = {header(gen._report_scope_path(entry)) for entry in parser.parse_interfaces()}
    vpn_titles = {header(gen._report_scope_path(entry))
                  for entry in parser.parse_ike_gateways() + parser.parse_ipsec_tunnels()}
    assert set(_sections(iface_report)) == iface_titles
    assert set(_sections(vpn_report)) == vpn_titles


def test_sections_and_entries_are_in_a_stable_order(tmp_path):
    first = _generate(tmp_path)
    second = _generate(tmp_path / 'again')
    assert first['INTERFACE_MIGRATION_REPORT.txt'] == second['INTERFACE_MIGRATION_REPORT.txt']
    assert first['VPN_MIGRATION_REPORT.txt'] == second['VPN_MIGRATION_REPORT.txt']


def test_no_report_when_there_is_nothing_to_report(tmp_path):
    """A fixture with no interface and no VPN entry writes neither report."""
    files = _generate(tmp_path, 'address_objects.xml')
    assert 'INTERFACE_MIGRATION_REPORT.txt' not in files
    assert 'VPN_MIGRATION_REPORT.txt' not in files
