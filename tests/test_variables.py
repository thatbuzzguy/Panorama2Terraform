"""F2.10: clean generated config - every emitted variable is consumed.

The generated variables.tf declares the credential variables, and the provider
block in provider.tf consumes all of them. No dead variables: a declared
variable that no .tf file references is a failure. (The old `device_group`
variable was dead: v2 location is derived per resource from the source XML, so
no global device-group variable has a consumer.)

F6.6 adds the second half of the declaration set: the site values the
value-to-variable table mapped. The set is read through `site_data.parse_rows`,
so the file and the data cannot disagree.
"""

import re
import tempfile
from pathlib import Path

import pytest

import sanity_checks
import site_data
from conftest import FIXTURES_DIR, SAMPLE_CONFIG, run_script

CASES = {
    "sample": SAMPLE_CONFIG,
    "kitchen_sink": FIXTURES_DIR / "kitchen_sink.xml",
}

CREDENTIALS = ("panos_hostname", "panos_username", "panos_password")

VAR_DECL_RE = re.compile(r'variable\s+"([A-Za-z0-9_]+)"')

# case -> the run output directory (session cache), so the `.tf` files and the
# site data read the same run.
_OUT_DIRS: dict[str, Path] = {}
_OUTPUTS: dict[str, dict[str, str]] = {}


def _out_dir(case: str) -> Path:
    """Run the converter CLI on one case once per session."""
    if case not in _OUT_DIRS:
        out_dir = Path(tempfile.mkdtemp(prefix='variables_'))
        result = run_script(
            'panorama_to_terraform.py', str(CASES[case]),
            '--output-dir', str(out_dir))
        assert result.returncode == 0, (
            f'converter failed on {case}: {result.stderr}\n{result.stdout}')
        _OUT_DIRS[case] = out_dir
    return _OUT_DIRS[case]


def _generate(case: str) -> dict[str, str]:
    """The converter's `.tf` output for one case. Cached per session."""
    if case not in _OUTPUTS:
        out_dir = _out_dir(case)
        _OUTPUTS[case] = {
            f.name: f.read_text() for f in sorted(out_dir.glob('*.tf'))
        }
    return _OUTPUTS[case]


def _site_rows(case: str) -> list:
    """The site data the run wrote, read through the rule that declares the row shape.

    A run that names no site value writes no file, so the reader returns no rows for it.
    """
    path = _out_dir(case) / site_data.SITE_DATA_FILE
    return site_data.parse_rows(path.read_text(encoding='utf-8')) if path.is_file() else []


@pytest.mark.parametrize('case', list(CASES))
def test_the_declaration_set_is_the_credentials_plus_the_site_values(case):
    """No dead variable survives: the declaration set is the credentials plus the values the table
    mapped (F6.6), and the file and the data read the same run.
    """
    declared = set(VAR_DECL_RE.findall(_generate(case)['variables.tf']))
    site = {name for row in _site_rows(case) for name in row['variables']}
    assert declared == set(CREDENTIALS) | site, (
        f'{case}: variables.tf declares {sorted(declared)}; expected the credentials plus '
        f'{sorted(site)}')


@pytest.mark.parametrize('case', list(CASES))
def test_every_declared_variable_is_consumed(case):
    """Every `variable "X"` has a `var.X` reference in the generated output.

    The rule lives in `sanity_checks.py`, so the conversion gate and this test
    share it (F4.1).
    """
    findings = sanity_checks.check_variables(_generate(case))
    assert findings == [], f'{case}: ' + ', '.join(f.render() for f in findings)


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
