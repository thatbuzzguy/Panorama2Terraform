"""Shared test fixtures and module loading.

The two converter scripts live at the repository root and are not an
installed package. Load them by file path so tests run from any directory.
"""

import importlib.util
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


@pytest.fixture
def make_parser(converter_module):
    """Return a factory that builds a PanoramaParser bound to a fixture file."""

    def _make(fixture_name: str):
        return converter_module.PanoramaParser(str(FIXTURES_DIR / fixture_name))

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
