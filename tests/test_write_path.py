"""F6.10.3 the write path: which file belongs to the unit set and which to the codebase root set, the one
function that writes bytes, and how the gate reads each set
(`docs/CODEBASE_ASSEMBLY.md` §14, `docs/ARCHITECTURE.md` §6).

Four groups:

1. The two sets: the unit set is the `.tf` files of one unit plus that unit's printed form, the codebase
   root set is the records the whole codebase owns, and the two are distinct.
2. How the gate reads each set: one block reader keyed by the path from the codebase root, one data rule
   that reads the records at the root as one rule over the rows of every unit, and no rule reads a report.
3. The one write path: one function writes bytes, `newline=LF` is forced there, and no other module of the
   tool writes a file, so the byte rule (`docs/ARCHITECTURE.md` §6) is enforced in one place.
4. Default output, not an opt-in: no flag names the layout, so a golden can pin what a default run emits.

Every test reads the corpus run through the rules. The run writes one directory per unit
`unit_manifest.units` names, so the path the reader keys by names the unit the file belongs to, because a
per-unit file carries no unit field. The directory name and the row shape are pinned in
`tests/test_unit_manifest.py`; the printed form, the two counts and the report lines are pinned in
`tests/test_data_file_gate.py`; the per-type file table is pinned by `tests/test_coverage_matrix.py`.
"""

import shutil
from pathlib import Path

import pytest

import commit_actions
import import_blocks
import naming
import ownership
import provenance
import reference_edges
import resource_mapping
import sanity_checks
import site_data
import unit_manifest
import write_path
from conftest import FIXTURES_DIR, GOLDEN_DIR, SRC_DIR, run_script

# The layout rule (`docs/ARCHITECTURE.md` §1.1): `src/` holds the tool's modules, so the pins that read a
# module source read it through `SRC_DIR`, and the scan reads the `src/` set.
CONVERTER = SRC_DIR / 'panorama_to_terraform.py'
KITCHEN = 'kitchen_sink.xml'

# The codebase root set, as the decision states it: the four records, the report files, README.md,
# SOURCE.txt. Each record is named through the module that owns its row shape, so the test states no second
# list. A report is named by shape, because a run writes one only when it has content.
RECORDS = {
    unit_manifest.MANIFEST_FILE: unit_manifest,
    ownership.OWNERSHIP_FILE: ownership,
    reference_edges.EDGE_FILE: reference_edges,
    site_data.SITE_DATA_FILE: site_data,
}
REPORT_SHAPE = '.txt'
ROOT_TEXT = ('README.md', 'SOURCE.txt')

# The unit set, as the decision states it: the per-type `.tf` files of one unit, plus the files the run
# writes once per unit, plus that unit's printed form. The per-type table names one file per resource kind,
# so the list here names the shapes the table does not: the files that hold no resource block, and the file
# that holds the profile names as comments.
UNIT_FILES = ('provider.tf', 'scope.tf', import_blocks.IMPORT_FILE, commit_actions.ACTIONS_FILE,
             'variables.tf', 'read_through.tf', 'security_profiles.tf', site_data.TFVARS_FILE)

# A unit directory the corpus manifest names, for the pins that read a file inside one.
UNIT_DIR = 'shared_a6577c11'

# The words a flag would need to name the layout. The scan reads `--help`, so the test names none of them.
LAYOUT_WORDS = ('unit', 'directory', 'split', 'layout', 'flat')


@pytest.fixture(scope='session')
def corpus_run(tmp_path_factory) -> Path:
    """One corpus run, so a test measures the two file sets through the run."""
    out = tmp_path_factory.mktemp('write_path_corpus')
    result = run_script(CONVERTER, str(FIXTURES_DIR / KITCHEN), '--output-dir', str(out))
    assert result.returncode == 0, result.stderr
    return out


def _copy(source_dir: Path, out_dir: Path) -> Path:
    """Copy one run's output, so a test can add a file without touching the pinned run."""
    shutil.copytree(source_dir, out_dir)
    return out_dir


def _rule_source(name: str, stop: str) -> str:
    """One rule's source, so a scan pins what that rule reads."""
    source = Path(sanity_checks.__file__).read_text(encoding='utf-8')
    return source[source.index(f'def {name}'):source.index(stop)]


def _for_file(findings: list, name: str) -> list:
    """The findings for one file, so a test reads only the finding its own rule states."""
    return [finding for finding in findings if finding.file == name]


def _rows(corpus_out: Path) -> list:
    """The manifest rows of one run, read through the module that owns the row shape."""
    return unit_manifest.parse_rows((corpus_out / unit_manifest.MANIFEST_FILE).read_text(encoding='utf-8'))


def _read_files(report: sanity_checks.SanityReport) -> set:
    """The files the report named, so a test pins that a finding names a file in one of the two sets."""
    return {finding.file for result in report.checks for finding in result.findings if finding.file}


# --- 1. The two sets -------------------------------------------------------------

def test_the_unit_set_and_the_codebase_root_set_are_distinct(corpus_run):
    """The unit set is the `.tf` files of one unit plus that unit's printed form; the codebase root set is the
    records the whole codebase owns. No file shape is in both, and the printed form is in neither, because the
    data rule compares it and does not count it.
    """
    files = sanity_checks.read_tf_files(corpus_run)
    assert files and all(name.endswith('.tf') for name in files), 'the block reader reads the unit set'
    assert RECORDS and not any(name.endswith('.tf') for name in RECORDS), 'the root set is the records'
    assert not set(RECORDS) & {Path(name).name for name in files}, 'no file shape is in both sets'
    assert site_data.TFVARS_FILE not in RECORDS, 'the printed form is compared and not counted'

    # A unit-set file names the kind it holds, never the unit, so the path is the only place a file states the
    # unit it belongs to.
    per_unit = sorted(row['output_file'] for row in resource_mapping.COVERAGE_MATRIX)
    assert per_unit and all(name.endswith('.tf') for name in per_unit), 'the per-type table is the unit set'
    for name in per_unit + [import_blocks.IMPORT_FILE, commit_actions.ACTIONS_FILE]:
        assert Path(name).name == name and 'unit' not in name, name
    assert not [name for name in per_unit if name in RECORDS], 'no unit-set file is a record'
    assert all(Path(name).name in set(per_unit) | set(UNIT_FILES) for name in files), \
        'the reader read only unit-set files'
    assert not [name for name in files if Path(name).name in set(RECORDS) | set(ROOT_TEXT)], \
        'the codebase root set holds no .tf file'


def test_a_per_unit_file_names_no_path_so_the_reader_names_the_unit(corpus_run):
    """The unit set is stated once, in the manifest row, so a per-unit file carries no unit field and states no
    path: the path from the codebase root is the only place a file names the unit it belongs to, and that is
    what a finding names.
    """
    files = sanity_checks.read_tf_files(corpus_run)
    dirs = {row['directory'] for row in _rows(corpus_run)}
    assert dirs and files
    assert all(Path(name).parent.name in dirs for name in files), 'the key names the unit directory'
    for name, content in files.items():
        assert not [directory for directory in dirs if f'{directory}/' in content], (name, 'no path inside')

    printed = {str(p.relative_to(corpus_run)): p.read_text(encoding='utf-8')
               for p in sorted(corpus_run.rglob(site_data.TFVARS_FILE))}
    assert printed, 'the printed form is a unit-set file, so it sits in the unit directory its row names'
    for path, text in printed.items():
        assert Path(path).parent.name in dirs, path
        assert not [directory for directory in dirs if f'{directory}/' in text], (path, 'no path inside')


def test_the_run_writes_one_directory_per_unit_the_manifest_names(corpus_run):
    """The write path is what F6.10.3 landed: the manifest row names the unit, so the run writes one directory
    per unit `unit_manifest.units` names, and the directory holds the unit set. A unit the manifest names gets
    a directory even when the run writes no block inside it, so the shape is the rule and not the content.
    """
    rows = _rows(corpus_run)
    assert len(rows) == 11, 'the corpus names eleven units, so one set per unit is eleven sets'
    dirs = sorted(row['directory'] for row in rows)
    assert sorted(p.name for p in corpus_run.iterdir() if p.is_dir()) == dirs, \
        'one directory per unit, named by the row, in the order the row prints'
    assert all((corpus_run / name).is_file() for name in RECORDS), 'one file per record for the codebase'
    assert not [p for p in corpus_run.iterdir() if p.is_file() and p.name.endswith('.tf')], \
        'the codebase root holds no unit-set file'

    # Every file the run wrote names exactly one set, so a new file shape must name which set it belongs to.
    for path in sorted(p for p in corpus_run.rglob('*') if p.is_file()):
        name = path.name
        membership = [path.parent.name in dirs, name in RECORDS,
                      name in ROOT_TEXT or name.endswith(REPORT_SHAPE)]
        assert sum(membership) == 1, (str(path.relative_to(corpus_run)), membership)
    for directory in dirs:
        names = {p.name for p in (corpus_run / directory).iterdir()}
        assert 'provider.tf' in names and 'variables.tf' in names, \
            (directory, 'provider.tf and variables.tf are unit-set files, so every unit has them')
    assert any(site_data.TFVARS_FILE in {p.name for p in (corpus_run / directory).iterdir()}
               for directory in dirs), 'the printed form is written inside the unit directory its row names'


# --- 2. How the gate reads each set --------------------------------------------

def test_the_block_reader_walks_the_tree_and_a_finding_names_the_path(corpus_run, tmp_path):
    """The block rules read every `.tf` file below the codebase root, so a `.tf` file inside a unit directory
    is read, and a finding names the path from the codebase root: the path names the unit the file belongs to,
    because a per-unit file carries no unit field.
    """
    out = _copy(corpus_run, tmp_path / 'split')
    path = f'{UNIT_DIR}/variables.tf'
    # The test adds the file through the write path, so it states no second writer.
    write_path.write_file(out / path, 'variable "pinned_tree_walk" {\n  type = string\n}\n')

    files = sanity_checks.read_tf_files(out)
    assert path in files, 'the reader reads the unit set below the root'
    findings = sanity_checks.check_variables(files)
    assert _for_file(findings, path), 'the variables rule names the path from the codebase root'
    report = sanity_checks.run_checks(out)
    assert report.file_count == len(files), 'the count names the unit set'
    assert path in _read_files(report), 'the report names the path, not the file name'


def test_one_reader_serves_the_unit_set_so_no_rule_can_read_only_the_root(corpus_run):
    """One reader serves the whole unit set, so the gate holds no second rule for the layout: the reader walks
    the tree and keys by the path, so a finding names the unit. The two counts name the two sets.
    """
    files = sanity_checks.read_tf_files(corpus_run)
    dirs = {row['directory'] for row in _rows(corpus_run)}
    assert all(Path(name).parent.name in dirs for name in files), 'the reader key is the path from the root'

    reader = _rule_source('read_tf_files', 'def count_data_files')
    assert ".rglob('*.tf')" in reader and 'relative_to' in reader, 'the reader walks the tree, keyed by path'
    assert ".glob('*.tf')" not in reader, 'no block rule reads only the codebase root'

    report = sanity_checks.run_checks(corpus_run)
    assert report.file_count == len(files) and report.data_file_count == len(RECORDS), \
        'the two counts name the two sets'
    printed = {str(p.relative_to(corpus_run)) for p in corpus_run.rglob(site_data.TFVARS_FILE)}
    assert _read_files(report) <= set(files) | set(RECORDS) | printed, 'a finding names a file in one set'
    for finding in report.findings('data_files'):
        assert finding.file in set(RECORDS) | printed, (finding.render(), 'the data rule names a record')


def test_the_data_rule_reads_the_records_at_the_codebase_root_only(corpus_run, tmp_path):
    """The data rule stays at the codebase root, so a record inside a unit directory is neither read nor
    counted: the same broken row is a finding when the rule reads it at the root.
    """
    out = _copy(corpus_run, tmp_path / 'split')
    broken = '{"unit": "Shared"}'
    write_path.write_file(out / UNIT_DIR / unit_manifest.MANIFEST_FILE, broken)
    assert sanity_checks.check_data_files(out) == [], 'the rule reads no file inside a unit directory'
    assert sanity_checks.count_data_files(out) == len(RECORDS), 'the count names the records at the root'

    write_path.write_file(out / unit_manifest.MANIFEST_FILE, broken)
    assert _for_file(sanity_checks.check_data_files(out), unit_manifest.MANIFEST_FILE), \
        'the same row is a finding when the rule reads it at the root'


def test_the_data_rule_is_one_rule_over_the_rows_of_every_unit(corpus_run):
    """The data rule is called once for the codebase and reads one record that holds the rows of every unit,
    so no per-unit record and no second shape rule appears. Its printed-form half reads the file inside the
    directory each row names, so that half names the path.
    """
    rows = _rows(corpus_run)
    assert len({row['directory'] for row in rows}) == len(rows) == 11, 'one record holds every unit rows'
    assert dict(sanity_checks.DATA_FILES) == RECORDS, 'each record is read through the module that owns it'

    rule = _rule_source('check_data_files', 'def check_control_chars')
    assert 'parse_rows' in rule and 'for name, module in DATA_FILES' in rule and 'out / name' in rule, \
        'the rule reads the records at the root, through the module that owns each row shape'
    assert 'rglob' not in rule, 'the data rule reads no file inside a unit directory'
    assert 'unit_path' in rule and 'render_tfvars' in rule, \
        'the printed form is read through the write-path builder and the module that renders the row'

    assert sanity_checks.check_data_files(corpus_run) == [], 'the corpus run reads clean'
    report = sanity_checks.run_checks(corpus_run)
    assert [result.check for result in report.checks] == list(sanity_checks.CHECK_ORDER)
    assert len(report.results('data_files')) == 1, 'one data rule result for the run'


def test_a_printed_form_finding_names_the_path_of_the_unit_it_belonged_to(corpus_run, tmp_path):
    """The printed-form half of the data rule reads one unit's file, so its finding names the path from the
    codebase root, and the position is the row ordinal the record states.
    """
    out = _copy(corpus_run, tmp_path / 'printed')
    rows = site_data.parse_rows((out / site_data.SITE_DATA_FILE).read_text(encoding='utf-8'))
    assert rows, 'the corpus names a site row'
    row = rows[0]
    path = write_path.unit_path(out, row['directory'], site_data.TFVARS_FILE)
    write_path.write_file(path, '# not the row rendered by its rule\n')
    findings = sanity_checks.check_data_files(out)
    assert findings, 'a printed form that is not the rendered row is a finding'
    assert all(finding.file == str(path.relative_to(out)) for finding in findings), findings
    assert findings[0].line == 1, 'the position is the row ordinal the record states'


def test_no_rule_reads_a_file_outside_the_two_sets(corpus_run):
    """No rule reads a report, `README.md` or `SOURCE.txt`, so the gate reads exactly the two sets plus the
    printed form it compares. The scan reads the gate source, so the gate cannot add a reader for a report
    later without changing this test.
    """
    source = Path(sanity_checks.__file__).read_text(encoding='utf-8')
    for name in ROOT_TEXT + ('CONVERSION_REPORT', 'INTERFACE_MIGRATION_REPORT', 'MANUAL_SETUP_REPORT',
                             'STATE_COVERAGE_REPORT', 'VPN_MIGRATION_REPORT', 'SANITY_REPORT'):
        assert name not in source, (name, 'the gate reads no report')

    report = sanity_checks.run_checks(corpus_run)
    printed = {str(p.relative_to(corpus_run)) for p in corpus_run.rglob(site_data.TFVARS_FILE)}
    read = _read_files(report)
    assert read <= set(sanity_checks.read_tf_files(corpus_run)) | set(RECORDS) | printed, read
    assert not [name for name in read if name.endswith(REPORT_SHAPE)], 'no finding names a report'
    assert report.fail_count == 0, 'the corpus run reads clean'


def test_the_plan_check_runs_on_one_directory_per_unit(corpus_run, tmp_path, monkeypatch):
    """A unit is one plan and one root, so the check that runs a plan reads one directory: one result per unit
    directory the manifest record names. The check runs with `cwd` on the directory it is given, so it cannot
    read a tree of units as one root, and it names no file: it names the directory it ran on.
    """
    source = Path(sanity_checks.__file__).read_text(encoding='utf-8')
    check = source[source.index('def check_terraform'):source.index('# --- The gate')]
    caller = source[source.index('def run_checks'):]
    assert 'cwd=output_dir' in check, 'the check runs on the directory it is given'
    assert 'unit_directories' in caller and 'check_terraform(' in caller, \
        'the gate calls it once per unit directory the record names'
    assert "note=f'{unit}: {note}'" in check, 'a passing plan result names the directory it ran on, through the note'

    # A copy keeps the pinned run clean: a check that runs `terraform init` writes a cache directory.
    out = _copy(corpus_run, tmp_path / 'plan')
    units = [row['directory'] for row in _rows(corpus_run)]
    assert sanity_checks.unit_directories(out) == units, \
        'the gate reads the unit set through the module that owns the row shape'

    # `terraform=None` is the offline case, so the suite runs offline. The result names the directory.
    result = sanity_checks.check_terraform(out, None)
    assert result.check == 'terraform' and result.findings, 'the offline case states one result'
    assert all(finding.file == '.' for finding in result.findings), \
        'the plan check names no file, so the report names the directory it ran on'

    # An empty PATH is the offline case: `run_checks` finds no binary, so each unit gets one SKIPPED
    monkeypatch.setenv('PATH', '')
    offline = sanity_checks.run_checks(out, run_terraform=True)
    report = offline
    plan_results = report.results('terraform')
    assert len(plan_results) == len(units), 'one plan check result per unit directory'
    assert sorted(finding.file for result in plan_results for finding in result.findings) == sorted(units), \
        'each result names the directory it ran on, as the path from the codebase root'
    assert all(result.result == sanity_checks.SKIP for result in plan_results), \
        'a missing binary is a SKIPPED result, not a failure'
    assert report.fail_count == 0, 'the offline run still reports the checks it could not run'

    # A unit that failed cannot be hidden behind a unit that passed, because the report states the worst
    # result the check produced.
    failed = sanity_checks.CheckResult('terraform', (
        sanity_checks.Finding('terraform', sanity_checks.FAIL, units[0], 0, 'boom'),))
    mixed = sanity_checks.SanityReport(offline.checks + (failed,),
                                       offline.file_count, offline.data_file_count, offline.resource_count)
    assert len(mixed.results('terraform')) == len(units) + 1, 'the report keeps one result per unit'
    assert mixed.result_of('terraform') == sanity_checks.FAIL, 'a failed unit is not hidden'
    assert offline.result_of('terraform') == sanity_checks.SKIP, 'a check that only skipped is SKIPPED'


# --- 3. The one write path -----------------------------------------------------

def test_one_function_writes_bytes_and_no_other_module_writes_a_file():
    """The LF rule is in the one write function, so the byte rule holds on every desktop: `open(..., 'w')`
    writes `os.linesep`, so a run on a Windows desktop writes CRLF and the goldens stop matching byte for
    byte. The scan reads the tool's modules, so no module can write a file outside the write path.
    """
    source = Path(write_path.__file__).read_text(encoding='utf-8')
    assert "LF = '\\n'" in source and 'newline=LF' in source, 'the byte rule is stated in the write path'
    writer = source[source.index('def write_file'):]
    assert 'newline=LF' in writer, 'the byte rule is in the one write function'
    assert 'import os' not in source, 'the write path never names the platform line ending'

    writers = []
    for path in sorted(SRC_DIR.glob('*.py')):
        if path.name == 'write_path.py':
            # The single writer is not a writer itself. The test harness is outside this set: `tests/` holds
            # the tests, and `src/` holds the tool's modules (`docs/ARCHITECTURE.md` §1.1).
            continue
        for line in path.read_text(encoding='utf-8').splitlines():
            # `write_file` is the single writer, so a module that calls it is not a writer itself.
            if 'write_text' in line or 'write_bytes' in line or 'os.linesep' in line or \
                    'open(' in line and ("'w'" in line or '"w"' in line or "'a'" in line):
                writers.append((path.name, line.strip()))
    assert not writers, writers
    assert not [line for line in Path(CONVERTER).read_text(encoding='utf-8').splitlines()
                if 'write_text' in line], 'the tool writes through the write path'


def test_a_record_module_renders_rows_and_writes_no_file():
    """A record module owns its row shape and its file name, and its usage example writes through the write
    path, so no module builds a path for a file it does not own.
    """
    for module in (unit_manifest, ownership, reference_edges, site_data, provenance):
        usage = Path(module.__file__).read_text(encoding='utf-8')
        assert 'write_file(' in usage and 'write_path' in usage, (module.__name__, 'the usage example writes')
        assert not any(line.strip().startswith('def write') for line in usage.splitlines()), \
            (module.__name__, 'a record module writes no file')


def test_the_write_path_states_two_builders_one_per_set():
    """The unit set is written inside the directory the row names and the root set at the root, so a writer
    names which builder it uses.
    """
    assert write_path.unit_path(Path('out'), 'shared_45ca31c3', 'provider.tf') == \
        Path('out') / 'shared_45ca31c3' / 'provider.tf'
    assert write_path.root_path(Path('out'), unit_manifest.MANIFEST_FILE) == \
        Path('out') / unit_manifest.MANIFEST_FILE

    generator = Path(CONVERTER).read_text(encoding='utf-8')
    assert 'write_path.write_file(' in generator, 'the tool writes through the write path'
    assert 'def write_unit_file' in generator and 'def write_root_file' in generator, \
        'the tool names which builder each writer uses'
    assert 'def write_file' in Path(write_path.__file__).read_text(encoding='utf-8'), \
        'the one function that writes bytes'


def test_the_bytes_a_run_writes_hold_no_cr(corpus_run):
    """The LF rule is what the goldens and the determinism rule measure, so every byte a run writes holds LF
    and no CR, including the per-unit layout.
    """
    dirs = {row['directory'] for row in _rows(corpus_run)}
    # Only the files the run wrote are the run's bytes, so the scan reads the two sets and not a cache.
    written = [p for p in sorted(corpus_run.rglob('*'))
               if p.is_file() and (p.parent.name in dirs or p.parent == corpus_run)]
    assert written, 'the corpus run writes files'
    crlf = [str(p.relative_to(corpus_run)) for p in written if b'\r' in p.read_bytes()]
    assert not crlf, crlf
    for path in sorted(GOLDEN_DIR.rglob('*')):
        if path.is_file():
            assert b'\r' not in path.read_bytes(), str(path)


def test_two_runs_on_the_same_bytes_write_the_same_bytes_in_the_same_layout(tmp_path):
    """Two runs on the same input write the same bytes, including the per-unit layout, so the golden byte rule
    holds for the file set the run now writes.
    """
    first = run_script(CONVERTER, str(FIXTURES_DIR / KITCHEN), '--output-dir', str(tmp_path / 'first'))
    second = run_script(CONVERTER, str(FIXTURES_DIR / KITCHEN), '--output-dir', str(tmp_path / 'second'))
    assert first.returncode == 0 and second.returncode == 0, (first.stderr, second.stderr)

    def shape(out: Path) -> dict:
        return {str(p.relative_to(out)): p.read_bytes() for p in sorted(out.rglob('*')) if p.is_file()}

    assert shape(tmp_path / 'first') == shape(tmp_path / 'second')
    layout = [path for path in shape(tmp_path / 'first') if path.endswith('.tf')]
    assert layout and all('/' in path for path in layout), 'the layout is one directory per unit'


# --- 4. Default output, not an opt-in ------------------------------------------

def test_no_flag_names_the_write_path():
    """The write path is default output, so a flag cannot select the layout: a flag would give the reference
    rule two shapes and force two gate readers, and the committed goldens pin what a default run emits. The
    modules that own the file names own no argument.
    """
    help_text = run_script(CONVERTER, '--help').stdout
    flags = [line.split()[0] for line in help_text.splitlines() if line.strip().startswith('--')]
    assert flags, help_text
    assert not [flag for flag in flags if any(word in flag for word in LAYOUT_WORDS)], flags
    for module in (naming, unit_manifest, import_blocks, commit_actions, site_data, sanity_checks, write_path):
        assert not hasattr(module, 'add_arguments'), module.__name__
    assert 'unit' not in reference_edges.FIELD_ORDER, 'the reference shape states no directory'


def test_the_golden_set_reads_as_the_unit_set_so_the_case_holds_unit_directories(corpus_run):
    """The goldens pin what a default run emits, so an opt-in shape cannot be pinned: no golden holds a
    directory the run writes only when a flag is on. The golden set is the unit set, read as paths from the
    case directory, so the same pin holds for a golden case that holds unit directories; the records and the
    reports are not in it, because they describe the whole codebase.
    """
    per_unit = {row['output_file'] for row in resource_mapping.COVERAGE_MATRIX}
    for case in ('sample', 'kitchen_sink', 'single_unit'):
        case_dir = GOLDEN_DIR / case
        paths = sorted(str(p.relative_to(case_dir)) for p in case_dir.rglob('*.tf'))
        assert paths, case
        # The case is read as paths from the case directory, so every entry names one unit.
        assert all(Path(name).parent.name for name in paths), 'the case holds unit directories'
        assert all(Path(name).name in set(per_unit) | set(UNIT_FILES) for name in paths), paths
    assert sorted(sanity_checks.read_tf_files(corpus_run)) == \
        sorted(str(p.relative_to(GOLDEN_DIR / 'kitchen_sink')) for p in (GOLDEN_DIR / 'kitchen_sink').rglob('*.tf')), \
        'the gate reading and the golden reading read the same unit set'
    assert not [p for p in GOLDEN_DIR.rglob('*') if p.is_file() and p.name in RECORDS], \
        'the records and the reports are not in the golden set'
    single = GOLDEN_DIR / 'single_unit'
    paths = sorted(str(p.relative_to(single)) for p in single.rglob('*.tf'))
    assert paths, 'the single-unit case pins one unit directory'
    assert len({Path(name).parent.name for name in paths}) == 1, 'one unit, so one directory'
