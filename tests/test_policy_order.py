"""F2.5 order-preserving policy emission.

Pins the per-device-group rule chain semantics on both the dedicated
multi-DG fixture and the committed goldens:

- the first rule of each chain anchors at the end of the rulebase
  (position.where = "last", no pivot, no depends_on);
- each later rule is placed directly after the previous rule
  (position.where = "after", directly = true, pivot = previous rule's
  Panorama name) and declares depends_on on exactly that previous
  rule's resource, so Terraform applies the chain in XML order;
- chains never cross device groups.

Provider v2.0.14 requires pivot and directly together for
where = "after", and fails the move when the pivot is missing, which is
why the depends_on is part of the contract.
"""

import re
from pathlib import Path

import pytest

from conftest import FIXTURES_DIR, GOLDEN_DIR, run_script

# ---------------------------------------------------------------------------
# Structural parser for the generated rule files.
#
# The generated format is fixed, so small structural regexes are enough.
# A resource block ends at the first newline followed by a column-0 brace.
# ---------------------------------------------------------------------------

def _search_one(body: str, pattern: str):
    m = re.search(pattern, body, re.S)
    return m.group(1) if m else None


def _rule_blocks(text: str, resource_type: str) -> list[dict]:
    """Parse generated rule resources into ordered dicts (file order)."""
    blocks = []
    pattern = re.compile(
        'resource "' + re.escape(resource_type) + r'" "([^"]+)" \{(.*?)\n\}', re.S)
    for m in pattern.finditer(text):
        local, body = m.group(1), m.group(2)
        # The rules list holds one object per rule; the Panorama rule name
        # is the only name = line inside it (the location block is outside).
        rules_body = _search_one(body, r'rules = \[(.*?)\n  \]') or ''
        rule_names = re.findall(r'name = "([^"]+)"', rules_body)
        depends_on = _search_one(body, r'depends_on = \[([^\]]*)\]') or ''
        blocks.append({
            'local': local,
            'device_group': _search_one(body, r'device_group = \{\s*name = "([^"]+)"'),
            'where': _search_one(body, r'where = "([^"]+)"'),
            'directly': _search_one(body, r'directly = (true|false)'),
            'pivot': _search_one(body, r'pivot = "([^"]+)"'),
            'depends_on': re.findall(r'([A-Za-z_][\w]*\.[A-Za-z_][\w]*)', depends_on),
            'names': rule_names,
        })
    return blocks


def _check_chain_semantics(blocks: list[dict], resource_type: str,
                           expected: list[tuple[str, list[str]]], msg: str):
    """Assert blocks form per-DG chains with anchor + after-previous positions."""
    assert len(blocks) == sum(len(names) for _, names in expected), msg
    idx = 0
    for dg, names in expected:
        chain = blocks[idx:idx + len(names)]
        idx += len(names)
        for b in chain:
            assert b['device_group'] == dg, msg
        # Every block holds exactly one rule; the rule name sequence is the
        # chain's XML order.
        assert [b['names'] for b in chain] == [[n] for n in names], msg
        # First rule of the chain: anchor at the end of the rulebase.
        first = chain[0]
        assert first['where'] == 'last', msg
        assert first['pivot'] is None, msg
        assert first['directly'] is None, msg
        assert first['depends_on'] == [], msg
        # Later rules: directly after the previous rule, applied after it.
        for prev, cur in zip(chain, chain[1:]):
            assert cur['where'] == 'after', msg
            assert cur['directly'] == 'true', msg
            assert cur['pivot'] == prev['names'][0], msg
            expected_dep = f'{resource_type}.{prev["local"]}'
            assert cur['depends_on'] == [expected_dep], msg


@pytest.fixture(scope='module')
def generated(tmp_path_factory) -> Path:
    """Generate the multi-DG fixture once for the whole module."""
    out = tmp_path_factory.mktemp('policy_order')
    proc = run_script(
        'panorama_to_terraform.py', str(FIXTURES_DIR / 'policy_order.xml'),
        '--output-dir', str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return out


EXPECTED_SECURITY = [
    ('Alpha-DG', ['alpha-rule-1', 'alpha-rule-2', 'alpha-rule-3']),
    ('Beta-DG', ['beta-rule-1', 'beta-rule-2']),
    ('Gamma-DG', ['gamma-rule-1']),
]
EXPECTED_NAT = [
    ('Alpha-DG', ['alpha-nat-1', 'alpha-nat-2']),
]


# --- Fixture: security rules -----------------------------------------------

def test_security_chains_emit_in_xml_order_per_device_group(generated):
    """Chains appear in first-seen DG order, rules in XML order."""
    blocks = _rule_blocks(
        (generated / 'security_rules.tf').read_text(encoding='utf-8'),
        'panos_security_policy_rules')
    _check_chain_semantics(blocks, 'panos_security_policy_rules',
                           EXPECTED_SECURITY, 'security fixture')
    assert [b['device_group'] for b in blocks] == (
        ['Alpha-DG'] * 3 + ['Beta-DG'] * 2 + ['Gamma-DG']), 'security fixture'


def test_security_single_rule_chain_has_only_the_anchor(generated):
    """Gamma-DG has one rule: anchor position, no pivot, no depends_on."""
    text = (generated / 'security_rules.tf').read_text(encoding='utf-8')
    blocks = _rule_blocks(text, 'panos_security_policy_rules')
    gamma = [b for b in blocks if b['device_group'] == 'Gamma-DG']
    assert len(gamma) == 1
    assert gamma[0]['where'] == 'last'
    assert gamma[0]['pivot'] is None
    assert gamma[0]['depends_on'] == []


def test_security_chains_do_not_cross_device_groups(generated):
    """A chain starts fresh in each DG: no pivot or depends_on from another DG."""
    text = (generated / 'security_rules.tf').read_text(encoding='utf-8')
    blocks = _rule_blocks(text, 'panos_security_policy_rules')
    by_dg: dict[str, list[dict]] = {}
    for b in blocks:
        by_dg.setdefault(b['device_group'], []).append(b)
    for dg, chain in by_dg.items():
        # Every depends_on target must be a resource of the same chain.
        locals_in_chain = {f'panos_security_policy_rules.{c["local"]}' for c in chain}
        for c in chain:
            for dep in c['depends_on']:
                assert dep in locals_in_chain, f'{dg}: cross-DG dep {dep}'
        # No pivot may reference a rule outside the chain's XML names.
        names_in_chain = {c['names'][0] for c in chain}
        for c in chain:
            if c['pivot'] is not None:
                assert c['pivot'] in names_in_chain, f'{dg}: cross-DG pivot {c["pivot"]}'


# --- Fixture: NAT rules ------------------------------------------------------

def test_nat_chains_follow_the_same_semantics(generated):
    blocks = _rule_blocks(
        (generated / 'nat_rules.tf').read_text(encoding='utf-8'),
        'panos_nat_policy_rules')
    _check_chain_semantics(blocks, 'panos_nat_policy_rules',
                           EXPECTED_NAT, 'nat fixture')


# --- Goldens -----------------------------------------------------------------

@pytest.mark.parametrize('fixture_file', [
    'sample/security_rules.tf',
    'sample/nat_rules.tf',
    'kitchen_sink/security_rules.tf',
    'kitchen_sink/nat_rules.tf',
], ids=lambda p: p.replace('/', '_'))
def test_goldens_preserve_order_preserving_positions(fixture_file):
    """The committed goldens already follow the chain contract."""
    path = GOLDEN_DIR / fixture_file
    if not path.exists():
        pytest.skip(f'golden {fixture_file} not present')
    text = path.read_text(encoding='utf-8')
    resource_type = ('panos_security_policy_rules' if 'security' in fixture_file
                     else 'panos_nat_policy_rules')
    blocks = _rule_blocks(text, resource_type)
    assert blocks, f'no rule blocks found in {fixture_file}'
    # Group consecutive blocks by device group (chains are emitted contiguously).
    expected: list[tuple[str, list[str]]] = []
    for b in blocks:
        if expected and expected[-1][0] == b['device_group']:
            expected[-1][1].append(b['names'][0])
        else:
            expected.append((b['device_group'], [b['names'][0]]))
    _check_chain_semantics(blocks, resource_type, expected, fixture_file)
