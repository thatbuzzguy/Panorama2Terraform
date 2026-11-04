"""Golden-file tests: pin the generator's Terraform output byte-for-byte.

The goldens under tests/golden/ are the committed expected output of two
pipeline runs: the sample config and the kitchen-sink fixture (which
exercises every generator path the sample never reaches).

Any change to generator output must update the goldens deliberately so
the behavior change is visible in review. Reports are not in the golden
set: only `.tf` files are, because report wording changes often and a
byte-for-byte report pin makes a wording edit look like a behavior change.

Regenerating a golden after an intended change:
    python3 src/panorama_to_terraform.py <source.xml> --output-dir /tmp/gold
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
    # F6.10.3: the single-unit case is the same rule, one time. The fixture names one unit, so the case holds
    # one unit directory.
    "single_unit": (FIXTURES_DIR / "address_objects.xml", GOLDEN_DIR / "single_unit"),
    # F7.8: the six filter containers. The fixture holds one entry per choice alternative the input states,
    # so the case holds the `filters.tf` file the emitter writes for all of them.
    "filter_containers": (FIXTURES_DIR / "filter_containers.xml", GOLDEN_DIR / "filter_containers"),
}

# (case, path from the case directory) pairs for the per-file tests, from the committed goldens.
# F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): the key is the path from the case directory, because the unit set
# is one set per unit, so each path names one unit directory.
CASE_FILES: list[tuple[str, str]] = sorted(
    (case, str(f.relative_to(golden_dir)))
    for case, (_src, golden_dir) in CASES.items() for f in golden_dir.rglob("*.tf")
)


def _generate(source_xml: Path, out_dir: Path) -> dict[str, bytes]:
    """Run the converter CLI. Return {path from the output directory: bytes} for the .tf output."""
    result = run_script("panorama_to_terraform.py", str(source_xml), "--output-dir", str(out_dir))
    assert result.returncode == 0, f"converter failed: {result.stderr}\n{result.stdout}"
    return {str(f.relative_to(out_dir)): f.read_bytes() for f in sorted(out_dir.rglob("*.tf"))}


def _goldens(golden_dir: Path) -> dict[str, bytes]:
    return {str(f.relative_to(golden_dir)): f.read_bytes() for f in sorted(golden_dir.rglob("*.tf"))}


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
    """The converter must emit exactly the .tf files in the golden set.

    F6.10.1 (`docs/CODEBASE_ASSEMBLY.md` §14): the key is the path from the case directory, so the pin holds for a
    golden case that holds unit directories. The committed goldens hold the per-unit layout, so each path names one
    unit directory.
    """
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
