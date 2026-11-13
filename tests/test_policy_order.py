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

from pathlib import Path

import pytest

import sanity_checks
from conftest import (
    FIXTURES_DIR,
    GOLDEN_DIR,
    check_chain_semantics,
    file_text,
    parts,
    rule_blocks,
    run_script,
    tf_files,
)

# The structural parser for the generated rule files and the chain check are read through
# `tests/conftest.py`, the one shared helper file (§1.1), because `tests/test_real_or_report.py` reads the
# same two functions. A resource block ends at the first newline followed by a column-0 brace.


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
    blocks = rule_blocks(
        file_text(tf_files(generated), 'security_rules.tf'),
        'panos_security_policy_rules')
    check_chain_semantics(blocks, 'panos_security_policy_rules',
                           EXPECTED_SECURITY, 'security fixture')
    assert [b['device_group'] for b in blocks] == (
        ['Alpha-DG'] * 3 + ['Beta-DG'] * 2 + ['Gamma-DG']), 'security fixture'


def test_security_single_rule_chain_has_only_the_anchor(generated):
    """Gamma-DG has one rule: anchor position, no pivot, no depends_on."""
    text = file_text(tf_files(generated), 'security_rules.tf')
    blocks = rule_blocks(text, 'panos_security_policy_rules')
    gamma = [b for b in blocks if b['device_group'] == 'Gamma-DG']
    assert len(gamma) == 1
    assert gamma[0]['where'] == 'last'
    assert gamma[0]['pivot'] is None
    assert gamma[0]['depends_on'] == []


def test_security_chains_do_not_cross_device_groups(generated):
    """A chain starts fresh in each DG: no pivot or depends_on from another DG."""
    text = file_text(tf_files(generated), 'security_rules.tf')
    blocks = rule_blocks(text, 'panos_security_policy_rules')
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
    blocks = rule_blocks(
        file_text(tf_files(generated), 'nat_rules.tf'),
        'panos_nat_policy_rules')
    check_chain_semantics(blocks, 'panos_nat_policy_rules',
                           EXPECTED_NAT, 'nat fixture')


# --- Goldens -----------------------------------------------------------------

@pytest.mark.parametrize('fixture_file', [
    'sample/security_rules.tf',
    'sample/nat_rules.tf',
    'kitchen_sink/security_rules.tf',
    'kitchen_sink/nat_rules.tf',
], ids=lambda p: p.replace('/', '_'))
def test_goldens_preserve_order_preserving_positions(fixture_file):
    """The committed goldens already follow the chain contract.

    F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): the case holds one part per unit, so the pin reads the parts
    as paths from the case directory. A chain never crosses a unit, so the grouping is read inside each part.
    """
    case, name = fixture_file.split('/')
    written = parts(sanity_checks.read_tf_files(GOLDEN_DIR / case), name)
    assert written, f'no golden part named {name} in {case}'
    resource_type = ('panos_security_policy_rules' if 'security' in name
                     else 'panos_nat_policy_rules')
    for path, text in written.items():
        blocks = rule_blocks(text, resource_type)
        assert blocks, f'no rule blocks found in {path}'
        # Group consecutive blocks by device group (chains are emitted contiguously).
        expected: list[tuple[str, list[str]]] = []
        for b in blocks:
            if expected and expected[-1][0] == b['device_group']:
                expected[-1][1].append(b['names'][0])
            else:
                expected.append((b['device_group'], [b['names'][0]]))
        check_chain_semantics(blocks, resource_type, expected, path)
