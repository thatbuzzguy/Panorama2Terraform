"""F6.3 the reference between units: one row per edge, as `REFERENCE_EDGES.json`.

An edge is a pair fact: the unit that uses a name, and the unit that owns it. `unit_manifest.py` rule 4
pins one row per unit, and `ownership.py` rule 1 pins one row per entry, so a pair needs its own record.
Seven rules, stated once here.

1. The edge set is the names the reference rule recorded (`TerraformGenerator.name_ref`,
   `ARCHITECTURE.md` §4.3), so this module records no name and resolves no name. A name the rule resolved
   inside the run is a reference inside one root, not an edge between units, so it writes no row. A name
   that no unit in the run declares writes no row either: the pair does not exist, and that name is
   already stated in the manifest's `references` field.
2. The target unit is the owner from the ownership row for (`type`, `entry`), not the declaring unit
   (`ownership.py` rule 5). A name several units declare as separate objects gives one row per owner,
   which is the ambiguous-device case in `ARCHITECTURE.md` §4.3 rule 1. The join is the F6.2 rule:
   `referrer` and `target` name units by their directory, so the row joins to `CODEBASE_MANIFEST.json` on
   `directory` and to `OWNERSHIP.json` on (`type`, `entry`). This module defines no naming rule and no
   identity key: it takes `TerraformGenerator.sanitize_name` as an argument, the way
   `unit_manifest.build_rows` and `ownership.build_rows` do, and it reads the unit identity through
   `unit_manifest`.
3. Self-reference exclusion. A row whose target is the referrer writes no row, because an edge is a fact
   between two units and a unit cannot come before itself. This is the rule that also keeps a unit out of
   its own `after` list (rule 7).
4. The row shape. The row is data, so a document describes its fields and never restates a row
   (`docs/README.md` rule). Fields print in the declared order, rows sort by the four fields in field
   order, which a reader can reproduce from the file, one row per pair, no timestamp and no path, so two
   runs on the same bytes write the same bytes. `parse_rows` reads a written file back and refuses a row
   that is not the declared shape, including a row that names one unit instead of two.
5. The acyclic rule: the edge graph must be acyclic (`docs/CODEBASE_ASSEMBLY.md` §6). A cycle is a
   finding, so it does not change the exit code, which the F4.1 gate decides, and the console prints no
   cycle line. The report prints one line per cycle, in its own section, grouped by the F3.9 scope rule.
   A cycle is read from its smallest unit, so one cycle is reported once and the same edge set produces
   the same lines. A finding reads its grouping facts through the manifest row of the unit it is read
   from, because the manifest is the file that states the unit.
6. The mechanism a name resolves through is not data here. The data block is the rule for a name outside
   the run (`ARCHITECTURE.md` §4.7, `sanity_checks.DATA_SOURCE_SCHEMA`); for a name another unit in the
   run owns, the mechanism must be that unit's outputs, which the generator does not write, so the choice
   stays open in `backlog.md`. This module writes no `.tf` byte.
7. The unit order. `after` names the units a unit must be planned after, and `rank` is its position in the
   order, from 1. Three rules produce `after` (`docs/CODEBASE_ASSEMBLY.md` §6), each read through the
   module that holds the fact: the ancestor unit before the unit that carries an override of a name it owns
   (`ownership.py` rule 4); the shallower scope before the deeper scope inside it, in the F3.9 level order;
   and the target unit before the referrer unit, from the edge. A tie follows the identity order, which is
   the order the manifest rows print, so `rank` is deterministic. A unit in a cycle cannot be ordered, so
   it states 0. `after` names only units the manifest names: a declared parent source names no unit, so the
   order graph reads only manifest units.

Usage:
    from reference_edges import EDGE_FILE, build_rows, render, parse_rows, findings, cycle_line, order
    rows = build_rows(ownership_rows, generator.unit_references(), generator.sanitize_name)
    manifest_rows = order(unit_manifest.build_rows(ledger, generator.unit_references(),
                                                   generator.sanitize_name), ownership_rows, rows)
    (output_dir / EDGE_FILE).write_text(render(rows), encoding='utf-8')
    for finding in findings(rows, manifest_rows):
        print(cycle_line(finding))
"""

import json
from collections import defaultdict
from typing import Callable

import unit_manifest

EDGE_FILE = 'REFERENCE_EDGES.json'

# Field order. Fixed, so two runs write the same bytes and a reader does not guess.
# The field names are the printed keys, so `parse_rows` reads a row back as itself.
FIELD_ORDER = ('referrer', 'target', 'type', 'entry')

# The four scope facts, read through `unit_manifest`, so the row joins to the manifest row and no
# second fact order appears.
FACT_KEYS = unit_manifest.FACT_KEYS

# The F3.9 level order (device group, then template, then device). The virtual system is a fact but not
# a report level, so a vsys adds no level to the order chain.
LEVEL_KEYS = ('device_group', 'template', 'vsys_device')

CYCLE_HEADING = 'Reference Cycles Between Units That Need an Operator Decision'

CYCLE_RULE = (
    'Two units that reference each other cannot be put in a plan order, so the edge graph must be acyclic. '
    'A cycle is listed here, one line per cycle, read from its smallest unit, which is the unit the line '
    'is grouped by. A finding is an operator action, not a broken output: it does not change the exit '
    'code, which the F4.1 gate still decides.'
)

CYCLE_REASON = 'no plan order can put one of these units before the other'

# `rank` states no position for a unit in a cycle, because such a unit cannot be ordered.
NO_RANK = 0


def build_rows(ownership_rows: list, references: dict, sanitize: Callable[[str], str]) -> list:
    """One row per edge the data can name, in the order the fields sort by.

    `references` is the reference names `name_ref` recorded, keyed by the referrer's four scope facts. The
    target unit is the `owner` field of an ownership row that covers (`type`, `entry`). A name no ownership
    row covers writes no row (rule 1), and a row whose target is the referrer writes no row (rule 3).
    """
    owners: dict = defaultdict(set)
    for row in ownership_rows:
        owners[row['entry']].add((row['type'], row['owner']))

    rows = []
    for facts, names in references.items():
        referrer = unit_manifest.directory_name(facts, sanitize)
        for name in sorted(names):
            for type_, owner in sorted(owners.get(name, ())):
                if not owner or owner == referrer:
                    continue    # rule 1 and rule 3: no target unit, or the same unit twice
                rows.append(dict(zip(FIELD_ORDER, (referrer, owner, type_, name))))
    return sorted(rows, key=lambda row: tuple(row[key] for key in FIELD_ORDER))


def render(rows: list) -> str:
    """The record as text: the rows in field order, with one trailing newline.

    Fields print in the declared order, not alphabetically, and no field states a timestamp or a path, so
    two runs on the same bytes write the same bytes.
    """
    return json.dumps([{key: row[key] for key in FIELD_ORDER} for row in rows], indent=2) + '\n'


def parse_rows(text: str) -> list:
    """Read a written record back as data, in the order the fields sort by.

    A row that is not the declared shape is a refusal: the record is data, so a reader cannot fall back to
    reading prose. A row must name two units, because one unit is not an edge.
    """
    document = json.loads(text)
    if not isinstance(document, list):
        raise ValueError('the edge record is not a list of rows')
    rows = []
    for row in document:
        if not isinstance(row, dict):
            raise ValueError(f'not an edge row: {row!r}')
        extra = [key for key in row if key not in FIELD_ORDER]
        if extra:
            raise ValueError(f'not a declared edge field: {extra}')
        missing = [key for key in FIELD_ORDER if key not in row]
        if missing:
            raise ValueError(f'the row does not state its fields: {missing}')
        if any(not isinstance(row[key], str) for key in FIELD_ORDER):
            raise ValueError(f'the fields of an edge row are not names: {row}')
        if not row['referrer'] or not row['target']:
            raise ValueError(f'an edge row must name two units: {row}')
        rows.append({key: row[key] for key in FIELD_ORDER})
    return sorted(rows, key=lambda row: tuple(row[key] for key in FIELD_ORDER))


def graph(rows: list) -> dict:
    """The edge graph: one unit to the units it references, in sorted order.

    Rule 3 keeps a node from pointing at itself, so no node can be a cycle of one unit.
    """
    adjacency: dict = defaultdict(set)
    for row in rows:
        if row['referrer'] != row['target']:
            adjacency[row['referrer']].add(row['target'])
    return {node: sorted(adjacency[node]) for node in sorted(adjacency)}


def _walk(adjacency: dict, start: str, node: str, walk: list, found: list) -> None:
    """Walk the graph from one node and record each cycle that starts at `start` (rule 5).

    The canonical rule is in the guard: a walk only visits units above `start`, so every cycle it records
    starts at its smallest unit and one cycle is reported once. Targets are visited in sorted order, so the
    same edge set produces the same walk.
    """
    walk.append(node)
    for target in adjacency.get(node, ()):
        if target == start:
            cycle = tuple(walk)
            if cycle not in found:
                found.append(cycle)
        elif target > start and target not in walk:
            _walk(adjacency, start, target, walk, found)
    walk.pop()


def cycles(rows: list) -> list:
    """The cycles of the edge graph, in report order (rule 5).

    A self-reference cannot be a cycle, because rule 3 writes no such row, so the smallest cycle is two
    units.
    """
    adjacency = graph(rows)
    found: list = []
    for start in sorted(adjacency):
        _walk(adjacency, start, start, [], found)
    return sorted(found)


def findings(rows: list, manifest_rows: list) -> list:
    """The cycles that need an operator decision, in report order (rule 5).

    A finding holds the four facts of the unit the cycle is read from, read through that unit's manifest
    row, so the report groups it with the F3.9 rule, plus the walk and the names on each hop.
    """
    facts_of = {row['directory']: tuple(row[key] for key in FACT_KEYS) for row in manifest_rows}
    hop_names: dict = defaultdict(set)
    for row in rows:
        hop_names[(row['referrer'], row['target'])].add(row['entry'])

    findings = []
    for cycle in cycles(rows):
        facts = facts_of.get(cycle[0])
        if facts is None:
            continue    # rule 2: a cycle is read from a unit the manifest names
        finding = {key: unit_manifest.fact(facts, key) for key in FACT_KEYS}
        finding['cycle'] = cycle
        finding['names'] = tuple(tuple(sorted(hop_names[(cycle[hop], cycle[(hop + 1) % len(cycle)])]))
                                 for hop in range(len(cycle)))
        finding['reason'] = CYCLE_REASON
        findings.append(finding)
    return sorted(findings, key=lambda finding: (tuple(finding[key] for key in FACT_KEYS),
                                                 finding['cycle']))


def cycle_line(finding: dict) -> str:
    """One cycle line: the units in walk order, the names on each hop, the reason.

    The shape is fixed (F6.3 AC-3.3). Units are named by their directory, the join key, the hop names print
    in hop order, and the line names no path, the same rule the other finding sections follow (F4.2 rule
    6).
    """
    walk = ' -> '.join(finding['cycle'])
    names = '; '.join(', '.join(group) for group in finding['names'])
    parts = [f'  cycle  {walk}  ', f'names: {names}  ', finding['reason']]
    return ''.join(parts).rstrip()


def dependencies(manifest_rows: list, ownership_rows: list, edge_rows: list) -> dict:
    """The units each unit must be planned after, in `after` order (rule 7).

    Only units the manifest names are nodes, so a declared parent source adds no dependency: a unit exists
    when the run's ledger has a row in it, and the parent source names no such row.
    """
    units = {tuple(row[key] for key in FACT_KEYS): row['directory'] for row in manifest_rows}
    nodes = set(units.values())
    deps: dict = defaultdict(set)

    # The level rule: the shallower scope before the deeper scope inside it, in the F3.9 level order. Each
    # prefix of the unit's scope path is the scope that contains it.
    for row in manifest_rows:
        facts = tuple(row[key] for key in FACT_KEYS)
        for level in range(1, len(LEVEL_KEYS) + 1):
            prefix = tuple(unit_manifest.fact(facts, key) if key in LEVEL_KEYS[:level] else ''
                           for key in FACT_KEYS)
            container = units.get(prefix)
            if container and container != row['directory']:
                deps[row['directory']].add(container)

    # The inheritance rule: the ancestor unit before the unit that carries an override of a name it owns.
    for row in ownership_rows:
        if row['owner'] and row['owner'] != row['directory']:
            deps[row['directory']].add(row['owner'])

    # The edge rule: the target unit before the referrer unit.
    for row in edge_rows:
        if row['target'] in nodes:
            deps[row['referrer']].add(row['target'])

    return {node: sorted(deps[node]) for node in sorted(nodes)}


def order(manifest_rows: list, ownership_rows: list, edge_rows: list) -> list:
    """Fill `rank` and `after` on the manifest rows, in the identity order the rows print in.

    `unit_manifest.py` states the row shape; this module states the order rules that fill the two fields.
    The order is a Kahn walk that starts from the units with no dependency in the identity order and takes
    the identity-smallest ready unit each step, so a tie follows the identity order. A unit that still has
    a dependency when the walk stops is in a cycle, so it keeps `NO_RANK` and the cycle section names it.
    """
    deps = dependencies(manifest_rows, ownership_rows, edge_rows)
    dependents: dict = defaultdict(set)
    for directory, after in deps.items():
        for unit in after:
            dependents[unit].add(directory)

    identity = {row['directory']: tuple(row[key] for key in FACT_KEYS) for row in manifest_rows}

    ranks: dict = {}
    remaining = {directory: set(after) for directory, after in deps.items()}
    ready = sorted([directory for directory, after in remaining.items() if not after],
                   key=lambda directory: identity[directory])
    while ready:
        directory = ready.pop(0)
        ranks[directory] = len(ranks) + 1
        for dependent in sorted(dependents[directory], key=lambda unit: identity[unit]):
            remaining[dependent].discard(directory)
            if dependent not in ranks and not remaining[dependent]:
                ready.append(dependent)
        ready.sort(key=lambda directory: identity[directory])

    rows = []
    for row in manifest_rows:
        filled = dict(row)
        filled['rank'] = ranks.get(row['directory'], NO_RANK)
        filled['after'] = sorted(deps[row['directory']])
        rows.append(filled)
    return rows
