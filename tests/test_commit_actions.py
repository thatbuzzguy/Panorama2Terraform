"""F6.7: the action block per unit, as `actions.tf`: the commit action, and the push action F6.10.4 adds.

Seven rule groups, one per section here:

1. **One block per unit.** `build_rows` writes one row per manifest row and per action the pinned schema
   declares, and the block names the fact its own unit selects through `unit_manifest.named_fact`. A unit whose
   fact no filter and no push type can name (a vsys, a device, the shared section) writes no row, and
   `actions.tf` is written only when it has content.
2. **The gate rule `actions`.** Every finding is read through the one block reader
   (`sanity_checks.blocks(files, ('action',))`) and the one field reader (`import_blocks`), against the
   `ACTION_SCHEMA` row, the `ACTION_FILTERS` mapping, and `SCOPE_ANSWER`. One test per violation type, and
   one corpus test that pins no false positive.
3. **One rule per fact.** `ACTION_FILTERS` is the only field mapping, `SCOPE_ANSWER` the only answer table,
   `naming.py` the only naming rule, `unit_manifest.named_fact` the only level rule. No module defines a
   second one, and the rule reads no data file.
4. **The address names the identity the block states**, so the gate reads a block back on its own:
   `read_block` returns the row the block states, and the address agrees with the names inside it.
5. **The Terraform minimum and the file order.** `required_version = ">= 1.14"` is in the generated
   `terraform` block and in both goldens, `actions.tf` is the last `.tf` file `main()` writes, and
   `terraform validate` accepts the block shape.
6. **Determinism.** Two runs on the same source write the same bytes.
7. **The push block (F6.10.4).** `block_fields` prints `name` for the fact and `type` for the fact key through
   `ACTION_FILTERS`, so the emitter and the gate read one mapping. No `devices`, because the tool names no serial
   (`docs/CODEBASE_ASSEMBLY.md` §9 rule 8), so the provider's documented default covers the target. Within one
   unit the blocks print in the `ACTION_SCHEMA` order, and the two blocks share one address.

The pinned provider fact is the two action rows `terraform providers schema -json` declares for provider
2.0.14.
"""

import inspect
import re
import subprocess
from pathlib import Path

import pytest

import commit_actions
import container_coverage
import naming
import panorama_to_terraform as converter_module
import resource_mapping
import sanity_checks
import unit_manifest
from conftest import (
    FIXTURES_DIR,
    GOLDEN_DIR,
    SAMPLE_CONFIG,
    SRC_DIR,
    TERRAFORM,
    corpus_fixtures,
    parts,
    run_script,
    tf_files,
)

CONVERTER = 'panorama_to_terraform.py'
ACTIONS = commit_actions.ACTIONS_FILE
MANIFEST = unit_manifest.MANIFEST_FILE
KITCHEN = 'kitchen_sink.xml'

# The fixtures the corpus pins read: the read rule's accepted set, not a name rule.
FIXTURES = corpus_fixtures()


def _run(source: Path, out_dir: Path, extra: tuple = ()) -> subprocess.CompletedProcess:
    """Run the converter and return the process result."""
    return run_script(CONVERTER, str(source), '--output-dir', str(out_dir), *extra)


def _files(out_dir: Path) -> dict:
    """The `.tf` files the run wrote, as text."""
    return tf_files(out_dir)


def _manifest(out_dir: Path) -> list:
    """The manifest the run wrote, read back as data.

    A run scoped to a scope writes no manifest, so this answers no row for it, and a pin that reads the corpus
    reads no row for that fixture.
    """
    path = out_dir / MANIFEST
    return unit_manifest.parse_rows(path.read_text(encoding='utf-8')) if path.is_file() else []


def _row(facts: dict) -> dict:
    """One manifest row, in the declared shape, for a unit built by hand."""
    identity = tuple(facts.get(key, '') for key in unit_manifest.FACT_KEYS)
    row = dict.fromkeys(unit_manifest.FIELD_ORDER, '')
    row.update(zip(unit_manifest.FACT_KEYS, identity))
    row['unit'] = unit_manifest.unit_name(identity)
    row['directory'] = unit_manifest.directory_name(identity, naming.sanitize)
    return row


def _block(fact: str, name: str, local: str = None, field: str = None,
           action: str = 'panos_commit') -> str:
    """One action block, in the shape the generator writes, with the address the rule expects."""
    local = local or commit_actions.local_name(fact, name, naming.sanitize)
    fields = commit_actions.block_fields(action, fact, name)
    if field:
        fields = {field: name}
    body = ''.join(f'    {part} = {commit_actions.field_text(action, part, fields[part])}\n'
                   for part in fields)
    return f'action "{action}" "{local}" {{\n  {commit_actions.CONFIG_BLOCK} {{\n{body}  }}\n}}\n'


# --- 1. One block per unit ---------------------------------------------------

def test_one_action_block_per_unit_the_manifest_names(tmp_path):
    """The file is the manifest read as blocks: one block per row that names a fact the answer answers,
    for each action the pinned schema declares."""
    out = tmp_path / 'kitchen'
    assert _run(FIXTURES_DIR / KITCHEN, out).returncode == 0
    rows = commit_actions.build_rows(_manifest(out), naming.sanitize)
    assert rows, 'the kitchen sink names a device group and a template'
    blocks = sanity_checks.blocks(_files(out), ('action',))
    assert len(blocks) == len(rows), (blocks, rows)
    # F6.10.4: the commit block and the push block for one unit share one address, so the pair (action,
    # address) is the key that names one row.
    by_block = {(row['action'], row['local_name']): row for row in rows}
    for block in blocks:
        shape = commit_actions.read_block(block)
        # A per-unit file states no unit inside its bytes, so the block shape names no directory and the
        # path names the unit the row put the block in.
        assert shape == {**by_block[(block.rtype, block.local)], 'directory': ''}, (block.file, block.local)
        assert Path(block.file).parent.name == by_block[(block.rtype, block.local)]['directory'], block.file


def test_the_blocks_print_in_the_identity_order_the_manifest_rows_print(tmp_path):
    """The file order is the identity order the manifest rows print: the identity as each block states
    it, so a reader reproduces the order from the block text alone.
    """
    out = tmp_path / 'kitchen'
    assert _run(FIXTURES_DIR / KITCHEN, out).returncode == 0
    rows = commit_actions.build_rows(_manifest(out), naming.sanitize)
    identities = [commit_actions.placed_identity(row['fact'], row['entry_name']) for row in rows]
    assert identities == sorted(identities), identities
    # F6.10.3 (§14): one file holds one unit's blocks, so the order is read inside each unit's file, and the
    # rows of one unit are the rows that print in that order.
    by_unit = {}
    for row in rows:
        by_unit.setdefault(row['directory'], []).append(row)
    for path, text in parts(_files(out), ACTIONS).items():
        unit = Path(path).parent.name
        assert [block.local for block in sanity_checks.blocks({path: text}, ('action',))] == \
            [row['local_name'] for row in by_unit[unit]], (path, unit)


def test_an_action_names_the_fact_its_own_unit_declares(tmp_path):
    """The fact in a block is the fact `named_fact` selects for that manifest row, and the field that
    states it is the mapping's row for that fact, so one block states one fact.
    """
    out = tmp_path / 'kitchen'
    assert _run(FIXTURES_DIR / KITCHEN, out).returncode == 0
    manifest = {row['directory']: row for row in _manifest(out)}
    for row in commit_actions.build_rows(_manifest(out), naming.sanitize):
        identity = tuple(manifest[row['directory']][key] for key in unit_manifest.FACT_KEYS)
        key, name = unit_manifest.named_fact(identity)
        assert (key, name) == (row['fact'], row['entry_name']), (row, key, name)
        assert row['field'] == commit_actions.filter_field(key, row['action']), row


def test_an_action_states_no_fact_an_ancestor_declares():
    """A unit that declares a device group and a template names the fact it selects, not the fact the
    ancestor unit owns.
    """
    shape = commit_actions.build_rows([_row({'device_group': 'DG-A', 'template': 'T-A'})], naming.sanitize)[0]
    assert (shape['fact'], shape['entry_name'], shape['field']) == ('template', 'T-A', 'templates'), shape
    assert sanity_checks.check_actions({ACTIONS: _block('template', 'T-A')}) == []


def test_a_shared_unit_and_a_vsys_unit_and_a_device_unit_write_no_action():
    """A commit that names no filter commits the whole config, so a unit whose selected fact no filter can
    name writes no row: the shared section, a virtual system, a device. A device group that declares a vsys
    selects the vsys as its own fact, so it writes no row either.
    """
    assert commit_actions.build_rows([_row({}), _row({'vsys': 'vsys1'}),
                                      _row({'vsys_device': 'fw-2.example.com'})], naming.sanitize) == []
    assert commit_actions.build_rows([_row({'device_group': 'DG-A', 'vsys': 'vsys1'})], naming.sanitize) == []
    # A device group with no deeper fact names its own group.
    shape = commit_actions.build_rows([_row({'device_group': 'DG-A'})], naming.sanitize)[0]
    assert (shape['fact'], shape['entry_name']) == ('device_group', 'DG-A'), shape


def test_the_placeholder_device_never_names_a_filter():
    """`localhost.localdomain` names no firewall (F3.5), so it never selects a fact and never enters a
    filter, and a device-group unit whose only other fact is the placeholder still names its group.
    """
    shape = commit_actions.build_rows([_row({'device_group': 'Production-DG',
                                            'vsys_device': container_coverage.PLACEHOLDER_DEVICE})],
                                      naming.sanitize)[0]
    assert (shape['fact'], shape['entry_name']) == ('device_group', 'Production-DG'), shape
    assert commit_actions.build_rows([_row({'vsys_device': container_coverage.PLACEHOLDER_DEVICE})],
                                     naming.sanitize) == []


def test_the_block_address_names_the_identity_the_block_states():
    """The address is the §5 name plus the digest of the identity as the block states it, so the gate reads
    a block back on its own, and the address is not the unit's directory name.
    """
    row = _row({'device_group': 'DG-A', 'template': 'T-A'})
    shape = commit_actions.build_rows([row], naming.sanitize)[0]
    expected = (f'{naming.sanitize(shape["entry_name"])}_'
                f'{unit_manifest.identity_digest(commit_actions.placed_identity(shape["fact"], shape["entry_name"]))}')
    assert shape['local_name'] == expected, shape
    assert shape['local_name'] != row['directory'], 'the digest is the identity the block states'
    block = sanity_checks.blocks({ACTIONS: _block('template', 'T-A')}, ('action',))[0]
    # `directory` is the manifest join, not a block field, so the reader reads nothing into it.
    assert commit_actions.read_block(block) == {**shape, 'directory': ''}
    assert sanity_checks.check_actions({ACTIONS: _block('template', 'T-A')}) == []


def test_the_file_is_written_only_when_it_has_content(tmp_path):
    """A run whose units name no commit-nameable fact writes no file, the rule for the report files and the
    four data files, and the run sequence writes it as the last `.tf` file.
    """
    out = tmp_path / 'no_action'
    assert _run(FIXTURES_DIR / 'address_objects.xml', out).returncode == 0
    assert not parts(_files(out), ACTIONS), 'the run names no fact a commit filter can name'
    source = inspect.getsource(converter_module.generate_run)
    assert 'if action_rows:' in source and 'for facts in tf_gen.unit_set()' in source, source
    assert 'commit_actions.ACTIONS_FILE' in source and 'write_path.unit_path' in source, \
        'the file is written through the write path, inside the unit directory'
    # The write is the last `.tf` write in the run sequence, so the gate reads the action against the
    # completed unit.
    tf_writes = [match.group(1) for match in re.finditer(r'(import_blocks\.IMPORT_FILE|commit_actions\.ACTIONS_FILE)',
                                                          source)]
    assert tf_writes[-1] == 'commit_actions.ACTIONS_FILE', tf_writes


# --- 2. The gate rule --------------------------------------------------------

def test_the_rule_reads_action_blocks_with_the_one_reader():
    """The rule reads the block through `blocks(files, ('action',))`, and a finding names that block."""
    files = {ACTIONS: _block('device_group', 'DG-A')}
    block = sanity_checks.blocks(files, ('action',))[0]
    assert (block.kind, block.rtype) == ('action', 'panos_commit')
    assert sanity_checks.check_actions(files) == []
    findings = sanity_checks.check_actions({ACTIONS: _block('device_group', 'DG-A', local='not_the_digest')})
    assert len(findings) == 1 and findings[0].check == 'actions'
    assert (findings[0].file, findings[0].line) == (block.file, block.line), findings
    assert block.address == f'panos_commit.{block.local}'


def test_an_action_type_not_in_the_schema_is_a_finding():
    """The two rows `ACTION_SCHEMA` holds are the two actions the pinned schema declares."""
    findings = sanity_checks.check_actions({'a.tf': 'action "panos_commit_all" "x_11111111" {\n  config {\n'
                                                    '    device_groups = ["DG-A"]\n  }\n}\n'})
    assert len(findings) == 1 and 'is not in ACTION_SCHEMA' in findings[0].detail, findings


def test_a_field_the_row_does_not_declare_is_a_finding():
    """A field inside `config` must be a field the row declares."""
    files = {ACTIONS: _block('device_group', 'DG-A').replace('"DG-A"]', '"DG-A"]\n    nonsense = "x"')}
    findings = sanity_checks.check_actions(files)
    assert len(findings) == 1 and 'nonsense is not a field' in findings[0].detail, findings


def test_a_field_at_the_block_level_is_a_finding():
    """The action grammar keeps its fields inside `config`: `terraform validate` refuses a field at the
    block's own level, so the rule reads the level the grammar requires.
    """
    inside = commit_actions.local_name('device_group', 'DG-A', naming.sanitize)
    findings = sanity_checks.check_actions({ACTIONS: f'action "panos_commit" "{inside}" {{\n'
                                                      '  device_groups = ["DG-A"]\n}\n'})
    # The block reports two facts: the field is at the level the grammar does not allow, and the level
    # the rule reads (`config`) states no name.
    assert len(findings) == 2, findings
    assert any('at its own level' in finding.detail for finding in findings), findings
    assert any('does not state one fact' in finding.detail for finding in findings), findings


def test_the_push_shape_requires_name_and_type():
    """The `panos_push_to_devices` row is the only action row with required fields, and its `name` names the
    fact its `type` states, so the reader takes the fact from the `type` value.
    """
    push = 'action "panos_push_to_devices" "x_11111111" {\n  config {\n    type = "device_group"\n  }\n}\n'
    findings = sanity_checks.check_actions({ACTIONS: push})
    assert any('has no name, which panos_push_to_devices requires' in finding.detail
               for finding in findings), findings
    full = push.replace('  config {\n', '  config {\n    name = "DG-A"\n')
    read = commit_actions.read_block(sanity_checks.blocks({ACTIONS: full}, ('action',))[0])
    assert (read['fact'], read['entry_name']) == ('device_group', 'DG-A'), read
    # A `type` value the answer table does not answer names a fact this tool states no block for.
    answered = full.replace('type = "device_group"', 'type = "vsys"')
    findings = sanity_checks.check_actions({ACTIONS: answered})
    assert any('names a fact SCOPE_ANSWER does not answer' in finding.detail for finding in findings), findings
    # A `type` value outside the tool's fact set states no fact, so the block names no unit.
    outside = full.replace('type = "device_group"', 'type = "log_collector_group"')
    findings = sanity_checks.check_actions({ACTIONS: outside})
    assert any('does not state one fact' in finding.detail for finding in findings), findings


def test_a_block_that_names_no_fact_is_a_finding():
    """The `panos_commit` row declares no required field, so the codebase rule is what makes an action a
    unit action: a block that names no filter commits the whole config, not a unit.
    """
    files = {ACTIONS: 'action "panos_commit" "x_11111111" {\n  config {\n    force = true\n  }\n}\n'}
    findings = sanity_checks.check_actions(files)
    assert any('does not state one fact' in finding.detail for finding in findings), findings
    empty = {ACTIONS: 'action "panos_commit" "x_11111111" {\n  config {\n    templates = []\n  }\n}\n'}
    findings = sanity_checks.check_actions(empty)
    assert any('does not state one fact' in finding.detail for finding in findings), findings


def test_a_block_that_states_two_names_is_a_finding():
    """One name per block, so one block names one unit: a second name is a second fact, and the address
    can only answer one identity.
    """
    two_values = _block('device_group', 'DG-A').replace('"DG-A"]', '"DG-A", "DG-B"]')
    findings = sanity_checks.check_actions({ACTIONS: two_values})
    assert any('more than one name' in finding.detail for finding in findings), findings
    two_fields = two_values.replace('    device_groups = ["DG-A", "DG-B"]',
                                    '    device_groups = ["DG-A"]\n    templates = ["T-A"]')
    findings = sanity_checks.check_actions({ACTIONS: two_fields})
    assert any('does not state one fact' in finding.detail for finding in findings), findings


def test_a_value_that_is_not_the_declared_shape_is_a_finding():
    """The value shape the row declares is read through the one field reader."""
    files = {ACTIONS: _block('device_group', 'DG-A').replace('device_groups = ["DG-A"]', 'device_groups = "DG-A"')}
    findings = sanity_checks.check_actions(files)
    assert len(findings) == 1 and 'is not a string_list value' in findings[0].detail, findings
    extra = '    force = true\n    description = "a commit"\n    device_groups'
    good = _block('device_group', 'DG-A').replace('    device_groups', extra)
    assert sanity_checks.check_actions({ACTIONS: good}) == [], good


def test_an_address_that_does_not_answer_the_names_inside_is_a_finding():
    """An address built from another unit's identity cannot answer the name inside the block, which is the
    gate form of "no action names a scope another unit owns".
    """
    inside = commit_actions.local_name('device_group', 'DG-A', naming.sanitize)
    other = commit_actions.local_name('device_group', 'DG-B', naming.sanitize)
    assert inside != other
    findings = sanity_checks.check_actions({ACTIONS: _block('device_group', 'DG-A', local=other)})
    assert len(findings) == 1 and findings[0].detail.endswith(f'({inside})'), findings


def test_no_false_positive_across_the_corpus(tmp_path):
    """Every run the corpus writes agrees with the rule, including a run scoped to a scope it writes no
    block for, which is why the rule does not resolve a filter name against the blocks the run declares.

    The pin measures content: every accepted fixture writes at least one `.tf` file, so the read set is never
    empty, and the two cases are stated separately. Which case a fixture is in is read through
    `commit_actions.build_rows`, the rule owner, so the test states no second rule and names no fixture: for a
    fixture the rule answers with rows, the actions file exists; for a fixture it answers with no row, no
    actions file exists, which is the content rule section 1 pins.
    """
    for name in FIXTURES:
        out = tmp_path / name
        assert _run(FIXTURES_DIR / name, out).returncode == 0
        files = _files(out)
        assert files, (name, 'the run wrote no .tf content for the rule to read')
        assert sanity_checks.check_actions(files) == [], name

        rows = commit_actions.build_rows(_manifest(out), naming.sanitize)
        wrote = parts(files, ACTIONS)
        if rows:
            assert wrote, (name, 'the rule answers with rows, so the file the rule writes exists')
        else:
            assert not wrote, (name, 'the rule answers with no row, so no file is written')


def test_the_goldens_pass_the_rule(tmp_path):
    """Both committed goldens gain `actions.tf`, and the file the run writes equals the golden byte."""
    for case, source in (('sample', SAMPLE_CONFIG), ('kitchen_sink', FIXTURES_DIR / KITCHEN)):
        golden = GOLDEN_DIR / case
        files = _files(golden)
        assert parts(files, ACTIONS), case
        assert sanity_checks.check_actions(files) == [], case
        out = tmp_path / case
        assert _run(source, out).returncode == 0
        # F6.10.3 (§14): the golden case holds one `actions.tf` per unit, and the run writes the same
        # parts, so the pin reads the parts by path.
        assert parts(files, ACTIONS) == parts(_files(out), ACTIONS), case


# --- 3. One rule per fact ----------------------------------------------------

def test_the_field_mapping_is_the_one_mapping():
    """No module names a commit filter field outside `ACTION_FILTERS`: the emitter reads the mapping through
    `filter_field` and the gate reads it through `field_fact`.
    """
    for name in ('commit_actions.py', 'sanity_checks.py'):
        text = (SRC_DIR / name).read_text(encoding='utf-8')
        for field in ('device_groups', 'templates', 'template_stacks'):
            hits = [line for line in text.split('\n') if field in line]
            assert hits == [], (name, field, hits)
    assert set(resource_mapping.ACTION_FILTERS) == {'device_groups', 'templates', 'template_stacks', 'name'}
    assert commit_actions.filter_field('template') == 'templates'
    assert commit_actions.filter_field('vsys') == '', 'no filter can name a vsys fact'


def test_the_answer_table_is_the_one_answer():
    """The action rule reads the fact-to-type answer through `SCOPE_ANSWER`, so it defines no second table,
    and the `device_group` row is read by the action rule, not by the scope rule.
    """
    source = (SRC_DIR / 'sanity_checks.py').read_text(encoding='utf-8')
    check = source[source.index('def check_actions'):]
    code = check[check.index('"""', check.index('"""') + 3) + 3:]
    assert code.count('SCOPE_ANSWER.get') == 1, code
    for fact in ('device_group', 'template', 'template_stack'):
        assert f"'{fact}': 'panos_" not in code, 'a second mapping'
    assert resource_mapping.SCOPE_ANSWER['device_group'] == 'panos_device_group'


def test_named_fact_is_the_one_level_rule():
    """`unit_name` is a delegate of `named_fact`, so no module states the level order a second time."""
    facts = ('DG-A', 'vsys1', 'T-A', 'fw-2.example.com', '')
    key, name = unit_manifest.named_fact(facts)
    assert (key, name) == ('vsys', 'vsys1'), (key, name)
    assert unit_manifest.unit_name(facts) == name
    assert unit_manifest.unit_name(('', '', '', '', '')) == unit_manifest.SHARED_UNIT
    for module in (commit_actions, sanity_checks, resource_mapping, naming):
        assert not hasattr(module, 'NAME_LEVELS'), module
        assert not any(getattr(module, attr, None) == unit_manifest.NAME_LEVELS for attr in dir(module)), module


def test_no_module_defines_a_second_naming_rule():
    """`commit_actions` takes the §5 rule as an argument, the way `unit_manifest` does, and defines no
    sanitizing rule and resolves no name.
    """
    assert not any(hasattr(commit_actions, name) for name in ('sanitize', 'sanitize_name', 'name_ref'))
    assert not any(hasattr(commit_actions, name) for name in ('resolve', 'resolve_reference'))
    source = (SRC_DIR / 'commit_actions.py').read_text(encoding='utf-8')
    assert 'import naming' not in source, 'the rule is taken as an argument'
    docstring = source.split('"""')[1]
    assert 'naming.py' in docstring, 'the rule is named in the module docstring'


def test_the_action_rule_reads_no_data_file():
    """The rule reads the block text, the tables, and `naming.py`, so the action rule reads no manifest
    row. F6.8 added the data rule for the four data files, so the two file sets are separate: a block rule
    reads a `.tf` file, and the data rule reads a record.
    """
    source = (SRC_DIR / 'sanity_checks.py').read_text(encoding='utf-8')
    check = source[source.index('def check_actions'):source.index('def check_references')]
    for name in ('MANIFEST', 'manifest', 'parse_rows', 'unit_manifest', 'OWNERSHIP', 'SITE_DATA'):
        assert name not in check, name
    assert 'commit_actions.read_block' in check and 'commit_actions.local_name' in check
    assert 'blocks(files, (\'action\',))' in check, 'the one block reader'
    assert 'naming.sanitize' in check, 'the one naming rule'


def test_action_schema_is_pinned_against_the_live_schema(provider_schemas):
    """Every `ACTION_SCHEMA` row equals the live action schema for that type: the fields, the value shapes,
    and the required fields, with nothing added and nothing missing.
    """
    live = provider_schemas['action_schemas']
    assert set(resource_mapping.ACTION_SCHEMA) == set(live), (set(live), set(resource_mapping.ACTION_SCHEMA))
    shapes = {'string': 'string', 'bool': 'bool', 'string_list': ['list', 'string']}
    for name, (required, row) in resource_mapping.ACTION_SCHEMA.items():
        attributes = live[name]['block'].get('attributes', {})
        assert sorted(row) == sorted(attributes), (name, sorted(attributes))
        required_live = sorted(field for field, value in attributes.items() if value.get('required'))
        assert sorted(required) == required_live, (name, required_live)
        for field, shape in row.items():
            value = attributes[field]
            if shape == 'object':
                assert 'nested_type' in value, (name, field)
            else:
                assert value['type'] == shapes[shape], (name, field, value['type'])
        assert not live[name]['block'].get('block_types'), (name, 'an action declares no sub-block')


# --- 4. Terraform minimum, order, and bytes ----------------------------------

def test_the_generated_terraform_block_declares_the_minimum():
    """Actions need Terraform 1.14, so the generated `terraform` block declares it and both goldens carry
    the same line.
    """
    for case in ('sample', 'kitchen_sink'):
        # F6.10.3 (§14): `provider.tf` is a unit-set file, so the case holds one per unit, and each states
        # the same block.
        paths = sorted((GOLDEN_DIR / case).rglob('provider.tf'))
        assert paths, case
        for path in paths:
            assert 'required_version = ">= 1.14"' in path.read_text(encoding='utf-8'), path
    source = inspect.getsource(converter_module.TerraformGenerator.generate_provider_config)
    assert 'required_version = ">= 1.14"' in source, source


def test_the_generated_readme_names_the_file_and_the_minimum(tmp_path):
    """The generated README names `actions.tf` and states the minimum."""
    out = tmp_path / 'readme'
    assert _run(SAMPLE_CONFIG, out).returncode == 0
    text = (out / 'README.md').read_text(encoding='utf-8')
    assert f'`{ACTIONS}`' in text, text
    assert '1.14' in text, text


def test_terraform_validate_accepts_an_action_block(tmp_path):
    """The gate's terraform check accepts the emitted shape: the fields inside `config`, which is the level
    the 1.14 action grammar requires.
    """
    if TERRAFORM is None:
        pytest.skip('terraform binary not found (the CI terraform-gate job provides it)')
    out = tmp_path / 'validate'
    assert _run(SAMPLE_CONFIG, out).returncode == 0
    init = subprocess.run([TERRAFORM, 'init', '-backend=false', '-input=false'], cwd=out,
                          capture_output=True, text=True, timeout=300)
    assert init.returncode == 0, f'terraform init failed:\n{init.stdout[-2000:]}\n{init.stderr[-2000:]}'
    result = sanity_checks.check_terraform(out, terraform=TERRAFORM)
    assert result.result == 'PASS' and not result.findings, [f.render() for f in result.findings]


def test_two_runs_write_the_same_bytes(tmp_path):
    """Two runs on the same source write the same action bytes."""
    first, second = tmp_path / 'first', tmp_path / 'second'
    assert _run(FIXTURES_DIR / KITCHEN, first).returncode == 0
    assert _run(FIXTURES_DIR / KITCHEN, second).returncode == 0
    # F6.10.3 (§14): the two runs write the same parts, keyed by the same paths.
    first_parts = {path: text.encode('utf-8') for path, text in parts(_files(first), ACTIONS).items()}
    second_parts = {path: text.encode('utf-8') for path, text in parts(_files(second), ACTIONS).items()}
    assert first_parts == second_parts, 'the action bytes are the same for the same source'
    assert commit_actions.build_rows(_manifest(first), naming.sanitize) == \
        commit_actions.build_rows(_manifest(second), naming.sanitize)


# --- 7. The push block (F6.10.4) ------------------------------------------------

PUSH = 'panos_push_to_devices'


def test_the_push_block_names_the_fact_and_the_fact_key():
    """`name` states the fact and `type` states the fact key, both read through `ACTION_FILTERS`, so the
    emitter and the reader use one mapping. The push row is the only action row with a required field, so the
    print order is the order the row declares.
    """
    fields = commit_actions.block_fields(PUSH, 'device_group', 'DG-A')
    assert fields == {'name': 'DG-A', 'type': 'device_group'}, fields
    assert list(fields) == list(resource_mapping.ACTION_SCHEMA[PUSH][0]), fields
    assert commit_actions.field_text(PUSH, 'name', 'DG-A') == '"DG-A"', 'a string field prints as a string'
    assert commit_actions.field_text('panos_commit', 'device_groups', 'DG-A') == '["DG-A"]'
    read = commit_actions.read_block(
        sanity_checks.blocks({ACTIONS: _block('device_group', 'DG-A', action=PUSH)}, ('action',))[0])
    assert (read['action'], read['fact'], read['field'], read['entry_name']) == \
        (PUSH, 'device_group', 'name', 'DG-A'), read
    # The two shapes share the address rule, so the commit block and the push block for one fact carry the
    # same address, and the action type is the only difference.
    assert commit_actions.local_name('device_group', 'DG-A', naming.sanitize) == read['local_name'], read
    assert _block('device_group', 'DG-A').split('"')[1] == 'panos_commit'


def test_a_fact_the_answer_does_not_answer_prints_no_field():
    """The same answer table gates both shapes: a `vsys` fact and a `vsys_device` fact name no push type, so
    the emitter prints no block for them and the gate reports such a block as naming no fact.
    """
    for fact in ('vsys', 'vsys_device', ''):
        assert commit_actions.block_fields(PUSH, fact, 'x') == {}, fact
        assert commit_actions.block_fields('panos_commit', fact, 'x') == {}, fact
    assert commit_actions.filter_field('vsys', PUSH) == ''
    assert commit_actions.filter_field('device_group', PUSH) == 'name'


def test_the_push_block_states_no_devices(tmp_path):
    """The tool names no serial, so the emitter prints no `devices` field and the provider pushes to all
    devices in the target. The row still declares the field, so the gate accepts a hand-written one.
    """
    out = tmp_path / 'kitchen'
    assert _run(FIXTURES_DIR / KITCHEN, out).returncode == 0
    texts = parts(_files(out), ACTIONS)
    assert texts, 'the kitchen sink names units the push shape can name'
    for path, text in texts.items():
        assert not any(line.strip().startswith('devices =') for line in text.split('\n')), path
        blocks = sanity_checks.blocks({path: text}, ('action',))
        assert any(block.rtype == PUSH for block in blocks), path
    assert 'devices' in resource_mapping.ACTION_SCHEMA[PUSH][1], 'the row declares it, the emitter prints none'
    assert sanity_checks.check_actions(texts) == [], [f.render() for f in sanity_checks.check_actions(texts)]


def test_the_push_block_prints_after_the_commit_block(tmp_path):
    """Within one unit the blocks print in the `ACTION_SCHEMA` order, which is the order a push follows a
    commit, and the two blocks share one address.
    """
    out = tmp_path / 'kitchen'
    assert _run(FIXTURES_DIR / KITCHEN, out).returncode == 0
    rows = commit_actions.build_rows(_manifest(out), naming.sanitize)
    order = list(resource_mapping.ACTION_SCHEMA)
    assert order[0] == 'panos_commit' and order[1] == PUSH, order
    for path, text in parts(_files(out), ACTIONS).items():
        blocks = sanity_checks.blocks({path: text}, ('action',))
        unit_rows = sorted((row for row in rows if row['directory'] == Path(path).parent.name),
                           key=lambda row: order.index(row['action']))
        assert [block.rtype for block in blocks] == [row['action'] for row in unit_rows], (path, blocks)
        assert len({block.local for block in blocks}) == 1, (path, blocks)


def test_check_order_names_actions_after_scope_blocks(tmp_path):
    """The report order places the action rule after the scope rule, and the gate runs it in a default run
    with no flag.
    """
    assert sanity_checks.CHECK_ORDER.index('actions') == sanity_checks.CHECK_ORDER.index('scope_blocks') + 1
    assert _run(SAMPLE_CONFIG, tmp_path).returncode == 0
    report = sanity_checks.run_checks(tmp_path)
    assert [result.check for result in report.checks] == list(sanity_checks.CHECK_ORDER)
    assert any(result.check == 'actions' and result.result == 'PASS' for result in report.checks)
