"""F8.5 the run over many sources (`docs/API_CONVERSION_PATH.md` §2.4): one response is one source.

Eleven groups:

1. One response keeps its own line map and its own parent walk, so the run builds no tree from many
   responses. A report position can only name a line inside the response that holds the entry.
2. The section-to-response join: `api_requests.response_for_section` answers the response that holds the
   container a section names, through the place the section names first and the entry the run read. The
   join states no second path rule, and it refuses a section the run read no response for.
3. Each parse method runs over the response that holds its container, so the marks and the rows it
   produces name entries inside that response.
4. The report position and the source name for a path 2 run: the report row names the response that holds
   the entry, with the line inside it, and the place a section names is stated once, so the same content
   agrees with path 1 except for the source. For content that holds no fact from §4, the agreement reaches
   the bytes the run writes.
5. The predefined read: no container table row names a built-in container, so the run runs no parse method
   over a predefined response. `container_coverage.is_predefined` answers a definitions read through the place
   the declared path names, as well as through the walk, so a read inside the built-in place names no finding
   and no entry row in both shapes the shape rule accepts, and the header counts the built-in entry. The join
   reports nothing for a definitions read, because the join reads the row set and a definitions read names none.
6. No test calls a network: every response is handed by an injected producer, as `tests/test_source_fetch.py`
   does, and the committed response set is read through it.
7. The unit join (`docs/API_CONVERSION_PATH.md` §3): the run's unit set is read through `unit_manifest.units`,
   and the fact path 2 adds is the scope the run read for a unit. A unit the join answers no entry for, and an
   index entry the run read no rows for, are findings the join reports as data rows.
8. The entry point and the run view (`docs/API_CONVERSION_PATH.md` §6): the entry point decides the run order
   and the cross-response join, and the run view answers the entry protocol through the ledger that holds the
   entry. Both entry points call the same run sequence. F11.1: the selection argument is the shared set, and a
   selection that names no unit is an argument error on a run, the shape `--path` already states.
9. The entry a membership list names and the run read as its own scope: the run reads that entry twice and keeps
   both answers, so each response records its own rows and writes its own block, and the gate reads the two sets
   as agreeing.
10. The targeted read set (F11.2, `docs/MULTI_RUN_CODEBASE.md` §2 rule 3): the entry point reads the read set and
    the name set through `api_requests`, so a targeted run reads the same membership responses as a run that
    declares no selection and reads entries only for the names the name rule states for the selection. A name the
    selection excludes is not an index entry, so the join reports no finding for it, and the record names no
    response for it.
11. The bytes a targeted run writes for the unit it selects (F11.3, `docs/MULTI_RUN_CODEBASE.md` §2 rule 6): for
   content that names no read-through name, the unit's `.tf` bytes and the printed form of its site row are the same
   for a targeted run and for a full run, measured on the committed response set for one unit both ways. The
   read-through exception is `tests/test_data_blocks.py`'s rule, so this group states no read-through rule of its
   own: it pins that the committed content answers nothing for either run. The printed form is measured as agreement
   on absence, because no unit on the committed response set names a value.

Every response is read through `source_fetch.fetch` with an injected producer, so the wrapper decision, the
origin, and the line map are the ones the run holds. No pin reads a response as a file, because the wrapper
decision belongs to the request that produced it. The predefined content is held by `tests/conftest.py`, with the
response shape built there, because two modules read it (§1.1).
"""

import argparse
import ast
import inspect
import re
import xml.etree.ElementTree as ET

import pytest

import api_requests
import api_to_terraform
import container_coverage
import entry_coverage
import naming
import ownership
import panorama_to_terraform
import provenance
import sanity_checks
import site_data
import source_fetch
import unit_manifest
import write_path
from conftest import (
    PREDEFINED_ENTRY_BODY,
    PREDEFINED_PLACE_BODY,
    RESPONSES_DIR,
    SRC_DIR,
    TESTS_DIR,
    api_producer,
    per_scope_response,
    run_pipeline,
    tf_bytes,
    tf_files,
    written_bytes,
)

HOST = "panorama.test"

# The two scope places the run read, in the per-scope shape F5.4 states: `result` holds the one element the
# path names. Each response holds one membership list, so the index reads its set from these responses, and
# one address entry inside a scope entry, so a report row is read inside a response rather than in a tree
# built from two responses. The same address name in both responses, at two different lines, is what the pin
# that names the source reads. `data-entry` is a container no table row covers, so the scan has a position to
# name, and `Unassigned-DG` lists no name, so the index makes no entry for it.
DEVICE_GROUP = (
    '<entry name="Office-FW">\n'
    '<devices><entry name="fw-1.example.com" /></devices>\n'
    "<address>\n"
    '<entry name="Web-Server-1"><ip-netmask>10.0.0.7</ip-netmask></entry>\n'
    "</address>\n"
    "<data-entry>\n"
    '<entry name="asset-owner"><field><member>owner</member></field></entry>\n'
    "</data-entry>\n"
    "</entry>\n"
    '<entry name="Unassigned-DG" />\n'
)
TEMPLATES = (
    '<entry name="HQ-Networks">\n'
    "<description>the stack applies this template</description>\n"
    '<devices><entry name="fw-1.example.com" /></devices>\n'
    "<address>\n"
    '<entry name="Web-Server-1"><ip-netmask>10.0.0.9</ip-netmask></entry>\n'
    "</address>\n"
    "</entry>\n"
)

# The same scope entries as responses for the entries themselves, which the run reads as its own sources.
ENTRY_OFFICE_FW = (
    '<entry name="Office-FW">\n'
    '<devices><entry name="fw-1.example.com" /></devices>\n'
    "<address>\n"
    '<entry name="Web-Server-1"><ip-netmask>10.0.0.7</ip-netmask></entry>\n'
    "</address>\n"
    "</entry>\n"
)
ENTRY_HQ_NETWORKS = (
    '<entry name="HQ-Networks">\n'
    '<devices><entry name="fw-1.example.com" /></devices>\n'
    "<address>\n"
    '<entry name="Web-Server-1"><ip-netmask>10.0.0.9</ip-netmask></entry>\n'
    "</address>\n"
    "</entry>\n"
)

PLACES = {"device-group": DEVICE_GROUP, "templates": TEMPLATES}
ENTRIES = {"device-group/entry/Office-FW": ENTRY_OFFICE_FW, "templates/entry/HQ-Networks": ENTRY_HQ_NETWORKS}
READ = ("device-group/entry/devices", "templates/entry/devices")

# The same content as a whole-config export, so path 1 and path 2 read the same entries and the two reports
# can only disagree on the source they name (`docs/API_CONVERSION_PATH.md` §5).
SAME_CONTENT_EXPORT = (
    '<?xml version="1.0"?>\n<response type="success" code="0">\n<result>\n<config>\n<panorama>\n'
    + "<device-group>\n"
    + DEVICE_GROUP
    + "</device-group>\n</panorama>\n</config>\n</result>\n</response>\n"
).encode()

# The content the byte-agreement pin reads: two scope entries, `Office-FW` in `device-group` and
# `HQ-Networks` in `templates`, each with one address object, and nothing else. The content states no membership
# list, so path 2 reads one response per place and each entry is read once. With a membership list the index
# names the entry as its own scope, the run reads the entry as a second response, and the same address is then
# written in two blocks with `_2` names, so the two paths would not write the same bytes.
AGREEMENT = {
    "device-group": '<entry name="Office-FW">\n<address>\n'
    '<entry name="10.0.0.7"><ip-netmask>10.0.0.7</ip-netmask></entry>\n</address>\n</entry>\n',
    "templates": '<entry name="HQ-Networks">\n<address>\n'
    '<entry name="10.0.0.9"><ip-netmask>10.0.0.9</ip-netmask></entry>\n</address>\n</entry>\n',
}
AGREEMENT_EXPORT = (
    '<?xml version="1.0"?>\n<response type="success" code="0">\n<result>\n<config>\n<panorama>\n'
    + "".join(f"<{place}>\n{AGREEMENT[place]}</{place}>\n" for place in sorted(AGREEMENT))
    + "</panorama>\n</config>\n</result>\n</response>\n"
).encode()

# The same two scope entries with a membership list in each, so the index names each entry as its own scope and
# the run reads the entry twice: once inside the place response, once as the response its own request made. The
# content above states no membership list, so it cannot measure the entry that is read twice. `MEMBERSHIP_EXPORT`
# is the same content as one whole-config export, so path 1 reads the same entries from one response.
MEMBERSHIP = {
    "device-group": '<entry name="Office-FW">\n<devices><member>HQ-Networks</member></devices>\n<address>\n'
    '<entry name="10.0.0.7"><ip-netmask>10.0.0.7</ip-netmask></entry>\n</address>\n</entry>\n',
    "templates": '<entry name="HQ-Networks">\n<devices><member>Office-FW</member></devices>\n<address>\n'
    '<entry name="10.0.0.9"><ip-netmask>10.0.0.9</ip-netmask></entry>\n</address>\n</entry>\n',
}
MEMBERSHIP_EXPORT = (
    '<?xml version="1.0"?>\n<response type="success" code="0">\n<result>\n<config>\n<panorama>\n'
    + "".join(f"<{place}>\n{MEMBERSHIP[place]}</{place}>\n" for place in sorted(MEMBERSHIP))
    + "</panorama>\n</config>\n</result>\n</response>\n"
).encode()

# The predefined read content, read from `tests/conftest.py` (§1.1): the two shapes the one definition
# validates for the built-in place, the place and one built-in entry inside it.


def _content_tags(body: str) -> set:
    """The element names the content holds, so a pin can state which of the §4 live-only facts it holds none of."""
    return {element.tag for element in ET.fromstring(body).iter()}


def _read(request, body: str, cache_dir):
    """One response, read through the injected producer. No test calls a network."""
    return source_fetch.fetch(request, cache_dir, producer=lambda r, b=body: per_scope_response(r, b))


def _run(request, body: str, cache_dir):
    """The run for one response: the source the door parsed, and the parser built on that source."""
    source = _read(request, body, cache_dir)
    return source, panorama_to_terraform.PanoramaParser(source)


def _membership(cache_dir) -> dict:
    """The tables as the run holds them, read from the responses the run read.

    `api_requests.py` states no merge rule, so the join across responses is the run order's work, stated in
    `api_to_terraform.py` and `docs/API_CONVERSION_PATH.md` §6. Here the tables are only data for the join, so
    the pins read the join against the same responses they parse.
    """
    tables = {}
    for container in sorted(PLACES):
        _, parser = _run(source_fetch.ApiRequest(host=HOST, path=container), PLACES[container], cache_dir)
        for table, values in parser.parse_associations().items():
            for owner, names in values.items():
                tables.setdefault(table, {}).setdefault(owner, []).extend(names)
    return tables


def _index(cache_dir) -> tuple:
    return api_requests.scope_index(HOST, _membership(cache_dir), READ)


def _entry(source, name: str):
    """One entry by name, inside the tree the door parsed."""
    return next(element for element in source.root.iter() if element.get("name") == name)


def _row(ledger, name: str) -> dict:
    """One report row by entry name."""
    return next(row for row in ledger.rows() if row["name"] == name)


# --- 1. one response is one source --------------------------------------------


def test_each_response_keeps_its_own_line_map(tmp_path):
    """AC-1.1: the door records one line map per response, so a report position can only name a line inside
    the response that holds the entry. An element of one response has no line in another's map, so the run
    would need a tree across responses to name one, and the rule is that it builds none.
    """
    source_a, source_b = (
        _read(source_fetch.ApiRequest(host=HOST, path=container), PLACES[container], tmp_path / container)
        for container in sorted(PLACES)
    )
    assert source_a.lines is not source_b.lines, "two maps, not one map for two responses"
    assert source_a.name != source_b.name, "two sources, each named by the request that made it"

    entry_a, entry_b = _entry(source_a, "Web-Server-1"), _entry(source_b, "Web-Server-1")
    assert entry_a is not entry_b, "the two responses hold two entries with the same name"
    assert source_a.line_of(entry_a) == 8, source_a.lines
    assert source_b.line_of(entry_b) == 9, source_b.lines
    assert source_b.line_of(entry_a) is None and source_a.line_of(entry_b) is None, (
        "no line in another response map, so a merged tree cannot name one"
    )


def test_the_parent_walk_answers_within_one_response(tmp_path):
    """AC-1.2: the parent walk, the entry ledger, and the scope walk are keyed on one tree, so each response
    gets its own. A walk built for one response holds no element of another.
    """
    source_a, parser_a = _run(source_fetch.ApiRequest(host=HOST, path="device-group"), DEVICE_GROUP, tmp_path / "a")
    source_b, parser_b = _run(source_fetch.ApiRequest(host=HOST, path="templates"), TEMPLATES, tmp_path / "b")

    assert parser_a.parent_map is not parser_b.parent_map
    assert parser_a.parent_map.get(source_a.root) is None, "the root of one tree has no parent"
    entry_a, entry_b = _entry(source_a, "Web-Server-1"), _entry(source_b, "Web-Server-1")
    assert parser_a.parent_map[entry_a].tag == "address"
    assert parser_b.parent_map[entry_b].tag == "address"
    assert entry_a not in parser_b.parent_map and entry_b not in parser_a.parent_map, "no element of another response"
    assert parser_a.ledger.source is source_a and parser_b.ledger.source is source_b, "one ledger per response"
    assert all(row["source"] == source_a.name for row in parser_a.ledger.rows()), parser_a.ledger.rows()
    assert all(row["source"] == source_b.name for row in parser_b.ledger.rows()), parser_b.ledger.rows()


def test_the_join_answers_one_response_per_section(tmp_path):
    """AC-1.3 and AC-2.1: the join answers one index entry per section, so no section needs a tree built
    across responses, and `api_requests.py` keeps no parser of its own.
    """
    index = _index(tmp_path)
    assert len({entry.path for entry in index}) == len(index), "one entry per scope, so one answer per section"

    for row in container_coverage.CONTAINER_TABLE:
        place = api_requests.list_container(row.path)
        if place not in PLACES:
            continue
        answered = api_requests.response_for_section(row.path, index)
        assert answered.container == place and answered.level == api_requests.CONTAINER_LEVEL, (row.path, answered)

    # The same section inside the entry the run read joins to that entry, so a row has one answer: the
    # response the run read for the scope that holds its container.
    answered = api_requests.response_for_section("device-group/entry/address", index, name="Office-FW")
    assert answered.path == "device-group/entry/Office-FW" and answered.level == api_requests.ENTRY_LEVEL, answered
    for name in ("parse", "parse_bytes", "element_from_line", "merge", "merge_membership", "join_tables"):
        assert not hasattr(api_requests, name), "the join keeps no parser and states no merge rule"


# --- 2. the section-to-response join ------------------------------------------


def test_a_section_that_names_no_scope_is_refused(tmp_path):
    """AC-2.3: a table row that names only a container names no scope, so the run reads it inside the
    response for the scope that holds it, and the join has no scope to answer.
    """
    index = _index(tmp_path)
    row = entry_coverage.covering_row("address")
    assert row is not None and row.path == "address", "the general row names no scope segment"
    with pytest.raises(ValueError) as excinfo:
        api_requests.response_for_section(row.path, index)
    message = str(excinfo.value)
    assert "does not name a place" in message and "address" in message, message


def test_the_join_refuses_a_section_inside_an_entry_the_run_read_no_response_for(tmp_path):
    """AC-2.3: the index reads its set from the membership responses, so an entry that lists no name gains no
    entry and the run read no response for it. The join refuses the section inside it rather than guessing a
    response, and answers the same section through the place the run did read.
    """
    index = _index(tmp_path)
    assert not any(entry.name == "Unassigned-DG" for entry in index), "the entry lists no name"
    with pytest.raises(ValueError) as excinfo:
        api_requests.response_for_section("device-group/entry/data-entry", index, name="Unassigned-DG")
    message = str(excinfo.value)
    assert "no entry for" in message and "device-group/entry/Unassigned-DG" in message, message

    answered = api_requests.response_for_section("device-group/entry/data-entry", index)
    assert answered.path == "device-group" and answered.level == api_requests.CONTAINER_LEVEL, answered


def test_the_join_names_the_response_the_parse_method_runs_over(tmp_path):
    """AC-2.1, AC-2.2 and AC-2.4: the join answers the response for the scope that holds the container a row
    names, so the method named by that row runs over that response, and the report row names the same
    response. `name` is the entry the run read for the row's scope, which the run order states.
    """
    index = _index(tmp_path)

    for container, body in sorted(PLACES.items()):
        request = source_fetch.ApiRequest(host=HOST, path=container)
        source, parser = _run(request, body, tmp_path / "place")
        rows = [
            row
            for row in container_coverage.CONTAINER_TABLE
            if api_requests.list_container(row.path) == container and row.read_via == "pattern"
        ]
        assert rows, "the run needs rows to run a method for"
        for row in rows:
            getattr(parser, row.method)()  # the parse method named by the row, over this response
        for report_row in parser.ledger.rows():
            answered = api_requests.response_for_section(report_row["container"], index)
            assert answered.request.cache_name() == report_row["source"], (report_row, answered)
            assert report_row["container"].split("/")[0] == answered.container, report_row

    # The run read the entry as its own source, so the join answers that source for a section inside it.
    for path, body in sorted(ENTRIES.items()):
        entry = [item for item in index if item.path == path][0]
        source, parser = _run(source_fetch.ApiRequest(host=HOST, path=path), body, tmp_path / "entry")
        assert source.root[0].get("name") == entry.name, "the response holds the entry its request names"
        parser.parse_address_objects()
        for report_row in parser.ledger.rows():
            section = report_row["container"]
            if section in (path.split("/")[0], path):
                continue
            answered = api_requests.response_for_section(section, index, name=entry.name)
            assert answered is entry, (section, answered)
            assert answered.request.cache_name() == report_row["source"], report_row
            row_entry = next(e for e in source.root.iter() if e.get("name") == report_row["name"])
            assert report_row["line"] == source.line_of(row_entry), (
                "the position is the line inside the response that holds the entry the row names"
            )


# --- 3. the parse method runs over one response -------------------------------


def test_a_parse_method_marks_only_the_entries_in_its_own_response(tmp_path):
    """AC-2.4: a method run over one response marks only the entries inside it, because the mark key is the
    element of the tree that was parsed, so a row from another response cannot be read through this ledger.
    """
    source_a, parser_a = _run(source_fetch.ApiRequest(host=HOST, path="device-group"), DEVICE_GROUP, tmp_path / "a")
    source_b, parser_b = _run(source_fetch.ApiRequest(host=HOST, path="templates"), TEMPLATES, tmp_path / "b")
    entry_a, entry_b = _entry(source_a, "Web-Server-1"), _entry(source_b, "Web-Server-1")

    parser_a.parse_address_objects()
    parser_b.parse_address_objects()
    assert parser_a.ledger.marked(entry_a) and parser_b.ledger.marked(entry_b), "each response read its own entries"
    assert not parser_a.ledger.marked(entry_b) and not parser_b.ledger.marked(entry_a), "no mark crosses a response"

    row_a, row_b = _row(parser_a.ledger, "Web-Server-1"), _row(parser_b.ledger, "Web-Server-1")
    assert row_a["source"] == source_a.name and row_b["source"] == source_b.name
    assert row_a["line"] == source_a.line_of(entry_a) and row_b["line"] == source_b.line_of(entry_b)
    assert row_a["fields"] == row_b["fields"], (row_a["fields"], row_b["fields"])
    assert row_a["fields"], "the same method read the same fields in both responses"
    assert row_a["container"] == "device-group/entry/address" and row_b["container"] == "templates/entry/address", (
        row_a["container"],
        row_b["container"],
        "the same container inside each response",
    )


def test_the_same_name_in_two_responses_gives_two_rows_naming_two_sources(tmp_path):
    """AC-3.3: one name in two responses is two entries, so the run holds two rows, each naming the response
    that holds it with the line inside it. A merged tree would name one source and one line for both.
    """
    source_a, parser_a = _run(source_fetch.ApiRequest(host=HOST, path="device-group"), DEVICE_GROUP, tmp_path / "a")
    source_b, parser_b = _run(source_fetch.ApiRequest(host=HOST, path="templates"), TEMPLATES, tmp_path / "b")
    parser_a.parse_address_objects()
    parser_b.parse_address_objects()

    rows = [row for row in parser_a.ledger.rows() + parser_b.ledger.rows() if row["name"] == "Web-Server-1"]
    assert len(rows) == 2, rows
    assert {row["source"] for row in rows} == {source_a.name, source_b.name}, rows
    assert len({row["line"] for row in rows}) == 2, "two lines, read from two maps"

    index = _index(tmp_path)
    for row in rows:
        scope = row["device_group"] or row["template"]
        assert scope in ("Office-FW", "HQ-Networks"), "the row names the scope entry it sits in"
        place = row["container"].split("/")[0]
        assert place in PLACES, row
        # The run read the place for both rows, so `name` is the place read and the join answers the place.
        # The row from the run that read the entry names the entry response, which the join pin reads.
        answered = api_requests.response_for_section(row["container"], index)
        assert answered.path == place and answered.level == api_requests.CONTAINER_LEVEL, (row, answered)
        assert answered.request.cache_name() == row["source"], "the join answers the row source"
        assert row["line"] > 3, "the position is a line inside the response, not the wrapper line"


def test_the_report_position_is_the_line_inside_the_response(tmp_path):
    """AC-3.2: the position a report line names is the line inside the response that holds the entry, read
    through that response's own map, in the shape `container_coverage.position_part` states.
    """
    source, parser = _run(source_fetch.ApiRequest(host=HOST, path="device-group"), DEVICE_GROUP, tmp_path / "run")
    findings = container_coverage.scan(source, parser.parent_map)
    assert len(findings) == 1, (findings, "the scan reads one response, so it names one position")
    finding = findings[0]
    container = next(element for element in source.root.iter() if element.tag == "data-entry")
    assert finding.path == "device-group/entry/data-entry", finding
    assert finding.line == source.line_of(container) == 10, source.lines
    assert container_coverage.position_phrase(finding) == "line 10", finding

    entry = _entry(source, "asset-owner")
    assert _row(parser.ledger, "asset-owner")["line"] == source.line_of(entry) == 11, source.lines

    section = container_coverage.render_section(findings, source.name)
    assert section.splitlines()[1] == f"{container_coverage.SOURCE_LABEL} {source.name}", section
    assert str(source.origin.path) not in section, "the report names the source by its name, not its path"
    assert "line 10" in section, section


# --- 4. the report row names its source ---------------------------------------


def test_a_path_2_report_row_names_the_response_by_name_only(tmp_path):
    """AC-3.1: the row's source is the response name, which is the key-free request identity, and it holds no
    path. The printed entry line names the position and the identity, so the source stays row data and the
    report value, which `tests/test_entry_coverage.py::test_every_row_names_the_source_that_holds_the_entry`
    already pins.
    """
    index = _index(tmp_path)
    for container, body in sorted(PLACES.items()):
        request = source_fetch.ApiRequest(host=HOST, path=container)
        source, parser = _run(request, body, tmp_path / "row")
        rows = parser.ledger.rows()
        assert rows, "the rule needs rows to read"
        for row in rows:
            assert row["source"] == source.name == request.cache_name(), row
            assert "/" not in row["source"], "the report value, not a path"
            assert api_requests.response_for_section(row["container"], index).request.cache_name() == row["source"], (
                "the row names the response the join answers"
            )
            assert row["source"] not in entry_coverage.entry_line(row), row
            assert f"line {row['line']:>4}" in entry_coverage.entry_line(row), row


def test_the_same_content_agrees_with_path_1_except_for_the_source(tmp_path):
    """AC-3.4: the report names the place a section names once, so the same content read as a per-scope place
    response and as a whole-config export names the same container path. The two reports disagree only on the
    source they name, which is the rule `docs/API_CONVERSION_PATH.md` §5 states.
    """
    export = source_fetch.fetch(
        source_fetch.ApiRequest(host=HOST), tmp_path / "path1", producer=lambda r: SAME_CONTENT_EXPORT
    )
    per_scope, parser = _run(source_fetch.ApiRequest(host=HOST, path="device-group"), DEVICE_GROUP, tmp_path / "path2")
    export_parser = panorama_to_terraform.PanoramaParser(export)
    for one in (export_parser, parser):
        one.parse_device_groups()
        one.parse_associations()

    fields = ("container", "name", "destination", "detail", "fields", "device_group")
    path1 = {tuple(row[field] for field in fields) for row in export_parser.ledger.rows()}
    path2 = {tuple(row[field] for field in fields) for row in parser.ledger.rows()}
    assert path1 == path2, (sorted(path1), sorted(path2))
    assert "device-group/entry/address" in {row["container"] for row in parser.ledger.rows()}, (
        "the place is stated once, not twice"
    )
    assert {row["source"] for row in export_parser.ledger.rows()} == {export.name}
    assert {row["source"] for row in parser.ledger.rows()} == {per_scope.name}
    assert export.name != per_scope.name, "the only disagreement is the source the report names"
    assert parser.source.is_per_scope and not export.is_per_scope, "one is a scope read, one is not"


def _agreement_producer(request, key=None, insecure=False):
    """The content above, handed by an injected producer: one response per place, and the whole-config export
    for a request that names no path. No test calls a network, so path 2 reads only this content and path 1
    reads the same content as one response.
    """
    if request.path == "":
        return AGREEMENT_EXPORT
    return per_scope_response(request, AGREEMENT[request.path]) if request.path in AGREEMENT else None


def _path2_run(argv, producer, monkeypatch) -> tuple:
    """A path 2 run, and the parts and the index the entry point built for it.

    `run()` answers only the exit code, and the values a report row carries for the captured object are recorded
    by the emission, so a pin that reads a report row reads the parts the run itself built, after the run. The
    hook is the shape `run_pipeline` uses for path 1's parser. `conftest.path2_run` cannot serve here, because it
    forces the producer for the committed response set, and this pin reads content that is not in that set.
    """
    captured = {}
    original = api_to_terraform.run_order

    def hooked(*args, **kwargs):
        result = original(*args, **kwargs)
        captured["parts"], captured["index"] = result
        return result

    monkeypatch.setattr(api_to_terraform, "run_order", hooked)
    return api_to_terraform.run(argv, producer), captured["parts"], captured["index"]


def test_content_with_no_live_only_fact_writes_the_same_tf_bytes_as_path_1(tmp_path, monkeypatch):
    """Path 2 writes the same `.tf` bytes as path 1 for content that holds no fact from
    `docs/API_CONVERSION_PATH.md` §4.

    Content: `AGREEMENT` and `AGREEMENT_EXPORT`, named above, read through `_agreement_producer` as one
    whole-config response for path 1 and as one response per place for path 2. The entries are `Office-FW` in
    `device-group` with the address `10.0.0.7`, and `HQ-Networks` in `templates` with the address `10.0.0.9`.

    Why the content holds no §4 fact, measured on the content:

    - Rulebase per rule, and rule position: no `rulebase` element, so no rule and no rule to order.
    - Device serial: no `device` element, so no device entry.
    - Per-device template variable override: no `variable` element.
    - Built-in name table: no `predefined` element.

    So every fact the two reports can hold comes from the same content, and the pin measures that they agree on
    it. The rows agree on every field, and the two that differ are the source each row names and the line inside
    that source, because a position is a line inside the response that holds the entry (§2.4). Path 2 reads no
    network here: every response it reads is this content. The output is read the way the gate reads it, through
    `tf_files`, and the reports through the ledgers.
    """
    out1, cache1 = tmp_path / "path1", tmp_path / "cache1"
    args, argv = _run_args(tmp_path)

    # Why the content holds no §4 fact, measured on the elements it holds in both shapes it is read in: no
    # rulebase, so no rule and no rule to order; no device entry; no variable; no predefined.
    facts = {"rulebase", "device", "variable", "predefined"}
    held = _content_tags(AGREEMENT_EXPORT.decode())
    for place, body in sorted(AGREEMENT.items()):
        held |= _content_tags(per_scope_response(source_fetch.ApiRequest(host=HOST, path=place), body).decode())
    assert not held & facts, (sorted(held), "the content holds a §4 fact")

    monkeypatch.setenv(source_fetch.API_KEY_ENV, "test-key")
    monkeypatch.setattr(source_fetch, "network_producer", _agreement_producer)
    path1 = run_pipeline(
        panorama_to_terraform, None, out1, ("--source", "api", "--host", HOST, "--cache-dir", str(cache1))
    )
    assert path1 is not None, "path 1 refused the content"
    code, parts, index = _path2_run(argv, _agreement_producer, monkeypatch)
    assert code == 0, "the path 2 run"

    # Path 2 read one response per place, and every response it read is this content. Both runs read through
    # `fetch`, so the response landed in the cache the run wrote, never as a file in the corpus.
    assert len(parts) == len(AGREEMENT), (parts, "one response per place")
    assert all(part.request.path in AGREEMENT for part in parts), "path 2 read a response outside the content"
    assert not path1.source.is_per_scope and all(part.source.is_per_scope for part in parts), (
        "path 1 read one response, path 2 one per place"
    )
    assert path1.source.origin.path.parent == cache1 and all(
        part.source.origin.path.parent == tmp_path / "cache" for part in parts
    ), (path1.source.origin.path, [part.source.origin.path for part in parts], "read through fetch")

    # The bytes, read the way the gate reads them.
    files1, files2 = tf_files(out1), tf_files(args.output_dir)
    assert files1 and files1 == files2, (sorted(files1), sorted(files2), "the same .tf bytes")

    # The reports, read through the ledgers the runs wrote them from.
    rows1 = sorted(path1.ledger.rows(), key=lambda row: (row["container"], row["name"]))
    view = _view(parts)
    rows2 = sorted(view.rows(), key=lambda row: (row["container"], row["name"]))
    assert rows1 and len(rows1) == len(rows2), (rows1, rows2, "the pin needs rows to read")
    # The pin read the two row sets as the same set, so `strict` states that it does.
    for row1, row2 in zip(rows1, rows2, strict=True):
        assert {key for key in row1 if row1[key] != row2.get(key)} == {"line", "source"}, (row1, row2)
        # The printed entry line agrees apart from the position, so the report differs only on the source.
        line1, line2 = f"line {row1['line']:>4}", f"line {row2['line']:>4}"
        assert entry_coverage.entry_line(row1).replace(line1, "line") == entry_coverage.entry_line(row2).replace(
            line2, "line"
        ), (row1, row2)
    assert {row["source"] for row in rows1}.isdisjoint({row["source"] for row in rows2}), (
        "the two read sets name no source in common"
    )

    # The gate reads the same file set for both runs and reports nothing for either. `request_set` is the one
    # rule the two cannot answer the same way, because path 1 holds no index: the index is the run order's
    # decision, and the gate reports a rule it has no index for as NOT RUN.
    gate1 = sanity_checks.run_checks(out1, run_terraform=False, ledger=path1.ledger)
    gate2 = sanity_checks.run_checks(args.output_dir, run_terraform=False, ledger=view, index=index)
    assert (gate1.file_count, gate1.data_file_count, gate1.resource_count) == (
        gate2.file_count,
        gate2.data_file_count,
        gate2.resource_count,
    ), (gate1, gate2)
    assert not [finding for c in gate1.checks + gate2.checks for finding in c.findings], (gate1.checks, gate2.checks)
    results1, results2 = {c.check: c.result for c in gate1.checks}, {c.check: c.result for c in gate2.checks}
    # Green means no finding for either run. The results that are not PASS are the two checks this pin did not ask
    # for, the plan check and the rule set, and each is NOT RUN for both runs, so the agreement is measured over the
    # checks the gate ran.
    command_checks = ("tflint", "terraform")
    assert all(result == "PASS" for name, result in results2.items() if name not in command_checks), (
        results1,
        results2,
    )
    assert all(results1[name] == results2[name] == sanity_checks.NOT_RUN for name in command_checks), (
        results1,
        results2,
        "this pin reads the gate without running a command",
    )
    assert {name: value for name, value in results1.items() if name != "request_set"} == {
        name: value for name, value in results2.items() if name != "request_set"
    }, (results1, results2)
    assert results1["request_set"] == sanity_checks.NOT_RUN and results2["request_set"] == "PASS", (
        results1,
        results2,
        "path 1 holds no index to answer the join with",
    )
    assert len(index) == len(AGREEMENT), "the index reads the places the content names"


# --- 5. the predefined read ---------------------------------------------------


def test_no_table_row_names_a_builtin_container(tmp_path):
    """AC-4.1: no container table row names a built-in container, so the run runs no parse method over a
    predefined response, and the entry report names no row for a built-in entry.
    """
    assert not [
        row for row in container_coverage.CONTAINER_TABLE if api_requests.list_container(row.path) == "predefined"
    ], "no row to run a method for"
    assert "predefined" in container_coverage.SCOPE_PATH_ROOTS
    assert "predefined" not in container_coverage.SCOPE_CONTAINERS, "a built-in section is a place, not a scope"

    _, parser = _run(source_fetch.ApiRequest(host=HOST, path="predefined"), PREDEFINED_PLACE_BODY, tmp_path / "place")
    assert parser.ledger.rows() == [], "the report names no row for a built-in entry"
    assert parser.ledger.predefined_total() == 1, "the ledger still counts the built-in entry"
    assert container_coverage.scan(parser.source, parser.parent_map) == [], (
        "the response holds the predefined element, so the built-in rule reaches it"
    )


def test_the_join_answers_no_response_for_a_builtin_place(tmp_path):
    """AC-4.3: the index reads its set from the membership responses, and no membership row reads
    `predefined`, so the join answers no response for a built-in place. The run can read a predefined scope as
    its declared scope, and the fact the built-in name table needs stays a live fact
    (`docs/API_CONVERSION_PATH.md` §4, `backlog.md`).
    """
    index = _index(tmp_path)
    assert not any(entry.container == "predefined" for entry in index), "the index read no built-in scope"
    assert container_coverage.is_scope_path("predefined"), "the shape rule still validates it as a place"
    with pytest.raises(ValueError) as excinfo:
        api_requests.response_for_section("predefined", index)
    message = str(excinfo.value)
    assert "no entry for" in message and "predefined" in message, message


def test_a_predefined_entry_read_names_no_finding(tmp_path):
    """F8.1 AC-3: `is_predefined` answers a definitions read through the place the declared path names, so an
    entry read inside the built-in place names no finding and the report names no coverage section for it. The
    pin that holds the walk for a file source is unchanged, and the place read is answered by the walk because
    its response holds the element.
    """
    source, parser = _run(
        source_fetch.ApiRequest(host=HOST, path="predefined/entry/url-list"), PREDEFINED_ENTRY_BODY, tmp_path / "entry"
    )
    assert container_coverage.scan(source, parser.parent_map) == [], (
        "the tree holds no element tagged with the place, so the declared place is what answers the fact"
    )
    assert source.scope_container == container_coverage.PREDEFINED_PLACE, "the fact the rule reads is the place"


def test_a_predefined_entry_read_names_no_row_and_the_header_counts_it(tmp_path):
    """F8.1 AC-4: the entry report rule names no row for a definitions entry, so an entry read inside the
    built-in place names no row, the header counts it through `predefined_total`, and it enters no gap count.
    The destination kinds are unchanged: `unaccounted` is the answer for an entry no row covers, and a
    definitions entry names no row, so it never reaches that answer.
    """
    _, parser = _run(
        source_fetch.ApiRequest(host=HOST, path="predefined/entry/url-list"),
        PREDEFINED_ENTRY_BODY,
        tmp_path / "entry read",
    )
    assert parser.ledger.rows() == [], "the report names no row for a definitions entry"
    assert parser.ledger.predefined_total() == 1, "the header counts it, as the file source and the place read do"
    assert parser.ledger.gap_count() == 0, "no row to be a gap"
    assert sum(parser.ledger.counts().values()) == 0, "no destination kind counts it"


def test_the_join_reports_nothing_for_a_definitions_read(tmp_path):
    """F8.1 AC-6: the join states no rule that a source is definitions, so it reports nothing for a definitions
    read: the join reads the row set, and a definitions read names no row, so it gains no unit, the join answers
    no pair for it, and no finding names its response. The pin that holds the direction,
    `test_a_unit_the_index_made_no_request_for_is_a_finding`, keeps the whole-config instance.
    """
    index = _index(tmp_path)
    source, parser = _run(
        source_fetch.ApiRequest(host=HOST, path="predefined/entry/url-list"),
        PREDEFINED_ENTRY_BODY,
        tmp_path / "entry read",
    )
    assert parser.ledger.rows() == [], "the join needs a row to build a unit from"
    assert unit_manifest.units(parser.ledger) == [], "no row, so no unit"
    assert api_requests.join_units(index, parser.ledger) == []
    findings = api_requests.unit_findings(index, parser.ledger)
    assert [row for row in findings if row[1] is None] == [], "no unit of this read to report"
    assert all(entry is not None for _facts, entry in findings), "every finding names an index entry, not this read"
    assert not any(entry.request.cache_name() == source.name for _facts, entry in findings), (
        "the join names no response for a read that holds no row"
    )


# --- 6. the committed set, read one response at a time ------------------------


def test_the_committed_response_is_one_source_and_names_itself_in_the_report(tmp_path):
    """AC-5.2: the committed per-scope response is one source, read through the injected producer, and the
    report rows for it name that response with the line inside it. The response name is the key-free request
    identity the file is named by, so the report names no path and no credential.
    """
    request = source_fetch.ApiRequest(host=HOST, path="device-group")
    committed = (RESPONSES_DIR / request.cache_name()).read_bytes()
    assert "device-group" in committed.decode("utf-8"), "the committed response is the device-group read"

    source = source_fetch.fetch(request, tmp_path, producer=lambda r: committed)
    parser = panorama_to_terraform.PanoramaParser(source)
    index = api_requests.scope_index(HOST, parser.parse_associations(), ("device-group/entry/devices",))
    rows = parser.ledger.rows()
    assert rows, "the rule needs rows to read"
    for row in rows:
        assert row["source"] == source.name == request.cache_name(), row
        assert "/" not in row["source"], "the report value, not a path"
        assert api_requests.response_for_section(row["container"], index).request.cache_name() == row["source"]
        assert row["line"] and row["line"] > 3, "the position is a line inside the response, not the wrapper"

    # The line the report names is the line inside the committed bytes, which a reader can reopen.
    entry = _entry(source, "Office-FW")
    lines = committed.decode("utf-8").splitlines()
    assert source.line_of(entry) == lines.index('  <entry name="Office-FW">') + 1, source.lines
    assert api_requests.response_for_section("device-group", index).request.cache_name() == source.name
    assert (RESPONSES_DIR / source.name).is_file(), "the origin names the committed response"


def test_no_test_in_this_file_calls_a_network_producer(tmp_path, monkeypatch):
    """AC-5.1: every response in this file is handed by an injected producer, so Goal 1 holds for the run over
    many sources.
    """
    monkeypatch.setattr(
        source_fetch,
        "network_producer",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("the run called the network")),
    )
    for container, body in sorted(PLACES.items()):
        source = _read(source_fetch.ApiRequest(host=HOST, path=container), body, tmp_path / container)
        assert source.origin.kind == "api", (container, "the door named a fetched source")
    for path, body in sorted(ENTRIES.items()):
        source = _read(source_fetch.ApiRequest(host=HOST, path=path), body, tmp_path / "entry reads")
        assert source.origin.kind == "api", (path, "the door named a fetched source")
    committed = source_fetch.fetch(
        source_fetch.ApiRequest(host=HOST, path="device-group"),
        tmp_path / "committed",
        producer=lambda r: (RESPONSES_DIR / r.cache_name()).read_bytes(),
    )
    assert committed.origin.kind == "api"
    assert (RESPONSES_DIR / committed.origin.name).is_file(), "the origin names the committed response"


# --- 7. the unit join -----------------------------------------------------------


def _rows_for(parser, methods: tuple) -> list:
    """Run the parse methods named by the run, over the response that holds its container, and return the rows.

    The join reads the row set through one ledger, because the join is per response (F8.5), so a pin reads the
    join against one run's ledger.
    """
    for method in methods:
        getattr(parser, method)()
    return parser.ledger.rows()


def test_the_unit_join_answers_the_scope_the_run_read_for_a_unit(tmp_path):
    """AC-1.3, AC-2.1, AC-2.2 and AC-2.3: the join reads the unit set through `unit_manifest.units` and
    answers, for each unit, the index entry whose request made the response that unit's rows name. The same
    content read as a place and as an entry gives two answers for the same unit, because the fact path 2 adds
    is the scope the run read, not the scope the unit sits in.
    """
    index = _index(tmp_path)
    place_source, place_parser = _run(
        source_fetch.ApiRequest(host=HOST, path="device-group"), DEVICE_GROUP, tmp_path / "place read"
    )
    place_rows = _rows_for(place_parser, ("parse_device_groups", "parse_associations"))
    assert place_rows, "the join needs rows to read"
    assert {row[ownership.SOURCE_FIELD] for row in place_rows} == {place_source.name}, (
        "each row names the response the run read"
    )
    place_pairs = api_requests.join_units(index, place_parser.ledger)
    assert [facts for facts, _entry in place_pairs] == unit_manifest.units(place_parser.ledger), (
        "the join reads the unit set through the one rule"
    )

    entry_source, entry_parser = _run(
        source_fetch.ApiRequest(host=HOST, path="device-group/entry/Office-FW"),
        ENTRY_OFFICE_FW,
        tmp_path / "entry read",
    )
    entry_rows = _rows_for(entry_parser, ("parse_device_groups", "parse_address_objects"))
    assert entry_rows, "the join needs rows to read"
    assert {row[ownership.SOURCE_FIELD] for row in entry_rows} == {entry_source.name}, (
        "the same content, named by a different request"
    )
    entry_pairs = api_requests.join_units(index, entry_parser.ledger)
    assert [facts for facts, _entry in entry_pairs] == unit_manifest.units(entry_parser.ledger), entry_pairs

    # The two runs read the same content, so the units they share are the same units, and the join answers a
    # shared unit with the response the run read: the place response for one run, the entry response for the
    # other. That answer is the fact path 1 cannot state.
    shared = sorted(set(unit_manifest.units(place_parser.ledger)) & set(unit_manifest.units(entry_parser.ledger)))
    assert shared, "the two runs share a unit"
    for facts in shared:
        assert [entry.path for row_facts, entry in place_pairs if row_facts == facts] == ["device-group"], (
            facts,
            place_pairs,
        )
        assert [entry.path for row_facts, entry in entry_pairs if row_facts == facts] == [
            "device-group/entry/Office-FW"
        ], (facts, entry_pairs)

    # The join reads the row's source field and the name rule in `source_fetch`, so the answer is the response
    # name the row carries, not a name the join states.
    for facts, answered in place_pairs:
        names = {row[ownership.SOURCE_FIELD] for row in place_rows if unit_manifest.facts_of(row) == facts}
        assert names == {answered.request.cache_name()}, (facts, names, answered)
    for facts, answered in entry_pairs:
        names = {row[ownership.SOURCE_FIELD] for row in entry_rows if unit_manifest.facts_of(row) == facts}
        assert names == {answered.request.cache_name()}, (facts, names, answered)


def test_a_unit_the_index_made_no_request_for_is_a_finding(tmp_path):
    """AC-3.1, the first direction: a unit the join answers no entry for, because the response its rows name
    is one the index made no request for. A whole-config response holds no scope entry, so the run read the
    unit through a response the index has no entry for. A definitions read is no longer an instance: the join
    reads the row set and a definitions read names no row, so the join reports nothing for it, which the pin
    `test_the_join_reports_nothing_for_a_definitions_read` holds.
    """
    index = _index(tmp_path)

    export_source = source_fetch.fetch(
        source_fetch.ApiRequest(host=HOST), tmp_path / "export read", producer=lambda r: SAME_CONTENT_EXPORT
    )
    export_parser = panorama_to_terraform.PanoramaParser(export_source)
    export_rows = _rows_for(export_parser, ("parse_device_groups", "parse_associations"))
    assert export_rows, "the join needs rows to read"
    assert not export_source.is_per_scope, "the whole-config shape holds no scope entry"

    # The response the rows name is not one the index made a request for, so the join answers no pair and every
    # unit it shows is a finding.
    assert not api_requests.join_units(index, export_parser.ledger), "the join answers nothing here"
    unit_findings = [row for row in api_requests.unit_findings(index, export_parser.ledger) if row[1] is None]
    assert [facts for facts, _entry in unit_findings] == unit_manifest.units(export_parser.ledger), unit_findings

    # The same content read as a per-scope place is answered, so the direction is about the request the run
    # read, not about the content.
    _, place_parser = _run(
        source_fetch.ApiRequest(host=HOST, path="device-group"), DEVICE_GROUP, tmp_path / "place read"
    )
    _rows_for(place_parser, ("parse_device_groups", "parse_associations"))
    assert api_requests.join_units(index, place_parser.ledger), "the join answers this unit"
    assert [row for row in api_requests.unit_findings(index, place_parser.ledger) if row[1] is None] == []


def test_an_index_entry_the_run_read_no_rows_for_is_a_finding(tmp_path):
    """AC-3.2, the second direction: an index entry the run read no rows for, so no unit answers it. The set
    is read from the membership responses, so an entry the index names can exist while the run read no row for
    it.
    """
    index = _index(tmp_path)
    source, parser = _run(
        source_fetch.ApiRequest(host=HOST, path="device-group"), DEVICE_GROUP, tmp_path / "one response"
    )
    rows = _rows_for(parser, ("parse_device_groups", "parse_associations"))
    assert rows, "the join needs rows to read"

    pairs = api_requests.join_units(index, parser.ledger)
    assert all(entry.path == "device-group" for _facts, entry in pairs), pairs

    findings = api_requests.unit_findings(index, parser.ledger)
    assert all(facts is None for facts, _entry in findings), "the run read rows for every unit it shows"
    answered = {entry.path for _facts, entry in pairs}
    assert [entry.path for _facts, entry in findings] == [
        entry.path for entry in index if entry.path not in answered
    ], findings

    # The join reads the name rule for each entry, so a finding names the entry whose response name the run
    # read no row for. The row set is this run's rows, because the join is per response (F8.5).
    read = {row[ownership.SOURCE_FIELD] for row in rows}
    assert all(entry.request.cache_name() not in read for _facts, entry in findings), findings
    assert read == {entry.request.cache_name() for entry in index if entry.path == "device-group"}, (
        "the run read one response, and that response names one index entry"
    )


def test_the_join_reports_the_findings_as_data_through_the_owners_names():
    """AC-1.2 and AC-3.3: the join names no field of its own and reports no shape of its own. It reads the
    fact order through `unit_manifest` and the field name for the row's source through `ownership`, and it
    builds no row, so the declared row shape and the declared record shape are unchanged by the join.
    """
    source = (SRC_DIR / "api_requests.py").read_text(encoding="utf-8")
    assert "unit_manifest.units(" in source and "unit_manifest.facts_of(" in source, (
        "the join reads the unit rule through its owner"
    )
    assert "ownership.SOURCE_FIELD" in source, "the field name for the row source is read through its owner"
    assert f"'{ownership.SOURCE_FIELD}'" not in source, "the join states no field name of its own"
    for field in unit_manifest.FIELD_ORDER:
        assert f"'{field}'" not in source, (field, "the join adds no field to the declared row shape")
    assert "dict.fromkeys" not in source, "the join builds no row shape of its own"

    # The join reports data rows only: no console line, no writer, no report section, and no unit rule.
    for name in (
        "finding_line",
        "console_line",
        "render",
        "write_file",
        "report_section",
        "check",
        "units",
        "unit_name",
        "named_fact",
        "identity_digest",
        "directory_name",
    ):
        assert not hasattr(api_requests, name), (name, "the join states no rule of this kind")
    for word in ("print(", "CONSOLE_PREFIX", "REPORT", "MANUAL_SETUP"):
        assert word not in source, (word, "the join prints nothing and writes nothing")


# --- 8. the entry point and the run view (F8.9, `docs/API_CONVERSION_PATH.md` §6) ---


def _read_order() -> tuple:
    """The order a run reads these responses: the membership lists in the order `api_requests` names them, read
    as the container that holds each list. Only the places this file holds a response for.
    """
    order = []
    for name in api_requests.membership_lists():
        container = api_requests.list_container(name)
        if container in PLACES and container not in order:
            order.append(container)
    return tuple(order)


def _parts(cache_dir, order: tuple = None) -> list:
    """The responses one run read, as the run holds them: the source the door returned, the request that read
    it, and the parser built on that source. Every response is read through the injected producer, so no test
    calls a network.
    """
    parts = []
    for path in order or _read_order():
        request = source_fetch.ApiRequest(host=HOST, path=path)
        source = _read(request, PLACES[path], cache_dir)
        parts.append(entry_coverage.RunPart(source, request, panorama_to_terraform.PanoramaParser(source)))
    return parts


def _concat_join(values):
    """The join as an argument, stated here so the pin measures what the view delegates to its owners. The
    merge rule is the entry point's decision and `api_requests.py` keeps none, so it is pinned by
    `test_the_entry_point_joins_the_tables_across_the_responses_it_read`.
    """
    if all(isinstance(value, list) for value in values):
        return [item for value in values for item in value]
    return values[-1]


def _producer(bodies: dict = None):
    """A producer that answers the responses this file holds, so a path 2 run can read more than the committed
    set. A request this file holds no response for answers None, the way `conftest.api_producer` does.
    """
    shapes = dict(PLACES, **(ENTRIES if bodies is None else bodies))
    return lambda request: per_scope_response(request, shapes[request.path]) if request.path in shapes else None


def _run_args(tmp_path) -> tuple:
    """The arguments one path 2 run reads, through the entry point's own parser, and the directory it writes to."""
    argv = ["--host", HOST, "--cache-dir", str(tmp_path / "cache"), "--output-dir", str(tmp_path / "out")]
    parser = api_to_terraform.build_parser()
    return parser.parse_args(argv), argv


def _view(parts) -> entry_coverage.RunView:
    """The run view the entry point builds, with the join the entry point supplies."""
    return entry_coverage.RunView(parts, panorama_to_terraform.join_results)


def test_the_run_order_is_the_membership_lists_then_the_index_entries(tmp_path):
    """Criterion 1: the entry point is the only place that states the run order, and the record file the run
    wrote is that order's own statement. `api_requests.py` states no read order and `provenance.py` rule 6 says
    the read order for a path 2 run is the run order's decision, so this pin reads the order through the names
    the owners state and never through a list this file states. The read set is the entry point's read of
    `api_requests.targeted_read_set`, which is the four lists for a run that declares no selection. For a selection
    the entry part reads only the names the name rule states, pinned by group 10.
    """
    args, argv = _run_args(tmp_path)
    parts, index = api_to_terraform.run_order(args, _producer())
    read = tuple(part.request.path for part in parts)

    # The order, read through the owners' names: the container each membership list names, in the order the
    # lists name them, then the entries the index names in index order. Two lists can name one container, and one
    # response is read once, so a container named by two lists enters the order at the first place a list names
    # it, and the entry part holds only the entries the run had not already read.
    named = []
    for name in api_requests.targeted_read_set(args.selection):
        path = api_requests.scope_path(api_requests.list_container(name))
        if path in read and path not in named:
            named.append(path)
    membership = tuple(named)
    containers = tuple(
        entry.path for entry in index if entry.level == api_requests.CONTAINER_LEVEL and entry.path in read
    )
    entries = tuple(entry.path for entry in index if entry.level == api_requests.ENTRY_LEVEL and entry.path in read)
    assert membership and entries, "the run read a membership response and an entry of its own"
    assert len({api_requests.list_container(name) for name in api_requests.membership_lists()}) < len(
        api_requests.membership_lists()
    ), "two lists name one container, so one response is read once"
    assert containers == membership, "the first part of the order is the membership order"
    assert read == membership + entries, (read, "the membership responses first, then the entries")
    assert len(set(read)) == len(read), "one response is read once"

    # The record the run wrote is the order's own statement, read back as data.
    assert api_to_terraform.run(argv, _producer()) == 0
    record = (tmp_path / "out" / provenance.PROVENANCE_FILE).read_text(encoding="utf-8")
    assert [row.cache_entry for row in provenance.parse_records(record)] == [
        part.request.cache_name() for part in parts
    ], "the record names the responses in the order it read them"

    # The order is stated once. The entry point reads it through the owners' names, so it states no path rule,
    # no sort, and no list of paths of its own, and no other module states it. The read set and the name set are
    # `api_requests`' rules, so the entry point reads them through its owner and states no name rule of its own: it
    # passes the selection to `scope_index`, which reads the name set.
    entry_source = (SRC_DIR / "api_to_terraform.py").read_text(encoding="utf-8")
    assert "def run_order" in entry_source, "the order is stated in the entry point"
    for name in ("targeted_read_set", "scope_index", "list_container", "scope_path"):
        assert f"api_requests.{name}(" in entry_source, (name, "the order is read through the owner")
    assert "sorted(" not in entry_source, "the entry point states no sort rule"
    for path in PLACES:
        assert path not in entry_source, (path, "no path of its own")
    for module in ("api_requests.py", "provenance.py", "entry_coverage.py"):
        text = (SRC_DIR / module).read_text(encoding="utf-8")
        assert "run order" in text, (module, "names the order as the entry point's decision")
        assert "def run_order" not in text, (module, "states no read order of its own")


def test_the_entry_point_joins_the_tables_across_the_responses_it_read(tmp_path):
    """Criterion 2: `api_requests.py` keeps no merge rule, so the tables `parse_associations` answers stay per
    response and the entry point is what joins them, in the order it read them. The join names the response each
    fact came from, which path 1 cannot state: the same content read as one whole-config export names one source
    for its facts, and read as per-scope responses names one source per response. One response answers itself
    through the same join, so path 1 is unchanged.
    """
    args, _ = _run_args(tmp_path)
    parts, index = api_to_terraform.run_order(args, _producer())
    view = _view(parts)
    tables = view.parse("parse_associations")

    # Each table answer stays the response's own, in the order the run read them: the join adds no fact a
    # response did not read, and the index reads its set from the joined tables.
    for part in parts:
        for table, owners in part.parser.parse_associations().items():
            for owner, names in owners.items():
                assert tables[table][owner] == names, (part.request.path, table, owner)
    assert api_requests.scope_index(HOST, tables, api_to_terraform.lists_read(parts)) == index, (
        "the joined tables are the set the index reads"
    )
    assert api_to_terraform.lists_read(parts) == tuple(
        name
        for name in api_requests.membership_lists()
        if api_requests.scope_path(api_requests.list_container(name)) in [part.request.path for part in parts]
    ), "the read set is what the entry point decided, not a list the join states"

    # A fact names the response it came from. The same entry name in two responses is two facts, each naming its
    # own response; read as one export the same content names one source for the same name. A whole-config
    # request names no path, so it is read through the door's own producer, not through the path shape.
    export = source_fetch.fetch(
        source_fetch.ApiRequest(host=HOST), tmp_path / "export", producer=lambda r: SAME_CONTENT_EXPORT
    )
    export_parser = panorama_to_terraform.PanoramaParser(export)
    export_parser.parse_address_objects()
    rows = [row for row in view.rows() if row["name"] == "Web-Server-1"]
    assert len(rows) == len(parts), (rows, "one fact per response the run read")
    assert [row["source"] for row in rows] == [part.source.name for part in parts], (
        "the facts name the responses in run order"
    )
    assert len({row["source"] for row in export_parser.ledger.rows()}) == 1, "one export names one source"
    for name in ("merge", "merge_membership", "join_tables", "join_value"):
        assert not hasattr(api_requests, name), (name, "the join keeps no merge rule")

    # One response answers itself, so a path 1 run is unchanged.
    single = _view(parts[:1])
    assert single.parse("parse_associations") == parts[0].parser.parse_associations()
    assert single.rows() == parts[0].ledger().rows()


def test_the_run_sequence_is_stated_once_and_both_entry_points_call_it():
    """Criterion 3: the parse order and the emission order cannot be derived from data, so they live in one
    function that both entry points call. Neither entry point states a parse order or a block builder of its own,
    and the pins that read the sequence read the run function, not `main()`.
    """
    entry_source = (SRC_DIR / "api_to_terraform.py").read_text(encoding="utf-8")
    path1 = inspect.getsource(panorama_to_terraform.main)
    assert "generate_run(" in entry_source and "generate_run(" in path1, (
        "both entry points call the sequence the run function states"
    )

    # Neither entry point states a parse order or a block builder: the run function is the only place that names
    # them. The entry point reads the parser through one method, `parse_associations`, because the index needs the
    # tables the run read, and it holds no order of its own.
    methods = sorted({method for _, method in panorama_to_terraform.PARSE_ORDER})

    def called(text: str) -> list:
        """The parse methods and block builders an entry point calls, read as code so prose does not count."""
        out = set()
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
                if name in methods or str(name).startswith("generate_"):
                    out.add(name)
        return sorted(out)

    assert called(entry_source) == ["generate_run", "parse_associations"], (
        called(entry_source),
        "the entry point calls the run sequence and the one read the index needs",
    )
    assert called(path1) == ["generate_run"], (called(path1), "path 1's entry point builds no block")
    assert not [name for name in methods if f"{name}(" in entry_source and name != "parse_associations"], (
        entry_source,
        "the entry point states no parse order of its own",
    )
    assert not [name for name in methods if f"{name}(" in path1], (path1, "path 1 calls no parse method")
    assert not hasattr(api_to_terraform, "PARSE_ORDER"), "the entry point holds no parse order"

    # The three pins that read the run sequence read the run function, because the sequence moved there.
    for name in ("test_scope_objects.py", "test_commit_actions.py", "test_site_data.py"):
        text = (TESTS_DIR / name).read_text(encoding="utf-8")
        assert "inspect.getsource(converter_module.generate_run)" in text, (name, "reads the run function")
    # No pin reads the sequence from `main()`, because the sequence is the run function's. The needle is built in
    # two parts so this pin cannot match itself: it reads `main()` only to check that main calls the run function.
    needle = "getsource(converter_module" + ".main)"
    reading_main = [
        path.name for path in sorted(TESTS_DIR.glob("test_*.py")) if needle in path.read_text(encoding="utf-8")
    ]
    assert reading_main == [], (reading_main, "no pin reads the sequence from `main()`")


def test_the_run_view_answers_the_entry_protocol_through_the_ledger_that_holds_the_entry(tmp_path):
    """Criterion 4: the view holds the responses in run order and answers the protocol through the ledger that
    holds the entry, so an entry belongs to one response and no answer is built from a tree across responses. A
    run that read one response is answered the same as that response's own ledger.
    """
    parts = _parts(tmp_path)
    assert len({part.source.name for part in parts}) == len(parts), (
        "two responses, each named by the request that read it"
    )
    view = entry_coverage.RunView(parts, _concat_join)

    assert view.parts() == parts, "the view holds the parts in the order the run read them"
    assert view.entries() == [entry for part in parts for entry in part.ledger().entries()], (
        "the entry set is the parts in run order"
    )
    assert view.rows() == [row for part in parts for row in part.ledger().rows()], (
        "the row set is the parts in run order"
    )
    assert view.sources() == [part.source for part in parts], "one source per response the run read"

    # Every protocol answer is the answer of the ledger that holds the entry, and the parent facts are the
    # merged per-response maps, so no entry has a parent in another response.
    for part in parts:
        for entry in part.ledger().entries():
            holder = part.ledger()
            assert view.ledger_for(entry) is holder, "the answer goes to the ledger that holds the entry"
            assert view.row_for(entry) == holder.row_for(entry)
            assert view.mark_for(entry) is holder.mark_for(entry)
            assert view.destination(entry) == holder.destination(entry)
            assert view.is_report_entry(entry) == holder.is_report_entry(entry)
            assert view.scope(entry) == holder.scope(entry)
            assert view.line_of(entry) == holder.line_of(entry)
            assert view.source_of(entry) is holder.source
            assert view.parents[entry] is holder.parents[entry]
            assert all(entry not in other.ledger().parents for other in parts if other is not part), (
                "no parent crosses a response"
            )

    single = entry_coverage.RunView(parts[:1], _concat_join)
    ledger = parts[0].ledger()
    for name in (
        "entries",
        "rows",
        "gaps",
        "counts",
        "property_findings",
        "property_entry_total",
        "predefined_total",
        "gap_count",
    ):
        assert getattr(single, name)() == getattr(ledger, name)(), name

    view.start_recording()
    assert all(part.ledger().recording for part in parts), "the read record is turned on for every response"


def _class_node(module: str, name: str) -> ast.ClassDef:
    """One class body, so a pin reads what the class states and not the module that holds it."""
    tree = ast.parse((SRC_DIR / module).read_text(encoding="utf-8"))
    return next(node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == name)


def test_the_run_view_states_no_row_shape_and_no_field_name_of_its_own():
    """Criterion 4: the view answers, it does not decide. It states no row shape, no field name, no naming
    rule, no sort rule, no writer, no console line, and no environment name, and it takes the join as an
    argument, because the cross-response merge is the entry point's decision.
    """
    node = _class_node("entry_coverage.py", "RunView")
    body = ast.unparse(node)
    fields = set(unit_manifest.FIELD_ORDER) | {
        "line",
        "source",
        "container",
        "destination",
        "detail",
        "fields",
        "captured",
        "property_entries",
    }
    for field in sorted(fields):
        assert f"'{field}'" not in body, (field, "the view adds no field to the row shape its owner states")
    assert "sorted(" not in body, "the view states no sort rule: the row order is the run order"
    for name in ("print(", "write_file", "write_text", "render", "console_line", "sanitize", "name_ref"):
        assert name not in body, (name, "the view states no rule of this kind")

    init = next(stmt for stmt in node.body if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__")
    assert "join" in [arg.arg for arg in init.args.args], "the join is an argument, so the view states no merge rule"


def _entry_code() -> ast.Module:
    """The entry point as code, so a pin reads what it states and not the document around it."""
    return ast.parse((SRC_DIR / "api_to_terraform.py").read_text(encoding="utf-8"))


def test_the_entry_point_accepts_the_arguments_of_one_run_and_refuses_the_ones_that_name_one_source(tmp_path):
    """Criterion 5: the arguments are `shared_arguments`, stated once for both entry points, so the entry point
    adds none of its own. The request set is the scope set, so an argument that names one source is refused, and
    an argument error exits 2. The limit is read through the door's own argument rule.
    """
    entry = api_to_terraform.build_parser()
    shared = argparse.ArgumentParser()
    panorama_to_terraform.shared_arguments(shared)
    accepted = vars(entry.parse_args(["--host", HOST, "--output-dir", str(tmp_path / "out")]))
    shared_accepted = vars(shared.parse_args(["--host", HOST, "--output-dir", str(tmp_path / "out")]))
    assert sorted(accepted) == sorted(shared_accepted), "the entry point adds no argument of its own"
    for name in (
        "host",
        "cache_dir",
        "offline",
        "insecure",
        "output_dir",
        "max_input_bytes",
        "validate",
        "tflint",
        "data_blocks",
        "import_blocks",
        "state",
        "workspace",
        "prune_cache",
        # F11.1 (`docs/MULTI_RUN_CODEBASE.md` §2 rule 1): the selection names the read set, not a source, so it
        # sits in the shared set and the entry point adds none of its own. Piece 13B.4 (`docs/INPUT_SHAPES.md` §2
        # rule 4): the member declaration names one member of a bundle, so it names no source either and sits in the
        # same set.
        "selection",
        "member",
    ):
        assert name in accepted, (name, "the argument one run reads")

    # The words that name one source are refused: the request set is the scope set, and the parent walk stays
    # inside one response (F8.5), so no argument names one source.
    for word in ("input_file", "--source", "--path", "--parent"):
        with pytest.raises(SystemExit) as raised:
            entry.parse_args([word, "--host", HOST, "--output-dir", str(tmp_path / "out")])
        assert raised.value.code == 2, (word, "an argument error exits 2")

    # The argument checks are `shared_checks`, so the entry point states none of its own beyond the words. An
    # argument error exits 2, and it exits before the run reads anything.
    entry_source = (SRC_DIR / "api_to_terraform.py").read_text(encoding="utf-8")
    assert "add_argument(" not in entry_source, "the entry point adds no argument"
    assert "shared_arguments(" in entry_source and "shared_checks(" in entry_source, "the checks are the owners"
    for case in (
        ["--host", HOST, "--insecure", "--offline", "--output-dir", str(tmp_path / "out")],
        ["--host", HOST, "--workspace", "ws", "--output-dir", str(tmp_path / "out")],
    ):
        with pytest.raises(SystemExit) as raised:
            api_to_terraform.run(case, _producer())
        assert raised.value.code == 2, (case, "an argument error exits 2")
        assert not (tmp_path / "out").exists(), "an argument error writes no file"

    # The input limit is the door's rule, read through `source_fetch`, so the entry point states no limit.
    assert accepted["max_input_bytes"] == source_fetch.DEFAULT_MAX_INPUT_BYTES, "the limit is the door default"
    assert "source_fetch.add_max_input_argument" in (SRC_DIR / "panorama_to_terraform.py").read_text(
        encoding="utf-8"
    ), "the door owns the argument rule"
    assert "max_input_bytes=args.max_input_bytes" in entry_source, "the limit is passed to the owners"


def _methods_for(place: str) -> tuple:
    """The parse methods the container table rows name for one place: the rows whose destination is `emitted` are
    the rows that write a report row, so the pin runs the methods the table names and states none of its own. A
    place no table row names has no method to run.
    """
    return tuple(
        row.method
        for row in container_coverage.CONTAINER_TABLE
        if row.destination == "emitted" and container_coverage.path_place(row.path) == place
    )


def test_a_selection_that_names_no_unit_is_an_argument_error_on_a_run(tmp_path):
    """F11.1 (`docs/MULTI_RUN_CODEBASE.md` §2 rules 1 and 2): a selection that names no unit in the run's read set
    is an argument error, exit 2, and writes no file, read through the shape `--path` already states, so no second
    error shape appears. The no-unit fact is read through `unit_manifest.units` on the reads the run makes for the
    places: the run runs the parse methods the container table rows name for a place, so a place a row names builds
    a report row and the unit rule names a unit for it, while no table row names the built-in place, which
    `test_no_table_row_names_a_builtin_container` holds, so its ledger holds no row and the unit rule names no unit.
    The shape is read through `container_coverage.is_scope_path`, so this pin states no path shape of its own.
    """
    cache = tmp_path / "cache"
    place = api_requests.list_container(api_requests.membership_lists()[0])
    _, place_parser = _run(source_fetch.ApiRequest(host=HOST, path=place), PLACES[place], cache)
    assert _methods_for(place), "the table names a method for a place it can build a unit for"
    _rows_for(place_parser, _methods_for(place))
    assert unit_manifest.units(place_parser.ledger), (place, "the place a table row names names a unit")

    _, built_in_parser = _run(
        source_fetch.ApiRequest(host=HOST, path=container_coverage.PREDEFINED_PLACE), PREDEFINED_PLACE_BODY, cache
    )
    assert _methods_for(container_coverage.PREDEFINED_PLACE) == (), (
        "no table row names a built-in container, so no parse method runs over its response"
    )
    assert unit_manifest.units(built_in_parser.ledger) == [], "no row, so the unit rule names no unit for it"

    # The argument error, read on a run: an argument error exits 2 and writes no file, the shape `--path` states.
    for case in (
        ["--host", HOST, "--selection", container_coverage.PREDEFINED_PLACE],
        ["--host", HOST, "--selection", api_requests.scope_path(container_coverage.PREDEFINED_PLACE, "url-list")],
        [
            "--host",
            HOST,
            "--selection",
            next(
                row.path for row in container_coverage.CONTAINER_TABLE if not container_coverage.is_scope_path(row.path)
            ),
        ],
    ):
        out = tmp_path / "refused"
        with pytest.raises(SystemExit) as raised:
            api_to_terraform.run([*case, "--output-dir", str(out)], _producer())
        assert raised.value.code == 2, (case, "an argument error exits 2")
        assert not out.exists(), "an argument error writes no file"

    # A selection that names a unit is accepted, so the rule is not a blanket refusal. The accepted run writes the
    # same file set as a run that declares no selection, because the read rule drops no unit, and its bytes differ
    # because the name rule reads one entry fewer for a selection, which
    # `test_the_record_names_the_read_set_in_run_order_for_a_targeted_run` measures.
    out = tmp_path / "accepted"
    argv = ["--host", HOST, "--selection", api_requests.scope_path(place), "--output-dir", str(out)]
    assert api_to_terraform.run(argv, _producer()) == 0, "the argument rule accepted the selection"
    assert out.exists(), "the accepted run writes files"
    plain = tmp_path / "plain"
    assert api_to_terraform.run(["--host", HOST, "--output-dir", str(plain)], _producer()) == 0
    accepted, plain_files = written_bytes(out), written_bytes(plain)
    assert sorted(accepted) == sorted(plain_files), (accepted.keys(), plain_files.keys(), "the same file set")
    assert accepted != plain_files, "a run that declares a selection is not byte-identical to one that declares none"


def test_the_entry_point_passes_the_index_it_built_to_the_gate_and_keeps_the_gate_code(tmp_path):
    """Criterion 6: `run_checks` reports `request_set` as NOT RUN when it has no index, so the entry point passes
    the index and the run view it built. Path 1 still passes no index, because it read no request. The join
    findings print through the gate, so the entry point prints no join block of its own, and the exit code stays
    the gate's decision.
    """
    args, argv = _run_args(tmp_path)
    parts, index = api_to_terraform.run_order(args, _producer())
    view = _view(parts)
    out = tmp_path / "out"
    assert api_to_terraform.run(argv, _producer()) == 0, "the gate decided 0 for a run that wrote no finding"

    # The gate reads the index the entry point built. Without it the join reports as NOT RUN, so the run's own
    # gate call is the only place the join can run. A join finding prints through the gate: an index that holds
    # only one of the responses the run read finds rows that name a response the index does not hold.
    assert sanity_checks.run_checks(out).result_of("request_set") == sanity_checks.NOT_RUN
    with_index = sanity_checks.run_checks(out, ledger=view, index=index)
    assert with_index.result_of("request_set") != sanity_checks.NOT_RUN, "the gate ran the join for this run"
    read_one = parts[:1]
    smaller = api_requests.scope_index(
        HOST, read_one[0].parser.parse_associations(), api_to_terraform.lists_read(read_one)
    )
    assert sanity_checks.run_checks(out, ledger=view, index=smaller).findings("request_set"), (
        "the join findings print through the gate"
    )

    entry_source = (SRC_DIR / "api_to_terraform.py").read_text(encoding="utf-8")
    path1 = inspect.getsource(panorama_to_terraform.main)
    assert "index=index" in entry_source, "the entry point passes the index it built"
    assert "run_checks" not in entry_source, "the gate call is the run sequence, stated once"
    assert "index=" not in path1, "path 1 passes no index: it read no request"

    # The findings print through the gate, so the entry point states no join block and no report of its own.
    for node in ast.walk(_entry_code()):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "print":
            assert any(
                getattr(inner.func, "attr", "") in ("read_line", "state_line")
                for inner in ast.walk(node)
                if isinstance(inner, ast.Call)
            ), "the entry point prints only the lines the owners state"

    # The exit code is the gate's decision: a file the gate fails on exits 1, and a refused input exits 1 and
    # writes no file.
    (out / "planted.tf").write_text(
        'resource "panos_address" "planted_00000000" {\n  name = "Planted"\n  value = panos_zone.ghost.name\n}\n',
        encoding="utf-8",
    )
    assert sanity_checks.run_checks(out).result_of("references") == "FAIL"
    assert api_to_terraform.run(argv, _producer()) == 1, "the gate FAIL is the run exit code"

    refused_args, refused_argv = _run_args(tmp_path / "refused run")

    def refusing(request):
        raise source_fetch.SourceFetchError("the response is refused by the door")

    assert api_to_terraform.run(refused_argv, refusing) == 1, "a refused input exits 1"
    assert not [p for p in (tmp_path / "refused run" / "out").rglob("*") if p.is_file()], (
        "a refused input writes no file"
    )


def test_the_entry_point_states_no_rule_an_owner_states():
    """Criterion 7: the entry point decides the run order and the arguments, and states nothing else. Every other
    rule has one owner, so the entry point reads each one through the module that owns it, and holds no rule
    name of its own.
    """
    tree = _entry_code()
    text = (SRC_DIR / "api_to_terraform.py").read_text(encoding="utf-8")

    # What the entry point holds is the entry point name as data, and the functions that state the order, the
    # arguments, one read, and the run.
    held = sorted({t.id for node in tree.body if isinstance(node, ast.Assign) for t in node.targets})
    stated = sorted(node.name for node in tree.body if isinstance(node, ast.FunctionDef))
    assert held == ["ENTRY_POINT"], held
    assert stated == ["build_parser", "lists_read", "main", "read_part", "run", "run_order"], stated
    # The name is the one fact the entry point can state, so it is data and not a rule.
    assert api_to_terraform.ENTRY_POINT == "api_to_terraform.py", api_to_terraform.ENTRY_POINT
    assert not re.search(r"\d", api_to_terraform.ENTRY_POINT), "the path name the label states is digit-free"

    # No rule an owner states. Each name below is stated by its owner, so the entry point cannot hold it, and it
    # reads what it needs through the module that owns it.
    owners = {
        "naming.py": ("sanitize", "variable_name", "variable_text"),
        "write_path.py": ("write_file", "root_path"),
        "container_coverage.py": (
            "CONSOLE_PREFIX",
            "CONTAINER_TABLE",
            "console_line",
            "position_part",
            "SECTION_TITLE",
        ),
        "entry_coverage.py": ("REPORT_HEADING", "GAP_HEADING", "entry_line", "console_lines"),
        "api_requests.py": (
            "scope_index",
            "targeted_read_set",
            "targeted_names",
            "membership_lists",
            "list_container",
            "scope_path",
            "CONTAINER_LEVEL",
            "ENTRY_LEVEL",
        ),
        "sanity_checks.py": ("run_checks", "Finding", "NOT_RUN"),
        "unit_manifest.py": ("FIELD_ORDER", "identity_digest", "directory_name", "unit_name"),
        "source_fetch.py": ("API_KEY_ENV", "add_max_input_argument", "add_member_argument", "fetch", "ApiRequest"),
    }
    for module, names in owners.items():
        for name in names:
            assert name in (SRC_DIR / module).read_text(encoding="utf-8"), (module, name, "the owner states it")
            assert not hasattr(api_to_terraform, name), (name, "the entry point states no rule of this kind")

    # Every module the entry point reads is an owner, so every name it uses is the owner's.
    read = sorted(
        {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
        | {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    )
    assert read == sorted(
        ["api_requests", "argparse", "entry_coverage", "panorama_to_terraform", "source_fetch", "state_input", "sys"]
    ), read
    used = sorted(
        {
            f"{node.value.id}.{node.attr}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in read
        }
    )
    assert all(part.split(".")[0] in read for part in used), used

    # The entry point states no join rule, no block builder, no writer, no sort rule, and no file rule of its own,
    # read as the names its code holds, not as the prose around them.
    held_names = {
        getattr(node, "attr", None) or getattr(node, "id", None)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Name, ast.Attribute))
    }
    for name in ("join_value", "merge", "sorted", "open", "write_text", "write_bytes", "linesep"):
        assert name not in held_names, (name, "the entry point states no rule of this kind")
    assert not any(str(name).startswith("generate_") and str(name) != "generate_run" for name in held_names), (
        "no block builder"
    )

    # The environment name is the door's, stated once, so the entry point names no second one: the name it holds
    # is the value `source_fetch.API_KEY_ENV`, never the word itself.
    assert source_fetch.API_KEY_ENV not in text, "no second environment name"
    assert not hasattr(api_to_terraform, "API_KEY_ENV"), "the entry point holds no environment name"
    assert not any(isinstance(node, ast.Attribute) and node.attr == "environ" for node in ast.walk(tree)), (
        "the entry point reads no environment of its own"
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "print":
            assert any(
                getattr(inner.func, "attr", "") in ("read_line", "state_line")
                for inner in ast.walk(node)
                if isinstance(inner, ast.Call)
            ), "the entry point prints through the owners"


def test_the_report_names_each_response_the_run_read_in_run_order(tmp_path):
    """Criterion 8: the report names each source the run read, in the order it read them. One response names
    itself, so a path 1 report is byte-identical. The parts that need a full ledger are answered per response and
    concatenated in run order; the parts that read the row set read the merged set.
    """
    args, argv = _run_args(tmp_path)
    parts, _ = api_to_terraform.run_order(args, _producer())
    assert api_to_terraform.run(argv, _producer()) == 0
    report = (tmp_path / "out" / entry_coverage.REPORT_FILE).read_text(encoding="utf-8").splitlines()
    named = [line for line in report if line.startswith(container_coverage.SOURCE_LABEL)]
    assert named == [f"{container_coverage.SOURCE_LABEL} {part.source.name}" for part in parts], (
        "one source line per response, in run order"
    )
    assert len(named) == len({part.source.name for part in parts}), "the run read four responses"

    # A run that read one response names that response only, which is the shape a path 1 report keeps.
    single = _view(parts[:1])
    assert single.sources() == [parts[0].source], "one response, one source line"
    export = source_fetch.fetch(
        source_fetch.ApiRequest(host=HOST), tmp_path / "export", producer=lambda r: SAME_CONTENT_EXPORT
    )
    export_parser = panorama_to_terraform.PanoramaParser(export)
    export_parser.parse_address_objects()
    assert export_parser.ledger.sources() == [export], "path 1 answers its own single source"

    # The parts that need a full ledger are the parts' own answers, in run order. The parts that read the row set
    # read the merged set, so a count is the merged count and not the largest part's.
    for name in ("rows", "gaps", "property_findings"):
        answer = getattr(_view(parts), name)()
        assert answer == [item for part in parts for item in getattr(part.ledger(), name)()], (
            name,
            "answered per response and concatenated in run order",
        )
    merged = _view(parts).counts()
    for key in {key for part in parts for key in part.ledger().counts()}:
        assert merged[key] == sum(part.ledger().counts()[key] for part in parts if key in part.ledger().counts()), (
            key,
            "the merged set is what the report reads",
        )
    for name in ("property_entry_total", "predefined_total"):
        assert getattr(_view(parts), name)() == sum(getattr(part.ledger(), name)() for part in parts), name

    # The report holds no path and no credential, so the source lines name the cache entries only, and the same
    # report the run wrote is the gate's input through the owners.
    assert HOST not in report, "the report names no host, and no path"
    assert all(len(line.split()) == 2 for line in named), "a source line names the source and nothing else"


# --- 9. the entry a membership list names and the run read as its own scope -------


def _membership_producer(request, key=None, insecure=False):
    """The content above, handed by an injected producer: one response per place, one response per entry the
    index names, and the same content as one whole-config export for a request that names no path. No test calls
    a network, so path 2 reads only this content and path 1 reads the same content as one response.
    """
    if request.path == "":
        return MEMBERSHIP_EXPORT
    container = request.segments()[0]
    return per_scope_response(request, MEMBERSHIP[container]) if container in MEMBERSHIP else None


def test_the_entry_read_answers_the_entry_its_own_request_names(tmp_path):
    """Criterion 3: a parse method reads the entries at the level its container-table row names, so the response
    that holds the entry the path names answers that entry. A whole-config source and a place read reach the level
    through the container element, so they are unchanged. A membership row names a level inside the entry the path
    names, so an entry response answers no membership table and the index keeps reading its set from the place
    responses.
    """
    args, _ = _run_args(tmp_path)
    parts, index = api_to_terraform.run_order(args, _membership_producer)
    assert len(parts) == 2 * len(MEMBERSHIP), (parts, "one response per place, then one per entry the index names")

    for part in parts:
        segments = part.request.segments()
        place = segments[0]
        row = [r for r in container_coverage.CONTAINER_TABLE if r.path == place and r.method.startswith("parse_")]
        assert len(row) == 1, row
        answer = getattr(part.parser, row[0].method)()
        assert answer, (part.request.path, "the method named by the row answered nothing at the level it names")
        answered_entry = api_requests.entry_for_path(index, part.request.path)

        if len(segments) == 3:
            # The response holds the entry its request names, so that entry is the entry at the level the row names.
            assert [obj["name"] for obj in answer] == [answered_entry.name], (part.request.path, answer)
            tables = part.parser.parse_associations()
            assert not [n for table in tables.values() for names in table.values() for n in names], (
                part.request.path,
                tables,
                "a membership row names a level inside the entry, so an entry response answers no table",
            )
        else:
            # The place read reaches the level through the container element, so it answers the names the index
            # read for that container.
            assert [obj["name"] for obj in answer] == list(api_requests.names_in_index(index, place)), (
                part.request.path,
                answer,
            )

        # The row a part built for the entry its own request names names that part, so the join answers that part
        # for it: `name` is the entry the run read for the row's scope, and a place row is answered by the place.
        scope_rows = [r for r in part.ledger().rows() if r["container"] == place]
        assert scope_rows, (part.request.path, part.ledger().rows(), "the join needs rows to read")
        for report_row in scope_rows:
            answered = (
                api_requests.response_for_section(place, index, name=report_row["name"])
                if len(segments) == 3
                else api_requests.response_for_section(place, index)
            )
            assert answered is api_requests.entry_for_path(index, part.request.path), (report_row, answered)
            assert answered.request.cache_name() == report_row["source"], (report_row, answered)


def test_an_entry_two_responses_hold_gives_one_block_per_response(tmp_path, monkeypatch):
    """Criteria 1, 2 and 4: the entry a membership list names is also the entry the run read as its own scope, so
    the run reads it twice and keeps both answers. One response is one source, so the entry is two report rows,
    each naming the response that holds it, and path 2 writes the content of each response it read: one block per
    response that holds the entry, so the name rule gives the second block the suffix it states for a repeated
    name. Path 1 read the same content as one response, so it writes one block per entry, and the two paths write
    different bytes for content that states a membership list.
    """
    out1, cache1 = tmp_path / "path1", tmp_path / "cache1"
    args, argv = _run_args(tmp_path)
    monkeypatch.setenv(source_fetch.API_KEY_ENV, "test-key")
    monkeypatch.setattr(source_fetch, "network_producer", _membership_producer)
    path1 = run_pipeline(
        panorama_to_terraform, None, out1, ("--source", "api", "--host", HOST, "--cache-dir", str(cache1))
    )
    assert path1 is not None, "path 1 refused the content"
    code, parts, index = _path2_run(argv, _membership_producer, monkeypatch)
    assert code == 0, "the path 2 run"

    # Path 2 read one response per place and one per entry the index names for the same entries path 1 read as
    # one response.
    assert len(parts) == 2 * len(MEMBERSHIP), (parts, "the entry is read twice")
    assert len({part.request.path for part in parts}) == len(parts), "one response is read once"
    assert not path1.source.is_per_scope and all(part.source.is_per_scope for part in parts), (
        "path 1 read one response, path 2 one per place and one per entry",
    )

    view = _view(parts)
    emitted = [row for row in view.rows() if row["destination"] == "emitted"]
    assert emitted, "the pin needs rows to read"
    for name in sorted({row["name"] for row in emitted}):
        held = [row for row in emitted if row["name"] == name]
        assert len(held) == 2, (name, held, "one row per response that holds the entry")
        assert len({row["source"] for row in held}) == 2, (held, "two rows name two responses")

    files1, files2 = tf_files(out1), tf_files(args.output_dir)
    blocks1 = sanity_checks.blocks(files1, ("resource",))
    blocks2 = sanity_checks.blocks(files2, ("resource",))
    assert blocks1 and blocks2, "the pins need blocks to read"
    assert len(blocks2) == 2 * len(blocks1), (blocks1, blocks2, "one block per response that holds the entry")
    assert files1 != files2, "the byte agreement holds only for content that states no membership list"

    # The unit is the one unit rule's name, and the writer writes one file per unit for it. Path 1's block for an
    # entry is the first of the two, so the second is the entry response's own block with the name rule's suffix.
    units = {unit_manifest.directory_name(facts, naming.sanitize) for facts in unit_manifest.units(view)}
    assert units == {block.file.split("/")[0] for block in blocks2}, (units, sorted(block.file for block in blocks2))
    for unit in sorted(units):
        read = [block for block in blocks2 if block.file.split("/")[0] == unit]
        first = sorted(block.local for block in read if not block.local.endswith("_2"))
        assert first == sorted(block.local for block in blocks1 if block.file.split("/")[0] == unit), (unit, read)
        assert len(first) == len(read) // 2 == 2, (unit, read, "one entry read twice writes two blocks")
        assert all(block.local.endswith("_2") for block in read if block.local not in first), (unit, read)


def test_the_double_read_agrees_with_the_gate(tmp_path, monkeypatch):
    """Criterion 5: the gate reads the double read as two sets that agree, so it reports nothing for it. The entry
    side reads 2 for the unit and the row that names the entry read twice, and the block side reads 2 for the same
    unit and row, because each response that holds the entry wrote a block. `check_request_set` reports nothing
    because both responses are in the read set. Path 1 reports nothing on the same content, and it reports
    `request_set` as NOT RUN because path 1 holds no index (`docs/API_CONVERSION_PATH.md` §3).
    """
    out1, cache1 = tmp_path / "path1", tmp_path / "cache1"
    args, argv = _run_args(tmp_path)
    monkeypatch.setenv(source_fetch.API_KEY_ENV, "test-key")
    monkeypatch.setattr(source_fetch, "network_producer", _membership_producer)
    path1 = run_pipeline(
        panorama_to_terraform, None, out1, ("--source", "api", "--host", HOST, "--cache-dir", str(cache1))
    )
    assert path1 is not None, "path 1 refused the content"
    code, parts, index = _path2_run(argv, _membership_producer, monkeypatch)
    assert code == 0, "the path 2 run"

    view = _view(parts)
    files1, files2 = tf_files(out1), tf_files(args.output_dir)
    assert sanity_checks.check_round_trip(files2, view, args.output_dir) == [], "the two counts read the same set"
    assert sanity_checks.check_request_set(index, view) == [], "both responses are in the read set"
    assert sanity_checks.check_round_trip(files1, path1.ledger, out1) == [], "path 1 read one response per entry"

    # The two counts the rule reads for one unit and one row, read through the owners the rule names.
    row = entry_coverage.matrix_row_for("device-group")
    assert row is not None, row
    entries = [
        r for r in view.rows() if r["destination"] == "emitted" and entry_coverage.matrix_row_for(r["container"]) is row
    ]
    assert len(entries) == 2, entries
    assert len({r["source"] for r in entries}) == 2, (entries, "two responses, two rows")
    unit = unit_manifest.directory_name(unit_manifest.facts_of(entries[0]), naming.sanitize)
    counted = [b for b in sanity_checks.blocks(files2, ("resource",)) if b.file.split("/")[0] == unit]
    assert len([b for b in counted if b.rtype == row["resource"]]) == 2, (unit, counted)


# --- 10. the targeted read set (F11.2, `docs/MULTI_RUN_CODEBASE.md` §2 rule 3) ---------------

# The read set and the name set are `api_requests`' rules, so these pins read a targeted run through the entry point
# and read both sets through their owner, and this file states no read set, no name rule, and no path shape of its
# own. The selection measured is a place, because a place names no fact a single read can state on its own, so the
# read set is the four lists and the names narrow to the names inside the place.


def _targeted_args(tmp_path, selection: str) -> tuple:
    """The arguments one targeted run reads, through the entry point's own parser."""
    argv = [
        "--host",
        HOST,
        "--cache-dir",
        str(tmp_path / "cache"),
        "--output-dir",
        str(tmp_path / "out"),
        "--selection",
        selection,
    ]
    return api_to_terraform.build_parser().parse_args(argv), argv


def _targeted_index(tmp_path, selection: str) -> tuple:
    """The index a targeted run builds, read through the read set and the name rule."""
    tables = _membership(tmp_path)
    return api_requests.scope_index(HOST, tables, api_requests.targeted_read_set(selection), selection)


def test_a_targeted_run_reads_the_lists_and_the_names_the_selection_states(tmp_path):
    """F11.2 (`docs/MULTI_RUN_CODEBASE.md` §2 rule 3): a targeted run reads the same membership responses as a run
    that declares no selection, because no list states a fact a single read can state on its own, and its entry part
    holds only the names the name rule states for the selection. The entry point states no read set and no name rule,
    so both are read here through `api_requests`.
    """
    selection = "device-group"
    args, _ = _targeted_args(tmp_path, selection)
    parts, index = api_to_terraform.run_order(args, _producer())
    read = tuple(part.request.path for part in parts)

    assert api_requests.targeted_read_set(selection) == api_requests.membership_lists(), (
        "no list is dropped for a selection, so the set narrows through the names and not through the lists"
    )

    # The membership part of the order: the container each list names, in the order the lists name them, read as the
    # responses the producer answers for the content this file holds.
    lists_read = tuple(
        api_requests.scope_path(api_requests.list_container(name))
        for name in api_requests.targeted_read_set(selection)
        if api_requests.list_container(name) in PLACES
    )
    assert lists_read, "the producer answers the responses for the lists this file holds content for"

    # The entry part: the names the name rule states, in index order, read through the one join rule.
    tables = panorama_to_terraform.join_results([part.parser.parse_associations() for part in parts])
    names = tuple(
        api_requests.scope_path(container, name)
        for container, name in api_requests.targeted_names(selection, tables)
        if api_requests.scope_path(container, name) in read
    )
    assert names, "the selection names a name inside a response the run read"
    assert read == lists_read + names, (read, "the membership responses first, then the names the selection states")

    # A name the selection excludes gains no entry, so the run read no response for it. The run that declares no
    # selection reads it, which is the difference the name rule decides.
    excluded = api_requests.scope_path("templates", "HQ-Networks")
    plain_args, _ = _run_args(tmp_path)
    _plain_parts, plain_index = api_to_terraform.run_order(plain_args, _producer())
    assert excluded in [entry.path for entry in plain_index], "the run that declares no selection holds an entry for it"
    assert excluded not in [entry.path for entry in index], index
    assert excluded not in read, (read, "no response is read for a name that is not an entry")


def test_the_join_reports_no_finding_for_a_name_the_selection_excludes(tmp_path):
    """F11.2 (`docs/MULTI_RUN_CODEBASE.md` §2 rule 3): the gate reads the join, and a name the selection excludes is
    not an index entry, so the join has no entry to report a finding against. The unit set is still
    `unit_manifest.units`, so the join answers a pair for a unit whose name the selection excludes, and the pair
    names the place entry, because the read set keeps every list and the run read the response that holds the name.
    """
    selection = "device-group"
    full = _index(tmp_path)
    targeted = _targeted_index(tmp_path, selection)
    _source, place_parser = _run(source_fetch.ApiRequest(host=HOST, path=selection), PLACES[selection], tmp_path)
    assert _methods_for(selection), "the table names a method for a place the selection can name"
    rows = _rows_for(place_parser, _methods_for(selection))
    assert rows, "the join needs rows to read"

    pairs = api_requests.join_units(targeted, place_parser.ledger)
    assert [facts for facts, _entry in pairs] == unit_manifest.units(place_parser.ledger), (
        "the join reads the same unit set for a targeted run"
    )
    assert all(entry is not None for _facts, entry in pairs), (pairs, "the join answers every unit it reads")
    assert {entry.path for _facts, entry in pairs} == {selection}, (pairs, "the pair names the place entry")

    full_findings = sanity_checks.check_request_set(full, place_parser.ledger)
    targeted_findings = sanity_checks.check_request_set(targeted, place_parser.ledger)
    assert any("HQ-Networks" in finding.detail for finding in full_findings), full_findings
    assert not any("HQ-Networks" in finding.detail for finding in targeted_findings), targeted_findings
    assert targeted_findings, "the targeted index keeps the entries the read set names, and reports those"


def test_the_record_names_the_read_set_in_run_order_for_a_targeted_run(tmp_path):
    """F11.2 (`docs/MULTI_RUN_CODEBASE.md` §2 rule 3): the record file a targeted run wrote names the responses in the
    order the run read them, and names only the read set, so it holds no row for a name the selection excludes. The
    record shape is `provenance`'s rule and the read set is `api_requests`' rule, so this pin reads the rows as data
    and states no shape of its own.
    """
    selection = "device-group"
    args, argv = _targeted_args(tmp_path, selection)
    parts, index = api_to_terraform.run_order(args, _producer())
    assert api_to_terraform.run(argv, _producer()) == 0, "the targeted run wrote a record"
    record = (tmp_path / "out" / provenance.PROVENANCE_FILE).read_text(encoding="utf-8")
    rows = provenance.parse_records(record)
    assert rows, "the record holds the responses the run read"
    assert [row.cache_entry for row in rows] == [part.request.cache_name() for part in parts], (
        "the record names the responses in the order it read them"
    )

    scopes = [row.scope for row in rows]
    read_set = {
        api_requests.scope_path(api_requests.list_container(name)) for name in api_requests.targeted_read_set(selection)
    }
    names = {
        api_requests.scope_path(container, name)
        for container, name in api_requests.targeted_names(selection, _membership(tmp_path))
    }
    outside = [scope for scope in scopes if scope not in read_set and scope not in names]
    assert not outside, (scopes, "no row names a response outside the read set")
    assert selection in scopes, "the record names the selected place, because its list is in the read set"
    assert api_requests.scope_path(selection, "Office-FW") in scopes, (
        "the record names the entry the selection states, which the run read as its own scope"
    )
    assert api_requests.scope_path("templates", "HQ-Networks") not in scopes, "no row for a name the selection excludes"


# --- 11. the bytes a targeted run writes for the unit it selects (F11.3, `docs/MULTI_RUN_CODEBASE.md` §2 rule 6) ---

# One unit, read both ways on the committed response set: the run that declares no selection, and the run that
# selects `device-group/entry/Office-FW`. Both read through `conftest.api_producer`, so no pin calls a network, and
# both read through the same cache, so the bytes come from the same response. The unit set is read through
# `unit_manifest`, the unit's files through `write_path`, the printed form through `site_data`, and the block set
# through the one block reader, so this group states no unit rule, no path rule, no file-shape rule and no
# read-through rule of its own. The content the two runs read is inside the condition rule 6 states: the committed
# responses name no read-through name, so the read-through branch answers nothing for either run.


SELECTION = "device-group/entry/Office-FW"


def _agreement_run(tmp_path, name: str, selection: str = "") -> tuple:
    """One path 2 run on the committed response set, and the parts and the index the entry point built for it.

    Both runs read through the same cache, so the record and the report name the same response, and the producer is
    `conftest.api_producer`, so the pin reads the committed bytes and not a file copy of them.
    """
    argv = ["--host", HOST, "--cache-dir", str(tmp_path / "cache"), "--output-dir", str(tmp_path / name)]
    if selection:
        argv += ["--selection", selection]
    args = api_to_terraform.build_parser().parse_args(argv)
    parts, index = api_to_terraform.run_order(args, api_producer)
    assert api_to_terraform.run(argv, api_producer) == 0, "the run wrote its output directory"
    return tmp_path / name, parts, index


def _agreement_unit(parts, index) -> str:
    """The directory the run writes for the unit the selection names.

    The unit is read through `api_requests.join_units` and its directory through `unit_manifest.directory_name`, so
    this group states no unit rule, no join rule and no directory rule of its own: it only names which of the join's
    answers is the one the selection states, through the path the name rule states.
    """
    entry = api_requests.entry_for_path(index, SELECTION)
    assert entry is not None, "the run read the response for the selection, so its name is an index entry"
    pairs = api_requests.join_units(index, _view(parts))
    assert pairs, "the join answers a pair for the unit the selection names"
    return unit_manifest.directory_name(next(f for f, _answered in pairs if entry.name in f), naming.sanitize)


def test_a_targeted_run_writes_the_same_tf_bytes_as_the_full_run_for_the_unit_it_selects(tmp_path):
    """F11.3 (`docs/MULTI_RUN_CODEBASE.md` §2 rule 6): for content that names no read-through name, the `.tf` bytes a
    targeted run writes for one unit are the bytes a full run writes for that unit, read as paths from the unit
    directory (`docs/CODEBASE_ASSEMBLY.md` §14).
    """
    full, _parts_full, _index_full = _agreement_run(tmp_path, "full")
    targeted, parts_targeted, index_targeted = _agreement_run(tmp_path, "targeted", SELECTION)
    directory = _agreement_unit(parts_targeted, index_targeted)

    bytes_full, bytes_targeted = tf_bytes(full / directory), tf_bytes(targeted / directory)
    assert bytes_full and bytes_targeted, (sorted(bytes_full), sorted(bytes_targeted), "the pin measures content")
    assert bytes_full == bytes_targeted, (directory, sorted(bytes_full), "the same .tf bytes for the unit")


def test_the_printed_form_of_the_unit_agrees_between_the_two_runs(tmp_path):
    """F11.3 (`docs/MULTI_RUN_CODEBASE.md` §2 rule 6): the printed form of the site row is a unit-set file inside the
    directory the row names, so the two runs are compared through `write_path.unit_path` and the names `site_data`
    states. On the committed response set no unit names a value, so both runs write no record row and no printed
    form: the half is measured as agreement on absence. The condition that would make it measure content is content
    that names a device value, which a committed response cannot hold because the device fact a site value names is a
    §4 live-only fact, so the condition is recorded in `backlog.md`.
    """
    full, _parts_full, _index_full = _agreement_run(tmp_path, "full")
    targeted, parts_targeted, index_targeted = _agreement_run(tmp_path, "targeted", SELECTION)

    directory = _agreement_unit(parts_targeted, index_targeted)

    for out in (full, targeted):
        assert not (out / site_data.SITE_DATA_FILE).is_file(), (out, "the run named no value for a site row")
        assert not write_path.unit_path(out, directory, site_data.TFVARS_FILE).is_file(), (
            out,
            directory,
            "no printed form for a unit that names no value",
        )
    assert tf_bytes(full / directory) == tf_bytes(targeted / directory), (
        directory,
        "the unit set is its .tf files plus its printed form, so the two sets agree",
    )


def test_neither_run_writes_a_read_through_block_for_content_that_names_no_read_through_name(tmp_path):
    """F11.3 (`docs/MULTI_RUN_CODEBASE.md` §2 rule 6): the agreement is stated for content that names no read-through
    name, because the read-through branch answers a name the codebase owns and the run read no unit for. That branch
    is F5.5's rule, pinned in `tests/test_data_blocks.py`, so this pin states no read-through rule of its own: it
    reads the block set through `sanity_checks.blocks` and the read-through file name through its owner, and holds
    that the committed content answers nothing for either run, which is what lets the byte agreement cover the unit's
    whole file set.
    """
    full, _parts_full, _index_full = _agreement_run(tmp_path, "full")
    targeted, parts_targeted, index_targeted = _agreement_run(tmp_path, "targeted", SELECTION)

    directory = _agreement_unit(parts_targeted, index_targeted)

    read_through = panorama_to_terraform.TerraformGenerator.READ_THROUGH_FILE
    for out in (full, targeted):
        blocks = sanity_checks.blocks(tf_files(out), ("data",))
        assert not blocks, (out, blocks, "no read-through block for content that names no read-through name")
        unit_file = write_path.unit_path(out, directory, read_through)
        assert not unit_file.is_file(), (
            unit_file,
            "a run that names no read-through name writes no read-through file (F5.5)",
        )
