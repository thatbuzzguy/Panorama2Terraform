#!/usr/bin/env python3
"""Epic 13, the shapes an input can be: one table of byte shape, accepted entry point, and printed line.

Seven rules, stated once here. The table is data, so a document links to it and restates no row
(`docs/INPUT_SHAPES.md` §3), and `tests/test_input_shapes.py` measures every held row against the door.

1. **One row shape** (`SHAPE_ROW_FIELDS`): the byte shape, the content that shows it, the entry point that accepts
   it, the line the run prints for it, the status, the decision or the piece a pending row waits for, and the owner
   function the pins read the row through. A row is one shape, so a shape two entry points answer differently is two
   rows.
2. **The module states no check and no reader.** The two byte checks stay `xml_input.check_bytes`, and the parse
   step is chosen by the source kind in `xml_input.py` and `state_input.py`, so this module adds no third kind, no
   size rule, no DTD rule, no parser, no writer, no console line, no naming rule, no environment name, and no
   control-character set. It names no file, no path, and no fixture: the shape is read from the bytes, which is the
   shape the DTD rule already has, because that check asks the parser and not a text search.
3. **The lines are the owners' wording, mirrored as data.** The door's wording is `xml_input.py`'s, the state
   door's is `state_input.py`'s, and the shape a run prints for a refusal is `panorama_to_terraform.refused`. The
   pins build each line through its owner and compare it with the row, so a mirror cannot drift from the module that
   states the rule. A part of a line the pins measure is written as a placeholder the pins fill with what they read:
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
   limit, so the size half of a refusal reads as a plain byte count.
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
    },
    {
        "shape": "a `<!DOCTYPE` that only appears in a prolog comment",
        "content": b'<?xml version="1.0"?>\n<!-- a <!DOCTYPE config> -->\n<config/>',
        "entry_point": "every entry point",
        "printed_line": "",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_bytes",
    },
    {
        "shape": "a JSON state document that reads as one object with a `resources` array",
        "content": b'{"version":4,"resources":[{"type":"panos_address","name":"host-1","values":{"name":"x"}}]}',
        "entry_point": "state_input.py",
        "printed_line": "",
        "status": "held",
        "pending_on": "",
        "measured_through": "state_input.parse_state",
    },
    {
        "shape": "a `<!DOCTYPE` inside a JSON value, where no prolog exists for the check to read",
        "content": b'{"resources":[{"type":"panos_address","name":"x","values":{"name":"<!DOCTYPE config>"}}]}',
        "entry_point": "state_input.py",
        "printed_line": "",
        "status": "held",
        "pending_on": "",
        "measured_through": "state_input.parse_state",
    },
    {
        "shape": "the firewall export shape, `devices/entry` with no `device-group` row",
        "content": b'<?xml version="1.0"?>\n<config><devices><entry name="0123456789"/></devices></config>',
        "entry_point": "panorama_to_terraform.py",
        "printed_line": "",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_bytes",
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
    },
    {
        "shape": "bytes the parser cannot read as one XML document, the magic bytes of a compressed member",
        "content": b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00not xml",
        "entry_point": "none",
        "printed_line": "Error: Failed to parse XML file: not well-formed (invalid token): line 1, column 0",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_bytes",
    },
    {
        "shape": "an entity reference with no DTD that declares it",
        "content": b'<?xml version="1.0"?>\n<config>&lol3;</config>',
        "entry_point": "none",
        "printed_line": "Error: Failed to parse XML file: undefined entity: line 2, column 8",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_bytes",
    },
    {
        "shape": "a control character the read layer refuses, as a raw byte inside XML content",
        "content": b'<?xml version="1.0"?>\n<config><entry name="host\x071"/></config>',
        "entry_point": "none",
        "printed_line": "Error: Failed to parse XML file: not well-formed (invalid token): line 2, column 25",
        "status": "held",
        "pending_on": "",
        "measured_through": "xml_input.parse_bytes",
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
    },
    {
        "shape": "the splitter reading the firewall export shape, the fact it prints for it",
        "content": b'<?xml version="1.0"?>\n<config><devices><entry name="0123456789"/></devices></config>',
        "entry_point": "split_device_groups.py",
        "printed_line": "line 2  devices  0 device-group/entry rows read, so the tree holds the shape named instead",
        "status": "held",
        "pending_on": "",
        "measured_through": "split_device_groups.console_lines",
    },
    {
        "shape": "a single-member gzip, or a tar.gz with one XML member, read through the archive producer",
        "content": b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00not xml",
        "entry_point": "none",
        "printed_line": "",
        "status": "pending",
        "pending_on": "§2 decision 4",
        "measured_through": "",
    },
    {
        "shape": "a bundle that holds more than one XML member, with no member selection rule yet",
        "content": b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00not xml",
        "entry_point": "none",
        "printed_line": "",
        "status": "pending",
        "pending_on": "§2 decision 4",
        "measured_through": "",
    },
    {
        "shape": "the bytes an archive read names in the provenance record",
        "content": b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00not xml",
        "entry_point": "none",
        "printed_line": "",
        "status": "pending",
        "pending_on": "§2 decision 5",
        "measured_through": "",
    },
)
