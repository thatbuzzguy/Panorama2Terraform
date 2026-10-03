"""F1.7: security and robustness tests.

Hostile input must fail cleanly (non-zero exit, no traceback, no data leak).
Degenerate input must produce valid output or skip safely.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
CONVERTER = REPO_ROOT / 'panorama_to_terraform.py'
SPLITTER = REPO_ROOT / 'split_device_groups.py'
FIXTURES_DIR = REPO_ROOT / 'tests' / 'fixtures'

# A unique marker so a leak is detectable even in shared environments.
XXE_SECRET_PATH = Path('/tmp/panos2tf_secret')
XXE_MARKER = 'PANOS2TF-XXE-LEAK-MARKER-3f9c'


def _run(script: Path, *args: str, workdir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=workdir,
    )


def _assert_clean_failure(proc: subprocess.CompletedProcess) -> None:
    assert proc.returncode != 0
    combined = proc.stdout + proc.stderr
    assert 'Traceback' not in combined


# --- Hostile input: must fail cleanly ---------------------------------------

def test_entity_expansion_rejected(tmp_path):
    """A DTD with expanding entities is rejected before parsing (no DoS)."""
    proc = _run(CONVERTER, str(FIXTURES_DIR / 'hostile_billion_laughs.xml'),
                '--output-dir', str(tmp_path / 'out'), workdir=tmp_path)
    _assert_clean_failure(proc)
    assert 'DTD' in proc.stdout + proc.stderr


def test_xxe_rejected_without_leak(tmp_path):
    """An external entity reference is rejected and the file is never read."""
    XXE_SECRET_PATH.write_text(XXE_MARKER, encoding='ascii')
    try:
        proc = _run(CONVERTER, str(FIXTURES_DIR / 'hostile_xxe.xml'),
                    '--output-dir', str(tmp_path / 'out'), workdir=tmp_path)
    finally:
        XXE_SECRET_PATH.unlink(missing_ok=True)
    _assert_clean_failure(proc)
    assert 'DTD' in proc.stdout + proc.stderr
    # No generated file may contain the secret.
    out_dir = tmp_path / 'out'
    if out_dir.is_dir():
        for f in out_dir.iterdir():
            assert XXE_MARKER not in f.read_text(encoding='utf-8', errors='replace')


def test_malformed_xml_rejected(tmp_path):
    """XML that is not well-formed (illegal control character) fails cleanly."""
    proc = _run(CONVERTER, str(FIXTURES_DIR / 'hostile_bad_control_char.xml'),
                '--output-dir', str(tmp_path / 'out'), workdir=tmp_path)
    _assert_clean_failure(proc)
    assert 'not well-formed' in proc.stdout + proc.stderr


def test_splitter_rejects_dtd(tmp_path):
    """The splitter applies the same DTD rejection."""
    proc = _run(SPLITTER, str(FIXTURES_DIR / 'hostile_xxe.xml'),
                '--output-dir', str(tmp_path / 'out'), workdir=tmp_path)
    _assert_clean_failure(proc)
    assert 'DTD' in proc.stdout + proc.stderr


# --- Degenerate input: must produce valid output ----------------------------

def test_tab_cr_names_produce_valid_tf(tmp_path):
    """Names with tabs/CRs generate .tf files free of raw control chars."""
    proc = _run(CONVERTER, str(FIXTURES_DIR / 'robust_tab_cr_names.xml'),
                '--output-dir', str(tmp_path / 'out'), workdir=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    address_tf = (tmp_path / 'out' / 'address_objects.tf').read_bytes()
    # HCL .tf files must not carry raw CR or C0 control characters (LF is
    # the only legal raw control byte).
    illegal = [b for b in address_tf if b < 0x20 and b != 0x0A]
    assert illegal == []
    assert b'\t' not in address_tf
    assert b'\r' not in address_tf


def test_entry_without_name_is_skipped(tmp_path):
    """An entry without a name attribute is skipped without crashing."""
    proc = _run(CONVERTER, str(FIXTURES_DIR / 'robust_empty_names.xml'),
                '--output-dir', str(tmp_path / 'out'), workdir=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = (tmp_path / 'out' / 'address_objects.tf').read_text(encoding='utf-8')
    assert 'resource "panos_address_object" "named_host"' in text
    # Exactly one resource: the unnamed entry must not produce a block.
    assert len(re.findall(r'resource "panos_address_object"', text)) == 1


def test_sanitization_collisions_get_unique_names(tmp_path):
    """a-b, a_b and A-B all sanitize to a_b; each must keep its own name."""
    proc = _run(CONVERTER, str(FIXTURES_DIR / 'robust_name_collisions.xml'),
                '--output-dir', str(tmp_path / 'out'), workdir=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = (tmp_path / 'out' / 'address_objects.tf').read_text(encoding='utf-8')
    names = re.findall(r'resource "panos_address_object" "([^"]+)"', text)
    # Three distinct resource addresses (duplicates would be invalid HCL).
    assert len(names) == 3
    assert len(set(names)) == 3
    # All three objects survive with their values.
    for ip in ('10.0.1.1', '10.0.1.2', '10.0.1.3'):
        assert ip in text


# --- Unit-level pinning of the helper fixes ---------------------------------

@pytest.fixture(scope='module')
def generator(tmp_path_factory):
    import panorama_to_terraform
    return panorama_to_terraform.TerraformGenerator(str(tmp_path_factory.mktemp('gen')))


def test_escape_string_escapes_control_chars(generator):
    assert generator.escape_string('a\tb') == '"a\\tb"'
    assert generator.escape_string('a\rb') == '"a\\rb"'
    assert generator.escape_string('a\nb') == '"a\\nb"'
    assert generator.escape_string('a"b\\c') == '"a\\"b\\\\c"'


def test_escape_string_strips_illegal_control_chars(generator):
    assert generator.escape_string('a\x01b') == '"ab"'
    assert generator.escape_string('a\x7fb') == '"ab"'


def test_unique_resource_name_avoids_collisions(generator):
    scope = 'panos_address_object'
    first = generator.unique_resource_name('a-b', scope)
    second = generator.unique_resource_name('a_b', scope)
    third = generator.unique_resource_name('A-B', scope)
    assert (first, second, third) == ('a_b', 'a_b_2', 'a_b_3')
    # A reference site recomputes the same input and gets the same name.
    assert generator.unique_resource_name('a_b', scope) == second
    # Collision domains are separate per resource type.
    assert generator.unique_resource_name('a_b', 'panos_service_object') == 'a_b'
