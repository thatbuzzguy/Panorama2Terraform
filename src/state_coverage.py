"""F5.6 state coverage: the ownership fact, the drift fact, and the device fact for a bound unit.

Seven rules, stated once here.

1. The state entry shape. A state entry is one instance object the producer read
   (`state_input.StateEntry`). Its matrix row is the row keyed by its resource type, through
   `entry_coverage.MATRIX_BY_RESOURCE`: the same table, the same key, no second naming rule. Its
   properties are the attribute keys it holds, read with the F4.3 rule (the entry name and the
   scope facts are identity, not content, and an empty value is not a property). A state entry has
   no source line, because only the expat handler path records one, so its position is its
   resource address.
2. The ownership key is §2.1 identity as the F3.9 rule reads it: the matrix row, the entry name,
   and the five declared scope facts (§2.2). `Shared` is the parse fallback, so the key uses the
   facts each source declares, never the fallback. The state declares its scope through its
   `location` block, through the block names `LOCATION_SCHEMA` declares. A nested block is read
   as an object, or as a one-element list of an object, because the provider writes a nested block
   either way. The `shared` block names the shared section, which states no name, so it fills no
   fact. A block the converter never emits (`template_stack`, `template_stack_vsys`,
   `template_vsys`) names a scope no run entry can sit in, so an entry placed there is not keyed.
3. The drift fact compares a property the matrix row declares, with values that are not equal. The
   state name for a property is `STATE_PROPERTY_NAMES`, the one mapping rule: measured per matrix row
   type against the pinned provider schema, and it holds a row only where the two names differ, so the
   same-name rule stands for a property the table has no row for. Only the pairs the measurement
   reached are in the table, so the scan compares nothing it did not read. A property one side does
   not hold is not compared. A value is compared as the two sides hold it, so member order is part of
   the value.
4. A drift fact needs an ownership fact, so the drift section is a subset of the ownership
   section. The scan scope is the F4.4 rule on both sides: an entry no matrix row covers is not a
   finding, and a state resource whose type has no matrix row is not in the index. A run with no
   declared state source has no state to read, so it reports neither fact.
5. The state scan is not an output, so it reads a captured value through the non-recording read
   (`entry_coverage.RecordingDict.value`), and the property section is unchanged by it. Report
   order is fixed: findings are sorted by line, then object type, then name. A finding is an
   operator action, not a broken output, so it does not change the exit code, which the F4.1 gate
   decides. The console prints no state line.
6. The existing codebase records are a reference source, read as data, so the read reaches this module
   as the two rules it states: `ownership_key` and `STATE_PROPERTY_NAMES`. The module states no reader,
   path rule, row shape or unit rule of its own, so the entry point reads each record through the module
   that owns its shape. The reference read reaches the ownership half, because `ownership_key` answers the
   same key for a state entry and for a row read back through `parse_rows`. The comparison half needs a
   value, and the ownership row shape holds no property field, so a comparison comes only from the state
   read the door makes, and the finding half reads `line`, `container` and `reason`, which `parse_rows`
   does not read back, so it stays on the rows the run built. Pinned by
   `tests/test_state_coverage.py::test_the_reference_source_is_read_as_data_through_the_readers_the_shape_owners_state`
   and
   `tests/test_state_coverage.py::test_the_reference_read_reaches_the_ownership_half_and_no_property_value`.

7. The device serial fact for a bound unit (decision 6 of `docs/IMPORT_BINDING.md` §2, taken 2026-11-26). The fact
   is the serial the state document declares for an entry, read through rule 2 (the location walk, the sub-block
   names `LOCATION_SCHEMA` declares), and named once here: `STATE_SERIAL_KEY` is the field the state document
   declares it with, and `STATE_SERIAL_FACT` is the §2.2 fact that field fills through `STATE_SCOPE_KEYS`, so no
   second name list and no new fact key appear. `serial_of` answers the value, or the empty answer for an entry
   that holds none. An entry needs the serial when the location it holds places it in a sub-block that declares the
   field, which `entry_needs_serial` answers through `LOCATION_SCHEMA`. The serial is read from the location, which
   `STATE_IDENTITY_KEYS` keeps out of the property set, so no drift line can compare it, and the shape table has
   no property row for it: `VALUE_VARIABLES` already states the field as a variable, so the block prints the
   reference and the id states the value through the same row. A run that reads no state document reads no entry,
   so it declares no serial, and the ids for entries that need one stay the placeholders the report already names
   for the operator. For a bound unit, an entry that needs the serial and has none is one finding, read through
   `ownership_key` so no second identity key appears, and the bound answer is read through `unit_manifest.mode_of`;
   this module states no unit rule, no mode value, no severity rule and no console line. Pinned by
   `tests/test_state_coverage.py` group 9.

Usage:
    from state_coverage import state_index, state_findings, ownership_line, drift_line, serial_findings, serial_line
    findings = state_findings(ledger, state_source)
    for finding in findings:
        print(ownership_line(finding))
    for finding in serial_findings(state_source, unit_manifest.marked_units(rows)):
        print(serial_line(finding))
"""

import json

import container_coverage
import entry_coverage
import unit_manifest
from resource_mapping import LOCATION_SCHEMA
from state_input import StateEntry, StateSource

OWNERSHIP_HEADING = "Entries Another Workspace Already Owns"
DRIFT_HEADING = "Owned Entries With a Value The Run Does Not Match"
SERIAL_HEADING = "Bound Entries That Need a Serial The State Document Names No Value For"

# Decision 6 (`docs/IMPORT_BINDING.md` §2, taken 2026-11-26): the serial, named once here. `STATE_SERIAL_KEY` is the
# field the state document declares it with, and `STATE_SERIAL_FACT` is the §2.2 fact that field fills through
# `STATE_SCOPE_KEYS`, so the pair is the one mapping rule this module already states, not a name list. The serial is
# read from the location, which `STATE_IDENTITY_KEYS` keeps out of the property set, so no drift line can compare
# it, and `unit_manifest.FACT_KEYS` gains no key: the serial is the value the `vsys_device` fact already holds.
STATE_SERIAL_KEY = "ngfw_device"
STATE_SERIAL_FACT = "vsys_device"

OWNERSHIP_RULE = (
    "An entry this run read that another workspace already owns is listed here. The state "
    "document names the workspace that holds the object, and the resource address names the "
    "entry in it. The key is the entry identity (device group, vsys, type, name), read from "
    "the location the state document holds, so an entry in a different scope is a different "
    "object and is not listed. A finding is an operator action, not a broken output: it does "
    "not change the exit code, which the F4.1 gate still decides."
)

DRIFT_RULE = (
    "An owned entry with a value this run does not match is listed here. Only a property the "
    "coverage matrix row declares is compared. The state name a property is read under comes from "
    "the comparison table; where the table holds no row for a property, the two sides are compared "
    "by the same name, and a property one side does not hold is not compared. A property the table "
    "maps prints both names. The values are printed as JSON text, so one finding stays on one line. "
    "A finding is an operator action, not a broken output, so it does not change the exit code, "
    "which the F4.1 gate still decides."
)

SERIAL_RULE = (
    "A bound entry that needs a serial and has none is listed here, in the unit this run marked. The state document "
    "names the serial for the entry it holds, and the export states a device as a hostname, so a value that names a "
    "physical unit reaches the run only from a state document read as a reference source. An entry needs the serial "
    "when the location the state document holds for it places it in a sub-block that declares the field, and the "
    "serial is not the entry's content, so no property line compares it. The entry is named by the identity key the "
    "ownership section reads it with. A finding is an operator action, not a broken output, so it does not change "
    "the exit code, which the F4.1 gate still decides, and it prints in the report only."
)

# Which §2.2 fact each `location` sub-block fills. The sub-block names and the field names
# come from `LOCATION_SCHEMA`, so this is the mapping, not a second naming rule; it is the
# same shape `entry_coverage.REPORT_SCOPE_KEYS` holds for containers. `shared` names the
# shared section, which states no name, so it fills no fact. A sub-block the table does not
# declare for the row (`template_stack_vsys`, `template_vsys`) names a scope this converter
# never emits, so an entry placed there is not keyed. `template_stack` is the fifth fact
# (F6.10.5), so an entry placed inside a stack is keyed by its stack
# (`tests/test_state_coverage.py::test_a_stack_sub_block_keys_the_fact_it_names`). The `ngfw` row fills the serial
# fact for the field `STATE_SERIAL_KEY` names, the name rule 7 states once.
STATE_SCOPE_KEYS = {
    "device_group": "device_group",
    "vsys": "vsys",
    "template": "template",
    "ngfw": STATE_SERIAL_FACT,
    "template_stack": "template_stack",
    "shared": None,
}

# A state entry is an entry, so its identity keys are the entry name and the location. Every
# other attribute key is a property the scan can read (F4.3 rule 3).
STATE_IDENTITY_KEYS = frozenset({"name", "location"})

# The one mapping the drift scan reads: a parse key the matrix row declares, and the attribute name the
# pinned provider schema declares for the same value. A row exists only where the two names differ, so a
# property the table has no row for is compared by the same name (rule 3).
#
# The rows are a measurement, not a choice, made 2026-11-21 per matrix row type against provider v2.0.14.
# A pair is kept when the run prints the parse key's value as the block's own top-level field under a
# different name, and the printed value is the same data the parse key holds, so the two sides hold the
# pair in the same shape. Pinned by
# `tests/test_state_coverage.py::test_the_table_rows_are_the_measured_pairs`.
#
# The measurement reaches nothing for 16 matrix rows: 10 print none of their properties at the block's own
# level, 4 print one there as a reference, a nested object, or a number text rather than as the same data the
# parse key holds, and 2 hold no report entry in the run, so no pair is read for them. Two shapes the
# measurement cannot write as one name are recorded in `backlog.md`: the address `value`, which the run prints
# under four names chosen by the entry's declared type, and the tag text, which `parse_tags` stores only as
# `comments`, so the `description` key the row declares is never filled for the measurement to pair.
STATE_PROPERTY_NAMES = {
    "panos_address_group": {"static_members": "static"},
    "panos_ike_crypto_profile": {
        "authentications": "hash",
        "dh_groups": "dh_group",
        "encryptions": "encryption",
    },
}


def nested_block(value) -> dict:
    """A nested block, read as the provider writes it: an object, or a one-element list (F5.6)."""
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        return value[0]
    return {}


def state_facts(entry: StateEntry) -> dict | None:
    """The five scope facts the state document declares for an entry, or None when it cannot key.

    None when the entry sits in a sub-block `LOCATION_SCHEMA` does not declare for its row,
    because that entry cannot be the same object as a run entry. An entry with no `location`
    declares no fact, so its facts are empty, the same reading a shared run entry has.
    """
    blocks = LOCATION_SCHEMA.get(entry.resource_type)
    if blocks is None:
        return None
    location = nested_block(entry.attributes.get("location"))
    facts = dict.fromkeys(container_coverage.SCOPE_FACT_KEYS, "")
    for block, value in location.items():
        declared = blocks.get(block)
        if declared is None:
            return None
        fact = STATE_SCOPE_KEYS.get(block)
        if fact is None:
            # `shared` names the shared section, which states no name.
            continue
        sub = nested_block(value)
        for field in declared:
            name = sub.get(field)
            if not name:
                continue
            if field == "name":
                facts[fact] = name
            elif field == "vsys":
                facts["vsys"] = name
            # The PAN-OS "this device" placeholder names no firewall (F3.5).
            elif field == STATE_SERIAL_KEY and name != container_coverage.PLACEHOLDER_DEVICE:
                # The serial the state document declares for the entry (rule 7), read through the same walk.
                facts[STATE_SERIAL_FACT] = name
    return facts


def state_name_for(resource_type: str, key: str) -> str:
    """The attribute name the state document holds for a parse key (rule 3).

    The table row when the table has one, otherwise the key itself: the same-name rule is unchanged for
    a property the table has no row for, so the table is the only mapping the scan reads.
    """
    return STATE_PROPERTY_NAMES.get(resource_type, {}).get(key, key)


def state_properties(entry: StateEntry) -> dict:
    """The attribute values a state entry holds, as the scan reads them (F4.3 rule 3)."""
    return {
        key: value
        for key, value in entry.attributes.items()
        if key not in STATE_IDENTITY_KEYS and value not in entry_coverage.EMPTY_FIELD_VALUES
    }


def ownership_key(matrix_row: str, name: str, facts: dict) -> tuple:
    """The key one entry is found by: §2.1 identity as the F3.9 rule reads it."""
    return (matrix_row, name) + tuple(facts[key] for key in container_coverage.SCOPE_FACT_KEYS)


def state_index(source: StateSource | None) -> dict:
    """The state entries a matrix row covers, keyed by identity, in document order.

    The first entry for a key wins, because one run entry is one finding (the F5.4 rule). An
    entry with no name, no row, or a location this converter cannot state is not in the index.
    """
    if source is None:
        return {}
    index = {}
    for entry in source.entries:
        name = entry.entry_name
        facts = state_facts(entry)
        if not name or facts is None or entry.resource_type not in entry_coverage.MATRIX_BY_RESOURCE:
            continue
        index.setdefault(ownership_key(entry.resource_type, name, facts), entry)
    return index


def state_findings(ledger, source: StateSource | None) -> list:
    """Run entries the state document owns, in report order.

    Each finding is the run row, plus the matrix row that covers it, the state source by its
    report value, the state resource address, and the properties the two sides hold with
    different values. The run side is read with the F4.4 row rule, and the state side with the
    same table, so no second naming rule exists.
    """
    if source is None:
        return []
    index = state_index(source)
    findings = []
    for entry in ledger.entries():
        # The scan scope is the F4.4 row rule, so the report-row rule decides which entries
        # can be findings.
        if not ledger.is_report_entry(entry):
            continue
        row = ledger.row_for(entry)
        matrix_row = entry_coverage.matrix_row_for(row["container"])
        mark = ledger.mark_for(entry)
        if matrix_row is None or mark is None:
            continue
        facts = {key: row[key] for key in container_coverage.SCOPE_FACT_KEYS}
        state_entry = index.get(ownership_key(matrix_row["resource"], row["name"], facts))
        if state_entry is None:
            continue
        finding = dict(row)
        finding["resource"] = matrix_row["resource"]
        finding["state_name"] = source.name
        finding["state_address"] = state_entry.address
        finding["drift"] = drift_properties(matrix_row, mark, state_entry)
        findings.append(finding)
    return sorted(findings, key=lambda row: (row["line"] or 0, row["container"], row["name"]))


def drift_properties(matrix_row: dict, mark: dict, state_entry: StateEntry) -> tuple:
    """The declared properties the two sides hold with different values, in sorted order.

    Only a property the matrix row declares is compared. The state side is read under the name the
    mapping table gives the key, which is the key itself where the table has no row (rule 3). A
    property one side does not hold is not compared. A read through `RecordingDict.value` does not
    count as a property an output used, so the state scan cannot move a property finding (rule 5).

    Each item names the parse key, the state name the value was read under, and the two values, so a
    mapped pair carries both names.
    """
    declared = set(matrix_row["properties"])
    captured = mark["captured"]
    state_values = state_properties(state_entry)
    differing = []
    for key in sorted(declared & set(captured.keys())):
        run_value = captured.value(key)
        if run_value in entry_coverage.EMPTY_FIELD_VALUES:
            continue
        name = state_name_for(matrix_row["resource"], key)
        if name not in state_values:
            continue
        if run_value != state_values[name]:
            differing.append((key, name, run_value, state_values[name]))
    return tuple(differing)


def value_text(value) -> str:
    """A value as text: the JSON form, so a string with a newline still prints on one line."""
    return json.dumps(value)


def ownership_line(finding: dict) -> str:
    """One ownership line: line, object type, name, matrix row, state source, resource address.

    The line names the run entry's source line, the same line the entry rows print, and the state
    entry by its resource address, because a JSON document records no source line. The shape is
    fixed (F5.6 AC-4.2), and the section prints no path: a source is named by its report value,
    the same rule the other report bodies follow (F4.2 rule 6).
    """
    name = f"{finding['container']}/{finding['name']}"
    line = f"{finding['line'] if finding['line'] is not None else 0}"
    parts = [
        f"  line {line:>4}  ",
        f"{name:<38} ",
        f"{finding['resource']:<32} ",
        f"state source: {finding['state_name']} ({finding['state_address']})",
    ]
    return "".join(parts).rstrip()


def entry_needs_serial(entry: StateEntry) -> bool:
    """Rule 7: the entry needs the serial when the location it holds places it in a sub-block that declares the field.

    The sub-block names and the field names are read through `LOCATION_SCHEMA`, and the location is read with the
    same rule rule 2 uses, so this module holds no name list of its own. A `shared` entry names no device, and a
    sub-block the row declares for another fact declares no device, so both answer False.
    """
    blocks = LOCATION_SCHEMA.get(entry.resource_type)
    if blocks is None:
        return False
    location = nested_block(entry.attributes.get("location"))
    return any(STATE_SERIAL_KEY in blocks.get(block, ()) for block in location)


def serial_of(facts: dict) -> str:
    """Rule 7: the serial a set of facts holds, or the empty answer for an entry that names none.

    The fact is named once, as `STATE_SERIAL_FACT`, the value `STATE_SCOPE_KEYS` states for `STATE_SERIAL_KEY`, so
    this reads the value and states no name of its own; the empty answer is the same answer the other scan shapes
    use for a field that does not apply. `facts` is the answer rule 2 gives for an entry, so the read reaches the
    serial through the entry shape, and an entry that rule 2 cannot key holds no serial to read.
    """
    return (facts or {}).get(STATE_SERIAL_FACT, "")


def serial_findings(source: StateSource | None, marked: list) -> list:
    """Rule 7: the entries that need a serial and name none, inside a unit the run marked, in document order.

    The entries are read through rule 2's index, so the identity each finding carries is `ownership_key` and no
    second identity key appears. The unit is read through `unit_manifest.facts_of` and `unit_name`, and the bound
    answer through `unit_manifest.mode_of`, so this module states no unit rule, no row field, and no value of the
    pair. A run that read no state document read no entry, so it reports nothing, and a run that declared no pair
    marked no unit, so it reports nothing either. The row carries the fields the ownership line shape reads, plus
    the unit and the mode, so the report's grouping rule reads the same scope facts the other sections read.
    """
    if source is None:
        return []
    modes = {unit_manifest.unit_name(unit_manifest.facts_of(row)): unit_manifest.mode_of(row) for row in marked}
    reported = []
    for entry in state_index(source).values():
        facts = state_facts(entry)
        matrix_row = entry_coverage.MATRIX_BY_RESOURCE.get(entry.resource_type)
        if not entry_needs_serial(entry) or serial_of(facts):
            continue
        unit = unit_manifest.unit_name(unit_manifest.facts_of(facts))
        if unit not in modes:
            continue
        finding = dict(facts)
        finding.update(
            {
                "name": entry.entry_name,
                "resource": matrix_row["resource"],
                "state_name": source.name,
                "state_address": entry.address,
                "unit": unit,
                "mode": modes[unit],
            }
        )
        reported.append(finding)
    return reported


def serial_line(finding: dict) -> str:
    """One serial line: the entry the state document holds, the unit it sits in, the mode the run declared, the fact.

    The entry is named by the two parts `ownership_key` reads, the matrix row and the entry name, so a reader can
    match a line to the ownership section, and the group header the report prints for it is the F3.9 scope rule.
    The line names no source line, because a state entry has none (rule 1), and no path, the rule the other report
    bodies follow (F4.2 rule 6). The unit and the mode are read through `unit_manifest`, so this shape states no
    unit rule, no field and no value of the pair. The report prints this line only, and the console prints no line
    for the fact, so no sixth console kind appears.
    """
    parts = [
        f"  {finding['resource']}/{finding['name']:<36} ",
        f"state source: {finding['state_name']} ({finding['state_address']})",
        "  unit: ",
        unit_manifest.unit_name(unit_manifest.facts_of(finding)),
        "  mode: ",
        unit_manifest.mode_of(finding),
        "  needs a serial the state document names no value for",
    ]
    return "".join(parts).rstrip()


def drift_line(finding: dict) -> str:
    """One drift line: the ownership line shape, then the properties the two values disagree on.

    A property the mapping table has no row for prints one name, the name both sides hold. A property
    the table maps prints both names, the parse key and the state name the value was read under, so the
    operator sees the pair the finding compared.
    """
    parts = [ownership_line(finding), "  value differs: "]
    labels = []
    for key, name, run, state in finding["drift"]:
        label = key if key == name else f"{key} as {name}"
        labels.append(f"{label} ({value_text(run)} vs {value_text(state)})")
    parts.append(", ".join(labels))
    return "".join(parts).rstrip()
