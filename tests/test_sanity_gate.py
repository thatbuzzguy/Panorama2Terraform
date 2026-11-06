"""F4.1: the post-run sanity gate.

The gate runs on every conversion and checks the files the operator receives.
Each rule is implemented once in `sanity_checks.py`; the tests call the same
functions the converter calls, so the runtime gate and the test gate cannot
disagree.

Pins:

- the gate runs on a conversion and writes `SANITY_REPORT.txt`;
- the report is byte-identical between two runs on the same input;
- each check detects its own violation (one negative test per rule);
- the gate reports no FAIL finding on every fixture, so it does not lie;
- a placeholder is WARN, not FAIL, so a run that only needs an operator action
  still exits 0;
- a FAIL finding exits non-zero;
- `--validate` runs `terraform init` + `terraform validate`, and a missing
  terraform binary is SKIPPED, never a failure, so the suite stays offline;
- the plan check reports one result per unit directory the record names, so a
  `--validate` pin reads the files the run wrote;
- the splitter writes XML, so the gate has nothing to check there.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import sanity_checks
import unit_manifest
import write_path
from conftest import FIXTURES_DIR, REPO_ROOT, SAMPLE_CONFIG, SRC_DIR, run_script, tf_files

TERRAFORM = shutil.which("terraform")
# The layout rule (`docs/ARCHITECTURE.md` §1.1): the entry points are tool modules, so they sit in `src/`.
CONVERTER = SRC_DIR / "panorama_to_terraform.py"
SPLITTER = SRC_DIR / "split_device_groups.py"

# The fixtures that produce output. The hostile fixtures fail before they write
# a file, so the gate never sees them (tests/test_robustness.py pins that path).
FIXTURES = sorted(
    p.name for p in FIXTURES_DIR.glob("*.xml") if not p.name.startswith("hostile_")
)


def _generate(source: Path, out_dir: Path, extra_args: tuple[str, ...] = ()) -> subprocess.CompletedProcess:
    """Run the converter and return the CompletedProcess."""
    return run_script("panorama_to_terraform.py", str(source), "--output-dir", str(out_dir),
                      *extra_args)


# --- The gate runs on every conversion ---------------------------------------

def test_gate_runs_and_writes_the_report(tmp_path):
    """A conversion writes SANITY_REPORT.txt next to the .tf files."""
    result = _generate(SAMPLE_CONFIG, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    report_path = tmp_path / "SANITY_REPORT.txt"
    assert report_path.is_file(), "the conversion wrote no sanity report"
    text = report_path.read_text(encoding="utf-8")
    assert 'Result: PASS (0 FAIL, 0 WARN)' in text
    # Every static check names its result, so a check cannot be silently absent.
    for name in sanity_checks.CHECK_ORDER:
        expected = 'NOT RUN' if name == 'terraform' else 'PASS'
        assert re.search(rf'^{name}\s+{expected}$', text, re.M)


def test_console_summary_reports_the_result(tmp_path):
    """The console summary states the result, not only the file list."""
    result = _generate(SAMPLE_CONFIG, tmp_path)
    # F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): the count names the unit set the gate read, so the
    # sample run - two units, so two sets - measures 14 .tf files.
    summary = [line for line in result.stdout.split('\n') if line.startswith('Sanity gate:')]
    assert summary == ['Sanity gate: PASS (0 FAIL, 0 WARN) - 14 .tf files, 2 data files, 20 resources']
    assert 'Sanity report: ' in result.stdout


# --- Determinism ---------------------------------------------------------------

def test_report_is_byte_identical_between_runs(tmp_path):
    """Two runs on the same input produce the same report bytes."""
    first = _generate(SAMPLE_CONFIG, tmp_path / 'run1')
    second = _generate(SAMPLE_CONFIG, tmp_path / 'run2')
    assert first.returncode == 0 and second.returncode == 0
    assert (tmp_path / 'run1' / 'SANITY_REPORT.txt').read_bytes() == \
        (tmp_path / 'run2' / 'SANITY_REPORT.txt').read_bytes()


def test_report_names_no_timestamp_and_no_absolute_path(tmp_path):
    """Determinism needs both: no clock value and no machine-dependent path."""
    _generate(SAMPLE_CONFIG, tmp_path)
    text = (tmp_path / 'SANITY_REPORT.txt').read_text(encoding='utf-8')
    assert not re.search(r'\d{2}:\d{2}:\d{2}', text)
    assert str(tmp_path) not in text
    # The report names file names, never a path to a file.
    for line in text.split('\n'):
        if line.startswith('  '):
            assert not line.lstrip().startswith('/')


# --- Every check detects its violation ---------------------------------------

def test_emitted_types_check_detects_a_type_outside_the_mapping():
    files = {'a.tf': 'resource "panos_zone" "z_00000000" {\n  location = {\n    shared = {}\n  }\n  name = "z"\n}\n'}
    assert sanity_checks.check_emitted_types(files) == []
    bad = {'bad.tf': 'resource "panos_made_up_type" "x_00000000" {\n  name = "x"\n}\n'}
    findings = sanity_checks.check_emitted_types(bad)
    assert len(findings) == 1
    assert findings[0].check == 'emitted_types'
    assert findings[0].severity == sanity_checks.FAIL
    assert findings[0].file == 'bad.tf'
    assert findings[0].line == 1


def test_location_check_detects_a_block_without_location():
    files = {'bad.tf': 'resource "panos_address" "host_00000000" {\n  name = "host"\n}\n'}
    findings = sanity_checks.check_location_present(files)
    assert len(findings) == 1
    assert 'no location block' in findings[0].detail
    # A resource block is read up to the first column-0 brace.
    ok = {'ok.tf': 'resource "panos_address" "host_00000000" {\n  location = {\n    shared = {}\n  }\n'}
    assert sanity_checks.check_location_present(ok) == []


def test_reference_check_detects_a_dangling_reference():
    files = {
        'ok.tf': 'resource "panos_zone" "zone_00000000" {\n  location = { shared = {} }\n  name = "z"\n}\n'
                 'resource "panos_address" "host_00000000" {\n  location = { shared = {} }\n'
                 '  tags = [panos_zone.zone_00000000.name]\n}\n',
    }
    assert sanity_checks.check_references(files) == []
    bad = {
        'bad.tf': 'resource "panos_address" "host_00000000" {\n  location = { shared = {} }\n'
                  '  tags = [panos_zone.ghost.name]\n}\n',
    }
    findings = sanity_checks.check_references(bad)
    assert len(findings) == 1
    assert findings[0].detail == 'dangling reference panos_zone.ghost.name'
    assert findings[0].line == 3


def test_reference_check_reads_only_the_written_files():
    """A resource that the generator declared in memory but never wrote does not
    make a reference resolve."""
    files = {'a.tf': 'resource "panos_address" "host_00000000" {\n  location = { shared = {} }\n'
                     '  tags = [panos_service.svc_00000000.name]\n}\n'}
    findings = sanity_checks.check_references(files)
    assert len(findings) == 1
    assert findings[0].detail == 'dangling reference panos_service.svc_00000000.name'


def test_variable_check_detects_an_unconsumed_variable():
    """F2.10, the first direction: a declaration with no consumer."""
    files = {
        'variables.tf': 'variable "dead" {\n  description = "no consumer"\n}\n\n'
                        'variable "used" {\n  description = "consumed"\n}\n',
        'provider.tf': 'provider "panos" {\n  hostname = var.used\n}\n',
    }
    findings = sanity_checks.check_variables(files)
    assert len(findings) == 1
    assert findings[0].file == 'variables.tf'
    assert findings[0].line == 1
    assert 'never consumed as var.dead' in findings[0].detail


def test_variable_check_detects_a_consumer_with_no_declaration():
    """F6.6, the second direction: a `var.` reference that names no declaration this run writes.

    The declaration set comes from the value-to-variable table, so the two directions are what make a
    generated declaration set checkable.
    """
    files = {'provider.tf': 'provider "panos" {\n  hostname = var.other\n}\n'}
    findings = sanity_checks.check_variables(files)
    assert len(findings) == 1
    assert findings[0].file == 'provider.tf'
    assert findings[0].line == 2
    assert 'var.other names no variable this run declares' in findings[0].detail
    both = {
        'variables.tf': 'variable "used" {\n  description = "consumed"\n}\n',
        'provider.tf': 'provider "panos" {\n  hostname = var.used\n}\n',
    }
    assert sanity_checks.check_variables(both) == []


def test_the_report_counts_both_file_sets(tmp_path):
    """The report names the `.tf` files and the data files, so a reader can tell which set the gate read.
    The printed form of a record is not one of the four, so the count names only the records.
    """
    _generate(SAMPLE_CONFIG, tmp_path)
    report = sanity_checks.run_checks(tmp_path)
    # F6.10.3 (§14): the reader reads the unit directories below the root, so the count names the parts it
    # read by path, and every path names a unit directory.
    files = tf_files(tmp_path)
    assert report.file_count == len(files), report.render()
    assert all(Path(name).parent.name for name in files), 'the count names the unit set'
    assert report.data_file_count == 2
    assert 'Files checked: 14 .tf files, 2 data files.' in report.render(), report.render()
    assert re.search(r'^data_files\s+PASS$', report.render(), re.M)


def test_data_file_check_detects_a_row_that_is_not_the_data_it_declares(tmp_path):
    """One negative test per rule: the data rule reports a row that does not read as its declared shape,
    a field that disagrees with `naming.py`, a row that joins to nothing, and a printed form that is not
    the record rendered. Each finding names the file and the row ordinal (F6.8).
    """
    _generate(SAMPLE_CONFIG, tmp_path)
    assert sanity_checks.check_data_files(tmp_path) == []
    rows = unit_manifest.parse_rows((tmp_path / unit_manifest.MANIFEST_FILE).read_text(encoding='utf-8'))
    planted = dict(rows[1])
    planted['unit'] = 'NotTheLevelName'
    rows[1] = planted
    # Write the row back through the module, so the test states no second shape rule.
    (tmp_path / unit_manifest.MANIFEST_FILE).write_text(unit_manifest.render(rows), encoding='utf-8')
    findings = sanity_checks.check_data_files(tmp_path)
    assert len(findings) == 1, [f.render() for f in findings]
    assert findings[0].severity == sanity_checks.FAIL
    assert findings[0].file == unit_manifest.MANIFEST_FILE and findings[0].line == 2
    assert 'level rule' in findings[0].detail, findings[0].render()


def test_control_char_check_detects_a_raw_control_character():
    files = {'bad.tf': 'resource "panos_address" "host_00000000" {\n  location = { shared = {} }\n'
                       '  name = "a\x01b"\n}\n'}
    findings = sanity_checks.check_control_chars(files)
    assert len(findings) == 1
    assert findings[0].line == 3
    assert '0x01' in findings[0].detail
    # LF is the only legal raw control byte; an escaped tab in the text is fine.
    clean = {'ok.tf': 'resource "panos_address" "host_00000000" {\n  name = "a\\tb"\n}\n'}
    assert sanity_checks.check_control_chars(clean) == []
    # DEL is reported too.
    assert len(sanity_checks.check_control_chars({'d.tf': 'name = "a\x7fb"\n'})) == 1


def test_placeholder_check_warns_and_does_not_fail():
    files = {'vpn.tf': 'resource "panos_ipsec_tunnel" "t_00000000" {\n'
                       '  location = { shared = {} }\n  key = "***CHANGE_ME***"\n}\n'}
    findings = sanity_checks.check_placeholders(files)
    assert len(findings) == 1
    assert findings[0].severity == sanity_checks.WARN
    # A comment that names the marker is documentation, not an emitted value.
    commented = {'vpn.tf': '# Search for "***CHANGE_ME***" and replace it.\n'}
    assert sanity_checks.check_placeholders(commented) == []
    # A WARN-only run is not a failed gate.
    report = sanity_checks.SanityReport(
        checks=(sanity_checks.CheckResult('placeholders', tuple(findings)),),
        file_count=1, resource_count=1)
    assert report.result_of('placeholders') == 'WARN'
    assert not report.failed


# --- No false positives --------------------------------------------------------

@pytest.mark.parametrize('fixture', FIXTURES)
def test_gate_reports_no_fail_finding_on_every_fixture(fixture, tmp_path):
    """Every fixture passes the gate, so the gate reports facts, not noise."""
    out_dir = tmp_path / fixture
    result = run_script("panorama_to_terraform.py", str(FIXTURES_DIR / fixture),
                        "--output-dir", str(out_dir))
    assert result.returncode == 0, f'{fixture}: {result.stdout}\n{result.stderr}'
    report = sanity_checks.run_checks(out_dir)
    findings = [f for r in report.checks for f in r.findings if f.severity == sanity_checks.FAIL]
    assert findings == [], f'{fixture}: ' + ', '.join(f.render() for f in findings)
    assert report.file_count > 0, f'{fixture}: the gate read no .tf file'


def test_kitchen_sink_warns_about_the_placeholder_and_exits_zero(tmp_path):
    """The VPN key placeholder is an expected output, so it is a WARN, not a FAIL."""
    result = _generate(FIXTURES_DIR / 'kitchen_sink.xml', tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    text = (tmp_path / 'SANITY_REPORT.txt').read_text(encoding='utf-8')
    assert re.search(r'^placeholders\s+WARN \(\d+\)$', text, re.M)
    assert 'Result: PASS' in text
    # The WARN line names the file and the line the operator must edit. F6.10.3 (§14): a finding names
    # the path from the codebase root, so the path names the unit directory the file is in.
    line = sanity_checks.run_checks(tmp_path).findings('placeholders')
    assert line and Path(line[0].file).name == 'vpn.tf', [f.render() for f in line]
    assert Path(line[0].file).parent.name, 'the path names the unit directory the finding is in'
    assert 'replace before terraform apply' in line[0].detail


# --- Exit code ---------------------------------------------------------------

def test_a_fail_finding_exits_non_zero(tmp_path):
    """A broken output is reported and the conversion does not exit 0."""
    # The gate reads the written files, so a planted file is checked like any other.
    (tmp_path / 'planted.tf').write_text(
        'resource "panos_address" "planted_00000000" {\n  name = "Planted"\n'
        '  value = panos_zone.ghost.name\n}\n', encoding='utf-8')
    result = _generate(SAMPLE_CONFIG, tmp_path)
    assert result.returncode == 1, result.stdout
    text = (tmp_path / 'SANITY_REPORT.txt').read_text(encoding='utf-8')
    assert 'Result: FAIL' in text
    assert 'location_present' in text.split('CHECK RESULTS')[1].split('FINDINGS')[0]
    assert 'planted.tf:1' in text
    assert 'planted.tf:3' in text


def test_a_warn_only_conversion_still_exits_zero(tmp_path):
    result = _generate(FIXTURES_DIR / 'kitchen_sink.xml', tmp_path)
    assert result.returncode == 0, result.stdout


# --- --validate --------------------------------------------------------------

def test_validate_flag_runs_the_terraform_check(tmp_path):
    if TERRAFORM is None:
        pytest.skip("terraform binary not found (the CI terraform-gate job provides it)")
    result = _generate(SAMPLE_CONFIG, tmp_path, ('--validate',))
    assert result.returncode == 0, result.stdout + result.stderr
    text = (tmp_path / 'SANITY_REPORT.txt').read_text(encoding='utf-8')
    assert re.search(r'^terraform\s+PASS$', text, re.M)
    assert 'Success!' in text


def test_validate_without_the_binary_is_skipped_not_failed(tmp_path):
    """An offline run reports the check it could not run and keeps the exit code."""
    env = dict(os.environ, PATH='')
    proc = subprocess.run(
        [sys.executable, str(CONVERTER), str(SAMPLE_CONFIG),
         '--output-dir', str(tmp_path), '--validate'],
        capture_output=True, text=True, env=env, cwd=REPO_ROOT, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = (tmp_path / 'SANITY_REPORT.txt').read_text(encoding='utf-8')
    assert re.search(r'^terraform\s+SKIPPED', text, re.M)
    assert 'terraform binary not found' in text


def test_terraform_check_failure_is_a_fail_finding(tmp_path):
    """A validate failure is reported as FAIL, so the gate does not hide it.

    F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): the plan check runs once per unit directory the record names,
    so the failure is the result of that directory, and every plan result names the directory it ran on: the
    finding names it, or the note names it when the plan passed. A run that names no unit runs the check on
    the codebase root, and that result names the root.
    """
    if TERRAFORM is None:
        pytest.skip("terraform binary not found")

    def named(result) -> str:
        """The directory one plan result names, as the path from the codebase root."""
        return result.findings[0].file if result.findings else result.note.split(':', 1)[0]

    # An HCL syntax error is the smallest failure terraform reports.
    assert _generate(SAMPLE_CONFIG, tmp_path).returncode == 0
    units = sanity_checks.unit_directories(tmp_path)
    assert units, 'the run wrote one directory per unit the record names'
    planted = units[0]
    write_path.write_file(write_path.unit_path(tmp_path, planted, 'broken.tf'),
                          'resource "panos_address" "x_00000000" {\n  name = "x"\n')

    report = sanity_checks.run_checks(tmp_path, run_terraform=True, terraform=TERRAFORM)
    results = report.results('terraform')
    assert len(results) == len(units), 'one plan check result per unit directory'
    assert sorted(named(result) for result in results) == sorted(units), \
        [named(result) for result in results]
    assert [result for result in results if named(result) == planted][0].result == 'FAIL', results
    assert report.failed, 'the planted unit is not hidden behind the units that read clean'

    # A directory with no record names no unit, so the check runs on the codebase root and names it.
    root = tmp_path / 'no_record'
    root.mkdir()
    write_path.write_file(write_path.root_path(root, 'broken.tf'),
                          'resource "panos_address" "y_00000000" {\n  name = "y"\n')
    lone = sanity_checks.run_checks(root, run_terraform=True, terraform=TERRAFORM)
    assert sanity_checks.unit_directories(root) == [], 'no record, so no unit directory'
    assert len(lone.results('terraform')) == 1, 'the root has one plan result'
    assert named(lone.results('terraform')[0]) == '.', 'the root result names the codebase root'
    assert lone.result_of('terraform') == 'FAIL'


def test_kitchen_sink_gate_passes_with_validate(tmp_path):
    """The kitchen run's plan results are the gate's report for the directories it wrote.

    The rule (`docs/ARCHITECTURE.md` §4.6): a value the provider constrains in its code, not in the schema,
    is not data the static gate can read, so it cannot become a gate rule; the `terraform` check is the rule
    that reports it as FAIL, and the report is the operator's notice. The fixture a validate pin reads is test
    data, so it states the value provider 2.0.14 accepts for `panos_administrative_tag`, and this pin reads
    the report the run wrote: the static counts are unchanged, and every plan result is PASS. The
    round-trip cross-check reads the same run, so the report names its own WARN result and its own findings
    block; `tests/test_round_trip.py` pins the four findings it states for this fixture.
    """
    if TERRAFORM is None:
        pytest.skip("terraform binary not found (the CI terraform-gate job provides it)")
    result = _generate(FIXTURES_DIR / 'kitchen_sink.xml', tmp_path, ('--validate',))
    assert result.returncode == 0, result.stdout + result.stderr
    text = (tmp_path / 'SANITY_REPORT.txt').read_text(encoding='utf-8')
    assert 'Result: PASS (0 FAIL, 5 WARN)' in text, text
    assert re.search(r'^placeholders\s+WARN \(1\)$', text, re.M), text
    assert re.search(r'^round_trip\s+WARN \(4\)$', text, re.M), text
    # One findings block per rule that reported, so the cross-check cannot be read as a placeholder.
    blocks, check = {}, None
    for line in text.split('FINDINGS')[1].splitlines():
        if line.startswith('['):
            check = line.strip('[]')
            blocks[check] = []
        elif line.startswith('  '):
            blocks[check].append(line)
    assert sorted(blocks) == ['placeholders', 'round_trip'], sorted(blocks)
    assert len(blocks['placeholders']) == 1 and len(blocks['round_trip']) == 4, blocks
    path = Path(blocks['placeholders'][0].split()[0].split(':')[0])
    assert path.name == 'vpn.tf' and path.parent.name, blocks

    units = sanity_checks.unit_directories(tmp_path)
    assert units, 'the run wrote one directory per unit the record names'
    section = text.split('CHECK RESULTS')[1].split('FINDINGS')[0]
    plan_lines = [line for line in section.splitlines() if line.startswith('terraform')]
    assert len(plan_lines) == len(units), 'one plan result per unit directory'
    assert all(re.match(r'terraform\s+PASS$', line) for line in plan_lines), plan_lines
    # A result that passed names the directory it ran on, so the pin can say which unit the plan read.
    assert all(f'{unit}: Success!' in section for unit in units), section


# --- The second entry point --------------------------------------------------

def test_splitter_output_has_no_tf_for_the_gate(tmp_path):
    """The splitter writes XML splits, so the gate has nothing to check there.

    This is stated so a reader does not assume the gate covers the splitter.
    """
    proc = run_script("split_device_groups.py", str(SAMPLE_CONFIG),
                      "--output-dir", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    assert list(tmp_path.glob('*.xml'))
    report = sanity_checks.run_checks(tmp_path)
    assert report.file_count == 0
    assert report.data_file_count == 0, 'the splitter writes no data file'
    assert report.resource_count == 0
