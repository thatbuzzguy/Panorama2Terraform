"""F5.4 cross-source shadow scan: a child entry name that repeats a parent entry name.

Three rules, stated once here.

1. The shadow fact. A child entry is a shadow when its name repeats a parent entry
   name, and both entries are covered by the same matrix row. The key is the project's
   one identity key rule (`state_coverage.ownership_key`) read with the facts the parent
   row declares, so it names the parent scope. The scan compares a child entry with the
   matrix row and entry name part of that key, because the child names its own scope: the
   fact is that one name sits in two scopes. So an address named Web-Server-1 that repeats
   a shared address of the same name is a shadow, and a service group with the same name
   is not.
2. The scan scope is the F4.4 rule, unchanged: only an entry a matrix row covers is a
   finding. The parent source is read with the same container helpers and the same row
   rule, so there is no second naming rule here. A run with no declared parent source has
   no parent to read, so it reports no shadow.
3. One finding names one parent entry. Identity is unique per entry, so two parent entries
   that carry the same name in two scopes are two keys, and a child entry that matches
   both gives one finding per parent entry: no parent entry is dropped. Report order is
   fixed: findings are sorted by line, then object type, then name, then the parent entry
   the finding names in the parent report order, so the same two sources produce the same
   bytes. A finding is an operator action, not a broken output, so it does not change the
   exit code, which the F4.1 gate decides.

Why the parent source is needed: a per-device-group run cannot see the parent, so an
inherited name stays a plain string in the child object and the parent entry is
invisible. The declared parent source makes the name visible, and this scan names it.

Usage:
    from shadow_coverage import shadow_findings, shadow_line, console_lines
    findings = shadow_findings(ledger, parent_ledger)
    for finding in findings:
        print(shadow_line(finding, report_scope_path))      # the report line, names the parent entry
    for line in console_lines(findings, report_scope_path):  # the console block, one line per finding
        print(line)

The report line shape is fixed below, and the console line shape is stated once in
`container_coverage.console_line`: this module states its fact phrase and its block header and calls that
function, so it defines no second shape. The parent entry is a second identity, so it stays in the report.
"""

import container_coverage
import entry_coverage
import state_coverage

SHADOW_HEADING = 'Entries That Repeat a Parent Entry Name'

# The fact phrases a shadow line states, on the report and on the console, so the two cannot disagree.
# The source is named by its report value, never by its path (F4.2 rule 6): the path is in the record.
PARENT_SOURCE_LABEL = 'parent source'
PARENT_ENTRY_LABEL = 'parent entry'

SHADOW_RULE = (
    'A child entry whose name repeats a parent entry name in the same matrix row is '
    'listed here. A per-device-group run cannot see its parent, so the parent source '
    'the run declares is what makes the inherited name visible. A finding is an '
    'operator action, not a broken output: it does not change the exit code, which the '
    'F4.1 gate still decides.'
)


def parent_index(parent_ledger) -> dict:
    """The parent entries a matrix row covers, keyed by identity.

    The key is the one identity key rule (`state_coverage.ownership_key`) read with the facts the parent
    row declares, so the key names the parent scope. Identity is unique per entry, so one key is one
    parent entry, and two parent entries that carry the same name in two scopes are two keys. The scan
    compares a child entry with the first two positions of the key, which is the part the shadow fact
    reads: the matrix row and the entry name. Insertion order is the parent report order, so the findings
    for one child entry follow the order the parent report reads. A parent entry no matrix row covers is
    not in the index, because the scan scope is the F4.4 rule.
    """
    index = {}
    for row in parent_ledger.rows():
        matrix_row = entry_coverage.matrix_row_for(row['container'])
        if matrix_row is None:
            continue
        index[state_coverage.ownership_key(matrix_row['resource'], row['name'], row)] = row
    return index


def shadow_findings(ledger, parent_ledger) -> list:
    """Child entries whose name repeats a parent entry name, in report order.

    Both ledgers are read through the same row rule (`entry_coverage`), so the matrix row that
    covers a child entry is the same row that covers the parent entry. Each finding is the child row,
    plus the parent key, the parent entry the child repeats, the matrix row, and the parent source by
    its report value. One finding per parent entry, so a child entry that matches parent entries in
    two scopes gives one finding for each.

    Report order is the child position, then object type, then name, then the parent entry the finding
    names in the parent report order, because a child entry can name more than one parent entry.
    """
    if parent_ledger is None:
        return []
    index = parent_index(parent_ledger)
    findings = []
    for row in ledger.rows():
        matrix_row = entry_coverage.matrix_row_for(row['container'])
        if matrix_row is None:
            continue
        name_part = (matrix_row['resource'], row['name'])
        for key, parent in index.items():
            if key[:2] != name_part:
                continue
            finding = dict(row)
            finding['resource'] = matrix_row['resource']
            finding['parent_key'] = key
            finding['parent'] = parent
            finding['parent_source'] = parent_ledger.source.name
            finding['parent_line'] = parent['line']
            findings.append(finding)
    return sorted(findings, key=lambda finding: (finding['line'] or 0, finding['container'],
                                                 finding['name'], parent_position(finding)))


def parent_position(finding: dict) -> tuple:
    """The parent entry's report position, which is the report order tie-break for a finding."""
    parent = finding['parent']
    return (parent['line'] or 0, parent['container'], parent['name'])


def parent_entry_part(finding: dict, scope_path) -> str:
    """Which parent entry the child repeats: the parent scope, then the parent entry identity.

    The scope is read through the F3.9 grouping rule, the same rule the report section header and the
    console line use, so no second scope rule, and the identity is the F4.3 row identity. Both come from
    the parent row the finding names, which is the key read as data. A finding the report does not group
    prints the identity alone.
    """
    parent = finding['parent']
    identity = entry_coverage.entry_identity(parent)
    scope = container_coverage.scope_part(parent, scope_path)
    return f'{scope} / {identity}' if scope else identity


def shadow_fact(finding: dict) -> str:
    """The fact part for a shadow: the source that holds the parent entry, by its report value.

    The minimum actionable field, because the operator's action for a shadow is to open the source that
    holds the parent entry, and the name is what identifies it. A console line cannot carry the
    provenance record (F5.3), so the path, the kind, the request, the cache entry, the size and the hash
    stay in `SOURCE.txt`, and the parent entry and the parent line stay in the report, because the shape
    names one position and one identity. Pinned by `tests/test_shadow_coverage.py`.
    """
    return f'{PARENT_SOURCE_LABEL}: {finding["parent_source"]}'


def shadow_line(finding: dict, scope_path) -> str:
    """One shadow line: the child entry, the matrix row that covers it, the parent entry, the parent source.

    The shape is fixed (F5.4 AC-4.2), and the section prints no path: a source is named
    by its report value, the same rule the other report bodies follow (F4.2 rule 6). The parent entry
    field names which parent entry the child repeats, because the child identity and the parent identity
    are the same text when the name repeats: only the parent scope tells them apart.
    """
    line = f'{finding["line"] if finding["line"] is not None else 0}'
    parent_line = finding['parent_line'] if finding['parent_line'] is not None else 0
    parts = [f'  line {line:>4}  ', f'{entry_coverage.entry_identity(finding):<38} ',
             f'{finding["resource"]:<32} ',
             f'{PARENT_ENTRY_LABEL}: {parent_entry_part(finding, scope_path)}  ',
             f'{PARENT_SOURCE_LABEL}: {finding["parent_source"]} (parent line {parent_line})']
    return ''.join(parts).rstrip()


def console_lines(findings: list, scope_path) -> list:
    """The console block for the shadows: the header, then one line per finding.

    Empty when there is nothing to say, so a run with no declared parent prints nothing new. The line
    names the child entry and the parent source name, and it names no matrix row, no parent entry and no
    parent line, because the console shape has no room for them (`docs/ARCHITECTURE.md` §3.2).
    """
    if not findings:
        return []
    lines = [f'Shadow findings ({len(findings)}):']
    lines.extend(container_coverage.console_line(container_coverage.scope_part(finding, scope_path),
                                                 container_coverage.position_part(finding['line']),
                                                 entry_coverage.entry_identity(finding), shadow_fact(finding))
                 for finding in findings)
    return lines
