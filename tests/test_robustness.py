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
    # F2.7 naming: sanitized name plus an 8-hex digest of the source identity.
    assert re.search(r'resource "panos_address" "named_host_[0-9a-f]{8}"', text)
    # Exactly one resource: the unnamed entry must not produce a block.
    assert len(re.findall(r'resource "panos_address"', text)) == 1


def test_sanitization_collisions_get_unique_names(tmp_path):
    """a-b, a_b and A-B all sanitize to a_b; each must keep its own name."""
    proc = _run(CONVERTER, str(FIXTURES_DIR / 'robust_name_collisions.xml'),
                '--output-dir', str(tmp_path / 'out'), workdir=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = (tmp_path / 'out' / 'address_objects.tf').read_text(encoding='utf-8')
    names = re.findall(r'resource "panos_address" "([^"]+)"', text)
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


def test_declare_resource_name_avoids_collisions(generator):
    import panorama_to_terraform
    scope = 'panos_address'
    first = generator.declare_resource_name('a-b', scope)
    second = generator.declare_resource_name('a_b', scope)
    third = generator.declare_resource_name('A-B', scope)
    names = (first, second, third)
    # Three distinct resource addresses (duplicates would be invalid HCL).
    assert len(set(names)) == 3
    # F2.7: each is the shared sanitized base plus a distinct 8-hex digest
    # of the raw name, so 'a-b' and 'a_b' stay apart deterministically.
    for n in names:
        assert re.fullmatch(r'a_b_[0-9a-f]{8}', n)
    # A reference site resolves each raw name to its own declared resource.
    for raw, local in (('a-b', first), ('a_b', second), ('A-B', third)):
        ref = generator.name_ref(raw, (scope,))
        assert isinstance(ref, panorama_to_terraform.HclRef)
        assert ref.expr == f'{scope}.{local}.name'
    # An undeclared name stays a plain brown-field string (never a ref).
    assert generator.name_ref('ghost', (scope,)) == 'ghost'
    # Collision domains are separate per resource type.
    assert re.fullmatch(
        r'a_b_[0-9a-f]{8}', generator.declare_resource_name('a_b', 'panos_service'))


def test_declare_resource_name_is_order_independent(tmp_path):
    """F2.7: the local name depends on the object identity, not emission order."""
    import panorama_to_terraform
    scope = 'panos_address'
    g1 = panorama_to_terraform.TerraformGenerator(str(tmp_path / 'g1'))
    g2 = panorama_to_terraform.TerraformGenerator(str(tmp_path / 'g2'))
    for raw in ('a-b', 'a_b', 'A-B'):
        g1.declare_resource_name(raw, scope)
    for raw in ('A-B', 'a_b', 'a-b'):
        g2.declare_resource_name(raw, scope)
    set1 = {g1.name_ref(r, (scope,)).expr for r in ('a-b', 'a_b', 'A-B')}
    set2 = {g2.name_ref(r, (scope,)).expr for r in ('a-b', 'a_b', 'A-B')}
    assert set1 == set2


def test_declare_empty_name_gets_a_stable_name(generator):
    """F2.7: an empty name yields a valid, digest-based resource name."""
    first = generator.declare_resource_name('', 'panos_zone')
    assert re.fullmatch(r'unnamed_[0-9a-f]{8}', first)
    # A second declaration of the same identity takes the counter suffix,
    # so two resources never share one address (the output stays valid HCL).
    second = generator.declare_resource_name('', 'panos_zone')
    assert second == f'{first}_2'


def test_name_ref_never_dangles(generator):
    """A name declared in one scope is unreachable through another scope."""
    local = generator.declare_resource_name('svc-x', 'panos_service')
    # The service scope resolves to a reference...
    assert generator.name_ref('svc-x', ('panos_service',)).expr == f'panos_service.{local}.name'
    # ...the address scopes do not (no phantom resource reference).
    assert generator.name_ref('svc-x', ('panos_address', 'panos_address_group')) == 'svc-x'


def test_declare_same_name_in_two_contexts_gets_unique_names(generator):
    """The same PAN-OS name in two device groups must yield two resources."""
    first = generator.declare_resource_name('default', 'panos_virtual_router', context='DG-A')
    second = generator.declare_resource_name('default', 'panos_virtual_router', context='DG-B')
    # F2.7: both are the sanitized base plus a digest that differs by context.
    assert re.fullmatch(r'default_[0-9a-f]{8}', first)
    assert re.fullmatch(r'default_[0-9a-f]{8}', second)
    assert first != second
    # A reference to the name resolves to the first declared name.
    assert generator.name_ref('default', ('panos_virtual_router',)).expr == (
        f'panos_virtual_router.{first}.name')
