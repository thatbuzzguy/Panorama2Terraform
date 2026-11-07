"""F5.3 provenance record: what one run read, and the report label that names it.

Six groups, one per acceptance rule:

1. What the record states: the eight fields, the values a file run and an api run write,
   and the byte facts measured by the door.
2. The record is data, and it is written outside the report bodies: the round trip, the
   refusal of a line that is not a field, and the report bodies keeping the name-only rule.
3. The label change: one `Source:` label, printed by both report writers for both sources.
4. The pruning rule: an entry a written record references is not prunable, and the
   reference is read as data, not from a printed line.
5. Determinism and the gate: two runs on the same bytes write the same record, a refusal
   writes no record, and the gate still decides the exit code.
6. The record directory and the prune action: the record is a codebase root-set file, so the
   action reads the record file the same run wrote; what it removes, what it keeps, what it
   refuses, and what it cannot change.

The path 2 case (F8.6) is pinned inside groups 1, 2 and 6: the record names the request that made each
response, the record file holds one record per request the run read, and the action protects every entry a
path 2 run read.

No test calls the network: every api run uses an injected producer, or reads a seeded cache
with `--offline`. The path 2 pins read every response through the injected producer, as
`tests/test_api_requests.py` does, and the committed response set is read through it.
"""

import dataclasses
import hashlib
from pathlib import Path

import pytest

import api_requests
import container_coverage
import entry_coverage
import provenance
import sanity_checks
import write_path
import xml_input
from conftest import (
    FIXTURES_DIR,
    RESPONSES_DIR,
    SAMPLE_CONFIG,
    file_text,
    run_main,
    run_script,
    tf_files,
    written_bytes,
)

FETCH_FIXTURE = 'api_response.xml'
UNKNOWN_FIXTURE = 'unknown_containers.xml'

# The F5.4 pair: the child scope the run reads, and the parent scope it declares.
CHILD_PATH = 'device-group/entry/Production-DG'
PARENT_PATH = 'shared'

# A key that a test can search for in every output file, so a leak is visible.
SECRET_KEY = 'SECRET-KEY-9f3'
HOST = 'panorama.test'

# The path 2 reads (F8.6, `docs/API_CONVERSION_PATH.md` §2.5): one response per request the run read.
# `device-group` is the committed response the offline harness holds (`tests/responses/`), read through the
# injected producer, so the record names the bytes the fixture holds. `templates` is the other membership
# read, and the two entry paths are the requests the scope index names for the entries those containers read.
PATH_2_READS = ('device-group/entry/devices', 'templates/entry/devices')
COMMITTED_READ = 'device-group'
PATH_2_BODIES = {
    'templates': '<entry name="HQ-Networks"><devices><entry name="fw-1.example.com" /></devices></entry>',
    'device-group/entry/Office-FW':
        '<entry name="Office-FW"><devices><entry name="fw-1.example.com" /></devices></entry>',
    'templates/entry/HQ-Networks':
        '<entry name="HQ-Networks"><devices><entry name="fw-1.example.com" /></devices></entry>',
}


def _bytes():
    return (FIXTURES_DIR / FETCH_FIXTURE).read_bytes()


def _run_file(fixture_name: str, out_dir) -> dict:
    """Run the converter on one fixture through the CLI. Return {file name: text}."""
    proc = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / fixture_name),
                      '--output-dir', str(out_dir))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    # F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): the `.tf` set is read as the gate reads it, so a `.tf`
    # entry holds the parts the run wrote for every unit, in path order. A report and a record are codebase
    # root-set files, so they stay at the root and are keyed by their name.
    tf = tf_files(out_dir)
    files = {Path(key).name: file_text(tf, Path(key).name) for key in tf}
    for path in sorted(Path(out_dir).iterdir()):
        if path.is_file() and path.name not in files:
            files[path.name] = path.read_text(encoding='utf-8')
    return files


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


def _run_pair(converter_module, fetch_module, tmp_path, monkeypatch):
    """Run the converter for a child scope and its declared parent (F5.4), reading both
    from a seeded cache so no test opens a connection. Returns (cache, out)."""
    monkeypatch.setenv(fetch_module.API_KEY_ENV, SECRET_KEY)
    cache = tmp_path / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    for path, fixture in ((CHILD_PATH, 'scope_child.xml'), (PARENT_PATH, 'scope_parent.xml')):
        request = fetch_module.ApiRequest(host=HOST, path=path)
        (cache / request.cache_name()).write_bytes((FIXTURES_DIR / fixture).read_bytes())
    out = tmp_path / 'out'
    assert run_main(converter_module, ['--source', 'api', '--host', HOST, '--cache-dir', str(cache),
                                       '--path', f'/{CHILD_PATH}', '--parent', f'/{PARENT_PATH}',
                                       '--offline', '--output-dir', str(out)]) == 0
    return cache, out


def _path_2_response(request) -> bytes:
    """The response for one path 2 request, in the shape that request states: `result` holds the element the
    path names, which is the entry itself for an entry read and the container for a place read. The
    `device-group` read is the committed response, so the record names the same bytes the fixture holds. The
    producer hands these bytes, so no test calls a network.
    """
    if request.path == COMMITTED_READ:
        return (RESPONSES_DIR / request.cache_name()).read_bytes()
    body = PATH_2_BODIES[request.path]
    segments = request.segments()
    held = body if len(segments) == 3 else f'<{segments[0]}>\n{body}\n</{segments[0]}>'
    return ('<?xml version="1.0"?>\n<response type="success" code="0">\n<result>\n'
            + held + '\n</result>\n</response>\n').encode()


def _path_2_run(converter_module, fetch_module, cache, out, monkeypatch):
    """The path 2 run, read one response at a time through the injected producer, in the order it read them:
    the membership responses first, because the scope index is built from them, then the response for each
    request the index names. Returns (index, reads), where `reads` names the request and the source for each
    response in read order, and writes the record file through the single writer at the codebase root, one
    record per request the run read.

    The record order is the read order. Which order a path 2 run reads is the run order's decision (the entry
    point, F8.9), so `provenance.py` states no read rule for it, and this helper states the read order only for
    the pin.
    """
    monkeypatch.setattr(fetch_module, 'network_producer', lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError('the run called the network')))

    membership, reads, read_names = {}, [], set()
    for list_path in PATH_2_READS:
        request = fetch_module.ApiRequest(host=HOST, path=api_requests.list_container(list_path))
        source = fetch_module.fetch(request, cache, producer=lambda r: _path_2_response(r))
        reads.append((request, source))
        read_names.add(request.cache_name())
        for table, values in converter_module.PanoramaParser(source).parse_associations().items():
            for owner, names in values.items():
                membership.setdefault(table, {}).setdefault(owner, []).extend(names)

    index = api_requests.scope_index(HOST, membership, PATH_2_READS)
    for entry in index:
        # A place is read once: the membership read is the response for the place the index names.
        if entry.request.cache_name() in read_names:
            continue
        source = fetch_module.fetch(entry.request, cache, producer=lambda r: _path_2_response(r))
        reads.append((entry.request, source))

    records = [provenance.record_for(source, request=request) for request, source in reads]
    write_path.write_file(write_path.root_path(out, provenance.PROVENANCE_FILE),
                          provenance.render_records(records))
    return index, reads


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
    assert record.scope == xml_input.DEFAULT_SCOPE
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
    assert record.scope == xml_input.DEFAULT_SCOPE


def test_the_record_never_names_the_key(converter_module, fetch_module, tmp_path, monkeypatch):
    cache, out = _run_api(converter_module, fetch_module, tmp_path, monkeypatch)
    text = (out / provenance.PROVENANCE_FILE).read_text(encoding='utf-8')
    assert SECRET_KEY not in text, 'the key rule holds for the record'
    assert SECRET_KEY not in (cache / fetch_module.ApiRequest(host=HOST).cache_name()).read_text(
        encoding='utf-8', errors='surrogateescape')


def test_the_path_2_record_names_the_request_that_made_each_response(
        converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-1.3, AC-1.5 and AC-3.1: for each request the run read, `scope` names the path that request declared
    and `request` names the key-free identity of that request, which is the shape the cache entry is hashed
    from. Every response is handed by an injected producer, so the two byte facts are the door's, and the
    record for the committed response names the same bytes the fixture holds.
    """
    cache, out = tmp_path / 'cache', tmp_path / 'out'
    index, reads = _path_2_run(converter_module, fetch_module, cache, out, monkeypatch)
    assert len(reads) == len(index), 'one response per request the index names'

    records = provenance.parse_records((out / provenance.PROVENANCE_FILE).read_text(encoding='utf-8'))
    for (request, source), record in zip(reads, records):
        entry = api_requests.entry_for_path(index, request.path)
        assert entry is not None and entry.request.cache_name() == request.cache_name(), (request, entry)
        assert record.kind == 'api', record
        assert record.scope == request.path == entry.path, 'the record names the path the request declared'
        assert record.request == request.canonical(), 'the record names the key-free identity'
        assert 'key=' not in record.request, 'the identity is the key-free shape'
        assert record.name == request.cache_name(), 'the report value, not the path'
        assert source.origin.name == request.cache_name(), 'the door named the response the record names'
        assert record.cache_entry == request.cache_name(), 'the entry that identity names'
        assert record.path == str(cache / request.cache_name()), 'the entry a reader reopens'
        data = _path_2_response(request)
        assert record.size == len(data), 'the byte facts come from the door'
        assert record.sha256 == hashlib.sha256(data).hexdigest(), record

    assert len(records) == 4, records
    assert len({record.cache_entry for record in records}) == len(records), 'one cache entry per request'
    assert SECRET_KEY not in (out / provenance.PROVENANCE_FILE).read_text(encoding='utf-8')


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


def test_one_record_writes_the_same_bytes_as_the_f5_3_rule(fetch_module):
    """F5.4 adds records, not a new record shape: a one-record file is `render`."""
    request = fetch_module.ApiRequest(host=HOST)
    origin = xml_input.SourceOrigin(kind='api', name=request.cache_name())
    source = fetch_module.unwrap_config_root(xml_input.parse_bytes(_bytes(), origin), request)
    record = provenance.record_for(source, request=request)
    assert record.scope == xml_input.DEFAULT_SCOPE, 'a whole-config record states the whole config'
    assert provenance.render_records([record]) == provenance.render(record)
    assert provenance.parse_records(provenance.render_records([record])) == [record]


def test_the_record_file_holds_one_record_per_source_read(converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-1.1 and AC-1.2: the main source, then the declared parent, in read order, with
    each record stating its own scope; and the path 2 case, where one response is one source, so a run
    that read N requests writes N records in the order it read them.
    """
    _, out = _run_pair(converter_module, fetch_module, tmp_path, monkeypatch)
    text = (out / provenance.PROVENANCE_FILE).read_text(encoding='utf-8')
    records = provenance.parse_records(text)
    assert [record.scope for record in records] == [CHILD_PATH, PARENT_PATH], records
    assert len(text.split('\n\n')) == 2, text
    assert text == provenance.render_records(records), 'the record file reads back as itself'
    # F8.1: the record names the whole sorted identity, so the path is one part of it and no
    # longer the last part. The pin keeps the fact it pins: the record names the request identity.
    assert f'path={CHILD_PATH}' in records[0].request, records[0].request
    assert 'key=' not in records[1].request, 'the key rule holds for the second request (AC-5.5)'
    assert records[0].cache_entry != records[1].cache_entry, 'one cache entry per request identity'

    # The path 2 case (F8.6): N requests, read through the injected producer, so N records, in the order the
    # run read them. The record module states no read rule for a path 2 run, so the file order is the order
    # the run read them, which is what the helper read them in.
    cache, path2 = tmp_path / 'cache', tmp_path / 'path2'
    index, reads = _path_2_run(converter_module, fetch_module, cache, path2, monkeypatch)
    text = (path2 / provenance.PROVENANCE_FILE).read_text(encoding='utf-8')
    records = provenance.parse_records(text)
    assert len(records) == len(reads) == len(index), 'one record per request the run read'
    assert [record.scope for record in records] == [request.path for request, _ in reads], records
    assert [record.request for record in records] == [request.canonical() for request, _ in reads], records
    assert [record.cache_entry for record in records] == [request.cache_name() for request, _ in reads]
    assert len(text.split('\n\n')) == len(records), 'one blank line between records, the whole shape'
    assert text == provenance.render_records(records), 'the record file reads back as itself'


def test_a_path_2_record_file_reads_back_with_no_new_field(
        converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-1.2: the eight fields and the fixed order are unchanged, so `parse_records` reads a path 2 record
    file back as itself, with no field outside the declared shape, and a second run that read the same
    requests writes the same record bytes.
    """
    cache, first, second = tmp_path / 'cache', tmp_path / 'out1', tmp_path / 'out2'
    _, reads = _path_2_run(converter_module, fetch_module, cache, first, monkeypatch)
    text = (first / provenance.PROVENANCE_FILE).read_text(encoding='utf-8')
    records = provenance.parse_records(text)
    assert text == provenance.render_records(records), 'the record file reads back as itself'
    for chunk in text.split('\n\n'):
        keys = [line.partition(': ')[0] for line in chunk.splitlines()]
        assert keys == list(provenance.FIELD_ORDER), (chunk, 'no new field, no prose, no timestamp')

    # Two runs that read the same requests write the same bytes, because the record names no timestamp and
    # both runs read the same cache.
    _path_2_run(converter_module, fetch_module, cache, second, monkeypatch)
    assert (first / provenance.PROVENANCE_FILE).read_bytes() == \
           (second / provenance.PROVENANCE_FILE).read_bytes()


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


def test_a_printed_parent_source_is_not_a_reference(converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-6.4: the shadow section prints a source name, and that printed line is not a
    reference. The reference is the `cache_entry` field of a parsed record."""
    cache, out = _run_pair(converter_module, fetch_module, tmp_path, monkeypatch)
    records = provenance.parse_records((out / provenance.PROVENANCE_FILE).read_text(encoding='utf-8'))
    parent = records[1]
    assert provenance.prunable_entries(cache, records) == [], 'both records reference their entries'

    # Read with the child record only: the parent entry is prunable, even though the
    # report line names it.
    prunable = provenance.prunable_entries(cache, records[:1])
    assert prunable == [cache / parent.cache_entry], prunable
    assert parent.name in (out / entry_coverage.REPORT_FILE).read_text(encoding='utf-8'), \
        'the shadow line shows the name, and that line is not a reference'


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
    """The gate reads the `.tf` files for the block rules and the four data files for the data rule
    (F6.8), and `SOURCE.txt` is neither, so the record cannot change what the gate counts or decides.
    """
    out = tmp_path / 'out'
    proc = run_script('panorama_to_terraform.py', str(SAMPLE_CONFIG), '--output-dir', str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = sanity_checks.run_checks(out)
    assert not report.failed
    assert report.file_count == len(tf_files(out)), 'the block reader counts the unit set'
    assert report.data_file_count == 2, 'the record is not one of the four data files'
    assert report.result_of('terraform') == 'NOT RUN'


def _stale_entry(cache) -> Path:
    """A cache entry the run did not read, so no written record references it."""
    cache.mkdir(parents=True, exist_ok=True)
    entry = cache / 'stale-entry.xml'
    entry.write_bytes(_bytes())
    return entry


def _prune_run(converter_module, fetch_module, cache, out, monkeypatch, extra_args=()):
    """Run the converter with the prune action declared. Returns the exit code.

    Every run here reads a seeded cache with `--offline`, so no test calls the network.
    """
    monkeypatch.setenv(fetch_module.API_KEY_ENV, SECRET_KEY)
    request = fetch_module.ApiRequest(host=HOST)
    cache.mkdir(parents=True, exist_ok=True)
    (cache / request.cache_name()).write_bytes(_bytes())
    return run_main(converter_module, ['--source', 'api', '--host', HOST, '--cache-dir', str(cache),
                                       '--offline', *extra_args, '--prune-cache',
                                       '--output-dir', str(out)])


# --- 6. The record directory, and the prune action -----------------------------

def test_the_prune_keeps_an_entry_a_written_record_references(converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-9: the action removes nothing that a written record references.

    The entry the run reads is the entry its own record references, so a run on a cache that holds
    only that entry removes nothing.
    """
    cache, out = tmp_path / 'cache', tmp_path / 'out'
    assert _prune_run(converter_module, fetch_module, cache, out, monkeypatch) == 0
    entry = cache / fetch_module.ApiRequest(host=HOST).cache_name()
    assert entry.is_file(), 'a referenced entry is not pruned'
    reference = provenance.parse_records((out / provenance.PROVENANCE_FILE).read_text(encoding='utf-8'))[0]
    assert reference.cache_entry == entry.name, 'the reference is the field of the written record'


def test_the_prune_removes_an_entry_no_written_record_references(converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-9: the action removes what `prunable_entries` names, and nothing else."""
    cache, out = tmp_path / 'cache', tmp_path / 'out'
    stale = _stale_entry(cache)
    assert _prune_run(converter_module, fetch_module, cache, out, monkeypatch) == 0
    assert not stale.is_file(), 'an unreferenced entry is pruned'
    kept = [path.name for path in cache.iterdir() if path.is_file()]
    assert kept == [fetch_module.ApiRequest(host=HOST).cache_name()], 'only the referenced entry stays'


def test_the_prune_reads_the_record_file_and_not_the_records_the_run_built(tmp_path):
    """The reference is the written record file, so a record file that names another entry protects that
    entry and leaves the entry the run read prunable. The action reads the file through `parse_records`.
    """
    out = tmp_path / 'out'
    out.mkdir()
    cache = tmp_path / 'cache'
    cache.mkdir()
    own = cache / 'the-entry-the-run-read'
    own.write_bytes(_bytes())
    other = cache / 'the-entry-the-written-record-names'
    other.write_bytes(_bytes())

    record = provenance.ProvenanceRecord(kind='api', name='source', path='-', scope=xml_input.DEFAULT_SCOPE,
                                         request=provenance.ABSENT, cache_entry=other.name,
                                         size=len(_bytes()), sha256=hashlib.sha256(_bytes()).hexdigest())
    record_file = write_path.root_path(out, provenance.PROVENANCE_FILE)
    write_path.write_file(record_file, provenance.render(record))
    assert provenance.prune(record_file, cache) == [own], 'the reference is the record file the action reads'
    assert other.is_file(), 'the entry the written record names stays'
    assert provenance.parse_records(record_file.read_text(encoding='utf-8')) == [record]


def test_the_prune_reads_a_record_file_with_two_records(converter_module, fetch_module, tmp_path, monkeypatch):
    """The two-record case: one file holds two records, so the action keeps both entries and prunes an
    entry neither record references.
    """
    cache, out = _run_pair(converter_module, fetch_module, tmp_path, monkeypatch)
    records = provenance.parse_records((out / provenance.PROVENANCE_FILE).read_text(encoding='utf-8'))
    assert len(records) == 2, records
    kept = [cache / record.cache_entry for record in records]
    stale = _stale_entry(cache)
    assert run_main(converter_module, ['--source', 'api', '--host', HOST, '--cache-dir', str(cache),
                                       '--path', f'/{CHILD_PATH}', '--parent', f'/{PARENT_PATH}',
                                       '--offline', '--prune-cache', '--output-dir', str(out)]) == 0
    for entry in kept:
        assert entry.is_file(), f'the record file references {entry.name}'
    assert not stale.is_file(), 'one file, two records, and an entry neither names is pruned'


def test_the_prune_protects_every_entry_a_path_2_run_read(
        converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-2.1 and AC-2.2: the record is a codebase root-set file, so the action reads the record file the path
    2 run wrote at the codebase root, and the reference is the `cache_entry` field of each parsed record, so a
    run that read N requests protects the N entries its own record names and prunes an entry none references.
    """
    cache, out = tmp_path / 'cache', tmp_path / 'out'
    _, reads = _path_2_run(converter_module, fetch_module, cache, out, monkeypatch)
    stale = _stale_entry(cache)

    # The record path is named through the builder for the set the record belongs to, because the module that
    # owns the record builds no path.
    record_file = write_path.root_path(out, provenance.PROVENANCE_FILE)
    assert record_file == out / provenance.PROVENANCE_FILE, 'the record directory is the output directory'
    removed = provenance.prune(record_file, cache)
    assert removed == [stale], 'the action removes only what no record references'

    parsed = provenance.parse_records(record_file.read_text(encoding='utf-8'))
    assert [provenance.cache_reference(record) for record in parsed] == [request.cache_name()
                                                                         for request, _ in reads], \
        'the reference is the field of the record file the action reads'
    kept = sorted(path.name for path in cache.iterdir() if path.is_file())
    assert kept == sorted(request.cache_name() for request, _ in reads), 'the N entries the run read stay'


def test_a_record_the_prune_cannot_read_is_refused(tmp_path):
    """AC-6: the record is data, so a record file that is not the declared shape, or no record file, is a
    refusal, and the refusal names the record file rather than an input file. A refusal prunes nothing.
    """
    out = tmp_path / 'out'
    out.mkdir()
    cache = tmp_path / 'cache'
    cache.mkdir()
    entry = cache / 'an-entry'
    entry.write_bytes(_bytes())

    bad = out / provenance.PROVENANCE_FILE
    write_path.write_file(bad, 'kind: file\nnote: the run read this from the network\n')
    with pytest.raises(ValueError) as refused:
        provenance.prune(bad, cache)
    assert str(bad) in str(refused.value), 'the refusal names the record file'
    assert entry.is_file(), 'a refusal prunes nothing'

    missing = out / 'no-record-here.txt'
    with pytest.raises(ValueError) as refused:
        provenance.prune(missing, cache)
    assert str(missing) in str(refused.value), 'a record file the action cannot read is a refusal'
    assert entry.is_file(), 'a refusal prunes nothing'

    # A cache directory that holds nothing has nothing to prune, so it is not a refusal.
    assert provenance.prune(bad, tmp_path / 'no-cache') == []


def test_a_refused_record_exits_one_and_a_prune_that_removes_nothing_changes_nothing(
        converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-6: the gate decides the exit code, and the prune cannot move it. A record the action cannot read
    is a refusal, so the run exits 1.
    """
    cache, clean = tmp_path / 'cache', tmp_path / 'clean'
    assert _prune_run(converter_module, fetch_module, cache, clean, monkeypatch) == 0, \
        'a prune that removes nothing does not change the code'
    report = sanity_checks.run_checks(clean)
    assert not report.failed, 'the gate still decides'
    assert report.data_file_count == 2, 'the record is not a gate input'
    assert not report.findings('data_files')

    # The stand-in is the refusal the same action raises, so the run's exit code for a refusal is pinned.
    def refuse(record_file, cache_dir):
        raise ValueError(f'cannot read the record: {record_file}')

    monkeypatch.setattr(provenance, 'prune', refuse)
    assert _prune_run(converter_module, fetch_module, cache, tmp_path / 'refused', monkeypatch) == 1


def test_a_run_that_does_not_declare_the_action_keeps_the_cache_and_writes_the_same_bytes(
        converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-5 and AC-7: the action is opt-in. A run that declares nothing keeps its cache and prints nothing
    new, and the cache is no output, so the same run with the action writes the same bytes.
    """
    monkeypatch.setenv(fetch_module.API_KEY_ENV, SECRET_KEY)
    cache = tmp_path / 'cache'
    cache.mkdir()
    entry = cache / fetch_module.ApiRequest(host=HOST).cache_name()
    entry.write_bytes(_bytes())
    stale = _stale_entry(cache)

    off = tmp_path / 'off'
    assert run_main(converter_module, ['--source', 'api', '--host', HOST, '--cache-dir', str(cache),
                                       '--offline', '--output-dir', str(off)]) == 0
    assert stale.is_file(), 'a run that declares no action keeps its cache'
    on = tmp_path / 'on'
    assert run_main(converter_module, ['--source', 'api', '--host', HOST, '--cache-dir', str(cache),
                                       '--offline', '--prune-cache', '--output-dir', str(on)]) == 0
    assert not stale.is_file(), 'the run that declares the action prunes it'
    assert written_bytes(off) == written_bytes(on), 'the action writes no output, so the goldens stay'


def test_the_console_prints_the_pruned_entries_only_when_it_removed_something(
        converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-7: one line per pruned entry, and no line when the action removed nothing or was not declared.
    The run is offline on a seeded cache, so no test calls the network.
    """
    cache = tmp_path / 'cache'
    cache.mkdir()
    (cache / fetch_module.ApiRequest(host=HOST).cache_name()).write_bytes(_bytes())
    stale = _stale_entry(cache)

    argv = ['--source', 'api', '--host', HOST, '--cache-dir', str(cache), '--offline']
    off = run_script('panorama_to_terraform.py', *argv, '--output-dir', str(tmp_path / 'off'))
    assert off.returncode == 0, off.stdout + off.stderr
    assert 'Cache prune' not in off.stdout, 'a run that declares no action prints nothing about the cache'

    on = run_script('panorama_to_terraform.py', *argv, '--prune-cache', '--output-dir', str(tmp_path / 'on'))
    assert on.returncode == 0, on.stdout + on.stderr
    assert not stale.is_file()
    block = [line for line in on.stdout.splitlines() if 'Cache prune' in line or stale.name in line]
    assert len(block) == 2, on.stdout

    # The same run again removes nothing, so it prints nothing new.
    again = run_script('panorama_to_terraform.py', *argv, '--prune-cache', '--output-dir', str(tmp_path / 'again'))
    assert again.returncode == 0, again.stdout + again.stderr
    assert 'Cache prune' not in again.stdout, again.stdout


def test_the_prune_flag_applies_to_the_api_source_only(tmp_path):
    """AC-4: a file record states `-` for the cache field, so a file run has nothing to prune and the flag
    is an argument error (exit 2). The flag names no part of the layout, so the no-flag scan is unchanged.
    """
    out = tmp_path / 'out'
    result = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / UNKNOWN_FIXTURE),
                        '--prune-cache', '--output-dir', str(out))
    assert result.returncode == 2, result.stdout + result.stderr
    assert not out.exists(), 'an argument error writes no record'

    help_text = run_script('panorama_to_terraform.py', '--help').stdout
    assert '--prune-cache' in help_text, help_text
    assert not hasattr(provenance, 'add_arguments'), 'the rule owner states no flag; the CLI does'


def test_a_state_record_protects_no_entry_when_the_action_runs(converter_module, fetch_module, tmp_path, monkeypatch):
    """F5.6 read through the action: the state record states `-` for its two request fields, so it
    references nothing and protects nothing, and the entry the api record references stays.
    """
    cache, out = tmp_path / 'cache', tmp_path / 'out'
    stale = _stale_entry(cache)
    assert _prune_run(converter_module, fetch_module, cache, out, monkeypatch,
                      extra_args=('--state', str(FIXTURES_DIR / 'state_workspace.json'),
                                  '--workspace', 'production')) == 0
    records = provenance.parse_records((out / provenance.PROVENANCE_FILE).read_text(encoding='utf-8'))
    assert [record.kind for record in records] == ['api', 'state'], records
    assert records[1].cache_entry == provenance.ABSENT, 'the state record references nothing'
    assert not stale.is_file(), 'the state record protected nothing'
    assert (cache / fetch_module.ApiRequest(host=HOST).cache_name()).is_file(), 'the api record protects its entry'
