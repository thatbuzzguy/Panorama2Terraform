"""Terraform gate: generated output must init and validate.

The gate has two checks:

1. ``terraform init -backend=false`` succeeds. This is the tooling gate:
   the provider declared in the output must be resolvable.
2. ``terraform validate`` succeeds against the v2 provider, for the
   sample config, the kitchen-sink fixture (which exercises every
   resource type), the crypto-profile-only fixture (which exercises the
   F2.8 standalone-profile emission path in vpn.tf), the two-device
   fixture (which exercises the F3.6 ``location.ngfw`` placement), and
   the filter fixture (which exercises the F7.8 container emission).

A plan reads the directory it runs on, and every fixture here writes one directory per unit, so each pin
calls the same function the CLI calls on ``--validate``, once per unit directory the manifest record names.
A validate at the codebase root reads no configuration file, so it passes without checking the run. The rule
is in `docs/ARCHITECTURE.md` §4.6, and the pin uses the gate's own result for the directory, so no second
plan rule appears here.

The test skips when the ``terraform`` binary is absent so the Python
matrix jobs are unaffected; the CI ``terraform-gate`` job provides it.
"""

import subprocess
from pathlib import Path

import pytest

import sanity_checks
from conftest import FIXTURES_DIR, SAMPLE_CONFIG, TERRAFORM, run_script

# The terraform binary is read through `tests/conftest.py` (§1.1), so the skip rule for a missing binary is
# the same rule as the gate's.
FIXTURES_KITCHEN = FIXTURES_DIR / "kitchen_sink.xml"
FIXTURES_VPN_PROFILES = FIXTURES_DIR / "ike_crypto_profiles.xml"
FIXTURES_MULTI_DEVICE = FIXTURES_DIR / "multi_device_templates.xml"
FIXTURES_FILTERS = FIXTURES_DIR / "filter_containers.xml"


def _generate(source_xml: Path, out_dir: Path) -> None:
    result = run_script("panorama_to_terraform.py", str(source_xml), "--output-dir", str(out_dir))
    assert result.returncode == 0, f"converter failed: {result.stderr}\n{result.stdout}"


def _plan_results(out_dir: Path) -> list[tuple[str, sanity_checks.CheckResult]]:
    """The gate's plan check, one result per unit directory the record names.

    This is the call `main()` makes on `--validate`, so the pin cannot disagree with the runtime gate.
    """
    units = sanity_checks.unit_directories(out_dir)
    assert units, "the run wrote no unit directory"
    return [(unit, sanity_checks.check_terraform(out_dir / unit, TERRAFORM, unit)) for unit in units]


def _assert_all_passed(results: list[tuple[str, sanity_checks.CheckResult]]) -> None:
    for unit, check in results:
        assert check.result == "PASS", f"{unit}: {[f.render() for f in check.findings]}"


def test_terraform_init_succeeds(tmp_path):
    """The provider declared in the output must resolve and install inside a unit directory the run wrote."""
    if TERRAFORM is None:
        pytest.skip("terraform binary not found (the CI terraform-gate job provides it)")
    out_dir = tmp_path / "tf_validate"
    _generate(SAMPLE_CONFIG, out_dir)
    units = sanity_checks.unit_directories(out_dir)
    assert units, "the run wrote no unit directory"
    init = subprocess.run(
        [TERRAFORM, "init", "-backend=false", "-input=false"],
        cwd=out_dir / units[0],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert init.returncode == 0, f"terraform init failed:\n{init.stdout[-2000:]}\n{init.stderr[-2000:]}"


def test_terraform_validate_succeeds(tmp_path):
    """The sample configuration must pass terraform validate, one plan per unit directory."""
    if TERRAFORM is None:
        pytest.skip("terraform binary not found (the CI terraform-gate job provides it)")
    out_dir = tmp_path / "tf_validate_sample"
    _generate(SAMPLE_CONFIG, out_dir)
    _assert_all_passed(_plan_results(out_dir))


def test_terraform_validate_kitchen_succeeds(tmp_path):
    """The kitchen-sink configuration must pass terraform validate, one plan per unit directory.

    The fixture states the value provider 2.0.14 accepts for `panos_administrative_tag`, so the plan that
    reads the written files passes. A value the provider constrains in its code, not in the schema, is a
    plan finding, not a static rule: `docs/ARCHITECTURE.md` §4.6, pinned by
    `tests/test_sanity_gate.py::test_kitchen_sink_gate_passes_with_validate`.
    """
    if TERRAFORM is None:
        pytest.skip("terraform binary not found (the CI terraform-gate job provides it)")
    out_dir = tmp_path / "tf_validate_kitchen"
    _generate(FIXTURES_KITCHEN, out_dir)
    _assert_all_passed(_plan_results(out_dir))


def test_terraform_validate_vpn_profiles_succeeds(tmp_path):
    """A standalone crypto profile must pass terraform validate.

    A config with crypto profiles but no gateway or tunnel must still
    emit a valid vpn.tf: the legacy emission gate dropped it silently.
    """
    if TERRAFORM is None:
        pytest.skip("terraform binary not found (the CI terraform-gate job provides it)")
    out_dir = tmp_path / "tf_validate_vpn_profiles"
    _generate(FIXTURES_VPN_PROFILES, out_dir)
    _assert_all_passed(_plan_results(out_dir))


def test_terraform_validate_filters_succeeds(tmp_path):
    """The filter fixture must pass terraform validate, one plan per unit directory.

    The pin calls the same function the CLI calls on `--validate`, so the choice levels
    the fixture answers with one element are the same choice levels the provider accepts.
    """
    if TERRAFORM is None:
        pytest.skip("terraform binary not found (the CI terraform-gate job provides it)")
    out_dir = tmp_path / "tf_validate_filters"
    _generate(FIXTURES_FILTERS, out_dir)
    _assert_all_passed(_plan_results(out_dir))


def test_terraform_validate_multi_device_succeeds(tmp_path):
    """A device-placed interface and a template-placed router must validate.

    `terraform validate` accepts an unknown location sub-block and drops it, so this gate proves the HCL
    parses and the sub-block shape is well formed; tests/test_multi_device_template.py checks the sub-block
    name itself.
    """
    if TERRAFORM is None:
        pytest.skip("terraform binary not found (the CI terraform-gate job provides it)")
    out_dir = tmp_path / "tf_validate_multi_device"
    _generate(FIXTURES_MULTI_DEVICE, out_dir)
    _assert_all_passed(_plan_results(out_dir))
