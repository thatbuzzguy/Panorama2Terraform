"""F1.7: security and robustness tests.

Hostile input must fail cleanly (non-zero exit, no traceback, no data leak).
Degenerate input must produce valid output or skip safely.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

import sanity_checks
import unit_manifest
from conftest import FIXTURES_DIR, REPO_ROOT, SRC_DIR, file_text, tf_files

# The layout rule (`docs/ARCHITECTURE.md` §1.1): the entry points are tool modules, so the test reads them
# from the `src/` namespace, through the paths conftest builds once.
CONVERTER = SRC_DIR / 'panorama_to_terraform.py'
SPLITTER = SRC_DIR / 'split_device_groups.py'

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

def test_a_parsed_secret_never_reaches_a_generated_file(tmp_path):
    """F7.7: a `sensitive` value the parse read is printed as the reference, so no file holds the value.

    `tests/fixtures/auth_profile.xml` states one distinct value per level, so the pin names each one. The block
    prints `var.<the §5 name of the entry that holds the field>`, `site_data.py` rule 2 writes no row for a name
    with no value, and no `.tfvars` line is written for it. The name itself, and its `sensitive = true` marking,
    are pinned by `tests/test_variables.py`.
    """
    result = _run(CONVERTER, str(FIXTURES_DIR / 'auth_profile.xml'), '--output-dir', str(tmp_path),
                  workdir=REPO_ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    values = ('bgp-secret-value', 'ospf-password-value', 'ospf-md5-value', 'rip-password-value',
             'ospfv3-ah-value', 'ospfv3-esp-value')
    written = {str(path): path.read_text(encoding='utf-8') for path in Path(tmp_path).rglob('*')
              if path.is_file()}
    assert not any(value in text for text in written.values() for value in values), sorted(written)
    tfvars = [text for path, text in written.items() if path.endswith('.tfvars')]
    assert not any(any(value in text for value in values) for text in tfvars), tfvars


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
    """Names with tabs/CRs generate .tf files free of raw control chars.

    The rule lives in `sanity_checks.py` (F4.1), so the conversion gate and this
    test share it: LF is the only legal raw control byte, and a tab or a CR
    means an escape was missed.
    """
    proc = _run(CONVERTER, str(FIXTURES_DIR / 'robust_tab_cr_names.xml'),
                '--output-dir', str(tmp_path / 'out'), workdir=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out_dir = tmp_path / 'out'
    files = {f.name: f.read_text(encoding='utf-8', errors='surrogateescape')
             for f in sorted(out_dir.glob('*.tf'))}
    findings = sanity_checks.check_control_chars(files)
    assert findings == [], ', '.join(f.render() for f in findings)
    # The whole output also passes the gate, so the exit code above is the
    # gate's verdict, not only the generator's.
    assert not sanity_checks.run_checks(out_dir).failed


def test_entry_without_name_is_skipped(tmp_path):
    """An entry without a name attribute is skipped without crashing."""
    proc = _run(CONVERTER, str(FIXTURES_DIR / 'robust_empty_names.xml'),
                '--output-dir', str(tmp_path / 'out'), workdir=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    # F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): the file is read as the gate reads it, so the parts the
    # run wrote for every unit are read in path order.
    text = file_text(tf_files(tmp_path / 'out'), 'address_objects.tf')
    # F2.7 naming: sanitized name plus an 8-hex digest of the source identity.
    assert re.search(r'resource "panos_address" "named_host_[0-9a-f]{8}"', text)
    # Exactly one resource: the unnamed entry must not produce a block.
    assert len(re.findall(r'resource "panos_address"', text)) == 1


def test_sanitization_collisions_get_unique_names(tmp_path):
    """a-b, a_b and A-B all sanitize to a_b; each must keep its own name."""
    proc = _run(CONVERTER, str(FIXTURES_DIR / 'robust_name_collisions.xml'),
                '--output-dir', str(tmp_path / 'out'), workdir=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = file_text(tf_files(tmp_path / 'out'), 'address_objects.tf')
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
    # F6.10.2: the naming site takes the object, so the unit the name belongs to is the
    # object's five facts, read through `unit_manifest.facts_of`.
    objs = {raw: {'name': raw} for raw in ('a-b', 'a_b', 'A-B')}
    first = generator.declare_resource_name('a-b', scope, objs['a-b'])
    second = generator.declare_resource_name('a_b', scope, objs['a_b'])
    third = generator.declare_resource_name('A-B', scope, objs['A-B'])
    names = (first, second, third)
    # Three distinct resource addresses (duplicates would be invalid HCL).
    assert len(set(names)) == 3
    # F2.7: each is the shared sanitized base plus a distinct 8-hex digest
    # of the raw name, so 'a-b' and 'a_b' stay apart deterministically.
    for n in names:
        assert re.fullmatch(r'a_b_[0-9a-f]{8}', n)
    # A reference site inside the declaring unit resolves each raw name to its own resource.
    for raw, local in (('a-b', first), ('a_b', second), ('A-B', third)):
        ref = generator.name_ref(raw, (scope,), objs[raw])
        assert isinstance(ref, panorama_to_terraform.HclRef)
        assert ref.expr == f'{scope}.{local}.name'
    # An undeclared name stays a plain brown-field string (never a ref).
    assert generator.name_ref('ghost', (scope,), objs['a-b']) == 'ghost'
    # Collision domains are separate per resource type.
    assert re.fullmatch(
        r'a_b_[0-9a-f]{8}', generator.declare_resource_name('a_b', 'panos_service', objs['a_b']))


def test_declare_resource_name_is_order_independent(tmp_path):
    """F2.7: the local name depends on the object identity, not emission order."""
    import panorama_to_terraform
    scope = 'panos_address'
    g1 = panorama_to_terraform.TerraformGenerator(str(tmp_path / 'g1'))
    g2 = panorama_to_terraform.TerraformGenerator(str(tmp_path / 'g2'))
    objs = {raw: {'name': raw} for raw in ('a-b', 'a_b', 'A-B')}
    for raw in ('a-b', 'a_b', 'A-B'):
        g1.declare_resource_name(raw, scope, objs[raw])
    for raw in ('A-B', 'a_b', 'a-b'):
        g2.declare_resource_name(raw, scope, objs[raw])
    set1 = {g1.name_ref(r, (scope,), objs[r]).expr for r in ('a-b', 'a_b', 'A-B')}
    set2 = {g2.name_ref(r, (scope,), objs[r]).expr for r in ('a-b', 'a_b', 'A-B')}
    assert set1 == set2


def test_declare_empty_name_gets_a_stable_name(generator):
    """F2.7: an empty name yields a valid, digest-based resource name."""
    entry = {'name': ''}
    first = generator.declare_resource_name('', 'panos_zone', entry)
    assert re.fullmatch(r'unnamed_[0-9a-f]{8}', first)
    # A second declaration of the same identity takes the counter suffix,
    # so two resources never share one address (the output stays valid HCL).
    second = generator.declare_resource_name('', 'panos_zone', entry)
    assert second == f'{first}_2'
    # The counter does not split the unit: the index still names one local name for it (F6.10.2).
    assert generator._declaration_index[('panos_zone', '')][unit_manifest.facts_of(entry)] == first


def test_name_ref_never_dangles(generator):
    """A name declared in one scope is unreachable through another scope."""
    entry = {'name': 'svc-x'}
    local = generator.declare_resource_name('svc-x', 'panos_service', entry)
    # The service scope resolves to a reference...
    assert generator.name_ref('svc-x', ('panos_service',), entry).expr == f'panos_service.{local}.name'
    # ...the address scopes do not (no phantom resource reference).
    assert generator.name_ref('svc-x', ('panos_address', 'panos_address_group'), entry) == 'svc-x'


def test_declare_same_name_in_two_contexts_gets_unique_names(generator):
    """The same PAN-OS name in two device groups must yield two resources."""
    entry_a = {'name': 'default', 'device_group': 'DG-A'}
    entry_b = {'name': 'default', 'device_group': 'DG-B'}
    first = generator.declare_resource_name('default', 'panos_virtual_router', entry_a, context='DG-A')
    second = generator.declare_resource_name('default', 'panos_virtual_router', entry_b, context='DG-B')
    # F2.7: both are the sanitized base plus a digest that differs by context.
    assert re.fullmatch(r'default_[0-9a-f]{8}', first)
    assert re.fullmatch(r'default_[0-9a-f]{8}', second)
    assert first != second
    # F6.10.2: each unit keeps its own name, so the reference rule resolves each one inside its own unit.
    assert generator.name_ref('default', ('panos_virtual_router',), entry_a).expr == (
        f'panos_virtual_router.{first}.name')
    assert generator.name_ref('default', ('panos_virtual_router',), entry_b).expr == (
        f'panos_virtual_router.{second}.name')


def test_name_ref_resolves_inside_the_referrers_own_unit(generator):
    """F3.1, F6.10.2: a referrer resolves a same-named object declared by its own unit."""
    scope = 'panos_address'
    entries = {dg: {'name': 'web', 'device_group': dg} for dg in ('DG-A', 'DG-B')}
    dg_a = generator.declare_resource_name('web', scope, entries['DG-A'], context='DG-A')
    dg_b = generator.declare_resource_name('web', scope, entries['DG-B'], context='DG-B')
    # A rule in DG-B references DG-B's 'web', not DG-A's.
    assert generator.name_ref('web', (scope,), entries['DG-B']).expr == f'{scope}.{dg_b}.name'
    assert generator.name_ref('web', (scope,), entries['DG-A']).expr == f'{scope}.{dg_a}.name'


def test_a_name_another_unit_declares_stays_a_plain_name(generator):
    """F6.10.2, `docs/CODEBASE_ASSEMBLY.md` §5 rule 5: a name is reachable only inside its own unit.

    The shared section is the unit with the empty facts (`unit_manifest.facts_of` maps the parse
    fallback to ''), so a rule in a device group cannot name an address the shared unit declares: one
    plan runs against one root and one state, so the value the provider reads is the name itself.
    """
    scope = 'panos_address'
    shared_entry = {'name': 'sh-web', 'device_group': 'Shared'}
    shared = generator.declare_resource_name('sh-web', scope, shared_entry, context='Shared')
    # The shared unit resolves its own name.
    assert generator.name_ref('sh-web', (scope,), shared_entry).expr == f'{scope}.{shared}.name'
    # A rule in another unit keeps the plain name.
    rule = {'name': 'rule-1', 'device_group': 'DG-A'}
    assert generator.name_ref('sh-web', (scope,), rule) == 'sh-web'
    # A name no unit declares stays plain too, and is not an index entry.
    assert generator.name_ref('no-such-name', (scope,), rule) == 'no-such-name'
    assert generator._declaration_index.get((scope, 'no-such-name')) is None


# --- F3.2: vsys completes the identity key -----------------------------------

def test_declare_same_name_in_two_vsys_gets_unique_names(generator):
    """F3.2: the same name in two vsys gets two digest-based names.

    The digest covers (scope, context, vsys, name), so the taken-name
    counter never decides which object keeps the base name.
    """
    scope = 'panos_address'
    entry1 = {'name': 'web', 'device_group': 'DG-A', 'vsys': 'vsys1'}
    entry2 = {'name': 'web', 'device_group': 'DG-A', 'vsys': 'vsys2'}
    vs1 = generator.declare_resource_name('web', scope, entry1, context='DG-A', vsys='vsys1')
    vs2 = generator.declare_resource_name('web', scope, entry2, context='DG-A', vsys='vsys2')
    assert re.fullmatch(r'web_[0-9a-f]{8}', vs1)
    assert re.fullmatch(r'web_[0-9a-f]{8}', vs2)
    assert vs1 != vs2
    # No counter suffix: the digest, not the guard, keeps them apart.
    assert not vs1.endswith('_2') and not vs2.endswith('_2')
    # F6.10.2: the two vsys are two units, so each unit resolves its own copy.
    assert generator.name_ref('web', (scope,), entry1).expr == f'{scope}.{vs1}.name'
    assert generator.name_ref('web', (scope,), entry2).expr == f'{scope}.{vs2}.name'


def test_name_ref_resolves_inside_the_referrers_own_vsys(generator):
    """F3.2, F6.10.2: a referrer resolves a name its own unit declares, not another vsys's copy.

    The device group alone is not a unit: the five facts decide, so a rule in vsys2 reaches vsys2's
    object and keeps the plain name for the copy vsys1 declared.
    """
    scope = 'panos_address'
    entry1 = {'name': 'web2', 'device_group': 'DG-A', 'vsys': 'vsys1'}
    entry2 = {'name': 'web2', 'device_group': 'DG-A', 'vsys': 'vsys2'}
    vs1 = generator.declare_resource_name('web2', scope, entry1, context='DG-A', vsys='vsys1')
    vs2 = generator.declare_resource_name('web2', scope, entry2, context='DG-A', vsys='vsys2')
    # A rule in vsys2 references vsys2's 'web2', not vsys1's.
    assert generator.name_ref('web2', (scope,), entry2).expr == f'{scope}.{vs2}.name'
    assert generator.name_ref('web2', (scope,), entry1).expr == f'{scope}.{vs1}.name'
    # A referrer in a third unit keeps the plain name for both.
    other = {'name': 'rule-1', 'device_group': 'DG-A', 'vsys': 'vsys3'}
    assert generator.name_ref('web2', (scope,), other) == 'web2'
    # The same name in one unit resolves to the first declaration of that identity (F2.6).
    same_unit = {'name': 'web2', 'device_group': 'DG-A', 'vsys': 'vsys1'}
    assert generator.name_ref('web2', (scope,), same_unit).expr == f'{scope}.{vs1}.name'


def test_name_ref_vsys_resolution_is_declaration_order_independent(tmp_path):
    """F3.2, F6.10.2: which unit's copy wins does not depend on which unit was declared first."""
    import panorama_to_terraform
    scope = 'panos_address'
    g1 = panorama_to_terraform.TerraformGenerator(str(tmp_path / 'g1'))
    g2 = panorama_to_terraform.TerraformGenerator(str(tmp_path / 'g2'))
    entries = {vs: {'name': 'web', 'device_group': 'DG-A', 'vsys': vs} for vs in ('vsys1', 'vsys2')}
    for vs in ('vsys1', 'vsys2'):
        g1.declare_resource_name('web', scope, entries[vs], context='DG-A', vsys=vs)
    for vs in ('vsys2', 'vsys1'):
        g2.declare_resource_name('web', scope, entries[vs], context='DG-A', vsys=vs)
    for vs in ('vsys1', 'vsys2'):
        assert g1.name_ref('web', (scope,), entries[vs]).expr == \
            g2.name_ref('web', (scope,), entries[vs]).expr
