"""F5.4 cross-source shadow report: a child entry name that repeats a parent entry name.

Six groups, one per acceptance rule:

1. The per-scope shape in the scan. `result` is read as the place the declared path
   names, so the entry under it is the declared scope entry, and a per-scope entry takes
   the declared scope as its scope fact instead of the `Shared` fallback.
2. The shadow fact. A child entry whose name repeats a parent entry name within the same
   matrix row is a finding; the matrix row is the key, the scan scope is the F4.4 rule,
   the parent source is read with the same container helpers, and a run with no declared
   parent reports nothing.
3. The ledger names the source of each entry as row data, and the entry line does not
   print it, so the entry-line bytes are unchanged for a one-source run.
4. The shadow section in `CONVERSION_REPORT.txt`: its own section after the property
   section, the fixed line shape, the F3.9 grouping, no console line, no exit-code change.
5. Determinism: two runs on the same two sources write the same bytes. The record rule
   (one record per source read, in read order, and the round trip) is pinned in
   `tests/test_provenance.py`, and the entry-line rule is pinned in
   `tests/test_entry_coverage.py`.
6. The CLI argument rules, and the offline run reading the second cache entry.

Every test runs in process or seeds the cache, so no test opens a connection. The child
entry the shadow names is line 10 of each fixture.
"""

import contextlib
import io
import sys

import container_coverage
import entry_coverage
import provenance
import shadow_coverage
import xml_input
from conftest import FIXTURES_DIR, run_main, run_pipeline, run_script

CHILD_FIXTURE = 'scope_child.xml'
PARENT_FIXTURE = 'scope_parent.xml'
HOST = 'panorama.test'
CHILD_PATH = 'device-group/entry/Production-DG'
PARENT_PATH = 'shared'

# The shared name the two fixtures carry, the name the child scope declares, and the
# matrix row that covers both entries.
SHARED_NAME = 'Web-Server-1'
CHILD_NAME = 'Production-DG'
MATRIX_ROW = 'panos_address'
CHILD_LINE = 10
PARENT_LINE = 10


def _bytes(fixture_name: str) -> bytes:
    return (FIXTURES_DIR / fixture_name).read_bytes()


def _source(fetch_module, path: str, data: bytes, name: str):
    """A per-scope source, read through the door and the wrapper decision."""
    origin = xml_input.SourceOrigin(kind='api', name=name)
    request = fetch_module.ApiRequest(host=HOST, path=path)
    return fetch_module.unwrap_config_root(xml_input.parse_bytes(data, origin), request)


def _shape(path: str, container: str, name: str) -> bytes:
    """One per-scope response: `result` holds the entry the path names, and the entry
    holds one container with one entry of the shared name."""
    return (b'<?xml version="1.0"?>\n<response type="success" code="0">\n<result>\n'
            + f'<entry name="{CHILD_NAME}">'.encode()
            + f'<{container}><entry name="{name}"><value>x</value></entry></{container}>'.encode()
            + b'\n</entry>\n</result>\n</response>\n')


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


def _argv(out_dir, cache, extra: tuple = ()):
    return ['--source', 'api', '--host', HOST, '--cache-dir', str(cache),
            '--path', f'/{CHILD_PATH}', '--parent', f'/{PARENT_PATH}',
            '--output-dir', str(out_dir), *extra]


def _run_pair(converter_module, fetch_module, out_dir, cache, monkeypatch, offline=False):
    """Run the pipeline in process for the child source and the declared parent source.

    Returns the parser the run built, so the test reads the ledger of the run itself.
    """
    monkeypatch.setenv(fetch_module.API_KEY_ENV, 'test-key')
    monkeypatch.setattr(fetch_module, 'network_producer', _producer(fetch_module))
    argv = _argv(out_dir, cache, ('--offline',) if offline else ())
    return run_pipeline(converter_module, None, out_dir, tuple(argv))


def _parent_ledger(fetch_module, cache):
    """The parent ledger, read from the cache the run wrote, through the same rule."""
    request = fetch_module.ApiRequest(host=HOST, path=PARENT_PATH)
    return entry_coverage.EntryLedger(fetch_module.fetch(request, cache, offline=True))


# --- 1. The per-scope shape in the scan -------------------------------------

def test_result_is_read_as_the_place_the_declared_path_names(fetch_module):
    """The wrapper decision keeps the origin and the line map, so a report line still
    names the line the response bytes carry."""
    source = _source(fetch_module, CHILD_PATH, _bytes(CHILD_FIXTURE), CHILD_FIXTURE)
    assert source.scope == CHILD_PATH
    assert source.is_per_scope
    assert source.scope_container == 'device-group'
    assert source.root.tag == 'result'

    parents = container_coverage.parent_map(source.root)
    entry = source.root.find('.//entry')
    # `result` is the place the path names, so the entry under it is read as an entry
    # inside `device-group`, not as an entry inside the envelope.
    assert container_coverage.container_tag(entry, parents, source) == 'device-group'
    assert container_coverage.is_scope_entry(entry, parents, source)
    assert container_coverage.section_path(container_coverage.parent_map(source.root)[entry],
                                           parents, source) == 'device-group'


def test_the_declared_scope_fact_replaces_the_shared_fallback(converter_module, fetch_module):
    """AC-1.4: the parser scope walk reads the same rule, so a per-scope entry names the
    declared group instead of falling back to Shared."""
    source = _source(fetch_module, CHILD_PATH, _bytes(CHILD_FIXTURE), CHILD_FIXTURE)
    parser = converter_module.PanoramaParser(source)
    child = next(e for e in source.root.iter() if e.get('name') == SHARED_NAME)
    assert parser.device_group_of(child) == CHILD_NAME
    assert parser.ledger.scope(child)['device_group'] == CHILD_NAME


# --- 2. The shadow fact -----------------------------------------------------

def test_a_child_name_that_repeats_a_parent_name_is_a_finding(converter_module, fetch_module, tmp_path, monkeypatch):
    """The fact is a run fact, read from the ledger of the run."""
    cache = tmp_path / 'cache'
    parser = _run_pair(converter_module, fetch_module, tmp_path / 'out', cache, monkeypatch)
    parent_ledger = _parent_ledger(fetch_module, cache)
    findings = shadow_coverage.shadow_findings(parser.ledger, parent_ledger)
    assert len(findings) == 1, findings
    finding = findings[0]
    assert finding['name'] == SHARED_NAME
    assert finding['resource'] == MATRIX_ROW
    assert finding['line'] == CHILD_LINE, 'the child line is the line the response bytes carry'
    assert finding['parent_line'] == PARENT_LINE
    assert finding['source'] == parser.source.name
    assert finding['parent_source'] == parent_ledger.source.name


def test_the_matrix_row_is_the_key_not_the_name_alone(fetch_module):
    """The same name under a different matrix row is not a shadow."""
    child = entry_coverage.EntryLedger(
        _source(fetch_module, CHILD_PATH, _shape(CHILD_PATH, 'service-group', SHARED_NAME), 'child'))
    parent = entry_coverage.EntryLedger(_source(fetch_module, PARENT_PATH, _bytes(PARENT_FIXTURE), 'parent'))
    child_row = next(r for r in child.rows() if r['name'] == SHARED_NAME)
    assert entry_coverage.matrix_row_for(child_row['container'])['resource'] == 'panos_service_group', \
        'the child entry is the shared name in another matrix row'
    assert shadow_coverage.shadow_findings(child, parent) == []


def test_the_scan_scope_is_the_f4_4_rule(fetch_module):
    """An entry no matrix row covers is not a finding: a count-only container row has no
    matrix row, so the scan does not read an entry there."""
    child = entry_coverage.EntryLedger(
        _source(fetch_module, CHILD_PATH, _shape(CHILD_PATH, 'region', SHARED_NAME), 'child'))
    parent = entry_coverage.EntryLedger(_source(fetch_module, PARENT_PATH, _bytes(PARENT_FIXTURE), 'parent'))
    row = next(r for r in child.rows() if r['name'] == SHARED_NAME)
    assert row['destination'] == 'count-only', row
    assert entry_coverage.matrix_row_for(row['container']) is None, row
    assert shadow_coverage.shadow_findings(child, parent) == []


def test_the_parent_is_read_with_the_same_row_rule(fetch_module):
    """No second naming rule: the parent index uses `entry_coverage`, the same row rule."""
    parent = entry_coverage.EntryLedger(_source(fetch_module, PARENT_PATH, _bytes(PARENT_FIXTURE), 'parent'))
    row = next(r for r in parent.rows() if r['name'] == SHARED_NAME)
    key = (entry_coverage.matrix_row_for(row['container'])['resource'], row['name'])
    assert shadow_coverage.parent_index(parent) == {key: row}, shadow_coverage.parent_index(parent)


def test_a_run_with_no_declared_parent_reports_no_shadow(converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-2.3: no second source, no parent to read, no shadow section."""
    monkeypatch.setenv(fetch_module.API_KEY_ENV, 'test-key')
    monkeypatch.setattr(fetch_module, 'network_producer',
                        lambda request, key, insecure=False: _bytes(CHILD_FIXTURE))
    out = tmp_path / 'out'
    parser = run_pipeline(converter_module, None, out, ('--source', 'api', '--host', HOST,
                                                        '--cache-dir', str(tmp_path / 'cache'),
                                                        '--path', f'/{CHILD_PATH}'))
    assert shadow_coverage.shadow_findings(parser.ledger, None) == []
    report = (out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8')
    assert shadow_coverage.SHADOW_HEADING not in report, report


# --- 3. The ledger names the source -----------------------------------------

def test_every_row_names_the_source_that_holds_the_entry(converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-3.1: `source` is row data, the report value of the source, with no directory."""
    parser = _run_pair(converter_module, fetch_module, tmp_path / 'out', tmp_path / 'cache', monkeypatch)
    rows = parser.ledger.rows()
    assert rows, 'the per-scope run read rows to name'
    assert all(row['source'] == parser.source.name for row in rows), rows
    assert all('/' not in row['source'] for row in rows), rows


def test_the_entry_line_prints_no_source(converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-3.2: `source` is row data, not a printed field, so the entry-line bytes are
    unchanged for a one-source run."""
    parser = _run_pair(converter_module, fetch_module, tmp_path / 'out', tmp_path / 'cache', monkeypatch)
    for row in parser.ledger.rows():
        without = {key: value for key, value in row.items() if key != 'source'}
        assert entry_coverage.entry_line(row) == entry_coverage.entry_line(without), row
        assert entry_coverage.entry_line(row).count(parser.source.name) == 0, row


# --- 4. The shadow section --------------------------------------------------

def _shadow_block(report: str) -> str:
    start = report.index(shadow_coverage.SHADOW_HEADING)
    return report[start:report.index('Entry lines are grouped by')]


def test_the_shadow_section_prints_after_the_property_section(converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-4.1: header, summary, gaps, property findings, shadows, then the entry lines.

    This run has no property finding, so the property section prints nothing, and the
    shadow section is the section that comes before the entry lines.
    """
    out = tmp_path / 'out'
    _run_pair(converter_module, fetch_module, out, tmp_path / 'cache', monkeypatch)
    report = (out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8')
    header_at = report.index(f'{container_coverage.SOURCE_LABEL} ')
    summary_at = report.index('Per-entry report:')
    shadow_at = report.index(shadow_coverage.SHADOW_HEADING)
    assert header_at < summary_at < shadow_at < report.index('Entry lines are grouped by')
    assert entry_coverage.GAP_HEADING not in report, 'this run has no gap'


def test_the_shadow_line_shape_is_fixed(converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-4.2: line, object type, name, matrix row, parent source, parent line."""
    cache = tmp_path / 'cache'
    out = tmp_path / 'out'
    parser = _run_pair(converter_module, fetch_module, out, cache, monkeypatch)
    parent_ledger = _parent_ledger(fetch_module, cache)
    finding = shadow_coverage.shadow_findings(parser.ledger, parent_ledger)[0]
    name = f'{finding["container"]}/{finding["name"]}'
    expected = (f'  line {CHILD_LINE:>4}  ' + f'{name:<38} ' + f'{MATRIX_ROW:<32} '
                + f'parent source: {parent_ledger.source.name} (parent line {PARENT_LINE})')
    assert shadow_coverage.shadow_line(finding) == expected, shadow_coverage.shadow_line(finding)
    assert expected in _shadow_block((out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8'))


def test_the_shadow_lines_are_grouped_by_the_f3_9_scope_rule(converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-4.3: the section names the scope the child entry sits in, through the same
    grouping function the other report sections use."""
    cache = tmp_path / 'cache'
    out = tmp_path / 'out'
    parser = _run_pair(converter_module, fetch_module, out, cache, monkeypatch)
    report = (out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8')
    row = next(r for r in parser.ledger.rows() if r['name'] == SHARED_NAME)
    generator = converter_module.TerraformGenerator(str(out), {})
    header = generator._report_section_header(generator._report_scope_path(row))
    assert header.startswith('DEVICE GROUP: Production-DG'), header
    assert header in _shadow_block(report), _shadow_block(report)
    assert header in report[report.index('Entry lines are grouped by'):], report


def test_the_console_prints_no_shadow_line_and_the_exit_code_is_unchanged(
        converter_module, fetch_module, tmp_path, monkeypatch):
    """The console prints the gap lines only (backlog rule); a shadow is an operator
    action, so the F4.1 gate still decides the exit code."""
    out = tmp_path / 'out'
    monkeypatch.setenv(fetch_module.API_KEY_ENV, 'test-key')
    monkeypatch.setattr(fetch_module, 'network_producer', _producer(fetch_module))
    saved_argv = list(sys.argv)
    sys.argv = ['panorama_to_terraform.py'] + _argv(out, tmp_path / 'cache')
    try:
        with contextlib.redirect_stdout(io.StringIO()) as console:
            code = converter_module.main()
    finally:
        sys.argv = saved_argv
    assert code == 0, 'a shadow does not change the exit code (AC-2.4)'
    assert 'parent source' not in console.getvalue(), console.getvalue()
    assert not hasattr(shadow_coverage, 'console_line'), 'the shadow scan owns no console wording'
    assert shadow_coverage.SHADOW_HEADING in (out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8')


# --- 5. Determinism and the exit code ---------------------------------------

def test_two_runs_on_the_same_sources_write_the_same_bytes(converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-6.1: the report, the record, and the shadow section are byte-identical between
    two runs with the same arguments on the same bytes."""
    cache = _seed_cache(fetch_module, tmp_path / 'cache', (CHILD_PATH, PARENT_PATH))
    first = tmp_path / 'first'
    second = tmp_path / 'second'
    _run_pair(converter_module, fetch_module, first, cache, monkeypatch, offline=True)
    _run_pair(converter_module, fetch_module, second, cache, monkeypatch, offline=True)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == \
           {path.name: path.read_bytes() for path in second.iterdir()}
    assert shadow_coverage.SHADOW_HEADING in (first / entry_coverage.REPORT_FILE).read_text(encoding='utf-8')


# --- 6. CLI argument rules and offline CI -----------------------------------

def test_path_and_parent_apply_to_the_api_source_only(tmp_path):
    """A file run reads one scope: the file, so a declared path is an argument error."""
    result = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / CHILD_FIXTURE),
                        '--path', f'/{CHILD_PATH}', '--output-dir', str(tmp_path))
    assert result.returncode == 2, result.stdout + result.stderr
    assert 'apply to --source api' in result.stderr, result.stderr


def test_parent_needs_a_path(tmp_path):
    """A whole-config source holds its own parent, so the tool does not guess one."""
    result = run_script('panorama_to_terraform.py', '--source', 'api', '--host', HOST,
                        '--parent', f'/{PARENT_PATH}', '--output-dir', str(tmp_path))
    assert result.returncode == 2, result.stdout + result.stderr
    assert '--parent needs --path' in result.stderr, result.stderr


def test_a_path_must_name_a_scope_path(tmp_path):
    """The path shape is one definition, so the CLI checks it against the declared set."""
    for bad in ('/address/Web-Server-1', '/device-group/Web-Server-1', '/device-group/entry/'):
        result = run_script('panorama_to_terraform.py', '--source', 'api', '--host', HOST,
                            '--path', bad, '--cache-dir', str(tmp_path), '--output-dir', str(tmp_path))
        assert result.returncode == 2, (bad, result.stdout + result.stderr)
        assert 'must name a scope path' in result.stderr, result.stderr

    # A declared scope path is accepted, and the run stops at the missing cache entry:
    # an input refusal (exit 1), not an argument error.
    for good in ('/device-group/entry/Production-DG', '/shared', '/templates'):
        result = run_script('panorama_to_terraform.py', '--source', 'api', '--host', HOST,
                            '--path', good, '--offline', '--cache-dir', str(tmp_path),
                            '--output-dir', str(tmp_path))
        assert result.returncode == 1, (good, result.stdout + result.stderr)


def test_the_offline_run_reads_the_second_entry_from_the_cache(converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-7.3: the second run reads both cache entries the first run wrote, and finds the
    same shadows from the same bytes."""
    cache = _seed_cache(fetch_module, tmp_path / 'cache', (CHILD_PATH, PARENT_PATH))
    first = tmp_path / 'first'
    assert run_main(converter_module, _argv(first, cache, ('--offline',))) == 0
    monkeypatch.setattr(fetch_module, 'network_producer',
                        lambda request: (_ for _ in ()).throw(AssertionError('a cache hit calls no producer')))
    second = tmp_path / 'second'
    assert run_main(converter_module, _argv(second, cache, ('--offline',))) == 0
    for name in (entry_coverage.REPORT_FILE, provenance.PROVENANCE_FILE):
        assert (first / name).read_bytes() == (second / name).read_bytes(), name
    report = (first / entry_coverage.REPORT_FILE).read_text(encoding='utf-8')
    assert shadow_coverage.SHADOW_HEADING in report, report
