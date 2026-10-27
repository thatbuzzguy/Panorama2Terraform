"""F5.2 the cached API export: the byte producer, the wrapper decision, and the cache.

Six groups, one per acceptance rule:

1. The door. `fetch` hands the producer bytes to `xml_input.parse_bytes` with an
   `api` origin and returns the `ParsedSource` contract. It keeps no second copy of
   the two checks, and it builds no device-object model.
2. The wrapper decision. The tree root becomes the `config` element under `result`,
   through the same origin and the same line map. A failed response is refused before
   the cache entry is written. The container table names no wrapper row.
3. The cache. The entry name is the request identity without the key. A miss calls the
   producer once and caches only the bytes that passed the door and the response
   check; a hit parses the cache bytes with no producer. Two runs on the same cache
   bytes write identical bytes.
4. Offline. `--offline` reads the cache only, refuses a missing entry, and needs no
   key to reopen cached bytes.
5. The https rules and the key rule. https only, a scheme-changing redirect is
   refused, verification is on by default, `--insecure` is explicit, and the key
   reaches the request URL and nothing else.
6. CLI and gate. `PanoramaParser` takes the contract, an api run writes the same
   `.tf` bytes as the file run of the same content, a fetch refusal exits 1 and
   writes no output, and the module imports the standard library only.

No test calls the network: every fetch uses an injected fixture-backed producer, or
the default producer is monkeypatched to stand in for one.
"""

import ast
import dataclasses
import re
import urllib.request

import pytest

import container_coverage
from conftest import FIXTURES_DIR, REPO_ROOT, run_main, run_pipeline, run_script

FETCH_FIXTURE = 'api_response.xml'

# Physical lines of the fixture: prolog 1, response 2, result 3, config 4,
# device-group 5, entry Edge 6, address 7, entry web-server 8.
CONFIG_LINE = 4
ENTRY_LINE = 8


def _bytes():
    return (FIXTURES_DIR / FETCH_FIXTURE).read_bytes()


def _request(fetch_module, host='panorama.test'):
    return fetch_module.ApiRequest(host=host)


def _producer(fetch_module, data):
    """The fixture-backed producer: hands bytes, never opens the network."""
    return lambda request: data


# --- 1. The door ------------------------------------------------------------

def test_fetch_hands_producer_bytes_to_the_door(fetch_module, tmp_path, monkeypatch):
    """No producer keeps its own check: fetch hands its bytes to parse_bytes."""
    data = _bytes()
    request = _request(fetch_module)
    calls = []
    real = fetch_module.parse_bytes

    def recording(handed, origin, limit):
        calls.append((len(handed), origin.kind, origin.name))
        return real(handed, origin, limit)

    monkeypatch.setattr(fetch_module, 'parse_bytes', recording)
    source = fetch_module.fetch(request, tmp_path, producer=_producer(fetch_module, data))
    assert calls == [(len(data), 'api', request.cache_name())], calls
    assert source.origin.kind == 'api'
    assert source.origin.name == request.cache_name()
    assert source.origin.path == tmp_path / request.cache_name()
    assert source.name == request.cache_name(), 'the report value names bytes a reader can reopen'


def test_fetch_refuses_producer_bytes_through_the_door_and_writes_no_entry(fetch_module, tmp_path):
    """The size refusal and the DTD refusal run on the bytes as they arrived, and a
    refused input never reaches the cache."""
    request = _request(fetch_module)
    data = _bytes()

    with pytest.raises(fetch_module.UnsafeInputError) as size:
        fetch_module.fetch(request, tmp_path, producer=_producer(fetch_module, data),
                           max_input_bytes=16)
    assert request.cache_name() in str(size.value), 'the refusal names the cache entry'
    assert 'larger than the limit' in str(size.value)

    dtd = b'<?xml version="1.0"?>\n<!DOCTYPE config>\n' + data.split(b'\n', 1)[1]
    with pytest.raises(fetch_module.UnsafeInputError) as scanned:
        fetch_module.fetch(request, tmp_path, producer=_producer(fetch_module, dtd))
    assert 'declares a DTD' in str(scanned.value)

    assert not (tmp_path / request.cache_name()).exists(), 'no cache entry for refused bytes'


def test_fetch_returns_the_contract_not_a_model(fetch_module, tmp_path):
    """fetch returns origin, tree, and line map; it builds no device-object model."""
    source = fetch_module.fetch(_request(fetch_module), tmp_path,
                                producer=_producer(fetch_module, _bytes()))
    assert isinstance(source, fetch_module.ParsedSource)
    assert hasattr(source.root, 'tag'), 'the tree is the ElementTree tree'
    assert callable(source.line_of)


# --- 2. The wrapper decision --------------------------------------------------

def test_fetch_root_is_the_config_element_under_result(fetch_module, tmp_path):
    """The root moves to the config element, and the line map survives unwrapping."""
    data = _bytes()
    request = _request(fetch_module)
    parsed = fetch_module.fetch(request, tmp_path, producer=_producer(fetch_module, data))
    assert parsed.root.tag == 'config'
    entry = parsed.root.find(".//entry[@name='web-server']")
    assert parsed.line_of(parsed.root) == CONFIG_LINE
    assert parsed.line_of(entry) == ENTRY_LINE, 'a report line names the line the response carries'
    scope = parsed.root.find(".//entry[@name='Edge']")
    assert parsed.line_of(scope) == 6

    # The unwrap is not a reparse: it takes the parsed source and hands back the
    # same origin and the same line map, with a different root.
    direct = fetch_module.parse_bytes(data, fetch_module.SourceOrigin(
        kind='api', name=request.cache_name(), path=tmp_path / request.cache_name()))
    unwrapped = fetch_module.unwrap_config_root(direct)
    assert unwrapped.origin is direct.origin
    assert unwrapped.lines is direct.lines, 'the same line map, not a copy'
    assert unwrapped.root is direct.root.find('result').find('config')
    assert unwrapped.line_of(unwrapped.root) == direct.line_of(direct.root.find('result').find('config'))


def test_result_root_and_plain_config_root_are_accepted(fetch_module, tmp_path):
    """The three shapes: response/result/config, result/config, and a plain config root.

    Each shape gets its own cache directory, so no shape is confused with a cached
    response of another shape.
    """
    result_only = b'<?xml version="1.0"?>\n<result>\n<config>\n<device-group/>\n</config>\n</result>\n'
    source = fetch_module.fetch(_request(fetch_module), tmp_path / 'a',
                                producer=_producer(fetch_module, result_only))
    assert source.root.tag == 'config'
    assert source.line_of(source.root) == 3

    plain = b'<?xml version="1.0"?>\n<config>\n<device-group/>\n</config>\n'
    source = fetch_module.fetch(_request(fetch_module), tmp_path / 'b',
                                producer=_producer(fetch_module, plain))
    assert source.root.tag == 'config'
    assert source.line_of(source.root) == 2


def test_failed_response_is_refused_before_the_cache_entry_is_written(fetch_module, tmp_path):
    """A response that is not success code 0 is refused, and the entry is not written."""
    failed = (b'<?xml version="1.0"?>\n<response type="error" code="14">\n'
              b'<result><config><device-group/></config></result>\n</response>\n')
    request = _request(fetch_module)
    with pytest.raises(fetch_module.SourceFetchError) as excinfo:
        fetch_module.fetch(request, tmp_path, producer=_producer(fetch_module, failed))
    message = str(excinfo.value)
    assert "type 'error' code '14'" in message, 'the refusal names the type and the code'
    assert request.cache_name() in message
    assert not (tmp_path / request.cache_name()).exists(), 'no cache entry for a refused response'


def test_result_without_a_config_element_is_refused(fetch_module, tmp_path):
    """A result that holds no config element is the per-scope shape F5.4 owns."""
    scoped = (b'<?xml version="1.0"?>\n<response type="success" code="0">\n'
              b'<result><device-group name="Edge"><entry name="Edge"/></device-group></result>\n</response>\n')
    with pytest.raises(fetch_module.SourceFetchError) as excinfo:
        fetch_module.fetch(_request(fetch_module), tmp_path,
                           producer=_producer(fetch_module, scoped))
    assert 'no config element' in str(excinfo.value)
    assert 'F5.4' in str(excinfo.value)


def test_container_table_names_no_wrapper_row():
    """The wrapper sits above the config root, so the table never scans it and
    needs no row for it."""
    assert not any('response' in row.path or 'result' in row.path
                   for row in container_coverage.CONTAINER_TABLE)
    assert not {'response', 'result'} & container_coverage.PATH_ROOTS


# --- 3. The cache ---------------------------------------------------------------

def test_cache_miss_then_hit_reopens_the_same_bytes(fetch_module, tmp_path):
    """The entry holds exactly the bytes the door parsed, and a hit calls no producer."""
    data = _bytes()
    request = _request(fetch_module)
    first = fetch_module.fetch(request, tmp_path, producer=_producer(fetch_module, data))
    entry = tmp_path / request.cache_name()
    assert entry.read_bytes() == data, 'the cache entry is what gets parsed'

    def no_call(request):
        raise AssertionError('a cache hit must not call the producer')

    second = fetch_module.fetch(request, tmp_path, producer=no_call)
    assert second.origin == first.origin
    assert second.line_of(second.root) == first.line_of(first.root)
    assert second.root.tag == first.root.tag


def test_cache_entry_name_is_the_request_identity_without_the_key(fetch_module):
    """The identity is host and sorted params. The credential is not part of it, so
    no cache name can carry it, and two different keys find the same entry."""
    request = _request(fetch_module)
    fields = {f.name for f in dataclasses.fields(request)}
    assert 'key' not in fields, 'the request holds no key'
    assert 'key' not in request.canonical()
    assert 'key' not in request.cache_name()
    assert 'key=' in request.url('SECRET-KEY-9f3'), 'the key reaches the request URL'
    assert request.cache_name().endswith('.xml')

    # A different key is the same identity.
    same = fetch_module.ApiRequest(host='panorama.test')
    assert same.cache_name() == request.cache_name()
    other = fetch_module.ApiRequest(host='panorama.test', params=(('type', 'export'),))
    assert other.cache_name() != request.cache_name(), 'a different request is a different entry'


def test_cache_hit_over_the_limit_is_refused_through_the_door(fetch_module, tmp_path):
    """A cache read keeps the size cap, and the refusal names the entry."""
    data = _bytes()
    request = _request(fetch_module)
    fetch_module.fetch(request, tmp_path, producer=_producer(fetch_module, data))
    with pytest.raises(fetch_module.UnsafeInputError) as excinfo:
        fetch_module.fetch(request, tmp_path,
                           producer=lambda r: (_ for _ in ()).throw(AssertionError('the door must decide')),
                           max_input_bytes=16)
    assert request.cache_name() in str(excinfo.value)


# --- 4. Offline ---------------------------------------------------------------

def test_offline_refuses_a_missing_entry_and_calls_no_producer(fetch_module, tmp_path):
    """--offline reads the cache only; the refusal names the entry it looked for."""
    request = _request(fetch_module)

    def no_call(request):
        raise AssertionError('the offline path must not call the producer')

    with pytest.raises(fetch_module.SourceFetchError) as excinfo:
        fetch_module.fetch(request, tmp_path, producer=no_call, offline=True)
    assert request.cache_name() in str(excinfo.value)
    assert '--offline reads the cache only' in str(excinfo.value)


def test_offline_reopens_an_entry_with_no_key(fetch_module, tmp_path, monkeypatch):
    """No credential is needed to reopen cached bytes."""
    monkeypatch.delenv(fetch_module.API_KEY_ENV, raising=False)
    data = _bytes()
    request = _request(fetch_module)
    fetch_module.fetch(request, tmp_path, producer=_producer(fetch_module, data))
    source = fetch_module.fetch(request, tmp_path,
                                producer=lambda r: (_ for _ in ()).throw(AssertionError('no producer')),
                                offline=True)
    assert source.root.tag == 'config'
    assert source.origin.kind == 'api'


# --- 5. The https rules and the key rule ---------------------------------------

def test_the_producer_accepts_https_only(fetch_module):
    """A bare host is read as https; any other scheme is refused before the fetch,
    so the rule holds for a cache hit too."""
    assert fetch_module.ApiRequest(host='panorama.test').https_host() == 'panorama.test'
    assert fetch_module.ApiRequest(host='https://panorama.test/api').https_host() == 'panorama.test'
    with pytest.raises(fetch_module.SourceFetchError) as excinfo:
        fetch_module.ApiRequest(host='http://panorama.test').https_host()
    assert "scheme 'http'" in str(excinfo.value)


def test_a_redirect_that_changes_the_scheme_is_refused(fetch_module):
    handler = fetch_module._SameSchemeRedirectHandler()
    request = urllib.request.Request('https://panorama.test/api/?type=export')
    with pytest.raises(fetch_module.SourceFetchError) as excinfo:
        handler.redirect_request(request, None, 301, None, {}, 'http://panorama.test/api/')
    assert 'changes the scheme' in str(excinfo.value)
    kept = handler.redirect_request(request, None, 302, None, {}, 'https://panorama.test/api2/')
    assert kept is not None and kept.full_url.startswith('https://'), 'same scheme may be followed'


def test_verification_is_on_by_default_and_insecure_is_explicit(fetch_module):
    """--insecure is the only way off, and it is a flag, not a default."""
    assert fetch_module._ssl_context(False).check_hostname, 'verification on by default'
    assert not fetch_module._ssl_context(True).check_hostname, '--insecure is the explicit opt-out'


def test_the_key_never_reaches_the_cache_name_or_the_output(fetch_module, converter_module, tmp_path, monkeypatch):
    """The key reaches the request URL and nothing else."""
    monkeypatch.setenv(fetch_module.API_KEY_ENV, 'SECRET-KEY-9f3')
    request = _request(fetch_module)
    cache = tmp_path / 'cache'
    out_dir = tmp_path / 'out'

    # The default producer stands in for the network inside the process.
    monkeypatch.setattr(fetch_module, 'network_producer',
                        lambda req, key, insecure=False: _bytes())
    exit_code = run_main(converter_module, ['--source', 'api', '--host', 'panorama.test',
                                            '--cache-dir', cache, '--output-dir', out_dir])
    assert exit_code == 0

    entry = cache / request.cache_name()
    assert entry.is_file()
    assert 'SECRET-KEY-9f3' not in entry.name
    assert b'SECRET-KEY-9f3' not in entry.read_bytes()
    for path in out_dir.rglob('*'):
        assert b'SECRET-KEY-9f3' not in path.read_bytes(), f'the key reached {path.name}'

    help_text = run_script('panorama_to_terraform.py', '--help').stdout
    assert '--key' not in help_text, 'the key comes from the environment, never from argv'


# --- 6. CLI and gate ----------------------------------------------------------

def test_parser_consumes_the_producer_contract(fetch_module, converter_module, tmp_path):
    """PanoramaParser takes the contract, not a path: the same shape for every source."""
    source = fetch_module.fetch(_request(fetch_module), tmp_path,
                                producer=_producer(fetch_module, _bytes()))
    parser = converter_module.PanoramaParser(source)
    assert parser.source is source
    addresses = parser.parse_address_objects()
    assert [a['name'] for a in addresses] == ['web-server']
    assert parser.line_of(
        next(e for e in source.root.iter() if e.get('name') == 'web-server')) == ENTRY_LINE


def test_api_run_writes_the_same_tf_bytes_as_the_file_run(converter_module, fetch_module, tmp_path, monkeypatch):
    """The wrapper decision and the cache do not change the model: the same content
    writes the same .tf bytes from either source."""
    monkeypatch.setenv(fetch_module.API_KEY_ENV, 'test-key')
    monkeypatch.setattr(fetch_module, 'network_producer',
                        lambda req, key, insecure=False: _bytes())
    out_api = tmp_path / 'api_out'
    assert run_main(converter_module, ['--source', 'api', '--host', 'panorama.test',
                                       '--cache-dir', tmp_path / 'cache',
                                       '--output-dir', out_api]) == 0

    out_file = tmp_path / 'file_out'
    run_pipeline(converter_module, FETCH_FIXTURE, out_file)

    api_tf = {p.name: p.read_bytes() for p in sorted(out_api.glob('*.tf'))}
    file_tf = {p.name: p.read_bytes() for p in sorted(out_file.glob('*.tf'))}
    assert api_tf == file_tf, 'the model and the naming are unchanged by the source'
    assert api_tf, 'the fixture emits a .tf file, so the comparison is not empty'


def test_two_runs_on_the_same_cache_bytes_write_identical_bytes(converter_module, fetch_module, tmp_path, monkeypatch):
    """Report determinism for a fetched source: the second run is offline and the
    whole output repeats byte for byte, including the report and the gate files."""
    monkeypatch.setenv(fetch_module.API_KEY_ENV, 'test-key')
    monkeypatch.setattr(fetch_module, 'network_producer',
                        lambda req, key, insecure=False: _bytes())
    cache = tmp_path / 'cache'
    out1 = tmp_path / 'run1'
    out2 = tmp_path / 'run2'
    cache_name = _request(fetch_module).cache_name()

    assert run_main(converter_module, ['--source', 'api', '--host', 'panorama.test',
                                       '--cache-dir', cache, '--output-dir', out1]) == 0

    # The second run has no producer: the stand-in is replaced by one that fails the
    # test if called, so the run proves it read the cache.
    monkeypatch.setattr(fetch_module, 'network_producer',
                        lambda req, key, insecure=False: (_ for _ in ()).throw(
                            AssertionError('offline run called the producer')))
    assert run_main(converter_module, ['--source', 'api', '--host', 'panorama.test',
                                       '--cache-dir', cache, '--offline',
                                       '--output-dir', out2]) == 0

    files1 = {p.name: p.read_bytes() for p in sorted(out1.rglob('*')) if p.is_file()}
    files2 = {p.name: p.read_bytes() for p in sorted(out2.rglob('*')) if p.is_file()}
    assert files1 == files2, 'the same cache bytes produce the same bytes'
    report = files2['CONVERSION_REPORT.txt'].decode('utf-8')
    assert f'Input file: {cache_name}' in report, 'the report names the cache entry'
    # The report row keeps the line the response bytes carry, so the report can
    # point back into the cache entry.
    assert re.search(rf'{ENTRY_LINE}\s+device-group/entry/address/web-server', report), report


def test_fetch_refusal_exits_1_and_writes_no_output(fetch_module, tmp_path):
    """A fetch refusal is an input refusal: it names the entry, exits 1, and writes
    no output file."""
    request = _request(fetch_module)
    cache = tmp_path / 'cache'
    out_dir = tmp_path / 'out'
    result = run_script('panorama_to_terraform.py', '--source', 'api', '--host', 'panorama.test',
                        '--cache-dir', str(cache), '--offline', '--output-dir', str(out_dir))
    assert result.returncode == 1
    assert request.cache_name() in result.stdout
    assert '--offline reads the cache only' in result.stdout
    assert not out_dir.exists() or not [p for p in out_dir.rglob('*') if p.is_file()], \
        'a refusal writes no output'


def test_cli_source_validation_errors(fetch_module):
    """--source api needs --host, --insecure never pairs with --offline, the api
    source takes no input file, and the network arguments do not apply to a file
    source. These are argument errors (exit 2), not conversion runs."""
    result = run_script('panorama_to_terraform.py', '--source', 'api',
                        '--output-dir', '/tmp/not-run')
    assert result.returncode == 2 and '--host' in result.stderr

    result = run_script('panorama_to_terraform.py', '--source', 'api', '--host', 'panorama.test',
                        '--insecure', '--offline', '--output-dir', '/tmp/not-run')
    assert result.returncode == 2 and '--insecure' in result.stderr

    result = run_script('panorama_to_terraform.py', '--source', 'api', '--host', 'panorama.test',
                        str(FIXTURES_DIR / FETCH_FIXTURE), '--output-dir', '/tmp/not-run')
    assert result.returncode == 2 and 'does not take an input file' in result.stderr

    result = run_script('panorama_to_terraform.py', '--output-dir', '/tmp/not-run')
    assert result.returncode == 2 and 'input file' in result.stderr

    # A file source reads no network, so the network arguments cannot be given to it.
    result = run_script('panorama_to_terraform.py', str(FIXTURES_DIR / FETCH_FIXTURE),
                        '--offline', '--output-dir', '/tmp/not-run')
    assert result.returncode == 2 and '--source api' in result.stderr


def test_source_fetch_imports_are_standard_library(fetch_module):
    """The fetch layer keeps the F3.8 decision: no dependency, no SDK import. The
    planned pan-os-python producer was dropped because the SDK cannot enforce the
    redirect rule (see backlog.md), so nothing in the project imports a third-party
    module."""
    tree = ast.parse((REPO_ROOT / 'source_fetch.py').read_text(encoding='utf-8'))
    top_level = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == 'xml_input':
                continue  # the shared door is the local module, not a dependency
            top_level.add(node.module.split('.')[0])
        elif isinstance(node, ast.Import):
            top_level.add(node.names[0].name.split('.')[0])
    allowed = {'hashlib', 'os', 'ssl', 'urllib', 'dataclasses', 'pathlib', 'typing'}
    assert top_level <= allowed, top_level - allowed
    source = (REPO_ROOT / 'source_fetch.py').read_text(encoding='utf-8')
    assert 'import panos' not in source and 'requests' not in source
    assert fetch_module.SOURCE_KIND == 'api'
