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
| `location_present` | every resource block carries a `location` block | FAIL |
| `references` | every `.name` reference resolves to a resource declared in the same run | FAIL |
| `variables` | every declared variable has a `var.` consumer | FAIL |
| `control_chars` | no raw control character or DEL in a `.tf` file | FAIL |
| `placeholders` | an expected placeholder is listed so the operator replaces it | WARN |
| `terraform` | `terraform init` + `terraform validate` (`--validate` only) | FAIL or SKIPPED |

Exit code: 0 when no finding is FAIL, 1 when one is. A WARN and a SKIPPED do
not fail the gate, so a run that only needs an operator action still exits 0
and an offline run still reports the checks it could not run.
"""

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import resource_mapping

FAIL = 'FAIL'
WARN = 'WARN'
SKIP = 'SKIPPED'
NOT_RUN = 'NOT RUN'

# Report order. The order is fixed so the report is byte-identical between runs.
CHECK_ORDER = (
    'emitted_types',
    'location_present',
    'references',
    'variables',
    'control_chars',
    'placeholders',
    'terraform',
)

REPORT_RULE = '=' * 80

# A resource block header. The body ends at the first column-0 brace, which is
# how the generator writes a block and how the existing tests read one.
RESOURCE_RE = re.compile(r'resource\s+"([a-z0-9_]+)"\s+"([^"]+)"\s*\{')
VARIABLE_RE = re.compile(r'^variable\s+"([A-Za-z0-9_]+)"', re.M)
REFERENCE_RE = re.compile(r'\b(panos_[a-z0-9_]+)\.([a-z0-9_]+)\.name\b')
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
class ResourceBlock:
    """One `resource` block as the operator reads it."""

    file: str
    line: int
    rtype: str
    local: str
    body: str


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


def resource_blocks(files: dict[str, str]) -> list[ResourceBlock]:
    """Every `resource` block, in file order then line order."""
    blocks = []
    for name in sorted(files):
        text = files[name]
        for match in RESOURCE_RE.finditer(text):
            end = text.find('\n}', match.end())
            body = text[match.end():end] if end != -1 else text[match.end():]
            blocks.append(ResourceBlock(
                name,
                text.count('\n', 0, match.start()) + 1,
                match.group(1),
                match.group(2),
                body,
            ))
    return blocks


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
    """Provider v2 requires `location` on every resource (F2.3)."""
    findings = []
    for block in resource_blocks(files):
        if 'location = {' not in block.body:
            findings.append(Finding(
                'location_present', FAIL, block.file, block.line,
                f'resource {block.rtype}.{block.local} has no location block',
            ))
    return findings


def check_references(files: dict[str, str]) -> list[Finding]:
    """Every `.name` reference must resolve to a resource declared in this run (F2.6)."""
    declared = {(block.rtype, block.local) for block in resource_blocks(files)}
    findings = []
    for name in sorted(files):
        for line, text in enumerate(files[name].split('\n'), start=1):
            for rtype, local in REFERENCE_RE.findall(text):
                if (rtype, local) not in declared:
                    findings.append(Finding(
                        'references', FAIL, name, line,
                        f'dangling reference {rtype}.{local}.name',
                    ))
    return findings


def check_variables(files: dict[str, str]) -> list[Finding]:
    """Every declared variable must be consumed as `var.<name>` (F2.10).

    A declaration is not a consumer: the consumer text is the whole output, but
    only a `var.` reference counts, so a variable cannot consume itself.
    """
    consumers = '\n'.join(files[name] for name in sorted(files))
    findings = []
    for file_name, name, line in variables(files):
        if not re.search(rf'\bvar\.{re.escape(name)}\b', consumers):
            findings.append(Finding(
                'variables', FAIL, file_name, line,
                f'variable {name} is declared but never consumed as var.{name}',
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
