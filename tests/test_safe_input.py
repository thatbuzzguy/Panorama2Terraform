"""F3.8: safe XML input.

Both entry points refuse input they cannot parse safely — a file over the
size limit, or a file that declares a DTD — before they allocate for it
and before they write any output.

Two checks, one implementation (`xml_input.py`):

- Size: the read is capped, so a huge file never reaches memory.
- DTD: a DTD is the only way an entity expansion or an external entity
  reaches `xml.etree`, so the parser is asked, not a text search. A text
  search is encoding-blind: it misses the `<!DOCTYPE` bytes of a UTF-16
  export (the bypass that made this task worth finishing).

F4.2 adds a third job to the same read: record the source line of every
element, so a report can name the line an entry came from. The tests here pin
that the extra job did not change the tree or the checks.
"""
import copy
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
CONVERTER = REPO_ROOT / 'panorama_to_terraform.py'
SPLITTER = REPO_ROOT / 'split_device_groups.py'
SAMPLE = REPO_ROOT / 'sample_panorama_config.xml'
FIXTURES_DIR = REPO_ROOT / 'tests' / 'fixtures'

# A minimal Panorama body, reused to build inputs of an exact size.
BODY = (
    '<config><shared><address><entry name="host-1">'
    '<ip-netmask>10.0.0.1/32</ip-netmask>'
    '</entry></address></shared></config>'
)


def _run(script: Path, *args: str, workdir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=workdir,
    )


def _error_text(proc: subprocess.CompletedProcess) -> str:
    """The 'Error: ...' lines of a run, joined. Fails if the run printed none."""
    combined = proc.stdout + proc.stderr
    lines = [line for line in combined.splitlines() if line.startswith('Error:')]
    assert lines, f"no Error: line in:\n{combined}"
    return '\n'.join(lines)


def _assert_clean_failure(proc: subprocess.CompletedProcess) -> None:
    assert proc.returncode != 0
    combined = proc.stdout + proc.stderr
    assert 'Traceback' not in combined


# --- Size limit -------------------------------------------------------------

def test_over_limit_input_is_refused(tmp_path):
    """A file over the limit exits non-zero with no traceback."""
    proc = _run(CONVERTER, str(SAMPLE), '--output-dir', str(tmp_path / 'out'),
                '--max-input-bytes', '1000', workdir=tmp_path)
    _assert_clean_failure(proc)


def test_refusal_names_the_file_the_limit_and_the_measured_size(tmp_path):
    """The refusal is actionable: which file, how big, what the limit was."""
    limit = 1000
    proc = _run(CONVERTER, str(SAMPLE), '--output-dir', str(tmp_path / 'out'),
                '--max-input-bytes', str(limit), workdir=tmp_path)
    message = _error_text(proc)
    assert SAMPLE.name in message
    assert f'{SAMPLE.stat().st_size} bytes' in message
    assert f'limit of {limit} bytes' in message
    assert '--max-input-bytes' in message


def test_at_limit_input_is_accepted(tmp_path):
    """The limit is inclusive: a file of exactly the limit is parsed."""
    out_dir = tmp_path / 'out'
    proc = _run(CONVERTER, str(SAMPLE), '--output-dir', str(out_dir),
                '--max-input-bytes', str(SAMPLE.stat().st_size), workdir=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out_dir / 'provider.tf').is_file()


def test_one_byte_over_the_limit_is_refused(tmp_path):
    """The boundary is exact: limit + 1 byte is refused."""
    proc = _run(CONVERTER, str(SAMPLE), '--output-dir', str(tmp_path / 'out'),
                '--max-input-bytes', str(SAMPLE.stat().st_size - 1), workdir=tmp_path)
    _assert_clean_failure(proc)
    assert 'exceeds the input limit' in _error_text(proc)


def test_splitter_applies_the_same_size_limit(tmp_path):
    """The splitter refuses an over-limit file and accepts an at-limit one."""
    over = _run(SPLITTER, str(SAMPLE), '--output-dir', str(tmp_path / 'over'),
                '--max-input-bytes', '1000', workdir=tmp_path)
    _assert_clean_failure(over)
    at_limit = _run(SPLITTER, str(SAMPLE), '--output-dir', str(tmp_path / 'ok'),
                    '--max-input-bytes', str(SAMPLE.stat().st_size), workdir=tmp_path)
    assert at_limit.returncode == 0, at_limit.stdout + at_limit.stderr
    assert list((tmp_path / 'ok').glob('*.xml'))


def test_both_scripts_print_the_same_refusal(tmp_path):
    """One implementation, one message: the two refusals are identical."""
    converter = _run(CONVERTER, str(SAMPLE), '--output-dir', str(tmp_path / 'a'),
                     '--max-input-bytes', '1000', workdir=tmp_path)
    splitter = _run(SPLITTER, str(SAMPLE), '--output-dir', str(tmp_path / 'b'),
                    '--max-input-bytes', '1000', workdir=tmp_path)
    assert _error_text(converter) == _error_text(splitter)
    assert converter.returncode == splitter.returncode


def test_refusal_writes_no_output_files(tmp_path):
    """A refused input leaves no output directory behind."""
    for script, extra in ((CONVERTER, []), (SPLITTER, [])):
        out_dir = tmp_path / f'out_{script.stem}'
        proc = _run(script, str(SAMPLE), '--output-dir', str(out_dir),
                    '--max-input-bytes', '1000', *extra, workdir=tmp_path)
        _assert_clean_failure(proc)
        assert not out_dir.exists(), f'{script.name} created {out_dir} for refused input'


def test_refusal_leaves_an_existing_output_directory_untouched(tmp_path):
    """A refusal does not clear or add to a directory the operator reuses."""
    out_dir = tmp_path / 'out'
    out_dir.mkdir()
    keep = out_dir / 'terraform.tfstate'
    keep.write_text('{"keep": true}', encoding='utf-8')
    for script in (CONVERTER, SPLITTER):
        proc = _run(script, str(SAMPLE), '--output-dir', str(out_dir),
                    '--max-input-bytes', '1000', workdir=tmp_path)
        _assert_clean_failure(proc)
        assert sorted(p.name for p in out_dir.iterdir()) == ['terraform.tfstate']
        assert keep.read_text(encoding='utf-8') == '{"keep": true}'


@pytest.mark.parametrize('script', [CONVERTER, SPLITTER])
def test_nonpositive_limit_is_an_argparse_error(script, tmp_path):
    """A limit of 0 or less is a usage error (exit 2), not a traceback."""
    for value in ('0', '-1', 'abc'):
        proc = _run(script, str(SAMPLE), '--max-input-bytes', value, workdir=tmp_path)
        assert proc.returncode == 2, f'{value!r}: {proc.stdout}\n{proc.stderr}'
        assert 'Traceback' not in proc.stderr
        assert 'max-input-bytes' in proc.stderr


def test_a_directory_is_a_clean_refusal(tmp_path):
    """An input path that is not a readable file is refused, not a traceback."""
    not_a_file = tmp_path / 'export.xml'
    not_a_file.mkdir()
    for script in (CONVERTER, SPLITTER):
        proc = _run(script, str(not_a_file), '--output-dir', str(tmp_path / 'out'), workdir=tmp_path)
        _assert_clean_failure(proc)
        assert 'cannot read' in _error_text(proc)


def test_both_scripts_document_the_shared_default(tmp_path):
    """Both CLIs carry the flag with the same default."""
    for script in (CONVERTER, SPLITTER):
        proc = _run(script, '--help', workdir=tmp_path)
        assert proc.returncode == 0
        assert '--max-input-bytes' in proc.stdout


def test_default_limit_is_one_number_for_every_caller(xml_input_module):
    """The default the CLIs show, the parser applies and the tests read match."""
    assert xml_input_module.DEFAULT_MAX_INPUT_BYTES == 64 * 1024 * 1024
    assert max(
        p.stat().st_size for p in list(FIXTURES_DIR.glob('*.xml')) + [SAMPLE]
    ) < xml_input_module.DEFAULT_MAX_INPUT_BYTES, 'the default limit must accept every committed fixture'


# --- DTD rejection ----------------------------------------------------------

def test_utf16_dtd_is_refused(tmp_path):
    """A DTD the old UTF-8 text search could not see is still refused.

    The F1.7 check searched the file read as UTF-8 for '<!DOCTYPE'. A
    UTF-16 export hides those bytes, so the DTD reached the parser and
    expanded. The check now asks the parser, which decodes first.
    """
    dtd = (
        '<!DOCTYPE config [\n'
        '  <!ENTITY a2 "x">\n'
        '  <!ENTITY a "&a2;&a2;">\n'
        ']>\n'
    )
    source = tmp_path / 'utf16_dtd.xml'
    source.write_bytes(f'<?xml version="1.0"?>\n{dtd}{BODY}'.encode('utf-16'))
    for script in (CONVERTER, SPLITTER):
        proc = _run(script, str(source), '--output-dir', str(tmp_path / 'out'), workdir=tmp_path)
        _assert_clean_failure(proc)
        message = _error_text(proc)
        assert 'DTD' in message
        assert 'expanded' not in proc.stdout


def test_clean_utf16_input_is_accepted(tmp_path):
    """Refusing a UTF-16 DTD must not refuse UTF-16 input in general."""
    source = tmp_path / 'utf16_clean.xml'
    source.write_bytes(f'<?xml version="1.0" encoding="UTF-16"?>\n{BODY}'.encode('utf-16'))
    out_dir = tmp_path / 'out'
    proc = _run(CONVERTER, str(source), '--output-dir', str(out_dir), workdir=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert '10.0.0.1/32' in (out_dir / 'address_objects.tf').read_text(encoding='utf-8')


def test_dtd_in_a_prolog_comment_is_not_a_refusal(tmp_path):
    """A comment that mentions <!DOCTYPE is legal input, not a DTD."""
    source = tmp_path / 'comment.xml'
    source.write_bytes(
        f'<?xml version="1.0"?>\n<!-- This export never carried a <!DOCTYPE config> -->\n{BODY}'
        .encode()
    )
    out_dir = tmp_path / 'out'
    proc = _run(CONVERTER, str(source), '--output-dir', str(out_dir), workdir=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out_dir / 'provider.tf').is_file()


def test_external_id_dtd_is_refused(tmp_path):
    """An external DTD (the XXE shape) is refused and named as external."""
    source = tmp_path / 'external_dtd.xml'
    source.write_bytes(
        f'<?xml version="1.0"?>\n'
        f'<!DOCTYPE config PUBLIC "-//O//PUB//EN" "http://dtd.invalid/x.dtd">\n{BODY}'
        .encode()
    )
    proc = _run(CONVERTER, str(source), '--output-dir', str(tmp_path / 'out'), workdir=tmp_path)
    _assert_clean_failure(proc)
    message = _error_text(proc)
    assert 'DTD' in message
    assert 'external id' in message


@pytest.mark.parametrize('fixture', ['hostile_billion_laughs.xml', 'hostile_xxe.xml'])
def test_hostile_fixtures_are_still_refused(fixture, tmp_path):
    """The F1.7 hostile corpus still fails cleanly on both entry points."""
    for script in (CONVERTER, SPLITTER):
        proc = _run(script, str(FIXTURES_DIR / fixture), '--output-dir',
                    str(tmp_path / f'out_{script.stem}'), workdir=tmp_path)
        _assert_clean_failure(proc)
        assert 'DTD' in _error_text(proc)


def test_entity_reference_without_a_dtd_is_a_parse_error(tmp_path):
    """Nothing expands when no DTD declares the entity: the parse just fails.

    This is the fact that makes DTD rejection enough, so it is pinned here:
    expat reports 'undefined entity' instead of substituting anything.
    """
    source = tmp_path / 'entity.xml'
    source.write_bytes(b'<?xml version="1.0"?>\n<config>&lol3;</config>')
    proc = _run(CONVERTER, str(source), '--output-dir', str(tmp_path / 'out'), workdir=tmp_path)
    _assert_clean_failure(proc)
    assert 'undefined entity' in proc.stdout + proc.stderr


# --- The shared module ------------------------------------------------------

def test_read_input_refuses_before_allocating(xml_input_module, tmp_path):
    """read_input raises UnsafeInputError for an over-limit file."""
    source = tmp_path / 'in.xml'
    source.write_text(f'<?xml version="1.0"?>\n{BODY}', encoding='utf-8')
    with pytest.raises(xml_input_module.UnsafeInputError) as excinfo:
        xml_input_module.read_input(source, 16)
    message = str(excinfo.value)
    assert source.name in message
    assert f'{source.stat().st_size} bytes' in message
    assert 'limit of 16 bytes' in message


def test_read_input_returns_the_whole_file_at_the_limit(xml_input_module, tmp_path):
    """At the limit the caller gets every byte, so the parse sees a full document."""
    source = tmp_path / 'in.xml'
    raw = f'<?xml version="1.0"?>\n{BODY}'.encode()
    source.write_bytes(raw)
    assert xml_input_module.read_input(source, len(raw)) == raw


def test_unsafe_input_error_is_a_value_error(xml_input_module):
    """Callers that already handle ValueError for this path keep working."""
    assert issubclass(xml_input_module.UnsafeInputError, ValueError)


def test_parse_reads_the_file_once(xml_input_module, tmp_path, monkeypatch):
    """The tree comes from the checked bytes: the path is opened once, not twice.

    The old code read the file as text for the DTD check and then re-read the
    path in ET.parse, so the bytes that were checked and the bytes that were
    parsed could differ.
    """
    source = tmp_path / 'in.xml'
    source.write_bytes(f'<?xml version="1.0"?>\n{BODY}'.encode())
    real_open = Path.open
    opened = []

    def counting_open(self, *args, **kwargs):
        opened.append(self)
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', counting_open)
    parsed = xml_input_module.parse_xml(source)
    assert parsed.root.tag == 'config'
    assert len(opened) == 1, f'expected one read of the input, got {len(opened)}'


def test_parser_and_splitter_use_the_shared_default(xml_input_module, converter_module, splitter_module,
                                                    tmp_path):
    """Neither entry point keeps its own limit or its own DTD check."""
    assert converter_module.parse_xml is xml_input_module.parse_xml
    assert splitter_module.parse_xml is xml_input_module.parse_xml
    assert converter_module.DEFAULT_MAX_INPUT_BYTES == xml_input_module.DEFAULT_MAX_INPUT_BYTES
    assert splitter_module.DEFAULT_MAX_INPUT_BYTES == xml_input_module.DEFAULT_MAX_INPUT_BYTES

    # A DTD reaches both entry points through the one check.
    source = tmp_path / 'dtd.xml'
    source.write_bytes(f'<?xml version="1.0"?>\n<!DOCTYPE config>\n{BODY}'.encode())
    with pytest.raises(xml_input_module.UnsafeInputError):
        converter_module.PanoramaParser(str(source))
    assert splitter_module.split_panorama_config(str(source), str(tmp_path / 'split')) is False


# --- F4.2: the same read records the source line ---------------------------

def _shape(elem):
    """Tag, attributes, text and child order, for a tree comparison."""
    return (elem.tag, dict(elem.attrib), elem.text, tuple(_shape(c) for c in elem))


def test_parse_records_the_opening_line_of_every_element(xml_input_module, tmp_path):
    """line_of names the line the parser was reading when it opened an element."""
    text = (
        '<?xml version="1.0"?>\n'
        '<config>\n'
        '  <shared>\n'
        '    <address>\n'
        '      <entry name="host-1">\n'
        '        <ip-netmask>10.0.0.1/32</ip-netmask>\n'
        '      </entry>\n'
        '    </address>\n'
        '  </shared>\n'
        '</config>\n'
    )
    source = tmp_path / 'lines.xml'
    source.write_text(text, encoding='utf-8')
    parsed = xml_input_module.parse_xml(source)

    assert parsed.name == 'lines.xml', 'a report names the file, not the path'
    assert parsed.line_of(parsed.root) == 2
    container = parsed.root.find('.//address')
    entry = parsed.root.find('.//address/entry')
    assert parsed.line_of(container) == 4
    assert parsed.line_of(entry) == 5
    assert parsed.line_of(entry.find('ip-netmask')) == 6


def test_line_of_a_multiline_element_is_the_opening_tag(xml_input_module, tmp_path):
    """An entry whose attributes wrap over two lines still reports its opening line."""
    text = (
        '<?xml version="1.0"?>\n'
        '<config>\n'
        '  <shared>\n'
        '    <address>\n'
        '      <entry\n'
        '        name="host-1">\n'
        '        <ip-netmask>10.0.0.1/32</ip-netmask>\n'
        '      </entry>\n'
        '    </address>\n'
        '  </shared>\n'
        '</config>\n'
    )
    source = tmp_path / 'wrapped.xml'
    source.write_text(text, encoding='utf-8')
    parsed = xml_input_module.parse_xml(source)
    entry = parsed.root.find('.//address/entry')
    assert entry.get('name') == 'host-1'
    assert parsed.line_of(entry) == 5, 'the opening tag starts on line 5'


def test_byte_order_mark_is_not_a_line(xml_input_module, tmp_path):
    """A UTF-16 input is read by the parser, and its first element is still on line 1 or 2."""
    text = (
        '<?xml version="1.0" encoding="UTF-16"?>\n'
        '<config><shared><address><entry name="host-1">'
        '<ip-netmask>10.0.0.1/32</ip-netmask></entry></address></shared></config>\n'
    )
    source = tmp_path / 'utf16.xml'
    source.write_bytes(text.encode('utf-16'))
    parsed = xml_input_module.parse_xml(source)
    entry = parsed.root.find('.//address/entry')
    assert entry is not None, 'the UTF-16 tree is the tree xml.etree builds'
    assert parsed.line_of(parsed.root) == 2, 'the prolog is line 1, the root is line 2'
    assert parsed.line_of(entry) == 2


def test_line_tracking_does_not_change_the_tree(xml_input_module, tmp_path):
    """For every committed input, the recorded lines did not alter the tree."""
    for path in sorted(FIXTURES_DIR.glob('*.xml')) + [SAMPLE]:
        try:
            parsed = xml_input_module.parse_xml(path)
        except xml_input_module.UnsafeInputError:
            continue  # refused before the parse, so no tree to compare
        except ET.ParseError:
            # A refused control character is still an ET.ParseError, so the
            # two paths must refuse the same input.
            with pytest.raises(ET.ParseError):
                ET.fromstring(path.read_bytes())
            continue
        assert _shape(parsed.root) == _shape(ET.fromstring(path.read_bytes())), path.name

    # A comment and a namespace are part of that claim.
    source = tmp_path / 'namespaces.xml'
    source.write_text(
        '<?xml version="1.0"?>\n'
        '<config xmlns:ns="urn:x" xmlns="urn:y">\n'
        '  <!---->\n'
        '  <entry name="a" xml:lang="en">\n'
        '    <ns:child x="1"/>\n'
        '  </entry>\n'
        '</config>\n', encoding='utf-8')
    parsed = xml_input_module.parse_xml(source)
    assert _shape(parsed.root) == _shape(ET.fromstring(source.read_bytes()))
    # Both paths drop the comment and keep the namespace form ET uses.
    assert [c.tag for c in parsed.root] == ['{urn:y}entry'], 'comment parity with ET'
    assert parsed.line_of(parsed.root) == 2


def test_a_copied_element_has_no_line(xml_input_module, tmp_path):
    """The line map covers the tree that was parsed, not a copy built from it.

    The device-group splitter builds new trees from copies, so it writes XML and
    never asks for a line.
    """
    source = tmp_path / 'copy.xml'
    source.write_text(f'<?xml version="1.0"?>\n{BODY}', encoding='utf-8')
    parsed = xml_input_module.parse_xml(source)
    original = parsed.root.find('.//entry')
    duplicate = copy.deepcopy(original)
    assert parsed.line_of(original), 'the parsed tree has a line'
    assert parsed.line_of(duplicate) is None
