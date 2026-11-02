"""F6.10.1 the shape of the write path (the decision): which file belongs to the unit set and which to the
codebase root set, the default shape, and how the gate reads each set
(`docs/CODEBASE_ASSEMBLY.md` §14).

Three groups:

1. The two sets: the unit set is the `.tf` files of one unit plus that unit's printed form, the codebase
   root set is the records the whole codebase owns, and the two are distinct.
2. How the gate reads each set: one block reader keyed by the path from the codebase root, one data rule
   that reads the records at the root as one rule over the rows of every unit, and no rule reads a report.
3. Default output, not an opt-in: no flag names the layout, so a golden can pin what a default run emits.

Every test reads the corpus run through the rules and changes no output byte. The step that writes one
directory per unit is still open, so the corpus run writes no unit directory and every path the gate names
is a file name. The one-file-per-codebase rule and the directory name are pinned in
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
import reference_edges
import resource_mapping
import sanity_checks
import site_data
import unit_manifest
from conftest import FIXTURES_DIR, GOLDEN_DIR, run_script

CONVERTER = 'panorama_to_terraform.py'
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

# A unit directory the corpus manifest names, for the pins that read a file inside one.
UNIT_DIR = 'shared_0bc98741'

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
    """Copy one run's output, so a test can add a unit directory without touching the pinned run."""
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


# --- 1. The two sets -------------------------------------------------------------

def test_the_unit_set_and_the_codebase_root_set_are_distinct(corpus_run):
    """The unit set is the `.tf` files of one unit plus that unit's printed form; the codebase root set is the
    records the whole codebase owns. No file shape is in both, and the printed form is in neither, because the
    data rule compares it and does not count it.
    """
    files = sanity_checks.read_tf_files(corpus_run)
    assert files and all(name.endswith('.tf') for name in files), 'the block reader reads the unit set'
    assert RECORDS and not any(name.endswith('.tf') for name in RECORDS), 'the root set is the records'
    assert not set(RECORDS) & set(files), 'no file shape is in both sets'
    assert site_data.TFVARS_FILE not in RECORDS and site_data.TFVARS_FILE not in files, \
        'the printed form is compared and not counted'

    # A unit-set file names the kind it holds, never the unit, so the path is the only place a file states the
    # unit it belongs to.
    per_unit = sorted(row['output_file'] for row in resource_mapping.COVERAGE_MATRIX)
    assert per_unit and all(name.endswith('.tf') for name in per_unit), 'the per-type table is the unit set'
    for name in per_unit + [import_blocks.IMPORT_FILE, commit_actions.ACTIONS_FILE]:
        assert Path(name).name == name and 'unit' not in name, name
    assert not [name for name in per_unit if name in RECORDS], 'no unit-set file is a record'


def test_a_per_unit_file_names_no_path_so_the_reader_names_the_unit(corpus_run):
    """The unit set is stated once, in the manifest row, so a per-unit file carries no unit field and states no
    path: the path from the codebase root is the only place a file names the unit it belongs to, and that is
    what a finding names.
    """
    files = sanity_checks.read_tf_files(corpus_run)
    dirs = {row['directory'] for row in _rows(corpus_run)}
    assert dirs and not [name for name in files if '/' in name], \
        'for a flat run the reader key is the file name, so the unit is not named inside the file'
    for name, content in files.items():
        assert not [directory for directory in dirs if f'{directory}/' in content], (name, 'no path inside')
    printed = (corpus_run / site_data.TFVARS_FILE).read_text(encoding='utf-8')
    assert not [directory for directory in dirs if f'{directory}/' in printed], 'the printed form names no path'


def test_the_unit_set_is_one_set_per_unit_and_the_data_set_is_one_file_for_the_codebase(corpus_run):
    """The records describe the whole codebase, so the run writes one file per record; the unit set is the
    files one plan reads, so one directory holds them. The corpus names ten units, so the block set cannot be
    one file for the codebase: it is one set per unit, and the unit set is stated once, in the manifest row.
    """
    rows = _rows(corpus_run)
    assert len(rows) == 10, 'the corpus names ten units, so one set per unit is ten sets'
    assert all((corpus_run / name).is_file() for name in RECORDS), 'one file per record for the codebase'

    files = sanity_checks.read_tf_files(corpus_run)
    root = sorted(p.name for p in corpus_run.iterdir() if p.is_file())
    assert set(files) == {name for name in root if name.endswith('.tf')}, \
        'the block reader reads the unit set the run wrote'
    # Every file the run wrote names exactly one set, so a new file shape must name which set it belongs to.
    for name in root:
        membership = [name.endswith('.tf'), name in RECORDS, name == site_data.TFVARS_FILE,
                      name in ROOT_TEXT or name.endswith(REPORT_SHAPE)]
        assert sum(membership) == 1, (name, membership)
    assert all(name in ROOT_TEXT or name.endswith(REPORT_SHAPE) for name in root
               if not name.endswith('.tf') and name not in RECORDS and name != site_data.TFVARS_FILE), \
        'the codebase root set holds no .tf file and no unit-set file'
    assert site_data.TFVARS_FILE in root, 'the printed form is a unit-set file, so no rule counts it'


# --- 2. How the gate reads each set --------------------------------------------

def test_the_block_reader_walks_the_tree_and_a_finding_names_the_path(corpus_run, tmp_path):
    """The block rules read every `.tf` file below the codebase root, so a `.tf` file inside a unit directory
    is read, and a finding names the path from the codebase root: the path names the unit the file belongs to,
    because a per-unit file carries no unit field.
    """
    out = _copy(corpus_run, tmp_path / 'split')
    unit = out / UNIT_DIR
    unit.mkdir()
    (unit / 'variables.tf').write_text('variable "pinned_tree_walk" {\n  type = string\n}\n', encoding='utf-8')

    files = sanity_checks.read_tf_files(out)
    path = f'{UNIT_DIR}/variables.tf'
    assert path in files, 'the reader reads the unit set below the root'
    findings = sanity_checks.check_variables(files)
    assert _for_file(findings, path), 'the variables rule names the path from the codebase root'
    report = sanity_checks.run_checks(out)
    assert report.file_count == len(files), 'the count names the unit set'
    assert path in {finding.file for result in report.checks for finding in result.findings}, \
        'the report names the path, not the file name'


def test_for_a_flat_run_the_path_is_the_file_name_so_no_report_byte_changes(corpus_run):
    """One reader serves today's flat run and the split run, so the gate holds no second rule for the layout:
    for a run that writes no unit directory the key is the file name, so the bytes a report names are
    unchanged. The scan pins that no rule can read only the codebase root.
    """
    files = sanity_checks.read_tf_files(corpus_run)
    assert all(name == Path(name).name for name in files), 'for a flat run the path is the file name'
    reader = _rule_source('read_tf_files', 'def count_data_files')
    assert ".rglob('*.tf')" in reader and 'relative_to' in reader, 'the reader walks the tree, keyed by path'
    assert ".glob('*.tf')" not in reader, 'no block rule reads only the codebase root'

    report = sanity_checks.run_checks(corpus_run)
    assert report.file_count == len(files) and report.data_file_count == len(RECORDS)
    for result in report.checks:
        for finding in result.findings:
            assert not finding.file or Path(finding.file).name == finding.file, finding.render()


def test_the_data_rule_reads_the_records_at_the_codebase_root_only(corpus_run, tmp_path):
    """The data rule stays at the codebase root, so a record inside a unit directory is neither read nor
    counted: the same broken row is a finding when the rule reads it at the root.
    """
    out = _copy(corpus_run, tmp_path / 'split')
    unit = out / UNIT_DIR
    unit.mkdir()
    broken = '{"unit": "Shared"}'
    (unit / unit_manifest.MANIFEST_FILE).write_text(broken, encoding='utf-8')
    assert sanity_checks.check_data_files(out) == [], 'the rule reads no file inside a unit directory'
    assert sanity_checks.count_data_files(out) == len(RECORDS), 'the count names the records at the root'

    (out / unit_manifest.MANIFEST_FILE).write_text(broken, encoding='utf-8')
    assert _for_file(sanity_checks.check_data_files(out), unit_manifest.MANIFEST_FILE), \
        'the same row is a finding when the rule reads it at the root'


def test_the_data_rule_is_one_rule_over_the_rows_of_every_unit(corpus_run):
    """The data rule is called once for the codebase and reads one record that holds the rows of every unit,
    so no per-unit record and no second shape rule appears, and no finding names a path.
    """
    rows = _rows(corpus_run)
    assert len({row['directory'] for row in rows}) == len(rows) == 10, 'one record holds every unit rows'
    assert dict(sanity_checks.DATA_FILES) == RECORDS, 'each record is read through the module that owns it'

    rule = _rule_source('check_data_files', 'def check_control_chars')
    assert 'parse_rows' in rule and 'for name, module in DATA_FILES' in rule and 'out / name' in rule, \
        'the rule reads the records at the root, through the module that owns each row shape'
    assert 'rglob' not in rule, 'the data rule reads no file inside a unit directory'

    findings = sanity_checks.check_data_files(corpus_run)
    assert all(not finding.file or Path(finding.file).name == finding.file for finding in findings), \
        'the rule names one file for the codebase, not one per unit'
    report = sanity_checks.run_checks(corpus_run)
    assert [result.check for result in report.checks] == list(sanity_checks.CHECK_ORDER)
    assert list(sanity_checks.CHECK_ORDER).count('data_files') == 1, 'one data rule result for the run'


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
    read = {finding.file for result in report.checks for finding in result.findings}
    assert read <= set(sanity_checks.read_tf_files(corpus_run)) | set(RECORDS) | {site_data.TFVARS_FILE}, read
    assert not [name for name in read if name.endswith(REPORT_SHAPE)], 'no finding names a report'
    assert report.fail_count == 0, 'the corpus run reads clean'


def test_the_plan_check_runs_on_one_directory_and_a_unit_is_one_directory(corpus_run):
    """A unit is one plan and one root, so the check that runs a plan reads one directory: the codebase root
    today, and each unit directory when the write path lands, because `provider.tf` and `variables.tf` are
    unit-set files. The check runs with `cwd` on the directory it is given, so it cannot read a tree of units
    as one root, and it names no file: it names the directory it ran on.
    """
    source = Path(sanity_checks.__file__).read_text(encoding='utf-8')
    check = source[source.index('def check_terraform'):source.index('# --- The gate')]
    caller = source[source.index('def run_checks'):]
    assert 'cwd=output_dir' in check, 'the check runs on the directory it is given'
    assert 'check_terraform(Path(output_dir)' in caller, 'the gate calls it once, on the root it is given'
    result = sanity_checks.check_terraform(corpus_run, None)
    assert result.check == 'terraform' and all(not finding.file for finding in result.findings), \
        'the plan check names no file, so the report names the directory it ran on'


# --- 3. Default output, not an opt-in ------------------------------------------

def test_no_flag_names_the_write_path():
    """The write path is default output, so a flag cannot select the layout: a flag would give the reference
    rule two shapes and force two gate readers, and the committed goldens pin what a default run emits. The
    modules that own the file names own no argument.
    """
    help_text = run_script(CONVERTER, '--help').stdout
    flags = [line.split()[0] for line in help_text.splitlines() if line.strip().startswith('--')]
    assert flags, help_text
    assert not [flag for flag in flags if any(word in flag for word in LAYOUT_WORDS)], flags
    for module in (naming, unit_manifest, import_blocks, commit_actions, site_data, sanity_checks):
        assert not hasattr(module, 'add_arguments'), module.__name__
    assert 'unit' not in reference_edges.FIELD_ORDER, 'the reference shape states no directory'


def test_the_golden_set_can_hold_unit_directories_so_only_default_output_can_be_pinned(corpus_run):
    """The goldens pin what a default run emits, so an opt-in shape cannot be pinned: no golden holds a
    directory the run writes only when a flag is on. The golden set is the unit set, read as paths from the
    case directory, so the same pin holds for a golden case that holds unit directories; the records and the
    reports are not in it, because they describe the whole codebase.
    """
    for case in ('sample', 'kitchen_sink'):
        case_dir = GOLDEN_DIR / case
        paths = sorted(str(p.relative_to(case_dir)) for p in case_dir.rglob('*.tf'))
        assert paths, case
        assert all(Path(name).name == name for name in paths), 'the committed goldens are flat today'
        assert all(name.endswith('.tf') for name in paths), 'the golden set is the unit set'
    assert sorted(sanity_checks.read_tf_files(corpus_run)) == \
        sorted(str(p.relative_to(GOLDEN_DIR / 'kitchen_sink')) for p in (GOLDEN_DIR / 'kitchen_sink').rglob('*.tf')), \
        'the gate reading and the golden reading read the same unit set'
    assert not [p for p in GOLDEN_DIR.rglob('*') if p.is_file() and p.name in RECORDS], \
        'the records and the reports are not in the golden set'


def test_no_unit_directory_is_written_yet(corpus_run):
    """The decision is not the write path: the step that writes one directory per unit is still open, so the
    corpus run writes the unit set at the codebase root. This pin changes when the write step lands, and it is
    the place that shows the decision is not implemented.
    """
    assert not [p for p in corpus_run.iterdir() if p.is_dir()], 'no unit directory is written yet'
    rows = _rows(corpus_run)
    assert len(rows) == 10 and all(row.get('directory') for row in rows), \
        'the name a directory would carry is already decided'
