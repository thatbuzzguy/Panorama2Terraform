"""F6.2 ownership as data: one row per entry a coverage matrix row covers.

Seven groups, one per rule in `ownership.py` and `acceptance.md`:

1. The row scope. The F4.4 rule read through the report row, so the scan adds no second
   scope rule: a property level, a skipped entry, and a name a unit only uses write no row.
2. The declaring unit, and the join to `CODEBASE_MANIFEST.json` on `directory`.
3. The owner rule. The ancestor entry owns the name, the export states the relation in two
   cases only, and the rule can say four things about an entry.
4. The service leg F6.2 closes: the parse captures the flag, the emitter prints it, and the
   `panos_service` row names it.
5. The record shape: the declared fields, the declared order, and the refusal rule.
6. Determinism, and the rule that a data file is written only when it has content.
7. The report section, the console, and the exit codes.

Every test runs in process or seeds the cache, so no test opens a connection.
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
import sanity_checks
import shadow_coverage
import state_coverage
import state_input
import unit_manifest
import xml_input
from conftest import FIXTURES_DIR, GOLDEN_DIR, SAMPLE_CONFIG, run_main, run_pipeline, run_script

CONVERTER = 'panorama_to_terraform.py'
RECORD = ownership.OWNERSHIP_FILE

# The fixture that pins the owner rule: one shared entry and one device-group entry that carry
# the same name, so the export states the relation between them.
FIXTURE = 'ownership_override.xml'
GROUPING = 'report_grouping.xml'
POINTERS = 'address_objects_dg_override.xml'
VSYS = 'edge_dup_names_across_vsys.xml'
STATE_FIXTURE = 'state_workspace.json'
WORKSPACE = 'production'

# The two units the fixture declares, and the three names the rule decides differently.
SHARED = ('', '', '', '')
BRANCH = ('Branch-DG', '', '', 'localhost.localdomain')
FLAGGED = 'App-Server'       # the flag is on the ancestor: the repeat is a contradiction
DECIDED = 'Printer-Pool'     # no flag: the rule names the owner
REVERSED = 'Desk-Phone'      # the flag is on a descendant: the rule names no owner
SERVICE = 'app-https'

# The two-source fixtures the F5.4 rule reads, and the offline pair the run builds from them.
PARENT_FIXTURE = 'scope_parent.xml'
CHILD_FIXTURE = 'scope_child.xml'
HOST = 'panorama.test'
PARENT_PATH = 'shared'
CHILD_PATH = 'device-group/entry/Production-DG'

# The whole set of findings the corpus produces, measured through the run: fixture ->
# (declaring unit, entry, reason). A fixture that produces a finding must be listed here, so a
# fixture cannot become a false positive.
CORPUS_FINDINGS = {
    'edge_dup_names_across_dgs.xml': [
        ('DG-A', 'web', ownership.NO_RELATION),
        ('DG-B', 'web', ownership.NO_RELATION),
    ],
    'ownership_override.xml': [
        ('', 'Desk-Phone', ownership.FLAG_NOT_ANCESTOR),
        ('Branch-DG', 'App-Server', ownership.FLAG_FORBIDS_OVERRIDE),
        ('Branch-DG', 'Desk-Phone', ownership.FLAG_NOT_ANCESTOR),
        ('Branch-DG', 'app-https', ownership.FLAG_FORBIDS_OVERRIDE),
    ],
    'report_grouping.xml': [
        ('Datacenter-FW', 'GW-Common', ownership.NO_RELATION),
        ('Datacenter-FW', 'TUN-Common', ownership.NO_RELATION),
        ('Datacenter-FW', 'ethernet1/1', ownership.NO_RELATION),
        ('Office-FW', 'GW-Common', ownership.NO_RELATION),
        ('Office-FW', 'TUN-Common', ownership.NO_RELATION),
        ('Office-FW', 'ethernet1/1', ownership.NO_RELATION),
    ],
}


def _run(source: Path, out_dir: Path, extra: tuple = ()) -> subprocess.CompletedProcess:
    """Run the converter as a script and return the process result."""
    return run_script(CONVERTER, str(source), '--output-dir', str(out_dir), *extra)


def _pipeline(module, source: Path, out_dir: Path, extra: tuple = ()) -> tuple:
    """Run the pipeline in process and return (parser, generator, exit code).

    The scan must read the read record the parse left, and the directory name is the generator's
    rule, so a test that wants both needs both objects. `conftest.run_pipeline` returns the
    parser, so this hooks the generator the same way.
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
    return caught.get('parser'), caught.get('generator'), code


def _scan(module, source: Path, out_dir: Path, extra: tuple = ()) -> list:
    """The scan result for a run: the rows with the facts the finding line reads."""
    parser, generator, _code = _pipeline(module, source, out_dir, extra)
    return ownership.build_rows(parser.ledger, None, generator.sanitize_name)


def _record(out_dir: Path) -> list:
    """A written record, read back as data."""
    return ownership.parse_rows((out_dir / RECORD).read_text(encoding='utf-8'))


def _row(rows: list, name: str, facts: tuple) -> dict:
    """The row for one entry in one unit."""
    return next(row for row in rows if row['entry'] == name and _facts(row) == facts)


def _facts(row: dict) -> tuple:
    """The declaring unit a row states, in `FACT_KEYS` order."""
    return tuple(row[key] for key in ownership.FACT_KEYS)


def _bytes(fixture_name: str) -> bytes:
    return (FIXTURES_DIR / fixture_name).read_bytes()


def _seed_cache(fetch_module, cache, paths):
    """The cache entries the offline run reads, so no test calls the network."""
    cache.mkdir(parents=True, exist_ok=True)
    for path in paths:
        request = fetch_module.ApiRequest(host=HOST, path=path)
        fixture = CHILD_FIXTURE if path == CHILD_PATH else PARENT_FIXTURE
        (cache / request.cache_name()).write_bytes(_bytes(fixture))
    return cache


def _producer(fetch_module):
    """The fixture-backed producer, chosen by the request path."""
    return lambda request, key, insecure=False: _bytes(
        CHILD_FIXTURE if request.path == CHILD_PATH else PARENT_FIXTURE)


def _parent_ledger(fetch_module, cache):
    """The parent ledger, read from the cache the run wrote, through the same rule."""
    request = fetch_module.ApiRequest(host=HOST, path=PARENT_PATH)
    return entry_coverage.EntryLedger(fetch_module.fetch(request, cache, offline=True))


def _state_args(extra: tuple = ()) -> tuple:
    return ('--state', str(FIXTURES_DIR / STATE_FIXTURE), '--workspace', WORKSPACE, *extra)


# --- 1. the row scope ---------------------------------------------------------

def test_one_row_per_entry_the_matrix_row_covers(converter_module, tmp_path):
    """AC-1.1: one row per entry the coverage matrix covers, so two rows can name the same unit.
    `unit_manifest.py` rule 4 pins the per-unit shape, and the two data files join on `directory`.
    """
    out = tmp_path / 'out'
    parser, _generator, code = _pipeline(converter_module, FIXTURES_DIR / FIXTURE, out)
    assert code == 0
    rows = _record(out)
    emitted = [row for row in parser.ledger.rows() if row['destination'] == 'emitted']
    assert len(rows) == len(emitted) == 8
    measured = {(row['name'], unit_manifest.facts_of(row)) for row in emitted}
    assert {(row['entry'], _facts(row)) for row in rows} == measured
    for name in (FLAGGED, DECIDED, REVERSED, SERVICE):
        assert sum(row['entry'] == name for row in rows) == 2, name


def test_an_entry_inside_a_config_object_entry_writes_no_row(converter_module, tmp_path):
    """AC-1.1: a property level is covered by the parent row's count, so the scan writes no row for
    it. `tests/test_unit_manifest.py` pins the count on the parent row.
    """
    out = tmp_path / 'out'
    parser, _generator, _code = _pipeline(converter_module, FIXTURES_DIR / GROUPING, out)
    parent = next(row for row in parser.ledger.rows() if row['property_entries'] == 1)
    assert unit_manifest.facts_of(parent) == ('Office-FW', '', '', '')
    assert '10.1.1.1/24' not in [row['entry'] for row in _record(out)], 'the ip entry is a property level'


def test_a_reference_pointer_writes_no_row(converter_module, tmp_path):
    """AC-1.2: the export declared no object for an entry that carries only `<id>`, so the scan has
    nothing to own there.
    """
    out = tmp_path / 'out'
    parser, _generator, _code = _pipeline(converter_module, FIXTURES_DIR / POINTERS, out)
    assert [row for row in parser.ledger.rows() if row['destination'] == 'skipped']
    rows = _record(out)
    assert len(rows) == 1
    assert rows[0]['entry'] == 'Web-Server-1' and rows[0]['kind'] == 'declared'


def test_a_name_a_unit_uses_but_does_not_declare_writes_no_row(converter_module, tmp_path):
    """AC-1.2 (Decision 2 rule 2): a member list and a reference string hold a name without
    declaring an object, so the reference rule stays the only place that names a use.
    """
    out = tmp_path / 'out'
    _parser, generator, _code = _pipeline(converter_module, FIXTURES_DIR / GROUPING, out)
    recorded = {name for names in generator.unit_references().values() for name in names}
    assert 'IKE-DEFAULT' in recorded
    assert 'IKE-DEFAULT' not in [row['entry'] for row in _record(out)], 'the manifest names the use, not an entry'


def test_the_scan_read_is_not_an_output_read(converter_module, xml_input_module):
    """AC-1.4: the scan reads a captured value through `RecordingDict.value`, so it cannot move a
    property finding (the F5.6 rule, reused). A read through `get` would.
    """
    parser = converter_module.PanoramaParser(xml_input.parse_xml(FIXTURES_DIR / FIXTURE))
    entry = next(e for e in parser.root.iter() if e.tag == 'entry' and e.get('name') == DECIDED)
    captured = parser.mark(entry, {'type': 'address', 'value': '10.40.0.21/32',
                                   'disable_override': 'yes'})
    parser.ledger.start_recording()
    row = entry_coverage.MATRIX_BY_RESOURCE['panos_address']
    assert ownership.override_value(row, captured) == 'yes'
    assert captured.used_keys() == (), 'the scan read must not count as a property the output used'
    captured.get('disable_override')
    assert captured.used_keys() == ('disable_override',)


# --- 2. the declaring unit and the join -------------------------------------

def test_a_row_names_the_unit_the_export_declares_the_entry_inside(converter_module, tmp_path):
    """AC-2.1 (`docs/CODEBASE_ASSEMBLY.md` §4 rule 1): the row names its unit through the manifest's
    naming rule, not a second one, so the two data files join on `directory`.
    """
    out = tmp_path / 'out'
    _parser, generator, _code = _pipeline(converter_module, FIXTURES_DIR / FIXTURE, out)
    manifest = unit_manifest.parse_rows((out / unit_manifest.MANIFEST_FILE).read_text(encoding='utf-8'))
    rows = _record(out)
    for row in rows:
        assert row['directory'] == unit_manifest.directory_name(_facts(row), generator.sanitize_name)
        assert row['directory'] in [entry['directory'] for entry in manifest], row
    assert {_facts(row) for row in rows} == {SHARED, BRANCH}


def test_every_row_belongs_to_a_unit_the_manifest_shows(converter_module, tmp_path):
    """AC-2.2: pinned across the fixture corpus, so a row cannot name a unit the run did not read."""
    for fixture in sorted(FIXTURES_DIR.glob('*.xml')):
        if fixture.name.startswith('hostile_'):
            continue
        out = tmp_path / fixture.stem
        parser, generator, _code = _pipeline(converter_module, fixture, out)
        if parser is None:
            continue    # the hostile fixtures are refused before the parse
        units = {unit_manifest.facts_of(row) for row in parser.ledger.rows()}
        for row in ownership.build_rows(parser.ledger, None, generator.sanitize_name):
            assert _facts(row) in units, (fixture.name, row)


def test_a_sole_entry_is_declared_and_owns_its_name(converter_module, tmp_path):
    """AC-2.3: a group with one entry has no ancestor to name, so its own unit owns it."""
    rows = _scan(converter_module, FIXTURES_DIR / POINTERS, tmp_path / 'out')
    assert rows[0]['kind'] == 'declared' and rows[0]['owner'] == rows[0]['directory']


# --- 3. the owner rule --------------------------------------------------------

def test_the_ancestor_entry_owns_the_name(converter_module, tmp_path):
    """AC-3.3: the shared entry is the ancestor the export states, so its unit owns the name and the
    device-group entry resolves as a reference to it.
    """
    rows = _scan(converter_module, FIXTURES_DIR / FIXTURE, tmp_path / 'out')
    ancestor = _row(rows, DECIDED, SHARED)
    descendant = _row(rows, DECIDED, BRANCH)
    assert ancestor['kind'] == 'definition' and ancestor['owner'] == ancestor['directory']
    assert descendant['kind'] == 'override' and descendant['owner'] == ancestor['directory']
    assert not descendant['reason'], 'the rule names the owner, so this name is not a finding'


def test_two_device_groups_have_no_stated_relation(converter_module, tmp_path):
    """AC-3.1: the device-group `parent` field is not captured, so the rule names no owner for two
    device groups in one source.
    """
    rows = _scan(converter_module, FIXTURES_DIR / 'edge_dup_names_across_dgs.xml', tmp_path / 'out')
    assert [row['kind'] for row in rows] == ['ambiguous', 'ambiguous']
    assert all(row['owner'] == '' for row in rows), rows
    assert all(row['reason'] == ownership.NO_RELATION for row in rows), rows


def test_a_name_in_two_units_that_cannot_be_one_chain_is_two_objects(converter_module, tmp_path):
    """AC-3.2 (`ARCHITECTURE.md` §2.1): a name in two virtual systems is a different object in each
    unit, so each unit owns its own entry and no decision is needed.
    """
    rows = _scan(converter_module, FIXTURES_DIR / VSYS, tmp_path / 'out')
    group = [row for row in rows if row['entry'] == 'web']
    assert len(group) == 2, group
    assert [row['kind'] for row in group] == ['declared', 'declared']
    assert all(row['owner'] == row['directory'] for row in group), group
    assert not ownership.findings(rows), 'two objects are not an operator decision'


def test_the_declared_parent_source_is_the_ancestor(converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-3.4: the F5.4 rule states the relation, so the parent entry owns the name and the run entry
    resolves as a reference to it. The run reads the parent source as entry names, not as objects, so
    the flag on a parent row is `unknown`.
    """
    out = tmp_path / 'out'
    cache = _seed_cache(fetch_module, tmp_path / 'cache', (CHILD_PATH, PARENT_PATH))
    monkeypatch.setenv(fetch_module.API_KEY_ENV, 'test-key')
    monkeypatch.setattr(fetch_module, 'network_producer', _producer(fetch_module))
    parser = run_pipeline(converter_module, None, out, ('--source', 'api', '--host', HOST,
                                                        '--cache-dir', str(cache), '--path', f'/{CHILD_PATH}',
                                                        '--parent', f'/{PARENT_PATH}', '--offline'))
    rows = ownership.build_rows(parser.ledger, _parent_ledger(fetch_module, cache),
                                converter_module.TerraformGenerator(str(out)).sanitize_name)
    parent = [row for row in rows if row['source'] != parser.source.name]
    child = [row for row in rows if row['source'] == parser.source.name]
    assert len(parent) == 1 and len(child) == 1, rows
    assert parent[0]['kind'] == 'definition' and parent[0]['override'] == 'unknown'
    assert child[0]['kind'] == 'override' and child[0]['owner'] == parent[0]['directory']
    assert not ownership.findings(rows), 'the export states this relation, so it is not a finding'


def test_the_flag_on_the_definition_makes_the_repeat_a_finding(converter_module, tmp_path):
    """AC-3.5: `disable_override` names the entry no descendant may override, so the ancestor keeps
    the name and the repeated entry cannot be an override.
    """
    rows = _scan(converter_module, FIXTURES_DIR / FIXTURE, tmp_path / 'out')
    definition = _row(rows, FLAGGED, SHARED)
    repeat = _row(rows, FLAGGED, BRANCH)
    assert definition['kind'] == 'definition' and definition['override'] == 'yes'
    assert repeat['kind'] == 'override' and repeat['owner'] == definition['directory']
    assert repeat['reason'] == ownership.FLAG_FORBIDS_OVERRIDE


def test_the_flag_on_a_descendant_names_no_owner(converter_module, tmp_path):
    """AC-3.5: the flag cannot make a descendant the ancestor, so the group is undecided."""
    rows = _scan(converter_module, FIXTURES_DIR / FIXTURE, tmp_path / 'out')
    for facts in (SHARED, BRANCH):
        row = _row(rows, REVERSED, facts)
        assert row['kind'] == 'ambiguous' and row['owner'] == ''
        assert row['reason'] == ownership.FLAG_NOT_ANCESTOR


def test_the_flag_is_read_as_the_parse_read_it(converter_module, tmp_path):
    """AC-3.6: `no` is the cleared default for a row that declares the property and carries no value,
    and `unknown` is a matrix row that does not declare it.
    """
    rows = _scan(converter_module, FIXTURES_DIR / FIXTURE, tmp_path / 'out')
    assert _row(rows, DECIDED, BRANCH)['override'] == 'no'
    gateways = [row for row in _scan(converter_module, FIXTURES_DIR / GROUPING, tmp_path / 'gate')
                if row['type'] == 'panos_ike_gateway']
    assert gateways and all(row['override'] == 'unknown' for row in gateways), gateways


# --- 4. the service leg -------------------------------------------------------

def test_the_service_parse_keeps_the_flag(converter_module, make_parser):
    """AC-4.1: `parse_service_objects` captures `disable-override` as the parse key, the way the
    address parser does (F3.4), so the ownership rule can read the flag for a service entry.
    """
    services = make_parser(FIXTURE).parse_service_objects()
    entry = next(s for s in services if s['name'] == SERVICE)
    assert entry['disable_override'] == 'yes'


def test_the_emitter_prints_the_flag_as_a_string(converter_module, tmp_path):
    """AC-4.2: the emitted line is the shape `panos_address` writes, the string after `description`,
    not a bool (verified against provider 2.0.14). An entry that carries no value prints nothing.
    """
    out = tmp_path / 'out'
    _pipeline(converter_module, FIXTURES_DIR / FIXTURE, out)
    parts = (out / 'service_objects.tf').read_text(encoding='utf-8').split('resource "panos_service"')
    assert len(parts) == 3, parts
    shared, branch = parts[1], parts[2]
    assert shared.index('  description = "https service"') < shared.index('  disable_override = "yes"'), shared
    assert 'disable_override' not in branch, 'the entry with no value prints no line'


def test_the_service_row_names_the_property_the_emitter_reads(converter_module, tmp_path):
    """AC-4.3: the `panos_service` row declares `disable_override`, and the emitter reads it, so the
    fixture produces no property finding: a captured field is an emitted field.
    """
    out = tmp_path / 'out'
    parser, _generator, _code = _pipeline(converter_module, FIXTURES_DIR / FIXTURE, out)
    assert 'disable_override' in entry_coverage.MATRIX_BY_RESOURCE['panos_service']['properties']
    assert parser.ledger.property_findings() == [], 'a captured field an output reads is not a finding'
    measured = set()
    for entry in parser.ledger.entries():
        mark = parser.ledger.mark_for(entry)
        if mark and isinstance(mark['captured'], entry_coverage.RecordingDict):
            measured.update(mark['captured'].used_keys())
    assert 'disable_override' in measured, measured


def test_the_goldens_are_byte_identical(tmp_path):
    """AC-4.4: no committed golden fixture holds a service entry with the flag, so the emitted line
    appears only for a run that reads one.
    """
    for case, source in (('sample', SAMPLE_CONFIG), ('kitchen_sink', FIXTURES_DIR / 'kitchen_sink.xml')):
        out = tmp_path / case
        proc = _run(source, out)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        goldens = {p.name: p.read_bytes() for p in sorted((GOLDEN_DIR / case).glob('*.tf'))}
        generated = {p.name: p.read_bytes() for p in sorted(out.glob('*.tf'))}
        assert generated == goldens, case


# --- 5. the record shape ------------------------------------------------------

GOOD = {'type': 'panos_address', 'entry': 'App-Server', 'source': 'ownership_override.xml',
        'device_group': '', 'vsys': '', 'template': '', 'vsys_device': '',
        'directory': 'shared_be5be69f', 'owner': 'shared_be5be69f',
        'kind': 'definition', 'override': 'yes'}


def test_the_fields_print_in_the_declared_order(converter_module, tmp_path):
    """Decision 4 rules 2 and 4: the field order is the declared order, not alphabetical, and the row
    order is the identity order, so a reader does not guess.
    """
    out = tmp_path / 'out'
    _pipeline(converter_module, FIXTURES_DIR / FIXTURE, out)
    document = json.loads((out / RECORD).read_text(encoding='utf-8'))
    assert [list(row) for row in document] == [list(ownership.FIELD_ORDER)] * len(document)
    rows = _record(out)
    assert [ownership.row_key(row) for row in rows] == sorted(ownership.row_key(row) for row in rows)


def test_the_record_writes_only_the_declared_fields(converter_module, tmp_path):
    """The scan keeps the facts the finding line reads (`line`, `container`, `reason`) as run facts,
    not as data fields: the record states a fact, the report states a finding.
    """
    out = tmp_path / 'out'
    _pipeline(converter_module, FIXTURES_DIR / FIXTURE, out)
    text = (out / RECORD).read_text(encoding='utf-8')
    for key in ('line', 'container', 'reason', 'from_parent'):
        assert key not in text, key
    for key in ownership.FIELD_ORDER:
        assert key in text, key
    assert text.endswith('\n') and not text.endswith('\n\n'), 'one trailing newline'
    assert text.isascii(), 'ASCII output'
    assert '\n    "type"' in text, 'indent 2'


def test_the_record_names_no_path_and_no_timestamp(converter_module, tmp_path):
    """Decision 4 rule 5: `source` is the report value of the source, never its path (F4.2 rule 6),
    and no field states a timestamp.
    """
    out = tmp_path / 'out'
    _pipeline(converter_module, FIXTURES_DIR / FIXTURE, out)
    rows = _record(out)
    assert all('/' not in row[key] for row in rows for key in ownership.FIELD_ORDER), rows
    assert all(row['source'] == FIXTURE for row in rows), rows
    assert str(FIXTURES_DIR) not in (out / RECORD).read_text(encoding='utf-8')


def test_the_record_reads_back_as_the_rows_it_wrote(converter_module, tmp_path):
    """Decision 4 rule 6: `parse_rows` reads a written record back as data, in the identity order."""
    out = tmp_path / 'out'
    _pipeline(converter_module, FIXTURES_DIR / FIXTURE, out)
    written = json.loads((out / RECORD).read_text(encoding='utf-8'))
    assert _record(out) == sorted([{key: row[key] for key in ownership.FIELD_ORDER} for row in written],
                                  key=ownership.row_key)


def test_parse_rows_refuses_a_row_that_is_not_the_declared_shape():
    """Decision 4 rule 6: the record is data, so a reader cannot fall back to reading prose."""
    bad_rows = (
        json.dumps([dict(GOOD, unit='Shared')]),
        json.dumps([{key: GOOD[key] for key in ownership.FIELD_ORDER if key != 'kind'}]),
        json.dumps([dict(GOOD, kind='owner')]),
        json.dumps([dict(GOOD, override='true')]),
        json.dumps([dict(GOOD, entry=7)]),
        json.dumps([dict(GOOD, reason='the ancestor')]),
        json.dumps({'type': 'panos_address'}),
        json.dumps(['App-Server']),
    )
    for bad in bad_rows:
        with pytest.raises(ValueError):
            ownership.parse_rows(bad)


# --- 6. determinism and the content rule --------------------------------------

def test_two_runs_on_the_same_bytes_write_the_same_bytes(tmp_path):
    """AC-6.2: the rows sort by the identity key, so the record does not depend on document order."""
    first, second = tmp_path / 'run1', tmp_path / 'run2'
    assert _run(FIXTURES_DIR / FIXTURE, first).returncode == 0
    assert _run(FIXTURES_DIR / FIXTURE, second).returncode == 0
    assert {p.name: p.read_bytes() for p in first.iterdir()} == \
           {p.name: p.read_bytes() for p in second.iterdir()}
    assert (first / RECORD).read_bytes() == (second / RECORD).read_bytes()


def test_the_record_is_written_only_when_it_has_content(tmp_path):
    """Decision 1 rule 3 and AC-6.3: a run that read no entry writes no file, and a refusal writes
    none. The manifest rule is the same one, pinned in `tests/test_unit_manifest.py`.
    """
    empty = tmp_path / 'empty.xml'
    empty.write_text('<?xml version="1.0"?>\n<config>\n<device-group/>\n</config>\n', encoding='utf-8')
    out = tmp_path / 'out'
    assert _run(empty, out).returncode == 0
    assert not (out / RECORD).is_file()
    assert (out / 'SOURCE.txt').is_file()
    refused = tmp_path / 'refused'
    assert _run(tmp_path / 'missing.xml', refused).returncode == 1
    assert not (refused / RECORD).is_file()


def test_a_plain_run_writes_the_record_without_a_flag(tmp_path):
    """Decision 1 rule 3: the tool writes data an orchestrator reads, so the CLI takes no flag for it."""
    help_text = run_script(CONVERTER, '--help').stdout
    assert 'OWNERSHIP' not in help_text, help_text
    assert _run(SAMPLE_CONFIG, tmp_path).returncode == 0
    assert (tmp_path / RECORD).is_file() and _record(tmp_path)


def test_the_gate_reads_no_data_file(tmp_path):
    """Decision 1 rule 5: the gate reads `.tf` files only, so a data file cannot change a gate result
    or a golden byte, and `CHECK_ORDER` is unchanged.
    """
    _run(SAMPLE_CONFIG, tmp_path)
    files = sanity_checks.read_tf_files(tmp_path)
    assert files and all(not name.endswith('.json') for name in files)
    report = sanity_checks.run_checks(tmp_path)
    assert [result.check for result in report.checks] == list(sanity_checks.CHECK_ORDER)
    assert report.fail_count == 0


def test_no_report_names_a_field_the_record_states(tmp_path):
    """AC-5.4: the record is a data file, not a report body, so no report names it or restates a row.
    The finding line prints a reason, never a `kind` value.
    """
    _run(FIXTURES_DIR / FIXTURE, tmp_path)
    for name in (entry_coverage.REPORT_FILE, 'MANUAL_SETUP_REPORT.txt',
                 'INTERFACE_MIGRATION_REPORT.txt', 'SANITY_REPORT.txt', 'README.md'):
        path = tmp_path / name
        if not path.is_file():
            continue    # a report is written only when it has content
        text = path.read_text(encoding='utf-8')
        assert RECORD not in text, name
        assert not any(f'{kind} =' in text for kind in ownership.KINDS), name


# --- 7. the report section, the console, and the exit code -------------------

def _section(report: str, heading: str) -> str:
    """One report section: from its heading to the next heading, or to the entry-line footer."""
    start = report.index(heading)
    rest = report[start + len(heading):]
    end = rest.index('--- ') if '--- ' in rest else report.index('Entry lines are grouped by')
    return report[start:end]


def test_the_section_prints_only_when_it_has_a_finding(tmp_path):
    """AC-5.1: a run that read a covered entry but decided every name prints no section."""
    out = tmp_path / 'decided'
    assert _run(FIXTURES_DIR / POINTERS, out).returncode == 0
    assert ownership.FINDING_HEADING not in (out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8')
    assert _record(out), 'the record still states the entry the rule decided'
    out = tmp_path / 'finding'
    assert _run(FIXTURES_DIR / FIXTURE, out).returncode == 0
    assert ownership.FINDING_HEADING in (out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8')


def test_the_section_prints_after_the_property_and_shadow_sections_and_before_the_state_sections(
        converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-5.1: header, summary, gaps, property findings, shadows, repeated names, state ownership,
    drift, then the entry lines.

    No single fixture produces all four scan results, so the report writer is fed the four results,
    each measured from its own run. The order pinned here is the writer's order, not the order one
    fixture happens to produce.
    """
    cache = _seed_cache(fetch_module, tmp_path / 'cache', (CHILD_PATH, PARENT_PATH))
    monkeypatch.setenv(fetch_module.API_KEY_ENV, 'test-key')
    monkeypatch.setattr(fetch_module, 'network_producer', _producer(fetch_module))
    pair = run_pipeline(converter_module, None, tmp_path / 'pair',
                        ('--source', 'api', '--host', HOST, '--cache-dir', str(cache),
                         '--path', f'/{CHILD_PATH}', '--parent', f'/{PARENT_PATH}', '--offline'))
    shadows = shadow_coverage.shadow_findings(pair.ledger, _parent_ledger(fetch_module, cache))
    state_run = run_pipeline(converter_module, 'kitchen_sink.xml', tmp_path / 'state', _state_args())
    state = state_coverage.state_findings(state_run.ledger, state_input.read_state(
        FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE))
    findings = ownership.findings(_scan(converter_module, FIXTURES_DIR / GROUPING, tmp_path / 'names'))
    report = converter_module.TerraformGenerator(str(tmp_path / 'out')).generate_conversion_report(
        state_run.ledger, shadows, state, findings)
    places = [report.index(f'{container_coverage.SOURCE_LABEL} '), report.index('Per-entry report:'),
              report.index(entry_coverage.GAP_HEADING), report.index(entry_coverage.PROPERTY_HEADING),
              report.index(shadow_coverage.SHADOW_HEADING), report.index(ownership.FINDING_HEADING),
              report.index(state_coverage.OWNERSHIP_HEADING), report.index(state_coverage.DRIFT_HEADING),
              report.index('Entry lines are grouped by')]
    assert places == sorted(places), report
    assert len(shadows) == 1 and len(state) >= 1, (shadows, state)


def test_the_finding_line_shape_is_fixed(converter_module, tmp_path):
    """AC-5.2: line, object type, entry name, matrix row, the reason; the section names a source by
    its report value, never by its path.
    """
    out = tmp_path / 'out'
    parser, generator, _code = _pipeline(converter_module, FIXTURES_DIR / GROUPING, out)
    findings = ownership.findings(ownership.build_rows(parser.ledger, None, generator.sanitize_name))
    row = next(finding for finding in findings if finding['type'] == 'panos_ike_gateway')
    name = f'{row["container"]}/{row["entry"]}'
    expected = (f'  line {row["line"]:>4}  ' + f'{name:<38} ' + f'{row["type"]:<32} ' + row['reason'])
    assert ownership.finding_line(row) == expected, ownership.finding_line(row)
    section = _section((out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8'),
                       ownership.FINDING_HEADING)
    assert expected in section, section
    assert str(FIXTURES_DIR) not in section, section


def test_the_findings_are_grouped_by_the_f3_9_scope_rule(converter_module, tmp_path):
    """AC-5.1: the same grouping function the other finding sections use, and one line per finding.

    The findings are sorted by the line, so within a scope group the lines print in that order;
    the groups print in the F3.9 group order, which is not the line order.
    """
    out = tmp_path / 'out'
    parser, generator, _code = _pipeline(converter_module, FIXTURES_DIR / FIXTURE, out)
    findings = ownership.findings(ownership.build_rows(parser.ledger, None, generator.sanitize_name))
    assert len(findings) == 4, findings
    groups = generator._group_by_scope(findings)
    flat = [row for _path, group in groups for row in group]
    assert len(flat) == len(findings)
    for row in findings:
        assert sum(row is other for other in flat) == 1, row
    section = _section((out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8'),
                       ownership.FINDING_HEADING)
    printed = [line for line in section.splitlines() if line.startswith('  line ')]
    assert printed == [ownership.finding_line(row) for _path, group in groups for row in group], printed
    for path, group in groups:
        header = generator._report_section_header(path)
        block = section[section.index(header):]
        block_lines = [line for line in block.splitlines() if line.startswith('  line ')]
        assert block_lines[:len(group)] == [ownership.finding_line(row) for row in group], block


def test_a_finding_does_not_change_the_exit_code_and_the_console_prints_no_line(converter_module, tmp_path):
    """AC-5.3: a finding is an operator action, so the F4.1 gate still decides the exit code, and the
    console prints the gap lines only (the rule the property and shadow findings hold).
    """
    out = tmp_path / 'out'
    code = run_main(converter_module, [str(FIXTURES_DIR / FIXTURE), '--output-dir', str(out)])
    assert code == 0, 'a repeated name is an operator action, not a broken output'
    console = run_script(CONVERTER, str(FIXTURES_DIR / FIXTURE), '--output-dir', str(tmp_path / 'run')).stdout
    for text in (ownership.FINDING_HEADING, ownership.NO_RELATION, ownership.FLAG_NOT_ANCESTOR,
                 ownership.FLAG_FORBIDS_OVERRIDE):
        assert text not in console, console
    assert not hasattr(ownership, 'console_line'), 'the ownership scan owns no console wording'
    assert ownership.FINDING_HEADING in (out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8')
    assert sanity_checks.run_checks(out).fail_count == 0


def test_the_exit_codes_are_unchanged(tmp_path):
    """AC-6.3: 0 when the gate reports no FAIL finding, 1 for an input refusal, 2 for an argument error."""
    assert _run(SAMPLE_CONFIG, tmp_path / 'run').returncode == 0
    assert _run(tmp_path / 'missing.xml', tmp_path / 'refused').returncode == 1
    assert run_script(CONVERTER, str(SAMPLE_CONFIG), '--offline').returncode == 2
    assert run_script(CONVERTER, str(SAMPLE_CONFIG), '--data-blocks', 'panos_made_up').returncode == 2


def test_the_corpus_findings_are_the_whole_set(converter_module, tmp_path):
    """AC-3.7: no fixture is a false positive. The pinned set is the measurement, so a fixture that
    starts producing a finding must be added to it in the same change.
    """
    findings = {}
    for path in sorted(FIXTURES_DIR.glob('*.xml')):
        out = tmp_path / path.stem
        parser = run_pipeline(converter_module, path.name, out)
        if parser is None:
            continue    # the hostile fixtures are refused before the parse
        generator = converter_module.TerraformGenerator(str(out))
        found = ownership.findings(ownership.build_rows(parser.ledger, None, generator.sanitize_name))
        if found:
            findings[path.name] = sorted((_facts(row)[0], row['entry'], row['reason']) for row in found)
    assert findings == CORPUS_FINDINGS, findings
