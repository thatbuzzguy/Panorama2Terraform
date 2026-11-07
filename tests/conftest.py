"""Shared test fixtures and the layout paths the tests read.

The tool's modules live in `src/` and are not an installed package. The import rule is in
`docs/ARCHITECTURE.md` §1.1: `src/` is one flat namespace, so a test imports a module by plain name, and
`pyproject.toml` `pythonpath = ["src"]` is the only place the path is stated for tests. This file builds the
paths a test reads the layout through, and states no second path rule.
"""

import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import panorama_to_terraform
import sanity_checks
import split_device_groups

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

# Every `resource "panos_x" "y" {` line in a Terraform file.
RESOURCE_RE = re.compile(r'resource\s+"([a-z0-9_]+)"\s+"[^"]+"\s*\{')


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
