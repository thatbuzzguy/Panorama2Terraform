"""F3.9: the two operator-facing migration reports name the scope each entry came from.

Both reports group by one rule, shared through `TerraformGenerator`: device
group first, then the template or the device the export places the entry in,
then the object kind inside the section. A section prints only the scope the
export declares, so the parser's `Shared` fallback is never printed as a device
group for an entry whose scope is a template or a device.

The fixture (tests/fixtures/report_grouping.xml) puts the same names in two
device groups, which is the case a flat report cannot tell apart.

The manual setup report's routing section (F7.1) names only the protocol entries the
`.tf` cannot hold, and its rows come from the ledger, so it uses the same grouping rule. The marker the VPN
section names is the table's one statement, `resource_mapping.PLACEHOLDER_TEXT`, so the report, the print site
that wrote it, and the gate rule read the same fact.

Epic 11 (`docs/MULTI_RUN_CODEBASE.md` §7): the run's report gains one section that names the run's unit set and
the codebase's unit set. Both sets are read through `unit_manifest.units`, the one unit rule, and the body is
grouped by the same F3.9 rule this module pins, so the section adds no unit rule and no grouping rule of its own.
It names a unit by name, never by directory, and it prints only when the codebase set names a unit the run set
does not, so a run that read the whole codebase writes the report bytes it writes today. The section is report
content and prints no console line; the console shape has one owner, `container_coverage.console_line`.
"""

import re
import shutil

import codebase_state
import entry_coverage
import ownership
import reference_edges
import resource_mapping
import shadow_coverage
import state_coverage
import unit_manifest
from conftest import (
    CODEBASE_FIXTURE,
    FIXTURES_DIR,
    JOIN_RECORDS,
    RUN_FIXTURE,
    partial_run,
    record_rows,
    run_script,
)

FIXTURE = "report_grouping.xml"
# The fixture that produces a reference cycle, so one report can show a finding section before the unit section.
CYCLE_FIXTURE = "reference_cycle.xml"

# A report section: an 80-character rule, the title, the rule, the body.
SECTION_RE = re.compile(r"={80}\n(?P<title>[^\n]+)\n={80}\n(?P<body>.*?)(?=(?:={80}\n|\Z))", re.S)

# Section titles the grouping rule can produce.
SCOPE_TITLES = ("DEVICE GROUP:", "TEMPLATE:", "DEVICE:", "SHARED SECTION")


def _generate(tmp_path, fixture=FIXTURE):
    """Run the converter and return the two reports as text."""
    result = run_script("panorama_to_terraform.py", str(FIXTURES_DIR / fixture), "--output-dir", str(tmp_path))
    assert result.returncode == 0, result.stderr
    return {f.name: f.read_text() for f in sorted(tmp_path.iterdir()) if f.is_file()}


def _sections(text: str) -> dict[str, str]:
    """Return {scope section title: body} for a grouped report."""
    return {title: body for title, body in SECTION_RE.findall(text) if title.startswith(SCOPE_TITLES)}


def _reports(tmp_path) -> tuple[str, str]:
    files = _generate(tmp_path)
    return files["INTERFACE_MIGRATION_REPORT.txt"], files["VPN_MIGRATION_REPORT.txt"]


# --- interface report ------------------------------------------------------


def test_interface_report_has_one_section_per_scope(tmp_path):
    iface, _vpn = _reports(tmp_path)
    assert set(_sections(iface)) == {
        "DEVICE GROUP: Datacenter-FW",
        "DEVICE GROUP: Office-FW",
        "SHARED SECTION",
        "TEMPLATE: HQ-Networks",
        "TEMPLATE: DC-Networks / DEVICE (this device placeholder): localhost.localdomain",
        "DEVICE: fw-2.example.com",
    }


def test_each_interface_section_lists_only_its_own_entries(tmp_path):
    iface, _vpn = _reports(tmp_path)
    sections = _sections(iface)
    own = {
        "DEVICE GROUP: Office-FW": "HQ uplink",
        "DEVICE GROUP: Datacenter-FW": "Datacenter uplink",
        "SHARED SECTION": "Shared management",
        "DEVICE: fw-2.example.com": "Own config",
    }
    for title, marker in own.items():
        assert marker in sections[title]
        # The same entry must not appear under another section.
        for other, body in sections.items():
            if other != title:
                assert marker not in body


def test_same_named_interface_appears_under_each_device_group(tmp_path):
    """The F3.9 point: two ethernet1/1 entries, one per device group."""
    iface, _vpn = _reports(tmp_path)
    sections = _sections(iface)
    occurrences = [title for title, body in sections.items() if "Interface: ethernet1/1" in body]
    assert sorted(occurrences) == ["DEVICE GROUP: Datacenter-FW", "DEVICE GROUP: Office-FW"]


def test_template_and_device_scopes_are_not_printed_as_a_device_group(tmp_path):
    iface, vpn = _reports(tmp_path)
    for report in (iface, vpn):
        for title, body in _sections(report).items():
            if title.startswith(("TEMPLATE:", "DEVICE:")):
                assert "DEVICE GROUP" not in title
                assert "DEVICE GROUP" not in body


def test_shared_section_is_named_shared(tmp_path):
    iface, vpn = _reports(tmp_path)
    assert "Interface: ethernet1/9" in _sections(iface)["SHARED SECTION"]
    assert "Gateway: GW-Shared" in _sections(vpn)["SHARED SECTION"]
    # The shared section is the PAN-OS shared section, not a device group.
    assert "DEVICE GROUP" not in _sections(iface)["SHARED SECTION"]


def test_placeholder_device_is_not_named_as_a_firewall(tmp_path):
    iface, _vpn = _reports(tmp_path)
    title = next(t for t in _sections(iface) if "localhost.localdomain" in t)
    assert "this device placeholder" in title


def test_interface_counts_are_per_section(tmp_path):
    iface, _vpn = _reports(tmp_path)
    assert "ETHERNET INTERFACES (2)" in _sections(iface)["DEVICE GROUP: Datacenter-FW"]
    assert "ETHERNET INTERFACES (1)" in _sections(iface)["DEVICE GROUP: Office-FW"]


def test_vsys_is_printed_only_when_the_export_declares_one(tmp_path):
    iface, vpn = _reports(tmp_path)
    # One declared vsys in the fixture, so one vsys line per report, and it
    # lands in the section that owns it.
    assert iface.count("Vsys:") == 1
    assert vpn.count("Vsys:") == 1
    assert "Vsys: vsys2" in _sections(iface)["DEVICE GROUP: Datacenter-FW"]
    assert "Vsys: vsys2" in _sections(vpn)["DEVICE GROUP: Datacenter-FW"]


def test_interface_footer_is_one_shared_block(tmp_path):
    iface, _vpn = _reports(tmp_path)
    for footer in ("MIGRATION CHECKLIST", "PLATFORM MIGRATION NOTES"):
        assert iface.count(footer) == 1
    titles = [title for title, _body in SECTION_RE.findall(iface)]
    # The footer is one shared block after every scope section.
    assert titles[-2:] == ["MIGRATION CHECKLIST", "PLATFORM MIGRATION NOTES"]
    assert any(title.startswith(SCOPE_TITLES) for title in titles[:-2])


# --- VPN report ------------------------------------------------------------


def test_vpn_report_has_one_section_per_scope(tmp_path):
    _iface, vpn = _reports(tmp_path)
    assert set(_sections(vpn)) == {
        "DEVICE GROUP: Datacenter-FW",
        "DEVICE GROUP: Office-FW",
        "SHARED SECTION",
    }


def test_each_vpn_section_lists_only_its_own_entries(tmp_path):
    _iface, vpn = _reports(tmp_path)
    sections = _sections(vpn)
    own = {
        "DEVICE GROUP: Office-FW": "203.0.1.10",
        "DEVICE GROUP: Datacenter-FW": "203.0.1.11",
        "SHARED SECTION": "203.0.1.12",
    }
    for title, marker in own.items():
        assert marker in sections[title]
        for other, body in sections.items():
            if other != title:
                assert marker not in body


def test_same_named_gateway_appears_under_each_device_group(tmp_path):
    _iface, vpn = _reports(tmp_path)
    sections = _sections(vpn)
    occurrences = [title for title, body in sections.items() if "\nGateway: GW-Common" in body]
    assert sorted(occurrences) == ["DEVICE GROUP: Datacenter-FW", "DEVICE GROUP: Office-FW"]


def test_pre_shared_key_warning_survives_at_the_top(tmp_path):
    _iface, vpn = _reports(tmp_path)
    warning = vpn.index("CRITICAL: PRE-SHARED KEY MANAGEMENT")
    first_section = min(vpn.index(title) for title in _sections(vpn))
    assert warning < first_section
    # The warning is shared, so it is printed once, not per section.
    assert vpn.count("CRITICAL: PRE-SHARED KEY MANAGEMENT") == 1


def test_per_gateway_placeholder_line_survives(tmp_path):
    _iface, vpn = _reports(tmp_path)
    # One line per pre-shared-key gateway, inside its own section.
    assert vpn.count("***MUST BE UPDATED***") == 4
    for _title, body in _sections(vpn).items():
        # 'Gateway: ' at the entry line, not the tunnel's IKE Gateway reference.
        assert body.count("***MUST BE UPDATED***") == body.count("\nGateway: ")
        # The marker is the table's one statement, read through `resource_mapping.PLACEHOLDER_TEXT`.
        assert resource_mapping.PLACEHOLDER_TEXT in body, body


def test_vpn_footer_is_one_shared_block(tmp_path):
    _iface, vpn = _reports(tmp_path)
    for footer in ("KEY MANAGEMENT BEST PRACTICES", "MIGRATION CHECKLIST", "IMPORTANT SECURITY NOTES"):
        assert vpn.count(footer) == 1
    titles = [title for title, _body in SECTION_RE.findall(vpn)]
    assert titles[-3:] == ["KEY MANAGEMENT BEST PRACTICES", "MIGRATION CHECKLIST", "IMPORTANT SECURITY NOTES"]
    assert any(title.startswith(SCOPE_TITLES) for title in titles[:-3])


# --- shared rule and determinism -------------------------------------------


def test_both_reports_use_the_same_grouping_rule(converter_module, make_parser, tmp_path):
    """The section titles come from one helper, so the reports cannot drift."""
    parser = make_parser(FIXTURE)
    gen = converter_module.TerraformGenerator(str(tmp_path))
    header = converter_module.TerraformGenerator._report_section_header

    iface_report, vpn_report = _reports(tmp_path)
    iface_titles = {header(gen._report_scope_path(entry)) for entry in parser.parse_interfaces()}
    vpn_titles = {
        header(gen._report_scope_path(entry)) for entry in parser.parse_ike_gateways() + parser.parse_ipsec_tunnels()
    }
    assert set(_sections(iface_report)) == iface_titles
    assert set(_sections(vpn_report)) == vpn_titles


def test_sections_and_entries_are_in_a_stable_order(tmp_path):
    first = _generate(tmp_path)
    second = _generate(tmp_path / "again")
    assert first["INTERFACE_MIGRATION_REPORT.txt"] == second["INTERFACE_MIGRATION_REPORT.txt"]
    assert first["VPN_MIGRATION_REPORT.txt"] == second["VPN_MIGRATION_REPORT.txt"]


def test_no_report_when_there_is_nothing_to_report(tmp_path):
    """A fixture with no interface and no VPN entry writes neither report."""
    files = _generate(tmp_path, "address_objects.xml")
    assert "INTERFACE_MIGRATION_REPORT.txt" not in files
    assert "VPN_MIGRATION_REPORT.txt" not in files


# --- manual setup report: the routing entries the file cannot express (F7.1) --

PROTOCOL_SECTION = "--- Routing protocol entries the generated file cannot express (F7.1) ---"


def _manual_sections(text: str) -> dict[str, str]:
    """{scope section title: body} for the grouped manual report sections."""
    blocks = {}
    current = None
    for line in text.splitlines():
        if line.startswith(SCOPE_TITLES):
            current = line
            blocks[current] = []
        elif current is not None:
            blocks[current].append(line)
    return {title: "\n".join(body) for title, body in blocks.items()}


def test_protocol_report_sections_name_the_scope_and_the_router(tmp_path):
    """The protocol rows use the same grouping rule as the other report sections (F3.9).

    tests/fixtures/router_scopes.xml puts one entry the `.tf` cannot express in each of the
    two scopes, so a flat section cannot tell them apart.
    """
    report = _generate(tmp_path, "router_scopes.xml")["MANUAL_SETUP_REPORT.txt"]
    assert PROTOCOL_SECTION in report
    sections = _manual_sections(report)
    assert set(sections) == {"DEVICE GROUP: Router-Group", "TEMPLATE: Router-Template"}, sections
    assert ("router R1: interface ethernet1/1 (no provider field for an interface outside an area)") in sections[
        "DEVICE GROUP: Router-Group"
    ]
    assert ("router R2: peer 10.2.0.1 (panos_virtual_router - no peer group names it)") in sections[
        "TEMPLATE: Router-Template"
    ]
    # One entry is one row: the parse keeps one path, so an entry is not named twice.
    assert report.count("router R1") == 1
    assert report.count("router R2") == 1


def test_device_router_section_names_the_device(tmp_path):
    """A router in a device's own config is printed under the device, not a device group."""
    report = _generate(tmp_path, "bgp.xml")["MANUAL_SETUP_REPORT.txt"]
    assert "DEVICE (this device placeholder): localhost.localdomain" in report
    assert report.count("router default") == 1
    assert "Vsys: vsys1" in report


def test_protocol_report_prints_only_what_the_file_cannot_hold(tmp_path):
    """The capture decision is the print decision, for the entries the `.tf` cannot hold (F7.1).

    The report names the entry the shape table states no provider field for, with the fields
    the table declares for that level, read through the captured object. An entry the emitter
    printed is not named here, so the report holds no duplicate of the `.tf`.
    """
    report = _generate(tmp_path, "bgp.xml")["MANUAL_SETUP_REPORT.txt"]
    assert "router default: peer 10.55.0.9 (panos_virtual_router - no peer group names it)" in report
    assert "    enable: True" in report
    assert "    peer_as: 65003" in report
    assert "    peer_address: ip=10.55.0.9" in report
    # The peer inside the peer group and the peer group itself are printed in the `.tf`, so the
    # report names neither.
    assert "10.55.0.2" not in report
    assert "PG-Branch" not in report


def test_protocol_report_is_byte_identical_between_runs(tmp_path):
    """The rows come from the ledger in report order, so the section cannot drift (F4.2 rule)."""
    first = _generate(tmp_path, "bgp.xml")
    second = _generate(tmp_path / "again", "bgp.xml")
    assert first["MANUAL_SETUP_REPORT.txt"] == second["MANUAL_SETUP_REPORT.txt"]


# --- the run's unit section (Epic 11, `docs/MULTI_RUN_CODEBASE.md` §7) ---------

ENTRY_LINES = "Entry lines are grouped by"
UNIT_HEADLINE = f"--- {entry_coverage.UNIT_HEADING} ---"
CONVERTER = "panorama_to_terraform.py"


def _unit_pair(tmp_path, first=CODEBASE_FIXTURE, second=RUN_FIXTURE):
    """The two runs as `tests/conftest.py::partial_run` states them, and the two row sets the section names.

    Each set is read through the module that owns its shape, so this module states no reader, no join key and no
    merge of its own. Returns the codebase directory, the run directory, the rows the run built, and the merged rows.
    """
    codebase, run, _second_run = partial_run(first, second, tmp_path)
    held, built = record_rows(codebase), record_rows(run)
    merged = {module: codebase_state.merge_rows(JOIN_RECORDS[module], held[module], built[module]) for module in held}
    return codebase, run, built[unit_manifest], merged[unit_manifest]


def _unit_section(report: str) -> dict[str, list[str]]:
    """The unit section as {scope title: lines}, in the order the report prints them.

    A line is read as the two words that name the set and the unit name, so the pin measures the words and the
    names, not the spacing between them.
    """
    text = report[report.index(UNIT_HEADLINE) + len(UNIT_HEADLINE) : report.index(ENTRY_LINES)]
    groups: dict[str, list[str]] = {}
    current = None
    rule_seen = False
    for line in text.splitlines():
        if not line:
            continue
        if not rule_seen:
            rule_seen = True
            continue  # the rule paragraph, which is the report rule's own statement
        if line.startswith("  "):
            groups[current].append(" ".join(line.strip().split()))
        else:
            current = line
            groups.setdefault(line, [])
    return groups


def test_the_unit_section_names_the_two_unit_sets_through_the_one_unit_rule(converter_module, tmp_path):
    """One line per unit the one unit rule names over the merged set, each named by the name the rule gives it.

    The part on the line is the answer the two sets give, so the pin measures the section against the sets rather
    than against a wording: a line whose unit is in the run's set names the run's part, and a line whose unit is
    only in the codebase set names the record part. Both parts and both names are read through their owners.
    """
    _codebase, run, run_rows, merged_rows = _unit_pair(tmp_path)
    run_units = set(unit_manifest.units(run_rows))
    codebase_units = set(unit_manifest.units(merged_rows))
    assert codebase_units - run_units, "the pair needs a unit the run did not read"

    report = (run / "CONVERSION_REPORT.txt").read_text(encoding="utf-8")
    section = _unit_section(report)
    lines = [line for body in section.values() for line in body]
    # One line per unit the rule names, and no line for a unit the rule does not name.
    assert len(lines) == len(codebase_units), lines
    assert any(entry_coverage.BUILT_PART in line for line in lines), "the run's own set must be named too"

    gen = converter_module.TerraformGenerator(str(tmp_path / "out"))
    for row in merged_rows:
        facts = unit_manifest.facts_of(row)
        title = converter_module.TerraformGenerator._report_section_header(gen._report_scope_path(row))
        part = entry_coverage.BUILT_PART if facts in run_units else entry_coverage.RECORD_ONLY_PART
        assert f"{part} {unit_manifest.unit_name(facts)}" in section[title], (title, section[title])


def test_the_unit_section_prints_only_when_a_unit_the_run_did_not_read_is_in_the_codebase_set(tmp_path):
    """A run that read the whole codebase names nothing, so its report bytes are the bytes it writes today.

    The pair prints the section because the codebase set names a unit the run set does not. The same fixture run
    twice puts the run in the codebase it read, so the second run's set is the codebase set and the section does
    not print at all.
    """
    _codebase, run, run_rows, merged_rows = _unit_pair(tmp_path)
    report = (run / "CONVERSION_REPORT.txt").read_text(encoding="utf-8")
    assert UNIT_HEADLINE in report
    assert set(unit_manifest.units(merged_rows)) - set(unit_manifest.units(run_rows))

    for name in ("whole", "again"):
        run_script(CONVERTER, str(FIXTURES_DIR / CODEBASE_FIXTURE), "--output-dir", str(tmp_path / name))
    first_report = (tmp_path / "whole" / "CONVERSION_REPORT.txt").read_text(encoding="utf-8")
    second_report = (tmp_path / "again" / "CONVERSION_REPORT.txt").read_text(encoding="utf-8")
    assert UNIT_HEADLINE not in first_report, first_report
    assert first_report == second_report, "a run that read the whole codebase writes the report bytes it writes today"


def test_the_unit_section_prints_after_the_sections_the_report_rule_already_orders(tmp_path):
    """The unit section is the last finding section, before the entry lines.

    One fixture produces a reference cycle and the pair produces the unit section, so one report shows a finding
    section and the unit section together. The order is read through the headings their owners state.
    """
    _codebase, run, _run_rows, _merged_rows = _unit_pair(tmp_path, first=CYCLE_FIXTURE)
    report = (run / "CONVERSION_REPORT.txt").read_text(encoding="utf-8")
    declared = [
        entry_coverage.GAP_HEADING,
        entry_coverage.PROPERTY_HEADING,
        shadow_coverage.SHADOW_HEADING,
        ownership.FINDING_HEADING,
        reference_edges.CYCLE_HEADING,
        state_coverage.OWNERSHIP_HEADING,
        state_coverage.DRIFT_HEADING,
        entry_coverage.UNIT_HEADING,
    ]
    present = [heading for heading in declared if f"--- {heading} ---" in report]
    positions = [report.index(f"--- {heading} ---") for heading in present]
    assert positions == sorted(positions), present
    assert report.index(ENTRY_LINES) > positions[-1]
    assert entry_coverage.UNIT_HEADING in present


def test_the_unit_section_names_no_directory_and_groups_by_the_f3_9_rule(converter_module, tmp_path):
    """The section titles are the scope the export declares, and the lines name a unit by name, not by directory.

    The grouping rule is the one this module pins for the other report sections, read through its owner, so the
    unit section states no grouping rule of its own.
    """
    _codebase, run, _run_rows, merged_rows = _unit_pair(tmp_path)
    report = (run / "CONVERSION_REPORT.txt").read_text(encoding="utf-8")
    section = _unit_section(report)
    gen = converter_module.TerraformGenerator(str(tmp_path / "out"))
    header = converter_module.TerraformGenerator._report_section_header

    groups: dict[str, list[dict]] = {}
    for row in merged_rows:
        groups.setdefault(header(gen._report_scope_path(row)), []).append(row)
    assert set(section) == set(groups), section
    assert all(lines for lines in section.values()), "every named unit's line is inside its own group"
    for title, rows in groups.items():
        names = [unit_manifest.unit_name(unit_manifest.facts_of(row)) for row in rows]
        # The name on each line is the name the one unit rule gives the row, and no line is empty.
        pairs = list(zip(section[title], names, strict=True))
        assert all(line.endswith(name) for line, name in pairs), (title, section[title])
        # The directory is the §5 shape of the same identity, so it is a different string from the name.
        for row in rows:
            directory = unit_manifest.directory_name(unit_manifest.facts_of(row), gen.sanitize_name)
            assert directory not in report, directory


def test_the_report_prints_no_console_line_for_the_unit_section(tmp_path):
    """The section is report content only, so the console prints nothing for it.

    The console shape has one owner, `container_coverage.console_line`, and no scan shape prints the two words that
    say which set names a unit, so the section's words and lines appear in the report file and not on the console.
    A console line may still name a unit through a finding, because the finding shape names the entry it found.
    """
    codebase, run, _second_run = partial_run(CODEBASE_FIXTURE, RUN_FIXTURE, tmp_path)
    # The same pair through the command, so the console is the run's own output.
    console_dir = shutil.copytree(codebase, tmp_path / "console")
    result = run_script(CONVERTER, str(FIXTURES_DIR / RUN_FIXTURE), "--output-dir", str(console_dir))
    report = (console_dir / "CONVERSION_REPORT.txt").read_text(encoding="utf-8")
    lines = [line for body in _unit_section(report).values() for line in body]
    assert lines, "the section prints, so there is something to check is not on the console"

    held, built = record_rows(codebase), record_rows(run)
    merged = {module: codebase_state.merge_rows(JOIN_RECORDS[module], held[module], built[module]) for module in held}
    codebase_units = set(unit_manifest.units(merged[unit_manifest]))
    run_units = set(unit_manifest.units(built[unit_manifest]))
    only_in_the_record = codebase_units - run_units
    assert only_in_the_record, only_in_the_record

    shapes = {" ".join(line.split()) for line in lines}
    for stdout_line in result.stdout.splitlines():
        normalized = " ".join(stdout_line.split())
        for part in (entry_coverage.BUILT_PART, entry_coverage.RECORD_ONLY_PART):
            assert part not in normalized, stdout_line
        assert normalized not in shapes, stdout_line
