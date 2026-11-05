"""F7.14: the certificate gate rule (`sanity_checks.check_certificate_blocks`).

`resource_mapping.CERTIFICATE_SHAPE` is the one table that states the shape of a certificate block, and
`resource_mapping.CERTIFICATE_TABLE` is the object the emitter and the gate both read it through, so no second
table names a certificate shape. The rule reads the block through the one block reader (`sanity_checks.blocks`)
and the one field reader (`import_blocks.fields_at`) that every block rule uses, so no second reader appears.
It reads the type to row lookup through `resource_mapping.CERTIFICATE_TYPES`, and the entry name through
`entry_coverage.name_field`, so the rule states no type and no field name of its own. The one-shape-owner rule
for the three shape tables is pinned in `tests/test_protocol_object.py::test_the_table_is_the_only_shape_owner`.

Pins:

- the rule reads the block through the two readers, at the block's own level, and `location` is the placement
  fact `location_present` owns, so the rule reads no sub-block and states no reader of its own;
- the type to row lookup reads `CERTIFICATE_TYPES` the other way, and the entry name reads through the one
  naming rule for both entry rows;
- the table states a row for every level the walk enters, so the level finding cannot fire for a certificate
  block, and the `sensitive` fact sits only inside `local`;
- one test per finding: a field the row does not declare, a value read as another shape, the block states no
  entry name, the exactly-one choice `certificate/local` states as `selects`, a `sensitive` field printed as a
  literal, and an element inside a `[` container that states no name;
- the gate reads the real run and reports nothing, the gate order puts the rule after `filter_blocks`, and the
  report is byte-identical between two runs, so no golden moves;
- a `sensitive` field prints as `var.` plus the §5 name of the entry that holds the field, read through
  `naming.py`. The literal half is held by
  `tests/test_robustness.py::test_a_parsed_secret_never_reaches_a_generated_file`, and no FAIL on any fixture is
  held by the corpus pin in `tests/test_sanity_gate.py`.
"""

import ast
import inspect
import textwrap
from pathlib import Path

import entry_coverage
import import_blocks
import naming
import resource_mapping
import sanity_checks
from conftest import FIXTURES_DIR, run_script, tf_files

CONVERTER = 'panorama_to_terraform.py'
FIXTURE = 'certificates.xml'

# A block a test hand-writes is read by the rule, so the address a finding prints is this one.
LOCAL = 'cert_00000000'

# A block that reads clean against its row, so each test changes one part of it.
GOOD_IMPORT = ('  name = "Edge-Cert"\n  local = {\n    pem = {\n      certificate = "edge-pem-value"\n'
               '      passphrase = var.edge_cert\n      private_key = var.edge_cert\n    }\n  }\n')
GOOD_PROFILE = ('  name = "Strict-OCSP"\n  use_ocsp = true\n  certificate = [\n    {\n'
                '      name = "Edge-Cert"\n    }\n  ]\n  username_field = {\n    subject = "cn"\n  }\n')


def _run(fixture: str, out_dir) -> dict:
    """Run the converter on one fixture and return the output files as text.

    The `.tf` set is read as the gate reads it, so a `.tf` entry holds the parts the run wrote for every unit,
    in path order, and a report is a codebase root-set file keyed by its name.
    """
    result = run_script(CONVERTER, str(FIXTURES_DIR / fixture), '--output-dir', str(out_dir))
    assert result.returncode == 0, result.stdout + result.stderr
    tf = tf_files(out_dir)
    files = {}
    for name in sorted({Path(key).name for key in tf}):
        files[name] = ''.join(tf[key] for key in sorted(tf) if Path(key).name == name)
    for path in sorted(Path(out_dir).iterdir()):
        if path.is_file():
            files[path.name] = path.read_text(encoding='utf-8')
    return files


def _row(path: str) -> dict:
    """One row of the shape table, read through the table object the rule uses."""
    row = resource_mapping.CERTIFICATE_TABLE.row(path)
    assert row is not None, path
    return row


def _findings(path: str, body: str) -> list:
    """One certificate block written by hand, read by the rule.

    `path` is the entry row the block is read against, so the block's own level is the level the walk enters.
    """
    return sanity_checks.check_certificate_blocks({
        'certificates.tf': f'resource "{resource_mapping.CERTIFICATE_TYPES[path]}" "{LOCAL}" {{\n{body}}}\n'})


def _detail(level: str, text: str) -> str:
    """A finding as the rule states it: the block address, then the level, then the field.

    The entry row a level belongs to is the first part of the level path, which is the key `CERTIFICATE_TYPES`
    names, so the pin states no type of its own.
    """
    return f'certificate {resource_mapping.CERTIFICATE_TYPES[level.split("/")[0]]}.{LOCAL} {level} {text}'


def _name_detail(path: str) -> str:
    """The entry-name finding: the address, then the field the one naming rule reads."""
    name_field = entry_coverage.name_field(resource_mapping.CERTIFICATE_TYPES[path])
    return (f'certificate {resource_mapping.CERTIFICATE_TYPES[path]}.{LOCAL} states no {name_field}, '
            f'which is the field entry_coverage.name_field reads for the entry name')


def _constants(source: str) -> set:
    """The string constants in one source, so a pin can check what a rule states."""
    return {node.value for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)}


def _rule_source() -> str:
    """The rule's own source, so a pin can read what it states."""
    return textwrap.dedent(inspect.getsource(sanity_checks.check_certificate_blocks))


def _block_fields(text: str) -> dict:
    """The fields at one block's own level, through the one field reader."""
    body = text[text.index('{\n') + 1:text.rindex('}\n')]
    return import_blocks.fields_at(body)


# --- 1. the two readers and the placement fact --------------------------------

def test_the_rule_reads_the_block_through_the_gate_readers():
    """The rule takes the file text, so a hand-written block is an input the gate reads, and the block it reads
    is the same object the reader gives every other block rule."""
    block = ('resource "panos_certificate_import" "edge_cert_47923f51" {\n  location = { shared = {} }\n'
             '  name = "Edge-Cert"\n}\n')
    files = {'certificates.tf': block}
    read = sanity_checks.blocks(files, ('resource',))
    assert [b.address for b in read] == ['panos_certificate_import.edge_cert_47923f51'], read
    assert _block_fields(block)['name'] == '"Edge-Cert"', block
    rule = _rule_source()
    body = rule.split('\n', 1)[1]
    assert 'blocks(files, ' in body and 'import_blocks.fields_at(' in body, rule
    assert 'def ' not in body and 're.search' not in body and 're.compile' not in body, \
        'the rule states no reader and no helper of its own'


def test_the_gate_does_not_read_the_location_sub_block():
    """The placement is the `location_present` rule, so the rule reads the block's own fields only."""
    path = 'certificate'
    block = ('resource "panos_certificate_import" "edge_cert_47923f51" {\n'
             '  location = {\n    vsys = {\n      name = "vsys1"\n    }\n  }\n  name = "Edge-Cert"\n}\n')
    assert 'location' in _block_fields(block), block
    assert 'location' not in _row(path)['fields'], _row(path)['fields']
    assert sanity_checks.check_certificate_blocks({'certificates.tf': block}) == [], block


# --- 2. the lookup and the one naming rule ------------------------------------

def test_the_type_row_lookup_is_the_table_read_the_other_way():
    """The rule reads `CERTIFICATE_TYPES` through `certificate_path`, so it states no resource type."""
    for path, resource in sorted(resource_mapping.CERTIFICATE_TYPES.items()):
        assert resource_mapping.certificate_path(resource) == path, (path, resource)
    assert resource_mapping.certificate_path('panos_zone') is None
    rule = _rule_source()
    assert not any(name in rule for name in resource_mapping.CERTIFICATE_TYPES.values()), \
        'the rule states no type of its own'


def test_the_entry_name_is_read_through_the_one_naming_rule():
    """`name_field` answers for both entry rows, so the rule states no field for the entry name. The rule states
    no field name the table declares: the name is read through the one naming rule, and the only name it states
    is `location`, the placement sub-block `location_present` owns."""
    for resource in sorted(resource_mapping.CERTIFICATE_TYPES.values()):
        assert entry_coverage.name_field(resource) == 'name', resource
    rule = _rule_source()
    assert 'entry_coverage.name_field(' in rule, 'the rule reads the name through the one naming rule'
    fields = {field for row in resource_mapping.CERTIFICATE_TABLE.rows.values() for field in row['fields']}
    assert _constants(rule) & fields == set(), _constants(rule) & fields
    assert 'location' in _constants(rule), 'the rule names the sub-block it excludes'


# --- 3. what the table can and cannot state -----------------------------------

def test_the_table_states_a_row_for_every_level_the_walk_enters():
    """The level finding cannot fire for a certificate block: every field the walk enters has a row under it,
    and every key `selects` names has a row for its alternative. `sensitive` is stated only inside `local`,
    which is the set `tests/test_protocol_object.py::test_the_sensitive_rows_are_the_reference_only_names`
    reads against `VALUE_VARIABLES`, the table the emitter reads at the print site."""
    table = resource_mapping.CERTIFICATE_TABLE
    for path, row in sorted(table.rows.items()):
        for field, shape in row['fields'].items():
            if shape in sanity_checks.SHAPE_LEVELS:
                assert table.row(f'{path}/{field}') is not None, (path, field)
        for key in row['selects'].values():
            assert table.row(f'{path}/{key}') is not None, (path, key)
    assert sorted(path for path, row in table.rows.items() if row['sensitive']) == [
        'certificate/local/pem', 'certificate/local/pkcs12']


# --- 4. one test per finding ---------------------------------------------------

def test_the_rule_refuses_a_field_the_row_does_not_declare():
    """Finding 1, first half: a field the entry row does not declare."""
    for path, good in (('certificate', GOOD_IMPORT), ('certificate_profile', GOOD_PROFILE)):
        assert _findings(path, good) == [], good
        findings = _findings(path, good + '  made_up = "x"\n')
        assert [f.detail for f in findings] == [
            _detail(path, 'made_up is not a field CERTIFICATE_SHAPE declares')], (path, findings)
        assert [f.check for f in findings] == ['certificate_blocks'], findings
        assert findings[0].severity == sanity_checks.FAIL, findings[0]


def test_the_rule_refuses_a_value_read_as_another_shape():
    """Finding 1, second half: a value the reader reads differently from the shape the row states."""
    path = 'certificate'
    assert _findings(path, GOOD_IMPORT) == [], GOOD_IMPORT
    findings = _findings(path, GOOD_IMPORT.replace('local = {', 'local = "pem"'))
    assert [f.detail for f in findings] == [_detail(path, 'local is not a one_of value')], findings
    path = 'certificate_profile'
    assert _findings(path, GOOD_PROFILE) == [], GOOD_PROFILE
    findings = _findings(path, GOOD_PROFILE.replace('use_ocsp = true', 'use_ocsp = "true"'))
    assert [f.detail for f in findings] == [_detail(path, 'use_ocsp is not a bool value')], findings
    findings = _findings(path, GOOD_PROFILE.replace(
        'certificate = [\n    {\n      name = "Edge-Cert"\n    }\n  ]', 'certificate = "Edge-Cert"'))
    assert [f.detail for f in findings] == [_detail(path, 'certificate is not a string_list value')], findings


def test_the_rule_refuses_a_block_that_states_no_entry_name():
    """Finding 2: the block states no name. The field rule reads only the fields the block states, so the name
    is read by the name rule, and a certificate entry has no name a reference resolves."""
    path = 'certificate'
    without = GOOD_IMPORT.replace('  name = "Edge-Cert"\n', '')
    assert 'name' not in _block_fields(_find_block(path, without)), without
    findings = _findings(path, without)
    assert [f.detail for f in findings] == [_name_detail(path)], findings
    # The name is read first, because the block states it before its content, which is the print order too.
    findings = _findings(path, '  made_up = {}\n')
    assert [f.detail for f in findings] == [
        _name_detail(path), _detail(path, 'made_up is not a field CERTIFICATE_SHAPE declares')], findings
    assert [f.check for f in findings] == ['certificate_blocks'] * 2, findings
    assert [f.line for f in findings] == [1, 1], findings


def _find_block(path: str, body: str) -> str:
    """The hand-written block the pin reads, so a helper can read its fields the same way."""
    return (f'resource "{resource_mapping.CERTIFICATE_TYPES[path]}" "{LOCAL}" {{\n{body}}}\n')


def test_the_rule_reads_the_choice_at_the_level_the_walk_enters():
    """Finding 3 (F7.12): `certificate/local` states exactly one of the keys `selects` names, so two keys or
    none is a finding, and a key the row does not select is the choice finding. The choice is read before the
    field rule, so a selected key is not read twice."""
    path, level = 'certificate', 'certificate/local'
    assert _findings(path, GOOD_IMPORT) == [], GOOD_IMPORT
    for key in sorted(resource_mapping.CERTIFICATE_TABLE.row(level)['selects'].values()):
        one = f'  name = "Edge-Cert"\n  local = {{\n    {key} = {{}}\n  }}\n'
        assert _findings(path, one) == [], (key, one)
    stated = '  name = "Edge-Cert"\n  local = {\n    pem = {}\n    pkcs12 = {}\n  }\n'
    assert [f.detail for f in _findings(path, stated)] == [
        _detail(level, 'states 2 keys, which is not the one key CERTIFICATE_SHAPE selects')]
    none = '  name = "Edge-Cert"\n  local = {\n  }\n'
    assert [f.detail for f in _findings(path, none)] == [
        _detail(level, 'states 0 keys, which is not the one key CERTIFICATE_SHAPE selects')]
    wrong = '  name = "Edge-Cert"\n  local = {\n    ssh = {}\n  }\n'
    assert [f.detail for f in _findings(path, wrong)] == [
        _detail(level, 'key ssh is not a key CERTIFICATE_SHAPE selects')]
    # One selected key plus one key the row does not select is one finding, because the choice is read first.
    assert [f.detail for f in _findings(path, '  name = "Edge-Cert"\n  local = {\n    pem = {}\n'
                                              '    made_up = {}\n  }\n')] == [
        _detail(level, 'key made_up is not a key CERTIFICATE_SHAPE selects')]
    # With one key stated, the field rule still reads the fields the row states.
    findings = _findings(path, '  name = "Edge-Cert"\n  local = {\n    pem = {\n'
                               '      made_up = "x"\n    }\n  }\n')
    assert [f.detail for f in findings] == [
        _detail('certificate/local/pem', 'made_up is not a field CERTIFICATE_SHAPE declares')], findings


def test_the_rule_refuses_a_sensitive_field_printed_as_a_literal():
    """Finding 4: a field the row marks `sensitive` prints as the variable reference, never as a value."""
    path = 'certificate'
    assert _findings(path, GOOD_IMPORT) == [], GOOD_IMPORT
    for field in sorted(_row('certificate/local/pem')['sensitive']):
        findings = _findings(path, GOOD_IMPORT.replace(f'{field} = var.edge_cert', f'{field} = "the value"'))
        assert [f.detail for f in findings] == [
            _detail('certificate/local/pem', f'{field} prints a sensitive value as a literal')], (field, findings)
    pkcs12 = ('  name = "Lab-Cert"\n  local = {\n    pkcs12 = {\n      certificate = "lab-pem-value"\n'
              '      passphrase = var.lab_cert\n    }\n  }\n')
    assert _findings(path, pkcs12) == [], pkcs12
    findings = _findings(path, pkcs12.replace('passphrase = var.lab_cert', 'passphrase = "the value"'))
    assert [f.detail for f in findings] == [
        _detail('certificate/local/pkcs12', 'passphrase prints a sensitive value as a literal')], findings
    # The name is not a sensitive field, so a literal is not a finding for it.
    assert _findings(path, GOOD_IMPORT.replace('certificate = "edge-pem-value"', 'certificate = "x"')) == []


def test_the_rule_refuses_an_element_that_states_no_name():
    """Finding 5: an element inside a `[` container is an entry, so it carries the name the row reads for it."""
    path = 'certificate_profile'
    assert _findings(path, GOOD_PROFILE) == [], GOOD_PROFILE
    findings = _findings(path, GOOD_PROFILE.replace('name = "Edge-Cert"\n', ''))
    assert [f.detail for f in findings] == [
        _detail('certificate_profile/certificate', 'element states no name')], findings


# --- 5. the run, the gate order, and determinism ------------------------------

def test_the_gate_reads_the_run_and_reports_nothing(tmp_path):
    """The blocks the run wrote for the two entry rows report no finding, and the report states the check.

    The run's summary is the whole gate, so the pin reads the report the run wrote, not a hand-built row. No
    FAIL on any fixture is held by the corpus pin in `tests/test_sanity_gate.py`.
    """
    files = _run(FIXTURE, tmp_path)
    assert sanity_checks.check_certificate_blocks(tf_files(tmp_path)) == [], tf_files(tmp_path)
    report = files['SANITY_REPORT.txt']
    line = next(line for line in report.split('\n') if line.startswith('certificate_blocks'))
    assert 'PASS' in line, report
    assert next(line for line in report.split('\n') if line.startswith('Result:')) == \
        'Result: PASS (0 FAIL, 0 WARN)', report
    assert sanity_checks.CHECK_ORDER.index('certificate_blocks') == (
        sanity_checks.CHECK_ORDER.index('filter_blocks') + 1), sanity_checks.CHECK_ORDER
    # The report names each check in `CHECK_ORDER` order, so the new rule reads between the two shape rules.
    named = [line.split()[0] for line in report.split('\n')
             if line.split(' ')[0] in sanity_checks.CHECK_ORDER]
    assert named == list(sanity_checks.CHECK_ORDER), named


def test_the_report_is_byte_identical_between_two_runs(tmp_path):
    """The rule writes no file, so the gate output for two runs on the same input is the same bytes and no
    golden moves."""
    first, second = tmp_path / 'first', tmp_path / 'second'
    for out in (first, second):
        assert run_script(CONVERTER, str(FIXTURES_DIR / FIXTURE), '--output-dir', str(out)).returncode == 0
    assert (first / 'SANITY_REPORT.txt').read_bytes() == (second / 'SANITY_REPORT.txt').read_bytes()
    for out in (first, second):
        assert sanity_checks.run_checks(out).findings('certificate_blocks') == []


def test_a_finding_names_the_file_and_the_line_the_reader_read(tmp_path):
    """A finding names the unit directory the file is in, through the reader that keys the `.tf` set.

    The fixture holds one import entry in a virtual system and one in a template, so the run wrote one file per
    unit, and the pin reads the file set the way the gate reads it.
    """
    run_script(CONVERTER, str(FIXTURES_DIR / FIXTURE), '--output-dir', str(tmp_path))
    written = [key for key in sorted(tf_files(tmp_path)) if Path(key).name == 'certificates.tf']
    units = {Path(key).parent.name for key in written}
    assert len(written) == 2 and len(units) == 2, written
    bad = {key: value.replace('\n}\n', '\n  made_up = "x"\n}\n', 1)
           for key, value in tf_files(tmp_path).items() if Path(key).name == 'certificates.tf'}
    findings = sanity_checks.check_certificate_blocks(bad)
    assert len(findings) == 2, findings
    assert {Path(finding.file).parent.name for finding in findings} == units, findings
    # The finding is stated at the block's header line, which is the line the one reader read.
    read = sorted(sanity_checks.blocks(bad, ('resource',)), key=lambda b: (b.file, b.line))
    assert [f.line for f in findings] == [b.line for b in read], findings
    assert [f.file for f in findings] == [b.file for b in read], findings


# --- 6. the sensitive print, read through the naming rule ---------------------

def _printed_level(fields: dict, path: str, level: str) -> dict:
    """The keys the run printed for one level, read the way the gate rule reads them."""
    for part in level[len(path):].split('/'):
        if not part:
            continue
        value = fields.get(part)
        if value is None:
            return {}
        fields = import_blocks.fields_at(import_blocks.container_body(value))
    return fields


def test_a_sensitive_field_prints_as_the_name_the_entry_names(tmp_path):
    """The reference half, grounded by a real run: the printed name is the §5 name of the entry that holds the
    field, read through `naming.py`, because a field cannot name itself."""
    _run(FIXTURE, tmp_path)
    table = resource_mapping.CERTIFICATE_TABLE
    read = 0
    for block in sanity_checks.blocks(tf_files(tmp_path), ('resource',)):
        path = resource_mapping.certificate_path(block.rtype)
        if path is None:
            continue
        fields = import_blocks.fields_at(block.body)
        entry_name = fields[entry_coverage.name_field(block.rtype)].strip('"')
        for level, row in sorted(table.rows.items()):
            if not row['sensitive'] or not level.startswith(path + '/'):
                continue
            printed = _printed_level(fields, path, level)
            for field in sorted(row['sensitive']):
                if field in printed:
                    assert printed[field] == naming.variable_text(entry_name), (block.file, field, printed)
                    read += 1
    assert read == 3, 'the fixture states two `pem` fields and one `pkcs12` field'
