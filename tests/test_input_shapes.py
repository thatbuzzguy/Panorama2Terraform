"""Epic 13, the shape table (`src/input_shapes.py`).

`SHAPE_TABLE` is the one table of byte shape, accepted entry point, and printed line, so a document links to it and
restates no row (`docs/INPUT_SHAPES.md` §3). These pins measure the table in four directions:

- the table is data: every row has the one row shape `SHAPE_ROW_FIELDS`, and the pins define no row shape, no row,
  no content and no row wording of their own; every row is read through `tests/conftest.py::shape_row`, so no test
  module holds a row reader of its own;
- the module states no rule an owner states, so the table is a mirror and not a second definition;
- every held refusal row is measured through the owner function the row names, and the line the entry point prints
  for its content is the wording the row states, which is what stops a mirror drifting from its owner;
- the one held row that states a console line is measured through the block its owner states, read with the prefix
  through the module that owns the shape, because a console line row is the fact an entry point read rather than a
  refusal;
- every accepted row answers no refusal when the shared read rule reads its content, and no row is pending today, so
  the table states no line a pin cannot measure;
- the record row is measured through the record build rule its owner names, and the record it builds is read back
  through `provenance.parse_record`, because a row is held only when a pin can call its owner;
- the archive rows are read through the producer the table names, so the pins measure the shape from the bytes, and
  the decompression row is measured against a limit that is above its content and below what its content expands to,
  which is the only way the refusal it states can come from the expansion;

The pins decide each shape from the row's bytes and not from a file name, and no row names a file name or a fixture.
The pins call `xml_input.check_bytes`, `xml_input.read_input`, `xml_input.parse_bytes`, `xml_input.parse_archive`,
`state_input.parse_state`, `split_device_groups.console_lines` and `provenance.record_for` through each row's own
`measured_through`, so this module holds no second size check, no second DTD rule, no second reader, no second
console line and no second record rule.
"""

import ast
from pathlib import Path

import pytest

import container_coverage
import input_shapes
import naming
import panorama_to_terraform
import provenance
import source_fetch
import split_device_groups
import state_input
import xml_input
from conftest import FIXTURES_DIR, SRC_DIR, TESTS_DIR, input_refusal, printed_refusal, run_script, shape_line, shape_row

# The owners the rows name. A row names its owner as a function, the pins resolve the name and call it, so the pins
# hold no reader of their own.
OWNERS = {
    "xml_input": xml_input,
    "state_input": state_input,
    "split_device_groups": split_device_groups,
    "provenance": provenance,
}

# The limit the size pins measure against, which is under every row's content that is not a compressed stream, so
# the size half of a refusal reads as a plain byte count and the pins can compare the numbers a line prints. A row
# states the origin and the byte counts as placeholders, which the pins fill with what they measure. Every other row
# is measured under the door's default limit, so the size check cannot answer before the rule the row states.
MEASURE_LIMIT = 10

# The limit the decompression row is measured against. It sits above the row's compressed content and below what
# that content expands to, so the refusal the pins read for that row can only come from the expansion, which is the
# rule the row states. The pins read the shape through `xml_input.GZIP_MAGIC`, the producer's own definition, so the
# pins hold no shape rule and no content of their own.
EXPANSION_LIMIT = 120

# The placeholders a line may hold, which are the only parts the pins measure. A part the row states as data, such
# as the DTD name or the JSON key, is compared as wording and is not a placeholder.
MEASURED_PARTS = ("origin", "size", "limit")

# The rows the entry-point pins read: one for the refusal shape and one for the parse shape, because the two kinds
# `panorama_to_terraform.is_refusal` states print in two different shapes, and the two member rows, because one of
# them is refused with no declaration and the other is refused through the declaration the row states, so the pins
# read the declaration as row data and hold none of their own.
ENTRY_POINT_ROWS = (
    "XML bytes that declare a DTD in the prolog",
    "bytes the parser cannot read as one XML document, the magic bytes of a compressed member",
    "a bundle that holds more than one XML member, refused when the operator names no member",
    "a declared member the bundle does not hold, so the producer reads no member",
)


def _rows(status: str, states_line: bool | None = None) -> list[dict]:
    """The rows a pin reads, by status and by whether the row states a line."""
    if states_line is None:
        return [row for row in input_shapes.SHAPE_TABLE if row["status"] == status]
    return [
        row for row in input_shapes.SHAPE_TABLE if row["status"] == status and bool(row["printed_line"]) == states_line
    ]


def _refusal_rows() -> list[dict]:
    """The held rows that state a line and name `none` as their entry point, which rule 6 states as the refusal
    rows, so the pins read a refusal through the door and nothing else."""
    return [row for row in _rows(input_shapes.STATUS_HELD, states_line=True) if row["entry_point"] == "none"]


def _console_rows() -> list[dict]:
    """The held rows that state a line through an entry point that accepts the shape, so the line is the fact that
    entry point read rather than a refusal."""
    return [row for row in _rows(input_shapes.STATUS_HELD, states_line=True) if row["entry_point"] != "none"]


def _owner(row: dict):
    """The function the row names, read through the row's own `measured_through`."""
    module, _, name = row["measured_through"].partition(".")
    return getattr(OWNERS[module], name)


def _origin(path: Path) -> xml_input.SourceOrigin:
    """The origin as the file producer states it, so the pins read the origin through the owner's own rule."""
    return xml_input.SourceOrigin.for_path(path)


def _limit(row: dict) -> int:
    """The limit one row is measured against: the pins' own limit when the row's line carries `{limit}`, which is
    the size half of a line, otherwise the door's default limit. A compressed row is measured against the limit that
    sits between its content and what its content expands to, so the refusal can only come from the expansion."""
    if "{limit}" not in row["printed_line"]:
        return xml_input.DEFAULT_MAX_INPUT_BYTES
    if row["content"][: len(xml_input.GZIP_MAGIC)] == xml_input.GZIP_MAGIC:
        return EXPANSION_LIMIT
    return MEASURE_LIMIT


def _answer(row: dict, path: Path) -> Exception | None:
    """What the row's owner answers for the row's content: the refusal it raises, or None when it accepts.

    A row that states a declaration is read with the row's own declaration, so the pins read the declaration as row
    data and hold no member name of their own.
    """
    reader = _owner(row)
    try:
        if reader is xml_input.read_input:
            path.write_bytes(row["content"])
            reader(path, _limit(row))
        elif reader is xml_input.check_bytes:
            # The door takes the limit the pins measure the row against, because the row states a size line.
            reader(row["content"], _origin(path), _limit(row))
        elif reader is xml_input.parse_archive:
            # The producer takes the limit and the declaration the row states.
            reader(row["content"], _origin(path), _limit(row), row["member"] or None)
        elif reader is provenance.record_for:
            # The record build rule takes a source, not bytes, so the pins hand it the source the producer returned
            # for the row's content and the request the run read, which is None for the producer this row shows.
            reader(xml_input.parse_archive(row["content"], _origin(path), _limit(row), row["member"] or None), None)
        else:
            reader(row["content"], _origin(path))
    except Exception as error:  # The two refusal kinds the door states, and no other kind.
        return error
    return None


def _line(row: dict, path: Path) -> str:
    """The row's own wording with the measured parts filled in, through `tests/conftest.py::shape_line`. Only the
    origin and the byte counts are the pins' own measurements."""
    return shape_line(row, _origin(path), len(row["content"]), _limit(row))


def _placeholders(row: dict) -> set[str]:
    """The parts of a line the pins measure, read from the row."""
    line = row["printed_line"]
    return {part for part in MEASURED_PARTS if "{" + part + "}" in line}


def test_the_table_is_data_with_one_row_shape():
    """Criterion 1: the table is data read through `ast`, every row has `SHAPE_ROW_FIELDS` and nothing else, the
    content is bytes, and the status vocabulary is the two words the module states."""
    tree = ast.parse((SRC_DIR / "input_shapes.py").read_text(encoding="utf-8"))
    table = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "SHAPE_TABLE"
    )
    assert isinstance(table.value, ast.Tuple), "the table is data, not a build"
    rows = [ast.literal_eval(row) for row in table.value.elts]
    assert len(rows) == len(input_shapes.SHAPE_TABLE), (rows, "the pins read the table the module states")
    statuses = set()
    for row in rows:
        assert tuple(row) == input_shapes.SHAPE_ROW_FIELDS, (row["shape"], "a row has the one row shape")
        assert isinstance(row["content"], bytes), (row["shape"], "the shape is shown by bytes")
        assert row["content"], (row["shape"], "every row shows its shape in bytes")
        statuses.add(row["status"])
        assert row["status"] in (input_shapes.STATUS_HELD, input_shapes.STATUS_PENDING), (row["shape"], "the status")
        assert len(_placeholders(row)) <= len(MEASURED_PARTS), (row["shape"], "the pins measure no part of their own")
        if row["status"] == input_shapes.STATUS_PENDING:
            assert row["measured_through"] == "", (row["shape"], "a pending row has no owner to read it through")
        else:
            module, _, name = row["measured_through"].partition(".")
            assert hasattr(OWNERS[module], name), (row["shape"], "every held row names a function its owner defines")
        assert row["entry_point"] in ("none", "every entry point") or row["entry_point"].endswith(".py"), (
            row["shape"],
            "the entry-point column names a module, or none",
        )
    assert statuses == {input_shapes.STATUS_HELD}, "no row is pending today, so the pins measure every row"
    assert not [row for row in rows if row["status"] == input_shapes.STATUS_PENDING], "no row is pending today"
    held_lines = _rows(input_shapes.STATUS_HELD, states_line=True)
    assert len(held_lines) == 16, "the pins measure every held row that states a line"
    assert len(_refusal_rows()) == 15, "the pins measure every held refusal row through its owner"
    assert len(_console_rows()) == 1, "the pins measure the held console line row through its owner"
    assert len(_rows(input_shapes.STATUS_HELD, states_line=False)) == 9, "the pins measure every accepted row"


def test_the_pins_define_no_row_shape_and_no_row_of_their_own():
    """Criterion 1, read as an absence: this module defines no row shape, no row, and no content of its own, so the
    table has one definition and the pins read it as data."""
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    held = {getattr(node.targets[0], "id", "") for node in tree.body if isinstance(node, ast.Assign)}
    assert "SHAPE_TABLE" not in held and "SHAPE_ROW_FIELDS" not in held, "the pins hold no copy of the table"
    assert not held & set(input_shapes.SHAPE_ROW_FIELDS), (held, "the pins state no field of their own")
    assert not [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Dict) and len(node.keys) == len(input_shapes.SHAPE_ROW_FIELDS)
    ], "the pins hold no row of their own"
    assert not [
        node
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, bytes)
    ], "the pins hold no content of their own, they read the table's content"


def test_the_module_states_no_rule_an_owner_states():
    """Criterion 2, as a scan of the table module's own code: it defines no function, runs nothing, imports nothing,
    and holds no copy of a rule an owner states, so the table is a mirror of the owners and not a second definition."""
    text = (SRC_DIR / "input_shapes.py").read_text(encoding="utf-8")
    tree = ast.parse(text)
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)], (
        "the table module states no rule as a function"
    )
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Call)], "the table module runs nothing"
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Import)], "the table module imports nothing"
    held = {getattr(node.targets[0], "id", "") for node in tree.body if isinstance(node, ast.Assign)}
    assert held == {"SHAPE_ROW_FIELDS", "STATUS_HELD", "STATUS_PENDING", "SHAPE_TABLE"}, held
    for rule in ("check_bytes", "reject_dtd", "parse_bytes", "parse_state", "read_input", "console_line"):
        assert f"def {rule}" not in text, (rule, "the table states no rule an owner states")
    for name in (xml_input.CONTROL_CHARS, container_coverage.CONSOLE_PREFIX, naming.UNNAMED, source_fetch.API_KEY_ENV):
        assert str(name) not in text, (name, "the table holds no copy of an owner's rule")
    assert "print(" not in text, "the table module prints no line"
    assert "open(" not in text, "the table module reads no file"


def test_no_row_names_a_file_name_or_a_fixture():
    """Criterion 4: the shape is read from the bytes, so no row names a file name, an extension, or a fixture."""
    fixtures = {path.name for path in FIXTURES_DIR.glob("*.xml")}
    for row in input_shapes.SHAPE_TABLE:
        for field, value in row.items():
            assert not isinstance(value, Path), (row["shape"], field, "a row names no path")
            if not isinstance(value, str):
                continue
            assert ".xml" not in value and ".json" not in value, (row["shape"], field, "a row names no file name")
            assert value not in fixtures, (row["shape"], field, "a row names no committed fixture")
            assert not value.startswith(("tests/", "src/")), (row["shape"], field, "a row names no path")


def test_the_shape_is_decided_from_the_bytes_and_not_from_a_file_name(tmp_path):
    """Criterion 4, measured: the same bytes answer the same way under three different names, so a name decides
    nothing. The magic-bytes row is refused under a name that says XML, and the accepted XML row is accepted under a
    name that says archive, both read through the shared read rule (`tests/conftest.py::input_refusal`). The accepted
    archive rows answer the same way under the same three names, so the shape is read from the bytes and not from the
    extension. The record row is one of them, because its content is a stream an entry point accepts, and the row read
    through a declared member is read with the declaration the row states, so the pins hold no member name of their
    own."""
    refused_row = shape_row("bytes the parser cannot read as one XML document, the magic bytes of a compressed member")
    accepted_row = shape_row("XML bytes, no DTD, within the input limit")
    archive_rows = [
        row
        for row in _rows(input_shapes.STATUS_HELD, states_line=False)
        if row["content"][: len(xml_input.GZIP_MAGIC)] == xml_input.GZIP_MAGIC
    ]
    assert len(archive_rows) == 4, (archive_rows, "every accepted archive row shows a compressed stream")
    for name in ("shape.bin", "shape.xml", "shape.gz"):
        refused = tmp_path / name
        refused.write_bytes(refused_row["content"])
        accepted = tmp_path / (name + ".accepted")
        accepted.write_bytes(accepted_row["content"])
        assert input_refusal(refused) is not None, (name, "the read rule refuses these bytes under any name")
        assert input_refusal(accepted) is None, (name, "the read rule accepts these bytes under any name")
        for row in archive_rows:
            shape = tmp_path / (name + ".shape")
            shape.write_bytes(row["content"])
            assert input_refusal(shape, row["member"] or None) is None, (
                name,
                row["shape"],
                "the read rule accepts this shape under any name",
            )


def test_the_decompression_row_is_measured_against_the_expansion_and_not_the_compressed_size(tmp_path):
    """Criterion 8, the decompression half: the row's content is under the limit the pins measure it against, so the
    size check passes for the compressed bytes and the refusal the row states can only come from what the content
    expands to. The pins read the row through the producer, the owner the row names, and hold that the answer is the
    line the door states for a size refusal, with the origin and the limit as the parts the pins measure. The row
    states no size number, because the pins cannot read an expansion as a content size."""
    row = shape_row(
        "the bytes a compressed stream expands to, past the input limit, refused while the cap is applied during "
        "decompression"
    )
    assert len(row["content"]) < EXPANSION_LIMIT, (row["shape"], "the compressed bytes pass the size check")
    path = tmp_path / "input"
    error = _answer(row, path)
    assert error is not None, (row["shape"], "the producer refuses this shape before the parse")
    assert panorama_to_terraform.is_refusal(error), (row["shape"], "the refusal kind is the one the door states")
    assert "{size}" not in row["printed_line"], (row["shape"], "the pins state no size they cannot read from the row")
    assert printed_refusal(error) == _line(row, path), (row["shape"], "the printed line is the row's wording")
    assert f"limit of {EXPANSION_LIMIT} bytes" in printed_refusal(error), (row["shape"], "the line names the limit")


def test_the_dtd_row_is_measured_by_the_parser_and_not_by_a_text_search(tmp_path):
    """Criterion 4: the UTF-16 row holds the same prolog as the accepted row, in an encoding no byte-level text
    search can read, and the parser still answers the row's line, so the row's answer is the parser's and not a text
    search's. The pins build the encoding from the accepted row's content, so they hold no content of their own."""
    row = shape_row("a DTD in an encoding a text search cannot read, the UTF-16 shape")
    # A text search reads bytes one for one, so these bytes hold no wording a text search can read.
    assert "<!DOCTYPE" not in row["content"].decode("latin-1"), "the bytes hold no wording a text search can read"
    path = tmp_path / "input"
    error = _answer(row, path)
    assert error is not None, "the door still refuses this shape"
    assert printed_refusal(error) == _line(row, path), (error, "the parser reads the prolog in any encoding")


@pytest.mark.parametrize("row", _refusal_rows())
def test_a_held_refusal_row_prints_the_line_its_owner_states(row, tmp_path):
    """Criterion 3: the pins run the row's content through the row's own owner, print the answer through the entry
    point's own print site, and hold that the line is the row's wording with only the measured parts filled in. The
    refusal kind is one of the two `is_refusal` states, so the pins state no third kind."""
    path = tmp_path / "input"
    error = _answer(row, path)
    assert error is not None, (row["shape"], "a held refusal row is refused by its owner")
    assert panorama_to_terraform.is_refusal(error), (row["shape"], "the refusal kinds are the two the door states")
    assert printed_refusal(error) == _line(row, path), (row["shape"], "the printed line is the row's wording")
    if row["measured_through"] in ("xml_input.check_bytes", "xml_input.read_input", "state_input.parse_state"):
        # The door's wording names the source, which the pins measure, so the source part is a placeholder.
        assert "{origin}" in row["printed_line"], (row["shape"], "the source part of a refusal is measured")
        if "{size}" in row["printed_line"]:
            assert str(len(row["content"])) in printed_refusal(error), (
                row["shape"],
                "the size the line prints is the content",
            )
    else:
        # The parse shape names no source: the answer part is what the parser answered for this content, so the row
        # states that answer as wording and holds no placeholder the pins would have to invent.
        assert printed_refusal(error).endswith(str(error)), (row["shape"], "the answer part is the parser's answer")


@pytest.mark.parametrize("row", _rows(input_shapes.STATUS_HELD, states_line=False))
def test_an_accepted_row_answers_no_refusal_through_the_shared_read_rule(row, tmp_path):
    """Criterion 3, the accepted half: the shared read rule (`tests/conftest.py::input_refusal`) accepts an XML row's
    content, so the row is right to state no line. A JSON row is read by the state door, which is the same rule with
    only the parse step chosen by the kind, so the pin reads it through the owner the row names."""
    path = tmp_path / "input"
    path.write_bytes(row["content"])
    assert _answer(row, path) is None, (row["shape"], "the owner the row names accepts its content")
    if row["measured_through"] == "state_input.parse_state":
        # The shared rule reads corpus material as XML, so a JSON shape is read through the door that owns the kind.
        assert input_refusal(path) is not None, (row["shape"], "the shared rule reads no JSON shape as XML")
    else:
        # A row that states a declaration is read with the row's own declaration, so the pins hold no member name.
        assert input_refusal(path, row["member"] or None) is None, (row["shape"], "the shared read rule accepts it")


@pytest.mark.parametrize("row", _console_rows())
def test_a_held_console_row_prints_the_fact_through_the_block_its_owner_states(row, tmp_path):
    """Criterion 3, the console half: the pin runs the row's content through the block the row's owner states and
    compares the printed line with the row. An entry point accepts this shape, so the answer is not a refusal and the
    pins read no door here, and the row states no placeholder, so the pin compares the whole line. The row holds no
    prefix, because the prefix is the part `container_coverage` states, so the pin reads the prefix through that
    owner, and the line's parts are the three the shape holds: the source line, the path the tree holds the entry at,
    and the fact. The pins read each part through the owner that states it, so the pins hold no part of their own.
    """
    path = tmp_path / "input"
    path.write_bytes(row["content"])
    refused = input_refusal(path)
    assert refused is None, (row["shape"], "the shared read rule accepts this shape, so the line is not a refusal")
    source = xml_input.parse_bytes(row["content"], _origin(path))
    read = split_device_groups.parse_device_groups(source)
    shape = split_device_groups.tree_shape(source)
    block = _owner(row)(source, read)
    assert not read, (row["shape"], "the fact is the row count the run read")
    assert len(block) == 2, (block, "the block prints its header and the line")
    prefix = container_coverage.CONSOLE_PREFIX
    assert prefix not in row["printed_line"], (row["shape"], "the table holds no copy of the shape")
    line = block[1]
    assert line == prefix + row["printed_line"], (row["shape"], "the printed line is the row's wording")
    parts = line[len(prefix) :].split("  ")
    assert parts == [
        container_coverage.position_part(shape["line"]),
        shape["path"],
        split_device_groups.row_fact(len(read)),
    ], (parts, "the line names the three parts the shape holds")


def test_no_row_is_pending_so_the_pins_measure_every_row_through_an_owner_they_call():
    """The pending half of the status rule (`docs/INPUT_SHAPES.md` §3 rule 3), read as an absence: no row is pending
    today, because Piece 13B.4 landed the owner its rule states, so every row names a function the pins can call and
    states a line the pins can measure. A pending row states no line, names no entry point as accepting its shape and
    names no owner, so a rule that has no owner cannot hold a row, and no row names a §2 decision a pin cannot
    measure. The row the piece moved is read through the producer the table names, so the pins read the member rule's
    answer through the owner that states it and hold no line of their own."""
    pending = [row for row in input_shapes.SHAPE_TABLE if row["status"] == input_shapes.STATUS_PENDING]
    assert pending == [], "no row is pending today"
    for row in input_shapes.SHAPE_TABLE:
        assert row["pending_on"] == "", (row["shape"], "a held row names no decision or piece it waits for")
        module, _, name = row["measured_through"].partition(".")
        assert hasattr(OWNERS[module], name), (row["shape"], "every row names a function its owner defines")
    moved = shape_row("a bundle that holds more than one XML member, refused when the operator names no member")
    assert moved["measured_through"] == "xml_input.parse_archive", (
        moved["shape"],
        "the pins read the member rule's answer through the producer",
    )


def test_the_member_rule_line_holds_only_the_origin_as_a_measured_part(tmp_path):
    """Criterion 2, the member half (`docs/INPUT_SHAPES.md` §3 rule 2): the member rule's line names the source as
    the part the pins measure and states no member count, because a count is a fact the pins read from the row's own
    content and a line that named one would state a number the pins cannot read from the row. The pins read the row
    through the producer, print the answer through the entry point's own print site, and hold that the line is the
    row's wording with only the origin filled in."""
    row = shape_row("a bundle that holds more than one XML member, refused when the operator names no member")
    assert _placeholders(row) == {"origin"}, (row["shape"], "the pins measure no part of their own")
    assert not any(character.isdigit() for character in row["printed_line"]), (
        row["shape"],
        "the line names no count the pins cannot read from the row",
    )
    path = tmp_path / "input"
    error = _answer(row, path)
    assert error is not None, (row["shape"], "the member rule refuses this shape")
    assert panorama_to_terraform.is_refusal(error), (row["shape"], "the refusal kind is the one the door states")
    assert printed_refusal(error) == _line(row, path), (row["shape"], "the printed line is the row's wording")


def test_the_table_mirrors_the_member_rule_and_holds_no_wording_of_its_own():
    """Criterion 2, as a scan of the table module and of the owner: the member rule's refusal is stated inside the
    rule function the owner defines, the table mirrors it as data and builds no wording of its own, and the producer
    reads the shape through the rule and states no refusal, so the table cannot mirror a wording a producer holds."""
    tree = ast.parse((SRC_DIR / "xml_input.py").read_text(encoding="utf-8"))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    rule = functions["read_member"]
    assert [node for node in ast.walk(rule) if isinstance(node, ast.Raise)], (
        "the member rule states its own refusal, which is the wording the row mirrors",
    )
    producer = functions["parse_archive"]
    assert "read_member" in [
        getattr(node.func, "id", "") for node in ast.walk(producer) if isinstance(node, ast.Call)
    ], (producer, "the producer reads the shape through the rule the owner states")
    assert not [node for node in ast.walk(producer) if isinstance(node, ast.Raise)], (
        "the producer states no refusal of its own",
    )
    table_tree = ast.parse((SRC_DIR / "input_shapes.py").read_text(encoding="utf-8"))
    assert not [node for node in ast.walk(table_tree) if isinstance(node, ast.JoinedStr)], (
        "the table mirrors the wording as data and builds none",
    )


def test_the_declaration_is_row_data_and_no_pin_holds_a_member_of_its_own():
    """Criterion 1, the declaration half: a row that states no declaration states the empty string, so the pins read
    the declaration as row data, and only a row read through the archive producer states one, because the declaration
    is the operator's argument and the pins read it through the row. The pins hold no declaration of their own."""
    for row in input_shapes.SHAPE_TABLE:
        assert row["member"] == "" or row["measured_through"] == "xml_input.parse_archive", (
            row["shape"],
            "only a row read through the archive producer states a declaration",
        )
    declared = {row["member"] for row in input_shapes.SHAPE_TABLE if row["member"]}
    assert declared, "the pins read at least one row through a declared member"
    for module in sorted(TESTS_DIR.glob("*.py")):
        text = module.read_text(encoding="utf-8")
        if "shape_row" not in text:
            continue
        tree = ast.parse(text)
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                assert node.value.value not in declared, (module.name, node.value.value, "a pin holds no member name")


def test_no_test_module_holds_a_row_line_or_a_print_shape_of_its_own():
    """Criterion 1, read across the test set: the rows are read through `tests/conftest.py::shape_row` and the line
    is captured through `tests/conftest.py::printed_refusal`, so a test module that reads a row defines no row reader
    of its own, no print shape of its own, and holds no line of a row as a string of its own, because the table is the
    one definition of the wording and the pins compare against it. The pins fill the parts they measure through the
    owners, so a pin that held a line would be a second definition."""
    for module in sorted(TESTS_DIR.glob("*.py")):
        text = module.read_text(encoding="utf-8")
        if "shape_row" not in text:
            continue
        tree = ast.parse(text)
        if module.name != "conftest.py":
            names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
            for shared in ("shape_row", "printed_refusal", "shape_line"):
                assert shared not in names, (module.name, shared, "the shared fact lives in `tests/conftest.py`")
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            for row in input_shapes.SHAPE_TABLE:
                if not row["printed_line"]:
                    continue
                assert row["printed_line"] not in node.value, (
                    module.name,
                    node.value,
                    "a test module holds a row line of its own",
                )


def test_the_record_row_is_measured_through_the_record_build_rule(tmp_path):
    """The record row, read through the owner the row names and back through the record module's reader, which is
    what makes a row held: a row is measured only when a pin can call its owner (`docs/INPUT_SHAPES.md` §3 rule 3).
    The pins hold no bytes of their own: the shape is the row's content, and the record's byte facts are read against
    the content the accepted row shows, so the pins hold that the record names the bytes the door checked and not the
    stream the row holds. The kind and the member are read through the origin, which is the one definition the record
    reads, and the record reads back as itself through `parse_record`, so the row's owner is a build rule the pins
    call, not a wording the table states.
    """
    row = shape_row("the decompressed bytes an archive read names in the provenance record")
    path = tmp_path / "input"
    origin = _origin(path)
    source = xml_input.parse_archive(row["content"], origin)
    record = _owner(row)(source, None)
    assert record == provenance.parse_record(provenance.render(record)), "the record row reads back as itself"
    assert record.kind == xml_input.ARCHIVE_KIND, "the record names the archive through the kind the producer states"
    assert record.member == source.origin.member, "the record names the member through the origin"
    assert record.member != provenance.ABSENT, "the stream states a member name"
    assert record.name == origin.name and record.path == str(origin.path), "the producer changed no name rule"
    assert record.size == len(shape_row("XML bytes, no DTD, within the input limit")["content"]), (
        "the size names the bytes the door checked, not the compressed stream"
    )
    assert record.sha256 == source.sha256, "the hash names the same bytes the door checked"
    assert provenance.cache_reference(record) is None, "the file producer reads no cache, so the record names none"

    # The member is the name each stream states, read by the producer, so the record module states no value for it:
    # the two accepted archive rows answer with two different names, and a stream that states no name answers the `-`
    # the record module states for a field that does not apply.
    gzip_row = shape_row("a gzip stream that holds exactly one member, read through the archive producer")
    tar_row = shape_row(
        "a gzip stream that holds a tar archive with exactly one member, read through the archive producer"
    )
    names = {}
    for record_shape in (gzip_row, tar_row):
        shape_source = _owner(record_shape)(record_shape["content"], _origin(tmp_path / "shape"))
        names[record_shape["shape"]] = provenance.record_for(shape_source, None).member
    assert names[gzip_row["shape"]] != names[tar_row["shape"]], (names, "the name comes from each stream")


@pytest.mark.parametrize("shape", ENTRY_POINT_ROWS)
def test_both_entry_points_print_the_same_line_for_the_same_bytes(shape, tmp_path):
    """Criterion 3, at the entry points: the converter and the splitter read the same bytes and print the same line,
    so the row's line is the shape both entry points print for it. Both exit 1 and neither writes a file. A row that
    states a declaration is read with the declaration the row states, so the pins pass no member name of their own.
    """
    row = shape_row(shape)
    path = tmp_path / "input"
    path.write_bytes(row["content"])
    expected = _line(row, path)
    declared = ["--member", row["member"]] if row["member"] else []
    converter = run_script("panorama_to_terraform.py", str(path), "--output-dir", str(tmp_path / "out"), *declared)
    splitter = run_script("split_device_groups.py", str(path), "--output-dir", str(tmp_path / "split"), *declared)
    assert converter.returncode == 1 and splitter.returncode == 1, (converter.stdout, splitter.stdout)
    assert [line for line in converter.stdout.splitlines() if line.startswith("Error:")] == [expected], converter.stdout
    assert [line for line in splitter.stdout.splitlines() if line.startswith("Error:")] == [expected], splitter.stdout
    assert sorted(p.name for p in tmp_path.iterdir()) == ["input"], "a refusal writes no output"
