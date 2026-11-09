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
- the splitter writes XML, so the gate has nothing to check there;
- the join rule (`check_request_set`, F8.8) reads the request set through the join's owners, so it pins the
  join through `api_requests` and the report section through the gate;
- a fact that the join and the ledger do not agree on prints as one finding, and the run-wide direction prints
  through the join;
- join findings sort by the data rule's key, so the gate order and the join order differ;
- the join prints no console line, and a join finding stays WARN, so a run that only needs an operator action
  still exits 0;
- the join reports NOT RUN when the gate has no index, so a path 1 pin is unchanged;
- the join reads the same files and reports the same findings on two runs;
- a path 2 run and a path 1 run on the same corpus report the same findings except the join rule.

Every join pin runs the pipeline in process with an injected producer, because a fact from a run must be read
from the run's ledger. `run_checks` builds no scope index, so a call with no index reports the rule as NOT RUN,
and a path 1 pin is unchanged. The join pins are in this file, and one is in `tests/test_round_trip.py`, where
the cross-check reads the same ledger the join reads.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import api_requests
import naming
import panorama_to_terraform
import sanity_checks
import source_fetch
import unit_manifest
import write_path
from conftest import (
    FIXTURES_DIR,
    REPO_ROOT,
    RESPONSES_DIR,
    SAMPLE_CONFIG,
    SRC_DIR,
    path2_run,
    run_main,
    run_pipeline,
    run_script,
    tf_files,
)

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
        # Path 1 read no request, so the entry point passes no index and the join rule reports NOT RUN.
        expected = 'NOT RUN' if name in ('request_set', 'terraform') else 'PASS'
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


# --- The join rule reads the request set through the join's owners (F8.8) ------

# The path 2 run these pins read: one committed response, the whole-config export, handed by the producer
# `tests/conftest.py` builds, so no test calls a network. Each pin runs the pipeline in process, because a fact
# from a run must be read from the run's ledger (`acceptance.md` criterion 10). The response holds the four
# membership lists and no scope entry of its own, so every pair the join answers is a fact that does not agree.
HOST = 'panorama.test'
JOIN_ROWS = 7
UNIT_SIDE_ROWS = 3
ENTRY_SIDE_ROWS = 4


def _join_rule_source() -> str:
    """The join rule's own source, so a scan pins what that rule reads. The boundaries are the ones
    `tests/test_data_file_gate.py` and `tests/test_round_trip.py` pin: `check_data_files` …
    `check_round_trip` … `check_request_set` … `check_control_chars`.
    """
    source = Path(sanity_checks.__file__).read_text(encoding='utf-8')
    return source[source.index('def check_request_set'):source.index('def check_control_chars')]


def _export_name() -> str:
    """The committed export response, named through the one name rule (`source_fetch.cache_name`)."""
    return (RESPONSES_DIR / source_fetch.ApiRequest(host=HOST).cache_name()).name


def _path2_run(output_dir: Path, cache_dir: Path, monkeypatch) -> tuple:
    """The run, and the index the gate reads for it, both read through the join's owners.

    `run_checks` builds no index, so the pin builds it the way the run order does. `tests/conftest.py` holds
    the run and the producer, because `tests/test_round_trip.py` reads the same run for the cross-check.
    """
    return path2_run(output_dir, cache_dir, monkeypatch, HOST)


def test_the_gate_checks_the_join_through_the_owners(tmp_path, monkeypatch):
    """F8.8 criteria 1 and 2: the gate calls the join and states no join rule, no membership rule, no unit
    rule, no naming rule, no cache rule and no reader of its own, and it is the only module that decides what
    the gate does with the join's rows.
    """
    parser, index = _path2_run(tmp_path, tmp_path / 'cache', monkeypatch)
    rule = _join_rule_source()
    assert 'api_requests.unit_findings' in rule, 'the gate reads the pairs through the join'
    assert 'unit_manifest.directory_name' in rule and 'naming.sanitize' in rule, \
        'the unit file is read through the one unit rule and the one naming rule'
    for name in ('LIST_JOIN', 'membership_lists', 'response_names', 'join_units', 'cache_name',
                 'SOURCE_FIELD', 'unit_name', 'facts_of', 'sanitize_name'):
        assert name not in rule, f'the rule states no {name} rule of its own'
    assert not [call for call in ('re.compile', 're.search', 're.match', 're.findall') if call in rule], \
        'the rule writes no reader of its own'
    # Criterion 1: the join answers rows, so it has no check, no report section and no render, and the gate is
    # the only module in `src/` that turns a row into a finding.
    assert not [name for name in ('check', 'report', 'report_section', 'render', 'console_line', 'finding')
                if hasattr(api_requests, name)], 'api_requests stays a join'
    readers = [path.name for path in SRC_DIR.glob('*.py') if '.unit_findings(' in path.read_text(encoding='utf-8')]
    assert readers == ['sanity_checks.py'], 'the gate is the only module that reads the join as a rule'
    rows = api_requests.unit_findings(index, parser.ledger)
    assert len(rows) == JOIN_ROWS, rows
    assert len(sanity_checks.check_request_set(index, parser.ledger)) == JOIN_ROWS, 'one finding per row'


def test_a_fact_that_the_join_and_the_ledger_do_not_agree_on_prints_in_the_report(tmp_path, monkeypatch):
    """F8.8 criterion 3, the unit side: the join answers no entry for a unit the ledger has rows for, so the
    fact names the unit directory the owners answer and no position in a file.
    """
    parser, index = _path2_run(tmp_path, tmp_path / 'cache', monkeypatch)
    rows = api_requests.unit_findings(index, parser.ledger)
    unit_rows = [row for row in rows if row[0] is not None]
    assert len(unit_rows) == UNIT_SIDE_ROWS and all(row[1] is None for row in unit_rows), rows

    findings = sanity_checks.check_request_set(index, parser.ledger)
    unit_findings = [f for f in findings if f.file]
    assert len(unit_findings) == UNIT_SIDE_ROWS, [f.render() for f in findings]
    for facts, _ in unit_rows:
        named = [f for f in unit_findings if f.file == unit_manifest.directory_name(facts, naming.sanitize)]
        assert len(named) == 1, (facts, [f.render() for f in unit_findings])
        assert named[0].check == 'request_set' and named[0].severity == sanity_checks.WARN, named[0].render()
        assert named[0].line == 0, 'the fact compares two sets, so it names no position in a file'

    # A row carries the pair and the side the join has no fact for, so the row states no severity, no file and
    # no section: those are the gate's, and the printed form is `Finding.render`'s.
    assert all(isinstance(row, tuple) and len(row) == 2 for row in rows), rows
    report = sanity_checks.run_checks(tmp_path, index=index, ledger=parser.ledger)
    assert report.findings('request_set') == findings, 'the report section holds the join rows'
    assert '[request_set]' in report.render().split('FINDINGS')[1], report.render()
    assert all(f'  {finding.render()}' in report.render() for finding in findings), report.render()


def test_the_run_wide_findings_print_through_the_join(tmp_path, monkeypatch):
    """F8.8 criterion 4, the run-wide side: an index entry the run read no rows for names no unit, so the fact
    names no file and prints in the root shape.
    """
    parser, index = _path2_run(tmp_path, tmp_path / 'cache', monkeypatch)
    rows = api_requests.unit_findings(index, parser.ledger)
    entry_rows = [row for row in rows if row[1] is not None]
    assert len(entry_rows) == ENTRY_SIDE_ROWS and all(row[0] is None for row in entry_rows), rows

    findings = sanity_checks.check_request_set(index, parser.ledger)
    run_wide = [f for f in findings if not f.file]
    assert len(run_wide) == ENTRY_SIDE_ROWS, [f.render() for f in findings]
    assert all(f.file == '' and f.line == 0 for f in run_wide), [f.render() for f in findings]
    assert all(f.render().startswith('(run)  ') for f in run_wide), \
        'the root shape is `Finding.render`\'s, the shape the plan check uses for a root fact'

    report = sanity_checks.run_checks(tmp_path, index=index, ledger=parser.ledger)
    assert report.findings('request_set') == findings, report.render()
    assert all(f'  {finding.render()}' in report.render() for finding in run_wide), report.render()
    # The rule states no row set of its own, so the entry set is the join's own table read through the owner,
    # and the row set for a run that read more than one response stays open with F8.9 in `backlog.md`.
    assert sorted(entry.path for entry in index) == sorted(entry.path for _, entry in entry_rows), index
    assert 'cross-response' in (REPO_ROOT / 'backlog.md').read_text(encoding='utf-8'), \
        'the cross-response row set is still open, so the rule reports one response only'


def test_the_join_findings_sort_by_the_data_rule(tmp_path, monkeypatch):
    """F8.8 criterion 5: the report section orders the findings by (file, line, detail), which is not the order
    the join states its rows in.
    """
    parser, index = _path2_run(tmp_path, tmp_path / 'cache', monkeypatch)
    rows = api_requests.unit_findings(index, parser.ledger)
    findings = sanity_checks.check_request_set(index, parser.ledger)
    # The join states its rows unit side first, in the order `unit_manifest.units` states them, then the
    # entries in the index order. The gate sorts the same rows by the three parts the data rule and the
    # cross-check use, so the run-wide facts print before the unit facts.
    join_order = [unit_manifest.directory_name(facts, naming.sanitize) if facts else '' for facts, _ in rows]
    assert join_order[:UNIT_SIDE_ROWS] == [unit_manifest.directory_name(facts, naming.sanitize)
                                           for facts in unit_manifest.units(parser.ledger)], join_order
    assert join_order[UNIT_SIDE_ROWS:] == [''] * ENTRY_SIDE_ROWS, join_order
    assert [f.file for f in findings] == [''] * ENTRY_SIDE_ROWS + sorted(join_order[:UNIT_SIDE_ROWS]), findings
    assert findings == sorted(findings, key=lambda f: (f.file, f.line, f.detail)), [f.render() for f in findings]


def test_the_join_prints_no_console_line_and_stays_a_warn(tmp_path, monkeypatch):
    """F8.8 criteria 6 and 7: the join states no console line, so the rule prints none of its own, and the fact
    compares two sets, so it is a WARN and the exit code follows the rules that read the files.
    """
    parser, index = _path2_run(tmp_path, tmp_path / 'cache', monkeypatch)
    rule = _join_rule_source()
    assert 'console_line' not in rule and 'CONSOLE_PREFIX' not in rule, 'the rule prints no console line'
    findings = sanity_checks.check_request_set(index, parser.ledger)
    assert findings and all(f.severity == sanity_checks.WARN for f in findings), [f.render() for f in findings]
    report = sanity_checks.run_checks(tmp_path, index=index, ledger=parser.ledger)
    assert (report.fail_count, report.warn_count) == (0, JOIN_ROWS), report.render()
    assert report.failed is False, 'a WARN does not fail the gate'
    assert run_main(panorama_to_terraform, ['--source', 'api', '--host', HOST, '--output-dir',
                                            str(tmp_path / 'exit'), '--cache-dir', str(tmp_path / 'exit-cache')]) \
        == 0, 'the path 2 run exits the way a path 1 run exits'
    # As measured, criterion 7 cannot hold as written: the gate's own summary prints every finding, so the
    # join's findings print there too, in the shape every finding uses. `acceptance.md` records the measurement.
    summary = report.console_summary()
    assert len([line for line in summary.splitlines() if line.startswith('    ')]) == JOIN_ROWS, summary
    assert all(f'    {f.render()}' in summary for f in findings), summary
    assert f'  request_set: {sanity_checks.WARN}' in summary, summary


def test_the_rule_reports_not_run_when_the_gate_has_no_index(tmp_path, monkeypatch):
    """F8.8 criterion 8, and the path 1 half of criterion 10: the join needs the index and the ledger together,
    so a call that is missing either one reports NOT RUN, and a path 1 pin is unchanged.
    """
    parser, index = _path2_run(tmp_path, tmp_path / 'cache', monkeypatch)
    ran = sanity_checks.run_checks(tmp_path, index=index, ledger=parser.ledger)
    assert ran.result_of('request_set') == sanity_checks.WARN, ran.render()

    half = sanity_checks.run_checks(tmp_path, ledger=parser.ledger)
    results = half.results('request_set')
    assert len(results) == 1 and not results[0].ran, results
    assert results[0].result == sanity_checks.NOT_RUN, results
    assert 'index' in results[0].note and 'ledger' in results[0].note, results[0].note
    assert half.findings('request_set') == [], 'NOT RUN states no finding'

    # Path 1 read no request, so the entry point passes no index, and the result names its shape so a reader
    # can tell a rule that ran and passed from a rule that could not run.
    assert _generate(SAMPLE_CONFIG, tmp_path / 'path1').returncode == 0
    plain = sanity_checks.run_checks(tmp_path / 'path1')
    assert plain.result_of('request_set') == sanity_checks.NOT_RUN, plain.render()
    assert plain.findings('request_set') == [], 'a path 1 run has no join fact to report'
    assert 'request_set: NOT RUN' in plain.console_summary(), plain.console_summary()


def test_two_runs_read_the_same_files_and_report_the_same_findings(tmp_path, monkeypatch):
    """F8.8 criteria 10 and 11: two path 2 runs on the same content write the same files and report the same
    findings, and the report the gate writes through `write_path` is LF bytes.
    """
    reports = []
    for case in ('first', 'second'):
        out = tmp_path / case
        parser, index = _path2_run(out, tmp_path / f'cache-{case}', monkeypatch)
        findings = sanity_checks.check_request_set(index, parser.ledger)
        report = sanity_checks.run_checks(out, index=index, ledger=parser.ledger)
        assert report.findings('request_set') == findings, report.render()
        write_path.write_file(write_path.root_path(out, 'SANITY_REPORT.txt'), report.render())
        reports.append(out / 'SANITY_REPORT.txt')
    assert tf_files(tmp_path / 'first') == tf_files(tmp_path / 'second'), 'the same content writes the same files'
    assert reports[0].read_bytes() == reports[1].read_bytes(), 'the byte rule: two runs state the same bytes'
    for report in reports:
        assert b'\r' not in report.read_bytes(), 'the LF rule: text takes LF through the writer'
        text = report.read_text(encoding='utf-8')
        assert not re.search(r'\d{2}:\d{2}:\d{2}', text), text
        assert str(tmp_path) not in text, 'no machine-dependent path'
        assert all(not line.lstrip().startswith('/') for line in text.split('\n') if line.startswith('  ')), text


def test_a_path_2_run_and_a_path_1_run_report_the_same_findings(tmp_path, monkeypatch):
    """F8.8 criteria 10 and 11, as measured: the same bytes read through both paths write the same files and
    report the same findings for every rule that reads the files. The join facts are run facts, so path 1
    reports NOT RUN, and both paths exit the same way.
    """
    response = RESPONSES_DIR / _export_name()
    path1 = run_pipeline(panorama_to_terraform, None, tmp_path / 'path1', (str(response),))
    parser, index = _path2_run(tmp_path / 'path2', tmp_path / 'cache', monkeypatch)
    assert path1 is not None, 'the path 1 run refused the input'
    assert tf_files(tmp_path / 'path1') == tf_files(tmp_path / 'path2'), 'the same bytes write the same files'

    first = sanity_checks.run_checks(tmp_path / 'path1', ledger=path1.ledger)
    second = sanity_checks.run_checks(tmp_path / 'path2', index=index, ledger=parser.ledger)
    for a, b in zip(first.checks, second.checks):
        if a.check == 'request_set':
            assert (a.result, b.result) == (sanity_checks.NOT_RUN, sanity_checks.WARN), (a.result, b.result)
        else:
            assert a.result == b.result, (a.check, a.result, b.result)
    assert (first.warn_count, second.warn_count) == (0, JOIN_ROWS), (first.render(), second.render())
    assert run_main(panorama_to_terraform, [str(response), '--output-dir', str(tmp_path / 'path1')]) == 0
    assert run_main(panorama_to_terraform, ['--source', 'api', '--host', HOST, '--output-dir',
                                            str(tmp_path / 'path2'), '--cache-dir', str(tmp_path / 'cache')]) == 0
    # The report a path 1 run writes names the join as a rule that did not run, so the two runs differ on one
    # line and on the source the record names.
    text = (tmp_path / 'path1' / 'SANITY_REPORT.txt').read_text(encoding='utf-8')
    assert re.search(r'^request_set\s+NOT RUN$', text, re.M), text
