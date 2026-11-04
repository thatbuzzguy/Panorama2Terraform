"""F4.4 property-level coverage: what a matrix row reads, and what no output read.

Six groups:

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
5. The console block. One line per finding in the shape `container_coverage.console_line` states
   (`docs/ARCHITECTURE.md` §3.2): the scope, the position, the entry, the fact. No matrix row, because
   a console line has no room for a column. The fact names the properties as the parsed-object key
   names. A run with no finding prints nothing new, and the report bytes are unchanged.
6. The five field gaps the scan cannot measure, one pin per gap: the fixture entry, the read the
   parse made, and the output that prints the field. A `report` container has no matrix row, so its
   field is closed by the report writer reading what it prints; an `emitted` container is closed by
   the emitter reading the key and the row naming it in the same change.

The scan scope is the entries a matrix row covers. A report, inventory, bookkeeping,
count-only, or nested-block container has no matrix row, so the scan does not report it;
those field gaps stay in backlog.md. F7.11: an entry the parse reaches through a field the parent row names is
not measured either, such as an interface entry inside an area entry, so the fields its row declares are grounded
by `PROTOCOL_SHAPE` instead of by the row.
"""

import container_coverage
import entry_coverage
import xml_input
from conftest import FIXTURES_DIR, run_pipeline, run_script, written_bytes
from resource_mapping import COVERAGE_MATRIX, protocol_row

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

    One row has no read of its own to measure: `panos_device_group_parent`, because the entry that
    feeds the parent record is covered by the device group row (F6.5 decision 4: one entry can feed two
    blocks, and the scan measures an entry against the row that covers its container). It is grounded by
    the emitter test in tests/test_coverage_matrix.py.

    `panos_aggregate_layer3_subinterface` was the second exception, and the row in the test below is what
    closed it: the container table now names the aggregate subinterface container, so a corpus entry
    reaches the row and its properties are measured through that entry.

    `panos_vsys` is measured with the empty set: its block carries the entry name and the location
    only, so the row declares no property and parity holds only while a fixture places a virtual
    system inside a template (`scope_objects.xml`).
    """
    measured = {}
    for _fixture, ledger in _corpus_ledgers(converter_module, tmp_path):
        for resource, keys in _read_set(ledger).items():
            measured.setdefault(resource, set()).update(keys)

    unmeasured = sorted({row['resource'] for row in ROWS} - set(measured))
    assert unmeasured == ['panos_device_group_parent'], unmeasured

    drift = {row['resource']: (sorted(row['properties']), sorted(measured[row['resource']]))
             for row in ROWS
             if row['resource'] in measured and set(row['properties']) != measured[row['resource']]}
    assert drift == {}, drift


def test_the_scan_measures_an_aggregate_subinterface_through_the_aggregate_row(converter_module, tmp_path):
    """The row that closed the second exception: the aggregate subinterface entry is measured by its own row.

    `parse_interfaces` reaches an aggregate subinterface with the same relative pattern it uses for the
    ethernet shape, so `covering_row` needs a row for the aggregate container: the longest match covers
    `ae1.101.20`, and `layer3/units` still covers the ethernet entry. The matrix element names the same
    container the table row names, plus the entry inside it, so the entry the element test reads is the entry
    the scan measures.

    `ae1.101` is an aggregate entry whose name carries a unit, so the table covers it with the group row:
    the row shape cannot state a name fact, and the emitter reaches the subinterface type for it through the
    name rule. The group row keeps the properties the run reads from that entry.
    """
    parser = run_pipeline(converter_module, 'interfaces_other.xml', tmp_path)
    assert parser is not None, 'interfaces_other.xml'
    ledger = parser.ledger
    sub = next(e for e in ledger.entries() if e.get('name') == 'ae1.101.20')
    path = container_coverage.section_path(ledger.parents[sub], ledger.parents, ledger.source)
    row = entry_coverage.covering_row(path)
    assert row.path == 'network/interface/aggregate-ethernet/entry/layer3/units', path
    assert entry_coverage.matrix_row_for(path)['resource'] == 'panos_aggregate_layer3_subinterface', path

    matrix_row = next(r for r in ROWS if r['resource'] == 'panos_aggregate_layer3_subinterface')
    # The element column states the row's container from the `network` root, plus the entry inside it.
    container = row.path.removeprefix('network/interface/')
    assert matrix_row['xml_element'] == container + '/entry', (row.path, matrix_row['xml_element'])
    assert matrix_row['xml_name'] == sub.get('name'), matrix_row['xml_name']

    recorded = ledger.mark_for(sub)['captured']
    assert isinstance(recorded, entry_coverage.RecordingDict), recorded
    assert sorted(set(recorded.used_keys()) - entry_coverage.NON_FIELD_KEYS) == \
        sorted(matrix_row['properties']), recorded.used_keys()
    assert ledger.property_findings() == [], ledger.property_findings()

    group = next(e for e in ledger.entries() if e.get('name') == 'ae1.101')
    group_row = entry_coverage.covering_row(
        container_coverage.section_path(ledger.parents[group], ledger.parents, ledger.source))
    assert entry_coverage.row_detail(group_row) == 'panos_aggregate_interface', group_row


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


def test_the_scan_measures_a_redist_profile_entry_and_a_dampening_entry(
        converter_module, tmp_path):
    """F7.10: the three entry levels the shape table added are in the scan scope, and the levels inside them
    are not.

    The `protocol` row states the two redistribution profile lists as `string_list` fields and the `bgp` row
    states the dampening profile as one, so the three levels gain a `CONTAINER_TABLE` row and the scan measures
    the fields each row declares against the router row. A `single` level inside an entry (`action`, `filter`,
    `filter/bgp`, `filter/ospf`) holds no entry, so `_protocol_level` builds it as a plain dict, which records
    nothing, and the container table names no row for it: the table grounds it. The properties the router row
    declares gain only what an entry measures.
    """
    parser = run_pipeline(converter_module, 'virtual_routers.xml', tmp_path)
    assert parser is not None, 'virtual_routers.xml'
    ledger = parser.ledger
    for entry_name, row_path in (('RP-Internal', 'protocol/redist-profile'),
                                 ('RP6-Internal', 'protocol/redist-profile-ipv6')):
        entry = next(e for e in ledger.entries() if e.get('name') == entry_name)
        path = container_coverage.section_path(ledger.parents[entry], ledger.parents, ledger.source)
        assert entry_coverage.covering_row(path).path == row_path, path
        row = entry_coverage.matrix_row_for(path)
        assert row is not None and row['resource'] == 'panos_virtual_router', row
        recorded = ledger.mark_for(entry)['captured']
        assert isinstance(recorded, entry_coverage.RecordingDict), recorded
        assert sorted(set(recorded.used_keys()) - entry_coverage.NON_FIELD_KEYS) == [
            'action', 'filter', 'priority'], recorded.used_keys()
        for field in ('action', 'filter'):
            assert not isinstance(recorded[field], entry_coverage.RecordingDict), field
    # The dampening entry is measured by the same rule, through the row the `bgp` row names.
    bgp_parser = run_pipeline(converter_module, 'bgp.xml', tmp_path)
    assert bgp_parser is not None, 'bgp.xml'
    entry = next(e for e in bgp_parser.ledger.entries() if e.get('name') == 'DAMP-Branch')
    path = container_coverage.section_path(bgp_parser.ledger.parents[entry],
                                           bgp_parser.ledger.parents, bgp_parser.ledger.source)
    assert entry_coverage.covering_row(path).path == 'protocol/bgp/dampening-profile', path
    recorded = bgp_parser.ledger.mark_for(entry)['captured']
    assert sorted(set(recorded.used_keys()) - entry_coverage.NON_FIELD_KEYS) == [
        'cutoff', 'decay_half_life_reachable', 'decay_half_life_unreachable', 'enable',
        'max_hold_time', 'reuse'], recorded.used_keys()
    # A level inside an entry holds no entry, so no row names it and the table grounds it.
    row_paths = {row.path for row in container_coverage.CONTAINER_TABLE}
    for path in ('protocol/redist-profile/action', 'protocol/redist-profile/filter',
                 'protocol/redist-profile/filter/bgp', 'protocol/redist-profile/filter/ospf',
                 'protocol/redist-profile-ipv6/filter', 'protocol/redist-profile-ipv6/filter/ospfv3'):
        assert path not in row_paths, path
    router_row = next(r for r in ROWS if r['resource'] == 'panos_virtual_router')
    for field in ('action', 'cutoff', 'decay_half_life_reachable', 'decay_half_life_unreachable',
                  'enable', 'filter', 'max_hold_time', 'priority', 'reuse'):
        assert field in router_row['properties'], router_row['properties']
    for ledger in (parser.ledger, bgp_parser.ledger):
        assert ledger.property_findings() == [], ledger.property_findings()


# --- 3. The scan -----------------------------------------------------------

def test_the_scan_measures_the_six_rows_and_not_a_level_inside_an_entry(converter_module, tmp_path):
    """F7.11: the entry levels the six rows completed are in the scan scope, and a level inside an entry is not.

    The peer group entry, the peer entry, and the redist rule entry are entries whose container a row covers, so
    the fields their rows gained join the measured set. `bfd`, `connection_options` and
    `subsequent_address_family_identifier` are measured as the fields of the peer entry, because
    `_protocol_level` builds a `single` level as a plain dict, which records nothing. The peer the fixture puts
    at the `bgp` level is covered by the row `CONTAINER_TABLE` states for `protocol/bgp/peer`, which is the
    same level the shape table states as `protocol/bgp/peer_group/peer`. An interface entry sits
    inside an area entry, so its section path holds an `entry` segment a row path cannot match: the eight fields
    the two interface rows gained stay grounded by the table, so the router row declares no property for them.
    The `ospfv3` area entry is in scope, so its new field is measured against the row.
    """
    parser = run_pipeline(converter_module, 'bgp.xml', tmp_path)
    assert parser is not None, 'bgp.xml'
    ledger = parser.ledger
    measured = (
        ('PG-Branch', 'protocol/bgp/peer-group',
         ['aggregated_confed_as_path', 'enable', 'peer', 'soft_reset_with_stored_info', 'type']),
        ('10.55.0.2', 'protocol/bgp/peer',
         ['address_family_identifier', 'bfd', 'connection_options', 'enable', 'enable_mp_bgp',
          'enable_sender_side_loop_detection', 'local_address', 'max_prefixes', 'peer_address', 'peer_as',
          'peering_type', 'reflector_client', 'subsequent_address_family_identifier']),
        ('redist-static', 'protocol/bgp/redist-rules',
         ['address_family_identifier', 'enable', 'metric', 'route_table', 'set_as_path_limit',
          'set_community', 'set_extended_community', 'set_local_preference', 'set_med', 'set_origin']),
    )
    for entry_name, row_path, keys in measured:
        entry = next(e for e in ledger.entries() if e.get('name') == entry_name)
        path = container_coverage.section_path(ledger.parents[entry], ledger.parents, ledger.source)
        assert entry_coverage.covering_row(path).path == row_path, path
        recorded = ledger.mark_for(entry)['captured']
        assert isinstance(recorded, entry_coverage.RecordingDict), recorded
        assert sorted(set(recorded.used_keys()) - entry_coverage.NON_FIELD_KEYS) == keys, recorded.used_keys()
        # A `single` level inside an entry is a plain dict, so it records nothing on its own.
        for field in ('bfd', 'connection_options', 'subsequent_address_family_identifier'):
            assert not isinstance(recorded.get(field), entry_coverage.RecordingDict), field
        assert ledger.property_findings() == [], ledger.property_findings()

    # An interface entry is inside an area entry, so the scan does not measure it.
    ospf = run_pipeline(converter_module, 'ospf.xml', tmp_path)
    assert ospf is not None, 'ospf.xml'
    interface = next(e for e in ospf.ledger.entries() if e.get('name') == 'ethernet1/2')
    path = container_coverage.section_path(ospf.ledger.parents[interface], ospf.ledger.parents, ospf.ledger.source)
    assert entry_coverage.matrix_row_for(path) is None, path
    router_row = next(r for r in ROWS if r['resource'] == 'panos_virtual_router')
    for field in ('dead_counts', 'gr_delay', 'hello_interval', 'retransmit_interval', 'transit_delay'):
        assert field in protocol_row('protocol/ospf/area/interface')['fields'], field
        assert field in protocol_row('protocol/ospfv3/area/interface')['fields'], field
        assert field not in router_row['properties'], router_row['properties']
    # `instance_id` is the one field the `ospfv3` interface row states that the `ospf` row does not.
    assert 'instance_id' in protocol_row('protocol/ospfv3/area/interface')['fields']
    assert 'instance_id' not in router_row['properties'], router_row['properties']
    assert ospf.ledger.property_findings() == [], ospf.ledger.property_findings()
    # The `ospfv3` area entry is in scope, so `authentication` is measured through it.
    ospfv3 = run_pipeline(converter_module, 'ospfv3.xml', tmp_path)
    assert ospfv3 is not None, 'ospfv3.xml'
    area = next(e for e in ospfv3.ledger.entries() if e.get('name') == '0.0.0.0')
    path = container_coverage.section_path(ospfv3.ledger.parents[area], ospfv3.ledger.parents,
                                           ospfv3.ledger.source)
    assert entry_coverage.covering_row(path).path == 'protocol/ospfv3/area', path
    recorded = ospfv3.ledger.mark_for(area)['captured']
    assert sorted(set(recorded.used_keys()) - entry_coverage.NON_FIELD_KEYS) == [
        'authentication', 'interface', 'range', 'type', 'virtual_link'], recorded.used_keys()
    assert ospfv3.ledger.property_findings() == [], ospfv3.ledger.property_findings()




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

    The fixture holds a captured field no output read, in a `count-only` container. The gap is real, so it
    stays in backlog.md, but the scan does not report it: only an emitted container has a matrix row, and a
    matrix row is what names the properties an emitter reads. A `report` container has no row either, so its
    field is honest only when the report line reads what it prints; that is the rule group 6 pins, and
    measured 2026-11-04 no `report` container in the corpus has a captured field no output read.
    """
    for fixture in ('regions.xml',):
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


# --- 5. The console block ---------------------------------------------------

def _console(fixture, tmp_path):
    """Run the converter on one fixture. Returns (exit code, console text)."""
    result = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / fixture),
                        '--output-dir', str(tmp_path))
    return result.returncode, result.stdout


def test_the_console_prints_the_property_findings(converter_module, tmp_path):
    """AC-3 and AC-5: one console line per finding, in the shape `container_coverage.console_line` states.

    The line keys on the entry's source line, the position the report row keys on, and it names the fact,
    not the matrix row, because a console line has no room for the report's fixed-width column. The block
    prints only when it has a finding, and a finding does not change the exit code.
    """
    parser = run_pipeline(converter_module, FINDING_FIXTURE, tmp_path / 'run')
    assert parser is not None
    ledger = parser.ledger
    generator = converter_module.TerraformGenerator(output_dir=str(tmp_path / 'gen'))
    rows = ledger.property_findings()
    assert rows, 'the fixture must trip a property finding'
    block = entry_coverage.property_console_lines(rows, generator._report_scope_path)
    code, console = _console(FINDING_FIXTURE, tmp_path / 'out')
    assert code == 0, 'a property finding is an operator action, so the F4.1 gate decides the exit code'
    for line in block:
        assert line in console, line
    for row, line in zip(rows, block[1:]):
        parts = line[len(container_coverage.CONSOLE_PREFIX):].split('  ')
        assert parts == [container_coverage.scope_part(row, generator._report_scope_path),
                         container_coverage.position_part(row['line']),
                         entry_coverage.entry_identity(row), entry_coverage.property_fact(row)], parts
        assert row['resource'] not in line, (line, 'the console line names no matrix row')


def test_the_console_fact_names_the_parsed_object_key_and_not_the_xml_tag(converter_module, tmp_path):
    """AC-4: captured fields are the keys of the object the parse method built (F4.3 rule 5), so the
    console line names a key name, not the XML spelling the value came from.

    `address_objects.xml` trips a finding on `declared_type`, the key the parse built from the XML
    attribute `type`, so the two names differ and the pin can tell them apart.
    """
    parser = run_pipeline(converter_module, 'address_objects.xml', tmp_path / 'run')
    assert parser is not None
    ledger = parser.ledger
    entry = next(e for e in ledger.entries() if e.get('name') == 'Wildcard-Net')
    key = 'declared_type'
    assert key in ledger.captured_fields(ledger.mark_for(entry)), 'the fact names a parsed-object key'
    assert entry.get('type') is not None, 'the value comes from the XML attribute `type`'
    row = next(r for r in ledger.property_findings() if r['name'] == entry.get('name'))
    generator = converter_module.TerraformGenerator(output_dir=str(tmp_path / 'gen'))
    line = entry_coverage.property_console_lines([row], generator._report_scope_path)[1]
    code, console = _console('address_objects.xml', tmp_path / 'out')
    assert code == 0, console
    assert line in console, line
    assert key in line and 'type' not in line.replace(key, ''), line


def test_the_console_prints_no_property_block_for_a_run_with_no_finding(tmp_path):
    """AC-5: a run with no finding in this kind prints nothing new, and the exit code is unchanged."""
    code, console = _console('tags.xml', tmp_path)
    assert code == 0
    assert 'Property findings' not in console, console


def _gap_run(converter_module, tmp_path, fixture):
    """Run one gap fixture in process. Returns (ledger, the manual report text, the `.tf` text).

    The read record is a run-time measurement, so the run must be in process. The report and the `.tf`
    file are the two outputs that can read a captured field, so the pin reads both.
    """
    out = tmp_path / fixture
    parser = run_pipeline(converter_module, fixture, out)
    assert parser is not None, fixture
    written = written_bytes(out)
    report = written.get('MANUAL_SETUP_REPORT.txt', b'').decode(encoding='utf-8')
    tf = '\n'.join(text.decode(encoding='utf-8') for text in written.values())
    return parser.ledger, report, tf


def _gap_mark(ledger, name):
    """The mark for one entry, and the captured fields the parse kept for it."""
    entry = next(e for e in ledger.entries() if e.get('name') == name)
    mark = ledger.mark_for(entry)
    assert mark is not None, name
    return entry, mark


# --- 6. The five field gaps the scan cannot measure ------------------------------------

def test_the_report_reads_the_application_filter_description_it_prints(converter_module, tmp_path):
    """Gap 1: `panos_application_filter` is not a resource, so the report is the output for the entry.

    `parse_application_filters` keeps `description` in the object it marks, read through `_get_text` like the
    other text fields of that entry, and the report line prints it through the captured object, so the read
    record names the key as a property an output used. The `application-filter` container is a `report` row,
    so `matrix_row_for` answers None and the scan measures nothing for it: the report reading what it prints
    is the only rule that can keep a field honest in a container with no matrix row.
    """
    ledger, report, _tf = _gap_run(converter_module, tmp_path, 'application_filters.xml')
    entry, mark = _gap_mark(ledger, 'high-risk-web')
    assert 'description' in ledger.captured_fields(mark), ledger.captured_fields(mark)
    line = next(line for line in report.splitlines() if 'high-risk-web' in line)
    assert 'description=Filter high risk web applications' in line, line
    assert 'description' in mark['captured'].used_keys(), mark['captured'].used_keys()
    path = container_coverage.section_path(ledger.parents[entry], ledger.parents, ledger.source)
    assert entry_coverage.matrix_row_for(path) is None, path
    assert ledger.property_findings() == [], ledger.property_findings()


def test_the_report_reads_the_schedule_description_it_prints(converter_module, tmp_path):
    """Gap 2: `panos_schedule` exists but declares no `description`, so the report prints the field.

    Measured 2026-11-04 against the pinned provider: `panos_schedule` declares `disable_override`, `location`,
    `name` and `schedule_type` only, so no emitter can print a description and the `schedule` container stays
    a `report` row. `parse_schedules` reads the field through `_get_text`, and the report line prints it
    through the captured object, so the read record names it as a property an output used. An entry with no
    value prints no field, and the captured set keeps such a field out (F4.3 rule 3).
    """
    ledger, report, _tf = _gap_run(converter_module, tmp_path, 'schedules.xml')
    entry, mark = _gap_mark(ledger, 'Business-Hours')
    assert 'description' in ledger.captured_fields(mark), ledger.captured_fields(mark)
    line = next(line for line in report.splitlines() if 'Business-Hours' in line)
    assert 'Business-Hours (Business hours): type=recurring' in line, line
    assert 'description' in mark['captured'].used_keys(), mark['captured'].used_keys()
    path = container_coverage.section_path(ledger.parents[entry], ledger.parents, ledger.source)
    assert entry_coverage.matrix_row_for(path) is None, path
    _entry, plain_mark = _gap_mark(ledger, 'One-Time')
    # No value, so no captured field (F4.3 rule 3), and the line prints none
    assert 'description' not in ledger.captured_fields(plain_mark), ledger.captured_fields(plain_mark)
    plain_line = next(line for line in report.splitlines() if 'One-Time' in line)
    assert plain_line == '  One-Time: type=non-recurring, entries=-', plain_line
    assert ledger.property_findings() == [], ledger.property_findings()


def test_the_security_rule_row_measures_the_profile_group_the_emitter_prints(converter_module, tmp_path):
    """Gap 3: the profile group reference is expressible, so the row names it and the emitter reads it.

    `parse_security_rules` reads the group members through `_get_members(rule, 'profile/group')`, and
    `generate_security_rules` prints them as `profile_setting = { group = [ ... ] }`, the shape the pinned
    provider declares (`profile_setting.group` is a list of strings). The row names the parsed-object key
    `profile_group`, so the emitter read and the declared property are the same key, and the corpus entry is
    the measurement. No profile-group reference scope exists, so the names stay brown-field strings.
    """
    ledger, _report, tf = _gap_run(converter_module, tmp_path, 'security_rules.xml')
    entry, mark = _gap_mark(ledger, 'Block-Risky-Apps')
    assert ledger.captured_fields(mark) == (
        'action', 'applications', 'destination_addresses', 'destination_zones', 'disabled',
        'log_end', 'log_start', 'profile_group', 'services', 'source_addresses', 'source_zones'), \
        ledger.captured_fields(mark)
    assert 'profile_group' in mark['captured'].used_keys(), mark['captured'].used_keys()
    row = entry_coverage.matrix_row_for(
        container_coverage.section_path(ledger.parents[entry], ledger.parents, ledger.source))
    assert row['resource'] == 'panos_security_policy_rules', row
    assert 'profile_group' in row['properties'], row['properties']
    assert 'profile_setting = {\n        group = [ "Strict-Profile" ]\n      }' in tf, tf
    assert ledger.property_findings() == [], ledger.property_findings()


def test_the_nat_service_is_read_in_both_export_forms(converter_module, tmp_path):
    """Gap 4: the string field reads the text form and the one-member form; a longer list is reported.

    Before the fix the parse read the member form as the whitespace between the element and its members.
    `panos_nat_policy_rules.rules.service` is a string (pinned provider, measured 2026-11-04), so one member
    reaches the field as the name, and more than one member is the set the field cannot hold: the block prints
    the `# NOTE:` line that names the members, so the field is printed or reported, never dropped. Both forms
    are read by the row's emitter, so `test_measured_reads_equal_the_declared_properties` holds for `service`
    and the run reports no finding for either entry.
    """
    ledger, _report, tf = _gap_run(converter_module, tmp_path, 'nat_rules.xml')
    forms = {
        'Outbound-NAT': ('text form', 'service = "any"'),
        'Member-Form-NAT': ('one member', 'service = "service-http"'),
        'Multi-Member-NAT': ('two members', '# NOTE: service service-http, service-https'),
    }
    for name, (_form, printed) in forms.items():
        entry, mark = _gap_mark(ledger, name)
        assert ledger.captured_fields(mark) and 'service' in ledger.captured_fields(mark), name
        assert 'service' in mark['captured'].used_keys(), (name, mark['captured'].used_keys())
        assert printed in tf, (name, tf)
    assert ledger.property_findings() == [], ledger.property_findings()
    row = next(r for r in ROWS if r['resource'] == 'panos_nat_policy_rules')
    assert 'service' in row['properties'], row['properties']


def test_the_report_reads_the_application_override_fields_it_prints(converter_module, tmp_path):
    """Gap 5: `panos_application_override_rule` is not a resource, so the report is the output for the entry.

    `parse_application_override_rules` keeps `description` and `destination_addresses` in the object it
    marks, read through `_get_text` and `_get_members` like the other fields of that entry, and the report
    line prints both through the captured object, so the read record names the keys as properties an output
    used. The `application-override/rules` container is a `report` row, so `matrix_row_for` answers None and
    the scan measures nothing for it: the report reading what it prints is the only rule that can keep a
    field honest in a container with no matrix row. The line shape lives in one place,
    `panorama_to_terraform.OVERRIDE_REPORT_FIELDS`.

    The fixture holds one entry that carries neither field, so the pin covers both sides: a field the entry
    carries no value for is not a captured field (F4.3 rule 3), and the line prints neither. Measured
    2026-11-04, this closed the last `report` container in the corpus with a captured field no output read.
    """
    ledger, report, _tf = _gap_run(converter_module, tmp_path, 'application_override_rules.xml')
    entry, mark = _gap_mark(ledger, 'Override-443')
    fields = ledger.captured_fields(mark)
    assert 'description' in fields and 'destination_addresses' in fields, fields
    line = next(line for line in report.splitlines() if 'Override-443' in line)
    assert line == (
        "  Override-443: from=['Trust'] to=['Untrust'] source=['Internal-Network'] "
        "destination=['any'] port=8443 protocol=tcp application=https disabled=False "
        "description=Override 8443 as HTTPS"), line
    for key in ('description', 'destination_addresses'):
        assert key in mark['captured'].used_keys(), (key, mark['captured'].used_keys())
    path = container_coverage.section_path(ledger.parents[entry], ledger.parents, ledger.source)
    assert entry_coverage.matrix_row_for(path) is None, path

    # The other side: an entry that carries neither field prints neither, and names neither as a captured
    # field. The entry is still marked, because `mark` stores the captured object by reference (F4.3 rule 4).
    plain_entry, plain_mark = _gap_mark(ledger, 'Override-RDP')
    plain_fields = ledger.captured_fields(plain_mark)
    assert 'description' not in plain_fields and 'destination_addresses' not in plain_fields, plain_fields
    plain_line = next(line for line in report.splitlines() if 'Override-RDP' in line)
    assert plain_line == (
        "  Override-RDP: from=['Trust'] to=['Untrust'] source=['Internal-Network'] "
        "port=3389 protocol=tcp application=rdp disabled=False"), plain_line
    plain_path = container_coverage.section_path(ledger.parents[plain_entry], ledger.parents, ledger.source)
    assert entry_coverage.matrix_row_for(plain_path) is None, plain_path
    assert ledger.property_findings() == [], ledger.property_findings()

    # The corpus copy of the same entry carries both fields, so the run reports no finding for it. The
    # fixture still has findings in containers that have a matrix row, and those are the pinned set.
    kitchen = run_pipeline(converter_module, 'kitchen_sink.xml', tmp_path / 'kitchen_sink')
    assert kitchen is not None, 'kitchen_sink.xml'
    findings = kitchen.ledger.property_findings()
    assert not [f for f in findings if f['name'] == 'Override-443'], findings
    assert _finding_rows(kitchen.ledger) == CORPUS_FINDINGS['kitchen_sink.xml'], findings


def test_the_console_shape_moves_no_report_bytes(converter_module, tmp_path):
    """AC-7: the report keeps the fixed-width line shape with the matrix row, so the console change moves
    no report bytes and the goldens stay.
    """
    parser = run_pipeline(converter_module, FINDING_FIXTURE, tmp_path / 'run')
    report = _report(tmp_path / 'out', FINDING_FIXTURE)
    for row in parser.ledger.property_findings():
        line = entry_coverage.property_line(row)
        assert line in report, line
        assert row['resource'] in line, 'the report keeps the matrix row column'
