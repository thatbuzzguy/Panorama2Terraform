"""F2.10: clean generated config - every emitted variable is consumed.

The generated variables.tf declares exactly the credential variables,
and the provider block in provider.tf consumes all of them. No dead
variables: a declared variable that no .tf file references is a
failure. (The old `device_group` variable was dead: v2 location is
derived per resource from the source XML, so no global device-group
variable has a consumer.)
"""

import re
import tempfile
from pathlib import Path

import pytest

from conftest import FIXTURES_DIR, SAMPLE_CONFIG, run_script

CASES = {
    "sample": SAMPLE_CONFIG,
    "kitchen_sink": FIXTURES_DIR / "kitchen_sink.xml",
}

CREDENTIALS = ("panos_hostname", "panos_username", "panos_password")

VAR_DECL_RE = re.compile(r'variable\s+"([A-Za-z0-9_]+)"')

# case -> {filename: text} of the converter's .tf output (session cache).
_OUTPUTS: dict[str, dict[str, str]] = {}


def _generate(case: str) -> dict[str, str]:
    """Run the converter CLI on one case. Cache the .tf output per session."""
    if case not in _OUTPUTS:
        out_dir = Path(tempfile.mkdtemp(prefix='variables_'))
        result = run_script(
            'panorama_to_terraform.py', str(CASES[case]),
            '--output-dir', str(out_dir))
        assert result.returncode == 0, (
            f'converter failed on {case}: {result.stderr}\n{result.stdout}')
        _OUTPUTS[case] = {
            f.name: f.read_text() for f in sorted(out_dir.glob('*.tf'))
        }
    return _OUTPUTS[case]


@pytest.mark.parametrize('case', list(CASES))
def test_variable_set_is_exactly_the_credentials(case):
    """No dead variable survives: the declaration set is exactly the credentials."""
    files = _generate(case)
    declared = VAR_DECL_RE.findall(files['variables.tf'])
    assert sorted(declared) == sorted(CREDENTIALS), (
        f'{case}: variables.tf declares {declared}; expected exactly '
        f'{list(CREDENTIALS)}. Remove the dead variable or give it a consumer.')


@pytest.mark.parametrize('case', list(CASES))
def test_every_declared_variable_is_consumed(case):
    """Every `variable "X"` has a `var.X` reference in the generated output."""
    files = _generate(case)
    declared = VAR_DECL_RE.findall(files['variables.tf'])
    consumers = '\n'.join(
        text for name, text in files.items() if name != 'variables.tf')
    for name in declared:
        assert re.search(rf'\bvar\.{re.escape(name)}\b', consumers), (
            f'{case}: variable {name!r} is declared but never consumed '
            f'as var.{name}')


@pytest.mark.parametrize('case', list(CASES))
def test_provider_block_consumes_the_credentials(case):
    """The provider block wires all three credential variables.

    Credentials reach the provider through variables (set in
    terraform.tfvars or via TF_VAR_*), not through commented-out lines.
    """
    files = _generate(case)
    provider = files['provider.tf']
    for name in CREDENTIALS:
        assert f'var.{name}' in provider, (
            f'{case}: provider block does not consume var.{name}')
    # The old commented-out wiring is gone.
    assert '# hostname = var.panos_hostname' not in provider


@pytest.mark.parametrize('case', list(CASES))
def test_password_is_the_only_sensitive_variable(case):
    """Only the password is a secret; hostname and username are not."""
    files = _generate(case)
    text = files['variables.tf']
    blocks = re.findall(
        r'variable\s+"([A-Za-z0-9_]+)"\s*\{(.*?)\n\}', text, re.S)
    for name, body in blocks:
        expected = 'sensitive' in body
        assert expected == (name == 'panos_password'), (
            f'{case}: variable {name!r} sensitive marking is unexpected: '
            f'{"sensitive" if expected else "not sensitive"}')
