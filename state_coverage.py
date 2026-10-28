"""F5.6 state coverage: the ownership fact and the drift fact.

Five rules, stated once here.

1. The state entry shape. A state entry is one instance object the producer read
   (`state_input.StateEntry`). Its matrix row is the row keyed by its resource type, through
   `entry_coverage.MATRIX_BY_RESOURCE`: the same table, the same key, no second naming rule. Its
   properties are the attribute keys it holds, read with the F4.3 rule (the entry name and the
   scope facts are identity, not content, and an empty value is not a property). A state entry has
   no source line, because only the expat handler path records one, so its position is its
   resource address.
2. The ownership key is §2.1 identity as the F3.9 rule reads it: the matrix row, the entry name,
   and the four declared scope facts (§2.2). `Shared` is the parse fallback, so the key uses the
   facts each source declares, never the fallback. The state declares its scope through its
   `location` block, through the block names `LOCATION_SCHEMA` declares. A nested block is read
   as an object, or as a one-element list of an object, because the provider writes a nested block
   either way. The `shared` block names the shared section, which states no name, so it fills no
   fact. A block the converter never emits (`template_stack`, `template_stack_vsys`,
   `template_vsys`) names a scope no run entry can sit in, so an entry placed there is not keyed.
3. The drift fact compares a property the matrix row declares that both sides hold by the same
   name, with values that are not equal. A property one side does not hold is not compared, and a
   property the two sides name differently is not compared: the matrix row names the key the
   emitter reads, the state names the attribute the provider stored, and no mapping rule exists.
   A value is compared as the two sides hold it, so member order is part of the value.
4. A drift fact needs an ownership fact, so the drift section is a subset of the ownership
   section. The scan scope is the F4.4 rule on both sides: an entry no matrix row covers is not a
   finding, and a state resource whose type has no matrix row is not in the index. A run with no
   declared state source has no state to read, so it reports neither fact.
5. The state scan is not an output, so it reads a captured value through the non-recording read
   (`entry_coverage.RecordingDict.value`), and the property section is unchanged by it. Report
   order is fixed: findings are sorted by line, then object type, then name. A finding is an
   operator action, not a broken output, so it does not change the exit code, which the F4.1 gate
   decides. The console prints no state line.

Usage:
    from state_coverage import state_index, state_findings, ownership_line, drift_line
    findings = state_findings(ledger, state_source)
    for finding in findings:
        print(ownership_line(finding))
"""

import json
from typing import Optional

import container_coverage
import entry_coverage
from resource_mapping import LOCATION_SCHEMA
from state_input import StateEntry, StateSource

OWNERSHIP_HEADING = 'Entries Another Workspace Already Owns'
DRIFT_HEADING = 'Owned Entries With a Value The Run Does Not Match'

OWNERSHIP_RULE = (
    'An entry this run read that another workspace already owns is listed here. The state '
    'document names the workspace that holds the object, and the resource address names the '
    'entry in it. The key is the entry identity (device group, vsys, type, name), read from '
    'the location the state document holds, so an entry in a different scope is a different '
    'object and is not listed. A finding is an operator action, not a broken output: it does '
    'not change the exit code, which the F4.1 gate still decides.'
)

DRIFT_RULE = (
    'An owned entry with a value this run does not match is listed here. Only a property the '
    'coverage matrix row declares is compared, and only when both sides hold it by the same '
    'name, because no rule maps a parse key to a provider attribute name. The values are '
    'printed as JSON text, so one finding stays on one line. A finding is an operator action, '
    'not a broken output, so it does not change the exit code, which the F4.1 gate still '
    'decides.'
)

# Which §2.2 fact each `location` sub-block fills. The sub-block names and the field names
# come from `LOCATION_SCHEMA`, so this is the mapping, not a second naming rule; it is the
# same shape `entry_coverage.REPORT_SCOPE_KEYS` holds for containers. `shared` names the
# shared section, which states no name, so it fills no fact. A sub-block the table does not
# declare for the row (`template_stack`, `template_stack_vsys`, `template_vsys`) names a scope
# this converter never emits, so an entry placed there is not keyed.
STATE_SCOPE_KEYS = {
    'device_group': 'device_group',
    'vsys': 'vsys',
    'template': 'template',
    'ngfw': 'vsys_device',
    'shared': None,
}

# A state entry is an entry, so its identity keys are the entry name and the location. Every
# other attribute key is a property the scan can read (F4.3 rule 3).
STATE_IDENTITY_KEYS = frozenset({'name', 'location'})


def nested_block(value) -> dict:
    """A nested block, read as the provider writes it: an object, or a one-element list (F5.6)."""
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        return value[0]
    return {}


def state_facts(entry: StateEntry) -> Optional[dict]:
    """The four scope facts the state document declares for an entry, or None when it cannot key.

    None when the entry sits in a sub-block `LOCATION_SCHEMA` does not declare for its row,
    because that entry cannot be the same object as a run entry. An entry with no `location`
    declares no fact, so its facts are empty, the same reading a shared run entry has.
    """
    blocks = LOCATION_SCHEMA.get(entry.resource_type)
    if blocks is None:
        return None
    location = nested_block(entry.attributes.get('location'))
    facts = dict.fromkeys(container_coverage.SCOPE_FACT_KEYS, '')
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
            if field == 'name':
                facts[fact] = name
            elif field == 'vsys':
                facts['vsys'] = name
            # The PAN-OS "this device" placeholder names no firewall (F3.5).
            elif field == 'ngfw_device' and name != container_coverage.PLACEHOLDER_DEVICE:
                facts['vsys_device'] = name
    return facts


def state_properties(entry: StateEntry) -> dict:
    """The attribute values a state entry holds, as the scan reads them (F4.3 rule 3)."""
    return {key: value for key, value in entry.attributes.items()
            if key not in STATE_IDENTITY_KEYS and value not in entry_coverage.EMPTY_FIELD_VALUES}


def ownership_key(matrix_row: str, name: str, facts: dict) -> tuple:
    """The key one entry is found by: §2.1 identity as the F3.9 rule reads it."""
    return (matrix_row, name) + tuple(facts[key] for key in container_coverage.SCOPE_FACT_KEYS)


def state_index(source: Optional[StateSource]) -> dict:
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


def state_findings(ledger, source: Optional[StateSource]) -> list:
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
        matrix_row = entry_coverage.matrix_row_for(row['container'])
        mark = ledger.mark_for(entry)
        if matrix_row is None or mark is None:
            continue
        facts = {key: row[key] for key in container_coverage.SCOPE_FACT_KEYS}
        state_entry = index.get(ownership_key(matrix_row['resource'], row['name'], facts))
        if state_entry is None:
            continue
        finding = dict(row)
        finding['resource'] = matrix_row['resource']
        finding['state_name'] = source.name
        finding['state_address'] = state_entry.address
        finding['drift'] = drift_properties(matrix_row, mark, state_entry)
        findings.append(finding)
    return sorted(findings, key=lambda row: (row['line'] or 0, row['container'], row['name']))


def drift_properties(matrix_row: dict, mark: dict, state_entry: StateEntry) -> tuple:
    """The declared properties the two sides hold with different values, in sorted order.

    Only a property the matrix row declares is compared, and only when both sides hold it by the
    same name (rule 3). A read through `RecordingDict.value` does not count as a property an
    output used, so the state scan cannot move a property finding (rule 5).
    """
    declared = set(matrix_row['properties'])
    captured = mark['captured']
    state_values = state_properties(state_entry)
    shared = declared & set(captured.keys()) & set(state_values)
    differing = []
    for key in sorted(shared):
        run_value = captured.value(key)
        if run_value in entry_coverage.EMPTY_FIELD_VALUES:
            continue
        if run_value != state_values[key]:
            differing.append((key, run_value, state_values[key]))
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
    name = f'{finding["container"]}/{finding["name"]}'
    line = f'{finding["line"] if finding["line"] is not None else 0}'
    parts = [f'  line {line:>4}  ', f'{name:<38} ', f'{finding["resource"]:<32} ',
             f'state source: {finding["state_name"]} ({finding["state_address"]})']
    return ''.join(parts).rstrip()


def drift_line(finding: dict) -> str:
    """One drift line: the ownership line shape, then the properties the two values disagree on."""
    parts = [ownership_line(finding), '  value differs: ']
    parts.append(', '.join(f'{key} ({value_text(run)} vs {value_text(state)})'
                           for key, run, state in finding['drift']))
    return ''.join(parts).rstrip()

