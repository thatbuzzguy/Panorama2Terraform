"""Epic 9 Piece 17 and Piece 18: the rule row shape, the two forms of the same rows, and the write path.

Ten pins, in the order the rules in `src/rule_data.py` state them:

1. The row shape, and `rulebase` not being in it while the parse records no rulebase fact (F3.5).
2. `parse_rows` refusing a shape it does not declare, including the printed CSV read as data.
3. The properties columns reading the fields they name through the recorded object, so the data file is an
   output and the honesty rule in `docs/COVERAGE_MATRIX.md` §1 holds for every column.
4. The key as the §2.1 identity read through `state_coverage.ownership_key` and the digest read through
   `unit_manifest.identity_digest`, so one name in two contexts is two rows with two digests.
5. The chain grouping as the F2.5 and F3.2 rule, measured on the multi-device-group fixture.
6. The generator reading that grouping through `rule_data`, so no module states the group a second time.
7. The printed CSV stating the same rows as the data.
8. The module stating no second rule and holding no writer of its own, so the run writes the pair through
   `write_path.py`.
9. The two file names, read through the same matrix row, and the pair naming the unit file set.
10. The run writing one pair per rule type per unit, each file reading back as the rows it was built from.
11. The printed map reading back through `printed_entries` as the same row keys, in the order the `.tf` file prints
    them, so the gate's cross-check and the block rule read the third form through this module and the printed form
    stays no reader input for a row.

The read record is read the way `tests/test_property_coverage.py` reads it: the record is turned on before the
parse, so a read through the recorded object counts as a read this output made. One pin plants its material,
because no committed fixture holds one rule name in two device groups; the pin says so, and the planted config is
read through the same input door the corpus pins read.
"""

import ast
import csv
import json
from pathlib import Path

import container_coverage
import entry_coverage
import import_blocks
import naming
import panorama_to_terraform
import rule_data
import sanity_checks
import state_coverage
import unit_manifest
import xml_input
from conftest import FIXTURES_DIR, RULE_TYPES, SRC_DIR, data_file_set, run_script, written_bytes

# The run the write-path pins read: the tool's entry point, read through the `src/` set (§1.1).
CONVERTER = SRC_DIR / "panorama_to_terraform.py"

# The rule types the single object iterates, read through the rule that names them and shared through
# `conftest.RULE_TYPES`, so no test module states the set a second time.


def parse_method(resource: str) -> str:
    """The parse method the container table names for one matrix row, read through the table (§3.1)."""
    row = next(row for row in container_coverage.CONTAINER_TABLE if entry_coverage.row_detail(row) == resource)
    return row.method


def recorded_rules(resource: str, fixture: str, path=None):
    """The rules one fixture holds for one rule type, as the recorded objects the read record measures."""
    source = FIXTURES_DIR / fixture if path is None else path
    parser = panorama_to_terraform.PanoramaParser(xml_input.parse_xml(source))
    parser.ledger.start_recording()
    return parser, getattr(parser, parse_method(resource))()


# --- 1. The row shape ------------------------------------------------------


def test_the_row_shape_is_the_declared_field_set():
    """AC-1: the shape is the six fields in order, and `rulebase` is not one of them.

    `rulebase` is the field `LOCATION_SCHEMA` declares for the four rule rows, but the parse records no rulebase
    fact, so a column naming it would name a field the parse cannot capture (F3.5), which is the honesty rule
    `docs/COVERAGE_MATRIX.md` §1 holds for every properties column. The column enters the shape when the live
    fact lands, so the pin holds both the shape and the absence.
    """
    assert rule_data.RULE_ROW_FIELDS == ("directory", "resource", "entry", "key", "pivot", "properties")
    assert "rulebase" not in rule_data.RULE_ROW_FIELDS

    for resource in RULE_TYPES:
        _, rules = recorded_rules(resource, entry_coverage.MATRIX_BY_RESOURCE[resource]["fixture"])
        rows = rule_data.build_rows(resource, rules, naming.sanitize)
        assert rows, (resource, "the pin measures rows, not an empty set")
        for row in rows:
            assert sorted(row) == sorted(rule_data.RULE_ROW_FIELDS), row
            assert row["resource"] in entry_coverage.MATRIX_BY_RESOURCE, row
            assert row["entry"], row
            assert row["properties"], row

    # `render` prints the declared shape, in field order, so a writer cannot write a field the shape does not
    # declare: an undeclared field is dropped, which is why `parse_rows` can refuse one it is handed.
    printed = json.loads(rule_data.render([dict(rows[0], rulebase="pre")]))
    assert [list(printed_row) for printed_row in printed] == [list(rule_data.RULE_ROW_FIELDS)], printed
    assert rule_data.render([rows[0]]).endswith("\n"), "the data form ends with one newline"


# --- 2. The refusal of a shape the module does not declare -----------------


def test_parse_rows_refuses_a_shape_it_does_not_declare():
    """AC-2: a row that is not the declared shape is a refusal, the way `site_data.parse_rows` refuses."""
    good = rule_data.build_rows(
        "panos_security_policy_rules",
        recorded_rules("panos_security_policy_rules", "security_rules.xml")[1],
        naming.sanitize,
    )[0]
    assert rule_data.parse_rows(rule_data.render([good])) == [good]

    def refuse(row, phrase):
        # The text is written here, not through `render`, because `render` prints only the declared fields, so
        # an undeclared field reaches the reader only in the text the file holds.
        text = json.dumps([row], indent=2)
        try:
            rule_data.parse_rows(text)
        except ValueError as exc:
            assert phrase in str(exc), (phrase, exc)
            return
        raise AssertionError(f"no refusal for {phrase}: {row}")

    extra = dict(good, rulebase="pre")
    refuse(extra, "not a declared rule field")
    missing = {key: value for key, value in good.items() if key != "pivot"}
    refuse(missing, "does not state its fields")

    # The key shape, in the three ways it can fail: a short ordinal, no digest half, a digest half that is not
    # the row's own unit digest.
    ordinal, digest = good["key"].split("_")
    refuse(dict(good, key=f"1_{digest}"), "ordinal_digest")
    refuse(dict(good, key=ordinal), "ordinal_digest")
    refuse(dict(good, key=f"{ordinal}_{'0' * unit_manifest.DIGEST_HEX}"), "not the row's own unit digest")

    # A property value that is not something the recorded object can hold, and a field the row does not name.
    refuse(dict(good, properties={"action": 3.5}), "not something the recorded object can hold")
    refuse(dict(good, properties={"action": None}), "not something the recorded object can hold")
    refuse(dict(good, properties={"uuid": "x"}), "names a field the row does not")
    refuse(dict(good, properties="action"), "properties is not a mapping")

    # A PBF rule's `action` is a mapping, so the shape declares it and reads it back.
    pbf_rows = rule_data.build_rows(
        "panos_pbf_policy_rules", recorded_rules("panos_pbf_policy_rules", "pbf_rules.xml")[1], naming.sanitize
    )
    assert isinstance(pbf_rows[0]["properties"]["action"], dict), pbf_rows[0]
    assert rule_data.parse_rows(rule_data.render([pbf_rows[0]])) == [pbf_rows[0]]

    # The printed form is not a reader input (rule 5).
    try:
        rule_data.parse_rows(rule_data.render_csv([good]))
    except ValueError as exc:
        assert "not the reader input" in str(exc), exc
    else:
        raise AssertionError("the printed form was read as data")


# --- 3. The properties columns read the fields they name -------------------


def test_build_rows_names_only_captured_fields_and_reads_through_the_recorded_object():
    """AC-3: every properties column is a captured field, read through the recorded object (rule 4).

    The recorded object lists the fields the row names as keys the output read, because `build_rows` reads each
    declared field through it. A field the recorded object holds with no value prints no column, the way the
    per-entry report reads `EMPTY_FIELD_VALUES`.
    """
    measured = 0
    fields_with_no_value = 0
    for resource in RULE_TYPES:
        _, rules = recorded_rules(resource, entry_coverage.MATRIX_BY_RESOURCE[resource]["fixture"])
        declared = entry_coverage.MATRIX_BY_RESOURCE[resource]["properties"]
        rows = rule_data.build_rows(resource, rules, naming.sanitize)
        for rule, row in zip(rules, rows, strict=True):
            read = set(rule.used_keys()) - set(entry_coverage.NON_FIELD_KEYS)
            assert read == set(declared), (resource, sorted(read))
            for field, value in row["properties"].items():
                assert field in declared, (resource, field)
                # `value` is the base read, so the comparison adds no read to the record.
                assert value == rule.value(field), (resource, field, value)
                assert value not in entry_coverage.EMPTY_FIELD_VALUES, (resource, field)
                measured += 1
            skipped = [field for field in declared if field not in row["properties"]]
            assert all(rule.value(field) in entry_coverage.EMPTY_FIELD_VALUES for field in skipped), (resource, row)
            fields_with_no_value += len(skipped)
    assert measured > 0, (measured, "the pin measures properties, not an empty set")
    assert fields_with_no_value > 0, (fields_with_no_value, "the pin measures a field that prints no column")


# --- 4. The key is the identity, not the name ------------------------------


def test_the_key_is_the_ordinal_and_the_digest_read_through_the_one_identity_rule(tmp_path):
    """AC-4: the key is the chain ordinal joined to the digest, both read through their owners (rules 1 and 2).

    `state_coverage.ownership_key` is the one place that answers an identity key and `unit_manifest.identity_digest`
    is the one place that answers a digest, so the pin recomputes each key through the two owners instead of
    restating a key rule. The digest is the unit identity digest, so the key half and the directory half of the
    same row name the same unit.
    """
    _, rules = recorded_rules("panos_security_policy_rules", "security_rules.xml")
    rows = rule_data.build_rows("panos_security_policy_rules", rules, naming.sanitize)
    digests = {row["key"].split("_")[1] for row in rows}
    assert len(digests) == 1, "the two rules are in one chain of one device group"
    for position, row in enumerate(rows, 1):
        ordinal, _, digest = row["key"].partition("_")
        assert ordinal == f"{position:0{rule_data.ORDINAL_WIDTH}d}", row
        assert len(digest) == unit_manifest.DIGEST_HEX, row
        assert row["directory"].rsplit("_", 1)[1] == digest, (row, "the two halves name the same unit")

    # One name in two device groups is two entries, so it is two rows with two digests. No committed fixture
    # holds the case, so the pin states the material it measures, read through the same input door the corpus
    # pins read, and the planted file stays out of the corpus.
    path = tmp_path / "two_contexts.xml"
    path.write_text(
        '<config><devices><entry name="localhost.localdomain"><device-group>'
        '<entry name="Alpha-DG"><pre-rulebase><security><rules>'
        '<entry name="Same-Name"><action>allow</action></entry>'
        '<entry name="Other-Name"><action>deny</action></entry>'
        "</rules></security></pre-rulebase></entry>"
        '<entry name="Beta-DG"><pre-rulebase><security><rules>'
        '<entry name="Same-Name"><action>deny</action></entry>'
        "</rules></security></pre-rulebase></entry>"
        "</device-group></entry></devices></config>",
        encoding="utf-8",
    )
    _, rules = recorded_rules("panos_security_policy_rules", path.name, path)
    rows = rule_data.build_rows("panos_security_policy_rules", rules, naming.sanitize)
    assert [row["entry"] for row in rows] == ["Same-Name", "Other-Name", "Same-Name"], rows
    assert len({row["key"] for row in rows}) == 3, "one name in two device groups cannot give one key"
    # The ordinal is the position inside the chain, not the position in the file, so the key is read through the
    # grouping and through the two owners, chain by chain.
    seen = 0
    for chain in rule_data.chains(rules):
        chain_rows = rows[seen : seen + len(chain)]
        seen += len(chain)
        for position, (rule, row) in enumerate(zip(chain, chain_rows, strict=True), 1):
            facts = unit_manifest.facts_of(rule)
            key = state_coverage.ownership_key(
                row["resource"], row["entry"], dict(zip(unit_manifest.FACT_KEYS, facts, strict=True))
            )
            # The key's fact tail is the fact set the row is measured on, which is what the digest half hashes.
            assert key[2:] == facts, (key, facts)
            assert row["key"] == f"{position:0{rule_data.ORDINAL_WIDTH}d}_{unit_manifest.identity_digest(key[2:])}", row
    assert seen == len(rows), (seen, len(rows))


# --- 5. The chain grouping -------------------------------------------------


def test_the_chain_grouping_and_order_are_the_f2_5_rule_read_through_rule_data():
    """AC-5: chains per (device group, vsys), document order inside a chain, first-seen order across chains.

    Measured on `tests/fixtures/policy_order.xml`, the fixture the F2.5 pins read: three device groups, so three
    chains, and `pivot` names the entry before each rule, the empty string for the first rule of a chain. The
    sorted key order is the XML order inside a chain, which is the apply order the single object reads.
    """
    _, rules = recorded_rules("panos_security_policy_rules", "policy_order.xml")
    chains = rule_data.chains(rules)
    assert [len(chain) for chain in chains] == [3, 2, 1], chains
    assert [chain[0].get("device_group") for chain in chains] == ["Alpha-DG", "Beta-DG", "Gamma-DG"], chains

    rows = rule_data.build_rows("panos_security_policy_rules", rules, naming.sanitize)
    assert [row["pivot"] for row in rows] == [
        "",
        "alpha-rule-1",
        "alpha-rule-2",
        "",
        "beta-rule-1",
        "",
    ], rows
    # Inside each chain the row order is the chain order, and the key order sorts to the same order.
    for chain in chains:
        chain_rows = [row for row in rows if row["entry"] in {rule.get("name") for rule in chain}]
        assert sorted(chain_rows, key=lambda row: row["key"]) == chain_rows, chain_rows
        ordinals = [row["key"].split("_")[0] for row in chain_rows]
        assert ordinals == [f"{i:0{rule_data.ORDINAL_WIDTH}d}" for i in range(1, len(chain) + 1)], ordinals

    # A rule the export cannot place in a device group is the shared unit, and a rule the export names no virtual
    # system for is grouped as vsys1, the two names this rule reads through its owner and its own default.
    loose = [{"name": "loose-rule", "action": "allow"}]
    assert [[rule["name"] for rule in chain] for chain in rule_data.chains(loose)] == [["loose-rule"]]
    loose_rows = rule_data.build_rows("panos_security_policy_rules", loose, naming.sanitize)
    facts = unit_manifest.facts_of(loose[0])
    assert loose_rows[0]["directory"] == unit_manifest.directory_name(facts, naming.sanitize), loose_rows
    assert loose_rows[0]["key"].split("_")[1] == unit_manifest.identity_digest(facts), loose_rows
    assert loose_rows[0]["pivot"] == "", loose_rows


# --- 6. The generator reads the grouping through this module ---------------


def test_the_generator_reads_the_chain_grouping_through_rule_data():
    """AC-6: the group is stated once, so the generator delegates to `rule_data.chains` (rule 3).

    Measured 2026-11-19: the per-instance position block is gone, because the instances inside one iterated block
    create in the key order (Epic 9 decision 4), so the helper's method ends at the next rule method. The print site
    pairs each chain with the rows built for it, so it reads the grouping through the helper and states none of its
    own; the `setdefault` it writes is the unit join, not a grouping.
    """
    source = Path(panorama_to_terraform.__file__).read_text(encoding="utf-8")
    method = source[source.index("def _policy_rule_chains") : source.index("def _rule_null")]
    assert "rule_data.chains(rules)" in method, method
    assert "setdefault" not in method, "the generator states no second grouping"
    site = source[source.index("def _print_policy_rules") : source.index("def generate_security_rules")]
    assert "self._policy_rule_chains(rules)" in site, "the print site reads the grouping through the helper"
    assert "rule_data.build_rows" in site, "the print site reads the row shape through the module that owns it"
    assert "rule_data.locals_name" in site, "the print site reads the map name through the same matrix row"
    holders = [
        path.name
        for path in sorted(SRC_DIR.glob("*.py"))
        if path.name != "rule_data.py" and "def chains" in path.read_text(encoding="utf-8")
    ]
    assert holders == [], holders


# --- 7. Two forms, one row set ---------------------------------------------


def test_the_printed_csv_states_the_same_rows_as_the_data():
    """AC-7: the header in field order, one line per row in row order, every value as its JSON text (rule 5)."""
    _, rules = recorded_rules("panos_security_policy_rules", "security_rules.xml")
    rows = rule_data.build_rows("panos_security_policy_rules", rules, naming.sanitize)
    printed = rule_data.render_csv(rows)
    lines = printed.splitlines()
    assert lines[0] == ",".join(rule_data.RULE_ROW_FIELDS), lines[0]
    assert len(lines) == len(rows) + 1, lines
    for line, row in zip(lines[1:], rows, strict=True):
        cells = list(csv.reader([line]))[0]
        assert len(cells) == len(rule_data.RULE_ROW_FIELDS), cells
        for cell, field in zip(cells, rule_data.RULE_ROW_FIELDS, strict=True):
            assert cell == json.dumps(row[field], ensure_ascii=True), (field, cell)
            assert json.loads(cell) == row[field], (field, cell)

    # The escape set is the one `import_blocks.unescape` reads back, so no second escape rule appears. The input
    # door refuses the control characters JSON prints as `\uXXXX`, so a value cannot hold one.
    value = 'say "hello"\tworld'
    printed_value = json.dumps(value, ensure_ascii=True)
    assert import_blocks.unescape(printed_value.strip('"')) == value, printed_value

    # A description with a comma stays one field, because the value is quoted by the print rule and by `csv`.
    comma = dict(rows[0], properties={"action": "allow", "description": "one, two"})
    cells = list(csv.reader(rule_data.render_csv([comma]).splitlines()[1:]))[0]
    assert json.loads(cells[5]) == comma["properties"], cells


# --- 8. No second rule and no writer ---------------------------------------


def test_the_rule_data_layer_states_no_second_rule_and_writes_no_file():
    """AC-8: the module states the row shape, the two file names, and the chain grouping, and reads every other
    rule through an owner.

    It defines no naming rule, no identity key, no unit rule, no path, no console line, no environment name, and
    no writer, and it imports only the standard library and the house modules. The row shape, the grouping and the
    two file names are the rules it states, so `parse_rows` is a reader of the shape and not a second statement of
    it, and the pair is written by the run through `write_path.py` (`tests/test_write_path.py` pins that no module
    of the tool writes a file outside the single writer).
    """
    source = Path(rule_data.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    defined = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            defined.add(node.name)
        elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            defined.add(node.targets[0].id)
    for name in ("write", "write_file", "sanitize", "name_ref", "ownership_key", "facts_of", "unit_name"):
        assert name not in defined, (name, "the module reads this rule through its owner")
    for token in ("CONSOLE_PREFIX", "console_line", "os.environ", "API_KEY_ENV", "open(", "write_text", "Path("):
        assert token not in source, token
    assert "RULE_ROW_FIELDS = " in source, "the module states the row shape it owns"

    # `re` is the reader for the third form, `printed_entries`, which names each entry of the printed map and hands
    # over its text, the part of it rule 5 owns. The module reads no value from that text, because reading a value is
    # the gate's one field reader's job and a shape rule stays in `parse_rows`. The module still writes nothing and
    # reads no record.
    imported = {alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names}
    house = {path.name[:-3] for path in SRC_DIR.glob("*.py")}
    assert imported <= {"csv", "io", "json", "re"} | house, imported
    assert imported & house, "the module reads its rules through the owners it imports"
    assert not hasattr(rule_data, "write_file"), "the single writer writes the file"
    entry_reader = source[source.index("def printed_entries") :]
    assert "field_value" not in entry_reader and "block_value" not in entry_reader, (
        "the printed-map reader names the entry and hands its text over, so no second field reader appears"
    )


# --- 9. The two file names, and the set the pair belongs to ------------------


def test_the_two_file_forms_are_unit_set_files_named_through_the_matrix_row(tmp_path):
    """AC-9: the two names are one stem with the two suffixes, and the pair names the unit file set (rule 5).

    `data_file`, `printed_file` and `locals_name` read the same matrix row, so the module states one name rule and
    not three: the stem is the row's `output_file` without its `.tf` suffix, the two files are that stem with `.json`
    and `.csv`, and the third form is the stem itself, which is the map the `.tf` file prints and the name of the
    block that reads it. A per-unit file names the kind it holds and never the unit, so the path is the only place
    the file states the unit it belongs to.
    states the unit it belongs to. The pair is not one of the four records the data rule reads, so the report's
    data count still names only the records at the codebase root. The generated `README.md` is the file inventory,
    so it names the two forms as files and states no row, no value, no count, no path and no timestamp, which is
    the exception `docs/CODEBASE_ASSEMBLY.md` §9 rule 9 grants it.
    """
    names = {rule_data.data_file(resource) for resource in RULE_TYPES}
    names |= {rule_data.printed_file(resource) for resource in RULE_TYPES}
    for resource in RULE_TYPES:
        stem = entry_coverage.MATRIX_BY_RESOURCE[resource]["output_file"][: -len(".tf")]
        assert rule_data.locals_name(resource) == stem, (resource, "the third form is the stem with no suffix")
        for name in (rule_data.data_file(resource), rule_data.printed_file(resource)):
            assert Path(name).stem == stem, (resource, name, "the two forms are one stem")
            assert Path(name).suffix in (".json", ".csv"), (resource, name)
            assert Path(name).name == name, (name, "a per-unit file names its unit only by its directory")
            assert "unit" not in name, name

    out = tmp_path / "unit_set"
    assert run_script(CONVERTER, str(FIXTURES_DIR / "kitchen_sink.xml"), "--output-dir", str(out)).returncode == 0
    written = written_bytes(out)
    dirs = {
        row["directory"]
        for row in unit_manifest.parse_rows((out / unit_manifest.MANIFEST_FILE).read_text(encoding="utf-8"))
    }
    pair = {key for key in written if Path(key).name in names}
    assert pair, "the corpus run writes the pair inside a unit directory"
    assert all(Path(key).parent.name in dirs for key in pair), sorted(pair)
    assert not names & set(dict(sanity_checks.DATA_FILES)), "neither form of the pair is one of the four records"
    # The count names the records at the root plus the pair's data member inside the unit directory its own rows
    # name, and no printed member: the printed form is not a reader input, the way `site.auto.tfvars` is not.
    members = {key for key in pair if Path(key).suffix == ".json"}
    assert members and len(pair) == 2 * len(members), sorted(pair)
    assert sanity_checks.count_data_files(out) == len(data_file_set(out)), "the count is the derivation"
    assert data_file_set(out) == sorted(list(dict(sanity_checks.DATA_FILES)) + sorted(members)), sorted(pair)

    readme = (out / "README.md").read_text(encoding="utf-8")
    inventory = readme[readme.index("## File Structure") :].splitlines()
    lines = [line for line in inventory if any(name in line for name in names)]
    assert lines, "the inventory names the two forms as files"
    for line in lines:
        assert not any(field in line for field in rule_data.RULE_ROW_FIELDS), (line, "the inventory names files")
        assert not any(char.isdigit() for char in line), (line, "no count")
        assert "/" not in line, (line, "no path")
        for word in ("timestamp", "generated_at"):
            assert word not in line, line
        assert not [directory for directory in dirs if directory in line], (line, "no unit name")


# --- 10. The run writes the pair ---------------------------------------------


def test_the_run_writes_one_pair_per_rule_type_per_unit_through_the_write_path(tmp_path):
    """AC-10: one pair per rule type per unit, inside the directory the `directory` column names (rule 5).

    Measured 2026-11-18 on the two fixtures the chain pins read. On `tests/fixtures/policy_order.xml` the manifest
    names five units and the three chains name three of them, so `panos_security_policy_rules` writes one pair in
    each of those three, `panos_nat_policy_rules` writes one pair in the one of them that has nat rows, and the two
    rule types with no rows write no pair in any unit. On `tests/fixtures/kitchen_sink.xml` all four rule types have
    rows in one unit, so each writes one pair there and no pair in the other ten. Each written JSON reads back through
    `parse_rows` as the rows `build_rows` built for that unit, each written CSV is `render_csv` of the same rows,
    and the bytes hold no CR, which is the byte rule `write_path.py` states in the one write function.
    """
    for fixture, units_measured in (("policy_order.xml", 5), ("kitchen_sink.xml", 11)):
        out = tmp_path / fixture
        assert run_script(CONVERTER, str(FIXTURES_DIR / fixture), "--output-dir", str(out)).returncode == 0
        written = written_bytes(out)
        dirs = {
            row["directory"]
            for row in unit_manifest.parse_rows((out / unit_manifest.MANIFEST_FILE).read_text(encoding="utf-8"))
        }
        assert len(dirs) == units_measured, (fixture, len(dirs))
        for resource in RULE_TYPES:
            rules = recorded_rules(resource, fixture)[1]
            rows = rule_data.build_rows(resource, rules, naming.sanitize)
            units = {row["directory"] for row in rows}
            for directory in dirs:
                key = f"{directory}/{rule_data.data_file(resource)}"
                printed = f"{directory}/{rule_data.printed_file(resource)}"
                assert (key in written) == (directory in units), (fixture, resource, directory)
                assert (printed in written) == (directory in units), (fixture, resource, directory)
                if directory not in units:
                    continue
                unit_rows = [row for row in rows if row["directory"] == directory]
                data_text = written[key].decode(encoding="utf-8")
                assert data_text == rule_data.render(unit_rows), key
                assert written[printed].decode(encoding="utf-8") == rule_data.render_csv(unit_rows), printed
                assert rule_data.parse_rows(data_text) == unit_rows, key
                assert b"\r" not in written[key] and b"\r" not in written[printed], (key, "the byte rule")


# --- 11. The third form reads back through the module that owns the key shape ---


def test_the_printed_map_reads_back_as_the_same_row_keys(tmp_path):
    """AC-11: the map the `.tf` file prints is the third form of the same rows, and `printed_entries` names its
    entries through the shape rule the module owns (rule 5).

    Measured 2026-11-19 on the kitchen-sink run: the file prints the unit's rows as the map, in the sorted key order,
    which is the XML order inside the chain. The keys read back are the keys `build_rows` built, the map name is the
    stem, and the printed form still answers no row to `parse_rows`, which refuses the printed forms and reads the
    data form. The reader hands over the entry text without reading a value from it, so the answer is the key and the
    text, and a hand-written map with a different indent reads as the same map.
    """
    out = tmp_path / "printed_map"
    assert run_script(CONVERTER, str(FIXTURES_DIR / "kitchen_sink.xml"), "--output-dir", str(out)).returncode == 0
    tf = {key: value.decode(encoding="utf-8") for key, value in written_bytes(out).items() if key.endswith(".tf")}
    read = 0
    for resource in RULE_TYPES:
        for key, text in sorted(tf.items()):
            if rule_data.locals_name(resource) not in text:
                continue
            directory = Path(key).parent.name
            rows = rule_data.parse_rows((out / directory / rule_data.data_file(resource)).read_text(encoding="utf-8"))
            keys = [entry["key"] for entry in rule_data.printed_entries(text, resource)]
            assert keys, key
            assert keys == sorted(row["key"] for row in rows), (key, keys)
            # The printed map is the third form, so the reader that reads rows refuses it.
            for form in (text, rule_data.render_csv(rows)):
                try:
                    rule_data.parse_rows(form)
                except ValueError:
                    continue
                raise AssertionError(f"{key}: the printed form is not reader input")
            read += 1
    assert read == 4, "the kitchen-sink run prints one map for each of the four rule types"

    # The indent is read from the file, so a map a person wrote answers the same entries as the map the emitter
    # printed: the gate reads the files the operator receives, so a different indent cannot answer a different set.
    resource = RULE_TYPES[0]
    stem = rule_data.locals_name(resource)
    key = "0001_" + "a" * unit_manifest.DIGEST_HEX
    printed_map = f'locals {{\n  {stem} = {{\n    "{key}" = {{\n      name = "one"\n    }}\n  }}\n}}\n'
    hand_written = f'locals {{\n\t{stem} = {{\n\t\t"{key}" = {{\n\t\t\tname = "one"\n\t\t}}\n\t}}\n}}\n'
    printed_answer = rule_data.printed_entries(printed_map, resource)
    hand_answer = rule_data.printed_entries(hand_written, resource)
    assert len(printed_answer) == 1 == len(hand_answer), (printed_answer, hand_answer)
    assert printed_answer[0]["key"] == hand_answer[0]["key"] == key, "the same key, whatever the indent states"
    assert set(printed_answer[0]) == {"key", "entry"}, "the answer names the entry and hands over its text"
    # A key that is not the declared shape is no answer, the way `parse_rows` refuses it.
    assert rule_data.printed_entries(printed_map.replace(key, "1_aaaaaaaa"), resource) == []
