"""F4.4 property-level coverage: what a matrix row reads, and what no output read.

Four groups:

1. The read record. `mark` stores the captured object as a `RecordingDict`, which records
   the keys an output reads from it. The record starts when the run starts the outputs, so
   a key the parse method read off the XML element is not a property an output used.
2. Parity with the matrix. For each matrix row, the properties the row declares equal the
   keys the corpus outputs read from the entries that row covers. This is a measurement
   over the corpus, not a restatement of the matrix.
3. The scan. Captured fields minus the keys an output read are findings, and the corpus
   findings are pinned below. Each is recorded as a follow-up in backlog.md.
4. The report section. The findings print in their own section, grouped by the F3.9 scope
   rule, byte-identical between runs. A finding is an operator action, so it does not
   change the exit code, which the F4.1 gate still decides.

The scan scope is the entries a matrix row covers. A report, inventory, bookkeeping,
count-only, or nested-block container has no matrix row, so the scan does not report it;
those field gaps stay in backlog.md.
"""

import container_coverage
import entry_coverage
import xml_input
from conftest import FIXTURES_DIR, run_pipeline, run_script
from resource_mapping import COVERAGE_MATRIX

ROWS = list(COVERAGE_MATRIX)

# A fixture with findings, for the report tests.
FINDING_FIXTURE = 'pbf_rules.xml'

# A fixture with both a gap row and a finding, so the section order is pinned.
BOTH_FIXTURE = 'kitchen_sink.xml'

# The corpus findings, from the run: (object type, entry name, matrix row, properties no
# output read). Each one is an operator action, and each is recorded in backlog.md.
CORPUS_FINDINGS = {
    'address_objects.xml': [
        # `declared_type` is read only by the manual report, for an address the converter
        # does not emit, so an emitted address row never reads it.
        ('address', 'Wildcard-Net', 'panos_address', ('declared_type',)),
        # A report-only address has no emitter, so its description is never read.
        ('address', 'Country-US', 'panos_address', ('description',)),
    ],
    'decryption_rules.xml': [
        ('devices/entry/device-group/entry/pre-rulebase/decryption/rules', 'Decrypt-HTTPS',
         'panos_decryption_policy_rules', ('uuid',)),
        ('devices/entry/device-group/entry/pre-rulebase/decryption/rules', 'Decrypt-SSH',
         'panos_decryption_policy_rules', ('uuid',)),
    ],
    'dependency_wiring.xml': [
        ('devices/entry/vsys/entry/network/ike/crypto-profiles/ipsec-crypto-profiles', 'dw-ipsec',
         'panos_ipsec_crypto_profile', ('protocol',)),
    ],
    'edge_ipv6.xml': [
        ('devices/entry/vsys/entry/address', 'v6-host', 'panos_address', ('declared_type',)),
        ('devices/entry/vsys/entry/address', 'v6-range', 'panos_address', ('declared_type',)),
    ],
    'ipsec_crypto_profiles.xml': [
        # The parse reads `protocol` off the XML element to choose the shape, so no output
        # reads it.
        ('devices/entry/vsys/entry/network/ike/crypto-profiles/ipsec-crypto-profiles',
         'IPSEC-DEFAULT', 'panos_ipsec_crypto_profile', ('protocol',)),
    ],
    'kitchen_sink.xml': [
        ('address', 'Web-Wildcard', 'panos_address', ('declared_type',)),
        ('address', 'Country-US', 'panos_address', ('description',)),
        # The v2 service group has no description attribute, so nothing reads it.
        ('service-group', 'Web-Services', 'panos_service_group', ('description',)),
        ('devices/entry/device-group/entry/pre-rulebase/decryption/rules', 'Decrypt-HTTPS',
         'panos_decryption_policy_rules', ('uuid',)),
        ('devices/entry/device-group/entry/pre-rulebase/pbf/rules', 'PBF-Forward',
         'panos_pbf_policy_rules', ('uuid',)),
        ('devices/entry/device-group/entry/pre-rulebase/pbf/rules', 'PBF-Discard',
         'panos_pbf_policy_rules', ('uuid',)),
        ('devices/entry/network/ike/crypto-profiles/ipsec-crypto-profiles', 'IPSEC-DEFAULT',
         'panos_ipsec_crypto_profile', ('protocol',)),
    ],
    'pbf_rules.xml': [
        ('devices/entry/device-group/entry/pre-rulebase/pbf/rules', 'PBF-Forward',
         'panos_pbf_policy_rules', ('uuid',)),
        ('devices/entry/device-group/entry/pre-rulebase/pbf/rules', 'PBF-ForwardVsys',
         'panos_pbf_policy_rules', ('uuid',)),
        ('devices/entry/device-group/entry/pre-rulebase/pbf/rules', 'PBF-Discard',
         'panos_pbf_policy_rules', ('uuid',)),
        ('devices/entry/device-group/entry/pre-rulebase/pbf/rules', 'PBF-NoPBF',
         'panos_pbf_policy_rules', ('uuid',)),
    ],
    'service_groups.xml': [
        ('service-group', 'Web-Services', 'panos_service_group', ('description',)),
    ],
}


def _corpus_ledgers(converter_module, tmp_path):
    """(fixture name, ledger) for every fixture the run accepted."""
    for path in sorted(FIXTURES_DIR.glob('*.xml')):
        parser = run_pipeline(converter_module, path.name, tmp_path)
        if parser is None:
            continue  # the hostile fixtures are refused before the parse
        yield path.name, parser.ledger


def _read_set(ledger) -> dict:
    """{matrix resource: keys an output read}, measured for the entries that row covers."""
    measured = {}
    for entry in ledger.entries():
        mark = ledger.mark_for(entry)
        if mark is None or not isinstance(mark['captured'], entry_coverage.RecordingDict):
            continue
        container = ledger.parents.get(entry)
        if container is None:
            continue
        row = entry_coverage.covering_row(
            container_coverage.section_path(container, ledger.parents))
        if row is None:
            continue
        resource = entry_coverage.row_detail(row)
        if resource not in entry_coverage.MATRIX_BY_RESOURCE:
            continue
        # The entry name and the five scope facts are the row identity, not content the
        # emitter reads, so the parity check compares the captured fields only.
        measured.setdefault(resource, set()).update(
            set(mark['captured'].used_keys()) - entry_coverage.NON_FIELD_KEYS)
    return measured


def _finding_rows(ledger) -> list:
    return [(row['container'], row['name'], row['resource'], row['unused_properties'])
            for row in ledger.property_findings()]


# --- 1. The read record ----------------------------------------------------

def test_read_record_tracks_the_keys_an_output_reads(converter_module, tmp_path):
    """`mark` returns the recorded object, and a read through it counts after the start."""
    parser = converter_module.PanoramaParser(xml_input.parse_xml(FIXTURES_DIR / 'tags.xml'))
    entry = next(e for e in parser.root.iter() if e.tag == 'entry' and e.get('name') == 'env-prod')
    recorded = parser.mark(entry, {'name': 'env-prod', 'color': 'light blue'})
    assert recorded.used_keys() == (), 'the record must stay off during the parse'
    parser.ledger.start_recording()
    recorded.get('color')
    assert recorded.used_keys() == ('color',)


def test_parse_time_read_is_not_a_property_use(converter_module):
    """A key the parse method read off the XML element is not a property the output used."""
    parser = converter_module.PanoramaParser(
        xml_input.parse_xml(FIXTURES_DIR / 'ipsec_crypto_profiles.xml'))
    parser.parse_ipsec_crypto_profiles()
    entry = next(e for e in parser.ledger.entries() if e.get('name') == 'IPSEC-DEFAULT')
    mark = parser.ledger.mark_for(entry)
    assert 'protocol' in parser.ledger.captured_fields(mark)
    assert 'protocol' not in mark['captured'].used_keys()


# --- 2. Parity with the matrix --------------------------------------------

def test_measured_reads_equal_the_declared_properties(converter_module, tmp_path):
    """For each matrix row, the properties the outputs read equal the row's declared list.

    Two rows have no read of their own to measure:
    `panos_aggregate_layer3_subinterface`, because the container table maps an aggregate
    subinterface to the ethernet subinterface row, so no corpus entry reaches it; and
    `panos_device_group_parent`, because the entry that feeds the parent record is covered by the
    device group row (F6.5 decision 4: one entry can feed two blocks, and the scan measures an
    entry against the row that covers its container). Both are grounded by the emitter test in
    tests/test_coverage_matrix.py, and the table limit is recorded in backlog.md.

    `panos_vsys` is measured with the empty set: its block carries the entry name and the location
    only, so the row declares no property and parity holds only while a fixture places a virtual
    system inside a template (`scope_objects.xml`).
    """
    measured = {}
    for _fixture, ledger in _corpus_ledgers(converter_module, tmp_path):
        for resource, keys in _read_set(ledger).items():
            measured.setdefault(resource, set()).update(keys)

    unmeasured = sorted({row['resource'] for row in ROWS} - set(measured))
    assert unmeasured == ['panos_aggregate_layer3_subinterface', 'panos_device_group_parent'], \
        unmeasured

    drift = {row['resource']: (sorted(row['properties']), sorted(measured[row['resource']]))
             for row in ROWS
             if row['resource'] in measured and set(row['properties']) != measured[row['resource']]}
    assert drift == {}, drift


def test_the_scan_measures_an_export_rule_and_not_a_scalar_level(converter_module, tmp_path):
    """F7.3: an export-rule entry is in the scan scope, and a single-object level is not.

    `mark` wraps the object it stores, so only a marked object can record a read. `_protocol_level` builds the
    three single-object levels as plain dicts inside the router's `protocol` field, so nothing is measured for
    them and the row is grounded by the table instead. An export rule is an entry, so the container table names
    a row for its container and the scan measures its fields against the router row.
    """
    parser = run_pipeline(converter_module, 'ospfv3.xml', tmp_path)
    assert parser is not None, 'ospfv3.xml'
    ledger = parser.ledger
    rule = next(e for e in ledger.entries() if e.get('name') == 'static-af')
    row = entry_coverage.matrix_row_for(
        container_coverage.section_path(ledger.parents[rule], ledger.parents, ledger.source))
    assert row is not None and row['resource'] == 'panos_virtual_router', row
    recorded = ledger.mark_for(rule)['captured']
    assert isinstance(recorded, entry_coverage.RecordingDict), recorded
    assert sorted(set(recorded.used_keys()) - entry_coverage.NON_FIELD_KEYS) == [
        'metric', 'new_path_type', 'new_tag'], recorded.used_keys()
    level = ledger.mark_for(next(e for e in ledger.entries() if e.get('name') == 'edge-af'))['captured']
    assert not isinstance(level['protocol']['ospfv3']['timers'], entry_coverage.RecordingDict), level


def test_the_scan_measures_an_ospf_export_rule_and_not_a_scalar_level(converter_module, tmp_path):
    """F7.9: the `ospf` export rule is in the scan scope, and the three single-object levels are not.

    `CONTAINER_TABLE` names `protocol/ospf/export-rules`, so the export rule the fixture states is measured
    against the router row, and the properties the row declares are the fields the emitter reads from it. The
    three single-object levels hold no entry, so `_protocol_level` builds them as plain dicts, which record
    nothing, and those rows are grounded by the table instead. The fixture states every field the four new rows
    declare, so the run reports no finding.
    """
    parser = run_pipeline(converter_module, 'ospf.xml', tmp_path)
    assert parser is not None, 'ospf.xml'
    ledger = parser.ledger
    rule = next(e for e in ledger.entries() if e.get('name') == 'export-static')
    path = container_coverage.section_path(ledger.parents[rule], ledger.parents, ledger.source)
    assert entry_coverage.covering_row(path).path == 'protocol/ospf/export-rules', path
    row = entry_coverage.matrix_row_for(path)
    assert row is not None and row['resource'] == 'panos_virtual_router', row
    recorded = ledger.mark_for(rule)['captured']
    assert isinstance(recorded, entry_coverage.RecordingDict), recorded
    assert sorted(set(recorded.used_keys()) - entry_coverage.NON_FIELD_KEYS) == [
        'metric', 'new_path_type', 'new_tag'], recorded.used_keys()
    level = ledger.mark_for(next(e for e in ledger.entries() if e.get('name') == 'default'))['captured']
    for field in ('timers', 'global_bfd', 'graceful_restart'):
        assert not isinstance(level['protocol']['ospf'][field], entry_coverage.RecordingDict), field
    assert ledger.property_findings() == [], ledger.property_findings()


def test_the_scan_measures_the_area_level_and_not_an_entry_inside_an_entry(converter_module, tmp_path):
    """F7.4: the area dict is in the scan scope, and the entries inside a property level are not.

    The area entry is an entry whose container the container table covers, so the scan measures the fields
    the row for `protocol/ospf/area` states, and `virtual_link` joins the measured set through the emitter
    reading the table. A neighbor entry sits inside an interface entry, so its section path holds an entry
    segment the row path cannot match, and the level stays grounded by the table: the router row declares no
    property for it.
    """
    parser = run_pipeline(converter_module, 'ospf.xml', tmp_path)
    assert parser is not None, 'ospf.xml'
    ledger = parser.ledger
    area = next(e for e in ledger.entries() if e.get('name') == '0.0.0.0')
    row = entry_coverage.matrix_row_for(
        container_coverage.section_path(ledger.parents[area], ledger.parents, ledger.source))
    assert row is not None and row['resource'] == 'panos_virtual_router', row
    recorded = ledger.mark_for(area)['captured']
    assert sorted(set(recorded.used_keys()) - entry_coverage.NON_FIELD_KEYS) == [
        'interface', 'range', 'type', 'virtual_link'], recorded.used_keys()
    neighbor = next(e for e in ledger.entries() if e.get('name') == '10.0.0.2'
                    and ledger.parents[e].tag == 'neighbor')
    path = container_coverage.section_path(ledger.parents[neighbor], ledger.parents, ledger.source)
    assert entry_coverage.matrix_row_for(path) is None, path
    router_row = next(r for r in ROWS if r['resource'] == 'panos_virtual_router')
    assert 'virtual_link' in router_row['properties'] and 'neighbor' not in router_row['properties'], \
        router_row['properties']


def test_the_scan_measures_a_rip_entry_and_not_a_level_inside_it(converter_module, tmp_path):
    """F7.5: an interface entry is in the scan scope, and the levels inside it are not.

    `protocol/rip/interfaces` is a `string_list` level, so its entries are marked and the scan measures the
    fields the row states for them against the router row. `bfd` is measured as the field of the entry, not as
    the level inside it, because `_protocol_level` builds the level dict as a plain dict, which records nothing.
    `timers` and `global_bfd` are single-object levels: no entry, so no mark, and the row is grounded by the
    table instead.
    """
    parser = run_pipeline(converter_module, 'rip.xml', tmp_path)
    assert parser is not None, 'rip.xml'
    ledger = parser.ledger
    entry = next(e for e in ledger.entries() if e.get('name') == 'ethernet1/2')
    row = entry_coverage.matrix_row_for(
        container_coverage.section_path(ledger.parents[entry], ledger.parents, ledger.source))
    assert row is not None and row['resource'] == 'panos_virtual_router', row
    recorded = ledger.mark_for(entry)['captured']
    assert isinstance(recorded, entry_coverage.RecordingDict), recorded
    assert sorted(set(recorded.used_keys()) - entry_coverage.NON_FIELD_KEYS) == [
        'authentication', 'bfd', 'default_route', 'enable', 'mode'], recorded.used_keys()
    level = ledger.mark_for(next(e for e in ledger.entries() if e.get('name') == 'default'))['captured']
    for field in ('timers', 'global_bfd'):
        assert not isinstance(level['protocol']['rip'][field], entry_coverage.RecordingDict), field
    assert not isinstance(recorded['bfd'], entry_coverage.RecordingDict), recorded['bfd']
    router_row = next(r for r in ROWS if r['resource'] == 'panos_virtual_router')
    for field in ('authentication', 'bfd', 'default_route', 'enable', 'mode'):
        assert field in router_row['properties'], router_row['properties']


def test_the_scan_measures_a_policy_entry_and_not_a_level_inside_it(converter_module, tmp_path):
    """F7.6: an entry at one of the four policy levels is in the scan scope, and a level inside it is not.

    The four entry levels the container table names are measured against the router row, so the properties their
    rows declare join the measured set. A filter entry lives inside an address entry, so its section path holds
    an `entry` segment a row path cannot match, and the level stays grounded by the table. The export rule the
    file cannot hold is read by the report, so it has no unused property and the scan reports nothing for it.
    """
    parser = run_pipeline(converter_module, 'bgp_policy.xml', tmp_path)
    assert parser is not None, 'bgp_policy.xml'
    ledger = parser.ledger
    entry = next(e for e in ledger.entries() if e.get('name') == 'agg-10.0.0.0-8')
    row = entry_coverage.matrix_row_for(
        container_coverage.section_path(ledger.parents[entry], ledger.parents, ledger.source))
    assert row is not None and row['resource'] == 'panos_virtual_router', row
    recorded = ledger.mark_for(entry)['captured']
    assert isinstance(recorded, entry_coverage.RecordingDict), recorded
    assert sorted(set(recorded.used_keys()) - entry_coverage.NON_FIELD_KEYS) == [
        'advertise_filters', 'aggregate_route_attributes', 'as_set', 'enable', 'prefix', 'summary',
        'suppress_filters'], recorded.used_keys()
    inner = next(e for e in ledger.entries() if e.get('name') == 'agg-advertises')
    path = container_coverage.section_path(ledger.parents[inner], ledger.parents, ledger.source)
    assert entry_coverage.matrix_row_for(path) is None, path
    # F7.6: the policy `address` level is covered by the policy row and not by the address row, so the address
    # rule reads no object for it, and the mark the protocol walk wrote is the one the scan reads.
    assert ledger.destination(entry) == 'emitted', ledger.destination(entry)
    router_row = next(r for r in ROWS if r['resource'] == 'panos_virtual_router')
    for field in ('action', 'advertise_filters', 'aggregate_route_attributes', 'as_set', 'match',
                  'non_exist_filters', 'prefix', 'summary', 'suppress_filters', 'used_by'):
        assert field in router_row['properties'], router_row['properties']
    assert ledger.property_findings() == [], ledger.property_findings()
    assert entry_coverage.covering_row(
        container_coverage.section_path(ledger.parents[entry], ledger.parents)).path == (
        'protocol/bgp/policy/aggregation/address')


def test_the_scan_measures_an_auth_profile_entry_and_not_the_entry_inside_it(converter_module, tmp_path):
    """F7.7: the four auth profile entries are in the scan scope, and the `md5` entry inside one is not.

    The four container rows the parse reads are the four levels, so the scan measures the fields each row
    declares against the router row. The `md5` entry sits inside the profile entry, so its section path holds an
    extra `entry` segment that no row path can match, and `key` stays grounded by the table. A `one_of` level
    inside the entry is read as the field of the entry, so `ah` and `esp` are measured and the five alternatives
    are not. The fixture states the two `ospfv3` choice levels in two entries, because the provider accepts one
    or the other for an entry.
    """
    parser = run_pipeline(converter_module, 'auth_profile.xml', tmp_path)
    assert parser is not None, 'auth_profile.xml'
    ledger = parser.ledger
    for level, entry_name in (('bgp', 'profile-bgp'), ('ospf', 'profile-ospf'), ('rip', 'profile-rip'),
                              ('ospfv3', 'profile-ospfv3-ah'), ('ospfv3', 'profile-ospfv3-esp')):
        entry = next(e for e in ledger.entries() if e.get('name') == entry_name)
        path = container_coverage.section_path(ledger.parents[entry], ledger.parents, ledger.source)
        row = entry_coverage.matrix_row_for(path)
        assert row is not None and row['resource'] == 'panos_virtual_router', (level, row, path)
        assert entry_coverage.covering_row(path).path == f'protocol/{level}/auth-profile', path
    inner = next(e for e in ledger.entries() if e.get('name') == 'profile-ospf-md5')
    path = container_coverage.section_path(ledger.parents[inner], ledger.parents, ledger.source)
    assert entry_coverage.matrix_row_for(path) is None, path
    recorded = ledger.mark_for(inner)['captured']
    assert sorted(set(recorded.used_keys()) - entry_coverage.NON_FIELD_KEYS) == ['key', 'preferred'], recorded
    router_row = next(r for r in ROWS if r['resource'] == 'panos_virtual_router')
    for field in ('ah', 'esp', 'md5', 'password', 'secret', 'spi'):
        assert field in router_row['properties'], router_row['properties']
    assert 'key' not in router_row['properties'], router_row['properties']
    assert ledger.property_findings() == [], ledger.property_findings()


# --- 3. The scan -----------------------------------------------------------

def test_scan_reports_the_properties_no_output_read(converter_module, tmp_path):
    """The corpus findings, pinned.

    Each finding is a captured field that the row's emitter does not read. The pinned set
    is the measurement, so an emitter that starts reading one of these properties must
    update this test and the follow-up in backlog.md in the same change.
    """
    findings = {}
    for fixture, ledger in _corpus_ledgers(converter_module, tmp_path):
        rows = _finding_rows(ledger)
        if rows:
            findings[fixture] = rows
    assert findings == CORPUS_FINDINGS, findings


def test_scan_scope_is_the_entries_a_matrix_row_covers(converter_module, tmp_path):
    """A field gap in a container the matrix does not cover is not a scan finding.

    Both fixtures hold a captured field no output read, in a report or count-only
    container. The gap is real, so it stays in backlog.md, but the scan does not report
    it: only an emitted container has a matrix row, and a matrix row is what names the
    properties an emitter reads.
    """
    for fixture in ('application_override_rules.xml', 'regions.xml'):
        parser = run_pipeline(converter_module, fixture, tmp_path)
        assert parser is not None, fixture
        ledger = parser.ledger
        assert ledger.property_findings() == [], fixture
        # The field gap is still there, outside the scan scope.
        unused = {(entry.get('name'), tuple(sorted(
            set(ledger.captured_fields(ledger.mark_for(entry)))
            - set(ledger.mark_for(entry)['captured'].used_keys()))))
            for entry in ledger.entries() if ledger.mark_for(entry)}
        assert any(keys for _name, keys in unused), f'{fixture}: the scan scope check is empty'


# --- 4. The report section ------------------------------------------------

def _report(tmp_path, fixture):
    result = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / fixture),
                        '--output-dir', str(tmp_path))
    assert result.returncode == 0, result.stderr
    return (tmp_path / entry_coverage.REPORT_FILE).read_text(encoding='utf-8')


def test_report_prints_the_property_section_for_a_finding(tmp_path):
    report = _report(tmp_path / 'a', FINDING_FIXTURE)
    assert entry_coverage.PROPERTY_HEADING in report
    assert entry_coverage.PROPERTY_RULE in report
    # The section is grouped by the F3.9 scope rule, so it names the scope the finding
    # came from, not just the entry.
    section = report[report.index(entry_coverage.PROPERTY_HEADING):]
    assert 'DEVICE GROUP: Production-DG' in section, section
    for _container, name, resource, properties in CORPUS_FINDINGS[FINDING_FIXTURE]:
        line = next(line for line in section.splitlines() if name in line)
        assert resource in line and ', '.join(properties) in line, line


def test_property_section_prints_after_the_gap_section(tmp_path):
    """The two report sections keep a fixed order (F4.3 rule 3)."""
    report = _report(tmp_path / 'b', BOTH_FIXTURE)
    assert entry_coverage.GAP_HEADING in report
    assert entry_coverage.PROPERTY_HEADING in report
    assert report.index(entry_coverage.GAP_HEADING) < report.index(entry_coverage.PROPERTY_HEADING)


def test_property_section_absent_when_no_output_missed_a_property(tmp_path):
    """A run with no finding prints no property section."""
    report = _report(tmp_path / 'c', 'tags.xml')
    assert entry_coverage.PROPERTY_HEADING not in report


def test_property_section_is_byte_identical_between_runs(tmp_path):
    first = _report(tmp_path / 'd1', BOTH_FIXTURE)
    second = _report(tmp_path / 'd2', BOTH_FIXTURE)
    assert first == second


def test_finding_does_not_change_the_exit_code(tmp_path):
    """A property finding is an operator action, not a broken output."""
    result = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / FINDING_FIXTURE),
                        '--output-dir', str(tmp_path / 'exit'))
    assert result.returncode == 0, result.stdout + result.stderr
    assert entry_coverage.PROPERTY_HEADING in (tmp_path / 'exit' / entry_coverage.REPORT_FILE).read_text()
