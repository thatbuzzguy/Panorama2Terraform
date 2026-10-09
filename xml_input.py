#!/usr/bin/env python3
"""
Safe XML input for both entry points (F3.8).

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
    root = parse_xml('export.xml')
"""

import argparse
import xml.etree.ElementTree as ET
import xml.parsers.expat as expat
from pathlib import Path

# Refuse an input larger than this before reading it (F3.8).
DEFAULT_MAX_INPUT_BYTES = 64 * 1024 * 1024

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


def _format_size(count: int) -> str:
    """A byte count for a message: '67108864 bytes (64 MiB)'."""
    if count >= _MIB:
        return f"{count} bytes ({count / _MIB:g} MiB)"
    return f"{count} bytes"


def _too_large(source: Path, measured: int, limit: int, exact: bool = True) -> UnsafeInputError:
    """Build the refusal for an input over the size limit."""
    found = f"the input is {_format_size(measured)}" if exact else "the input is larger than the limit"
    return UnsafeInputError(
        f"refusing to read '{source}': {found}, which exceeds the input limit of "
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
    source = Path(path)
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise UnsafeInputError(f"cannot read '{source}': {exc.strerror or exc}") from exc
    if size > max_input_bytes:
        raise _too_large(source, size, max_input_bytes)
    try:
        with source.open('rb') as handle:
            data = handle.read(max_input_bytes + 1)
    except OSError as exc:
        # A directory, a permission denial or a vanished file: a refusal
        # with the same shape as every other input fault, not a traceback.
        raise UnsafeInputError(f"cannot read '{source}': {exc.strerror or exc}") from exc
    if len(data) > max_input_bytes:
        raise _too_large(source, len(data), max_input_bytes, exact=False)
    return data


def reject_dtd(data: bytes, source) -> None:
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
            f"refusing to parse '{source}': the input declares a DTD for "
            f"'{found.doctype_name}'{external}, which a Panorama export never includes. "
            "A DTD can expand entities without bound or name a file to read."
        ) from None
    except expat.ExpatError:
        # The prolog is not well-formed XML. Say nothing here; the parse
        # reports the same fault with its position.
        return


def parse_xml(path, max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES) -> ET.Element:
    """Read and parse an input file, refusing unsafe input.

    Returns the root element. Raises UnsafeInputError for a size or DTD
    refusal, and xml.etree.ElementTree.ParseError for malformed XML.
    """
    source = Path(path)
    data = read_input(source, max_input_bytes)
    reject_dtd(data, source)
    # Parse the bytes that passed both checks, so nothing can change
    # between the check and the parse.
    return ET.fromstring(data)


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
