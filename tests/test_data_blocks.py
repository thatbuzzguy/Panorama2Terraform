"""F5.5: read-through data blocks.

A read-through `data` block is written for a name the run did not read. Six rules,
one per group here:

1. One block reader (`sanity_checks.blocks`) serves every block kind, so the `import`
   and `action` rules Epic 6 adds use the same reader.
2. The gate rule for a `data` block: the type is in `DATA_SOURCE_SCHEMA`, the
   `location` sub-block and its fields are ones that row declares, and `name` is
   present when the row declares one. A row with no `name` is not refused for having
   none.
3. A `.name` reference resolves to a block of its own kind.
4. The emit path is opt-in: a run that declares no read-through scope writes the golden
   bytes, and a reference site that resolves nothing inside the run writes one block per
   identity.
5. No coverage section names a read-through name; the record is the `.tf` file plus the
   `README.md` label.
6. A read-through run is labelled, because a `data` block resolves at plan time.

The table itself is pinned against the live schema in tests/test_data_source_schema.py.
"""

import re
import subprocess
from pathlib import Path

import pytest

import resource_mapping
import sanity_checks
from conftest import FIXTURES_DIR, GOLDEN_DIR, SAMPLE_CONFIG, run_pipeline, run_script
from panorama_to_terraform import ADDR_SCOPES, REFERENCE_SCOPES, TerraformGenerator

CONVERTER = 'panorama_to_terraform.py'
READ_THROUGH = 'read_through.tf'

# The fixtures that produce output. The hostile fixtures fail before they write a
# file, so the gate never sees them (tests/test_robustness.py pins that path).
FIXTURES = sorted(p.name for p in FIXTURES_DIR.glob('*.xml') if not p.name.startswith('hostile_'))

# The read-through scopes, as the CLI would take them: only a reference scope whose
# row declares `name` can be a target.
SCOPES_WITH_NAME = sorted(scope for scope in REFERENCE_SCOPES if resource_mapping.DATA_SOURCE_SCHEMA[scope][0])

# A `data` block that follows the table for its type.
GOOD_BLOCK = ('data "panos_address" "web_11111111" {\n  name = "Web"\n'
              '  location = {\n    device_group = {\n      name = "DG-A"\n'
              '      panorama_device = "Panorama-1"\n    }\n  }\n}\n')


def _run(source: Path, out_dir: Path, extra: tuple = ()) -> subprocess.CompletedProcess:
    """Run the converter and return the process result."""
    return run_script(CONVERTER, str(source), '--output-dir', str(out_dir), *extra)


def _files(out_dir: Path) -> dict:
    """The `.tf` files the run wrote, as text."""
    return {path.name: path.read_text(encoding='utf-8') for path in sorted(out_dir.glob('*.tf'))}


@pytest.fixture
def gen(tmp_path):
    """A generator with one read-through scope declared."""
    return TerraformGenerator(str(tmp_path), data_scopes={'panos_address'})


# --- 1. one block reader -----------------------------------------------------

def test_the_reader_reads_a_data_block_as_a_block_of_its_own_kind():
    files = {
        'a.tf': 'resource "panos_address" "web_11111111" {\n  location = { shared = {} }\n}\n',
        'b.tf': 'data "panos_address" "web_11111111" {\n  name = "Web"\n'
                '  location = { shared = {} }\n}\n',
    }
    assert [(b.kind, b.rtype, b.local) for b in sanity_checks.blocks(files)] == [
        ('resource', 'panos_address', 'web_11111111'),
        ('data', 'panos_address', 'web_11111111'),
    ]
    assert [b.kind for b in sanity_checks.resource_blocks(files)] == ['resource']
    assert [b.kind for b in sanity_checks.data_blocks(files)] == ['data']


def test_the_same_reader_serves_the_kinds_epic_6_will_check():
    """F6.4 (import) and F6.7 (action) add rules that read a block. The reader here is
    the one they use, so no second block reader appears."""
    files = {
        'c.tf': 'import "panos_address" "web_11111111" {\n  id = "abc"\n'
                '  to = panos_address.web_11111111\n}\n',
        'd.tf': 'action "panos_commit" "commit" {\n  location = { shared = {} }\n}\n',
    }
    assert [b.kind for b in sanity_checks.blocks(files)] == ['import', 'action']
    assert sanity_checks.data_blocks(files) == []


def test_the_gate_counts_resources_only(tmp_path):
    """The console summary line names resources, so a `data` block does not change it:
    the same input with and without the opt-in reports the same resource count."""
    plain = _run(SAMPLE_CONFIG, tmp_path / 'plain')
    read = _run(SAMPLE_CONFIG, tmp_path / 'read', ('--data-blocks', 'panos_address'))
    assert plain.returncode == 0 and read.returncode == 0
    assert sanity_checks.run_checks(tmp_path / 'plain').resource_count == \
        sanity_checks.run_checks(tmp_path / 'read').resource_count
    assert len(sanity_checks.data_blocks(_files(tmp_path / 'read'))) > 0


# --- 2. the gate rule for a data block ---------------------------------------

def test_the_data_check_passes_a_block_that_follows_the_table():
    assert sanity_checks.check_data_blocks({'a.tf': GOOD_BLOCK}) == []


def test_the_data_check_reports_a_type_outside_the_table():
    files = {'bad.tf': 'data "panos_made_up_type" "x_11111111" {\n  name = "x"\n'
                       '  location = { shared = {} }\n}\n'}
    findings = sanity_checks.check_data_blocks(files)
    assert len(findings) == 1
    assert findings[0].check == 'data_blocks'
    assert findings[0].severity == sanity_checks.FAIL
    assert findings[0].detail == 'data panos_made_up_type.x_11111111 is not in DATA_SOURCE_SCHEMA'


def test_the_data_check_reports_a_sub_block_the_type_does_not_declare():
    files = {'bad.tf': 'data "panos_address" "web_11111111" {\n  name = "Web"\n'
                       '  location = { template = { name = "T-1" } }\n}\n'}
    findings = sanity_checks.check_data_blocks(files)
    assert len(findings) == 1
    assert findings[0].detail == (
        'data panos_address.web_11111111 location.template is not a sub-block '
        'panos_address declares')


def test_the_data_check_reports_a_field_the_type_does_not_declare():
    files = {'bad.tf': 'data "panos_address" "web_11111111" {\n  name = "Web"\n'
                       '  location = { device_group = { name = "DG-A" vsys = "v1" } }\n}\n'}
    findings = sanity_checks.check_data_blocks(files)
    assert len(findings) == 1
    assert findings[0].detail == (
        'data panos_address.web_11111111 location.device_group.vsys is not a field '
        'panos_address declares')


def test_the_data_check_reports_a_missing_name_for_a_type_that_declares_one():
    files = {'bad.tf': 'data "panos_address" "web_11111111" {\n  location = { shared = {} }\n}\n'}
    findings = sanity_checks.check_data_blocks(files)
    assert len(findings) == 1
    assert findings[0].detail == (
        'data panos_address.web_11111111 has no name, which panos_address declares')


def test_a_no_name_type_is_not_refused_for_having_no_name():
    """The 22 rows that declare no `name` (the settings, policy, and collection shapes)
    are correct without one, so the rule is stated per row."""
    files = {'ok.tf': 'data "panos_general_settings" "s_11111111" {\n'
                      '  location = { template = { name = "T-1" } }\n}\n'}
    assert sanity_checks.check_data_blocks(files) == []


def test_location_presence_is_one_rule_for_both_kinds():
    """The missing `location` block is the `location_present` finding, so the `data` rule
    does not report the same fact twice."""
    files = {'bad.tf': 'data "panos_address" "web_11111111" {\n  name = "Web"\n}\n'}
    findings = sanity_checks.check_location_present(files)
    assert len(findings) == 1
    assert findings[0].detail == 'data panos_address.web_11111111 has no location block'
    assert sanity_checks.check_data_blocks(files) == []
    resource = sanity_checks.check_location_present(
        {'r.tf': 'resource "panos_address" "web_11111111" {\n  name = "Web"\n}\n'})
    assert resource[0].detail == 'resource panos_address.web_11111111 has no location block'


def test_the_data_check_row_is_in_the_fixed_report_order(tmp_path):
    """The report order is fixed, so a run that gains the new row still prints the same
    order between runs."""
    result = _run(SAMPLE_CONFIG, tmp_path, ('--data-blocks', 'panos_address'))
    assert result.returncode == 0, result.stdout + result.stderr
    text = (tmp_path / 'SANITY_REPORT.txt').read_text(encoding='utf-8')
    rows = [line.split()[0] for line in text.split('CHECK RESULTS')[1].split('FINDINGS')[0].split('\n')
            if line.split() and line.split()[0] in sanity_checks.CHECK_ORDER]
    assert rows == list(sanity_checks.CHECK_ORDER)
    assert rows.index('data_blocks') == rows.index('location_present') + 1


def test_the_data_check_reports_no_finding_on_the_corpus(tmp_path):
    """No false positive: every fixture run with the read-through scopes opted in writes
    blocks that follow the table, and the gate still passes."""
    for fixture in FIXTURES:
        out = tmp_path / fixture
        result = _run(FIXTURES_DIR / fixture, out, ('--data-blocks', ','.join(SCOPES_WITH_NAME)))
        assert result.returncode == 0, f'{fixture}: {result.stderr[-400:]}'
        findings = sanity_checks.check_data_blocks(_files(out))
        assert findings == [], f'{fixture}: ' + ', '.join(f.render() for f in findings)


# --- 3. a reference resolves to a block of its own kind ----------------------

def test_a_data_reference_resolves_to_the_data_block():
    files = {
        'a.tf': GOOD_BLOCK,
        'b.tf': 'resource "panos_security_policy_rules" "r_11111111" {\n  location = { shared = {} }\n'
                '  source_addresses = [data.panos_address.web_11111111.name]\n}\n',
    }
    assert sanity_checks.check_references(files) == []


def test_a_plain_reference_cannot_resolve_to_a_data_block():
    files = {
        'a.tf': GOOD_BLOCK,
        'b.tf': 'resource "panos_security_policy_rules" "r_11111111" {\n  location = { shared = {} }\n'
                '  source_addresses = [panos_address.web_11111111.name]\n}\n',
    }
    findings = sanity_checks.check_references(files)
    assert len(findings) == 1
    assert findings[0].detail == 'dangling reference panos_address.web_11111111.name'


def test_a_data_reference_to_a_block_the_run_did_not_write_is_dangling():
    files = {'a.tf': 'resource "panos_security_policy_rules" "r_11111111" {\n  location = { shared = {} }\n'
                     '  source_addresses = [data.panos_address.ghost.name]\n}\n'}
    findings = sanity_checks.check_references(files)
    assert len(findings) == 1
    assert findings[0].detail == 'dangling reference data.panos_address.ghost.name'


# --- 4. the emit path --------------------------------------------------------

def test_a_run_that_declares_no_read_through_scope_writes_the_golden_bytes(tmp_path):
    """The default keeps the plain-string rule, so the committed goldens are unchanged
    and no read-through file is written."""
    result = _run(SAMPLE_CONFIG, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    golden = {path.name: path.read_bytes() for path in sorted((GOLDEN_DIR / 'sample').glob('*.tf'))}
    assert {path.name: path.read_bytes() for path in sorted(tmp_path.glob('*.tf'))} == golden
    assert READ_THROUGH not in _files(tmp_path)


def test_a_name_outside_the_run_becomes_one_data_block(tmp_path):
    result = _run(SAMPLE_CONFIG, tmp_path, ('--data-blocks', 'panos_address'))
    assert result.returncode == 0, result.stdout + result.stderr
    files = _files(tmp_path)
    blocks = sanity_checks.data_blocks({READ_THROUGH: files[READ_THROUGH]})
    assert blocks, 'the run wrote no data block'
    for block in blocks:
        # A block holds the type, the name, and the location, and nothing else.
        keys = sorted(set(re.findall(r'^  ([A-Za-z0-9_]+) =', block.body, re.M)))
        assert keys == ['location', 'name'], block.render()
        assert f'data.{block.rtype}.{block.local}.name' in '\n'.join(files.values())
    # The reference sites name the blocks the file wrote, so the gate resolves them.
    assert sanity_checks.check_references(files) == []


def test_a_name_that_resolves_inside_the_run_stays_a_resource_reference(gen):
    """A read-through scope does not turn a name the run declared into a block."""
    local = gen.declare_resource_name('Web', 'panos_address', context='DG-A')
    ref = gen.name_ref('Web', ADDR_SCOPES, context='DG-A')
    assert str(ref) == f'panos_address.{local}.name'
    assert gen._data_blocks == {}


def test_two_reference_sites_with_the_same_identity_share_one_block(gen):
    first = gen.name_ref('Ghost', ADDR_SCOPES, context='DG-A')
    again = gen.name_ref('Ghost', ADDR_SCOPES, context='DG-A')
    assert str(first) == str(again)
    assert len(gen._data_blocks) == 1


def test_two_contexts_write_two_blocks(gen):
    first = gen.name_ref('Ghost', ADDR_SCOPES, context='DG-A')
    second = gen.name_ref('Ghost', ADDR_SCOPES, context='DG-B')
    assert str(first) != str(second)
    assert len(gen._data_blocks) == 2


def test_an_ambiguous_device_name_stays_a_plain_string(gen):
    """F3.5 and F3.6 stay in force: a name two devices declare is a guess, so the
    read-through branch does not run for it."""
    gen.declare_resource_name('Web', 'panos_address', context='DG-A', device='fw-1')
    gen.declare_resource_name('Web', 'panos_address', context='DG-A', device='fw-2')
    assert gen.name_ref('Web', ADDR_SCOPES, context='DG-A') == 'Web'
    assert gen._data_blocks == {}


def test_the_block_type_is_the_first_opted_in_scope_in_the_lookup_order(gen):
    """ADDR_SCOPES is (object, group). Only the group is opted in here, so the block type
    is the group."""
    gen.data_scopes = frozenset({'panos_address_group'})
    assert str(gen.name_ref('Ghost', ADDR_SCOPES, context='DG-A')).startswith(
        'data.panos_address_group.')


def test_the_read_through_path_cannot_change_a_resource_name(tmp_path):
    """The name rule is one rule (F2.7), so a read-through block takes the name the
    object would have had as a resource, and a block a reference site creates enters no
    declaration index."""
    gen = TerraformGenerator(str(tmp_path), data_scopes={'panos_address'})
    local = str(gen.name_ref('Web', ADDR_SCOPES, context='DG-A')).split('.')[2]
    assert re.fullmatch(r'web_[0-9a-f]{8}', local), local
    assert gen._flat_registry == {}, 'a data block is not a declaration index entry'
    plain_run = TerraformGenerator(str(tmp_path / 'plain'))
    assert plain_run.declare_resource_name('Web', 'panos_address', 'DG-A') == local


def test_the_data_path_targets_only_types_that_declare_name():
    """Every reference scope has a row, declares `name`, and has a `location` row the
    generator can render, so `--data-blocks` can never pick a type the rule cannot read."""
    for scope in REFERENCE_SCOPES:
        assert scope in resource_mapping.DATA_SOURCE_SCHEMA, scope
        assert resource_mapping.DATA_SOURCE_SCHEMA[scope][0], scope
        assert scope in resource_mapping.LOCATION_SCHEMA, scope


# --- 5. the CLI opt-in -------------------------------------------------------

def test_a_data_source_that_answers_no_reference_is_an_argument_error(tmp_path):
    """A data source outside the reference sets cannot answer a name a reference needs,
    so the CLI refuses it. Every reference scope declares `name` (pinned by
    `test_the_data_path_targets_only_types_that_declare_name`), so the `name` half of the
    rule cannot fire today: it stands for a reference scope a future feature adds."""
    result = _run(SAMPLE_CONFIG, tmp_path, ('--data-blocks', 'panos_general_settings'))
    assert result.returncode == 2
    assert 'answers no reference' in result.stderr


def test_a_scope_outside_the_reference_sets_is_an_argument_error(tmp_path):
    result = _run(SAMPLE_CONFIG, tmp_path, ('--data-blocks', 'panos_zone_protection_profile'))
    assert result.returncode == 2
    assert 'a scope a reference resolves against' in result.stderr


def test_data_blocks_needs_at_least_one_scope(tmp_path):
    result = _run(SAMPLE_CONFIG, tmp_path, ('--data-blocks', ' '))
    assert result.returncode == 2
    assert 'needs at least one scope' in result.stderr


def test_a_list_and_a_repeated_argument_are_both_read(tmp_path):
    result = _run(SAMPLE_CONFIG, tmp_path, ('--data-blocks', 'panos_address,panos_zone',
                                           '--data-blocks', 'panos_service'))
    assert result.returncode == 0, result.stdout + result.stderr
    readme = (tmp_path / 'README.md').read_text(encoding='utf-8')
    assert 'read-through scopes (panos_address, panos_service, panos_zone)' in readme


# --- 6. the reports ----------------------------------------------------------

def test_no_coverage_section_names_a_read_through_name(tmp_path):
    """The entry report, the property scan, and the shadow scan read entries the parse
    captured, so a read-through name cannot enter them: the report bytes are the same
    with and without the opt-in."""
    plain = _run(SAMPLE_CONFIG, tmp_path / 'plain')
    read = _run(SAMPLE_CONFIG, tmp_path / 'read', ('--data-blocks', 'panos_address'))
    assert plain.returncode == 0 and read.returncode == 0
    for name in ('CONVERSION_REPORT.txt', 'SOURCE.txt'):
        assert (tmp_path / 'plain' / name).read_bytes() == (tmp_path / 'read' / name).read_bytes(), name
    for name in ('any', 'Public-IP'):
        assert name not in (tmp_path / 'read' / 'CONVERSION_REPORT.txt').read_text(), name


def test_the_property_scan_records_no_read_through_name(converter_module, tmp_path):
    """The read-through path reads no captured object, so the property record is the same
    for both runs."""
    plain = run_pipeline(converter_module, None, tmp_path / 'plain', extra_args=(str(SAMPLE_CONFIG),))
    read = run_pipeline(converter_module, None, tmp_path / 'read',
                        extra_args=(str(SAMPLE_CONFIG), '--data-blocks', 'panos_address'))
    assert plain is not None and read is not None
    assert plain.ledger.rows() == read.ledger.rows()
    assert plain.ledger.property_findings() == read.ledger.property_findings()


def test_the_manual_setup_report_can_name_a_read_through_block(tmp_path):
    """The one report that may name a read-through name is the manual setup report,
    through the existing F3.5 and F3.6 location rules: a read-through block whose location
    cannot be resolved is reported by the rule that already reports it."""
    result = _run(SAMPLE_CONFIG, tmp_path, ('--data-blocks', 'panos_zone'))
    assert result.returncode == 0, result.stdout + result.stderr
    manual = (tmp_path / 'MANUAL_SETUP_REPORT.txt').read_text(encoding='utf-8')
    report = (tmp_path / 'CONVERSION_REPORT.txt').read_text(encoding='utf-8')
    assert 'panos_zone "Trust"' in manual
    assert 'Trust' not in report


# --- 7. the README label -----------------------------------------------------

def test_a_read_through_run_labels_itself(tmp_path):
    result = _run(SAMPLE_CONFIG, tmp_path, ('--data-blocks', 'panos_address'))
    assert result.returncode == 0, result.stdout + result.stderr
    readme = (tmp_path / 'README.md').read_text(encoding='utf-8')
    assert '## Read-through data blocks' in readme
    assert 'resolves at plan time' in readme
    count = len(sanity_checks.data_blocks(_files(tmp_path)))
    assert f'with {count} data blocks' in readme
    assert count > 0


def test_a_run_that_declares_no_read_through_scope_writes_the_same_readme(tmp_path):
    """The label is the only difference a read-through run makes to the README."""
    plain = _run(SAMPLE_CONFIG, tmp_path / 'plain')
    read = _run(SAMPLE_CONFIG, tmp_path / 'read', ('--data-blocks', 'panos_address'))
    assert plain.returncode == 0 and read.returncode == 0
    baseline = (tmp_path / 'plain' / 'README.md').read_text(encoding='utf-8')
    label = (tmp_path / 'read' / 'README.md').read_text(encoding='utf-8')
    assert 'Read-through data blocks' not in baseline
    head, tail = baseline.split('## Important Notes')
    assert label.startswith(head)
    assert label.endswith(tail)


# --- 8. determinism and the exit code ----------------------------------------

def test_the_read_through_file_is_byte_identical_between_runs(tmp_path):
    args = ('--data-blocks', 'panos_address,panos_zone')
    first = _run(SAMPLE_CONFIG, tmp_path / 'a', args)
    second = _run(SAMPLE_CONFIG, tmp_path / 'b', args)
    assert first.returncode == 0 and second.returncode == 0
    for name in (READ_THROUGH, 'SANITY_REPORT.txt', 'CONVERSION_REPORT.txt', 'README.md'):
        assert (tmp_path / 'a' / name).read_bytes() == (tmp_path / 'b' / name).read_bytes(), name


def test_a_data_block_that_breaks_the_table_fails_the_gate(tmp_path):
    """The exit code is still the gate's decision (F4.1), and the new rule is a FAIL."""
    out = tmp_path / 'out'
    result = _run(SAMPLE_CONFIG, out, ('--data-blocks', 'panos_address'))
    assert result.returncode == 0, result.stdout + result.stderr
    (out / READ_THROUGH).write_text(
        'data "panos_address" "web_11111111" {\n  name = "Web"\n'
        '  location = { template = { name = "T-1" } }\n}\n', encoding='utf-8')
    report = sanity_checks.run_checks(out)
    assert report.failed, report.render()
    assert report.result_of('data_blocks') == 'FAIL'
