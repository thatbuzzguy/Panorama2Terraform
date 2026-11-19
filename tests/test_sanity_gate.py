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
  still exits 0; the marker it reports is the table's one statement, `resource_mapping.PLACEHOLDER_TEXT`, read
  by the print site, the report, and this rule; a `reference_only` field the export cannot carry has no value, so
  the block prints the marker and the run records no pair for it;
- the control-character rule is the read layer's (`xml_input.CONTROL_CHARS`), so the gate reads the definition
  and states no second one;
- a FAIL finding exits non-zero;
- `--validate` runs `terraform init` + `terraform validate`, and a missing
  terraform binary is SKIPPED, never a failure, so the suite stays offline;
- the plan check reports one result per unit directory the record names, so a
  `--validate` pin reads the files the run wrote;
- the tflint check (`--tflint`) runs the rule set the tool states as data, so no config file restates it; the
  rule set is the eight rules the gate states no rule for, and the rules the gate or the emitter already state
  are recorded as the set the check runs nothing for;
- the severity rule and the exit-code rule are data in the gate, and a run that answered non-zero with nothing
  to report is a FAIL finding, never a silent pass;
- a tflint finding prints through the gate's one finding shape, so no module states a second console shape;
- the committed tflint material reads as findings through the harness, one finding per rule, and one pin compares
  the committed answer with the live answer so a committed fact cannot drift; the pins that run the binary skip
  only for a missing binary and assert on a non-zero run;
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

import ast
import inspect
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import api_requests
import naming
import panorama_to_terraform
import resource_mapping
import sanity_checks
import site_data
import source_fetch
import unit_manifest
import write_path
import xml_input
from conftest import (
    FIXTURES_DIR,
    GOLDEN_DIR,
    REPO_ROOT,
    RESPONSES_DIR,
    SAMPLE_CONFIG,
    SRC_DIR,
    TERRAFORM,
    TFLINT,
    TFLINT_DIR,
    corpus_fixtures,
    file_text,
    path2_run,
    run_main,
    run_pipeline,
    run_script,
    tf_files,
    written_bytes,
)

# The terraform binary and the golden, fixture and source paths are read through `tests/conftest.py` (§1.1),
# so no module resolves the binary a second time and the skip rule for a missing binary stays one rule.
# The layout rule (`docs/ARCHITECTURE.md` §1.1): the entry points are tool modules, so they sit in `src/`.
CONVERTER = SRC_DIR / "panorama_to_terraform.py"
SPLITTER = SRC_DIR / "split_device_groups.py"

# The fixtures the corpus pins read: the read rule's accepted set, not a name rule. A fixture the rule refuses
# writes no file, so the gate never sees it (tests/test_robustness.py pins that path).
FIXTURES = corpus_fixtures()


def _generate(source: Path, out_dir: Path, extra_args: tuple[str, ...] = ()) -> subprocess.CompletedProcess:
    """Run the converter and return the CompletedProcess."""
    return run_script("panorama_to_terraform.py", str(source), "--output-dir", str(out_dir), *extra_args)


# --- The gate runs on every conversion ---------------------------------------


def test_gate_runs_and_writes_the_report(tmp_path):
    """A conversion writes SANITY_REPORT.txt next to the .tf files."""
    result = _generate(SAMPLE_CONFIG, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    report_path = tmp_path / "SANITY_REPORT.txt"
    assert report_path.is_file(), "the conversion wrote no sanity report"
    text = report_path.read_text(encoding="utf-8")
    assert "Result: PASS (0 FAIL, 0 WARN)" in text
    # Every static check names its result, so a check cannot be silently absent.
    for name in sanity_checks.CHECK_ORDER:
        # Path 1 read no request, so the entry point passes no index and the join rule reports NOT RUN. The two
        # checks that run an external command report NOT RUN for a call that did not ask for them.
        expected = "NOT RUN" if name in ("request_set", "tflint", "terraform") else "PASS"
        assert re.search(rf"^{name}\s+{expected}$", text, re.M)


def test_console_summary_reports_the_result(tmp_path):
    """The console summary states the result, not only the file list."""
    result = _generate(SAMPLE_CONFIG, tmp_path)
    # F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): the count names the unit set the gate read, so the
    # sample run - two units, so two sets - measures 14 .tf files.
    summary = [line for line in result.stdout.split("\n") if line.startswith("Sanity gate:")]
    # Measured 2026-11-19: the resource count is 17, because the four `*_policy_rules` types print one iterated
    # block per rule type per unit instead of one block per rule (Epic 9 Piece 19).
    assert summary == ["Sanity gate: PASS (0 FAIL, 0 WARN) - 14 .tf files, 2 data files, 17 resources"]
    assert "Sanity report: " in result.stdout


# --- Determinism ---------------------------------------------------------------


def test_report_is_byte_identical_between_runs(tmp_path):
    """Two runs on the same input produce the same report bytes."""
    first = _generate(SAMPLE_CONFIG, tmp_path / "run1")
    second = _generate(SAMPLE_CONFIG, tmp_path / "run2")
    assert first.returncode == 0 and second.returncode == 0
    assert (tmp_path / "run1" / "SANITY_REPORT.txt").read_bytes() == (
        tmp_path / "run2" / "SANITY_REPORT.txt"
    ).read_bytes()


def test_report_names_no_timestamp_and_no_absolute_path(tmp_path):
    """Determinism needs both: no clock value and no machine-dependent path."""
    _generate(SAMPLE_CONFIG, tmp_path)
    text = (tmp_path / "SANITY_REPORT.txt").read_text(encoding="utf-8")
    assert not re.search(r"\d{2}:\d{2}:\d{2}", text)
    assert str(tmp_path) not in text
    # The report names file names, never a path to a file.
    for line in text.split("\n"):
        if line.startswith("  "):
            assert not line.lstrip().startswith("/")


# --- Every check detects its violation ---------------------------------------


def test_emitted_types_check_detects_a_type_outside_the_mapping():
    files = {"a.tf": 'resource "panos_zone" "z_00000000" {\n  location = {\n    shared = {}\n  }\n  name = "z"\n}\n'}
    assert sanity_checks.check_emitted_types(files) == []
    bad = {"bad.tf": 'resource "panos_made_up_type" "x_00000000" {\n  name = "x"\n}\n'}
    findings = sanity_checks.check_emitted_types(bad)
    assert len(findings) == 1
    assert findings[0].check == "emitted_types"
    assert findings[0].severity == sanity_checks.FAIL
    assert findings[0].file == "bad.tf"
    assert findings[0].line == 1


def test_location_check_detects_a_block_without_location():
    files = {"bad.tf": 'resource "panos_address" "host_00000000" {\n  name = "host"\n}\n'}
    findings = sanity_checks.check_location_present(files)
    assert len(findings) == 1
    assert "no location block" in findings[0].detail
    # A resource block is read up to the first column-0 brace.
    ok = {"ok.tf": 'resource "panos_address" "host_00000000" {\n  location = {\n    shared = {}\n  }\n'}
    assert sanity_checks.check_location_present(ok) == []


def test_reference_check_detects_a_dangling_reference():
    files = {
        "ok.tf": 'resource "panos_zone" "zone_00000000" {\n  location = { shared = {} }\n  name = "z"\n}\n'
        'resource "panos_address" "host_00000000" {\n  location = { shared = {} }\n'
        "  tags = [panos_zone.zone_00000000.name]\n}\n",
    }
    assert sanity_checks.check_references(files) == []
    bad = {
        "bad.tf": 'resource "panos_address" "host_00000000" {\n  location = { shared = {} }\n'
        "  tags = [panos_zone.ghost.name]\n}\n",
    }
    findings = sanity_checks.check_references(bad)
    assert len(findings) == 1
    assert findings[0].detail == "dangling reference panos_zone.ghost.name"
    assert findings[0].line == 3


def test_reference_check_reads_only_the_written_files():
    """A resource that the generator declared in memory but never wrote does not
    make a reference resolve."""
    files = {
        "a.tf": 'resource "panos_address" "host_00000000" {\n  location = { shared = {} }\n'
        "  tags = [panos_service.svc_00000000.name]\n}\n"
    }
    findings = sanity_checks.check_references(files)
    assert len(findings) == 1
    assert findings[0].detail == "dangling reference panos_service.svc_00000000.name"


def test_variable_check_detects_an_unconsumed_variable():
    """F2.10, the first direction: a declaration with no consumer."""
    files = {
        "variables.tf": 'variable "dead" {\n  description = "no consumer"\n}\n\n'
        'variable "used" {\n  description = "consumed"\n}\n',
        "provider.tf": 'provider "panos" {\n  hostname = var.used\n}\n',
    }
    findings = sanity_checks.check_variables(files)
    assert len(findings) == 1
    assert findings[0].file == "variables.tf"
    assert findings[0].line == 1
    assert "never consumed as var.dead" in findings[0].detail


def test_variable_check_detects_a_consumer_with_no_declaration():
    """F6.6, the second direction: a `var.` reference that names no declaration this run writes.

    The declaration set comes from the value-to-variable table, so the two directions are what make a
    generated declaration set checkable.
    """
    files = {"provider.tf": 'provider "panos" {\n  hostname = var.other\n}\n'}
    findings = sanity_checks.check_variables(files)
    assert len(findings) == 1
    assert findings[0].file == "provider.tf"
    assert findings[0].line == 2
    assert "var.other names no variable this run declares" in findings[0].detail
    both = {
        "variables.tf": 'variable "used" {\n  description = "consumed"\n}\n',
        "provider.tf": 'provider "panos" {\n  hostname = var.used\n}\n',
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
    assert all(Path(name).parent.name for name in files), "the count names the unit set"
    assert report.data_file_count == 2
    assert "Files checked: 14 .tf files, 2 data files." in report.render(), report.render()
    assert re.search(r"^data_files\s+PASS$", report.render(), re.M)


def test_data_file_check_detects_a_row_that_is_not_the_data_it_declares(tmp_path):
    """One negative test per rule: the data rule reports a row that does not read as its declared shape,
    a field that disagrees with `naming.py`, a row that joins to nothing, and a printed form that is not
    the record rendered. Each finding names the file and the row ordinal (F6.8).
    """
    _generate(SAMPLE_CONFIG, tmp_path)
    assert sanity_checks.check_data_files(tmp_path) == []
    rows = unit_manifest.parse_rows((tmp_path / unit_manifest.MANIFEST_FILE).read_text(encoding="utf-8"))
    planted = dict(rows[1])
    planted["unit"] = "NotTheLevelName"
    rows[1] = planted
    # Write the row back through the module, so the test states no second shape rule.
    (tmp_path / unit_manifest.MANIFEST_FILE).write_text(unit_manifest.render(rows), encoding="utf-8")
    findings = sanity_checks.check_data_files(tmp_path)
    assert len(findings) == 1, [f.render() for f in findings]
    assert findings[0].severity == sanity_checks.FAIL
    assert findings[0].file == unit_manifest.MANIFEST_FILE and findings[0].line == 2
    assert "level rule" in findings[0].detail, findings[0].render()


def test_the_control_character_rule_is_stated_once_in_src():
    """The read layer owns the control-character rule, so the gate reads the definition and states no second one.

    A source scan, for the reason `acceptance.md` records: a state value never reaches a `.tf` file, so no run
    pin can show the gate firing on tool output. The content halves are
    `tests/test_state_input.py::test_the_state_door_refuses_a_control_character_in_a_value`, which measures the
    door's refusal, and `tests/test_robustness.py::test_escape_string_prints_the_shapes_it_escapes`, which
    measures that the escape holds no strip.
    """
    # One definition of the set, in the read layer.
    text = {path.name: path.read_text(encoding="utf-8") for path in sorted(SRC_DIR.glob("*.py"))}
    assert "CONTROL_CHARS = {chr(code) for code in range(0x20)} | {chr(0x7F)}" in text["xml_input.py"]
    holders = [name for name, source in text.items() if "CONTROL_CHARS =" in source]
    assert holders == ["xml_input.py"], holders
    # The state door and the gate rule read the set through the owner, so neither states a second definition.
    for name in ("state_input.py", "sanity_checks.py"):
        assert "CONTROL_CHARS" in text[name], name
        assert "from xml_input import" in text[name] or "import xml_input" in text[name], name
        assert "CONTROL_CHARS =" not in text[name], (name, "a reader states no second set")
    assert not hasattr(sanity_checks, "CONTROL_CHARS"), "the gate holds no copy of the set"

    # No module holds a strip, which is the rule the escape path used to state before the change.
    for name, source in text.items():
        assert "ord(ch) < 32" not in source, name
        assert "ch >= ' '" not in source, name

    # The escape states only the shapes a printed string needs, and the shapes are the read layer's set.
    escape = inspect.getsource(panorama_to_terraform.TerraformGenerator.escape_string)
    shapes = {
        node.value
        for node in ast.walk(ast.parse(textwrap.dedent(escape)))
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) == 1
    }
    assert shapes == {"\\", '"'} | set(xml_input.ESCAPE_SHAPES), shapes


def test_control_char_check_detects_a_raw_control_character():
    files = {
        "bad.tf": 'resource "panos_address" "host_00000000" {\n  location = { shared = {} }\n  name = "a\x01b"\n}\n'
    }
    findings = sanity_checks.check_control_chars(files)
    assert len(findings) == 1
    assert findings[0].line == 3
    assert "0x01" in findings[0].detail
    # LF is the only legal raw control byte; an escaped tab in the text is fine.
    clean = {"ok.tf": 'resource "panos_address" "host_00000000" {\n  name = "a\\tb"\n}\n'}
    assert sanity_checks.check_control_chars(clean) == []
    # DEL is reported too.
    assert len(sanity_checks.check_control_chars({"d.tf": 'name = "a\x7fb"\n'})) == 1


def test_the_placeholder_is_stated_once_in_src():
    """The marker is `resource_mapping.PLACEHOLDER_TEXT`, stated once, so no print site or gate states it again.

    A source scan, for the reason `acceptance.md` records: a second statement prints the same string, so no run
    can show which statement answered. The content halves are
    `test_a_reference_only_field_with_no_value_prints_the_marker`, which measures the marker a run printed, and
    `test_placeholder_check_warns_and_does_not_fail`, which measures the gate reading the same fact.
    """
    text = {path.name: path.read_text(encoding="utf-8") for path in sorted(SRC_DIR.glob("*.py"))}
    # One statement of the marker.
    holders = [name for name, source in text.items() if "PLACEHOLDER_TEXT =" in source]
    assert holders == ["resource_mapping.py"], holders
    for name, source in text.items():
        assert resource_mapping.PLACEHOLDER_TEXT not in source or "PLACEHOLDER_TEXT =" in source, (
            name,
            "a reader states no second copy of the marker",
        )
    # The print site, the gate rule, and the report read it through the owner.
    for name in ("panorama_to_terraform.py", "sanity_checks.py"):
        assert "resource_mapping.PLACEHOLDER_TEXT" in text[name] or "PLACEHOLDER_TEXT" in text[name], name
        assert "PLACEHOLDER_TEXT =" not in text[name], (name, "a reader states no second statement")
    assert not hasattr(sanity_checks, "PLACEHOLDER_TEXT"), "the gate holds no copy of the marker"
    assert sanity_checks.EXPECTED_PLACEHOLDERS == (resource_mapping.PLACEHOLDER_TEXT,)


def test_placeholder_check_warns_and_does_not_fail():
    """The marker the gate reports is the table's one statement, so the check reads the same fact the print
    site wrote, and it is a WARN, not a FAIL."""
    marker = resource_mapping.PLACEHOLDER_TEXT
    assert (marker,) == sanity_checks.EXPECTED_PLACEHOLDERS, sanity_checks.EXPECTED_PLACEHOLDERS
    files = {
        "vpn.tf": 'resource "panos_ipsec_tunnel" "t_00000000" {\n'
        f'  location = {{ shared = {{}} }}\n  key = "{marker}"\n}}\n'
    }
    findings = sanity_checks.check_placeholders(files)
    assert len(findings) == 1
    assert findings[0].severity == sanity_checks.WARN
    # A comment that names the marker is documentation, not an emitted value.
    commented = {"vpn.tf": f'# Search for "{marker}" and replace it.\n'}
    assert sanity_checks.check_placeholders(commented) == []
    # A WARN-only run is not a failed gate.
    report = sanity_checks.SanityReport(
        checks=(sanity_checks.CheckResult("placeholders", tuple(findings)),), file_count=1, resource_count=1
    )
    assert report.result_of("placeholders") == "WARN"
    assert not report.failed


def test_a_reference_only_field_with_no_value_prints_the_marker(tmp_path, make_parser, converter_module):
    """F7.7: a `reference_only` field the export cannot carry has no value, so the block prints the marker.

    `VALUE_VARIABLES` is the only place that decides the shape of a field the provider marks `sensitive`, and the
    name rule has nothing to name for a field the run read no value for, because a value cannot name itself and a
    pair needs a source. So no pair is recorded: the run declares no variable for it and the `.tfvars` writer
    writes no line for it. The parse stores no value either, which is what `REFERENCE_ONLY` states for a fact the
    export does not carry.
    """
    out = tmp_path / "out"
    result = run_script("panorama_to_terraform.py", str(FIXTURES_DIR / "ike_gateways.xml"), "--output-dir", str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    marker = resource_mapping.PLACEHOLDER_TEXT

    # The parse holds no value for the field: the export states the authentication method, not the key.
    gateways = make_parser("ike_gateways.xml").parse_ike_gateways()
    assert gateways, "the pin needs an entry to measure"
    for gateway in gateways:
        assert gateway.get("auth_type") == "pre-shared-key", gateway
        assert not [key for key in gateway if "key" in key], gateway

    # The block prints the marker, through the print site, on the field the table states as `reference_only`.
    text = file_text(tf_files(out), "vpn.tf")
    assert f'key = "{marker}"' in text, text
    # The same call on the same field answers the marker, which is the path the bytes came from.
    generator = converter_module.TerraformGenerator(str(tmp_path / "gen"))
    facts = unit_manifest.facts_of(gateways[0])
    assert generator.printed_value("key", "", facts) == f'"{marker}"'

    # No pair is recorded for a field with no value, so the record holds no row for the entry and the unit
    # declares no variable for it. `site_data.py` rule 2 states that a name with no value writes no line.
    name = naming.variable_name(gateways[0]["name"])
    written = tf_files(out)
    declared = [key for key in written if Path(key).name == "variables.tf"]
    assert declared, "the pin needs the unit the run wrote"
    for key in declared:
        assert f'variable "{name}"' not in written[key], (key, written[key])
    record = out / site_data.SITE_DATA_FILE
    if record.is_file():
        assert not [
            row for row in site_data.parse_rows(record.read_text(encoding="utf-8")) if name in row["variables"]
        ], record
    else:
        assert not [key for key in written if key.endswith(".tfvars")], "no row, so no printed form"


# --- No false positives --------------------------------------------------------


@pytest.mark.parametrize("fixture", FIXTURES)
def test_gate_reports_no_fail_finding_on_every_fixture(fixture, tmp_path):
    """Every fixture passes the gate, so the gate reports facts, not noise."""
    out_dir = tmp_path / fixture
    result = run_script("panorama_to_terraform.py", str(FIXTURES_DIR / fixture), "--output-dir", str(out_dir))
    assert result.returncode == 0, f"{fixture}: {result.stdout}\n{result.stderr}"
    report = sanity_checks.run_checks(out_dir)
    findings = [f for r in report.checks for f in r.findings if f.severity == sanity_checks.FAIL]
    assert findings == [], f"{fixture}: " + ", ".join(f.render() for f in findings)
    assert report.file_count > 0, f"{fixture}: the gate read no .tf file"


def test_kitchen_sink_warns_about_the_placeholder_and_exits_zero(tmp_path):
    """The VPN key placeholder is an expected output, so it is a WARN, not a FAIL."""
    result = _generate(FIXTURES_DIR / "kitchen_sink.xml", tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    text = (tmp_path / "SANITY_REPORT.txt").read_text(encoding="utf-8")
    assert re.search(r"^placeholders\s+WARN \(\d+\)$", text, re.M)
    assert "Result: PASS" in text
    # The WARN line names the file and the line the operator must edit. F6.10.3 (§14): a finding names
    # the path from the codebase root, so the path names the unit directory the file is in.
    line = sanity_checks.run_checks(tmp_path).findings("placeholders")
    assert line and Path(line[0].file).name == "vpn.tf", [f.render() for f in line]
    assert Path(line[0].file).parent.name, "the path names the unit directory the finding is in"
    assert "replace before terraform apply" in line[0].detail


# --- Exit code ---------------------------------------------------------------


def test_a_fail_finding_exits_non_zero(tmp_path):
    """A broken output is reported and the conversion does not exit 0."""
    # The gate reads the written files, so a planted file is checked like any other.
    (tmp_path / "planted.tf").write_text(
        'resource "panos_address" "planted_00000000" {\n  name = "Planted"\n  value = panos_zone.ghost.name\n}\n',
        encoding="utf-8",
    )
    result = _generate(SAMPLE_CONFIG, tmp_path)
    assert result.returncode == 1, result.stdout
    text = (tmp_path / "SANITY_REPORT.txt").read_text(encoding="utf-8")
    assert "Result: FAIL" in text
    assert "location_present" in text.split("CHECK RESULTS")[1].split("FINDINGS")[0]
    assert "planted.tf:1" in text
    assert "planted.tf:3" in text


def test_a_warn_only_conversion_still_exits_zero(tmp_path):
    result = _generate(FIXTURES_DIR / "kitchen_sink.xml", tmp_path)
    assert result.returncode == 0, result.stdout


# --- --validate --------------------------------------------------------------


def test_validate_flag_runs_the_terraform_check(tmp_path):
    if TERRAFORM is None:
        pytest.skip("terraform binary not found (the CI terraform-gate job provides it)")
    result = _generate(SAMPLE_CONFIG, tmp_path, ("--validate",))
    assert result.returncode == 0, result.stdout + result.stderr
    text = (tmp_path / "SANITY_REPORT.txt").read_text(encoding="utf-8")
    assert re.search(r"^terraform\s+PASS$", text, re.M)
    assert "Success!" in text


def test_validate_without_the_binary_is_skipped_not_failed(tmp_path):
    """An offline run reports the check it could not run and keeps the exit code."""
    env = dict(os.environ, PATH="")
    proc = subprocess.run(
        [sys.executable, str(CONVERTER), str(SAMPLE_CONFIG), "--output-dir", str(tmp_path), "--validate"],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = (tmp_path / "SANITY_REPORT.txt").read_text(encoding="utf-8")
    assert re.search(r"^terraform\s+SKIPPED", text, re.M)
    assert "terraform binary not found" in text


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
        return result.findings[0].file if result.findings else result.note.split(":", 1)[0]

    # An HCL syntax error is the smallest failure terraform reports.
    assert _generate(SAMPLE_CONFIG, tmp_path).returncode == 0
    units = sanity_checks.unit_directories(tmp_path)
    assert units, "the run wrote one directory per unit the record names"
    planted = units[0]
    write_path.write_file(
        write_path.unit_path(tmp_path, planted, "broken.tf"), 'resource "panos_address" "x_00000000" {\n  name = "x"\n'
    )

    report = sanity_checks.run_checks(tmp_path, run_terraform=True, terraform=TERRAFORM)
    results = report.results("terraform")
    assert len(results) == len(units), "one plan check result per unit directory"
    assert sorted(named(result) for result in results) == sorted(units), [named(result) for result in results]
    assert [result for result in results if named(result) == planted][0].result == "FAIL", results
    assert report.failed, "the planted unit is not hidden behind the units that read clean"

    # A directory with no record names no unit, so the check runs on the codebase root and names it.
    root = tmp_path / "no_record"
    root.mkdir()
    write_path.write_file(
        write_path.root_path(root, "broken.tf"), 'resource "panos_address" "y_00000000" {\n  name = "y"\n'
    )
    lone = sanity_checks.run_checks(root, run_terraform=True, terraform=TERRAFORM)
    assert sanity_checks.unit_directories(root) == [], "no record, so no unit directory"
    assert len(lone.results("terraform")) == 1, "the root has one plan result"
    assert named(lone.results("terraform")[0]) == ".", "the root result names the codebase root"
    assert lone.result_of("terraform") == "FAIL"


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
    result = _generate(FIXTURES_DIR / "kitchen_sink.xml", tmp_path, ("--validate",))
    assert result.returncode == 0, result.stdout + result.stderr
    text = (tmp_path / "SANITY_REPORT.txt").read_text(encoding="utf-8")
    assert "Result: PASS (0 FAIL, 5 WARN)" in text, text
    assert re.search(r"^placeholders\s+WARN \(1\)$", text, re.M), text
    assert re.search(r"^round_trip\s+WARN \(4\)$", text, re.M), text
    # One findings block per rule that reported, so the cross-check cannot be read as a placeholder.
    blocks, check = {}, None
    for line in text.split("FINDINGS")[1].splitlines():
        if line.startswith("["):
            check = line.strip("[]")
            blocks[check] = []
        elif line.startswith("  "):
            blocks[check].append(line)
    assert sorted(blocks) == ["placeholders", "round_trip"], sorted(blocks)
    assert len(blocks["placeholders"]) == 1 and len(blocks["round_trip"]) == 4, blocks
    path = Path(blocks["placeholders"][0].split()[0].split(":")[0])
    assert path.name == "vpn.tf" and path.parent.name, blocks

    units = sanity_checks.unit_directories(tmp_path)
    assert units, "the run wrote one directory per unit the record names"
    section = text.split("CHECK RESULTS")[1].split("FINDINGS")[0]
    plan_lines = [line for line in section.splitlines() if line.startswith("terraform")]
    assert len(plan_lines) == len(units), "one plan result per unit directory"
    assert all(re.match(r"terraform\s+PASS$", line) for line in plan_lines), plan_lines
    # A result that passed names the directory it ran on, so the pin can say which unit the plan read.
    assert all(f"{unit}: Success!" in section for unit in units), section


# --- The rule set that runs through the tflint command ------------------------


def test_the_tflint_flag_runs_the_check_on_a_conversion(tmp_path):
    """The flag is the mirror of `--validate`: a run that asks for the check reports its result, and the
    committed goldens read clean through the rule set, so the report names one result per unit directory and
    names the directory each result ran on.
    """
    if TFLINT is None:
        pytest.skip("tflint binary not found (the CI terraform-gate job provides it)")
    result = _generate(SAMPLE_CONFIG, tmp_path, ("--tflint",))
    assert result.returncode == 0, result.stdout + result.stderr
    text = (tmp_path / "SANITY_REPORT.txt").read_text(encoding="utf-8")
    units = sanity_checks.unit_directories(tmp_path)
    assert units, "the run wrote one directory per unit the record names"
    section = text.split("CHECK RESULTS")[1].split("FINDINGS")[0]
    rule_lines = [line for line in section.splitlines() if line.startswith("tflint")]
    assert len(rule_lines) == len(units), "one rule-set result per unit directory"
    assert all(re.match(r"tflint\s+PASS$", line) for line in rule_lines), rule_lines
    # A result that passed has no finding, so the note names the directory the check ran on.
    assert all(f"{unit}: no finding" in section for unit in units), section
    assert "tflint: PASS" in result.stdout, result.stdout


def test_the_tflint_check_reports_not_run_when_the_caller_did_not_ask_for_it(tmp_path):
    """The default gate reads only offline data, so a call that did not ask for the check reports it as NOT RUN,
    the shape `check_terraform` already states for a caller that did not pass `--validate`. A NOT RUN result
    states no finding and does not fail the gate.
    """
    result = _generate(SAMPLE_CONFIG, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    text = (tmp_path / "SANITY_REPORT.txt").read_text(encoding="utf-8")
    assert re.search(r"^tflint\s+NOT RUN$", text, re.M), text
    assert "run the converter with --tflint" in text, "the report names the flag that runs it"

    plain = sanity_checks.run_checks(tmp_path)
    assert plain.result_of("tflint") == sanity_checks.NOT_RUN
    assert plain.findings("tflint") == [], "NOT RUN states no finding"
    assert plain.failed is False, "a rule that did not run does not fail the gate"
    assert "tflint: NOT RUN" in plain.console_summary(), plain.console_summary()
    # The report order is the byte rule's key, so the rule that reads the files it wrote sits before the rule
    # that reads a directory.
    assert [check.check for check in plain.checks] == list(sanity_checks.CHECK_ORDER), plain.render()


def test_the_tflint_rule_set_is_data_in_the_gate():
    """The rule set is stated once, as data in the runtime home for the static rules, and the argument builder
    names exactly that set in sorted order. `--only` names each rule, so no config file is needed, and a config
    file would be a second statement of the set.
    """
    argv = sanity_checks.tflint_arguments("tflint")
    assert argv[:3] == ["tflint", *sanity_checks.TFLINT_FLAGS], argv
    named = [argv[i + 1] for i, part in enumerate(argv) if part == sanity_checks.TFLINT_RULE_FLAG]
    assert named == sorted(sanity_checks.TFLINT_RULES), argv
    assert "--chdir" not in argv, "the check sets the working directory, so the answer names the file name"

    source = (SRC_DIR / "sanity_checks.py").read_text(encoding="utf-8")
    assert source.count("TFLINT_RULES = (") == 1, "the set is stated once"
    assert not list(REPO_ROOT.rglob(".tflint.hcl")), "no config file, so nothing can restate the set"

    # The gate holds one shape rule, and it is the answer of the command it runs. The data files are read through
    # the modules that wrote them, so a data rule states no shape rule of its own (`tests/test_data_file_gate.py`).
    assert source.count("json.loads(") == 1, "one shape rule, the answer read"
    assert "def tflint_findings" in source, "the shape rule reads the answer, not a row shape"

    # The set holds only the rules the gate states no rule for, so the two sets cannot name one rule twice.
    overlap = set(sanity_checks.TFLINT_RULES) & set(sanity_checks.TFLINT_RULES_ALREADY_HELD)
    assert overlap == set(), overlap
    for rule, owner in sanity_checks.TFLINT_RULES_ALREADY_HELD.items():
        module, _, name = owner.partition(".")
        assert f"def {name}(" in (SRC_DIR / f"{module}.py").read_text(encoding="utf-8"), (rule, owner)


def test_the_committed_tflint_output_reads_as_findings_through_the_harness():
    """The committed answer for the committed probe content reads as one finding per rule in the set, through
    the harness the check uses. The finding shape is the gate's one shape, and the sort key is the byte rule's.
    """
    answer = (TFLINT_DIR / "probe.json").read_text(encoding="utf-8")
    findings = sanity_checks.tflint_findings("tests/tflint", answer, 2)
    assert len(findings) == len(sanity_checks.TFLINT_RULES), findings
    assert sorted(finding.detail.split(":", 1)[0] for finding in findings) == sorted(sanity_checks.TFLINT_RULES)
    assert findings == sorted(findings, key=lambda finding: (finding.file, finding.line, finding.detail))

    for finding in findings:
        assert finding.check == "tflint", finding.render()
        assert Path(finding.file).parent.name == "tflint", finding.render()
        assert Path(finding.file).name == "probe.tf", finding.render()
        assert finding.line > 0, finding.render()
        assert finding.render() == f"{finding.file}:{finding.line}  {finding.detail}", finding.render()

    # The severity rule reads the committed answer: a warning is a shape the printed file holds, so it is FAIL,
    # and the one info finding is an operator action, so it is WARN.
    assert sanity_checks.WARN in {finding.severity for finding in findings}, findings
    naming_fact = [finding for finding in findings if "naming_convention" in finding.detail]
    assert [finding.severity for finding in naming_fact] == [sanity_checks.WARN], naming_fact
    assert all(finding.severity == sanity_checks.FAIL for finding in findings if finding not in naming_fact)


def test_the_committed_tflint_output_agrees_with_the_binary():
    """A committed fact cannot drift from the rule it records: the same content run through the tool answers the
    committed bytes. The pin skips only for a missing binary and asserts on a non-zero run.
    """
    if TFLINT is None:
        pytest.skip("tflint binary not found (the CI terraform-gate job provides it)")
    proc = subprocess.run(
        sanity_checks.tflint_arguments(TFLINT), cwd=TFLINT_DIR, capture_output=True, text=True, timeout=180
    )
    assert proc.returncode in sanity_checks.TFLINT_EXIT_CODES, proc.returncode
    assert proc.stdout == (TFLINT_DIR / "probe.json").read_text(encoding="utf-8"), (
        "the committed answer has drifted from the rule it records"
    )


def test_the_tflint_severity_rule_and_the_exit_code_rule_are_data_in_the_gate():
    """The two tables the check reads, and no second mapping in the check itself. A severity outside the table
    is reported, so a gap in the table cannot read as a pass.
    """
    assert sanity_checks.TFLINT_SEVERITY == {
        "error": sanity_checks.FAIL,
        "warning": sanity_checks.FAIL,
        "info": sanity_checks.WARN,
    }
    assert sanity_checks.TFLINT_EXIT_CODES == {0: "no finding", 1: "error entry", 2: "issue reported"}

    source = (SRC_DIR / "sanity_checks.py").read_text(encoding="utf-8")
    read = source[source.index("def tflint_findings") : source.index("def check_tflint")]
    assert read.count("TFLINT_SEVERITY.get") == 1, read
    assert read.count("TFLINT_EXIT_CODES.get") == 1, read

    # A severity the table answers nothing for is a finding, not a pass.
    unmapped = sanity_checks.tflint_findings(
        "tests/tflint",
        json.dumps(
            {
                "issues": [
                    {
                        "rule": {"name": "terraform_comment_syntax", "severity": "note"},
                        "message": "m",
                        "range": {"filename": "probe.tf", "start": {"line": 1}},
                    }
                ]
            }
        ),
        2,
    )
    assert [finding.severity for finding in unmapped] == [sanity_checks.FAIL], unmapped
    assert "unmapped severity note" in unmapped[0].detail, unmapped[0].render()


def test_a_non_zero_tflint_run_with_nothing_to_report_is_a_fail_finding():
    """A run that answered non-zero with nothing to report is reported, never a silent pass. A run that answered
    zero with nothing to report is the pass the exit-code table states.
    """
    quiet = '{"issues":[],"errors":[]}'
    findings = sanity_checks.tflint_findings("tests/tflint", quiet, 2)
    assert len(findings) == 1, findings
    assert findings[0].severity == sanity_checks.FAIL, findings[0].render()
    assert "exited 2 (issue reported) with nothing to report" in findings[0].detail, findings[0].render()
    assert findings[0].file == "tests/tflint", "the finding names the directory the check ran on"
    assert findings[0].line == 0, "the fact is about the run, not about a file"
    assert sanity_checks.tflint_findings("tests/tflint", quiet, 0) == [], "exit 0 is the stated pass"


def test_tflint_without_the_binary_is_skipped_not_failed(tmp_path, monkeypatch):
    """Skip honesty: a check that cannot run because the binary is absent says so, and the exit code stays with
    the rules that read the files. The pin clears PATH, so it measures the same answer on a machine that has the
    binary, and it runs in every CI job.
    """
    env = dict(os.environ, PATH="")
    proc = subprocess.run(
        [sys.executable, str(CONVERTER), str(SAMPLE_CONFIG), "--output-dir", str(tmp_path), "--tflint"],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = (tmp_path / "SANITY_REPORT.txt").read_text(encoding="utf-8")
    assert re.search(r"^tflint\s+SKIPPED", text, re.M), text
    assert "tflint binary not found" in text, text

    # The same shape read in process, so the skip is the check's own answer and not the report's wording.
    result = sanity_checks.check_tflint(tmp_path, None)
    assert result.result == "SKIPPED", result
    assert "tflint binary not found; skipped" in result.findings[0].detail, result.findings[0].render()
    # The check resolves the binary through `shutil.which`, so the pin clears PATH in process as well and gets
    # the same answer on a machine that has the binary.
    monkeypatch.setenv("PATH", "")
    report = sanity_checks.run_checks(tmp_path, run_tflint=True, tflint=None)
    assert report.result_of("tflint") == "SKIPPED", report.render()
    assert report.failed is False, "a SKIPPED result does not fail the gate"
    assert "tflint: SKIPPED" in report.console_summary(), report.console_summary()


def test_the_tflint_check_runs_once_per_unit_directory_and_names_the_directory_it_ran_on(tmp_path):
    """The check reads one directory, the way the plan check reads one root, so it produces one result per unit
    directory the record names, and names the directory it ran on in the note. The run writes nothing inside the
    directory it ran on, so a pin that reads a committed golden directory needs no copy of it.
    """
    if TFLINT is None:
        pytest.skip("tflint binary not found (the CI terraform-gate job provides it)")

    assert _generate(SAMPLE_CONFIG, tmp_path).returncode == 0
    units = sanity_checks.unit_directories(tmp_path)
    assert units, "the run wrote one directory per unit the record names"
    report = sanity_checks.run_checks(tmp_path, run_tflint=True, tflint=TFLINT)
    results = report.results("tflint")
    assert len(results) == len(units), "one rule-set result per unit directory"
    # A result that passed has no finding, so the note names the directory the check ran on.
    assert sorted(result.note.split(":", 1)[0] for result in results) == sorted(units), results

    # A run that names no unit has no unit directory, so the check runs on the codebase root and names it.
    root = tmp_path / "no_record"
    root.mkdir()
    lone = sanity_checks.run_checks(root, run_tflint=True, tflint=TFLINT)
    assert sanity_checks.unit_directories(root) == [], "no record, so no unit directory"
    assert len(lone.results("tflint")) == 1, "the root has one rule-set result"
    assert lone.results("tflint")[0].note.split(":", 1)[0] == ".", lone.results("tflint")[0].note

    # The committed goldens read clean through the set, and the bytes are the same after the run.
    before = written_bytes(GOLDEN_DIR)
    for case in sorted(GOLDEN_DIR.iterdir()):
        if not case.is_dir():
            continue
        for directory in sorted(p for p in case.iterdir() if p.is_dir()):
            path = f"{case.name}/{directory.name}"
            result = sanity_checks.check_tflint(directory, TFLINT, path)
            assert list(result.findings) == [], (path, [f.render() for f in result.findings])
            assert result.note.split(":", 1)[0] == path, result.note
    assert written_bytes(GOLDEN_DIR) == before, "the run writes nothing inside the directory it ran on"


def test_the_gate_states_no_second_naming_rule_for_the_shape_tflint_reports():
    """`naming.py` is the owner of the naming rule, so the naming fact the rule set reports is the generator's
    own output read through the tool's rule. The §5 shape keeps a doubled underscore, which is the shape the
    naming rule refuses, so the gate holds no second naming rule for it.
    """
    assert "terraform_naming_convention" in sanity_checks.TFLINT_RULES
    assert naming.sanitize("DG East__prod") == "dg_east__prod", "the §5 shape keeps the doubled underscore"
    source = (SRC_DIR / "sanity_checks.py").read_text(encoding="utf-8")
    assert "snake_case" not in source, "the gate states no naming rule of its own"

    # The finding names the rule and the message the tool wrote, so the check states no wording of its own.
    fact = sanity_checks.tflint_findings(
        ".",
        json.dumps(
            {
                "issues": [
                    {
                        "rule": {"name": "terraform_naming_convention", "severity": "info"},
                        "message": "must match the following format",
                        "range": {"filename": "scope.tf", "start": {"line": 1}},
                    }
                ]
            }
        ),
        2,
    )
    assert [finding.detail for finding in fact] == ["terraform_naming_convention: must match the following format"]
    assert [finding.severity for finding in fact] == [sanity_checks.WARN], fact


def test_the_enabled_rule_set_answers_nothing_on_the_goldens_and_one_fact_on_the_corpus(tmp_path):
    """What the rule set adds beyond the static rules, measured 2026-11-18 on tflint 0.66.0 with the bundled
    ruleset 0.17.0: nothing on the committed goldens, and one fact on the accepted corpus, on
    `edge_quoted_dg_names` in `scope.tf`, where the §5 shape kept a doubled underscore. The fact is an info
    finding, so it is WARN and the run still exits 0.
    """
    if TFLINT is None:
        pytest.skip("tflint binary not found (the CI terraform-gate job provides it)")

    for case in sorted(GOLDEN_DIR.iterdir()):
        if not case.is_dir():
            continue
        # The golden case is the output of one run, so its unit set is the directories it holds.
        for directory in sorted(p for p in case.iterdir() if p.is_dir()):
            path = f"{case.name}/{directory.name}"
            result = sanity_checks.check_tflint(directory, TFLINT, path)
            assert list(result.findings) == [], (path, [f.render() for f in result.findings])

    facts = []
    for name in corpus_fixtures():
        out = tmp_path / name.replace(".xml", "")
        proc = run_script("panorama_to_terraform.py", str(FIXTURES_DIR / name), "--output-dir", str(out))
        assert proc.returncode == 0, f"{name}: {proc.stdout}\n{proc.stderr}"
        report = sanity_checks.run_checks(out, run_tflint=True, tflint=TFLINT)
        findings = report.findings("tflint")
        if not findings:
            continue
        # Every corpus fact is the same kind: a name the §5 shape keeps and the naming rule refuses.
        for finding in findings:
            assert finding.detail.split(":", 1)[0] == "terraform_naming_convention", (name, finding.render())
            assert "__" in finding.detail, (name, finding.render())
            facts.append((name, Path(finding.file).name, finding.line, finding.severity, finding.detail))
            assert report.result_of("tflint") == sanity_checks.WARN, (name, report.render())
            assert report.failed is False, "a WARN does not change the exit code"

    assert len(facts) == 1, facts
    fixture, file, line, severity, detail = facts[0]
    assert fixture == "edge_quoted_dg_names.xml", facts
    assert file == "scope.tf" and line == 1, facts
    assert severity == sanity_checks.WARN, facts
    # The name the fact names is already the §5 shape, so the fact is the generator's own output: the two rules
    # disagree only on the doubled underscore the §5 shape keeps.
    block_name = detail.split("`")[1]
    assert naming.sanitize(block_name) == block_name, (detail, "the name is the §5 shape")
    assert "__" in block_name, (detail, "the §5 shape keeps the doubled underscore the naming rule refuses")


# --- The second entry point --------------------------------------------------


def test_splitter_output_has_no_tf_for_the_gate(tmp_path):
    """The splitter writes XML splits, so the gate has nothing to check there.

    This is stated so a reader does not assume the gate covers the splitter.
    """
    proc = run_script("split_device_groups.py", str(SAMPLE_CONFIG), "--output-dir", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    assert list(tmp_path.glob("*.xml"))
    report = sanity_checks.run_checks(tmp_path)
    assert report.file_count == 0
    assert report.data_file_count == 0, "the splitter writes no data file"
    assert report.resource_count == 0


# --- The join rule reads the request set through the join's owners (F8.8) ------

# The path 2 run these pins read: one committed response, the whole-config export, handed by the producer
# `tests/conftest.py` builds, so no test calls a network. Each pin runs the pipeline in process, because a fact
# from a run must be read from the run's ledger (`acceptance.md` criterion 10). The response holds the four
# membership lists and no scope entry of its own, so every pair the join answers is a fact that does not agree.
HOST = "panorama.test"
JOIN_ROWS = 7
UNIT_SIDE_ROWS = 3
ENTRY_SIDE_ROWS = 4


def _join_rule_source() -> str:
    """The join rule's own source, so a scan pins what that rule reads. The boundaries are the ones
    `tests/test_data_file_gate.py` and `tests/test_round_trip.py` pin: `check_data_files` …
    `check_round_trip` … `check_request_set` … `check_control_chars`.
    """
    source = Path(sanity_checks.__file__).read_text(encoding="utf-8")
    return source[source.index("def check_request_set") : source.index("def check_control_chars")]


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
    parser, index = _path2_run(tmp_path, tmp_path / "cache", monkeypatch)
    rule = _join_rule_source()
    assert "api_requests.unit_findings" in rule, "the gate reads the pairs through the join"
    assert "unit_manifest.directory_name" in rule and "naming.sanitize" in rule, (
        "the unit file is read through the one unit rule and the one naming rule"
    )
    for name in (
        "LIST_JOIN",
        "membership_lists",
        "response_names",
        "join_units",
        "cache_name",
        "SOURCE_FIELD",
        "unit_name",
        "facts_of",
        "sanitize_name",
    ):
        assert name not in rule, f"the rule states no {name} rule of its own"
    assert not [call for call in ("re.compile", "re.search", "re.match", "re.findall") if call in rule], (
        "the rule writes no reader of its own"
    )
    # Criterion 1: the join answers rows, so it has no check, no report section and no render, and the gate is
    # the only module in `src/` that turns a row into a finding.
    assert not [
        name
        for name in ("check", "report", "report_section", "render", "console_line", "finding")
        if hasattr(api_requests, name)
    ], "api_requests stays a join"
    readers = [path.name for path in SRC_DIR.glob("*.py") if ".unit_findings(" in path.read_text(encoding="utf-8")]
    assert readers == ["sanity_checks.py"], "the gate is the only module that reads the join as a rule"
    rows = api_requests.unit_findings(index, parser.ledger)
    assert len(rows) == JOIN_ROWS, rows
    assert len(sanity_checks.check_request_set(index, parser.ledger)) == JOIN_ROWS, "one finding per row"


def test_a_fact_that_the_join_and_the_ledger_do_not_agree_on_prints_in_the_report(tmp_path, monkeypatch):
    """F8.8 criterion 3, the unit side: the join answers no entry for a unit the ledger has rows for, so the
    fact names the unit directory the owners answer and no position in a file.
    """
    parser, index = _path2_run(tmp_path, tmp_path / "cache", monkeypatch)
    rows = api_requests.unit_findings(index, parser.ledger)
    unit_rows = [row for row in rows if row[0] is not None]
    assert len(unit_rows) == UNIT_SIDE_ROWS and all(row[1] is None for row in unit_rows), rows

    findings = sanity_checks.check_request_set(index, parser.ledger)
    unit_findings = [f for f in findings if f.file]
    assert len(unit_findings) == UNIT_SIDE_ROWS, [f.render() for f in findings]
    for facts, _ in unit_rows:
        named = [f for f in unit_findings if f.file == unit_manifest.directory_name(facts, naming.sanitize)]
        assert len(named) == 1, (facts, [f.render() for f in unit_findings])
        assert named[0].check == "request_set" and named[0].severity == sanity_checks.WARN, named[0].render()
        assert named[0].line == 0, "the fact compares two sets, so it names no position in a file"

    # A row carries the pair and the side the join has no fact for, so the row states no severity, no file and
    # no section: those are the gate's, and the printed form is `Finding.render`'s.
    assert all(isinstance(row, tuple) and len(row) == 2 for row in rows), rows
    report = sanity_checks.run_checks(tmp_path, index=index, ledger=parser.ledger)
    assert report.findings("request_set") == findings, "the report section holds the join rows"
    assert "[request_set]" in report.render().split("FINDINGS")[1], report.render()
    assert all(f"  {finding.render()}" in report.render() for finding in findings), report.render()


def test_the_run_wide_findings_print_through_the_join(tmp_path, monkeypatch):
    """F8.8 criterion 4, the run-wide side: an index entry the run read no rows for names no unit, so the fact
    names no file and prints in the root shape.
    """
    parser, index = _path2_run(tmp_path, tmp_path / "cache", monkeypatch)
    rows = api_requests.unit_findings(index, parser.ledger)
    entry_rows = [row for row in rows if row[1] is not None]
    assert len(entry_rows) == ENTRY_SIDE_ROWS and all(row[0] is None for row in entry_rows), rows

    findings = sanity_checks.check_request_set(index, parser.ledger)
    run_wide = [f for f in findings if not f.file]
    assert len(run_wide) == ENTRY_SIDE_ROWS, [f.render() for f in findings]
    assert all(f.file == "" and f.line == 0 for f in run_wide), [f.render() for f in findings]
    assert all(f.render().startswith("(run)  ") for f in run_wide), (
        "the root shape is `Finding.render`'s, the shape the plan check uses for a root fact"
    )

    report = sanity_checks.run_checks(tmp_path, index=index, ledger=parser.ledger)
    assert report.findings("request_set") == findings, report.render()
    assert all(f"  {finding.render()}" in report.render() for finding in run_wide), report.render()
    # The rule states no row set of its own, so the entry set is the join's own table read through the owner.
    # F8.9 closed the table half of the cross-response join; the row half stays open in `backlog.md`, which the
    # pin does not read. The open half is what the pin measures: every index entry is a row, because the join
    # has no row set to answer from.
    assert sorted(entry.path for entry in index) == sorted(entry.path for _, entry in entry_rows), index
    assert len(entry_rows) == len(index), "no row set of its own, so the join reports the index it was given"


def test_the_join_findings_sort_by_the_data_rule(tmp_path, monkeypatch):
    """F8.8 criterion 5: the report section orders the findings by (file, line, detail), which is not the order
    the join states its rows in.
    """
    parser, index = _path2_run(tmp_path, tmp_path / "cache", monkeypatch)
    rows = api_requests.unit_findings(index, parser.ledger)
    findings = sanity_checks.check_request_set(index, parser.ledger)
    # The join states its rows unit side first, in the order `unit_manifest.units` states them, then the
    # entries in the index order. The gate sorts the same rows by the three parts the data rule and the
    # cross-check use, so the run-wide facts print before the unit facts.
    join_order = [unit_manifest.directory_name(facts, naming.sanitize) if facts else "" for facts, _ in rows]
    assert join_order[:UNIT_SIDE_ROWS] == [
        unit_manifest.directory_name(facts, naming.sanitize) for facts in unit_manifest.units(parser.ledger)
    ], join_order
    assert join_order[UNIT_SIDE_ROWS:] == [""] * ENTRY_SIDE_ROWS, join_order
    assert [f.file for f in findings] == [""] * ENTRY_SIDE_ROWS + sorted(join_order[:UNIT_SIDE_ROWS]), findings
    assert findings == sorted(findings, key=lambda f: (f.file, f.line, f.detail)), [f.render() for f in findings]


def test_the_join_prints_no_console_line_and_stays_a_warn(tmp_path, monkeypatch):
    """F8.8 criteria 6 and 7: the join states no console line, so the rule prints none of its own, and the fact
    compares two sets, so it is a WARN and the exit code follows the rules that read the files.
    """
    parser, index = _path2_run(tmp_path, tmp_path / "cache", monkeypatch)
    rule = _join_rule_source()
    assert "console_line" not in rule and "CONSOLE_PREFIX" not in rule, "the rule prints no console line"
    findings = sanity_checks.check_request_set(index, parser.ledger)
    assert findings and all(f.severity == sanity_checks.WARN for f in findings), [f.render() for f in findings]
    report = sanity_checks.run_checks(tmp_path, index=index, ledger=parser.ledger)
    assert (report.fail_count, report.warn_count) == (0, JOIN_ROWS), report.render()
    assert report.failed is False, "a WARN does not fail the gate"
    assert (
        run_main(
            panorama_to_terraform,
            [
                "--source",
                "api",
                "--host",
                HOST,
                "--output-dir",
                str(tmp_path / "exit"),
                "--cache-dir",
                str(tmp_path / "exit-cache"),
            ],
        )
        == 0
    ), "the path 2 run exits the way a path 1 run exits"
    # As measured, criterion 7 cannot hold as written: the gate's own summary prints every finding, so the
    # join's findings print there too, in the shape every finding uses. `acceptance.md` records the measurement.
    summary = report.console_summary()
    assert len([line for line in summary.splitlines() if line.startswith("    ")]) == JOIN_ROWS, summary
    assert all(f"    {f.render()}" in summary for f in findings), summary
    assert f"  request_set: {sanity_checks.WARN}" in summary, summary


def test_the_rule_reports_not_run_when_the_gate_has_no_index(tmp_path, monkeypatch):
    """F8.8 criterion 8, and the path 1 half of criterion 10: the join needs the index and the ledger together,
    so a call that is missing either one reports NOT RUN, and a path 1 pin is unchanged.
    """
    parser, index = _path2_run(tmp_path, tmp_path / "cache", monkeypatch)
    ran = sanity_checks.run_checks(tmp_path, index=index, ledger=parser.ledger)
    assert ran.result_of("request_set") == sanity_checks.WARN, ran.render()

    half = sanity_checks.run_checks(tmp_path, ledger=parser.ledger)
    results = half.results("request_set")
    assert len(results) == 1 and not results[0].ran, results
    assert results[0].result == sanity_checks.NOT_RUN, results
    assert "index" in results[0].note and "ledger" in results[0].note, results[0].note
    assert half.findings("request_set") == [], "NOT RUN states no finding"

    # Path 1 read no request, so the entry point passes no index, and the result names its shape so a reader
    # can tell a rule that ran and passed from a rule that could not run.
    assert _generate(SAMPLE_CONFIG, tmp_path / "path1").returncode == 0
    plain = sanity_checks.run_checks(tmp_path / "path1")
    assert plain.result_of("request_set") == sanity_checks.NOT_RUN, plain.render()
    assert plain.findings("request_set") == [], "a path 1 run has no join fact to report"
    assert "request_set: NOT RUN" in plain.console_summary(), plain.console_summary()


def test_two_runs_read_the_same_files_and_report_the_same_findings(tmp_path, monkeypatch):
    """F8.8 criteria 10 and 11: two path 2 runs on the same content write the same files and report the same
    findings, and the report the gate writes through `write_path` is LF bytes.
    """
    reports = []
    for case in ("first", "second"):
        out = tmp_path / case
        parser, index = _path2_run(out, tmp_path / f"cache-{case}", monkeypatch)
        findings = sanity_checks.check_request_set(index, parser.ledger)
        report = sanity_checks.run_checks(out, index=index, ledger=parser.ledger)
        assert report.findings("request_set") == findings, report.render()
        write_path.write_file(write_path.root_path(out, "SANITY_REPORT.txt"), report.render())
        reports.append(out / "SANITY_REPORT.txt")
    assert tf_files(tmp_path / "first") == tf_files(tmp_path / "second"), "the same content writes the same files"
    assert reports[0].read_bytes() == reports[1].read_bytes(), "the byte rule: two runs state the same bytes"
    for report in reports:
        assert b"\r" not in report.read_bytes(), "the LF rule: text takes LF through the writer"
        text = report.read_text(encoding="utf-8")
        assert not re.search(r"\d{2}:\d{2}:\d{2}", text), text
        assert str(tmp_path) not in text, "no machine-dependent path"
        assert all(not line.lstrip().startswith("/") for line in text.split("\n") if line.startswith("  ")), text


def test_a_path_2_run_and_a_path_1_run_report_the_same_findings(tmp_path, monkeypatch):
    """F8.8 criteria 10 and 11, as measured: the same bytes read through both paths write the same files and
    report the same findings for every rule that reads the files. The join facts are run facts, so path 1
    reports NOT RUN, and both paths exit the same way.
    """
    response = RESPONSES_DIR / _export_name()
    path1 = run_pipeline(panorama_to_terraform, None, tmp_path / "path1", (str(response),))
    parser, index = _path2_run(tmp_path / "path2", tmp_path / "cache", monkeypatch)
    assert path1 is not None, "the path 1 run refused the input"
    assert tf_files(tmp_path / "path1") == tf_files(tmp_path / "path2"), "the same bytes write the same files"

    first = sanity_checks.run_checks(tmp_path / "path1", ledger=path1.ledger)
    second = sanity_checks.run_checks(tmp_path / "path2", index=index, ledger=parser.ledger)
    # Both reports hold one result per rule in `CHECK_ORDER`, so the two sides are the same set.
    for a, b in zip(first.checks, second.checks, strict=True):
        if a.check == "request_set":
            assert (a.result, b.result) == (sanity_checks.NOT_RUN, sanity_checks.WARN), (a.result, b.result)
        else:
            assert a.result == b.result, (a.check, a.result, b.result)
    assert (first.warn_count, second.warn_count) == (0, JOIN_ROWS), (first.render(), second.render())
    assert run_main(panorama_to_terraform, [str(response), "--output-dir", str(tmp_path / "path1")]) == 0
    assert (
        run_main(
            panorama_to_terraform,
            [
                "--source",
                "api",
                "--host",
                HOST,
                "--output-dir",
                str(tmp_path / "path2"),
                "--cache-dir",
                str(tmp_path / "cache"),
            ],
        )
        == 0
    )
    # The report a path 1 run writes names the join as a rule that did not run, so the two runs differ on one
    # line and on the source the record names.
    text = (tmp_path / "path1" / "SANITY_REPORT.txt").read_text(encoding="utf-8")
    assert re.search(r"^request_set\s+NOT RUN$", text, re.M), text
