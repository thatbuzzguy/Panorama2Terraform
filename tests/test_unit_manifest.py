"""F6.1: the unit boundary as data, the codebase manifest.

Seven groups, one per rule in `unit_manifest.py` and `acceptance.md`:

1. The unit. One row per combination of the four scope facts, built from the ledger
   `entry_coverage.py` already writes, so F6.1 adds no parse data.
2. The directory naming rule. `sanitize(unit name) + '_' + 8-hex digest of the unit identity`,
   always, so a name depends on the unit alone and not on the other units in the run.
3. The row shape. Fixed fields in the declared order, rows in identity order, read back as data.
4. The reference names, recorded by `name_ref` at the site that applies the reference rule.
5. The no-change rule. The `.tf` bytes, the report bytes, the gate inputs, and the exit codes.
6. The CLI, and the rule that a file is written only when it has content.
7. Determinism. Two runs on the same bytes write the same bytes.

The manifest names the directory; F6.1 does not write one. Every test runs offline.
"""

import contextlib
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

import container_coverage
import entry_coverage
import ownership
import reference_edges
import sanity_checks
import site_data
import unit_manifest
from conftest import FIXTURES_DIR, GOLDEN_DIR, SAMPLE_CONFIG, run_script

CONVERTER = 'panorama_to_terraform.py'
GROUPING = 'report_grouping.xml'
MULTI = 'multi_device_templates.xml'
MANIFEST = unit_manifest.MANIFEST_FILE

# The reference names the grouping fixture produces, keyed by the referrer's four facts.
GROUPING_REFERENCES = {
    ('', '', '', ''): ('IKE-DEFAULT',),
    ('Datacenter-FW', '', '', ''): ('IKE-DEFAULT', 'IPSEC-DEFAULT'),
    ('Datacenter-FW', 'vsys2', '', ''): ('IKE-DEFAULT',),
    ('Office-FW', '', '', ''): ('IKE-DEFAULT', 'IPSEC-DEFAULT'),
}

# The units the grouping fixture shows, in the order the rows sort by the identity.
GROUPING_UNITS = [
    ('', '', '', ''),
    ('', '', '', 'fw-2.example.com'),
    ('', '', 'DC-Networks', ''),
    ('', '', 'DC-Networks', container_coverage.PLACEHOLDER_DEVICE),
    ('', '', 'HQ-Networks', ''),
    ('', '', 'HQ-Networks', 'fw-1.example.com'),
    ('Datacenter-FW', '', '', ''),
    ('Datacenter-FW', '', '', 'fw-2.example.com'),
    ('Datacenter-FW', 'vsys2', '', ''),
    ('Office-FW', '', '', ''),
    ('Office-FW', '', '', 'fw-1.example.com'),
]


def _run(source: Path, out_dir: Path, extra: tuple = ()) -> subprocess.CompletedProcess:
    """Run the converter as a script and return the process result."""
    return run_script(CONVERTER, str(source), '--output-dir', str(out_dir), *extra)


def _manifest(out_dir: Path) -> list:
    """A written manifest, read back as data."""
    return unit_manifest.parse_rows((out_dir / MANIFEST).read_text(encoding='utf-8'))


def _row(rows: list, facts: tuple) -> dict:
    """The row for one unit."""
    return next(row for row in rows if tuple(row[key] for key in unit_manifest.FACT_KEYS) == facts)


def _pipeline(converter_module, source: Path, out_dir: Path, extra: tuple = ()) -> tuple:
    """Run the pipeline in process and return (parser, generator).

    The reference record lives on the generator, so a test that wants it needs both objects, and
    the record is made during emission, so the run must be in process. `conftest.run_pipeline`
    returns the parser, so this hooks the generator the same way.
    """
    generator_class = converter_module.TerraformGenerator
    caught = {}
    parser_init = converter_module.PanoramaParser.__init__
    generator_init = generator_class.__init__

    def init_parser(self, *args, **kwargs):
        parser_init(self, *args, **kwargs)
        caught['parser'] = self

    def init_generator(self, *args, **kwargs):
        generator_init(self, *args, **kwargs)
        caught['generator'] = self

    saved_argv = list(sys.argv)
    converter_module.PanoramaParser.__init__ = init_parser
    generator_class.__init__ = init_generator
    try:
        sys.argv = [CONVERTER, str(source), '--output-dir', str(out_dir), *[str(a) for a in extra]]
        with contextlib.redirect_stdout(io.StringIO()):
            converter_module.main()
    finally:
        converter_module.PanoramaParser.__init__ = parser_init
        generator_class.__init__ = generator_init
        sys.argv = saved_argv
    return caught['parser'], caught['generator']


@pytest.fixture
def gen(converter_module, tmp_path):
    """A generator, for the naming rule the manifest reads through it.

    The class the script holds, so the test and the run share one sanitizing rule.
    """
    return converter_module.TerraformGenerator(str(tmp_path / 'gen'))


# --- 1. the unit ---------------------------------------------------------------

def test_one_row_per_combination_of_the_four_facts(converter_module, tmp_path):
    """A unit is one combination of the four scope facts, and the rows come from the ledger."""
    parser, _gen = _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    rows = _manifest(tmp_path)
    units = sorted({unit_manifest.facts_of(row) for row in parser.ledger.rows()})
    assert [tuple(row[key] for key in unit_manifest.FACT_KEYS) for row in rows] == units == GROUPING_UNITS
    assert sum(row['entry_count'] for row in rows) == len(parser.ledger.rows())


def test_the_scope_entry_is_one_of_its_rows(converter_module, tmp_path):
    """A declared scope is a ledger row, so the entry that defines a unit counts inside it.

    F6.5: a scope entry is an object, so the row that defines the unit is an `emitted` row.
    """
    parser, _gen = _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    defining = [row for row in parser.ledger.rows()
                if unit_manifest.facts_of(row) == ('Datacenter-FW', '', '', '')]
    assert [row for row in defining if row['name'] == 'Datacenter-FW']
    assert [row for row in defining if row['destination'] == 'emitted']
    assert _row(_manifest(tmp_path), ('Datacenter-FW', '', '', ''))['entry_count'] == len(defining)


def test_the_property_level_is_counted_on_the_parent_row(converter_module, tmp_path):
    """An entry inside a config-object entry is a property level (§3.1), so it is not a row of its
    own: the parent row shows the count.
    """
    parser, _gen = _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    office = [row for row in parser.ledger.rows() if unit_manifest.facts_of(row) == ('Office-FW', '', '', '')]
    parent = next(row for row in office if row['name'] == 'ethernet1/1')
    assert parent['property_entries'] == 1
    assert '10.1.1.1/24' not in [row['name'] for row in office], 'the ip entry is a property level'
    assert _row(_manifest(tmp_path), ('Office-FW', '', '', ''))['entry_count'] == len(office)


def test_the_shared_unit_is_the_unit_with_empty_facts_and_is_named_shared(converter_module, tmp_path):
    """`Shared` names the shared section (F3.9). The four facts alone cannot name it, so the row
    states the name.
    """
    _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    row = _row(_manifest(tmp_path), ('', '', '', ''))
    assert row['unit'] == unit_manifest.SHARED_UNIT
    assert row['device_group'] == '', 'Shared is the name of the unit, not a fact value'


def test_shared_in_device_group_is_not_a_fact_value(converter_module, tmp_path):
    """`Shared` in `device_group` is the parse fallback for an entry the parse cannot place (§2.2),
    so it never enters the identity. The state scan holds the same rule.
    """
    parser, _gen = _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    entry = next(row for row in parser.ledger.rows() if row['name'] == 'ethernet1/9')
    assert entry['device_group'] == ''
    object_facts = {'device_group': 'Shared', 'vsys': '', 'template': '', 'vsys_device': ''}
    assert unit_manifest.facts_of(object_facts) == unit_manifest.facts_of(entry)


def test_the_rows_are_sorted_by_the_identity_not_by_document_order(converter_module, tmp_path):
    """The sort is the identity order, so it is a total order and does not depend on document order.
    The grouping fixture puts the device groups first in the file.
    """
    _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    rows = _manifest(tmp_path)
    assert [tuple(row[key] for key in unit_manifest.FACT_KEYS) for row in rows] == GROUPING_UNITS
    assert rows[0]['device_group'] == '' and rows[-1]['device_group'] == 'Office-FW'


# --- 2. the directory naming rule --------------------------------------------

def test_the_directory_name_is_the_sanitized_name_plus_the_digest(gen, tmp_path):
    """The §5 shape, read through `TerraformGenerator.sanitize_name`, so no second naming rule
    exists here.
    """
    _run(FIXTURES_DIR / GROUPING, tmp_path)
    rows = _manifest(tmp_path)
    shared = hashlib.sha256(b'|||').hexdigest()[:8]
    assert _row(rows, ('', '', '', ''))['directory'] == f'{gen.sanitize_name("Shared")}_{shared}'

    facts = ('Datacenter-FW', 'vsys2', '', '')
    digest = hashlib.sha256(b'Datacenter-FW|vsys2||').hexdigest()[:8]
    assert _row(rows, facts)['directory'] == f'{gen.sanitize_name("vsys2")}_{digest}'


def test_the_manifest_defines_no_second_sanitize_or_naming_rule():
    """The manifest takes the §5 sanitizing rule as an argument, so the rule it owns is the identity
    digest and the unit name only.
    """
    assert not any(hasattr(unit_manifest, name) for name in ('sanitize_name', 'sanitize', 'name_ref'))


def test_a_name_that_sanitizes_to_nothing_keeps_the_shape(gen):
    """§5: an empty name becomes `unnamed`, so a directory name is never empty, and the shape a name
    sanitizes to is the §5 shape, not a second rule.
    """
    facts = ('!', '', '', '')
    assert unit_manifest.directory_name(facts, gen.sanitize_name) == \
        f'unnamed_{unit_manifest.identity_digest(facts)}'
    facts = ('Sales & Eng', '', '', '')
    assert gen.sanitize_name('Sales & Eng') == 'sales___eng'
    assert unit_manifest.directory_name(facts, gen.sanitize_name) == \
        f'sales___eng_{unit_manifest.identity_digest(facts)}'


def test_the_digest_is_always_present_not_only_on_a_collision(converter_module, tmp_path):
    """A collision-only rule would make one unit's name depend on the other units in the run, so an
    unrelated scope would move an existing directory. The digest is always in the name.
    """
    _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    rows = _manifest(tmp_path)
    for row in rows:
        facts = tuple(row[key] for key in unit_manifest.FACT_KEYS)
        assert row['directory'].rsplit('_', 1)[1] == unit_manifest.identity_digest(facts)
    # Two units that sanitize to the same base stay apart, by the digest alone.
    same_base = [row for row in rows if row['unit'] == 'fw-2.example.com']
    assert len(same_base) == 2 and len({row['directory'] for row in same_base}) == 2


def test_a_directory_name_does_not_move_when_an_unrelated_unit_is_added(tmp_path):
    """The name depends on the unit alone, so the same unit in two different runs gets the same
    directory name.
    """
    _run(FIXTURES_DIR / GROUPING, tmp_path / 'first')
    _run(FIXTURES_DIR / MULTI, tmp_path / 'second')
    first = _row(_manifest(tmp_path / 'first'), ('', '', '', ''))
    second = _row(_manifest(tmp_path / 'second'), ('', '', '', ''))
    assert first['directory'] == second['directory']
    assert first['unit'] == second['unit']


def test_the_deepest_declared_scope_names_the_unit(converter_module, tmp_path):
    """The unit name is the deepest scope the export declares, in the F3.9 level order."""
    _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    rows = _manifest(tmp_path)
    assert _row(rows, ('Datacenter-FW', 'vsys2', '', ''))['unit'] == 'vsys2'
    assert _row(rows, ('', '', 'HQ-Networks', ''))['unit'] == 'HQ-Networks'
    assert _row(rows, ('', '', 'HQ-Networks', 'fw-1.example.com'))['unit'] == 'fw-1.example.com'


def test_the_placeholder_device_names_no_unit(converter_module, tmp_path):
    """F3.5: `localhost.localdomain` names no firewall, so the unit takes the scope above it."""
    _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    row = _row(_manifest(tmp_path), ('', '', 'DC-Networks', container_coverage.PLACEHOLDER_DEVICE))
    assert row['unit'] == 'DC-Networks'
    assert row['vsys_device'] == container_coverage.PLACEHOLDER_DEVICE


# --- 3. the row shape ---------------------------------------------------------

def test_the_row_fields_are_the_declared_shape_in_order(tmp_path):
    """The row is data, so the field order is fixed and a document describes it without restating a
    row.
    """
    assert unit_manifest.FIELD_ORDER == ('unit', 'device_group', 'vsys', 'template', 'vsys_device',
                                         'directory', 'entry_count', 'references', 'rank', 'after')
    _run(FIXTURES_DIR / GROUPING, tmp_path)
    text = (tmp_path / MANIFEST).read_text(encoding='utf-8')
    assert list(json.loads(text)[0]) == list(unit_manifest.FIELD_ORDER)
    # Fields print in the declared order, not alphabetically.
    assert text.index('"unit"') < text.index('"device_group"') < text.index('"directory"')
    # F6.3 rule 5: the two order fields print after the F6.1 fields.
    assert text.index('"references"') < text.index('"rank"') < text.index('"after"')


def test_the_manifest_round_trips_as_data(gen, tmp_path):
    """A reader reads the file back as itself, the way `provenance.parse_record` reads a record."""
    _run(FIXTURES_DIR / GROUPING, tmp_path)
    rows = _manifest(tmp_path)
    assert rows and all(set(row) == set(unit_manifest.FIELD_ORDER) for row in rows)
    for row in rows:
        facts = tuple(row[key] for key in unit_manifest.FACT_KEYS)
        assert row['unit'] == unit_manifest.unit_name(facts)
        assert row['directory'] == unit_manifest.directory_name(facts, gen.sanitize_name)


def test_a_row_that_is_not_the_declared_shape_is_refused():
    """The manifest is data, so a reader cannot fall back to reading prose."""
    good = {'unit': 'Shared', 'device_group': '', 'vsys': '', 'template': '', 'vsys_device': '',
            'directory': 'shared_be5be69f', 'entry_count': 2, 'references': [],
            'rank': 1, 'after': []}
    assert unit_manifest.parse_rows(json.dumps([good]))[0]['directory'] == 'shared_be5be69f'
    bad_rows = (
        json.dumps({'unit': 'Shared'}),                       # not a list of rows
        json.dumps(['Shared']),                               # a row that is not an object
        json.dumps([dict(good, source_line=4)]),              # a field the shape does not declare
        json.dumps([{key: value for key, value in good.items() if key != 'entry_count'}]),
        json.dumps([dict(good, entry_count='2')]),
        json.dumps([dict(good, references='IKE-DEFAULT')]),
        json.dumps([dict(good, vsys=None)]),
        json.dumps([dict(good, rank='1')]),                   # F6.3: rank is a position
        json.dumps([dict(good, after='shared_be5be69f')]),    # F6.3: after is a list of directories
    )
    for bad in bad_rows:
        with pytest.raises(ValueError):
            unit_manifest.parse_rows(bad)


def test_the_manifest_is_one_file_for_the_codebase(tmp_path):
    """One file per run, one row per unit. A reader cannot find a per-unit file before it knows the
    directory name, and the directory name is the fact the manifest decides.

    F6.2: the two data files are the manifest (one row per unit) and the ownership record (one row
    per entry). F6.3 adds the edge record (one row per pair), which states neither a unit set nor an
    entry set, so the assertion names them. F6.6 adds the site record, which names only the units that
    state a value and joins to this row on `directory`, so the manifest stays the only place that states
    the unit set — which is why the unit order lives on this row instead (rule 5).
    """
    _run(FIXTURES_DIR / GROUPING, tmp_path)
    rows = _manifest(tmp_path)
    assert len(rows) == len(GROUPING_UNITS)
    assert (tmp_path / MANIFEST).is_file()
    data_files = {MANIFEST, ownership.OWNERSHIP_FILE, reference_edges.EDGE_FILE,
                  site_data.SITE_DATA_FILE}
    assert not any(p.name.endswith('.json') and p.name not in data_files for p in tmp_path.iterdir())
    assert not [p for p in tmp_path.iterdir() if p.is_dir()], 'F6.1 names the directory, it writes none'


# --- 4. the reference names ---------------------------------------------------

def test_the_reference_names_are_recorded_for_the_referrers_facts(converter_module, tmp_path):
    """The names `name_ref` resolved outside the run, keyed by the referrer's four scope facts, and
    printed sorted.
    """
    _parser, generator = _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    assert generator.unit_references() == GROUPING_REFERENCES
    rows = _manifest(tmp_path)
    for facts, names in GROUPING_REFERENCES.items():
        assert _row(rows, facts)['references'] == list(names)
    for row in rows:
        assert row['references'] == sorted(row['references'])


def test_a_contextless_call_site_records_the_name_for_the_referrers_unit(converter_module, tmp_path):
    """The VPN sites resolve through the shared chain with no call-site context, but the referrer
    sits in a declared scope, so the name is recorded for that unit, not for the shared one.
    """
    _parser, generator = _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    shared = ('', '', '', '')
    office = ('Office-FW', '', '', '')
    assert generator.unit_references()[shared] == ('IKE-DEFAULT',)
    assert 'IPSEC-DEFAULT' in generator.unit_references()[office]


def test_a_name_the_run_declares_is_not_recorded(converter_module, tmp_path):
    """GW-Common is declared inside the run, so a reference to it resolves and is not an outside
    name. A name recorded for the shared unit comes from a referrer in the shared section.
    """
    _parser, generator = _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    recorded = {name for names in generator.unit_references().values() for name in names}
    assert 'GW-Common' not in recorded
    assert 'GW-Shared' not in recorded
    assert recorded == {'IKE-DEFAULT', 'IPSEC-DEFAULT'}


def test_the_ambiguous_device_name_is_recorded_as_an_outside_name(gen):
    """F3.6: a name two devices declare stays plain because the referrer is ambiguous, not because
    the name is outside the run. The edge list (F6.3) is the feature that names the other unit, so
    this record keeps one fact, and the case is recorded here.
    """
    gen.generate_interfaces([
        {'name': 'ethernet1/1', 'type': 'ethernet', 'mode': 'layer3',
         'device_group': 'Shared', 'vsys': '', 'template': '', 'vsys_device': 'fw-1.example.com'},
        {'name': 'ethernet1/1', 'type': 'ethernet', 'mode': 'layer3',
         'device_group': 'Shared', 'vsys': '', 'template': '', 'vsys_device': 'fw-2.example.com'},
    ])
    router = {'name': 'vr-shared', 'type': 'virtual-router', 'vsys': '', 'template': '',
              'vsys_device': '', 'interfaces': ['ethernet1/1']}
    gen.generate_virtual_routers([router])
    text = (gen.output_dir / 'virtual_routers.tf').read_text(encoding='utf-8')
    assert 'panos_ethernet_interface.' not in text
    assert 'data.panos_ethernet_interface' not in text
    assert gen.unit_references() == {('', '', '', ''): ('ethernet1/1',)}


def test_a_read_through_name_is_recorded(converter_module, tmp_path):
    """A name that became a read-through `data` block (F5.5) is an outside name, so the row states
    it. Every block the run writes is one recorded name.
    """
    _parser, generator = _pipeline(converter_module, SAMPLE_CONFIG, tmp_path,
                                   ('--data-blocks', 'panos_address,panos_zone'))
    blocks = [line.split(' = ')[1].strip('"') for line in
              (tmp_path / 'read_through.tf').read_text(encoding='utf-8').splitlines()
              if line.startswith('  name = ')]
    recorded = {name for names in generator.unit_references().values() for name in names}
    assert blocks and set(blocks) <= recorded
    assert 'any' in recorded


def test_every_recorded_name_belongs_to_a_unit_the_ledger_shows(converter_module, tmp_path):
    """The row set is the units the ledger shows, so a recorded name cannot name a unit the run did
    not read. Pinned across the fixture corpus.
    """
    for fixture in sorted(FIXTURES_DIR.glob('*.xml')):
        if fixture.name.startswith('hostile_'):
            continue
        out = tmp_path / fixture.stem
        parser, generator = _pipeline(converter_module, fixture, out)
        units = {unit_manifest.facts_of(row) for row in parser.ledger.rows()}
        for facts in generator.unit_references():
            assert facts in units, (fixture.name, facts)


def test_a_name_is_stored_once_per_unit(converter_module, tmp_path):
    """Two sites in the same unit that name the same outside name record it once."""
    _parser, generator = _pipeline(converter_module, SAMPLE_CONFIG, tmp_path)
    for names in generator.unit_references().values():
        assert len(set(names)) == len(names)
    row = _row(_manifest(tmp_path), ('Production-DG', '', '', 'localhost.localdomain'))
    assert row['references'].count('any') == 1
    assert row['references'] == sorted(row['references'])


# --- 5. the no-change rule ----------------------------------------------------

def test_the_generated_tf_bytes_are_unchanged(tmp_path):
    """Both golden cases write the same bytes as the committed goldens."""
    for case, source in (('sample', SAMPLE_CONFIG), ('kitchen_sink', FIXTURES_DIR / 'kitchen_sink.xml')):
        out = tmp_path / case
        proc = _run(source, out)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        goldens = {p.name: p.read_bytes() for p in sorted((GOLDEN_DIR / case).glob('*.tf'))}
        generated = {p.name: p.read_bytes() for p in sorted(out.glob('*.tf'))}
        assert generated == goldens, case


def test_the_gate_reads_no_data_file(tmp_path):
    """The gate reads `.tf` files, so a data file in the output directory is not a gate input, and the
    report prints the checks in `CHECK_ORDER` order.
    """
    _run(SAMPLE_CONFIG, tmp_path)
    files = sanity_checks.read_tf_files(tmp_path)
    assert files and all(not name.endswith('.json') for name in files)
    report = sanity_checks.run_checks(tmp_path)
    assert [result.check for result in report.checks] == list(sanity_checks.CHECK_ORDER)
    assert report.file_count == len(files)
    assert report.fail_count == 0


def test_no_report_names_a_field_the_manifest_states(tmp_path):
    """The manifest is a data file, not a report body: no report names it or restates a row."""
    _run(SAMPLE_CONFIG, tmp_path)
    for name in (entry_coverage.REPORT_FILE, 'MANUAL_SETUP_REPORT.txt',
                 'INTERFACE_MIGRATION_REPORT.txt', 'SANITY_REPORT.txt', 'SOURCE.txt', 'README.md'):
        path = tmp_path / name
        if not path.is_file():
            continue    # a report is written only when it has content
        text = path.read_text(encoding='utf-8')
        assert MANIFEST not in text, name
        assert 'entry_count' not in text, name


def test_the_exit_codes_are_unchanged(tmp_path):
    """0 when the gate reports no FAIL finding, 1 for an input refusal, 2 for an argument error."""
    assert _run(SAMPLE_CONFIG, tmp_path / 'run').returncode == 0
    assert _run(tmp_path / 'missing.xml', tmp_path / 'refused').returncode == 1
    assert not (tmp_path / 'refused' / MANIFEST).is_file(), 'a refusal writes no manifest'
    assert run_script(CONVERTER, str(SAMPLE_CONFIG), '--offline').returncode == 2
    assert run_script(CONVERTER, str(SAMPLE_CONFIG), '--data-blocks', 'panos_made_up').returncode == 2


# --- 6. the CLI and the content rule ------------------------------------------

def test_a_plain_run_writes_the_manifest_without_a_flag(tmp_path):
    """The unit boundary is a fact of every run, so the manifest is not opt-in and the CLI takes no
    flag for it.
    """
    assert 'manifest' not in run_script(CONVERTER, '--help').stdout.lower()
    assert _run(SAMPLE_CONFIG, tmp_path).returncode == 0
    assert (tmp_path / MANIFEST).is_file()
    assert _manifest(tmp_path)


def test_the_manifest_is_written_only_when_it_has_content(tmp_path):
    """A run that read no entry writes no manifest, and the record is still written.
    """
    empty = tmp_path / 'empty.xml'
    empty.write_text('<?xml version="1.0"?>\n<config>\n<device-group/>\n</config>\n', encoding='utf-8')
    out = tmp_path / 'out'
    assert _run(empty, out).returncode == 0
    assert not (out / MANIFEST).is_file()
    assert (out / 'SOURCE.txt').is_file()


# --- 7. determinism -------------------------------------------------------------

def test_two_runs_write_the_same_bytes(tmp_path):
    """The rows are sorted by the identity and the names are sorted, so two runs on the same input
    write the same bytes.
    """
    first, second = tmp_path / 'run1', tmp_path / 'run2'
    assert _run(FIXTURES_DIR / GROUPING, first).returncode == 0
    assert _run(FIXTURES_DIR / GROUPING, second).returncode == 0
    assert (first / MANIFEST).read_bytes() == (second / MANIFEST).read_bytes()


def test_the_manifest_names_no_path_and_no_timestamp(tmp_path):
    """Two runs on the same bytes from different output directories write the same bytes, so no
    field states where the run wrote them or when.
    """
    first, second = tmp_path / 'a' / 'out', tmp_path / 'b' / 'out'
    assert _run(SAMPLE_CONFIG, first).returncode == 0
    assert _run(SAMPLE_CONFIG, second).returncode == 0
    assert (first / MANIFEST).read_bytes() == (second / MANIFEST).read_bytes()
    text = (first / MANIFEST).read_text(encoding='utf-8')
    assert str(tmp_path) not in text
    assert 'timestamp' not in text
