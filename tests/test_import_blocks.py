"""F6.4: import blocks, one block per entry, as `imports.tf`.

Nine groups, one per rule set here:

1. The id encoding: base64 of the JSON object, keys sorted at every level; `decode_id` is its inverse and
   refuses a shape it does not declare.
2. The agreement gate rule: the address, the entry name, the location, and the id shape, read through the one
   block reader (`sanity_checks.blocks`).
3. No false positive: the corpus writes no finding for this rule.
4. The four `*_policy_rules` types write no block and one WARN finding each, because their import object
   names the rulebase, the position, and a list of names (F3.5).
5. The block comes from the same data the resource block uses: `location_data` and the name the naming rule
   recorded. No second location rule and no second naming rule.
6. Determinism and the no-change rule: two runs write the same bytes, and a run that declares nothing writes
   the same `.tf` bytes as before.
7. The file shape, the reader, and the declaration (`docs/IMPORT_BINDING.md` §2 decision 3, taken 2026-11-26): `to`
   then `id`, one `.tf` file for each unit the declaration marks, `CHECK_ORDER` names `import_blocks`, and the pair
   is read through the owners: the value set through this module and the scope shape through `container_coverage`. A
   run that declares no pair writes no block.
8. The mode as data, at the unit (`docs/IMPORT_BINDING.md` §2 decision 1, taken 2026-11-25): the two values and
   the level read as data through the owner, the fact that no row shape names a field for the mode, and the fact
   that the owner states no unit rule, no level rule and no mode reader of its own.
9. The write answer for the pair, read through the row owner (decision 3): the value that writes blocks is the answer
   `unit_manifest.unit_writes_blocks` gives for a unit's row, so this module states no write rule of its own, and the
   pins build a declaration through `conftest.declaration_pairs`, which reads the place-to-fact pair through
   `container_coverage`.

The pinned provider fact is the object the provider docs import line for `panos_address` encodes.
"""

import base64
from pathlib import Path

import pytest

import container_coverage
import entry_coverage
import import_blocks
import ownership
import panorama_to_terraform as module
import reference_edges
import rule_data
import sanity_checks
import site_data
import unit_manifest
from conftest import (
    DECLARATION_ARGUMENT,
    FIXTURES_DIR,
    GOLDEN_DIR,
    MODE_VALUES,
    SAMPLE_CONFIG,
    SRC_DIR,
    corpus_fixtures,
    declaration_args,
    declaration_pairs,
    file_text,
    parts,
    record_rows,
    run_script,
    tf_files,
)

CONVERTER = "panorama_to_terraform.py"
IMPORTS = import_blocks.IMPORT_FILE

# The fixtures the corpus pins read: the read rule's accepted set, not a name rule. A fixture the rule refuses
# writes no file, so the gate never sees it.
FIXTURES = corpus_fixtures()

# The object the pinned provider docs import line for `panos_address` encodes (§12), in the key order
# `build_id` writes.
PROVIDER_JSON = (
    '{"location":{"device_group":{"name":"example-device-group",'
    '"panorama_device":"localhost.localdomain"}},"name":"addr1"}'
)
EXAMPLE_LOCATION = {"device_group": {"name": "example-device-group", "panorama_device": "localhost.localdomain"}}


def _run(source: Path, out_dir: Path, extra: tuple = ()):
    """Run the converter and return the process result."""
    return run_script(CONVERTER, str(source), "--output-dir", str(out_dir), *extra)


def _files(out_dir: Path) -> dict:
    """The `.tf` files the run wrote, as text, keyed by the path from the output directory."""
    return tf_files(out_dir)


def _bytes(out_dir: Path) -> dict:
    """The `.tf` bytes the run wrote, keyed by the same path the text reader keys by (F6.10.3, §14)."""
    return {key: text.encode("utf-8") for key, text in _files(out_dir).items()}


def _declared(source: Path, out_dir: Path, value: str = MODE_VALUES[0]) -> tuple:
    """The run the declaration pins read, as the rule reads it: the first run writes the record, and the second run
    writes into the same output with one pair per unit that record shows, in the order the argument rule sorts them.
    The pairs are built through `conftest.declaration_pairs`, the one place a pin builds a pair, and the record is
    read through `conftest.record_rows`, so this module states no row shape and no place-to-fact mapping of its own.
    Returns (the second run's result, the pairs it declared).
    """
    _run(source, out_dir)
    pairs = declaration_pairs(record_rows(out_dir)[unit_manifest], value)
    return _run(source, out_dir, declaration_args(pairs)), pairs


def _pair(name: str, location: dict) -> str:
    """A resource block and the import block that names it, in the shape the generator writes."""
    row = import_blocks.row("unit_a_11111111", "panos_address", "web_11111111", name, location)
    sub_block, fields = next(iter(location.items()))
    body = "".join(f'      {key} = "{value}"\n' for key, value in fields.items())
    shape = (
        f'resource "panos_address" "web_11111111" {{\n'
        f"  location = {{\n    {sub_block} = {{\n{body}    }}\n  }}\n"
        f'  name = "{name}"\n}}\n\n'
    )
    return shape + import_blocks.render([row])


GOOD = _pair("Web", EXAMPLE_LOCATION)


# --- 1. The id encoding ------------------------------------------------------


def test_the_id_round_trips():
    """`decode_id` is the inverse of `build_id`."""
    encoded = import_blocks.build_id(EXAMPLE_LOCATION, "Web Server")
    assert import_blocks.decode_id(encoded) == {"location": EXAMPLE_LOCATION, "name": "Web Server"}


def test_the_id_matches_the_pinned_provider_example():
    """The encoding is the provider docs example, byte for byte (§12)."""
    encoded = import_blocks.build_id(EXAMPLE_LOCATION, "addr1")
    # The provider parses the JSON object, so the object is the fact; the bytes are ours and they are fixed.
    assert base64.b64decode(encoded).decode("utf-8") == PROVIDER_JSON
    assert base64.b64encode(PROVIDER_JSON.encode()).decode() == encoded
    assert import_blocks.decode_id(encoded) == {"location": EXAMPLE_LOCATION, "name": "addr1"}


def test_shared_encodes_as_the_empty_sub_block():
    """`location.shared` declares no field, so the id states it as `{}`, the shape the block writes."""
    assert import_blocks.decode_id(import_blocks.build_id({"shared": {}}, "addr1")) == (
        {"location": {"shared": {}}, "name": "addr1"}
    )


def test_a_non_ascii_name_rounds_trip_and_the_bytes_stay_ascii():
    """`ensure_ascii` keeps two runs on the same bytes writing the same bytes."""
    encoded = import_blocks.build_id({"device_group": {"name": "DG-A"}}, "Café Server")
    assert all(byte < 128 for byte in base64.b64decode(encoded))
    assert import_blocks.decode_id(encoded)["name"] == "Café Server"


@pytest.mark.parametrize(
    "bad",
    [
        "not base64 at all",
        base64.b64encode(b"not json").decode(),
        base64.b64encode(b'["location", "name"]').decode(),
        base64.b64encode(b'{"location": {"shared": true}}').decode(),
        base64.b64encode(b'{"name": "addr1"}').decode(),
        base64.b64encode(b'{"location": {"shared": {}}, "name": ""}').decode(),
    ],
)
def test_decode_refuses_a_shape_it_does_not_declare(bad):
    """An id is data, so a reader cannot fall back to reading prose."""
    with pytest.raises(ValueError):
        import_blocks.decode_id(bad)


# --- 2. The agreement rule ---------------------------------------------------


def test_an_import_block_that_agrees_with_its_block_passes():
    assert sanity_checks.check_import_blocks({"a.tf": GOOD}) == []


def test_wrong_type_is_detected():
    """The address names a type the run declares no block for."""
    findings = sanity_checks.check_import_blocks(
        {"a.tf": GOOD.replace("to = panos_address.web_11111111", "to = panos_service_group.web_11111111")}
    )
    assert len(findings) == 1
    assert "names no resource block" in findings[0].detail
    assert findings[0].severity == sanity_checks.FAIL


def test_wrong_local_name_is_detected():
    findings = sanity_checks.check_import_blocks(
        {"a.tf": GOOD.replace("to = panos_address.web_11111111", "to = panos_address.other_22222222")}
    )
    assert len(findings) == 1
    assert "names no resource block" in findings[0].detail


def test_wrong_location_is_detected():
    findings = sanity_checks.check_import_blocks({"a.tf": GOOD.replace('"example-device-group"', '"other-group"')})
    assert len(findings) == 1
    assert findings[0].check == "import_blocks"
    assert "location" in findings[0].detail


def test_wrong_name_is_detected():
    findings = sanity_checks.check_import_blocks({"a.tf": GOOD.replace('name = "Web"', 'name = "Web 2"')})
    assert len(findings) == 1
    assert "name" in findings[0].detail


def test_an_import_block_that_names_a_data_block_is_refused():
    """An import object names a resource, so a `data` block cannot answer it."""
    files = {
        "a.tf": 'data "panos_address" "web_11111111" {\n  name = "Web"\n'
        '  location = {\n    device_group = {\n      name = "DG-A"\n'
        '      panorama_device = "Panorama-1"\n    }\n  }\n}\n\n'
        "import {\n  to = panos_address.web_11111111\n"
        f'  id = "{import_blocks.build_id(EXAMPLE_LOCATION, "Web")}"\n}}\n\n',
    }
    findings = sanity_checks.check_import_blocks(files)
    assert len(findings) == 1
    assert "names no resource block" in findings[0].detail


def test_a_bad_id_is_refused_by_the_same_rule():
    files = {"a.tf": GOOD.replace(import_blocks.build_id(EXAMPLE_LOCATION, "Web"), "not base64")}
    findings = sanity_checks.check_import_blocks(files)
    assert len(findings) == 1
    assert "not base64" in findings[0].detail


def test_the_rule_reads_import_blocks_with_the_one_reader():
    """The finding names the file and line the one block reader read."""
    findings = sanity_checks.check_import_blocks({"a.tf": GOOD.replace('"example-device-group"', '"other-group"')})
    block = sanity_checks.blocks({"a.tf": GOOD}, ("import",))[0]
    assert (findings[0].file, findings[0].line) == (block.file, block.line)
    assert block.address == "panos_address.web_11111111"


# --- 3. No false positive ----------------------------------------------------


def test_no_false_positive_across_the_corpus(tmp_path):
    """Every entry the corpus writes agrees with the block it names, so the pins declare the pairs the run's own
    rows show and read the blocks the declaration writes.
    """
    for fixture in FIXTURES:
        out = tmp_path / fixture
        result, pairs = _declared(FIXTURES_DIR / fixture, out)
        assert result.returncode == 0, (fixture, pairs)
        files = _files(out)
        if files:
            # A WARN for a rule entry is the reported decision, not a violation.
            assert [f for f in sanity_checks.check_import_blocks(files) if f.severity == sanity_checks.FAIL] == [], (
                fixture,
                pairs,
            )


# --- 4. The four `*_policy_rules` types --------------------------------------


def test_the_rule_set_comes_from_the_rulebase_field():
    """No second table names the four types: they are the types `LOCATION_SCHEMA` declares `rulebase` for."""
    assert import_blocks.rule_types() == {
        "panos_security_policy_rules",
        "panos_nat_policy_rules",
        "panos_decryption_policy_rules",
        "panos_pbf_policy_rules",
    }


def test_a_rule_entry_writes_no_block_and_one_warn_finding(tmp_path):
    """The rulebase, the position, and the list of names are not facts the parse can state, so the pins read the
    blocks through a declaration the run's own rows show.
    """
    out = tmp_path / "rules"
    result, pairs = _declared(FIXTURES_DIR / "kitchen_sink.xml", out)
    assert result.returncode == 0, (pairs, "the declaration names one pair per unit the run built")
    files = _files(out)
    text = file_text(files, IMPORTS)
    for rule_type in import_blocks.rule_types():
        assert rule_type not in text
    findings = sanity_checks.check_import_blocks(files)
    reported = [f for f in findings if f.severity == sanity_checks.WARN]
    assert reported, "the run must report the rule entries"
    assert all(f.check == "import_blocks" for f in findings)
    assert all("no import id" in f.detail and "rulebase" in f.detail for f in reported)
    # A WARN is an operator action: the gate still exits 0, and the finding prints as every gate finding does.
    assert sanity_checks.run_checks(out).fail_count == 0
    assert "[import_blocks]" in (out / "SANITY_REPORT.txt").read_text()


# --- 5. One location rule and one naming rule --------------------------------


def test_the_id_states_the_location_the_block_states(tmp_path):
    """`import_blocks.row` encodes `location_data`, so the block and the id state one fact."""
    generator = module.TerraformGenerator(str(tmp_path))
    obj = {"name": "Web", "device_group": "DG-A", "vsys": "", "template": "", "vsys_device": ""}
    location = generator.location_data("panos_address", obj)
    generator.location_block("panos_address", obj, "web_11111111")
    row = generator.import_rows[-1]
    assert import_blocks.decode_id(row["import_id"]) == {"location": location, "name": "Web"}
    assert row["local_name"] == "web_11111111"
    # The unit is the `unit_manifest` identity, read through `facts_of`: no second identity key.
    assert row["unit"] == unit_manifest.directory_name(unit_manifest.facts_of(obj), generator.sanitize_name)


def test_the_module_defines_no_location_rule_and_no_naming_rule():
    """`import_blocks` states the id shape, the row shape, and the order: it resolves no name and picks no location."""
    source = (SRC_DIR / "import_blocks.py").read_text(encoding="utf-8")
    for rule in ("def location_data", "def sanitize_name", "def name_ref", "def declare_block_name"):
        assert rule not in source


# --- 6. Order, bytes, and the no-change rule ---------------------------------


def test_the_file_prints_units_in_order_then_entries_in_order():
    rows = [
        import_blocks.row("unit_b_22222222", "panos_address", "z_11111111", "Z", {"shared": {}}),
        import_blocks.row("unit_a_11111111", "panos_service", "b_22222222", "B", {"shared": {}}),
        import_blocks.row("unit_a_11111111", "panos_address", "a_11111111", "A", {"shared": {}}),
    ]
    addresses = [
        line.split("to = ")[1] for line in import_blocks.render(rows).split("\n") if line.startswith("  to = ")
    ]
    assert addresses == ["panos_address.a_11111111", "panos_service.b_22222222", "panos_address.z_11111111"]


def test_the_file_names_no_timestamp_and_no_path(tmp_path):
    out = tmp_path / "run"
    result, pairs = _declared(SAMPLE_CONFIG, out)
    assert result.returncode == 0, pairs
    text = file_text(_files(out), IMPORTS)
    assert "timestamp" not in text.lower()
    assert str(tmp_path) not in text
    assert ".xml" not in text


def test_two_runs_write_the_same_bytes(tmp_path):
    """Two runs on the same input write the same bytes, including the per-unit layout (F6.10.3, §14). The second run
    declares the same pairs in the reverse order, so the bytes cannot depend on the order the pairs were declared.
    """
    first, pairs = _declared(SAMPLE_CONFIG, tmp_path / "first")
    second = _run(SAMPLE_CONFIG, tmp_path / "second", declaration_args(tuple(reversed(pairs))))
    assert first.returncode == 0 and second.returncode == 0, pairs
    assert _bytes(tmp_path / "first") == _bytes(tmp_path / "second")


def test_a_run_that_declares_no_pair_writes_the_golden_bytes(tmp_path):
    """The declaration is opt-in, so both golden sets stay byte-identical: a run that declares no pair writes no
    block, and the manifest row states the answer for a unit the run did not mark.
    """
    assert _run(SAMPLE_CONFIG, tmp_path).returncode == 0
    assert not parts(tf_files(tmp_path), IMPORTS), "a run that declares no pair writes no file"
    for row in record_rows(tmp_path)[unit_manifest]:
        assert row["mode"] == unit_manifest.EMPTY_ANSWER, row
    for path in sorted((GOLDEN_DIR / "sample").rglob("*.tf")):
        # F6.10.3 (§14): the golden case holds the same per-unit layout the run writes, so the byte
        # comparison reads the path inside the case.
        assert (tmp_path / path.relative_to(GOLDEN_DIR / "sample")).read_bytes() == path.read_bytes()


def test_the_file_is_written_only_when_it_has_content(tmp_path):
    """Rule 6: the file is written only when the run has block content for the unit. The pins build a pair from a
    run that shows units, through `conftest.declaration_pairs`, the one place a pin builds a pair, and read it back
    through `unit_manifest.pair_parts` and the one scope path definition, so this module holds no path shape and no
    mapping of its own. Run on an input whose units no pair names, the row owner answers the empty answer, `render`
    prints nothing for no row, and no file is written.
    """
    built = tmp_path / "built"
    assert _run(SAMPLE_CONFIG, built).returncode == 0
    pairs = declaration_pairs(record_rows(built)[unit_manifest], MODE_VALUES[0])
    assert pairs, "the pins read a record that shows units"
    assert all(container_coverage.is_scope_path(pair[0]) for pair in pairs), pairs

    source = tmp_path / "empty.xml"
    source.write_text(
        '<?xml version="1.0"?>\n<config version="10.0.0"><devices>'
        '<entry name="localhost.localdomain"><vsys><entry name="vsys1">'
        "<network><interface><ethernet/></interface></network></entry></vsys>"
        "</entry></devices></config>\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    assert _run(source, out, declaration_args(pairs)).returncode == 0
    rows = record_rows(out)[unit_manifest]
    assert rows, "the run built units, so the answer is read through a row"
    key, name = unit_manifest.pair_parts(pairs[0][0])
    assert not any(unit_manifest.fact(unit_manifest.facts_of(row), key) == name for row in rows), (
        "the pair names a unit this run did not build",
    )
    assert not parts(_files(out), IMPORTS)
    assert "import {" not in import_blocks.render([])


# --- 7. The file shape, the reader, and the declaration ------------------------


def test_a_block_states_to_then_id():
    """Decision 1 rule 3: one block, two fields, in this order."""
    block = import_blocks.render(
        [
            import_blocks.row("unit_a_11111111", "panos_address", "a_11111111", "A", {"shared": {}}),
        ]
    ).split("\n\n")[-2]
    lines = block.split("\n")
    assert lines[0] == "import {"
    assert lines[1] == "  to = panos_address.a_11111111"
    assert lines[2].startswith('  id = "')


def test_the_one_reader_reads_both_block_shapes_in_one_pass():
    """The `import {` shape has no quoted names, so the reader takes the target from `to`."""
    blocks = sanity_checks.blocks({"a.tf": GOOD}, ("resource", "import"))
    assert [(b.kind, b.address) for b in blocks] == [
        ("resource", "panos_address.web_11111111"),
        ("import", "panos_address.web_11111111"),
    ]
    assert blocks[1].attribute("id") == import_blocks.build_id(EXAMPLE_LOCATION, "Web")


def test_the_import_file_is_a_gate_input(tmp_path):
    """Decision 1 rule 1: the agreement rule reads `.tf` files only, so the shape is a `.tf` file, and rule 6 of
    `unit_manifest.py` decides which unit's directory holds it."""
    out = tmp_path / "run"
    result, pairs = _declared(SAMPLE_CONFIG, out)
    assert result.returncode == 0, pairs
    assert parts(sanity_checks.read_tf_files(out), import_blocks.IMPORT_FILE), (
        "the gate reads the file through the unit directory"
    )
    assert "import_blocks" in sanity_checks.CHECK_ORDER
    assert "import_blocks" in (out / "SANITY_REPORT.txt").read_text()


def test_the_declaration_appears_in_help_and_a_run_that_declares_nothing_writes_no_block(tmp_path):
    """Decision 3, answer 4: the declaration is opt-in, following the `--data-blocks` precedent, so a run that
    declares no pair writes no block and every manifest row states the answer for a unit the run did not mark."""
    assert DECLARATION_ARGUMENT in run_script(CONVERTER, "--help").stdout
    assert _run(SAMPLE_CONFIG, tmp_path).returncode == 0
    assert not parts(tf_files(tmp_path), IMPORTS)
    for row in record_rows(tmp_path)[unit_manifest]:
        assert row["mode"] == unit_manifest.EMPTY_ANSWER, row


# --- 8. The mode as data at the unit, and the field decision 2 names (`docs/IMPORT_BINDING.md` §2) ---


def test_the_two_mode_values_are_data_read_through_the_owner():
    """Decision 1 takes two values, so the pin reads them as data through the owner the decision names,
    `src/import_blocks.py`, and not through the wording of `docs/IMPORT_BINDING.md`. Four test modules read the pair,
    so `tests/conftest.py` holds the one definition, and that definition reads through this module.

    Measured 2026-11-25 on the tree that holds the decision: the pair is `imported` and `added`, the plan
    outcome for one unit, and it has two members, so a third value moves this pin with the decision.
    """
    assert MODE_VALUES == ("imported", "added")
    assert len(MODE_VALUES) == 2, "the decision takes two values, so the pair has two members"
    assert MODE_VALUES is import_blocks.MODE_VALUES, "the shared definition reads through the owner and copies nothing"


def test_the_mode_level_is_the_unit_the_one_unit_rule_answers(tmp_path):
    """Decision 1 stops the mode at the unit, so the level the data names is the unit identity the manifest row
    already states and not one of the five scope facts: a device, a virtual system, a device group and a template
    are already units, so a per-device or per-device-group request needs no new level.

    Measured 2026-11-25 on `SAMPLE_CONFIG` run through the pipeline, with the rows read back through `parse_rows`
    and the unit set read through `units`, so this pin states no unit rule of its own.
    """
    out = tmp_path / "run"
    assert _run(SAMPLE_CONFIG, out).returncode == 0
    rows = unit_manifest.parse_rows((out / unit_manifest.MANIFEST_FILE).read_text(encoding="utf-8"))
    assert rows, "the pin reads a record with content"
    assert len(unit_manifest.units(rows)) == len(rows), "the record is one row per unit"
    level = import_blocks.MODE_LEVEL
    assert level == "unit", level
    assert level == unit_manifest.FIELD_ORDER[0], "the level names the unit identity the row states"
    assert level not in unit_manifest.FACT_KEYS, "the mode does not sit at a scope-fact level"
    for row in rows:
        assert row[level] == unit_manifest.unit_name(unit_manifest.facts_of(row)), row


def test_the_field_name_and_the_pair_are_each_stated_once_in_their_owner(tmp_path):
    """Decision 2 (`docs/IMPORT_BINDING.md` §2, taken 2026-11-25): the field name is in the shape `unit_manifest.py`
    owns, and the two values stay in this module, the owner decision 1 names, so each is stated once. The other
    shapes name no field for the mode, and this module defines no field name of its own.

    Measured 2026-11-25 on `SAMPLE_CONFIG` run through the pipeline, with each row read back through its module's
    `parse_rows`, so this pin states no shape of its own. Decision 3 (`docs/IMPORT_BINDING.md` §2, taken 2026-11-26)
    takes the answer for a run that declares no pair, so the pin runs without a declaration and every manifest row
    states the answer for a unit the run did not mark, read through its owner.
    """
    shapes = {
        "unit_manifest": unit_manifest.FIELD_ORDER,
        "ownership": ownership.FIELD_ORDER,
        "reference_edges": reference_edges.FIELD_ORDER,
        "rule_data": rule_data.RULE_ROW_FIELDS,
        "site_data": site_data.SITE_ROW_FIELDS,
    }
    assert "mode" in shapes["unit_manifest"], "the field is in the shape its owner states"
    for name, shape in shapes.items():
        if name != "unit_manifest":
            assert "mode" not in shape, (name, "the shape states no field for the mode")
    assert "mode" not in import_blocks.IMPORT_ROW_FIELDS, "the block row shape names no field for the mode"
    assert not hasattr(import_blocks, "MODE_FIELD"), "this module states no field name for the mode"
    assert not hasattr(unit_manifest, "MODE_VALUES"), "the reader reads the pair through its owner"
    out = tmp_path / "run"
    assert _run(SAMPLE_CONFIG, out).returncode == 0
    rows = record_rows(out)
    assert any(rows.values()), "the pin reads a record with content"
    for record_module, record in rows.items():
        for row in record:
            if record_module is unit_manifest:
                assert row["mode"] == unit_manifest.EMPTY_ANSWER, (record_module.__name__, row)
            else:
                assert "mode" not in row, (record_module.__name__, "no other record holds the mode")
    assert import_blocks.MODE_LEVEL not in ownership.FIELD_ORDER, "the entry level is not the mode's level"


def test_the_mode_data_adds_no_unit_rule_and_no_mode_rule_to_the_owner():
    """Decision 1 names values and a level, and no rule, so the owner holds data only: the unit rule stays
    `unit_manifest.units`, the row reader stays each record module's `parse_rows`, and no module holds the pair or
    the level a second time. The pin reads the owner's source for the definitions it does not define and the
    module objects for the names they do not hold.
    """
    source = (SRC_DIR / "import_blocks.py").read_text(encoding="utf-8")
    for rule in ("def units", "def facts_of", "def parse_rows", "def mode"):
        assert rule not in source, f"import_blocks.py states a rule its owner defines ({rule})"
    for other in (unit_manifest, ownership, reference_edges, rule_data, site_data, entry_coverage, sanity_checks):
        assert not hasattr(other, "MODE_VALUES"), (other.__name__, "a second pair of mode values")
        assert not hasattr(other, "MODE_LEVEL"), (other.__name__, "a second level for the mode")


# --- 9. The write answer for the pair, read through the row owner (decision 3) ---


def test_a_unit_declared_the_block_value_writes_blocks_and_a_unit_declared_the_other_value_writes_none(tmp_path):
    """Rule 7, read through the row owner: the value that writes blocks is the answer `unit_manifest.unit_writes_blocks`
    gives for a unit's row, so this module states no write rule of its own. A pair names the units that hold the fact
    its place names, so a unit the declaration marks with the value that writes blocks answers True, a unit marked the
    other value answers False, and a unit no pair names answers False because its row states the empty answer. The
    file is written for a unit that answers True and has block content, the rule this module already states.

    Measured 2026-11-26 on `report_grouping.xml` read back through `parse_rows`: 11 rows, 5 pairs, and 7 parts when
    every pair is declared. The pins read three pairs that name 3, 2 and 2 rows, hold no unit in common, and hold 2,
    2 and 1 parts, declare two of them with a different value each, and name no pair for the third, so the run wrote
    the 2 parts for the units the first pair names and none for the units the other two name.
    """
    source = FIXTURES_DIR / "report_grouping.xml"
    whole = tmp_path / "whole"
    first, pairs = _declared(source, whole)
    assert first.returncode == 0, pairs
    rows = record_rows(whole)[unit_manifest]
    assert len(rows) == 11 and len(pairs) == 5, (len(rows), pairs)
    written = parts(_files(whole), IMPORTS)
    assert len(written) == 7, sorted(written)

    def rows_named(pair: tuple) -> list:
        """The rows the pair names, read through `pair_parts` and `fact`, the rules `unit_manifest.py` owns, so this
        module holds no place-to-fact mapping of its own.
        """
        key, name = unit_manifest.pair_parts(pair[0])
        return [row for row in rows if unit_manifest.fact(unit_manifest.facts_of(row), key) == name]

    def parts_for(group: list) -> list:
        return sorted(f"{row['directory']}/{IMPORTS}" for row in group if f"{row['directory']}/{IMPORTS}" in written)

    block, other, quiet = pairs[0], pairs[3], pairs[4]
    named = (rows_named(block), rows_named(other), rows_named(quiet))
    assert [len(group) for group in named] == [3, 2, 2], named
    assert [len(parts_for(group)) for group in named] == [2, 2, 1], named
    assert len({row["directory"] for group in named for row in group}) == 7, (
        "the three pairs name different units, so no unit holds two values in the declaration the pins read",
    )

    declaration = (block, (other[0], MODE_VALUES[1]))
    mixed = tmp_path / "mixed"
    result = _run(source, mixed, declaration_args(declaration))
    assert result.returncode == 0, (result.stderr, declaration)
    parts_after = sorted(parts(_files(mixed), IMPORTS))
    assert parts_after == parts_for(named[0]), (parts_after, block)

    # The answer, read through the row owner, agrees with the declaration for every row in the run, and each row
    # states the value its pair declared, or the empty answer for a unit no pair named.
    mixed_rows = record_rows(mixed)[unit_manifest]
    assert len(mixed_rows) == 11, mixed_rows
    for pair, want in (block, (other[0], MODE_VALUES[1]), (quiet[0], unit_manifest.EMPTY_ANSWER)):
        key, name = unit_manifest.pair_parts(pair)
        for row in mixed_rows:
            if unit_manifest.fact(unit_manifest.facts_of(row), key) == name:
                assert row["mode"] == want, (row["unit"], row["mode"], want)
                assert unit_manifest.unit_writes_blocks(mixed_rows, unit_manifest.facts_of(row)) == (
                    want == MODE_VALUES[0]
                ), (row["unit"], row["mode"], "the answer is the value that writes blocks")
