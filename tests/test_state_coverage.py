"""F5.6 state coverage: the ownership fact and the drift fact.

Six groups, one per acceptance rule:

1. The state entry shape the scan reads: the matrix row is the row keyed by the resource type
   through the same table, the properties are read with the F4.3 rule, and the position is the
   resource address.
2. The ownership fact: §2.1 identity as the F3.9 rule reads it, the declared facts only, the
   first entry for a key wins in document order, the scan scope is the F4.4 rule on both sides,
   and a run with no state source reports nothing.
3. The drift fact: a declared property both sides hold by the same name, the value compared as
   held, order part of the value, and a drift fact needs an ownership fact.
4. The two report sections, the fixed line shapes, the F3.9 grouping, no console line, and the
   exit code the F4.1 gate still decides.
5. The state scan is not an output, so it cannot move a property finding.
6. Determinism, and the record: two runs on the same arguments and the same bytes write the same
   bytes, and a state record reads back through `parse_records` with no new field.

Every test uses a committed fixture, so no test opens a connection. The run side is
`tests/fixtures/address_objects.xml`; the state side is `tests/fixtures/state_workspace.json`.
"""

import contextlib
import io
import sys

import pytest

import container_coverage
import entry_coverage
import provenance
import state_coverage
import state_input
from conftest import FIXTURES_DIR, run_main, run_pipeline
from xml_input import parse_xml

STATE_FIXTURE = 'state_workspace.json'
RUN_FIXTURE = 'address_objects.xml'
SERVICE_FIXTURE = 'service_groups.xml'
REGION_FIXTURE = 'regions.xml'
WORKSPACE = 'production'

# The entries both sides hold, and the lines the run side reads them at.
OWNED_NAME = 'Web-Server-1'
OWNED_LINE = 5
ORDER_NAME = 'Web-Services'
STATE_ADDRESS = 'panos_address.web_server_1_11f477f4'
NO_FACTS = {'device_group': '', 'vsys': '', 'template': '', 'vsys_device': ''}
FOOTER = 'Entry lines are grouped by'


@pytest.fixture
def state():
    """The committed state document, read through the state door."""
    return state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)


def _entry(state: state_input.StateSource, name: str, resource_type: str = 'panos_address') -> state_input.StateEntry:
    """One fixture entry, read through the producer."""
    return next(e for e in state.entries if e.entry_name == name and e.resource_type == resource_type)


def _state_args(extra: tuple = ()) -> tuple:
    return ('--state', str(FIXTURES_DIR / STATE_FIXTURE), '--workspace', WORKSPACE, *extra)


def _findings(converter_module, fixture: str, out, state) -> list:
    """The findings of the run itself, so the facts come from the run's ledger."""
    parser = run_pipeline(converter_module, fixture, out, _state_args())
    return state_coverage.state_findings(parser.ledger, state)


def _section(report: str, heading: str) -> str:
    """One report section: from its heading to the next heading, or to the entry-line footer."""
    start = report.index(heading)
    rest = report[start + len(heading):]
    end = rest.index('--- ') if '--- ' in rest else report.index(FOOTER)
    return report[start:start + len(heading) + end]


def _report(out) -> str:
    return (out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8')


# --- 1. The state entry shape ------------------------------------------------

def test_the_matrix_row_is_the_same_table_the_property_scan_uses(state):
    """AC-1.3: the row is keyed by the resource type through `MATRIX_BY_RESOURCE`, so the scan
    holds no second naming rule for a state entry."""
    entry = _entry(state, OWNED_NAME)
    assert entry.resource_type in entry_coverage.MATRIX_BY_RESOURCE, entry.resource_type
    assert entry_coverage.MATRIX_BY_RESOURCE[entry.resource_type] is \
        entry_coverage.MATRIX_BY_RESOURCE['panos_address']


def test_the_identity_keys_are_not_properties(state):
    """AC-1.3, F4.3 rule 3: the entry name and the location are identity, not content, and an
    empty value is not a property."""
    properties = state_coverage.state_properties(_entry(state, OWNED_NAME))
    assert 'name' not in properties and 'location' not in properties, properties
    assert properties['description'] == 'Web tier', properties

    empty = next(e for e in state.entries if e.resource_name == 'empty_property_b2b2b2b2')
    assert 'tag' not in state_coverage.state_properties(empty), state_coverage.state_properties(empty)
    assert 'description' not in state_coverage.state_properties(empty), \
        'an empty value is not a property'


def test_the_position_is_the_resource_address(state):
    """AC-1.4: a state entry has no source line, so its position is its resource address."""
    assert _entry(state, 'Module-Only').address == 'network:panos_address.module_only_66666666'
    assert _entry(state, OWNED_NAME).address == STATE_ADDRESS, _entry(state, OWNED_NAME)
    assert not hasattr(state.entries[0], 'line'), 'the producer records no source line'


def test_a_nested_block_reads_as_an_object_or_a_one_element_list(state):
    """AC-1.6: the provider writes a nested block either way, so both shapes read."""
    assert state_coverage.nested_block({'shared': {}}) == {'shared': {}}
    assert state_coverage.nested_block([{'shared': [{}]}]) == {'shared': [{}]}
    assert state_coverage.nested_block('not a block') == {}, 'a value that is not a block fills nothing'
    # The fixture holds both shapes for the same key, so both read the same facts.
    list_shape = next(e for e in state.entries if e.resource_name == 'web_server_1_11f477f4')
    object_shape = next(e for e in state.entries if e.resource_name == 'empty_property_b2b2b2b2')
    assert state_coverage.state_facts(list_shape) == state_coverage.state_facts(object_shape)


# --- 2. The ownership fact ---------------------------------------------------

def test_the_key_is_identity_as_the_f3_9_rule_reads_it(converter_module, tmp_path, state):
    """AC-2.1: the matrix row, the entry name, and the four declared facts, read from the run.
    A shared run entry is keyed with empty facts, never with the `Shared` fallback."""
    findings = _findings(converter_module, RUN_FIXTURE, tmp_path / 'out', state)
    row = next(f for f in findings if f['name'] == OWNED_NAME)
    key = state_coverage.ownership_key(row['resource'], row['name'],
                                      {fact: row[fact] for fact in container_coverage.SCOPE_FACT_KEYS})
    assert key == ('panos_address', OWNED_NAME, '', '', '', ''), key
    assert all(row[fact] == '' for fact in container_coverage.SCOPE_FACT_KEYS), row
    assert state_coverage.state_index(state)[key] is _entry(state, OWNED_NAME), key
    assert 'Shared' not in str(key), 'the parse fallback is not a declared fact'


def test_a_declared_fact_makes_a_different_object(state):
    """AC-2.2: the same name in a different scope is a different object, so a shared run entry is
    not keyed against the state entry in `Production-DG`."""
    index = state_coverage.state_index(state)
    shared_key = ('panos_address', 'Web-Range', '', '', '', '')
    declared_key = ('panos_address', 'Web-Range', 'Production-DG', 'Vsys2', '', 'firewall-2')
    assert shared_key in index and declared_key in index, index
    assert index[shared_key] is not index[declared_key], 'two objects, two keys'


def test_the_shared_block_fills_no_fact(state):
    """AC-2.2: `shared` names the shared section, which states no name, so it fills no fact."""
    assert state_coverage.state_facts(_entry(state, OWNED_NAME)) == NO_FACTS, \
        state_coverage.state_facts(_entry(state, OWNED_NAME))


def test_the_placeholder_device_names_no_device(state):
    """AC-2.2, F3.5: `localhost.localdomain` names no firewall, so it is never a `vsys_device`
    fact, and `container_coverage.PLACEHOLDER_DEVICE` is the one definition both paths read."""
    facts = state_coverage.state_facts(_entry(state, 'Placeholder-Device'))
    assert facts['vsys_device'] == '', facts
    assert facts['vsys'] == 'Vsys1', facts
    assert container_coverage.PLACEHOLDER_DEVICE == 'localhost.localdomain', container_coverage.PLACEHOLDER_DEVICE


def test_a_block_that_names_no_fact_is_not_keyed(state):
    """AC-2.2: `template_stack` names a scope this converter never emits, so an entry placed there
    is not keyed."""
    entry = next(e for e in state.entries if e.resource_name == 'web_server_1_55555555')
    assert state_coverage.state_facts(entry) is None, state_coverage.state_facts(entry)


def test_the_first_entry_for_a_key_wins_in_document_order(state):
    """AC-2.3: one run entry is one finding, so the first state entry that carries the key wins."""
    index = state_coverage.state_index(state)
    key = ('panos_address', OWNED_NAME, '', '', '', '')
    assert index[key].resource_name == 'web_server_1_11f477f4', index[key]
    same_key = [e for e in state.entries if e.entry_name == OWNED_NAME
                and e.resource_type == 'panos_address' and state_coverage.state_facts(e) == NO_FACTS]
    assert len(same_key) == 2, 'the fixture holds two entries that carry the same key'
    assert index[key] is same_key[0], 'the first one in document order wins'


def test_the_scan_scope_is_the_f4_4_rule_on_both_sides(state):
    """AC-2.4: a state resource whose type has no matrix row is not in the index, and a run entry
    no matrix row covers is not a finding."""
    index = state_coverage.state_index(state)
    assert not any(key[0] == 'panos_schedule' for key in index), index

    # `regions.xml` holds the name the state document holds, under a count-only container row.
    region_ledger = entry_coverage.EntryLedger(parse_xml(FIXTURES_DIR / REGION_FIXTURE))
    row = next(r for r in region_ledger.rows() if r['name'] == 'North-America')
    assert row['destination'] == 'count-only', row
    assert entry_coverage.matrix_row_for(row['container']) is None, row
    assert state_coverage.state_findings(region_ledger, state) == [], 'the run side is not covered'


def test_a_run_with_no_declared_state_reports_nothing(converter_module, tmp_path):
    """AC-2.5: no state source, no state to read, no ownership fact and no drift fact."""
    out = tmp_path / 'out'
    parser = run_pipeline(converter_module, RUN_FIXTURE, out)
    assert state_coverage.state_findings(parser.ledger, None) == []
    report = _report(out)
    assert state_coverage.OWNERSHIP_HEADING not in report, report
    assert state_coverage.DRIFT_HEADING not in report, report


# --- 3. The drift fact -------------------------------------------------------

def test_only_a_declared_property_both_sides_hold_by_the_same_name_is_compared(converter_module, tmp_path):
    """AC-3.1 and AC-3.2: a property one side does not hold is not compared, and a property the
    two sides name differently is not compared, because no mapping rule exists."""
    findings = _findings(converter_module, RUN_FIXTURE, tmp_path / 'out',
                         state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE))
    drifted = {finding['name']: finding['drift'] for finding in findings}
    assert drifted[OWNED_NAME] == (('description', 'Web server', 'Web tier'),
                                   ('type', 'ip-netmask', 'address')), drifted
    # The state holds `description` for Web-Range; the run side holds none for that entry.
    assert drifted['Web-Range'] == (), drifted
    keys = {key for finding in findings for key, _, _ in finding['drift']}
    assert 'tag' not in keys and 'uuid' not in keys, keys


def test_member_order_is_part_of_the_value(converter_module, tmp_path):
    """AC-3.3: the same members in a different order is a drift finding."""
    state = state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)
    findings = _findings(converter_module, SERVICE_FIXTURE, tmp_path / 'out', state)
    finding = next(f for f in findings if f['name'] == ORDER_NAME)
    assert finding['drift'] == (('members', ['service-http', 'TCP-8080'],
                                 ['TCP-8080', 'service-http']),), finding['drift']


def test_a_drift_fact_needs_an_ownership_fact(converter_module, tmp_path):
    """AC-3.4: an entry the state does not own cannot drift, so the drift section is a subset of
    the ownership section: every drift line is an ownership line with the values added."""
    out = tmp_path / 'out'
    state = state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)
    findings = _findings(converter_module, RUN_FIXTURE, out, state)
    drifting = [f for f in findings if f['drift']]
    assert drifting, findings
    assert {f['name'] for f in drifting} < {f['name'] for f in findings}, findings
    report = _report(out)
    ownership = _section(report, state_coverage.OWNERSHIP_HEADING)
    for finding in drifting:
        prefix = state_coverage.ownership_line(finding)
        assert prefix in ownership, ownership
        assert state_coverage.drift_line(finding) in _section(report, state_coverage.DRIFT_HEADING)
        assert len(state_coverage.drift_line(finding).splitlines()) == 1


def test_the_state_scan_read_does_not_count_as_a_property_read(converter_module, tmp_path):
    """AC-3.5: the state scan is not an output, so it reads through `RecordingDict.value` and the
    property section is unchanged by it."""
    before_out = tmp_path / 'without_state'
    after_out = tmp_path / 'with_state'
    without = run_pipeline(converter_module, RUN_FIXTURE, before_out)
    before = sorted(entry_coverage.property_line(row) for row in without.ledger.property_findings())
    before_rows = sorted((row['name'], row['fields']) for row in without.ledger.rows())
    with_state = run_pipeline(converter_module, RUN_FIXTURE, after_out, _state_args())
    after = sorted(entry_coverage.property_line(row) for row in with_state.ledger.property_findings())
    after_rows = sorted((row['name'], row['fields']) for row in with_state.ledger.rows())
    assert before == after, (before, after)
    assert before_rows == after_rows, (before_rows, after_rows)
    for line in _section(_report(before_out), entry_coverage.PROPERTY_HEADING).splitlines():
        assert line in _report(after_out), line


# --- 4. The report sections and the exit code --------------------------------

def test_the_two_sections_print_after_the_property_section(converter_module, tmp_path):
    """AC-4.1: ownership, then drift, both after the property section, and each prints only when
    it has a finding."""
    out = tmp_path / 'out'
    run_pipeline(converter_module, RUN_FIXTURE, out, _state_args())
    report = _report(out)
    assert report.index(entry_coverage.PROPERTY_HEADING) < \
        report.index(state_coverage.OWNERSHIP_HEADING) < \
        report.index(state_coverage.DRIFT_HEADING) < report.index(FOOTER), report
    assert report.count(state_coverage.OWNERSHIP_HEADING) == 1, report
    assert report.count(state_coverage.DRIFT_HEADING) == 1, report


def test_the_ownership_line_shape_is_fixed(converter_module, tmp_path):
    """AC-4.2: line, object type, name, matrix row, state source, resource address."""
    out = tmp_path / 'out'
    state = state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)
    findings = _findings(converter_module, RUN_FIXTURE, out, state)
    finding = next(f for f in findings if f['name'] == OWNED_NAME)
    name = f'{finding["container"]}/{finding["name"]}'
    expected = (f'  line {OWNED_LINE:>4}  ' + f'{name:<38} ' + f'{finding["resource"]:<32} '
                + f'state source: {STATE_FIXTURE} ({finding["state_address"]})')
    assert state_coverage.ownership_line(finding) == expected, state_coverage.ownership_line(finding)
    report = _report(out)
    assert expected in _section(report, state_coverage.OWNERSHIP_HEADING), report
    # The section names the source by its report value, never by its path (F4.2 rule 6).
    assert '/' not in STATE_FIXTURE, STATE_FIXTURE
    assert str(FIXTURES_DIR) not in _section(report, state_coverage.OWNERSHIP_HEADING), report


def test_the_drift_line_shape_is_fixed(converter_module, tmp_path):
    """AC-4.2: the ownership shape, then the properties in sorted order, values as JSON text so
    one finding stays on one line."""
    out = tmp_path / 'out'
    findings = _findings(converter_module, RUN_FIXTURE, out,
                         state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE))
    finding = next(f for f in findings if f['drift'])
    expected = (state_coverage.ownership_line(finding)
                + '  value differs: description ("Web server" vs "Web tier"), '
                + 'type ("ip-netmask" vs "address")')
    assert state_coverage.drift_line(finding) == expected, state_coverage.drift_line(finding)
    assert expected in _section(_report(out), state_coverage.DRIFT_HEADING)
    assert len(expected.splitlines()) == 1, 'one finding stays on one line'


def test_the_lines_are_grouped_by_the_f3_9_scope_rule(converter_module, tmp_path):
    """AC-4.3: the same grouping function the other report sections use."""
    out = tmp_path / 'out'
    state = state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)
    findings = _findings(converter_module, RUN_FIXTURE, out, state)
    generator = converter_module.TerraformGenerator(str(out), {})
    header = generator._report_section_header(generator._report_scope_path(findings[0]))
    assert header == 'SHARED SECTION', header
    report = _report(out)
    assert header in _section(report, state_coverage.OWNERSHIP_HEADING), report
    assert header in _section(report, state_coverage.DRIFT_HEADING), report
    assert header in report[report.index(FOOTER):], report


def test_the_console_prints_no_state_line_and_the_exit_code_is_unchanged(converter_module, tmp_path):
    """AC-4.4: a state fact is an operator action, so the F4.1 gate still decides the exit code,
    and the console prints no state line."""
    out = tmp_path / 'out'
    saved_argv = list(sys.argv)
    sys.argv = ['panorama_to_terraform.py', str(FIXTURES_DIR / RUN_FIXTURE),
                '--output-dir', str(out), *_state_args()]
    try:
        with contextlib.redirect_stdout(io.StringIO()) as console:
            code = converter_module.main()
    finally:
        sys.argv = saved_argv
    assert code == 0, 'a state fact does not change the exit code (AC-4.4)'
    value = console.getvalue()
    assert 'state source' not in value and 'value differs' not in value, value
    assert not hasattr(state_coverage, 'console_line'), 'the state scan owns no console wording'
    report = _report(out)
    assert state_coverage.OWNERSHIP_HEADING in report, report
    assert state_coverage.DRIFT_HEADING in report, report


# --- 5. Determinism and the record -------------------------------------------

def test_two_runs_on_the_same_bytes_write_the_same_bytes(converter_module, tmp_path):
    """AC-8: the index keeps the first entry for a key in document order and the findings are
    sorted by line, then object type, then name, so two runs write the same bytes."""
    first = tmp_path / 'first'
    second = tmp_path / 'second'
    run_pipeline(converter_module, RUN_FIXTURE, first, _state_args())
    run_pipeline(converter_module, RUN_FIXTURE, second, _state_args())
    assert {path.name: path.read_bytes() for path in first.iterdir()} == \
           {path.name: path.read_bytes() for path in second.iterdir()}
    lines = [line for line in _section(_report(first), state_coverage.OWNERSHIP_HEADING).splitlines()
             if line.startswith('  line')]
    assert lines == sorted(lines), lines
    assert len(lines) == 2, lines


def test_the_state_record_reads_back_with_no_new_field(converter_module, tmp_path):
    """AC-6.1, AC-6.3 and AC-6.4: one record per source read, in read order, and the byte facts
    name the file a reader can reopen."""
    out = tmp_path / 'out'
    assert run_main(converter_module, [str(FIXTURES_DIR / RUN_FIXTURE), '--output-dir', str(out),
                             *_state_args()]) == 0
    records = provenance.parse_records((out / provenance.PROVENANCE_FILE).read_text(encoding='utf-8'))
    assert [record.kind for record in records] == ['file', 'state'], records
    state_record = records[1]
    assert state_record.name == STATE_FIXTURE, state_record
    assert state_record.path == str(FIXTURES_DIR / STATE_FIXTURE), state_record
    assert state_record.scope == WORKSPACE, state_record
    assert state_record.size == (FIXTURES_DIR / STATE_FIXTURE).stat().st_size, state_record
    assert provenance.cache_reference(state_record) is None, 'the state record references nothing'
