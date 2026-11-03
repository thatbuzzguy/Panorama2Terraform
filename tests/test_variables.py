"""F2.10: clean generated config - every emitted variable is consumed.

The generated variables.tf declares the credential variables, and the provider
block in provider.tf consumes all of them. No dead variables: a declared
variable that no .tf file references is a failure. (The old `device_group`
variable was dead: v2 location is derived per resource from the source XML, so
no global device-group variable has a consumer.)

F6.6 adds the second half of the declaration set: the site values the
value-to-variable table mapped. The set is read through `site_data.parse_rows`,
so the file and the data cannot disagree.

F7.1 adds the sensitive rule: `sensitive = true` is the table's `reference_only` row, so a name
that is not in the table is never a secret.

F7.7 adds the second way a reference-only name is named: a `sensitive` field the run read inside an entry
cannot name itself, so the name is the §5 name of the entry that holds it, and the declaration set holds that
name for the run that read it.

F6.10.4 adds the third part of the declaration set: a name the table records with no value for it, because the
tool cannot read the fact it names. The set is read through the table and through the provider block that
references it.
"""

import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import entry_coverage
import naming
import resource_mapping
import sanity_checks
import site_data
from conftest import FIXTURES_DIR, SAMPLE_CONFIG, file_text, run_script, tf_files

CASES = {
    "sample": SAMPLE_CONFIG,
    "kitchen_sink": FIXTURES_DIR / "kitchen_sink.xml",
    # F7.7: the fixture that states an auth profile at each of the four routing levels, so the run records a
    # reference-only name for a field it read inside an entry.
    "auth_profile": FIXTURES_DIR / "auth_profile.xml",
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
        _OUTPUTS[case] = tf_files(out_dir)
    return _OUTPUTS[case]


def _site_rows(case: str) -> list:
    """The site data the run wrote, read through the rule that declares the row shape.

    A run that names no site value writes no file, so the reader returns no rows for it.
    """
    path = _out_dir(case) / site_data.SITE_DATA_FILE
    return site_data.parse_rows(path.read_text(encoding='utf-8')) if path.is_file() else []


def _held_names(case: str) -> set[str]:
    """F6.10.4: the names the table declares with no value, read through the table.

    A name the tool cannot fill is a declaration only for the units whose provider block prints it, so the
    reader keeps the names one run actually references. `provider.tf` is the unit's file, so the file set is
    the unit set.
    """
    named = {naming.variable_name(field) for field, shape in resource_mapping.VALUE_VARIABLES.items()
             if shape == resource_mapping.OPERATOR_SUPPLIED}
    return {name for path, text in _generate(case).items()
            if Path(path).name == 'provider.tf'
            for name in named if f'var.{name}' in text}


def _reference_names(case: str, converter_module) -> set[str]:
    """F7.7: the names a run records for a `sensitive` field it read inside an entry, read through the table.

    A `sensitive` value cannot name itself, so the name is the §5 name of the entry that holds the field: an
    entry names itself when the field is its own, and a level inside an entry names the entry that holds it. The
    pin walks the fixture through the `sensitive` sets of the `PROTOCOL_SHAPE` rows, through the `string_list`
    shape, which is the table's way of saying the object is an entry, and through `_protocol_xml_name`, the one
    rule that turns a table name into the element the input spells, so it states no name list of its own. A
    field with no value names nothing, because the parse records nothing for it, and a case with no protocol
    object names nothing.
    """
    root = ET.fromstring(CASES[case].read_text(encoding='utf-8'))
    spell = converter_module.PanoramaParser._protocol_xml_name
    parents = {child: parent for parent in root.iter() for child in parent}
    names = set()
    for path, row in sorted(resource_mapping.PROTOCOL_SHAPE.items()):
        if not row['sensitive']:
            continue
        # A `string_list` row reads entries, so the input holds one `entry` element for each object the row
        # names; every other row reads the level itself, so the entry that names the reference is the one that
        # holds the level.
        segments = path.split('/')
        parts = []
        for index, segment in enumerate(segments):
            parts.append(spell(segment))
            walked = resource_mapping.PROTOCOL_SHAPE.get('/'.join(segments[:index + 1]))
            if walked and walked['shape'] == 'string_list':
                parts.append('entry')
        xml_path = '/'.join(parts)
        for obj in root.findall(f'.//virtual-router/entry/{xml_path}'):
            for field in row['sensitive']:
                value = obj.find(spell(field))
                if value is None or value.text in entry_coverage.EMPTY_FIELD_VALUES:
                    continue
                holder = obj
                while holder is not None and holder.tag != 'entry':
                    holder = parents.get(holder)
                if holder is not None:
                    names.add(naming.variable_name(holder.get('name')))
    return names


@pytest.mark.parametrize('case', list(CASES))
def test_the_declaration_set_is_the_credentials_plus_the_site_values(case, converter_module):
    """No dead variable survives: the declaration set is the credentials plus the values the table
    mapped (F6.6), and the file and the data read the same run.

    F6.10.4: the table also names a value the run cannot read, so the declaration set holds the names it
    declares with no value for the units whose provider block references them. F7.7: a `sensitive` field the
    run read inside an entry names a variable after the entry, so the set also holds those names.
    """
    # F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): `variables.tf` is the unit's file, so the declaration
    # set is the union across the unit set, read in path order.
    declared = set(VAR_DECL_RE.findall(file_text(_generate(case), 'variables.tf')))
    site = {name for row in _site_rows(case) for name in row['variables']}
    assert declared == set(CREDENTIALS) | site | _held_names(case) | _reference_names(case, converter_module), (
        f'{case}: variables.tf declares {sorted(declared)}; expected the credentials plus '
        f'{sorted(site)} plus {sorted(_held_names(case))} plus '
        f'{sorted(_reference_names(case, converter_module))}')


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
    provider = file_text(files, 'provider.tf')
    for name in CREDENTIALS:
        assert f'var.{name}' in provider, (
            f'{case}: provider block does not consume var.{name}')
    # The old commented-out wiring is gone.
    assert '# hostname = var.panos_hostname' not in provider


@pytest.mark.parametrize('case', list(CASES))
def test_a_variable_block_is_sensitive_when_the_table_marks_its_name_reference_only(case, converter_module):
    """F7.1: `sensitive = true` follows `VALUE_VARIABLES`, not a name list.

    A reference-only name is either the field the table marks `sensitive` (the credential `password`), or the
    §5 name of the entry that holds such a field (F7.7), because a value cannot name itself. The pin reads both
    through the table and the naming rule, so a name outside the two is never a secret.
    """
    files = _generate(case)
    text = file_text(files, 'variables.tf')
    blocks = re.findall(
        r'variable\s+"([A-Za-z0-9_]+)"\s*\{(.*?)\n\}', text, re.S)
    reference_only = {field for field, row in resource_mapping.VALUE_VARIABLES.items()
                      if row == resource_mapping.REFERENCE_ONLY}
    entry_names = _reference_names(case, converter_module)
    for name, body in blocks:
        # A variable name is the §5 name of a field: `panos_password` is the credential field `password`.
        field = name[len('panos_'):] if name.startswith('panos_') else name
        marking = 'sensitive' if 'sensitive' in body else 'not sensitive'
        assert ('sensitive' in body) == (field in reference_only or name in entry_names), (
            f'{case}: variable {name!r} sensitive marking is unexpected: {marking}')
    # F6.10.4: `operator_supplied` is the shape word for a name the run cannot fill, and it states no marking,
    # so the declaration for `target` holds none. A serial is not a secret.
    assert resource_mapping.OPERATOR_SUPPLIED != resource_mapping.REFERENCE_ONLY
    named = [body for name, body in blocks if name == 'target']
    assert all('sensitive' not in body for body in named), (case, named)
