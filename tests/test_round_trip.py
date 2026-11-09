"""F4.6 (`docs/ARCHITECTURE.md` §4.6): the round-trip cross-check (`sanity_checks.check_round_trip`).

The rule compares two sets, each read through the module that owns it: the `.tf` block set through the one
block reader (`sanity_checks.blocks`, `kinds = ('resource',)`), and the entry set through the run's
`entry_coverage.EntryLedger` and the one scope rule `entry_coverage.matrix_row_for`. The join is the matrix
row and the unit, so the rule states no reader, no count, no scope, no kind, no type, no field name, no file
name and no unit rule of its own. `run_checks` takes the ledger as an argument, so a call with no ledger
reports the check as NOT RUN and a pin that reads only the output directory is unchanged.

Pins, one per criterion in `acceptance.md`:

- 1.1-1.7 what the rule reads: the one block reader, the run's ledger, the one scope rule, the one unit rule,
  the NOT RUN path, the second source, and the report's two counts;
- 2.1-2.8 the finding: one finding per unit and per row, the fact is the two counts, the position is the
  position the reader read, the row is named through `COVERAGE_MATRIX`, both directions, the sort, the root
  file, and no scan console line;
- 3.1-3.10 which types the rule can compare: the scan scope, the destination kinds, the scope rows, and the
  rows no entry measures;
- 4.1-4.7 the `CHECK_ORDER` position, the report order, the corpus, determinism, the exit code, and the path 2
  run, where the join reads the same ledger the cross-check reads.

Four criteria could not hold as written, and each is pinned as measured with the measurement in the
`acceptance.md` Result:

- 4.3: the corpus is not silent. The rule reports 20 findings on 9 fixtures, in three categories: an
  `emitted` entry the row counts with no block of the row's type, a block read for a property level (no
  ledger row), and one entry that writes more than one block. `backlog.md` keeps the three open.
- 2.4 and 4.6: a disagreeing count names no broken output, so the rule states WARN, the decision
  `entry_coverage.PROPERTY_RULE` already states for a gap. The exit code follows the rules that read the
  files, so every fixture still exits 0, which is the corpus pin in `tests/test_sanity_gate.py`.
- 3.3: `matrix_row_for` answers no row for a `nested-block` container, so the entry side reads no count for
  it, but a block that entry wrote still enters the block side, so the pair is compared and disagrees.
- 3.2: `EntryLedger.destination` answers the destination in one place, in the order: the per-entry fact on
  the recorded object, then the destination the mark recorded, then the container table row. An entry the run
  reports enters no count, so `address_objects.xml` reads clean and `GAP_FIXTURE` names the fixture the rule
  still reports.

Every test that reads the entry side runs the pipeline in process, because `run_script` loses the ledger with
the process. The suite runs offline.
"""

import re
from pathlib import Path

import api_requests
import container_coverage
import entry_coverage
import naming
import panorama_to_terraform
import sanity_checks
import unit_manifest
from conftest import FIXTURES_DIR, SAMPLE_CONFIG, path2_run, run_pipeline, run_script, tf_files

CONVERTER = 'panorama_to_terraform.py'

# An `emitted` entry the row counts with no block of the row's type: `ae1.101`, an aggregate entry whose
# block is a `panos_aggregate_layer3_subinterface` block. `address_objects.xml` reads clean once the
# destination is answered from the recorded object, so the pin reads a fixture the rule still reports.
GAP_FIXTURE = 'interfaces_other.xml'
# The unit the run names for that fixture: its entries sit under a declared vsys, not under `Shared`.
GAP_UNIT = 'vsys1_b3e94a35'
SHARED_UNIT = 'shared_45ca31c3'
# A `nested-block` container row: `network/interface/virtual-wire/units`.
NESTED_FIXTURE = 'interfaces_ethernet.xml'
# Bookkeeping rows, the five scope containers, and the run that names `report`, `count-only`, `inventory`
# and `skipped` rows together.
BOOKKEEPING_FIXTURE = 'multi_device_templates.xml'
SCOPE_FIXTURE = 'scope_objects.xml'
REPORT_FIXTURE = 'application_filters.xml'
KIND_FIXTURE = 'kitchen_sink.xml'
# The fixture the property scan reports, so the console shape that names one identity stays visible.
PROPERTY_SCAN_FIXTURE = 'address_objects.xml'

# The corpus findings, as the rule reports them: (row, unit, entries the ledger reads, blocks the reader
# reads), in the order the rule sorts them. Each is one of the three categories the rule cannot join, and each
# is recorded in `backlog.md`: an `emitted` entry the row counts with no block of the row's type (the entry
# side counts more than the block side), a block read for a property level (the entry side reads no row, so the
# count is zero), and one entry that writes more than one block (the block side counts more). The sample run
# reads clean, so the check prints PASS on the run `tests/test_sanity_gate.py` pins. `address_objects.xml`
# reads clean, because its three report-only entries answer `report` and enter no count.
CORPUS_GAPS = {
    'dependency_wiring.xml': [('panos_ethernet_interface', 'vsys1_d7045c06', 3, 2),
                              ('panos_ethernet_layer3_subinterface', 'vsys1_d7045c06', 0, 2)],
    'edge_mixed_vr_lr.xml': [('panos_virtual_router_static_route_ipv4', 'fw_template_00a08cdc', 0, 2),
                             ('panos_virtual_router_static_route_ipv4', 'vsys1_b3e94a35', 0, 1)],
    'interfaces_ethernet.xml': [('panos_ethernet_interface', 'vsys1_b3e94a35', 4, 5),
                                ('panos_ethernet_layer3_subinterface', 'vsys1_b3e94a35', 0, 2)],
    'interfaces_other.xml': [('panos_aggregate_interface', 'vsys1_b3e94a35', 2, 1),
                             ('panos_aggregate_layer3_subinterface', 'vsys1_b3e94a35', 0, 2)],
    'logical_routers.xml': [('panos_virtual_router_static_route_ipv4', 'fw_template_00a08cdc', 0, 1)],
    'report_grouping.xml': [('panos_ethernet_layer3_subinterface', 'datacenter_fw_31baa141', 0, 1),
                            ('panos_ethernet_layer3_subinterface', 'fw_2_example_com_35aafbcf', 0, 1),
                            ('panos_ethernet_layer3_subinterface', 'office_fw_4507d824', 0, 1),
                            ('panos_ethernet_layer3_subinterface', SHARED_UNIT, 0, 1),
                            ('panos_ethernet_layer3_subinterface', 'vsys2_536d5bfc', 0, 1)],
    'scope_child.xml': [('panos_address', SHARED_UNIT, 0, 1)],
    'virtual_routers.xml': [('panos_virtual_router_static_route_ipv4', 'fw_template_00a08cdc', 0, 2)],
    KIND_FIXTURE: [('panos_virtual_router_static_route_ipv4', 'fw_template_00a08cdc', 0, 3),
                   ('panos_ethernet_layer3_subinterface', 'shared_a6577c11', 0, 1),
                   ('panos_aggregate_interface', 'shared_a6577c11', 2, 1),
                   ('panos_aggregate_layer3_subinterface', 'shared_a6577c11', 0, 2)],
}

# The same 20 findings, counted by category: the entry side counts more, the entry side reads no row for the
# block, and the block side counts more. The first category has three instances: `dependency_wiring.xml`,
# `interfaces_other.xml`, and the same aggregate case in `kitchen_sink.xml`.
CATEGORY_COUNTS = {'entry side counts more': 3, 'block read for a property level': 16,
                   'entry writes more than one block': 1}

# The two counts, read out of the fact the rule states.
COUNTS_RE = re.compile(r'reads (\d+) entries, the reader reads (\d+) blocks')
STATE_ARGS = ('--state', str(FIXTURES_DIR / 'state_workspace.json'), '--workspace', 'production')


def _run(fixture: str, out_dir, extra: tuple = ()) -> tuple:
    """Run the pipeline in process and return the two sets the rule compares."""
    parser = run_pipeline(panorama_to_terraform, fixture, out_dir, extra)
    assert parser is not None, f'{fixture}: the run refused the input'
    return tf_files(out_dir), parser.ledger


def _rule_source() -> str:
    """One rule's source, so a scan pins what that rule reads. The boundaries are the ones
    `tests/test_data_file_gate.py` pins: `check_data_files` … `check_round_trip` … `check_request_set` …
    `check_control_chars`.
    """
    source = Path(sanity_checks.__file__).read_text(encoding='utf-8')
    return source[source.index('def check_round_trip'):source.index('def check_request_set')]


def _fact(finding) -> tuple:
    """The fact as the rule states it: the row, the unit, and the two counts.

    The rule names no entry, so a test reads the fact through these four parts and restates no wording.
    """
    parts = re.search(r'row ([a-z0-9_]+) in unit ([a-z0-9_]+)', finding.detail)
    counts = COUNTS_RE.search(finding.detail)
    if parts is None or counts is None:
        raise AssertionError(finding.render())
    return (parts.group(1), parts.group(2), int(counts.group(1)), int(counts.group(2)))


def _count_rows() -> set:
    """The count rows: the matrix rows the one scope rule can answer, read over the container table."""
    return {matrix['resource'] for matrix in
            (entry_coverage.matrix_row_for(container.path)
             for container in container_coverage.CONTAINER_TABLE) if matrix is not None}


def _corpus_fixtures() -> list:
    """The corpus the pins read: the committed fixtures, and not the hostile inputs a byte rule reads."""
    return sorted(p.name for p in FIXTURES_DIR.glob('*.xml') if not p.name.startswith('hostile_'))


# --- 1. What the rule reads ----------------------------------------------------

def test_the_rule_reads_the_block_set_through_the_gate_reader(tmp_path):
    """1.1: one reader serves the rule, so no second reader and no field reader appears.
    """
    files, ledger = _run(GAP_FIXTURE, tmp_path)
    rule = _rule_source()
    assert "blocks(files, ('resource',))" in rule, 'the rule reads through the one block reader'
    assert not [call for call in ('re.compile', 're.search', 're.match', 're.findall') if call in rule], \
        'the rule writes no reader of its own'
    assert 'fields_at' not in rule, 'a count is a fact about blocks, not about fields'
    # The block side is the set the one reader read, at the reader's kinds.
    read = sanity_checks.blocks(files, ('resource',))
    assert len(read) == 6, [block.file for block in read]
    assert all(Path(block.file).parent.name == GAP_UNIT for block in read), 'one unit directory'
    assert not sanity_checks.blocks(files, ('data', 'import', 'action')), 'no other kind enters the count'
    assert len(sanity_checks.check_round_trip(files, ledger)) == 2, 'the two counts do not agree'


def test_the_entry_count_is_read_through_the_ledger_and_the_scan_scope_rule(tmp_path):
    """1.2: the entry side is the run's ledger, and the scope is the one scope rule the scan reads.
    """
    files, ledger = _run(GAP_FIXTURE, tmp_path)
    rule = _rule_source()
    assert 'ledger.rows()' in rule and 'entry_coverage.matrix_row_for' in rule, \
        'the entry count comes from the module that owns it'
    assert 'covering_row' not in rule, 'no second scope rule appears'
    # The count the fact states is the set the ledger names for one unit and one row.
    fact = _fact(sanity_checks.check_round_trip(files, ledger)[0])
    row = entry_coverage.MATRIX_BY_RESOURCE[fact[0]]
    entries = [r for r in ledger.rows()
               if r['destination'] == 'emitted' and entry_coverage.matrix_row_for(r['container']) is row]
    assert fact[2] == len(entries) == 2, fact
    assert all(r['source'] == ledger.source.origin.name for r in entries), 'one ledger, one source'
    assert fact[3] == len([block for block in sanity_checks.blocks(files, ('resource',))
                           if Path(block.file).parent.name == fact[1] and block.rtype == fact[0]]) == 1, \
        'the block side is the reader\'s set for that unit and row'
    assert len(sanity_checks.check_round_trip(files, ledger)) == 2, 'one finding for one unit and row'


def test_the_unit_is_read_through_the_one_unit_rule(tmp_path):
    """1.3: the block's unit is the directory part of the path the reader read, and the entry's unit is the
    same name read through `unit_manifest`.
    """
    files, ledger = _run(GAP_FIXTURE, tmp_path)
    rule = _rule_source()
    assert 'unit_manifest.facts_of' in rule and 'unit_manifest.directory_name' in rule, \
        'the unit is read through the one unit rule'
    assert 'naming.sanitize' in rule, 'the directory shape is read through the one naming rule'
    unit = _fact(sanity_checks.check_round_trip(files, ledger)[0])[1]
    assert unit == GAP_UNIT, 'the run names the unit the fixture entries sit under'
    block = sanity_checks.blocks(files, ('resource',))[0]
    assert Path(block.file).parent.name == unit, 'the unit is the directory the reader read'
    row = [r for r in ledger.rows() if r['destination'] == 'emitted'][0]
    assert unit_manifest.directory_name(unit_manifest.facts_of(row), naming.sanitize) == unit, \
        'the entry and the block land on one unit name'
    assert len(unit_manifest.units(ledger)) == 2, 'the run wrote two unit directories'
    assert unit in {unit_manifest.directory_name(facts, naming.sanitize)
                    for facts in unit_manifest.units(ledger)}


def test_the_rule_reads_no_report_and_no_data_file(tmp_path):
    """1.4: the rule reads the `.tf` block set and the run's ledger, and nothing else, so the data rule's
    input and the report bodies are unchanged.
    """
    rule = _rule_source()
    for name in ('DATA_FILES', 'parse_rows', 'render_tfvars', 'site_data', 'ownership',
                 'reference_edges', 'read_tf_files', 'CONVERSION_REPORT', 'SANITY_REPORT'):
        assert name not in rule, f'the cross-check reads no record through {name}'
    # The data rule's slice now ends here, so its half still reads only the records at the root.
    source = Path(sanity_checks.__file__).read_text(encoding='utf-8')
    data_rule = source[source.index('def check_data_files'):source.index('def check_round_trip')]
    assert 'parse_rows' in data_rule and 'check_round_trip' not in data_rule, \
        'the data rule reads no ledger, and the cross-check reads no record'
    files, ledger = _run(GAP_FIXTURE, tmp_path)
    plain = sanity_checks.run_checks(tmp_path)
    ran = sanity_checks.run_checks(tmp_path, ledger=ledger)
    assert (plain.file_count, plain.data_file_count, plain.resource_count) == \
        (ran.file_count, ran.data_file_count, ran.resource_count), 'the report counts do not move'
    assert plain.data_file_count == 2, 'the four records at the root are still the data rule\'s input'
    assert 'Files checked: 5 .tf files, 2 data files.' in ran.render(), ran.render()


def test_the_rule_reports_not_run_when_the_caller_passes_no_ledger(tmp_path):
    """1.5: a pin that reads only the output directory is unchanged, and a run that passes the ledger reports
    a rule that ran.
    """
    files, ledger = _run(GAP_FIXTURE, tmp_path)
    plain = sanity_checks.run_checks(tmp_path)
    results = plain.results('round_trip')
    assert len(results) == 1 and not results[0].ran, results
    assert results[0].result == sanity_checks.NOT_RUN, results
    assert 'ledger' in results[0].note, results[0].note
    assert plain.findings('round_trip') == [], 'NOT RUN states no finding'
    ran = sanity_checks.run_checks(tmp_path, ledger=ledger)
    assert [result.check for result in ran.checks] == list(sanity_checks.CHECK_ORDER), ran.render()
    assert ran.result_of('round_trip') == sanity_checks.WARN, ran.render()
    assert re.search(r'^round_trip\s+WARN \(2\)$', ran.render(), re.M), ran.render()
    # `main()` passes the run's ledger, so a real run reports the check as a rule that ran.
    out = tmp_path / 'run'
    assert run_script(CONVERTER, str(FIXTURES_DIR / GAP_FIXTURE), '--output-dir', str(out)).returncode == 0
    assert re.search(r'^round_trip\s+WARN \(2\)$', (out / 'SANITY_REPORT.txt').read_text(encoding='utf-8'),
                     re.M)


def test_a_second_source_adds_no_count(tmp_path):
    """1.6: the rule reads the ledger for the source the run wrote output from, so a state source (F5.6) adds
    no count. The declared parent source half (F5.4) is held by `tests/test_ownership.py`.
    """
    files, ledger = _run(KIND_FIXTURE, tmp_path / 'plain')
    state_files, state_ledger = _run(KIND_FIXTURE, tmp_path / 'state', STATE_ARGS)
    assert state_files == files, 'the state source writes no file, so the block set is the same'
    assert sanity_checks.check_round_trip(files, ledger) == \
        sanity_checks.check_round_trip(state_files, state_ledger), 'the state source adds no count'
    assert state_ledger.source.origin.kind == 'file', 'the run names one source for its output'
    # No ledger row names the state file, because the run writes no output from it.
    state_rows = [r for r in state_ledger.rows() if r['source'] != state_ledger.source.origin.name]
    assert state_rows == [], [r['source'] for r in state_rows]
    assert len(state_ledger.rows()) == len(ledger.rows()), 'the state scan adds no entry to the ledger'


def test_the_report_counts_do_not_move_for_the_cross_check(tmp_path):
    """1.7: the report's two counts are the `.tf` files the reader read and the four records at the root, so
    the cross-check is not a third count. `tests/test_sanity_gate.py::test_console_summary_reports_the_result`
    holds the same fact.
    """
    assert run_script(CONVERTER, str(SAMPLE_CONFIG), '--output-dir', str(tmp_path)).returncode == 0
    plain = sanity_checks.run_checks(tmp_path)
    parser = run_pipeline(panorama_to_terraform, None, tmp_path, (str(SAMPLE_CONFIG),))
    ran = sanity_checks.run_checks(tmp_path, ledger=parser.ledger)
    assert (plain.file_count, plain.data_file_count, plain.resource_count) == (14, 2, 20), plain.render()
    assert ran.file_count == len(tf_files(tmp_path)), 'the block counts do not move'
    assert 'Files checked: 14 .tf files, 2 data files.' in ran.render(), ran.render()
    assert 'Resources checked: 20.' in ran.render(), ran.render()
    assert 'Sanity gate: PASS (0 FAIL, 0 WARN) - 14 .tf files, 2 data files, 20 resources' in \
        ran.console_summary(), ran.console_summary()


# --- 2. The finding ------------------------------------------------------------

def test_a_count_that_does_not_agree_is_one_finding_per_unit_and_row(tmp_path):
    """2.1: one finding per unit and per row, and the fact is the two counts.
    """
    files, ledger = _run(KIND_FIXTURE, tmp_path)
    findings = sanity_checks.check_round_trip(files, ledger)
    facts = [_fact(f) for f in findings]
    assert len(facts) == 4, [f.render() for f in findings]
    assert len(set(facts)) == len(facts), 'one fact per unit and row'
    assert len({(row, unit) for row, unit, _, _ in facts}) == 4, facts
    assert len({unit for _, unit, _, _ in facts}) == 2, 'the same row in two units is two findings'
    assert all(f.check == 'round_trip' and COUNTS_RE.search(f.detail) for f in findings), \
        [f.render() for f in findings]
    # A fact that names no entry cannot restate the per-entry report, which `docs/ARCHITECTURE.md` §3.2 owns.
    names = {r['name'] for r in ledger.rows() if len(r['name']) > 2}
    assert all(not [name for name in names if name in f.detail] for f in findings), \
        [f.render() for f in findings]


def test_the_rule_names_no_entry(tmp_path):
    """2.1: the fact names the row and the unit, never one entry.
    """
    files, ledger = _run(GAP_FIXTURE, tmp_path)
    finding = sanity_checks.check_round_trip(files, ledger)[0]
    # A name that is a digit cannot be told from the unit name the fact states, so the pin reads the names
    # longer than two characters, as `test_a_count_that_does_not_agree_is_one_finding_per_unit_and_row` does.
    names = {r['name'] for r in ledger.rows() if r['destination'] == 'emitted' and len(r['name']) > 2}
    assert len(names) == 2, sorted(names)
    assert not [name for name in names if name in finding.detail], finding.render()
    assert _fact(finding) == ('panos_aggregate_interface', GAP_UNIT, 2, 1), finding.render()
    # The two entries the fact counts are `ae1` and `ae1.101`, and the reader read one block for that row.
    assert COUNTS_RE.search(finding.detail).groups() == ('2', '1'), finding.render()
    assert finding.detail.count(':') == 1, 'the fact states the two counts and nothing else'


def test_a_finding_names_the_file_and_the_line_the_reader_read(tmp_path):
    """2.2: the position is the path from the codebase root and the line of the first block the reader read
    for that unit and row; when the reader read no block, the position is the file as a whole.
    """
    files, ledger = _run(KIND_FIXTURE, tmp_path)
    findings = sanity_checks.check_round_trip(files, ledger)
    blocks_read = sanity_checks.blocks(files, ('resource',))
    assert blocks_read, 'the reader read a block for the run'
    named = [f for f in findings if _fact(f)[3]]
    assert named, findings
    for finding in named:
        row, unit = _fact(finding)[0], _fact(finding)[1]
        first = [block for block in blocks_read
                 if Path(block.file).parent.name == unit and block.rtype == row][0]
        assert finding.file == first.file, finding.render()
        assert finding.line == first.line, finding.render()
    # The finding whose entry side counts a row the reader read no block for states the whole file, and the
    # file is the unit plus the name the row states.
    whole = sanity_checks.check_round_trip({}, ledger)
    assert whole, findings
    for finding in whole:
        row, unit = _fact(finding)[0], _fact(finding)[1]
        assert finding.line == 0, finding.render()
        assert finding.file == f'{unit}/{entry_coverage.MATRIX_BY_RESOURCE[row]["output_file"]}', \
            finding.render()
    # The same rule with no block read: the position is the file as a whole for each row the entry side
    # counts. In the gap unit the aggregate row counts `ae1` and `ae1.101`, and the three other interface
    # rows count one entry each, so the rule states the file for each of them.
    single = sanity_checks.check_round_trip({}, run_pipeline(panorama_to_terraform, GAP_FIXTURE,
                                                             tmp_path / 'ao').ledger)
    assert [f.render() for f in single] == [
        f'{GAP_UNIT}/interfaces.tf  row panos_aggregate_interface in unit {GAP_UNIT}: '
        f'the ledger reads 2 entries, the reader reads 0 blocks',
        f'{GAP_UNIT}/interfaces.tf  row panos_loopback_interface in unit {GAP_UNIT}: '
        f'the ledger reads 1 entries, the reader reads 0 blocks',
        f'{GAP_UNIT}/interfaces.tf  row panos_tunnel_interface in unit {GAP_UNIT}: '
        f'the ledger reads 1 entries, the reader reads 0 blocks',
        f'{GAP_UNIT}/interfaces.tf  row panos_vlan_interface in unit {GAP_UNIT}: '
        f'the ledger reads 1 entries, the reader reads 0 blocks'], [f.render() for f in single]


def test_the_rule_states_no_type_of_its_own(tmp_path):
    """2.3: the fact names the row through `COVERAGE_MATRIX`, so no `panos_` name is a string constant.
    """
    rule = _rule_source()
    assert 'panos_' not in rule, 'the type comes from the table, not from the rule'
    assert 'entry_coverage.MATRIX_BY_RESOURCE' in rule, 'the join reads the same table the scope rule reads'
    files, ledger = _run(GAP_FIXTURE, tmp_path)
    fact = _fact(sanity_checks.check_round_trip(files, ledger)[0])
    assert fact[0] in entry_coverage.MATRIX_BY_RESOURCE, fact
    assert entry_coverage.MATRIX_BY_RESOURCE[fact[0]]['resource'] == 'panos_aggregate_interface', fact
    assert not [part for part in re.findall(r"'[^']*'", rule) if 'panos_' in part], rule


def test_the_rule_detects_a_block_with_no_entry(tmp_path):
    """2.4, first direction: the gate reads the files as the operator receives them, so a hand-written block
    is an input. The finding is a coverage fact, so the rule states WARN, not FAIL, and the exit code is the
    rules that read the files; `acceptance.md` states FAIL and the measurement is in the Result.
    """
    files, ledger = _run(GAP_FIXTURE, tmp_path)
    planted = dict(files)
    planted[f'{GAP_UNIT}/planted.tf'] = 'resource "panos_address" "planted_00000000" {\n  name = "Planted"\n}\n'
    findings = sanity_checks.check_round_trip(planted, ledger)
    assert len(findings) == 3, [f.render() for f in findings]
    # The planted row is one the entry side reads no row for in this unit, so the fact is the block side alone.
    planted_finding = [f for f in findings if _fact(f)[0] == 'panos_address']
    assert len(planted_finding) == 1, [f.render() for f in findings]
    assert _fact(planted_finding[0]) == ('panos_address', GAP_UNIT, 0, 1), planted_finding[0].render()
    # The position is the first block the reader read for that unit and row, so the planted block is read like
    # any other input rather than named as an exception.
    read_for_row = [block for block in sanity_checks.blocks(planted, ('resource',))
                    if Path(block.file).parent.name == GAP_UNIT and block.rtype == 'panos_address']
    assert len(read_for_row) == 1 and read_for_row[0].file == planted_finding[0].file, \
        [f.render() for f in findings]
    assert planted_finding[0].line == read_for_row[0].line, planted_finding[0].render()
    assert len(sanity_checks.blocks(planted, ('resource',))) == 7, 'the planted block enters the count'
    assert all(finding.severity == sanity_checks.WARN for finding in findings), \
        [f.render() for f in findings]


def test_the_rule_detects_an_entry_with_no_block(tmp_path):
    """2.4, second direction: the silent drop the cross-check exists for.
    """
    files, ledger = _run(GAP_FIXTURE, tmp_path)
    findings = sanity_checks.check_round_trip(files, ledger)
    assert len(findings) == 2 and COUNTS_RE.search(findings[0].detail).groups() == ('2', '1'), \
        [f.render() for f in findings]
    assert findings[0].severity == sanity_checks.WARN, findings[0].render()
    # Both directions are findings, so a count of zero on one side is still a finding.
    only_blocks = {f'{GAP_UNIT}/interfaces.tf':
                   'resource "panos_aggregate_interface" "one_00000000" {\n  name = "One"\n}\n'}
    assert len(sanity_checks.check_round_trip(only_blocks, ledger)) == 4, 'one block for five entries'
    no_blocks = sanity_checks.check_round_trip({}, ledger)
    assert len(no_blocks) == 4 and _fact(no_blocks[0])[3] == 0, [f.render() for f in no_blocks]
    assert no_blocks[0].line == 0, 'the reader read no block, so the position is the file as a whole'
    # The exit code is the rules that read the files, so the cross-check adds no exit-code rule.
    out = tmp_path / 'run'
    assert run_script(CONVERTER, str(FIXTURES_DIR / GAP_FIXTURE), '--output-dir', str(out)).returncode == 0


def test_the_rule_reports_an_emitted_entry_that_writes_no_block(tmp_path):
    """2.5: the report line names the entry as `emitted` and the unit directory holds no block of the row's
    type for it, so the rule states it as a count that does not agree. `acceptance.md` says no committed
    fixture shows one; `tests/fixtures/interfaces_other.xml` shows one for the aggregate row, so the pin reads
    the fixture, and `backlog.md` keeps the fact with this rule named as the rule that states it.
    """
    files, ledger = _run(GAP_FIXTURE, tmp_path)
    emitted = [r for r in ledger.rows() if r['destination'] == 'emitted']
    assert len(emitted) == 5, [r['name'] for r in emitted]
    read = sanity_checks.blocks(files, ('resource',))
    assert len(read) == 6, 'the aggregate row counts two entries against one block'
    # The block a run writes is named by the entry name in the slug shape, so the aggregate row holds one
    # block, for `ae1`, and none for `ae1.101`, whose block is read for the subinterface row.
    aggregate_blocks = [block for block in read if block.rtype == 'panos_aggregate_interface']
    assert len(aggregate_blocks) == 1 and aggregate_blocks[0].local.startswith('ae1_'), \
        [block.local for block in read]
    assert not [block for block in aggregate_blocks if '101' in block.local], [block.local for block in read]
    # The per-entry report names the entry as `emitted`, which is the fact the cross-check reads.
    report = (tmp_path / 'CONVERSION_REPORT.txt').read_text(encoding='utf-8')
    line = [part for part in report.splitlines() if 'aggregate-ethernet/ae1.101' in part and 'emitted' in part]
    assert line and 'captured' in line[0], line
    assert len(sanity_checks.check_round_trip(files, ledger)) == 2, 'one fact per row, not one line per entry'


def test_the_report_is_byte_identical_between_two_runs(tmp_path):
    """2.6 and 4.4: the same files read twice state the same bytes, with no timestamp and no absolute path,
    and the findings are in the (file, line, detail) order `check_data_files` already uses.
    """
    for case in ('first', 'second'):
        assert run_script(CONVERTER, str(FIXTURES_DIR / KIND_FIXTURE),
                          '--output-dir', str(tmp_path / case)).returncode == 0
    first, second = tmp_path / 'first', tmp_path / 'second'
    assert (first / 'SANITY_REPORT.txt').read_bytes() == (second / 'SANITY_REPORT.txt').read_bytes()
    for case in (first, second):
        text = case.read_text(encoding='utf-8') if case.is_file() else (case / 'SANITY_REPORT.txt').read_text(
            encoding='utf-8')
        assert not re.search(r'\d{2}:\d{2}:\d{2}', text), text
        assert str(tmp_path) not in text
        for line in text.split('\n'):
            if line.startswith('  '):
                assert not line.lstrip().startswith('/'), line
    # The rule is the same between two reads of the same files, and the findings sort by the three parts.
    parser = run_pipeline(panorama_to_terraform, KIND_FIXTURE, tmp_path / 'third')
    findings = sanity_checks.check_round_trip(tf_files(first), parser.ledger)
    assert findings == sanity_checks.check_round_trip(tf_files(second), parser.ledger)
    assert findings == sorted(findings, key=lambda f: (f.file, f.line, f.detail)), [f.render() for f in findings]


def test_a_tf_file_at_the_root_names_no_unit(tmp_path):
    """2.7: `write_path.py` writes no `.tf` file in the root set, so a block read there is a count that
    cannot be assigned to a unit.
    """
    files, ledger = _run(GAP_FIXTURE, tmp_path)
    planted = dict(files)
    planted['root.tf'] = 'resource "panos_address" "root_00000000" {\n  name = "Root"\n}\n'
    findings = sanity_checks.check_round_trip(planted, ledger)
    assert len(findings) == 3, [f.render() for f in findings]
    root = [f for f in findings if f.file == 'root.tf']
    assert root, findings
    assert 'cannot be assigned to a unit' in root[0].detail, root[0].render()
    assert root[0].line == 1 and root[0].file == 'root.tf', root[0].render()
    assert Path('root.tf').parent.name == '', 'the root set names no unit'
    # The run itself writes no `.tf` file at the root, so the root finding only comes from an input file.
    assert not [name for name in files if '/' not in name], 'the run writes no root .tf file'


def test_the_rule_prints_no_scan_line(tmp_path):
    """2.8: the fact compares two sets, so the console shape, which names one identity, is not used here, and
    the gate's own summary prints the finding as it prints every finding.
    """
    rule = _rule_source()
    assert 'console_line' not in rule and 'CONSOLE_PREFIX' not in rule, 'the rule prints no scan line'
    out = tmp_path / 'run'
    result = run_script(CONVERTER, str(FIXTURES_DIR / GAP_FIXTURE), '--output-dir', str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    gate = result.stdout.split('Sanity gate:')[1]
    assert 'round_trip: WARN' in gate, gate
    # The finding prints in the gate summary, in the shape every finding uses, and the gate gains no scan
    # section of its own.
    finding = [line for line in gate.splitlines() if line.startswith('    ')]
    assert len(finding) == 2 and 'row panos_aggregate_interface in unit' in finding[0], gate
    # The scans that print still print: the gap fixture reports no property finding, so the pin reads the
    # fixture the property scan reports.
    scan = run_script(CONVERTER, str(FIXTURES_DIR / PROPERTY_SCAN_FIXTURE),
                      '--output-dir', str(tmp_path / 'scan'))
    assert scan.returncode == 0, scan.stdout + scan.stderr
    assert 'Property findings' in scan.stdout, scan.stdout


# --- 3. Which types the rule can compare ---------------------------------------

def test_the_count_scope_is_the_scan_scope_read_through_one_rule(tmp_path):
    """3.1: the count scope is the property-scan scope, so the rule states no kind list of its own.
    """
    count_rows = _count_rows()
    assert len(count_rows) == 41, sorted(count_rows)
    assert 'panos_address' in count_rows and 'panos_device_group_parent' not in count_rows, sorted(count_rows)
    rule = _rule_source()
    assert 'matrix_row_for' in rule, 'one scope rule serves the scan and the cross-check'
    assert not [part for part in re.findall(r"'[^']*'", rule) if part in entry_coverage.DESTINATION_KINDS], \
        'the rule states no kind list'
    files, ledger = _run(GAP_FIXTURE, tmp_path)
    findings = sanity_checks.check_round_trip(files, ledger)
    assert all(_fact(f)[0] in count_rows for f in findings), [f.render() for f in findings]
    # The scan and the cross-check read the same rule, so a row the scan names is a row the count can name.
    for row in ledger.rows():
        if row['destination'] == 'emitted':
            assert entry_coverage.matrix_row_for(row['container'])['resource'] in count_rows, row['container']
    assert entry_coverage.matrix_row_for('address') is entry_coverage.MATRIX_BY_RESOURCE['panos_address'], \
        'the same rule, the same table'


def test_an_entry_the_run_reports_is_not_counted(tmp_path):
    """3.2: the destination is read per entry, so an entry the run reports is not in the count. The
    `report_only` address case now holds as written, because the fact is read from the recorded object.
    """
    files, ledger = _run(REPORT_FIXTURE, tmp_path)
    reported = [r for r in ledger.rows() if r['destination'] == 'report']
    assert len(reported) == 1, [r['name'] for r in reported]
    assert entry_coverage.matrix_row_for(reported[0]['container']) is None, reported[0]['container']
    assert sanity_checks.check_round_trip(files, ledger) == [], 'a report entry enters no count'
    # The address case reads clean, so the pin keeps a run that still disagrees: a planted `panos_address`
    # block for `Country-US` is a count the entry side cannot join, so the whole fact is the pair.
    files, ledger = _run(PROPERTY_SCAN_FIXTURE, tmp_path)
    report_only = [r for r in ledger.rows() if r['captured'].get('report_only')]
    assert len(report_only) == 2, [r['name'] for r in report_only]
    assert all(r['destination'] == 'report' for r in report_only), [r['name'] for r in report_only]
    assert sanity_checks.check_round_trip(files, ledger) == [], 'so those two entries leave the count'
    planted = dict(files)
    planted[f'{SHARED_UNIT}/planted.tf'] = (
        'resource "panos_address" "country_us_00000000" {\n  name = "Country-US"\n}\n')
    findings = sanity_checks.check_round_trip(planted, ledger)
    assert len(findings) == 1, [f.render() for f in findings]
    assert _fact(findings[0]) == ('panos_address', SHARED_UNIT, 5, 6), findings[0].render()


def test_a_nested_block_row_is_not_counted(tmp_path):
    """3.3: a `nested-block` row writes lines inside a parent block, so `matrix_row_for` answers no row for
    the entry side. A block that entry wrote still enters the block side, so the pair is compared and
    disagrees; the criterion concluded the rule cannot compare it, and the measurement is in the
    `acceptance.md` Result.
    """
    files, ledger = _run(NESTED_FIXTURE, tmp_path)
    nested = [r for r in ledger.rows() if r['destination'] == 'nested-block']
    assert len(nested) == 1, [r['name'] for r in nested]
    assert entry_coverage.matrix_row_for(nested[0]['container']) is None, nested[0]['container']
    findings = sanity_checks.check_round_trip(files, ledger)
    assert len(findings) == 2, [f.render() for f in findings]
    assert {_fact(f)[1] for f in findings} == {'vsys1_b3e94a35'}, [f.render() for f in findings]
    # The nested-block entry wrote a block, so the block side counts it against an entry side of four.
    entry = [f for f in findings if _fact(f)[0] == 'panos_ethernet_interface']
    assert entry and _fact(entry[0]) == ('panos_ethernet_interface', 'vsys1_b3e94a35', 4, 5), \
        [f.render() for f in findings]
    assert 'nested-block' in entry_coverage.DESTINATION_KINDS, 'the kind is stated once'


def test_a_bookkeeping_row_is_not_counted(tmp_path):
    """3.4: the fact a bookkeeping row records is the relation between the entry and its container, so the
    count reads no row for it.
    """
    files, ledger = _run(BOOKKEEPING_FIXTURE, tmp_path)
    bookkeeping = [r for r in ledger.rows() if r['destination'] == 'bookkeeping']
    assert len(bookkeeping) == 7, len(bookkeeping)
    assert all(entry_coverage.matrix_row_for(r['container']) is None for r in bookkeeping), \
        [r['container'] for r in bookkeeping]
    assert entry_coverage.NAMES_NO_FIELD_KINDS == ('bookkeeping',), 'the kind is stated once'
    assert sanity_checks.check_round_trip(files, ledger) == [], 'the bookkeeping rows read clean'
    assert ledger.counts()['bookkeeping'] == 7, 'the rule reads the ledger, not a count of its own'


def test_a_kind_that_writes_no_block_is_not_counted(tmp_path):
    """3.5: `count-only`, `inventory`, `skipped` and `unaccounted` write no block, so they enter no count; the
    report section and the console line are the output for those entries. The destination is read per entry,
    so a `skipped` entry inside a container row the scope rule answers is still not counted.
    """
    files, ledger = _run(KIND_FIXTURE, tmp_path)
    kinds = {r['destination'] for r in ledger.rows()}
    assert {'count-only', 'inventory', 'skipped', 'report'} <= kinds, sorted(kinds)
    for kind in ('count-only', 'inventory', 'skipped', 'report', 'bookkeeping'):
        rows = [r for r in ledger.rows() if r['destination'] == kind]
        assert rows, kind
        # The count reads only `emitted` rows, so a kind that writes no block enters no count even when its
        # entry sits inside a container the scope rule answers.
        assert all(entry_coverage.matrix_row_for(r['container']) is None for r in rows) \
            or kind in ('skipped', 'report'), \
            (kind, [r['container'] for r in rows if entry_coverage.matrix_row_for(r['container'])])
    # The report half, as the rule answers it: the report-only address entry sits inside `address`, the
    # container the scope rule answers, and still enters no count.
    report_rows = [r for r in ledger.rows() if r['destination'] == 'report']
    answered = [r for r in report_rows if entry_coverage.matrix_row_for(r['container'])]
    assert len(answered) == 1 and answered[0]['container'] == 'address', [r['container'] for r in answered]
    skipped = [r for r in ledger.rows() if r['destination'] == 'skipped']
    assert [r for r in skipped if entry_coverage.matrix_row_for(r['container'])], \
        'a skipped entry can sit inside a row the scope rule answers, and is still not counted'
    assert entry_coverage.GAP_KINDS == ('count-only', 'skipped', 'unaccounted'), 'one definition'
    counted = {_fact(f)[0] for f in sanity_checks.check_round_trip(files, ledger)}
    assert counted <= set(entry_coverage.MATRIX_BY_RESOURCE), sorted(counted)
    assert len(sanity_checks.check_round_trip(files, ledger)) == 4, [f.render() for f in
        sanity_checks.check_round_trip(files, ledger)]


def test_the_scope_rows_are_counted_through_the_same_rule(tmp_path):
    """3.6: the five scope containers are `emitted` rows the scope rule answers, so they are in the count
    through the same rule, and the row is named through `row['resource']`.
    """
    files, ledger = _run(SCOPE_FIXTURE, tmp_path)
    rows = [entry_coverage.matrix_row_for(r['container']) for r in ledger.rows()
            if r['destination'] == 'emitted']
    assert len(rows) == 7, len(rows)
    named = sorted({row['resource'] for row in rows})
    scope_named = sorted(entry_coverage.matrix_row_for(container)['resource']
                         for container in sorted(container_coverage.SCOPE_CONTAINERS)
                         if entry_coverage.matrix_row_for(container) is not None)
    assert scope_named == ['panos_device_group', 'panos_template', 'panos_template_stack', 'panos_vsys'], \
        scope_named
    assert named == sorted(scope_named + ['panos_template_variable']), named
    assert entry_coverage.matrix_row_for('variable') is \
        entry_coverage.MATRIX_BY_RESOURCE['panos_template_variable'], 'the scope rule answers the variable row'
    assert all(row is entry_coverage.MATRIX_BY_RESOURCE[row['resource']] for row in rows), 'the table row'
    assert all(row['resource'] in _count_rows() for row in rows), 'a scope row is a count row'
    assert sanity_checks.check_round_trip(files, ledger) == [], [f.render() for f in
        sanity_checks.check_round_trip(files, ledger)]


def test_a_row_no_entry_measures_is_not_a_count_row(tmp_path):
    """3.7: `panos_device_group_parent` is the row the scope rule can never answer, because one device-group
    entry feeds the scope block and the parent record, so it is not a count row.
    """
    row = entry_coverage.MATRIX_BY_RESOURCE['panos_device_group_parent']
    assert entry_coverage.matrix_row_for(row['xml_element']) is None, row['xml_element']
    assert entry_coverage.matrix_row_for('devices') is None, \
        'the scope container that feeds the parent record answers no row'
    assert 'panos_device_group_parent' not in _count_rows(), sorted(_count_rows())
    rule = _rule_source()
    assert 'panos_device_group_parent' not in rule, 'the rule states no exception list'
    files, ledger = _run('device_groups.xml', tmp_path)
    assert sanity_checks.check_round_trip(files, ledger) == [], [f.render() for f in
        sanity_checks.check_round_trip(files, ledger)]
    blocks_read = sanity_checks.blocks(tf_files(tmp_path), ('resource',))
    assert all(block.rtype in _count_rows() for block in blocks_read), [block.rtype for block in blocks_read]


def test_no_other_block_kind_enters_the_count(tmp_path):
    """3.8: the decision is the reader's `kinds` argument, so a `data` block, an `import` block, an `action`
    block and a `variable` declaration enter no count.
    """
    files, ledger = _run(GAP_FIXTURE, tmp_path)
    planted = dict(files)
    planted[f'{GAP_UNIT}/other.tf'] = (
        'data "panos_address" "d_00000000" {\n  location = { vsys1 = {} }\n  name = "Other"\n}\n'
        'import {\n  to = panos_aggregate_interface.ae1_5552830e\n}\n'
        'action "commit" "a_00000000" {\n  location = { vsys1 = {} }\n}\n'
        'variable "other" {\n  description = "no block"\n}\n')
    read = sanity_checks.blocks(planted, ('resource', 'data', 'import', 'action'))
    assert len(read) == 9, [block.kind for block in read]
    assert len(sanity_checks.blocks(planted, ('resource',))) == 6, 'the reader read one kind for the count'
    assert sorted({block.kind for block in read}) == ['action', 'data', 'import', 'resource'], \
        sorted({block.kind for block in read})
    findings = sanity_checks.check_round_trip(planted, ledger)
    assert len(findings) == 2, [f.render() for f in findings]
    assert _fact(findings[0]) == ('panos_aggregate_interface', GAP_UNIT, 2, 1), findings[0].render()
    assert all(block.kind == 'resource' for block in sanity_checks.blocks(planted, ('resource',)))
    rule = _rule_source()
    assert "blocks(files, ('resource',))" in rule, 'the decision is the reader\'s kinds argument'


def test_the_rule_states_no_field_name_of_its_own(tmp_path):
    """3.9: the rule reads no field, so it reads no name, and `entry_coverage.name_field` is not called.
    """
    rule = _rule_source()
    assert 'name_field' not in rule, 'the rule reads no name, so it reads no field'
    for field in ('name', 'entry', 'captured', 'fields', 'detail'):
        assert f"'{field}'" not in rule, f'the rule states no field name: {field}'
    assert 'row[' in rule, 'the rule reads the row shape the module owns'
    assert entry_coverage.name_field('panos_address') == 'name', 'the one naming rule stays the owner'
    files, ledger = _run(GAP_FIXTURE, tmp_path)
    finding = sanity_checks.check_round_trip(files, ledger)[0]
    row = entry_coverage.MATRIX_BY_RESOURCE['panos_aggregate_interface']
    assert not [field for field in row['properties'] if field in finding.detail], finding.render()
    # The fact names no entry: read the names the fact counts, because a name the fact could not name (the
    # scope entry `vsys1`) is also part of the unit name it states.
    counted = [r for r in ledger.rows() if r['destination'] == 'emitted'
               and entry_coverage.matrix_row_for(r['container']) is row]
    assert len(counted) == 2, [r['name'] for r in counted]
    assert not [r['name'] for r in counted if r['name'] in finding.detail], finding.render()


def test_the_rule_reads_no_file_name_rule(tmp_path):
    """3.10: the count is a fact about a unit and a row, so a block for a row written in another file of the
    same unit is not a finding, and the rule states no file name of its own.
    """
    rule = _rule_source()
    assert '*.tf' not in rule and 'glob' not in rule, 'the rule checks no file name'
    assert 'output_file' in rule, 'the whole-file position reads the name the row states'
    files, ledger = _run(GAP_FIXTURE, tmp_path)
    moved = {f'{GAP_UNIT}/moved_{Path(name).name}': text for name, text in files.items()}
    findings = sanity_checks.check_round_trip(moved, ledger)
    assert len(findings) == 2, [f.render() for f in findings]
    # The same unit and the same row, so the count is the same fact in another file of that unit.
    assert _fact(findings[0]) == ('panos_aggregate_interface', GAP_UNIT, 2, 1), findings[0].render()
    assert Path(findings[0].file).parent.name == GAP_UNIT, findings[0].render()
    moved_name = entry_coverage.MATRIX_BY_RESOURCE['panos_aggregate_interface']['output_file']
    assert Path(findings[0].file).name == f'moved_{moved_name}', findings[0].render()
    # The file names themselves are pinned by `tests/test_golden_files.py`, not by this rule.
    assert run_script(CONVERTER, str(FIXTURES_DIR / GAP_FIXTURE),
                      '--output-dir', str(tmp_path / 'run')).returncode == 0


# --- 4. Gate order, determinism, and the corpus -------------------------------

def test_check_order_puts_the_cross_check_after_the_data_rule():
    """4.1: the cross-check and the join are the two rules that read two sets, so they sit after every rule
    that reads one set, and the two agreement rules stay together.
    """
    order = list(sanity_checks.CHECK_ORDER)
    assert order.index('round_trip') == order.index('data_files') + 1, order
    assert order.index('round_trip') < order.index('control_chars'), order
    assert order[-1] == 'terraform', 'the cross-check is a static rule, so the plan stays last'
    assert len(order) == len(set(order)), order
    assert [name for name in order if order.index(name) < order.index('round_trip')][-1] == 'data_files'


def test_the_report_names_the_checks_in_the_pinned_order(tmp_path):
    """4.2: the report names the checks in the pinned order, and the cross-check is a rule that ran.
    """
    parser = run_pipeline(panorama_to_terraform, None, tmp_path, (str(SAMPLE_CONFIG),))
    report = sanity_checks.run_checks(tmp_path, ledger=parser.ledger)
    assert [result.check for result in report.checks] == list(sanity_checks.CHECK_ORDER), report.render()
    assert re.search(r'^round_trip\s+PASS$', report.render(), re.M), report.render()
    for name in sanity_checks.CHECK_ORDER:
        assert re.search(rf'^{name}\s+', report.render(), re.M), report.render()
    # A check that cannot run names its result, so a check cannot be silently absent.
    plain = sanity_checks.run_checks(tmp_path)
    assert re.search(r'^round_trip\s+NOT RUN', plain.render(), re.M), plain.render()
    assert re.search(r'^terraform\s+NOT RUN', plain.render(), re.M), plain.render()
    assert plain.failed is False, 'a NOT RUN result does not fail the gate'
    assert re.search(r'^terraform\s+NOT RUN', plain.render(), re.M), 'the plan stays the last result'


def test_the_rule_reports_nothing_across_the_corpus(tmp_path):
    """4.3, the half that holds: the sample run reads clean, so the gate reports PASS for the check on the run
    `tests/test_sanity_gate.py` pins. The other half is `::test_the_rule_reports_the_gaps_the_corpus_contains`.
    """
    assert run_script(CONVERTER, str(SAMPLE_CONFIG), '--output-dir', str(tmp_path)).returncode == 0
    text = (tmp_path / 'SANITY_REPORT.txt').read_text(encoding='utf-8')
    assert 'Result: PASS (0 FAIL, 0 WARN)' in text, text
    assert re.search(r'^round_trip\s+PASS$', text, re.M), text
    assert 'FINDINGS' in text and '(No finding.)' in text.split('FINDINGS')[1], text
    for fixture in _corpus_fixtures():
        out = tmp_path / fixture
        parser = run_pipeline(panorama_to_terraform, fixture, out)
        if parser is None:
            continue
        findings = sanity_checks.check_round_trip(tf_files(out), parser.ledger)
        if fixture in CORPUS_GAPS:
            assert findings, fixture
        else:
            assert findings == [], (fixture, [f.render() for f in findings])
            assert not [f for f in findings if f.check == 'round_trip'], fixture


def test_the_rule_reports_the_gaps_the_corpus_contains(tmp_path):
    """4.3, as measured: `acceptance.md` claimed the corpus trips no finding, so this pin reads what the rule
    reports instead. The 20 findings on 9 fixtures are the three categories the rule cannot join, and each is
    recorded in `backlog.md`.
    """
    base = tmp_path / 'corpus'
    total = 0
    by_category = dict.fromkeys(CATEGORY_COUNTS, 0)
    for fixture in _corpus_fixtures():
        out = base / fixture
        parser = run_pipeline(panorama_to_terraform, fixture, out)
        if parser is None:
            continue
        findings = sanity_checks.check_round_trip(tf_files(out), parser.ledger)
        total += len(findings)
        assert sorted(_fact(f) for f in findings) == sorted(CORPUS_GAPS.get(fixture, [])), \
            (fixture, [f.render() for f in findings])
        for finding in findings:
            assert finding.check == 'round_trip' and finding.severity == sanity_checks.WARN, finding.render()
            assert Path(finding.file).parent.name, finding.render()
            row, _, entries, blocks_read = _fact(finding)
            if entries == 0:
                by_category['block read for a property level'] += 1
            elif entries > blocks_read:
                by_category['entry side counts more'] += 1
            else:
                by_category['entry writes more than one block'] += 1
    assert total == 20, total
    assert by_category == CATEGORY_COUNTS, by_category
    assert len(CORPUS_GAPS) == 9, sorted(CORPUS_GAPS)


def test_the_cross_check_finding_is_a_coverage_fact_not_a_broken_output(tmp_path):
    """The severity the rule can hold: a disagreeing count names no broken output, so the rule states WARN, the
    decision `entry_coverage.PROPERTY_RULE` already states for a gap. `acceptance.md` stated FAIL for both
    directions, which would fail the corpus pins in `tests/test_sanity_gate.py`; the measurement is in the
    `acceptance.md` Result.
    """
    files, ledger = _run(GAP_FIXTURE, tmp_path)
    findings = sanity_checks.check_round_trip(files, ledger)
    assert findings and all(f.severity == sanity_checks.WARN for f in findings), \
        [f.render() for f in findings]
    report = sanity_checks.SanityReport(checks=(sanity_checks.CheckResult('round_trip', tuple(findings)),),
                                        file_count=len(files),
                                        resource_count=len(sanity_checks.blocks(files, ('resource',))))
    assert report.result_of('round_trip') == sanity_checks.WARN, report.render()
    assert not report.failed, 'a WARN-only result does not fail the gate'
    out = tmp_path / 'run'
    assert run_script(CONVERTER, str(FIXTURES_DIR / GAP_FIXTURE), '--output-dir', str(out)).returncode == 0
    assert 'Result: PASS (0 FAIL, 2 WARN)' in (out / 'SANITY_REPORT.txt').read_text(encoding='utf-8')


def test_not_run_does_not_change_the_exit_code(tmp_path):
    """4.6: the exit code follows the findings through `tests/test_sanity_gate.py`, a NOT RUN result changes
    nothing, and the rules that read the files still decide it.
    """
    assert run_script(CONVERTER, str(SAMPLE_CONFIG), '--output-dir', str(tmp_path)).returncode == 0
    text = (tmp_path / 'SANITY_REPORT.txt').read_text(encoding='utf-8')
    assert 'Result: PASS (0 FAIL, 0 WARN)' in text, text
    parser = run_pipeline(panorama_to_terraform, None, tmp_path, (str(SAMPLE_CONFIG),))
    assert sanity_checks.run_checks(tmp_path).result_of('round_trip') == sanity_checks.NOT_RUN
    assert sanity_checks.run_checks(tmp_path, ledger=parser.ledger).result_of('round_trip') == 'PASS'
    # A planted file the file-reading rules refuse still exits 1, so the cross-check cannot hide a FAIL.
    (tmp_path / 'planted.tf').write_text(
        'resource "panos_address" "planted_00000000" {\n  name = "Planted"\n'
        '  value = panos_zone.ghost.name\n}\n', encoding='utf-8')
    assert run_script(CONVERTER, str(SAMPLE_CONFIG), '--output-dir', str(tmp_path)).returncode == 1
    text = (tmp_path / 'SANITY_REPORT.txt').read_text(encoding='utf-8')
    assert 'Result: FAIL' in text, text
    assert '[references]' in text.split('FINDINGS')[1], text
    # The cross-check names the same file as a coverage fact, so the FAIL comes from the rule that reads the
    # file, not from the count.
    cross = [line for line in text.split('FINDINGS')[1].splitlines() if line.startswith('  ')]
    assert len(cross) == 3, cross
    assert any('[round_trip]' in line for line in text.split('FINDINGS')[1].splitlines()), text


def test_the_cross_check_reads_the_join_ledger_on_a_path_2_run(tmp_path, monkeypatch):
    """4.7: a path 2 run reads the join, so the cross-check compares the block set with the join's own rows
    through the same ledger the join joins. The join answers rows, not counts, so a path 2 run reports no
    cross-check finding: the set the cross-check compares is the set the run wrote, and the run wrote the join's
    rows as entries. The pin plants one block for a unit the join names, so the two rules name the same unit
    through the one unit rule.
    """
    out = tmp_path / 'run'
    parser, index = path2_run(out, tmp_path / 'cache', monkeypatch)
    join = api_requests.unit_findings(index, parser.ledger)
    join_units = {unit_manifest.directory_name(facts, naming.sanitize) for facts, entry in join if facts}
    assert len(join) == 7 and len(join_units) == 3, sorted(join_units)
    assert sanity_checks.check_round_trip(tf_files(out), parser.ledger) == [], 'the run reads sets that agree'
    # `shared_45ca31c3` is a unit both rules name, and its row is the row the container table answers for the
    # address container, so one planted block makes the two counts disagree on a row the join reads.
    unit = 'shared_45ca31c3'
    assert unit in join_units, sorted(join_units)
    (out / unit / 'planted.tf').write_text(
        'resource "panos_address" "planted_00000000" {\n  location = { shared = {} }\n'
        '  name = "Planted"\n}\n', encoding='utf-8')
    findings = sanity_checks.check_round_trip(tf_files(out), parser.ledger)
    assert len(findings) == 1, [f.render() for f in findings]
    fact = _fact(findings[0])
    assert fact[1] == unit and fact[1] in join_units, 'the two rules name the same unit'
    assert fact[0] == entry_coverage.matrix_row_for('address')['resource'], fact
    assert fact[2] < fact[3], 'the planted block is the block the reader reads and the join has no entry for'
    # The planted block names no unit of its own: the fact is the fact the join's data holds for that unit,
    # so the join reports the same fact shape with no position.
    join_fact = [f for f in sanity_checks.check_request_set(index, parser.ledger)
                 if f.file == unit]
    assert join_fact and join_fact[0].line == 0 and join_fact[0].severity == sanity_checks.WARN, join_fact
