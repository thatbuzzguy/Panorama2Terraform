"""Terraform gate: generated output must init and validate.

The gate has two checks:

1. ``terraform init -backend=false`` succeeds. This is the tooling gate:
   the provider declared in the output must be resolvable. It must pass
   today.
2. ``terraform validate`` succeeds. The current v1-style output fails
   against the v2 provider (unsupported resource types, missing required
   ``location``, unsupported arguments), so this check is ``xfail`` with
   Epic 2 references. It goes green when Epic 2 (F2.2 resource mapping,
   F2.3 location, F2.4 arguments) rewrites the generator.

The test skips when the ``terraform`` binary is absent so the Python
matrix jobs are unaffected; the CI ``terraform-gate`` job provides it.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import SAMPLE_CONFIG, run_script

TERRAFORM = shutil.which("terraform")


def _generate_sample_output(out_dir: Path) -> None:
    result = run_script("panorama_to_terraform.py", str(SAMPLE_CONFIG), "--output-dir", str(out_dir))
    assert result.returncode == 0, f"converter failed: {result.stderr}\n{result.stdout}"


@pytest.fixture(scope="session")
def tf_workspace(tmp_path_factory) -> dict:
    """Generate the sample output, terraform init it, and return both.

    Returns {"dir": output directory, "init": init CompletedProcess}.
    """
    if TERRAFORM is None:
        pytest.skip("terraform binary not found (the CI terraform-gate job provides it)")
    out_dir = tmp_path_factory.mktemp("tf_validate")
    _generate_sample_output(out_dir)
    init = subprocess.run(
        [TERRAFORM, "init", "-backend=false", "-input=false"],
        cwd=out_dir,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return {"dir": out_dir, "init": init}


def test_terraform_init_succeeds(tf_workspace):
    """The provider declared in the output must resolve and install."""
    init = tf_workspace["init"]
    assert init.returncode == 0, (
        f"terraform init failed:\n{init.stdout[-2000:]}\n{init.stderr[-2000:]}"
    )


@pytest.mark.xfail(
    reason="output uses v1 resource types and lacks required location; fixed by Epic 2 F2.2, F2.3, F2.4",
    strict=False,
)
def test_terraform_validate_succeeds(tf_workspace):
    """The generated configuration must pass terraform validate."""
    result = subprocess.run(
        [TERRAFORM, "validate"],
        cwd=tf_workspace["dir"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"terraform validate failed:\n{result.stdout[-4000:]}\n{result.stderr[-2000:]}"
    )
