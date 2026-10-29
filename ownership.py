"""F6.2 ownership as data: one row per entry a matrix row covers, as `OWNERSHIP.json`.

Ownership is a per-entry fact, so the file holds one row per entry, not one row per unit
(`unit_manifest.py` rule 4 pins the per-unit shape). Six rules, stated once here.

1. The row scope is the F4.4 rule, read through the report row: an entry a matrix row covers,
   whose destination writes an object (`emitted`). An entry inside a config-object entry is a
   property level, so the parent row's count covers it and it writes no row. A skipped entry (no
   name, or a reference pointer that carries only `<id>`) and a report-only entry write no row:
   the export declared no object there. A name a unit uses but does not declare writes no row, so
   the reference rule (`ARCHITECTURE.md` §4.3) stays the only place that names a use.
2. The declaring unit. Each entry belongs to the unit the export declares it inside
   (`docs/CODEBASE_ASSEMBLY.md` §4 rule 1). The identity is the matrix row, the entry name, and the
   four scope facts, read through `state_coverage.ownership_key` and `unit_manifest.facts_of`, so no
   second identity key appears. A row names a unit by its directory, so the two data files join on
   the manifest's `directory` field; this module defines no naming rule and takes
   `TerraformGenerator.sanitize_name` as an argument, the way `unit_manifest.build_rows` does.
3. Two entries are one object only when the export can place them in one inheritance chain: the
   shared unit (the four facts empty) and the units whose declared fact is a device group. A name in
   a template, a virtual system, or a device is a different object in each unit (`ARCHITECTURE.md`
   §2.1), so each unit owns its own entry.
4. The owner rule. The ancestor entry owns the name, as `docs/CODEBASE_ASSEMBLY.md` §1 rule 2 states
   it. The export states the relation in three cases: the shared unit, the parent source the run
   declares with `--parent` (the F5.4 rule), and the device-group `parent` field, which the parse
   captures from F6.5 and which orders two device groups inside one source. A device group with no
   `parent` is a top-level group, so it is not the ancestor of another top-level group: two
   top-level groups that repeat a name are peers, and the case stays `ambiguous`.
   `disable_override` does not choose the owner: it names the entry that no descendant may override
   (verified against provider 2.0.14 and the provider docs), so a second entry with the same name is
   a contradiction, not an override.
5. What the rule can say, per entry (`kind`): `declared` (one entry, or units that cannot sit in one
   chain), `definition` (this entry owns the name), `override` (this entry repeats a name another
   entry owns, so the codebase resolves it as a reference to `owner`), `ambiguous` (the rule names no
   owner). `override` states the flag as the parse read it: `yes`, `no`, or `unknown` when the matrix
   row does not declare the property. A row from a declared parent source states `unknown`, because
   `main()` builds the parent ledger from entry names and never runs the parse methods, so no mark
   exists there; the owner rule still names the parent source as the ancestor.
6. A finding is an operator action, so it does not change the exit code, which the F4.1 gate decides.
   The report prints one line per finding, in report order, and the console prints no ownership line.
   The scan reads a captured value through the non-recording read (`RecordingDict.value`), so it is not
   an output read and cannot move a property finding (the F5.6 rule).

The scan result holds the declared fields plus the facts the report line reads (`line`,
`container`, `reason`) and the unit fact the owner rule reads (`chain`, the device group chain the
export states, F6.5). `render` writes only the declared fields, and `parse_rows` refuses a file that
states anything else. Report order is fixed: findings are sorted by line, then object type, then name,
so the same sources produce the same bytes.

Usage:
    from ownership import OWNERSHIP_FILE, build_rows, render, parse_rows, findings
    rows = build_rows(ledger, parent_ledger, generator.sanitize_name)
    (output_dir / OWNERSHIP_FILE).write_text(render(rows), encoding='utf-8')
    for finding in findings(rows):
        print(finding_line(finding))
"""

import json
from typing import Callable

import container_coverage
import entry_coverage
import state_coverage
import unit_manifest

OWNERSHIP_FILE = 'OWNERSHIP.json'

# Field order. Fixed, so two runs write the same bytes and a reader does not guess.
# The field names are the printed keys, so `parse_rows` reads a row back as itself.
FIELD_ORDER = ('type', 'entry', 'source', 'device_group', 'vsys', 'template', 'vsys_device',
               'directory', 'owner', 'kind', 'override')

# The four scope facts, read through `unit_manifest`, so the row joins to the manifest row and no
# second fact order appears.
FACT_KEYS = unit_manifest.FACT_KEYS

# What the rule can say about an entry (rule 5), and the flag values it can state.
KINDS = ('declared', 'definition', 'override', 'ambiguous')
OVERRIDE_VALUES = ('yes', 'no', 'unknown')

# The flag, as the parse key. Only `panos_address` and `panos_service` capture it, so a row for
# another matrix row states `unknown` (the extraction gap in `backlog.md`).
FLAG_KEY = 'disable_override'

FINDING_HEADING = 'Repeated Names That Need an Operator Decision'

FINDING_RULE = (
    'A name two units declare inside one inheritance chain is listed here. Panorama resolves a '
    'repeated name through inheritance at commit time, so one object on the device is two entries '
    'in the export, and the codebase needs the entry that defines it. The ancestor entry owns the '
    'name. The export names the ancestor for the shared section and for the parent source the run '
    'declares, so a repeated name in two device groups is an operator decision. `disable_override` '
    'names the entry that no descendant may override, so a second entry with the same name is an '
    'operator decision as well. A finding is an operator action, not a broken output: it does not '
    'change the exit code, which the F4.1 gate still decides.'
)

# One reason per case the rule cannot decide on its own (rule 4).
NO_RELATION = 'no inheritance relation stated between the units'
FLAG_NOT_ANCESTOR = 'disable_override names an entry that is not the ancestor'
FLAG_FORBIDS_OVERRIDE = 'the definition names disable_override, so this entry cannot be an override'


def row_facts(row: dict) -> tuple:
    """The declaring unit identity a row states, in `FACT_KEYS` order."""
    return tuple(row[key] for key in FACT_KEYS)


def row_key(row: dict) -> tuple:
    """The order a row sorts by: the identity key, then the source, because two sources can state
    the same identity."""
    return state_coverage.ownership_key(row['type'], row['entry'], dict(zip(FACT_KEYS, row_facts(row)))) \
        + (row['source'],)


def in_chain(facts: tuple) -> bool:
    """True when a unit can sit in one inheritance chain: the shared unit, or a unit whose declared
    fact is a device group (rule 3)."""
    return all(value == '' for value in facts) or unit_manifest.fact(facts, 'device_group') != ''


def override_value(matrix_row: dict, captured) -> str:
    """The flag as the parse read it (rule 5). `unknown` when the matrix row does not declare the
    property, or when no object was captured for the entry."""
    if FLAG_KEY not in matrix_row['properties']:
        return 'unknown'
    if not isinstance(captured, entry_coverage.RecordingDict):
        return 'unknown'
    # The scan is not an output, so the read must not count as a property an output used.
    value = (captured.value(FLAG_KEY) or '').strip().lower()
    return value if value in ('yes', 'no') else 'no'


def parent_map(ledger) -> dict:
    """{device group: the parent group the export states}, for the groups this ledger read (rule 4).

    The parse captures the field, so the relation is a fact and not a guess. The read is the
    non-recording read, so the scan does not count it as a property an output used (the F5.6 rule).
    A ledger built from a declared parent source runs no parse method, so it has no marks and this
    map is empty there: the parent source is already the ancestor, and the chain adds nothing.
    """
    groups = {}
    for entry in ledger.entries():
        if entry.tag != 'entry':
            continue
        if container_coverage.container_tag(entry, ledger.parents, ledger.source) != 'device-group':
            continue
        mark = ledger.mark_for(entry)
        captured = mark['captured'] if mark else None
        if isinstance(captured, entry_coverage.RecordingDict):
            groups[entry.get('name') or ''] = (captured.value('parent') or '').strip()
    return groups


def chain_of(groups: dict, unit: str) -> tuple:
    """The device group chain one unit states, from that unit upward, in order (rule 4).

    The chain is the captured `parent` names, so a group that states no parent ends it. The export
    calls a group with no parent a top-level group, so this states no ancestor above it, which is
    not the same as being an ancestor: two top-level groups are peers.
    """
    chain = []
    node = unit
    while node and node in groups and node not in chain:
        node = groups[node]
        if node:
            chain.append(node)
    return tuple(chain)


def scan_row(ledger, entry, matrix_row: dict, groups: dict) -> dict:
    """One row for an entry the scan scope covers, or None when the entry is not in scope.

    `is_report_entry` is the F4.3 row rule, and `matrix_row_for` is the F4.4 row rule, so the scan
    adds no second scope rule. The destination is the F4.3 fact: only an entry that writes an object
    can own a name.
    """
    if not ledger.is_report_entry(entry):
        return None
    row = ledger.row_for(entry)
    if row['destination'] != 'emitted':
        return None
    mark = ledger.mark_for(entry)
    facts = unit_manifest.facts_of(row)
    unit = dict(zip(FACT_KEYS, facts))
    return {
        'type': matrix_row['resource'],
        'entry': row['name'],
        'source': row['source'],
        **dict(zip(FACT_KEYS, facts)),
        'directory': '',      # filled by build_rows, which holds the sanitizing rule
        'owner': '',
        'kind': '',
        'override': override_value(matrix_row, mark['captured'] if mark else None),
        # Run facts the report line reads. `render` writes only the declared fields.
        'line': row['line'],
        'container': row['container'],
        'reason': '',
        # The device group chain the export states for this row's unit (rule 4, F6.5). A fact the
        # owner rule reads, not a data field, so it is not written.
        'chain': chain_of(groups, unit['device_group']),
    }


def decide(rows: list) -> list:
    """Assign `kind`, `owner`, and the reason for one group of entries that share a name.

    `rows` is the rows that share (matrix row, entry name) — the key `shadow_coverage.py` uses.
    Only rows whose unit can sit in one inheritance chain are one object (rule 3); the others are
    each their own object, so each is `declared`.
    """
    single = [row for row in rows if not in_chain(row_facts(row))]
    for row in single:
        row['kind'] = 'declared'
        row['owner'] = row['directory']

    group = [row for row in rows if in_chain(row_facts(row))]
    if not group:
        return single
    if len(group) == 1:
        row = group[0]
        row['kind'] = 'declared'
        row['owner'] = row['directory']
        return single + group

    flagged = [row for row in group if row['override'] == 'yes']
    if flagged:
        # The flag names the entry that no descendant may override. It can only own the name when it
        # can be the ancestor, so a flag on a descendant names no owner for the name.
        definition = flagged[0] if len(flagged) == 1 and is_ancestor(flagged[0], group) else None
    else:
        ancestors = [row for row in group if is_ancestor(row, group)]
        definition = ancestors[0] if len(ancestors) == 1 else None

    for row in group:
        if definition is None:
            row['kind'] = 'ambiguous'
            row['owner'] = ''
            row['reason'] = FLAG_NOT_ANCESTOR if flagged else NO_RELATION
            continue
        if row is definition:
            row['kind'] = 'definition'
            row['owner'] = row['directory']
            continue
        row['kind'] = 'override'
        row['owner'] = definition['directory']
        if definition['override'] == 'yes':
            row['reason'] = FLAG_FORBIDS_OVERRIDE
    return single + group


def is_ancestor(row: dict, group: list) -> bool:
    """True when the export states that this entry's unit is the ancestor of the others (rule 4).

    Three cases state the relation: the shared unit, the parent source the run declares, and the
    device-group `parent` chain the parse captures (F6.5). A group that states no parent is a
    top-level group, so it is not the ancestor of another top-level group: two top-level groups that
    repeat a name are peers, and the rule names no owner for them.
    """
    if all(value == '' for value in row_facts(row)) or row.get('from_parent', False):
        return True
    unit = unit_manifest.fact(row_facts(row), 'device_group')
    if not unit:
        return False
    return any(unit in other.get('chain', ()) for other in group if other is not row)


def build_rows(ledger, parent_ledger, sanitize: Callable[[str], str]) -> list:
    """One row per entry the scan scope covers, in the identity order.

    The run ledger and the declared parent ledger are read with the same row rule, so the matrix row
    that covers a run entry is the row that covers a parent entry (the F5.4 rule). A run with no
    declared parent source has no parent to read, so no row comes from it.
    """
    rows = []
    for current, is_parent in ([(ledger, False)] + ([(parent_ledger, True)] if parent_ledger else [])):
        stated = parent_map(current)
        for entry in current.entries():
            container = current.parents.get(entry)
            if container is None:
                continue
            matrix_row = entry_coverage.matrix_row_for(
                container_coverage.section_path(container, current.parents, current.source))
            row = scan_row(current, entry, matrix_row, stated) if matrix_row else None
            if row is None:
                continue
            row['from_parent'] = is_parent
            row['directory'] = unit_manifest.directory_name(row_facts(row), sanitize)
            rows.append(row)
    # The group is the key `shadow_coverage.py` uses: the matrix row and the entry name.
    groups: dict = {}
    for row in rows:
        groups.setdefault((row['type'], row['entry']), []).append(row)
    for group in groups.values():
        decide(sorted(group, key=row_key))
    return sorted(rows, key=row_key)


def render(rows: list) -> str:
    """The record as text: the rows in field order, with one trailing newline.

    Fields print in the declared order, not alphabetically, and no field states a timestamp or a
    path, so two runs on the same bytes write the same bytes. The report facts (`line`, `container`,
    `reason`) are not data fields, so they are not written.
    """
    return json.dumps([{key: row[key] for key in FIELD_ORDER} for row in rows], indent=2) + '\n'


def parse_rows(text: str) -> list:
    """Read a written record back as data, in the identity order.

    A row that is not the declared shape is a refusal: the record is data, so a reader cannot fall
    back to reading prose.
    """
    document = json.loads(text)
    if not isinstance(document, list):
        raise ValueError('the ownership record is not a list of rows')
    rows = []
    for row in document:
        if not isinstance(row, dict):
            raise ValueError(f'not an ownership row: {row!r}')
        extra = [key for key in row if key not in FIELD_ORDER]
        if extra:
            raise ValueError(f'not a declared ownership field: {extra}')
        missing = [key for key in FIELD_ORDER if key not in row]
        if missing:
            raise ValueError(f'the row does not state its fields: {missing}')
        if any(not isinstance(row[key], str) for key in FIELD_ORDER):
            raise ValueError(f'the fields of an ownership row are not names: {row}')
        if row['kind'] not in KINDS:
            raise ValueError(f'not a declared kind: {row["kind"]}')
        if row['override'] not in OVERRIDE_VALUES:
            raise ValueError(f'not a declared flag value: {row["override"]}')
        rows.append({key: row[key] for key in FIELD_ORDER})
    return sorted(rows, key=row_key)


def findings(rows: list) -> list:
    """The rows that need an operator decision, in report order (rule 6)."""
    return sorted([row for row in rows if row['reason']],
                  key=lambda row: (row['line'] or 0, row['container'], row['entry']))


def finding_line(row: dict) -> str:
    """One finding line: line, object type, entry name, matrix row, the reason.

    The shape is the shape the other finding sections use, and the line names a source by its report
    value, never by its path (F4.2 rule 6), because the reason names the units, not a file.
    """
    name = f'{row["container"]}/{row["entry"]}'
    line = f'{row["line"] if row["line"] is not None else 0}'
    parts = [f'  line {line:>4}  ', f'{name:<38} ', f'{row["type"]:<32} ', row['reason']]
    return ''.join(parts).rstrip()
