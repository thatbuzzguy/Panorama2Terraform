"""F6.1: the unit boundary as data, the codebase manifest.

Ten groups, one per rule in `unit_manifest.py` (`docs/CODEBASE_ASSEMBLY.md` §3), the last two for the two unit
sets Piece 11B.2 states (`docs/MULTI_RUN_CODEBASE.md` §2 rule 5) and for the units an update run wrote
(`docs/MULTI_RUN_CODEBASE.md` §4 rule 1), and the last one for the declaration rule (`docs/IMPORT_BINDING.md` §2,
decision 3, taken 2026-11-26):

1. The unit. One row per combination of the five scope facts, built from the ledger
   `entry_coverage.py` already writes, so F6.1 adds no parse data. F8.7: the unit join in
   `api_requests.py` reads this set through `units`, so path 2 states no second unit rule.
2. The directory naming rule. `sanitize(unit name) + '_' + 8-hex digest of the unit identity`,
   always, so a name depends on the unit alone and not on the other units in the run. The §5 fallback word is
   stated once, in `naming.py`, so no module holds a second definition of it.
3. The row shape. Fixed fields in the declared order, rows in identity order, read back as data. The
   row states the scope a unit sits in through the five fact keys, so it names no field for a place, and
   no row carries two container facts. The row also states the mode as the field decision 2 names, read as
   data through `MODE_VALUES`, the pair `import_blocks.py` owns.
4. The reference names, recorded by `name_ref` at the site that applies the reference rule.
5. The no-change rule. The `.tf` bytes, the report bytes, the gate inputs, and the exit codes.
6. The CLI, and the rule that a file is written only when it has content.
7. Determinism. Two runs on the same bytes write the same bytes.
8. The two unit sets, read through the one rule over two row sets.
9. The units an update run wrote: `units` over the rows its own ledger built, so the directories it wrote
   inside are the directories its own set names.
10. The declaration. One pair is one scope path and one value, and it reaches a unit through `units` and the one
   pair between a place and the fact it names, so this module holds no mapping of its own and names no directory.
   The pairs are sorted by name, so no answer depends on the order they were declared. A unit a pair names prints
   that pair's value and a unit no pair names prints `EMPTY_ANSWER`. Two modes for one unit are an input refusal,
   so the run exits 1 and writes no file. The pair shape is the CLI's rule, and the argument is held by the CLI,
   so no rule owner states a flag of its own; the write step reads the answer through this module.

The manifest names the directory; F6.1 does not write one. Every test runs offline.
"""

import argparse
import ast
import contextlib
import hashlib
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import api_requests
import codebase_state
import container_coverage
import entry_coverage
import naming
import ownership
import reference_edges
import sanity_checks
import site_data
import source_fetch
import unit_manifest
import xml_input
from conftest import (
    CODEBASE_FIXTURE,
    DECLARATION_ARGUMENT,
    FIXTURES_DIR,
    GOLDEN_DIR,
    MODE_VALUES,
    PAIR_JOIN,
    RESOURCE_ADDRESS_RE,
    RESPONSES_DIR,
    RUN_FIXTURE,
    SAMPLE_CONFIG,
    SRC_DIR,
    corpus_fixtures,
    data_file_set,
    declaration_args,
    declaration_pairs,
    file_text,
    pair_for,
    pair_text,
    partial_run,
    record_rows,
    run_script,
    tf_bytes,
    tf_files,
    written_bytes,
)

CONVERTER = "panorama_to_terraform.py"
HOST = "panorama.test"
GROUPING = "report_grouping.xml"
MULTI = "multi_device_templates.xml"
NEW_SITE = "template_no_device.xml"
MANIFEST = unit_manifest.MANIFEST_FILE

# The committed pair the two unit sets are read on (Piece 11B.2): the run that builds a whole codebase, and a
# second run that names one unit inside it. Both records are read through `parse_rows`, the one reader of the
# row shape, and the run's own set is read through `units`.

# The reference names the grouping fixture produces, keyed by the referrer's five facts.
GROUPING_REFERENCES = {
    ("", "", "", "", ""): ("IKE-DEFAULT",),
    ("Datacenter-FW", "", "", "", ""): ("IKE-DEFAULT", "IPSEC-DEFAULT"),
    ("Datacenter-FW", "vsys2", "", "", ""): ("IKE-DEFAULT",),
    ("Office-FW", "", "", "", ""): ("IKE-DEFAULT", "IPSEC-DEFAULT"),
}

# The units the grouping fixture shows, in the order the rows sort by the identity.
GROUPING_UNITS = [
    ("", "", "", "", ""),
    ("", "", "", "fw-2.example.com", ""),
    ("", "", "DC-Networks", "", ""),
    ("", "", "DC-Networks", container_coverage.PLACEHOLDER_DEVICE, ""),
    ("", "", "HQ-Networks", "", ""),
    ("", "", "HQ-Networks", "fw-1.example.com", ""),
    ("Datacenter-FW", "", "", "", ""),
    ("Datacenter-FW", "", "", "fw-2.example.com", ""),
    ("Datacenter-FW", "vsys2", "", "", ""),
    ("Office-FW", "", "", "", ""),
    ("Office-FW", "", "", "fw-1.example.com", ""),
]


def _run(source: Path, out_dir: Path, extra: tuple = ()) -> subprocess.CompletedProcess:
    """Run the converter as a script and return the process result."""
    return run_script(CONVERTER, str(source), "--output-dir", str(out_dir), *extra)


def _manifest(out_dir: Path) -> list:
    """A written manifest, read back as data."""
    return unit_manifest.parse_rows((out_dir / MANIFEST).read_text(encoding="utf-8"))


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
        caught["parser"] = self

    def init_generator(self, *args, **kwargs):
        generator_init(self, *args, **kwargs)
        caught["generator"] = self

    saved_argv = list(sys.argv)
    converter_module.PanoramaParser.__init__ = init_parser
    generator_class.__init__ = init_generator
    try:
        sys.argv = [CONVERTER, str(source), "--output-dir", str(out_dir), *[str(a) for a in extra]]
        with contextlib.redirect_stdout(io.StringIO()):
            converter_module.main()
    finally:
        converter_module.PanoramaParser.__init__ = parser_init
        generator_class.__init__ = generator_init
        sys.argv = saved_argv
    return caught["parser"], caught["generator"]


@pytest.fixture
def gen(converter_module, tmp_path):
    """A generator, for the naming rule the manifest reads through it.

    The class the script holds, so the test and the run share one sanitizing rule.
    """
    return converter_module.TerraformGenerator(str(tmp_path / "gen"))


# --- 1. the unit ---------------------------------------------------------------


def test_one_row_per_combination_of_the_five_facts(converter_module, tmp_path):
    """A unit is one combination of the five scope facts, and the rows come from the ledger."""
    parser, _gen = _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    rows = _manifest(tmp_path)
    units = sorted({unit_manifest.facts_of(row) for row in parser.ledger.rows()})
    assert [tuple(row[key] for key in unit_manifest.FACT_KEYS) for row in rows] == units == GROUPING_UNITS
    assert sum(row["entry_count"] for row in rows) == len(parser.ledger.rows())


def test_the_join_reads_the_unit_set_through_this_rule(converter_module, tmp_path):
    """F8.7 (`docs/API_CONVERSION_PATH.md` §3): the unit join reads the run's unit set through `units`, so
    path 2 states no second unit rule and counts no unit a second way. A unit exists only when the ledger has
    a row in it, so a run that read no rows gives the join nothing to answer and nothing to report.
    """
    request = source_fetch.ApiRequest(host=HOST, path="device-group")
    source = source_fetch.fetch(
        request, tmp_path / "read", producer=lambda r: (RESPONSES_DIR / r.cache_name()).read_bytes()
    )
    parser = converter_module.PanoramaParser(source)
    tables = parser.parse_associations()
    parser.parse_device_groups()
    rows = parser.ledger.rows()
    assert rows, "the join needs rows to read"

    pairs = api_requests.join_units(
        api_requests.scope_index(HOST, tables, ("device-group/entry/devices",)), parser.ledger
    )
    units = unit_manifest.units(parser.ledger)
    assert [facts for facts, _entry in pairs] == units, pairs
    assert len(pairs) == len(units), "one answer per unit, so no unit is counted a second way"
    assert len({facts for facts, _entry in pairs}) == len(pairs), "the join reports a unit once"

    # The answer names the index entry the row's source names, read through the name rule in `source_fetch`,
    # so the join holds no field name and no cache name of its own.
    answered = dict(pairs)
    assert all(
        answered[unit_manifest.facts_of(row)].request.cache_name() == row[ownership.SOURCE_FIELD] for row in rows
    ), (answered, rows)

    # A unit exists only when the ledger has a row in it, so the set the join reads is the set the rows show.
    assert set(units) == {unit_manifest.facts_of(row) for row in rows}, (units, rows)

    # Path 2 names no unit rule of its own: the fact order is read through this module.
    source_text = (SRC_DIR / "api_requests.py").read_text(encoding="utf-8")
    assert "unit_manifest.units(" in source_text and "unit_manifest.facts_of(" in source_text
    for key in unit_manifest.FACT_KEYS:
        assert f"'{key}'" not in source_text, (key, "the join names no fact of its own")


def test_the_scope_entry_is_one_of_its_rows(converter_module, tmp_path):
    """A declared scope is a ledger row, so the entry that defines a unit counts inside it.

    F6.5: a scope entry is an object, so the row that defines the unit is an `emitted` row.
    """
    parser, _gen = _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    defining = [row for row in parser.ledger.rows() if unit_manifest.facts_of(row) == ("Datacenter-FW", "", "", "", "")]
    assert [row for row in defining if row["name"] == "Datacenter-FW"]
    assert [row for row in defining if row["destination"] == "emitted"]
    assert _row(_manifest(tmp_path), ("Datacenter-FW", "", "", "", ""))["entry_count"] == len(defining)


def test_the_property_level_is_counted_on_the_parent_row(converter_module, tmp_path):
    """An entry inside a config-object entry is a property level (§3.1), so it is not a row of its
    own: the parent row shows the count.
    """
    parser, _gen = _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    office = [row for row in parser.ledger.rows() if unit_manifest.facts_of(row) == ("Office-FW", "", "", "", "")]
    parent = next(row for row in office if row["name"] == "ethernet1/1")
    assert parent["property_entries"] == 1
    assert "10.1.1.1/24" not in [row["name"] for row in office], "the ip entry is a property level"
    assert _row(_manifest(tmp_path), ("Office-FW", "", "", "", ""))["entry_count"] == len(office)


def test_the_shared_unit_is_the_unit_with_empty_facts_and_is_named_shared(converter_module, tmp_path):
    """`Shared` names the shared section (F3.9). The five facts alone cannot name it, so the row
    states the name.
    """
    _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    row = _row(_manifest(tmp_path), ("", "", "", "", ""))
    assert row["unit"] == unit_manifest.SHARED_UNIT
    assert row["device_group"] == "", "Shared is the name of the unit, not a fact value"


def test_shared_in_device_group_is_not_a_fact_value(converter_module, tmp_path):
    """`Shared` in `device_group` is the parse fallback for an entry the parse cannot place (§2.2),
    so it never enters the identity. The state scan holds the same rule.
    """
    parser, _gen = _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    entry = next(row for row in parser.ledger.rows() if row["name"] == "ethernet1/9")
    assert entry["device_group"] == ""
    object_facts = {"device_group": "Shared", "vsys": "", "template": "", "vsys_device": "", "template_stack": ""}
    assert unit_manifest.facts_of(object_facts) == unit_manifest.facts_of(entry)


def test_a_template_entry_no_device_names_keeps_the_device_fact_empty(converter_module, tmp_path):
    """E10.3 (`docs/TEMPLATE_STACK_DEPLOYMENT.md` §4): the shape a new site takes in an export is a template
    entry with no device inside it, so the parse records no device for the unit and the row keeps the device fact
    as the empty fact. The entry is read as an `emitted` scope row, so the unit exists and the row is written for
    it. `Shared` in `device_group` is the parse fallback (§2.2), so the row states no device group for the entry
    either: the device group lists the entry, and the entry names no group. The identity, the digest, and the
    directory name are read from the four facts the export can name, so no part of them holds a device value the
    run did not read.
    """
    parser, gen = _pipeline(converter_module, FIXTURES_DIR / NEW_SITE, tmp_path)
    entry = parser.root.find("panorama/templates").find("entry")
    facts = unit_manifest.facts_of(parser.identity_of(entry))
    assert facts == ("", "", "Remote-Networks", "", ""), facts
    assert any(unit_manifest.facts_of(row) == facts for row in parser.ledger.rows()), "the unit has no ledger row"
    row = _row(_manifest(tmp_path), facts)
    assert row["unit"] == unit_manifest.unit_name(facts) == "Remote-Networks", row
    assert row["directory"] == unit_manifest.directory_name(facts, gen.sanitize_name), row
    assert row["directory"].endswith(f"_{unit_manifest.identity_digest(facts)}"), row


def test_the_rows_are_sorted_by_the_identity_not_by_document_order(converter_module, tmp_path):
    """The sort is the identity order, so it is a total order and does not depend on document order.
    The grouping fixture puts the device groups first in the file.
    """
    _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    rows = _manifest(tmp_path)
    assert [tuple(row[key] for key in unit_manifest.FACT_KEYS) for row in rows] == GROUPING_UNITS
    assert rows[0]["device_group"] == "" and rows[-1]["device_group"] == "Office-FW"


# --- 2. the directory naming rule --------------------------------------------


def test_the_directory_name_is_the_sanitized_name_plus_the_digest(gen, tmp_path):
    """The §5 shape, read through `TerraformGenerator.sanitize_name`, so no second naming rule
    exists here.
    """
    _run(FIXTURES_DIR / GROUPING, tmp_path)
    rows = _manifest(tmp_path)
    shared = hashlib.sha256(b"||||").hexdigest()[:8]
    assert _row(rows, ("", "", "", "", ""))["directory"] == f"{gen.sanitize_name('Shared')}_{shared}"

    facts = ("Datacenter-FW", "vsys2", "", "", "")
    digest = hashlib.sha256(b"Datacenter-FW|vsys2|||").hexdigest()[:8]
    assert _row(rows, facts)["directory"] == f"{gen.sanitize_name('vsys2')}_{digest}"


def test_the_manifest_defines_no_second_sanitize_or_naming_rule():
    """The manifest takes the §5 sanitizing rule as an argument, so the rule it owns is the identity
    digest and the unit name only.
    """
    assert not any(hasattr(unit_manifest, name) for name in ("sanitize_name", "sanitize", "name_ref"))


def test_a_name_that_sanitizes_to_nothing_keeps_the_shape(gen):
    """§5: an empty name becomes `unnamed`, so a directory name is never empty, and the shape a name
    sanitizes to is the §5 shape, not a second rule.
    """
    facts = ("!", "", "", "", "")
    assert unit_manifest.directory_name(facts, gen.sanitize_name) == f"unnamed_{unit_manifest.identity_digest(facts)}"
    facts = ("Sales & Eng", "", "", "", "")
    assert gen.sanitize_name("Sales & Eng") == "sales___eng"
    assert (
        unit_manifest.directory_name(facts, gen.sanitize_name) == f"sales___eng_{unit_manifest.identity_digest(facts)}"
    )


def test_the_word_prints_the_same_string_at_both_print_sites(tmp_path):
    """§5 rule 2 as content: the two sites that name a thing with no name print the same word for one unit.

    A source scan cannot show which definition answered, because two definitions of one word print the same
    string, so the pin that fails before the change is `test_the_fallback_word_is_stated_once_in_src`. This pin
    measures the content the rule prints: the unit directory name `generate_units` wrote, and the block name the
    run printed in that directory, for content whose name sanitizes to nothing. Both come from `naming.UNNAMED`.
    """
    source = tmp_path / "no_name.xml"
    source.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<config>\n  <templates>\n'
        '    <entry name="!"><devices><entry name="fw-2.example.com"/></devices>\n'
        "      <network><address>\n"
        '        <entry name="!"><type>IP</type><ip-net-block>10.0.0.1</ip-net-block></entry>\n'
        "      </address></network>\n    </entry>\n  </templates>\n</config>\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    result = _run(source, out)
    assert result.returncode == 0, result.stdout + result.stderr

    facts = ("", "", "!", "", "")
    row = _row(_manifest(out), facts)
    # The unit half: the §5 shape of the unit name, with the owner's fallback.
    directory = row["directory"]
    assert (
        directory == f"{naming.sanitize(unit_manifest.unit_name(facts)) or naming.UNNAMED}"
        f"_{unit_manifest.identity_digest(facts)}"
    ), row

    # The block half, read from the bytes the run wrote in that directory.
    text = file_text(tf_files(out), "scope.tf")
    address = RESOURCE_ADDRESS_RE.search(text).group(2)
    assert address.startswith(f"{naming.UNNAMED}_"), (address, text)
    assert address != directory, (address, directory, "the digest is the entry identity, not the unit identity")


def test_the_fallback_word_is_stated_once_in_src():
    """§5 rule 2: `naming.UNNAMED` is the one statement of the fallback word, so no module states it twice.

    A source scan, for the reason `acceptance.md` records: two definitions print the same string, so no run can
    show which definition answered. The content half is
    `test_the_word_prints_the_same_string_at_both_print_sites`, which measures the word a run wrote at both
    places, and `tests/test_robustness.py::test_declare_empty_name_gets_a_stable_name`, which measures the shape
    the word prints for a name.
    """
    holders = {}
    for path in sorted(SRC_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        held = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and node.value == unit_manifest.UNNAMED
        ]
        if held:
            holders[path.name] = len(held)
    assert holders == {"naming.py": 1}, holders
    # The two readers read the word through the owner, so the rule has one place.
    for name in ("unit_manifest.py", "panorama_to_terraform.py"):
        text = (SRC_DIR / name).read_text(encoding="utf-8")
        assert "naming.UNNAMED" in text or "from naming import UNNAMED" in text, name


def test_the_digest_is_always_present_not_only_on_a_collision(converter_module, tmp_path):
    """A collision-only rule would make one unit's name depend on the other units in the run, so an
    unrelated scope would move an existing directory. The digest is always in the name.
    """
    _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    rows = _manifest(tmp_path)
    for row in rows:
        facts = tuple(row[key] for key in unit_manifest.FACT_KEYS)
        assert row["directory"].rsplit("_", 1)[1] == unit_manifest.identity_digest(facts)
    # Two units that sanitize to the same base stay apart, by the digest alone.
    same_base = [row for row in rows if row["unit"] == "fw-2.example.com"]
    assert len(same_base) == 2 and len({row["directory"] for row in same_base}) == 2


def test_a_directory_name_does_not_move_when_an_unrelated_unit_is_added(tmp_path):
    """The name depends on the unit alone, so the same unit in two different runs gets the same
    directory name. The multi fixture names the stack unit, which the grouping fixture does not.
    """
    _run(FIXTURES_DIR / GROUPING, tmp_path / "first")
    _run(FIXTURES_DIR / MULTI, tmp_path / "second")
    unit = ("Datacenter-FW", "", "", "", "")
    first = _row(_manifest(tmp_path / "first"), unit)
    second = _row(_manifest(tmp_path / "second"), unit)
    assert first["directory"] == second["directory"]
    assert first["unit"] == second["unit"]


def test_the_deepest_declared_scope_names_the_unit(converter_module, tmp_path):
    """The unit name is the deepest scope the export declares, in the F3.9 level order."""
    _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    rows = _manifest(tmp_path)
    assert _row(rows, ("Datacenter-FW", "vsys2", "", "", ""))["unit"] == "vsys2"
    assert _row(rows, ("", "", "HQ-Networks", "", ""))["unit"] == "HQ-Networks"
    assert _row(rows, ("", "", "HQ-Networks", "fw-1.example.com", ""))["unit"] == "fw-1.example.com"


def test_the_stack_names_its_unit(converter_module, tmp_path):
    """F6.10.5: the fifth fact is the scope a stack names, so the entry that defines a stack names a
    unit. The level order is read on the shapes the export can hold, so the pair measured here is the vsys
    inside a template, not a template inside a stack: a template entry and a stack entry name no container
    (`docs/TEMPLATE_STACK_DEPLOYMENT.md` §3).

    `tests/fixtures/scope_objects.xml` is the fixture that carries the stack entry and the variable
    inside it, so the run names the stack unit and counts both entries in it.
    """
    _pipeline(converter_module, FIXTURES_DIR / "scope_objects.xml", tmp_path)
    rows = _manifest(tmp_path)
    stack = ("", "", "", "", "Edge-Stack")
    row = _row(rows, stack)
    assert row["unit"] == "Edge-Stack"
    assert row["directory"] == f"edge_stack_{unit_manifest.identity_digest(stack)}"
    assert row["entry_count"] == 2, "the stack entry and the variable inside it"
    # The level order, read innermost first: a vsys inside a template names its vsys.
    assert unit_manifest.named_fact(("", "edge-vsys", "Edge-Networks", "", "")) == ("vsys", "edge-vsys")
    assert unit_manifest.named_fact(stack) == ("template_stack", "Edge-Stack")


def test_the_placeholder_device_names_no_unit(converter_module, tmp_path):
    """F3.5: `localhost.localdomain` names no firewall, so the unit takes the scope above it."""
    _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    row = _row(_manifest(tmp_path), ("", "", "DC-Networks", container_coverage.PLACEHOLDER_DEVICE, ""))
    assert row["unit"] == "DC-Networks"
    assert row["vsys_device"] == container_coverage.PLACEHOLDER_DEVICE


# --- 3. the row shape ---------------------------------------------------------


def test_the_row_fields_are_the_declared_shape_in_order(tmp_path):
    """The row is data, so the field order is fixed and a document describes it without restating a
    row.
    """
    assert unit_manifest.FIELD_ORDER == (
        "unit",
        "mode",
        "device_group",
        "vsys",
        "template",
        "vsys_device",
        "template_stack",
        "directory",
        "entry_count",
        "references",
        "rank",
        "after",
    )
    _run(FIXTURES_DIR / GROUPING, tmp_path)
    text = (tmp_path / MANIFEST).read_text(encoding="utf-8")
    assert list(json.loads(text)[0]) == list(unit_manifest.FIELD_ORDER)
    # Fields print in the declared order, not alphabetically.
    assert text.index('"unit"') < text.index('"mode"') < text.index('"device_group"')
    assert text.index('"device_group"') < text.index('"directory"')
    # F6.3 rule 5: the two order fields print after the F6.1 fields.
    assert text.index('"references"') < text.index('"rank"') < text.index('"after"')


def test_the_row_states_placement_through_the_fact_keys_it_already_reads(converter_module, tmp_path):
    """Piece E10.2: the row needs no field for the scope a unit sits in, because the five fact keys are that
    fact. A template unit and a stack unit read with no container fact, so the placement answer is the fact
    key that names the entry itself plus the container keys left empty (`docs/TEMPLATE_STACK_DEPLOYMENT.md` §3).

    Measured on `tests/fixtures/scope_objects.xml`: the parse records `Shared` for the group of each of these
    two entries, which is the §2.2 fallback and not a fact value, so both rows read empty.
    """
    _pipeline(converter_module, FIXTURES_DIR / "scope_objects.xml", tmp_path)
    rows = _manifest(tmp_path)
    template = _row(rows, ("", "", "Edge-Networks", "", ""))
    stack = _row(rows, ("", "", "", "", "Edge-Stack"))
    for row in (template, stack):
        assert row["device_group"] == "", row
    assert template["template"] == "Edge-Networks" and template["template_stack"] == "", template
    assert stack["template_stack"] == "Edge-Stack" and stack["template"] == "", stack
    # The declared shape names no field for a place: the fact keys, then the run facts. `mode` is a run fact,
    # the field decision 2 names for the plan outcome, so it is in the second list and no fact key holds it.
    assert [field for field in unit_manifest.FIELD_ORDER if field not in unit_manifest.FACT_KEYS] == [
        "unit",
        "mode",
        "directory",
        "entry_count",
        "references",
        "rank",
        "after",
    ]


def test_no_row_carries_two_container_facts(converter_module, tmp_path):
    """The level order reads a row from the deepest declared scope inward, so a row that carried both the
    `template` and the `template_stack` fact would be a template inside a stack. Piece E10.2 decides that a
    template entry and a stack entry name no container, so no row can carry both. Measured across the fixture
    corpus, no run builds such a row.
    """
    for name in corpus_fixtures():
        fixture = FIXTURES_DIR / name
        parser, _generator = _pipeline(converter_module, fixture, tmp_path / fixture.stem)
        for facts in {unit_manifest.facts_of(row) for row in parser.ledger.rows()}:
            assert not (
                facts[unit_manifest.FACT_KEYS.index("template")]
                and facts[unit_manifest.FACT_KEYS.index("template_stack")]
            ), (
                name,
                facts,
            )


def test_the_manifest_round_trips_as_data(gen, tmp_path):
    """A reader reads the file back as itself, the way `provenance.parse_record` reads a record."""
    _run(FIXTURES_DIR / GROUPING, tmp_path)
    rows = _manifest(tmp_path)
    assert rows and all(set(row) == set(unit_manifest.FIELD_ORDER) for row in rows)
    for row in rows:
        facts = tuple(row[key] for key in unit_manifest.FACT_KEYS)
        assert row["unit"] == unit_manifest.unit_name(facts)
        assert row["directory"] == unit_manifest.directory_name(facts, gen.sanitize_name)


def test_a_row_that_is_not_the_declared_shape_is_refused():
    """The manifest is data, so a reader cannot fall back to reading prose."""
    good = {
        "unit": "Shared",
        "mode": "",
        "device_group": "",
        "vsys": "",
        "template": "",
        "vsys_device": "",
        "template_stack": "",
        "directory": "shared_45ca31c3",
        "entry_count": 2,
        "references": [],
        "rank": 1,
        "after": [],
    }
    assert unit_manifest.parse_rows(json.dumps([good]))[0]["directory"] == "shared_45ca31c3"
    bad_rows = (
        json.dumps({"unit": "Shared"}),  # not a list of rows
        json.dumps(["Shared"]),  # a row that is not an object
        json.dumps([dict(good, source_line=4)]),  # a field the shape does not declare
        json.dumps([{key: value for key, value in good.items() if key != "entry_count"}]),
        json.dumps([dict(good, entry_count="2")]),
        json.dumps([dict(good, references="IKE-DEFAULT")]),
        json.dumps([dict(good, vsys=None)]),
        # Decision 2 (2026-11-25): `mode` is a declared field, so a value outside the pair is a refusal.
        json.dumps([dict(good, mode="bound")]),
        json.dumps([dict(good, rank="1")]),  # F6.3: rank is a position
        json.dumps([dict(good, after="shared_45ca31c3")]),  # F6.3: after is a list of directories
    )
    for bad in bad_rows:
        with pytest.raises(ValueError):
            unit_manifest.parse_rows(bad)


def test_the_mode_field_reads_back_as_a_value_of_the_pair_through_its_owner(tmp_path):
    """Decision 2 (`docs/IMPORT_BINDING.md` §2, taken 2026-11-25): the mode is a field of this row. The two values
    are data in `import_blocks.py`, the owner decision 1 names, so this module states the field and reads the pair
    through that owner instead of naming the values a second time. The answer for a unit the run did not mark is
    stated once here as `EMPTY_ANSWER`, in the style of `provenance.py` rule 1, so one shape reads.

    Measured 2026-11-25 on `SAMPLE_CONFIG` run through the script: no argument declares a mode yet (decision 3), so
    every row states the answer for a unit the run did not mark. A mode is read as data by writing the row through
    `render` and reading it back through `parse_rows`: each value of the pair, and the empty answer, reads back as
    itself, and a value outside the pair is refused.
    """
    _run(SAMPLE_CONFIG, tmp_path)
    rows = _manifest(tmp_path)
    assert rows, "the pin reads a record with content"
    for row in rows:
        assert row["mode"] == unit_manifest.EMPTY_ANSWER, row
    for value in MODE_VALUES + (unit_manifest.EMPTY_ANSWER,):
        row = dict(rows[0], mode=value)
        assert unit_manifest.parse_rows(unit_manifest.render([row]))[0]["mode"] == value, value
    with pytest.raises(ValueError):
        unit_manifest.parse_rows(unit_manifest.render([dict(rows[0], mode="bound")]))

    # The field is stated once, in this module, and the values are stated once, in their owner.
    source = (SRC_DIR / "unit_manifest.py").read_text(encoding="utf-8")
    assert "import_blocks.MODE_VALUES" in source, "the reader reads the pair through its owner"
    for value in MODE_VALUES:
        assert f'"{value}"' not in source, (value, "the reader states a value its owner states")


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
    data_files = {MANIFEST, ownership.OWNERSHIP_FILE, reference_edges.EDGE_FILE, site_data.SITE_DATA_FILE}
    assert not any(p.name.endswith(".json") and p.name not in data_files for p in tmp_path.iterdir())
    # F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): the directory name the row decides is the directory the run
    # writes, so the codebase root holds the records and each unit directory holds the unit set.
    assert sorted(p.name for p in tmp_path.iterdir() if p.is_dir()) == sorted(row["directory"] for row in rows), (
        "one directory per unit the row names"
    )


# --- 4. the reference names ---------------------------------------------------


def test_the_reference_names_are_recorded_for_the_referrers_facts(converter_module, tmp_path):
    """The names `name_ref` could not resolve inside the referrer's own unit, keyed by the referrer's
    five scope facts, and printed sorted.
    """
    _parser, generator = _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    assert generator.unit_references() == GROUPING_REFERENCES
    rows = _manifest(tmp_path)
    for facts, names in GROUPING_REFERENCES.items():
        assert _row(rows, facts)["references"] == list(names)
    for row in rows:
        assert row["references"] == sorted(row["references"])


def test_a_contextless_call_site_records_the_name_for_the_referrers_unit(converter_module, tmp_path):
    """The VPN sites resolve with no call-site context, so the referrer sits in the shared unit and the
    name is recorded for it; the office referrer records for its own unit.
    """
    _parser, generator = _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    shared = ("", "", "", "", "")
    office = ("Office-FW", "", "", "", "")
    assert generator.unit_references()[shared] == ("IKE-DEFAULT",)
    assert "IPSEC-DEFAULT" in generator.unit_references()[office]


def test_a_name_the_referrers_unit_declares_is_not_recorded(converter_module, tmp_path):
    """GW-Common is declared inside the unit the referrer belongs to, so the name resolves there and is
    not recorded. A name recorded for the shared unit comes from a referrer in the shared section.
    """
    _parser, generator = _pipeline(converter_module, FIXTURES_DIR / GROUPING, tmp_path)
    recorded = {name for names in generator.unit_references().values() for name in names}
    assert "GW-Common" not in recorded
    assert "GW-Shared" not in recorded
    assert recorded == {"IKE-DEFAULT", "IPSEC-DEFAULT"}


def test_the_record_names_the_referrers_unit_not_the_declaring_unit(gen):
    """Two devices declare `ethernet1/1`, and the referrer names no unit, so the name stays plain. The
    record keys it by the referrer's unit, never by the unit that declared it, because the reference
    fact is the referrer's. The edge list (F6.3) is the feature that names the other unit, so this
    record keeps one fact, and the case is recorded here.
    """
    gen.generate_interfaces(
        [
            {
                "name": "ethernet1/1",
                "type": "ethernet",
                "mode": "layer3",
                "device_group": "Shared",
                "vsys": "",
                "template": "",
                "vsys_device": "fw-1.example.com",
            },
            {
                "name": "ethernet1/1",
                "type": "ethernet",
                "mode": "layer3",
                "device_group": "Shared",
                "vsys": "",
                "template": "",
                "vsys_device": "fw-2.example.com",
            },
        ]
    )
    router = {
        "name": "vr-shared",
        "type": "virtual-router",
        "vsys": "",
        "template": "",
        "vsys_device": "",
        "interfaces": ["ethernet1/1"],
    }
    gen.generate_virtual_routers([router])
    text = file_text(tf_files(gen.output_dir), "virtual_routers.tf")
    assert "panos_ethernet_interface." not in text
    assert "data.panos_ethernet_interface" not in text
    assert gen.unit_references() == {("", "", "", "", ""): ("ethernet1/1",)}


def test_a_read_through_name_is_recorded(converter_module, tmp_path):
    """A name that became a read-through `data` block (F5.5) is an outside name, so the row states
    it. Every block the run writes is one recorded name.
    """
    _parser, generator = _pipeline(
        converter_module, SAMPLE_CONFIG, tmp_path, ("--data-blocks", "panos_address,panos_zone")
    )
    blocks = [
        line.split(" = ")[1].strip('"')
        for line in file_text(tf_files(tmp_path), "read_through.tf").splitlines()
        if line.startswith("  name = ")
    ]
    recorded = {name for names in generator.unit_references().values() for name in names}
    assert blocks and set(blocks) <= recorded
    assert "any" in recorded


def test_every_recorded_name_belongs_to_a_unit_the_ledger_shows(converter_module, tmp_path):
    """The row set is the units the ledger shows, so a recorded name cannot name a unit the run did
    not read. Pinned across the fixture corpus.
    """
    # The read rule's accepted set, so an accepted fixture cannot fail here.
    for name in corpus_fixtures():
        fixture = FIXTURES_DIR / name
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
    row = _row(_manifest(tmp_path), ("Production-DG", "", "", "localhost.localdomain", ""))
    assert row["references"].count("any") == 1
    assert row["references"] == sorted(row["references"])


# --- 5. the no-change rule ----------------------------------------------------


def test_the_generated_tf_bytes_are_unchanged(tmp_path):
    """Both golden cases write the same bytes as the committed goldens."""
    for case, source in (("sample", SAMPLE_CONFIG), ("kitchen_sink", FIXTURES_DIR / "kitchen_sink.xml")):
        out = tmp_path / case
        proc = _run(source, out)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        goldens = tf_bytes(GOLDEN_DIR / case)
        generated = tf_bytes(out)
        # Both sets must hold content, or the comparison measures nothing.
        # The tool reads inputs through tests/conftest.py (see the module header).
        assert goldens, (case, "the golden case holds no .tf content to compare")
        assert generated, (case, "the run wrote no .tf content")
        assert generated == goldens, case


def test_the_gate_reads_the_manifest_through_unit_manifest(tmp_path):
    """F6.8 changed the file set: the block rules read the `.tf` files, and the data rule reads the data files,
    each through the module that owns the row shape, so no second shape rule appears. The report counts the two
    sets separately, and the data rule reports no finding on a manifest the tool wrote.

    The count names the four records at the codebase root plus the rule data pair's data member inside each unit
    directory its own rows name, so it is read through the shared derivation `conftest.data_file_set` and not a
    number this module states: the sample run writes the manifest and the ownership record at the root, and the
    pair's data member for 2 rule types inside the unit its rows name, so 4.
    """
    _run(SAMPLE_CONFIG, tmp_path)
    files = sanity_checks.read_tf_files(tmp_path)
    assert files and all(name.endswith(".tf") for name in files), "the block reader is .tf-only"
    assert dict(sanity_checks.DATA_FILES)[MANIFEST] is unit_manifest
    assert not hasattr(unit_manifest, "check"), "the manifest owns no gate check"
    report = sanity_checks.run_checks(tmp_path)
    assert [result.check for result in report.checks] == list(sanity_checks.CHECK_ORDER)
    assert report.file_count == len(files)
    assert report.data_file_count == len(data_file_set(tmp_path)), report.render()
    assert MANIFEST in data_file_set(tmp_path), "the manifest is one of the files the count names"
    assert report.findings("data_files") == []
    checked = f"Files checked: 14 .tf files, {len(data_file_set(tmp_path))} data files."
    assert checked in report.render(), report.render()


def test_no_report_names_a_field_the_manifest_states(tmp_path):
    """The manifest is a data file, not a report body: no report names it or restates a row."""
    _run(SAMPLE_CONFIG, tmp_path)
    for name in (
        entry_coverage.REPORT_FILE,
        "MANUAL_SETUP_REPORT.txt",
        "INTERFACE_MIGRATION_REPORT.txt",
        "SANITY_REPORT.txt",
        "SOURCE.txt",
        "README.md",
    ):
        path = tmp_path / name
        if not path.is_file():
            continue  # a report is written only when it has content
        text = path.read_text(encoding="utf-8")
        assert MANIFEST not in text, name
        assert "entry_count" not in text, name


def test_the_exit_codes_are_unchanged(tmp_path):
    """0 when the gate reports no FAIL finding, 1 for an input refusal, 2 for an argument error."""
    assert _run(SAMPLE_CONFIG, tmp_path / "run").returncode == 0
    assert _run(tmp_path / "missing.xml", tmp_path / "refused").returncode == 1
    assert not (tmp_path / "refused" / MANIFEST).is_file(), "a refusal writes no manifest"
    assert run_script(CONVERTER, str(SAMPLE_CONFIG), "--offline").returncode == 2
    assert run_script(CONVERTER, str(SAMPLE_CONFIG), "--data-blocks", "panos_made_up").returncode == 2


# --- 6. the CLI and the content rule ------------------------------------------


def test_a_plain_run_writes_the_manifest_without_a_flag(tmp_path):
    """The unit boundary is a fact of every run, so the manifest is not opt-in and the CLI takes no
    flag for it.
    """
    assert "manifest" not in run_script(CONVERTER, "--help").stdout.lower()
    assert _run(SAMPLE_CONFIG, tmp_path).returncode == 0
    assert (tmp_path / MANIFEST).is_file()
    assert _manifest(tmp_path)


def test_the_manifest_is_written_only_when_it_has_content(tmp_path):
    """A run that read no entry writes no manifest, and the record is still written."""
    empty = tmp_path / "empty.xml"
    empty.write_text('<?xml version="1.0"?>\n<config>\n<device-group/>\n</config>\n', encoding="utf-8")
    out = tmp_path / "out"
    assert _run(empty, out).returncode == 0
    assert not (out / MANIFEST).is_file()
    assert (out / "SOURCE.txt").is_file()


# --- 7. determinism -------------------------------------------------------------


def test_two_runs_write_the_same_bytes(tmp_path):
    """The rows are sorted by the identity and the names are sorted, so two runs on the same input
    write the same bytes.
    """
    first, second = tmp_path / "run1", tmp_path / "run2"
    assert _run(FIXTURES_DIR / GROUPING, first).returncode == 0
    assert _run(FIXTURES_DIR / GROUPING, second).returncode == 0
    assert (first / MANIFEST).read_bytes() == (second / MANIFEST).read_bytes()


def test_the_manifest_names_no_path_and_no_timestamp(tmp_path):
    """Two runs on the same bytes from different output directories write the same bytes, so no
    field states where the run wrote them or when.
    """
    first, second = tmp_path / "a" / "out", tmp_path / "b" / "out"
    assert _run(SAMPLE_CONFIG, first).returncode == 0
    assert _run(SAMPLE_CONFIG, second).returncode == 0
    assert (first / MANIFEST).read_bytes() == (second / MANIFEST).read_bytes()
    text = (first / MANIFEST).read_text(encoding="utf-8")
    assert str(tmp_path) not in text
    assert "timestamp" not in text


# --- 8. the two unit sets (Epic 11, Piece 11B.2) --------------------------------


def test_the_codebase_unit_set_is_read_through_the_one_unit_rule(converter_module, tmp_path):
    """Rule 4 read both ways: the run's set is `units` over the rows its own ledger read, and the codebase's set
    is the same rule over the rows a record read back through `parse_rows`. The same run answered through its
    ledger and read back through its record answers the same units, so the piece states one rule and no second
    unit set, and this pin states no row shape of its own: `units` reads a row through `facts_of`, the shape rule
    both sides use, and a row set is one row per unit.

    Measured 2026-11-22 on `address_objects.xml` run through the pipeline in process.
    """
    out = tmp_path / "run"
    parser, _gen = _pipeline(converter_module, FIXTURES_DIR / RUN_FIXTURE, out)
    rows = _manifest(out)
    assert rows, "the pin reads a record with content"

    run_set = unit_manifest.units(parser.ledger)
    read_back = unit_manifest.units(rows)
    assert run_set == read_back, (run_set, read_back, "one rule answers the same units for both row sets")
    assert [tuple(row[key] for key in unit_manifest.FACT_KEYS) for row in rows] == read_back, (
        "one row per unit, so the row set read back is the unit set",
    )

    # The rule reads a row through the shape rule this module owns, so a reader that has no ledger and no record
    # names no unit: the codebase set for a codebase with no manifest record is the empty set.
    rule = Path(unit_manifest.__file__).read_text(encoding="utf-8")
    assert "facts_of(" in rule[rule.index("def units(") :], "the rule reads the row through its own shape rule"
    assert unit_manifest.units([]) == [], "no row, so no unit"


def test_the_two_unit_sets_differ_only_by_the_units_read_through_the_record(converter_module, tmp_path):
    """The two facts, read through the one rule over two row sets: the run's set is `units` over its own ledger,
    and the codebase's set is `units` over the merged manifest rows read through `parse_rows`. The run's set is
    inside the codebase's set, because the merge replaces the rows for the units the run built, and the units the
    codebase set names that the run set does not are the units the run read only through the record: for each of
    them the merged row is the row as the record states it, not a row the run built. For a run that read nothing
    from the record the two sets are the same set, which is the single-run case every committed golden measures,
    so no committed golden moves.

    Measured 2026-11-22 on the committed pair: the kitchen-sink run as the codebase and the
    `address_objects.xml` run as the second run, 11 units against 1, so the difference is 10.
    """
    codebase_out, run_out = tmp_path / "codebase", tmp_path / "run"
    assert _run(FIXTURES_DIR / CODEBASE_FIXTURE, codebase_out).returncode == 0
    parser, _gen = _pipeline(converter_module, FIXTURES_DIR / RUN_FIXTURE, run_out)
    codebase_rows, run_rows = _manifest(codebase_out), _manifest(run_out)
    assert codebase_rows and run_rows, "both pins read a record with content"

    record = next(entry for entry in codebase_state.JOIN_KEYS if entry[0] is unit_manifest)
    merged = codebase_state.merge_rows(record, codebase_rows, run_rows)

    codebase_set = unit_manifest.units(codebase_rows)
    run_set = unit_manifest.units(parser.ledger)
    merged_set = unit_manifest.units(merged)
    assert len(codebase_set) == 11 and len(run_set) == 1, (codebase_set, run_set)
    assert set(run_set) <= set(merged_set), "the units the run built are inside the codebase's set"

    only_through_record = [facts for facts in merged_set if facts not in set(run_set)]
    assert len(only_through_record) == 10, only_through_record
    for facts in only_through_record:
        row = next(row for row in merged if tuple(row[key] for key in unit_manifest.FACT_KEYS) == facts)
        assert row in codebase_rows and row not in run_rows, (facts, "the run read this unit only through the record")

    # The single-run case: a run that read nothing from the record names no unit through a record, so the merged
    # set is its own set and the difference between the two sets is empty.
    assert unit_manifest.units(codebase_state.merge_rows(record, [], codebase_rows)) == codebase_set
    assert unit_manifest.units(codebase_state.merge_rows(record, [], run_rows)) == run_set


# --- 9. The units an update run wrote (Epic 11, Piece 11C.1) -------------------


def test_the_units_the_run_names_are_the_units_it_wrote_files_inside(converter_module, tmp_path):
    """§4 rule 1: the units an update run wrote are `unit_manifest.units` over the rows its own ledger built, and the
    units it read only through the record are the same rule over the merged rows. The run states no second unit set,
    so the directories it wrote inside are the directories its own set names, read through `directory_name` and the
    sanitize rule in `naming.py`, the one naming rule `write_path` uses for both sets.

    Measured 2026-11-22 on the committed pair through `tests/conftest.py`: the kitchen-sink run is the codebase and
    `address_objects.xml` is the second run. The run's own set names 1 unit, `shared_45ca31c3`, and the merged set
    names 11, so the difference is the 10 units the run read only through the record. Inside the 1 directory its own
    set names the tree holds 12 files and 1 byte differs from the first run, `shared_45ca31c3/address_objects.tf`,
    the file the run wrote. Inside the 10 directories only the merged set names, all 60 bytes are the bytes the first
    run wrote and no file there is new.
    """
    codebase_dir, partial_dir, second = partial_run(CODEBASE_FIXTURE, RUN_FIXTURE, tmp_path)
    codebase_rows = record_rows(codebase_dir)[unit_manifest]
    run_rows = record_rows(partial_dir)[unit_manifest]
    assert codebase_rows and run_rows, "both sets read a record with content"

    record = next(entry for entry in codebase_state.JOIN_KEYS if entry[0] is unit_manifest)
    merged_set = set(unit_manifest.units(codebase_state.merge_rows(record, codebase_rows, run_rows)))
    run_set = set(unit_manifest.units(second.ledger))
    assert run_set <= merged_set and len(merged_set) - len(run_set) == 10, (run_set, merged_set)

    run_dirs = {unit_manifest.directory_name(facts, naming.sanitize) for facts in run_set}
    merged_dirs = {unit_manifest.directory_name(facts, naming.sanitize) for facts in merged_set}
    assert sorted(run_dirs) == ["shared_45ca31c3"], run_dirs

    before, after = written_bytes(codebase_dir), written_bytes(partial_dir)
    inside = sorted(key for key in after if Path(key).parent.name in run_dirs)
    assert len(inside) == 12, inside
    assert [key for key in inside if after[key] != before.get(key)] == ["shared_45ca31c3/address_objects.tf"], (
        "the run wrote one file inside the directory its own set names",
    )
    outside = sorted(key for key in after if Path(key).parent.name in merged_dirs - run_dirs)
    assert len(outside) == 60, outside
    assert outside == sorted(key for key in before if Path(key).parent.name in merged_dirs - run_dirs), (
        "the run wrote no new file inside a unit its own set does not name",
    )
    assert all(after[key] == before[key] for key in outside), (
        "every byte inside those 10 directories is the byte the first run wrote",
    )


# --- 10. The declaration names units (Epic 14, Piece 14A.3) -------------------


def test_the_declaration_names_the_units_inside_the_scope_through_the_one_unit_rule(tmp_path):
    """Rule 6: one pair is one scope path and one value, and it reaches a unit through the one unit rule and the
    one pair between a place and the fact it names, so this module holds no mapping of its own and the declaration
    names no directory.

    Measured 2026-11-26 on `GROUPING` run through the script and read back through `parse_rows`: the rows show 5
    pairs, and the pairs name 3, 2, 2, 2 and 2 units through `units`, which is the whole set of 11 with no unit
    named by two pairs. The pair for `Datacenter-FW` names `Datacenter-FW`, `fw-2.example.com` and `vsys2` through
    `unit_name`, and the pair for `HQ-Networks` names `HQ-Networks` and `fw-1.example.com`, so a pair names the
    units inside the place as well as the place itself. `pair_parts` reads the place, the entry segment and the
    fact through `container_coverage`, so the pair is stated once there, and the scan finds no dict literal in
    `unit_manifest.py` whose keys are all places.
    """
    _run(FIXTURES_DIR / GROUPING, tmp_path)
    rows = _manifest(tmp_path)
    pairs = declaration_pairs(rows, MODE_VALUES[0])
    assert len(pairs) == 5, pairs

    named = {}
    for pair in pairs:
        key, name = unit_manifest.pair_parts(pair[0])
        assert key == container_coverage.fact_of_place(container_coverage.path_place(pair[0])), pair
        units = [facts for facts in unit_manifest.units(rows) if unit_manifest.fact(facts, key) == name]
        named[pair[0]] = sorted(unit_manifest.unit_name(facts) for facts in units)
    assert named == {
        "device-group/entry/Datacenter-FW": ["Datacenter-FW", "fw-2.example.com", "vsys2"],
        "device-group/entry/Office-FW": ["Office-FW", "fw-1.example.com"],
        "devices/entry/fw-2.example.com": ["fw-2.example.com", "fw-2.example.com"],
        "templates/entry/DC-Networks": ["DC-Networks", "DC-Networks"],
        "templates/entry/HQ-Networks": ["HQ-Networks", "fw-1.example.com"],
    }, named
    assert sum(len(units) for units in named.values()) == len(list(unit_manifest.units(rows))), named
    assert named["device-group/entry/Datacenter-FW"] == ["Datacenter-FW", "fw-2.example.com", "vsys2"], named

    # The pair is stated once in its owner, and the rule names no directory, so a declaration cannot move a file.
    source = (SRC_DIR / "unit_manifest.py").read_text(encoding="utf-8")
    for word in (
        "container_coverage.path_place(",
        "container_coverage.path_segments(",
        "container_coverage.fact_of_place(",
    ):
        assert word in source, (word, "the pair reaches a unit through its owner")
    places = set(container_coverage.SCOPE_PATH_ROOTS)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = [key.value for key in node.keys if isinstance(key, ast.Constant)]
            if keys and all(key in places for key in keys):
                raise AssertionError((dict(zip(keys, node.values, strict=True)), "a second mapping of the pair"))
    pair_rule = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "pair_parts")
    assert not [
        node.attr for node in ast.walk(pair_rule) if isinstance(node, ast.Attribute) and node.attr == "directory_name"
    ], "the declaration names no directory"


def test_the_declaration_pairs_are_sorted_by_name_so_no_answer_depends_on_the_order(tmp_path, converter_module):
    """Rule 6, the CLI half: the pairs are sorted by the name of the place they state before the run reads them, so
    no answer depends on the order the operator declared them, and two runs that declare the same pairs in a
    different order write the same bytes.

    Measured 2026-11-26 on `GROUPING` through the script, read through `tests/conftest.py`: 60 files, 49 of them
    `.tf` and 7 `imports.tf`, and the bytes a run writes for a declaration stated in reverse order equal the bytes
    it writes for the same declaration in the sorted order. The rule reads the pairs through `shared_arguments`,
    the argument set both entry points read, and answers them in the sorted order, and the row order stays the
    identity order the row rule states, so the record bytes do not depend on the declaration order either.
    """
    _run(FIXTURES_DIR / GROUPING, tmp_path)
    pairs = declaration_pairs(_manifest(tmp_path), MODE_VALUES[0])
    assert list(pairs) == sorted(pairs), pairs
    assert list(pairs) != list(reversed(pairs)), pairs

    parser = argparse.ArgumentParser()
    converter_module.shared_arguments(parser)
    args = parser.parse_args(list(declaration_args(tuple(reversed(pairs)))))
    assert list(converter_module.import_modes(parser, args)) == list(pairs), args.import_mode

    first, second = tmp_path / "sorted", tmp_path / "reversed"
    assert _run(FIXTURES_DIR / GROUPING, first, declaration_args(pairs)).returncode == 0
    assert _run(FIXTURES_DIR / GROUPING, second, declaration_args(tuple(reversed(pairs)))).returncode == 0
    assert written_bytes(first) == written_bytes(second), "the order the pairs were declared in changes no byte"
    keys = sorted(written_bytes(first))
    assert len(keys) == 60, keys
    assert len([key for key in keys if key.endswith(".tf")]) == 49, keys
    blocks = [key for key in keys if key.endswith("imports.tf")]
    assert len(blocks) == 7, blocks
    dirs = {row["directory"] for row in _manifest(first)}
    assert all(Path(key).parent.name in dirs for key in blocks), blocks


def test_a_declared_unit_prints_its_mode_and_an_undeclared_unit_prints_the_empty_answer(tmp_path):
    """Rule 6: `build_rows` takes the declaration, so a unit a pair names prints that pair's value on its row and a
    unit no pair names prints `EMPTY_ANSWER`, the answer a run that declares nothing writes today. The value is read
    positionally through `MODE_VALUES`, the pair its owner states, so this pin names no value.

    Measured 2026-11-26 on `GROUPING` through the script with one pair, the pair for `Datacenter-FW`: 11 rows, 3 of
    them state the value and 8 state the empty answer. The 3 rows are the units the pair names through `units`:
    `Datacenter-FW`, `fw-2.example.com` and `vsys2`. `declared_mode` answers the value for a unit the pair names and
    the empty answer for a unit it does not, so the row rule reads the declaration through the same pair the run does.
    """
    _run(FIXTURES_DIR / GROUPING, tmp_path)
    pair = declaration_pairs(_manifest(tmp_path), MODE_VALUES[0])[0]
    out = tmp_path / "declared"
    assert _run(FIXTURES_DIR / GROUPING, out, declaration_args((pair,))).returncode == 0
    rows = _manifest(out)
    assert len(rows) == 11, rows
    declared = [row for row in rows if row["mode"] == MODE_VALUES[0]]
    assert len(declared) == 3, declared
    assert sorted(row["unit"] for row in declared) == ["Datacenter-FW", "fw-2.example.com", "vsys2"], declared
    assert all(row["mode"] == unit_manifest.EMPTY_ANSWER for row in rows if row not in declared), rows

    key, name = unit_manifest.pair_parts(pair[0])
    for facts in unit_manifest.units(rows):
        expected = MODE_VALUES[0] if unit_manifest.fact(facts, key) == name else unit_manifest.EMPTY_ANSWER
        assert unit_manifest.declared_mode(facts, (pair,)) == expected, (facts, name)


def test_two_modes_for_one_unit_are_refused_and_the_run_writes_no_file(tmp_path, converter_module):
    """Rule 6: two pairs that name one unit are an input refusal, so the run exits 1 and writes no file, the shape
    `is_refusal` states, and the line names the unit, the value the merged record names for it, and the value the run
    declares. The refusal is `xml_input.UnsafeInputError`, the kind the entry point reads, so the exit code is the
    refusal code and not the argument code.

    Measured 2026-11-26 on `GROUPING` through the script: the two pairs name the unit `fw-2.example.com`, and the
    sorted order reads the pair that states the second value first, so the record answer for the unit is that value
    and the line names the other one as the declaration. The output directory does not exist. Read through
    `check_declared_modes` with no record, the same refusal reaches the run's own rows through `units`.
    """
    _run(FIXTURES_DIR / GROUPING, tmp_path)
    rows = _manifest(tmp_path)
    first = pair_for("devices", "fw-2.example.com", MODE_VALUES[0])
    second = pair_for("devices", "fw-2.example.com", MODE_VALUES[1])
    out = tmp_path / "refused"
    proc = _run(FIXTURES_DIR / GROUPING, out, declaration_args((first, second)))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert not out.exists(), "the refusal happens before the run writes"
    line = next(line for line in proc.stdout.splitlines() if line.startswith("Error:"))
    assert line == (
        "Error: refusing to declare two modes for unit fw-2.example.com: the merged record names "
        f"{MODE_VALUES[1]} and this run declares {MODE_VALUES[0]}"
    ), line

    with pytest.raises(xml_input.UnsafeInputError) as raised:
        unit_manifest.check_declared_modes((first, second), [], rows)
    assert "fw-2.example.com" in str(raised.value), raised.value
    assert converter_module.is_refusal(raised.value), "the refusal is the kind the entry point reads"


def test_a_declared_mode_that_disagrees_with_the_record_is_refused_and_writes_no_file(tmp_path):
    """Rule 6, the record half: the value a run declares must agree with the value the merged record names for the
    same unit, so a run that declares the other value for a unit it read only through the record is refused before it
    writes, exits 1, and leaves the record as it read it.

    Measured 2026-11-26 on the committed pair through `tests/conftest.py`: the first run declares the value that
    writes blocks for `Dev-DG` and writes 84 files, 62 of them `.tf`, and its record row for `Dev-DG` states that
    value. The copy is the codebase the second run writes into. `RUN_FIXTURE` shows 1 unit, `Shared`, so `Dev-DG`
    reaches the second run only through the record, and the second run declares the other value for it: exit 1, the
    same 84 files with the same bytes, and the line names `Dev-DG`, the value the record states and the value the run
    declares.
    """
    codebase = tmp_path / "codebase"
    pair = pair_for("device-group", "Dev-DG", MODE_VALUES[0])
    assert _run(FIXTURES_DIR / CODEBASE_FIXTURE, codebase, declaration_args((pair,))).returncode == 0
    record = _manifest(codebase)
    assert [row["mode"] for row in record if row["unit"] == "Dev-DG"] == [MODE_VALUES[0]], record

    own = tmp_path / "own"
    assert _run(FIXTURES_DIR / RUN_FIXTURE, own).returncode == 0
    own_rows = _manifest(own)
    assert [row["unit"] for row in own_rows] == ["Shared"], own_rows

    partial = tmp_path / "partial"
    shutil.copytree(codebase, partial)
    other = pair_for("device-group", "Dev-DG", MODE_VALUES[1])
    proc = _run(FIXTURES_DIR / RUN_FIXTURE, partial, declaration_args((other,)))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    line = next(line for line in proc.stdout.splitlines() if line.startswith("Error:"))
    assert line == (
        "Error: refusing to declare two modes for unit Dev-DG: the merged record names "
        f"{MODE_VALUES[0]} and this run declares {MODE_VALUES[1]}"
    ), line
    before, after = written_bytes(codebase), written_bytes(partial)
    assert len(before) == 84 and len(after) == 84, (len(before), len(after))
    assert before == after, "the refusal wrote no file"
    with pytest.raises(xml_input.UnsafeInputError):
        unit_manifest.check_declared_modes((other,), record, own_rows)


def test_a_pair_that_names_no_unit_is_an_argument_error(tmp_path):
    """Rule 6, the CLI half: the pair shape is the CLI's rule, so a shape error exits 2 and writes no file, and the
    row owner answers no error of its own, which is why the row rule cannot exit and the argument rule can.

    Measured 2026-11-26 on `GROUPING` through the script: each of the five shapes exits 2 and writes no output
    directory - a pair with no join, a value outside the pair, a place the one scope path definition refuses, a place
    that names no fact, and a pair that names the place only. `pair_parts` answers the fact key with `None` for a
    place that names no fact and the empty name for a place-only pair, so the answer the argument rule refuses is the
    row owner's answer, stated without an error.
    """
    shapes = [
        pair_text(pair_for("device-group", "Datacenter-FW", MODE_VALUES[0])).replace(PAIR_JOIN, ""),
        pair_text(pair_for("devices", "fw-2.example.com", "outside-the-pair")),
        pair_text(pair_for("bogus", "x", MODE_VALUES[0])),
        pair_text(pair_for("shared", "url-list", MODE_VALUES[0])),
        "device-group",
    ]
    for shape in shapes:
        out = tmp_path / shape.replace("/", "_")
        proc = run_script(
            CONVERTER, str(FIXTURES_DIR / GROUPING), "--output-dir", str(out), DECLARATION_ARGUMENT, shape
        )
        assert proc.returncode == 2, (shape, proc.stdout + proc.stderr)
        assert not out.exists(), (shape, "an argument error writes no file")

    assert unit_manifest.pair_parts(pair_for("shared", "url-list", MODE_VALUES[0])[0]) == (None, "url-list")
    assert unit_manifest.pair_parts("device-group") == (container_coverage.fact_of_place("device-group"), "")
    assert "parser.error" not in (SRC_DIR / "unit_manifest.py").read_text(encoding="utf-8")


def test_the_declaration_is_held_by_the_cli_and_the_rule_owner_states_no_flag_of_its_own(tmp_path, converter_module):
    """Rule 6: the declaration is an argument, so the CLI holds it and the rule owner states no flag of its own. The
    argument is stated once, in `shared_arguments`, the set both entry points read, and both entry points read the
    pairs through the one rule, so no entry point holds a second reader of the declaration.

    Measured 2026-11-26: `shared_arguments` holds one `add_argument` for the argument, `import_modes` is defined once
    in `panorama_to_terraform.py` and called once there and once in `api_to_terraform.py`, and the argument name
    appears in no rule owner. A run that declares nothing reads no pair, so the rule answers the empty set and the
    run writes the bytes a default run writes, which is the golden answer.
    """
    generator = (SRC_DIR / "panorama_to_terraform.py").read_text(encoding="utf-8")
    api = (SRC_DIR / "api_to_terraform.py").read_text(encoding="utf-8")
    shared = next(
        node
        for node in ast.walk(ast.parse(generator))
        if isinstance(node, ast.FunctionDef) and node.name == "shared_arguments"
    )
    held = [
        node
        for node in ast.walk(shared)
        if isinstance(node, ast.Call)
        and getattr(node.func, "attr", None) == "add_argument"
        and node.args
        and getattr(node.args[0], "value", None) == DECLARATION_ARGUMENT
    ]
    assert len(held) == 1, held
    trees = [ast.parse(generator), ast.parse(api)]
    defs = [
        node
        for tree in trees
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "import_modes"
    ]
    assert len(defs) == 1, defs
    calls = [
        node
        for tree in trees
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (getattr(node.func, "id", None) == "import_modes" or getattr(node.func, "attr", None) == "import_modes")
    ]
    assert len(calls) == 2, calls

    owners = ("unit_manifest.py", "import_blocks.py", "container_coverage.py", "naming.py", "write_path.py")
    for name in owners:
        text = (SRC_DIR / name).read_text(encoding="utf-8")
        assert "add_argument" not in text, (name, "a rule owner states no argument")
        assert DECLARATION_ARGUMENT not in text, (name, "the flag is the CLI's")
    assert DECLARATION_ARGUMENT in generator, "the CLI holds the argument"

    parser = argparse.ArgumentParser()
    converter_module.shared_arguments(parser)
    args = parser.parse_args([])
    assert converter_module.import_modes(parser, args) == [], args
    out = tmp_path / "default"
    assert _run(FIXTURES_DIR / GROUPING, out).returncode == 0
    assert not list(out.rglob("imports.tf")), "a run that declares nothing writes no block file"


def test_the_write_step_reads_the_mode_through_the_row_owner_and_names_no_value(tmp_path):
    """Rule 6, the write half: the answer for whether a unit writes blocks is a rule function in the row owner, and
    the value that writes blocks is read positionally through `import_blocks.MODE_VALUES`, so the write step states no
    value of the pair and `import_blocks.py` states no mode rule of its own. This module writes no file, which
    `tests/test_write_path.py::test_a_record_module_renders_rows_and_writes_no_file` pins, so the write step answers
    the fact and `write_path.py` writes.

    Measured 2026-11-26 on `GROUPING` through the script with one pair for `Datacenter-FW`: 3 rows state the value,
    and `imports.tf` is written inside 2 of the 3 unit directories those rows name; the third unit writes no block
    file because the run wrote nothing inside it, which is the content rule. No block file is written outside a
    directory a declared row names, and the run's answer is True for each declared row and False for every other row.
    """
    _run(FIXTURES_DIR / GROUPING, tmp_path)
    pair = declaration_pairs(_manifest(tmp_path), MODE_VALUES[0])[0]
    out = tmp_path / "declared"
    assert _run(FIXTURES_DIR / GROUPING, out, declaration_args((pair,))).returncode == 0
    rows = _manifest(out)
    declared = [row for row in rows if row["mode"] == MODE_VALUES[0]]
    assert len(declared) == 3, declared
    dirs = {row["directory"] for row in declared}
    blocks = sorted(str(p.relative_to(out)) for p in out.rglob("imports.tf"))
    assert len(blocks) == 2, blocks
    assert all(Path(key).parent.name in dirs for key in blocks), blocks
    for row in rows:
        facts = tuple(row[key] for key in unit_manifest.FACT_KEYS)
        assert unit_manifest.unit_writes_blocks(rows, facts) == (row["mode"] == MODE_VALUES[0]), row

    generator = (SRC_DIR / "panorama_to_terraform.py").read_text(encoding="utf-8")
    source = (SRC_DIR / "unit_manifest.py").read_text(encoding="utf-8")
    blocks_owner = (SRC_DIR / "import_blocks.py").read_text(encoding="utf-8")
    assert "unit_manifest.unit_writes_blocks(" in generator, "the write step reads the answer through the row owner"
    assert "import_blocks.MODE_VALUES[0]" in source, "the answer reads the value through its owner"
    for value in MODE_VALUES:
        assert f'"{value}"' not in generator, (value, "the write step states no value of the pair")
    assert "unit_writes_blocks" not in blocks_owner, "the pair owner states no mode rule of its own"
