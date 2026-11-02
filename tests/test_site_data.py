"""F6.6 the site data layer: the pinned table, the site row, and the `.tfvars` written from it.

Seven groups, one per rule in `site_data.py`, `resource_mapping.VALUE_VARIABLES`, and
`docs/CODEBASE_ASSEMBLY.md` §9:

1. The pinned table: one row per location field `LOCATION_SCHEMA` declares, plus one row per
   reference-only name (F7.1), and only the device field maps to a variable.
2. The site row: the declared shape, the identity order, the join to the manifest on `directory`,
   and the refusals `parse_rows` states.
3. The `.tfvars` writer: the bytes for a string and for a list, the sort, the dedupe, and the
   content rule.
4. The device name as a variable, and the device that names none.
5. The declaration set: the file, the data, and the `.tfvars` read the same run.
6. The two gate rules, and the corpus that trips neither.
7. Determinism, and the gate rule that reads the record through this module and compares the printed
   form, and the rule that no report names a site field, with the `README.md` file-inventory label as the one
   exception (F6.10.4).

The golden bytes pin the print shape (`tests/test_golden_files.py`), and the device-name rule is
pinned here for a device the parse names. Every test runs offline.
"""

import inspect
import json
import subprocess
from pathlib import Path

import pytest

import entry_coverage
import import_blocks
import naming
import resource_mapping
import sanity_checks
import site_data
import unit_manifest
from conftest import FIXTURES_DIR, GOLDEN_DIR, SAMPLE_CONFIG, file_text, parts, run_script, tf_files

CONVERTER = 'panorama_to_terraform.py'
MANIFEST = unit_manifest.MANIFEST_FILE
DEVICE = 'fw-2.example.com'
NO_DEVICE = 'localhost.localdomain'
KITCHEN = 'kitchen_sink.xml'

# The fixtures that name a site value, with the rows the run writes in identity order. A fixture
# that starts naming a value must be added here in the same change, so no fixture can become a
# silent false positive.
CORPUS_ROWS = {
    'dependency_wiring.xml': [('vsys1_a62792be', {'device1': 'device1'})],
    KITCHEN: [
        ('fw_2_example_com_5cef6fb6', {naming.variable_name(DEVICE): DEVICE}),
        ('vsys1_53549b38', {naming.variable_name(DEVICE): DEVICE}),
        ('vsys2_803b06c0', {naming.variable_name(DEVICE): DEVICE}),
    ],
    'multi_device_templates.xml': [
        ('fw_1_example_com_21a67a9f', {'fw_1_example_com': 'fw-1.example.com'}),
        ('fw_2_example_com_5cef6fb6', {naming.variable_name(DEVICE): DEVICE}),
    ],
    'reference_cycle.xml': [
        ('fw_a_example_com_4daa3d43', {'fw_a_example_com': 'fw-a.example.com'}),
        ('fw_b_example_com_f80a1db9', {'fw_b_example_com': 'fw-b.example.com'}),
    ],
    'report_grouping.xml': [('fw_2_example_com_5cef6fb6', {naming.variable_name(DEVICE): DEVICE})],
    'virtual_routers.xml': [
        ('fw_1_example_com_21a67a9f', {'fw_1_example_com': 'fw-1.example.com'}),
        ('vsys2_bbdff6d9', {'fw_1_example_com': 'fw-1.example.com'}),
    ],
}


def _run(source: Path, out_dir: Path, extra: tuple = ()) -> subprocess.CompletedProcess:
    """Run the converter as a script and return the process result."""
    return run_script(CONVERTER, str(source), '--output-dir', str(out_dir), *extra)


def _rows(out_dir: Path) -> list:
    """The site data the run wrote, read through the rule that declares the row shape."""
    path = out_dir / site_data.SITE_DATA_FILE
    return site_data.parse_rows(path.read_text(encoding='utf-8'))


def _pairs(rows: list) -> list:
    """The site rows as (`directory`, `variables`), the two declared fields."""
    return [(row['directory'], row['variables']) for row in rows]


def _printed_forms(out_dir: Path) -> dict:
    """The printed form of every unit the run wrote, keyed by the path from the output directory.

    F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): the printed form is the unit's file, so the run writes one
    per unit that names a value, and each holds only the printed form of that unit's row.
    """
    return {str(p.relative_to(out_dir)): p.read_text(encoding='utf-8')
            for p in sorted(out_dir.rglob(site_data.TFVARS_FILE))}


def _value_lines(text: str) -> list:
    """The `.tfvars` lines that state a value, without the header."""
    return [line for line in text.split('\n') if line and not line.startswith('#')]


def _tfvars_lines(out_dir: Path) -> list:
    """The value lines the run printed, across the unit set. Two units that name the same value hold the
    same line, so the helper names the distinct lines.
    """
    lines = set()
    for text in _printed_forms(out_dir).values():
        lines.update(_value_lines(text))
    return sorted(lines)


# --- 1. the pinned table ------------------------------------------------------

# The names the provider schema marks `sensitive` inside the protocol object (F7.1).
# tests/test_protocol_object.py pins this against the live provider schema.
REFERENCE_ONLY_NAMES = {'secret', 'key', 'password'}


def test_the_table_covers_every_field_the_location_can_state():
    """The table is complete: one row per field `LOCATION_SCHEMA` declares, plus one row per
    reference-only name (F7.1), plus the one row for a fact the location cannot state because the export
    holds no value for it (`target`, F6.10.4), so a field cannot gain a row without the test naming it.
    """
    fields = {field for scopes in resource_mapping.LOCATION_SCHEMA.values()
              for sub_block in scopes.values() for field in sub_block}
    assert set(resource_mapping.VALUE_VARIABLES) == fields | REFERENCE_ONLY_NAMES | {'target'}, fields


def test_only_the_device_field_maps_to_a_variable():
    """The table states what the block prints for each field, and only `ngfw_device` prints as a variable
    that holds a value (§9 rule 1). A reference-only name is the other case: the block prints the reference to
    a variable the run declares, and the value itself is never in the table (F7.1).

    F6.10.4: `target` names a variable and holds no value, because the export states a device as a hostname,
    so no serial reaches the parse and the operator supplies the value.
    """
    variable, literal, reference, named = (
        resource_mapping.VARIABLE, resource_mapping.LITERAL, resource_mapping.REFERENCE_ONLY,
        resource_mapping.OPERATOR_SUPPLIED)
    assert {
        'ngfw_device': variable,
        'name': literal,
        'vsys': literal,
        'panorama_device': literal,
        'rulebase': literal,
        'target': named,
        'secret': reference,
        'key': reference,
        'password': reference,
    } == resource_mapping.VALUE_VARIABLES
    assert variable != named, 'the device field holds a value; the run names `target` and holds none'


def test_the_generator_prints_a_value_through_the_table(converter_module):
    """One shape rule: `location_field` delegates to `printed_value`, so a printed value's shape
    cannot be decided in two places (F7.1).
    """
    source = inspect.getsource(converter_module.TerraformGenerator.location_field)
    assert 'self.printed_value(' in source, source
    assert 'VALUE_VARIABLES' not in source, source


def test_the_table_holds_no_property():
    """A property at the block's own level is the entry's content, not a site value, so the table
    holds location fields and the reference-only names only (`docs/CODEBASE_ASSEMBLY.md` §9 rule 2).
    A reference-only name is not a property either: the block prints the reference to a variable, and
    no `.tf` holds the value (F7.1). `panos_template_variable` prints its value as
    the export states it, and no variable is declared for it.
    F6.10.4 adds one row for a fact the export cannot state: `target` names the device the unit plans
    against, so the run names the variable and holds no value for it. It is not a property.
    """
    allowed = {'name', 'ngfw_device', 'panorama_device', 'rulebase', 'vsys', 'target'} | REFERENCE_ONLY_NAMES
    assert all(field in allowed for field in resource_mapping.VALUE_VARIABLES), resource_mapping.VALUE_VARIABLES
    assert resource_mapping.VALUE_VARIABLES['target'] == resource_mapping.OPERATOR_SUPPLIED, \
        'the run names the variable, the operator supplies the value'
    assert not REFERENCE_ONLY_NAMES & {prop for row in resource_mapping.COVERAGE_MATRIX
                                       for prop in row['properties']}, \
        'a reference-only name is printed as a reference, not as a property'
    # F6.10.3: `scope.tf` is the unit's file, so the golden set holds one per unit that has a scope block.
    scope = ''.join(p.read_text(encoding='utf-8')
                    for p in sorted((GOLDEN_DIR / 'kitchen_sink').rglob('scope.tf')))
    assert 'panos_template_variable' in scope, 'the kitchen-sink case declares a template variable'
    assert 'var.' not in scope, scope
    assert '"10.9.9.9/32"' in scope, scope


# --- 2. the site row and the join ---------------------------------------------

def test_the_corpus_rows_are_pinned(tmp_path):
    """One row per site that names a value, in identity order, read back as data. A fixture that
    names no value writes no file, so the assertion names the six that do.
    """
    for name, expected in sorted(CORPUS_ROWS.items()):
        out = tmp_path / name
        assert _run(FIXTURES_DIR / name, out).returncode == 0, name
        assert _pairs(_rows(out)) == expected, name


def test_the_sample_run_names_no_value_and_writes_no_file(tmp_path):
    """A run that names no site value writes no site data and no `.tfvars`, the rule the report
    files and the other data files use.
    """
    out = tmp_path / 'sample'
    assert _run(SAMPLE_CONFIG, out).returncode == 0
    assert not (out / site_data.SITE_DATA_FILE).is_file()
    assert not (out / site_data.TFVARS_FILE).is_file()


def test_the_row_joins_to_the_manifest_on_directory(tmp_path):
    """The join is the manifest row: `directory` is the name `unit_manifest.directory_name` decides
    for the unit the row names, so no second unit rule appears in this module.
    """
    out = tmp_path / 'kitchen'
    assert _run(FIXTURES_DIR / KITCHEN, out).returncode == 0
    manifest = unit_manifest.parse_rows((out / MANIFEST).read_text(encoding='utf-8'))
    rows = _rows(out)
    assert rows, 'the kitchen-sink run names a device, so it must write the site data'
    for row in rows:
        named = [entry for entry in manifest if entry['directory'] == row['directory']]
        assert len(named) == 1, f'{row["directory"]} names no manifest row'
        facts = tuple(named[0][key] for key in unit_manifest.FACT_KEYS)
        assert row['directory'] == unit_manifest.directory_name(facts, naming.sanitize)


def test_parse_rows_refuses_a_row_that_is_not_the_declared_shape():
    """The record is data, so a reader cannot fall back to prose: an extra field, a missing field, a
    value that is not a string or a list, and a name that is not the §5 shape of its value are
    refusals.
    """
    good = {'directory': 'vsys1_a62792be', 'variables': {'device1': 'device1'}}
    assert site_data.parse_rows(site_data.render([good])) == [good]
    bad_rows = [
        dict(good, source='tests/fixtures/dependency_wiring.xml'),
        {'directory': 'vsys1_a62792be'},
        {'variables': {'device1': 'device1'}},
        {'directory': '', 'variables': {'device1': 'device1'}},
        {'directory': 'vsys1_a62792be', 'variables': ['device1']},
        {'directory': 'vsys1_a62792be', 'variables': {'device1': 1}},
        {'directory': 'vsys1_a62792be', 'variables': {'device1': ['device1', 2]}},
        # A name that is not the §5 shape of its value: the name is the mapping result, not a choice.
        {'directory': 'vsys1_a62792be', 'variables': {'device1': 'device-1'}},
        {'directory': 'vsys1_a62792be', 'variables': {'': 'device1'}},
    ]
    for row in bad_rows:
        with pytest.raises(ValueError):
            site_data.parse_rows(json.dumps([row]))
    with pytest.raises(ValueError):
        site_data.parse_rows('not a list of rows')


def test_the_fields_print_in_the_declared_order():
    """The row shape is fixed, so a reader does not guess, the rows keep the order the run wrote, and
    no field states a timestamp or a path.
    """
    assert site_data.ROW_FIELDS == ('directory', 'variables')
    rows = [
        {'directory': 'vsys2_803b06c0', 'variables': {naming.variable_name(DEVICE): DEVICE}},
        {'directory': 'fw_2_example_com_5cef6fb6', 'variables': {naming.variable_name(DEVICE): DEVICE}},
    ]
    printed = site_data.render(rows)
    assert list(site_data.parse_rows(printed)[0]) == list(site_data.ROW_FIELDS)
    assert [row['directory'] for row in site_data.parse_rows(printed)] == [
        row['directory'] for row in rows], printed
    assert not any(field in printed for field in ('timestamp', 'path', 'generated_at')), printed


# --- 3. the `.tfvars` writer ---------------------------------------------------

def test_the_tfvars_bytes_for_a_string_value():
    """One line per variable, in name order, and the escape set is the one `import_blocks.unescape`
    reads back, so no second escape rule appears.
    """
    rows = [{'directory': 'vsys1_a62792be', 'variables': {'device1': 'device1'}}]
    text = site_data.render_tfvars(rows)
    line = f"device1 = {site_data.value_text('device1')}\n"
    assert line in text, text
    assert text.endswith(line), text
    # The writer's quoted form is the form the one escape rule reads back, so no second escape rule
    # appears: the block value and the `.tfvars` value state the same string.
    for value in ('device1', 'a\tb', 'say "hi"', 'back\\slash'):
        assert import_blocks.unescape(site_data.value_text(value)[1:-1]) == value, value


def test_a_list_prints_inline_and_an_empty_list_prints_empty():
    """The row shape declares a list, so the writer prints one; the table maps no field to a list
    today, so a corpus run writes only strings.
    """
    assert site_data.value_text(['a', 'b']) == '[ "a", "b" ]'
    assert site_data.value_text([]) == '[]'
    rows = [{'directory': 'vsys1_a62792be', 'variables': {'tags': ['a', 'b']}}]
    assert 'tags = [ "a", "b" ]' in site_data.render_tfvars(rows)


def test_a_value_that_is_neither_a_string_nor_a_list_is_a_refusal():
    """The row shape declares no other kind, so the writer refuses it instead of guessing a shape."""
    for value in (1, None, {'a': 'b'}, ['a', 2]):
        with pytest.raises(ValueError):
            site_data.value_text(value)


def test_a_name_two_rows_state_prints_one_line():
    """The name is the §5 shape of the value, so one value cannot produce two names and the file
    cannot state one name twice. The lines are in name order across the whole file, and one name that
    two rows state with two values is a refusal.
    """
    name = naming.variable_name(DEVICE)
    rows = [
        {'directory': 'vsys1_a62792be', 'variables': {name: DEVICE}},
        {'directory': 'vsys2_803b06c0', 'variables': {name: DEVICE}},
    ]
    text = site_data.render_tfvars(rows)
    assert text.count(f'{name} = {site_data.value_text(DEVICE)}') == 1, text

    lines = [line for line in site_data.render_tfvars([
        {'directory': 'vsys2_803b06c0', 'variables': {'scope_b': 'scope-b'}},
        {'directory': 'vsys1_a62792be', 'variables': {'scope_a': 'scope-a'}},
    ]).split('\n') if line and not line.startswith('#')]
    assert lines == ['scope_a = "scope-a"', 'scope_b = "scope-b"'], lines

    with pytest.raises(ValueError):
        site_data.render_tfvars([
            {'directory': 'vsys1_a62792be', 'variables': {'tags': ['a']}},
            {'directory': 'vsys2_803b06c0', 'variables': {'tags': ['b']}},
        ])


def test_the_tfvars_file_is_written_only_when_it_has_content(tmp_path):
    """The content rule, and the file name keeps the operator's own file: the tool never writes
    `terraform.tfvars`, and the generated file names no credential (§11).
    """
    out = tmp_path / 'kitchen'
    assert _run(FIXTURES_DIR / KITCHEN, out).returncode == 0
    assert site_data.TFVARS_FILE == 'site.auto.tfvars'
    assert not (out / 'terraform.tfvars').is_file()
    printed = _printed_forms(out)
    assert len(printed) == len(_rows(out)), 'one printed form per site row, in the unit its row names'
    line = f'{naming.variable_name(DEVICE)} = {site_data.value_text(DEVICE)}'
    for path, text in printed.items():
        assert _value_lines(text) == [line], (path, text)
        assert 'panos_' not in text, path


def test_a_name_the_tool_cannot_fill_writes_no_row_and_no_line(tmp_path):
    """F6.10.4 rule 3: a row is a value the run read (§9 rule 2), so the record holds no row for `target`
    and the printed form holds no line for it, even though the run declares the variable for it.
    """
    out = tmp_path / 'kitchen'
    assert _run(FIXTURES_DIR / KITCHEN, out).returncode == 0
    rows = _rows(out)
    assert rows, 'the kitchen sink names a device value'
    for row in rows:
        assert 'target' not in row['variables'], row
    for path, text in _printed_forms(out).items():
        assert not any(line.startswith('target =') for line in _value_lines(text)), (path, text)
    assert len(_printed_forms(out)) == len(rows), 'no printed form for a name with no row'


# --- 4. the device name as a variable ------------------------------------------

def test_the_emitter_prints_a_mapped_field_as_the_table_says(converter_module, tmp_path):
    """The print site is the only place the shape is decided, and it records the pair for the site
    that applies the table, the way `name_ref` records a reference name.
    """
    gen = converter_module.TerraformGenerator(str(tmp_path))
    obj = {'name': 'trust', 'template': 'HQ-Networks', 'vsys_device': DEVICE}
    text = gen.location_block('panos_zone', obj)
    assert f'      ngfw_device = {naming.variable_text(DEVICE)}' in text, text
    assert gen.value_variables() == {unit_manifest.facts_of(obj): {naming.variable_name(DEVICE): DEVICE}}


def test_a_field_the_table_does_not_map_still_prints_as_a_literal(converter_module, tmp_path):
    """The table maps one field, so every other location field prints as the value the export states.
    This is the proof that the change is a mapping and not a style.
    """
    gen = converter_module.TerraformGenerator(str(tmp_path))
    obj = {'name': 'trust', 'template': 'HQ-Networks', 'vsys_device': DEVICE, 'vsys': 'vsys3'}
    text = gen.location_block('panos_zone', obj)
    assert '      name = "HQ-Networks"' in text, text
    assert '      vsys = "vsys3"' in text, text
    assert text.count('var.') == 1, text


def test_the_print_site_keeps_the_value_as_the_fact(converter_module, tmp_path):
    """`location_data` keeps the value, because the import id encodes the value and the provider
    parses the id, so a variable name is not a device name (§12).
    """
    gen = converter_module.TerraformGenerator(str(tmp_path))
    obj = {'name': 'vr', 'vsys_device': DEVICE}
    data = gen.location_data('panos_virtual_router', obj)
    assert data == {'ngfw': {'ngfw_device': DEVICE}}, data
    row = import_blocks.row('', 'panos_virtual_router', naming.sanitize(obj['name']), 'vr', data)
    assert import_blocks.decode_id(row['import_id'])['location'] == data, row
    block = gen.location_block('panos_virtual_router', obj)
    assert f'      ngfw_device = {naming.variable_text(DEVICE)}' in block, block


def test_a_device_that_names_no_device_names_no_variable(converter_module, tmp_path):
    """`localhost.localdomain` is never a location field (F3.5), so it never reaches the table and no
    site row states it.
    """
    gen = converter_module.TerraformGenerator(str(tmp_path))
    text = gen.location_block('panos_ethernet_interface', {'name': 'ethernet1/1',
                                                           'vsys_device': NO_DEVICE})
    assert NO_DEVICE not in text and 'var.' not in text, text
    assert gen.value_variables() == {}


def test_a_fact_the_tool_cannot_read_names_a_variable_and_holds_no_value(converter_module, tmp_path):
    """F6.10.4: `target` is the row the tool cannot fill, so `printed_value` records the name with no value
    and records the shape, the way F7.1 records a `reference_only` name.

    The name is the §5 rule applied to the field, because a fact the tool cannot read has no value to name
    it from. A row is a value the run read (§9 rule 2), so the record holds no row for it and the printed
    form holds no line for it.
    """
    gen = converter_module.TerraformGenerator(str(tmp_path))
    obj = {'name': 'vr', 'vsys_device': DEVICE}
    facts = unit_manifest.facts_of(obj)
    assert gen.printed_value('target', '', facts) == naming.variable_text('target'), 'the name is the field'
    # The recorded set holds the name with no value, so the accessor that reads the values returns none for
    # the unit, and `build_rows` writes no row for a unit with no value.
    assert gen.value_variables() == {facts: {}}, gen.value_variables()
    assert gen.value_shapes() == {facts: {'target': resource_mapping.OPERATOR_SUPPLIED}}, gen.value_shapes()


def test_the_provider_block_prints_target_only_for_a_unit_that_names_a_device(tmp_path):
    """F6.10.4 rule 4: the provider block is the consumer of the name, so it prints the reference for a unit
    whose manifest row names a device and prints none for a unit that names no device. The placeholder device
    names none (F3.5), so a run that names no device declares no `target` at all.
    """
    out = tmp_path / 'kitchen'
    assert _run(FIXTURES_DIR / KITCHEN, out).returncode == 0
    rows = {row['directory']: row for row in
            unit_manifest.parse_rows((out / MANIFEST).read_text(encoding='utf-8'))}
    seen = False
    for path, text in parts(tf_files(out), 'provider.tf').items():
        unit = Path(path).parent.name
        device = rows[unit]['vsys_device']
        names_a_device = bool(device) and device != NO_DEVICE
        assert ('target = var.target' in text) == names_a_device, (path, device)
        seen = seen or names_a_device
    assert seen, 'the kitchen sink names a device, so one provider block prints the reference'
    # The name is the §5 rule applied to the field, so the printed reference and the declared name agree.
    assert naming.variable_name('target') == 'target'
    """The golden bytes pin the shape: the kitchen-sink set prints the variable name for the device
    field in the four files that carry a device location, and the sample set names no device, so it
    holds no `var.` location field at all.
    """
    for path in sorted((GOLDEN_DIR / 'sample').rglob('*.tf')):
        assert 'ngfw_device = var.' not in path.read_text(encoding='utf-8'), path
    changed = sorted({path.name for path in (GOLDEN_DIR / 'kitchen_sink').rglob('*.tf')
                      if 'ngfw_device = var.' in path.read_text(encoding='utf-8')})
    assert changed == ['address_objects.tf', 'service_objects.tf', 'virtual_routers.tf',
                       'zones.tf'], changed
    # F6.10.4: `target` is printed only for a unit whose provider block names a device, so the golden set
    # holds the reference in three unit files and no target row in the sample set, which names no device.
    printed = sorted({Path(path).parent.name for path in (GOLDEN_DIR / 'kitchen_sink').rglob('provider.tf')
                      if 'target = var.target' in path.read_text(encoding='utf-8')})
    assert printed == ['fw_2_example_com_5cef6fb6', 'vsys1_53549b38', 'vsys2_803b06c0'], printed
    for path in sorted((GOLDEN_DIR / 'sample').rglob('provider.tf')):
        assert 'var.target' not in path.read_text(encoding='utf-8'), path
    # F6.10.3: `variables.tf` is the unit's file, so the declaration set is the union the run wrote,
    # one file per unit.
    declared = set()
    for path in sorted((GOLDEN_DIR / 'kitchen_sink').rglob('variables.tf')):
        declared.update(sanity_checks.VARIABLE_RE.findall(path.read_text(encoding='utf-8')))
    assert sorted(declared) == ['fw_2_example_com', 'panos_hostname', 'panos_password',
                                'panos_username', 'target'], declared


# --- 5. the declaration set ----------------------------------------------------

def test_the_file_the_data_and_the_tfvars_read_the_same_run(tmp_path):
    """`variables.tf` declares the values the run consumed, and the `.tfvars` states the same names,
    so the three cannot disagree.
    """
    out = tmp_path / 'kitchen'
    assert _run(FIXTURES_DIR / KITCHEN, out).returncode == 0
    site = {name for row in _rows(out) for name in row['variables']}
    declared = set(sanity_checks.VARIABLE_RE.findall(file_text(tf_files(out), 'variables.tf')))
    assert site <= declared, (site, declared)
    files = tf_files(out)
    findings = sanity_checks.check_variables(files)
    assert findings == [], [finding.render() for finding in findings]
    assert sorted(line.split(' = ')[0] for line in _tfvars_lines(out)) == sorted(site)


def test_the_declaration_file_is_written_after_the_emitters(converter_module):
    """The declaration set is the recorded pairs, so `main()` cannot write the file before the
    emitters run. The order rule for `scope.tf` is unchanged.
    """
    calls = inspect.getsource(converter_module.main)
    assert calls.index('generate_variables()') > calls.index('generate_address_objects'), calls
    assert calls.index('generate_variables()') < calls.index('generate_readme'), calls
    assert calls.index('generate_scope_objects') < calls.index('generate_address_objects'), calls


# --- 6. the two gate rules -----------------------------------------------------

def test_the_import_rule_compares_a_mapped_field_by_name():
    """The id keeps the value and the block prints the §5 name of it, so the rule compares the name
    for a field the table maps and the value for every other field.

    Two violation types: a block that prints the literal for a field the table maps, and a block whose
    value for an unmapped field is not the value the id states.
    """
    location = {'template': {'name': 'HQ-Networks', 'ngfw_device': DEVICE}}
    block = ('resource "panos_zone" "trust_00000000" {\n  location = {\n    template = {\n'
             f'      name = "HQ-Networks"\n      ngfw_device = {naming.variable_text(DEVICE)}\n'
             '    }\n  }\n  name = "trust"\n}\n')
    imports = ('import {\n  to = panos_zone.trust_00000000\n'
               f'  id = "{import_blocks.build_id(location, "trust")}"\n}}\n')
    assert sanity_checks.check_import_blocks({'imports.tf': imports, 'zones.tf': block}) == []

    # A block that prints the literal for a field the table maps is not the location the id states.
    literal_block = block.replace(naming.variable_text(DEVICE), site_data.value_text(DEVICE))
    findings = sanity_checks.check_import_blocks({'imports.tf': imports, 'zones.tf': literal_block})
    assert len(findings) == 1, findings
    assert findings[0].check == 'import_blocks' and findings[0].severity == sanity_checks.FAIL, findings
    assert 'id location is not the location the block states' in findings[0].detail, findings

    # An unmapped field is still compared by value, so the one reader keeps the block and the id on
    # the same location.
    other = block.replace('"HQ-Networks"', '"Other-Template"')
    findings = sanity_checks.check_import_blocks({'imports.tf': imports, 'zones.tf': other})
    assert len(findings) == 1, findings
    assert findings[0].check == 'import_blocks', findings


def test_the_variable_rule_reads_both_directions():
    """A declaration with no consumer, and a consumer with no declaration, are both findings. The
    second direction is what makes a generated declaration set checkable (F6.6).
    """
    files = {'variables.tf': 'variable "dead" {\n  type = string\n}\n\n'
                             'variable "used" {\n  type = string\n}\n',
             'main.tf': 'provider "panos" {\n  hostname = var.used\n}\n'}
    findings = sanity_checks.check_variables(files)
    assert len(findings) == 1, findings
    assert 'never consumed as var.dead' in findings[0].detail, findings
    orphan = {'main.tf': 'provider "panos" {\n  hostname = var.orphan\n}\n'}
    findings = sanity_checks.check_variables(orphan)
    assert len(findings) == 1, findings
    assert 'var.orphan names no variable this run declares' in findings[0].detail, findings
    both = {'variables.tf': 'variable "used" {\n  type = string\n}\n',
            'main.tf': 'provider "panos" {\n  hostname = var.used\n}\n'}
    assert sanity_checks.check_variables(both) == []


def test_the_corpus_trips_neither_rule(tmp_path):
    """No fixture produces a FAIL finding for either rule, so the mapping cannot make a clean run
    fail. The import rule reads the `.tf` files, so the run is asked to write them.
    """
    for name in sorted(CORPUS_ROWS):
        out = tmp_path / name
        proc = _run(FIXTURES_DIR / name, out, extra=('--import-blocks',))
        assert proc.returncode == 0, name
        report = sanity_checks.run_checks(out)
        for check in ('import_blocks', 'variables'):
            assert not [finding for finding in report.findings(check)
                        if finding.severity == sanity_checks.FAIL], (name, check)
        assert report.fail_count == 0, name


# --- 7. determinism and the gate rule that reads this record -------------------

def test_two_runs_on_the_same_bytes_write_the_same_bytes(tmp_path):
    """Two runs on the same input write the same bytes for both new files."""
    first, second = tmp_path / 'first', tmp_path / 'second'
    source = FIXTURES_DIR / KITCHEN
    assert _run(source, first).returncode == 0
    assert _run(source, second).returncode == 0
    for name in (site_data.SITE_DATA_FILE, site_data.TFVARS_FILE):
        # F6.10.3: the record is one file for the codebase and the printed form is the unit's file, so the
        # determinism rule reads the printed form of each unit against the same unit in the other run.
        first_set = {str(p.relative_to(first)): p.read_bytes() for p in sorted(first.rglob(name))}
        second_set = {str(p.relative_to(second)): p.read_bytes() for p in sorted(second.rglob(name))}
        assert first_set == second_set, name


def test_the_gate_reads_the_record_and_its_printed_form_through_site_data(tmp_path):
    """F6.8 changed the file set: the data rule reads this record through `site_data.parse_rows`, and the
    printed form through `site_data.render_tfvars`, so no second shape rule appears. The printed form is
    not one of the four, so the count names only the records, and the block reader stays `.tf`-only.
    """
    out = tmp_path / 'kitchen'
    assert _run(FIXTURES_DIR / KITCHEN, out).returncode == 0
    files = sanity_checks.read_tf_files(out)
    assert files and all(name.endswith('.tf') for name in files), 'the block reader is .tf-only'
    assert dict(sanity_checks.DATA_FILES)[site_data.SITE_DATA_FILE] is site_data
    assert site_data.TFVARS_FILE not in dict(sanity_checks.DATA_FILES), 'the print is not a data file'
    assert not hasattr(site_data, 'check'), 'the record owns no gate check'
    report = sanity_checks.run_checks(out)
    assert [check.check for check in report.checks] == list(sanity_checks.CHECK_ORDER)
    assert report.data_file_count == 4, report.render()
    assert report.findings('data_files') == []
    assert report.fail_count == 0, report.render()


def test_no_report_names_a_field_the_site_data_states(tmp_path):
    """The site record is a data file, not a report body: no report names the mapping result or restates a
    row. A report may name the value, which is the parse fact.

    F6.10.4 carves one exception for `README.md`: the README is the file inventory, so it names the site
    record and its printed form as files. The label states no row, no value, and no mapping result, so the
    rule holds for the record itself, and no other report names the record.
    """
    out = tmp_path / 'kitchen'
    assert _run(FIXTURES_DIR / KITCHEN, out).returncode == 0
    mapping_result = naming.variable_name(DEVICE)
    for name in (entry_coverage.REPORT_FILE, 'MANUAL_SETUP_REPORT.txt',
                 'INTERFACE_MIGRATION_REPORT.txt', 'SANITY_REPORT.txt', 'SOURCE.txt', 'README.md'):
        path = out / name
        if not path.is_file():
            continue    # a report is written only when it has content
        text = path.read_text(encoding='utf-8')
        if name == 'README.md':
            # The inventory may name the files; it still states no field, no row and no value.
            assert '## Site values' in text, name
        else:
            assert site_data.SITE_DATA_FILE not in text, name
            assert site_data.TFVARS_FILE not in text, name
        assert mapping_result not in text, name
        assert not any(line.strip().startswith(mapping_result + ' =') for line in text.split('\n')), name


def test_the_readme_names_the_site_files_and_states_no_row(tmp_path):
    """F6.10.4: the README is the file inventory, so the label names the site record, its printed form, and
    `imports.tf`, and names `target` as the fact the tool names as a variable and cannot name as a value.

    The label states no row, no value, no mapping result, no count, no path and no timestamp, so the §9 rule 6
    exception is a file name, not a field. It is fixed text, so two runs on the same bytes write the same bytes.
    """
    out = tmp_path / 'kitchen'
    assert _run(FIXTURES_DIR / KITCHEN, out).returncode == 0
    text = (out / 'README.md').read_text(encoding='utf-8')
    label = text.split('## Site values', 1)[1]
    for name in (site_data.SITE_DATA_FILE, site_data.TFVARS_FILE, 'imports.tf', 'target'):
        assert name in text, name
    assert naming.variable_name(DEVICE) not in text, 'no mapping result'
    assert DEVICE not in text, 'no value'
    assert not any(char.isdigit() for char in label), 'no count'
    for word in ('timestamp', 'generated_at'):
        assert word not in text, word
    second = tmp_path / 'second'
    assert _run(FIXTURES_DIR / KITCHEN, second).returncode == 0
    assert (second / 'README.md').read_text(encoding='utf-8') == text, 'the label is deterministic'
    # The label is the only difference the site half makes, so the F5.5 read-through label rule holds.
    plain = tmp_path / 'plain'
    read = tmp_path / 'read'
    assert _run(FIXTURES_DIR / KITCHEN, plain).returncode == 0
    assert _run(FIXTURES_DIR / KITCHEN, read, ('--data-blocks', 'panos_address')).returncode == 0
    plain_text = (plain / 'README.md').read_text(encoding='utf-8')
    read_text = (read / 'README.md').read_text(encoding='utf-8')
    head, tail = plain_text.split('## Important Notes')
    assert read_text.startswith(head + '## Site values') or read_text.startswith(head), 'same head'
    assert read_text.endswith(tail), 'same tail'
    assert 'Read-through data blocks' in read_text, 'the read run adds its own label'


def test_site_data_defines_no_second_naming_rule():
    """The module reads the §5 rule from `naming.py` and defines no second one, the way
    `unit_manifest.py` takes it as an argument.
    """
    assert not any(hasattr(site_data, name) for name in ('sanitize', 'sanitize_name', 'name_ref'))
    assert not any(hasattr(site_data, name) for name in ('resolve', 'resolve_reference'))
    assert not hasattr(site_data, 'value_variable_for')
