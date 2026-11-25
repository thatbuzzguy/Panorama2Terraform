#!/usr/bin/env python3
"""
Safe XML input for both entry points (F3.8), through one producer boundary (F5.1).

Copyright (c) 2026 Ryan Brown

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

The notice above names the author of the content in this file: no line here comes
from the upstream, so no commercial term applies (see docs/LICENSING.md).

A Panorama export is a plain XML file with no DTD. Anything else is a
corrupt export or an attack, so this module refuses it before the
converter spends memory on it and before it writes any file.

Two risks, two checks:

1. Size. ``xml.etree`` builds the whole document in memory, several times
   the file size, so an unbounded read is a memory denial of service. The
   read is capped at ``max_input_bytes`` (default 64 MiB, which is larger
   than a Panorama export this project has seen by three orders of
   magnitude).
2. Entity expansion and external entities (XXE). Both need a DTD. The
   check asks the parser, not a text search, so it holds for every
   encoding the parser accepts: a UTF-16 export hides the ``<!DOCTYPE``
   bytes from a UTF-8 text search, but not from the parser.

F4.2 adds one job: record the source line of every element. ``ElementTree``
does not keep a line number, so ``parse_xml`` builds the tree through expat
handlers that read ``CurrentLineNumber`` at the moment an opening tag is
decoded. The tree is the same tree ``ET.fromstring`` returns for the pinned
shapes (tag, ``name`` attribute, child order, comment, namespace).

F5.1 adds the producer boundary. ``parse_bytes`` is the door: it runs both checks on
the bytes it is handed, so no producer can bypass them. ``parse_xml`` is the file
producer and keeps the size check before the read. A producer that hands bytes with no
file behind it gets the same refusal as a file. The tree shape does not change, so the
container table, the entry ledger, the parent walk and the line map are unchanged.

F5.1 also holds the archive producer, `parse_archive`. The shape is read from the bytes
and not from a name, and one accepted member is expanded: a single-member gzip, and a gzip
stream that holds a tar archive with exactly one member. The two checks run on the bytes the
producer hands the door, which for an accepted shape are the expanded bytes. The read cap is
applied while the bytes expand, so a bundle that expands past the cap is refused before a tree
is built. The producer adds no check and no refusal wording: a shape it does not accept is
handed to the door unchanged, and the parse answers it with the line the shape table holds.

Piece 13B.3 adds what the producer states for an accepted read: `ARCHIVE_KIND` as the source
kind, and the member name it read from the shape, as `SourceOrigin.member`. The producer states
no naming rule and no `-` rule; the record reads both through the origin, and the record module
states the value for a member the shape does not name.

F5.3 records the size and the SHA-256 hex of the bytes the door parsed, so the
provenance record names the bytes it checked, not whatever file stands at the origin
path now. The door is the only place that can know which bytes were parsed.

F5.4 adds the `scope` field: the scope the source holds. `whole-config` is the default;
a per-scope source names its own declared path. The field is a fact the producer records,
so `container_coverage` and `entry_coverage` read it through the contract, and the
provenance record states it.

The text rule, stated once here for the text every reader of a source uses:

1. Control character. A source text holds no control character except the three it can state as
   content — tab, CR, LF — because those three are the shapes a print escapes. The XML door refuses
   the rest through the parser (``&#7;`` is "reference to invalid character number", a raw ``0x07``
   byte is "not well-formed (invalid token)"), so no value reaches the printer with one. A JSON state
   document states no such rule, because ``json.loads`` accepts ``\\u0007`` inside a string, so the
   state door applies this rule to the values it reads. ``sanity_checks.check_control_chars`` reads the
   same set for the printed files, so the gate is the check on the print, not a second rule, and
   ``escape_string`` states only the escape shapes.
2. Whitespace. The whitespace around text read from the tree is the export's formatting, not part of the
   value, so a value is read without it (``read_text``). A name read from the ``name`` attribute is read
   through §5, and ``naming.sanitize`` strips it the same way, so the value rule and the naming rule agree.
   A JSON state string is read as it states itself, because whitespace inside a quoted JSON string is part
   of the value, not the export's formatting.

Facts this module depends on, verified against expat 2.6.1 (the parser
behind ``xml.etree``):

- expat expands an entity only when a DTD declares it. ``&a;`` with no
  DTD is a hard ``ParseError`` ("undefined entity"), so nothing expands.
- expat never fetches an external entity, because ``xml.etree`` installs
  no ``ExternalEntityRefHandler``. A DTD is the only door.
- A DTD can only appear in the prolog, so the scan stops at the root
  element start tag and costs a fraction of the parse.

Usage:
    from xml_input import parse_xml
    source = parse_xml('export.xml')
    root = source.root
    line = source.line_of(root.find('.//entry'))

    # A producer that hands bytes uses the same door:
    from xml_input import parse_bytes, SourceOrigin
    origin = SourceOrigin(kind='api', name='panorama:export')
    source = parse_bytes(data, origin)
    line = source.line_of(root.find('.//entry'))
"""

import argparse
import hashlib
import io
import tarfile
import xml.etree.ElementTree as ET
import xml.parsers.expat as expat
import zlib
from dataclasses import dataclass, field, replace
from pathlib import Path

# Refuse an input larger than this before reading it (F3.8).
DEFAULT_MAX_INPUT_BYTES = 64 * 1024 * 1024

# The scope vocabulary a source states (F5.4). One definition, read by `provenance.py`, by
# the per-scope rule in `container_coverage.py`, and by the request-shape check in
# `source_fetch.py`, which may import only this module.
DEFAULT_SCOPE = "whole-config"
ENTRY_SEGMENT = "entry"

# The control characters, as the text rule above states them. One definition, read by the state door
# (`state_input.py`) and by the gate rule `control_chars` (`sanity_checks.py`). The three escape shapes
# are the characters a source may state as content, so the door does not refuse them.
CONTROL_CHARS = {chr(code) for code in range(0x20)} | {chr(0x7F)}
ESCAPE_SHAPES = frozenset("\t\r\n")

# The shape the archive producer reads from the bytes, not from a name (`docs/INPUT_SHAPES.md` §2 rule 3): the gzip
# magic, and the tar magic that a tar header states at byte 257. A stream that holds one of these is read by the
# producer; every other shape is answered by the door.
GZIP_MAGIC = b"\x1f\x8b"
TAR_MAGIC = b"ustar"
TAR_MAGIC_AT = 257

# The gzip header, as the gzip reader reads it: the fixed part is ten bytes, and the flags byte names the optional
# fields that follow it, which appear in the order the format states them, so the name is read after any extra field.
# The flag values are the ones `zlib` reads, not the ones RFC 1952 states: the reader names 4 for the extra field
# and 8 for the name, where RFC 1952 names 2 and 4. The producer reads the shape with the reader, so it states the
# values the reader uses.
GZIP_HEADER_LEN = 10
GZIP_FLAGS_AT = 3
GZIP_EXTRA_FIELD_FLAG = 4
GZIP_NAME_FIELD_FLAG = 8

# The kind an accepted archive read names in the provenance record (`docs/INPUT_SHAPES.md` §2 rule 5), as the api
# producer states `SOURCE_KIND` in `source_fetch.py` and the state producer states `STATE_KIND` in `state_input.py`.
# A read that is not an accepted shape keeps the kind its producer states, because no member was read for it.
ARCHIVE_KIND = "archive"


def control_chars(text: str) -> list[str]:
    """The control characters in text that the read layer refuses, in the order they appear."""
    return [ch for ch in text if ch in CONTROL_CHARS and ch not in ESCAPE_SHAPES]


def read_text(text: str | None) -> str | None:
    """Text read from the tree, as the text rule above states it: without the whitespace around it.

    An element that is not there answers None, so the rule never turns an absent field into an empty one.
    """
    return None if text is None else text.strip()


# One MiB, for the human-readable part of a size message.
_MIB = 1024 * 1024


class UnsafeInputError(ValueError):
    """Input this converter refuses to parse.

    A ValueError subclass, so a caller that already handles ValueError for
    this input path keeps working.
    """


class _PrologScanDone(Exception):
    """Raised by the scan handler at the root element: no DTD was found."""


class _DtdFound(Exception):
    """Raised by the scan handler when the parser reports a DOCTYPE."""

    def __init__(self, doctype_name: str, has_external_id: bool):
        super().__init__(doctype_name)
        self.doctype_name = doctype_name
        self.has_external_id = has_external_id


@dataclass(frozen=True)
class SourceOrigin:
    """Where the bytes a producer handed came from, as a report states it.

    ``kind`` is ``file`` for the file producer. F5.2 adds ``api`` and F5.6 adds
    ``state``. Piece 13B.3 adds ``archive``, the kind the archive producer states for a read
    of an accepted shape, through `ARCHIVE_KIND`.

    ``name`` is the value a report prints. For a file it is the file name with no
    directory, so a report line does not depend on the path.

    ``path`` is the file a reader can reopen, and is None for a producer that hands
    bytes with no file behind it. A report must still name a source a reader can check,
    so a network producer caches what it fetched and the cache file becomes the path.

    ``member`` is the member an archive read took, read from the shape by the producer that
    expanded it. It is None when the origin names no member, which is every read that is not
    an accepted archive read, so the origin states no value for an absent member and the record
    module states the one value a record writes for a field that does not apply.
    """

    kind: str
    name: str
    path: Path | None = None
    member: str | None = None

    @classmethod
    def for_path(cls, path: Path) -> "SourceOrigin":
        """The origin of a file read."""
        return cls(kind="file", name=path.name, path=path)


def _format_size(count: int) -> str:
    """A byte count for a message: '67108864 bytes (64 MiB)'."""
    if count >= _MIB:
        return f"{count} bytes ({count / _MIB:g} MiB)"
    return f"{count} bytes"


def origin_phrase(origin: SourceOrigin) -> str:
    """The source as a refusal names it: the path when there is one, else the origin."""
    return f"'{origin.path}'" if origin.path is not None else f"'{origin.name}'"


def _too_large(origin: SourceOrigin, measured: int, limit: int, exact: bool = True) -> UnsafeInputError:
    """Build the refusal for an input over the size limit."""
    found = f"the input is {_format_size(measured)}" if exact else "the input is larger than the limit"
    return UnsafeInputError(
        f"refusing to read {origin_phrase(origin)}: {found}, which exceeds the input limit of "
        f"{_format_size(limit)}. Pass --max-input-bytes N to raise the limit for a trusted file."
    )


def read_input(path, max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES) -> bytes:
    """Read the input file, refusing anything larger than max_input_bytes.

    The size is checked before the read, so an over-limit file is never
    allocated. The read itself is capped at max_input_bytes + 1, because
    st_size does not describe the content of a pipe, a device or a file
    that grows while the converter runs.
    """
    if max_input_bytes <= 0:
        raise UnsafeInputError(f"the input limit must be greater than 0 bytes, got {max_input_bytes}")
    origin = SourceOrigin.for_path(Path(path))
    try:
        size = origin.path.stat().st_size
    except OSError as exc:
        raise UnsafeInputError(f"cannot read {origin_phrase(origin)}: {exc.strerror or exc}") from exc
    if size > max_input_bytes:
        raise _too_large(origin, size, max_input_bytes)
    try:
        with origin.path.open("rb") as handle:
            data = handle.read(max_input_bytes + 1)
    except OSError as exc:
        # A directory, a permission denial or a vanished file: a refusal
        # with the same shape as every other input fault, not a traceback.
        raise UnsafeInputError(f"cannot read {origin_phrase(origin)}: {exc.strerror or exc}") from exc
    if len(data) > max_input_bytes:
        raise _too_large(origin, len(data), max_input_bytes, exact=False)
    return data


def reject_dtd(data: bytes, origin: SourceOrigin) -> None:
    """Refuse input that declares a DTD.

    expat reports the DOCTYPE declaration while it reads the prolog, so
    the scan sees the DTD in any encoding the parser accepts and ignores
    a '<!DOCTYPE' that only appears in a comment or a processing
    instruction. The scan stops at the root element start tag: a DTD
    cannot legally appear after it.
    """

    def on_doctype(doctype_name, *rest):
        # expat calls this positionally with (name, systemId, publicId,
        # standalone) — verified against pyexpat, and not the order the
        # Python documentation states. The two ids are therefore only used
        # as "an external id is present", never labelled.
        raise _DtdFound(doctype_name, any(rest[:2]))

    def on_start_element(*_args):
        raise _PrologScanDone

    parser = expat.ParserCreate()
    parser.StartDoctypeDeclHandler = on_doctype
    parser.StartElementHandler = on_start_element
    try:
        # isfinal=False: a truncated prolog is not an error here. The parse
        # that follows reports it with a line and column.
        parser.Parse(data, False)
    except _PrologScanDone:
        return
    except _DtdFound as found:
        external = " with an external id" if found.has_external_id else ""
        raise UnsafeInputError(
            f"refusing to parse {origin_phrase(origin)}: the input declares a DTD for "
            f"'{found.doctype_name}'{external}, which a Panorama export never includes. "
            "A DTD can expand entities without bound or name a file to read."
        ) from None
    except expat.ExpatError:
        # The prolog is not well-formed XML. Say nothing here; the parse
        # reports the same fault with its position.
        return


@dataclass(frozen=True)
class ParsedSource:
    """A parsed input: the source it came from, the tree, and the source line of each element.

    ``line_of`` answers the F4.2 question a report needs: which line of the
    input defined this entry. Only the opening tag has a position, because
    that is the tag the parser was reading.

    ``lines`` is keyed by ``id(element)``. The root holds the whole tree, so
    every element stays alive while the source is held and an id cannot be
    reused. An element copied out of this tree is not in the map, so the
    device-group splitter gets a line for the source entries its tables key by,
    and gets none for a copy: the entry a split file holds is a copy, not the
    entry the input stated.

    ``size`` and ``sha256`` are the facts the F5.3 provenance record states: measured on
    the bytes the door parsed, so the record names the bytes it checked, not a file that
    may have changed since the run.

    ``scope`` is the fact the F5.4 rule reads: ``whole-config`` for a source that declares
    no scope, and the declared path (no leading slash) for a per-scope source. The producer
    records it, so the scan and the record read it through the contract.
    """

    origin: SourceOrigin
    root: ET.Element
    lines: dict = field(default_factory=dict, compare=False, repr=False)
    size: int = 0
    sha256: str = ""
    scope: str = DEFAULT_SCOPE

    @property
    def name(self) -> str:
        """Source name, no directory. A report line must not depend on the path."""
        return self.origin.name

    @property
    def is_per_scope(self) -> bool:
        """True when the source holds a declared scope, not the whole config."""
        return self.scope != DEFAULT_SCOPE

    @property
    def scope_container(self) -> str:
        """The first segment of the declared path, or '' for the whole config."""
        return self.scope.split("/")[0] if self.is_per_scope else ""

    def line_of(self, elem: ET.Element) -> int | None:
        """Line of elem's opening tag, or None when the parse did not record it."""
        return self.lines.get(id(elem))


def _fixname(name: str) -> str:
    """Name a decoded element or attribute the way ElementTree names it.

    With namespace processing on, expat reports a qualified name as
    ``uri}local``. ElementTree turns that into ``{uri}local`` and leaves an
    unqualified name alone, so this is the mapping xml.etree applies.
    """
    return "{" + name if "}" in name else name


def _parse_with_lines(data: bytes, origin: SourceOrigin) -> ParsedSource:
    """Parse the checked bytes once and record each element's opening line.

    expat reports the line it is reading in ``CurrentLineNumber``. The handlers
    run when an opening tag, comment or processing instruction is decoded, so
    the recorded number is the line of that opening tag.

    Namespace processing is enabled the way ``xml.etree`` enables it, so the
    tree is the tree ``ET.fromstring`` builds from the same bytes.

    The size and the SHA-256 hex are measured on these bytes, so the F5.3 record names
    the bytes the door checked. A caller that hashes a file instead can name bytes the
    parse never saw.
    """
    parser = expat.ParserCreate(None, "}")
    builder = ET.TreeBuilder()
    lines = {}

    def record(elem):
        # A line number of 0 means the parser is reading the prolog or a byte
        # order mark, which is not a position a report can use.
        line = parser.CurrentLineNumber
        if line:
            lines[id(elem)] = line

    def start(qname, atts):
        record(builder.start(_fixname(qname), {_fixname(k): v for k, v in atts.items()}))

    def end(qname):
        builder.end(_fixname(qname))

    def comment(text):
        record(builder.comment(text))

    def processing_instruction(target, text):
        record(builder.pi(target, text))

    def character_data(text):
        # Character data is not an element, so it records no line. It is what
        # gives an element its text, so the handler is required for the tree to
        # match the one xml.etree builds.
        builder.data(text)

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = character_data
    parser.CommentHandler = comment
    parser.ProcessingInstructionHandler = processing_instruction
    # No external entity is fetched. The DTD check already refused the input,
    # so this handler only keeps the door closed if a DTD reached the parse.
    parser.ExternalEntityRefHandler = lambda *_args: 0

    try:
        parser.Parse(data)
    except expat.ExpatError as exc:
        # Keep the F3.8 error type: both entry points catch ET.ParseError.
        raise ET.ParseError(str(exc)) from exc

    return ParsedSource(
        origin=origin,
        root=builder.close(),
        lines=lines,
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )


def check_bytes(data: bytes, origin: SourceOrigin, max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES) -> None:
    """The two F3.8 checks, run on the bytes a producer handed (F5.1, F5.6).

    Both checks are byte checks, so they run for every source kind. The size check is
    kind-independent. The DTD check asks the parser, and only XML has a prolog, so a JSON
    source reaches no DOCTYPE and is refused by it only for its size.

    This is the fact F5.6 depends on: the checks are one definition, and only the parse step
    is chosen by the source kind.
    """
    if max_input_bytes <= 0:
        raise UnsafeInputError(f"the input limit must be greater than 0 bytes, got {max_input_bytes}")
    if len(data) > max_input_bytes:
        raise _too_large(origin, len(data), max_input_bytes, exact=False)
    reject_dtd(data, origin)


def parse_bytes(data: bytes, origin: SourceOrigin, max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES) -> ParsedSource:
    """The producer boundary (F5.1): check the bytes a producer handed, then parse them.

    Both F3.8 checks run through `check_bytes`, so no producer can bypass them. The tree is
    parsed from the bytes that passed both checks.

    A producer that hands bytes with no file behind it is refused the same way a file
    is, and the refusal names the origin. This is the fact F5.2 depends on: adding a
    source means adding a producer, not adding a check.

    The bytes that passed both checks are the bytes recorded in the F5.3 provenance
    record, so the record names the bytes the door checked.

    Raises UnsafeInputError for a size or DTD refusal, and
    xml.etree.ElementTree.ParseError for malformed XML.
    """
    check_bytes(data, origin, max_input_bytes)
    return _parse_with_lines(data, origin)


def _gzip_member_name(data: bytes) -> str | None:
    """The member name a gzip header states, or None when the header states none.

    The flags byte names the optional fields, and the name is present only when the flags state it. The extra
    field comes before it, so the name is read after that field is skipped. Each field ends at a NUL. A header
    that ends before a field its flags state is not a readable stream, so this answers the same None the producer
    answers for a shape it does not accept.
    """
    if len(data) <= GZIP_FLAGS_AT:
        return None
    flags = data[GZIP_FLAGS_AT]
    if not flags & GZIP_NAME_FIELD_FLAG:
        return None
    position = GZIP_HEADER_LEN
    if flags & GZIP_EXTRA_FIELD_FLAG:
        length = int.from_bytes(data[position : position + 2], "little")
        position += 2 + length
    end = data.find(b"\x00", position)
    if end < 0:
        return None
    # The name is bytes, so it is read as text the way the record prints it. A name that is not valid UTF-8 still
    # reads, because the record names the bytes the stream stated rather than a name it built.
    return data[position:end].decode("utf-8", "surrogateescape")


def _single_tar_member(data: bytes) -> tuple[str | None, bytes] | None:
    """The member a tar archive holds, as its name and its content, or None when the archive holds no single member.

    `data` is already expanded, so this reads the archive structure and not a compressed stream: the producer
    expands once. A stream the tar reader cannot read, or one that holds more than one member, is not an accepted
    shape, so this answers None and the door answers the bytes with the line the shape table already holds.
    """
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
            members = [member for member in archive if member.isfile()]
            if len(members) != 1:
                return None
            handle = archive.extractfile(members[0])
            content = None if handle is None else handle.read()
            if content is None:
                return None
            # A member that names nothing answers None for its name, so the record writes the value its own rule
            # states for a field that does not apply.
            return (members[0].name or None, content)
    except tarfile.TarError:
        return None


def _expand_one_member(data: bytes, max_input_bytes: int) -> tuple[str | None, bytes] | None:
    """The member an accepted gzip shape holds, as its name and its content, or None when the bytes are not one.

    The read stops at `max_input_bytes + 1`, which is the cap `read_input` already states, applied while the bytes
    expand. This states no size rule of its own: `check_bytes` stays the one definition of the size check, and the
    door runs it on the bytes this function hands back, so a bundle that expands past the cap is refused before a
    tree is built, and without the whole expansion being read.

    A stream with more than one member is not an accepted shape. The refusal the member rule prints for it has no
    owner yet (`docs/INPUT_SHAPES.md` §2 rule 4, Piece 13B.4), so this function states no refusal: it answers None,
    the producer hands the bytes to the door unchanged, and the parse answers them.

    The name is the member fact the record states: the gzip header's name field, or the name the single tar member
    states. A stream that states no name answers None for it, so the answer is not a second name rule.
    """
    if not data.startswith(GZIP_MAGIC):
        return None
    name = _gzip_member_name(data)
    reader = zlib.decompressobj(16 | zlib.MAX_WBITS)
    try:
        expanded = reader.decompress(data, max_input_bytes + 1)
    except zlib.error:
        # A stream with the magic and no readable member is not an accepted shape, so the door gets the bytes
        # unchanged and the parse answers them with the line the shape table holds for them.
        return None
    if len(expanded) > max_input_bytes:
        # The cap stopped the expansion. These are the bytes the door checks, so the size refusal is the answer.
        return (name, expanded)
    if not reader.eof or reader.unused_data:
        return None
    if expanded[TAR_MAGIC_AT : TAR_MAGIC_AT + len(TAR_MAGIC)] == TAR_MAGIC:
        return _single_tar_member(expanded)
    return (name, expanded)


def parse_archive(data: bytes, origin: SourceOrigin, max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES) -> ParsedSource:
    """The archive producer (F5.1): read the shape from the bytes, expand one member, hand the bytes to the door.

    Adding a source means adding a producer, not a check, so this function runs no check and states no refusal: the
    two checks stay `check_bytes`, run by the door on the bytes the producer hands it, which for an accepted shape
    are the expanded bytes. Bytes that are not an accepted shape are handed to the door unchanged, so the answer a
    producer gets for them is the answer the door already gives.

    For an accepted shape the origin gains the kind the archive read names and the member it took, and keeps the
    name and the path the producer was handed, so a record built from this source names bytes a reader can reopen.
    The producer states no value for a member it did not read, because the record module states that value.

    Raises UnsafeInputError for a size or DTD refusal, and
    xml.etree.ElementTree.ParseError for malformed XML.
    """
    member = _expand_one_member(data, max_input_bytes)
    if member is None:
        return parse_bytes(data, origin, max_input_bytes)
    name, content = member
    return parse_bytes(content, replace(origin, kind=ARCHIVE_KIND, member=name), max_input_bytes)


def parse_xml(path, max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES) -> ParsedSource:
    """The file producer (F5.1): read the file, hand the bytes to the producer, and parse what the door checks.

    The size is checked before the read, so an over-limit file is never allocated. The shape is read from the bytes
    the read returned, and the bytes that passed both checks are the bytes that are parsed, so the input is read
    once and no check can be handed different bytes.
    """
    origin = SourceOrigin.for_path(Path(path))
    data = read_input(origin.path, max_input_bytes)
    return parse_archive(data, origin, max_input_bytes)


def positive_int(text: str) -> int:
    """argparse type: a positive integer number of bytes."""
    try:
        value = int(text)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(f"expected an integer number of bytes, got {text!r}") from None
    if value <= 0:
        raise argparse.ArgumentTypeError(f"the limit must be greater than 0 bytes, got {value}")
    return value


def add_max_input_argument(parser: argparse.ArgumentParser) -> None:
    """Add the shared --max-input-bytes flag so both CLIs behave the same."""
    parser.add_argument(
        "--max-input-bytes",
        type=positive_int,
        metavar="N",
        default=DEFAULT_MAX_INPUT_BYTES,
        help=(
            f"refuse an input larger than N bytes (default {_format_size(DEFAULT_MAX_INPUT_BYTES)}). "
            "A Panorama export is far smaller; raise the limit only for a trusted file."
        ),
    )
