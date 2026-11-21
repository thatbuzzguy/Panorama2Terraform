"""F5.6 state coverage: the ownership fact and the drift fact.

Seven groups, one per acceptance rule:

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

Every test uses a committed fixture, so no test opens a connection. The run side is
`tests/fixtures/address_objects.xml`; the state side is `tests/fixtures/state_workspace.json`. The pins
in group 7 read the live provider schema through `tests/conftest.py`, which owns the skip rule.
"""

import ast
import contextlib
import inspect
import io
import sys

import pytest

import container_coverage
import entry_coverage
import import_blocks
import provenance
import resource_mapping
import sanity_checks
import state_coverage
import state_input
from conftest import FIXTURES_DIR, SRC_DIR, run_main, run_pipeline, written_bytes
from xml_input import parse_xml

STATE_FIXTURE = "state_workspace.json"
RUN_FIXTURE = "address_objects.xml"
SERVICE_FIXTURE = "service_groups.xml"
REGION_FIXTURE = "regions.xml"
GROUP_FIXTURE = "address_groups.xml"
WORKSPACE = "production"

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


# --- 5. Determinism and the record -------------------------------------------


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
# reached a pair for, the rows it cannot reach because their properties print inside a nested level or
# inside the `for_each` map, so `state_properties` never reads them as an attribute, and the table rows,
# which are the pairs where the two names differ.
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
    document holds the value under `static`, the name the pinned schema declares for
    `panos_address_group`, and the run side holds the same value under the parse key `static_members`, so
    under the same-name rule this entry compares nothing: the finding exists only because of the table.
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
