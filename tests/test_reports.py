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

Epic 14 (`docs/IMPORT_BINDING.md` §2, decision 4, taken 2026-11-26): the report gains one section after the unit
section that names the units the run marked and the entries inside them the property scan reads as a whole block.
The marked units are read through `unit_manifest.marked_units` and the value through `unit_manifest.mode_of`, so the
section states no unit rule, no row field and no value of the pair, and the entry lines read the pair answer through
`entry_coverage.pair_answer`, so one line shape prints both the fact name and the difference. The section prints only
when the run marked a unit, so a run that declares nothing writes the report bytes it writes today, and it is report
content that prints no console line, so the console keeps the kinds `docs/ARCHITECTURE.md` §3.2 states.

Epic 14 (`docs/IMPORT_BINDING.md` §2, decision 6, taken 2026-11-26): the report gains the state scan's third
section, after the drift section and before the unit section, for a bound entry that needs a serial the state
document names no value for. The heading, the rule paragraph, the line shape and the finding set are read through
their owner, `state_coverage.py` rule 7, so this module pins the printing condition and the grouping only: the
section prints when the run read a state document and marked a unit, so a run that read no state document, or read
one and declared no pair, writes the report bytes it writes today, and the group is the same F3.9 rule. The section
is report content and prints no console line, so the console keeps the kinds §3.2 states, and the fact names an
operator action, so the gate still decides the exit code.
"""

import re
import shutil

import codebase_state
import container_coverage
import entry_coverage
import ownership
import reference_edges
import resource_mapping
import shadow_coverage
import state_coverage
import state_input
import unit_manifest
from conftest import (
    CODEBASE_FIXTURE,
    FIXTURES_DIR,
    JOIN_RECORDS,
    MODE_VALUES,
    RUN_FIXTURE,
    WORKSPACE,
    declaration_args,
    declaration_pairs,
    partial_run,
    record_rows,
    run_main,
    run_pipeline,
    run_script,
    serial_run,
    written_bytes,
)

FIXTURE = "report_grouping.xml"
# The fixture that produces a reference cycle, so one report can show a finding section before the unit section.
CYCLE_FIXTURE = "reference_cycle.xml"
# The fixture a pair read through `declaration_pairs` marks a unit inside, and the fixture that trips a property
# finding, so one report shows a finding section, the unit section and the marked section together.
MARKED_FIXTURE = "dependency_wiring.xml"

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
MARKED_HEADLINE = f"--- {entry_coverage.MARKED_HEADING} ---"
CONVERTER = "panorama_to_terraform.py"


def _unit_pair(tmp_path, first=CODEBASE_FIXTURE, second=RUN_FIXTURE, extra_args: tuple = ()):
    """The two runs as `tests/conftest.py::partial_run` states them, and the two row sets the section names.

    Each set is read through the module that owns its shape, so this module states no reader, no join key and no
    merge of its own. `extra_args` reaches the second run, so a pin that reads the units a run marked passes the
    declaration built from `record_rows` over the first run's rows. Returns the codebase directory, the run
    directory, the rows the run built, and the merged rows.
    """
    codebase, run, _second_run = partial_run(first, second, tmp_path, extra_args)
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


def test_the_unit_section_prints_after_the_sections_the_report_rule_already_orders(converter_module, tmp_path):
    """The unit section is the last finding section, before the entry lines, and the marked section prints after it.

    One fixture produces a reference cycle and the pair produces the unit section, so one report shows a finding
    section and the unit section together. The order is read through the headings their owners state. No committed
    fixture pair prints a cycle section and the marked section in one report, because only `CYCLE_FIXTURE` trips a
    cycle and the units its rows name are named by no pair from another fixture's rows, so the marked position is
    measured on its own pair: the property findings, the unit section, the marked section, then the entry lines.
    """
    declared = [
        entry_coverage.GAP_HEADING,
        entry_coverage.PROPERTY_HEADING,
        shadow_coverage.SHADOW_HEADING,
        ownership.FINDING_HEADING,
        reference_edges.CYCLE_HEADING,
        state_coverage.OWNERSHIP_HEADING,
        state_coverage.DRIFT_HEADING,
        state_coverage.SERIAL_HEADING,
        entry_coverage.UNIT_HEADING,
        entry_coverage.MARKED_HEADING,
    ]

    _codebase, run, _run_rows, _merged_rows = _unit_pair(tmp_path / "cycle", first=CYCLE_FIXTURE)
    report = (run / "CONVERSION_REPORT.txt").read_text(encoding="utf-8")
    present = [heading for heading in declared if f"--- {heading} ---" in report]
    positions = [report.index(f"--- {heading} ---") for heading in present]
    assert positions == sorted(positions), present
    assert report.index(ENTRY_LINES) > positions[-1]
    assert entry_coverage.UNIT_HEADING in present

    # The marked position: a pair read through `declaration_pairs`, so the second run marks a unit. Measured
    # 2026-11-26 on (`CODEBASE_FIXTURE`, `MARKED_FIXTURE`): 9 pairs, and the report prints the gap section, the
    # property findings, the unit section and the marked section, in that order, before the entry lines.
    _codebase, marked_run, rows, _scan, pairs = _marked_pair(converter_module, tmp_path / "marked")
    assert len(pairs) == 9, pairs
    assert unit_manifest.marked_units(rows), rows
    marked_report = (marked_run / "CONVERSION_REPORT.txt").read_text(encoding="utf-8")
    present = [heading for heading in declared if f"--- {heading} ---" in marked_report]
    positions = [marked_report.index(f"--- {heading} ---") for heading in present]
    assert positions == sorted(positions), present
    assert marked_report.index(ENTRY_LINES) > positions[-1]
    assert present == [
        entry_coverage.GAP_HEADING,
        entry_coverage.PROPERTY_HEADING,
        entry_coverage.UNIT_HEADING,
        entry_coverage.MARKED_HEADING,
    ], present

    # The serial position, measured on content that prints it: the section sits after the drift section and before
    # the unit section, so the order rule reads the headings their owners state and gains no position of its own.
    _source, _plain, _state_only, serial_run_out, _pairs, _document = serial_run(converter_module, tmp_path / "serial")
    serial_report = (serial_run_out / entry_coverage.REPORT_FILE).read_text(encoding="utf-8")
    present = [heading for heading in declared if f"--- {heading} ---" in serial_report]
    positions = [serial_report.index(f"--- {heading} ---") for heading in present]
    assert positions == sorted(positions), present
    assert serial_report.index(ENTRY_LINES) > positions[-1]
    assert present == [
        entry_coverage.GAP_HEADING,
        state_coverage.SERIAL_HEADING,
        entry_coverage.MARKED_HEADING,
    ], present


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


# --- the marked-unit section (Epic 14, decision 4 of `docs/IMPORT_BINDING.md` §2, taken 2026-11-26) ---


def _marked_pair(converter_module, tmp_path, first=CODEBASE_FIXTURE, second=MARKED_FIXTURE):
    """The pair as `tests/conftest.py::partial_run` states it, with the declaration the second run reads.

    The pairs are read through `declaration_pairs` over the rows the first run wrote, and the argument shape through
    `declaration_args`, so this module states no pair rule, no path shape and no value of the pair. Returns the
    codebase directory, the run directory, the rows the run built, the scan rows for the entries the run read, and
    the pairs the declaration names.
    """
    measured = tmp_path / "measured"
    assert run_pipeline(converter_module, first, measured) is not None, first
    pairs = declaration_pairs(record_rows(measured)[unit_manifest], MODE_VALUES[0])
    codebase, run, parser = partial_run(first, second, tmp_path / "pair", declaration_args(pairs))
    return codebase, run, record_rows(run)[unit_manifest], parser.ledger.block_rows(), pairs


def _shape(line: str) -> str:
    """A line read as its words, so a pin measures content and not the column padding the report shape uses."""
    return " ".join(line.strip().split())


def _marked_section(report: str) -> dict[str, list[str]]:
    """The marked section as {scope title: lines}, in the order the report prints them: one unit line, then the
    entry lines for the entries inside that unit. The rule paragraph is the report rule's own statement, so the pin
    reads the body only, and each line is read as its words.
    """
    text = report[report.index(MARKED_HEADLINE) + len(MARKED_HEADLINE) : report.index(ENTRY_LINES)]
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
            groups[current].append(_shape(line))
        else:
            current = line
            groups.setdefault(line, [])
    return groups


def test_the_marked_section_names_the_units_the_run_marked_through_the_record(converter_module, tmp_path):
    """Decision 4 of `docs/IMPORT_BINDING.md` §2, taken 2026-11-26: the section names the units this run marked, read
    through `unit_manifest.marked_units`, and the value through `unit_manifest.mode_of`, so the report states no unit
    rule, no row field and no value of the pair. The line shape is `entry_coverage.marked_unit_line`, stated once.

    Measured 2026-11-26 on the pair (`CODEBASE_FIXTURE`, `MARKED_FIXTURE`): 9 pairs, and the rows the run built show
    1 marked unit, `vsys1`, stating the first value of the pair. The run's other unit read entries but was not
    marked, so it prints no line here.
    """
    _codebase, run, rows, _scan_rows, pairs = _marked_pair(converter_module, tmp_path)
    assert len(pairs) == 9, pairs
    marked = unit_manifest.marked_units(rows)
    assert len(marked) == 1, [unit_manifest.mode_of(row) for row in rows]
    assert all(unit_manifest.mode_of(row) == MODE_VALUES[0] for row in marked), marked

    report = (run / "CONVERSION_REPORT.txt").read_text(encoding="utf-8")
    section = _marked_section(report)
    unit_lines = [line for lines in section.values() for line in lines if entry_coverage.MARKED_PART in line]
    assert len(unit_lines) == len(marked), unit_lines
    for row in marked:
        line = _shape(entry_coverage.marked_unit_line(row))
        assert any(line in lines for lines in section.values()), (line, section)
        assert unit_manifest.unit_name(unit_manifest.facts_of(row)) in line, line
        assert unit_manifest.mode_of(row) in line, line


def test_the_marked_section_prints_one_line_per_entry_in_the_scan_scope(converter_module, tmp_path):
    """One line per entry inside a unit the run marked, read through the scan's own row shape, and the fact part is
    `pair_answer`, so the same shape prints the fact name for an entry the scan reads as a whole block and the
    difference for the rest. An entry inside a unit the run did not mark prints no line, so the section prints the
    marked unit's entries and not the whole scan scope.

    Measured 2026-11-26 on the pair (`CODEBASE_FIXTURE`, `MARKED_FIXTURE`): 21 scan rows, 11 of them inside the
    marked unit and printed, 10 inside the run's unmarked unit and not printed. Of the 11, 10 answer the fact name
    and 1 answers a difference.
    """
    _codebase, run, rows, scan, _pairs = _marked_pair(converter_module, tmp_path)
    marked = {unit_manifest.facts_of(row) for row in unit_manifest.marked_units(rows)}
    inside = [row for row in scan if unit_manifest.facts_of(row) in marked]
    outside = [row for row in scan if unit_manifest.facts_of(row) not in marked]
    assert len(inside) == 11 and len(outside) == 10, (len(inside), len(outside))

    report = (run / "CONVERSION_REPORT.txt").read_text(encoding="utf-8")
    section = _marked_section(report)
    entry_lines = [line for lines in section.values() for line in lines if entry_coverage.MARKED_PART not in line]
    assert len(entry_lines) == len(inside), entry_lines
    for row in inside:
        line = _shape(entry_coverage.property_line(row))
        assert any(line in lines for lines in section.values()), (line, section)
        # The fact part of the line is the pair answer, and only the vsys part follows it.
        answer = entry_coverage.pair_answer(row)
        after = line[line.rindex(answer) + len(answer) :].strip()
        assert after == "" or after == f"[{row.get('vsys', '')}]", (line, answer, after)

    whole = [row for row in inside if not row["unused_properties"]]
    difference = [row for row in inside if row["unused_properties"]]
    assert len(whole) == 10 and len(difference) == 1, (len(whole), len(difference))
    assert all(entry_coverage.pair_answer(row) == entry_coverage.WHOLE_BLOCK_FACT for row in whole), whole
    assert all(entry_coverage.pair_answer(row) == entry_coverage.property_fact(row) for row in difference), difference
    # One fact name per entry, so no entry prints both.
    assert not any(entry_coverage.WHOLE_BLOCK_FACT in entry_coverage.property_fact(row) for row in scan), scan


def test_the_marked_section_prints_only_when_the_run_marked_a_unit(converter_module, tmp_path):
    """A run that declares no pair marks no unit, so the section prints nothing and a default run's report bytes are
    unchanged.

    Measured 2026-11-26 on the pair (`CODEBASE_FIXTURE`, `MARKED_FIXTURE`): the pair run with no declaration marks
    no unit and prints no section, and the pair run with the declaration the first run's rows name marks 1 unit and
    prints the section. The declared report with the section taken out reads byte for byte as the plain report, so
    every other section and the entry lines are the bytes the report rule already writes.
    """
    _plain_codebase, plain_run, _plain_parser = partial_run(CODEBASE_FIXTURE, MARKED_FIXTURE, tmp_path / "plain")
    _codebase, declared_run, rows, _scan, pairs = _marked_pair(converter_module, tmp_path / "declared")
    assert pairs, "the pin runs a run that declared a pair"

    plain_report = (plain_run / "CONVERSION_REPORT.txt").read_text(encoding="utf-8")
    declared_report = (declared_run / "CONVERSION_REPORT.txt").read_text(encoding="utf-8")
    assert not unit_manifest.marked_units(record_rows(plain_run)[unit_manifest]), record_rows(plain_run)[unit_manifest]
    assert unit_manifest.marked_units(rows), rows
    assert MARKED_HEADLINE not in plain_report, plain_report
    assert MARKED_HEADLINE in declared_report, declared_report

    start = declared_report.index("\n" + MARKED_HEADLINE)
    end = declared_report.index("\n" + ENTRY_LINES)
    assert declared_report[:start] + declared_report[end:] == plain_report, declared_report


def test_the_marked_section_groups_by_the_f3_9_rule_and_names_no_directory(converter_module, tmp_path):
    """The section titles are the scope the export declares, read through the one grouping rule this module pins, and
    the lines name a unit by its name and an entry by its identity, so the section states no grouping rule of its own
    and names no directory.

    Measured 2026-11-26 on the pair (`CODEBASE_FIXTURE`, `MARKED_FIXTURE`): the marked unit sits in the device scope
    its row states, so the section has one title, `DEVICE: device1`, and each entry line sits inside it.
    """
    _codebase, run, rows, scan, _pairs = _marked_pair(converter_module, tmp_path)
    report = (run / "CONVERSION_REPORT.txt").read_text(encoding="utf-8")
    section = _marked_section(report)
    gen = converter_module.TerraformGenerator(str(tmp_path / "out"))
    header = converter_module.TerraformGenerator._report_section_header
    marked = {unit_manifest.facts_of(row) for row in unit_manifest.marked_units(rows)}

    titles = {header(gen._report_scope_path(row)) for row in unit_manifest.marked_units(rows)}
    assert set(section) == titles, section
    assert titles == {"DEVICE: device1"}, titles

    by_unit: dict = {}
    for row in scan:
        by_unit.setdefault(unit_manifest.facts_of(row), []).append(row)
    # The unit line is read from the row the record states, because the scan row carries the pair and not the mode.
    unit_rows = {unit_manifest.facts_of(row): row for row in unit_manifest.marked_units(rows)}
    for facts, group in by_unit.items():
        title = header(gen._report_scope_path(group[0]))
        if facts in marked:
            unit_line = _shape(entry_coverage.marked_unit_line(unit_rows[facts]))
            assert unit_line == section[title][0], (unit_line, section[title])
            # The entry lines are in the order the scan's own sort gives them.
            assert section[title][1:] == [_shape(entry_coverage.property_line(row)) for row in group], (
                title,
                section[title],
            )
        else:
            # An entry inside a unit the run did not mark prints no line, so its group has no title here.
            assert title not in section, (title, group)
    for facts in by_unit:
        directory = unit_manifest.directory_name(facts, gen.sanitize_name)
        assert directory not in report, directory


def test_the_marked_section_is_byte_identical_between_runs(converter_module, tmp_path):
    """Rule 7, read through the new section: two runs that declare the same pairs on the same input write the same
    bytes, so the marked section is not a source of run-to-run difference. `tests/conftest.py::written_bytes` is the
    whole layout, so the pin compares the report bytes, the manifest bytes and the unit directories together.

    Measured 2026-11-26 on the pair (`CODEBASE_FIXTURE`, `MARKED_FIXTURE`): two runs that declare the same 9 pairs
    write byte-identical layouts, and the report inside them contains the marked section.
    """
    measured = tmp_path / "measured"
    assert run_pipeline(converter_module, CODEBASE_FIXTURE, measured) is not None, CODEBASE_FIXTURE
    pairs = declaration_pairs(record_rows(measured)[unit_manifest], MODE_VALUES[0])
    args = declaration_args(pairs)

    first = tmp_path / "first"
    assert run_pipeline(converter_module, MARKED_FIXTURE, first, args) is not None, MARKED_FIXTURE
    second = tmp_path / "second"
    assert run_pipeline(converter_module, MARKED_FIXTURE, second, args) is not None, MARKED_FIXTURE
    assert written_bytes(first) == written_bytes(second), sorted(written_bytes(first))
    report = (first / entry_coverage.REPORT_FILE).read_text(encoding="utf-8")
    assert MARKED_HEADLINE in report, report


def test_the_report_prints_no_console_line_for_the_marked_section(converter_module, tmp_path):
    """The marked section is report content only, so the console prints nothing for it, and the console keeps the
    kinds `docs/ARCHITECTURE.md` §3.2 states: the fact name reaches no console line, so no sixth kind appears and
    `tests/test_container_coverage.py::test_the_console_line_shape_is_stated_in_one_place` is unchanged.

    Measured 2026-11-26 on the pair (`CODEBASE_FIXTURE`, `MARKED_FIXTURE`): the run that declares the 9 pairs the
    first run's rows name prints the marked section in its report and prints the same scan block lines as the run
    that declares nothing, because the console block is built from the difference subset. The two console outputs
    differ only in the output-directory path lines and the `.tf` count the declared run's import blocks cause, so
    the pin compares the block lines and not the whole console.
    """
    _codebase, run, _rows, _scan, pairs = _marked_pair(converter_module, tmp_path)
    report = (run / "CONVERSION_REPORT.txt").read_text(encoding="utf-8")
    lines = [line for body in _marked_section(report).values() for line in body]
    assert lines, "the section prints, so there is something to check is not on the console"

    plain_dir = tmp_path / "plain_console"
    assert run_pipeline(converter_module, MARKED_FIXTURE, plain_dir) is not None, MARKED_FIXTURE
    pairs_for_run = declaration_pairs(record_rows(plain_dir)[unit_manifest], MODE_VALUES[0])
    console_dir = shutil.copytree(plain_dir, tmp_path / "declared_console")
    result = run_script(
        CONVERTER,
        str(FIXTURES_DIR / MARKED_FIXTURE),
        "--output-dir",
        str(console_dir),
        *declaration_args(pairs_for_run),
    )
    block = [line for line in result.stdout.splitlines() if line.startswith(container_coverage.CONSOLE_PREFIX)]
    assert block, result.stdout
    assert not any(entry_coverage.WHOLE_BLOCK_FACT in line for line in block), block
    for line in lines:
        normalized = " ".join(line.split())
        assert not any(normalized == " ".join(scan_line.split()) for scan_line in block), (line, block)


# --- the serial section (Epic 14, decision 6, `docs/IMPORT_BINDING.md` §2, taken 2026-11-26) ---

SERIAL_HEADLINE = f"--- {state_coverage.SERIAL_HEADING} ---"


def _serial_section(report: str) -> dict[str, list[str]]:
    """The serial section as {scope title: lines}, in the order the report prints them.

    The same shape the other report bodies read: the rule paragraph is the report rule's own statement, so the pin
    reads the body only, and each line is read as its words.
    """
    # The serial section is not the last section before the entry lines: the unit section and the marked section
    # print after it, so the reader stops at the next heading instead of at the entry lines.
    start = report.index(SERIAL_HEADLINE) + len(SERIAL_HEADLINE)
    end = report.find("--- ", start)
    end = report.index(ENTRY_LINES) if end < 0 else end
    text = report[start:end]
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
            groups[current].append(_shape(line))
        else:
            current = line
            groups.setdefault(line, [])
    return groups


def test_the_serial_section_prints_only_when_a_run_read_a_state_document_and_marked_a_unit(converter_module, tmp_path):
    """Rule 7, the printing half: the section needs both halves of the fact, so a run that read no state document, or
    a run that read one and declared no pair, writes the report bytes it writes today.

    Measured 2026-11-27 on the content `tests/conftest.py::serial_content` writes, because the committed corpus holds
    no state entry that needs a serial inside a unit a declaration can mark: the run that reads the state document and
    declares no pair prints no serial section, and the same run with the declaration read through `declaration_pairs`
    prints one section with one line. With the section taken out, the declared report reads byte for byte as the
    report of the run that read the same document and declared nothing, so the state read itself and the grouping rule
    write the same bytes as before the piece.
    """
    source, plain, state_only, declared, pairs, document = serial_run(converter_module, tmp_path)
    plain_report = (plain / entry_coverage.REPORT_FILE).read_text(encoding="utf-8")
    state_report = (state_only / entry_coverage.REPORT_FILE).read_text(encoding="utf-8")
    declared_report = (declared / entry_coverage.REPORT_FILE).read_text(encoding="utf-8")
    assert SERIAL_HEADLINE not in plain_report, plain_report
    assert SERIAL_HEADLINE not in state_report, state_report
    assert SERIAL_HEADLINE in declared_report, declared_report

    # The line is the shape its owner states, read through the same rule the section prints it with.
    section = _serial_section(declared_report)
    lines = [line for body in section.values() for line in body]
    assert lines, section
    findings = state_coverage.serial_findings(
        state_input.read_state(document, workspace=WORKSPACE),
        unit_manifest.marked_units(record_rows(declared)[unit_manifest]),
    )
    assert lines == [_shape(state_coverage.serial_line(finding)) for finding in findings], (section, findings)

    start = declared_report.index("\n" + SERIAL_HEADLINE)
    end = declared_report.index("\n" + ENTRY_LINES)
    assert declared_report[:start] + declared_report[end:] == state_report, declared_report


def test_the_serial_section_is_byte_identical_between_runs(converter_module, tmp_path):
    """Rule 7, the determinism half: two runs on the same arguments and the same bytes write the same report bytes, so
    the section is not a source of run-to-run difference. `tests/conftest.py::written_bytes` is the whole layout.

    Measured 2026-11-27 on the content `tests/conftest.py::serial_content` writes: two runs that read the same state
    document and declare the same pair write byte-identical layouts, and both reports hold the serial section.
    """
    source, _plain, _state_only, first, pairs, document = serial_run(converter_module, tmp_path)
    first_report = (first / entry_coverage.REPORT_FILE).read_text(encoding="utf-8")
    assert SERIAL_HEADLINE in first_report, first_report

    second = tmp_path / "again"
    assert (
        run_main(
            converter_module,
            [
                str(source),
                "--output-dir",
                str(second),
                "--state",
                str(document),
                "--workspace",
                WORKSPACE,
                *declaration_args(pairs),
            ],
        )
        == 0
    )
    second_report = (second / entry_coverage.REPORT_FILE).read_text(encoding="utf-8")
    assert SERIAL_HEADLINE in second_report, second_report
    assert written_bytes(first) == written_bytes(second), sorted(written_bytes(second))
    assert _serial_section(first_report) == _serial_section(second_report)
