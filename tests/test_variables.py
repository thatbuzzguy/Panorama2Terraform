"""F2.10: clean generated config - every emitted variable is consumed.

The generated `variables.tf` declares the names the run named, and the provider block in `provider.tf`
consumes each one in the same unit directory (`docs/CODEBASE_ASSEMBLY.md` §14). No dead variables: a
declared variable that no `.tf` file references is a failure. (The old `device_group` variable was dead: v2
location is derived per resource from the source XML, so no global device-group variable has a consumer.)

F6.6 adds the second half of the declaration set: the site values the value-to-variable table mapped. The
set is read through `site_data.parse_rows`, so the file and the data cannot disagree.

F7.1 adds the sensitive rule: `sensitive = true` is the table's `reference_only` row, so a name that is not
in the table is never a secret.

F7.7 adds the second way a reference-only name is named: a `sensitive` field the run read inside an entry
cannot name itself, so the name is the §5 name of the entry that holds it, and the declaration set holds that
name for the run that read it.

F6.10.4 adds the third part of the declaration set: a name the table records with no value for it, because the
tool cannot read the fact it names. The set is read through the table and through the provider block that
references it.

The credential rule (`docs/CODEBASE_ASSEMBLY.md` §11) is the fourth part, stated once: the credential is the
key, the run takes it from the environment, and the provider reads that same environment at plan time, so the
run declares no credential and writes no credential value. The host is the fact the run names for every unit,
and the provider block prints it through the table. Pins, one per part of the rule: the declaration set holds
no name a table row states for a credential, the provider block prints the names the table states, and no
printed argument is one the pinned schema marks `sensitive`.
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
import source_fetch
from conftest import FIXTURES_DIR, SAMPLE_CONFIG, SRC_DIR, file_text, parts, run_script, tf_files

CASES = {
    "sample": SAMPLE_CONFIG,
    "kitchen_sink": FIXTURES_DIR / "kitchen_sink.xml",
    # F7.7: the fixture that states an auth profile at each of the four routing levels, so the run records a
    # reference-only name for a field it read inside an entry.
    "auth_profile": FIXTURES_DIR / "auth_profile.xml",
}

VAR_DECL_RE = re.compile(r'variable\s+"([A-Za-z0-9_]+)"')

# One argument line inside a provider block, at the block's own level. A comment line is not an argument.
PROVIDER_BLOCK_RE = re.compile(r'provider\s+"panos"\s*\{(.*?)\n\}', re.S)
PROVIDER_ARG_RE = re.compile(r'^  ([a-z0-9_]+)\s*=', re.M)

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
    """F6.10.4 and §11: the names the table declares with no value, read through the table.

    A name the tool cannot fill is a declaration only for the units whose provider block prints it, so the
    reader keeps the names one run actually references. `provider.tf` is the unit's file, so the file set is
    the unit set.
    """
    named = {naming.variable_name(field) for field, shape in resource_mapping.VALUE_VARIABLES.items()
             if shape == resource_mapping.OPERATOR_SUPPLIED}
    return {name for path, text in _generate(case).items()
            if Path(path).name == 'provider.tf'
            for name in named if f'var.{name}' in text}


def _provider_arguments(case: str) -> dict[str, set[str]]:
    """The arguments one provider block states, keyed by the unit directory the file names (F2.10, §14).

    The gate's block reader serves `resource`, `data`, `import` and `action`, so this reader is the provider
    form of the same rule: the block's own level, one argument per line, no comment.
    """
    blocks = {}
    for path, text in parts(_generate(case), 'provider.tf').items():
        block = PROVIDER_BLOCK_RE.search(text)
        assert block, path
        blocks[Path(path).parent.name] = set(PROVIDER_ARG_RE.findall(block.group(1)))
    return blocks


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
        parts_list = []
        for index, segment in enumerate(segments):
            parts_list.append(spell(segment))
            walked = resource_mapping.PROTOCOL_SHAPE.get('/'.join(segments[:index + 1]))
            if walked and walked['shape'] == 'string_list':
                parts_list.append('entry')
        xml_path = '/'.join(parts_list)
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
def test_the_declaration_set_is_the_names_the_run_named(case, converter_module):
    """No dead variable survives: the declaration set is the values the table mapped (F6.6), the names the
    table records with no value for it (F6.10.4, §11), and the reference names (F7.7). The file and the data
    read the same run.

    §11: the table holds no row for a credential, so the set cannot hold one, and the pin states no name list:
    it reads the table's shape words and the naming rule.
    """
    # F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): `variables.tf` is the unit's file, so the declaration
    # set is the union across the unit set, read in path order.
    declared = set(VAR_DECL_RE.findall(file_text(_generate(case), 'variables.tf')))
    site = {name for row in _site_rows(case) for name in row['variables']}
    assert declared == site | _held_names(case) | _reference_names(case, converter_module), (
        f'{case}: variables.tf declares {sorted(declared)}; expected '
        f'{sorted(site)} plus {sorted(_held_names(case))} plus '
        f'{sorted(_reference_names(case, converter_module))}')
    # A field cannot name itself (F7.7), and §11 states no credential row, so no declaration is named by a
    # table field the provider marks sensitive.
    reference_fields = {field for field, shape in resource_mapping.VALUE_VARIABLES.items()
                        if shape == resource_mapping.REFERENCE_ONLY}
    assert not declared & reference_fields, (case, declared & reference_fields)


@pytest.mark.parametrize('case', list(CASES))
def test_every_declared_variable_is_consumed(case):
    """Every `variable "X"` has a `var.X` reference in the generated output.

    The rule lives in `sanity_checks.py`, so the conversion gate and this test
    share it (F4.1).
    """
    findings = sanity_checks.check_variables(_generate(case))
    assert findings == [], f'{case}: ' + ', '.join(f.render() for f in findings)


@pytest.mark.parametrize('case', list(CASES))
def test_the_provider_block_prints_only_the_names_the_table_states(case):
    """§11: the block's arguments are the rows the table states for it, read through the table and the naming
    rule, so no name list decides a provider argument and the run states no credential argument.

    The host row is read by every unit, because a unit is one plan against one state and a plan needs the host
    it plans against (§14). The serial row is read only by a unit whose manifest row names a device, because a
    declaration with no consumer is a finding (F6.10.4, F2.10).
    """
    provider_arguments = {naming.variable_name(field) for field, shape in
                          resource_mapping.VALUE_VARIABLES.items()
                          if shape == resource_mapping.OPERATOR_SUPPLIED}
    assert provider_arguments, 'the table states no provider argument'
    blocks = _provider_arguments(case)
    assert blocks, f'{case}: no provider block'
    for unit, arguments in blocks.items():
        assert arguments <= provider_arguments, (case, unit, arguments)
    host = naming.variable_name('hostname')
    for unit, arguments in blocks.items():
        assert host in arguments, (case, unit, arguments)
    assert host in provider_arguments, provider_arguments


@pytest.mark.parametrize('case', list(CASES))
def test_no_provider_block_argument_is_one_the_provider_marks_sensitive(case, provider_schemas):
    """Measured against the pinned provider: the block prints only optional arguments, and none of them is one
    the provider marks `sensitive` (§11).

    No argument is required, so a block that states only the facts the run names is a complete block. The two
    `sensitive` arguments are the credential path the provider takes when the operator does not use the
    environment, which is not the path the codebase takes.
    """
    block = provider_schemas.get('provider') or provider_schemas.get('provider_config_block')
    assert block, 'the schema names no provider configuration block'
    arguments = block.get('block', {}).get('attributes', {})
    assert arguments, 'the provider declares no arguments'
    assert not block.get('block', {}).get('required'), 'no provider argument is required'
    sensitive = {name for name, argument in arguments.items() if argument.get('sensitive')}
    assert sensitive, 'the provider marks no argument sensitive'
    for unit, printed in _provider_arguments(case).items():
        assert not printed & sensitive, (case, unit, printed & sensitive)
        for name in printed:
            assert name in arguments, (case, unit, name)
            assert not arguments[name].get('required'), (case, unit, name)


@pytest.mark.parametrize('case', list(CASES))
def test_the_generated_block_names_the_environment_the_fetch_layer_reads(case):
    """§11: one statement, one name. The generated provider block names the environment the provider reads at
    plan time, and `source_fetch.py` is the only tool module that states it, so the generator reads it through
    the module that owns the key rule instead of restating it.
    """
    for path, text in parts(_generate(case), 'provider.tf').items():
        assert source_fetch.API_KEY_ENV in text, path
    stating = [path.name for path in sorted(SRC_DIR.glob('*.py'))
               if path.name != 'source_fetch.py' and source_fetch.API_KEY_ENV in path.read_text(encoding='utf-8')]
    assert stating == [], stating


@pytest.mark.parametrize('case', list(CASES))
def test_a_variable_block_is_sensitive_when_the_table_marks_its_name_reference_only(case, converter_module):
    """F7.1: `sensitive = true` follows `VALUE_VARIABLES`, not a name list.

    A reference-only name is the §5 name of the entry that holds a field the table marks `sensitive` (F7.7),
    because a value cannot name itself. The pin reads it through the table and the naming rule, so a name
    outside the two is never a secret.

    §11: an `operator_supplied` name is a fact the tool cannot read, and a fact is not a secret, so the
    marking stays the `reference_only` row's rule alone and no name list appears.
    """
    files = _generate(case)
    text = file_text(files, 'variables.tf')
    blocks = re.findall(
        r'variable\s+"([A-Za-z0-9_]+)"\s*\{(.*?)\n\}', text, re.S)
    reference_fields = {field for field, row in resource_mapping.VALUE_VARIABLES.items()
                        if row == resource_mapping.REFERENCE_ONLY}
    assert reference_fields, 'the table states no reference-only row'
    entry_names = _reference_names(case, converter_module)
    # §11: the table holds no credential row, so a field the provider marks sensitive is never a declaration.
    declared = {name for name, _ in blocks}
    assert not declared & reference_fields, (case, declared & reference_fields)
    for name, body in blocks:
        marking = 'sensitive' if 'sensitive' in body else 'not sensitive'
        assert ('sensitive' in body) == (name in entry_names), (
            f'{case}: variable {name!r} sensitive marking is unexpected: {marking}')
    # F6.10.4 and §11: `operator_supplied` is the shape word for a name the run cannot fill, and it states no
    # marking, so the declarations for the provider arguments hold none.
    assert resource_mapping.OPERATOR_SUPPLIED != resource_mapping.REFERENCE_ONLY
    named = [body for name, body in blocks
            if name in {naming.variable_name(field) for field, row
                        in resource_mapping.VALUE_VARIABLES.items()
                        if row == resource_mapping.OPERATOR_SUPPLIED}]
    assert named, (case, 'the run declares the names the tool cannot read')
    assert all('sensitive' not in body for body in named), (case, named)
