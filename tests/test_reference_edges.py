"""F6.3 the reference between units: the edge record, the acyclic rule, and the unit order.

Six groups, one per rule in `reference_edges.py` and `acceptance.md`:

1. The edge row and the join: one row per pair the data can name, joined to the manifest on
   `directory` and to the ownership record on (`type`, `entry`).
2. The reference fact stays one fact: the module records no name and resolves no name, and a unit
   cannot be its own target.
3. The acyclic rule: the cycle walk, the report section, and the unit in a cycle that cannot be ranked.
4. The unit order: `after` from the three bases (ancestor, level, edge), `rank` with the identity tie.
5. The report section, the console, and the exit codes.
6. The gates, determinism, and the rule that a file is written only when it has content.

Every test runs offline, and the module writes no `.tf` byte.
"""

import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

import container_coverage
import entry_coverage
import ownership
import reference_edges
import sanity_checks
import state_coverage
import state_input
import unit_manifest
from conftest import FIXTURES_DIR, GOLDEN_DIR, SAMPLE_CONFIG, run_main, run_pipeline, run_script

CONVERTER = 'panorama_to_terraform.py'
RECORD = reference_edges.EDGE_FILE
MANIFEST = unit_manifest.MANIFEST_FILE
CYCLE_FIXTURE = 'reference_cycle.xml'
KITCHEN = 'kitchen_sink.xml'
MULTI = 'multi_device_templates.xml'
OVERRIDE = 'ownership_override.xml'
GROUPING = 'report_grouping.xml'
STATE_FIXTURE = 'state_workspace.json'
WORKSPACE = 'production'

# The edge set across the fixture corpus, measured through the run, in the order the four fields sort
# by. A fixture that starts producing an edge must be added here in the same change, so no fixture can
# become a silent false positive (AC-1.1).
CORPUS_EDGES = {
    KITCHEN: [
        ('fw_2_example_com_5cef6fb6', 'shared_0bc98741', 'panos_ethernet_interface', 'ethernet1/1'),
        ('vsys1_53549b38', 'shared_0bc98741', 'panos_ethernet_interface', 'ethernet1/1'),
        ('vsys2_803b06c0', 'shared_0bc98741', 'panos_ethernet_interface', 'ethernet1/2'),
    ],
    MULTI: [
        ('hq_networks_0491f4e3', 'fw_1_example_com_21a67a9f', 'panos_ethernet_interface', 'ethernet1/1'),
        ('hq_networks_0491f4e3', 'fw_2_example_com_5cef6fb6', 'panos_ethernet_interface', 'ethernet1/1'),
    ],
    CYCLE_FIXTURE: [
        ('fw_a_example_com_4daa3d43', 'fw_b_example_com_f80a1db9', 'panos_ethernet_interface',
         'ethernet1/2'),
        ('fw_b_example_com_f80a1db9', 'fw_a_example_com_4daa3d43', 'panos_ethernet_interface',
         'ethernet1/1'),
    ],
}

# The one finding the cycle fixture produces. The unit the cycle is read from is the smaller of the two,
# so the line is grouped by it (rule 5).
CYCLE_FACTS = ('', '', '', 'fw-a.example.com')
CYCLE_UNITS = ('fw_a_example_com_4daa3d43', 'fw_b_example_com_f80a1db9')
UNIT_A, UNIT_B = CYCLE_UNITS


def _run(source: Path, out_dir: Path, extra: tuple = ()) -> subprocess.CompletedProcess:
    """Run the converter as a script and return the process result."""
    return run_script(CONVERTER, str(source), '--output-dir', str(out_dir), *extra)


def _pipeline(module, source: Path, out_dir: Path, extra: tuple = ()) -> tuple:
    """Run the pipeline in process and return (parser, generator, exit code).

    The reference record lives on the generator and is made during emission, so a test that wants it
    needs both objects. `conftest.run_pipeline` returns the parser, so this hooks the generator the same
    way.
    """
    generator_class = module.TerraformGenerator
    caught = {}
    parser_init = module.PanoramaParser.__init__
    generator_init = generator_class.__init__

    def init_parser(self, *args, **kwargs):
        parser_init(self, *args, **kwargs)
        caught['parser'] = self

    def init_generator(self, *args, **kwargs):
        generator_init(self, *args, **kwargs)
        caught['generator'] = self

    saved_argv = list(sys.argv)
    module.PanoramaParser.__init__ = init_parser
    generator_class.__init__ = init_generator
    try:
        sys.argv = [CONVERTER, str(source), '--output-dir', str(out_dir), *[str(a) for a in extra]]
        with contextlib.redirect_stdout(io.StringIO()):
            code = module.main()
    finally:
        module.PanoramaParser.__init__ = parser_init
        generator_class.__init__ = generator_init
        sys.argv = saved_argv
    # A hostile fixture is refused before the parse, so no parser exists to return.
    return caught.get('parser'), caught.get('generator'), code


def _sets(module, source: Path, out_dir: Path, extra: tuple = ()) -> tuple:
    """The three sets one run builds: the ownership rows, the edge rows, the ordered manifest rows.

    The same three calls `main()` makes, so the test reads the rule through the modules that hold it.
    Returns None for a fixture the run refuses before the parse.
    """
    parser, generator, _code = _pipeline(module, source, out_dir, extra)
    if parser is None:
        return None
    ownership_rows = ownership.build_rows(parser.ledger, None, generator.sanitize_name)
    edge_rows = reference_edges.build_rows(ownership_rows, generator.unit_references(),
                                           generator.sanitize_name)
    manifest_rows = reference_edges.order(
        unit_manifest.build_rows(parser.ledger, generator.unit_references(), generator.sanitize_name),
        ownership_rows, edge_rows)
    return ownership_rows, edge_rows, manifest_rows


def _record(out_dir: Path) -> list:
    """A written edge record, read back as data."""
    return reference_edges.parse_rows((out_dir / RECORD).read_text(encoding='utf-8'))


def _manifest(out_dir: Path) -> list:
    """A written manifest, read back as data."""
    return unit_manifest.parse_rows((out_dir / MANIFEST).read_text(encoding='utf-8'))


def _row(rows: list, directory: str) -> dict:
    """The manifest row for one unit."""
    return next(row for row in rows if row['directory'] == directory)


def _facts(row: dict) -> tuple:
    """The unit identity a row states, in `FACT_KEYS` order."""
    return tuple(row[key] for key in reference_edges.FACT_KEYS)


def _section(report: str, heading: str) -> str:
    """One report section: from its heading to the next heading, or to the entry-line footer."""
    start = report.index(heading)
    rest = report[start + len(heading):]
    end = rest.index('--- ') if '--- ' in rest else report.index('Entry lines are grouped by')
    return report[start:end]


# --- 1. the edge row and the join ---------------------------------------------

def test_the_record_is_one_row_per_edge_the_data_can_name(converter_module, tmp_path):
    """AC-1.1: one row per pair, no repeated row. The pinned set is the measurement, so a fixture that
    starts producing an edge must be added to it in the same change.
    """
    edges = {}
    for path in sorted(FIXTURES_DIR.glob('*.xml')):
        sets = _sets(converter_module, path, tmp_path / path.stem)
        if sets is None:
            continue    # the hostile fixtures are refused before the parse
        _owners, edge_rows, _rows = sets
        if edge_rows:
            edges[path.name] = [tuple(row[key] for key in reference_edges.FIELD_ORDER) for row in edge_rows]
    assert edges == CORPUS_EDGES, edges
    assert sum(len(rows) for rows in edges.values()) == 7
    pairs = [pair for rows in edges.values() for pair in rows]
    assert len(pairs) == len(set(pairs)), 'one row per pair'
    for fixture, expected in CORPUS_EDGES.items():
        out = tmp_path / 'written' / fixture
        assert _run(FIXTURES_DIR / fixture, out).returncode == 0
        assert [{key: row[key] for key in reference_edges.FIELD_ORDER} for row in _record(out)] == \
            [dict(zip(reference_edges.FIELD_ORDER, pair)) for pair in expected]


def test_the_rows_are_the_declared_shape_in_field_order(tmp_path):
    """AC-1.3: the record is data, so the field order is fixed and a document describes it without
    restating a row.
    """
    assert reference_edges.FIELD_ORDER == ('referrer', 'target', 'type', 'entry')
    assert _run(FIXTURES_DIR / CYCLE_FIXTURE, tmp_path).returncode == 0
    text = (tmp_path / RECORD).read_text(encoding='utf-8')
    assert list(json.loads(text)[0]) == list(reference_edges.FIELD_ORDER)
    # Fields print in the declared order, not alphabetically.
    assert text.index('"referrer"') < text.index('"target"') < text.index('"type"') < text.index('"entry"')
    # Rows sort by the four fields in field order, which a reader can reproduce from the file.
    rows = _record(tmp_path)
    assert rows == sorted(rows, key=lambda row: tuple(row[key] for key in reference_edges.FIELD_ORDER))


def test_the_row_joins_to_the_manifest_and_to_the_ownership_record(converter_module, tmp_path):
    """AC-1.2: `referrer` and `target` name units the manifest names, and (`type`, `entry`) names the
    ownership row whose `owner` is the target. The join key is `directory`, the F6.2 rule.
    """
    owners, edge_rows, manifest_rows = _sets(converter_module, FIXTURES_DIR / CYCLE_FIXTURE, tmp_path)
    directories = {row['directory'] for row in manifest_rows}
    assert edge_rows
    for row in edge_rows:
        assert row['referrer'] in directories and row['target'] in directories, row
        joined = [owner for owner in owners if owner['type'] == row['type'] and owner['entry'] == row['entry']]
        assert joined, row
        assert any(owner['owner'] == row['target'] for owner in joined), row
    text = reference_edges.render(edge_rows)
    assert 'path' not in text and 'source_line' not in text, 'the record states no path'


def test_a_name_no_unit_declares_writes_no_row_and_stays_in_the_manifest(converter_module, tmp_path):
    """AC-1.3: the pair does not exist, so the record writes no row, and the name is still stated in
    the manifest's `references` field, the only place that states a reference name.
    """
    out = tmp_path / 'out'
    _owners, edge_rows, manifest_rows = _sets(converter_module, FIXTURES_DIR / GROUPING, out)
    recorded = {name for row in manifest_rows for name in row['references']}
    assert recorded, 'the grouping fixture records names the rule resolved outside the run'
    assert not edge_rows, 'no unit in the run declares those names'
    assert not (out / RECORD).is_file(), 'a record with no row is not written'
    # No ownership row covers a recorded name, so the join finds no pair to name.
    assert not any(row['entry'] in recorded for row in _sets(converter_module, FIXTURES_DIR / GROUPING,
                                                             tmp_path / 'again')[0])


def test_the_record_round_trips_as_data(tmp_path):
    """AC-1.4: a reader reads the record back as itself, the way `provenance.parse_record` reads a
    record.
    """
    assert _run(FIXTURES_DIR / CYCLE_FIXTURE, tmp_path).returncode == 0
    rows = _record(tmp_path)
    assert rows and all(set(row) == set(reference_edges.FIELD_ORDER) for row in rows)
    assert (tmp_path / RECORD).read_text(encoding='utf-8') == reference_edges.render(rows)


def test_a_row_that_is_not_the_declared_shape_is_refused():
    """AC-1.4: the record is data, so a reader cannot fall back to reading prose, and a row that names
    one unit is not an edge.
    """
    good = {'referrer': UNIT_A, 'target': UNIT_B, 'type': 'panos_ethernet_interface', 'entry': 'ethernet1/2'}
    assert reference_edges.parse_rows(json.dumps([good]))[0]['target'] == UNIT_B
    bad_rows = (
        json.dumps({'referrer': UNIT_A}),                     # not a list of rows
        json.dumps([UNIT_A]),                                 # a row that is not an object
        json.dumps([dict(good, route='zone')]),               # a field the shape does not declare
        json.dumps([{key: value for key, value in good.items() if key != 'entry'}]),
        json.dumps([dict(good, entry=2)]),                    # a field that is not a name
        json.dumps([dict(good, referrer='')]),                # a row that names one unit
        json.dumps([dict(good, target='')]),
    )
    for bad in bad_rows:
        with pytest.raises(ValueError):
            reference_edges.parse_rows(bad)


# --- 2. the reference fact stays one fact -------------------------------------

def test_the_module_resolves_no_name_and_records_no_name():
    """AC-2.1: the edge set comes from the names `name_ref` recorded at the sites that applied the rule,
    so this module owns the pair, the walk, and the order only.
    """
    assert not any(hasattr(reference_edges, name) for name in
                   ('name_ref', 'resolve_reference', 'sanitize_name', 'unit_references'))
    assert reference_edges.FACT_KEYS == unit_manifest.FACT_KEYS, 'no second fact order'
    modules = [line.split()[1] for line in Path(reference_edges.__file__).read_text(
        encoding='utf-8').splitlines() if line.startswith(('import ', 'from '))]
    assert modules == ['json', 'collections', 'typing', 'unit_manifest'], modules


def test_a_self_reference_writes_no_row(converter_module, tmp_path):
    """AC-2.2: an edge is a fact between two units, so a name a unit declares and references writes no
    row. No corpus fixture produces one, so the rule is pinned on its own input.
    """
    gen = converter_module.TerraformGenerator(str(tmp_path / 'gen'))
    facts = ('', '', '', 'fw-a.example.com')
    own = unit_manifest.directory_name(facts, gen.sanitize_name)
    assert reference_edges.build_rows(
        [{'type': 'panos_ethernet_interface', 'entry': 'ethernet1/1', 'directory': own, 'owner': own}],
        {facts: ('ethernet1/1',)}, gen.sanitize_name) == []
    across = []
    for path in sorted(FIXTURES_DIR.glob('*.xml')):
        sets = _sets(converter_module, path, tmp_path / path.stem)
        if sets is None:
            continue    # the hostile fixtures are refused before the parse
        _owners, edge_rows, _rows = sets
        across.extend(row for row in edge_rows if row['referrer'] == row['target'])
    assert not across, 'no fixture produces a row that names one unit'


def test_a_name_several_units_own_gives_one_row_per_owner(converter_module, tmp_path):
    """AC-2.3 and `ownership.py` rule 5: the target is the owner, so a name several units declare as
    separate objects gives one row per owner, which is the ambiguous-device case.
    """
    gen = converter_module.TerraformGenerator(str(tmp_path / 'gen'))
    facts = ('HQ-Networks', '', '', '')
    referrer = unit_manifest.directory_name(facts, gen.sanitize_name)
    owners = [unit_manifest.directory_name(('', '', '', 'fw-1.example.com'), gen.sanitize_name),
              unit_manifest.directory_name(('', '', '', 'fw-2.example.com'), gen.sanitize_name)]
    rows = reference_edges.build_rows(
        [{'type': 'panos_ethernet_interface', 'entry': 'ethernet1/1', 'directory': owner, 'owner': owner}
         for owner in owners], {facts: ('ethernet1/1',)}, gen.sanitize_name)
    assert len(rows) == 2 and {row['target'] for row in rows} == set(owners)
    assert all(row['referrer'] == referrer for row in rows), rows
    assert rows == sorted(rows, key=lambda row: tuple(row[key] for key in reference_edges.FIELD_ORDER))


def test_the_golden_tf_bytes_are_unchanged(tmp_path):
    """AC-2.4: F6.3 writes no `.tf` byte, so both golden sets are byte-identical.
    """
    for case, source in (('sample', SAMPLE_CONFIG), ('kitchen_sink', FIXTURES_DIR / KITCHEN)):
        out = tmp_path / case
        assert _run(source, out).returncode == 0
        goldens = {p.name: p.read_bytes() for p in sorted((GOLDEN_DIR / case).glob('*.tf'))}
        generated = {p.name: p.read_bytes() for p in sorted(out.glob('*.tf'))}
        assert generated == goldens, case


# --- 3. the acyclic rule ------------------------------------------------------

def test_the_cycle_fixture_produces_two_edges_and_one_finding(converter_module, tmp_path):
    """AC-3.1: `tests/fixtures/reference_cycle.xml` is the fixture that pins the cycle, and it produces
    no ownership finding because every name in it is unique.
    """
    owners, edge_rows, manifest_rows = _sets(converter_module, FIXTURES_DIR / CYCLE_FIXTURE, tmp_path)
    assert len(edge_rows) == 2 and reference_edges.cycles(edge_rows) == [CYCLE_UNITS]
    findings = reference_edges.findings(edge_rows, manifest_rows)
    assert len(findings) == 1
    finding = findings[0]
    assert _facts(finding) == CYCLE_FACTS
    assert finding['cycle'] == CYCLE_UNITS, 'the cycle is read from its smallest unit'
    assert finding['names'] == (('ethernet1/2',), ('ethernet1/1',))
    assert finding['reason'] == reference_edges.CYCLE_REASON
    assert all(row['owner'] == row['directory'] for row in owners), owners
    assert not ownership.findings(owners), 'no name in the fixture is repeated'
    out = tmp_path / 'run'
    assert _run(FIXTURES_DIR / CYCLE_FIXTURE, out).returncode == 0
    assert {row['referrer'] for row in _record(out)} == {UNIT_A, UNIT_B}


def test_no_corpus_fixture_produces_a_cycle_finding(converter_module, tmp_path):
    """AC-3.2: no false positive. The cycle fixture is the only fixture the corpus produces a cycle from,
    so a fixture that starts producing one must be added here in the same change.
    """
    found = {}
    for path in sorted(FIXTURES_DIR.glob('*.xml')):
        sets = _sets(converter_module, path, tmp_path / path.stem)
        if sets is None:
            continue    # the hostile fixtures are refused before the parse
        _owners, edge_rows, manifest_rows = sets
        findings = reference_edges.findings(edge_rows, manifest_rows)
        if findings:
            found[path.name] = [_facts(finding) for finding in findings]
    assert found == {CYCLE_FIXTURE: [CYCLE_FACTS]}, found


def test_a_self_reference_cannot_be_a_cycle(converter_module, tmp_path):
    """AC-3.4: rule 3 writes no self row, so the smallest cycle is two units.
    """
    gen = converter_module.TerraformGenerator(str(tmp_path / 'gen'))
    own = unit_manifest.directory_name(('', '', '', 'fw-a.example.com'), gen.sanitize_name)
    other = unit_manifest.directory_name(('', '', '', 'fw-b.example.com'), gen.sanitize_name)
    rows = [{'referrer': own, 'target': other, 'type': 'panos_ethernet_interface', 'entry': 'a'},
            {'referrer': other, 'target': own, 'type': 'panos_ethernet_interface', 'entry': 'b'},
            {'referrer': own, 'target': own, 'type': 'panos_ethernet_interface', 'entry': 'self'}]
    assert len(reference_edges.cycles(rows)) == 1
    assert reference_edges.cycles([rows[2]]) == []
    assert reference_edges.graph([rows[0], rows[1]]) == {own: [other], other: [own]}


def test_the_cycle_line_shape_is_fixed(converter_module, tmp_path):
    """AC-3.3: `cycle`, the units in walk order, the names in hop order, the reason. Units are named by
    their directory, the join key, and the line names no path.
    """
    _owners, edge_rows, manifest_rows = _sets(converter_module, FIXTURES_DIR / CYCLE_FIXTURE, tmp_path)
    finding = reference_edges.findings(edge_rows, manifest_rows)[0]
    expected = f'  cycle  {UNIT_A} -> {UNIT_B}  names: ethernet1/2; ethernet1/1  {reference_edges.CYCLE_REASON}'
    assert reference_edges.cycle_line(finding) == expected, reference_edges.cycle_line(finding)
    out = tmp_path / 'out'
    assert _run(FIXTURES_DIR / CYCLE_FIXTURE, out).returncode == 0
    report = (out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8')
    section = _section(report, reference_edges.CYCLE_HEADING)
    assert expected in section, section
    # Grouped by the same F3.9 rule the other finding sections use, through the manifest row.
    generator = converter_module.TerraformGenerator(str(out))
    assert generator._report_section_header(generator._report_scope_path(finding)) in section, section
    assert str(FIXTURES_DIR) not in section, section


def test_a_cycle_does_not_change_the_exit_code_and_the_console_prints_no_line(converter_module, tmp_path):
    """AC-3.3 and AC-5.3: a cycle is an operator action, not a broken output, so the F4.1 gate still
    decides the exit code, and the console prints no cycle line.
    """
    out = tmp_path / 'out'
    code = run_main(converter_module, [str(FIXTURES_DIR / CYCLE_FIXTURE), '--output-dir', str(out)])
    assert code == 0, 'a cycle is an operator action, not a broken output'
    console = run_script(CONVERTER, str(FIXTURES_DIR / CYCLE_FIXTURE), '--output-dir',
                         str(tmp_path / 'run')).stdout
    for text in (reference_edges.CYCLE_HEADING, reference_edges.CYCLE_REASON, UNIT_A, UNIT_B):
        assert text not in console, console
    assert not hasattr(reference_edges, 'console_line'), 'the edge scan owns no console wording'
    assert reference_edges.CYCLE_HEADING in (out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8')
    assert sanity_checks.run_checks(out).fail_count == 0


def test_a_unit_in_a_cycle_states_no_rank(converter_module, tmp_path):
    """AC-3.4 and AC-4.5: a unit in a cycle cannot be ordered, so it states 0, and the cycle section
    names it.
    """
    out = tmp_path / 'out'
    assert _run(FIXTURES_DIR / CYCLE_FIXTURE, out).returncode == 0
    rows = _manifest(out)
    assert all(row['rank'] == reference_edges.NO_RANK for row in rows), rows
    assert {row['directory'] for row in rows} == {UNIT_A, UNIT_B}
    section = _section((out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8'),
                       reference_edges.CYCLE_HEADING)
    assert UNIT_A in section and UNIT_B in section, section


# --- 4. the unit order --------------------------------------------------------

def test_the_parent_unit_comes_before_the_unit_that_overrides_its_name(converter_module, tmp_path):
    """AC-4.1: `ownership.py` rule 4, read through the ownership row.
    """
    _owners, _edges, rows = _sets(converter_module, FIXTURES_DIR / OVERRIDE, tmp_path)
    child = _row(rows, 'branch_dg_ddec9c8a')
    parent = _row(rows, 'shared_be5be69f')
    assert child['after'] == [parent['directory']], child
    assert child['rank'] > parent['rank'], child


def test_the_shallower_scope_comes_before_the_deeper_scope_inside_it(converter_module, tmp_path):
    """AC-4.2: the F3.9 level order, device group, then template, then device. A container the manifest
    does not name adds no dependency.
    """
    _owners, _edges, rows = _sets(converter_module, FIXTURES_DIR / MULTI, tmp_path)
    shared = _row(rows, 'shared_be5be69f')
    template = _row(rows, 'dc_networks_ad53ac42')
    device = _row(rows, 'fw_2_example_com_114d91b6')
    assert reference_edges.LEVEL_KEYS == ('device_group', 'template', 'vsys_device')
    assert shared['after'] == []
    assert template['after'] == [shared['directory']]
    # `after` is sorted, so it reads as the chain from the outermost scope in.
    assert device['after'] == sorted([shared['directory'], template['directory']])
    assert shared['rank'] < template['rank'] < device['rank'], (shared, template, device)


def test_the_edge_target_comes_before_the_referrer(converter_module, tmp_path):
    """AC-4.3: the order rule reads the edge, so the unit that owns the name comes before the unit that
    uses it.
    """
    _owners, edges, rows = _sets(converter_module, FIXTURES_DIR / KITCHEN, tmp_path)
    assert edges
    for row in edges:
        referrer = _row(rows, row['referrer'])
        target = _row(rows, row['target'])
        assert row['target'] in referrer['after'], referrer
        assert referrer['rank'] > target['rank'], (referrer, target)


def test_after_never_names_the_unit_itself(converter_module, tmp_path):
    """AC-4.3 and AC-4.4: the same rule that excludes a self edge keeps a unit out of its own `after`,
    and `after` is sorted.
    """
    for path in sorted(FIXTURES_DIR.glob('*.xml')):
        sets = _sets(converter_module, path, tmp_path / path.stem)
        if sets is None:
            continue    # the hostile fixtures are refused before the parse
        _owners, _edges, rows = sets
        for row in rows:
            assert row['directory'] not in row['after'], (path.name, row)
            assert row['after'] == sorted(row['after']), row


def test_rank_is_a_total_order_that_respects_every_dependency(converter_module, tmp_path):
    """AC-4.5: `rank` is a position from 1, so for an acyclic graph every unit has a rank, each unit
    comes after everything in its `after`, and a unit with no dependency states an empty list.
    """
    for path in sorted(FIXTURES_DIR.glob('*.xml')):
        sets = _sets(converter_module, path, tmp_path / path.stem)
        if sets is None:
            continue    # the hostile fixtures are refused before the parse
        _owners, edges, rows = sets
        if not rows or reference_edges.cycles(edges):
            continue    # the cycle fixture is pinned by AC-3.4
        ranks = {row['directory']: row['rank'] for row in rows}
        assert sorted(ranks.values()) == list(range(1, len(rows) + 1)), (path.name, ranks)
        for row in rows:
            for unit in row['after']:
                assert ranks[row['directory']] > ranks[unit], (path.name, row)
        unranked = [row for row in rows if not row['after']]
        assert unranked, 'a unit with no dependency states an empty list'
        assert all(row['rank'] > 0 for row in unranked)


def test_ties_follow_the_identity_order(converter_module, tmp_path):
    """AC-4.5: the units with no dependency are ranked in the identity order, which is the order the
    manifest rows print, so `rank` does not depend on document order.
    """
    _owners, edges, rows = _sets(converter_module, FIXTURES_DIR / KITCHEN, tmp_path)
    assert not reference_edges.cycles(edges)
    first = [row for row in rows if not row['after']]
    assert first == sorted(first, key=lambda row: _facts(row))
    assert [row['rank'] for row in first] == sorted(row['rank'] for row in first), first
    assert first[0]['unit'] == unit_manifest.SHARED_UNIT and first[0]['rank'] == 1, first


def test_a_declared_parent_source_adds_no_dependency(converter_module, tmp_path):
    """AC-4.6: a unit exists when the run's ledger has a row in it, so the order graph reads only units
    the manifest names, and a parent source names no such unit.
    """
    gen = converter_module.TerraformGenerator(str(tmp_path / 'gen'))
    parent = unit_manifest.directory_name(('Parent-DG', '', '', ''), gen.sanitize_name)
    child_facts = ('Child-DG', '', '', '')
    child = unit_manifest.directory_name(child_facts, gen.sanitize_name)
    rows = [dict(dict.fromkeys(unit_manifest.FIELD_ORDER, ''), device_group='Child-DG',
                 directory=child, entry_count=1, references=[])]
    filled = reference_edges.order(rows, [{'type': 'panos_address', 'entry': 'web',
                                           'directory': parent, 'owner': parent}], [])
    assert parent not in {row['directory'] for row in filled}, 'the parent source names no unit'
    assert filled[0]['after'] == [] and filled[0]['rank'] == 1, filled
    # An edge row can name a parent-source directory, and the order row states nothing about it.
    filled = reference_edges.order(rows, [], [{'referrer': child, 'target': parent,
                                               'type': 'panos_address', 'entry': 'web'}])
    assert filled[0]['after'] == [], filled


# --- 5. the report section, the console, and the exit code -------------------

def test_the_section_prints_after_the_repeated_names_section_and_before_the_state_sections(
        converter_module, tmp_path):
    """AC-5.1: header, summary, gaps, property findings, shadows, repeated names, reference cycles,
    state ownership, drift, then the entry lines. No single fixture produces all of them, so the report
    writer is fed the results, each measured from its own run.
    """
    state_run = run_pipeline(converter_module, KITCHEN, tmp_path / 'state',
                             ('--state', str(FIXTURES_DIR / STATE_FIXTURE), '--workspace', WORKSPACE))
    names = ownership.findings(ownership.build_rows(
        run_pipeline(converter_module, OVERRIDE, tmp_path / 'names').ledger, None,
        converter_module.TerraformGenerator(str(tmp_path / 'names')).sanitize_name))
    _owners, edge_rows, manifest_rows = _sets(converter_module, FIXTURES_DIR / CYCLE_FIXTURE, tmp_path)
    cycles = reference_edges.findings(edge_rows, manifest_rows)
    assert len(names) >= 1 and len(cycles) >= 1, (names, cycles)
    report = converter_module.TerraformGenerator(str(tmp_path / 'out')).generate_conversion_report(
        state_run.ledger, None, state_coverage.state_findings(
            state_run.ledger, state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)),
        names, cycles)
    places = [report.index(f'{container_coverage.SOURCE_LABEL} '), report.index('Per-entry report:'),
              report.index(entry_coverage.GAP_HEADING), report.index(entry_coverage.PROPERTY_HEADING),
              report.index(ownership.FINDING_HEADING), report.index(reference_edges.CYCLE_HEADING),
              report.index(state_coverage.OWNERSHIP_HEADING), report.index(state_coverage.DRIFT_HEADING),
              report.index('Entry lines are grouped by')]
    assert places == sorted(places), report
    assert state_coverage.DRIFT_HEADING in report, 'the state sections print for this run'


def test_the_section_prints_only_when_it_has_a_finding(tmp_path):
    """AC-5.1: a run that records reference names but produces no cycle prints no section, so the report
    bytes of a plain run are unchanged.
    """
    out = tmp_path / 'finding'
    assert _run(FIXTURES_DIR / CYCLE_FIXTURE, out).returncode == 0
    assert reference_edges.CYCLE_HEADING in (out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8')
    for fixture in (GROUPING, SAMPLE_CONFIG.name):
        # One directory per fixture: the gate reads the files that are there, so two runs that shared a
        # directory would read the first run's `.tf` files as part of the second run's output.
        source = FIXTURES_DIR / fixture if fixture != SAMPLE_CONFIG.name else SAMPLE_CONFIG
        out = tmp_path / fixture
        assert _run(source, out).returncode == 0
        report = (out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8')
        assert reference_edges.CYCLE_HEADING not in report, fixture
        assert reference_edges.CYCLE_RULE not in report, fixture


def test_no_report_names_the_record_or_a_field_it_states(tmp_path):
    """AC-5.2: the record is a data file, not a report body, so no report names it or restates a row, and
    the cycle line names units by their directory instead of by a field name.
    """
    assert _run(FIXTURES_DIR / CYCLE_FIXTURE, tmp_path).returncode == 0
    for name in (entry_coverage.REPORT_FILE, 'MANUAL_SETUP_REPORT.txt',
                 'INTERFACE_MIGRATION_REPORT.txt', 'SANITY_REPORT.txt', 'SOURCE.txt', 'README.md'):
        path = tmp_path / name
        if not path.is_file():
            continue    # a report is written only when it has content
        text = path.read_text(encoding='utf-8')
        assert RECORD not in text, name
        # Only the field names a report could not otherwise say, so the pin does not read prose.
        for field in ('referrer', 'rank'):
            assert field not in text, (name, field)
    lines = [line for line in (tmp_path / entry_coverage.REPORT_FILE).read_text(encoding='utf-8').splitlines()
             if line.startswith('  cycle  ')]
    assert lines and UNIT_A in lines[0] and UNIT_B in lines[0], lines


def test_the_exit_codes_are_unchanged_and_a_refusal_writes_no_record(tmp_path):
    """AC-5.4: 0 when the gate reports no FAIL finding, 1 for an input refusal, 2 for an argument error,
    and a refusal writes no record.
    """
    assert _run(SAMPLE_CONFIG, tmp_path / 'run').returncode == 0
    assert _run(FIXTURES_DIR / CYCLE_FIXTURE, tmp_path / 'cycle').returncode == 0
    assert _run(tmp_path / 'missing.xml', tmp_path / 'refused').returncode == 1
    assert not (tmp_path / 'refused' / RECORD).is_file(), 'a refusal writes no record'
    assert run_script(CONVERTER, str(SAMPLE_CONFIG), '--offline').returncode == 2
    assert run_script(CONVERTER, str(SAMPLE_CONFIG), '--data-blocks', 'panos_made_up').returncode == 2


# --- 6. the gates, determinism, and the content rule --------------------------

def test_two_runs_write_the_same_bytes(tmp_path):
    """AC-6.1: the rows sort by the four fields in field order, so two runs on the same bytes write the
    same bytes, for the record, the manifest, and the reports.
    """
    first, second = tmp_path / 'run1', tmp_path / 'run2'
    assert _run(FIXTURES_DIR / CYCLE_FIXTURE, first).returncode == 0
    assert _run(FIXTURES_DIR / CYCLE_FIXTURE, second).returncode == 0
    assert (first / RECORD).read_bytes() == (second / RECORD).read_bytes()
    assert (first / MANIFEST).read_bytes() == (second / MANIFEST).read_bytes()
    for name in (entry_coverage.REPORT_FILE, 'SANITY_REPORT.txt', 'SOURCE.txt'):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_the_record_names_no_path_and_no_timestamp(tmp_path):
    """AC-6.1: two runs on the same bytes from different output directories write the same bytes, so no
    field states where the run wrote them or when.
    """
    first, second = tmp_path / 'a' / 'out', tmp_path / 'b' / 'out'
    assert _run(FIXTURES_DIR / CYCLE_FIXTURE, first).returncode == 0
    assert _run(FIXTURES_DIR / CYCLE_FIXTURE, second).returncode == 0
    assert (first / RECORD).read_bytes() == (second / RECORD).read_bytes()
    text = (first / RECORD).read_text(encoding='utf-8')
    assert str(tmp_path) not in text
    assert 'timestamp' not in text


def test_the_gate_reads_no_data_file_and_check_order_is_unchanged(tmp_path):
    """AC-6.2: the gate reads `.tf` files only, so the record is not a gate input.
    """
    assert _run(FIXTURES_DIR / CYCLE_FIXTURE, tmp_path).returncode == 0
    files = sanity_checks.read_tf_files(tmp_path)
    assert files and all(not name.endswith('.json') for name in files)
    report = sanity_checks.run_checks(tmp_path)
    assert [result.check for result in report.checks] == list(sanity_checks.CHECK_ORDER)
    assert report.file_count == len(files)
    assert report.fail_count == 0
    assert not hasattr(reference_edges, 'check'), 'the edge record owns no gate check'


def test_the_record_is_written_only_when_it_has_content(tmp_path):
    """AC-6.3: a run that writes no edge writes no record; a run that writes edges writes it without a
    flag, and the manifest is still written when it has rows.
    """
    out = tmp_path / 'no_edges'
    assert _run(SAMPLE_CONFIG, out).returncode == 0
    assert not (out / RECORD).is_file()
    assert (out / MANIFEST).is_file()
    out = tmp_path / 'edges'
    assert _run(FIXTURES_DIR / CYCLE_FIXTURE, out).returncode == 0
    assert (out / RECORD).is_file() and _record(out)
    empty = tmp_path / 'empty.xml'
    empty.write_text('<?xml version="1.0"?>\n<config>\n<device-group/>\n</config>\n', encoding='utf-8')
    out = tmp_path / 'empty'
    assert _run(empty, out).returncode == 0
    assert not (out / RECORD).is_file()
    assert not (out / MANIFEST).is_file()
    assert (out / 'SOURCE.txt').is_file()


def test_the_cli_takes_no_flag_for_the_record(tmp_path):
    """AC-6.4: the tool writes data an orchestrator reads, so the record is not opt-in and `--help`
    is unchanged.
    """
    help_text = run_script(CONVERTER, '--help').stdout
    flags = [line.split()[0] for line in help_text.splitlines() if line.strip().startswith('--')]
    assert not [flag for flag in flags if 'edge' in flag or 'reference' in flag], flags
    assert _run(FIXTURES_DIR / CYCLE_FIXTURE, tmp_path).returncode == 0
    assert (tmp_path / RECORD).is_file()
    assert not hasattr(reference_edges, 'add_arguments'), 'the record owns no CLI flag'
