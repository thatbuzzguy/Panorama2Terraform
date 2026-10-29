"""F4.1: post-run sanity gate.

Every rule this module enforces is stated once here. The tests call these
functions instead of restating a rule, so the gate that runs during a
conversion and the gate that runs during a test cannot disagree.

The checks read what the operator receives: the files written to the output
directory. A rule is satisfied by a file, not by a bookkeeping value that
never reached one.

Checks, in report order:

| Check | Rule | Severity |
|---|---|---|
| `emitted_types` | every resource type is in `EMITTED_TYPES` | FAIL |
| `location_present` | every `resource` and `data` block carries a `location` block | FAIL |
| `data_blocks` | every `data` block matches the `DATA_SOURCE_SCHEMA` row for its type | FAIL |
| `import_blocks` | every `import` block agrees with the `resource` block it names | FAIL, WARN |
| `scope_blocks` | a name inside a scope block's `location` names a scope this run declares | FAIL |
| `references` | every `.name` reference resolves to a block declared in the same run, by kind | FAIL |
| `variables` | a declared variable has a `var.` consumer, and a `var.` consumer names a declared variable | FAIL |
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

import entry_coverage
import import_blocks
import naming
import resource_mapping

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
    'references',
    'variables',
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
    """One rule violation, or one reported fact, at one line of one file."""

    check: str
    severity: str
    file: str
    line: int
    detail: str

    def render(self) -> str:
        location = f'{self.file}:{self.line}' if self.file else '(run)'
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
        match = re.search(r'\blocation\s*=\s*\{', self.body)
        if match is None:
            return ''
        start = match.end() - 1
        depth = 0
        for index in range(start, len(self.body)):
            char = self.body[index]
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return self.body[start + 1:index]
        return self.body[start + 1:]

    def attribute(self, key: str) -> str:
        """One quoted field of this block, as the gate reads it (the one field reader)."""
        return import_blocks.block_value(self, key)

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
    resource_count: int

    def findings(self, check: str) -> list[Finding]:
        """Findings for one check, in report order."""
        for result in self.checks:
            if result.check == check:
                return list(result.findings)
        return []

    def result_of(self, check: str) -> str:
        for result in self.checks:
            if result.check == check:
                return result.result
        return NOT_RUN

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
        lines.append(f'Files checked: {self.file_count} .tf files.')
        lines.append(f'Resources checked: {self.resource_count}.')
        lines.append('')
        lines.append('CHECK RESULTS')
        lines.append('-' * 80)
        for name in CHECK_ORDER:
            result = next((r for r in self.checks if r.check == name), None)
            if result is None:
                continue
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
                result = next((r for r in self.checks if r.check == name), None)
                if result is None or not result.findings:
                    continue
                lines.append(f'[{name}]')
                for finding in result.findings:
                    lines.append(f'  {finding.render()}')
        return '\n'.join(lines) + '\n'

    def console_summary(self) -> str:
        """The short console summary. One line per check, then each finding."""
        lines = [
            f'Sanity gate: {"FAIL" if self.failed else "PASS"} '
            f'({self.fail_count} FAIL, {self.warn_count} WARN) - '
            f'{self.file_count} .tf files, {self.resource_count} resources'
        ]
        for name in CHECK_ORDER:
            result = next((r for r in self.checks if r.check == name), None)
            if result is None:
                continue
            lines.append(f'  {name}: {result.result}')
            for finding in result.findings:
                lines.append(f'    {finding.render()}')
        return '\n'.join(lines)


# --- Reading the output ------------------------------------------------------

def read_tf_files(output_dir: Path) -> dict[str, str]:
    """Read every `.tf` file in the output directory, keyed by file name.

    `surrogateescape` keeps a non-UTF-8 byte readable instead of raising, so
    the gate reports an unreadable file rather than crashing on it.
    """
    files = {}
    for path in sorted(Path(output_dir).glob('*.tf')):
        files[path.name] = path.read_text(encoding='utf-8', errors='surrogateescape')
    return files


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
                    timeout: int = 300) -> CheckResult:
    """Run `terraform init` + `terraform validate` on the output (`--validate`).

    A missing binary is a SKIPPED result, not a failure: the offline CI matrix
    has no terraform, and the static checks still decide the exit code.
    """
    if terraform is None:
        return CheckResult('terraform', (Finding(
            'terraform', SKIP, '', 0, 'terraform binary not found; skipped',
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
            'terraform', FAIL, '', 0, f'terraform init failed: {init_out[-2000:]}',
        ),))

    validate_code, validate_out = run(['validate'])
    if validate_code != 0:
        return CheckResult('terraform', (Finding(
            'terraform', FAIL, '', 0, f'terraform validate failed: {validate_out[-2000:]}',
        ),))
    note = next((line for line in validate_out.split('\n') if line.strip()), '')
    return CheckResult('terraform', (), note=note)


# --- The gate ----------------------------------------------------------------

def run_checks(output_dir: Path, run_terraform: bool = False,
               terraform: Optional[str] = None) -> SanityReport:
    """Run every static check on one output directory.

    `run_terraform` adds the terraform check. Pass `terraform=None` with
    `run_terraform=True` to report the check as SKIPPED.
    """
    files = read_tf_files(Path(output_dir))
    checks = [
        CheckResult('emitted_types', tuple(check_emitted_types(files))),
        CheckResult('location_present', tuple(check_location_present(files))),
        CheckResult('data_blocks', tuple(check_data_blocks(files))),
        CheckResult('import_blocks', tuple(check_import_blocks(files))),
        CheckResult('scope_blocks', tuple(check_scope_blocks(files))),
        CheckResult('references', tuple(check_references(files))),
        CheckResult('variables', tuple(check_variables(files))),
        CheckResult('control_chars', tuple(check_control_chars(files))),
        CheckResult('placeholders', tuple(check_placeholders(files))),
    ]
    if run_terraform:
        checks.append(check_terraform(Path(output_dir), terraform or shutil.which('terraform')))
    else:
        # State the check the caller did not ask for, so the report cannot look as
        # if the terraform gate is part of the default run.
        checks.append(CheckResult('terraform', (), ran=False, note='run the converter with --validate'))
    return SanityReport(
        checks=tuple(checks),
        file_count=len(files),
        resource_count=len(resource_blocks(files)),
    )
