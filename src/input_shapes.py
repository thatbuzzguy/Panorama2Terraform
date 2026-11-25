#!/usr/bin/env python3
"""Epic 13, the shapes an input can be: one table of byte shape, accepted entry point, and printed line.

Seven rules, stated once here. The table is data, so a document links to it and restates no row
(`docs/INPUT_SHAPES.md` §3), and `tests/test_input_shapes.py` measures every held row against the door.

1. **One row shape** (`SHAPE_ROW_FIELDS`): the byte shape, the content that shows it, the entry point that accepts
   it, the line the run prints for it, the status, the decision or the piece a pending row waits for, the owner
   function the pins read the row through, and the member the row is read through when the operator declares one. A
   row is one shape, so a shape two entry points answer differently is two rows. A row that states no declaration
   states `""`, so the pins read the declaration as row data and hold none of their own, and only a row read through
   the archive producer states one.
2. **The module states no check and no reader.** The two byte checks stay `xml_input.check_bytes`, and the parse
   step is chosen by the source kind in `xml_input.py` and `state_input.py`, so this module adds no third kind, no
   size rule, no DTD rule, no parser, no writer, no console line, no naming rule, no environment name, and no
   control-character set. It names no file, no path, and no fixture: the shape is read from the bytes, which is the
   shape the DTD rule already has, because that check asks the parser and not a text search.
3. **The lines are the owners' wording, mirrored as data.** The door's wording is `xml_input.py`'s, the member
   rule's is `xml_input.read_member`'s, the state door's is `state_input.py`'s, and the shape a run prints for a
   refusal is `panorama_to_terraform.refused`. The pins build each line through its owner and compare it with the
   row, so a mirror cannot drift from the module that states the rule. A row states no count the pins cannot read
   from its own content, so the member rule's line names no member count. A part of a line the pins measure is
   written as a placeholder the pins fill with what they read:
   `{origin}`, `{size}`, `{limit}`. A part the row's own content states, such as the DTD name, is written as data, so
   the pin compares the whole line. A console line row holds the parts in the order the shape states them, without the
   prefix, because the prefix belongs to `container_coverage`, which is the module that states the shape, and the pin
   reads the prefix through that owner.
4. **A pending row states no line.** A line exists only when a run prints one, so a row whose rule has no owner yet
   states no line and names the decision or the piece that will state it. A pending row is not a placeholder for a
   fact: the pins hold that it states no line, names a decision, and is read by no entry point today.
5. **The status vocabulary is two words**, `held` for a row the pins measure and `pending` for a row that waits for
   a decision. No row holds a third status, and no row holds both a line and a pending status.
6. **The entry-point column names the entry point that accepts the shape**, as the module name the layout rule
   states (`docs/ARCHITECTURE.md` §1.1), `every entry point` for a shape no entry point treats differently, or `none`
   for a shape no entry point accepts. A row that names `none` is a refusal row: the entry point prints the refusal,
   and the line is that refusal. A row that names an entry point is a shape that entry point accepts, so its line is
   the fact that entry point prints for the content, which is the fact its own rule read. The `measured_through`
   column names the owner function the pins read the row through, so a pin calls the owner instead of restating what
   the owner does.
7. **The content is the smallest document that shows the shape**, so a pin can read a shape without a committed
   fixture. The committed fixture pair is Piece 13A.3 and adds no row here. Each content is well under the input
   limit, so the size half of a refusal reads as a plain byte count. An archive row shows its shape as the compressed
   stream, because the shape is the stream and not the text inside it, so its content is one literal stream and no
   call builds it. The decompression row's content is the smallest stream that shows the shape: it is under the limit
   the pins measure it against, and it expands past that limit, so the refusal can only come from the expansion. The
   record row shows the two facts its owner reads: a stream that states a member name, and content that expands to
   the bytes another row shows, so the pins read the record's byte facts as another row's content and hold no number
   of their own.
"""

# One row shape, read by the pins and named by the `docs/ARCHITECTURE.md` §1 rule column.
SHAPE_ROW_FIELDS = (
    "shape",
    "content",
    "entry_point",
    "printed_line",
    "status",
    "pending_on",
    "measured_through",
    "member",
)

# The status vocabulary, stated once here, so a pin can tell a row it measures from a row that waits.
STATUS_HELD = "held"
STATUS_PENDING = "pending"

# The table is data, so every row is one literal. A content that runs past the gate's line length is written as
# literals the parser joins, which `ast.literal_eval` still reads as one value.
SHAPE_TABLE = (
    {
        "shape": "XML bytes, no DTD, within the input limit",
        "content": b'<?xml version="1.0"?>\n<config><entry name="host-1"/></config>',
        "entry_point": "every entry point",
        "printed_line": "",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_bytes",
        "member": "",
    },
    {
        "shape": "a `<!DOCTYPE` that only appears in a prolog comment",
        "content": b'<?xml version="1.0"?>\n<!-- a <!DOCTYPE config> -->\n<config/>',
        "entry_point": "every entry point",
        "printed_line": "",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_bytes",
        "member": "",
    },
    {
        "shape": "a JSON state document that reads as one object with a `resources` array",
        "content": b'{"version":4,"resources":[{"type":"panos_address","name":"host-1","values":{"name":"x"}}]}',
        "entry_point": "state_input.py",
        "printed_line": "",
        "status": "held",
        "pending_on": "",
        "measured_through": "state_input.parse_state",
        "member": "",
    },
    {
        "shape": "a `<!DOCTYPE` inside a JSON value, where no prolog exists for the check to read",
        "content": b'{"resources":[{"type":"panos_address","name":"x","values":{"name":"<!DOCTYPE config>"}}]}',
        "entry_point": "state_input.py",
        "printed_line": "",
        "status": "held",
        "pending_on": "",
        "measured_through": "state_input.parse_state",
        "member": "",
    },
    {
        "shape": "the firewall export shape, `devices/entry` with no `device-group` row",
        "content": b'<?xml version="1.0"?>\n<config><devices><entry name="0123456789"/></devices></config>',
        "entry_point": "panorama_to_terraform.py",
        "printed_line": "",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_bytes",
        "member": "",
    },
    {
        "shape": "more bytes than the input limit, handed by a producer",
        "content": b'<?xml version="1.0"?>\n<config><entry name="host-1"/></config>',
        "entry_point": "none",
        "printed_line": "Error: refusing to read {origin}: the input is larger than the limit, which exceeds the "
        "input limit of {limit} bytes. Pass --max-input-bytes N to raise the limit for a trusted file.",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.check_bytes",
        "member": "",
    },
    {
        "shape": "more bytes than the input limit, read through the file producer",
        "content": b'<?xml version="1.0"?>\n<config><entry name="host-1"/></config>',
        "entry_point": "none",
        "printed_line": "Error: refusing to read {origin}: the input is {size} bytes, which exceeds the input limit "
        "of {limit} bytes. Pass --max-input-bytes N to raise the limit for a trusted file.",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.read_input",
        "member": "",
    },
    {
        "shape": "XML bytes that declare a DTD in the prolog",
        "content": b'<?xml version="1.0"?>\n<!DOCTYPE config>\n<config><entry name="host-1"/></config>',
        "entry_point": "none",
        "printed_line": "Error: refusing to parse {origin}: the input declares a DTD for 'config', which a Panorama "
        "export never includes. A DTD can expand entities without bound or name a file to read.",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.check_bytes",
        "member": "",
    },
    {
        "shape": "a DTD that states an external id, the XXE shape",
        "content": b'<?xml version="1.0"?>\n<!DOCTYPE config PUBLIC "P" "http://dtd.invalid/y.dtd">\n<config/>',
        "entry_point": "none",
        "printed_line": "Error: refusing to parse {origin}: the input declares a DTD for 'config' with an external "
        "id, which a Panorama export never includes. A DTD can expand entities without bound or name a file to read.",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.check_bytes",
        "member": "",
    },
    {
        "shape": "a DTD in an encoding a text search cannot read, the UTF-16 shape",
        "content": b"\xff\xfe<\x00!\x00D\x00O\x00C\x00T\x00Y\x00P\x00E\x00 \x00c\x00o\x00n\x00f\x00i\x00g\x00>\x00",
        "entry_point": "none",
        "printed_line": "Error: refusing to parse {origin}: the input declares a DTD for 'config', which a Panorama "
        "export never includes. A DTD can expand entities without bound or name a file to read.",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.check_bytes",
        "member": "",
    },
    {
        "shape": "bytes the parser cannot read as one XML document, the magic bytes of a compressed member",
        "content": b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00not xml",
        "entry_point": "none",
        "printed_line": "Error: Failed to parse XML file: not well-formed (invalid token): line 1, column 0",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_bytes",
        "member": "",
    },
    {
        "shape": "an entity reference with no DTD that declares it",
        "content": b'<?xml version="1.0"?>\n<config>&lol3;</config>',
        "entry_point": "none",
        "printed_line": "Error: Failed to parse XML file: undefined entity: line 2, column 8",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_bytes",
        "member": "",
    },
    {
        "shape": "a control character the read layer refuses, as a raw byte inside XML content",
        "content": b'<?xml version="1.0"?>\n<config><entry name="host\x071"/></config>',
        "entry_point": "none",
        "printed_line": "Error: Failed to parse XML file: not well-formed (invalid token): line 2, column 25",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_bytes",
        "member": "",
    },
    {
        "shape": "a control character the read layer refuses, inside a JSON value",
        "content": b'{"version":4,"resources":[{"type":"panos_address","name":"x","values":{"name":"a\\u0007b"}}]}',
        "entry_point": "none",
        "printed_line": "Error: refusing to read {origin}: the value of name holds a control character the read "
        "layer refuses",
        "status": "held",
        "pending_on": "",
        "measured_through": "state_input.parse_state",
        "member": "",
    },
    {
        "shape": "a resource that names no type or no name, so the identity key cannot read it",
        "content": b'{"version":4,"resources":[{"type":"panos_address","values":{"name":"x"}}]}',
        "entry_point": "none",
        "printed_line": "Error: refusing to read {origin}: a resource names no type or no name, so the identity key "
        "cannot read it",
        "status": "held",
        "pending_on": "",
        "measured_through": "state_input.parse_state",
        "member": "",
    },
    {
        "shape": "the splitter reading the firewall export shape, the fact it prints for it",
        "content": b'<?xml version="1.0"?>\n<config><devices><entry name="0123456789"/></devices></config>',
        "entry_point": "split_device_groups.py",
        "printed_line": "line 2  devices  0 device-group/entry rows read, so the tree holds the shape named instead",
        "status": "held",
        "pending_on": "",
        "measured_through": "split_device_groups.console_lines",
        "member": "",
    },
    {
        "shape": "a gzip stream that holds exactly one member, read through the archive producer",
        # One member, written as a stored block so the XML inside it can be read from the literal. The header states
        # no name, so the stream is the smallest one that shows the shape.
        "content": (
            b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00\x01=\x00\xc2\xff<?xml version="1.0"?>\x0a<config><entry n'
            b'ame="host-1"/></config>Q\x9d:\xd2=\x00\x00\x00'
        ),
        "entry_point": "every entry point",
        "printed_line": "",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_archive",
        "member": "",
    },
    {
        "shape": "a gzip stream that holds a tar archive with exactly one member, read through the archive producer",
        # One tar member, so the stream holds the header block, the data block and the terminator. The member names
        # no file, and its content is the accepted XML row's content.
        "content": (
            b"\x1f\x8b\x08\x00~\xfc\x05k\x02\xff\xed\xd2\xb1\x0a\xc20\x14\x85\xe1\xcc>E\xc8\xaeM\xb0\x9a%m\x9f\xa5"
            b"\x94\xa8\x05\x9b@\x1bE\xdf\xde\x10\x04\xc1]\x1d\xfc\xbf\xe5\\\xce\x1d\xeer\x87\x18\x0e\xe3Q|\x94\xce"
            b"\xf6u]2{O\xad\xed\xee5\x97\xde\x9a\xad\x15R\x8b/\xb8,\xa9\x9f\xf3I\xf1\x9f\\w\x9b\xce\xf2\xea\xe7e"
            b"\x8c\xa1Qf\xa3U\xd7\xae\xdcP\xde\xa2u>\xa4\xf9.C?\xf9F\x9d\xe2\x92\xd6FU\xad\xab\x9ek\x01\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf8\x95\x07\xe3\x1a`$\x00(\x00\x00"
        ),
        "entry_point": "every entry point",
        "printed_line": "",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_archive",
        "member": "",
    },
    {
        "shape": "a bundle that holds more than one XML member, read through a declared member",
        # Two members, and the row declares the first, whose content is the accepted row's content, so the pins read
        # the bytes the door checks as another row shows them and hold no content of their own.
        "content": (
            b"\x1f\x8b\x08\x08\x00\x00\x00\x00\x02\xfffirst\x00\xb3\xb1\xaf\xc8\xcdQ(K-*\xce"
            b"\xcc\xcf\xb3U2\xd43P\xb2\xb7\xe3\xb2I\xce\xcfK\xcbL\xb7\xb3I\xcd+)\xaaT\xc8K\xcc"
            b"M\xb5U\xca\xc8/.\xd15T\xd2\xb7\xb3\xd1\x87J\x03\x00Q\x9d:\xd2=\x00\x00\x00\x1f"
            b"\x8b\x08\x08\x00\x00\x00\x00\x02\xffsecond\x00\xb3I\xce\xcfK\xcbL\xd7\xb7\x03\x00"
            b"\x11\x10\xd1\xf1\t\x00\x00\x00"
        ),
        "entry_point": "every entry point",
        "printed_line": "",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_archive",
        "member": "first",
    },
    {
        "shape": (
            "the bytes a compressed stream expands to, past the input limit, refused while the cap is applied "
            "during decompression"
        ),
        # The content is under the limit the pins measure this row against and expands past it, so the refusal can
        # only come from the expansion. The pins read the row through the producer, which is where the cap is applied.
        "content": (
            b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff\xb3\xb1\xaf\xc8\xcdQ(K-*\xce\xcc\xcf\xb3U2\xd43P\xb2\xb7"
            b"\xe3\xb2I\xce\xcfK\xcbL\xb7\xb3I\xcd+)\xaaT\xc8K\xccM\xb5U\xca\xc8/.\xd15T\xb2\xb3II-N.\xca,(\x01"
            b"\xea\xb0K$\x11\xd8\xe8#\xeb\xb6\xd1\x07[\x00\xa4\xa1\x16\x02\x00^\xc8/C\x8f\x00\x00\x00"
        ),
        "entry_point": "none",
        "printed_line": "Error: refusing to read {origin}: the input is larger than the limit, which exceeds the "
        "input limit of {limit} bytes. Pass --max-input-bytes N to raise the limit for a trusted file.",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_archive",
        "member": "",
    },
    {
        "shape": (
            "the bytes a declared member expands to, past the input limit, refused while the cap is applied during "
            "decompression"
        ),
        # The content is under the limit the pins measure this row against and the declared member expands past it, so
        # the refusal can only come from the expansion of the member the row names. The pins read the row through the
        # producer, which is where the cap is applied.
        "content": (
            b"\x1f\x8b\x08\x08\x00\x00\x00\x00\x02\xfffirst\x00st\x1c<\x00\x00\x9fX\x87*\x8c"
            b"\x00\x00\x00\x1f\x8b\x08\x08\x00\x00\x00\x00\x02\xffsecond\x00\xb3I\xce\xcfK\xcb"
            b"L\xd7\xb7\x03\x00\x11\x10\xd1\xf1\t\x00\x00\x00"
        ),
        "entry_point": "none",
        "printed_line": "Error: refusing to read {origin}: the input is larger than the limit, which exceeds the "
        "input limit of {limit} bytes. Pass --max-input-bytes N to raise the limit for a trusted file.",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_archive",
        "member": "first",
    },
    {
        "shape": "a DTD inside a declared member of a bundle that holds more than one member",
        # The declared member holds the DTD row's content, so the pins read the answer as the DTD line on the bytes
        # the member expands to, and the other member only shows that the bundle holds more than one.
        "content": (
            b"\x1f\x8b\x08\x08\x00\x00\x00\x00\x02\xfffirst\x00\xb3\xb1\xaf\xc8\xcdQ(K-*\xce"
            b"\xcc\xcf\xb3U2\xd43P\xb2\xb7\xe3\xb2Qt\xf1w\x0e\x89\x0cpUH\xce\xcfK\xcbL\x07\x8a"
            b"@\x196\xa9y%E\x95\ny\x89\xb9\xa9\xb6J\x19\xf9\xc5%\xba\x86J\xfav6\xfaPi\x00\xc8"
            b"O\xee\xdeO\x00\x00\x00\x1f\x8b\x08\x08\x00\x00\x00\x00\x02\xffsecond\x00\xb3I\xce"
            b"\xcfK\xcbL\xd7\xb7\x03\x00\x11\x10\xd1\xf1\t\x00\x00\x00"
        ),
        "entry_point": "none",
        "printed_line": "Error: refusing to parse {origin}: the input declares a DTD for 'config', which a Panorama "
        "export never includes. A DTD can expand entities without bound or name a file to read.",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_archive",
        "member": "first",
    },
    {
        "shape": "a bundle that holds more than one XML member, refused when the operator names no member",
        # Two members, each the smallest XML body, so the count the member rule reads is two and the row states no
        # declaration. The flags byte names the name field, so each member names itself.
        "content": (
            b"\x1f\x8b\x08\x08\x00\x00\x00\x00\x02\xfffirst\x00\xb3I\xce\xcfK\xcbL\xd7\xb7\x03"
            b"\x00\x11\x10\xd1\xf1\t\x00\x00\x00\x1f\x8b\x08\x08\x00\x00\x00\x00\x02\xffseco"
            b"nd\x00\xb3I\xce\xcfK\xcbL\xd7\xb7\x03\x00\x11\x10\xd1\xf1\t\x00\x00\x00"
        ),
        "entry_point": "none",
        "printed_line": "Error: refusing to read {origin}: the bundle holds more than one member and the run "
        "declares none. Pass --member NAME to read one.",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_archive",
        "member": "",
    },
    {
        "shape": "a declared member the bundle does not hold, so the producer reads no member",
        # One member, named first, and the row declares a name the bundle does not hold, so the bytes reach the door
        # unchanged and the parse answers them with the line the table already holds for the magic bytes.
        "content": (
            b"\x1f\x8b\x08\x08\x00\x00\x00\x00\x02\xfffirst\x00\xb3I\xce\xcfK\xcbL\xd7\xb7\x03"
            b"\x00\x11\x10\xd1\xf1\t\x00\x00\x00"
        ),
        "entry_point": "none",
        "printed_line": "Error: Failed to parse XML file: not well-formed (invalid token): line 1, column 0",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_archive",
        "member": "second",
    },
    {
        "shape": "the decompressed bytes an archive read names in the provenance record",
        # The smallest stream that shows the two facts the record reads for an archive read. The flags byte names
        # the name field, so the stream states a member, and the member is a stored block that holds the accepted
        # row's content, so the bytes the door checks are bytes another row shows and not the stream itself.
        "content": (
            b'\x1f\x8b\x08\x08\x00\x00\x00\x00\x00\x00x\x00\x01=\x00\xc2\xff<?xml version="1.0"?>'
            b'\n<config><entry name="host-1"/></config>Q\x9d:\xd2=\x00\x00\x00'
        ),
        "entry_point": "every entry point",
        "printed_line": "",
        "status": "held",
        "pending_on": "",
        "measured_through": "provenance.record_for",
        "member": "",
    },
)
