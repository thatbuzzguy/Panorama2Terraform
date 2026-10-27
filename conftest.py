"""Shared test fixtures and module loading.

The two converter scripts live at the repository root and are not an
installed package. Load them by file path so tests run from any directory.
"""

import contextlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent
SAMPLE_CONFIG = REPO_ROOT / "sample_panorama_config.xml"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
GOLDEN_DIR = REPO_ROOT / "tests" / "golden"
TERRAFORM = shutil.which("terraform")

# Every `resource "panos_x" "y" {` line in a Terraform file.
RESOURCE_RE = re.compile(r'resource\s+"([a-z0-9_]+)"\s+"[^"]+"\s*\{')


def declared_provider() -> tuple[str, str]:
    """Read the panos provider source and version from the golden provider.tf.

    The golden provider.tf is the single source of truth for which provider
    version the tests verify against (F2.1 pins it).
    """
    text = (GOLDEN_DIR / "sample" / "provider.tf").read_text()
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
def provider_schema(tmp_path_factory) -> dict:
    """The panos provider's resource schemas, keyed by resource type.

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
    return data["provider_schemas"][key]["resource_schemas"]


def _load_module(alias: str, filename: str):
    """Load a root-level script as a module under a stable name."""
    path = REPO_ROOT / filename
    spec = importlib.util.spec_from_file_location(alias, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def converter_module():
    """The panorama_to_terraform script as an importable module."""
    return _load_module("panorama_to_terraform", "panorama_to_terraform.py")


@pytest.fixture(scope="session")
def splitter_module():
    """The split_device_groups script as an importable module."""
    return _load_module("split_device_groups", "split_device_groups.py")


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


def run_script(filename: str, *args: str) -> subprocess.CompletedProcess:
    """Run a repository script as a subprocess. Returns the process result."""
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / filename), *args],
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
