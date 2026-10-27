"""F5.3 provenance record: what one run read, and the report label that names it.

Five groups, one per acceptance rule:

1. What the record states: the eight fields, the values a file run and an api run write,
   and the byte facts measured by the door.
2. The record is data, and it is written outside the report bodies: the round trip, the
   refusal of a line that is not a field, and the report bodies keeping the name-only rule.
3. The label change: one `Source:` label, printed by both report writers for both sources.
4. The pruning rule: an entry a written record references is not prunable, and the
   reference is read as data, not from a printed line.
5. Determinism and the gate: two runs on the same bytes write the same record, a refusal
   writes no record, and the gate still decides the exit code.

No test calls the network: every api run uses an injected producer.
"""

import dataclasses
import hashlib

import pytest

import container_coverage
import entry_coverage
import provenance
import sanity_checks
from conftest import FIXTURES_DIR, SAMPLE_CONFIG, run_main, run_script

FETCH_FIXTURE = 'api_response.xml'
UNKNOWN_FIXTURE = 'unknown_containers.xml'

# A key that a test can search for in every output file, so a leak is visible.
SECRET_KEY = 'SECRET-KEY-9f3'
HOST = 'panorama.test'


def _bytes():
    return (FIXTURES_DIR / FETCH_FIXTURE).read_bytes()


def _run_file(fixture_name: str, out_dir) -> dict:
    """Run the converter on one fixture through the CLI. Return {file name: text}."""
    proc = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / fixture_name),
                      '--output-dir', str(out_dir))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return {path.name: path.read_text(encoding='utf-8') for path in out_dir.iterdir()}


def _run_api(converter_module, fetch_module, tmp_path, monkeypatch, cache_dir=None, out_dir=None):
    """Run the converter through the api producer, with an injected producer."""
    monkeypatch.setenv(fetch_module.API_KEY_ENV, SECRET_KEY)
    monkeypatch.setattr(fetch_module, 'network_producer', lambda req, key, insecure=False: _bytes())
    cache = cache_dir or tmp_path / 'cache'
    out = out_dir or tmp_path / 'out'
    assert run_main(converter_module, ['--source', 'api', '--host', HOST,
                                       '--cache-dir', str(cache), '--output-dir', str(out)]) == 0
    return cache, out


def _record(out_dir) -> provenance.ProvenanceRecord:
    """Read the record a run wrote, as data."""
    path = out_dir / provenance.PROVENANCE_FILE
    assert path.is_file(), f'the run wrote no {provenance.PROVENANCE_FILE}'
    return provenance.parse_record(path.read_text(encoding='utf-8'))


# --- 1. What the record states ------------------------------------------------

def test_the_record_field_names_are_the_printed_keys():
    """A tool reads the record as data, so a printed key must be a field name."""
    names = tuple(field.name for field in dataclasses.fields(provenance.ProvenanceRecord))
    assert names == provenance.FIELD_ORDER, names
    assert 'key' not in names, 'the record states no credential'
    assert len(provenance.FIELD_ORDER) == 8, provenance.FIELD_ORDER


def test_a_file_run_record_names_bytes_a_reader_can_reopen(tmp_path):
    """Kind, name, path, scope, the two api fields as `-`, and the byte facts."""
    out = tmp_path / 'out'
    proc = run_script('panorama_to_terraform.py', str(SAMPLE_CONFIG), '--output-dir', str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    record = _record(out)
    data = SAMPLE_CONFIG.read_bytes()
    assert record.kind == 'file'
    assert record.name == SAMPLE_CONFIG.name, 'the name is the report value, no directory'
    assert record.path == str(SAMPLE_CONFIG), 'the record is the file a reader reopens'
    assert record.scope == provenance.DEFAULT_SCOPE
    assert record.request == provenance.ABSENT, 'a file source has no request identity'
    assert record.cache_entry == provenance.ABSENT
    assert record.size == len(data)
    assert record.sha256 == hashlib.sha256(data).hexdigest(), 'the byte facts come from the door'


def test_an_api_run_record_names_the_request_identity_and_the_cache_entry(
        converter_module, fetch_module, tmp_path, monkeypatch):
    request = fetch_module.ApiRequest(host=HOST)
    cache, out = _run_api(converter_module, fetch_module, tmp_path, monkeypatch)
    record = _record(out)
    data = _bytes()
    assert record.kind == 'api'
    assert record.name == request.cache_name(), 'the report value is the cache entry'
    assert record.cache_entry == request.cache_name()
    assert record.request == request.canonical(), 'the identity is host and sorted params'
    assert 'key=' not in record.request, 'the identity is the key-free shape'
    assert record.path == str(cache / request.cache_name())
    assert record.size == len(data)
    assert record.sha256 == hashlib.sha256(data).hexdigest(), 'the cache entry holds the parsed bytes'
    assert record.scope == provenance.DEFAULT_SCOPE


def test_the_record_never_names_the_key(converter_module, fetch_module, tmp_path, monkeypatch):
    cache, out = _run_api(converter_module, fetch_module, tmp_path, monkeypatch)
    text = (out / provenance.PROVENANCE_FILE).read_text(encoding='utf-8')
    assert SECRET_KEY not in text, 'the key rule holds for the record'
    assert SECRET_KEY not in (cache / fetch_module.ApiRequest(host=HOST).cache_name()).read_text(
        encoding='utf-8', errors='surrogateescape')


# --- 2. The record is data, written outside the report bodies -----------------

def test_the_record_round_trips_as_data(tmp_path):
    """`parse_record` reads the written text back as the same record."""
    out = tmp_path / 'out'
    files = _run_file(UNKNOWN_FIXTURE, out)
    text = files[provenance.PROVENANCE_FILE]
    record = provenance.parse_record(text)
    assert provenance.render(record) == text
    # Data only: one line per field, so no prose line and no timestamp line.
    assert len(text.splitlines()) == len(provenance.FIELD_ORDER), text


def test_a_record_line_that_is_not_a_field_is_refused():
    """A reader cannot fall back to prose, so a line outside the fields is a refusal."""
    with pytest.raises(ValueError):
        provenance.parse_record('note: the run read this from the network')
    with pytest.raises(ValueError):
        provenance.parse_record('kind: file\nname: unknown_containers.xml\n')


def test_the_report_bodies_still_name_the_name_not_the_path(tmp_path):
    """The record is not a report body: a report body names the source name only.

    The same run writes both, so the path in the record cannot move a report byte.
    """
    out = tmp_path / 'out'
    files = _run_file(UNKNOWN_FIXTURE, out)
    for name in (entry_coverage.REPORT_FILE, 'MANUAL_SETUP_REPORT.txt'):
        body = files[name]
        assert f'Source: {UNKNOWN_FIXTURE}' in body, name
        assert str(FIXTURES_DIR) not in body, f'{name} names a path'
        assert 'Input file:' not in body, name
    record = provenance.parse_record(files[provenance.PROVENANCE_FILE])
    assert str(FIXTURES_DIR) in record.path, 'the record is the file that names the path'
    assert 'sha256:' not in files[entry_coverage.REPORT_FILE]
    assert 'sha256:' not in files['MANUAL_SETUP_REPORT.txt']


# --- 3. The label -------------------------------------------------------------

def test_one_label_for_both_sources(converter_module, fetch_module, tmp_path, monkeypatch):
    """One label, printed by the per-entry report and by the container section, for both sources."""
    assert container_coverage.SOURCE_LABEL == 'Source:'

    file_out = tmp_path / 'file'
    files = _run_file(UNKNOWN_FIXTURE, file_out)
    api_out = tmp_path / 'api'
    _run_api(converter_module, fetch_module, tmp_path, monkeypatch, out_dir=api_out)

    cache_name = fetch_module.ApiRequest(host=HOST).cache_name()
    for out, expected in ((file_out, UNKNOWN_FIXTURE), (api_out, cache_name)):
        body = (out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8')
        label = [line for line in body.splitlines() if line.startswith(container_coverage.SOURCE_LABEL)]
        assert label == [f'Source: {expected}'], (out.name, label)

    # The container section prints the same label, from the same constant.
    section = [line for line in files['MANUAL_SETUP_REPORT.txt'].splitlines()
               if line.startswith(container_coverage.SOURCE_LABEL)]
    assert section == [f'Source: {UNKNOWN_FIXTURE}'], section


# --- 4. The pruning rule reads the reference as data --------------------------

def test_an_entry_a_written_record_references_is_not_prunable(
        converter_module, fetch_module, tmp_path, monkeypatch):
    cache, out = _run_api(converter_module, fetch_module, tmp_path, monkeypatch)
    record = _record(out)
    assert provenance.cache_reference(record) == record.cache_entry
    assert provenance.prunable_entries(cache, [record]) == [], 'a referenced entry is not prunable'


def test_an_entry_no_record_references_is_prunable(converter_module, fetch_module, tmp_path, monkeypatch):
    cache, out = _run_api(converter_module, fetch_module, tmp_path, monkeypatch)
    record = _record(out)
    stale = cache / 'stale-entry.xml'
    stale.write_bytes(_bytes())
    assert provenance.prunable_entries(cache, [record]) == [stale]


def test_the_reference_is_data_not_a_printed_line(converter_module, fetch_module, tmp_path, monkeypatch):
    """A report line that shows the entry name is not a reference. Only the field is.

    The same bytes are read twice: once through the api producer, which writes a record
    that references the cache entry, and once as a file whose name is the entry name, which
    prints that name in the report body while its record references nothing.
    """
    request = fetch_module.ApiRequest(host=HOST)
    cache, out = _run_api(converter_module, fetch_module, tmp_path, monkeypatch)
    api_record = _record(out)

    mirror = tmp_path / 'mirror'
    mirror.mkdir()
    named = mirror / request.cache_name()
    named.write_bytes(_bytes())
    file_out = tmp_path / 'file_run'
    proc = run_script('panorama_to_terraform.py', str(named), '--output-dir', str(file_out))
    assert proc.returncode == 0, proc.stdout + proc.stderr

    file_record = _record(file_out)
    assert file_record.name == request.cache_name(), 'the report value is the name the run was given'
    assert provenance.cache_reference(file_record) is None, 'a file record references no cache entry'
    assert request.cache_name() in (file_out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8'), \
        'the report body shows the name, and that line is not a reference'
    assert provenance.prunable_entries(cache, [file_record]) == [cache / request.cache_name()], \
        'the printed line protects nothing'
    assert provenance.prunable_entries(cache, [file_record, api_record]) == []


# --- 5. Determinism and the gate ---------------------------------------------

def test_two_runs_on_the_same_bytes_write_the_same_record(tmp_path):
    first = tmp_path / 'a'
    second = tmp_path / 'b'
    _run_file(FETCH_FIXTURE, first)
    _run_file(FETCH_FIXTURE, second)
    assert (first / provenance.PROVENANCE_FILE).read_bytes() == \
           (second / provenance.PROVENANCE_FILE).read_bytes()


def test_a_cache_derived_name_repeats_across_cache_dirs(
        converter_module, fetch_module, tmp_path, monkeypatch):
    """The name comes from the request identity, not from the directory, so the record
    repeats for the same bytes even when the path field cannot."""
    cache1, out1 = _run_api(converter_module, fetch_module, tmp_path, monkeypatch,
                            cache_dir=tmp_path / 'cache1', out_dir=tmp_path / 'out1')
    cache2, out2 = _run_api(converter_module, fetch_module, tmp_path, monkeypatch,
                            cache_dir=tmp_path / 'cache2', out_dir=tmp_path / 'out2')
    first, second = _record(out1), _record(out2)
    assert first.cache_entry == second.cache_entry
    assert first.request == second.request
    assert first.size == second.size and first.sha256 == second.sha256
    assert first.path != second.path, 'the two runs read two different files'
    assert dataclasses.replace(second, path=first.path) == first, 'only the path differs'


def test_the_record_is_written_on_every_completed_run(tmp_path):
    """A run that read no entry writes no report, but it still writes the record."""
    empty = tmp_path / 'empty.xml'
    empty.write_text('<?xml version="1.0"?>\n<config>\n<device-group/>\n</config>\n', encoding='utf-8')
    out = tmp_path / 'out'
    proc = run_script('panorama_to_terraform.py', str(empty), '--output-dir', str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not (out / entry_coverage.REPORT_FILE).is_file()
    record = _record(out)
    assert record.name == 'empty.xml'
    assert record.size == len(empty.read_bytes())


def test_a_refusal_writes_no_record(converter_module, fetch_module, tmp_path):
    """A refusal writes no output, so it writes no record either (F5.2 AC-6.3)."""
    cache = tmp_path / 'cache'
    out = tmp_path / 'out'
    result = run_script('panorama_to_terraform.py', '--source', 'api', '--host', HOST,
                        '--cache-dir', str(cache), '--offline', '--output-dir', str(out))
    assert result.returncode == 1
    assert not out.exists() or not [path for path in out.rglob('*') if path.is_file()]


def test_the_record_is_not_a_gate_input_and_the_exit_code_is_unchanged(tmp_path):
    """The gate reads `.tf` files, so the record cannot change what it counts or decides."""
    out = tmp_path / 'out'
    proc = run_script('panorama_to_terraform.py', str(SAMPLE_CONFIG), '--output-dir', str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = sanity_checks.run_checks(out)
    assert not report.failed
    assert report.file_count == len(list(out.glob('*.tf'))), 'the gate counts .tf files only'
    assert report.result_of('terraform') == 'NOT RUN'
