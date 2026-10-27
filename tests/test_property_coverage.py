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
        # The entry name and the four scope facts are the row identity, not content the
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
    parser = converter_module.PanoramaParser(str(FIXTURES_DIR / 'tags.xml'))
    entry = next(e for e in parser.root.iter() if e.tag == 'entry' and e.get('name') == 'env-prod')
    recorded = parser.mark(entry, {'name': 'env-prod', 'color': 'light blue'})
    assert recorded.used_keys() == (), 'the record must stay off during the parse'
    parser.ledger.start_recording()
    recorded.get('color')
    assert recorded.used_keys() == ('color',)


def test_parse_time_read_is_not_a_property_use(converter_module):
    """A key the parse method read off the XML element is not a property the output used."""
    parser = converter_module.PanoramaParser(str(FIXTURES_DIR / 'ipsec_crypto_profiles.xml'))
    parser.parse_ipsec_crypto_profiles()
    entry = next(e for e in parser.ledger.entries() if e.get('name') == 'IPSEC-DEFAULT')
    mark = parser.ledger.mark_for(entry)
    assert 'protocol' in parser.ledger.captured_fields(mark)
    assert 'protocol' not in mark['captured'].used_keys()


# --- 2. Parity with the matrix --------------------------------------------

def test_measured_reads_equal_the_declared_properties(converter_module, tmp_path):
    """For each matrix row, the properties the outputs read equal the row's declared list.

    A row whose shape the corpus never exercises has no read to measure. That is
    `panos_aggregate_layer3_subinterface`: the container table maps an aggregate
    subinterface to the ethernet subinterface row, so no corpus entry reaches it. Its
    declared properties are grounded by the emitter test in tests/test_coverage_matrix.py,
    and the table limit is recorded in backlog.md.
    """
    measured = {}
    for _fixture, ledger in _corpus_ledgers(converter_module, tmp_path):
        for resource, keys in _read_set(ledger).items():
            measured.setdefault(resource, set()).update(keys)

    unmeasured = sorted({row['resource'] for row in ROWS} - set(measured))
    assert unmeasured == ['panos_aggregate_layer3_subinterface'], unmeasured

    drift = {row['resource']: (sorted(row['properties']), sorted(measured[row['resource']]))
             for row in ROWS
             if row['resource'] in measured and set(row['properties']) != measured[row['resource']]}
    assert drift == {}, drift


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
