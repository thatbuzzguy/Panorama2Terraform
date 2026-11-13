"""Shared test fixtures and the definitions the tests read.

The tool's modules live in `src/` and are not an installed package. The import rule is in
`docs/ARCHITECTURE.md` §1.1: `src/` is one flat namespace, so a test imports a module by plain name, and
`pyproject.toml` `pythonpath = ["src"]` is the only place the path is stated for tests. This file builds the
paths a test reads the layout through, states no second path rule, and holds the definitions more than one
test module reads: the terraform binary, the two resource-line patterns, and the rule-block parser. A test
module does not define its own copy of any of them, and no test module imports another test module.
"""

import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import api_requests
import panorama_to_terraform
import sanity_checks
import source_fetch
import split_device_groups
import xml_input

TESTS_DIR = Path(__file__).parent
REPO_ROOT = TESTS_DIR.parent
SRC_DIR = REPO_ROOT / "src"
TOOLS_DIR = REPO_ROOT / "tools"
EXAMPLES_DIR = REPO_ROOT / "examples"
SAMPLE_CONFIG = EXAMPLES_DIR / "sample_panorama_config.xml"
FIXTURES_DIR = TESTS_DIR / "fixtures"
GOLDEN_DIR = TESTS_DIR / "golden"
# The committed API responses (F8.4). A response is not a Panorama export, so the scan and the fixture
# assembler never read it: `FIXTURES_DIR` is the corpus, and this is a separate set (§1.1).
RESPONSES_DIR = TESTS_DIR / "responses"
TERRAFORM = shutil.which("terraform")

# Every `resource "panos_x" "y" {` line in a Terraform file, read through this file by the test set.
# Two named patterns, each with the rule it serves. `RESOURCE_RE` answers the resource type, which the pins
# that read the emitted type set read. `RESOURCE_ADDRESS_RE` answers the same line with the local name
# captured, for `tests/test_dependency_wiring.py`, which reads `findall` as (type, local name) pairs, so a
# one-group pattern cannot serve it. Both require the block brace, so neither pattern is broader than the
# other, and no pin passes because a merged pattern is wider. Measured 2026-11-13 on the committed goldens
# (87 `.tf` files) and the output of a corpus run (584 `.tf` files): the three shapes the test set held
# before answer the same 414 matches, and 0 resource lines lack the trailing brace, so the brace changes
# nothing on the measured material; the real difference is the capture groups (42 distinct types, 262
# distinct addresses). The decision is recorded in `acceptance.md`.
RESOURCE_RE = re.compile(r'resource\s+"([a-z0-9_]+)"\s+"[^"]+"\s*\{')
RESOURCE_ADDRESS_RE = re.compile(r'resource\s+"([a-z0-9_]+)"\s+"([^"]+)"\s*\{')


def tf_files(output_dir) -> dict[str, str]:
    """The `.tf` files a run wrote, keyed by the path from the output directory.

    F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): the run writes one directory per unit, so a test reads the
    file set the way the gate reads it, through `sanity_checks.read_tf_files`. A test that names a file
    names the path, because a per-unit file names its unit only by its directory.
    """
    return sanity_checks.read_tf_files(Path(output_dir))


def parts(files: dict[str, str], name: str) -> dict[str, str]:
    """The parts of one file name across the unit set, keyed by the path the reader names (F6.10.3, §14).

    A per-unit file names its unit only by its directory, so one file shape holds one part per unit. A test
    that pins one file for one unit reads the part; a test that pins the shape across the run reads the
    parts in path order.
    """
    return {key: files[key] for key in sorted(files) if Path(key).name == name}


def file_text(files: dict[str, str], name: str) -> str:
    """The text one file name holds across the unit set, with the parts in path order.

    A test that pins one emitter's whole file reads the parts the run wrote for every unit, so the same pin
    holds for a file set the run wrote one file per unit. `name` is the file name, not a path.
    """
    return ''.join(parts(files, name).values())


def written_bytes(output_dir) -> dict[str, bytes]:
    """The bytes a run wrote, keyed by the path from the output directory (F6.10.3, §14).

    The run writes the root set at the root and the unit set inside one directory per unit, so a test that
    pins two runs writing the same bytes compares the whole layout, not only the files at the root.
    """
    out = Path(output_dir)
    return {str(path.relative_to(out)): path.read_bytes() for path in sorted(out.rglob('*')) if path.is_file()}


def tf_bytes(output_dir) -> dict[str, bytes]:
    """The `.tf` bytes a directory holds, keyed by the path from that directory (F6.10.3, §14).

    A golden case is the output of one run, so the `.tf` set sits inside the unit directories and not at the
    case root: a read of `glob('*.tf')` at the case root answers nothing, and a pin built on it compares two
    empty sets. Keyed by the file name, two units that write the same file name collapse, so the key is the
    path. This is the shape `tests/test_golden_files.py` reads. A pin that compares two directories through it
    states that both sets are not empty, so the pin measures content.
    """
    return {key: value for key, value in written_bytes(output_dir).items() if Path(key).suffix == '.tf'}


# --- The corpus read rule the corpus pins read (F3.8, F3.9) ---------------------

def input_refusal(path) -> str | None:
    """What the tool's input rule answers for one committed fixture: the refusal reason, or None when it accepts.

    The rule is `xml_input.check_bytes`, then the parse, read on the committed bytes. This is the one place the
    test set decides which fixtures a corpus pin reads, so the exclusion is the tool's read rule and not a file
    name. `tools/build_kitchen_sink.py` states the same rule for the same reason, and
    `tests/test_build_kitchen_sink.py` pins that the two agree on the committed corpus. A fixture this answers
    None for cannot fail the parse, so a pin that reads it needs no guard.
    """
    try:
        xml_input.parse_xml(path)
    except xml_input.UnsafeInputError as exc:
        return str(exc)
    except ET.ParseError as exc:
        return f'the parse cannot read it: {exc}'
    return None


def corpus_fixtures() -> list[str]:
    """The fixture names a corpus pin reads: the committed corpus, less the fixtures the read rule refuses.

    Names, in the order the corpus pins read them, so a pin's failure message names the fixture. The rule is
    `input_refusal`; a fixture name is not a rule.
    """
    return [path.name for path in sorted(FIXTURES_DIR.glob('*.xml')) if input_refusal(path) is None]


def declared_provider() -> tuple[str, str]:
    """Read the panos provider source and version from the golden provider.tf.

    The golden provider.tf is the single source of truth for which provider
    version the tests verify against (F2.1 pins it). F6.10.3: `provider.tf` is a unit-set file, so a
    golden case holds one per unit, and each states the same provider block, so any one gives the version.
    """
    path = sorted((GOLDEN_DIR / "sample").rglob("provider.tf"))[0]
    text = path.read_text()
    block = re.search(r"panos\s*=\s*\{([^}]*)\}", text, re.S).group(1)
    source = re.search(r'source\s*=\s*"([^"]+)"', block).group(1)
    version = re.search(r'version\s*=\s*"([^"]+)"', block).group(1)
    return source, version


def emitted_types() -> set[str]:
    """The set of panos resource types emitted across the committed goldens."""
    types: set[str] = set()
    for path in sorted(GOLDEN_DIR.rglob("*.tf")):
        for m in RESOURCE_RE.finditer(path.read_text()):
            types.add(m.group(1))
    return types


# --- The rule-block parser the policy pins read (F2.5) ------------------------

# `tests/test_policy_order.py` and `tests/test_real_or_report.py` both read these three functions, so they
# live in the one shared helper file (§1.1) and neither module defines its own copy. The generated format
# is fixed, so small structural regexes are enough: a resource block ends at the first newline followed by
# a column-0 brace.

def _search_one(body: str, pattern: str):
    m = re.search(pattern, body, re.S)
    return m.group(1) if m else None


def rule_blocks(text: str, resource_type: str) -> list[dict]:
    """Parse generated rule resources into ordered dicts (file order)."""
    blocks = []
    pattern = re.compile(
        'resource "' + re.escape(resource_type) + r'" "([^"]+)" \{(.*?)\n\}', re.S)
    for m in pattern.finditer(text):
        local, body = m.group(1), m.group(2)
        # The rules list holds one object per rule; the Panorama rule name
        # is the only name = line inside it (the location block is outside).
        rules_body = _search_one(body, r'rules = \[(.*?)\n  \]') or ''
        rule_names = re.findall(r'name = "([^"]+)"', rules_body)
        depends_on = _search_one(body, r'depends_on = \[([^\]]*)\]') or ''
        blocks.append({
            'local': local,
            'device_group': _search_one(body, r'device_group = \{\s*name = "([^"]+)"'),
            'where': _search_one(body, r'where = "([^"]+)"'),
            'directly': _search_one(body, r'directly = (true|false)'),
            'pivot': _search_one(body, r'pivot = "([^"]+)"'),
            'depends_on': re.findall(r'([A-Za-z_][\w]*\.[A-Za-z_][\w]*)', depends_on),
            'names': rule_names,
        })
    return blocks


def check_chain_semantics(blocks: list[dict], resource_type: str,
                          expected: list[tuple[str, list[str]]], msg: str):
    """Assert blocks form per-DG chains with anchor + after-previous positions."""
    assert len(blocks) == sum(len(names) for _, names in expected), msg
    idx = 0
    for dg, names in expected:
        chain = blocks[idx:idx + len(names)]
        idx += len(names)
        for b in chain:
            assert b['device_group'] == dg, msg
        # Every block holds exactly one rule; the rule name sequence is the
        # chain's XML order.
        assert [b['names'] for b in chain] == [[n] for n in names], msg
        # First rule of the chain: anchor at the end of the rulebase.
        first = chain[0]
        assert first['where'] == 'last', msg
        assert first['pivot'] is None, msg
        assert first['directly'] is None, msg
        assert first['depends_on'] == [], msg
        # Later rules: directly after the previous rule, applied after it.
        for prev, cur in zip(chain, chain[1:]):
            assert cur['where'] == 'after', msg
            assert cur['directly'] == 'true', msg
            assert cur['pivot'] == prev['names'][0], msg
            expected_dep = f'{resource_type}.{prev["local"]}'
            assert cur['depends_on'] == [expected_dep], msg


@pytest.fixture(scope="session")
def provider_schemas(tmp_path_factory) -> dict:
    """The panos provider schema block for one type block: both kinds.

    Runs `terraform init` + `terraform providers schema -json` against the
    provider version declared in the golden provider.tf. Skips when the
    terraform binary or registry access is unavailable.
    """
    if TERRAFORM is None:
        pytest.skip("terraform binary not found (F1.5 makes it mandatory in CI)")
    source, version = declared_provider()
    workdir = tmp_path_factory.mktemp("panos_provider")
    (workdir / "provider.tf").write_text(
        "terraform {\n"
        "  required_providers {\n"
        '    panos = {\n'
        f'      source  = "{source}"\n'
        f'      version = "{version}"\n'
        "    }\n"
        "  }\n"
        "}\n"
    )
    init = subprocess.run(
        [TERRAFORM, "init", "-backend=false", "-input=false"],
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if init.returncode != 0:
        pytest.skip(f"terraform init failed (no registry access?): {init.stderr[-400:]}")
    schema = subprocess.run(
        [TERRAFORM, "providers", "schema", "-json"],
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert schema.returncode == 0, schema.stderr
    data = json.loads(schema.stdout)
    key = next(k for k in data["provider_schemas"] if k.endswith("/panos"))
    return data["provider_schemas"][key]


@pytest.fixture(scope="session")
def provider_schema(provider_schemas) -> dict:
    """The panos provider's resource schemas, keyed by resource type."""
    return provider_schemas["resource_schemas"]


@pytest.fixture(scope="session")
def provider_data_schemas(provider_schemas) -> dict:
    """The panos provider's data source schemas, keyed by data source type (F5.5)."""
    return provider_schemas["data_source_schemas"]


@pytest.fixture(scope="session")
def converter_module():
    """The converter module in the `src/` namespace, read through the import rule (§1.1)."""
    return panorama_to_terraform


@pytest.fixture(scope="session")
def splitter_module():
    """The splitter module in the `src/` namespace, read through the import rule (§1.1)."""
    return split_device_groups


@pytest.fixture(scope="session")
def xml_input_module(converter_module):
    """The shared safe-input module (F3.8) both entry points import.

    Returned after the converter loads, so the module object is the one the
    scripts hold: a test and a script then share one UnsafeInputError class.
    """
    return sys.modules["xml_input"]


@pytest.fixture(scope="session")
def fetch_module(xml_input_module):
    """The F5.2 fetch module as the converter holds it.

    The same module object, so a test and the script share one
    SourceFetchError class and the same parse_bytes reference the door is.
    """
    return sys.modules["source_fetch"]


@pytest.fixture
def make_parser(converter_module, xml_input_module):
    """Return a factory that builds a PanoramaParser bound to a fixture file.

    F5.2: the parser takes a ParsedSource, so the factory reads the fixture
    through the door and hands the contract, not a path.
    """

    def _make(fixture_name: str):
        return converter_module.PanoramaParser(
            xml_input_module.parse_xml(FIXTURES_DIR / fixture_name))

    return _make


def api_producer(request, key=None, insecure=False):
    """The committed response for one request, handed by the name `RESPONSES_DIR` holds it under (§1.1).

    A path 2 pin runs the pipeline in process with this producer, so no test calls a network. A request with
    no committed response answers None, so a run reads only the committed set, and the join reads the set the
    run read.
    """
    entry = RESPONSES_DIR / request.cache_name()
    return None if not entry.is_file() else entry.read_bytes()


def path2_run(output_dir, cache_dir, monkeypatch, host: str = 'panorama.test') -> tuple:
    """A path 2 run, and the index the join reads for it.

    A path 2 pin cannot use `run_script`, because the injected producer lives in this process, so the run is
    in process and the index is built the way the run order builds it: the tables `parse_associations`
    returned for the response the run read, and the read set the join states.
    """
    monkeypatch.setattr(source_fetch, 'network_producer', api_producer)
    monkeypatch.setenv(source_fetch.API_KEY_ENV, 'test-key')
    parser = run_pipeline(panorama_to_terraform, None, output_dir,
                          ('--source', 'api', '--host', host, '--cache-dir', str(cache_dir)))
    assert parser is not None, 'the run refused the input'
    return parser, api_requests.scope_index(host, parser.parse_associations(), api_requests.membership_lists())


def run_script(module_name, *args: str) -> subprocess.CompletedProcess:
    """Run a tool module as a subprocess. Returns the process result.

    `module_name` is a module name in the `src/` namespace (`docs/ARCHITECTURE.md` §1.1), so the path is
    built once here and every test names the module, not the directory. A path is used as given.
    """
    path = Path(module_name)
    if not path.is_absolute():
        path = SRC_DIR / path
    return subprocess.run(
        [sys.executable, str(path), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
    )


def run_main(module, argv: list):
    """Run the converter main() in process with the given argv. Returns the exit code.

    F5.2 tests need an in-process run so an injected producer can stand in for the
    network. Console output is redirected, so an in-process run does not fill the
    pytest report.
    """
    saved_argv = list(sys.argv)
    sys.argv = ['panorama_to_terraform.py', *[str(a) for a in argv]]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return module.main()
    finally:
        sys.argv = saved_argv


def run_pipeline(module, fixture_name, output_dir, extra_args: tuple = ()):
    """Run the converter pipeline in process and return the parser it built.

    The F4.4 property scan measures which keys an output reads from a captured object,
    so a test that wants the read record must run the pipeline in process: `run_script`
    runs a subprocess and the record is lost with the process. `main()` builds the
    parser itself, so this helper hooks `PanoramaParser.__init__` to get the instance
    back.

    `extra_args` is appended to argv (F5.4), so a run can declare a source, a host, or a
    scope path. `fixture_name` is None when argv names the source instead of a file.

    Returns None when the run refuses the input before the parse, because no parser
    exists to return. Console output is redirected, so a corpus run does not fill the
    pytest report.
    """
    captured = {}
    original_init = module.PanoramaParser.__init__

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        captured['parser'] = self

    argv = ['panorama_to_terraform.py']
    if fixture_name:
        argv.append(str(FIXTURES_DIR / fixture_name))
    argv.extend(['--output-dir', str(output_dir)])
    argv.extend(str(arg) for arg in extra_args)

    saved_argv = list(sys.argv)
    module.PanoramaParser.__init__ = init
    try:
        sys.argv = argv
        with contextlib.redirect_stdout(io.StringIO()), contextlib.suppress(SystemExit):
            module.main()
    finally:
        module.PanoramaParser.__init__ = original_init
        sys.argv = saved_argv
    return captured.get('parser')
