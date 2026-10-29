"""F6.5 scope objects: the emitter, the placement rule, the device member rule, and the gate rule.

`acceptance.md` states the decisions; these tests pin them:

1. Emission and order. One `resource` block per scope entry, in the level order `SCOPE_LEVEL_ORDER`
   states and in document order inside a type, in one file for the run. The file is written only
   when the run has content, and `main()` writes it after `provider.tf` and `variables.tf` and
   before the object files, so the reader sees the unit before the config inside it. Emission is the
   default for every run, so no flag names it.
2. The name field. `panos_device_group_parent` declares no `name`, so its entry name reaches the
   block through the field `entry_coverage.name_field` states, the same rule the import agreement
   gate reads.
3. The value shape. `SCOPE_SHAPE` is grounded against the live provider schema, and the emitter
   prints a device membership as the list of objects the provider takes.
4. The device member rule. The PAN-OS "this device" placeholder never enters a printed list, and a
   list that held only the placeholder writes no line.
5. Placement. A scope entry the export places in no template or template stack writes no block and
   is reported as `skipped` with the reason, and `panorama_device` is not emitted.
6. The gate rule. Each violation type `sanity_checks.check_scope_blocks` states is pinned, and the
   corpus produces no finding.
7. Determinism. Two runs on the same bytes write the same bytes.

`tests/fixtures/scope_objects.xml` carries one entry for each of the six scope types, including a
device group that lists only the placeholder device.
"""

import inspect
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import container_coverage
import entry_coverage
import resource_mapping
import sanity_checks
from conftest import FIXTURES_DIR, run_pipeline, run_script

CONVERTER = 'panorama_to_terraform.py'
SCOPE_FILE = 'scope.tf'
FIXTURE = 'scope_objects.xml'
NO_SCOPE_FIXTURE = 'address_objects.xml'
PLACEMENT_FIXTURE = 'report_grouping.xml'
PLACEHOLDER = container_coverage.PLACEHOLDER_DEVICE

# Every `resource "panos_x" "y" {` line in a Terraform file.
RESOURCE_RE = re.compile(r'resource\s+"([a-z0-9_]+)"\s+"([^"]+)"\s*\{')

# The eight blocks the fixture writes: three device groups, one parent record, and one entry for
# each of the four template shapes.
BLOCK_ORDER = ['panos_device_group', 'panos_device_group', 'panos_device_group',
               'panos_device_group_parent', 'panos_template', 'panos_template_stack',
               'panos_template_variable', 'panos_vsys']


def _generate(fixture: str, out_dir: Path) -> str:
    """Run the converter on one fixture and return the scope file text (empty when unwritten)."""
    result = run_script(CONVERTER, str(FIXTURES_DIR / fixture), '--output-dir', str(out_dir))
    assert result.returncode == 0, f'converter failed on {fixture}: {result.stderr}\n{result.stdout}'
    path = out_dir / SCOPE_FILE
    return path.read_text(encoding='utf-8') if path.is_file() else ''


def _blocks(text: str, rtype: str) -> list[str]:
    """The resource blocks of one type. A block closes at the first `}` in column 0."""
    found = []
    for match in RESOURCE_RE.finditer(text):
        if match.group(1) != rtype:
            continue
        end = text.find('\n}', match.end())
        assert end != -1, f'unclosed resource block for {rtype}'
        found.append(text[match.start():end + 2])
    return found


def _block(text: str, rtype: str, name: str) -> str:
    """The block of one type that states one entry name."""
    for block in _blocks(text, rtype):
        if name in block:
            return block
    raise AssertionError(f'no {rtype} block states {name!r}:\n{text}')


@pytest.fixture(scope='module')
def scope_text(tmp_path_factory) -> str:
    """The scope file the run writes for the fixture, generated once for the module."""
    return _generate(FIXTURE, tmp_path_factory.mktemp('scope_objects'))


# --- 1. Emission and order --------------------------------------------------

def test_one_block_per_scope_entry(scope_text):
    """Eight blocks: the fixture carries one entry of each of the six types, and one device-group
    entry feeds two blocks (the scope object and the parent record).
    """
    assert [m.group(1) for m in RESOURCE_RE.finditer(scope_text)] == BLOCK_ORDER


def test_blocks_print_in_the_level_order_the_table_states(scope_text):
    """The order the file prints is the order `SCOPE_LEVEL_ORDER` states, read through the first block
    of each type, so the emitter cannot print a level out of order.
    """
    order = [match.group(1) for match in RESOURCE_RE.finditer(scope_text)]
    first_type_of_each_level = list(dict.fromkeys(order))
    assert first_type_of_each_level == list(resource_mapping.SCOPE_LEVEL_ORDER), first_type_of_each_level
    # A type's blocks sit together, so the level order is the print order.
    for rtype in resource_mapping.SCOPE_LEVEL_ORDER:
        positions = [index for index, type_name in enumerate(order) if type_name == rtype]
        assert positions == list(range(positions[0], positions[-1] + 1)), (rtype, order)


def test_entries_print_in_document_order_within_a_type(scope_text):
    """Within a type the entries print in the order the export holds them, so the file is stable."""
    names = [re.search(r'name = "([^"]+)"', block).group(1)
             for block in _blocks(scope_text, 'panos_device_group')]
    assert names == ['Shared-Parent', 'Edge-FW', 'Placeholder-Only'], names
    entries = ET.parse(FIXTURES_DIR / FIXTURE).getroot().findall('.//device-group/entry')
    assert [entry.get('name') for entry in entries] == names


def test_the_scope_file_is_written_before_the_config_inside_it(converter_module):
    """The order rule (`docs/CODEBASE_ASSEMBLY.md` §6): `main()` writes the scope file after
    `provider.tf` and before the object files.

    F6.6 moves `variables.tf` after the emitters, because the declaration set is the site values the
    emitters printed. The scope-file-before-the-config rule is unchanged.
    """
    calls = re.findall(r'tf_gen\.(\w+)\(', inspect.getsource(converter_module.main))
    position = calls.index('generate_scope_objects')
    assert calls[:position] == ['generate_provider_config'], calls[:position]
    assert calls.index('generate_variables') > position, calls
    assert calls[position + 1], 'the scope file must be written before the object files'
    assert 'generate_address_objects' in calls[position + 1:], calls[position + 1:]


def test_the_file_is_written_only_when_it_has_content(tmp_path):
    """A run on an input with no scope entry writes no file, the rule the report and data files use."""
    assert _generate(NO_SCOPE_FIXTURE, tmp_path) == ''


def test_emission_is_default_and_no_flag_names_it(tmp_path):
    """Decision 1: F6.5 is not a flag, so no argument turns it on and an unknown argument is still
    the argument error the exit code states.
    """
    out = tmp_path / 'default'
    assert _generate(FIXTURE, out) != '', 'a run must write the scope blocks by default'
    refused = run_script(CONVERTER, str(FIXTURES_DIR / FIXTURE), '--output-dir', str(tmp_path),
                         '--scope-blocks')
    assert refused.returncode == 2, refused.stdout


# --- 2. The name field -------------------------------------------------------

def test_the_parent_record_carries_the_entry_name_through_the_field_the_rule_states(scope_text):
    """Decision 4: the provider declares no `name` for `panos_device_group_parent`, so the entry name
    reaches the block through `entry_coverage.name_field`, and one entry feeds two blocks.
    """
    assert entry_coverage.name_field('panos_device_group_parent') == 'device_group'
    record = _block(scope_text, 'panos_device_group_parent', 'Edge-FW')
    assert 'device_group = "Edge-FW"' in record
    assert 'name = "Edge-FW"' in _block(scope_text, 'panos_device_group', 'Edge-FW')


def test_the_device_group_block_prints_no_parent(scope_text, provider_schema):
    """The device group row declares `parent` because the emitter reads it for the record, but the
    provider has no `parent` attribute for `panos_device_group`, so the scope block prints none.
    """
    assert 'parent' not in provider_schema['panos_device_group']['block']['attributes']
    group = _block(scope_text, 'panos_device_group', 'Edge-FW')
    assert not _field_line(group, 'parent'), group
    assert 'parent = "Shared-Parent"' in _block(scope_text, 'panos_device_group_parent', 'Edge-FW')


def _field_line(block: str, key: str) -> bool:
    """True when the block states one field at its own level."""
    return any(line.lstrip().startswith(f'{key} =') for line in block.split('\n'))


def test_a_record_that_would_state_no_fact_is_not_written(scope_text):
    """A device group that states no parent writes no parent record, so the file holds one record."""
    assert len(_blocks(scope_text, 'panos_device_group_parent')) == 1
    top_level = _block(scope_text, 'panos_device_group', 'Shared-Parent')
    assert not _field_line(top_level, 'parent'), top_level


# --- 3. The value shape ------------------------------------------------------

PROVIDER_TYPES = {'string': 'string', 'string_list': ['list', 'string']}

# The property a row declares but another block prints: the device-group entry feeds the scope block
# and the parent record, and the provider has no `parent` attribute for the scope type, so the record
# prints it (`acceptance.md` decision 11).
PRINTED_BY_ANOTHER_BLOCK = {'panos_device_group': ('parent',)}


def test_scope_shape_covers_the_properties_the_rows_declare():
    """Every property a scope row declares at the block's own level has a shape entry, so the emitter
    cannot print a property whose shape the table does not state. The placement keys are the
    location's fields, not the block's own, so they are not shape entries.
    """
    for row in resource_mapping.COVERAGE_MATRIX:
        if row['resource'] not in resource_mapping.SCOPE_TYPES:
            continue
        own = [key for key in row['properties']
               if key not in resource_mapping.SCOPE_PLACEMENT[row['resource']]
               and key not in PRINTED_BY_ANOTHER_BLOCK.get(row['resource'], ())]
        assert sorted(own) == sorted(resource_mapping.SCOPE_SHAPE[row['resource']]), row['resource']


def test_scope_shape_is_the_provider_shape(scope_text, provider_schema):
    """Every entry in `SCOPE_SHAPE` is the provider type for that attribute, so the shape the emitter
    prints is the shape the provider takes. `terraform validate` refuses a string where the provider
    takes an object, which is why the shape is a table and not a style choice.
    """
    for rtype, shapes in resource_mapping.SCOPE_SHAPE.items():
        attributes = provider_schema[rtype]['block']['attributes']
        for key, shape in shapes.items():
            attribute = attributes[key]
            mode = attribute.get('nesting_mode') or attribute.get('nested_type', {}).get('nesting_mode')
            if shape in PROVIDER_TYPES:
                assert attribute.get('type') == PROVIDER_TYPES[shape], (rtype, key)
            elif shape == 'object_list':
                assert mode == 'list', (rtype, key)
                fields = attribute.get('nested_type', attribute).get('attributes', {})
                assert 'name' in fields, (rtype, key)
            else:
                assert mode == 'single', (rtype, key)


def test_a_device_membership_prints_as_the_objects_the_provider_takes(scope_text):
    """`devices` is a list of objects for the two types that declare it that way, and a list of
    strings for `templates`, which the provider declares as a list of strings.
    """
    group = _block(scope_text, 'panos_device_group', 'Edge-FW')
    assert 'devices = [\n    {\n      name = "edge-firewall"\n    }\n  ]' in group
    assert 'templates = [ "Edge-Networks" ]' in group
    stack = _blocks(scope_text, 'panos_template_stack')[0]
    assert 'devices = [\n    {\n      name = "edge-firewall"\n    }\n  ]' in stack


def test_the_template_variable_value_prints_as_the_object_the_provider_takes(scope_text):
    """Decision 3: the value stays a literal, because the value-to-variable mapping is F6.6."""
    variable = _block(scope_text, 'panos_template_variable', 'edge-tag')
    assert 'type = {\n    ip_netmask = "10.0.0.50/32"\n  }' in variable
    assert 'var.' not in variable


# --- 4. The device member rule -----------------------------------------------

def test_the_placeholder_device_never_enters_a_printed_list(scope_text):
    """Decision 5: `localhost.localdomain` names no firewall, so it is never a printed member."""
    assert PLACEHOLDER not in scope_text
    group = _block(scope_text, 'panos_device_group', 'Edge-FW')
    assert 'edge-firewall' in group
    only = _block(scope_text, 'panos_device_group', 'Placeholder-Only')
    assert 'devices' not in only, 'a list that held only the placeholder writes no line'
    assert PLACEHOLDER not in group


# --- 5. Placement ------------------------------------------------------------

def test_the_four_panorama_scopes_print_the_empty_sub_block(scope_text):
    """Decision 6: the codebase states no device fact in a location, so `location` prints the empty
    sub-block, the shape `shared = {}` already uses, and `panorama_device` is never emitted.
    """
    for rtype in ('panos_device_group', 'panos_device_group_parent', 'panos_template',
                  'panos_template_stack'):
        for block in _blocks(scope_text, rtype):
            assert 'panorama = {}' in block, block
    assert 'panorama_device' not in scope_text
    assert 'ngfw_device' not in scope_text


def test_a_variable_and_a_vsys_place_in_the_scope_the_export_declares(scope_text):
    """The location names the scope entry the export holds the entry inside, never a guess."""
    assert 'template_stack = {\n      name = "Edge-Stack"\n    }' in _block(
        scope_text, 'panos_template_variable', 'edge-tag')
    assert 'template = {\n      name = "Edge-Networks"\n    }' in _block(scope_text, 'panos_vsys', 'edge-vsys')


def test_a_scope_entry_the_export_places_nowhere_writes_no_block(converter_module, tmp_path):
    """Decision 6, pinned on the fixture that holds a virtual system inside a device group: the run
    reports the entry as `skipped` with the reason and writes no block for it.
    """
    out = tmp_path / 'placement'
    parser = run_pipeline(converter_module, PLACEMENT_FIXTURE, out)
    assert parser is not None
    row = next(row for row in parser.ledger.rows() if row['name'] == 'vsys2')
    assert row['destination'] == 'skipped', row
    assert 'no template holds this virtual system' in row['detail'], row
    assert 'panos_vsys' not in (out / SCOPE_FILE).read_text(encoding='utf-8')


# --- 6. The gate rule --------------------------------------------------------

ANSWERED = (
    'resource "panos_template" "edge_networks_20f2b6ae" {\n'
    '  location = {\n    panorama = {}\n  }\n  name = "Edge-Networks"\n}\n\n'
    'resource "panos_template_variable" "edge_tag_d3a43225" {\n'
    '  location = {\n    template = {\n      name = "Edge-Networks"\n    }\n  }\n'
    '  name = "edge-tag"\n}\n\n'
)
VARIABLE_FILE = 'scope.tf'


def test_a_name_a_block_declares_answers_the_location():
    """The rule passes when the name inside `location` is a scope this run declares."""
    assert sanity_checks.check_scope_blocks({VARIABLE_FILE: ANSWERED}) == []


def test_a_location_name_no_block_declares_is_a_finding():
    """The violation type: a name inside `location` that no block of the answering type states."""
    files = {VARIABLE_FILE: ANSWERED.replace('      name = "Edge-Networks"', '      name = "Edge-Other"')}
    findings = sanity_checks.check_scope_blocks(files)
    assert len(findings) == 1, findings
    assert findings[0].check == 'scope_blocks'
    assert findings[0].severity == sanity_checks.FAIL
    assert 'names no panos_template block this run declares' in findings[0].detail


def test_a_data_block_cannot_answer_a_scope_name():
    """A `data` block is a read-through, not a declaration, so it answers no location name."""
    data_only = (
        'data "panos_template" "edge_networks_20f2b6ae" {\n'
        '  location = {\n    panorama = {}\n  }\n  name = "Edge-Networks"\n}\n\n'
        'resource "panos_template_variable" "edge_tag_d3a43225" {\n'
        '  location = {\n    template = {\n      name = "Edge-Networks"\n    }\n  }\n'
        '  name = "edge-tag"\n}\n\n'
    )
    findings = sanity_checks.check_scope_blocks({'scope.tf': data_only})
    assert len(findings) == 1, findings
    assert 'names no panos_template block' in findings[0].detail


def test_a_field_that_names_a_device_states_no_scope_name():
    """`panorama_device` names a device, not a scope, so the rule reads no name there."""
    with_device = ANSWERED.replace(
        '    template = {\n      name = "Edge-Networks"\n    }',
        '    template = {\n      name = "Edge-Networks"\n      panorama_device = "Panorama-1"\n    }')
    assert sanity_checks.check_scope_blocks({VARIABLE_FILE: with_device}) == []


def test_an_empty_sub_block_names_nothing_to_resolve():
    """The `panorama = {}` shape states no name, so the rule has nothing to check."""
    assert sanity_checks.check_scope_blocks({VARIABLE_FILE: ANSWERED}) == []
    empty = ('resource "panos_template_variable" "edge_tag_d3a43225" {\n'
             '  location = {\n    template_stack = {}\n  }\n  name = "edge-tag"\n}\n\n')
    assert sanity_checks.check_scope_blocks({'scope.tf': empty}) == []


def test_the_rule_reads_blocks_with_the_one_reader():
    """The finding names the file and the line the one block reader read."""
    files = {VARIABLE_FILE: ANSWERED.replace('      name = "Edge-Networks"', '      name = "Edge-Other"')}
    findings = sanity_checks.check_scope_blocks(files)
    block = [block for block in sanity_checks.blocks(files, ('resource',))
             if block.rtype == 'panos_template_variable'][0]
    assert (findings[0].file, findings[0].line) == (block.file, block.line)
    assert block.address == 'panos_template_variable.edge_tag_d3a43225'


def test_no_false_positive_across_the_corpus(tmp_path):
    """Every scope block the corpus writes names a scope this run declares."""
    for path in sorted(FIXTURES_DIR.glob('*.xml')):
        out = tmp_path / path.stem
        result = run_script(CONVERTER, str(path), '--output-dir', str(out))
        if result.returncode != 0:
            continue    # the hostile fixtures are refused before the parse
        files = sanity_checks.read_tf_files(out)
        if files:
            assert sanity_checks.check_scope_blocks(files) == [], path.name


def test_scope_blocks_is_in_the_check_order():
    """The gate table names the new rule after `import_blocks`, the order the report prints."""
    assert 'scope_blocks' in sanity_checks.CHECK_ORDER
    assert sanity_checks.CHECK_ORDER.index('scope_blocks') == \
        sanity_checks.CHECK_ORDER.index('import_blocks') + 1


# --- 7. Determinism -----------------------------------------------------------

def test_two_runs_on_the_same_bytes_write_the_same_bytes(tmp_path):
    """The file is byte-identical between runs, so the goldens can pin it."""
    first = _generate(FIXTURE, tmp_path / 'run1')
    second = _generate(FIXTURE, tmp_path / 'run2')
    assert first == second
