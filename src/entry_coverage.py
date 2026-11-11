"""F4.3 per-entry coverage: what the parser read from each entry, and where it went.

Five rules, stated once here.

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
3. The destination. `EntryLedger.destination` is the one place that answers a destination, in this
   order: the per-entry fact on the recorded object (`report_only` content is `report`), then the
   destination the mark recorded, then the container table row. `mark` records what the parse method
   took and only the destination the caller states, so it states no destination of its own. The fact
   is read at read time through `RecordingDict.value()`, so the decision records no property use and
   the order of `mark` and the field cannot change the answer.
4. The property scan (F4.4). The matrix row for an emitted container names the
   properties its emitter reads. A captured property that no output read for this
   entry is a gap, and the scan reports it. The scan measures reads at run time:
   the object a mark stores records every key an output reads from it, and the
   record starts after the parse, so a key the parse method read off the XML
   element is not a property the output used.
5. The run view (F8.9). A run may read more than one response, so `RunView` answers rules 1 to 4 for the
   set: each protocol answer goes to the ledger that holds the entry, and the parse answers are joined in
   the run order the entry point decided. The view states no rule of its own and takes the join as an
   argument, so a run that read one response is answered the same as that response's own ledger.

The entry name (F2.3) and the five scope facts (F3.1, F3.2, F6.10.5) are not captured
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

The report line shape and the fact phrases are stated here. The console line shape is stated in one
place, `container_coverage.console_line`, so the console wording here builds the parts and calls it:
this module states no second shape (`docs/ARCHITECTURE.md` §3.2).

The captured part of a line is the shape `captured_part` states: a row that reaches another output names
the fields it captured, and a row whose kind has no other output prints the value of each field it names,
read through the captured object. `docs/COVERAGE_MATRIX.md` §1 owns that rule, and
`tests/test_property_coverage.py::test_the_report_line_reads_the_region_addresses_it_prints` pins it.

A `bookkeeping` row records a relation between an entry and the container that lists it, so the entry carries no
value for it and the captured part names no field. The shape is `NAMES_NO_FIELD_KINDS`, and
`tests/test_property_coverage.py::test_the_bookkeeping_line_names_no_field_for_the_membership_entry_it_marks`
pins it. The relation is the `detail` column, and the value of the relation is printed by the block of the entry
that owns the container, through the row that covers that entry.
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

# The gap kind whose report line must print a value, because the line is the only output its entry
# reaches (`docs/COVERAGE_MATRIX.md` §1). A `count-only` row has no matrix row, so no property finding
# can name it, and it has no report section, so the entry line is the only place its captured field can
# be read. The other two gap kinds have no captured object to print: `mark_skipped` records an empty
# object, and an `unaccounted` entry has no mark.
PRINTS_VALUE_KINDS = ('count-only',)

# The kind whose report line names no field, because the fact its row records is a relation between the entry and
# the container that lists it (`docs/COVERAGE_MATRIX.md` §1). The entry carries no value for a relation, so the
# line states the row identity only. The relation itself is the `detail` column, and the value belongs to the entry
# that owns the container. Stated as a data set, in the same shape as `PRINTS_VALUE_KINDS`, so no writer branch
# decides the captured part per kind.
NAMES_NO_FIELD_KINDS = ('bookkeeping',)

# Keys a parsed object carries that are not entry fields: the entry name and the
# five scope facts.
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
    'template-stack': 'template_stack',
}

REPORT_FILE = 'CONVERSION_REPORT.txt'
REPORT_HEADING = 'PER-ENTRY CONVERSION REPORT'
GAP_HEADING = 'Entries That Produced No Output'
PROPERTY_HEADING = 'Captured Properties No Output Read'

# The two words a fact part starts with, stated once so the report line and the console line state the
# same fact (`docs/ARCHITECTURE.md` §3.2).
CAPTURED_LABEL = 'captured'
NO_OUTPUT_READ = 'no output read'

# One matrix row per emitted type, keyed by resource name, so the property scan can
# find the row that covers an entry. `row_detail` gives the resource name for the
# entry, so this is a lookup on the same name, not a second naming rule.
MATRIX_BY_RESOURCE = {row['resource']: row for row in resource_mapping.COVERAGE_MATRIX}


def protocol_report_rows(ledger: 'EntryLedger') -> list:
    """The protocol entries the emitter cannot express (F7.1), in report order.

    A peer no peer group names, and an interface at the OSPF level: `PROTOCOL_SHAPE` states no provider
    field for either, so the parse marks them for the report. The destination comes from the ledger, which
    is the one record, so no second list names these entries. The row carries the captured object, and the
    report reads the fields it prints, so the property scan counts those reads as an output use.
    """
    rows = []
    for entry in ledger.entries():
        mark = ledger.mark_for(entry)
        container = ledger.parents.get(entry)
        if not mark or container is None or ledger.destination(entry) != 'report':
            continue
        path = container_coverage.section_path(container, ledger.parents, ledger.source_of(entry))
        if '/protocol/' not in '/' + path:
            continue
        # `row_for` carries the captured object, so the report can read through it.
        row = ledger.row_for(entry)
        # The entry is a property level of a router, so the report names the router it belongs to: the
        # ancestor entry the router container holds, which is the block the `.tf` writes.
        node = entry
        while node is not None:
            parent = ledger.parents.get(node)
            if parent is not None and parent.tag.endswith('router'):
                break
            node = parent
        row['router'] = node.get('name') if node is not None else ''
        row['level'] = path.rsplit('/', 1)[-1]
        rows.append(row)
    return sorted(rows, key=lambda row: (row['line'] or 0, row['container'], row['name']))


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

    F7.14: a type `DATA_SOURCE_SCHEMA` has no row for is a resource-only type, so the name fact comes from
    `RESOURCE_NAME_FIELDS`, the table that states it for those two types.
    """
    row = resource_mapping.DATA_SOURCE_SCHEMA.get(resource_type)
    if row is None:
        return resource_mapping.RESOURCE_NAME_FIELDS[resource_type]
    declares_name, _shape = row
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

    # --- the source part -----------------------------------------------------
    # F8.9: a run may have read more than one response, so the source part is answered through a method
    # rather than the attribute, and `RunView` answers the same method for its set. A single ledger holds
    # one response, so its answer is itself, and a one-response run is unchanged.

    def parts(self) -> list:
        """The responses the run read, in run order. One ledger holds one response, so this is itself."""
        return [self]

    def source_of(self, entry: ET.Element) -> ParsedSource:
        """The source that holds this entry (F5.4, F8.9). For one ledger that is its own source."""
        return self.source

    def line_of(self, entry: ET.Element) -> Optional[int]:
        """The line this entry's response names, read through the source that holds it (F4.2 rule 5)."""
        return self.source.line_of(entry)

    # --- marks ---------------------------------------------------------------

    def mark(self, entry: ET.Element, captured: dict, detail: str = '',
             destination: Optional[str] = None) -> dict:
        """Record what a parse method took from an entry, and return the object.

        `captured` is stored as a `RecordingDict`, so a field a method adds after the
        mark is still in the report, and the object also records the keys an output
        reads from it (F4.4). The destination is what the caller states: `mark` states
        no destination of its own, so a per-entry fact on the object answers through
        `EntryLedger.destination` at read time.
        """
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
        """The destination for one entry, answered in one place, in this order.

        1. The per-entry fact on the recorded object: `report_only` content answers `report`. The read
           is through `RecordingDict.value()`, so the decision records no property use, and a field the
           parse method adds after the mark is still the recorded fact.
        2. The destination `mark` recorded, which is what the caller stated.
        3. The container table row.

        F6.5: a scope entry is an object the output writes, so the table row alone decides. The
        `devices` entry stays `bookkeeping`, because no provider resource exists for a device.
        """
        mark = self.mark_for(entry)
        if mark:
            # `mark_skipped` records no object, so the fact answers only for a mark that holds the
            # recorded object, and the mark's destination answers for a skipped entry.
            recorded = mark['captured']
            if isinstance(recorded, RecordingDict) and recorded.value('report_only'):
                return 'report'
            if mark['destination']:
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
        row_data = {'line': self.line_of(entry),
                    'source': self.source_of(entry).name,
                    'container': path,
                    'name': entry.get('name') or '(no name)',
                    'destination': destination,
                    'detail': detail,
                    'fields': self.captured_fields(mark),
                    # The captured object itself, so a report line can read a value through the recorded
                    # read (F4.4): `fields` is the names, and the row must carry the object to print a value.
                    'captured': mark['captured'] if mark else {},
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


# --- the run view (F8.9, `docs/API_CONVERSION_PATH.md` §6) ---------------------

class RunPart:
    """One response the run read, and the tables its parse methods answered.

    A part is the source the door returned, the request that read it, the parser that reads it, and the
    answers its parse methods gave. `answer` fills once, so the run parses a response once. The run order
    is the entry point's decision, so nothing here decides it.
    """

    def __init__(self, source: ParsedSource, request, parser, results: Optional[dict] = None):
        self.source = source
        self.request = request
        self.parser = parser
        self.results = results if results is not None else {}

    def answer(self, name: str):
        """The table one parse method answers for this response, built once."""
        if name not in self.results:
            self.results[name] = getattr(self.parser, name)()
        return self.results[name]

    def ledger(self) -> EntryLedger:
        """The ledger this response's parse wrote."""
        return self.parser.ledger


class RunView:
    """The entry protocol answered across the responses one run read (F8.9).

    The view holds the parts in run order and answers each protocol method through the ledger that holds
    the entry, so the protocol has one answer for a run that read many responses and the same answer as a
    single ledger for a run that read one. It states no row shape, no field name, no naming rule, no sort
    rule, no writer, no console line, and no environment name: every answer is the owner's answer.

    It builds no tree across responses, because F8.5 keeps one line map and one parent map per response.
    `parents` is the merged answer of the per-response maps, so an entry's parents are the parents of the
    response that holds it, and no parent crosses a response.

    The join is an argument, because the cross-response merge is the entry point's decision: this module
    states no merge rule, and `api_requests.py` states none either. A run that read one response gets each
    answer unchanged, so path 1 is unchanged.
    """

    def __init__(self, parts, join):
        self.ordered = list(parts)
        self.join = join
        # Which response holds each entry, so a protocol answer goes to the ledger that read it. The key is
        # the element identity, the same key the marks and the parent map use.
        self.holder = {}
        for part in self.ordered:
            for entry in part.ledger().entries():
                self.holder[id(entry)] = part
        # The parent facts, merged in run order. Not a merged tree: each response keeps its own map.
        self.parents = {}
        for part in self.ordered:
            self.parents.update(part.ledger().parents)

    def parts(self) -> list:
        """The responses the run read, in run order."""
        return list(self.ordered)

    def sources(self) -> list:
        """The sources the run read, in run order, one per response."""
        return [part.source for part in self.ordered]

    def ledger_for(self, entry: ET.Element) -> EntryLedger:
        """The ledger that holds this entry."""
        return self.holder[id(entry)].ledger()

    # --- the entry protocol, answered through the ledger that holds the entry ---

    def entries(self) -> list:
        """Every entry the run read, in run order. This states no sort rule of its own."""
        return [entry for part in self.ordered for entry in part.ledger().entries()]

    def row_for(self, entry: ET.Element) -> dict:
        return self.ledger_for(entry).row_for(entry)

    def mark_for(self, entry: ET.Element) -> Optional[dict]:
        return self.ledger_for(entry).mark_for(entry)

    def destination(self, entry: ET.Element) -> str:
        return self.ledger_for(entry).destination(entry)

    def is_report_entry(self, entry: ET.Element) -> bool:
        return self.ledger_for(entry).is_report_entry(entry)

    def line_of(self, entry: ET.Element) -> Optional[int]:
        return self.ledger_for(entry).line_of(entry)

    def source_of(self, entry: ET.Element) -> ParsedSource:
        return self.ledger_for(entry).source_of(entry)

    def scope(self, entry: ET.Element) -> dict:
        return self.ledger_for(entry).scope(entry)

    # --- the parse answers, joined in run order through the join the run was given ---

    def parse(self, name: str):
        """One parse method answered per response, joined in run order."""
        return self.join([part.answer(name) for part in self.ordered])

    def rows(self) -> list:
        """Report rows for the entries the run read, in run order."""
        return self.join([part.ledger().rows() for part in self.ordered])

    def gaps(self) -> list:
        return self.join([part.ledger().gaps() for part in self.ordered])

    def counts(self) -> Counter:
        return Counter(self.join([part.ledger().counts() for part in self.ordered]))

    def property_findings(self) -> list:
        return self.join([part.ledger().property_findings() for part in self.ordered])

    def property_entry_total(self) -> int:
        return self.join([part.ledger().property_entry_total() for part in self.ordered])

    def predefined_total(self) -> int:
        return self.join([part.ledger().predefined_total() for part in self.ordered])

    def gap_count(self) -> int:
        return len(self.gaps())

    def start_recording(self) -> None:
        """Turn on the read record for every response the run read (F4.4)."""
        for part in self.ordered:
            part.ledger().start_recording()


# --- wording ---------------------------------------------------------------
# The wording functions take a row dict, so the generator can group rows with the
# F3.9 scope rule (`TerraformGenerator._report_scope_path`) and print the scope in
# front of each line. Grouping stays in one place.
#
# The report line shapes are the fixed-width ones `docs/ARCHITECTURE.md` §3.2 states. The console line
# shape is stated in one place, `container_coverage.console_line`, so the functions here build only the
# parts: the identity, the position, the scope, and the fact. A console line has no room for the
# fixed-width matrix-row column, so the matrix row stays in the report.

# The row identity the report names: object type, then entry name (F4.3 rule 2). The console line names
# the same identity, so a console line and a report row name the same entry.
def entry_identity(row: dict) -> str:
    return f'{row["container"]}/{row["name"]}'


def report_value(value) -> str:
    """One captured value as a report line prints it.

    A list is the members in the order the parse kept them; anything else is the text the parse stored.
    One shape, so the entry line prints a value the way the report sections print it.
    """
    if isinstance(value, (list, tuple)):
        return '[' + ', '.join(str(item) for item in value) + ']'
    return str(value)


def captured_part(row: dict) -> str:
    """The captured part of a report line, in the sorted field order the report already uses (F4.3 rule 4).

    A row that reaches another output names the fields it captured, so the line keeps the names. A row
    whose kind prints a value (`PRINTS_VALUE_KINDS`, `docs/COVERAGE_MATRIX.md` §1) has no other output, so
    the line is the only output its entry reaches and it prints each field's value, read through the
    captured object: that read is the property use the property scan counts. A row whose kind names no field
    (`NAMES_NO_FIELD_KINDS`, the same §1 rule) records a relation the entry carries no value for, so the line
    states the row identity only. A row with no captured field says `name only`, because a field the entry
    carries no value for is not a captured field (F4.3 rule 3).
    """
    fields = row['fields']
    if not fields or row['destination'] in NAMES_NO_FIELD_KINDS:
        return f'{CAPTURED_LABEL}: name only'
    captured = row.get('captured')
    if row['destination'] not in PRINTS_VALUE_KINDS or not captured:
        return f'{CAPTURED_LABEL}: ' + ', '.join(fields)
    return f'{CAPTURED_LABEL}: ' + ', '.join(
        f'{key}={report_value(captured.get(key))}' for key in fields)


def entry_line(row: dict) -> str:
    """One report line: line, object type, name, destination, detail, captured fields."""
    line = f'{row["line"] if row["line"] is not None else 0}'
    parts = [f'  line {line:>4}  ', f'{entry_identity(row):<38} ', f'{row["destination"]:<12} ',
             f'{row["detail"]:<36} ']
    parts.append(captured_part(row))
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
    """One property scan line: line, object type, name, the properties no output read.

    The matrix row is a fixed-width column, so it is on the report line and not on the console line
    (`docs/ARCHITECTURE.md` §3.2).
    """
    line = f'{row["line"] if row["line"] is not None else 0}'
    parts = [f'  line {line:>4}  ', f'{entry_identity(row):<38} ', f'{row["resource"]:<32} ',
             property_fact(row)]
    if row.get('vsys'):
        parts.append(f'  [{row["vsys"]}]')
    return ''.join(parts).rstrip()


def property_fact(row: dict) -> str:
    """The fact part for a property finding: the properties no output read.

    The scan measures the keys of the object the parse method built (F4.3 rule 4), so the console line
    names them as parsed-object key names, never as an XML tag.
    """
    return f'{NO_OUTPUT_READ}: ' + ', '.join(row['unused_properties'])


def gap_fact(row: dict) -> str:
    """The fact part for a gap row: the destination, the detail, the captured part, and the count.

    The fact is the words the report line already uses for the same finding (`docs/ARCHITECTURE.md` §3.2),
    so the console and the report cannot disagree. Captured fields are the parsed-object key names
    (F4.3 rule 5), so a console line may name them, and a row whose kind prints a value prints the value.
    """
    fact = f'{row["destination"]}  {row["detail"] or "no detail"}  {captured_part(row)}'
    if row['property_entries']:
        fact += f'  property entries: {row["property_entries"]}'
    return fact


def console_lines(ledger: EntryLedger, scope_path) -> list:
    """The console block for the gap rows: the header, then one line per gap.

    Empty when there is nothing to say, so a run with no gap prints nothing new. `scope_path` is the
    F3.9 grouping rule, so a console line names the scope the report groups the entry under.
    """
    gaps = ledger.gaps()
    if not gaps:
        return []
    lines = [f'Per-entry report gaps ({len(gaps)}):']
    lines.extend(container_coverage.console_line(container_coverage.scope_part(row, scope_path),
                                                 container_coverage.position_part(row['line']),
                                                 entry_identity(row), gap_fact(row))
                 for row in gaps)
    return lines


def property_console_lines(findings: list, scope_path) -> list:
    """The console block for the property findings: the header, then one line per finding.

    Empty when there is nothing to say, so a run with no property finding prints nothing new. The line
    names no matrix row, so the block names the entry and the fact and the report keeps the row.
    """
    if not findings:
        return []
    lines = [f'Property findings ({len(findings)}):']
    lines.extend(container_coverage.console_line(container_coverage.scope_part(row, scope_path),
                                                 container_coverage.position_part(row['line']),
                                                 entry_identity(row), property_fact(row))
                 for row in findings)
    return lines
