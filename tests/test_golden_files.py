"""Golden-file tests: pin the generator's Terraform output byte-for-byte.

The goldens under tests/golden/ are the committed expected output of two
pipeline runs: the sample config and the kitchen-sink fixture (which
exercises every generator path the sample never reaches).

Any change to generator output must update the goldens deliberately so
the behavior change is visible in review. When the Epic 2 provider-v2
rewrite lands, these goldens are the before/after reference.

Regenerating a golden after an intended change:
    python3 panorama_to_terraform.py <source.xml> --output-dir /tmp/gold
    cp /tmp/gold/*.tf tests/golden/<case>/
"""

from pathlib import Path

import pytest

from conftest import FIXTURES_DIR, SAMPLE_CONFIG, run_script

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

# case name -> (source XML, golden directory)
CASES: dict[str, tuple[Path, Path]] = {
    "sample": (SAMPLE_CONFIG, GOLDEN_DIR / "sample"),
    "kitchen_sink": (FIXTURES_DIR / "kitchen_sink.xml", GOLDEN_DIR / "kitchen_sink"),
}

# (case, filename) pairs for the per-file tests, from the committed goldens.
CASE_FILES: list[tuple[str, str]] = sorted(
    (case, f.name) for case, (_src, golden_dir) in CASES.items() for f in golden_dir.glob("*.tf")
)


def _generate(source_xml: Path, out_dir: Path) -> dict[str, bytes]:
    """Run the converter CLI. Return {filename: bytes} for the .tf output."""
    result = run_script("panorama_to_terraform.py", str(source_xml), "--output-dir", str(out_dir))
    assert result.returncode == 0, f"converter failed: {result.stderr}\n{result.stdout}"
    return {f.name: f.read_bytes() for f in sorted(out_dir.glob("*.tf"))}


def _goldens(golden_dir: Path) -> dict[str, bytes]:
    return {f.name: f.read_bytes() for f in sorted(golden_dir.glob("*.tf"))}


@pytest.fixture(scope="session")
def generated_outputs(tmp_path_factory) -> dict[str, dict[str, bytes]]:
    """Run the converter once per case. Map case -> {filename: bytes}."""
    return {
        case: _generate(source_xml, tmp_path_factory.mktemp(f"golden_{case}"))
        for case, (source_xml, _golden_dir) in CASES.items()
    }


@pytest.fixture(scope="session")
def golden_outputs() -> dict[str, dict[str, bytes]]:
    """Committed golden bytes. Map case -> {filename: bytes}."""
    return {case: _goldens(golden_dir) for case, (_src, golden_dir) in CASES.items()}


@pytest.mark.parametrize("case", list(CASES))
def test_golden_file_set_matches(case, generated_outputs, golden_outputs):
    """The converter must emit exactly the .tf files in the golden set."""
    assert set(generated_outputs[case]) == set(golden_outputs[case]), (
        f"file set mismatch for case {case!r}: "
        f"missing={set(golden_outputs[case]) - set(generated_outputs[case])} "
        f"extra={set(generated_outputs[case]) - set(golden_outputs[case])}"
    )


@pytest.mark.parametrize("case,filename", CASE_FILES)
def test_golden_bytes_match(case, filename, generated_outputs, golden_outputs):
    """Every generated .tf file must equal its committed golden byte-for-byte."""
    assert filename in generated_outputs[case], f"{case}/{filename} not generated"
    assert generated_outputs[case][filename] == golden_outputs[case][filename], (
        f"{case}/{filename} differs from golden. If the change is intended, "
        "regenerate the golden (see module docstring) and review the diff."
    )
