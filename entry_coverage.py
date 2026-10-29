"""F4.3 per-entry coverage: what the parser read from each entry, and where it went.

Four rules, stated once here.

1. The ledger. Every parse method marks the entries it reads. A mark records the
   entry, the object the method built from it, and the destination when the
   method knows better than the container table. The report is built from the
   ledger after the parse, so a parse method that reads an entry and does not
   mark it fails the gate (tests/test_entry_coverage.py).
2. The report row. One entry is one `<entry name>` element, not the lines it
   spans. An entry inside a config-object entry is a property level, so the
   property matrix (F4.4) owns it: the entry row shows the count, and the property
   scan reports the properties.
   Entries under `predefined` are PAN-OS built-in definitions, not operator
   objects (F4.2), so they are not rows.
3. The destination. The container table row that covers the entry's container
   gives the destination. No second table. A mark can override it when the fact
   is per-entry: `report_only` content is `report`, and a skipped entry is
   `skipped`.
4. The property scan (F4.4). The matrix row for an emitted container names the
   properties its emitter reads. A captured property that no output read for this
   entry is a gap, and the scan reports it. The scan measures reads at run time:
   the object a mark stores records every key an output reads from it, and the
   record starts after the parse, so a key the parse method read off the XML
   element is not a property the output used.

The entry name (F2.3) and the four scope facts (F3.1, F3.2) are not captured
fields: they name the object and place it, so the report shows them as the row
identity, not as content the parser took. A field the parser read as a name
reference (an interface `ip` entry, an OSPF area `range` entry) is recorded on
the parent row through the field the name went into.

F5.4: every row carries `source`, the report value of the source that holds the entry.
It is row data for the cross-source scan (`shadow_coverage.py`), not a printed field, so
the entry-line bytes are unchanged for a one-source run.

Report order is fixed: rows are sorted by line, then object type, then name, so
the same input produces the same bytes. The report names the source name only, never
the path (F4.2 rule 6); the path is in the provenance record (F5.3). The label is
`container_coverage.SOURCE_LABEL`.
"""

import re
import xml.etree.ElementTree as ET
from collections import Counter
from typing import Optional

import container_coverage
import resource_mapping
from container_coverage import ContainerRow
from xml_input import ParsedSource

# The destination kinds are container_coverage.DESTINATION_KINDS, which F4.3
# extended with `skipped` (an entry a parse method visited and did not model) and
# `unaccounted` (an entry no parse method read). One place defines the kinds.
DESTINATION_KINDS = container_coverage.DESTINATION_KINDS

# The kinds that write nothing for the entry. A row with one of these is a gap.
GAP_KINDS = ('count-only', 'skipped', 'unaccounted')

# Keys a parsed object carries that are not entry fields: the entry name and the
# four scope facts.
NON_FIELD_KEYS = frozenset({'name'}) | frozenset(container_coverage.SCOPE_FACT_KEYS)

# A field with no value is not a captured field (F4.3 rule 3), so the property scan and the
# state scan (F5.6) both drop it through this one definition.
EMPTY_FIELD_VALUES = (None, '', [], {}, ())

# Which report key each scope container fills. The container set is
# container_coverage.SCOPE_CONTAINERS, so this is the mapping, not a second rule.
REPORT_SCOPE_KEYS = {
    'device-group': 'device_group',
    'vsys': 'vsys',
    'templates': 'template',
    'devices': 'vsys_device',
}

REPORT_FILE = 'CONVERSION_REPORT.txt'
REPORT_HEADING = 'PER-ENTRY CONVERSION REPORT'
GAP_HEADING = 'Entries That Produced No Output'
PROPERTY_HEADING = 'Captured Properties No Output Read'

# One matrix row per emitted type, keyed by resource name, so the property scan can
# find the row that covers an entry. `row_detail` gives the resource name for the
# entry, so this is a lookup on the same name, not a second naming rule.
MATRIX_BY_RESOURCE = {row['resource']: row for row in resource_mapping.COVERAGE_MATRIX}


def name_field(resource_type: str) -> str:
    """The field a block of this type carries the entry name in (F6.5 decision 4).

    `DATA_SOURCE_SCHEMA` is the one place that says whether a type declares a `name` attribute. When
    it does not, the entry name reaches the block through the field that names the scope the type
    defines, and `REPORT_SCOPE_KEYS` is the one mapping from a scope container to that field:
    `device_group` for `panos_device_group_parent`. A type with neither fact keeps `name`, because
    the four `*_policy_rules` types state the name inside `location` and have no name field at the
    block's own level.

    The emitter prints the name through this rule, the import agreement gate (F6.4) reads it through
    this rule, and `tests/test_coverage_matrix.py` checks a block against it, so no second naming
    rule exists.
    """
    declares_name, _shape = resource_mapping.DATA_SOURCE_SCHEMA[resource_type]
    if declares_name:
        return 'name'
    return REPORT_SCOPE_KEYS.get(
        MATRIX_BY_RESOURCE[resource_type]['xml_element'].split('/')[0], 'name')


class RecordingDict(dict):
    """A captured entry object that records which keys an output reads from it (F4.4).

    `EntryLedger.mark` stores the object by reference, so this is the same object the
    parse method returned; only the read record is added. A key is recorded only while
    the ledger is recording, so a key the parse method read off the XML element does not
    count as a property the output used.
    """

    def __init__(self, ledger: 'EntryLedger', data: dict):
        super().__init__(data)
        self._ledger = ledger
        self._used: set = set()

    def _record(self, key):
        if self._ledger.recording and isinstance(key, str):
            self._used.add(key)

    def get(self, key, default=None):
        self._record(key)
        return super().get(key, default)

    def __getitem__(self, key):
        self._record(key)
        return super().__getitem__(key)

    def used_keys(self) -> tuple:
        """Keys an output read from this object, in sorted order."""
        return tuple(sorted(self._used))

    def value(self, key):
        """Read a captured value without recording the read (F5.6).

        The state scan is not an output, so a read through it must not count as a property an
        output used. `dict.get` is the base read, so the recording override is bypassed.
        """
        return dict.get(self, key)


RULE_PARAGRAPH = (
    'Rule: one line per config entry the parse pipeline read. One entry is one '
    '<entry name> element, not the lines it spans. An entry inside a '
    'config-object entry is a property level, so the property scan (F4.4) names '
    'its properties and the count shows on the parent row. Entries under '
    '`predefined` are PAN-OS built-in definitions, not operator objects (F4.2), so '
    'the report does not list them.'
)

GAP_RULE = (
    'An entry whose destination writes nothing is listed here. Some are recorded '
    'by design: an entry with no name is not an object, and a reference pointer '
    'has no content of its own. The rest are coverage gaps the converter cannot '
    'model.'
)

PROPERTY_RULE = (
    'Each matrix row names the properties its emitter reads. A property the parse '
    'captured that no output read for this entry is listed here. A finding is an '
    'operator action, not a broken output: it does not change the exit code, which '
    'the F4.1 gate still decides.'
)


def covering_row(section: str) -> Optional[ContainerRow]:
    """The table row that covers a section path.

    Matching uses `container_coverage.covers`, so this is the same rule F4.2
    pinned. The longest matching row wins, because a sub-shape row describes the
    entry more exactly than the general row for its container.
    """
    matches = [row for row in container_coverage.CONTAINER_TABLE
               if container_coverage.covers(row.path, section)]
    if not matches:
        return None
    return max(matches, key=lambda row: len(row.path))


def row_detail(row: ContainerRow) -> str:
    """Detail for a row: the resource type for an emitted row, the note otherwise."""
    types = re.findall(r'panos_[a-z0-9_]+', row.note)
    if row.destination in ('emitted', 'nested-block') and types:
        return types[0]
    return row.note


def matrix_row_for(section: str) -> Optional[dict]:
    """The matrix row that covers a section path (F4.4 scan scope).

    None when no row covers it, or when the covering row is not an emitted row: a
    report, inventory, bookkeeping, count-only, or nested-block destination has no
    matrix row, so the property scan and the shadow scan do not read an entry there.
    """
    container_row = covering_row(section)
    if container_row is None or container_row.destination != 'emitted':
        return None
    return MATRIX_BY_RESOURCE.get(row_detail(container_row))


class EntryLedger:
    """The marks one parse run made, and the report rows they produce."""

    def __init__(self, source: ParsedSource, parents: Optional[dict] = None):
        self.source = source
        self.parents = parents if parents is not None else container_coverage.parent_map(source.root)
        self._marks = {}
        # F4.4: the read record is only meaningful for an output, so it stays off during
        # the parse and the run turns it on before the first generator call.
        self.recording = False

    def start_recording(self) -> None:
        """Start recording which keys an output reads from a captured object (F4.4)."""
        self.recording = True

    # --- marks ---------------------------------------------------------------

    def mark(self, entry: ET.Element, captured: dict, detail: str = '',
             destination: Optional[str] = None) -> dict:
        """Record what a parse method took from an entry, and return the object.

        `captured` is stored as a `RecordingDict`, so a field a method adds after the
        mark is still in the report, and the object also records the keys an output
        reads from it (F4.4).
        """
        if captured.get('report_only') and destination is None:
            # report_only is an entry fact, not a container fact, so the mark wins
            # over the table row (F4.3 AC-2.4).
            destination = 'report'
        recorded = RecordingDict(self, captured)
        self._marks[id(entry)] = {'entry': entry, 'captured': recorded,
                                  'detail': detail, 'destination': destination}
        return recorded

    def mark_skipped(self, entry: ET.Element, reason: str) -> None:
        """Record an entry a parse method visited and did not model."""
        self._marks[id(entry)] = {'entry': entry, 'captured': {},
                                  'detail': reason, 'destination': 'skipped'}

    def mark_for(self, entry: ET.Element) -> Optional[dict]:
        return self._marks.get(id(entry))

    def marked(self, entry: ET.Element) -> bool:
        return id(entry) in self._marks

    # --- rules -------------------------------------------------------------

    def entries(self) -> list:
        """Every `<entry>` element in the parsed tree, in document order."""
        return [element for element in self.source.root.iter() if element.tag == 'entry']

    def is_report_entry(self, entry: ET.Element) -> bool:
        """True when this entry is a report row: section level, not predefined.

        An entry inside a config-object entry is a property level (F4.2 AC-3.2),
        so the property matrix owns it and this report counts it on the parent row.
        `predefined` entries are PAN-OS definitions, not operator objects.
        An entry whose container is the envelope has no container the table can read
        (F5.4), so a file input writes no row for it; a per-scope source reads its root
        through the place rule, so its scope entry is a row.
        """
        container = self.parents.get(entry)
        if container is None:
            return False
        if container.tag in container_coverage.ENVELOPE and container is not self.source.root:
            return False
        if container_coverage.is_predefined(container, self.parents):
            return False
        return container_coverage.is_section(container, self.parents, self.source)

    def destination(self, entry: ET.Element) -> str:
        """Destination for one entry: the mark wins over the table row (F4.3 AC-2.4).

        F6.5: a scope entry is an object the output writes, so the table row alone decides. The
        `devices` entry stays `bookkeeping`, because no provider resource exists for a device.
        """
        mark = self.mark_for(entry)
        if mark and mark['destination']:
            return mark['destination']
        container = self.parents.get(entry)
        row = covering_row(container_coverage.section_path(container, self.parents, self.source))
        if row:
            return row.destination
        return 'unaccounted'

    def captured_fields(self, mark: Optional[dict]) -> tuple:
        """Keys the parse method kept for an entry, in sorted order (F4.3 AC-3)."""
        if not mark:
            return ()
        return tuple(sorted(
            key for key, value in mark['captured'].items()
            if key not in NON_FIELD_KEYS and value not in EMPTY_FIELD_VALUES
        ))

    def property_entry_count(self, entry: ET.Element) -> int:
        """Entries inside this entry. The property scan (F4.4) reports the properties;
        the entry row shows the count.

        The entry itself is not a property entry of itself.
        """
        return sum(1 for element in entry.iter()
                   if element.tag == 'entry' and element is not entry)

    def scope(self, entry: ET.Element) -> dict:
        """The scope facts the entry sits in, read from its scope ancestors.

        These are the keys the F3.9 grouping rule (`_report_scope_path`) uses, so the
        conversion report groups rows the same way the other reports do.

        A scope is an entry, not an attribute: the name of a device group, a template,
        or a device sits on the `<entry>` the scope container holds, so the walk has to
        read the entry that defines each scope, not the container above it.

        The container name comes from `container_coverage.container_tag` (F5.4), so a
        per-scope entry takes the declared scope as its fact instead of the fallback.
        """
        facts = dict.fromkeys(container_coverage.SCOPE_FACT_KEYS, '')
        node = entry
        while node is not None:
            container = self.parents.get(node)
            key = REPORT_SCOPE_KEYS.get(container_coverage.container_tag(node, self.parents, self.source))
            if key and node.get('name') and not facts[key] \
                    and container_coverage.is_scope_entry(node, self.parents, self.source):
                facts[key] = node.get('name')
            node = container
        return facts

    # --- rows --------------------------------------------------------------

    def row_for(self, entry: ET.Element) -> dict:
        """Build one report row."""
        container = self.parents.get(entry)
        path = container_coverage.section_path(container, self.parents, self.source)
        row = covering_row(path)
        mark = self.mark_for(entry)
        destination = self.destination(entry)
        if destination == 'unaccounted':
            detail = f'no parse method reads {path}'
        elif row:
            detail = row_detail(row)
        else:
            detail = ''
        if mark and mark['detail']:
            detail = f'{detail} - {mark["detail"]}' if detail else mark['detail']
        row_data = {'line': self.source.line_of(entry),
                    'source': self.source.name,
                    'container': path,
                    'name': entry.get('name') or '(no name)',
                    'destination': destination,
                    'detail': detail,
                    'fields': self.captured_fields(mark),
                    'property_entries': self.property_entry_count(entry)}
        row_data.update(self.scope(entry))
        return row_data

    def rows(self) -> list:
        """Report rows for the entries the parse pipeline read, in report order."""
        return sorted([self.row_for(entry) for entry in self.entries() if self.is_report_entry(entry)],
                      key=lambda row: (row['line'] or 0, row['container'], row['name']))

    def gaps(self) -> list:
        """Rows whose destination writes nothing for the entry."""
        return [row for row in self.rows() if row['destination'] in GAP_KINDS]

    def counts(self) -> Counter:
        counts = Counter(row['destination'] for row in self.rows())
        for kind in DESTINATION_KINDS:
            counts.setdefault(kind, 0)
        return counts

    def property_entry_total(self) -> int:
        return sum(row['property_entries'] for row in self.rows())

    def predefined_total(self) -> int:
        return sum(1 for entry in self.entries()
                   if self.parents.get(entry) is not None
                   and container_coverage.is_predefined(self.parents[entry], self.parents))

    def gap_count(self) -> int:
        return len(self.gaps())

    def property_findings(self) -> list:
        """Entries with a captured property no output read (F4.4), in report order.

        Scope is the entries a matrix row covers. An entry whose container row is a
        report, inventory, bookkeeping, count-only, or nested-block destination has no
        matrix row, so the scan does not report it; those field gaps are recorded in
        `backlog.md`. A property entry inside a config-object entry is in scope when its
        container maps to a matrix row.
        """
        findings = []
        for entry in self.entries():
            container = self.parents.get(entry)
            mark = self.mark_for(entry)
            if container is None or not mark or not isinstance(mark['captured'], RecordingDict):
                continue
            matrix_row = matrix_row_for(container_coverage.section_path(container, self.parents, self.source))
            if matrix_row is None:
                continue
            captured = set(self.captured_fields(mark))
            unused = tuple(sorted(captured - set(mark['captured'].used_keys())))
            if not unused:
                continue
            finding = self.row_for(entry)
            finding['resource'] = matrix_row['resource']
            finding['unused_properties'] = unused
            findings.append(finding)
        return sorted(findings, key=lambda row: (row['line'] or 0, row['container'], row['name']))


# --- wording ---------------------------------------------------------------
# The wording functions take a row dict, so the generator can group rows with the
# F3.9 scope rule (`TerraformGenerator._report_scope_path`) and print the scope in
# front of each line. Grouping stays in one place.

def entry_line(row: dict) -> str:
    """One report line: line, object type, name, destination, detail, captured fields."""
    name = f'{row["container"]}/{row["name"]}'
    line = f'{row["line"] if row["line"] is not None else 0}'
    parts = [f'  line {line:>4}  ', f'{name:<38} ', f'{row["destination"]:<12} ',
             f'{row["detail"]:<36} ']
    parts.append('captured: ' + (', '.join(row['fields']) if row['fields'] else 'name only'))
    if row['property_entries']:
        parts.append(f'  property entries: {row["property_entries"]}')
    if row.get('vsys'):
        parts.append(f'  [{row["vsys"]}]')
    return ''.join(parts).rstrip()


def summary_lines(ledger: EntryLedger) -> list:
    counts = ledger.counts()
    lines = [f'Per-entry report: {len(ledger.rows())} entries read']
    for kind in DESTINATION_KINDS:
        marker = '  (writes nothing: gap)' if kind in GAP_KINDS else ''
        lines.append(f'  {kind:<14} {counts[kind]}{marker}')
    lines.append(f'Property entries inside config-object entries: {ledger.property_entry_total()} '
                 f'(property scan: {len(ledger.property_findings())} entries with a property '
                 'no output read)')
    lines.append(f'predefined entries not listed: {ledger.predefined_total()}')
    return lines


def gap_lines(ledger: EntryLedger) -> list:
    return [entry_line(row) for row in ledger.gaps()]


def property_line(row: dict) -> str:
    """One property scan line: line, object type, name, the properties no output read."""
    name = f'{row["container"]}/{row["name"]}'
    line = f'{row["line"] if row["line"] is not None else 0}'
    parts = [f'  line {line:>4}  ', f'{name:<38} ', f'{row["resource"]:<32} ',
             'no output read: ' + ', '.join(row['unused_properties'])]
    if row.get('vsys'):
        parts.append(f'  [{row["vsys"]}]')
    return ''.join(parts).rstrip()


def console_lines(ledger: EntryLedger, scope_path) -> list:
    """Console wording for a run with gaps. Empty when there is nothing to say.

    `scope_path` is the F3.9 grouping rule, so a console line names the scope the
    report groups the entry under.
    """
    gaps = ledger.gaps()
    if not gaps:
        return []
    lines = [f'Per-entry report gaps ({len(gaps)}):']
    for row in gaps:
        scope = ' / '.join(label if not value else f'{label}: {value}'
                           for _level, label, value in scope_path(row))
        name = f'{row["container"]}/{row["name"]}'
        line = row['line'] if row['line'] is not None else 'position unknown'
        detail = row['detail'] or 'no detail'
        fields = ', '.join(row['fields']) or 'name only'
        parts = [f'  - {scope}  line {line}  {name}  {row["destination"]}  {detail}  captured: {fields}']
        if row['property_entries']:
            parts.append(f'  property entries: {row["property_entries"]}')
        lines.append(''.join(parts))
    return lines
