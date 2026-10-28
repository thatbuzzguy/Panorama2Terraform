#!/usr/bin/env python3
"""
Safe XML input for both entry points (F3.8), through one producer boundary (F5.1).

Copyright (c) 2025 GSW Systems

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

F5.3 records the size and the SHA-256 hex of the bytes the door parsed, so the
provenance record names the bytes it checked, not whatever file stands at the origin
path now. The door is the only place that can know which bytes were parsed.

F5.4 adds the `scope` field: the scope the source holds. `whole-config` is the default;
a per-scope source names its own declared path. The field is a fact the producer records,
so `container_coverage` and `entry_coverage` read it through the contract, and the
provenance record states it.

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
import xml.etree.ElementTree as ET
import xml.parsers.expat as expat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Refuse an input larger than this before reading it (F3.8).
DEFAULT_MAX_INPUT_BYTES = 64 * 1024 * 1024

# The scope vocabulary a source states (F5.4). One definition, read by `provenance.py`, by
# the per-scope rule in `container_coverage.py`, and by the request-shape check in
# `source_fetch.py`, which may import only this module.
DEFAULT_SCOPE = 'whole-config'
ENTRY_SEGMENT = 'entry'

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
    ``state``.

    ``name`` is the value a report prints. For a file it is the file name with no
    directory, so a report line does not depend on the path.

    ``path`` is the file a reader can reopen, and is None for a producer that hands
    bytes with no file behind it. A report must still name a source a reader can check,
    so a network producer caches what it fetched and the cache file becomes the path.
    """

    kind: str
    name: str
    path: Optional[Path] = None

    @classmethod
    def for_path(cls, path: Path) -> 'SourceOrigin':
        """The origin of a file read."""
        return cls(kind='file', name=path.name, path=path)


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
        with origin.path.open('rb') as handle:
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
    device-group splitter, which builds new trees from copies, gets no line.

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
    sha256: str = ''
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
        return self.scope.split('/')[0] if self.is_per_scope else ''

    def line_of(self, elem: ET.Element) -> Optional[int]:
        """Line of elem's opening tag, or None when the parse did not record it."""
        return self.lines.get(id(elem))


def _fixname(name: str) -> str:
    """Name a decoded element or attribute the way ElementTree names it.

    With namespace processing on, expat reports a qualified name as
    ``uri}local``. ElementTree turns that into ``{uri}local`` and leaves an
    unqualified name alone, so this is the mapping xml.etree applies.
    """
    return '{' + name if '}' in name else name


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


def check_bytes(data: bytes, origin: SourceOrigin,
                max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES) -> None:
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


def parse_bytes(data: bytes, origin: SourceOrigin,
                max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES) -> ParsedSource:
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


def parse_xml(path, max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES) -> ParsedSource:
    """The file producer (F5.1): read the file, then check and parse the bytes.

    The size is checked before the read, so an over-limit file is never allocated.
    The bytes that passed both checks are the bytes that are parsed, so the input is
    read once and no check can be handed different bytes.
    """
    origin = SourceOrigin.for_path(Path(path))
    data = read_input(origin.path, max_input_bytes)
    return parse_bytes(data, origin, max_input_bytes)


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
        '--max-input-bytes',
        type=positive_int,
        metavar='N',
        default=DEFAULT_MAX_INPUT_BYTES,
        help=(
            f"refuse an input larger than N bytes (default {_format_size(DEFAULT_MAX_INPUT_BYTES)}). "
            "A Panorama export is far smaller; raise the limit only for a trusted file."
        ),
    )
