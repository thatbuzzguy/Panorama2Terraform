"""Piece 6: the splitter reads the owners' rules (`docs/DEVICE_GROUP_SPLITTING.md`, `docs/ARCHITECTURE.md`
§2.3 and §6).

Four rules, each stated by its owner and read by the splitter:

1. `write_path.py` owns the byte rule, so a split file is the text the single writer wrote: LF, and the final
   line the single writer ends a text with. The splitter states no writer of its own.
2. `naming.py` §5 owns the name rule, so the file name is the §5 shape of the device group name. Two names that
   read the same shape name one file, and that is a refusal: a numbering would depend on the order the entries
   appear in, which §6 says is not a rule a run may depend on.
3. §2.3 says one entry produces one object and no method keeps a name-keyed dict, so the splitter's tables are
   keyed by the source line the read layer records (F4.2), and the join answers the devices of the entry that
   lists them.
4. The shared merge dedupes the pair (path, name) at its own level and keeps each entry at the path it sits at.
5. The printed fact reads the run's own row set and the path an entry sits at, and the line shape comes from
   `container_coverage.console_line`, so the splitter states no console line of its own.

Pins:

- the file name is the naming rule applied to the name, and two names that read one file name are refused with
  no file written;
- a split file is the text the single writer wrote: no CR, and the final line;
- the three association tables are keyed by the source line, two entries with one name are two rows that answer
  their own devices, and the join answers its rows in source line order;
- the merge keeps a nested entry at its own path and dedupes the pair (path, name) at its own level, the tree
  holds one container per path, and a section that states no entry writes no container;
- the extraction answers through the row it was given, and states no lookup, no absent answer and no warning;
- the run prints the three parts of the fact it read for a file with no device-group row, through the
  console-line owner, and prints nothing new when its table answers; a part the run cannot name is the honest
  statement.

The scan pin for the last rule is there for the reason `acceptance.md` states: a branch that cannot fire cannot
be shown by a run.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import container_coverage
import naming
import split_device_groups
import xml_input
from conftest import SRC_DIR, run_script

SPLITTER = SRC_DIR / "split_device_groups.py"

# The content the pins read. Each block states the shape one pin reads. The corpus states no device-group name
# that reads to the same file name as another, so the pins write their own content.
TWO_ENTRIES_ONE_NAME = (
    '<?xml version="1.0"?>\n<config>\n  <panorama>\n    <device-group>\n'
    '      <entry name="DG-Dup"><devices><entry name="fw-1"/></devices></entry>\n'
    '      <entry name="DG-Dup"><devices><entry name="fw-2"/></devices></entry>\n'
    "    </device-group>\n    <templates>\n"
    '      <entry name="T-1"><devices><entry name="fw-1"/></devices></entry>\n'
    '      <entry name="T-2"><devices><entry name="fw-2"/></devices></entry>\n'
    "    </templates>\n  </panorama>\n</config>\n"
)

# Two template entries that list one device, stated so the source order is not the order a name sort would put
# them in.
JOIN_ORDER = (
    '<?xml version="1.0"?>\n<config>\n  <panorama>\n    <device-group>\n'
    '      <entry name="DG-Join"><devices><entry name="fw-1"/></devices></entry>\n'
    "    </device-group>\n    <templates>\n"
    '      <entry name="T-b"><devices><entry name="fw-1"/></devices></entry>\n'
    '      <entry name="T-a"><devices><entry name="fw-1"/></devices></entry>\n'
    "    </templates>\n  </panorama>\n</config>\n"
)

# Two shared sections: the first states the container at its level, the second states an entry at a level the
# first does not state.
NESTED_MERGE = (
    '<?xml version="1.0"?>\n<config>\n  <device-group>\n'
    '    <entry name="DG-Merge"><devices><entry name="fw-1"/></devices></entry>\n'
    "  </device-group>\n"
    '  <shared><interface><entry name="x"/></interface></shared>\n'
    '  <shared><interface><virtual-wire><units><entry name="y"/></units></virtual-wire></interface></shared>\n'
    "</config>\n"
)

# The same name at two depths, and the same pair (path, name) stated twice.
DEPTH_MERGE = (
    '<?xml version="1.0"?>\n<config>\n  <device-group>\n'
    '    <entry name="DG-Merge"><devices><entry name="fw-1"/></devices></entry>\n'
    "  </device-group>\n"
    '  <shared><address><entry name="x"/></address></shared>\n'
    '  <shared><address><group><entry name="x"/></group><entry name="x"/></address></shared>\n'
    "</config>\n"
)

# The names the file-name pins read: one that the §5 shape changes, and one that sanitizes to nothing.
NAMES = ("DG-Internet", ".")

# Two names that read the same §5 shape, so they name one file.
COLLISION = ("DG/A", "DG A")


def _file(tmp_path, name, text) -> Path:
    """Content as a file, so the pins read it through the door and get the line map the reports read."""
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _split(tmp_path, text, out_name) -> Path:
    """One splitter run on content. Returns the output directory the run wrote."""
    source = _file(tmp_path, "split_input.xml", text)
    out = tmp_path / out_name
    result = run_script("split_device_groups.py", str(source), "--output-dir", str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    return out


def _file_name(name: str) -> str:
    """The file name, read through the naming rule so the pin states no second name rule (§5)."""
    return f"{naming.variable_name(name)}.xml"


def _tree(source, row: dict) -> ET.Element:
    """The tree the extraction builds for one row. The join is an argument, so the pin hands the tables the same
    source answers and the extraction states no lookup of its own."""
    return split_device_groups.extract_device_group_config(source, row, split_device_groups.device_associations(source))


def _names_at(container: ET.Element, path: str) -> list:
    """The entry names at one level, in the order the tree states them. Direct children only, because the
    dedupe reads the pair (path, name) at the level the path names."""
    node = container.find(path)
    return [entry.get("name") for entry in node.findall("entry")] if node is not None else []


# --- 2. The file name is the naming rule, with a collision decision ------------


def test_the_split_file_name_is_the_naming_rule_applied_to_the_name(tmp_path):
    """The file name is the §5 shape of the device group name, read through `naming`.

    Before the change the name kept every character the two `replace` calls did not name, so `DG-Internet` wrote
    `DG-Internet.xml` and a name that sanitizes to nothing wrote `..xml`.
    """
    content = (
        '<?xml version="1.0"?>\n<config>\n  <device-group>\n'
        + "".join(f'      <entry name="{name}"/>\n' for name in NAMES)
        + "  </device-group>\n</config>\n"
    )
    out = _split(tmp_path, content, "out_names")
    written = sorted(p.name for p in out.glob("*.xml"))
    assert written == sorted(_file_name(name) for name in NAMES), written

    # The rule is one function, so the print site and the pin read the same answer.
    rows = split_device_groups.parse_device_groups(xml_input.parse_xml(_file(tmp_path, "names.xml", content)))
    assert [split_device_groups.split_file_name(row["name"]) for row in rows] == [_file_name(name) for name in NAMES], (
        rows
    )


def test_two_names_that_read_one_file_name_are_refused_and_no_file_is_written(tmp_path):
    """Two names that read the same §5 shape name one file, so the run refuses before it writes.

    The numbering the run would have to pick depends on the order the entries appear in, so it is not a rule the
    run can depend on (§6). The refusal names both source names and the file name they read to. Before the
    change the second write replaced the first: the directory held one file, `DG_A.xml`, and it held the second
    entry.
    """
    content = (
        '<?xml version="1.0"?>\n<config>\n  <device-group>\n'
        + "".join(f'      <entry name="{name}"/>\n' for name in COLLISION)
        + "  </device-group>\n</config>\n"
    )
    source = _file(tmp_path, "collision.xml", content)
    out = tmp_path / "out_collision"
    result = run_script("split_device_groups.py", str(source), "--output-dir", str(out))
    assert result.returncode == 1, result.stdout + result.stderr
    message = result.stdout + result.stderr
    for name in COLLISION:
        assert name in message, (name, message)
    assert _file_name(COLLISION[0]) in message, message
    assert "Traceback" not in result.stderr, "a refusal is not the shape an unexpected error takes"
    assert not out.exists(), f"the run made {out} for a refused pair of names"

    # The same rule as a function: the pair is an input-layer refusal, so the print site and the rule read the
    # same kind, and a pair that does not collide answers the naming rule.
    rows = split_device_groups.parse_device_groups(xml_input.parse_xml(source))
    with pytest.raises(xml_input.UnsafeInputError) as caught:
        split_device_groups.split_file_names(rows)
    for name in COLLISION:
        assert name in str(caught.value), (name, caught.value)


# --- 1. The split files go through the single writer ---------------------------


def test_a_split_file_is_the_text_the_single_writer_writes(tmp_path):
    """The bytes a run wrote for one device group are the single writer's text: no CR, and the final line.

    The writer scan cannot show which writer wrote a file, because an element writer can produce the same bytes
    for the same tree; the final line is what the content shows. Before the change the file ended at the closing
    tag byte.
    """
    content = (
        '<?xml version="1.0"?>\n<config>\n  <device-group>\n'
        '    <entry name="DG-Writer"><description>the value the run reads</description></entry>\n'
        "  </device-group>\n"
        '  <shared><address><entry name="host-1"><ip-netmask>10.0.0.1/32</ip-netmask></entry></address>'
        "</shared>\n</config>\n"
    )
    out = _split(tmp_path, content, "out_writer")
    written = sorted(out.glob("*.xml"))
    assert written, "the run wrote no split file"
    for path in written:
        data = path.read_bytes()
        assert b"\r" not in data, path.name
        assert data.endswith(b"\n"), (path.name, "the single writer ends a text with the line it states")

    # The file reads back through the door as the tree the run built for that group.
    parsed = xml_input.parse_xml(written[0])
    entry = parsed.root.find(".//device-group/entry")
    assert entry is not None and entry.get("name") == "DG-Writer", written[0].name
    assert xml_input.read_text(entry.find("description").text) == "the value the run reads"
    assert xml_input.read_text(parsed.root.find(".//shared/address/entry/ip-netmask").text) == "10.0.0.1/32"


# --- 3. The tables are keyed by the source line --------------------------------


def test_the_splitter_tables_are_keyed_by_the_source_line(tmp_path):
    """§2.3: one entry is one object, and no method keeps a name-keyed dict, so the key is the source line.

    Before the change the table answered one row for two entries that shared a name.
    """
    source = xml_input.parse_xml(_file(tmp_path, "two_entries.xml", TWO_ENTRIES_ONE_NAME))
    entries = source.root.findall(".//device-group/entry")
    tables = split_device_groups.device_associations(source)
    table = tables["device_groups"]
    assert len(table) == len(entries) == 2, "two entries, so two rows"
    assert sorted(table) == [source.line_of(entry) for entry in entries], sorted(table)
    for entry in entries:
        row = table[source.line_of(entry)]
        assert row["line"] == source.line_of(entry), row
        assert row["entry"] is entry, "the row names the entry the run read"
        assert row["name"] == "DG-Dup", row["name"]

    # The join reads the same tables, so a name is not a key anywhere in the splitter.
    for kind in ("templates", "template_stacks"):
        for row in tables[kind].values():
            assert row["line"] == source.line_of(row["entry"]), (kind, row)


def test_two_entries_with_one_name_are_two_rows_that_answer_their_own_devices(tmp_path):
    """The join answers the devices of the entry that lists them, so one entry does not answer for two.

    Before the change the two entries merged into one device set, so the split file for the name copied the
    templates of both entries and held only the first entry.
    """
    source = xml_input.parse_xml(_file(tmp_path, "two_entries_join.xml", TWO_ENTRIES_ONE_NAME))
    rows = sorted(split_device_groups.parse_device_groups(source), key=lambda row: row["line"])
    assert [row["devices"] for row in rows] == [["fw-1"], ["fw-2"]], rows

    for row, template in zip(rows, ("T-1", "T-2"), strict=True):
        tree = _tree(source, row)
        assert [entry.get("name") for entry in tree.findall(".//templates/entry")] == [template], row
        held = tree.find(".//device-group/entry")
        assert held.get("name") == row["name"], row
        # The copy rule holds: the tree holds a copy, so it is independent of the source and of the other rows.
        assert held is not row["entry"], "the split tree is independent of the source"


def test_the_join_answers_the_rows_in_source_line_order(tmp_path):
    """The join's rows are in the order the input states them, so no second order rule appears (§6).

    The content states the two template entries in the order an alphabetical name sort would change. Before the
    change the join sorted names, so the copy order was `T-a`, `T-b`.
    """
    source = xml_input.parse_xml(_file(tmp_path, "join_order.xml", JOIN_ORDER))
    rows = sorted(split_device_groups.parse_device_groups(source), key=lambda row: row["line"])
    assert [row["name"] for row in rows] == ["DG-Join"], rows
    tree = _tree(source, rows[0])
    entries = tree.findall(".//templates/entry")
    assert [entry.get("name") for entry in entries] == ["T-b", "T-a"], entries


# --- 4. The shared merge merges by path and name, and keeps the path ----------


def test_the_merge_keeps_an_entry_at_the_path_it_sits_at(tmp_path):
    """An entry from a later shared section is merged at its own path, not under the container.

    Before the change the merge appended an unmatched entry directly under the container, so `y` was written as
    `interface/entry`, and the converter reported that entry as unaccounted.
    """
    out = _split(tmp_path, NESTED_MERGE, "out_nested")
    written = sorted(out.glob("*.xml"))
    assert written, "the run wrote no split file"
    shared = xml_input.parse_xml(written[0]).root.find(".//shared")
    assert shared is not None, written[0].name
    assert _names_at(shared, "interface") == ["x"], shared
    assert _names_at(shared, "interface/virtual-wire/units") == ["y"], shared


def test_the_merge_dedupes_the_pair_path_and_name_at_its_own_level(tmp_path):
    """One name at two depths is two entries, and the same pair (path, name) twice is one entry.

    Before the change the dedupe read the entries at any depth, so the second `x` was dropped and the `group`
    level the content stated was gone.
    """
    out = _split(tmp_path, DEPTH_MERGE, "out_depth")
    written = sorted(out.glob("*.xml"))
    assert written, "the run wrote no split file"
    shared = xml_input.parse_xml(written[0]).root.find(".//shared")
    assert shared is not None, written[0].name
    assert _names_at(shared, "address") == ["x"], shared
    assert _names_at(shared, "address/group") == ["x"], shared


def test_the_run_writes_one_container_per_path(tmp_path):
    """An entry is written at the path its row states, and the tree holds one container per path.

    Before the change the container name was fixed per kind, so content that states `<template>` (the singular
    spelling the read rule accepts) was written as `templates`, and a second entry at the same path added a
    second, empty container.
    """
    content = (
        '<?xml version="1.0"?>\n<config>\n  <device-group>\n'
        '    <entry name="DG-Path"><devices><entry name="fw-1"/></devices></entry>\n'
        "  </device-group>\n  <template>\n"
        '    <entry name="T-1"><devices><entry name="fw-1"/></devices></entry>\n'
        '    <entry name="T-2"><devices><entry name="fw-1"/></devices></entry>\n'
        "  </template>\n</config>\n"
    )
    out = _split(tmp_path, content, "out_path")
    written = sorted(out.glob("*.xml"))
    assert written, "the run wrote no split file"
    localhost = xml_input.parse_xml(written[0]).root.find(".//devices/entry")
    containers = [child.tag for child in localhost]
    assert containers == ["device-group", "template"], containers
    assert _names_at(localhost, "template") == ["T-1", "T-2"], containers


def test_an_empty_shared_section_writes_no_container(tmp_path):
    """A `shared` section that states no entry writes no container, so the split file carries content only.

    Before the change the run wrote a `shared` element whenever the export had a `shared` section, so an empty
    section wrote an empty container, and the converter reported the shared section as present with nothing in it.
    """
    content = (
        '<?xml version="1.0"?>\n<config>\n  <device-group>\n'
        '    <entry name="DG-Empty"><description>the value the run reads</description></entry>\n'
        "  </device-group>\n  <shared></shared>\n</config>\n"
    )
    out = _split(tmp_path, content, "out_empty_shared")
    written = sorted(out.glob("*.xml"))
    assert written, "the run wrote no split file"
    root = xml_input.parse_xml(written[0]).root
    assert root.find(".//shared") is None, [child.tag for child in root]
    entry = root.find(".//device-group/entry")
    assert entry is not None and entry.get("name") == "DG-Empty", written[0].name


# --- 5. The extraction answers through the row it was given -------------------


def test_the_extraction_states_no_lookup_and_no_warning():
    """The source scan for the rule content cannot show: a branch that cannot fire cannot be shown by a run.

    `parse_device_groups` names only entries the run read, so the extraction cannot be handed a name that is not
    in the tree. The rule is that the extraction states no lookup of its own, answers no absent value, and prints
    no warning, so the scan is what holds it.
    """
    source = Path(SPLITTER).read_text(encoding="utf-8")
    method = source[source.index("def extract_device_group_config") : source.index("def split_panorama_config")]
    assert "row" in method, "the extraction takes the table row it was given"
    assert "find" not in method, "the extraction states no lookup of its own"
    assert "None" not in method, "the extraction answers no absent value"
    assert "print" not in method, "the extraction prints no warning"


def test_the_extraction_answers_through_the_row_it_was_given(tmp_path):
    """Content half of the same rule: for every row the tree the run built holds that row's own entry.

    The answer is never the absent answer, so the row and the tree name the same entry. This is what the run
    writes for a row, and it is the shape the print site reads the row through.
    """
    source = xml_input.parse_xml(_file(tmp_path, "rows.xml", TWO_ENTRIES_ONE_NAME))
    rows = sorted(split_device_groups.parse_device_groups(source), key=lambda row: row["line"])
    assert len(rows) == 2, rows
    for row in rows:
        tree = _tree(source, row)
        held = tree.find(".//device-group/entry")
        assert held.get("name") == row["name"], row
        assert held is not row["entry"], "the split tree is independent of the source"


# --- 6. The fact the run prints for the shape it read ---------------------------


# Content that shows the shape the fact reads: a device entry with no device-group row. The entry sits at the
# path `devices`, on the line the pins count from the content.
FIREWALL_SHAPE = (
    '<?xml version="1.0"?>\n<config>\n  <devices>\n    <entry name="0123456789"/>\n  </devices>\n</config>\n'
)

# The same shape with nothing for the walk to hold, so the line can only state the honest parts.
NO_ENTRY = '<?xml version="1.0"?>\n<config/>\n'


def test_the_splitter_prints_the_fact_it_read_for_a_file_with_no_device_group_row(tmp_path):
    """The run prints the three parts through the console-line owner: the row count, the path the tree holds
    instead, and the source line. Before the change the run printed a guess about where the export came from,
    which named none of the three parts. The exit code stays with the rules that read the files
    (`docs/ARCHITECTURE.md` §4.6), so this run still exits 1 and writes nothing.
    """
    source = _file(tmp_path, "firewall.xml", FIREWALL_SHAPE)
    out = tmp_path / "out_fact"
    result = run_script("split_device_groups.py", str(source), "--output-dir", str(out))
    assert result.returncode == 1, result.stdout + result.stderr
    assert not out.exists(), f"the run made {out} for a shape its tables answer nothing for"

    # The parts are read through the owners that state them, so the pin restates no wording of its own: the
    # position is the read layer's line, the identity is the path the entry sits at, and the fact is the count.
    parsed = xml_input.parse_xml(source)
    rows = split_device_groups.parse_device_groups(parsed)
    shape = split_device_groups.tree_shape(parsed)
    assert not rows, "the run read no row for this shape, which is the fact the line states"
    assert shape["line"] == 4 and shape["path"] == "devices", (shape, "the content shows the parts the line names")
    printed = result.stdout.splitlines()
    assert printed == [
        f"{container_coverage.CONSOLE_WARNING}  {split_device_groups.BLOCK_HEADER}",
        container_coverage.console_line(
            "",
            container_coverage.position_part(shape["line"]),
            shape["path"],
            split_device_groups.row_fact(len(rows)),
        ),
    ], printed


def test_the_run_prints_nothing_new_when_its_table_answers(tmp_path):
    """A block prints only when it has a finding, so a run that read rows prints no diagnostic line and goes on to
    write its files.
    """
    parsed = xml_input.parse_xml(_file(tmp_path, "rows.xml", NESTED_MERGE))
    rows = split_device_groups.parse_device_groups(parsed)
    assert rows, "the content shows the shape the run reads"
    assert split_device_groups.console_lines(parsed, rows) == [], "the run states no fact for a shape it read"
    out = _split(tmp_path, NESTED_MERGE, "out_no_fact")
    assert sorted(p.name for p in out.glob("*.xml")) == [_file_name("DG-Merge")], "the run wrote the row it read"


def test_the_line_names_the_honest_statement_when_the_tree_holds_no_entry(tmp_path):
    """A part the run cannot name is the honest statement, not a guess: the position part is
    `container_coverage.position_part` for a finding with no line, and the identity part is the module's own
    statement for a tree that holds no entry at any path. The exit code is the same as the run above.
    """
    source = _file(tmp_path, "no_entry.xml", NO_ENTRY)
    parsed = xml_input.parse_xml(source)
    rows = split_device_groups.parse_device_groups(parsed)
    assert split_device_groups.tree_shape(parsed) is None, "the tree holds no entry to name"
    block = split_device_groups.console_lines(parsed, rows)
    assert block[1] == container_coverage.console_line(
        "",
        container_coverage.position_part(0),
        split_device_groups.NO_ENTRY_SHAPE,
        split_device_groups.row_fact(len(rows)),
    ), block
    result = run_script(
        "split_device_groups.py",
        str(source),
        "--output-dir",
        str(tmp_path / "out_honest"),
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout.splitlines() == block, result.stdout
