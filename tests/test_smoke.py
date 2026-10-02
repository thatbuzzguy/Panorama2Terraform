"""Smoke tests: both scripts run end to end without crashing.

These tests are the baseline gate. Deeper parser and generator tests
land in later tasks (see to-do.md F1.2-F1.4).
"""

from conftest import SAMPLE_CONFIG, run_script


def test_sample_config_exists():
    """The committed sample config must exist for the other tests."""
    assert SAMPLE_CONFIG.is_file(), f"missing sample config: {SAMPLE_CONFIG}"


def test_converter_runs_on_sample(converter_module, tmp_path):
    """The converter exits 0 and writes the core output files."""
    out_dir = tmp_path / "tf_out"
    result = run_script("panorama_to_terraform.py", str(SAMPLE_CONFIG), "--output-dir", str(out_dir))
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"

    # Core files the converter must always emit.
    expected = [
        "provider.tf",
        "variables.tf",
        "address_objects.tf",
        "address_groups.tf",
        "service_objects.tf",
        "service_groups.tf",
        "security_rules.tf",
        "nat_rules.tf",
    ]
    for name in expected:
        path = out_dir / name
        assert path.is_file(), f"converter did not emit {name}"
        assert path.stat().st_size > 0, f"converter emitted empty {name}"


def test_splitter_help_exits_zero():
    """The splitter --help path works (argparse wiring is intact)."""
    result = run_script("split_device_groups.py", "--help")
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


def test_splitter_runs_on_sample(tmp_path):
    """The splitter exits 0 and writes one file per device group."""
    out_dir = tmp_path / "split_out"
    result = run_script("split_device_groups.py", str(SAMPLE_CONFIG), "--output-dir", str(out_dir))
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
    split_files = sorted(out_dir.glob("*.xml"))
    assert split_files, "splitter did not write any device group files"
    for path in split_files:
        assert path.stat().st_size > 0, f"splitter wrote empty {path.name}"
