"""F5.6 state producer: the Terraform state document, read as a declared reference source.

Six groups, one per acceptance rule:

1. The door keeps its two byte checks for every source kind. The size check is
   kind-independent, and the DTD check asks the parser, so a JSON document reaches no DOCTYPE:
   `<!DOCTYPE` inside a JSON value is not a refusal.
2. The entry shape a scan can read: one entry per instance object, the nested block as an object
   or a one-element list, and the resource address as the position.
3. The document-shape refusals, through the same input-refusal class the door uses.
4. The record facts the producer states: the origin kind, the byte facts measured on the bytes
   the door checked, and the scope as the workspace the run declared.
5. The CLI argument rules, and the exit codes that do not change.
6. The read stays offline: a state read is a file read, so `--offline` covers the api producer
   only, and every test here uses a committed fixture.

The fixture is `tests/fixtures/state_workspace.json`; the run side is
`tests/fixtures/address_objects.xml`.
"""

import hashlib
import json

import pytest

import container_coverage
import provenance
import source_fetch
import state_input
import xml_input
from conftest import FIXTURES_DIR, run_main, run_script

STATE_FIXTURE = 'state_workspace.json'
RUN_FIXTURE = 'address_objects.xml'
WORKSPACE = 'production'


def _bytes() -> bytes:
    return (FIXTURES_DIR / STATE_FIXTURE).read_bytes()


def _origin(name: str = STATE_FIXTURE) -> xml_input.SourceOrigin:
    """A state origin with no file behind it, the shape a producer hands."""
    return xml_input.SourceOrigin(kind=state_input.STATE_KIND, name=name)


def _document(resources) -> bytes:
    return json.dumps({'version': 4, 'resources': resources}).encode()


def _entry(name: str, attributes: dict, module: str = 'root',
          resource_type: str = 'panos_address') -> dict:
    """One resource in the shape state format version 4 writes."""
    return {'module': module, 'type': resource_type, 'name': name,
            'instances': [{'schema_version': 0, 'attributes': attributes}]}


def _run(extra_args: tuple, tmp_path) -> tuple:
    """Run the converter with the committed state fixture. Returns (exit code, console)."""
    result = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / RUN_FIXTURE),
                        '--state', str(FIXTURES_DIR / STATE_FIXTURE),
                        '--output-dir', str(tmp_path), *extra_args)
    return result.returncode, result.stdout + result.stderr


# --- 1. The two byte checks run for every source kind ------------------------

def test_the_size_check_runs_on_the_state_bytes():
    """AC-1.1: the size check is kind-independent, so a JSON source is refused by it exactly as
    a file is, and the refusal names the origin."""
    data = _bytes()
    with pytest.raises(xml_input.UnsafeInputError) as refused:
        state_input.parse_state(data, _origin(), max_input_bytes=len(data) - 1)
    message = str(refused.value)
    assert f"'{STATE_FIXTURE}'" in message, message
    assert 'exceeds the input limit' in message, message


def test_the_dtd_check_refuses_nothing_for_a_json_document():
    """AC-1.1: only XML has a prolog, so `<!DOCTYPE` inside a JSON value is not a refusal. The
    door keeps the same definition, so a DTD in XML bytes is still refused."""
    source = state_input.parse_state(_document([_entry('x', {'note': '<!DOCTYPE html>'})]), _origin())
    assert source.entries[0].attributes['note'] == '<!DOCTYPE html>', source.entries

    with pytest.raises(xml_input.UnsafeInputError):
        xml_input.reject_dtd(b'<!DOCTYPE config SYSTEM "evil.dtd">\n<config/>', _origin())


# --- 2. The entry shape the scan reads ---------------------------------------

def test_one_entry_is_one_instance_object():
    """AC-1.3: two instances are two entries, and an older document holds the same values in
    `values`."""
    source = state_input.parse_state(_document([
        {'module': 'root', 'type': 'panos_address', 'name': 'two_instances',
         'instances': [{'attributes': {'name': 'A'}}, {'attributes': {'name': 'B'}}]},
        {'module': 'root', 'type': 'panos_address', 'name': 'older_shape', 'values': {'name': 'C'}},
    ]), _origin())
    assert [entry.entry_name for entry in source.entries] == ['A', 'B', 'C'], source.entries


def test_the_position_is_the_resource_address():
    """AC-1.4: the root module names no path, so an entry in it is `type.name`, and a module
    instance is `module.path:type.name`. A state entry has no source line, because only the expat
    handler path records one."""
    source = state_input.parse_state(_document([
        _entry('in_root', {'name': 'A'}),
        _entry('in_module', {'name': 'B'}, module='network'),
    ]), _origin())
    assert source.entries[0].address == 'panos_address.in_root', source.entries[0]
    assert source.entries[1].address == 'network:panos_address.in_module', source.entries[1]
    assert not hasattr(source.entries[0], 'line'), 'the producer records no source line'


def test_the_producer_keeps_both_nested_block_shapes():
    """AC-1.6: the provider writes a nested block as an object or as a one-element list, so the
    producer keeps the bytes as the document states them and the scan reads either shape."""
    object_shape = state_input.parse_state(_document([_entry('x', {'location': {'shared': {}}})]), _origin())
    list_shape = state_input.parse_state(_document([_entry('x', {'location': [{'shared': [{}]}]})]), _origin())
    assert object_shape.entries[0].attributes['location'] == {'shared': {}}, object_shape.entries
    assert list_shape.entries[0].attributes['location'] == [{'shared': [{}]}], list_shape.entries


# --- 3. The document-shape refusals ------------------------------------------

@pytest.mark.parametrize('document, phrase', [
    (b'{"version": 4, "resources": [', 'not JSON'),
    (b'[1, 2, 3]', 'one object, not list'),
    (json.dumps({'version': 4}).encode(), 'holds no `resources` array'),
    (_document(['not an object']), 'item is not an object'),
    (_document([{'module': 'root', 'type': '', 'name': 'x'}]), 'names no type or no name'),
    (_document([{'module': 'root', 'type': 'panos_address', 'name': ''}]), 'names no type or no name'),
])
def test_a_document_the_scan_cannot_key_is_an_input_refusal(document: bytes, phrase: str):
    """AC-1.5: every document-shape refusal is an input refusal, so the CLI exits 1 and writes no
    record."""
    with pytest.raises(xml_input.UnsafeInputError) as refused:
        state_input.parse_state(document, _origin())
    assert phrase in str(refused.value), str(refused.value)


def test_a_refusal_names_the_origin_and_exits_1(tmp_path):
    """The refusal is the door's refusal shape, and an input refusal exits 1 and writes no record."""
    not_a_state = tmp_path / 'not_a_state.json'
    not_a_state.write_text('not json', encoding='utf-8')
    result = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / RUN_FIXTURE),
                        '--state', str(not_a_state), '--output-dir', str(tmp_path))
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'not JSON' in result.stdout, result.stdout
    assert not (tmp_path / provenance.PROVENANCE_FILE).exists(), 'a refusal writes no record'


# --- 4. The record facts -----------------------------------------------------

def test_the_producer_states_the_record_facts(tmp_path):
    """AC-6.1 and AC-6.4: the origin kind is `state`, and the size and the SHA-256 hex are the
    bytes the door checked."""
    source = state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)
    data = _bytes()
    assert source.origin.kind == 'state', source.origin
    assert source.origin.name == STATE_FIXTURE, source.origin
    assert source.origin.path == FIXTURES_DIR / STATE_FIXTURE, source.origin
    assert source.name == STATE_FIXTURE, 'the report value names the source with no directory'
    assert source.size == len(data), source
    assert source.sha256 == hashlib.sha256(data).hexdigest(), source
    assert source.scope == WORKSPACE, 'the scope names the workspace the run declared'

    record = provenance.record_for(source)
    assert record.kind == 'state', record
    assert record.scope == WORKSPACE, record
    assert provenance.parse_record(provenance.render(record)) == record, 'the record shape reads back'


def test_a_state_record_declares_no_workspace_when_the_run_does_not(tmp_path):
    """AC-6.1: the default scope is `xml_input.DEFAULT_SCOPE`, so a run that declares no workspace
    keeps it."""
    source = state_input.read_state(FIXTURES_DIR / STATE_FIXTURE)
    assert source.scope == xml_input.DEFAULT_SCOPE, source
    assert provenance.record_for(source).scope == xml_input.DEFAULT_SCOPE


def test_a_state_record_references_nothing_so_it_prunes_nothing(tmp_path):
    """AC-6.2: a state source has no request and no cache entry, so the record references nothing.
    An entry no record references is still prunable through the F5.3 rule, so the state record
    cannot protect one."""
    record = provenance.record_for(state_input.read_state(FIXTURES_DIR / STATE_FIXTURE))
    assert record.request == provenance.ABSENT, record
    assert record.cache_entry == provenance.ABSENT, record
    assert provenance.cache_reference(record) is None, record
    cache = tmp_path / 'cache'
    cache.mkdir()
    entry = cache / 'an-entry-a'
    entry.write_text('x', encoding='utf-8')
    assert provenance.prunable_entries(cache, [record]) == [entry], 'the state record prunes nothing itself'


# --- 5. CLI argument rules ---------------------------------------------------

def test_the_state_source_applies_to_a_file_run(tmp_path):
    """AC-7.1: the state source is a reference source, so a file run accepts it and the record
    names it last, in read order."""
    code, console = _run(('--workspace', WORKSPACE), tmp_path)
    assert code == 0, console
    record = (tmp_path / provenance.PROVENANCE_FILE).read_text(encoding='utf-8')
    assert 'kind: state' in record, record
    assert f'scope: {WORKSPACE}' in record, record
    assert record.index('kind: state') > record.index('kind: file'), 'the record is in read order'


def test_the_state_source_applies_to_an_api_run(tmp_path):
    """AC-7.1: the reference position is the same one the declared parent holds, so an api run
    reads the state after its source and the record keeps both."""
    cache = tmp_path / 'cache'
    cache.mkdir()
    request = source_fetch.ApiRequest(host='panorama.test', path=container_coverage.record_path('/shared'))
    (cache / request.cache_name()).write_bytes((FIXTURES_DIR / 'scope_parent.xml').read_bytes())
    result = run_script('panorama_to_terraform.py', '--source', 'api', '--host', 'panorama.test',
                        '--path', '/shared', '--offline',
                        '--state', str(FIXTURES_DIR / STATE_FIXTURE),
                        '--cache-dir', str(cache), '--output-dir', str(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr
    records = provenance.parse_records((tmp_path / provenance.PROVENANCE_FILE).read_text(encoding='utf-8'))
    assert [record.kind for record in records] == ['api', 'state'], records
    assert records[0].cache_entry != provenance.ABSENT, 'the api record keeps its cache reference'
    assert records[1].cache_entry == provenance.ABSENT, 'the state record references nothing'


def test_workspace_needs_a_state_document(tmp_path):
    """AC-7.2: `--workspace` applies to the state source only, so it is an argument error."""
    result = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / RUN_FIXTURE),
                        '--workspace', WORKSPACE, '--output-dir', str(tmp_path))
    assert result.returncode == 2, result.stdout + result.stderr
    assert 'needs --state' in result.stderr, result.stderr


def test_a_missing_state_file_is_an_input_refusal(tmp_path):
    """AC-7.1: a state file that is not there is an input refusal, not an argument error."""
    result = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / RUN_FIXTURE),
                        '--state', str(tmp_path / 'absent.tfstate'), '--output-dir', str(tmp_path))
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'cannot read' in result.stdout, result.stdout


def test_an_over_limit_state_file_is_refused_before_the_read(tmp_path):
    """AC-1.1 through the CLI: the size is checked before the read, so an over-limit file is
    never allocated, exactly as the file producer does."""
    result = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / RUN_FIXTURE),
                        '--state', str(FIXTURES_DIR / STATE_FIXTURE),
                        '--max-input-bytes', '10', '--output-dir', str(tmp_path))
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'exceeds the input limit' in result.stdout, result.stdout


# --- 6. The read stays offline -----------------------------------------------

def test_a_state_read_calls_no_producer(converter_module, fetch_module, tmp_path, monkeypatch):
    """AC-5.1 and AC-5.2: a state read is a file read. `--offline` still means the api producer
    reads the cache entry only, and a state read calls no producer even when a producer that
    raises stands in for the network."""
    cache = tmp_path / 'cache'
    cache.mkdir()
    request = fetch_module.ApiRequest(host='panorama.test', path=container_coverage.record_path('/shared'))
    (cache / request.cache_name()).write_bytes((FIXTURES_DIR / 'scope_parent.xml').read_bytes())
    monkeypatch.setattr(fetch_module, 'network_producer',
                        lambda request, key, insecure=False: (_ for _ in ()).throw(
                            AssertionError('a cache hit calls no producer')))

    argv = ['--source', 'api', '--host', 'panorama.test', '--path', '/shared', '--offline',
            '--cache-dir', str(cache), '--output-dir', str(tmp_path),
            '--state', str(FIXTURES_DIR / STATE_FIXTURE), '--workspace', WORKSPACE]
    assert run_main(converter_module, argv) == 0
    records = provenance.parse_records((tmp_path / provenance.PROVENANCE_FILE).read_text(encoding='utf-8'))
    assert [record.kind for record in records] == ['api', 'state'], records
    assert records[1].path == str(FIXTURES_DIR / STATE_FIXTURE), \
        'the state record names a file a reader can reopen'
