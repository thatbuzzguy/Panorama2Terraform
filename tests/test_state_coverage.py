"""F5.6 state coverage: the ownership fact, the drift fact, and the device serial fact for a bound unit.

Nine groups, one per acceptance rule:

1. The state entry shape the scan reads: the matrix row is the row keyed by the resource type
   through the same table, the properties are read with the F4.3 rule, and the position is the
   resource address.
2. The ownership fact: §2.1 identity as the F3.9 rule reads it, the declared facts only, the
   first entry for a key wins in document order, the scan scope is the F4.4 rule on both sides,
   and a run with no state source reports nothing.
3. The drift fact: a declared property the state reads under the name the comparison table gives it,
   or under the same name where the table has no row, the value compared as held, order part of the
   value, and a drift fact needs an ownership fact.
4. The two report sections, the fixed line shapes, the F3.9 grouping, no console line, and the
   exit code the F4.1 gate still decides.
5. The state scan is not an output, so it cannot move a property finding.
6. Determinism, and the record: two runs on the same arguments and the same bytes write the same
   bytes, and a state record reads back through `parse_records` with no new field.
7. The comparison table: the rows are a measurement per matrix row type against the pinned provider
   schema, the scan reads the mapping only through the table, and the same-name rule stands where the
   table has no row.
8. The existing codebase records as a reference source: read as data through the readers the shape owners
   state, and the half the read reaches (`docs/MULTI_RUN_CODEBASE.md` §4 rule 1).
9. The device serial fact for a bound unit (decision 6 of `docs/IMPORT_BINDING.md` §2, taken 2026-11-26): the
   value the state document holds for the entry through the location it holds, the one name the module states,
   the block and the id as one fact through the shape table, no serial for a run that reads no state document,
   the report-only finding for a bound unit, the exit code the F4.1 gate still decides, and the owner shape that
   states no reader, no path rule, no row shape, no unit rule, no severity rule, no value of the pair and no name
   list of its own.

Every test uses a committed fixture, so no test opens a connection. The run side is
`tests/fixtures/address_objects.xml`; the state side is `tests/fixtures/state_workspace.json`. The pins
in group 7 read the live provider schema through `tests/conftest.py`, which owns the skip rule, and the pins
in group 7 and group 8 read the committed pair through `tests/conftest.py`. The committed corpus holds no state
entry that needs a serial inside a unit a declaration can mark, so the pins in group 9 read the content
`tests/conftest.py::serial_content` writes, and no committed byte moves.
"""

import ast
import contextlib
import inspect
import io
import sys
from pathlib import Path

import pytest

import codebase_state
import container_coverage
import entry_coverage
import import_blocks
import input_shapes
import naming
import ownership
import provenance
import resource_mapping
import sanity_checks
import site_data
import state_coverage
import state_input
import unit_manifest
from conftest import (
    CODEBASE_FIXTURE,
    FIXTURES_DIR,
    JOIN_RECORDS,
    MODE_VALUES,
    RUN_FIXTURE,
    SERIAL_ENTRY_NAME,
    SERIAL_GROUP,
    SERIAL_VSYS,
    SRC_DIR,
    STATE_FIXTURE,
    WORKSPACE,
    declaration_args,
    partial_run,
    record_rows,
    run_main,
    run_pipeline,
    serial_run,
    tf_bytes,
    written_bytes,
)
from xml_input import parse_xml

SERVICE_FIXTURE = "service_groups.xml"
REGION_FIXTURE = "regions.xml"
GROUP_FIXTURE = "address_groups.xml"

# The entries both sides hold, and the lines the run side reads them at.
OWNED_NAME = "Web-Server-1"
OWNED_LINE = 5
ORDER_NAME = "Web-Services"
STATE_ADDRESS = "panos_address.web_server_1_11f477f4"
NO_FACTS = {"device_group": "", "vsys": "", "template": "", "vsys_device": "", "template_stack": ""}
FOOTER = "Entry lines are grouped by"


@pytest.fixture
def state():
    """The committed state document, read through the state door."""
    return state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)


def _entry(state: state_input.StateSource, name: str, resource_type: str = "panos_address") -> state_input.StateEntry:
    """One fixture entry, read through the producer."""
    return next(e for e in state.entries if e.entry_name == name and e.resource_type == resource_type)


def _state_args(extra: tuple = ()) -> tuple:
    return ("--state", str(FIXTURES_DIR / STATE_FIXTURE), "--workspace", WORKSPACE, *extra)


def _findings(converter_module, fixture: str, out, state) -> list:
    """The findings of the run itself, so the facts come from the run's ledger."""
    parser = run_pipeline(converter_module, fixture, out, _state_args())
    return state_coverage.state_findings(parser.ledger, state)


def _section(report: str, heading: str) -> str:
    """One report section: from its heading to the next heading, or to the entry-line footer."""
    start = report.index(heading)
    rest = report[start + len(heading) :]
    end = rest.index("--- ") if "--- " in rest else report.index(FOOTER)
    return report[start : start + len(heading) + end]


def _report(out) -> str:
    return (out / entry_coverage.REPORT_FILE).read_text(encoding="utf-8")


# --- 1. The state entry shape ------------------------------------------------


def test_the_matrix_row_is_the_same_table_the_property_scan_uses(state):
    """AC-1.3: the row is keyed by the resource type through `MATRIX_BY_RESOURCE`, so the scan
    holds no second naming rule for a state entry."""
    entry = _entry(state, OWNED_NAME)
    assert entry.resource_type in entry_coverage.MATRIX_BY_RESOURCE, entry.resource_type
    assert entry_coverage.MATRIX_BY_RESOURCE[entry.resource_type] is entry_coverage.MATRIX_BY_RESOURCE["panos_address"]


def test_the_identity_keys_are_not_properties(state):
    """AC-1.3, F4.3 rule 3: the entry name and the location are identity, not content, and an
    empty value is not a property."""
    properties = state_coverage.state_properties(_entry(state, OWNED_NAME))
    assert "name" not in properties and "location" not in properties, properties
    assert properties["description"] == "Web tier", properties

    empty = next(e for e in state.entries if e.resource_name == "empty_property_b2b2b2b2")
    assert "tag" not in state_coverage.state_properties(empty), state_coverage.state_properties(empty)
    assert "description" not in state_coverage.state_properties(empty), "an empty value is not a property"


def test_the_position_is_the_resource_address(state):
    """AC-1.4: a state entry has no source line, so its position is its resource address."""
    assert _entry(state, "Module-Only").address == "network:panos_address.module_only_66666666"
    assert _entry(state, OWNED_NAME).address == STATE_ADDRESS, _entry(state, OWNED_NAME)
    assert not hasattr(state.entries[0], "line"), "the producer records no source line"


def test_a_nested_block_reads_as_an_object_or_a_one_element_list(state):
    """AC-1.6: the provider writes a nested block either way, so both shapes read."""
    assert state_coverage.nested_block({"shared": {}}) == {"shared": {}}
    assert state_coverage.nested_block([{"shared": [{}]}]) == {"shared": [{}]}
    assert state_coverage.nested_block("not a block") == {}, "a value that is not a block fills nothing"
    # The fixture holds both shapes for the same key, so both read the same facts.
    list_shape = next(e for e in state.entries if e.resource_name == "web_server_1_11f477f4")
    object_shape = next(e for e in state.entries if e.resource_name == "empty_property_b2b2b2b2")
    assert state_coverage.state_facts(list_shape) == state_coverage.state_facts(object_shape)


# --- 2. The ownership fact ---------------------------------------------------


def test_the_key_is_identity_as_the_f3_9_rule_reads_it(converter_module, tmp_path, state):
    """AC-2.1: the matrix row, the entry name, and the five declared facts, read from the run.
    A shared run entry is keyed with empty facts, never with the `Shared` fallback."""
    findings = _findings(converter_module, RUN_FIXTURE, tmp_path / "out", state)
    row = next(f for f in findings if f["name"] == OWNED_NAME)
    key = state_coverage.ownership_key(
        row["resource"], row["name"], {fact: row[fact] for fact in container_coverage.SCOPE_FACT_KEYS}
    )
    assert key == ("panos_address", OWNED_NAME, "", "", "", "", ""), key
    assert all(row[fact] == "" for fact in container_coverage.SCOPE_FACT_KEYS), row
    assert state_coverage.state_index(state)[key] is _entry(state, OWNED_NAME), key
    assert "Shared" not in str(key), "the parse fallback is not a declared fact"


def test_a_declared_fact_makes_a_different_object(state):
    """AC-2.2: the same name in a different scope is a different object, so a shared run entry is
    not keyed against the state entry in `Production-DG`."""
    index = state_coverage.state_index(state)
    shared_key = ("panos_address", "Web-Range", "", "", "", "", "")
    declared_key = ("panos_address", "Web-Range", "Production-DG", "Vsys2", "", "firewall-2", "")
    assert shared_key in index and declared_key in index, index
    assert index[shared_key] is not index[declared_key], "two objects, two keys"


def test_the_shared_block_fills_no_fact(state):
    """AC-2.2: `shared` names the shared section, which states no name, so it fills no fact."""
    assert state_coverage.state_facts(_entry(state, OWNED_NAME)) == NO_FACTS, state_coverage.state_facts(
        _entry(state, OWNED_NAME)
    )


def test_the_placeholder_device_names_no_device(state):
    """AC-2.2, F3.5: `localhost.localdomain` names no firewall, so it is never a `vsys_device`
    fact, and `container_coverage.PLACEHOLDER_DEVICE` is the one definition both paths read."""
    facts = state_coverage.state_facts(_entry(state, "Placeholder-Device"))
    assert facts["vsys_device"] == "", facts
    assert facts["vsys"] == "Vsys1", facts
    assert container_coverage.PLACEHOLDER_DEVICE == "localhost.localdomain", container_coverage.PLACEHOLDER_DEVICE


def test_a_block_the_row_does_not_declare_is_not_keyed(state):
    """AC-2.2: `panos_address` declares no `template_stack` sub-block, so an entry placed there is not
    keyed. The fact the sub-block names is `template_stack` (F6.10.5), so the refusal is the row's
    schema, not the fact set."""
    entry = next(e for e in state.entries if e.resource_name == "web_server_1_55555555")
    assert state_coverage.state_facts(entry) is None, state_coverage.state_facts(entry)


def test_a_stack_sub_block_keys_the_fact_it_names(state):
    """F6.10.5: `template_stack` is a fact, so a state entry the provider places inside a stack is
    keyed by its stack. The entry is built here, because no committed fixture holds a state entry of a
    type that declares the `template_stack` sub-block.
    """
    entry = state_input.StateEntry(
        "root", "panos_template_variable", "edge-tag", {"location": {"template_stack": {"name": "Edge-Stack"}}}
    )
    facts = state_coverage.state_facts(entry)
    assert facts == dict(NO_FACTS, template_stack="Edge-Stack"), facts
    key = state_coverage.ownership_key("panos_template_variable", "edge-tag", facts)
    assert key == ("panos_template_variable", "edge-tag", "", "", "", "", "Edge-Stack"), key


def test_the_first_entry_for_a_key_wins_in_document_order(state):
    """AC-2.3: one run entry is one finding, so the first state entry that carries the key wins."""
    index = state_coverage.state_index(state)
    key = ("panos_address", OWNED_NAME, "", "", "", "", "")
    assert index[key].resource_name == "web_server_1_11f477f4", index[key]
    same_key = [
        e
        for e in state.entries
        if e.entry_name == OWNED_NAME
        and e.resource_type == "panos_address"
        and state_coverage.state_facts(e) == NO_FACTS
    ]
    assert len(same_key) == 2, "the fixture holds two entries that carry the same key"
    assert index[key] is same_key[0], "the first one in document order wins"


def test_the_scan_scope_is_the_f4_4_rule_on_both_sides(state):
    """AC-2.4: a state resource whose type has no matrix row is not in the index, and a run entry
    no matrix row covers is not a finding."""
    index = state_coverage.state_index(state)
    assert not any(key[0] == "panos_schedule" for key in index), index

    # `regions.xml` holds the name the state document holds, under a count-only container row.
    region_ledger = entry_coverage.EntryLedger(parse_xml(FIXTURES_DIR / REGION_FIXTURE))
    row = next(r for r in region_ledger.rows() if r["name"] == "North-America")
    assert row["destination"] == "count-only", row
    assert entry_coverage.matrix_row_for(row["container"]) is None, row
    assert state_coverage.state_findings(region_ledger, state) == [], "the run side is not covered"


def test_a_run_with_no_declared_state_reports_nothing(converter_module, tmp_path):
    """AC-2.5: no state source, no state to read, no ownership fact and no drift fact."""
    out = tmp_path / "out"
    parser = run_pipeline(converter_module, RUN_FIXTURE, out)
    assert state_coverage.state_findings(parser.ledger, None) == []
    report = _report(out)
    assert state_coverage.OWNERSHIP_HEADING not in report, report
    assert state_coverage.DRIFT_HEADING not in report, report


# --- 3. The drift fact -------------------------------------------------------


def test_only_a_declared_property_both_sides_hold_is_compared(converter_module, tmp_path):
    """AC-3.1 and AC-3.2: a property the row does not declare is not compared, and a property one side
    does not hold is not compared. The state side is read under the name `STATE_PROPERTY_NAMES` gives
    the key, which for these properties is the name both sides hold."""
    findings = _findings(
        converter_module,
        RUN_FIXTURE,
        tmp_path / "out",
        state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE),
    )
    drifted = {finding["name"]: finding["drift"] for finding in findings}
    assert drifted[OWNED_NAME] == (
        ("description", "description", "Web server", "Web tier"),
        ("type", "type", "ip-netmask", "address"),
    ), drifted
    # The state holds `description` for Web-Range; the run side holds none for that entry.
    assert drifted["Web-Range"] == (), drifted
    # `tag` and `uuid` are state attributes the matrix row for `panos_address` does not declare.
    keys = {key for finding in findings for key, _, _, _ in finding["drift"]}
    assert "tag" not in keys and "uuid" not in keys, keys


def test_member_order_is_part_of_the_value(converter_module, tmp_path):
    """AC-3.3: the same members in a different order is a drift finding."""
    state = state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)
    findings = _findings(converter_module, SERVICE_FIXTURE, tmp_path / "out", state)
    finding = next(f for f in findings if f["name"] == ORDER_NAME)
    assert finding["drift"] == (("members", "members", ["service-http", "TCP-8080"], ["TCP-8080", "service-http"]),), (
        finding["drift"]
    )


def test_a_drift_fact_needs_an_ownership_fact(converter_module, tmp_path):
    """AC-3.4: an entry the state does not own cannot drift, so the drift section is a subset of
    the ownership section: every drift line is an ownership line with the values added."""
    out = tmp_path / "out"
    state = state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)
    findings = _findings(converter_module, RUN_FIXTURE, out, state)
    drifting = [f for f in findings if f["drift"]]
    assert drifting, findings
    assert {f["name"] for f in drifting} < {f["name"] for f in findings}, findings
    report = _report(out)
    ownership = _section(report, state_coverage.OWNERSHIP_HEADING)
    for finding in drifting:
        prefix = state_coverage.ownership_line(finding)
        assert prefix in ownership, ownership
        assert state_coverage.drift_line(finding) in _section(report, state_coverage.DRIFT_HEADING)
        assert len(state_coverage.drift_line(finding).splitlines()) == 1


# --- 4. The report sections and the exit code --------------------------------


def test_the_two_sections_print_after_the_property_section(converter_module, tmp_path):
    """AC-4.1: ownership, then drift, both after the property section, and each prints only when
    it has a finding."""
    out = tmp_path / "out"
    run_pipeline(converter_module, RUN_FIXTURE, out, _state_args())
    report = _report(out)
    assert (
        report.index(entry_coverage.PROPERTY_HEADING)
        < report.index(state_coverage.OWNERSHIP_HEADING)
        < report.index(state_coverage.DRIFT_HEADING)
        < report.index(FOOTER)
    ), report
    assert report.count(state_coverage.OWNERSHIP_HEADING) == 1, report
    assert report.count(state_coverage.DRIFT_HEADING) == 1, report


def test_the_ownership_line_shape_is_fixed(converter_module, tmp_path):
    """AC-4.2: line, object type, name, matrix row, state source, resource address."""
    out = tmp_path / "out"
    state = state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)
    findings = _findings(converter_module, RUN_FIXTURE, out, state)
    finding = next(f for f in findings if f["name"] == OWNED_NAME)
    name = f"{finding['container']}/{finding['name']}"
    expected = (
        f"  line {OWNED_LINE:>4}  "
        + f"{name:<38} "
        + f"{finding['resource']:<32} "
        + f"state source: {STATE_FIXTURE} ({finding['state_address']})"
    )
    assert state_coverage.ownership_line(finding) == expected, state_coverage.ownership_line(finding)
    report = _report(out)
    assert expected in _section(report, state_coverage.OWNERSHIP_HEADING), report
    # The section names the source by its report value, never by its path (F4.2 rule 6).
    assert "/" not in STATE_FIXTURE, STATE_FIXTURE
    assert str(FIXTURES_DIR) not in _section(report, state_coverage.OWNERSHIP_HEADING), report


def test_the_drift_line_shape_is_fixed(converter_module, tmp_path):
    """AC-4.2: the ownership shape, then the properties in sorted order, values as JSON text so
    one finding stays on one line."""
    out = tmp_path / "out"
    findings = _findings(
        converter_module, RUN_FIXTURE, out, state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)
    )
    finding = next(f for f in findings if f["drift"])
    expected = (
        state_coverage.ownership_line(finding)
        + '  value differs: description ("Web server" vs "Web tier"), '
        + 'type ("ip-netmask" vs "address")'
    )
    assert state_coverage.drift_line(finding) == expected, state_coverage.drift_line(finding)
    assert expected in _section(_report(out), state_coverage.DRIFT_HEADING)
    assert len(expected.splitlines()) == 1, "one finding stays on one line"


def test_the_lines_are_grouped_by_the_f3_9_scope_rule(converter_module, tmp_path):
    """AC-4.3: the same grouping function the other report sections use."""
    out = tmp_path / "out"
    state = state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)
    findings = _findings(converter_module, RUN_FIXTURE, out, state)
    generator = converter_module.TerraformGenerator(str(out), {})
    header = generator._report_section_header(generator._report_scope_path(findings[0]))
    assert header == "SHARED SECTION", header
    report = _report(out)
    assert header in _section(report, state_coverage.OWNERSHIP_HEADING), report
    assert header in _section(report, state_coverage.DRIFT_HEADING), report
    assert header in report[report.index(FOOTER) :], report


def test_the_console_prints_no_state_line_and_the_exit_code_is_unchanged(converter_module, tmp_path):
    """AC-4.4: a state fact is an operator action, so the F4.1 gate still decides the exit code,
    and the console prints no state line."""
    out = tmp_path / "out"
    saved_argv = list(sys.argv)
    sys.argv = ["panorama_to_terraform.py", str(FIXTURES_DIR / RUN_FIXTURE), "--output-dir", str(out), *_state_args()]
    try:
        with contextlib.redirect_stdout(io.StringIO()) as console:
            code = converter_module.main()
    finally:
        sys.argv = saved_argv
    assert code == 0, "a state fact does not change the exit code (AC-4.4)"
    value = console.getvalue()
    assert "state source" not in value and "value differs" not in value, value
    assert not hasattr(state_coverage, "console_line"), "the state scan owns no console wording"
    report = _report(out)
    assert state_coverage.OWNERSHIP_HEADING in report, report
    assert state_coverage.DRIFT_HEADING in report, report


# --- 5. The state scan is not an output --------------------------------------


def test_the_state_scan_read_does_not_count_as_a_property_read(converter_module, tmp_path):
    """AC-3.5: the state scan is not an output, so it reads through `RecordingDict.value` and the
    property section is unchanged by it."""
    before_out = tmp_path / "without_state"
    after_out = tmp_path / "with_state"
    without = run_pipeline(converter_module, RUN_FIXTURE, before_out)
    before = sorted(entry_coverage.property_line(row) for row in without.ledger.property_findings())
    before_rows = sorted((row["name"], row["fields"]) for row in without.ledger.rows())
    with_state = run_pipeline(converter_module, RUN_FIXTURE, after_out, _state_args())
    after = sorted(entry_coverage.property_line(row) for row in with_state.ledger.property_findings())
    after_rows = sorted((row["name"], row["fields"]) for row in with_state.ledger.rows())
    assert before == after, (before, after)
    assert before_rows == after_rows, (before_rows, after_rows)
    for line in _section(_report(before_out), entry_coverage.PROPERTY_HEADING).splitlines():
        assert line in _report(after_out), line


# --- 6. Determinism and the record -------------------------------------------


def test_two_runs_on_the_same_bytes_write_the_same_bytes(converter_module, tmp_path):
    """AC-8: the index keeps the first entry for a key in document order and the findings are
    sorted by line, then object type, then name, so two runs write the same bytes."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    run_pipeline(converter_module, RUN_FIXTURE, first, _state_args())
    run_pipeline(converter_module, RUN_FIXTURE, second, _state_args())
    # F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): the layout is the root set plus one directory per unit,
    # so two runs are compared on the whole shape they wrote, keyed by path.
    assert written_bytes(first) == written_bytes(second)
    lines = [
        line
        for line in _section(_report(first), state_coverage.OWNERSHIP_HEADING).splitlines()
        if line.startswith("  line")
    ]
    assert lines == sorted(lines), lines
    assert len(lines) == 2, lines


def test_the_state_record_reads_back_with_no_new_field(converter_module, tmp_path):
    """AC-6.1, AC-6.3 and AC-6.4: one record per source read, in read order, and the byte facts
    name the file a reader can reopen."""
    out = tmp_path / "out"
    assert run_main(converter_module, [str(FIXTURES_DIR / RUN_FIXTURE), "--output-dir", str(out), *_state_args()]) == 0
    records = provenance.parse_records((out / provenance.PROVENANCE_FILE).read_text(encoding="utf-8"))
    assert [record.kind for record in records] == ["file", "state"], records
    state_record = records[1]
    assert state_record.name == STATE_FIXTURE, state_record
    assert state_record.path == str(FIXTURES_DIR / STATE_FIXTURE), state_record
    assert state_record.scope == WORKSPACE, state_record
    assert state_record.size == (FIXTURES_DIR / STATE_FIXTURE).stat().st_size, state_record
    assert provenance.cache_reference(state_record) is None, "the state record references nothing"


# --- 7. The comparison table -------------------------------------------------

# The pair the committed fixtures hold on both sides: the run side is the address group entry the matrix
# row's own fixture names, the state side is the same entry in the state document, read under the name
# the pinned schema declares.
GROUP_TYPE = "panos_address_group"
GROUP_ENTRY = "Web-Servers"
MAPPED_KEY = "static_members"
MAPPED_STATE_NAME = "static"
GROUP_ADDRESS = "panos_address_group.web_servers_group_c3c3c3c3"

# Measured 2026-11-21, read through the measurement helper below: the matrix rows it reads, the types it
# reached a pair for, the rows that reached no field, and the table rows, which are the pairs where the two
# names differ. Measured on the 16 rows that reach no field: 10 print none of their properties at the block's
# own level, 4 print one there as a reference, a nested object, or a number text rather than as the same data
# the parse key holds, and 2 hold no report entry in the run, so nothing pairs with them.
MEASURED_ROWS = 42
MEASURED_TYPES_WITH_PAIRS = 26
MEASURED_ROWS_REACHING_NO_FIELD = 16
MEASURED_TYPES_WITH_DIFFERING_PAIRS = 2
MEASURED_TABLE_ROWS = 4


def _field_as_data(block, name: str):
    """One printed field as data, read through the gate's one field reader.

    A field whose value is a nested block is not data the scan compares: `state_properties` reads a
    nested block as an object, so a parse key that holds one value cannot be compared with it.
    """
    raw = block.fields()[name]
    if raw.startswith("["):
        return tuple(import_blocks.block_list(block, name))
    if raw.startswith('"'):
        return import_blocks.block_value(block, name)
    return None


def _measured_pairs(converter_module, out, provider_schema) -> tuple:
    """The pairs the measurement reads, per matrix row: the parse key, and the names the run printed.

    A pair is kept when the printed name is an attribute the pinned schema declares at the block's top
    level for the row's type, when the printed value is the data the parse key holds, and when one
    printed field answers for exactly one parse key. An empty value is not a property (F4.3 rule 3), so a
    field that reads as nothing pairs with nothing. `reached` names the rows with no field read at the
    block's own level. The measurement is what the table states, so a pin that reads it cannot pass by
    naming a pair a person picked.
    """
    pairs, ambiguous, unreached = {}, [], []
    for row in sorted(resource_mapping.COVERAGE_MATRIX, key=lambda r: r["resource"]):
        run_out = out / row["fixture"]
        parser = run_pipeline(converter_module, row["fixture"], run_out)
        assert parser is not None, f"{row['fixture']}: the run refused the input"
        files = sanity_checks.read_tf_files(run_out)
        blocks = [b for b in sanity_checks.blocks(files, ("resource",)) if b.rtype == row["resource"]]
        attributes = set(provider_schema[row["resource"]].get("block", {}).get("attributes", {}))
        matrix_row = entry_coverage.MATRIX_BY_RESOURCE[row["resource"]]
        name_field = entry_coverage.name_field(row["resource"])
        hit = False
        for entry in parser.ledger.entries():
            if not parser.ledger.is_report_entry(entry):
                continue
            data = parser.ledger.row_for(entry)
            if entry_coverage.matrix_row_for(data["container"]) is not matrix_row:
                continue
            mark = parser.ledger.mark_for(entry)
            if mark is None:
                continue
            captured = mark["captured"]
            block = next((b for b in blocks if b.attribute(name_field) == data["name"]), None)
            if block is None:
                continue
            for name in block.fields():
                if name not in attributes:
                    continue
                value = _field_as_data(block, name)
                if value in entry_coverage.EMPTY_FIELD_VALUES:
                    continue
                holders = [
                    key
                    for key in row["properties"]
                    if key in captured
                    and key not in entry_coverage.NON_FIELD_KEYS
                    and (tuple(captured.value(key)) if isinstance(captured.value(key), list) else captured.value(key))
                    == value
                ]
                if not holders:
                    continue
                hit = True
                if len(holders) > 1:
                    ambiguous.append((row["resource"], name, sorted(holders)))
                    continue
                pairs.setdefault(row["resource"], {}).setdefault(holders[0], set()).add(name)
        if not hit:
            unreached.append(row["resource"])
    return pairs, ambiguous, sorted(unreached)


def test_the_table_rows_are_the_measured_pairs(converter_module, tmp_path, provider_schema):
    """Criterion 1: the table is the measured set, not a picked one. Measured 2026-11-21 over the 42 matrix
    rows against provider v2.0.14: 26 types reach a pair, no printed field answers for more than one
    parse key, 16 rows reach no field at the block's own level, and four pairs name the parse key and a
    different attribute name, which are the four table rows. The pin skips only when the terraform binary
    is absent, the rule `tests/conftest.py` states."""
    pairs, ambiguous, unreached = _measured_pairs(converter_module, tmp_path, provider_schema)
    assert len(pairs) == MEASURED_TYPES_WITH_PAIRS, pairs
    assert len(unreached) == MEASURED_ROWS_REACHING_NO_FIELD, unreached
    assert ambiguous == [], ambiguous
    differing = {}
    for resource, row in pairs.items():
        for key, names in sorted(row.items()):
            if len(names) == 1 and key != next(iter(names)):
                differing.setdefault(resource, {})[key] = next(iter(names))
    assert differing, "the measurement reached pairs, so the pin measures content"
    assert sum(len(row) for row in differing.values()) == MEASURED_TABLE_ROWS, differing
    assert len(differing) == MEASURED_TYPES_WITH_DIFFERING_PAIRS, differing
    assert differing == state_coverage.STATE_PROPERTY_NAMES, (pairs, state_coverage.STATE_PROPERTY_NAMES)
    for resource, row in state_coverage.STATE_PROPERTY_NAMES.items():
        for key, name in row.items():
            assert key in entry_coverage.MATRIX_BY_RESOURCE[resource]["properties"], (resource, key)
            assert name in provider_schema[resource].get("block", {}).get("attributes", {}), (resource, name)
            assert key != name, "a row exists only where the two names differ"


def test_a_parse_key_the_run_prints_under_four_names_has_no_row(converter_module, tmp_path, provider_schema):
    """Criterion 1: `value` for `panos_address` is one parse key the run prints under four names, one per
    declared type, so no single name is the answer and the table has no row for it. Measured on
    `tests/fixtures/address_objects.xml`: the four names are `fqdn`, `ip_netmask`, `ip_range` and
    `ip_wildcard`, each an attribute the pinned schema declares at the block's top level."""
    pairs, _, _ = _measured_pairs(converter_module, tmp_path, provider_schema)
    names = sorted(pairs["panos_address"]["value"])
    assert names == ["fqdn", "ip_netmask", "ip_range", "ip_wildcard"], names
    assert "panos_address" not in state_coverage.STATE_PROPERTY_NAMES, state_coverage.STATE_PROPERTY_NAMES
    assert state_coverage.state_name_for("panos_address", "value") == "value", "no row, so the same-name rule stands"


def test_a_mapped_pair_is_compared_and_the_finding_names_both_names(converter_module, tmp_path):
    """Criterion 3: the pair the table maps is compared, and the finding names both sides. The state
    document holds the member list under `static`, the name the pinned schema declares for
    `panos_address_group`, and the run side reads that entry's members under the parse key
    `static_members`. The two values differ, and under the same-name rule the scan would read no state
    attribute for that entry, so the finding exists only because of the table.
    """
    state = state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)
    entry = _entry(state, GROUP_ENTRY, GROUP_TYPE)
    properties = state_coverage.state_properties(entry)
    assert "static" in properties and "static_members" not in properties, properties
    findings = _findings(converter_module, GROUP_FIXTURE, tmp_path / "out", state)
    finding = next(f for f in findings if f["name"] == GROUP_ENTRY)
    assert state_coverage.state_name_for(GROUP_TYPE, MAPPED_KEY) == MAPPED_STATE_NAME, GROUP_TYPE
    assert finding["drift"] == ((MAPPED_KEY, MAPPED_STATE_NAME, ["Web-Server-1", "Web-Server-2"], ["Web-Server-1"]),), (
        finding["drift"]
    )
    assert finding["state_address"] == GROUP_ADDRESS, finding


def test_the_same_name_rule_stands_where_the_table_has_no_row(converter_module, tmp_path):
    """Criterion 2: a property the table has no row for is compared by the name both sides hold,
    unchanged, and the table holds no row for a pair whose two names are the same."""
    assert state_coverage.state_name_for("panos_service_group", "members") == "members", "no row, so the name stands"
    for row in state_coverage.STATE_PROPERTY_NAMES.values():
        assert all(key != name for key, name in row.items()), row

    state = state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)
    findings = _findings(converter_module, SERVICE_FIXTURE, tmp_path / "out", state)
    finding = next(f for f in findings if f["name"] == ORDER_NAME)
    key, name, _, _ = finding["drift"][0]
    assert key == name == "members", finding["drift"]
    assert "  value differs: members (" in state_coverage.drift_line(finding), state_coverage.drift_line(finding)


def test_no_module_holds_a_second_mapping_from_a_parse_key_to_an_attribute_name(provider_schema):
    """Criterion 2: the table is the only mapping the scan reads. Measured across the `src/` set: the
    only module-level dict that pairs a parse key with a provider attribute name the row does not name it
    under is the table, and the drift scan resolves the state name through `state_name_for`, the one
    lookup. A parse key that needs a mapping is one the row declares and the schema has no attribute of
    the same name for, so a dict that pairs it with a different attribute name is a mapping rule.
    """
    rows = {row["resource"]: row for row in resource_mapping.COVERAGE_MATRIX}
    attributes = {
        resource: set(block.get("block", {}).get("attributes", {})) for resource, block in provider_schema.items()
    }

    def entry_is_mapping(resource, key, value):
        """A dict entry that pairs a parse key with an attribute name it is not named under."""
        if resource not in rows or key not in rows[resource]["properties"]:
            return False
        return key != value and key not in attributes[resource] and value in attributes[resource]

    hits = []
    for path in sorted(SRC_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
                continue
            target = getattr(node.targets[0], "id", "?")
            for key, value in zip(node.value.keys, node.value.values, strict=True):
                if isinstance(value, ast.Dict):
                    # A mapping table keyed by resource type, the shape the table is.
                    if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                        continue
                    for inner_key, inner_value in zip(value.keys, value.values, strict=True):
                        if (
                            isinstance(inner_key, ast.Constant)
                            and isinstance(inner_value, ast.Constant)
                            and isinstance(inner_key.value, str)
                            and isinstance(inner_value.value, str)
                            and entry_is_mapping(key.value, inner_key.value, inner_value.value)
                        ):
                            hits.append((path.name, target, key.value, inner_key.value, inner_value.value))
                elif isinstance(key, ast.Constant) and isinstance(value, ast.Constant):
                    if isinstance(key.value, str) and isinstance(value.value, str):
                        for resource in rows:
                            if entry_is_mapping(resource, key.value, value.value):
                                hits.append((path.name, target, resource, key.value, value.value))
                                break
    assert hits, "the scan finds no mapping anywhere, so the pin is not measuring the table"
    assert all(hit[0] == "state_coverage.py" and hit[1] == "STATE_PROPERTY_NAMES" for hit in hits), hits
    table = sorted(
        (resource, key, name)
        for resource, row in state_coverage.STATE_PROPERTY_NAMES.items()
        for key, name in row.items()
    )
    assert sorted(hit[2:] for hit in hits) == table, hits
    source = inspect.getsource(state_coverage.drift_properties)
    assert "state_name_for" in source, "the scan reads the mapping through the one lookup"


def test_a_mapped_pair_prints_both_names_in_the_drift_line(converter_module, tmp_path):
    """Criterion 5: the line keeps its shape and names both sides of a mapped pair, so the operator
    can see the two names the finding compared."""
    out = tmp_path / "out"
    state = state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)
    findings = _findings(converter_module, GROUP_FIXTURE, out, state)
    finding = next(f for f in findings if f["name"] == GROUP_ENTRY)
    expected = (
        state_coverage.ownership_line(finding)
        + "  value differs: static_members as static "
        + '(["Web-Server-1", "Web-Server-2"] vs ["Web-Server-1"])'
    )
    assert state_coverage.drift_line(finding) == expected, state_coverage.drift_line(finding)
    assert expected in _section(_report(out), state_coverage.DRIFT_HEADING), _report(out)
    assert len(expected.splitlines()) == 1, "one finding stays on one line"


# --- 8. The existing codebase records as a reference source -------------------


def test_the_reference_source_is_read_as_data_through_the_readers_the_shape_owners_state(tmp_path):
    """§4 rule 1: an update run reads the records the codebase already holds as data, through the reader each shape
    owner states, and `state_coverage` gains no reader, path rule, shape or unit rule of its own. Each record is
    read through its own module's `parse_rows` and the sets are combined only through `codebase_state.merge_rows`,
    so the read is the same data read the gate already makes and no container table, parent walk, expat line map or
    second key appears in it.

    Measured 2026-11-22 on the committed pair through `tests/conftest.py`: the kitchen-sink run is the codebase and
    `address_objects.xml` is the second run, so the read answers 11, 61, 9 and 3 rows through `parse_rows` and the
    merge answers 11, 62, 9 and 3. Read through `ast`, `state_coverage.py` defines no reader, writer, path rule, row
    shape or unit rule of its own, so the entry point is the only reader and it reads through the owners.
    """
    codebase_dir, partial_dir, _second = partial_run(CODEBASE_FIXTURE, RUN_FIXTURE, tmp_path)
    held = record_rows(codebase_dir)
    built = record_rows(partial_dir)
    merged = {module: codebase_state.merge_rows(JOIN_RECORDS[module], held[module], built[module]) for module in held}
    assert {module.__name__: len(merged[module]) for module in merged} == {
        "unit_manifest": 11,
        "ownership": 62,
        "reference_edges": 9,
        "site_data": 3,
    }, merged

    tree = ast.parse(Path(state_coverage.__file__).read_text(encoding="utf-8"))
    defined = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    defined |= {
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    for name in (
        "units",
        "facts_of",
        "row_key",
        "parse_rows",
        "render",
        "read_text",
        "write_file",
        "root_path",
        "unit_path",
    ):
        assert name not in defined, (name, "the module reads this rule through its owner")
    assert "ownership_key" in defined and "STATE_PROPERTY_NAMES" in defined, (
        "the reference read reaches the module through the two rules it states",
    )


def test_the_reference_read_reaches_the_ownership_half_and_no_property_value(tmp_path):
    """§4 rule 1, the half the read reaches: `ownership_key` answers for a row read back from the record as it does
    for a state entry, so the reference read reaches the ownership half of the scan. The comparison half cannot be
    answered from the record, because `ownership.FIELD_ORDER` holds no field the comparison table names, so a merged
    row carries no property value and the value side comes only from the state read the door makes. The finding half
    stays on the rows the run built, because `ownership.findings` reads `line`, `container` and `reason`, which
    `parse_rows` does not read back.

    Measured 2026-11-22 on the committed pair through `tests/conftest.py`: for the pair both sides hold
    (`panos_address_group`, `Web-Servers`), the key rule answers the same key for the state entry and for the merged
    row, the table row for that type is one pair, and no field of that pair is a field of the ownership row.
    """
    codebase_dir, partial_dir, _second = partial_run(CODEBASE_FIXTURE, RUN_FIXTURE, tmp_path)
    held = record_rows(codebase_dir)
    built = record_rows(partial_dir)
    merged = codebase_state.merge_rows(JOIN_RECORDS[ownership], held[ownership], built[ownership])
    row = next(row for row in merged if row["type"] == GROUP_TYPE and row["entry"] == GROUP_ENTRY)
    state = state_input.read_state(FIXTURES_DIR / STATE_FIXTURE, workspace=WORKSPACE)
    entry = _entry(state, GROUP_ENTRY, GROUP_TYPE)

    assert state_coverage.ownership_key(entry.resource_type, entry.entry_name, state_coverage.state_facts(entry)) == (
        codebase_state.join_key(JOIN_RECORDS[ownership], row)
    ), "the one key rule reaches a row read from the record as it reaches a state entry"
    names = state_coverage.STATE_PROPERTY_NAMES[row["type"]]
    assert names == {MAPPED_KEY: MAPPED_STATE_NAME}, names
    assert [field for field in ownership.FIELD_ORDER if field in names] == [], (
        "the record row shape holds no property field, so the reference read supplies no value to compare"
    )
    assert MAPPED_KEY not in row, row


# --- 9. The device serial fact for a bound unit (decision 6, `docs/IMPORT_BINDING.md` §2, taken 2026-11-26) ---

# The committed state entry that names the serial, and the value it names. The pin names the variable through the
# naming rule, reads the sub-block through `LOCATION_SCHEMA` and the fact through `STATE_SCOPE_KEYS`, and states no
# name list of its own. The content a finding needs is written through `tests/conftest.py`, because the committed
# corpus holds no state entry that needs a serial inside a unit a declaration can mark, so no committed byte moves.
SERIAL_ADDRESS = "panos_address.web_range_33333333"
SERIAL_VALUE = "firewall-2"
SERIAL_VARIABLE = naming.variable_name(SERIAL_VALUE)
SHARED_ADDRESS = "panos_address.web_range_a1b2c3d4"


def _state_entry(state: state_input.StateSource, address: str) -> state_input.StateEntry:
    """One committed state entry, read through the producer."""
    return next(entry for entry in state.entries if entry.address == address)


def test_the_serial_is_read_through_the_entry_shape_and_the_one_name(state):
    """Decision 6 answer 1: the serial for a state entry is the value the document holds for it, read through the
    entry shape and rule 2's location walk, and the module names it once.

    Measured 2026-11-27 on the committed state document: `SERIAL_ADDRESS` is the entry that names the field, so the
    pin measures the fact as content on committed material. The sub-block is read through `LOCATION_SCHEMA` and the
    fact through `STATE_SCOPE_KEYS`, so the pin states no name list. An entry the document places in `shared` sits
    in no sub-block that declares the field, so it needs no serial, and the property scan reads no property for the
    field, because the location is identity and not content (F4.3 rule 3).
    """
    entry = _state_entry(state, SERIAL_ADDRESS)
    row = resource_mapping.LOCATION_SCHEMA[entry.resource_type]
    blocks = [block for block, fields in row.items() if state_coverage.STATE_SERIAL_KEY in fields]
    assert blocks, "the pin reads a row that declares no sub-block for the field"
    # The sub-block fills its own fact through `STATE_SCOPE_KEYS`; the field fills the fact the module names once,
    # so the table holds no row for the serial and the pin states no name of its own.
    assert state_coverage.STATE_SCOPE_KEYS[blocks[0]] == blocks[0]
    assert "serial" not in state_coverage.STATE_SCOPE_KEYS, state_coverage.STATE_SCOPE_KEYS
    assert state_coverage.entry_needs_serial(entry)
    assert state_coverage.serial_of(state_coverage.state_facts(entry)) == SERIAL_VALUE
    assert state_coverage.STATE_SERIAL_KEY not in state_coverage.state_properties(entry)
    assert not state_coverage.entry_needs_serial(_state_entry(state, SHARED_ADDRESS))
    assert "serial" not in state_coverage.STATE_IDENTITY_KEYS, state_coverage.STATE_IDENTITY_KEYS
    assert "serial" not in resource_mapping.VALUE_VARIABLES, "the piece added no row to the shape table"
    assert resource_mapping.VALUE_VARIABLES[state_coverage.STATE_SERIAL_KEY] == resource_mapping.VARIABLE


def test_the_block_and_the_id_state_the_same_fact_through_the_shape_table(state, converter_module, tmp_path):
    """Decision 6 answer 2: the block prints the shape the table states for the name, the id states the value the run
    read, and the gate reads the two as one fact, so the pair is one fact read through `VALUE_VARIABLES`,
    `site_data.record_pair`, `decode_id` and `sanity_checks.check_import_blocks`.

    Measured 2026-11-27 on the committed state entry that names the serial, printed through the print site the table
    governs: the block prints the §5 name of the value, the id holds the value inside the location the entry sits in,
    the pair is recorded through the owner, and the gate answers nothing for the pair. The same fact printed as a
    literal is a finding through the same gate rule, so `location_agrees` gained no branch of its own.
    """
    entry = _state_entry(state, SERIAL_ADDRESS)
    facts = state_coverage.state_facts(entry)
    local = SERIAL_ADDRESS.split(".", 1)[1]
    generator = converter_module.TerraformGenerator(str(tmp_path), {})
    obj = dict(facts)
    obj["name"] = entry.entry_name
    data = generator.location_data(entry.resource_type, obj)
    block = generator.location_block(entry.resource_type, obj, local)
    shape = import_blocks.row("unit_a_11111111", entry.resource_type, local, entry.entry_name, data)
    text = f'resource "{entry.resource_type}" "{local}" {{\n{block}\n  name = "{entry.entry_name}"\n}}\n'
    assert naming.variable_text(SERIAL_VARIABLE) in block, block
    assert generator.printed_value(state_coverage.STATE_SERIAL_KEY, SERIAL_VALUE, unit_manifest.facts_of(obj)) == (
        naming.variable_text(SERIAL_VARIABLE)
    )
    assert generator.value_variables()[unit_manifest.facts_of(obj)] == {SERIAL_VARIABLE: SERIAL_VALUE}
    decoded = import_blocks.decode_id(shape["import_id"])
    assert decoded["name"] == entry.entry_name
    assert decoded["location"] == data, "the id encodes the same location the block states"
    row = resource_mapping.LOCATION_SCHEMA[entry.resource_type]
    sub = next(block for block, fields in row.items() if state_coverage.STATE_SERIAL_KEY in fields)
    assert decoded["location"][sub][state_coverage.STATE_SERIAL_KEY] == SERIAL_VALUE
    assert sanity_checks.check_import_blocks({"a.tf": text + import_blocks.render([shape])}) == []
    literal = text.replace(naming.variable_text(SERIAL_VARIABLE), f'"{SERIAL_VALUE}"') + import_blocks.render([shape])
    assert sanity_checks.check_import_blocks({"a.tf": literal}), "a block that prints the literal is a finding"


def test_a_run_that_reads_no_state_document_declares_no_serial_and_writes_the_bytes_it_writes_today(
    converter_module, tmp_path
):
    """Decision 6 answer 3: a run that reads no state document reads no entry, so it holds no value for the serial,
    the declaration set holds no name for it, and the ids for entries that need one hold no serial.

    Measured 2026-11-27 on `RUN_FIXTURE`: the run with no state source and the same run with the committed state
    document write the same `.tf` bytes, because the state document is read as a reference source and prints nothing.
    The declared run on the pair content writes ids that hold no value for the fact, and its declaration set holds no
    name named by the value the state document holds for the entry it read.
    """
    plain = tmp_path / "plain"
    with_state = tmp_path / "with_state"
    assert run_main(converter_module, [str(FIXTURES_DIR / RUN_FIXTURE), "--output-dir", str(plain)]) == 0
    state_argv = [str(FIXTURES_DIR / RUN_FIXTURE), "--output-dir", str(with_state), *_state_args()]
    code = run_main(converter_module, state_argv)
    assert code == 0, code
    assert tf_bytes(plain) == tf_bytes(with_state), (sorted(tf_bytes(with_state)), sorted(tf_bytes(plain)))
    assert tf_bytes(plain), "the pins read a run that wrote output"
    names = {name for row in record_rows(plain)[site_data] for name in row["variables"]}
    assert SERIAL_VARIABLE not in names, names
    _source, _pair_plain, _pair_state_only, pair_declared, _pairs, _document = serial_run(
        converter_module, tmp_path / "pair"
    )
    files = {
        str(path.relative_to(pair_declared)): path.read_text(encoding="utf-8")
        for path in sorted(Path(pair_declared).rglob("*.tf"))
    }
    written = sanity_checks.blocks(files, ("import",))
    assert written, "the declared run wrote an import block for the entry that needs the fact"
    for block in written:
        decoded = import_blocks.decode_id(import_blocks.block_value(block, "id"))
        for fields in decoded["location"].values():
            assert fields.get(state_coverage.STATE_SERIAL_KEY, "") != SERIAL_VALUE, (block.file, decoded)
    declared_names = {name for row in record_rows(pair_declared)[site_data] for name in row["variables"]}
    assert SERIAL_VARIABLE not in declared_names, declared_names


def test_a_bound_unit_with_an_entry_that_needs_a_serial_and_has_none_reports_one_line(converter_module, tmp_path):
    """Rule 7, decision 6 answer 4: one line per entry that needs a serial and has none, inside its own section, with
    the entry named through `ownership_key`, the bound answer read through `unit_manifest.mode_of`, and the group
    read through the F3.9 rule.

    Measured 2026-11-27 on the content `tests/conftest.py::serial_content` writes, because the committed corpus holds
    no state entry that needs a serial inside a unit a declaration can mark: the export places the entry inside
    `Vsys1` in `Production-DG`, the state document holds the same entry with no value for the field, and the
    declaration names the unit the run's own rows show. The section holds one line, and the group header names the
    device group the F3.9 rule reads for the entry.
    """
    _source, _plain, _state_only, declared, _pairs, document = serial_run(converter_module, tmp_path)
    marked = unit_manifest.marked_units(record_rows(declared)[unit_manifest])
    assert marked, "the pins read a run that marked a unit"
    state = state_input.read_state(document, workspace=WORKSPACE)
    findings = state_coverage.serial_findings(state, marked)
    assert len(findings) == 1, findings
    finding = findings[0]
    facts = {key: finding[key] for key in container_coverage.SCOPE_FACT_KEYS}
    key = state_coverage.ownership_key(finding["resource"], finding["name"], facts)
    assert key[0] == finding["resource"] and key[1] == SERIAL_ENTRY_NAME, key
    assert key[2:] == tuple(facts.values()), "the finding names the entry through the one key rule"
    assert key[2] == SERIAL_GROUP and key[3] == SERIAL_VSYS, key
    assert state_coverage.serial_of(facts) == "", "the document names no value for the field, which is the finding"
    entry = next(item for item in state.entries if item.address == finding["state_address"])
    assert state_coverage.entry_needs_serial(entry), entry
    assert unit_manifest.unit_name(unit_manifest.facts_of(finding)) == SERIAL_VSYS, finding
    assert unit_manifest.mode_of(finding) == MODE_VALUES[0], finding
    report = _report(declared)
    section = _section(report, state_coverage.SERIAL_HEADING)
    body = [line for line in section.splitlines() if "state source" in line]
    assert body == [state_coverage.serial_line(finding)], (section, body)
    generator = converter_module.TerraformGenerator(str(tmp_path / "gen"), {})
    header = generator._report_section_header(generator._report_scope_path(finding))
    assert header in section, section
    assert header == "DEVICE GROUP: Production-DG", header


def test_the_serial_finding_does_not_move_the_exit_code_and_prints_no_console_line(converter_module, tmp_path):
    """Rule 7, decision 6 answer 4, the half the gate decides: the fact names an operator action, so the F4.1 gate
    still decides the exit code, the gate rule reads nothing for it, and the console prints no line for it. The
    console shape has one owner, `container_coverage.console_line`, and the piece changed no kind list, so
    `tests/test_container_coverage.py::test_the_console_line_shape_is_stated_in_one_place` is unchanged.
    """
    source, _plain, _state_only, declared, pairs, document = serial_run(converter_module, tmp_path)
    saved_argv = list(sys.argv)
    sys.argv = [
        "panorama_to_terraform.py",
        str(source),
        "--output-dir",
        str(tmp_path / "console"),
        "--state",
        str(document),
        "--workspace",
        WORKSPACE,
        *declaration_args(pairs),
    ]
    try:
        with contextlib.redirect_stdout(io.StringIO()) as console:
            code = converter_module.main()
    finally:
        sys.argv = saved_argv
    assert code == 0, "the fact does not change the exit code"
    value = console.getvalue()
    # The console names the serial inside the file names it prints, so the pin reads the fact wording the line
    # shape would use, and the state position the shape has no room for: neither appears on a console line.
    assert "needs a serial" not in value, value
    assert "state source" not in value, value
    assert not hasattr(state_coverage, "console_line"), "the state scan owns no console wording"
    assert not hasattr(state_coverage, "CONSOLE_KINDS"), "the kind list has one owner"
    assert sanity_checks.run_checks(declared).fail_count == 0, sanity_checks.run_checks(declared)


def test_the_serial_fact_adds_no_source_kind_and_no_input_shape_row():
    """Decision 6 answer 1, the half the door states: the state document reaches the run through the door's one shape
    row for it and through the kind `state_input` states, so the piece added no source kind and no `SHAPE_TABLE` row,
    and the module states no reader of its own.

    Measured 2026-11-27 on the table: one row names the JSON state document shape, and no row names the serial or the
    field the serial reads by, so the fact reaches `state_coverage` through the door unchanged.
    """
    rows = [row for row in input_shapes.SHAPE_TABLE if "state document" in row["shape"]]
    assert len(rows) == 1, rows
    for row in input_shapes.SHAPE_TABLE:
        assert state_coverage.STATE_SERIAL_KEY not in row["shape"], (row, "a shape row that names the serial")
    assert state_input.STATE_KIND == "state", state_input.STATE_KIND
    assert not hasattr(state_coverage, "STATE_KIND"), "the module states no source kind of its own"
    assert not hasattr(state_coverage, "read_state"), "the module states no reader of its own"


def test_the_serial_fact_names_no_second_identity_key_and_no_new_fact_key():
    """Rule 7, the shape of the owner: the serial is read inside the location, which `STATE_IDENTITY_KEYS` already
    keeps out of the property set, `unit_manifest.FACT_KEYS` gains no key, and the finding reads the unit and the
    bound answer through `unit_manifest`, so `state_coverage.py` states no reader, no path rule, no row shape, no
    unit rule, no severity rule, no value of the pair, and no name list of its own.

    Measured 2026-11-27: `FACT_KEYS` is the set its owner states, read through that owner, and the module holds no
    second statement of the finding rule, the mode values, or the kind list.
    """
    assert frozenset({"name", "location"}) == state_coverage.STATE_IDENTITY_KEYS
    assert unit_manifest.FACT_KEYS == container_coverage.SCOPE_FACT_KEYS
    assert "serial" not in unit_manifest.FACT_KEYS, unit_manifest.FACT_KEYS
    assert state_coverage.STATE_SERIAL_FACT in unit_manifest.FACT_KEYS
    source_text = (SRC_DIR / "state_coverage.py").read_text(encoding="utf-8")
    for rule in (
        "def units",
        "def parse_rows",
        "def mode_of",
        "def marked_units",
        "def unit_name",
        "def read_state",
        "def sanitize_name",
        "def variable_name",
    ):
        assert rule not in source_text, f"state_coverage.py states a rule its owner defines ({rule})"
    for other in (unit_manifest, resource_mapping, entry_coverage, sanity_checks, site_data, naming, state_input):
        assert not hasattr(other, "SERIAL_RULE"), (other.__name__, "a second statement of the finding rule")
    assert not hasattr(state_coverage, "MODE_VALUES"), "the value is read through the pair's owner"
    assert state_coverage.STATE_SERIAL_KEY == "ngfw_device", "the field name is stated once in the owner"
