"""F4.1: post-run sanity gate.

Every rule this module enforces is stated once here. The tests call these
functions instead of restating a rule, so the gate that runs during a
conversion and the gate that runs during a test cannot disagree.

The checks read what the operator receives: the files written to the output
directory. A rule is satisfied by a file, not by a bookkeeping value that
never reached one. The block rules read the `.tf` files; the data rule (F6.8)
reads the four data files, and the site record's printed form, through the
module that owns each row shape, so no second shape rule appears.

The round-trip cross-check is the one exception to that boundary, because its fact compares two sets:
the `.tf` block set it read, and the entry set the parse read through the run's ledger (`docs/ARCHITECTURE.md`
§4.6). It reads no report and no data file, and a call with no ledger reports the check as NOT RUN, so a
rule that reads only the output directory is unchanged. Its finding is a coverage fact, not a broken
output, so it is a WARN and the exit code still follows the rules that read the files.

F6.10.1 (`docs/CODEBASE_ASSEMBLY.md` §14) states which set each rule reads: the block rules read the
`.tf` files of one unit, keyed by the path from the codebase root, and the data rule reads the records at
the root as one rule over the rows of every unit. No rule reads a report. F6.10.3 lands that shape: the
run writes one directory per unit, so the path a finding names is the unit directory plus the file name,
and the plan check runs once per unit directory.

Checks, in report order:

| Check | Rule | Severity |
|---|---|---|
| `emitted_types` | every resource type is in `EMITTED_TYPES` | FAIL |
| `location_present` | every `resource` and `data` block carries a `location` block | FAIL |
| `data_blocks` | every `data` block matches the `DATA_SOURCE_SCHEMA` row for its type | FAIL |
| `import_blocks` | every `import` block agrees with the `resource` block it names | FAIL, WARN |
| `scope_blocks` | a name inside a scope block's `location` names a scope this run declares | FAIL |
| `actions` | every `action` block matches its `ACTION_SCHEMA` row inside `config` and names one unit | FAIL |
| `protocol_object` | a `protocol` object on a `panos_virtual_router` block matches its `PROTOCOL_SHAPE` row | FAIL |
| `filter_blocks` | a filter container block matches its `FILTER_SHAPE` row | FAIL |
| `certificate_blocks` | a certificate block matches its `CERTIFICATE_SHAPE` row | FAIL |
| `references` | every `.name` reference resolves to a block declared in the same run, by kind | FAIL |
| `variables` | a declared variable has a `var.` consumer, and a `var.` consumer names a declared variable | FAIL |
| `data_files` | every data file reads as its declared rows and agrees with the rules that produced it (F6.8) | FAIL |
| `round_trip` | the block set agrees with the entry set the run's ledger read, per unit and row | WARN, or NOT RUN |
| `control_chars` | no raw control character or DEL in a `.tf` file | FAIL |
| `placeholders` | an expected placeholder is listed so the operator replaces it | WARN |
| `terraform` | `terraform init` + `terraform validate` (`--validate` only) | FAIL or SKIPPED |

Exit code: 0 when no finding is FAIL, 1 when one is. A WARN and a SKIPPED do
not fail the gate, so a run that only needs an operator action still exits 0
and an offline run still reports the checks it could not run.

One reader serves every block kind, so a rule that covers more than one kind
reads the same block text. A block is reported once for a fact: the presence of
a `location` block is the `location_present` rule for both kinds, so the `data`
rule reports the shape inside the block and not the missing block.
"""

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import commit_actions
import container_coverage
import entry_coverage
import import_blocks
import naming
import ownership
import reference_edges
import resource_mapping
import site_data
import unit_manifest
import write_path

FAIL = 'FAIL'
WARN = 'WARN'
SKIP = 'SKIPPED'
NOT_RUN = 'NOT RUN'

# Report order. The order is fixed so the report is byte-identical between runs.
CHECK_ORDER = (
    'emitted_types',
    'location_present',
    'data_blocks',
    'import_blocks',
    'scope_blocks',
    'actions',
    'protocol_object',
    'filter_blocks',
    'certificate_blocks',
    'references',
    'variables',
    'data_files',
    'round_trip',
    'control_chars',
    'placeholders',
    'terraform',
)

REPORT_RULE = '=' * 80

# A block header, for every block kind a gate rule reads. The body ends at the
# first column-0 brace, which is how the generator writes a block and how the
# existing tests read one. F5.5 reads `data`; Epic 6 reads `import` (F6.4) and
# `action` (F6.7) with this same reader, so no second block reader appears.
BLOCK_RE = re.compile(r'\b(resource|data|import|action)\s+"([a-z0-9_]+)"\s+"([^"]+)"\s*\{')
BLOCK_KINDS = ('resource', 'data', 'import', 'action')
# F6.4: an `import` block may name its target inside the block, as `to = <type>.<local name>`, so the
# reader reads the two names from the body for that shape. One reader still serves every kind.
IMPORT_BLOCK_RE = re.compile(r'\bimport\s*\{')
TO_RE = re.compile(r'\bto\s*=\s*([a-z0-9_]+)\.([A-Za-z0-9_]+)')
VARIABLE_RE = re.compile(r'^variable\s+"([A-Za-z0-9_]+)"', re.M)
# A location field as the block states it: the quoted value, or the `var.` reference the
# value-to-variable table prints (F6.6).
LOCATION_FIELD_RE = re.compile(r'([A-Za-z0-9_]+)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|(var\.[A-Za-z0-9_]+))')
# A `var.` consumer, which is the second direction of the `variables` rule (F6.6).
CONSUMER_RE = re.compile(r'\bvar\.([A-Za-z0-9_]+)')
# A `.name` reference, with the kind the reference names. A `data.` reference
# resolves to a data block and a plain reference to a resource block, so the
# kind is part of the identity (F5.5).
REFERENCE_RE = re.compile(r'\b(data\.)?(panos_[a-z0-9_]+)\.([a-z0-9_]+)\.name\b')
ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

# Placeholders the generator writes on purpose. The operator must replace them
# before apply. They are an expected output, so they are a WARN, not a failure.
EXPECTED_PLACEHOLDERS = ('***CHANGE_ME***',)


@dataclass(frozen=True)
class Finding:
    """One rule violation, or one reported fact, at one position of one file.

    The position is a line for a `.tf` file, and a row ordinal for a data file (F6.8), because a data
    row spans many lines. `line` 0 means the finding is about the file as a whole.
    """

    check: str
    severity: str
    file: str
    line: int
    detail: str

    def render(self) -> str:
        if not self.file:
            location = '(run)'
        elif not self.line:
            location = self.file
        else:
            location = f'{self.file}:{self.line}'
        return f'{location}  {self.detail}'


@dataclass(frozen=True)
class Block:
    """One block as the operator reads it: `resource`, `data`, `import`, `action`."""

    file: str
    line: int
    kind: str
    rtype: str
    local: str
    body: str

    @property
    def address(self) -> str:
        """The block address, in the shape a reference names it."""
        return f'{self.rtype}.{self.local}'

    @property
    def has_location(self) -> bool:
        """Whether this block carries a `location` block."""
        return re.search(r'\blocation\s*=\s*\{', self.body) is not None

    def location_body(self) -> str:
        """The text inside this block's `location` block, or '' when it has none."""
        return import_blocks.sub_block_body(self, 'location')

    def config_body(self) -> str:
        """The text inside this block's `config` block, or '' when it has none (F6.7).

        An action's fields live inside `config`: that is the grammar Terraform 1.14 requires for an
        action block, measured with `terraform validate`.
        """
        return import_blocks.sub_block_body(self, 'config')

    def attribute(self, key: str, sub_block: str = '') -> str:
        """One quoted field of this block, as the gate reads it (the one field reader)."""
        return import_blocks.block_value(self, key, sub_block)

    def list_values(self, key: str, sub_block: str = '') -> tuple:
        """One list field of this block, element by element, through the same field reader (F6.7)."""
        return import_blocks.block_list(self, key, sub_block)

    def fields(self, sub_block: str = '') -> dict[str, str]:
        """Every field of this block, as the raw value text, in the block's order (F6.7)."""
        return import_blocks.fields(self, sub_block)

    def location_values(self) -> dict[str, dict[str, str]]:
        """The `location` sub-block as {sub-block: {field: value}}, in sorted order.

        The shape the import id states (`import_blocks.decode_id`), so the agreement rule compares
        the block and the id through one reader. A sub-block with no field is the `{}` shape.

        A field is read as the block states it (F6.6): the unescaped value for a quoted field, and the
        reference text `var.<name>` for a field the value-to-variable table maps. The rule that decides
        which shape a field has is `resource_mapping.VALUE_VARIABLES`, so the reader does not guess.
        """
        text = self.location_body()
        found: dict[str, dict[str, str]] = {}
        for match in re.finditer(r'([A-Za-z0-9_]+)\s*=\s*\{', text):
            name = match.group(1)
            start = match.end() - 1
            depth = 0
            end = len(text)
            for index in range(start, len(text)):
                char = text[index]
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        end = index
                        break
            inner = text[start + 1:end]
            fields = {}
            for match in LOCATION_FIELD_RE.finditer(inner):
                field = match.group(1)
                quoted, reference = match.group(2), match.group(3)
                # F6.6: a mapped field prints the §5 name of the value, so the reader keeps the text
                # the block states and the agreement rule compares the name for it.
                fields[field] = reference if reference else import_blocks.unescape(quoted or '')
            found[name] = dict(sorted(fields.items()))
        return dict(sorted(found.items()))

    def sub_blocks(self) -> dict[str, tuple[str, ...]]:
        """The `location` sub-blocks as {sub-block: fields}, in sorted order.

        A sub-block is read as `name = { ... }` or as the one-line `name = {}`
        shape, which is what the generator writes for an empty sub-block.
        """
        text = self.location_body()
        found: dict[str, list[str]] = {}
        for match in re.finditer(r'([A-Za-z0-9_]+)\s*=\s*\{', text):
            name = match.group(1)
            start = match.end() - 1
            depth = 0
            end = len(text)
            for index in range(start, len(text)):
                char = text[index]
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        end = index
                        break
            inner = text[start + 1:end]
            fields = sorted(m.group(1) for m in re.finditer(
                r'([A-Za-z0-9_]+)\s*=\s*[^{\n]', inner))
            found[name] = tuple(fields)
        return {name: tuple(fields) for name, fields in sorted(found.items())}


@dataclass(frozen=True)
class CheckResult:
    """One check: its findings, and whether it ran."""

    check: str
    findings: tuple[Finding, ...] = ()
    ran: bool = True
    note: str = ''

    @property
    def result(self) -> str:
        if not self.ran:
            return NOT_RUN
        for severity in (FAIL, WARN, SKIP):
            if any(f.severity == severity for f in self.findings):
                return severity
        return 'PASS'


@dataclass(frozen=True)
class SanityReport:
    """The gate output. Deterministic: no timestamp, no absolute path."""

    checks: tuple[CheckResult, ...]
    file_count: int
    data_file_count: int = 0
    resource_count: int = 0

    def results(self, check: str) -> list[CheckResult]:
        """The results one check produced, in report order.

        A check can hold more than one result: the plan check runs once per unit directory (F6.10.3, §14),
        so it produces one result per unit. The report prints each result, and a count over the report
        counts every result.
        """
        return [result for result in self.checks if result.check == check]

    def findings(self, check: str) -> list[Finding]:
        """Findings for one check, in report order."""
        return [finding for result in self.results(check) for finding in result.findings]

    def result_of(self, check: str) -> str:
        """The check as the report states it: the worst result the check produced.

        A check that did not run is NOT RUN; a check that ran on more than one unit and failed on one of
        them is FAIL, so the report cannot hide a unit that failed behind a unit that passed.
        """
        results = self.results(check)
        if not results:
            return NOT_RUN
        if all(not result.ran for result in results):
            return NOT_RUN
        for severity in (FAIL, WARN, SKIP):
            if any(result.result == severity for result in results):
                return severity
        return 'PASS'

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.checks for f in r.findings if f.severity == FAIL)

    @property
    def warn_count(self) -> int:
        return sum(1 for r in self.checks for f in r.findings if f.severity == WARN)

    @property
    def failed(self) -> bool:
        return self.fail_count > 0

    def render(self) -> str:
        lines = [REPORT_RULE, 'SANITY REPORT', REPORT_RULE]
        lines.append(f'Result: {"FAIL" if self.failed else "PASS"} '
                     f'({self.fail_count} FAIL, {self.warn_count} WARN)')
        lines.append(f'Files checked: {self.file_count} .tf files, {self.data_file_count} data files.')
        lines.append(f'Resources checked: {self.resource_count}.')
        lines.append('')
        lines.append('CHECK RESULTS')
        lines.append('-' * 80)
        for name in CHECK_ORDER:
            for result in self.results(name):
                count = len(result.findings)
                label = f'{result.result} ({count})' if count else result.result
                lines.append(f'{name:<24} {label}')
                if result.note:
                    lines.append(f'{"":<24} {result.note}')
        lines.append('')
        lines.append('FINDINGS')
        lines.append('-' * 80)
        if not self.checks or all(not r.findings for r in self.checks):
            lines.append('(No finding.)')
        else:
            for name in CHECK_ORDER:
                for result in self.results(name):
                    if not result.findings:
                        continue
                    lines.append(f'[{name}]')
                    for finding in result.findings:
                        lines.append(f'  {finding.render()}')
        return '\n'.join(lines) + '\n'

    def console_summary(self) -> str:
        """The short console summary. One line per check result, then each finding."""
        lines = [
            f'Sanity gate: {"FAIL" if self.failed else "PASS"} '
            f'({self.fail_count} FAIL, {self.warn_count} WARN) - '
            f'{self.file_count} .tf files, {self.data_file_count} data files, '
            f'{self.resource_count} resources'
        ]
        for name in CHECK_ORDER:
            for result in self.results(name):
                lines.append(f'  {name}: {result.result}')
                for finding in result.findings:
                    lines.append(f'    {finding.render()}')
        return '\n'.join(lines)


# --- Reading the output ------------------------------------------------------

def read_tf_files(output_dir: Path) -> dict[str, str]:
    """Read every `.tf` file the run wrote, keyed by the path from the codebase root.

    F6.10.1 (`docs/CODEBASE_ASSEMBLY.md` §14): the block rules read the `.tf` files of each unit
    directory, so the reader walks the codebase root and the directories under it. The key is the path
    from the root, so a finding names the unit the file belongs to: a per-unit file names its unit only by
    the directory it sits in. For a run that writes no unit directory the key is the file name, so the
    gate reads the same files in the same order as before. One reader serves both shapes, so the gate
    holds no second rule for the layout.

    `surrogateescape` keeps a non-UTF-8 byte readable instead of raising, so
    the gate reports an unreadable file rather than crashing on it.
    """
    out = Path(output_dir)
    files = {}
    for path in sorted(out.rglob('*.tf')):
        files[str(path.relative_to(out))] = path.read_text(encoding='utf-8', errors='surrogateescape')
    return files


# The four data files, each read through the module that owns the row shape (F6.8). The rule
# reports a `parse_rows` refusal as a finding, because the gate reads the files the operator
# receives, and a data file a person hand-wrote is an input. No second shape rule appears, and the
# rule reads no `.tf` file, so no block rule reads a data file.
# F6.10.1 (`docs/CODEBASE_ASSEMBLY.md` §14): this is the codebase root set, one file per run, and the
# rule reads it as one rule over the rows of every unit, not one rule per unit, so the rule reads no file
# inside a unit directory.
DATA_FILES = (
    (unit_manifest.MANIFEST_FILE, unit_manifest),
    (ownership.OWNERSHIP_FILE, ownership),
    (reference_edges.EDGE_FILE, reference_edges),
    (site_data.SITE_DATA_FILE, site_data),
)


def count_data_files(output_dir: Path) -> int:
    """How many of the four data files the output holds: the count the report names.

    `site.auto.tfvars` is not counted, because it is the printed form of the site record and not a
    data file (F6.8). F6.10.1 (`docs/CODEBASE_ASSEMBLY.md` §14): the printed form is a unit-set file, so
    it sits in the unit directory named by its own row, and the count names only the records.
    """
    out = Path(output_dir)
    return sum(1 for name, _ in DATA_FILES if (out / name).is_file())


def blocks(files: dict[str, str], kinds: tuple[str, ...] = BLOCK_KINDS) -> list[Block]:
    """Every block, in file order then line order.

    `kinds` limits the reader to the block kinds a rule reads, so one reader
    serves every rule (F5.5, and Epic 6 for `import` and `action`).
    """
    found = []
    for name in sorted(files):
        text = files[name]
        # One pass, so the blocks come out in file order whatever header shape they use.
        matches = [(m.start(), m.group(1), m.group(2), m.group(3), m.end())
                   for m in BLOCK_RE.finditer(text) if m.group(1) in kinds]
        if 'import' in kinds:
            for match in IMPORT_BLOCK_RE.finditer(text):
                body = text[match.end():text.find('\n}', match.end())]
                target = TO_RE.search(body)
                if target:
                    matches.append((match.start(), 'import', target.group(1), target.group(2), match.end()))
        for start, kind, rtype, local, end in sorted(matches):
            close = text.find('\n}', end)
            body = text[end:close] if close != -1 else text[end:]
            found.append(Block(name, text.count('\n', 0, start) + 1, kind, rtype, local, body))
    return found


def resource_blocks(files: dict[str, str]) -> list[Block]:
    """Every `resource` block, through the same reader as the other kinds."""
    return blocks(files, ('resource',))


def data_blocks(files: dict[str, str]) -> list[Block]:
    """Every `data` block, through the same reader as the other kinds."""
    return blocks(files, ('data',))


def variables(files: dict[str, str]) -> list[tuple[str, str, int]]:
    """Every `variable` declaration as (file, name, line)."""
    found = []
    for file_name in sorted(files):
        text = files[file_name]
        for match in VARIABLE_RE.finditer(text):
            found.append((file_name, match.group(1), text.count('\n', 0, match.start()) + 1))
    return found


# --- Checks ------------------------------------------------------------------

def check_emitted_types(files: dict[str, str]) -> list[Finding]:
    """Every resource type must be in `EMITTED_TYPES` (F2.2)."""
    findings = []
    for block in resource_blocks(files):
        if block.rtype not in resource_mapping.EMITTED_TYPES:
            findings.append(Finding(
                'emitted_types', FAIL, block.file, block.line,
                f'resource type {block.rtype} is not in EMITTED_TYPES',
            ))
    return findings


def check_location_present(files: dict[str, str]) -> list[Finding]:
    """Provider v2 requires `location` on every resource and data block (F2.3, F5.5)."""
    findings = []
    for block in blocks(files, ('resource', 'data')):
        if not block.has_location:
            findings.append(Finding(
                'location_present', FAIL, block.file, block.line,
                f'{block.kind} {block.address} has no location block',
            ))
    return findings


def check_data_blocks(files: dict[str, str]) -> list[Finding]:
    """Every `data` block must match its `DATA_SOURCE_SCHEMA` row (F5.5).

    The missing `location` block is the `location_present` rule, so this rule
    reports the shape inside it: the sub-block, the fields, and `name`. A row
    that declares no `name` (the settings, policy, and collection shapes) is not
    refused for having none.
    """
    findings = []
    for block in data_blocks(files):
        row = resource_mapping.DATA_SOURCE_SCHEMA.get(block.rtype)
        if row is None:
            findings.append(Finding(
                'data_blocks', FAIL, block.file, block.line,
                f'data {block.address} is not in DATA_SOURCE_SCHEMA',
            ))
            continue
        declares_name, shape = row
        if declares_name and not re.search(r'\bname\s*=', block.body):
            findings.append(Finding(
                'data_blocks', FAIL, block.file, block.line,
                f'data {block.address} has no name, which {block.rtype} declares',
            ))
        for sub_block, fields in block.sub_blocks().items():
            if sub_block not in shape:
                findings.append(Finding(
                    'data_blocks', FAIL, block.file, block.line,
                    f'data {block.address} location.{sub_block} is not a sub-block '
                    f'{block.rtype} declares',
                ))
                continue
            for field in fields:
                if field not in shape[sub_block]:
                    findings.append(Finding(
                        'data_blocks', FAIL, block.file, block.line,
                        f'data {block.address} location.{sub_block}.{field} is not a '
                        f'field {block.rtype} declares',
                    ))
    return findings


def location_agrees(id_location: dict, printed: dict) -> bool:
    """Compare the location an import id states with the location the block prints (F6.6).

    A field the value-to-variable table maps prints as the §5 name of the value, so this rule compares
    the name for that field and the value for every other field. The id keeps the value, because the
    provider parses the id and a variable name is not a device name, so a run that prints `var.<name>`
    still agrees with its own id. A block that prints the literal for a mapped field is a finding,
    because then the block and the id are not the same location.
    """
    if set(id_location) != set(printed):
        return False
    for sub_block, fields in printed.items():
        id_fields = id_location[sub_block]
        for field, text in fields.items():
            value = id_fields.get(field, '')
            if resource_mapping.VALUE_VARIABLES.get(field) == resource_mapping.VARIABLE:
                if text != naming.variable_text(value):
                    return False
            elif value != text:
                return False
    return True


def check_import_blocks(files: dict[str, str]) -> list[Finding]:
    """Every `import` block must agree with the `resource` block it names (F6.4).

    Four facts, each read through one rule: the address (`to`, read by `blocks`), the entry name, the
    location, and the id shape (`import_blocks.decode_id`). A wrong type and a wrong local name are both
    "the address names no resource block", and a `data` block cannot answer, because an import object names
    a resource. The location is compared through `VALUE_VARIABLES`, so a field the table maps to a variable
    is compared by its §5 name (F6.6).

    A `*_policy_rules` entry writes no block: its import object names the rulebase, the position, and a
    list (`import_blocks` rule 5). The run reports the entry as an operator action, so the finding is WARN
    and the exit code is unchanged. It is reported only when the run declared import blocks.
    """
    import_blocks_read = blocks(files, ('import',))
    resources = {(block.rtype, block.local): block for block in resource_blocks(files)}
    findings = []
    for block in import_blocks_read:
        try:
            decoded = import_blocks.decode_id(block.attribute('id'))
        except ValueError as exc:
            findings.append(Finding('import_blocks', FAIL, block.file, block.line, str(exc)))
            continue
        target = resources.get((block.rtype, block.local))
        if target is None:
            findings.append(Finding(
                'import_blocks', FAIL, block.file, block.line,
                f'import {block.address} names no resource block in this run',
            ))
            continue
        name = target.attribute(entry_coverage.name_field(block.rtype))
        if decoded['name'] != name:
            findings.append(Finding(
                'import_blocks', FAIL, block.file, block.line,
                f'import {block.address} id name {decoded["name"]!r} is not the name '
                f'the block states ({name!r})',
            ))
        location = target.location_values()
        if not location_agrees(decoded['location'], location):
            findings.append(Finding(
                'import_blocks', FAIL, block.file, block.line,
                f'import {block.address} id location is not the location the block states '
                f'({location})',
            ))
    if import_blocks_read:
        for block in resource_blocks(files):
            if block.rtype in import_blocks.rule_types():
                findings.append(Finding(
                    'import_blocks', WARN, block.file, block.line,
                    f'resource {block.address}: no import id, because {import_blocks.RULE_DECISION}',
                ))
    return findings


# A shape word as the field reader reads it (F7.6). `value_shape` reads a shape family, so a specialization
# reads back as its family word: `one_of` and `block` are object values, and `member_list` is a `[` value.
# `SHAPE_LEVELS` is the set of words that name a level the walk enters. A `member_list` names no level,
# because its members are values and not entries, and a `block` field names a level that states no fields.
SHAPE_READS_AS = {'one_of': 'object', 'block': 'object', 'member_list': 'string_list'}
SHAPE_LEVELS = ('object', 'one_of', 'string_list')


def value_shape(raw: str) -> str:
    """The value shape a field states, as the one field reader read it (F6.7).

    The shapes `ACTION_SCHEMA` and `PROTOCOL_SHAPE` declare: `string`, `number`, `string_list`, `bool`,
    `object`, and each specialization as its family word through `SHAPE_READS_AS` above, because a one-of level
    is an object value that states one key, a `block` field is an object value that states none, and a
    `member_list` is a `[` value whose members are values. The reader keeps the raw
    text so the opening character states the shape, which makes this the reader's own inverse and no second
    table names the shapes.
    """
    if raw.startswith('['):
        return 'string_list'
    if raw.startswith('{'):
        return 'object'
    if raw.startswith('"'):
        return 'string'
    if raw in ('true', 'false'):
        return 'bool'
    if raw.isdigit():
        # F7.1: a number is the shape the reader reads for `metric`, which the shape table states as a
        # `number` field, so the reader's inverse states it as its own word.
        return 'number'
    return ''


def check_scope_blocks(files: dict[str, str]) -> list[Finding]:
    """A name inside a scope block's `location` must name a scope this run declares (F6.5).

    A `.name` reference is the `references` rule, but a name written inside a `location` is not a
    reference: it names the scope the block sits in, so the reference rule cannot reach it. This
    rule reads that name against the block that declares the scope, through `SCOPE_ANSWER`. Only a
    `resource` block answers, because a `data` block is a read-through, not a declaration, and the
    rule that a `data` block answers a reference is the `references` rule.

    Two shapes state no name to resolve, so they are not checked: an empty sub-block (the
    `panorama = {}` shape the four Panorama scopes write), and a field that names a device rather
    than a scope (`panorama_device`, `ngfw_device`).

    The `device_group` row of `SCOPE_ANSWER` is read by the action rule, not here: a scope block
    states its own device group at its own level (the `name_field` rule), and the six scope types
    place an empty `device_group` sub-block or none, so the scope rule has no device-group name to
    resolve.
    """
    answering = set(resource_mapping.SCOPE_ANSWER.values())
    declared = set()
    for block in resource_blocks(files):
        if block.rtype in answering:
            name = block.attribute('name')
            if name:
                declared.add((block.rtype, name))
    findings = []
    for block in sorted(resource_blocks(files), key=lambda b: (b.file, b.line)):
        if block.rtype not in resource_mapping.SCOPE_TYPES:
            continue
        for sub_block, fields in block.location_values().items():
            scope_type = resource_mapping.SCOPE_ANSWER.get(sub_block)
            if scope_type is None:
                continue
            name = fields.get('name', '')
            if not name:
                continue
            if (scope_type, name) not in declared:
                findings.append(Finding(
                    'scope_blocks', FAIL, block.file, block.line,
                    f'{block.address} location.{sub_block}.name = "{name}" names no '
                    f'{scope_type} block this run declares',
                ))
    return findings


def check_actions(files: dict[str, str]) -> list[Finding]:
    """Every `action` block must match its `ACTION_SCHEMA` row and name one unit (F6.7).

    Four findings, each a FAIL, and each read through one rule:

    1. The type is not in `ACTION_SCHEMA`, a field is not in the row, a required field is missing, or
       a field is stated at the block's own level instead of inside `config`, which is the level the
       Terraform 1.14 action grammar requires.
    2. The block states no scope name, so it commits the whole config and not a unit: the `panos_commit`
       row declares no required field, so the codebase rule is what makes an action a unit action.
    3. The fact a filter field names must be a scope fact `SCOPE_ANSWER` answers, the F6.5 rule shape,
       because a name inside a filter is not a `.name` reference the `references` rule can reach. The
       name is not resolved against a block this run declares: a run scoped to a scope writes no block
       for the scope it read (measured on an API scope run), so the block text alone cannot resolve it,
       and the address rule below is what makes the action name its own unit.
    4. The block states one name, and its address is the §5 name plus the digest of the identity the
       names inside the block build, so the address and the names agree. This is the gate form of "no
       action names a scope another unit owns", and it needs no data file.

    The block is read through the one block reader and the one field reader. This rule reads no data
    file, so the gate input is the block text, the tables, and `naming.py`.
    """
    findings = []
    for block in sorted(blocks(files, ('action',)), key=lambda b: (b.file, b.line)):
        row = resource_mapping.ACTION_SCHEMA.get(block.rtype)
        if row is None:
            findings.append(Finding(
                'actions', FAIL, block.file, block.line,
                f'action {block.address} is not in ACTION_SCHEMA',
            ))
            continue
        required, shape = row
        outside = block.fields()
        for field in sorted(outside):
            findings.append(Finding(
                'actions', FAIL, block.file, block.line,
                f'action {block.address} states {field} at its own level, which the action grammar '
                f'does not allow: the fields are inside `config`',
            ))
        fields = block.fields(commit_actions.CONFIG_BLOCK)
        for field in sorted(required):
            if field not in fields:
                findings.append(Finding(
                    'actions', FAIL, block.file, block.line,
                    f'action {block.address} has no {field}, which {block.rtype} requires',
                ))
        for field in sorted(fields):
            declares = shape.get(field)
            if declares is None:
                findings.append(Finding(
                    'actions', FAIL, block.file, block.line,
                    f'action {block.address} {field} is not a field {block.rtype} declares',
                ))
            elif value_shape(fields[field]) != declares:
                findings.append(Finding(
                    'actions', FAIL, block.file, block.line,
                    f'action {block.address} {field} is not a {declares} value',
                ))
        try:
            read = commit_actions.read_block(block)
        except ValueError as exc:
            findings.append(Finding('actions', FAIL, block.file, block.line, str(exc)))
            continue
        fact = read['fact']
        if resource_mapping.SCOPE_ANSWER.get(fact) is None:
            findings.append(Finding(
                'actions', FAIL, block.file, block.line,
                f'action {block.address} names a fact SCOPE_ANSWER does not answer ({fact})',
            ))
        expected = commit_actions.local_name(fact, read['entry_name'], naming.sanitize)
        if block.local != expected:
            findings.append(Finding(
                'actions', FAIL, block.file, block.line,
                f'action {block.address} is not the §5 name plus the identity digest the block states '
                f'({expected})',
            ))
    return findings


def check_protocol_object(files: dict[str, str]) -> list[Finding]:
    """Every `protocol` object on a `panos_virtual_router` block must match its `PROTOCOL_SHAPE` row (F7.1).

    Five findings, each a FAIL, and each read through the one block reader and the one field reader:

    0. A `protocol` the field reader can read as a name but not as a field, which is the block shape the
       provider refuses.
    1. A level the shape table states no row for, a field the row does not declare, or a value whose shape
       the reader reads differently from the shape the row states. A specialization is read as its family word
       through `SHAPE_READS_AS`, because the field reader reads the family: `one_of` and `block` are read as
       `object`, and `member_list` is read as `string_list`. The walk enters only the words in
       `SHAPE_LEVELS`, so a member list is never walked and rule 4 reads only an entry list.
    2. A row that states `selects` names the attributes that form an exactly-one choice, and the level or the
       entry states exactly one of them: a `one_of` level that states no key, or more than one key, or a key the
       mapping does not state. `terraform validate` accepts a `{ ... }` value for `protocol`, so the gate is the
       rule that keeps a choice to the one key the provider can read (F7.12). The same helper serves both shape
       tables, so one wording covers both, and for a filter block the choice is read at the block's own level as
       well (F7.13).
    3. A field the row marks `sensitive` printed as a literal. No generated file may state the value, so
       the block prints the variable reference for it.
    4. An element inside a `[` container that states no `name`, which is the field the row reads as the
       entry name.

    The walk reads one level at a time, so a field inside an object value is not read at the block's own
    level. The rule reads no data file: the block text and the tables are the whole input.
    """
    findings = []
    for block in sorted(blocks(files, ('resource',)), key=lambda b: (b.file, b.line)):
        if block.rtype != resource_mapping.PROTOCOL_TYPE:
            continue
        raw = import_blocks.field_value(block, resource_mapping.PROTOCOL_FIELD)
        if not raw:
            continue
        # Rule 0: `protocol` is a field of the block. `field_at` reads a name followed by `{` the way the
        # action grammar requires, so this is the one place that states the difference `terraform validate`
        # refuses: a `protocol { ... }` block is not the shape the provider reads.
        body = block.body
        if not re.search(rf'(?m)^ {{{import_blocks.level_of(body)}}}{resource_mapping.PROTOCOL_FIELD}\s*=', body):
            findings.append(Finding(
                'protocol_object', FAIL, block.file, block.line,
                f'protocol {block.address} is a block, not the field PROTOCOL_SHAPE states',
            ))
            continue
        _shape_level_findings(block, resource_mapping.PROTOCOL_FIELD, raw, findings,
                            resource_mapping.PROTOCOL_TABLE)
    return findings


def _shape_choice_findings(block, path: str, fields: dict, findings: list, table) -> bool:
    """The exactly-one choice a row states as `selects`, read at the level or entry the row states (F7.12).

    `selects` is the one place the table states a choice, so one rule reads both shapes it can hold: the whole
    value is the choice for a `one_of` row, where every key the value states is a key the row selects, and the
    choice is part of the value for a row that also states other fields, where those keys are read by the field
    rule. A `string_list` row holds entries, so the choice is read inside each entry. The provider reads the
    choice as exactly one (`terraform validate`, provider 2.0.14, measured 2026-11-03), so a level or an entry
    that states a different number is a finding. Both tables state a choice this way, so one wording covers both.

    Returns True when the choice is read here, so the field rule does not read the same key twice.
    """
    row = table.row(path)
    selects = row['selects']
    if not selects:
        return False
    alternatives = set(selects.values())
    if row['shape'] == 'one_of':
        # The whole value is the choice, so a key the row does not select is the choice finding.
        extra = [field for field in fields if field not in alternatives]
        if extra:
            findings.append(Finding(
                table.rule, FAIL, block.file, block.line,
                f'{table.word} {block.address} {path} key {extra[0]} is not a key {table.name} selects',
            ))
            return True
    stated = [field for field in fields if field in alternatives]
    if len(stated) != 1:
        findings.append(Finding(
            table.rule, FAIL, block.file, block.line,
            f'{table.word} {block.address} {path} states {len(stated)} keys, which is not the one key '
            f'{table.name} selects',
        ))
        return True
    key = stated[0]
    if key not in row['fields']:
        # F7.6: the alternative is the row the table states for it, so the walk enters it here.
        _shape_level_findings(block, f'{path}/{key}', fields[key], findings, table)
        return True
    return False


def _shape_level_findings(block, path: str, raw: str, findings: list, table) -> None:
    """One level of a shape-table value, walked from the text the one field reader read.

    `table` is the shape table the level belongs to, so the same reader serves the `protocol` object and a
    filter container (F7.8). The finding wording reads `table.word` and `table.name`, so the protocol text is
    unchanged, and `table.rule` names the rule the finding belongs to.
    """
    row = table.row(path)
    if row is None:
        findings.append(Finding(
            table.rule, FAIL, block.file, block.line,
            f'{table.word} level {path} is not a level {table.name} states ({block.address})',
        ))
        return
    shape = row['shape']
    if shape == 'string_list':
        if not raw.startswith('['):
            findings.append(Finding(
                table.rule, FAIL, block.file, block.line,
                f'{table.word} {block.address} {path} is not a string_list value',
            ))
            return
        for element in import_blocks.elements_of(raw):
            fields = import_blocks.fields_at(import_blocks.container_body(element))
            # Rule 4: an element inside a container is an entry, and the entry name is the field the row
            # reads for it. Rule 2 reads the choice inside the entry, because a row can state the choice as
            # two of its fields (F7.12).
            if 'name' not in fields:
                findings.append(Finding(
                    table.rule, FAIL, block.file, block.line,
                    f'{table.word} {block.address} {path} element states no name',
                ))
            if not _shape_choice_findings(block, path, fields, findings, table):
                _shape_field_findings(block, path, fields, findings, table)
        return
    if not raw.startswith('{'):
        findings.append(Finding(
            table.rule, FAIL, block.file, block.line,
            f'{table.word} {block.address} {path} is not an object value',
        ))
        return
    fields = import_blocks.fields_at(import_blocks.container_body(raw))
    # Rule 2: the choice the row states as `selects`, which is the whole value for a `one_of` row.
    if _shape_choice_findings(block, path, fields, findings, table):
        return
    _shape_field_findings(block, path, fields, findings, table)


def _shape_field_findings(block, path: str, fields: dict, findings: list, table) -> None:
    """The fields at one level, checked against the row that states them."""
    row = table.row(path)
    for field, value in fields.items():
        declares = row['fields'].get(field)
        if declares is None:
            findings.append(Finding(
                table.rule, FAIL, block.file, block.line,
                f'{table.word} {block.address} {path} {field} is not a field {table.name} declares',
            ))
            continue
        if field in row['sensitive']:
            # Rule 3: a value the provider marks sensitive reaches the block only as a variable reference.
            if not value.startswith('var.'):
                findings.append(Finding(
                    table.rule, FAIL, block.file, block.line,
                    f'{table.word} {block.address} {path} {field} prints a sensitive value as a literal',
                ))
            continue
        word = SHAPE_READS_AS.get(declares, declares)
        if value_shape(value) != word:
            findings.append(Finding(
                table.rule, FAIL, block.file, block.line,
                f'{table.word} {block.address} {path} {field} is not a {declares} value',
            ))
        elif declares in SHAPE_LEVELS:
            _shape_level_findings(block, f'{path}/{field}', value, findings, table)


def check_filter_blocks(files: dict[str, str]) -> list[Finding]:
    """Every filter container block must match its `FILTER_SHAPE` row (F7.8).

    Two findings, each a FAIL, read through the same block reader and field reader `protocol_object` uses:

    1. A level the table states no row for, a field the row does not declare, or a value whose shape the
       reader reads differently from the shape the row states.
    2. The exactly-one choice a row states as `selects`, at the level or entry the walk enters, which for a
       filter block includes the block's own level (F7.13).
    3. An element inside a `[` container that states no `name`, which is the field the row reads for the
       entry name.

    `location` is the placement fact, so the rule reads the fields at the block's own level and not the
    sub-block: `location_present` is the rule that asks for it. The choice is read before the field rule, as in
    `_shape_level_findings`, so a selected key is not read twice. `sensitive` is empty for every filter row, so
    the sensitive rule never fires for a filter block: no filter field is marked sensitive by the provider.

    The rule reads no data file: the block text and the table are the whole input.
    """
    findings = []
    table = resource_mapping.FILTER_TABLE
    for block in sorted(blocks(files, ('resource',)), key=lambda b: (b.file, b.line)):
        path = resource_mapping.filter_path(block.rtype)
        if path is None:
            continue
        # `location` is the placement sub-block, not a field the container row declares.
        fields = {key: value for key, value in import_blocks.fields_at(block.body).items() if key != 'location'}
        # The entry row is the level the walk enters for a filter block, so the choice is read here too.
        if not _shape_choice_findings(block, path, fields, findings, table):
            _shape_field_findings(block, path, fields, findings, table)
    return findings

def check_certificate_blocks(files: dict[str, str]) -> list[Finding]:
    """Every certificate block must match its `CERTIFICATE_SHAPE` row (F7.14).

    Five findings, each a FAIL, read through the same block reader and field reader the other two shape-table
    rules use:

    1. A level the table states no row for, a field the row does not declare, or a value whose shape the
       reader reads differently from the shape the row states. The level half cannot fire for a certificate
       block, because every field the walk enters has a row under it.
    2. The block states no entry name, which is the field `entry_coverage.name_field` reads for its type. The
       field rule reads only the fields the block states, so an absent name is read here. A certificate entry
       has no name a reference resolves, so the `references` rule cannot reach it.
    3. The exactly-one choice a row states as `selects`. For `certificate/local` that is `pem` or `pkcs12`, so
       a `local` that states both, or none, is a finding (F7.12).
    4. A field the row marks `sensitive` prints as the variable reference, never as a literal. The row's
       `sensitive` set is the same fact `VALUE_VARIABLES` states for the emitter, which is the table the print
       reads, so one table decides the shape.
    5. An element inside a `[` container states the name the row reads for the entry name.

    `location` is the placement fact, so the rule reads the fields at the block's own level and not the
    sub-block: `location_present` is the rule that asks for it. The entry name is read first, because the block
    states it before its content, which is also the order the emitter prints. The choice is read before the
    field rule, as in `_shape_level_findings`, so a selected key is not read twice. The rule reads no data
    file: the block text and the table are the whole input.
    """
    findings = []
    table = resource_mapping.CERTIFICATE_TABLE
    for block in sorted(blocks(files, ('resource',)), key=lambda b: (b.file, b.line)):
        path = resource_mapping.certificate_path(block.rtype)
        if path is None:
            continue
        # `location` is the placement sub-block, not a field the entry row declares.
        fields = {key: value for key, value in import_blocks.fields_at(block.body).items() if key != 'location'}
        # Rule 2, through the one naming rule: `name` is not a name this rule states.
        name_field = entry_coverage.name_field(block.rtype)
        if name_field not in fields:
            findings.append(Finding(
                table.rule, FAIL, block.file, block.line,
                f'{table.word} {block.address} states no {name_field}, which is the field '
                'entry_coverage.name_field reads for the entry name',
            ))
        # The entry row is the level the walk enters for a certificate block, so the choice is read here too.
        if not _shape_choice_findings(block, path, fields, findings, table):
            _shape_field_findings(block, path, fields, findings, table)
    return findings


def check_references(files: dict[str, str]) -> list[Finding]:
    """Every `.name` reference must resolve to a block declared in this run (F2.6, F5.5).

    The kind is part of the identity: a `data.` reference resolves to a `data`
    block and a plain reference to a `resource` block, so a block of one kind
    cannot answer a reference written for the other.
    """
    declared = {(block.kind, block.rtype, block.local) for block in blocks(files)}
    findings = []
    for name in sorted(files):
        for line, text in enumerate(files[name].split('\n'), start=1):
            for prefix, rtype, local in REFERENCE_RE.findall(text):
                kind = 'data' if prefix else 'resource'
                if (kind, rtype, local) not in declared:
                    findings.append(Finding(
                        'references', FAIL, name, line,
                        f'dangling reference {prefix}{rtype}.{local}.name',
                    ))
    return findings


def check_variables(files: dict[str, str]) -> list[Finding]:
    """Every declared variable must have a `var.` consumer, and every `var.` consumer must name a
    variable this run declares (F2.10, F6.6).

    A declaration is not a consumer: the consumer text is the whole output, but only a `var.` reference
    counts, so a variable cannot consume itself.

    The second direction is what makes a generated declaration set checkable. F6.6 declares the site
    values the emitter printed, so the run declares exactly what it consumed, and a `var.` reference
    that names no declaration means the two sets disagree.
    """
    consumers = '\n'.join(files[name] for name in sorted(files))
    declared = {(file_name, name, line) for file_name, name, line in variables(files)}
    findings = []
    for file_name, name, line in sorted(declared):
        if not re.search(rf'\bvar\.{re.escape(name)}\b', consumers):
            findings.append(Finding(
                'variables', FAIL, file_name, line,
                f'variable {name} is declared but never consumed as var.{name}',
            ))
    names = {name for _, name, _ in declared}
    for file_name in sorted(files):
        for line, text in enumerate(files[file_name].split('\n'), start=1):
            for name in CONSUMER_RE.findall(text):
                if name not in names:
                    findings.append(Finding(
                        'variables', FAIL, file_name, line,
                        f'var.{name} names no variable this run declares',
                    ))
    return findings


def check_data_files(output_dir: Path) -> list[Finding]:
    """Every data file must read as the data it declares, and the data must agree with each other (F6.8).

    Six findings, each a FAIL, and each read through the module that owns the fact:

    1. A data file that does not read as its declared rows (`parse_rows` refuses), or a data file with
       no rows. The content rule says the tool writes a data file only when it has content, so a data
       file cannot hold no rows. The rule reports a refusal instead of raising, because the gate reads
       the files the operator receives and a data file a person hand-wrote is an input.
    2. A field `naming.py` decides must be stated as the rule states it: the manifest `unit` and
       `directory`, and the ownership `directory`, each read through `unit_manifest`. The site record
       variable name is refused by `parse_rows`, so no second naming rule appears.
    3. A join. The manifest is the file that states the units, so a `directory` another data file names
       must name a manifest unit, or a directory the ownership record names: the tool writes an
       ownership row for an entry from a declared parent source, and the manifest names no unit for it
       (F5.4). An edge row must join on (`type`, `entry`) to an ownership row whose `owner` names the
       `target`. A `kind` `ambiguous` row states no owner, so it cannot name one.
    4. An order. The manifest `rank` and `after` must be what `reference_edges.order` produces from the
       three records read back, so `after` names only units the manifest names.
    5. A printed form. `site.auto.tfvars` must equal `site_data.render_tfvars` of the site rows, and the
       two files stand or fall together on the content rule.
    6. A position. A data-file finding is stated at its row ordinal, because a data row spans many
       lines, and a finding about the whole file states no row.

    Findings sort by (file, row), so the report is byte-identical between runs on the same files.
    """
    out = Path(output_dir)
    findings: list[Finding] = []
    parsed: dict[str, list] = {}

    # Finding 1, read through each module's `parse_rows`.
    for name, module in DATA_FILES:
        path = out / name
        if not path.is_file():
            continue
        text = path.read_text(encoding='utf-8', errors='surrogateescape')
        try:
            rows = module.parse_rows(text)
        except ValueError as exc:
            findings.append(Finding('data_files', FAIL, name, 0, str(exc)))
            continue
        if not rows:
            findings.append(Finding(
                'data_files', FAIL, name, 0,
                'a data file is written only when it has content, so it cannot hold no rows',
            ))
            continue
        parsed[name] = rows

    manifest = parsed.get(unit_manifest.MANIFEST_FILE, [])
    ownership_rows = parsed.get(ownership.OWNERSHIP_FILE, [])
    edge_rows = parsed.get(reference_edges.EDGE_FILE, [])
    site_rows = parsed.get(site_data.SITE_DATA_FILE, [])
    units = {row['directory'] for row in manifest}
    record_units = {row['directory'] for row in ownership_rows}

    def facts_of(row: dict) -> tuple:
        return tuple(row[key] for key in unit_manifest.FACT_KEYS)

    # Finding 2: the fields `naming.py` decides.
    for ordinal, row in enumerate(manifest, start=1):
        row_facts = facts_of(row)
        unit = unit_manifest.unit_name(row_facts)
        if row['unit'] != unit:
            findings.append(Finding(
                'data_files', FAIL, unit_manifest.MANIFEST_FILE, ordinal,
                f'row {ordinal}: unit {row["unit"]} is not the name the level rule states ({unit})',
            ))
        directory = unit_manifest.directory_name(row_facts, naming.sanitize)
        if row['directory'] != directory:
            findings.append(Finding(
                'data_files', FAIL, unit_manifest.MANIFEST_FILE, ordinal,
                f'row {ordinal}: directory {row["directory"]} is not the naming rule shape of the '
                f'facts the row states ({directory})',
            ))
    for ordinal, row in enumerate(ownership_rows, start=1):
        directory = unit_manifest.directory_name(facts_of(row), naming.sanitize)
        if row['directory'] != directory:
            findings.append(Finding(
                'data_files', FAIL, ownership.OWNERSHIP_FILE, ordinal,
                f'row {ordinal}: directory {row["directory"]} is not the naming rule shape of the '
                f'facts the row states ({directory})',
            ))

    # Finding 3: the joins, through `directory`.
    for ordinal, row in enumerate(ownership_rows, start=1):
        if not row['owner']:
            continue    # an `ambiguous` row states no owner, so the join reads nothing
        if row['kind'] == 'ambiguous':
            findings.append(Finding(
                'data_files', FAIL, ownership.OWNERSHIP_FILE, ordinal,
                f'row {ordinal}: a kind {row["kind"]} row states no owner, so it cannot name one',
            ))
        elif row['owner'] != row['directory'] and row['owner'] not in units and row['owner'] not in record_units:
            findings.append(Finding(
                'data_files', FAIL, ownership.OWNERSHIP_FILE, ordinal,
                f'row {ordinal}: owner {row["owner"]} names no unit the manifest names or a row of the '
                f'ownership record',
            ))
    for ordinal, row in enumerate(edge_rows, start=1):
        if row['referrer'] not in units:
            findings.append(Finding(
                'data_files', FAIL, reference_edges.EDGE_FILE, ordinal,
                f'row {ordinal}: referrer {row["referrer"]} names no unit the manifest names',
            ))
        if row['target'] not in units and row['target'] not in record_units:
            findings.append(Finding(
                'data_files', FAIL, reference_edges.EDGE_FILE, ordinal,
                f'row {ordinal}: target {row["target"]} names no unit the manifest names or a row of '
                f'the ownership record',
            ))
        if not any(owner['type'] == row['type'] and owner['entry'] == row['entry']
                   and owner['owner'] == row['target'] for owner in ownership_rows):
            findings.append(Finding(
                'data_files', FAIL, reference_edges.EDGE_FILE, ordinal,
                f'row {ordinal}: ({row["type"]}, {row["entry"]}) joins no ownership row whose owner '
                f'names the target',
            ))
    for ordinal, row in enumerate(site_rows, start=1):
        if row['directory'] not in units:
            findings.append(Finding(
                'data_files', FAIL, site_data.SITE_DATA_FILE, ordinal,
                f'row {ordinal}: directory {row["directory"]!r} names no unit the manifest names',
            ))

    # Finding 4: the order, read through `reference_edges.order`.
    if manifest:
        filled = reference_edges.order(manifest, ownership_rows, edge_rows)
        for ordinal, (written, expected) in enumerate(zip(manifest, filled), start=1):
            if written['rank'] != expected['rank'] or written['after'] != expected['after']:
                findings.append(Finding(
                    'data_files', FAIL, unit_manifest.MANIFEST_FILE, ordinal,
                    f'row {ordinal}: rank {written["rank"]} and after {written["after"]} are not what '
                    f'the order rule produces ({expected["rank"]}, {expected["after"]})',
                ))

    # Finding 5: the site record and its printed form. The record is one file for the codebase, so the
    # rule reads it at the root; the printed form is the unit's file, so the rule compares the printed
    # form of one row with the file in the directory that row names (F6.10.3, §14). A printed form is not
    # one of the four data files, so the count names only the records. The finding names the path from
    # the codebase root, because a per-unit file names its unit only by its directory, and its position
    # is the row ordinal the record states.
    for ordinal, row in enumerate(site_rows, start=1):
        printed = write_path.unit_path(out, row['directory'], site_data.TFVARS_FILE)
        if not printed.is_file():
            findings.append(Finding(
                'data_files', FAIL, str(printed.relative_to(out)), ordinal,
                f'row {ordinal}: the site row has content, so the unit it names must hold its printed form',
            ))
            continue
        try:
            expected = site_data.render_tfvars([row])
        except ValueError as exc:
            findings.append(Finding('data_files', FAIL, site_data.SITE_DATA_FILE, ordinal, str(exc)))
            continue
        if printed.read_text(encoding='utf-8', errors='surrogateescape') != expected:
            findings.append(Finding(
                'data_files', FAIL, str(printed.relative_to(out)), ordinal,
                f'row {ordinal}: the printed form is not the row rendered by the rule that prints it',
            ))

    # Finding 6: the position is the row ordinal, and a finding about a whole file states row 0.
    return sorted(findings, key=lambda finding: (finding.file, finding.line, finding.detail))


def check_round_trip(files: dict[str, str], ledger) -> list[Finding]:
    """Compare the block set the reader read with the entry set the run's ledger read, per unit and per row (§4.6).

    Two sets, each read through the module that owns it, so the rule states no reader, no count, no scope,
    no kind, no type, no field name, no file name and no unit rule of its own:

    - the entry side through `entry_coverage.EntryLedger`, and the count scope through
      `entry_coverage.matrix_row_for`, the property-scan scope rule, so only an `emitted` container row
      names an entry here. The destination is read per entry, so an entry the run reports is not in the
      count even when its container row is `emitted`.
    - the block side through the one block reader, `blocks`, with `kinds = ('resource',)`, so a `data`
      block, an `import` block, an `action` block and a `variable` declaration enter no count.
    - the join through `entry_coverage.MATRIX_BY_RESOURCE`, the same table `matrix_row_for` reads, and
      through `unit_manifest` (`facts_of`, `directory_name`, `units`).

    A row `matrix_row_for` can never answer is not a count row, because no entry maps to it, so the rule
    states no exception list. A `.tf` file at the codebase root names no unit, because `write_path.py`
    writes no `.tf` file in the root set, so its count cannot be assigned.

    One finding per unit and per row where the two counts do not agree, and the fact is the two counts. The
    rule names no entry: `docs/ARCHITECTURE.md` §3.2 owns one entry, and the gap section names the entries
    that write nothing, so the gate cannot restate the per-entry report. Both directions are findings: a
    block the reader read that no entry produced, and an entry the parse read and modelled that has no
    block. A finding is a coverage fact, not a broken output, so it is a WARN and does not change the exit
    code, the decision the property scan already states (`entry_coverage.PROPERTY_RULE`). The position is
    the line of the first block the reader read for that unit and row; when the reader read no block, the
    position is the file as a whole (`line` 0) and the file is the unit directory plus the row's
    `output_file` read from the row.

    The two populations are not the same population, so a disagreeing count is a real gap, not noise: an
    `emitted` entry whose type has no v2 attribute writes no block, a block written for a property level
    has no ledger row, and one entry can write more than one block. The rule states no exception list for
    them; `tests/test_round_trip.py` pins the three, and `backlog.md` keeps them open.

    Findings sort by (file, line, detail), the rule `check_data_files` already uses, so the report is
    byte-identical between runs on the same files. The rule prints no scan console line, because its fact
    compares two sets and the console shape names one identity (`docs/ARCHITECTURE.md` §3.2).
    """
    # A count row is a matrix row the one scope rule can answer, read over the container table. A row the
    # rule can never answer is not in the count, because no entry maps to it, so no exception list appears.
    count_rows = {matrix_row['resource'] for matrix_row in
                  (entry_coverage.matrix_row_for(container_row.path)
                   for container_row in container_coverage.CONTAINER_TABLE)
                  if matrix_row is not None}

    # The unit set is the run's, read through the one unit rule, so the entry's facts and the directory the
    # reader read for the same entry land on one name.
    directories = {facts: unit_manifest.directory_name(facts, naming.sanitize)
                   for facts in unit_manifest.units(ledger)}

    entry_counts: dict[tuple, int] = {}
    for row in ledger.rows():
        # `row['destination']` is the fact `EntryLedger.destination` records for the entry, so the count reads
        # the destination per entry and not the container row. Measured: `report_only` is recorded after the
        # mark, so a report-only address still answers `emitted` and is counted here (`backlog.md`).
        if row['destination'] != 'emitted':
            continue
        covered = entry_coverage.matrix_row_for(row['container'])
        if covered is None:
            continue            # the scan scope: no row covers the entry, or its kind writes no block
        key = (covered['resource'], directories[unit_manifest.facts_of(row)])
        entry_counts[key] = entry_counts.get(key, 0) + 1

    # The block side, in the order the one reader read it.
    blocks_read: dict[tuple, list] = {}
    for block in blocks(files, ('resource',)):
        row = entry_coverage.MATRIX_BY_RESOURCE.get(block.rtype)
        if row is None or row['resource'] not in count_rows:
            continue            # not a count row: no entry measures it
        blocks_read.setdefault((row['resource'], Path(block.file).parent.name), []).append(block)

    findings = []
    for key in sorted(set(entry_counts) | set(blocks_read)):
        resource, unit = key
        read = blocks_read.get(key, [])
        entries = entry_counts.get(key, 0)
        if entries == len(read):
            continue
        row = entry_coverage.MATRIX_BY_RESOURCE[resource]
        if not unit:
            # The reader read the block in the root set, which names no unit, so the count cannot be
            # assigned to one.
            findings.append(Finding(
                'round_trip', WARN, read[0].file, read[0].line,
                f'row {resource}: the count cannot be assigned to a unit, because the reader read '
                f'{len(read)} blocks in a .tf file at the codebase root',
            ))
            continue
        if read:
            file_name, line = read[0].file, read[0].line
        else:
            # The reader read no block, so the position is the file as a whole and the file is the unit
            # directory plus the name the row states.
            file_name, line = f'{unit}/{row["output_file"]}', 0
        findings.append(Finding(
            'round_trip', WARN, file_name, line,
            f'row {resource} in unit {unit}: the ledger reads {entries} entries, '
            f'the reader reads {len(read)} blocks',
        ))
    return sorted(findings, key=lambda finding: (finding.file, finding.line, finding.detail))


def check_control_chars(files: dict[str, str]) -> list[Finding]:
    """No raw control character or DEL may reach a `.tf` file (F1.7).

    LF is the only legal raw control byte. A tab or a CR means an escape was
    missed, because HCL quoted strings carry `\\t` and `\\r`, not the raw byte.
    """
    findings = []
    for name in sorted(files):
        for line, text in enumerate(files[name].split('\n'), start=1):
            bad = sorted({ord(ch) for ch in text if ord(ch) < 32 or ord(ch) == 127})
            if bad:
                codes = ' '.join(f'0x{code:02x}' for code in bad)
                findings.append(Finding(
                    'control_chars', FAIL, name, line, f'raw control character {codes}',
                ))
    return findings


def check_placeholders(files: dict[str, str]) -> list[Finding]:
    """An expected placeholder is reported so the operator replaces it (F2.9).

    A VPN pre-shared key is never written as a literal credential, so a
    placeholder in the output is correct output that still needs an action.
    """
    findings = []
    for name in sorted(files):
        for line, text in enumerate(files[name].split('\n'), start=1):
            # A comment that names the marker is documentation. Only an emitted
            # value needs the operator's action.
            if text.lstrip().startswith('#'):
                continue
            for marker in EXPECTED_PLACEHOLDERS:
                if marker in text:
                    findings.append(Finding(
                        'placeholders', WARN, name, line,
                        f'expected placeholder {marker}: replace before terraform apply',
                    ))
    return findings


def check_terraform(output_dir: Path, terraform: Optional[str] = None,
                    unit: str = '.', timeout: int = 300) -> CheckResult:
    """Run `terraform init` + `terraform validate` on one unit directory (`--validate`).

    A unit is one plan and one root, so this check reads one directory (F6.10.3, §14). `unit` is the path
    the report names for the directory it ran on, and `.` is the codebase root, which is where the check
    runs when the manifest record names no unit. The check names no file, because a plan reads a directory,
    so the report names the directory it ran on: the finding, or the note when the plan passed.

    A missing binary is a SKIPPED result, not a failure: the offline CI matrix
    has no terraform, and the static checks still decide the exit code. A run that names no unit has no
    unit directory, so the gate states one result for the run, not one per unit.
    """
    if terraform is None:
        return CheckResult('terraform', (Finding(
            'terraform', SKIP, unit, 0, 'terraform binary not found; skipped',
        ),))

    def run(args: list[str]) -> tuple[int, str]:
        try:
            proc = subprocess.run(
                [terraform, *args],
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return 1, f'terraform {args[0]} timed out after {timeout} seconds'
        # Terraform colours its output. Strip the escape sequences so the report
        # text is plain and stays byte-identical between runs.
        output = ANSI_RE.sub('', proc.stdout + proc.stderr).strip()
        return proc.returncode, output

    init_code, init_out = run(['init', '-backend=false', '-input=false'])
    if init_code != 0:
        return CheckResult('terraform', (Finding(
            'terraform', FAIL, unit, 0, f'terraform init failed: {init_out[-2000:]}',
        ),))

    validate_code, validate_out = run(['validate'])
    if validate_code != 0:
        return CheckResult('terraform', (Finding(
            'terraform', FAIL, unit, 0, f'terraform validate failed: {validate_out[-2000:]}',
        ),))
    # A result that passes has no finding, so the note names the directory the check ran on: the report can
    # still say which unit the plan read (F6.10.3, §14).
    note = next((line for line in validate_out.split('\n') if line.strip()), '')
    return CheckResult('terraform', (), note=f'{unit}: {note}')


# --- The gate ----------------------------------------------------------------

def unit_directories(output_dir: Path) -> list[str]:
    """The unit directories the manifest record names, in the order the record prints its rows.

    F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): the manifest is the place that states the unit set, so the
    gate reads it through `unit_manifest` and names no second rule. A record that is not there, or that
    does not read as its rows, names no unit: the data rule reports that, and the plan check runs on the
    codebase root.
    """
    out = Path(output_dir)
    path = out / unit_manifest.MANIFEST_FILE
    if not path.is_file():
        return []
    try:
        rows = unit_manifest.parse_rows(path.read_text(encoding='utf-8', errors='surrogateescape'))
    except ValueError:
        # The data rule reports a record that does not read as its rows.
        return []
    return [row['directory'] for row in rows]


def run_checks(output_dir: Path, run_terraform: bool = False,
               terraform: Optional[str] = None,
               ledger: Optional[entry_coverage.EntryLedger] = None) -> SanityReport:
    """Run every static check on one output directory.

    `run_terraform` adds the terraform check. Pass `terraform=None` with
    `run_terraform=True` to report the check as SKIPPED.

    `ledger` is the run's ledger for the cross-check, the one rule that reads two sets. A call with no
    ledger reports the check as NOT RUN, so a test that reads only the output directory is unchanged.
    """
    files = read_tf_files(Path(output_dir))
    checks = [
        CheckResult('emitted_types', tuple(check_emitted_types(files))),
        CheckResult('location_present', tuple(check_location_present(files))),
        CheckResult('data_blocks', tuple(check_data_blocks(files))),
        CheckResult('import_blocks', tuple(check_import_blocks(files))),
        CheckResult('scope_blocks', tuple(check_scope_blocks(files))),
        CheckResult('actions', tuple(check_actions(files))),
        CheckResult('protocol_object', tuple(check_protocol_object(files))),
        CheckResult('filter_blocks', tuple(check_filter_blocks(files))),
        CheckResult('certificate_blocks', tuple(check_certificate_blocks(files))),
        CheckResult('references', tuple(check_references(files))),
        CheckResult('variables', tuple(check_variables(files))),
        CheckResult('data_files', tuple(check_data_files(Path(output_dir)))),
        # The cross-check is the one rule that reads the run's ledger, so a caller that passes no ledger
        # gets NOT RUN, not an empty count: an empty count would read as a rule that ran and passed.
        CheckResult('round_trip',
                    tuple(check_round_trip(files, ledger)) if ledger is not None else (),
                    ran=ledger is not None,
                    note="the cross-check reads the run's ledger, so pass it to the gate"),
        CheckResult('control_chars', tuple(check_control_chars(files))),
        CheckResult('placeholders', tuple(check_placeholders(files))),
    ]
    if run_terraform:
        binary = terraform or shutil.which('terraform')
        # F6.10.3 (§14): one plan reads one root, so the plan check runs once per unit directory the
        # manifest record names. A run that names no unit has no unit directory, so the check runs on the
        # codebase root, which is where the gate reads the files.
        units = unit_directories(Path(output_dir))
        if not units:
            checks.append(check_terraform(Path(output_dir), binary, '.'))
        else:
            for directory in units:
                checks.append(check_terraform(Path(output_dir) / directory, binary, directory))
    else:
        # State the check the caller did not ask for, so the report cannot look as
        # if the terraform gate is part of the default run.
        checks.append(CheckResult('terraform', (), ran=False, note='run the converter with --validate'))
    return SanityReport(
        checks=tuple(checks),
        file_count=len(files),
        data_file_count=count_data_files(Path(output_dir)),
        resource_count=len(resource_blocks(files)),
    )
