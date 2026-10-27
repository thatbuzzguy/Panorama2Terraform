"""F5.4 cross-source shadow scan: a child entry name that repeats a parent entry name.

Three rules, stated once here.

1. The shadow fact. A child entry is a shadow when its name repeats a parent entry
   name, and both entries are covered by the same matrix row. The matrix row is the
   key, not the entry name alone, so a shadow is a fact within one container kind:
   an address named Web-Server-1 that inherits a shared address of the same name is a
   shadow, and a service group with the same name is not.
2. The scan scope is the F4.4 rule, unchanged: only an entry a matrix row covers is a
   finding. The parent source is read with the same container helpers and the same
   row rule, so there is no second naming rule here. A run with no declared parent
   source has no parent to read, so it reports no shadow.
3. Report order is fixed: findings are sorted by line, then object type, then name, so
   the same two sources produce the same bytes. A finding is an operator action, not a
   broken output, so it does not change the exit code, which the F4.1 gate decides.

Why the parent source is needed: a per-device-group run cannot see the parent, so an
inherited name stays a plain string in the child object and the parent entry is
invisible. The declared parent source makes the name visible, and this scan names it.

Usage:
    from shadow_coverage import shadow_findings, shadow_line
    findings = shadow_findings(ledger, parent_ledger)
    for finding in findings:
        print(shadow_line(finding))
"""

import entry_coverage

SHADOW_HEADING = 'Entries That Repeat a Parent Entry Name'

SHADOW_RULE = (
    'A child entry whose name repeats a parent entry name in the same matrix row is '
    'listed here. A per-device-group run cannot see its parent, so the parent source '
    'the run declares is what makes the inherited name visible. A finding is an '
    'operator action, not a broken output: it does not change the exit code, which the '
    'F4.1 gate still decides.'
)


def parent_index(parent_ledger) -> dict:
    """The parent entries a matrix row covers, keyed by (matrix row, entry name).

    Report order, so the first parent row wins when two parent entries share a key:
    two parent entries in two scopes can carry the same name, and one child entry is
    one finding. A parent entry no matrix row covers is not in the index, because the
    scan scope is the F4.4 rule.
    """
    index = {}
    for row in parent_ledger.rows():
        matrix_row = entry_coverage.matrix_row_for(row['container'])
        if matrix_row is None:
            continue
        index.setdefault((matrix_row['resource'], row['name']), row)
    return index


def shadow_findings(ledger, parent_ledger) -> list:
    """Child entries whose name repeats a parent entry name, in report order.

    Both ledgers are read through the same row rule (`entry_coverage`), so the matrix
    row that covers a child entry is the same row that covers the parent entry. Each
    finding is the child row, plus the matrix row and the parent source by its report
    value.
    """
    if parent_ledger is None:
        return []
    index = parent_index(parent_ledger)
    findings = []
    for row in ledger.rows():
        matrix_row = entry_coverage.matrix_row_for(row['container'])
        if matrix_row is None:
            continue
        parent = index.get((matrix_row['resource'], row['name']))
        if parent is None:
            continue
        finding = dict(row)
        finding['resource'] = matrix_row['resource']
        finding['parent_source'] = parent_ledger.source.name
        finding['parent_line'] = parent['line']
        findings.append(finding)
    return sorted(findings, key=lambda row: (row['line'] or 0, row['container'], row['name']))


def shadow_line(finding: dict) -> str:
    """One shadow line: the child entry, the matrix row that covers it, the parent entry.

    The shape is fixed (F5.4 AC-4.2), and the section prints no path: a source is named
    by its report value, the same rule the other report bodies follow (F4.2 rule 6).
    """
    name = f'{finding["container"]}/{finding["name"]}'
    line = f'{finding["line"] if finding["line"] is not None else 0}'
    parent_line = finding['parent_line'] if finding['parent_line'] is not None else 0
    parts = [f'  line {line:>4}  ', f'{name:<38} ', f'{finding["resource"]:<32} ',
             f'parent source: {finding["parent_source"]} (parent line {parent_line})']
    return ''.join(parts).rstrip()
