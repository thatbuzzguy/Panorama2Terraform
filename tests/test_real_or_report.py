"""F2.9: real resources or explicit reports.

The comment-only .tf generators are gone. Every Panorama area is now
either a real provider v2.0.14 resource or an explicit entry in
MANUAL_SETUP_REPORT.txt that names the captured data and the reason it
is not emitted:

- decryption rules -> panos_decryption_policy_rules, one resource per
  rule, chained per device group (F2.5 position semantics);
- PBF rules -> panos_pbf_policy_rules, the same per-rule chain model,
  with the full single-choice action set (forward, forward_to_vsys,
  discard, no_pbf) and optional path monitoring on the forward action;
- PBF path monitoring profiles -> panos_monitor_profile (the v2 resource
  manages network/profiles/monitor-profile, template-scoped);
- application override rules -> report (no v2 resource);
- QoS profiles -> report (no v2 resource);
- IPsec tunnel monitor profiles -> report (no v2 resource:
  panos_monitor_profile is a different PAN-OS object);
- schedules -> report (panos_schedule exists, but only entry names are
  parsed and v2.0.14 has no monthly schedule support);
- log forwarding profiles -> report (v2 resource exists, body not parsed);
- zone protection profiles -> report (v2 resource exists, body not parsed).
"""

from pathlib import Path

from test_policy_order import _check_chain_semantics, _rule_blocks

from conftest import FIXTURES_DIR, run_script

# The legacy comment-only placeholder text must be gone from all output.
PLACEHOLDER_TEXT = 'Manual Terraform configuration is required'

# The .tf files that used to contain comments only. They must not be
# written anymore: their data lives in MANUAL_SETUP_REPORT.txt.
REMOVED_TF_FILES = (
    'application_override_rules.tf',
    'qos_profiles.tf',
    'tunnel_monitor_profiles.tf',
    'schedules.tf',
    'log_settings.tf',
    'zone_protection_profiles.tf',
)


def _convert(fixture_name: str, tmp_path: Path) -> Path:
    """Run the converter CLI on one fixture. Return the output directory."""
    out = tmp_path / fixture_name
    proc = run_script(
        'panorama_to_terraform.py', str(FIXTURES_DIR / fixture_name),
        '--output-dir', str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return out


# --- Decryption rules: real v2 resources ------------------------------------

def test_decryption_rules_emit_real_v2_resources(tmp_path):
    """One panos_decryption_policy_rules resource per rule, chained, full body."""
    out = _convert('decryption_rules.xml', tmp_path)
    text = (out / 'decryption_rules.tf').read_text(encoding='utf-8')

    blocks = _rule_blocks(text, 'panos_decryption_policy_rules')
    _check_chain_semantics(
        blocks, 'panos_decryption_policy_rules',
        [('Production-DG', ['Decrypt-HTTPS', 'Decrypt-SSH'])],
        'decryption fixture')

    # Rule body: the parser's full capture must reach the output
    assert 'profile = "ssl-decrypt-policy"' in text
    assert 'profile = "ssh-decrypt-profile"' in text
    assert 'log_setting = "default"' in text
    # log-start / log-end map to the v2 log_success / log_fail attributes
    assert 'log_success = true' in text
    assert 'log_fail = true' in text
    assert 'source_zones = [ "Trust" ]' in text
    assert 'destination_zones = [ "Untrust" ]' in text
    assert 'services = [ "service-https" ]' in text
    assert 'description = "Decrypt HTTPS"' in text

    # The v2 action enum: both the modern export (action=decrypt) and the
    # legacy export (action=ssh-proxy, no type block) normalize to the v2
    # enum value plus the matching type block
    assert 'action = "decrypt"' in text
    assert text.count('action = "decrypt"') == 2
    assert 'ssl_forward_proxy = {}' in text
    assert 'ssh_proxy = {}' in text
    # No comment-only placeholder output
    assert PLACEHOLDER_TEXT not in text


# --- PBF rules: real v2 resources -------------------------------------------

def test_pbf_rules_emit_chained_v2_resources(tmp_path):
    """One panos_pbf_policy_rules resource per rule, chained in XML order."""
    out = _convert('pbf_rules.xml', tmp_path)
    text = (out / 'pbf_rules.tf').read_text(encoding='utf-8')

    blocks = _rule_blocks(text, 'panos_pbf_policy_rules')
    _check_chain_semantics(
        blocks, 'panos_pbf_policy_rules',
        [('Production-DG', ['PBF-Forward', 'PBF-ForwardVsys',
                            'PBF-Discard', 'PBF-NoPBF'])],
        'pbf fixture')

    # The full single-choice action set reaches the output (v2 names)
    assert 'ip_address = "10.0.0.1"' in text
    assert 'egress_interface = "ethernet1/1"' in text
    assert 'forward_to_vsys = "vsys2"' in text
    assert 'discard = {}' in text
    assert 'no_pbf = {}' in text
    # Path monitoring on the forward action
    assert 'profile = "PM-Branch"' in text
    assert 'ip_address = "10.1.1.1"' in text
    assert 'disable_if_unreachable = true' in text
    # Enforce symmetric return and the optional schedule
    assert 'enforce_symmetric_return' in text
    assert 'enabled = true' in text
    assert 'schedule = "Business-Hours"' in text
    assert PLACEHOLDER_TEXT not in text


# --- PBF path monitoring profiles: real v2 resources -------------------------

def test_pbf_monitor_profiles_emit_real_v2_resources(tmp_path):
    """panos_monitor_profile with the complete parsed profile body."""
    out = _convert('pbf_monitor_profiles.xml', tmp_path)
    text = (out / 'monitor_profiles.tf').read_text(encoding='utf-8')

    assert text.count('resource "panos_monitor_profile"') == 2
    assert 'name = "PM-Branch"' in text
    assert 'name = "PM-HQ"' in text
    # Both enum values pass through
    assert 'action = "wait-recover"' in text
    assert 'action = "fail-over"' in text
    assert 'interval = 10' in text
    assert 'interval = 30' in text
    assert 'threshold = 5' in text
    assert 'threshold = 3' in text
    # Template-scoped location; the default "Shared" template convention
    assert 'template' in text
    assert 'name = "Shared"' in text
    assert PLACEHOLDER_TEXT not in text


# --- Report-only areas: explicit MANUAL_SETUP_REPORT.txt ---------------------

def test_report_only_areas_go_to_manual_setup_report(tmp_path):
    """The five report areas name their data and reason in the report."""
    out = _convert('kitchen_sink.xml', tmp_path)
    report = (out / 'MANUAL_SETUP_REPORT.txt').read_text(encoding='utf-8')

    # Application override rules: no v2 resource, rule details listed
    assert '--- Application Override Rules (no v2 resource) ---' in report
    assert 'Override-443' in report
    assert 'port=8443' in report
    assert 'application=https' in report

    # QoS profiles: no v2 resource, profile and class details listed
    assert '--- QoS Profiles (no v2 resource) ---' in report
    assert 'QOS-Default' in report
    assert 'Class-1(high)' in report

    # IPsec tunnel monitor profiles: no v2 resource; the report must state
    # that panos_monitor_profile is a different PAN-OS object
    assert '--- IPsec Tunnel Monitor Profiles (no v2 resource) ---' in report
    assert 'TM-Default' in report
    assert 'panos_monitor_profile' in report

    # Schedules: v2 resource exists, entry body not parsed
    assert '--- Schedules (v2 resource exists, not emitted) ---' in report
    assert 'Business-Hours: type=recurring, entries=Weekdays' in report
    assert 'panos_schedule' in report

    # Log forwarding: v2 resource exists, body not parsed
    assert '--- Log Forwarding Profiles (v2 resource exists, not emitted) ---' in report
    assert 'Log-To-SIEM' in report
    assert 'panos_log_forwarding_profile' in report

    # Zone protection: v2 resource exists, body not parsed
    assert '--- Zone Protection Profiles (v2 resource exists, not emitted) ---' in report
    assert 'ZPP-Default' in report
    assert 'panos_zone_protection_profile' in report

    # The comment-only .tf files are no longer written
    for name in REMOVED_TF_FILES:
        assert not (out / name).exists(), f'{name} must not be written anymore'


def test_no_report_when_no_report_only_items(tmp_path):
    """A config without report-only areas writes no MANUAL_SETUP_REPORT.txt.

    Pins the early-return: the report is explicit, never an empty
    checklist.
    """
    out = _convert('security_rules.xml', tmp_path)
    assert not (out / 'MANUAL_SETUP_REPORT.txt').exists()
