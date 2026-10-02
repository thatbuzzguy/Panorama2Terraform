"""Shared test fixtures and module loading.

The two converter scripts live at the repository root and are not an
installed package. Load them by file path so tests run from any directory.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent
SAMPLE_CONFIG = REPO_ROOT / "sample_panorama_config.xml"


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


def run_script(filename: str, *args: str) -> subprocess.CompletedProcess:
    """Run a repository script as a subprocess. Returns the process result."""
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / filename), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
    )
